import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'must_change_pass' not in st.session_state: st.session_state['must_change_pass'] = False

# --- LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login"):
        u = st.text_input("Utilizador").strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            try:
                base = get_base()
                df_users = pd.DataFrame(base.list_rows("Utilizadores"))
                # Comparação insensível a maiúsculas no Login
                user_row = df_users[df_users['Username'].str.lower() == u.lower()]
                
                if not user_row.empty:
                    stored_pass = str(user_row.iloc[0]['Password'])
                    if p == DEFAULT_PASS and stored_pass == DEFAULT_PASS:
                        st.session_state['must_change_pass'] = True
                        valid = True
                    elif hash_password(p) == stored_pass:
                        st.session_state['must_change_pass'] = False
                        valid = True
                    else: valid = False
                    
                    if valid:
                        st.session_state['auth_status'] = True
                        st.session_state['user_info'] = {
                            'username': user_row.iloc[0]['Username'],
                            'role': user_row.iloc[0]['Funcao'],
                            'row_id': user_row.iloc[0]['_id']
                        }
                        st.rerun()
                else: st.error("Incorreto.")
            except: st.error("Erro de ligação.")

else:
    base = get_base()
    user_data = st.session_state['user_info']

    # --- FORÇAR MUDANÇA DE PASS ---
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Altere a sua password.")
        with st.form("change_p"):
            new_p = st.text_input("Nova Password", type="password")
            if st.form_submit_button("Guardar"):
                base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(new_p)})
                st.session_state['must_change_pass'] = False
                st.rerun()
        st.stop()

    # --- MENU LATERAL ---
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    role = user_data['role']
    # Nome do utilizador em minúsculas para comparação segura
    current_user_lower = user_data['username'].lower().strip()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão de Direção")
        t1, t2 = st.tabs(["📅 Eventos", "🏫 Escola Geral"])
        with t2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                cols = [c for c in ['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in aulas.columns]
                st.dataframe(aulas[cols], hide_index=True, use_container_width=True)

    # --- 2. PROFESSOR (Correção de Filtro) ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        
        # Inserção
        with st.expander("➕ Novo Aluno"):
            with st.form("new_al"):
                na = st.text_input("Nome")
                ca = st.text_input("Contacto")
                ha = st.text_input("Horário")
                sa = st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": na, "Contacto": ca, "DiaHora": ha, "Sala": sa})
                    st.rerun()

        # Listagem
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            # FILTRO CORRIGIDO: Compara tudo em minúsculas
            meus = aulas[aulas['Professor'].str.lower().str.strip() == current_user_lower]
            
            if not meus.empty:
                cols = [c for c in ['Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in meus.columns]
                st.dataframe(meus[cols], hide_index=True, use_container_width=True)
                
                st.divider()
                rem_al = st.selectbox("Remover aluno:", meus['Aluno'].tolist())
                if st.button("Confirmar Remoção"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == rem_al].iloc[0]['_id'])
                    st.rerun()
            else:
                st.info("Ainda não tem alunos registados no seu nome.")
