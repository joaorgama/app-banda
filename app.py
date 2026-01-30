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

    # --- PERFIL MÚSICO (Agenda, Dados, Instrumento, Repertório, Galeria) ---
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
                    c1, c2 = st.columns(2); n_tel = c1.text_input("Telefone", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                    n_mail = c1.text_input("Email", value=str(m_row.get('Email', ''))); n_nasc = c1.date_input("Nascimento", value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990,1,1))
                    n_morada = c2.text_area("Morada", value=str(m_row.get('Morada', '')))
                    if st.form_submit_button("💾 Guardar Dados"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)}); st.success("Guardado!"); st.rerun()
        with t3:
            if m_row:
                with st.form("inst_form"):
                    proprio = st.checkbox("Instrumento Próprio", value=m_row.get('Instrumento Proprio', False))
                    inst_nome = st.text_input("Instrumento", value=m_row.get('Instrumento', ''))
                    marca = st.text_input("Marca", value=m_row.get('Marca', ''), disabled=proprio)
                    modelo = st.text_input("Modelo", value=m_row.get('Modelo', ''), disabled=proprio)
                    n_serie = st.text_input("Número de Série", value=m_row.get('Num Serie', ''), disabled=proprio)
                    if st.form_submit_button("💾 Atualizar Instrumento"):
                        upd = {"Instrumento Proprio": proprio, "Instrumento": inst_nome, "Marca": "" if proprio else marca, "Modelo": "" if proprio else modelo, "Num Serie": "" if proprio else n_serie}
                        base.update_row("Musicos", m_row['_id'], upd); st.success("Atualizado!"); st.rerun()
        with t4:
            rep = base.list_rows("Repertorio")
            for r in rep or []:
                with st.expander(f"🎵 {r.get('Nome da Obra')}"):
                    l = r.get('Links', '')
                    if l: st.video(l) if "youtube" in l else st.link_button("Abrir Link", l)
        with t5:
            arts = [e for e in base.list_rows("Eventos") if e.get('Cartaz') and str(e['Cartaz']).strip().startswith('http')]
            cols = st.columns(3); [cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento']) for i, ev in enumerate(arts)]

    # --- PAINEL DIREÇÃO ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4, t5 = st.tabs(["📅 Eventos & Presenças", "🎷 Inventário", "🏫 Escola Geral", "🖼️ Galeria", "📊 Status"])
        with t1:
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    ce1, ce2 = st.columns(2); n, d = ce1.text_input("Nome"), ce2.date_input("Data")
                    h, t = ce1.text_input("Hora"), ce2.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada", "Outro"])
                    c = st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"): base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Hora": h, "Tipo": t, "Cartaz": c}); st.rerun()
            evs = base.list_rows("Eventos"); pres_all = base.list_rows("Presencas")
            for e in evs:
                with st.expander(f"📝 {formatar_data_pt(e['Data'])} - {e['Nome do Evento']}"):
                    te1, te2 = st.tabs(["✏️ Editar", "👥 Presenças"])
                    with te1:
                        with st.form(f"ed_{e['_id']}"):
                            ed_n = st.text_input("Nome", value=e.get('Nome do Evento')); ed_d = st.date_input("Data", value=converter_data_robusta(e.get('Data')))
                            ed_c = st.text_input("URL Cartaz", value=e.get('Cartaz', ''))
                            if st.form_submit_button("💾 Atualizar"): base.update_row("Eventos", e['_id'], {"Nome do Evento": ed_n, "Data": str(ed_d), "Cartaz": ed_c}); st.rerun()
                            if st.form_submit_button("🗑️ Apagar"): base.delete_row("Eventos", e['_id']); st.rerun()
                    with te2:
                        p_ev = [p for p in pres_all if p['EventoID'] == e['_id']]
                        if p_ev: st.dataframe(pd.DataFrame(p_ev)[['Username', 'Resposta']], use_container_width=True, hide_index=True)
        with t2:
            mus_list = base.list_rows("Musicos")
            if mus_list: st.dataframe(pd.DataFrame(mus_list)[['Nome', 'Instrumento', 'Instrumento Proprio', 'Marca', 'Num Serie']], use_container_width=True, hide_index=True)
        with t3:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Local', 'Professor', 'Aluno', 'Hora']], use_container_width=True, hide_index=True)
        with t4:
            arts = [e for e in base.list_rows("Eventos") if e.get('Cartaz') and str(e['Cartaz']).strip().startswith('http')]
            cols = st.columns(3); [cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento']) for i, ev in enumerate(arts)]
        with t5:
            mus_raw = base.list_rows("Musicos")
            st_list = [{"Nome": m.get('Nome'), "Estado": "✅ OK" if not [f for f in ["Username", "Telefone", "Email", "Morada", "Data de Nascimento"] if not m.get(f)] else "❌ Incompleto"} for m in mus_raw]
            st.dataframe(pd.DataFrame(st_list), use_container_width=True, hide_index=True)

    # --- PAINEL PROFESSOR (CALENDÁRIO COM DESTAQUE ⭐ E RECORRÊNCIA) ---
    elif user['role'] == "Professor":
        st.header("👨‍🏫 Portal do Professor")
        tab_cal, tab_meus = st.tabs(["📅 Mapa de Ocupação ⭐", "👤 Meus Alunos"])

        aulas_raw = base.list_rows("Aulas")
        df_aulas = pd.DataFrame(aulas_raw) if aulas_raw else pd.DataFrame()

        with tab_cal:
            local_sel = st.radio("Local:", ["Algés", "Oeiras"], horizontal=True)
            
            # Cálculo de 14 dias
            hoje = datetime.now().date()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            dias_calendario = [inicio_semana + timedelta(days=i) for i in range(14)]
            
            horas_dia = [f"{h:02d}:00" for h in range(8, 22)]
            col_names = [d.strftime("%a %d/%m") for d in dias_calendario]
            df_cal = pd.DataFrame("", index=horas_dia, columns=col_names)

            if not df_aulas.empty:
                df_aulas['Data_Obj'] = df_aulas['Data Aula'].apply(converter_data_robusta)
                filtro = df_aulas[df_aulas['Local'] == local_sel]
                
                for _, aula in filtro.iterrows():
                    h_aula = str(aula.get('Hora', ''))[:5]
                    if h_aula not in horas_dia: continue
                    
                    is_mine = (aula['Professor'] == user['display_name'])
                    prefix = "⭐ " if is_mine else ""
                    content = f"{prefix}{aula['Professor']} ({aula['Sala']})"

                    # Lógica de preenchimento
                    for d_cal in dias_calendario:
                        # Se for recorrente, preenche o mesmo dia da semana. Se for pontual, só a data exata.
                        is_recorrente = aula.get('Recorrente', False)
                        mesmo_dia_semana = (aula['Data_Obj'].weekday() == d_cal.weekday())
                        data_exata = (aula['Data_Obj'] == d_cal)

                        if (is_recorrente and mesmo_dia_semana) or (not is_recorrente and data_exata):
                            col_idx = d_cal.strftime("%a %d/%m")
                            df_cal.at[h_aula, col_idx] = content

            st.write(f"### Mapa de Salas - {local_sel}")
            st.info("⭐ Marca as tuas aulas. Aulas recorrentes aparecem semanalmente.")
            st.dataframe(df_cal, use_container_width=True)

            with st.expander("➕ Marcar Nova Aula"):
                with st.form("nova_aula_rec"):
                    c1, c2 = st.columns(2)
                    al = c1.text_input("Aluno")
                    dt_a = c2.date_input("Data de Início/Aula", min_value=hoje)
                    loc = c1.selectbox("Local", ["Algés", "Oeiras"])
                    hr = c2.selectbox("Hora Início", horas_dia)
                    sl = c1.text_input("Sala")
                    rec = st.checkbox("Aula Recorrente (Semanal)", value=True)
                    if st.form_submit_button("Confirmar"):
                        base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": al, "Data Aula": str(dt_a), "Local": loc, "Hora": hr, "Sala": sl, "Recorrente": rec})
                        st.success("Registado!"); time.sleep(1); st.rerun()

        with tab_meus:
            if not df_aulas.empty:
                meus = df_aulas[df_aulas['Professor'] == user['display_name']]
                if not meus.empty:
                    st.dataframe(meus[['Aluno', 'Local', 'Data Aula', 'Hora', 'Recorrente']], use_container_width=True, hide_index=True)
                    al_rem = st.selectbox("Remover Aula de:", meus['Aluno'].tolist())
                    if st.button("Eliminar"):
                        base.delete_row("Aulas", meus[meus['Aluno'] == al_rem].iloc[0]['_id']); st.rerun()

    # --- PAINEL MAESTRO (Repertório, Agenda, Escola) ---
    elif user['role'] == "Maestro":
        t1, t2, t3 = st.tabs(["🎼 Repertório", "📅 Agenda", "🏫 Escola Geral"])
        with t1:
            rep = base.list_rows("Repertorio")
            for r in rep or []:
                c1, c2 = st.columns([5,1]); c1.write(f"🎵 {r.get('Nome da Obra')}")
                if c2.button("Apagar", key=f"del_{r['_id']}"): base.delete_row("Repertorio", r['_id']); st.rerun()
        with t2:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty: st.dataframe(evs[['Data', 'Nome do Evento', 'Tipo']], use_container_width=True, hide_index=True)
