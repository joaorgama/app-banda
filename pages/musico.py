import streamlit as st
from utils.helpers import formatar_data_pt, converter_data_robusta
from utils.seatable_conn import add_presenca
from datetime import datetime

def render(base, user):
    """Renderiza interface do músico"""
    st.title("👤 Portal do Músico")
    
    t1, t2, t3, t4, t5 = st.tabs([
        "📅 Agenda",
        "👤 Meus Dados",
        "🎷 Instrumento",
        "🎼 Repertório",
        "🖼️ Galeria"
    ])
    
    # Carregar dados do músico
    musicos = base.list_rows("Musicos")
    m_row = next((r for r in musicos if str(r.get('Username', '')).lower() == user['username']), None)
    
    # TAB 1: AGENDA
    with t1:
        st.subheader("Próximos Eventos")
        eventos = base.list_rows("Eventos")
        presencas = base.list_rows("Presencas")
        
        if not eventos:
            st.info("📭 Nenhum evento agendado")
        else:
            for e in eventos:
                data_evento = formatar_data_pt(e.get('Data'))
                nome_evento = e.get('Nome do Evento', 'Sem nome')
                
                with st.expander(f"📅 {data_evento} - {nome_evento}"):
                    # Verificar resposta atual
                    resp_atual = next(
                        (p['Resposta'] for p in presencas 
                         if p.get('EventoID') == e['_id'] and p.get('Username') == user['username']),
                        "Pendente"
                    )
                    
                    st.write(f"**Hora:** {e.get('Hora', '---')}")
                    st.write(f"**Seu estado:** {resp_atual}")
                    
                    # Botões de resposta
                    c1, c2, c3 = st.columns(3)
                    
                    if c1.button("✅ Vou", key=f"vou_{e['_id']}", use_container_width=True):
                        if add_presenca(base, e['_id'], user['username'], "Vou"):
                            st.success("Confirmado!")
                            st.rerun()
                    
                    if c2.button("❌ Não Vou", key=f"nao_{e['_id']}", use_container_width=True):
                        if add_presenca(base, e['_id'], user['username'], "Não Vou"):
                            st.success("Registado!")
                            st.rerun()
                    
                    if c3.button("❓ Talvez", key=f"talvez_{e['_id']}", use_container_width=True):
                        if add_presenca(base, e['_id'], user['username'], "Talvez"):
                            st.success("Registado!")
                            st.rerun()
    
    # TAB 2: DADOS PESSOAIS
    with t2:
        st.subheader("Ficha Pessoal")
        if m_row:
            with st.form("ficha_pessoal"):
                tel = st.text_input("📞 Telemóvel", value=str(m_row.get('Telefone', '')).replace('.0', ''))
                mail = st.text_input("📧 Email", value=str(m_row.get('Email', '')))
                nasc = st.date_input(
                    "🎂 Data de Nascimento",
                    value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990, 1, 1)
                )
                mor = st.text_area("🏠 Morada", value=str(m_row.get('Morada', '')))
                
                if st.form_submit_button("💾 Guardar Alterações", use_container_width=True):
                    try:
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone": tel,
                            "Email": mail,
                            "Morada": mor,
                            "Data de Nascimento": str(nasc)
                        })
                        st.success("✅ Dados atualizados!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
        else:
            st.warning("⚠️ Ficha de músico não encontrada")
    
    # TAB 3: INSTRUMENTO
    with t3:
        st.subheader("Instrumento")
        if m_row:
            with st.form("instrumento"):
                prop = st.checkbox(
                    "Instrumento Próprio",
                    value=m_row.get('Instrumento Proprio', False)
                )
                inst = st.text_input("Instrumento", value=m_row.get('Instrumento', ''))
                marc = st.text_input("Marca", value=m_row.get('Marca', ''), disabled=prop)
                seri = st.text_input("Nº Série", value=m_row.get('Num Serie', ''), disabled=prop)
                
                if st.form_submit_button("💾 Atualizar", use_container_width=True):
                    try:
                        base.update_row("Musicos", m_row['_id'], {
                            "Instrumento Proprio": prop,
                            "Instrumento": inst,
                            "Marca": marc if not prop else "",
                            "Num Serie": seri if not prop else ""
                        })
                        st.success("✅ Instrumento atualizado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
    
    # TAB 4: REPERTÓRIO
    with t4:
        st.subheader("Repertório da Banda")
        repertorio = base.list_rows("Repertorio")
        
        if not repertorio:
            st.info("📭 Nenhuma obra no repertório")
        else:
            for r in repertorio:
                with st.expander(f"🎼 {r.get('Nome da Obra', 'S/ Nome')}"):
                    st.write(f"**Compositor:** {r.get('Compositor', '---')}")
                    link = r.get('Links', '')
                    if link:
                        if "youtube" in link.lower() or "youtu.be" in link.lower():
                            st.video(link)
                        else:
                            st.link_button("🔗 Abrir Partitura", link)
    
    # TAB 5: GALERIA
    with t5:
        st.subheader("Galeria de Eventos")
        eventos_gal = base.list_rows("Eventos")
        eventos_com_cartaz = [e for e in eventos_gal if e.get('Cartaz')]
        
        if not eventos_com_cartaz:
            st.info("📭 Nenhum cartaz disponível")
        else:
            cols = st.columns(3)
            for i, ev in enumerate(eventos_com_cartaz):
                with cols[i % 3]:
                    st.image(ev['Cartaz'], caption=ev.get('Nome do Evento', 'Evento'), use_column_width=True)
