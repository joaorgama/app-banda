"""
Interface do Maestro - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta

def render(base, user):
    """Renderiza interface do maestro"""
    st.title("🎼 Painel do Maestro")
    
    # Tabs COM ANIVERSÁRIOS
    t1, t2, t3, t4, t5 = st.tabs([
        "🎼 Reportório",
        "📅 Agenda de Eventos",
        "🖼️ Galeria",
        "💬 Mensagens",
        "🎂 Aniversários"
    ])
    
    # ========================================
    # TAB 1: GESTÃO DE REPORTÓRIO
    # ========================================
    with t1:
        st.subheader("🎵 Reportório da Banda")
        
        # Adicionar nova obra
        with st.expander("➕ Adicionar Nova Obra", expanded=False):
            with st.form("add_repertorio"):
                nome_obra = st.text_input(
                    "Nome da Obra*",
                    placeholder="Ex: Radetzky March"
                )
                
                compositor = st.text_input(
                    "Compositor*",
                    placeholder="Ex: Johann Strauss"
                )
                
                link = st.text_input(
                    "Link (YouTube ou Partitura)",
                    placeholder="https://...",
                    help="Cole o link do YouTube ou da partitura em PDF"
                )
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if st.form_submit_button("📝 Publicar Obra", use_container_width=True):
                        if not nome_obra or not compositor:
                            st.error("⚠️ Preencha pelo menos o nome e compositor")
                        else:
                            try:
                                base.append_row("Repertorio", {
                                    "Nome da Obra": nome_obra,
                                    "Compositor": compositor,
                                    "Links": link
                                })
                                st.success(f"✅ Obra **{nome_obra}** adicionada!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
        
        st.divider()
        
        # Listar reportório
        try:
            repertorio = base.list_rows("Repertorio")
            
            if not repertorio:
                st.info("📭 Nenhuma obra no reportório")
            else:
                st.write(f"**Total de obras:** {len(repertorio)}")
                
                # Pesquisa
                search = st.text_input("🔍 Pesquisar", placeholder="Nome ou compositor...")
                
                for r in repertorio:
                    nome = r.get('Nome da Obra', 'S/ Nome')
                    comp = r.get('Compositor', 'Desconhecido')
                    
                    # Filtro
                    if not search or search.lower() in nome.lower() or search.lower() in comp.lower():
                        col1, col2 = st.columns([6, 1])
                        
                        with col1:
                            st.write(f"🎵 **{nome}** - *{comp}*")
                            if r.get('Links'):
                                st.caption(f"🔗 {r.get('Links')}")
                        
                        with col2:
                            if st.button("🗑️", key=f"del_rep_{r['_id']}", help="Remover obra"):
                                try:
                                    base.delete_row("Repertorio", r['_id'])
                                    st.success("Removido!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                        
                        st.divider()
        
        except Exception as e:
            st.error(f"Erro ao carregar reportório: {e}")
    
    # ========================================
    # TAB 2: AGENDA DE EVENTOS
    # ========================================
    with t2:
        st.subheader("📅 Eventos Agendados")
        
        try:
            eventos = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            
            if not eventos:
                st.info("📭 Nenhum evento agendado")
            else:
                for e in eventos:
                    with st.expander(f"📅 {formatar_data_pt(e.get('Data'))} - {e.get('Nome do Evento')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Hora:** {e.get('Hora', '---')}")
                            st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")
                            if e.get('Descricao'):
                                st.write(f"**Descrição:** {e.get('Descricao')}")
                        
                        with col2:
                            if e.get('Cartaz'):
                                st.image(e['Cartaz'], width=150)
                        
                        # Estatísticas de presenças
                        st.divider()
                        st.write("**📊 Presenças Confirmadas:**")
                        
                        presencas_evento = [p for p in presencas if p.get('EventoID') == e['_id']]
                        
                        if presencas_evento:
                            vao = len([p for p in presencas_evento if p.get('Resposta') == 'Vou'])
                            nao_vao = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vão'])
                            talvez = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("✅ Vão", vao)
                            c2.metric("❌ Não Vão", nao_vao)
                            c3.metric("❓ Talvez", talvez)
                        else:
                            st.info("Sem respostas ainda")
        
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")
    
    # ========================================
    # TAB 3: GALERIA
    # ========================================
    with t3:
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
    
    # ========================================
    # TAB 4: MENSAGENS
    # ========================================
    with t4:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=False)
    
    # ========================================
    # TAB 5: ANIVERSÁRIOS
    # ========================================
    with t5:
        st.subheader("🎂 Aniversários Próximos")
        
        try:
            musicos = base.list_rows("Musicos")
            
            if not musicos:
                st.info("📭 Sem dados de músicos")
            else:
                # Calcular aniversários
                hoje = datetime.now().date()
                data_limite = hoje + timedelta(days=15)
                aniversarios = []
                
                for m in musicos:
                    data_nasc = converter_data_robusta(m.get('Data de Nascimento'))
                    
                    if not data_nasc:
                        continue
                    
                    try:
                        aniversario_este_ano = data_nasc.replace(year=hoje.year)
                    except ValueError:
                        aniversario_este_ano = data_nasc.replace(year=hoje.year, day=28)
                    
                    if aniversario_este_ano < hoje:
                        try:
                            aniversario_este_ano = data_nasc.replace(year=hoje.year + 1)
                        except ValueError:
                            aniversario_este_ano = data_nasc.replace(year=hoje.year + 1, day=28)
                    
                    if hoje <= aniversario_este_ano <= data_limite:
                        dias_faltam = (aniversario_este_ano - hoje).days
                        idade = hoje.year - data_nasc.year
                        
                        aniversarios.append({
                            'nome': m.get('Nome', 'Desconhecido'),
                            'data_aniversario': aniversario_este_ano,
                            'dias_faltam': dias_faltam,
                            'idade': idade,
                            'instrumento': m.get('Instrumento', 'N/D')
                        })
                
                aniversarios.sort(key=lambda x: x['dias_faltam'])
                
                if not aniversarios:
                    st.info("🎈 Não há aniversários nos próximos 15 dias")
                else:
                    st.caption(f"📊 {len(aniversarios)} aniversário(s) nos próximos 15 dias")
                    
                    for aniv in aniversarios:
                        dias = aniv['dias_faltam']
                        
                        if dias == 0:
                            emoji, msg = "🎉", "**HOJE!**"
                        elif dias == 1:
                            emoji, msg = "🎂", "**Amanhã**"
                        else:
                            emoji, msg = "🎈", f"Em {dias} dias"
                        
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"{emoji} **{aniv['nome']}** {msg}")
                            st.caption(f"📅 {formatar_data_pt(str(aniv['data_aniversario']))} • {aniv['idade']} anos • 🎷 {aniv['instrumento']}")
                        
                        with col2:
                            if dias == 0:
                                st.success("HOJE")
                            elif dias <= 3:
                                st.warning(f"{dias}d")
                            else:
                                st.info(f"{dias}d")
                        
                        st.divider()
        
        except Exception as e:
            st.error(f"Erro ao carregar aniversários: {e}")
            st.exception(e)
