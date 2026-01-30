import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
import unicodedata
from datetime import datetime

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

def get_base():
    for i in range(3):
        try:
            base = Base(API_TOKEN, SERVER_URL); base.auth()
            return base
        except: time.sleep(1)
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def remover_acentos(texto):
    if not texto or pd.isna(texto): return ""
    return unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8').lower().strip().replace(" ", "_")

def gerar_username(nome_completo):
    partes = str(nome_completo).strip().split()
    if len(partes) >= 2:
        u = f"{partes[0]}_{partes[-1]}"
    else:
        u = partes[0]
    return remover_acentos(u)

def formatar_data_pt(data_str):
    try:
        if not data_str or str(data_str) in ['None', 'nan', '']: return "---"
        return pd.to_datetime(data_str).strftime('%d/%m/%Y')
    except: return str(data_str)

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- LOGIN ---
if base and not st.session_state['auth_status']:
    st.header("🎵 Portal da Banda")
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            match = df_u[df_u['Username'] == u_in]
            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                if (p_in == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p_in) == stored_p:
                    st.session_state.update({
                        'auth_status': True, 
                        'must_change_pass': (stored_p == DEFAULT_PASS), 
                        'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}
                    })
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🖼️ Galeria"])
        
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)

        with t2:
            musicos = base.list_rows("Musicos")
            # Procura o músico comparando o username gerado pelo nome na tabela
            m_row = next((r for r in musicos if gerar_username(r.get('Nome')) == user['username']), None)
            
            if m_row:
                with st.form("perfil_musico"):
                    # Limpeza de telefone (remover .0)
                    tel_val = str(m_row.get('Telefone', '')).replace('.0', '')
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        n_tel = st.text_input("Telefone", value=tel_val)
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                        # Data de Nascimento
                        d_nasc_raw = m_row.get('Data de Nascimento')
                        try:
                            d_init = datetime.strptime(d_nasc_raw, '%Y-%m-%d') if d_nasc_raw else datetime.now()
                        except:
                            d_init = datetime.now()
                        n_nasc = st.date_input("Data de Nascimento", value=d_init)
                    
                    with col2:
                        st.info(f"Ingresso na Banda: {formatar_data_pt(m_row.get('Data Ingresso Banda'))}")
                        n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    
                    st.text_area("Observações (Apenas Leitura)", value=str(m_row.get('Obs', '')), disabled=True)
                    
                    if st.form_submit_button("Gravar Alterações"):
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)
                        })
                        st.success("Dados atualizados com sucesso!"); time.sleep(1); st.rerun()
            else:
                st.warning("Não foi possível encontrar a sua ficha de músico. Contacte a Direção.")

        with t3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(2)
                for i, ev in enumerate(arts):
                    with cols[i%2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- PAINEL DIREÇÃO ---
    elif user['role'] == "Direcao":
        st.title("🛡️ Gestão Direção")
        tab1, tab2, tab3 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria"])
        
        with tab1:
            with st.expander("➕ Novo Evento"):
                with st.form("novo_evento"):
                    n, d, t, c = st.text_input("Nome"), st.date_input("Data"), st.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada"]), st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Tipo": t, "Cartaz": c}); st.rerun()
            
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                # Mostrar em tabela formatada
                st.subheader("Lista de Eventos")
                for idx, row in evs.iterrows():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.write(row['Nome do Evento'])
                    c2.write(formatar_data_pt(row['Data']))
                    c3.write(row['Tipo'])
                    if c4.button("🗑️", key=f"del_ev_{idx}"):
                        base.delete_row("Eventos", row['_id']); st.rerun()
                    st.divider()

        with tab2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)

        with tab3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3)
                for i, ev in enumerate(arts):
                    with cols[i%3]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- PAINEL PROFESSOR ---
    elif user['role'] == "Professor":
        st.title("👨‍🏫 Área Professor")
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add_al"):
                n, c, h, s = st.text_input("Nome"), st.text_input("Contacto"), st.text_input("Dia/Hora"), st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
        
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'] == user['display_name']]
            st.subheader("Os meus Alunos")
            for idx, row in meus.iterrows():
                cols = st.columns([3, 2, 2, 2, 1])
                cols[0].write(row['Aluno'])
                cols[1].write(row['Contacto'])
                cols[2].write(row['DiaHora'])
                cols[3].write(row['Sala'])
                if cols[4].button("🗑️", key=f"del_al_{idx}"):
                    base.delete_row("Aulas", row['_id']); st.rerun()
                st.divider()
