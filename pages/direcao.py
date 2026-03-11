"""
Interface da Direção - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta

def render(base, user):
    st.title("📊 Painel da Direção")

    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "📅 Eventos",
        "🎷 Inventário",
        "🏫 Escola",
        "📊 Status Geral",
        "💬 Mensagens",
        "🎂 Aniversários",
        "👥 Utilizadores",
        "👤 Músicos"
    ])

    # ========================================
    # TAB 1: GESTÃO DE EVENTOS
    # ========================================
    with t1:
        st.subheader("📅 Gestão de Eventos")

        with st.expander("➕ Criar Novo Evento", expanded=False):
            with st.form("novo_evento"):
                col1, col2 = st.columns(2)
                with col1:
                    nome = st.text_input("Nome do Evento*", placeholder="Ex: Concerto de Natal")
                    data = st.date_input("Data*", min_value=datetime.now())
                with col2:
                    hora       = st.text_input("Hora*", placeholder="Ex: 21:00")
                    tipo       = st.selectbox("Tipo", ["Concerto", "Ensaio", "Actuação", "Outro"])
                descricao  = st.text_area("Descrição", placeholder="Descrição do evento...")
                cartaz_url = st.text_input("URL do Cartaz", placeholder="https://...")

                if st.form_submit_button("✅ Criar Evento", use_container_width=True):
                    if not nome or not data or not hora:
                        st.error("⚠️ Preencha todos os campos obrigatórios")
                    else:
                        try:
                            base.append_row("Eventos", {
                                "Nome do Evento": nome,
                                "Data":           str(data),
                                "Hora":           hora,
                                "Tipo":           tipo,
                                "Descricao":      descricao,
                                "Cartaz":         cartaz_url
                            })
                            st.success(f"✅ Evento **{nome}** criado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        st.divider()

        try:
            eventos   = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            musicos   = base.list_rows("Musicos")

            if not eventos:
                st.info("📭 Nenhum evento criado")
            else:
                # Ordenar cronologicamente — datas inválidas ficam no fim
                def _data_sort(ev):
                    try:
                        return datetime.strptime(str(ev.get('Data', ''))[:10], "%Y-%m-%d").date()
                    except Exception:
                        return datetime.max.date()

                eventos = sorted(eventos, key=_data_sort)

                st.write(f"**Total de eventos:** {len(eventos)}")

                for e in eventos:
                    with st.expander(f"📝 {e.get('Nome do Evento')} - {formatar_data_pt(e.get('Data'))}"):
                        edit_key = f"edit_mode_{e['_id']}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False

                        if st.session_state[edit_key]:
                            st.markdown("#### ✏️ Editar Evento")
                            with st.form(f"form_edit_{e['_id']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    nome_edit  = st.text_input("Nome do Evento*", value=e.get('Nome do Evento', ''))
                                    data_atual = e.get('Data', '')
                                    try:
                                        data_obj = datetime.strptime(str(data_atual)[:10], '%Y-%m-%d').date() if data_atual else datetime.now().date()
                                    except Exception:
                                        data_obj = datetime.now().date()
                                    data_edit = st.date_input("Data*", value=data_obj)
                                with col2:
                                    hora_edit  = st.text_input("Hora*", value=e.get('Hora', ''))
                                    tipos      = ["Concerto", "Ensaio", "Actuação", "Outro"]
                                    tipo_atual = e.get('Tipo', 'Concerto')
                                    tipo_idx   = tipos.index(tipo_atual) if tipo_atual in tipos else 0
                                    tipo_edit  = st.selectbox("Tipo", tipos, index=tipo_idx)
                                descricao_edit = st.text_area("Descrição", value=e.get('Descricao', ''))
                                cartaz_edit    = st.text_input("URL do Cartaz", value=e.get('Cartaz', ''))

                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    guardar  = st.form_submit_button("💾 Guardar Alterações", use_container_width=True, type="primary")
                                with col_cancel:
                                    cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

                                if guardar:
                                    if not nome_edit or not hora_edit:
                                        st.error("⚠️ Preencha todos os campos obrigatórios")
                                    else:
                                        try:
                                            base.update_row("Eventos", e['_id'], {
                                                "Nome do Evento": nome_edit,
                                                "Data":           str(data_edit),
                                                "Hora":           hora_edit,
                                                "Tipo":           tipo_edit,
                                                "Descricao":      descricao_edit,
                                                "Cartaz":         cartaz_edit
                                            })
                                            st.session_state[edit_key] = False
                                            st.success("✅ Evento atualizado!")
                                            st.rerun()
                                        except Exception as e_edit:
                                            st.error(f"❌ Erro ao guardar: {e_edit}")
                                if cancelar:
                                    st.session_state[edit_key] = False
                                    st.rerun()

                        else:
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.write(f"**Data:** {formatar_data_pt(e.get('Data'))}")
                                st.write(f"**Hora:** {e.get('Hora', '---')}")
                                st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")
                                if e.get('Descricao'):
                                    st.write(f"**Descrição:** {e.get('Descricao')}")
                            with col2:
                                pres_evento = [p for p in presencas if p.get('EventoID') == e['_id']]
                                vao      = len([p for p in pres_evento if p.get('Resposta') == 'Vou'])
                                nao_vao  = len([p for p in pres_evento if p.get('Resposta') == 'Não Vou'])
                                talvez   = len([p for p in pres_evento if p.get('Resposta') == 'Talvez'])
                                pendentes = len(musicos) - len(pres_evento)
                                st.metric("✅ Confirmados", vao)
                                st.caption(f"❌ Não Vão: {nao_vao} | ❓ Talvez: {talvez} | ⏳ Pendentes: {pendentes}")
                            with col3:
                                if st.button("✏️ Editar", key=f"btn_edit_{e['_id']}", use_container_width=True):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                                if st.button("🗑️ Apagar", key=f"del_ev_{e['_id']}", type="secondary", use_container_width=True):
                                    try:
                                        base.delete_row("Eventos", e['_id'])
                                        st.success("Evento removido!")
                                        st.rerun()
                                    except Exception as e_error:
                                        st.error(f"Erro: {e_error}")

                            st.divider()

                            if musicos:
                                st.subheader("🎼 Presenças por Músico")
                                pres_evento     = [p for p in presencas if p.get('EventoID') == e['_id']]
                                respostas_dict  = {}
                                for p in pres_evento:
                                    username_p = p.get('Username')
                                    if username_p:
                                        respostas_dict[str(username_p).lower().strip()] = p.get('Resposta')

                                lista_musicos = []
                                for m in musicos:
                                    username_raw  = m.get('Username')
                                    username      = str(username_raw).lower().strip() if username_raw and str(username_raw).strip() else str(m.get('Nome', '')).lower().strip()
                                    instrumento_raw = m.get('Instrumento')
                                    instrumento   = str(instrumento_raw).strip() if instrumento_raw and str(instrumento_raw).strip() else "Não definido"
                                    lista_musicos.append({
                                        'Nome':       m.get('Nome', 'Desconhecido'),
                                        'Instrumento': instrumento,
                                        'Resposta':   respostas_dict.get(username, 'Pendente')
                                    })

                                df_musicos = pd.DataFrame(lista_musicos).sort_values(['Instrumento', 'Nome'])

                                col_filtro1, col_filtro2 = st.columns([2, 2])
                                with col_filtro1:
                                    filtro_resposta = st.multiselect(
                                        "Filtrar por resposta:",
                                        options=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                        default=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                        key=f"filtro_resp_{e['_id']}"
                                    )
                                with col_filtro2:
                                    inst_def   = df_musicos[df_musicos['Instrumento'] != 'Não definido']
                                    num_naipes = len(inst_def['Instrumento'].unique()) if not inst_def.empty else 0
                                    st.caption(f"📊 Naipes definidos: {num_naipes}")

                                df_filtrado = df_musicos[df_musicos['Resposta'].isin(filtro_resposta)].copy()

                                def add_emoji(r):
                                    return {'Vou': '✅ Vou', 'Não Vou': '❌ Não Vou', 'Talvez': '❓ Talvez'}.get(r, '⏳ Pendente')

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
                                        st.dataframe(df_naipes, use_container_width=True, hide_index=True)
                                        naipes_vazios = df_naipes[df_naipes['✅ Vão'] == 0]['Naipe'].tolist()
                                        if naipes_vazios:
                                            st.warning(f"⚠️ Naipes sem confirmações: {', '.join(naipes_vazios)}")
                                else:
                                    st.info("ℹ️ Os músicos ainda não têm instrumentos definidos.")
                            else:
                                st.info("Nenhum músico registado no sistema")

        except Exception as e:
            st.error(f"❌ Erro ao carregar eventos: {str(e)}")

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
                if 'Instrumento' in df_mus.columns:
                    col1, col2, col3 = st.columns(3)
                    total_inst = df_mus['Instrumento'].notna().sum()
                    proprios   = df_mus['Instrumento Proprio'].sum() if 'Instrumento Proprio' in df_mus.columns else 0
                    col1.metric("Total Instrumentos", total_inst)
                    col2.metric("Próprios", proprios)
                    col3.metric("Da Banda", total_inst - proprios)
                    st.divider()
                    colunas_mostrar    = ['Nome', 'Instrumento', 'Marca', 'Modelo', 'Num Serie']
                    colunas_existentes = [c for c in colunas_mostrar if c in df_mus.columns]
                    if colunas_existentes:
                        st.dataframe(df_mus[colunas_existentes], use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Ainda não há dados de instrumentos.")
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
                col1, col2 = st.columns(2)
                col1.metric("Total de Alunos", len(df_aulas))
                col2.metric("Professores Ativos", df_aulas['Professor'].nunique() if 'Professor' in df_aulas.columns else 0)
                st.divider()
                colunas_existentes = [c for c in ['Professor', 'Aluno', 'DiaHora', 'Sala'] if c in df_aulas.columns]
                if colunas_existentes:
                    st.dataframe(df_aulas[colunas_existentes], use_container_width=True, hide_index=True)
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
                    campos = sum([bool(m.get('Telefone')), bool(m.get('Email')), bool(m.get('Morada'))])
                    status_list.append({
                        "Nome":        m.get('Nome', '---'),
                        "📞 Telefone": "✅" if m.get('Telefone') else "❌",
                        "📧 Email":    "✅" if m.get('Email')    else "❌",
                        "🏠 Morada":   "✅" if m.get('Morada')   else "❌",
                        "Completude":  f"{int((campos / 3) * 100)}%"
                    })
                df_status = pd.DataFrame(status_list)
                completos = len([s for s in status_list if s["Completude"] == "100%"])
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Músicos",     len(status_list))
                col2.metric("✅ Fichas Completas", completos)
                col3.metric("⚠️ Incompletas",     len(status_list) - completos)
                st.divider()
                st.dataframe(df_status, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erro: {e}")

    # ========================================
    # TAB 5: MENSAGENS
    # ========================================
    with t5:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=True)

    # ========================================
    # TAB 6: ANIVERSÁRIOS
    # ========================================
    with t6:
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

    # ========================================
    # TAB 7: GESTÃO DE UTILIZADORES
    # ========================================
    with t7:
        st.subheader("👥 Gestão de Utilizadores")
        st.info("🔧 Ferramentas para manter a tabela de utilizadores sincronizada e limpa")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧹 Limpar Duplicados")
            st.write("Remove utilizadores duplicados, mantendo a versão com password encriptada.")
            if st.button("🧹 Limpar Duplicados", type="primary", use_container_width=True):
                with st.spinner("A remover duplicados..."):
                    from user_sync import limpar_duplicados_utilizadores
                    resultado = limpar_duplicados_utilizadores(base)
                    if resultado["erro"]:
                        st.error(f"❌ Erro: {resultado['erro']}")
                    elif resultado["removidos"] > 0:
                        st.success(f"✅ {resultado['removidos']} utilizador(es) duplicado(s) removido(s)!")
                        st.rerun()
                    else:
                        st.info("✨ Nenhum duplicado encontrado!")
        with col2:
            st.markdown("### 🔄 Sincronizar Músicos")
            st.write("Cria utilizadores para músicos que ainda não têm conta (password: 1234).")
            if st.button("🔄 Sincronizar Músicos", type="secondary", use_container_width=True):
                with st.spinner("A criar novos utilizadores..."):
                    from user_sync import sincronizar_novos_utilizadores
                    resultado = sincronizar_novos_utilizadores(base)
                    if resultado["erro"]:
                        st.warning(f"⚠️ {resultado['criados']} criado(s). Erros: {resultado['erro']}")
                    elif resultado["criados"] > 0:
                        st.success(f"✅ {resultado['criados']} novo(s) utilizador(es) criado(s)!")
                        st.rerun()
                    else:
                        st.info("✨ Todos os músicos já têm conta!")
        st.divider()
        st.markdown("### 📋 Lista de Utilizadores")
        try:
            utilizadores = base.list_rows("Utilizadores")
            if not utilizadores:
                st.info("📭 Nenhum utilizador registado")
            else:
                users_list = []
                for u in utilizadores:
                    password = str(u.get('Password', ''))
                    if password.startswith('$2b$'):
                        status_pass = "🔒 Encriptada"
                    elif password == "1234":
                        status_pass = "⚠️ Padrão (1234)"
                    else:
                        status_pass = "❓ Desconhecida"
                    users_list.append({
                        "Nome":     u.get('Nome', '---'),
                        "Username": u.get('Username', '---'),
                        "Função":   u.get('Funcao', '---'),
                        "Password": status_pass
                    })
                df_users = pd.DataFrame(users_list)
                col1, col2, col3 = st.columns(3)
                col1.metric("Total", len(users_list))
                encriptadas = len([u for u in users_list if u["Password"] == "🔒 Encriptada"])
                col2.metric("🔒 Encriptadas", encriptadas)
                padrao = len([u for u in users_list if u["Password"] == "⚠️ Padrão (1234)"])
                col3.metric("⚠️ Padrão", padrao)
                st.divider()
                st.dataframe(
                    df_users, use_container_width=True, hide_index=True,
                    column_config={
                        "Nome":     st.column_config.TextColumn("👤 Nome",     width="large"),
                        "Username": st.column_config.TextColumn("🔑 Username", width="medium"),
                        "Função":   st.column_config.TextColumn("🎭 Função",   width="small"),
                        "Password": st.column_config.TextColumn("🔐 Password", width="medium")
                    }
                )
                if padrao > 0:
                    st.warning(f"⚠️ **Atenção:** {padrao} utilizador(es) ainda têm password padrão (1234).")
                st.divider()
                st.markdown("### 🔄 Resetar Password de Utilizador")
                st.caption("A nova password será '1234' e o utilizador será obrigado a mudá-la no próximo login.")
                col_reset1, col_reset2 = st.columns([3, 1])
                with col_reset1:
                    users_nomes    = [f"{u.get('Nome')} ({u.get('Username')})" for u in utilizadores]
                    user_selecionado = st.selectbox(
                        "Selecione o utilizador:",
                        options=range(len(utilizadores)),
                        format_func=lambda i: users_nomes[i],
                        key="select_reset_user"
                    )
                with col_reset2:
                    if st.button("🔄 Resetar para 1234", type="secondary", use_container_width=True):
                        try:
                            user_row = utilizadores[user_selecionado]
                            base.update_row("Utilizadores", user_row['_id'], {"Password": "1234"})
                            st.success(f"✅ Password de **{user_row.get('Nome')}** resetada para '1234'!")
                            st.info("💡 O utilizador será obrigado a mudar a password no próximo login.")
                            st.rerun()
                        except Exception as e_reset:
                            st.error(f"❌ Erro ao resetar password: {e_reset}")
        except Exception as e:
            st.error(f"Erro ao carregar utilizadores: {e}")

    # ========================================
    # TAB 8: GESTÃO DE MÚSICOS
    # ========================================
    with t8:
        st.subheader("👤 Gestão de Músicos")
        st.info("➕ Adicione, edite ou arquive músicos sem precisar aceder às tabelas diretamente.")

        with st.expander("➕ Adicionar Novo Músico", expanded=False):
            with st.form("form_novo_musico"):
                st.markdown("#### Dados Pessoais")
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome      = st.text_input("Nome Completo*", placeholder="Ex: João Silva")
                    novo_telefone  = st.text_input("Telefone", placeholder="Ex: 912345678")
                    novo_email     = st.text_input("Email", placeholder="Ex: joao@email.com")
                    novo_morada    = st.text_input("Morada", placeholder="Ex: Lisboa")
                with col2:
                    novo_nascimento = st.date_input(
                        "Data de Nascimento",
                        value=None,
                        min_value=datetime(1920, 1, 1).date(),
                        max_value=datetime.now().date()
                    )
                    novo_ingresso = st.date_input(
                        "Data de Ingresso na Banda",
                        value=datetime.now().date(),
                        min_value=datetime(1900, 1, 1).date(),
                        max_value=datetime.now().date()
                    )
                    novo_instrumento = st.text_input("Instrumento", placeholder="Ex: Clarinete")
                    novo_obs         = st.text_area("Observações", placeholder="Notas adicionais...", height=80)

                st.markdown("---")
                if st.form_submit_button("✅ Adicionar Músico", use_container_width=True, type="primary"):
                    if not novo_nome.strip():
                        st.error("⚠️ O nome é obrigatório")
                    else:
                        try:
                            dados_musico = {
                                "Nome":        novo_nome.strip(),
                                "Telefone":    novo_telefone.strip()  if novo_telefone  else "",
                                "Email":       novo_email.strip()     if novo_email     else "",
                                "Morada":      novo_morada.strip()    if novo_morada    else "",
                                "Instrumento": novo_instrumento.strip() if novo_instrumento else "",
                                "Obs":         novo_obs.strip()       if novo_obs       else "",
                            }
                            if novo_nascimento:
                                dados_musico["Data de Nascimento"]  = str(novo_nascimento)
                            if novo_ingresso:
                                dados_musico["Data Ingresso Banda"] = str(novo_ingresso)
                            base.append_row("Musicos", dados_musico)
                            st.success(f"✅ Músico **{novo_nome}** adicionado com sucesso!")
                            st.info("💡 Lembra-te de ir a **Utilizadores → Sincronizar Músicos** para criar a conta de acesso.")
                            st.rerun()
                        except Exception as e_add:
                            st.error(f"❌ Erro ao adicionar músico: {e_add}")

        st.divider()

        try:
            musicos = base.list_rows("Musicos")
            if not musicos:
                st.info("📭 Nenhum músico registado")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("👥 Total de Músicos", len(musicos))
                com_instrumento = len([m for m in musicos if m.get('Instrumento')])
                col2.metric("🎷 Com Instrumento", com_instrumento)
                col3.metric("⚠️ Sem Instrumento", len(musicos) - com_instrumento)

                st.divider()

                pesquisa = st.text_input("🔍 Pesquisar músico", placeholder="Nome ou instrumento...")
                musicos_filtrados = musicos
                if pesquisa.strip():
                    termo = pesquisa.strip().lower()
                    musicos_filtrados = [
                        m for m in musicos
                        if termo in str(m.get('Nome', '')).lower()
                        or termo in str(m.get('Instrumento', '')).lower()
                    ]

                st.caption(f"A mostrar {len(musicos_filtrados)} de {len(musicos)} músicos")
                st.divider()

                for m in musicos_filtrados:
                    musico_nome = m.get('Nome', 'Sem nome')
                    musico_inst = m.get('Instrumento', '---')

                    with st.expander(f"🎵 {musico_nome} — {musico_inst}"):
                        edit_key_m = f"edit_musico_{m['_id']}"
                        if edit_key_m not in st.session_state:
                            st.session_state[edit_key_m] = False

                        if st.session_state[edit_key_m]:
                            st.markdown("#### ✏️ Editar Músico")
                            with st.form(f"form_edit_musico_{m['_id']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_nome     = st.text_input("Nome Completo*", value=m.get('Nome', ''))
                                    edit_telefone = st.text_input("Telefone", value=str(m.get('Telefone', '') or ''))
                                    edit_email    = st.text_input("Email",    value=str(m.get('Email', '')    or ''))
                                    edit_morada   = st.text_input("Morada",   value=str(m.get('Morada', '')   or ''))
                                with col2:
                                    nasc_raw = m.get('Data de Nascimento')
                                    try:
                                        nasc_val = datetime.strptime(str(nasc_raw)[:10], '%Y-%m-%d').date() if nasc_raw else None
                                    except Exception:
                                        nasc_val = None
                                    edit_nasc = st.date_input(
                                        "Data de Nascimento",
                                        value=nasc_val,
                                        min_value=datetime(1920, 1, 1).date(),
                                        max_value=datetime.now().date()
                                    )
                                    ing_raw = m.get('Data Ingresso Banda')
                                    try:
                                        ing_val = datetime.strptime(str(ing_raw)[:10], '%Y-%m-%d').date() if ing_raw else datetime.now().date()
                                    except Exception:
                                        ing_val = datetime.now().date()
                                    edit_ingresso    = st.date_input(
                                        "Data de Ingresso",
                                        value=ing_val,
                                        min_value=datetime(1900, 1, 1).date(),
                                        max_value=datetime.now().date()
                                    )
                                    edit_instrumento = st.text_input("Instrumento",  value=str(m.get('Instrumento', '') or ''))
                                    edit_obs         = st.text_area("Observações",   value=str(m.get('Obs', '')         or ''), height=80)

                                col_s, col_c = st.columns(2)
                                with col_s:
                                    guardar_m  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                                with col_c:
                                    cancelar_m = st.form_submit_button("❌ Cancelar", use_container_width=True)

                                if guardar_m:
                                    if not edit_nome.strip():
                                        st.error("⚠️ O nome é obrigatório")
                                    else:
                                        try:
                                            base.update_row("Musicos", m['_id'], {
                                                "Nome":               edit_nome.strip(),
                                                "Telefone":           edit_telefone.strip(),
                                                "Email":              edit_email.strip(),
                                                "Morada":             edit_morada.strip(),
                                                "Instrumento":        edit_instrumento.strip(),
                                                "Obs":                edit_obs.strip(),
                                                "Data de Nascimento": str(edit_nasc)    if edit_nasc    else "",
                                                "Data Ingresso Banda": str(edit_ingresso) if edit_ingresso else "",
                                            })
                                            st.session_state[edit_key_m] = False
                                            st.success("✅ Músico atualizado!")
                                            st.rerun()
                                        except Exception as e_upd:
                                            st.error(f"❌ Erro: {e_upd}")
                                if cancelar_m:
                                    st.session_state[edit_key_m] = False
                                    st.rerun()

                        else:
                            col1, col2, col3 = st.columns([3, 3, 1])
                            with col1:
                                st.write(f"**📞 Telefone:** {m.get('Telefone') or '---'}")
                                st.write(f"**📧 Email:** {m.get('Email') or '---'}")
                                st.write(f"**🏠 Morada:** {m.get('Morada') or '---'}")
                            with col2:
                                nasc = converter_data_robusta(m.get('Data de Nascimento'))
                                ing  = converter_data_robusta(m.get('Data Ingresso Banda'))
                                st.write(f"**🎂 Nascimento:** {formatar_data_pt(str(nasc)) if nasc else '---'}")
                                st.write(f"**📅 Ingresso:** {formatar_data_pt(str(ing)) if ing else '---'}")
                                st.write(f"**🎷 Instrumento:** {m.get('Instrumento') or '---'}")
                                if m.get('Obs'):
                                    st.write(f"**📝 Obs:** {m.get('Obs')}")
                            with col3:
                                if st.button("✏️ Editar", key=f"btn_edit_m_{m['_id']}", use_container_width=True):
                                    st.session_state[edit_key_m] = True
                                    st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao carregar músicos: {str(e)}")
