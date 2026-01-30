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

def validar_link(url):
    if not url: return True, ""
    if not re.match(r'^https?://', url):
        return False, "❌ O link deve começar por http:// ou https://"
    if "drive.google.com" in url and "usp=sharing" not in url and "/view" not in url:
        return True, "⚠️ Atenção: Este link do Drive pode não estar configurado corretamente para partilha pública."
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
    st.warning("⚠️ Segurança: Altere a sua password de primeiro acesso (1234).")
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
    
    if user['role'] == "Maestro":
        with st.sidebar.expander("📖 Guia de Links (Drive)"):
            st.caption("Como partilhar:")
            st.write("1. No Drive, clique com o botão direito.")
            st.write("2. Escolha **Partilhar**.")
            st.write("3. Mude para **'Qualquer pessoa com o link'**.")
            st.write("4. Copie e cole no portal.")

    if st.sidebar.button("🚪 Sair"): st.session_state.clear(); st.rerun()

    # --- PERFIL MÚSICO ---
    if user['role'] == "Musico":
        t1, t2, t3, t4 = st.tabs(["📅 Agenda", "👤 Meus Dados", "🎼 Repertório", "🖼️ Galeria"])
        with t1:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data Visual'] = evs['Data'].apply(formatar_data_pt)
                evs['Hora Visual'] = evs['Hora'].apply(lambda x: str(x) if x else "---")
                st.dataframe(evs[['Data Visual', 'Hora Visual', 'Nome do Evento', 'Tipo']], hide_index=True, use_container_width=True)
        with t2:
            musicos = base.list_rows("Musicos")
            m_row = next((r for r in musicos if str(r.get('Username','')).lower() == user['username']), None)
            if m_row:
                with st.form("ficha"):
                    col1, col2 = st.columns(2)
                    with col1:
                        n_tel = st.text_input("Telefone", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                        n_mail = st.text_input("Email", value=str(m_row.get('Email', '')))
                        dt_obj = converter_data_robusta(m_row.get('Data de Nascimento'))
                        n_nasc = st.date_input("Data de Nascimento", value=dt_obj if dt_obj else datetime(1990,1,1), format="DD/MM/YYYY")
                    with col2:
                        st.info(f"📅 Ingresso: {formatar_data_pt(m_row.get('Data Ingresso Banda'))}")
                        n_morada = st.text_area("Morada", value=str(m_row.get('Morada', '')))
                    if st.form_submit_button("💾 Guardar"):
                        base.update_row("Musicos", m_row['_id'], {"Telefone": n_tel, "Email": n_mail, "Morada": n_morada, "Data de Nascimento": str(n_nasc)})
                        st.success("Dados guardados!"); st.rerun()
        with t3:
            st.subheader("🎼 Repertório em Trabalho")
            rep = base.list_rows("Repertorio")
            if rep:
                for r in rep:
                    with st.expander(f"🎵 {r.get('Nome da Obra', 'S/ Nome')}"):
                        st.write(f"**Compositor:** {r.get('Compositor', '---')}")
                        l = r.get('Links', '')
                        if l: st.video(l) if "youtube.com" in l or "youtu.be" in l else st.link_button("Abrir Link / Partitura", l)
        with t4:
            evs_gal = base.list_rows("Eventos")
            arts = [e for e in evs_gal if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3); [cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento']) for i, ev in enumerate(arts)]

    # --- PAINEL DIREÇÃO ---
    elif user['role'] == "Direcao":
        t1, t2, t3, t4 = st.tabs(["📅 Eventos", "🏫 Escola Geral", "🖼️ Galeria", "📊 Status"])
        with t1:
            # Criar Evento
            with st.expander("➕ Novo Evento"):
                with st.form("ne"):
                    ce1, ce2 = st.columns(2)
                    n, d = ce1.text_input("Nome"), ce2.date_input("Data")
                    h, t = ce1.text_input("Hora"), ce2.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada", "Outro"])
                    c = st.text_input("URL Cartaz")
                    if st.form_submit_button("Criar"):
                        base.append_row("Eventos", {"Nome do Evento": n, "Data": str(d), "Hora": h, "Tipo": t, "Cartaz": c}); st.rerun()
            
            # Listar, Editar e Apagar Eventos
            evs_list = base.list_rows("Eventos")
            if evs_list:
                df_evs = pd.DataFrame(evs_list)
                df_evs['Data_FT'] = df_evs['Data'].apply(formatar_data_pt)
                st.dataframe(df_evs[['Data_FT', 'Hora', 'Nome do Evento', 'Tipo']], use_container_width=True, hide_index=True)
                
                st.subheader("⚙️ Gestão de Eventos")
                for i, r in df_evs.iterrows():
                    with st.expander(f"📝 {r['Data_FT']} - {r['Nome do Evento']}"):
                        with st.form(f"edit_ev_{i}"):
                            col_ed1, col_ed2 = st.columns(2)
                            ed_n = col_ed1.text_input("Nome", value=r.get('Nome do Evento', ''))
                            ed_d = col_ed2.date_input("Data", value=converter_data_robusta(r.get('Data')))
                            ed_h = col_ed1.text_input("Hora", value=r.get('Hora', ''))
                            ed_t = col_ed2.selectbox("Tipo", ["Ensaio", "Concerto", "Arruada", "Outro"], index=["Ensaio", "Concerto", "Arruada", "Outro"].index(r.get('Tipo', 'Ensaio')))
                            ed_c = st.text_input("URL Cartaz", value=r.get('Cartaz', ''))
                            
                            c_save, c_del = st.columns([1,1])
                            if c_save.form_submit_button("💾 Guardar Alterações"):
                                base.update_row("Eventos", r['_id'], {"Nome do Evento": ed_n, "Data": str(ed_d), "Hora": ed_h, "Tipo": ed_t, "Cartaz": ed_c})
                                st.success("Atualizado!"); time.sleep(0.5); st.rerun()
                            if c_del.form_submit_button("🗑️ Apagar Evento"):
                                base.delete_row("Eventos", r['_id']); st.rerun()

        with t2:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)
        with t3:
            evs_gal = base.list_rows("Eventos")
            arts = [e for e in evs_gal if e.get('Cartaz') and str(e['Cartaz']).startswith('http')]
            if arts:
                cols = st.columns(3); [cols[i%3].image(ev['Cartaz'], caption=ev['Nome do Evento']) for i, ev in enumerate(arts)]
        with t4:
            st.subheader("📋 Status e Exportação")
            mus_raw = base.list_rows("Musicos")
            if mus_raw:
                st_list = []
                for m in mus_raw:
                    faltam = [f for f in ["Username", "Telefone", "Email", "Morada", "Data de Nascimento"] if not m.get(f)]
                    st_list.append({"Nome": m.get('Nome'), "Estado": "✅ OK" if not faltam else f"❌ Falta: {', '.join(faltam)}"})
                df_st = pd.DataFrame(st_list)
                st.dataframe(df_st, use_container_width=True, hide_index=True)
                csv = df_st.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Descarregar CSV", csv, "status_musicos.csv", "text/csv")

    # --- PAINEL MAESTRO ---
    elif user['role'] == "Maestro":
        t1, t2, t3 = st.tabs(["🎼 Repertório", "📅 Agenda", "🏫 Escola Geral"])
        with t1:
            st.subheader("Gerir Repertório")
            with st.expander("➕ Adicionar Obra"):
                with st.form("add_rep"):
                    n, c = st.text_input("Nome da Obra"), st.text_input("Compositor")
                    l = st.text_input("Link (Drive/Youtube)")
                    ok, msg = validar_link(l)
                    if not ok: st.error(msg)
                    elif msg: st.warning(msg)
                    if st.form_submit_button("Publicar") and ok:
                        base.append_row("Repertorio", {"Nome da Obra": n, "Compositor": c, "Links": l})
                        st.success("Publicado!"); time.sleep(1); st.rerun()
            rep = base.list_rows("Repertorio")
            if rep:
                for idx, r in enumerate(rep):
                    c1, c2 = st.columns([5,1]); c1.write(f"🎵 **{r.get('Nome da Obra')}** - {r.get('Compositor')}")
                    if c2.button("Remover", key=f"del_rep_{idx}"): base.delete_row("Repertorio", r['_id']); st.rerun()
        with t2:
            evs = pd.DataFrame(base.list_rows("Eventos"))
            if not evs.empty:
                evs['Data_FT'] = evs['Data'].apply(formatar_data_pt)
                st.dataframe(evs[['Data_FT', 'Hora', 'Nome do Evento', 'Tipo']], use_container_width=True, hide_index=True)
        with t3:
            aulas = pd.DataFrame(base.list_rows("Aulas"))
            if not aulas.empty: st.dataframe(aulas[['Professor', 'Aluno', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)

    # --- PAINEL PROFESSOR ---
    elif user['role'] == "Professor":
        st.title("👨‍🏫 Alunos")
        with st.expander("➕ Novo Aluno"):
            with st.form("add_al"):
                n, c, h, s = st.text_input("Nome"), st.text_input("Contacto"), st.text_input("Horário"), st.text_input("Sala")
                if st.form_submit_button("Confirmar"):
                    base.append_row("Aulas", {"Professor": user['display_name'], "Aluno": n, "Contacto": c, "DiaHora": h, "Sala": s}); st.rerun()
        aulas = pd.DataFrame(base.list_rows("Aulas"))
        if not aulas.empty:
            meus = aulas[aulas['Professor'] == user['display_name']]
            st.dataframe(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']], use_container_width=True, hide_index=True)
            with st.expander("🗑️ Remover"):
                for i, r in meus.iterrows():
                    c1, c2 = st.columns([5,1]); c1.write(f"👤 {r['Aluno']}")
                    if c2.button("Apagar", key=f"dal_{i}"): base.delete_row("Aulas", r['_id']); st.rerun()
