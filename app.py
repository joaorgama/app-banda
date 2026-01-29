import streamlit as st
import pandas as pd
from seatable_api import Base

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]

def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

st.set_page_config(page_title="App Banda", page_icon="🎵")

# --- LOGIN STATE ---
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- SIDEBAR ---
if st.session_state['user_role'] is not None:
    st.sidebar.write(f"Logado como: **{st.session_state['username']}**")
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.rerun()
    if st.sidebar.button("Sair"):
        st.session_state['user_role'] = None
        st.session_state['username'] = None
        st.rerun()

# --- LÓGICA DE LOGIN ---
if st.session_state['user_role'] is None:
    st.header("🎵 Login da Banda")
    username_input = st.text_input("Utilizador")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Entrar"):
        try:
            base = get_base()
            users = base.list_rows("Utilizadores")
            df_users = pd.DataFrame(users)
            
            user_found = df_users[
                (df_users['Username'] == username_input) & 
                (df_users['Password'] == str(password_input))
            ]
            
            if not user_found.empty:
                st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                st.session_state['username'] = user_found.iloc[0]['Username']
                st.rerun()
            else:
                st.error("Utilizador ou Password errados.")
        except Exception as e:
            st.error(f"Erro de ligação: {e}")

# --- ÁREA RESTRITA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username']
    base = get_base()

    if role == "Direcao":
        st.title("Painel Direção")
        rows = base.list_rows("Eventos")
        st.write("Lista de Eventos:")
        st.dataframe(pd.DataFrame(rows))

    elif role == "Professor":
        st.title("Área do Professor")
        st.subheader(f"Horário de: {user}")
        
        rows = base.list_rows("Aulas")
        if rows:
            df = pd.DataFrame(rows)
            # Filtro para mostrar apenas as aulas deste professor
            meus_alunos = df[df['Professor'] == user]
            if not meus_alunos.empty:
                st.table(meus_alunos)
            else:
                st.info("Nenhuma aula encontrada para o seu utilizador.")
        else:
            st.warning("Tabela de aulas vazia.")

    elif role == "Musico":
        st.title("Agenda de Músico")
        rows = base.list_rows("Eventos")
        if rows:
            st.write("Próximos compromissos:")
            st.table(pd.DataFrame(rows))
