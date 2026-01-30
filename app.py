import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
from datetime import datetime

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

def converter_data_para_python(data_seatable):
    """Converte a string do SeaTable (YYYY-MM-DD) para objeto datetime do Python"""
    if not data_seatable or str(data_seatable) in ['None', 'nan', '']:
        return None
    try:
        # Tenta converter o formato padrão do SeaTable
        return datetime.strptime(str(data_seatable).strip(), '%Y-%m-%d')
    except:
        try:
            # Tenta converter caso esteja em formato europeu na base
            return datetime.strptime(str(data_seatable).strip(), '%d/%m/%Y')
        except:
            return None

def formatar_data_pt(data_str):
    """Exibe no formato DD/MM/YYYY para o utilizador"""
    dt = converter_data_para_python(data_str)
    return dt.strftime('%d/%m/%Y') if dt else "---"

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- LOGIN ---
if base and not st.session_state['auth_status']:
    st.header("🎵 Portal da Banda Municipal de Oeiras")
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            if not df_u.empty:
                match = df_u[df_u['Username'].str.lower() == u_in]
                if not match.empty:
                    row = match.iloc[0]
                    stored_p = str(row.get('Password', DEFAULT_PASS))
                    if (p_in == stored_p) or (hash_password(p_in) == stored_p):
                        st.session_state.update({
                            'auth_status': True, 
                            'must_change_pass': (stored_p == DEFAULT_PASS), 
                            'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}
                        })
                        st.rerun()
                    else: st.error("Password incorreta.")
                else: st.error("Utilizador não encontrado.")

# --- MUDANÇA DE PASSWORD OBRIGATÓRIA ---
elif st.session_state.get('must_change_pass'):
    st.warning("⚠️ Altere a sua password de primeiro acesso (1234).")
    with st.form("f_change"):
        n1 = st.text_input("Nova Password", type="password")
        n2 = st.text_input("Confirmar", type="password")
        if st.form_submit_button("Atualizar"):
            if n1 == n2 and len(n1) >= 4:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(n1)})
                st.session_state['must_change_pass'] = False
                st.success("Sucesso! A entrar..."); time.sleep(1); st.rerun()
            else: st.error("Erro nas passwords.")

# --- INTERFACE PRINCIPAL ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    if user['role'] == "Musico":
        t1, t2, t3 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🖼️ Galeria"])
        
        with t1:
            evs = base.list_rows("Eventos")
            if evs:
                df_evs = pd.DataFrame(evs)
                df_evs['Data Visual'] = df_evs['Data'].apply(formatar_data_pt)
                st.dataframe(df_evs[['Data Visual', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)

        with t2:
            musicos = base.list_rows("Musicos")
            # Busca prioritária por Username
            m_row = next((r for r in musicos if str(r.get('Username','')).lower() == user['username']), None)
            
            if m_row:
                with st.form("ficha"):
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                        
                        # TRATAMENTO DA DATA DE NASCIMENTO
                        dt_obj = converter_data_para_python(m_row.get('Data de Nascimento'))
                        # Se não existir data, sugere 1990 para não ser "hoje"
                        n_nasc = st.date_input("Data de Nascimento", value=dt_obj if dt_obj else datetime(1990, 1, 1), format="DD/MM/YYYY")
                    
                    with col2:
                        ingresso = formatar_data_pt(m_row.get('Data Ingresso Banda'))
                        st.info(f"📅 Ingresso na Banda: {ingresso}")
                        n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    
                    st.text_area("Observações (Apenas Leitura)", value=str(m_row.get('Obs', '')), disabled=True)
                    if st.form_submit_button("💾 Guardar Alterações"):
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone": n_tel, "Email": n_mail, "Morada": n_morada, 
                            "Data de Nascimento": n_nasc.strftime('%Y-%m-%d')
                        })
                        st.success("Dados atualizados!"); time.sleep(1); st.rerun()
            else:
                st.error("Ficha não encontrada. Verifique a coluna Username no SeaTable.")

        with t3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3)
                for i, ev in enumerate(arts):
                    with cols[i%3]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    elif user['role'] == "Direcao":
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola", "🖼️ Galeria"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    n, d, t, c = st.text_input("Nome"), st.date_input("Data"), st.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada"]), st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": d.strftime('%Y-%m-%d'), "Tipo": t, "Cartaz": c}); st.rerun()
            
            evs = base.list_rows("Eventos")
            if evs:
                df_d = pd.DataFrame(evs)
                df_d['Data Visual'] = df_d['Data'].apply(formatar_data_pt)
                st.dataframe(df_d[['Data Visual', 'Nome do Evento', 'Tipo']], use_container_width=True, hide_index=True)
                with st.expander("🗑️ Apagar Evento"):
                    for idx, r in df_d.iterrows():
                        c1, c2 = st.columns([5,1])
                        c1.write(f"{r['Nome do Evento']} ({r['Data Visual']})")
                        if c2.button("Apagar", key=f"dev_{idx}"):
                            base.delete_row("Eventos", r['_id']); st.rerun()

    elif user['role'] == "Professor":
        st.title("👨‍🏫 Área Professor")
        aulas = base.list_rows("Aulas")
        if aulas:
            df_a = pd.DataFrame(aulas)
            meus = df_a[df_a['Professor'] == user['display_name']]
            st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
