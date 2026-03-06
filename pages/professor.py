"""
Interface do Professor - Portal BMO
"""
import streamlit as st
import pandas as pd

def render(base, user):
    """Renderiza interface do professor"""
    st.title("👨‍🏫 Área do Professor")
    st.caption(f"Bem-vindo(a), **{user['display_name']}**")

    t1, t2 = st.tabs([
        "📚 Os Meus Alunos",
        "➕ Adicionar Aluno"
    ])

    # ========================================
    # CARREGAR DADOS (partilhado entre tabs)
    # ========================================
    try:
        aulas_raw = base.list_rows("Aulas")
        alunos_raw = base.list_rows("Alunos")
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return

    # DataFrame de todos os alunos da escola (tabela Alunos)
    df_alunos = pd.DataFrame(alunos_raw) if alunos_raw else pd.DataFrame()

    # Filtrar aulas APENAS deste professor
    df_aulas = pd.DataFrame(aulas_raw) if aulas_raw else pd.DataFrame()
    if not df_aulas.empty and 'Professor' in df_aulas.columns:
        minhas_aulas = df_aulas[df_aulas['Professor'] == user['display_name']].copy()
    else:
        minhas_aulas = pd.DataFrame()

    # ========================================
    # TAB 1: OS MEUS ALUNOS
    # ========================================
    with t1:
        st.subheader("📚 Os Meus Alunos")

        if minhas_aulas.empty:
            st.info("📭 Ainda não tem alunos atribuídos. Use a aba **➕ Adicionar Aluno** para começar.")
        else:
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("👥 Total de Alunos", len(minhas_aulas))

            if 'Local' in minhas_aulas.columns:
                locais = minhas_aulas['Local'].value_counts()
                col2.metric("📍 Local mais frequente", locais.index[0] if not locais.empty else "---")

            recorrentes = 0
            if 'Recorrente' in minhas_aulas.columns:
                recorrentes = int(minhas_aulas['Recorrente'].sum()) if minhas_aulas['Recorrente'].dtype == bool else minhas_aulas['Recorrente'].astype(str).str.lower().isin(['true','1','yes']).sum()
            col3.metric("🔁 Aulas Recorrentes", recorrentes)

            st.divider()

            # Para cada aula, cruzar com tabela Alunos para obter contactos
            for _, aula in minhas_aulas.iterrows():
                nome_aluno = aula.get('Aluno', 'Sem nome')
                hora = aula.get('Hora', '---')
                sala = aula.get('Sala', '---')
                local = aula.get('Local', '---')
                dia = aula.get('Dia da Semana', '')
                recorrente = aula.get('Recorrente', False)
                data_aula = aula.get('Data Aula', '')

                # Horário formatado
                if dia and str(dia).strip():
                    horario_str = f"{dia} {hora}"
                elif data_aula and str(data_aula).strip():
                    horario_str = f"{str(data_aula)[:10]} {hora}"
                else:
                    horario_str = hora

                # Buscar dados de contacto na tabela Alunos
                telefone = "---"
                email = "---"
                if not df_alunos.empty and 'Nome' in df_alunos.columns:
                    match_aluno = df_alunos[df_alunos['Nome'] == nome_aluno]
                    if not match_aluno.empty:
                        aluno_data = match_aluno.iloc[0]
                        telefone = str(aluno_data.get('Telefone', '') or '---').strip() or '---'
                        email = str(aluno_data.get('Email', '') or '---').strip() or '---'

                with st.expander(f"🎵 {nome_aluno} — {horario_str} | {local}"):
                    col_info, col_contacto, col_acao = st.columns([3, 3, 1])

                    with col_info:
                        st.markdown("**📅 Horário**")
                        st.write(f"🕐 **Hora:** {hora}")
                        if dia and str(dia).strip():
                            st.write(f"📆 **Dia:** {dia}")
                        if data_aula and str(data_aula).strip():
                            st.write(f"📅 **Data:** {str(data_aula)[:10]}")
                        st.write(f"🏫 **Sala:** {sala}")
                        st.write(f"📍 **Local:** {local}")
                        st.write(f"🔁 **Recorrente:** {'Sim' if recorrente else 'Não'}")

                    with col_contacto:
                        st.markdown("**📞 Contacto do Aluno**")
                        st.write(f"📞 **Telefone:** {telefone}")
                        st.write(f"📧 **Email:** {email}")
                        # Contacto extra que possa estar em Aulas
                        contacto_aula = str(aula.get('Contacto', '') or '').strip()
                        if contacto_aula and contacto_aula != '---':
                            st.write(f"📱 **Contacto (aula):** {contacto_aula}")

                    with col_acao:
                        st.markdown("**⚙️ Ações**")
                        row_id = aula.get('_id')
                        confirm_key = f"confirm_remove_{row_id}"

                        if st.session_state.get(confirm_key, False):
                            st.warning("Tens a certeza?")
                            if st.button("✅ Sim, remover", key=f"yes_{row_id}", use_container_width=True, type="primary"):
                                try:
                                    base.delete_row("Aulas", row_id)
                                    st.session_state.pop(confirm_key, None)
                                    st.success(f"✅ **{nome_aluno}** removido das tuas aulas!")
                                    st.rerun()
                                except Exception as e_del:
                                    st.error(f"❌ Erro: {e_del}")
                            if st.button("❌ Cancelar", key=f"no_{row_id}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
                        else:
                            if st.button("🗑️ Remover", key=f"rem_{row_id}", use_container_width=True):
                                st.session_state[confirm_key] = True
                                st.rerun()

    # ========================================
    # TAB 2: ADICIONAR ALUNO
    # ========================================
    with t2:
        st.subheader("➕ Adicionar Aluno à Minha Lista")

        if df_alunos.empty:
            st.error("❌ Não foi possível carregar a lista de alunos da escola.")
            return

        if 'Nome' not in df_alunos.columns:
            st.error("❌ A tabela Alunos não tem a coluna 'Nome'.")
            return

        # Lista de alunos já atribuídos a este professor
        nomes_ja_atribuidos = set()
        if not minhas_aulas.empty and 'Aluno' in minhas_aulas.columns:
            nomes_ja_atribuidos = set(minhas_aulas['Aluno'].dropna().tolist())

        # Todos os alunos disponíveis na tabela Alunos
        todos_alunos = df_alunos['Nome'].dropna().sort_values().tolist()

        # Separar em "já atribuídos" vs "disponíveis"
        disponiveis = [n for n in todos_alunos if n not in nomes_ja_atribuidos]
        ja_atribuidos_lista = [n for n in todos_alunos if n in nomes_ja_atribuidos]

        st.info(f"📊 **{len(todos_alunos)}** alunos na escola · **{len(ja_atribuidos_lista)}** já nas tuas aulas · **{len(disponiveis)}** disponíveis")

        if not disponiveis:
            st.success("✅ Todos os alunos da escola já estão nas tuas aulas!")
        else:
            # Pesquisa para filtrar a lista
            pesquisa_aluno = st.text_input("🔍 Pesquisar aluno", placeholder="Escreve parte do nome...")

            if pesquisa_aluno.strip():
                disponiveis_filtrados = [n for n in disponiveis if pesquisa_aluno.strip().lower() in n.lower()]
            else:
                disponiveis_filtrados = disponiveis

            if not disponiveis_filtrados:
                st.warning(f"Nenhum aluno encontrado com '{pesquisa_aluno}'")
            else:
                with st.form("form_add_aluno"):
                    st.markdown("#### 👤 Selecionar Aluno")

                    aluno_escolhido = st.selectbox(
                        "Aluno*",
                        options=disponiveis_filtrados,
                        help="Seleciona o aluno da lista da escola"
                    )

                    # Mostrar dados do aluno selecionado (preview)
                    if aluno_escolhido:
                        match = df_alunos[df_alunos['Nome'] == aluno_escolhido]
                        if not match.empty:
                            a = match.iloc[0]
                            tel = str(a.get('Telefone', '') or '').strip()
                            eml = str(a.get('Email', '') or '').strip()
                            polo = str(a.get('Pólo da escola', '') or '').strip()
                            instr = str(a.get('Instrumento Pretendido', '') or str(a.get('Instrumentos', '') or '')).strip()

                            preview_parts = []
                            if tel: preview_parts.append(f"📞 {tel}")
                            if eml: preview_parts.append(f"📧 {eml}")
                            if polo: preview_parts.append(f"📍 {polo}")
                            if instr: preview_parts.append(f"🎷 {instr}")

                            if preview_parts:
                                st.success("  |  ".join(preview_parts))

                    st.markdown("#### 📅 Dados da Aula")
                    col1, col2 = st.columns(2)

                    with col1:
                        dias_semana = ["", "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                                       "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
                        dia_escolhido = st.selectbox("Dia da Semana", options=dias_semana)
                        hora_aula = st.text_input("Hora*", placeholder="Ex: 16:00")
                        recorrente_check = st.checkbox("🔁 Aula Recorrente", value=True)

                    with col2:
                        local_opcoes = ["Oeiras", "Algés", "Outro"]
                        local_escolhido = st.selectbox("Local", options=local_opcoes)
                        sala_aula = st.text_input("Sala", placeholder="Ex: Sala 3")
                        data_especifica = None
                        if not recorrente_check:
                            data_especifica = st.date_input("Data da Aula")

                    st.caption("* Campos obrigatórios")

                    if st.form_submit_button("✅ Adicionar Aluno", use_container_width=True, type="primary"):
                        if not hora_aula.strip():
                            st.error("⚠️ A hora da aula é obrigatória")
                        else:
                            try:
                                # Buscar contacto do aluno para guardar também em Aulas
                                contacto_aluno = ""
                                match_c = df_alunos[df_alunos['Nome'] == aluno_escolhido]
                                if not match_c.empty:
                                    tel_c = str(match_c.iloc[0].get('Telefone', '') or '').strip()
                                    contacto_aluno = tel_c

                                nova_aula = {
                                    "Professor": user['display_name'],
                                    "Aluno": aluno_escolhido,
                                    "Hora": hora_aula.strip(),
                                    "Sala": sala_aula.strip(),
                                    "Contacto": contacto_aluno,
                                    "Local": local_escolhido,
                                    "Dia da Semana": dia_escolhido if dia_escolhido else "",
                                    "Recorrente": recorrente_check,
                                }
                                if data_especifica and not recorrente_check:
                                    nova_aula["Data Aula"] = str(data_especifica)

                                base.append_row("Aulas", nova_aula)
                                st.success(f"✅ **{aluno_escolhido}** adicionado às tuas aulas!")
                                st.balloons()
                                st.rerun()

                            except Exception as e_add:
                                st.error(f"❌ Erro ao adicionar: {e_add}")

        # Mostrar lista de já atribuídos (informativo)
        if ja_atribuidos_lista:
            st.divider()
            with st.expander(f"ℹ️ Alunos já nas tuas aulas ({len(ja_atribuidos_lista)})"):
                for n in sorted(ja_atribuidos_lista):
                    st.write(f"✅ {n}")
