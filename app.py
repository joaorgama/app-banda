import streamlit as st
import pandas as pd
from seatable_api import Base

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]

# Função de ligação persistente
def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

# Inicialização do estado da sessão
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
        # Comparação case-insensitive para o username
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
        st.error("Erro de ligação. Verifique o API Token.")
        return False

# --- INTERFACE DE LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Utilizador").strip()
        p = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if login_user(u, p):
                st.rerun() # Força a atualização imediata para entrar à primeira
            else:
                st.error("Utilizador ou Password incorretos.")

# --- APP PRINCIPAL (ÁREA LOGADA) ---
else:
    role = st.session_state['user_info']['role']
    user = st.session_state['user_info']['username'].lower()
    base = get_base()

    # Sidebar de navegação
    st.sidebar.title("Menu")
    st.sidebar.write(f"Utilizador: **{st.session_state['user_info']['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state['auth_status'] = False
        st.session_state['user_info'] = {}
        st.rerun()

    # --- 1. PERFIL: DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão de Direção")
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "👥 Utilizadores", "🖼️ Galeria"])
        
        with t1:
            st.subheader("Novo Evento")
            with st.expander("Adicionar Evento"):
                with st.form("add_ev"):
                    nome = st.text_input("Nome")
                    data = st.date_input("Data")
                    tipo = st.selectbox("Tipo", ["Ensaio", "Concerto", "Outro"])
                    cartaz = st.text_input("Link Cartaz")
                    if st.form_submit_button("Submeter"):
                        base.append_row("Eventos", {"Nome do Evento": nome, "Data": str(data), "Tipo": tipo, "Cartaz": cartaz})
                        st.rerun()

            st.divider()
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                st.dataframe(evs[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)
                ev_del = st.selectbox("Apagar evento:", evs['Nome do Evento'].tolist())
                if st.button("Eliminar Evento"):
                    base.delete_row("Eventos", evs[evs['Nome do Evento'] == ev_del].iloc[0]['_id'])
                    st.rerun()

        with t2:
            st.subheader("Lista Completa de Alunos")
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                st.dataframe(aulas[['Professor', 'Aluno', 'Contacto', 'DiaHora']], hide_index=True)

        with t3:
            st.dataframe(pd.DataFrame(base.list_rows("Utilizadores"))[['Nome', 'Funcao']], hide_index=True)

        with t4:
            # Galeria de Imagens
            evs_img = [e for e in base.list_rows("Eventos") if e.get('Cartaz')]
            cols = st.columns(2)
            for i, ev in enumerate(evs_img):
                with cols[i % 2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- 2. PERFIL: PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        
        with st.expander("➕ Novo Aluno"):
            with st.form("new_al"):
                na = st.text_input("Nome do Aluno")
                ca = st.text_input("Contacto")
                ha = st.text_input("Horário")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user, "Aluno": na, "Contacto": ca, "DiaHora": ha})
                    st.rerun()

        df_aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not df_aulas.empty:
            meus = df_aulas[df_aulas['Professor'].str.lower() == user]
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora']], hide_index=True, use_container_width=True)
                st.divider()
                rem_al = st.selectbox("Remover aluno:", meus['Aluno'].tolist())
                if st.button("Confirmar Saída"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == rem_al].iloc[0]['_id'])
                    st.rerun()

    # --- 3. PERFIL: MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Agenda e Galeria")
        m_t1, m_t2 = st.tabs(["📅 Agenda", "🖼️ Galeria"])
        with m_t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True)
        with m_t2:
            # Reutiliza a lógica da galeria
            evs_img = [e for e in base.list_rows("Eventos") if e.get('Cartaz')]
            cols = st.columns(2)
            for i, ev in enumerate(evs_img):
                with cols[i % 2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])
