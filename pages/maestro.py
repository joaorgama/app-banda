"""
Interface do Maestro - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta

def render(base, user):
    st.title("🎼 Painel do Maestro")

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
            - ✅ Os músicos vão ver estes links e podem clicar neles
            - ✅ Se não tiver link, pode deixar o campo vazio e preencher depois

            ---

            #### 🆘 **Precisa de ajuda?**

            Se tiver dificuldades, peça ajuda a um músico mais jovem ou contacte a direção! 😊
            """)

        with st.expander("➕ Adicionar Nova Obra", expanded=False):
            with st.form("add_repertorio"):
                nome_obra  = st.text_input("Nome da Obra*",  placeholder="Ex: Radetzky March")
                compositor = st.text_input("Compositor*",    placeholder="Ex: Johann Strauss")
                link       = st.text_input(
                    "Link (YouTube ou Partitura)",
                    placeholder="https://...",
                    help="Cole aqui o link do YouTube ou da partitura em PDF."
                )

                if st.form_submit_button("📝 Publicar Obra", use_container_width=True):
                    if not nome_obra or not compositor:
                        st.error("⚠️ Preencha pelo menos o nome e compositor")
                    else:
                        try:
                            base.append_row("Repertorio", {
                                "Nome da Obra": nome_obra,
                                "Compositor":   compositor,
                                "Links":        link
                            })
                            st.success(f"✅ Obra **{nome_obra}** adicionada!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        st.divider()

        try:
            repertorio = base.list_rows("Repertorio")

            if not repertorio:
                st.info("📭 Nenhuma obra no reportório")
            else:
                st.write(f"**Total de obras:** {len(repertorio)}")
                search = st.text_input("🔍 Pesquisar", placeholder="Nome ou compositor...")

                for r in repertorio:
                    nome = r.get('Nome da Obra', 'S/ Nome')
                    comp = r.get('Compositor', 'Desconhecido')

                    if not search or search.lower() in nome.lower() or search.lower() in comp.lower():
                        col1, col2 = st.columns([6, 1])

                        with col1:
                            st.write(f"🎵 **{nome}** - *{comp}*")
                            if r.get('Links'):
                                links = str(r.get('Links')).split(',')
                                for lnk in links:
                                    lnk = lnk.strip()
                                    if lnk:
                                        if 'youtube' in lnk.lower() or 'youtu.be' in lnk.lower():
                                            st.caption(f"🎥 [Ver no YouTube]({lnk})")
                                        elif '.pdf' in lnk.lower() or 'drive.google' in lnk.lower() or 'dropbox' in lnk.lower():
                                            st.caption(f"📄 [Abrir Partitura]({lnk})")
                                        else:
                                            st.caption(f"🔗 [Abrir Link]({lnk})")

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
            eventos   = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            musicos   = base.list_rows("Musicos")

            if not eventos:
                st.info("📭 Nenhum evento agendado")
            else:
                # Ordenar cronologicamente — datas inválidas ficam no fim
                def _data_sort(ev):
                    try:
                        return datetime.strptime(str(ev.get('Data', ''))[:10], "%Y-%m-%d").date()
                    except Exception:
                        return datetime.max.date()

                eventos = sorted(eventos, key=_data_sort)

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

                        st.divider()

                        presencas_evento = [p for p in presencas if p.get('EventoID') == e['_id']]

                        if presencas_evento:
                            vao      = len([p for p in presencas_evento if p.get('Resposta') == 'Vou'])
                            nao_vao  = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vou'])
                            talvez   = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
                            pendentes = len(musicos) - len(presencas_evento)
                            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                            col_s1.metric("✅ Vão",       vao)
                            col_s2.metric("❌ Não Vão",   nao_vao)
                            col_s3.metric("❓ Talvez",    talvez)
                            col_s4.metric("⏳ Pendentes", pendentes)
                        else:
                            st.info("⏳ Sem respostas ainda")

                        if musicos:
                            st.divider()
                            st.subheader("🎼 Presenças por Músico")

                            respostas_dict = {}
                            for p in presencas_evento:
                                username_p = p.get('Username')
                                if username_p:
                                    respostas_dict[str(username_p).lower().strip()] = p.get('Resposta')

                            lista_musicos = []
                            for m in musicos:
                                username_raw = m.get('Username')
                                username     = str(username_raw).lower().strip() if username_raw and str(username_raw).strip() else str(m.get('Nome', '')).lower().strip()
                                instrumento_raw = m.get('Instrumento')
                                instrumento  = str(instrumento_raw).strip() if instrumento_raw and str(instrumento_raw).strip() else "Não definido"
                                lista_musicos.append({
                                    'Nome':        m.get('Nome', 'Desconhecido'),
                                    'Instrumento': instrumento,
                                    'Resposta':    respostas_dict.get(username, 'Pendente')
                                })

                            df_musicos = pd.DataFrame(lista_musicos).sort_values(['Instrumento', 'Nome'])

                            col_filtro1, col_filtro2 = st.columns([2, 2])
                            with col_filtro1:
                                filtro_resposta = st.multiselect(
                                    "Filtrar por resposta:",
                                    options=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                    default=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                    key=f"filtro_resp_maestro_{e['_id']}"
                                )
                            with col_filtro2:
                                inst_def   = df_musicos[df_musicos['Instrumento'] != 'Não definido']
                                num_naipes = len(inst_def['Instrumento'].unique()) if not inst_def.empty else 0
                                st.caption(f"📊 Naipes definidos: {num_naipes}")

                            df_filtrado = df_musicos[df_musicos['Resposta'].isin(filtro_resposta)].copy()

                            def add_emoji(resposta):
                                return {'Vou': '✅ Vou', 'Não Vou': '❌ Não Vou', 'Talvez': '❓ Talvez'}.get(resposta, '⏳ Pendente')

                            df_filtrado['Estado'] = df_filtrado['Resposta'].apply(add_emoji)
                            st.dataframe(
                                df_filtrado[['Nome', 'Instrumento', 'Estado']],
                                use_container_width=True, hide_index=True,
                                column_config={
                                    "Nome":        st.column_config.TextColumn("👤 Músico",      width="medium"),
                                    "Instrumento": st.column_config.TextColumn("🎷 Instrumento", width="medium"),
                                    "Estado":      st.column_config.TextColumn("📋 Resposta",    width="medium")
                                }
                            )

                            instrumentos_validos = df_musicos[df_musicos['Instrumento'] != 'Não definido']
                            if not instrumentos_validos.empty:
                                st.divider()
                                st.subheader("📊 Análise por Naipe")
                                naipes_stats = []
                                for inst in sorted(instrumentos_validos['Instrumento'].unique()):
                                    df_inst = df_musicos[df_musicos['Instrumento'] == inst]
                                    naipes_stats.append({
                                        'Naipe':        inst,
                                        'Total':        len(df_inst),
                                        '✅ Vão':       len(df_inst[df_inst['Resposta'] == 'Vou']),
                                        '❌ Não Vão':   len(df_inst[df_inst['Resposta'] == 'Não Vou']),
                                        '❓ Talvez':    len(df_inst[df_inst['Resposta'] == 'Talvez']),
                                        '⏳ Pendentes': len(df_inst[df_inst['Resposta'] == 'Pendente'])
                                    })
                                if naipes_stats:
                                    df_naipes = pd.DataFrame(naipes_stats)
                                    st.dataframe(
                                        df_naipes,
                                        use_container_width=True, hide_index=True,
                                        column_config={
                                            "Naipe":        st.column_config.TextColumn("🎷 Naipe",   width="medium"),
                                            "Total":        st.column_config.NumberColumn("👥 Total",  width="small"),
                                            "✅ Vão":       st.column_config.NumberColumn("✅ Vão",    width="small"),
                                            "❌ Não Vão":   st.column_config.NumberColumn("❌ Não",    width="small"),
                                            "❓ Talvez":    st.column_config.NumberColumn("❓ Talvez", width="small"),
                                            "⏳ Pendentes": st.column_config.NumberColumn("⏳ Pend.",  width="small")
                                        }
                                    )
                                    naipes_vazios = df_naipes[df_naipes['✅ Vão'] == 0]['Naipe'].tolist()
                                    if naipes_vazios:
                                        st.warning(f"⚠️ **Atenção:** Naipes sem confirmações: {', '.join(naipes_vazios)}")
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
            eventos_gal        = base.list_rows("Eventos")
            eventos_com_cartaz = [e for e in eventos_gal if e.get('Cartaz')]

            if not eventos_com_cartaz:
                st.info("📭 Nenhum cartaz disponível no momento")
            else:
                cols = st.columns(3)
                for i, ev in enumerate(eventos_com_cartaz):
                    with cols[i % 3]:
                        st.image(ev['Cartaz'], caption=ev.get('Nome do Evento', 'Evento'), use_column_width=True)
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
        st.subheader("🎂 Aniversários")

        try:
            musicos = base.list_rows("Musicos")

            if not musicos:
                st.info("📭 Sem dados de músicos")
            else:
                hoje        = datetime.now().date()
                data_limite = hoje + timedelta(days=15)
                aniversarios = []

                for m in musicos:
                    data_nasc = converter_data_robusta(m.get('Data de Nascimento'))
                    if not data_nasc:
                        continue
                    try:
                        aniv = data_nasc.replace(year=hoje.year)
                    except ValueError:
                        aniv = data_nasc.replace(year=hoje.year, day=28)
                    if aniv < hoje:
                        try:
                            aniv = data_nasc.replace(year=hoje.year + 1)
                        except ValueError:
                            aniv = data_nasc.replace(year=hoje.year + 1, day=28)
                    if hoje <= aniv <= data_limite:
                        aniversarios.append({
                            'nome':             m.get('Nome', 'Desconhecido'),
                            'data_aniversario': aniv,
                            'dias_faltam':      (aniv - hoje).days,
                            'idade':            hoje.year - data_nasc.year,
                            'instrumento':      m.get('Instrumento', 'N/D')
                        })

                aniversarios.sort(key=lambda x: x['dias_faltam'])

                if not aniversarios:
                    st.info("🎈 Não há aniversários nos próximos 15 dias")
                else:
                    st.caption(f"📊 {len(aniversarios)} aniversário(s) nos próximos 15 dias")

                    for aniv in aniversarios:
                        dias = aniv['dias_faltam']
                        emoji, msg = ("🎉", "**HOJE!**") if dias == 0 else ("🎂", "**Amanhã**") if dias == 1 else ("🎈", f"Em {dias} dias")

                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"{emoji} **{aniv['nome']}** {msg}")
                            st.caption(f"📅 {formatar_data_pt(str(aniv['data_aniversario']))} • {aniv['idade']} anos • 🎷 {aniv['instrumento']}")
                        with col2:
                            if dias == 0:    st.success("HOJE")
                            elif dias <= 3:  st.warning(f"{dias}d")
                            else:            st.info(f"{dias}d")
                        st.divider()

        except Exception as e:
            st.error(f"Erro ao carregar aniversários: {e}")
