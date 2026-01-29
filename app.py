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
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

# --- LOGIN (Sem formulário para evitar 2 cliques) ---
if st.session_state['user_role'] is None:
    st.header("🎵 Portal da Banda")
    u = st.text_input("Utilizador").strip().lower()
    p = st.text_input("Password", type="password").strip()
    
    if st.button("Entrar"):
        try:
            base = get_base()
            users = base.list_rows("Utilizadores")
            df_users = pd.DataFrame(users)
            user_found = df_users[(df_users['Username'].str.lower() == u) & (df_users['Password'].astype(str) == p)]
            if not user_found.empty:
                st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                st.session_state['username'] = user_found.iloc[0]['Username']
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        except:
            st.error("Erro de ligação. Verifique os segredos.")

# --- ÁREA LOGADA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username'].lower().strip()
    base = get_base()

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Painel de Gestão")
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola (Alunos/Prof)", "🖼️ Galeria"])
        
        with t1:
            evs = base.list_rows("Eventos")
            if evs: 
                st.dataframe(pd.DataFrame(evs)[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)

        with t2:
            st.subheader("Consulta Geral de Alunos e Contactos")
            aulas = base.list_rows("Aulas")
            if aulas:
                df_aulas = pd.DataFrame(aulas)
                # Selecionar e organizar colunas
                cols = [c for c in ['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in df_aulas.columns]
                df_final = df_aulas[cols].sort_values(by='Professor')
                st.dataframe(df_final, hide_index=True, use_container_width=True)
            else: st.info("Sem dados de aulas.")

        with t3:
            # Galeria de imagens
            eventos = base.list_rows("Eventos")
            valid_evs = [e for e in eventos if e.get('Cartaz')]
            if valid_evs:
                cols_img = st.columns(2)
                for i, ev in enumerate(valid_evs):
                    with cols_img[i % 2]:
                        st.image(ev['Cartaz'], caption=ev.get('Nome do Evento'), use_container_width=True)

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        
        with st.expander("➕ Registar Novo Aluno"):
            with st.form("novo_aluno"):
                nome_aluno = st.text_input("Nome do Aluno")
                tel_aluno = st.text_input("Contacto (Telemóvel)")
                horario = st.text_input("Dia/Hora")
                sala = st.text_input("Sala")
                if st.form_submit_button("Guardar"):
                    base.append_row("Aulas", {
                        "Professor": user, 
                        "Aluno": nome_aluno, 
                        "Contacto": tel_aluno,
                        "DiaHora": horario, 
                        "Sala": sala
                    })
                    st.success("Aluno adicionado!")
                    st.rerun()

        st.divider()
        
        rows = base.list_rows("Aulas")
        if rows:
            df = pd.DataFrame(rows)
            mask = df['Professor'].str.lower().str.strip() == user
            meus = df[mask]
            
            if not meus.empty:
                st.subheader("A Minha Lista de Alunos")
                # Mostrar tabela sem a coluna de índice
                cols_visiveis = [c for c in ['DiaHora', 'Aluno', 'Contacto', 'Sala'] if c in meus.columns]
                st.dataframe(meus[cols_visiveis], hide_index=True, use_container_width=True)
                
                st.subheader("🗑️ Remover Aluno")
                aluno_del = st.selectbox("Escolha o aluno que saiu:", meus['Aluno'].tolist())
                if st.button("Confirmar Remoção", type="primary"):
                    row_id = meus[meus['Aluno'] == aluno_del].iloc[0]['_id']
                    base.delete_row("Aulas", row_id)
                    st.rerun()
            else: st.info("Ainda não registou alunos.")

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Espaço do Músico")
        evs = base.list_rows("Eventos")
        if evs:
            st.dataframe(pd.DataFrame(evs)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
