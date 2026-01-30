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
    partes = str(nome_completo).strip().split()
    if len(partes) >= 2:
        return f"{partes[0].lower()}_{partes[-1].lower()}"
    return partes[0].lower()

def sincronizar_utilizadores(base):
    """Cria utilizadores na tabela Utilizadores se existirem novos Músicos"""
    try:
        df_utilizadores = pd.DataFrame(base.list_rows("Utilizadores"))
        df_musicos = pd.DataFrame(base.list_rows("Musicos"))
        
        usernames_existentes = df_utilizadores['Username'].str.lower().tolist() if not df_utilizadores.empty else []
        
        for _, musico in df_musicos.iterrows():
            novo_user = gerar_username(musico['Nome'])
            if novo_user not in usernames_existentes:
                # Criar novo utilizador automaticamente
                base.append_row("Utilizadores", {
                    "Username": novo_user,
                    "Password": DEFAULT_PASS,
                    "Funcao": "Musico",
                    "Nome": musico['Nome'] # Guarda o nome real para referência
                })
        return True
    except Exception as e:
        st.error(f"Erro na sincronização: {e}")
        return False

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}

# --- PROCESSO DE LOGIN ---
base = get_base()

if base and not st.session_state['auth_status']:
    # Sincroniza sempre antes do login para garantir que novos músicos podem entrar
    sincronizar_utilizadores(base)
    
    st.header("🎵 Portal da Banda")
    with st.form("login_form"):
        u_input = st.text_input("Utilizador (ex: joao_gama)").strip().lower()
        p_input = st.text_input("Password", type="password").strip()
        
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            match = df_u[df_u['Username'].str.lower() == u_input]

            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                
                # Valida password (seja texto limpo '1234' ou hash)
                if (p_input == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p_input) == stored_p:
                    st.session_state['auth_status'] = True
                    st.session_state['user_info'] = {
                        'username': u_input,
                        'display_name': row.get('Nome', u_input),
                        'role': row['Funcao'],
                        'row_id': row['_id']
                    }
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado. Verifique se o nome está correto na tabela Musicos.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    # MÚSICO
    if user['role'] == "Musico":
        st.title("🎺 Área do Músico")
        t1, t2 = st.tabs(["📅 Agenda", "👤 Os Meus Dados"])
        
        with t1:
            evs = base.list_rows("Eventos")
            if evs: st.dataframe(pd.DataFrame(evs)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        
        with t2:
            # Para editar dados, precisamos de encontrar a linha dele na tabela Musicos
            df_m = pd.DataFrame(base.list_rows("Musicos"))
            df_m['gen_user'] = df_m['Nome'].apply(gerar_username)
            musico_match = df_m[df_m['gen_user'] == user['username']]
            
            if not musico_match.empty:
                m_row = musico_match.iloc[0]
                with st.form("edit_perfil"):
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=str(m_row.get('Telefone', '')))
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                    with col2:
                        st.info(f"Nascimento: {m_row.get('Data de Nascimento', '---')}")
                        st.info(f"Ingresso: {m_row.get('Data Ingresso Banda', '---')}")
                    
                    n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    
                    if st.form_submit_button("Guardar Alterações"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada})
                        st.success("Dados atualizados na ficha de músico!")
            else: st.warning("Não foi possível localizar a sua ficha na tabela Musicos para edição.")

    # DIREÇÃO / PROFESSOR
    elif user['role'] in ["Direcao", "Professor"]:
        st.title(f"🛡️ Painel {user['role']}")
        # ... resto do código de gestão ...
