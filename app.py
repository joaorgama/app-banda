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
    if not valor or str(valor) in ['None', 'nan', '', '0', 0]: return None
    if isinstance(valor, (datetime, pd.Timestamp)): return valor.date()
    if hasattr(valor, 'date'): return valor.date()
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
    st.warning("⚠️ Segurança: Altere a sua password (1234).")
    with st.form("f_change"):
        n1, n2 = st.text_input("Nova Password", type="password"), st.text_input("Confirmar", type="password")
        if st.form_submit_button("Atualizar"):
            if n1 == n2 and len(n1) >= 4:
                base.update_row("Utilizadores", st.session_state['user_info']['row_id'], {"Password": hash_password(n1)})
                st.session_state['must_change_pass'] = False
                st.success("Sucesso!"); time.sleep(1); st.rerun()
            else: st.error("Erro na validação.")

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
            evs = base.list_rows("Eventos")
            pres = base.list_rows("Presencas")
            for e in evs:
                with st.expander(f"📅 {formatar_data_pt(e['Data'])} - {e['Nome do Evento']}"):
                    resp_atual = next((p['Resposta'] for p in pres if p['EventoID'] == e['_id'] and p['Username'] == user['username']), "Não respondido")
                    st.write(f"Resposta: **{resp_atual}**")
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
                    if st.form_submit_button("💾 Guardar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)}); st.success("Ok!"); st.rerun()
        with t3:
            if m_row:
                with st.form("inst"):
                    pr = st.checkbox("Próprio", value=m_row.get('Instrumento Proprio', False))
                    inst = st.text_input("Instrumento", value=m_row.get('Instrumento', ''))
                    marca = st.text_input("Marca", value=m_row.get('Marca', ''), disabled=pr)
                    serie = st.text_input("Nº Série", value=m_row.get('Num Serie', ''), disabled=pr)
                    if st.form_submit_button("💾 Atualizar"):
                        base.update_row("Musicos", m_row['_id'], {"Instrumento Proprio": pr, "Instrumento": inst, "Marca": marca, "Num Serie": serie}); st.success("Atualizado!"); st.rerun()
        with t4:
            rep = base.list_rows("Repertorio")
            for r in rep or []:
                with st.expander(f"🎵 {r.get('Nome da Obra')}"):
                    l = r.get('Links', '')
                    if l: st.video(l) if "youtube" in l else st.link_button("Abrir", l)
        with t5:
            arts = [e for e in base.list_rows("Eventos") if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            cols = st.columns(3); [cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento']) for i, ev in enumerate(arts)]

    # --- PAINEL PROFESSOR (CORRIGIDO) ---
    elif user['role'] == "Professor":
        st.header("👨‍🏫 Portal do Professor")
        tab_cal, tab_meus = st.tabs(["📅 Mapa de Ocupação ⭐", "👤 Meus Alunos"])

        aulas_raw = base.list_rows("Aulas")
        df_aulas = pd.DataFrame(aulas_raw) if aulas_raw else pd.DataFrame()

        with tab_cal:
            local_sel = st.radio("Local:", ["Algés", "Oeiras"], horizontal=True)
            hoje = datetime.now().date()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            dias_calendario = [inicio_semana + timedelta(days=i) for i in range(14)]
            
            horas_dia = [f"{h:02d}:00" for h in range(8, 22)]
            col_names = [d.strftime("%a %d/%m") for d in dias_calendario]
            df_cal = pd.DataFrame("", index=horas_dia, columns=col_names)

            if not df_aulas.empty:
                filtro = df_aulas[df_aulas['Local'] == local_sel]
                for _, aula in filtro.iterrows():
                    # Correção: Converter data de forma segura
                    dt_obj = converter_data_robusta(aula.get('Data Aula'))
                    if dt_obj is None: continue # Ignora se a data for inválida
                    
                    h_aula = str(aula.get('Hora', ''))[:5]
                    if h_aula not in horas_dia: continue
                    
                    is_mine = (aula.get('Professor') == user['display_name'])
                    prefix = "⭐ " if is_mine else ""
                    content = f"{prefix}{aula.get('Professor', 'Prof')} ({aula.get('Sala', '?')})"

                    for d_cal in dias_calendario:
                        is_recorrente = bool(aula.get('Recorrente', False))
                        mesmo_dia = (dt_obj.weekday() == d_cal.weekday())
                        data_exata = (dt_obj == d_cal)

                        if (is_recorrente and mesmo_dia) or (not is_recorrente and data_exata):
                            col_idx = d_cal.strftime("%a %d/%m")
                            # Acumular se houver mais de uma aula na mesma hora
                            existente = df_cal.at[h_aula, col_idx]
                            df_cal.at[h_aula, col_idx] = f"{existente}\n{content}".strip() if existente else content

            st.dataframe(df_cal, use_container_width=True)

            with st.expander("➕ Nova Aula"):
                with st.form("f_aula"):
                    c1, c2 = st.columns(2)
                    al, dt_a = c1.text_input("Aluno"), c2.date_input("Data", min_value=hoje)
                    loc, hr = c1.selectbox("Local", ["Algés", "Oeiras"]), c2.selectbox("Hora", horas_dia)
                    sl, rec = c1.text_input("Sala"), c2.checkbox("Recorrente (Semanal)", value=True)
                    if st.form_submit_button("Gravar"):
                        base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": al, "Data Aula": str(dt_a), "Local": loc, "Hora": hr, "Sala": sl, "Recorrente": rec})
                        st.success("Registado!"); time.sleep(1); st.rerun()

        with tab_meus:
            if not df_aulas.empty:
                meus = df_aulas[df_aulas['Professor'] == user['display_name']]
                if not meus.empty:
                    st.dataframe(meus[['Aluno', 'Local', 'Hora', 'Recorrente']], use_container_width=True, hide_index=True)
                    al_rem = st.selectbox("Remover:", meus['Aluno'].tolist())
                    if st.button("Eliminar"):
                        base.delete_row("Aulas", meus[meus['Aluno'] == al_rem].iloc[0]['_id']); st.rerun()

    # --- PERFIL DIREÇÃO (Eventos, Inventário, Status) ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🎷 Inventário", "🏫 Escola", "📊 Status"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    n, d = st.text_input("Nome"), st.date_input("Data")
                    h, t = st.text_input("Hora"), st.selectbox("Tipo", ["Ensaio", "Concerto", "Outro"])
                    c = st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"): base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Hora": h, "Tipo": t, "Cartaz": c}); st.rerun()
            evs = base.list_rows("Eventos")
            for e in evs:
                with st.expander(f"📝 {formatar_data_pt(e['Data'])} - {e['Nome do Evento']}"):
                    if st.button("🗑️ Apagar", key=f"del_{e['_id']}"): base.delete_row("Eventos", e['_id']); st.rerun()
        with t2:
            mus = base.list_rows("Musicos")
            if mus: st.dataframe(pd.DataFrame(mus)[['Nome', 'Instrumento', 'Marca', 'Num Serie']], use_container_width=True, hide_index=True)
        with t3:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Local', 'Professor', 'Aluno', 'Hora']], use_container_width=True, hide_index=True)
        with t4:
            mus_raw = base.list_rows("Musicos")
            st_list = [{"Nome": m.get('Nome'), "Estado": "✅ OK" if m.get('Telefone') else "❌ Falta Telefone"} for m in mus_raw]
            st.dataframe(pd.DataFrame(st_list), use_container_width=True, hide_index=True)

    # --- PERFIL MAESTRO ---
    elif user['role'] == "Maestro":
        t1, t2 = st.tabs(["🎼 Repertório", "📅 Agenda"])
        with t1:
            with st.form("add_rep"):
                n, l = st.text_input("Obra"), st.text_input("Link")
                if st.form_submit_button("Adicionar") and validar_link(l)[0]: 
                    base.append_row("Repertorio", {"Nome da Obra": n, "Links": l}); st.rerun()
            rep = base.list_rows("Repertorio")
            for r in rep: st.write(f"🎵 {r.get('Nome da Obra')}")
        with t2:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty: st.dataframe(evs[['Data', 'Nome do Evento']], use_container_width=True, hide_index=True)
