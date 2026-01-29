import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

# Função de ligação com tentativa de recuperação (Resolve erro de 1ª vez)
def get_base():
    for i in range(3):
        try:
            base = Base(API_TOKEN, SERVER_URL)
            base.auth()
            return base
        except:
            time.sleep(0.5)
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

# Inicialização robusta de estados
if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'must_change_pass' not in st.session_state: st.session_state['must_change_pass'] = False

# --- INTERFACE DE LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login_form"):
        u = st.text_input("Utilizador").strip().lower()
        p = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Entrar")
        
        if submit:
            base = get_base()
            if base:
                users = base.list_rows("Utilizadores")
                df_users = pd.DataFrame(users)
                user_row = df_users[df_users['Username'].str.lower() == u]
                
                if not user_row.empty:
                    stored_p = str(user_row.iloc[0]['Password'])
                    if p == DEFAULT_PASS and stored_p == DEFAULT_PASS:
                        st.session_state['must_change_pass'] = True
                        valid = True
                    elif hash_password(p) == stored_p:
                        st.session_state['must_change_pass'] = False
                        valid = True
                    else: 
                        st.error("Password incorreta.")
                        valid = False
                    
                    if valid:
                        st.session_state['auth_status'] = True
                        st.session_state['user_info'] = {
                            'username': user_row.iloc[0]['Username'],
                            'role': user_row.iloc[0]['Funcao'],
                            'row_id': user_row.iloc[0]['_id']
                        }
                        st.rerun()
                else: st.error("Utilizador não encontrado.")
            else: st.error("Servidor ocupado. Tente novamente.")

# --- ÁREA LOGADA ---
else:
    base = get_base()
    user_data = st.session_state['user_info']
    role = user_data['role']
    username_clean = user_data['username'].lower().strip()

    # MUDANÇA DE PASSWORD
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Altere a sua password para continuar.")
        with st.form("new_pass"):
            np = st.text_input("Nova Password", type="password")
            if st.form_submit_button("Guardar"):
                base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(np)})
                st.session_state['must_change_pass'] = False
                st.success("Atualizado!")
                st.rerun()
        st.stop()

    # MENU LATERAL
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão Direção")
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria"])
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty: st.dataframe(evs[['Nome do Evento', 'Data', 'Tipo']], hide_index=True)
        with t2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True)
        with t3:
            for e in base.list_rows("Eventos"):
                if e.get('Cartaz'): st.image(e['Cartaz'], caption=e['Nome do Evento'])

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área Professor")
        # Inserção de alunos
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add"):
                n = st.text_input("Nome"); c = st.text_input("Contacto"); h = st.text_input("Horário"); s = st.text_input("Sala")
                if st.form_submit_button("OK"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s})
                    st.rerun()
        
        # Filtro corrigido para mostrar dados do Marco/Nelson
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'].str.lower().str.strip() == username_clean]
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True)
            else: st.info("Sem alunos registados.")

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Área Músico")
        m_t1, m_t2 = st.tabs(["📅 Agenda", "🖼️ Galeria"])
        evs = pd.DataFrame(base.list_rows("Eventos"))
        with m_t1:
            if not evs.empty: st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True)
        with m_t2:
            for e in base.list_rows("Eventos"):
                if e.get('Cartaz'): st.image(e['Cartaz'], caption=e['Nome do Evento'])
