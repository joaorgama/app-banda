"""
Interface da Direção - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt
from datetime import datetime

def render(base, user):
    """Renderiza interface da direção"""
    st.title("📊 Painel da Direção")
    
    t1, t2, t3, t4 = st.tabs([
        "📅 Eventos",
        "🎷 Inventário",
        "🏫 Escola",
        "📊 Status Geral"
    ])
    
    # ========================================
    # TAB 1: GESTÃO DE EVENTOS
    # ========================================
    with t1:
        st.subheader("📅 Gestão de Eventos")
        
        # Criar novo evento
        with st.expander("➕ Criar Novo Evento", expanded=False):
            with st.form("novo_evento"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome do Evento*", placeholder="Ex: Concerto de Natal")
                    data = st.date_input("Data*", min_value=datetime.now())
                
                with col2:
                    hora = st.text_input("Hora*", placeholder="Ex: 21:00")
                    tipo = st.selectbox("Tipo", ["Concerto", "Ensaio", "Actuação", "Outro"])
                
                descricao = st.text_area("Descrição", placeholder="Descrição do evento...")
                cartaz_url = st.text_input("URL do Cartaz", placeholder="https://...")
                
                if st.form_submit_button("✅ Criar Evento", use_container_width=True):
                    if not nome or not data or not hora:
                        st.error("⚠️ Preencha todos os campos obrigatórios")
                    else:
                        try:
                            base.append_row("Eventos", {
                                "Nome do Evento": nome,
                                "Data": str(data),
                                "Hora": hora,
                                "Tipo": tipo,
                                "Descricao": descricao,
                                "Cartaz": cartaz_url
                            })
                            st.success(f"✅ Evento **{nome}** criado!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
        
        st.divider()
        
        # Listar eventos com detalhes de presenças
        try:
            eventos = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            musicos = base.list_rows("Musicos")
            
            if not eventos:
                st.info("📭 Nenhum evento criado")
            else:
                st.write(f"**Total de eventos:** {len(eventos)}")
                
                for e in eventos:
                    with st.expander(f"📝 {e.get('Nome do Evento')} - {formatar_data_pt(e.get('Data'))}"):
                        
                        # Informações do evento
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**Data:** {formatar_data_pt(e.get('Data'))}")
                            st.write(f"**Hora:** {e.get('Hora', '---')}")
                            st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")
                        
                        with col2:
                            # Estatísticas rápidas
                            pres_evento = [p for p in presencas if p.get('EventoID') == e['_id']]
                            vao = len([p for p in pres_evento if p.get('Resposta') == 'Vou'])
                            nao_vao = len([p for p in pres_evento if p.get('Resposta') == 'Não Vou'])
                            talvez = len([p for p in pres_evento if p.get('Resposta') == 'Talvez'])
                            pendentes = len(musicos) - len(pres_evento)
                            
                            st.metric("✅ Confirmados", vao)
                            st.caption(f"❌ Não Vão: {nao_vao} | ❓ Talvez: {talvez} | ⏳ Pendentes: {pendentes}")
                        
                        with col3:
                            if st.button("🗑️ Apagar", key=f"del_ev_{e['_id']}", type="secondary"):
                                try:
                                    base.delete_row("Eventos", e['_id'])
                                    st.success("Evento removido!")
                                    st.rerun()
                                except Exception as e_error:
                                    st.error(f"Erro: {e_error}")
                        
                        st.divider()
                        
                        # ========================================
                        # LISTA DETALHADA DE PRESENÇAS POR NAIPE
                        # ========================================
                        st.subheader("🎼 Presenças por Músico e Naipe")
                        
                        # Criar dicionário de respostas
                        respostas_dict = {}
                        for p in pres_evento:
                            username_p = p.get('Username')
                            if username_p:
                                # Garantir que é string antes de fazer lower()
                                username_key = str(username_p).lower().strip()
                                respostas_dict[username_key] = p.get('Resposta')
                        
                        # Criar lista com todos os músicos e suas respostas
                        lista_musicos = []
                        for m in musicos:
                            # Verificação segura do username
                            username_raw = m.get('Username')
                            if username_raw and str(username_raw).strip():
                                username = str(username_raw).lower().strip()
                            else:
                                # Se não tem username, usar o nome como identificador
                                username = str(m.get('Nome', '')).lower().strip()
                            
                            nome = m.get('Nome', 'Desconhecido')
                            instrumento = m.get('Instrumento', 'Não definido')
                            resposta = respostas_dict.get(username, 'Pendente')
                            
                            lista_musicos.append({
                                'Nome': nome,
                                'Instrumento': instrumento,
                                'Resposta': resposta
                            })
                        
                        if lista_musicos:
                            # Criar DataFrame
                            df_musicos = pd.DataFrame(lista_musicos)
                            
                            # Ordenar por Instrumento e depois por Nome
                            df_musicos = df_musicos.sort_values(['Instrumento', 'Nome'])
                            
                            # Filtro por resposta
                            col_filtro1, col_filtro2 = st.columns([2, 2])
                            
                            with col_filtro1:
                                filtro_resposta = st.multiselect(
                                    "Filtrar por resposta:",
                                    options=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                    default=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                    key=f"filtro_resp_{e['_id']}"
                                )
                            
                            with col_filtro2:
                                # Contar instrumentos únicos
                                instrumentos_unicos = df_musicos['Instrumento'].unique()
                                st.caption(f"📊 Naipes presentes: {len(instrumentos_unicos)}")
                            
                            # Aplicar filtro
                            df_filtrado = df_musicos[df_musicos['Resposta'].isin(filtro_resposta)]
                            
                            # Adicionar emoji de status
                            def add_emoji(resposta):
                                if resposta == 'Vou':
                                    return '✅ Vou'
                                elif resposta == 'Não Vou':
                                    return '❌ Não Vou'
                                elif resposta == 'Talvez':
                                    return '❓ Talvez'
                                else:
                                    return '⏳ Pendente'
                            
                            df_filtrado['Estado'] = df_filtrado['Resposta'].apply(add_emoji)
                            
                            # Exibir tabela interativa
                            st.dataframe(
                                df_filtrado[['Nome', 'Instrumento', 'Estado']],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Nome": st.column_config.TextColumn("👤 Músico", width="medium"),
                                    "Instrumento": st.column_config.TextColumn("🎷 Instrumento", width="medium"),
                                    "Estado": st.column_config.TextColumn("📋 Resposta", width="medium")
                                }
                            )
                            
                            st.divider()
                            
                            # ========================================
                            # ANÁLISE POR NAIPE
                            # ========================================
                            st.subheader("📊 Análise por Naipe")
                            
                            # Agrupar por instrumento
                            naipes_stats = []
                            for inst in sorted(df_musicos['Instrumento'].unique()):
                                df_inst = df_musicos[df_musicos['Instrumento'] == inst]
                                total = len(df_inst)
                                vao_inst = len(df_inst[df_inst['Resposta'] == 'Vou'])
                                nao_vao_inst = len(df_inst[df_inst['Resposta'] == 'Não Vou'])
                                talvez_inst = len(df_inst[df_inst['Resposta'] == 'Talvez'])
                                pend_inst = len(df_inst[df_inst['Resposta'] == 'Pendente'])
                                
                                naipes_stats.append({
                                    'Naipe': inst,
                                    'Total': total,
                                    '✅ Vão': vao_inst,
                                    '❌ Não Vão': nao_vao_inst,
                                    '❓ Talvez': talvez_inst,
                                    '⏳ Pendentes': pend_inst
                                })
                            
                            df_naipes = pd.DataFrame(naipes_stats)
                            
                            # Exibir tabela de naipes
                            st.dataframe(
                                df_naipes,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Naipe": st.column_config.TextColumn("🎷 Naipe", width="medium"),
                                    "Total": st.column_config.NumberColumn("👥 Total", width="small"),
                                    "✅ Vão": st.column_config.NumberColumn("✅ Vão", width="small"),
                                    "❌ Não Vão": st.column_config.NumberColumn("❌ Não", width="small"),
                                    "❓ Talvez": st.column_config.NumberColumn("❓ Talvez", width="small"),
                                    "⏳ Pendentes": st.column_config.NumberColumn("⏳ Pend.", width="small")
                                }
                            )
                            
                            # Alerta de naipes vazios
                            naipes_vazios = df_naipes[df_naipes['✅ Vão'] == 0]
                            if not naipes_vazios.empty:
                                st.warning(f"⚠️ **Atenção:** Os seguintes naipes não têm confirmações: {', '.join(naipes_vazios['Naipe'].tolist())}")
                        
                        else:
                            st.info("Nenhum músico registado no sistema")
        
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")
            st.exception(e)
    
    # ========================================
    # TAB 2: INVENTÁRIO DE INSTRUMENTOS
    # ========================================
    with t2:
        st.subheader("🎷 Inventário de Instrumentos")
        
        try:
            musicos = base.list_rows("Musicos")
            
            if not musicos:
                st.info("📭 Sem dados de músicos")
            else:
                df_mus = pd.DataFrame(musicos)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                
                total_inst = df_mus['Instrumento'].notna().sum()
                proprios = df_mus['Instrumento Proprio'].sum() if 'Instrumento Proprio' in df_mus.columns else 0
                banda = total_inst - proprios
                
                col1.metric("Total Instrumentos", total_inst)
                col2.metric("Próprios", proprios)
                col3.metric("Da Banda", banda)
                
                st.divider()
                
                # Tabela
                colunas_mostrar = ['Nome', 'Instrumento', 'Marca', 'Modelo', 'Num Serie']
                colunas_existentes = [c for c in colunas_mostrar if c in df_mus.columns]
                
                if colunas_existentes:
                    st.dataframe(
                        df_mus[colunas_existentes],
                        use_container_width=True,
                        hide_index=True
                    )
        
        except Exception as e:
            st.error(f"Erro: {e}")
    
    # ========================================
    # TAB 3: ESCOLA DE MÚSICA
    # ========================================
    with t3:
        st.subheader("🏫 Aulas da Escola")
        
        try:
            aulas = base.list_rows("Aulas")
            
            if not aulas:
                st.info("📭 Sem aulas registadas")
            else:
                df_aulas = pd.DataFrame(aulas)
                
                # Estatísticas
                col1, col2 = st.columns(2)
                
                total_alunos = len(df_aulas)
                professores = df_aulas['Professor'].nunique() if 'Professor' in df_aulas.columns else 0
                
                col1.metric("Total de Alunos", total_alunos)
                col2.metric("Professores Ativos", professores)
                
                st.divider()
                
                # Tabela
                colunas_mostrar = ['Professor', 'Aluno', 'DiaHora', 'Sala']
                colunas_existentes = [c for c in colunas_mostrar if c in df_aulas.columns]
                
                if colunas_existentes:
                    st.dataframe(
                        df_aulas[colunas_existentes],
                        use_container_width=True,
                        hide_index=True
                    )
        
        except Exception as e:
            st.error(f"Erro: {e}")
    
    # ========================================
    # TAB 4: STATUS GERAL
    # ========================================
    with t4:
        st.subheader("📊 Status dos Músicos")
        
        try:
            musicos = base.list_rows("Musicos")
            
            if not musicos:
                st.info("📭 Sem dados")
            else:
                status_list = []
                
                for m in musicos:
                    nome = m.get('Nome', '---')
                    tem_telefone = bool(m.get('Telefone'))
                    tem_email = bool(m.get('Email'))
                    tem_morada = bool(m.get('Morada'))
                    
                    # Calcular completude
                    campos_preenchidos = sum([tem_telefone, tem_email, tem_morada])
                    percentagem = int((campos_preenchidos / 3) * 100)
                    
                    status_list.append({
                        "Nome": nome,
                        "📞 Telefone": "✅" if tem_telefone else "❌",
                        "📧 Email": "✅" if tem_email else "❌",
                        "🏠 Morada": "✅" if tem_morada else "❌",
                        "Completude": f"{percentagem}%"
                    })
                
                df_status = pd.DataFrame(status_list)
                
                # Métricas
                completos = len([s for s in status_list if s["Completude"] == "100%"])
                incompletos = len(status_list) - completos
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Músicos", len(status_list))
                col2.metric("✅ Fichas Completas", completos)
                col3.metric("⚠️ Incompletas", incompletos)
                
                st.divider()
                
                # Tabela
                st.dataframe(
                    df_status,
                    use_container_width=True,
                    hide_index=True
                )
        
        except Exception as e:
            st.error(f"Erro: {e}")
