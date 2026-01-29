import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

# Função de ligação ultra-robusta
def get_base():
    for i in range(3):
        try:
            base = Base(API_TOKEN, SERVER_URL)
            base.auth()
            return base
        except:
            time.sleep(1) # Espera um pouco mais entre tentativas
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

# Inicialização de estados
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
                try:
                    df_users = pd.DataFrame(base.list_rows("Utilizadores"))
                    user_row = df_users[df_users['Username'].str.lower().str.strip() == u]
                    if not user_row.empty:
                        stored_p = str(user_row.iloc[0]['Password'])
                        if (p == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p) == stored_p:
                            st.session_state['must_change_pass'] = (stored_p == DEFAULT_PASS)
                            st.session_state['auth_status'] = True
                            st.session_state['user_info'] = {
                                'username': user_row.iloc[0]['Username'], 
                                'role': user_row.iloc[0]['Funcao'], 
                                'row_id': user_row.iloc[0]['_id']
                            }
                            st.rerun()
                        else: st.error("Password incorreta.")
                    else: st.error("Utilizador não encontrado.")
                except: st.error("Erro ao ler base de dados. Tente novamente.")
            else: st.error("Erro de ligação ao servidor.")

else:
    base = get_base()
    if not base:
        st.error("Erro de ligação. A recarregar...")
        st.rerun()
        
    user_data = st.session_state['user_info']
    
    # FORÇAR MUDANÇA DE PASS
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Altere a sua password de acesso.")
        with st.form("new_p"):
            np = st.text_input("Nova Password", type="password")
            if st.form_submit_button("Guardar"):
                if len(np) >= 4:
                    base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(np)})
                    st.session_state['must_change_pass'] = False
                    st.success("Sucesso! A entrar...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("A password deve ter pelo menos 4 caracteres.")
        st.stop()

    # MENU LATERAL
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    role = user_data['role']
    username_clean = user_data['username'].lower().strip()

    # --- 1. DIREÇÃO (CORRIGIDO) ---
    if role == "Direcao":
        st.title("🛡️ Gestão Direção")
        t1, t2 = st.tabs(["📅 Eventos", "🏫 Escola Geral"])
        
        with t1:
            evs_data = base.list_rows("Eventos")
            if evs_data:
                df_evs = pd.DataFrame(evs_data)
                cols_ev = [c for c in ['Nome do Evento', 'Data', 'Tipo'] if c in df_evs.columns]
                st.dataframe(df_evs[cols_ev], hide_index=True, use_container_width=True)
            else: st.info("Sem eventos registados.")

        with t2:
            aulas_data = base.list_rows("Aulas")
            if aulas_data:
                df_aulas = pd.DataFrame(aulas_data)
                cols_aula = [c for c in ['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala'] if c in df_aulas.columns]
                st.dataframe(df_aulas[cols_aula], hide_index=True, use_container_width=True)
            else: st.info("Sem dados de aulas na escola.")

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add"):
                n = st.text_input("Nome"); c = st.text_input("Contacto"); h = st.text_input("Horário"); s = st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s})
                    st.rerun()

        aulas_all = base.list_rows("Aulas")
        if aulas_all:
            df_p = pd.DataFrame(aulas_all)
            meus = df_p[df_p['Professor'].str.lower().str.strip() == username_clean].copy()
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
                st.divider()
                rem = st.selectbox("Remover aluno:", meus['Aluno'].tolist())
                if st.button("Eliminar Aluno", type="primary"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == rem].iloc[0]['_id'])
                    st.rerun()
            else: st.info("Ainda não tem alunos registados.")

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Área Músico")
        evs_m = base.list_rows("Eventos")
        if evs_m:
            df_m = pd.DataFrame(evs_m)
            st.dataframe(df_m[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
