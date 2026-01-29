import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

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

if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'must_change_pass' not in st.session_state: st.session_state['must_change_pass'] = False

# --- LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    with st.form("login_form"):
        u = st.text_input("Utilizador").strip().lower()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            base = get_base()
            if base:
                df_users = pd.DataFrame(base.list_rows("Utilizadores"))
                user_row = df_users[df_users['Username'].str.lower() == u]
                if not user_row.empty:
                    stored_p = str(user_row.iloc[0]['Password'])
                    if (p == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p) == stored_p:
                        st.session_state['must_change_pass'] = (stored_p == DEFAULT_PASS)
                        st.session_state['auth_status'] = True
                        st.session_state['user_info'] = {'username': user_row.iloc[0]['Username'], 'role': user_row.iloc[0]['Funcao'], 'row_id': user_row.iloc[0]['_id']}
                        st.rerun()
                    else: st.error("Password incorreta.")
                else: st.error("Utilizador não encontrado.")
            else: st.error("Erro de ligação.")

else:
    base = get_base()
    user_data = st.session_state['user_info']
    
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Altere a sua password.")
        with st.form("new_p"):
            np = st.text_input("Nova Password", type="password")
            if st.form_submit_button("Guardar"):
                base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(np)})
                st.session_state['must_change_pass'] = False
                st.rerun()
        st.stop()

    # MENU LATERAL
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    role = user_data['role']
    username_clean = user_data['username'].lower().strip()

    # --- PERFIL: PROFESSOR (Com Botão de Excluir Recuperado) ---
    if role == "Professor":
        st.title("🏫 Área do Professor")
        
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add_aluno"):
                n = st.text_input("Nome"); c = st.text_input("Contacto"); h = st.text_input("Horário"); s = st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s})
                    st.rerun()

        st.subheader("Os Meus Alunos")
        rows = base.list_rows("Aulas")
        if rows:
            df = pd.DataFrame(rows)
            # Filtro inteligente para garantir que vê os alunos (Marco, Nelson, etc)
            meus = df[df['Professor'].str.lower().str.strip() == username_clean].copy()
            
            if not meus.empty:
                # Tabela limpa (sem índice 0, 1...) e com a coluna Sala
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
                
                st.divider()
                st.subheader("🗑️ Gestão de Saídas")
                # Botão de excluir com seleção simples
                aluno_selecionado = st.selectbox("Selecione o aluno que deseja remover:", meus['Aluno'].tolist())
                if st.button("Remover Aluno Permanentemente", type="primary"):
                    row_id = meus[meus['Aluno'] == aluno_selecionado].iloc[0]['_id']
                    base.delete_row("Aulas", row_id)
                    st.success(f"O aluno {aluno_selecionado} foi removido com sucesso.")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("Ainda não tem alunos registados na sua lista.")

    # --- OUTROS PERFIS (Direção / Músico) ---
    elif role == "Direcao":
        st.title("🛡️ Gestão Direção")
        t1, t2 = st.tabs(["📅 Eventos", "🏫 Escola Geral"])
        with t2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty:
                st.dataframe(aulas[['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
    
    elif role == "Musico":
        st.title("🎺 Área Músico")
        evs = pd.DataFrame(base.list_rows("Eventos"))
        if not evs.empty:
            st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
