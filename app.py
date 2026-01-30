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
            base = Base(API_TOKEN, SERVER_URL); base.auth()
            return base
        except: time.sleep(1)
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def remover_acentos(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().replace(" ", "_")

def gerar_username(nome_completo):
    partes = str(nome_completo).strip().split()
    u = f"{partes[0]}_{partes[-1]}" if len(partes) >= 2 else partes[0]
    return remover_acentos(u)

def formatar_data_pt(data_str):
    """Converte YYYY-MM-DD para DD/MM/YYYY com segurança"""
    try:
        if not data_str or str(data_str) == 'None': return "---"
        return pd.to_datetime(data_str).strftime('%d/%m/%Y')
    except: return str(data_str)

def sincronizar_e_limpar(base):
    try:
        rows_u = base.list_rows("Utilizadores")
        df_m = pd.DataFrame(base.list_rows("Musicos"))
        
        # Remove users com acentos/cedilhas
        for r in rows_u:
            u_orig = r.get('Username', '')
            if u_orig != remover_acentos(u_orig):
                base.delete_row("Utilizadores", r['_id'])
        
        df_u_atual = pd.DataFrame(base.list_rows("Utilizadores"))
        existentes = df_u_atual['Username'].tolist() if not df_u_atual.empty else []
        
        for _, m in df_m.iterrows():
            novo_u = gerar_username(m['Nome'])
            if novo_u not in existentes:
                base.append_row("Utilizadores", {
                    "Username": novo_u, "Password": DEFAULT_PASS,
                    "Funcao": "Musico", "Nome": m['Nome']
                })
    except: pass

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- LOGIN ---
if base and not st.session_state['auth_status']:
    sincronizar_e_limpar(base)
    st.header("🎵 Portal da Banda")
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            match = df_u[df_u['Username'] == u_in]
            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                if p_in == DEFAULT_PASS and stored_p == DEFAULT_PASS:
                    st.session_state.update({'auth_status': True, 'must_change_pass': True, 'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                elif hash_password(p_in) == stored_p:
                    st.session_state.update({'auth_status': True, 'must_change_pass': False, 'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    
    # MUDANÇA DE PASSWORD OBRIGATÓRIA
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Altere a sua password para o primeiro acesso.")
        with st.form("change"):
            n1 = st.text_input("Nova Password", type="password")
            n2 = st.text_input("Confirmar", type="password")
            if st.form_submit_button("Atualizar"):
                if n1 == n2 and len(n1) >= 4:
                    base.update_row("Utilizadores", user['row_id'], {"Password": hash_password(n1)})
                    st.session_state['must_change_pass'] = False
                    st.success("Sucesso! Faça login com a nova password.")
                    time.sleep(2); st.session_state.clear(); st.rerun()
                else: st.error("Erro: Passwords diferentes ou muito curtas.")
        st.stop()

    st.sidebar.button("Sair", on_click=lambda: st.session_state.clear())

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        st.title("🎺 Área do Músico")
        t1, t2 = st.tabs(["📅 Agenda", "👤 Os Meus Dados"])
        
        with t1:
            evs = base.list_rows("Eventos")
            if evs:
                df_evs = pd.DataFrame(evs)
                # Formatar data na tabela de eventos
                df_evs['Data'] = df_evs['Data'].apply(formatar_data_pt)
                st.dataframe(df_evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        
        with t2:
            musicos = base.list_rows("Musicos")
            m_row = next((r for r in musicos if r.get('Nome') == user['display_name']), None)
            
            if m_row:
                st.subheader("Ficha de Dados Pessoais")
                with st.form("perfil"):
                    tel_limpo = str(m_row.get('Telefone', '')).split('.')[0]
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=tel_limpo)
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                    with col2:
                        st.write(f"**Nascimento:** {formatar_data_pt(m_row.get('Data de Nascimento'))}")
                        st.write(f"**Ingresso na Banda:** {formatar_data_pt(m_row.get('Data Ingresso Banda'))}")
                    
                    n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    st.text_area("Observações (Apenas Direção)", value=str(m_row.get('Obs', '')), disabled=True)
                    
                    if st.form_submit_button("Gravar Alterações"):
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone": n_tel, "Email": n_mail, "Morada": n_morada
                        })
                        st.success("Os seus dados foram atualizados no sistema!")
                        time.sleep(1); st.rerun()
            else: st.error("Ficha não encontrada na tabela Músicos.")

    # --- PERFIL DIREÇÃO / PROFESSOR ---
    elif user['role'] in ["Direcao", "Professor"]:
        st.title(f"🛡️ Painel {user['role']}")
        # Lógica de gestão de eventos e alunos...
