import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import bcrypt  # IMPORTANTE: adicionar este import

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
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# ============================================
# CSS CUSTOMIZADO (COM PROTEÇÃO TOTAL)
# ============================================
st.markdown("""
    <style>
        /* Esconder navegação de páginas do Streamlit */
        [data-testid="stSidebarNav"] {
            display: none;
        }
        
        section[data-testid="stSidebarNav"] {
            display: none !important;
        }
        
        /* Esconder menu principal, footer e botões indesejados */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {visibility: hidden;}
        
        /* Esconder botão Deploy e GitHub */
        .stDeployButton {display: none;}
        button[kind="header"] {display: none;}
        
        /* Esconder toolbar do GitHub */
        div[data-testid="stToolbar"] {display: none;}
        
        /* ESCONDER BOTÃO "MANAGE APP" NO CANTO INFERIOR DIREITO */
        .stAppDeployButton {display: none !important;}
        div[data-testid="stStatusWidget"] {display: none !important;}
        button[data-testid="baseButton-header"] {display: none !important;}
        section[data-testid="stSidebar"] button[kind="header"] {display: none !important;}
        div[data-testid="stDecoration"] {display: none !important;}
        
        /* Esconder status bar e elementos flutuantes */
        div[data-testid="stBottom"] {display: none !important;}
        .element-container:has(iframe[title="streamlit_app"]) {display: none !important;}
        
        /* Esconder ícone de status/conexão */
        div[class*="viewerBadge"] {display: none !important;}
        .viewerBadge_container__1QSob {display: none !important;}
        .styles_viewerBadge__1yB5_ {display: none !important;}
        
        /* CSS da página de login */
        .login-header {
            text-align: center;
            padding: 2rem 0;
            color: #ff6b35;
        }
    </style>
""", unsafe_allow_html=True)


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
# FORÇAR MUDANÇA DE PASSWORD
# ============================================

if st.session_state['auth_status'] and st.session_state['must_change_pass']:
    st.warning("⚠️ **ATENÇÃO:** Está a usar a password padrão. Por razões de segurança, deve alterá-la.")
    
    user = st.session_state['user_info']
    
    st.title("🔒 Alterar Password")
    st.write(f"Olá **{user['display_name']}**, bem-vindo(a) ao Portal BMO!")
    st.info("Por favor, defina uma nova password antes de continuar.")
    
    with st.form("change_password"):
        new_pass = st.text_input(
            "🔑 Nova Password",
            type="password",
            help="Mínimo 4 caracteres"
        )
        
        confirm_pass = st.text_input(
            "🔑 Confirmar Password",
            type="password"
        )
        
        if st.form_submit_button("💾 Guardar Nova Password", use_container_width=True):
            if len(new_pass) < 4:
                st.error("❌ A password deve ter pelo menos 4 caracteres")
            elif new_pass != confirm_pass:
                st.error("❌ As passwords não coincidem")
            elif new_pass == DEFAULT_PASS or new_pass == "1234":
                st.error("❌ Não pode usar a password padrão '1234'")
            else:
                try:
                    # Atualizar password na base de dados (ENCRIPTADA)
                    nova_password_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    base.update_row("Utilizadores", user['row_id'], {
                        "Password": nova_password_hash
                    })
                    
                    st.session_state['must_change_pass'] = False
                    st.success("✅ Password alterada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao alterar password: {e}")
    
    st.stop()

# ============================================
# PÁGINA DE LOGIN
# ============================================

if not st.session_state['auth_status']:
    st.markdown('<h1 class="login-header">🎵 Banda Municipal de Oeiras</h1>', unsafe_allow_html=True)
    
    # Centralizar form de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Entrar no Portal")
            
            u_in = st.text_input(
                "👤 Utilizador",
                placeholder="Introduza o seu username"
            ).strip().lower()
            
            p_in = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Introduza a sua password"
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
                                stored_pass = str(row.get('Password', ''))
                                
                                # Verificar se password é válida
                                password_correta = False
                                precisa_trocar = False
                                
                                # Caso 1: Password padrão "1234" (texto simples)
                                if stored_pass == "1234":
                                    if p_in == "1234":
                                        password_correta = True
                                        precisa_trocar = True
                                
                                # Caso 2: Password encriptada com bcrypt (começa com $2b$)
                                elif stored_pass.startswith('$2b$'):
                                    try:
                                        # USAR bcrypt.checkpw() para verificar
                                        if bcrypt.checkpw(p_in.encode('utf-8'), stored_pass.encode('utf-8')):
                                            password_correta = True
                                            precisa_trocar = False
                                    except Exception:
                                        password_correta = False
                                
                                # Caso 3: Password em texto simples (não recomendado)
                                else:
                                    if p_in == stored_pass:
                                        password_correta = True
                                        precisa_trocar = False
                                
                                if password_correta:
                                    # Login bem-sucedido
                                    st.session_state.update({
                                        'auth_status': True,
                                        'must_change_pass': precisa_trocar,
                                        'user_info': {
                                            'username': u_in,
                                            'display_name': row.get('Nome', u_in),
                                            'role': row.get('Funcao', 'Musico'),
                                            'row_id': row['_id']
                                        }
                                    })
                                    st.success(f"✅ Bem-vindo(a), {row.get('Nome', u_in)}!")
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
# FOOTER
# ============================================

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "© 2026 Banda Municipal de Oeiras | Desenvolvido com ❤️ e 🎵"
    "</p>",
    unsafe_allow_html=True
)
