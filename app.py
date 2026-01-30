import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
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
            match = df_u[df_u['Username'].str.lower() == u_in]
            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                
                # Validação de password (texto simples ou hash)
                valid_pass = (p_in == stored_p) or (hash_password(p_in) == stored_p)
                
                if valid_pass:
                    must_change = (stored_p == DEFAULT_PASS)
                    st.session_state.update({
                        'auth_status': True, 
                        'must_change_pass': must_change, 
                        'user_info': {
                            'username': u_in, 
                            'display_name': row.get('Nome', u_in), 
                            'role': row['Funcao'], 
                            'row_id': row['_id']
                        }
                    })
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- BLOQUEIO PARA ALTERAÇÃO DE PASSWORD ---
elif st.session_state.get('must_change_pass'):
    st.warning("⚠️ Segurança: Altere a sua password de primeiro acesso (1234).")
    with st.form("force_change"):
        np = st.text_input("Nova Password", type="password")
        cp = st.text_input("Confirmar Password", type="password")
        if st.form_submit_button("Atualizar e Entrar"):
            if np == cp and len(np) >= 4:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(np)})
                st.session_state['must_change_pass'] = False
                st.success("Sucesso! A carregar portal...")
                time.sleep(1); st.rerun()
            else: st.error("As passwords não coincidem ou são muito curtas.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    if user['role'] == "Musico":
        t1, t2, t3 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🖼️ Galeria"])
        
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data_FT'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data_FT', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)

        with t2:
            musicos = base.list_rows("Musicos")
            # Procura primeiro por Username, depois por Nome
            m_row = next((r for r in musicos if str(r.get('Username','')).lower() == user['username']), None)
            if not m_row:
                m_row = next((r for r in musicos if r.get('Nome') == user['display_name']), None)
            
            if m_row:
                with st.form("perfil"):
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                        
                        # DATA DE NASCIMENTO (Validação Real)
                        d_val = m_row.get('Data de Nascimento')
                        try:
                            d_init = datetime.strptime(str(d_val), '%Y-%m-%d') if d_val else datetime(2000, 1, 1)
                        except:
                            d_init = datetime(2000, 1, 1)
                        n_nasc = st.date_input("Data de Nascimento", value=d_init)
                    
                    with col2:
                        st.info(f"📅 Ingresso: {formatar_data_pt(m_row.get('Data Ingresso Banda'))}")
                        n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    
                    st.text_area("Observações", value=str(m_row.get('Obs', '')), disabled=True)
                    if st.form_submit_button("💾 Guardar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)})
                        st.success("Dados guardados!"); time.sleep(1); st.rerun()
            else:
                st.error("Não encontrámos a sua ficha. Peça à Direção para preencher o seu 'Username' na tabela Musicos.")

        with t3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3)
                for i, ev in enumerate(arts):
                    with cols[i%3]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    elif user['role'] == "Direcao":
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola", "🖼️ Galeria"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    n, d, t, c = st.text_input("Nome"), st.date_input("Data"), st.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada"]), st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Tipo": t, "Cartaz": c}); st.rerun()
            
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                df_d = evs.copy(); df_d['Data'] = df_d['Data'].apply(formatar_data_pt)
                st.dataframe(df_d[['Data', 'Nome do Evento', 'Tipo']], use_container_width=True, hide_index=True)
                with st.expander("🗑️ Apagar Evento"):
                    for idx, r in evs.iterrows():
                        c1, c2 = st.columns([5,1])
                        c1.write(f"{r['Nome do Evento']} ({r['Data']})")
                        if c2.button("Apagar", key=f"dev_{idx}"):
                            base.delete_row("Eventos", r['_id']); st.rerun()
        with t2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
        with t3:
            evs = base.list_rows("Eventos")
            for e in evs:
                if e.get('Cartaz'): st.image(e['Cartaz'], width=300)

    elif user['role'] == "Professor":
        st.title("👨‍🏫 Meus Alunos")
        with st.expander("➕ Novo Aluno"):
            with st.form("na"):
                n, c, h, s = st.text_input("Nome"), st.text_input("Telemóvel"), st.text_input("Horário"), st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
        
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'] == user['display_name']]
            st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
            with st.expander("🗑️ Remover Aluno"):
                for idx, r in meus.iterrows():
                    c1, c2 = st.columns([5,1])
                    if c2.button("Eliminar", key=f"dal_{idx}"):
                        base.delete_row("Aulas", r['_id']); st.rerun()
