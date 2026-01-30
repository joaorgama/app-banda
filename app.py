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
            time.sleep(1)
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def gerar_username(nome_completo):
    """Gera username no formato primeiro_ultimo (ex: joao_gama)"""
    partes = str(nome_completo).strip().split()
    if len(partes) >= 2:
        return f"{partes[0].lower()}_{partes[-1].lower()}"
    return partes[0].lower()

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}

# --- LOGIN ---
if not st.session_state['auth_status']:
    st.header("🎵 Portal da Banda")
    with st.form("login_form"):
        u_input = st.text_input("Utilizador (ex: joao_gama)").strip().lower()
        p_input = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            base = get_base()
            if base:
                # Busca em Utilizadores (Direção/Professor)
                df_u = pd.DataFrame(base.list_rows("Utilizadores"))
                match_u = df_u[df_u['Username'].str.lower().str.strip() == u_input] if not df_u.empty else pd.DataFrame()
                
                # Busca em Musicos (Login Automático)
                df_m = pd.DataFrame(base.list_rows("Musicos"))
                if not df_m.empty:
                    df_m['gen_user'] = df_m['Nome'].apply(gerar_username)
                    match_m = df_m[df_m['gen_user'] == u_input]
                else: match_m = pd.DataFrame()

                if not match_u.empty:
                    row = match_u.iloc[0]
                    role = row['Funcao']
                    display_name = row['Username']
                    target_table = "Utilizadores"
                elif not match_m.empty:
                    row = match_m.iloc[0]
                    role = "Musico"
                    display_name = row['Nome']
                    target_table = "Musicos"
                else:
                    st.error("Utilizador não encontrado.")
                    st.stop()

                # Verificação de Password (Default: 1234)
                stored_p = str(row.get('Password', DEFAULT_PASS))
                if (p_input == DEFAULT_PASS and (stored_p == DEFAULT_PASS or stored_p == 'nan')) or hash_password(p_input) == stored_p:
                    st.session_state['auth_status'] = True
                    st.session_state['user_info'] = {
                        'username': u_input, 'display_name': display_name,
                        'role': role, 'row_id': row['_id'], 'table': target_table
                    }
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Erro de ligação ao SeaTable.")

else:
    base = get_base()
    user = st.session_state['user_info']
    
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # --- ÁREA MÚSICO ---
    if user['role'] == "Musico":
        st.title("🎺 Área do Músico")
        t1, t2 = st.tabs(["📅 Agenda", "👤 Os Meus Dados"])
        
        with t1:
            evs = base.list_rows("Eventos")
            if evs:
                st.dataframe(pd.DataFrame(evs)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        
        with t2:
            st.subheader("Consulta e Edição de Perfil")
            m_data = base.get_row("Musicos", user['row_id'])
            
            with st.form("edit_me"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_tel = st.text_input("Telefone", value=str(m_data.get('Telefone', '')))
                    novo_email = st.text_input("Email", value=str(m_data.get('Email', '')))
                with col2:
                    st.info(f"Nascimento: {m_data.get('Data de Nascimento', '')}")
                    st.info(f"Ingresso: {m_data.get('Data Ingresso Banda', '')}")
                
                nova_morada = st.text_area("Morada", value=str(m_data.get('Morada', '')))
                
                if st.form_submit_button("Guardar Alterações"):
                    base.update_row("Musicos", user['row_id'], {
                        "Telefone": novo_tel,
                        "Email": novo_email,
                        "Morada": nova_morada
                    })
                    st.success("Dados atualizados!")
                    time.sleep(1)
                    st.rerun()

    # --- ÁREA PROFESSOR / DIREÇÃO ---
    elif user['role'] in ["Professor", "Direcao"]:
        # (Aqui continua o código anterior de gestão de eventos e alunos)
        st.title(f"🛡️ Painel {user['role']}")
        st.write("Funcionalidades de gestão ativas.")
