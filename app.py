import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
import unicodedata

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

def remover_acentos(texto):
    """Transforma 'joão' em 'joao' e remove espaços"""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().replace(" ", "_")

def gerar_username(nome_completo):
    partes = str(nome_completo).strip().split()
    if len(partes) >= 2:
        username = f"{partes[0]}_{partes[-1]}"
    else:
        username = partes[0]
    return remover_acentos(username)

def sincronizar_utilizadores(base):
    try:
        df_u = pd.DataFrame(base.list_rows("Utilizadores"))
        df_m = pd.DataFrame(base.list_rows("Musicos"))
        existentes = df_u['Username'].str.lower().tolist() if not df_u.empty else []
        
        for _, m in df_m.iterrows():
            novo_u = gerar_username(m['Nome'])
            if novo_u not in existentes:
                base.append_row("Utilizadores", {
                    "Username": novo_u,
                    "Password": DEFAULT_PASS,
                    "Funcao": "Musico",
                    "Nome": m['Nome']
                })
    except: pass

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False
if 'user_info' not in st.session_state: st.session_state['user_info'] = {}
if 'must_change_pass' not in st.session_state: st.session_state['must_change_pass'] = False

base = get_base()

# --- LOGIN ---
if base and not st.session_state['auth_status']:
    sincronizar_utilizadores(base)
    st.header("🎵 Portal da Banda")
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            match = df_u[df_u['Username'].str.lower() == u_in]
            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                # Verifica se é pass default ou se o hash coincide
                if (p_in == DEFAULT_PASS and stored_p == DEFAULT_PASS):
                    st.session_state['must_change_pass'] = True
                    valid = True
                elif hash_password(p_in) == stored_p:
                    st.session_state['must_change_pass'] = False
                    valid = True
                else:
                    st.error("Password incorreta."); valid = False
                
                if valid:
                    st.session_state['auth_status'] = True
                    st.session_state['user_info'] = {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}
                    st.rerun()
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    # BLOQUEIO PARA MUDANÇA DE PASSWORD
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Defina uma nova password (a atual é a padrão).")
        with st.form("force_change"):
            nova_p = st.text_input("Nova Password", type="password")
            conf_p = st.text_input("Confirmar Password", type="password")
            if st.form_submit_button("Guardar Password"):
                if len(nova_p) < 4: st.error("Mínimo 4 caracteres.")
                elif nova_p != conf_p: st.error("As passwords não coincidem.")
                else:
                    base.update_row("Utilizadores", user['row_id'], {"Password": hash_password(nova_p)})
                    st.session_state['must_change_pass'] = False
                    st.success("Password guardada com sucesso!")
                    time.sleep(1); st.rerun()
        st.stop()

    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear(); st.rerun()

    # MÚSICO
    if user['role'] == "Musico":
        st.title("🎺 Área do Músico")
        t1, t2 = st.tabs(["📅 Agenda", "👤 Meus Dados"])
        with t1:
            evs = base.list_rows("Eventos")
            if evs: st.dataframe(pd.DataFrame(evs)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        with t2:
            df_m = pd.DataFrame(base.list_rows("Musicos"))
            df_m['gen_user'] = df_m['Nome'].apply(gerar_username)
            m_match = df_m[df_m['gen_user'] == user['username']]
            if not m_match.empty:
                m_row = m_match.iloc[0]
                with st.form("edit"):
                    n_tel = st.text_input("Telefone", value=str(m_row.get('Telefone', '')))
                    n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                    n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    if st.form_submit_button("Atualizar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada})
                        st.success("Dados atualizados!")
            else: st.warning("Ficha de músico não encontrada.")

    # DIREÇÃO / PROFESSOR
    elif user['role'] in ["Direcao", "Professor"]:
        st.title(f"🛡️ Painel {user['role']}")
        # Aqui deve incluir o código anterior das tabelas de gestão (Eventos/Aulas)
