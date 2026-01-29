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

# Inicialização de estados
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- LOGIN (Com suporte a tecla ENTER) ---
if not st.session_state['logged_in']:
    st.header("🎵 Portal da Banda")
    with st.form("login_form"):
        u_input = st.text_input("Utilizador").strip().lower()
        p_input = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Entrar")
        
        if submit:
            try:
                base = get_base()
                users = base.list_rows("Utilizadores")
                df_users = pd.DataFrame(users)
                user_found = df_users[(df_users['Username'].str.lower() == u_input) & (df_users['Password'].astype(str) == p_input)]
                
                if not user_found.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                    st.session_state['username'] = user_found.iloc[0]['Username']
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
            except:
                st.error("Erro de ligação. Verifique se o API Token nos 'Secrets' está correto.")
else:
    # --- ÁREA LOGADA ---
    role = st.session_state['user_role']
    user = st.session_state['username'].lower().strip()
    base = get_base()

    # Barra lateral
    st.sidebar.markdown(f"### Olá, **{st.session_state['username'].capitalize()}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Painel de Gestão")
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "👥 Utilizadores", "🏫 Escola Geral", "🖼️ Galeria"])
        
        with t1:
            st.subheader("Adicionar Evento")
            with st.expander("Abrir Formulário"):
                with st.form("add_event"):
                    n = st.text_input("Nome do Evento")
                    d = st.date_input("Data")
                    t = st.selectbox("Tipo", ["Ensaio", "Concerto", "Outro"])
                    img = st.text_input("URL do Cartaz")
                    if st.form_submit_button("Guardar Evento"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Tipo": t, "Cartaz": img})
                        st.success("Adicionado!")
                        st.rerun()
            
            evs = base.list_rows("Eventos")
            if evs:
                df_ev = pd.DataFrame(evs)
                st.dataframe(df_ev[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)
                
                st.subheader("🗑️ Apagar Evento")
                ev_to_del = st.selectbox("Evento a remover:", df_ev['Nome do Evento'].tolist())
                if st.button("Eliminar"):
                    id_del = df_ev[df_ev['Nome do Evento'] == ev_to_del].iloc[0]['_id']
                    base.delete_row("Eventos", id_del)
                    st.rerun()

        with t2:
            st.dataframe(pd.DataFrame(base.list_rows("Utilizadores"))[['Nome', 'Funcao']], hide_index=True)

        with t3:
            st.subheader("Todos os Professores e Alunos")
            aulas = base.list_rows("Aulas")
            if aulas:
                df_all = pd.DataFrame(aulas)
                df_all = df_all[['Professor', 'Aluno', 'Contacto', 'DiaHora']].sort_values(by='Professor')
                st.dataframe(df_all, hide_index=True, use_container_width=True)

        with t4:
            evs_img = [e for e in base.list_rows("Eventos") if e.get('Cartaz')]
            cols = st.columns(2)
            for i, ev in enumerate(evs_img):
                with cols[i % 2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        
        with st.expander("➕ Registar Aluno"):
            with st.form("add_aluno"):
                n_a = st.text_input("Nome")
                c_a = st.text_input("Contacto")
                h_a = st.text_input("Horário")
                if st.form_submit_button("Confirmar"):
                    base.append_row("Aulas", {"Professor": user, "Aluno": n_a, "Contacto": c_a, "DiaHora": h_a})
                    st.rerun()

        aulas = base.list_rows("Aulas")
        if aulas:
            df = pd.DataFrame(aulas)
            meus = df[df['Professor'].str.lower() == user]
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora']], hide_index=True, use_container_width=True)
                st.subheader("🗑️ Remover Aluno")
                rem = st.selectbox("Escolha:", meus['Aluno'].tolist())
                if st.button("Remover"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == rem].iloc[0]['_id'])
                    st.rerun()

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Agenda")
        evs = base.list_rows("Eventos")
        if evs: st.dataframe(pd.DataFrame(evs)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True)
