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

st.set_page_config(page_title="App Banda", page_icon="🎵", layout="wide")

# --- LOGIN STATE ---
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- SIDEBAR ---
if st.session_state['user_role'] is not None:
    st.sidebar.markdown(f"### Bem-vindo, \n**{st.session_state['username'].capitalize()}**")
    st.sidebar.write(f"Perfil: {st.session_state['user_role']}")
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.rerun()
    if st.sidebar.button("🚪 Sair"):
        st.session_state['user_role'] = None
        st.session_state['username'] = None
        st.rerun()

# --- LÓGICA DE LOGIN ---
if st.session_state['user_role'] is None:
    st.header("🎵 Gestão da Banda")
    with st.form("login_form"):
        u_input = st.text_input("Utilizador").strip()
        p_input = st.text_input("Password", type="password").strip()
        submit_login = st.form_submit_button("Entrar")
    
    if submit_login:
        try:
            base = get_base()
            users = base.list_rows("Utilizadores")
            df_users = pd.DataFrame(users)
            
            # Login case-insensitive: converte tudo para minúsculas para comparar
            user_found = df_users[
                (df_users['Username'].str.lower() == u_input.lower()) & 
                (df_users['Password'].astype(str) == p_input)
            ]
            
            if not user_found.empty:
                st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                st.session_state['username'] = user_found.iloc[0]['Username']
                st.rerun()
            else:
                st.error("Utilizador ou Password incorretos.")
        except Exception as e:
            st.error(f"Erro de ligação ao servidor: {e}")

# --- ÁREA RESTRITA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username'].lower().strip()
    base = get_base()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Painel de Direção")
        
        tab1, tab2 = st.tabs(["📅 Eventos", "👥 Utilizadores"])
        
        with tab1:
            rows = base.list_rows("Eventos")
            if rows:
                df = pd.DataFrame(rows)
                cols = [c for c in ['Nome do Evento', 'Data', 'Tipo', 'Descricao'] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info("Nenhum evento registado.")

        with tab2:
            rows_u = base.list_rows("Utilizadores")
            if rows_u:
                df_u = pd.DataFrame(rows_u)
                cols_u = [c for c in ['Nome', 'Funcao', 'Username'] if c in df_u.columns]
                st.table(df_u[cols_u])

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        st.subheader(f"Horário de: {st.session_state['username']}")
        
        rows = base.list_rows("Aulas")
        if rows:
            df = pd.DataFrame(rows)
            # Filtro case-insensitive para o professor
            mask = df['Professor'].str.lower().str.strip() == user
            meus_alunos = df[mask]
            
            if not meus_alunos.empty:
                cols = [c for c in ['DiaHora', 'Aluno', 'Sala'] if c in meus_alunos.columns]
                st.table(meus_alunos[cols])
            else:
                st.info("Não tem aulas agendadas para o seu nome.")
        else:
            st.warning("A tabela de aulas está vazia.")

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Espaço do Músico")
        st.subheader("📅 Próximos Concertos e Ensaios")
        
        rows = base.list_rows("Eventos")
        if rows:
            df = pd.DataFrame(rows)
            # Limpeza de colunas para o músico
            cols = [c for c in ['Data', 'Nome do Evento', 'Tipo', 'Descricao'] if c in df.columns]
            # Ordenar por data se a coluna existir
            if 'Data' in df.columns:
                df = df.sort_values(by='Data')
            
            st.table(df[cols])
        else:
            st.info("Não existem eventos marcados de momento.")
