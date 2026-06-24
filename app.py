"""
Portal BMO - app.py
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import bcrypt

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "pages"))
sys.path.insert(0, str(current_dir / "utils"))

from seatable_conn import get_base
from helpers import hash_password, DEFAULT_PASS
from cache import (
    get_utilizadores_cached,
    get_musicos_cached,
    get_eventos_cached,
    get_presencas_cached,
    get_aulas_cached,
    get_faltas_ensaios_cached
)
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
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# ============================================
# CSS BASE
# ============================================
st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
section[data-testid="stSidebarNav"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
.stAppDeployButton { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stBottom"] { display: none !important; }
div.viewerBadge { display: none !important; }
.viewerBadgeContainer1QSob { display: none !important; }
.styles_viewerBadge1yB5 { display: none !important; }
[data-testid="collapsedControl"] { display: flex !important; }
.login-header { text-align: center; padding: 2rem 0; color: #ff6b35; }
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER: APLICAR TEMA VIA CSS
# ============================================
def aplicar_tema_css(dark):
    if dark:
        st.markdown("""
        <style>
        /* ===== DARK MODE ===== */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #121212 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #1f1f1f !important;
            color: #f5f5f5 !important;
        }
        .stMarkdown p, .stMarkdown span, .stMarkdown label, [data-testid="stText"], [data-testid="stMarkdownContainer"] p { color: #f5f5f5; }
        h1, h2, h3, h4 { color: #f5f5f5 !important; }

        /* Botões */
        .stButton > button {
            background-color: #2d2d2d !important;
            color: #f5f5f5 !important;
            border: 1px solid #555 !important;
        }
        .stButton > button:hover {
            background-color: #3d3d3d !important;
            border-color: #ff6b35 !important;
        }
        .stButton > button p { color: #f5f5f5 !important; }

        /* Inputs */
        .stTextInput div div input,
        .stTextArea div div textarea,
        .stSelectbox div div {
            background-color: #2a2a2a !important;
            color: #f5f5f5 !important;
            border-color: #444 !important;
        }

        /* Date input */
        .stDateInput input {
            color-scheme: dark;
            background-color: #2a2a2a !important;
            color: #f5f5f5 !important;
        }
        input[type="date"] { color-scheme: dark; }

        /* Dropdowns abertos */
        div[data-baseweb="popover"],
        div[data-baseweb="menu"] {
            background-color: #2a2a2a !important;
        }
        div[data-baseweb="menu"] li,
        div[data-baseweb="select"] [role="option"] {
            background-color: #2a2a2a !important;
            color: #f5f5f5 !important;
        }
        div[data-baseweb="menu"] li:hover {
            background-color: #3d3d3d !important;
        }

        /* Tags multiselect */
        div[data-baseweb="tag"] {
            background-color: #ff6b35 !important;
            color: #ffffff !important;
        }

        /* Expander e Forms */
        .stExpander {
            background-color: #1f1f1f !important;
            border-color: #444 !important;
        }
        [data-testid="stForm"] {
            background-color: #1f1f1f !important;
            border-color: #444 !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background-color: #1f1f1f !important; }
        .stTabs [data-baseweb="tab"] { color: #f5f5f5 !important; }
        .stTabs [aria-selected="true"] {
            color: #ff6b35 !important;
            border-bottom-color: #ff6b35 !important;
        }

        /* DataFrames */
        .stDataFrame { background-color: #1f1f1f !important; }

        /* Métricas */
        div[data-testid="metric-container"] {
            background-color: #1f1f1f;
            border-radius: 8px;
            padding: 10px;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        /* ===== LIGHT MODE ===== */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #ffffff !important;
        }
        [data-testid="stSidebar"] {
            background-color: #f0f2f6 !important;
            color: #000000 !important;
        }
        .stMarkdown p, .stMarkdown span, .stMarkdown label, [data-testid="stText"], [data-testid="stMarkdownContainer"] p { color: #000000; }
        h1, h2, h3, h4 { color: #000000 !important; }

        /* Botões */
        .stButton > button {
            background-color: #f0f2f6 !important;
            color: #000000 !important;
            border: 1px solid #cccccc !important;
        }
        .stButton > button:hover {
            background-color: #e0e2e6 !important;
            border-color: #ff6b35 !important;
        }
        .stButton > button p { color: #000000 !important; }

        /* Inputs */
        .stTextInput div div input,
        .stTextArea div div textarea,
        .stSelectbox div div {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-color: #cccccc !important;
        }

        /* Date input — fix fundo preto */
        .stDateInput input {
            color-scheme: light !important;
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        input[type="date"] { color-scheme: light !important; }

        /* Dropdowns abertos — fix fundo escuro */
        div[data-baseweb="popover"],
        div[data-baseweb="menu"] {
            background-color: #ffffff !important;
        }
        div[data-baseweb="menu"] li,
        div[data-baseweb="select"] [role="option"] {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        div[data-baseweb="menu"] li:hover {
            background-color: #f0f2f6 !important;
        }

        /* Tags multiselect */
        div[data-baseweb="tag"] {
            background-color: #ff6b35 !important;
            color: #ffffff !important;
        }

        /* Expander e Forms */
        .stExpander {
            background-color: #f0f2f6 !important;
            border-color: #cccccc !important;
        }
        [data-testid="stForm"] {
            background-color: #f0f2f6 !important;
            border-color: #cccccc !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background-color: #f0f2f6 !important; }
        .stTabs [data-baseweb="tab"] { color: #000000 !important; }
        .stTabs [aria-selected="true"] {
            color: #ff6b35 !important;
            border-bottom-color: #ff6b35 !important;
        }

        /* DataFrames */
        .stDataFrame { background-color: #ffffff !important; }

        /* Métricas */
        div[data-testid="metric-container"] {
            background-color: #f0f2f6;
            border-radius: 8px;
            padding: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

# ============================================
# HELPER: DETECTAR ERRO 429
# ============================================
def is_429(e):
    return '429' in str(e) or 'too many requests' in str(e).lower()

# ============================================
# INICIALIZAR SESSION STATE
# ============================================
if 'auth_status' not in st.session_state:
    st.session_state.update({
        'auth_status': False,
        'user_info': {},
        'must_change_pass': False,
        'dark_mode': True
    })

# ============================================
# CONECTAR À BASE DE DADOS
# ============================================
base = get_base()
if not base:
    st.error("❌ Erro ao conectar à base de dados. Verifique o token nas secrets.")
    st.stop()

# ============================================
# APLICAR TEMA
# ============================================
aplicar_tema_css(st.session_state.get('dark_mode', True))

# ============================================
# BOTÃO TEMA — TOPO DA PÁGINA
# ============================================
tema_atual = st.session_state.get('dark_mode', True)
label_btn_tema = "☀️ Modo Claro" if tema_atual else "🌙 Modo Escuro"
col_spacer, col_tema = st.columns([9, 1])
with col_tema:
    if st.button(label_btn_tema, key="btn_tema_topo"):
        novo_dark = not tema_atual
        st.session_state['dark_mode'] = novo_dark
        if st.session_state.get('auth_status'):
            try:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {
                    "Tema": 'dark' if novo_dark else 'light'
                })
                get_utilizadores_cached.clear()
            except Exception:
                pass
        st.rerun()

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.title("🎵 BMO Portal")
    st.divider()
    if st.session_state.get('auth_status'):
        user = st.session_state['user_info']
        st.write(f"👤 **{user['display_name']}**")
        st.caption(f"_{user['role']}_")
        st.divider()
        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()
    st.divider()
    with st.expander("ℹ️ Sobre"):
        st.write("""
        **Banda Municipal de Oeiras**

        Portal de gestão para músicos,
        professores, maestros e direção.

        Versão: 2.0
        """)

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
        new_pass     = st.text_input("🔑 Nova Password", type="password", help="Mínimo 4 caracteres")
        confirm_pass = st.text_input("🔑 Confirmar Password", type="password")
        if st.form_submit_button("💾 Guardar Nova Password", use_container_width=True):
            if len(new_pass) < 4:
                st.error("❌ A password deve ter pelo menos 4 caracteres")
            elif new_pass != confirm_pass:
                st.error("❌ As passwords não coincidem")
            elif new_pass in (DEFAULT_PASS, "1234"):
                st.error("❌ Não pode usar a password padrão '1234'")
            else:
                try:
                    nova_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    base.update_row("Utilizadores", user['row_id'], {"Password": nova_hash})
                    get_utilizadores_cached.clear()
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
    st.markdown("<h1 class='login-header'>🎵 Banda Municipal de Oeiras</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Entrar no Portal")
            u_in = st.text_input("👤 Utilizador", placeholder="Introduza o seu username").strip().lower()
            p_in = st.text_input("🔒 Password", type="password", placeholder="Introduza a sua password").strip()
            if st.form_submit_button("🚀 Entrar", use_container_width=True):
                if not u_in or not p_in:
                    st.error("Preencha todos os campos")
                else:
                    try:
                        users_list = get_utilizadores_cached()
                        df_users = pd.DataFrame(users_list) if users_list else pd.DataFrame()
                        if df_users.empty:
                            st.error("Erro ao carregar utilizadores da base de dados")
                        else:
                            match = df_users[df_users['Username'].str.lower() == u_in]
                            if match.empty:
                                st.error("Utilizador não encontrado")
                            else:
                                row = match.iloc[0]
                                stored_pass      = str(row.get('Password', ''))
                                password_correta = False
                                precisa_trocar   = False
                                if stored_pass == '1234':
                                    if p_in == '1234':
                                        password_correta = True
                                        precisa_trocar   = True
                                elif stored_pass.startswith('$2b'):
                                    try:
                                        if bcrypt.checkpw(p_in.encode('utf-8'), stored_pass.encode('utf-8')):
                                            password_correta = True
                                    except Exception:
                                        password_correta = False
                                else:
                                    password_correta = p_in == stored_pass

                                if password_correta:
                                    tema_guardado = str(row.get('Tema', 'dark')).strip().lower()
                                    if tema_guardado not in ('dark', 'light'):
                                        tema_guardado = 'dark'
                                    st.session_state.update({
                                        'auth_status':      True,
                                        'must_change_pass': precisa_trocar,
                                        'dark_mode':        tema_guardado == 'dark',
                                        'user_info': {
                                            'username':     u_in,
                                            'display_name': row.get('Nome', u_in),
                                            'role':         row.get('Funcao', 'Musico'),
                                            'row_id':       row['_id']
                                        }
                                    })
                                    st.success(f"Bem-vindo(a), {row.get('Nome', u_in)}!")
                                    st.rerun()
                                else:
                                    st.error("Password incorreta")
                    except Exception as e:
                        if is_429(e):
                            st.warning("O servidor está temporariamente sobrecarregado (demasiados pedidos).")
                            st.info("Por favor aguarde 1 a 2 minutos e tente novamente. Se o problema persistir, contacte o administrador.")
                        else:
                            st.error(f"Erro ao fazer login: {str(e)}")
                            st.info("Verifique se a tabela 'Utilizadores' existe no SeaTable")
    st.stop()

# ============================================
# ROUTING POR ROLE
# ============================================
else:
    user = st.session_state['user_info']
    try:
        if user['role'] == 'Musico':
            musico.render(base, user)
        elif user['role'] == 'Professor':
            professor.render(base, user)
        elif user['role'] == 'Maestro':
            maestro.render(base, user)
        elif user['role'] == 'Direcao':
            direcao.render(base, user)
        else:
            st.error(f"Role {user['role']} não reconhecido")
            st.info("Roles válidos: Musico, Professor, Maestro, Direcao")
            if st.button("Tentar novamente"):
                st.rerun()
    except Exception as e:
        if is_429(e):
            st.warning("O servidor está temporariamente sobrecarregado.")
            st.info("Aguarde 1 a 2 minutos e clique em Recarregar.")
        else:
            st.error(f"Erro ao carregar a página: {str(e)}")
            st.exception(e)
        if st.button("Recarregar"):
            st.rerun()

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:gray;font-size:0.8rem'>© 2026 Banda Municipal de Oeiras</p>",
    unsafe_allow_html=True
)
