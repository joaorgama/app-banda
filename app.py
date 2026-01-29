import streamlit as st
import pandas as pd
from seatable_api import Base

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]

def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

st.set_page_config(page_title="App Banda", page_icon="🎵", layout="wide")

# Inicialização de estados
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- SIDEBAR ---
if st.session_state['user_role'] is not None:
    st.sidebar.markdown(f"### Olá, **{st.session_state['username'].capitalize()}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

# --- LOGIN (Corrigido para 1 clique) ---
if st.session_state['user_role'] is None:
    st.header("🎵 Portal da Banda")
    u = st.text_input("Utilizador").strip().lower()
    p = st.text_input("Password", type="password").strip()
    
    if st.button("Entrar"):
        try:
            base = get_base()
            df_users = pd.DataFrame(base.list_rows("Utilizadores"))
            user_found = df_users[(df_users['Username'].str.lower() == u) & (df_users['Password'].astype(str) == p)]
            if not user_found.empty:
                st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                st.session_state['username'] = user_found.iloc[0]['Username']
                st.rerun()
            else:
                st.error("Utilizador ou Password incorretos.")
        except Exception as e:
            st.error(f"Erro de ligação: {e}")

# --- ÁREA LOGADA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username'].lower()
    base = get_base()

    def mostrar_galeria(eventos_list):
        st.subheader("🖼️ Galeria de Cartazes")
        valid_evs = [e for e in eventos_list if e.get('Cartaz')]
        if valid_evs:
            cols = st.columns(2)
            for i, ev in enumerate(valid_evs):
                with cols[i % 2]:
                    st.image(ev['Cartaz'], caption=ev.get('Nome do Evento'), use_container_width=True)
        else:
            st.info("Nenhuma imagem disponível.")

    # --- 1. DIREÇÃO (Com Adicionar e Apagar) ---
    if role == "Direcao":
        st.title("🛡️ Painel de Gestão")
        t1, t2, t3 = st.tabs(["📅 Gerir Eventos", "👥 Utilizadores", "🖼️ Galeria"])
        
        with t1:
            st.subheader("Adicionar Novo Evento")
            with st.expander("Clique para abrir formulário"):
                with st.form("novo_evento", clear_on_submit=True):
                    n = st.text_input("Nome do Evento")
                    d = st.date_input("Data")
                    t = st.selectbox("Tipo", ["Ensaio", "Concerto", "Outro"])
                    desc = st.text_area("Descrição")
                    img = st.text_input("Link do Cartaz (URL)")
                    if st.form_submit_button("Guardar no SeaTable"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Tipo": t, "Descricao": desc, "Cartaz": img})
                        st.success("Evento adicionado!")
                        st.rerun()

            st.divider()
            st.subheader("Eventos Atuais")
            ev_rows = base.list_rows("Eventos")
            if ev_rows:
                df_ev = pd.DataFrame(ev_rows)
                # Mostrar apenas colunas limpas
                cols_to_show = [c for c in ['Nome do Evento', 'Data', 'Tipo'] if c in df_ev.columns]
                st.table(df_ev[cols_to_show])
                
                # Seleção para apagar
                st.subheader("🗑️ Apagar Evento")
                evento_para_apagar = st.selectbox("Escolha o evento para remover:", df_ev['Nome do Evento'].tolist())
                if st.button("Confirmar Eliminação", type="primary"):
                    row_to_del = df_ev[df_ev['Nome do Evento'] == evento_para_apagar].iloc[0]
                    base.delete_row("Eventos", row_to_del['_id'])
                    st.warning(f"Evento '{evento_para_apagar}' apagado.")
                    st.rerun()

        with t2:
            st.table(pd.DataFrame(base.list_rows("Utilizadores"))[['Nome', 'Funcao', 'Username']])
        with t3:
            mostrar_galeria(base.list_rows("Eventos"))

    # --- 2. PROFESSOR ---
    elif role == "Professor":
        st.title("🏫 Área do Professor")
        df_aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not df_aulas.empty:
            mask = df_aulas['Professor'].str.lower().str.strip() == user
            minhas = df_aulas[mask]
            if not minhas.empty:
                cols = [c for c in ['DiaHora', 'Aluno', 'Sala'] if c in minhas.columns]
                st.table(minhas[cols])
            else: st.info("Sem aulas agendadas.")

    # --- 3. MÚSICO ---
    elif role == "Musico":
        st.title("🎺 Espaço do Músico")
        t_m1, t_m2 = st.tabs(["📅 Agenda", "🖼️ Galeria"])
        evs = base.list_rows("Eventos")
        with t_m1:
            if evs:
                df = pd.DataFrame(evs)
                st.table(df[['Data', 'Nome do Evento', 'Tipo']] if 'Data' in df.columns else df)
        with t_m2:
            mostrar_galeria(evs)
