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
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().replace(" ", "_")

def gerar_username(nome_completo):
    partes = str(nome_completo).strip().split()
    u = f"{partes[0]}_{partes[-1]}" if len(partes) >= 2 else partes[0]
    return remover_acentos(u)

def formatar_data_pt(data_str):
    try:
        if not data_str or str(data_str) in ['None', 'nan', '']: return "---"
        return pd.to_datetime(data_str).strftime('%d/%m/%Y')
    except: return str(data_str)

def sincronizar_e_limpar(base):
    try:
        rows_u = base.list_rows("Utilizadores")
        df_m = pd.DataFrame(base.list_rows("Musicos"))
        # Limpa users com acentos/cedilhas no Username
        for r in rows_u:
            u_orig = r.get('Username', '')
            if u_orig != remover_acentos(u_orig):
                base.delete_row("Utilizadores", r['_id'])
        
        df_u_atual = pd.DataFrame(base.list_rows("Utilizadores"))
        existentes = df_u_atual['Username'].tolist() if not df_u_atual.empty else []
        for _, m in df_m.iterrows():
            novo_u = gerar_username(m['Nome'])
            if novo_u not in existentes:
                base.append_row("Utilizadores", {"Username": novo_u, "Password": DEFAULT_PASS, "Funcao": "Musico", "Nome": m['Nome']})
    except: pass

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- INTERFACE DE LOGIN ---
if base and not st.session_state['auth_status']:
    sincronizar_e_limpar(base)
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
                if p_in == DEFAULT_PASS and stored_p == DEFAULT_PASS:
                    st.session_state.update({'auth_status': True, 'must_change_pass': True, 'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                elif hash_password(p_in) == stored_p:
                    st.session_state.update({'auth_status': True, 'must_change_pass': False, 'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Altere a sua password para o primeiro acesso.")
        with st.form("change"):
            n1 = st.text_input("Nova Password", type="password")
            n2 = st.text_input("Confirmar", type="password")
            if st.form_submit_button("Atualizar"):
                if n1 == n2 and len(n1) >= 4:
                    base.update_row("Utilizadores", user['row_id'], {"Password": hash_password(n1)})
                    st.session_state['must_change_pass'] = False
                    st.success("Sucesso! Password alterada.")
                    time.sleep(1); st.session_state.clear(); st.rerun()
                else: st.error("Erro nas passwords.")
        st.stop()

    # SIDEBAR
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    st.sidebar.caption(f"Acesso: {user['role']}")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear(); st.rerun()

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🖼️ Galeria"])
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True)
        with t2:
            musicos = base.list_rows("Musicos")
            m_row = next((r for r in musicos if r.get('Nome') == user['display_name']), None)
            if m_row:
                with st.form("perfil"):
                    tel_limpo = str(m_row.get('Telefone', '')).split('.')[0]
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=tel_limpo)
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                        d_nasc_val = m_row.get('Data de Nascimento')
                        try: d_nasc_default = datetime.strptime(d_nasc_val, '%Y-%m-%d') if d_nasc_val else datetime.now()
                        except: d_nasc_default = datetime.now()
                        n_nasc = st.date_input("Data de Nascimento", value=d_nasc_default)
                    with col2:
                        st.info(f"Ingresso: {formatar_data_pt(m_row.get('Data Ingresso Banda'))}")
                        n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    st.text_area("Observações", value=str(m_row.get('Obs', '')), disabled=True)
                    if st.form_submit_button("Gravar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)})
                        st.success("Dados guardados!"); time.sleep(1); st.rerun()
        with t3:
            evs = base.list_rows("Eventos")
            cartazes = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if cartazes:
                c = st.columns(2)
                for i, ev in enumerate(cartazes):
                    with c[i%2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])
            else: st.info("Sem cartazes.")

    # --- PAINEL DIREÇÃO ---
    elif user['role'] == "Direcao":
        st.title("🛡️ Painel de Direção")
        tab_ev, tab_esc = st.tabs(["📅 Gestão de Eventos", "🏫 Escola Geral"])
        with tab_ev:
            with st.expander("➕ Novo Evento"):
                with st.form("add_ev"):
                    e_nome = st.text_input("Nome do Evento")
                    col1, col2 = st.columns(2)
                    e_data = col1.date_input("Data")
                    e_tipo = col2.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada", "Outro"])
                    e_cartaz = st.text_input("URL do Cartaz")
                    if st.form_submit_button("Criar Evento"):
                        base.append_row("Eventos", {"Nome do Evento": e_nome, "Data": str(e_data), "Tipo": e_tipo, "Cartaz": e_cartaz})
                        st.success("Evento criado!"); st.rerun()
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data_FT'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data_FT', 'Nome do Evento', 'Tipo']], hide_index=True)
        with tab_esc:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], hide_index=True)

    # --- PAINEL PROFESSOR ---
    elif user['role'] == "Professor":
        st.title("👨‍🏫 Área do Professor")
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add_aluno"):
                al_nome = st.text_input("Nome do Aluno")
                al_cont = st.text_input("Contacto")
                al_hora = st.text_input("Dia/Hora (ex: 2ª feira 18:00)")
                al_sala = st.text_input("Sala")
                if st.form_submit_button("Registar Aluno"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": al_nome, "Contacto": al_cont, "DiaHora": al_hora, "Sala": al_sala})
                    st.rerun()
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'] == user['display_name']]
            st.write("### Os meus Alunos")
            st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True)
