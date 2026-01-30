import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
from datetime import datetime
import re

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

def converter_data_robusta(valor):
    if not valor or str(valor) in ['None', 'nan', '']: return None
    if isinstance(valor, (datetime, pd.Timestamp)): return valor.date()
    str_data = str(valor).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
        try: return datetime.strptime(str_data.split(' ')[0].split('T')[0], fmt).date()
        except: continue
    return None

def formatar_data_pt(valor):
    dt = converter_data_robusta(valor)
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
            match = df_u[df_u['Username'].str.lower() == u_in] if not df_u.empty else pd.DataFrame()
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

elif st.session_state.get('must_change_pass'):
    st.warning("⚠️ Segurança: Altere a sua password inicial (1234).")
    with st.form("f_change"):
        n1, n2 = st.text_input("Nova Password", type="password"), st.text_input("Confirmar", type="password")
        if st.form_submit_button("Atualizar"):
            if n1 == n2 and len(n1) >= 4 and n1 != DEFAULT_PASS:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(n1)})
                st.session_state['must_change_pass'] = False
                st.success("Sucesso!"); time.sleep(1); st.rerun()
            else: st.error("Dados inválidos.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3, t4, t5 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🎷 Instrumento", "🎼 Repertório", "🖼️ Galeria"])
        musicos = base.list_rows("Musicos")
        m_row = next((r for r in musicos if str(r.get('Username','')).lower() == user['username']), None)
        
        with t1:
            evs = base.list_rows("Eventos")
            pres = base.list_rows("Presencas")
            for e in evs:
                with st.expander(f"📅 {formatar_data_pt(e['Data'])} - {e['Nome do Evento']}"):
                    resp = next((p['Resposta'] for p in pres if p['EventoID'] == e['_id'] and p['Username'] == user['username']), "Pendente")
                    st.write(f"Estado: **{resp}**")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("✅ Vou", key=f"v_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Vou"}); st.rerun()
                    if c2.button("❌ Não", key=f"n_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Não Vou"}); st.rerun()
                    if c3.button("❓ Talvez", key=f"t_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Talvez"}); st.rerun()

        with t2:
            if m_row:
                with st.form("ficha"):
                    tel = st.text_input("Telemóvel", value=str(m_row.get('Telefone','')).replace('.0',''))
                    mail = st.text_input("Email", value=str(m_row.get('Email','')))
                    nasc = st.date_input("Nascimento", value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990,1,1))
                    mor = st.text_area("Morada", value=str(m_row.get('Morada','')))
                    if st.form_submit_button("💾 Guardar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": tel, "Email": mail, "Morada": mor, "Data de Nascimento": str(nasc)}); st.rerun()

        with t3:
            if m_row:
                with st.form("inst"):
                    prop = st.checkbox("Instrumento Próprio", value=m_row.get('Instrumento Proprio', False))
                    inst = st.text_input("Instrumento", value=m_row.get('Instrumento', ''))
                    marc = st.text_input("Marca", value=m_row.get('Marca', ''), disabled=prop)
                    seri = st.text_input("Série", value=m_row.get('Num Serie', ''), disabled=prop)
                    if st.form_submit_button("💾 Atualizar"):
                        base.update_row("Musicos", m_row['_id'], {"Instrumento Proprio": prop, "Instrumento": inst, "Marca": marc if not prop else "", "Num Serie": seri if not prop else ""}); st.rerun()

        with t4:
            rep = base.list_rows("Repertorio")
            for r in rep or []:
                with st.expander(f"🎼 {r.get('Nome da Obra', 'S/ Nome')}"):
                    st.write(f"**Compositor:** {r.get('Compositor', '---')}")
                    l = r.get('Links', '')
                    if l: st.video(l) if "youtube" in l else st.link_button("Abrir Partitura", l)

        with t5:
            arts = [e for e in base.list_rows("Eventos") if e.get('Cartaz')]
            if arts:
                cols = st.columns(3)
                for i, ev in enumerate(arts): cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento'])

    # --- PERFIL PROFESSOR ---
    elif user['role'] == "Professor":
        st.header("👨‍🏫 Gestão de Alunos")
        with st.expander("➕ Novo Aluno"):
            with st.form("add_al"):
                n, c, h, s = st.text_input("Nome"), st.text_input("Contacto"), st.text_input("Horário"), st.text_input("Sala")
                if st.form_submit_button("Confirmar Registo"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
        
        aulas_raw = base.list_rows("Aulas")
        if aulas_raw:
            df_aulas = pd.DataFrame(aulas_raw)
            meus = df_aulas[df_aulas['Professor'] == user['display_name']]
            if not meus.empty:
                st.subheader("Meus Alunos")
                st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)
                with st.expander("🗑️ Remover Aluno"):
                    al_r = st.selectbox("Selecione:", options=meus['Aluno'].tolist())
                    if st.button("Confirmar Remoção"):
                        rid = meus[meus['Aluno'] == al_r].iloc[0]['_id']
                        base.delete_row("Aulas", rid); st.rerun()

    # --- PERFIL DIREÇÃO ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🎷 Inventário", "🏫 Escola Geral", "📊 Status"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    n, d, h, c = st.text_input("Nome"), st.date_input("Data"), st.text_input("Hora"), st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Hora": h, "Cartaz": c}); st.rerun()
            for e in base.list_rows("Eventos"):
                with st.expander(f"📝 {e.get('Nome do Evento')}"):
                    if st.button("Apagar", key=e['_id']): base.delete_row("Eventos", e['_id']); st.rerun()
        with t2:
            mus = base.list_rows("Musicos")
            if mus: st.dataframe(pd.DataFrame(mus)[['Nome', 'Instrumento', 'Marca', 'Num Serie']], use_container_width=True)
        with t3:
            aulas = base.list_rows("Aulas")
            if aulas: st.dataframe(pd.DataFrame(aulas)[['Professor', 'Aluno', 'DiaHora', 'Sala']], use_container_width=True)

    # --- PERFIL MAESTRO ---
    elif user['role'] == "Maestro":
        t1, t2 = st.tabs(["🎼 Repertório", "📅 Agenda"])
        with t1:
            with st.form("add_rep"):
                n, c, l = st.text_input("Obra"), st.text_input("Compositor"), st.text_input("Link")
                if st.form_submit_button("Publicar"):
                    base.append_row("Repertorio", {"Nome da Obra": n, "Compositor": c, "Links": l}); st.rerun()
            for r in base.list_rows("Repertorio") or []:
                st.write(f"🎵 {r.get('Nome da Obra')} - {r.get('Compositor')}")
