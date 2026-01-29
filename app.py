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

if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- SIDEBAR ---
if st.session_state['user_role'] is not None:
    st.sidebar.markdown(f"### Olá, **{st.session_state['username'].capitalize()}**")
    if st.sidebar.button("🔄 Atualizar"): st.rerun()
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

# --- LOGIN ---
if st.session_state['user_role'] is None:
    st.header("🎵 Portal da Banda")
    with st.form("login"):
        u = st.text_input("Utilizador").strip().lower()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            try:
                base = get_base()
                df_users = pd.DataFrame(base.list_rows("Utilizadores"))
                user_found = df_users[(df_users['Username'].str.lower() == u) & (df_users['Password'].astype(str) == p)]
                if not user_found.empty:
                    st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                    st.session_state['username'] = user_found.iloc[0]['Username']
                    st.rerun()
                else: st.error("Incorreto")
            except: st.error("Erro de ligação")

# --- ÁREA LOGADA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username'].lower()
    base = get_base()

    # --- FUNÇÃO GALERIA (Para Músicos e Direção) ---
    def mostrar_galeria():
        st.subheader("🖼️ Cartazes e Fotos")
        eventos = base.list_rows("Eventos")
        if eventos:
            cols = st.columns(2) # Cria 2 colunas para telemóvel
            for i, ev in enumerate([e for e in eventos if e.get('Cartaz')]):
                with cols[i % 2]:
                    st.image(ev['Cartaz'], caption=ev.get('Nome do Evento'), use_container_width=True)
        else: st.write("Sem imagens.")

    if role == "Direcao":
        st.title("🛡️ Gestão")
        t1, t2, t3 = st.tabs(["Agenda", "Utilizadores", "Galeria"])
        with t1:
            df = pd.DataFrame(base.list_rows("Eventos"))
            st.dataframe(df[['Nome do Evento', 'Data', 'Tipo']] if not df.empty else [])
        with t2:
            st.table(pd.DataFrame(base.list_rows("Utilizadores"))[['Nome', 'Funcao']])
        with t3: mostrar_galeria()

    elif role == "Professor":
        st.title("🏫 Professor")
        df = pd.DataFrame(base.list_rows("Aulas"))
        if not df.empty:
            meus = df[df['Professor'].str.lower() == user]
            st.table(meus[['DiaHora', 'Aluno', 'Sala']] if not meus.empty else [])

    elif role == "Musico":
        st.title("🎺 Músico")
        t_m1, t_m2 = st.tabs(["📅 Agenda", "🖼️ Galeria"])
        with t_m1:
            df = pd.DataFrame(base.list_rows("Eventos"))
            if not df.empty:
                st.table(df[['Data', 'Nome do Evento', 'Tipo']])
        with t_m2: mostrar_galeria()
