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
                df_u = pd.DataFrame(base.list_rows("Utilizadores"))
                user_row = df_u[df_u['Username'].str.lower().str.strip() == u]
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
        st.warning("⚠️ Altere a sua password.")
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
    u_clean = user_data['username'].lower().strip()

    # Função Galeria
    def render_galeria(rows):
        st.subheader("🖼️ Galeria de Cartazes")
        imgs = [r for r in rows if r.get('Cartaz') and str(r['Cartaz']).startswith('http')]
        if imgs:
            c = st.columns(2)
            for idx, i in enumerate(imgs):
                with c[idx % 2]:
                    st.image(i['Cartaz'], caption=f"{i.get('Nome do Evento')}", use_container_width=True)
        else: st.info("Sem cartazes (links URL) disponíveis.")

    # --- DIREÇÃO ---
    if role == "Direcao":
        st.title("🛡️ Gestão Direção")
        t1, t2, t3 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("f_ev"):
                    n_ev = st.text_input("Nome"); d_ev = st.date_input("Data"); t_ev = st.selectbox("Tipo", ["Concerto", "Ensaio", "Outro"]); c_ev = st.text_input("Link URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n_ev, "Data": str(d_ev), "Tipo": t_ev, "Cartaz": c_ev})
                        st.rerun()
            evs = base.list_rows("Eventos")
            if evs:
                df_evs = pd.DataFrame(evs)
                st.dataframe(df_evs[['Nome do Evento', 'Data', 'Tipo']], hide_index=True, use_container_width=True)
                st.divider()
                rem_ev = st.selectbox("Remover:", df_evs['Nome do Evento'].tolist())
                if st.button("Apagar Evento", type="primary"):
                    base.delete_row("Eventos", df_evs[df_evs['Nome do Evento'] == rem_ev].iloc[0]['_id'])
                    st.rerun()
        with t2:
            aulas = base.list_rows("Aulas")
            if aulas: st.dataframe(pd.DataFrame(aulas)[['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
        with t3: render_galeria(base.list_rows("Eventos"))

    # --- PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área Professor")
        with st.expander("➕ Novo Aluno"):
            with st.form("f_al"):
                na = st.text_input("Nome"); ca = st.text_input("Contacto"); ha = st.text_input("Horário"); sa = st.text_input("Sala")
                if st.form_submit_button("Gravar"):
                    base.append_row("Aulas", {"Professor": user_data['username'], "Aluno": na, "Contacto": ca, "DiaHora": ha, "Sala": sa})
                    st.rerun()
        rows_a = base.list_rows("Aulas")
        if rows_a:
            df_a = pd.DataFrame(rows_a)
            meus = df_a[df_a['Professor'].str.lower().str.strip() == u_clean].copy()
            if not meus.empty:
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], hide_index=True, use_container_width=True)
                st.divider()
                al_rem = st.selectbox("Remover aluno:", meus['Aluno'].tolist())
                if st.button("Confirmar Remoção", type="primary"):
                    base.delete_row("Aulas", meus[meus['Aluno'] == al_rem].iloc[0]['_id'])
                    st.rerun()

    # --- MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Área Músico")
        m1, m2 = st.tabs(["📅 Agenda", "🖼️ Galeria"])
        with m1:
            evs_m = base.list_rows("Eventos")
            if evs_m: st.dataframe(pd.DataFrame(evs_m)[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        with m2: render_galeria(base.list_rows("Eventos"))
