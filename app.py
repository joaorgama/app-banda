import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
from datetime import datetime, timedelta
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

def converter_data_robusta(valor, dia_semana_texto=None):
    dt = None
    if valor and str(valor) not in ['None', 'nan', '', '0']:
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
            try: 
                dt = datetime.strptime(str(valor).split(' ')[0].split('T')[0], fmt).date()
                break
            except: continue
    if dt is None and dia_semana_texto:
        dias_map = {'seg': 0, 'ter': 1, 'qua': 2, 'qui': 3, 'sex': 4, 'sáb': 5, 'dom': 6}
        texto = str(dia_semana_texto).lower()
        for chave, idx in dias_map.items():
            if chave in texto:
                hoje = datetime.now().date()
                dt = hoje - timedelta(days=hoje.weekday()) + timedelta(days=idx)
                break
    return dt

def normalizar_hora(hora_str):
    if not hora_str: return None
    h = str(hora_str).replace('h', ':').strip()
    try:
        p = h.split(':')
        return f"{int(p[0]):02d}:00"
    except: return None

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- LOGIN E SEGURANÇA ---
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
    st.warning("⚠️ Segurança: Altere a sua password inicial.")
    with st.form("f_change"):
        n1, n2 = st.text_input("Nova Password", type="password"), st.text_input("Confirmar", type="password")
        if st.form_submit_button("Atualizar"):
            if n1 == n2 and len(n1) >= 4 and n1 != DEFAULT_PASS:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(n1)})
                st.session_state['must_change_pass'] = False
                st.success("Password atualizada!"); time.sleep(1); st.rerun()
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
                with st.expander(f"📅 {e.get('Data')} - {e.get('Nome do Evento')}"):
                    resp = next((p['Resposta'] for p in pres if p['EventoID'] == e['_id'] and p['Username'] == user['username']), "Pendente")
                    st.write(f"Estado: **{resp}**")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("✅ Vou", key=f"v_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Vou"}); st.rerun()
                    if c2.button("❌ Não Vou", key=f"nv_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Não Vou"}); st.rerun()
                    if c3.button("❓ Talvez", key=f"t_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID='{e['_id']}' AND Username='{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Talvez"}); st.rerun()
        
        with t2:
            if m_row:
                with st.form("ficha"):
                    c1, c2 = st.columns(2)
                    tel = c1.text_input("Telemóvel", value=str(m_row.get('Telefone','')))
                    ema = c1.text_input("Email", value=str(m_row.get('Email','')))
                    nasc = c2.date_input("Data Nascimento", value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(2000,1,1))
                    mor = c2.text_area("Morada", value=str(m_row.get('Morada','')))
                    if st.form_submit_button("💾 Atualizar Ficha"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": tel, "Email": ema, "Morada": mor, "Data de Nascimento": str(nasc)})
                        st.success("Dados Gravados!"); st.rerun()
        
        with t4:
            for r in base.list_rows("Repertorio"):
                with st.expander(f"🎼 {r.get('Nome da Obra')}"):
                    l = r.get('Links', '')
                    if "youtube" in l or "youtu.be" in l: st.video(l)
                    elif l: st.link_button("Ver Partitura", l)

    # --- PERFIL PROFESSOR ---
    elif user['role'] == "Professor":
        tab_cal, tab_meus = st.tabs(["📅 Mapa de Ocupação ⭐", "👤 Meus Alunos"])
        aulas_raw = base.list_rows("Aulas")
        df_aulas = pd.DataFrame(aulas_raw) if aulas_raw else pd.DataFrame()

        with tab_cal:
            loc = st.radio("Local:", ["Algés", "Oeiras"], horizontal=True)
            hoje = datetime.now().date()
            dias = [hoje - timedelta(days=hoje.weekday()) + timedelta(days=i) for i in range(14)]
            horas = [f"{h:02d}:00" for h in range(8, 22)]
            df_cal = pd.DataFrame("", index=horas, columns=[d.strftime("%a %d/%m") for d in dias])
            
            if not df_aulas.empty:
                for _, a in df_aulas[df_aulas['Local'] == loc].iterrows():
                    dt_b = converter_data_robusta(a.get('Data Aula'), a.get('Dia da Semana'))
                    hr = normalizar_hora(a.get('Hora'))
                    if dt_b and hr in horas:
                        is_mine = (str(a.get('Professor')) == user['display_name'])
                        txt = f"{'⭐ ' if is_mine else ''}{a.get('Professor')} ({a.get('Aluno')})"
                        for d_c in dias:
                            if (a.get('Recorrente') and dt_b.weekday() == d_c.weekday()) or (not a.get('Recorrente') and dt_b == d_c):
                                df_cal.at[hr, d_c.strftime("%a %d/%m")] = txt
            st.dataframe(df_cal, use_container_width=True, height=500)

    # --- PERFIL DIREÇÃO ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🎷 Inventário", "🏫 Escola Geral", "📊 Status"])
        with t1:
            evs = base.list_rows("Eventos")
            for e in evs:
                with st.expander(f"📝 {e.get('Data')} - {e.get('Nome do Evento')}"):
                    with st.form(f"f_{e['_id']}"):
                        n = st.text_input("Nome", value=e.get('Nome do Evento'))
                        d = st.text_input("Data", value=e.get('Data'))
                        if st.form_submit_button("💾 Gravar"):
                            base.update_row("Eventos", e['_id'], {"Nome do Evento": n, "Data": d}); st.rerun()
        with t3:
            a = base.list_rows("Aulas")
            if a: st.table(pd.DataFrame(a)[['Professor', 'Aluno', 'Local', 'Dia da Semana', 'Hora']])
        with t4:
            m = base.list_rows("Musicos")
            if m: st.table(pd.DataFrame(m)[['Nome', 'Instrumento', 'Telefone']])

    # --- PERFIL MAESTRO ---
    elif user['role'] == "Maestro":
        t1, t2 = st.tabs(["🎼 Repertório", "📅 Agenda"])
        with t1:
            st.subheader("Gestão de Obras")
            with st.form("new_r"):
                o, l = st.text_input("Obra"), st.text_input("Link")
                if st.form_submit_button("Adicionar"):
                    base.append_row("Repertorio", {"Nome da Obra": o, "Links": l}); st.rerun()
            for r in base.list_rows("Repertorio"):
                st.write(f"🎵 {r['Nome da Obra']}")
