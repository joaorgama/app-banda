import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234" # Password que obriga a mudar

def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

# Função para encriptar a password
def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

# Inicialização de estados
if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'must_change_pass' not in st.session_state: st.session_state['must_change_pass'] = False

# --- LÓGICA DE LOGIN ---
def login_user(u, p):
    try:
        base = get_base()
        df_users = pd.DataFrame(base.list_rows("Utilizadores"))
        user_row = df_users[df_users['Username'].str.lower() == u.lower()]
        
        if not user_row.empty:
            stored_pass = str(user_row.iloc[0]['Password'])
            
            # Verifica se é a pass default (sem encriptação) ou a pass encriptada
            if p == DEFAULT_PASS and stored_pass == DEFAULT_PASS:
                st.session_state['must_change_pass'] = True
                valid = True
            elif hash_password(p) == stored_pass:
                st.session_state['must_change_pass'] = False
                valid = True
            else:
                return False

            if valid:
                st.session_state['auth_status'] = True
                st.session_state['user_info'] = {
                    'username': user_row.iloc[0]['Username'],
                    'role': user_row.iloc[0]['Funcao'],
                    'row_id': user_row.iloc[0]['_id']
                }
                return True
        return False
    except: return False

# --- INTERFACE DE LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login"):
        u = st.text_input("Utilizador").strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            if login_user(u, p): st.rerun()
            else: st.error("Incorreto.")

# --- APP PRINCIPAL ---
else:
    base = get_base()
    user_data = st.session_state['user_info']

    # FORÇAR ALTERAÇÃO DE PASSWORD
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Deve alterar a sua password de primeiro acesso.")
        with st.form("change_pass_force"):
            new_p = st.text_input("Nova Password", type="password")
            conf_p = st.text_input("Confirme a Nova Password", type="password")
            if st.form_submit_button("Guardar Password"):
                if len(new_p) < 4:
                    st.error("A password deve ter pelo menos 4 caracteres.")
                elif new_p == conf_p:
                    base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(new_p)})
                    st.session_state['must_change_pass'] = False
                    st.success("Password alterada! A aplicação vai reiniciar.")
                    st.rerun()
                else: st.error("As passwords não coincidem.")
        st.stop() # Bloqueia o resto da app até mudar

    # MENU LATERAL COM OPÇÃO DE MUDAR PASS
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    
    with st.sidebar.expander("⚙️ Definições de Conta"):
        if st.button("Alterar Password"):
            st.session_state['must_change_pass'] = True
            st.rerun()

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # --- RESTO DA APP (Direção / Professor / Musico) ---
    role = user_data['role']
    user = user_data['username'].lower()

    if role == "Direcao":
        st.title("🛡️ Gestão")
        # ... (Tabelas e Tabs de Direção igual à v8)
        st.info("Nota: Para resetar a pass de alguém, escreva '1234' no SeaTable dessa pessoa.")
        
    elif role == "Professor":
        st.title("🏫 Área Professor")
        # ... (Gestão de Alunos igual à v8)

    elif role == "Musico":
        st.title("🎺 Espaço Músico")
        # ... (Agenda igual à v8)
