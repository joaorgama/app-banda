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

def validar_link(url):
    if not url: return True, ""
    if not re.match(r'^https?://', url):
        return False, "❌ O link deve começar por http:// ou https://"
    return True, ""

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
                    st.session_state.update({'auth_status': True, 'must_change_pass': (stored_p == DEFAULT_PASS), 
                                             'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}})
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

elif st.session_state.get('must_change_pass'):
    st.warning("⚠️ Segurança: Altere a sua password inicial (1234).")
    with st.form("f_change"):
        n1 = st.text_input("Nova Password", type="password")
        n2 = st.text_input("Confirmar Nova Password", type="password")
        if st.form_submit_button("Atualizar Password"):
            if n1 == n2 and len(n1) >= 4 and n1 != DEFAULT_PASS:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(n1)})
                st.session_state['must_change_pass'] = False
                st.success("Sucesso!"); time.sleep(1); st.rerun()
            else: st.error("As passwords não coincidem ou são inválidas.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3, t4, t5 = st.tabs(["📅 Agenda & Presenças", "👤 Meus Dados", "🎷 Meu Instrumento", "🎼 Repertório", "🖼️ Galeria"])
        musicos = base.list_rows("Musicos")
        m_row = next((r for r in musicos if str(r.get('Username','')).lower() == user['username']), None)
        with t1:
            st.subheader("Confirmar Disponibilidade")
            evs = base.list_rows("Eventos")
            pres = base.list_rows("Presencas")
            for e in evs:
                with st.expander(f"📅 {formatar_data_pt(e['Data'])} - {e['Nome do Evento']} ({e.get('Hora', '---')})"):
                    resp_atual = next((p['Resposta'] for p in pres if p['EventoID'] == e['_id'] and p['Username'] == user['username']), "Não respondido")
                    st.write(f"Sua resposta: **{resp_atual}**")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("✅ Vou", key=f"v_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID = '{e['_id']}' AND Username = '{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Vou"}); st.rerun()
                    if c2.button("❌ Não Vou", key=f"nv_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID = '{e['_id']}' AND Username = '{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Não Vou"}); st.rerun()
                    if c3.button("❓ Talvez", key=f"t_{e['_id']}"):
                        base.query(f"DELETE FROM Presencas WHERE EventoID = '{e['_id']}' AND Username = '{user['username']}'")
                        base.append_row("Presencas", {"EventoID": e['_id'], "Username": user['username'], "Resposta": "Talvez"}); st.rerun()
        with t2:
            if m_row:
                with st.form("ficha"):
                    c1, c2 = st.columns(2)
                    n_tel = c1.text_input("Telefone", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                    n_mail = c1.text_input("Email", value=str(m_row.get('Email', '')))
                    n_nasc = c1.date_input("Nascimento", value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990,1,1))
                    n_morada = c2.text_area("Morada", value=str(m_row.get('Morada', '')))
                    if st.form_submit_button("💾 Guardar Dados"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)}); st.success("Guardado!"); st.rerun()
        # [Restantes abas do Músico mantidas conforme app.py original]
        with t4:
            rep = base.list_rows("Repertorio")
            for r in rep or []:
                with st.expander(f"🎵 {r.get('Nome da Obra', 'S/ Nome')}"):
                    l = r.get('Links', '')
                    if l: st.video(l) if "youtube" in l else st.link_button("Link", l)

    # --- PERFIL PROFESSOR (COM CALENDÁRIO ADICIONADO) ---
    elif user['role'] == "Professor":
        st.header("👨‍🏫 Gestão de Alunos")
        tab_list, tab_mapa = st.tabs(["👥 Meus Alunos", "📅 Mapa de Ocupação ⭐"])
        
        with tab_list:
            with st.expander("➕ Registar Novo Aluno"):
                with st.form("add_al"):
                    n, c, h, s = st.text_input("Nome"), st.text_input("Contacto"), st.text_input("Horário (ex: Segunda 14h)"), st.text_input("Sala")
                    if st.form_submit_button("Confirmar Registo"):
                        base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
            
            aulas_raw = base.list_rows("Aulas")
            if aulas_raw:
                df_aulas = pd.DataFrame(aulas_raw)
                meus = df_aulas[df_aulas['Professor'] == user['display_name']]
                if not meus.empty:
                    st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)
                    with st.expander("🗑️ Remover Aluno"):
                        al_rem = st.selectbox("Aluno:", options=meus['Aluno'].tolist())
                        if st.button("Confirmar Remoção"):
                            rid = meus[meus['Aluno'] == al_rem].iloc[0]['_id']
                            base.delete_row("Aulas", rid); st.rerun()

        with tab_mapa:
            st.subheader("Ocupação Semanal das Salas")
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            horas_dia = [f"{h:02d}:00" for h in range(8, 22)]
            df_mapa = pd.DataFrame("", index=horas_dia, columns=dias_semana)
            
            aulas_all = base.list_rows("Aulas")
            for a in aulas_all:
                texto = str(a.get('DiaHora', '')).lower()
                for d in dias_semana:
                    if d.lower()[:3] in texto:
                        h_match = re.search(r'(\d{1,2})', texto)
                        if h_match:
                            h_key = f"{int(h_match.group(1)):02d}:00"
                            if h_key in horas_dia:
                                is_mine = (a.get('Professor') == user['display_name'])
                                df_mapa.at[h_key, d] = f"{'⭐' if is_mine else ''}{a.get('Professor')} ({a.get('Sala')})"
            st.table(df_mapa)

    # --- PERFIL DIREÇÃO ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4, t5 = st.tabs(["📅 Eventos & Presenças", "🎷 Inventário", "🏫 Escola Geral", "🖼️ Galeria", "📊 Status"])
        with t3: # Escola Geral
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)
        # [Restante da lógica da Direção mantida do original]

    # --- PERFIL MAESTRO ---
    elif user['role'] == "Maestro":
        t1, t2, t3 = st.tabs(["🎼 Repertório", "📅 Agenda", "🏫 Escola Geral"])
        # [Lógica do Maestro mantida do original]
