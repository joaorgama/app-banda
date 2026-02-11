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
    # TAB 1: GESTÃO DE REPORTÓRIO (COM TUTORIAL)
    # ========================================
    with t1:
        st.subheader("🎵 Reportório da Banda")
        
        # ========================================
        # TUTORIAL PARA O MAESTRO
        # ========================================
        with st.expander("❓ Como adicionar links (YouTube, Partituras PDF)", expanded=False):
            st.markdown("""
            ### 📚 Tutorial Rápido - Como Adicionar Links
            
            #### 🎥 **Para adicionar vídeo do YouTube:**
            
            1. **Abra o YouTube** no seu navegador
            2. **Procure** pela música que quer adicionar
            3. **Clique** no vídeo para abrir
            4. Na barra de endereço no topo, **copie o link completo**
               - Exemplo: `https://www.youtube.com/watch?v=abc123`
            5. **Cole** esse link no campo "Link" ao adicionar a obra
            
            ---
            
            #### 📄 **Para adicionar partitura em PDF:**
            
            **Opção 1 - Se o PDF está na internet:**
            1. **Abra** a página onde está o PDF
            2. **Clique com o botão direito** no link do PDF
            3. Escolha **"Copiar endereço do link"** ou **"Copiar URL"**
            4. **Cole** no campo "Link"
            
            **Opção 2 - Se o PDF está no seu computador:**
            1. **Carregue** o PDF para o Google Drive ou Dropbox
            2. **Clique com botão direito** no ficheiro
            3. Escolha **"Obter link"** ou **"Partilhar"**
            4. **Ative** a opção "Qualquer pessoa com o link pode ver"
            5. **Copie** o link e **cole** no campo "Link"
            
            ---
            
            #### 💡 **Dicas úteis:**
            
            - ✅ Pode adicionar **vários links** separados por vírgula
            - ✅ Exemplo: `https://youtube.com/..., https://drive.google.com/...`
            - ✅ Os músicos vão ver estes links e podem clicar neles
            - ✅ Se não tiver link, pode deixar o campo vazio e preencher depois
            
            ---
            
            #### 🆘 **Precisa de ajuda?**
            
            Se tiver dificuldades, peça ajuda a um músico mais jovem ou contacte a direção! 😊
            """)
        
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
                    help="Cole aqui o link do YouTube ou da partitura em PDF. Veja o tutorial acima se tiver dúvidas!"
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
                                # Suportar múltiplos links separados por vírgula
                                links = str(r.get('Links')).split(',')
                                for link in links:
                                    link = link.strip()
                                    if link:
                                        # Identificar tipo de link e criar botão clicável
                                        if 'youtube' in link.lower() or 'youtu.be' in link.lower():
                                            st.caption(f"🎥 [Ver no YouTube]({link})")
                                        elif '.pdf' in link.lower() or 'drive.google' in link.lower() or 'dropbox' in link.lower():
                                            st.caption(f"📄 [Abrir Partitura]({link})")
                                        else:
                                            st.caption(f"🔗 [Abrir Link]({link})")
                        
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
    # TAB 2: AGENDA DE EVENTOS (COM DETALHES DE PRESENÇAS)
    # ========================================
    with t2:
        st.subheader("📅 Eventos Agendados")
        
        try:
            eventos = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            musicos = base.list_rows("Musicos")
            
            if not eventos:
                st.info("📭 Nenhum evento agendado")
            else:
                for e in eventos:
                    with st.expander(f"📅 {formatar_data_pt(e.get('Data'))} - {e.get('Nome do Evento')}"):
                        
                        # Informações do evento
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
                        
                        presencas_evento = [p for p in presencas if p.get('EventoID') == e['_id']]
                        
                        if presencas_evento:
                            vao = len([p for p in presencas_evento if p.get('Resposta') == 'Vou'])
                            nao_vao = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vou'])
                            talvez = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
                            pendentes = len(musicos) - len(presencas_evento)
                            
                            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                            col_stat1.metric("✅ Vão", vao)
                            col_stat2.metric("❌ Não Vão", nao_vao)
                            col_stat3.metric("❓ Talvez", talvez)
                            col_stat4.metric("⏳ Pendentes", pendentes)
                        else:
                            st.info("⏳ Sem respostas ainda")
                        
                        # ========================================
                        # LISTA DETALHADA DE PRESENÇAS POR MÚSICO
                        # ========================================
                        if musicos:
                            st.divider()
                            st.subheader("🎼 Presenças por Músico")
                            
                            # Criar dicionário de respostas
                            respostas_dict = {}
                            for p in presencas_evento:
                                username_p = p.get('Username')
                                if username_p:
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
                                    username = str(m.get('Nome', '')).lower().strip()
                                
                                nome = m.get('Nome', 'Desconhecido')
                                
                                # Verificação segura do instrumento
                                instrumento_raw = m.get('Instrumento')
                                if instrumento_raw and str(instrumento_raw).strip():
                                    instrumento = str(instrumento_raw).strip()
                                else:
                                    instrumento = "Não definido"
                                
                                resposta = respostas_dict.get(username, 'Pendente')
                                
                                lista_musicos.append({
                                    'Nome': nome,
                                    'Instrumento': instrumento,
                                    'Resposta': resposta
                                })
                            
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
                                    key=f"filtro_resp_maestro_{e['_id']}"
                                )
                            
                            with col_filtro2:
                                # Contar instrumentos únicos (excluindo "Não definido")
                                instrumentos_definidos = df_musicos[df_musicos['Instrumento'] != 'Não definido']
                                num_naipes = len(instrumentos_definidos['Instrumento'].unique()) if not instrumentos_definidos.empty else 0
                                st.caption(f"📊 Naipes definidos: {num_naipes}")
                            
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
                            
                            # ========================================
                            # ANÁLISE POR NAIPE
                            # ========================================
                            instrumentos_validos = df_musicos[df_musicos['Instrumento'] != 'Não definido']
                            
                            if not instrumentos_validos.empty:
                                st.divider()
                                st.subheader("📊 Análise por Naipe")
                                
                                # Agrupar por instrumento
                                naipes_stats = []
                                for inst in sorted(instrumentos_validos['Instrumento'].unique()):
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
                                
                                if naipes_stats:
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
                                    if not naipes_vazios.empty and len(naipes_vazios) > 0:
                                        naipes_lista = naipes_vazios['Naipe'].tolist()
                                        if naipes_lista:
                                            st.warning(f"⚠️ **Atenção:** Os seguintes naipes não têm confirmações: {', '.join(naipes_lista)}")
                            else:
                                st.info("ℹ️ Os músicos ainda não têm instrumentos definidos.")
        
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
