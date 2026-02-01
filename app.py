import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Adicionar pastas ao path do Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "pages"))
sys.path.insert(0, str(current_dir / "utils"))

# Imports das utils
from seatable_conn import get_base
from helpers import hash_password, DEFAULT_PASS

# Imports das páginas
import musico
import professor
import maestro
import direcao

# ============================================
# CONFIGURAÇÃO DA APLICAÇÃO
# ============================================

st.set_page_config(
    page_title="BMO Portal",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# INICIALIZAR SESSION STATE
# ============================================

if 'auth_status' not in st.session_state:
    st.session_state.update({
        'auth_status': False,
        'user_info': {},
        'must_change_pass': False
    })

# ============================================
# CONECTAR À BASE DE DADOS
# ============================================

base = get_base()

if not base:
    st.error("❌ Erro ao conectar à base de dados. Verifique o token nas secrets.")
    st.stop()

# ============================================
# PÁGINA DE LOGIN
# ============================================

if not st.session_state['auth_status']:
    # CSS customizado para login
    st.markdown("""
        <style>
        .login-header {
            text-align: center;
            padding: 2rem 0;
            color: #ff6b35;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="login-header">🎵 Banda Municipal de Oeiras</h1>', unsafe_allow_html=True)
    
    # Centralizar form de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Entrar no Portal")
            
            u_in = st.text_input(
                "👤 Utilizador",
                placeholder="Digite o seu username"
            ).strip().lower()
            
            p_in = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Digite a sua password"
            ).strip()
            
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submit:
                if not u_in or not p_in:
                    st.error("⚠️ Preencha todos os campos")
                else:
                    # Buscar utilizadores
                    try:
                        users_list = base.list_rows("Utilizadores")
                        df_users = pd.DataFrame(users_list) if users_list else pd.DataFrame()
                        
                        if df_users.empty:
                            st.error("❌ Erro ao carregar utilizadores da base de dados")
                        else:
                            # Procurar utilizador
                            match = df_users[df_users['Username'].str.lower() == u_in]
                            
                            if match.empty:
                                st.error("❌ Utilizador não encontrado")
                            else:
                                row = match.iloc[0]
                                stored_pass = str(row.get('Password', DEFAULT_PASS))
                                
                                # Verificar password (aceita plain text ou hash)
                                if (p_in == stored_pass) or (hash_password(p_in) == stored_pass):
                                    # Login bem-sucedido
                                    st.session_state.update({
                                        'auth_status': True,
                                        'must_change_pass': (stored_pass == DEFAULT_PASS),
                                        'user_info': {
                                            'username': u_in,
                                            'display_name': row.get('Nome', u_in),
                                            'role': row.get('Funcao', 'Musico'),
                                            'row_id': row['_id']
                                        }
                                    })
                                    st.success(f"✅ Bem-vindo, {row.get('Nome', u_in)}!")
                                    st.rerun()
                                else:
                                    st.error("❌ Password incorreta")
                    
                    except Exception as e:
                        st.error(f"❌ Erro ao fazer login: {str(e)}")
                        st.info("💡 Verifique se a tabela 'Utilizadores' existe no SeaTable")

# ============================================
# ÁREA AUTENTICADA (APÓS LOGIN)
# ============================================

else:
    user = st.session_state['user_info']
    
    # ============================================
    # SIDEBAR COMUM
    # ============================================
    
    with st.sidebar:
        st.title("🎵 BMO Portal")
        st.divider()
        
        st.write(f"👤 **{user['display_name']}**")
        st.caption(f"_{user['role']}_")
        
        st.divider()
        
        # Botão de logout
        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
        
        st.divider()
        
        # Informações adicionais
        with st.expander("ℹ️ Sobre"):
            st.write("""
            **Banda Municipal de Oeiras**
            
            Portal de gestão para músicos, 
            professores, maestros e direção.
            
            Versão: 2.0
            """)
    
    # ============================================
    # ROUTER - REDIRECIONAR PARA PÁGINA CORRETA
    # ============================================
    
    try:
        if user['role'] == "Musico":
            musico.render(base, user)
        
        elif user['role'] == "Professor":
            professor.render(base, user)
        
        elif user['role'] == "Maestro":
            maestro.render(base, user)
        
        elif user['role'] == "Direcao":
            direcao.render(base, user)
        
        else:
            st.error(f"⚠️ Role '{user['role']}' não reconhecido")
            st.info("Roles válidos: Musico, Professor, Maestro, Direcao")
            
            if st.button("🔄 Tentar novamente"):
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar a página: {str(e)}")
        st.exception(e)
        
        if st.button("🔄 Recarregar"):
            st.rerun()

# ============================================
# FOOTER (OPCIONAL)
# ============================================

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "© 2026 Banda Municipal de Oeiras | Desenvolvido com ❤️ e Streamlit"
    "</p>",
    unsafe_allow_html=True
)
