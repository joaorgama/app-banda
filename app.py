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

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state:
    st.session_state['auth_status'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}

# --- LÓGICA DE LOGIN ---
def login_user(u, p):
    try:
        base = get_base()
        users = base.list_rows("Utilizadores")
        df_users = pd.DataFrame(users)
        match = df_users[(df_users['Username'].str.lower() == u.lower()) & (df_users['Password'].astype(str) == p)]
        
        if not match.empty:
            st.session_state['auth_status'] = True
            st.session_state['user_info'] = {
                'username': match.iloc[0]['Username'],
                'role': match.iloc[0]['Funcao']
            }
            return True
        return False
    except:
        return False

# --- INTERFACE DE LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login_form"):
        u = st.text_input("Utilizador").strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            if login_user(u, p):
                st.rerun()
            else:
                st.error("Utilizador ou Password incorretos.")

# --- ÁREA LOGADA ---
else:
    role = st.session_state['user_info']['role']
    user = st.session_state['user_info']['username'].lower().strip()
    base = get_base()

    st.sidebar.title("Menu")
    st.sidebar.write(f"Utilizador: **{st.session_state['user_info']['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão de Direção")
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "👥 Utilizadores", "🖼️ Galeria"])
        
        with t1:
            # (Gestão de Eventos)
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                st.dataframe(evs[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)

        with t2:
            st.subheader("Lista Geral de Alunos e Salas")
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                # ADICIONADO: 'Sala' na visualização da Direção
                cols_dir = [c for c in ['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in aulas.columns]
                st.dataframe(aulas[cols_dir].sort_values(by='Professor'), hide_index=True, use_container_width=True)

        with t3:
            st.dataframe(pd.DataFrame(base.list_rows("Utilizadores"))[['Nome', 'Funcao']], hide_index=True)

        with t4:
            evs_img = [e for e in base.list_rows("Eventos") if e.get('Cartaz')]
            cols = st.columns(2)
            for i, ev in enumerate(evs_img):
                with cols[i % 2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        
        with st.expander("➕ Novo Aluno"):
            with st.form("new_al"):
                na = st.text_input("Nome")
                ca = st.text_input("Contacto")
                ha = st.text_input("Horário")
                sa = st.text_input("Sala") # Campo de inserção da Sala
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user, "Aluno": na, "Contacto": ca, "DiaHora": ha, "Sala": sa})
                    st.rerun()

        df_aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not df_aulas.empty:
            meus = df_aulas[df_aulas['Professor'].str.lower().str.strip() == user]
            if not meus.empty:
                # ADICIONADO: 'Sala' na visualização do Professor
                cols_prof = [c for c in ['Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in meus.columns]
                st.dataframe(meus[cols_prof], hide_index=True, use_container_width=True)
                
                st.divider()
                rem_al = st.selectbox("Remover aluno:", meus['Aluno'].tolist())
                if st.button("Confirmar Remoção"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == rem_al].iloc[0]['_id'])
                    st.rerun()

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Agenda")
        evs = pd.DataFrame(base.list_rows("Eventos"))
        if not evs.empty:
            st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
