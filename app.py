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

st.set_page_config(page_title="Banda Municipal de Oeiras", page_icon="🎵", layout="wide")

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
                df_users = pd.DataFrame(base.list_rows("Utilizadores"))
                user_row = df_users[df_users['Username'].str.lower().str.strip() == u]
                if not user_row.empty:
                    stored_p = str(user_row.iloc[0]['Password'])
                    if (p == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p) == stored_p:
                        st.session_state['must_change_pass'] = (stored_p == DEFAULT_PASS)
                        st.session_state['auth_status'] = True
                        st.session_state['user_info'] = {'username': user_row.iloc[0]['Username'], 'role': user_row.iloc[0]['Funcao'], 'row_id': user_row.iloc[0]['_id']}
                        st.rerun()
                    else: st.error("Password incorreta.")
                else: st.error("Utilizador não encontrado.")
            else: st.error("Erro de ligação.")

else:
    base = get_base()
    user_data = st.session_state['user_info']
    
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Segurança: Altere a sua password.")
        with st.form("new_p"):
            np = st.text_input("Nova Password", type="password")
            if st.form_submit_button("Guardar"):
                base.update_row("Utilizadores", user_data['row_id'], {"Password": hash_password(np)})
                st.session_state['must_change_pass'] = False
                st.rerun()
        st.stop()

    st.sidebar.title("Menu")
    st.sidebar.write(f"Olá, **{user_data['username']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

    role = user_data['role']
    username_clean = user_data['username'].lower().strip()

    # --- FUNÇÃO PARA RENDERIZAR GALERIA ---
    def mostrar_galeria(lista_eventos):
        st.subheader("🖼️ Galeria de Cartazes")
        cartazes = [ev for ev in lista_eventos if ev.get('Cartaz') and str(ev['Cartaz']).startswith('http')]
        
        if cartazes:
            cols = st.columns(2)  # Cria 2 colunas para telemóvel
            for idx, ev in enumerate(cartazes):
                with cols[idx % 2]:
                    st.image(ev['Cartaz'], caption=f"{ev.get('Nome do Evento')} ({ev.get('Data')})", use_container_width=True)
        else:
            st.info("Ainda não existem links de cartazes na tabela Eventos.")

    # --- 1. DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão Direção")
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria"])
        
        with t1:
            st.subheader("Gestão de Eventos")
            with st.expander("➕ Adicionar Novo Evento"):
                with st.form("add_event"):
                    nome_ev = st.text_input("Nome do Evento")
                    data_ev = st.date_input("Data")
                    tipo_ev = st.selectbox("Tipo", ["Concerto", "Ensaio", "Arruada", "Outro"])
                    link_cartaz = st.text_input("URL do Cartaz (Link da Imagem)")
                    if st.form_submit_button("Criar Evento"):
                        base.append_row("Eventos", {"Nome do Evento": nome_ev, "Data": str(data_ev), "Tipo": tipo_ev, "Cartaz": link_cartaz})
                        st.rerun()

            evs_data = base.list_rows("Eventos")
            if evs_data:
                df_evs = pd.DataFrame(evs_data)
                st.dataframe(df_evs[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)
                st.divider()
                ev_to_rem = st.selectbox("Selecione para apagar:", df_evs['Nome do Evento'].tolist())
                if st.button("Confirmar Eliminação", type="primary"):
                    ev_id = df_evs[df_evs['Nome do Evento'] == ev_to_rem].iloc[0]['_id']
                    base.delete_row("Eventos", ev_id)
                    st.rerun()

        with t2:
            st.subheader("Escola Geral")
            aulas_data = base.list_rows("Aulas")
            if aulas_data:
                df_aulas = pd.DataFrame(aulas_data)
                st.dataframe(df_aulas[['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)

        with t3:
            mostrar_galeria(base.list_rows("Eventos"))

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        with st.expander("➕ Adicionar Aluno"):
            with st.form("add_al"):
                n = st.text_input("Nome"); c = st.text_input("Contacto"); h = st.text_input("Horário"); s = st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s})
                    st.rerun()

        aulas_all = base.list_rows("Aulas")
        if aulas_all:
            df_p = pd.DataFrame(aulas_all)
            meus = df_p[df_p['Professor'].str.lower().str.strip() == username_clean].copy()
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index
