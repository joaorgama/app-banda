"""
Interface do Maestro - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt

def render(base, user):
    """Renderiza interface do maestro"""
    st.title("🎼 Painel do Maestro")
    
    t1, t2 = st.tabs(["🎼 Repertório", "📅 Agenda de Eventos"])
    
    # ========================================
    # TAB 1: GESTÃO DE REPERTÓRIO
    # ========================================
    with t1:
        st.subheader("🎵 Repertório da Banda")
        
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
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
        
        st.divider()
        
        # Listar repertório
        try:
            repertorio = base.list_rows("Repertorio")
            
            if not repertorio:
                st.info("📭 Nenhuma obra no repertório")
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
            st.error(f"Erro ao carregar repertório: {e}")
    
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
                            nao_vao = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vou'])
                            talvez = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("✅ Vão", vao)
                            c2.metric("❌ Não Vão", nao_vao)
                            c3.metric("❓ Talvez", talvez)
                        else:
                            st.info("Sem respostas ainda")
        
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")
