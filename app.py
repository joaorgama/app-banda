import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
import unicodedata
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

def remover_acentos(texto):
    if not texto or pd.isna(texto): return ""
    return unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('utf-8').lower().strip().replace(" ", "_")

def gerar_username(nome_completo):
    partes = str(nome_completo).strip().split()
    u = f"{partes[0]}_{partes[-1]}" if len(partes) >= 2 else partes[0]
    return remover_acentos(u)

def formatar_data_pt(data_str):
    try:
        if not data_str or str(data_str) in ['None', 'nan', '']: return "---"
        return pd.to_datetime(data_str).strftime('%d/%m/%Y')
    except: return str(data_str)

def sincronizar_e_limpar(base):
    try:
        rows_u = base.list_rows("Utilizadores")
        df_m = pd.DataFrame(base.list_rows("Musicos"))
        for r in rows_u:
            u_orig = r.get('Username', '')
            if u_orig != remover_acentos(u_orig):
                base.delete_row("Utilizadores", r['_id'])
        df_u_atual = pd.DataFrame(base.list_rows("Utilizadores"))
        existentes = df_u_atual['Username'].tolist() if not df_u_atual.empty else []
        for _, m in df_m.iterrows():
            novo_u = gerar_username(m['Nome'])
            if novo_u not in existentes:
                base.append_row("Utilizadores", {"Username": novo_u, "Password": DEFAULT_PASS, "Funcao": "Musico", "Nome": m['Nome']})
    except: pass

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")
if 'auth_status' not in st.session_state: st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

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
                if (p_in == DEFAULT_PASS and stored_p == DEFAULT_PASS) or hash_password(p_in) == stored_p:
                    st.session_state.update({'auth_status': True, 'must_change_pass': (stored_p == DEFAULT_PASS), 'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    if st.session_state['must_change_pass']:
        st.warning("⚠️ Altere a sua password para o primeiro acesso.")
        with st.form("ch"):
            n1, n2 = st.text_input("Nova", type="password"), st.text_input("Confirmar", type="password")
            if st.form_submit_button("Gravar"):
                if n1 == n2 and len(n1) >= 4:
                    base.update_row("Utilizadores", user['row_id'], {"Password": hash_password(n1)})
                    st.session_state.clear(); st.success("OK! Reentre."); time.sleep(1); st.rerun()
        st.stop()

    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    # --- MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🖼️ Galeria"])
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        with t2:
            musicos = base.list_rows("Musicos")
            # Busca inteligente ignorando acentos para o user logado
            m_row = next((r for r in musicos if remover_acentos(r.get('Nome')) == user['username']), None)
            if m_row:
                with st.form("p"):
                    tel = str(m_row.get('Telefone', '')).split('.')[0]
                    col1, col2 = st.columns(2)
                    n_tel = col1.text_input("Telefone", value=tel)
                    n_mail = col1.text_input("Email", value=str(m_row.get('Email', '')))
                    d_nasc_str = m_row.get('Data de Nascimento')
                    try: d_nasc_val = datetime.strptime(d_nasc_str, '%Y-%m-%d') if d_nasc_str else datetime.now()
                    except: d_nasc_val = datetime.now()
                    n_nasc = col1.date_input("Data de Nascimento", value=d_nasc_val)
                    n_morada = col2.text_area("Morada", value=str(m_row.get('Morada', '')))
                    st.text_area("Observações", value=str(m_row.get('Obs', '')), disabled=True)
                    if st.form_submit_button("Gravar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)})
                        st.success("Dados atualizados!"); time.sleep(1); st.rerun()
        with t3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(2)
                for i, ev in enumerate(arts):
                    with cols[i%2]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- DIREÇÃO ---
    elif user['role'] == "Direcao":
        st.title("🛡️ Gestão Direção")
        tab1, tab2, tab3 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria"])
        with tab1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    n, d, t, c = st.text_input("Nome"), st.date_input("Data"), st.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada"]), st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Tipo": t, "Cartaz": c}); st.rerun()
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                for idx, row in evs.iterrows():
                    cols = st.columns([3, 2, 2, 1])
                    cols[0].write(row['Nome do Evento'])
                    cols[1].write(formatar_data_pt(row['Data']))
                    cols[2].write(row['Tipo'])
                    if cols[3].button("🗑️", key=f"del_ev_{idx}"):
                        base.delete_row("Eventos", row['_id']); st.rerun()
        with tab2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], hide_index=True)
        with tab3:
            evs = base.list_rows("Eventos")
            arts = [e for e in evs if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3)
                for i, ev in enumerate(arts):
                    with cols[i%3]: st.image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- PROFESSOR ---
    elif user['role'] == "Professor":
        st.title("👨‍🏫 Área Professor")
        with st.expander("➕ Adicionar Aluno"):
            with st.form("aa"):
                n, c, h, s = st.text_input("Nome"), st.text_input("Contacto"), st.text_input("Dia/Hora"), st.text_input("Sala")
                if st.form_submit_button("Registar"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'] == user['display_name']]
            st.subheader("Os meus Alunos")
            for idx, row in meus.iterrows():
                cols = st.columns([3, 2, 2, 2, 1])
                cols[0].write(row['Aluno'])
                cols[1].write(row['Contacto'])
                cols[2].write(row['DiaHora'])
                cols[3].write(row['Sala'])
                if cols[4].button("🗑️", key=f"del_al_{idx}"):
                    base.delete_row("Aulas", row['_id']); st.rerun()
