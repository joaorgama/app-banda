"""
Interface do Músico - Portal BMO
"""
import streamlit as st
import time
from helpers import formatar_data_pt, converter_data_robusta
from seatable_conn import add_presenca
from datetime import datetime

def render(base, user):
    """Renderiza interface do músico"""
    st.title("👤 Portal do Músico")
    
    # Criar tabs
    t1, t2, t3, t4, t5 = st.tabs([
        "📅 Agenda",
        "👤 Meus Dados",
        "🎷 Instrumento",
        "🎼 Reportório",
        "🖼️ Galeria"
    ])
    
    # Carregar dados do músico
    try:
        musicos = base.list_rows("Musicos")
        m_row = next((r for r in musicos if str(r.get('Username', '')).lower() == user['username']), None)
    except:
        m_row = None
        st.error("❌ Erro ao carregar dados do músico")
    
    # ========================================
    # TAB 1: AGENDA DE EVENTOS
    # ========================================
    with t1:
        st.subheader("📅 Próximos Eventos")
        
        try:
            eventos = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            
            if not eventos:
                st.info("📭 Nenhum evento agendado no momento")
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
                        
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Hora:** {e.get('Hora', '---')}")
                            st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")
                        
                        with col2:
                            if resp_atual == "Vou":
                                st.success(f"**Estado:** ✅ {resp_atual}")
                            elif resp_atual == "Não Vou":
                                st.error(f"**Estado:** ❌ {resp_atual}")
                            elif resp_atual == "Talvez":
                                st.warning(f"**Estado:** ❓ {resp_atual}")
                            else:
                                st.info(f"**Estado:** ⏳ {resp_atual}")
                        
                        # Mostrar descrição se existir
                        if e.get('Descricao'):
                            st.markdown(f"*{e.get('Descricao')}*")
                        
                        st.divider()
                        
                        # Botões de resposta
                        st.write("**Confirmar presença:**")
                        c1, c2, c3 = st.columns(3)
                        
                        if c1.button("✅ Vou", key=f"vou_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Vou"):
                                st.success("✅ Presença confirmada!")
                                st.rerun()
                        
                        if c2.button("❌ Não Vou", key=f"nao_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Não Vou"):
                                st.info("Ausência registada")
                                st.rerun()
                        
                        if c3.button("❓ Talvez", key=f"talvez_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Talvez"):
                                st.warning("Resposta registada como 'Talvez'")
                                st.rerun()
        
        except Exception as e:
            st.error(f"Erro ao carregar agenda: {e}")
    
    # ========================================
    # TAB 2: DADOS PESSOAIS
    # ========================================
    with t2:
        st.subheader("📋 Ficha Pessoal")
        
        if not m_row:
            st.warning("⚠️ Ficha de músico não encontrada na base de dados")
        else:
            with st.form("ficha_pessoal"):
                col1, col2 = st.columns(2)
                
                with col1:
                    tel = st.text_input(
                        "📞 Telemóvel",
                        value=str(m_row.get('Telefone', '')).replace('.0', ''),
                        help="Formato: 912345678"
                    )
                    
                    nasc = st.date_input(
                        "🎂 Data de Nascimento",
                        value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990, 1, 1),
                        min_value=datetime(1940, 1, 1),
                        max_value=datetime.now()
                    )
                
                with col2:
                    mail = st.text_input(
                        "📧 Email",
                        value=str(m_row.get('Email', '')),
                        help="Email válido para contactos"
                    )
                
                mor = st.text_area(
                    "🏠 Morada Completa",
                    value=str(m_row.get('Morada', '')),
                    height=100,
                    help="Rua, Código Postal, Localidade"
                )
                
                submitted = st.form_submit_button("💾 Guardar Alterações", use_container_width=True)
                
                if submitted:
                    try:
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone": tel,
                            "Email": mail,
                            "Morada": mor,
                            "Data de Nascimento": str(nasc)
                        })
                        st.success("✅ Dados atualizados com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar: {e}")
    
    # ========================================
    # TAB 3: INSTRUMENTO
    # ========================================
    with t3:
        st.subheader("🎷 Gestão de Instrumento")
        
        if not m_row:
            st.warning("⚠️ Dados não encontrados")
        else:
            with st.form("instrumento"):
                prop = st.checkbox(
                    "✅ Instrumento Próprio",
                    value=m_row.get('Instrumento Proprio', False),
                    help="Marque se o instrumento é seu (não da banda)"
                )
                
                inst = st.text_input(
                    "Instrumento",
                    value=m_row.get('Instrumento', ''),
                    help="Ex: Trompete, Trombone, Clarinete"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    marc = st.text_input(
                        "Marca",
                        value=m_row.get('Marca', ''),
                        disabled=prop,
                        help="Marca do instrumento da banda"
                    )
                
                with col2:
                    seri = st.text_input(
                        "Nº de Série",
                        value=m_row.get('Num Serie', ''),
                        disabled=prop,
                        help="Número de série do instrumento da banda"
                    )
                
                if prop:
                    st.info("ℹ️ Como usa instrumento próprio, não precisa preencher marca/série")
                
                if st.form_submit_button("💾 Atualizar Instrumento", use_container_width=True):
                    try:
                        base.update_row("Musicos", m_row['_id'], {
                            "Instrumento Proprio": prop,
                            "Instrumento": inst,
                            "Marca": marc if not prop else "",
                            "Num Serie": seri if not prop else ""
                        })
                        st.success("✅ Instrumento atualizado!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
    
    # ========================================
    # TAB 4: REPORTÓRIO
    # ========================================
    with t4:
        st.subheader("🎼 Reportório da Banda")
        
        try:
            repertorio = base.list_rows("Repertorio")
            
            if not repertorio:
                st.info("📭 Nenhuma obra no reportório atual")
            else:
                # Filtro de pesquisa
                search = st.text_input("🔍 Pesquisar obra ou compositor", "")
                
                for r in repertorio:
                    nome_obra = r.get('Nome da Obra', 'S/ Nome')
                    compositor = r.get('Compositor', '---')
                    
                    # Aplicar filtro
                    if search.lower() in nome_obra.lower() or search.lower() in compositor.lower() or not search:
                        with st.expander(f"🎼 {nome_obra}"):
                            st.write(f"**Compositor:** {compositor}")
                            
                            link = r.get('Links', '')
                            if link:
                                if "youtube" in link.lower() or "youtu.be" in link.lower():
                                    st.video(link)
                                else:
                                    st.link_button("🔗 Abrir Partitura", link, use_container_width=True)
                            else:
                                st.info("Sem partitura disponível")
        
        except Exception as e:
            st.error(f"Erro ao carregar reportório: {e}")
    
    # ========================================
    # TAB 5: GALERIA
    # ========================================
    with t5:
        st.subheader("🖼️ Galeria de Eventos")
        
        try:
            eventos_gal = base.list_rows("Eventos")
            eventos_com_cartaz = [e for e in eventos_gal if e.get('Cartaz')]
            
            if not eventos_com_cartaz:
                st.info("📭 Nenhum cartaz disponível no momento")
            else:
                cols = st.columns(3)
                for i, ev in enumerate(eventos_com_cartaz):
                    with cols[i % 3]:
                        st.image(
                            ev['Cartaz'],
                            caption=ev.get('Nome do Evento', 'Evento'),
                            use_column_width=True
                        )
                        st.caption(formatar_data_pt(ev.get('Data')))
        
        except Exception as e:
            st.error(f"Erro ao carregar galeria: {e}")
