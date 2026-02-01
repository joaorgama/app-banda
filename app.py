import streamlit as st
import pandas as pd
from utils.seatable_conn import get_base
from utils.helpers import hash_password, DEFAULT_PASS

# Importar páginas
from pages import musico, professor, maestro, direcao

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

# Inicializar session state
if 'auth_status' not in st.session_state:
    st.session_state.update({
        'auth_status': False,
        'user_info': {},
        'must_change_pass': False
    })

base = get_base()

# --- ÁREA DE LOGIN ---
if base and not st.session_state['auth_status']:
    st.header("🎵 Banda Municipal de Oeiras")
    
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        
        if st.form_submit_button("Entrar"):
            users_list = base.list_rows("Utilizadores")
            df_u = pd.DataFrame(users_list) if users_list else pd.DataFrame()
            
            if not df_u.empty:
                match = df_u[df_u['Username'].str.lower() == u_in]
                
                if not match.empty:
                    row = match.iloc[0]
                    stored_p = str(row.get('Password', DEFAULT_PASS))
                    
                    # Verificar password
                    if (p_in == stored_p) or (hash_password(p_in) == stored_p):
                        st.session_state.update({
                            'auth_status': True,
                            'must_change_pass': (stored_p == DEFAULT_PASS),
                            'user_info': {
                                'username': u_in,
                                'display_name': row.get('Nome', u_in),
                                'role': row['Funcao'],
                                'row_id': row['_id']
                            }
                        })
                        st.rerun()
                    else:
                        st.error("❌ Password incorreta.")
                else:
                    st.error("❌ Utilizador não encontrado.")
            else:
                st.error("❌ Erro ao carregar utilizadores.")

# --- ÁREA AUTENTICADA - ROUTER ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    # Sidebar comum
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    st.sidebar.write(f"*{user['role']}*")
    
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()
    
    # Router baseado no role
    if user['role'] == "Musico":
        musico.render(base, user)
    elif user['role'] == "Professor":
        professor.render(base, user)
    elif user['role'] == "Maestro":
        maestro.render(base, user)
    elif user['role'] == "Direcao":
        direcao.render(base, user)
    else:
        st.error("⚠️ Role não reconhecido")
