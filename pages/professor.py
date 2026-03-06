"""
Interface do Professor - Portal BMO
"""
import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date

# ============================================
# CONSTANTES
# ============================================

DIAS_PT_MAP = {
    "Segunda-Feira": 0,
    "Terça-Feira": 1,
    "Quarta-Feira": 2,
    "Quinta-Feira": 3,
    "Sexta-Feira": 4,
    "Sábado": 5,
    "Domingo": 6,
}

MESES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

CORES_PROFESSORES = [
    "#ff6b35", "#4ecdc4", "#45b7d1", "#96ceb4",
    "#dda0dd", "#f39c12", "#bb8fce", "#85c1e9", "#58d68d", "#ec7063"
]

# ============================================
# HELPERS
# ============================================

def _normalizar_recorrente(val):
    if isinstance(val, bool):
        return val
    return str(val).lower() in ['true', '1', 'yes', 'sim']


def _get_aulas_do_mes(df_aulas, ano, mes):
    """Retorna dict {dia: [lista de aulas]} para o mês/ano dado."""
    aulas_por_dia = {}
    if df_aulas.empty:
        return aulas_por_dia

    num_dias = calendar.monthrange(ano, mes)[1]

    for dia in range(1, num_dias + 1):
        data_dia = date(ano, mes, dia)
        weekday = data_dia.weekday()
        aulas_do_dia = []

        for _, aula in df_aulas.iterrows():
            is_recorrente = _normalizar_recorrente(aula.get('Recorrente', False))

            if is_recorrente:
                dia_semana = str(aula.get('Dia da Semana', '') or '').strip()
                if dia_semana in DIAS_PT_MAP and DIAS_PT_MAP[dia_semana] == weekday:
                    aulas_do_dia.append(aula)
            else:
                data_raw = str(aula.get('Data Aula', '') or '').strip()
                if data_raw:
                    try:
                        if datetime.strptime(data_raw[:10], '%Y-%m-%d').date() == data_dia:
                            aulas_do_dia.append(aula)
                    except Exception:
                        pass

        if aulas_do_dia:
            aulas_por_dia[dia] = aulas_do_dia

    return aulas_por_dia


def _verificar_conflitos(df_aulas, hora, local, dia_semana, data_especifica, recorrente):
    """
    Verifica se existe alguma aula com o mesmo horário e local.
    Retorna lista de conflitos encontrados.
    """
    conflitos = []
    if df_aulas.empty:
        return conflitos

    for _, aula in df_aulas.iterrows():
        aula_hora = str(aula.get('Hora', '') or '').strip()
        aula_local = str(aula.get('Local', '') or '').strip()

        # Só interessa conflito no mesmo local e mesma hora
        if aula_hora != hora or aula_local != local:
            continue

        aula_recorrente = _normalizar_recorrente(aula.get('Recorrente', False))

        if recorrente and dia_semana:
            # Nova aula recorrente → conflita com recorrente no mesmo dia
            if aula_recorrente:
                aula_dia = str(aula.get('Dia da Semana', '') or '').strip()
                if aula_dia == dia_semana:
                    conflitos.append({
                        'professor': aula.get('Professor', '---'),
                        'aluno': aula.get('Aluno', '---'),
                        'tipo': f"Recorrente ({aula_dia})",
                        'hora': aula_hora,
                        'local': aula_local
                    })
            else:
                # Conflita com aula específica que cai no mesmo dia da semana
                data_raw = str(aula.get('Data Aula', '') or '').strip()
                if data_raw and dia_semana in DIAS_PT_MAP:
                    try:
                        d = datetime.strptime(data_raw[:10], '%Y-%m-%d').date()
                        if d.weekday() == DIAS_PT_MAP[dia_semana]:
                            conflitos.append({
                                'professor': aula.get('Professor', '---'),
                                'aluno': aula.get('Aluno', '---'),
                                'tipo': f"Data específica {data_raw[:10]}",
                                'hora': aula_hora,
                                'local': aula_local
                            })
                    except Exception:
                        pass
        elif not recorrente and data_especifica:
            data_str = str(data_especifica)
            weekday_nova = data_especifica.weekday()

            if aula_recorrente:
                aula_dia = str(aula.get('Dia da Semana', '') or '').strip()
                if aula_dia in DIAS_PT_MAP and DIAS_PT_MAP[aula_dia] == weekday_nova:
                    conflitos.append({
                        'professor': aula.get('Professor', '---'),
                        'aluno': aula.get('Aluno', '---'),
                        'tipo': f"Recorrente ({aula_dia})",
                        'hora': aula_hora,
                        'local': aula_local
                    })
            else:
                data_raw = str(aula.get('Data Aula', '') or '').strip()
                if data_raw[:10] == data_str[:10]:
                    conflitos.append({
                        'professor': aula.get('Professor', '---'),
                        'aluno': aula.get('Aluno', '---'),
                        'tipo': f"Data específica {data_raw[:10]}",
                        'hora': aula_hora,
                        'local': aula_local
                    })

    return conflitos


def _render_calendario(df_aulas):
    """Renderiza calendário mensal navegável."""
    hoje = date.today()

    if 'cal_ano' not in st.session_state:
        st.session_state['cal_ano'] = hoje.year
    if 'cal_mes' not in st.session_state:
        st.session_state['cal_mes'] = hoje.month

    ano = st.session_state['cal_ano']
    mes = st.session_state['cal_mes']

    # ---- Navegação ----
    col_prev, col_titulo, col_hoje_btn, col_next = st.columns([1, 3, 1, 1])
    with col_prev:
        if st.button("◀ Anterior", use_container_width=True, key="cal_prev"):
            if mes == 1:
                st.session_state['cal_mes'] = 12
                st.session_state['cal_ano'] = ano - 1
            else:
                st.session_state['cal_mes'] = mes - 1
            st.rerun()
    with col_titulo:
        st.markdown(
            f"<h3 style='text-align:center; margin:0; padding:4px 0'>{MESES_PT[mes]} {ano}</h3>",
            unsafe_allow_html=True
        )
    with col_hoje_btn:
        if st.button("📅 Hoje", use_container_width=True, key="cal_hoje"):
            st.session_state['cal_ano'] = hoje.year
            st.session_state['cal_mes'] = hoje.month
            st.rerun()
    with col_next:
        if st.button("Próximo ▶", use_container_width=True, key="cal_next"):
            if mes == 12:
                st.session_state['cal_mes'] = 1
                st.session_state['cal_ano'] = ano + 1
            else:
                st.session_state['cal_mes'] = mes + 1
            st.rerun()

    # ---- Filtros ----
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        locais_disp = ["Todos"]
        if not df_aulas.empty and 'Local' in df_aulas.columns:
            locais_disp += sorted(df_aulas['Local'].dropna().unique().tolist())
        filtro_local = st.selectbox("📍 Filtrar por Local", locais_disp, key="cal_loc")
    with col_f2:
        profs_disp = ["Todos"]
        if not df_aulas.empty and 'Professor' in df_aulas.columns:
            profs_disp += sorted(df_aulas['Professor'].dropna().unique().tolist())
        filtro_prof = st.selectbox("👨‍🏫 Filtrar por Professor", profs_disp, key="cal_prof")

    # Aplicar filtros
    df_fil = df_aulas.copy() if not df_aulas.empty else pd.DataFrame()
    if not df_fil.empty:
        if filtro_local != "Todos" and 'Local' in df_fil.columns:
            df_fil = df_fil[df_fil['Local'] == filtro_local]
        if filtro_prof != "Todos" and 'Professor' in df_fil.columns:
            df_fil = df_fil[df_fil['Professor'] == filtro_prof]

    # Cores por professor
    profs_todos = []
    if not df_aulas.empty and 'Professor' in df_aulas.columns:
        profs_todos = sorted(df_aulas['Professor'].dropna().unique().tolist())
    cores_prof = {p: CORES_PROFESSORES[i % len(CORES_PROFESSORES)] for i, p in enumerate(profs_todos)}

    # Aulas por dia
    aulas_por_dia = _get_aulas_do_mes(df_fil, ano, mes)

    # ---- CSS do calendário ----
    css = """
    <style>
    .bmo-cal { width:100%; border-collapse:collapse; table-layout:fixed; margin-top:8px; }
    .bmo-cal th {
        background:#ff6b35; color:white; padding:8px 4px;
        text-align:center; font-weight:bold; font-size:0.82rem;
    }
    .bmo-cal td {
        border:1px solid #ddd; padding:4px; vertical-align:top;
        height:85px; width:14.28%; font-size:0.75rem; background:#fff;
    }
    .bmo-cal td.vazio { background:#f5f5f5; }
    .bmo-cal td.e-hoje { background:#fff8f5; border:2px solid #ff6b35 !important; }
    .bmo-cal td.fim-semana { background:#fafafa; }
    .cal-num { font-weight:bold; font-size:0.88rem; color:#555; margin-bottom:2px; }
    .cal-num-hoje { color:#ff6b35; font-size:0.95rem; }
    .aula-pill {
        display:block; padding:2px 5px; margin:1px 0;
        border-radius:4px; font-size:0.68rem; color:white;
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .bmo-legenda { display:flex; flex-wrap:wrap; gap:10px; margin:8px 0 4px 0; }
    .bmo-leg-item { display:flex; align-items:center; gap:5px; font-size:0.8rem; }
    .bmo-leg-dot { width:11px; height:11px; border-radius:50%; display:inline-block; flex-shrink:0; }
    </style>
    """

    # ---- Legenda ----
    leg_html = '<div class="bmo-legenda">'
    for prof, cor in cores_prof.items():
        leg_html += f'<div class="bmo-leg-item"><span class="bmo-leg-dot" style="background:{cor}"></span>{prof}</div>'
    leg_html += '</div>'

    # ---- Tabela ----
    cal_matrix = calendar.monthcalendar(ano, mes)
    dias_header = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    html = css + leg_html + '<table class="bmo-cal"><thead><tr>'
    for d in dias_header:
        html += f'<th>{d}</th>'
    html += '</tr></thead><tbody>'

    for semana in cal_matrix:
        html += '<tr>'
        for idx, dia in enumerate(semana):
            if dia == 0:
                html += '<td class="vazio"></td>'
            else:
                data_celula = date(ano, mes, dia)
                is_hoje = (data_celula == hoje)
                is_fds = idx >= 5
                classes_td = []
                if is_hoje:
                    classes_td.append('e-hoje')
                elif is_fds:
                    classes_td.append('fim-semana')
                td_class = ' '.join(classes_td)
                html += f'<td class="{td_class}">'
                num_class = 'cal-num-hoje' if is_hoje else 'cal-num'
                html += f'<div class="{num_class}">{dia}</div>'

                if dia in aulas_por_dia:
                    for aula in sorted(aulas_por_dia[dia], key=lambda a: str(a.get('Hora', ''))):
                        prof = str(aula.get('Professor', '') or '')
                        aluno = str(aula.get('Aluno', '') or '')
                        hora = str(aula.get('Hora', '') or '')
                        local = str(aula.get('Local', '') or '')
                        cor = cores_prof.get(prof, '#888888')
                        tooltip = f"{hora} | {aluno} | {prof} | {local}"
                        html += f'<span class="aula-pill" style="background:{cor}" title="{tooltip}">{hora} {aluno[:12]}</span>'

                html += '</td>'
        html += '</tr>'

    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # ---- Métricas do mês ----
    st.divider()
    total_ocorrencias = sum(len(v) for v in aulas_por_dia.values())
    dias_com_aulas = len(aulas_por_dia)

    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Dias com aulas", dias_com_aulas)
    col2.metric("🎵 Ocorrências no mês", total_ocorrencias)
    if aulas_por_dia:
        dia_cheio = max(aulas_por_dia, key=lambda d: len(aulas_por_dia[d]))
        col3.metric("🔥 Dia mais ocupado", f"{dia_cheio} {MESES_PT[mes][:3]}")

    # ---- Detalhe por dia ----
    st.divider()
    st.markdown("#### 🔍 Detalhe de um Dia")

    dias_lista = sorted(aulas_por_dia.keys())
    if not dias_lista:
        st.info("Nenhuma aula encontrada neste mês com os filtros selecionados.")
    else:
        dia_sel = st.selectbox(
            "Selecionar dia:",
            options=dias_lista,
            format_func=lambda d: f"{d} de {MESES_PT[mes]} — {len(aulas_por_dia[d])} aula(s)",
            key="cal_dia_detalhe"
        )
        if dia_sel:
            aulas_sel = sorted(aulas_por_dia[dia_sel], key=lambda a: str(a.get('Hora', '')))
            for aula in aulas_sel:
                prof = aula.get('Professor', '---')
                cor = cores_prof.get(prof, '#888')
                st.markdown(
                    f"<div style='border-left:4px solid {cor}; padding:6px 10px; margin:4px 0; background:#fafafa; border-radius:0 6px 6px 0'>"
                    f"🕐 <b>{aula.get('Hora','---')}</b> &nbsp;|&nbsp; "
                    f"👤 {aula.get('Aluno','---')} &nbsp;|&nbsp; "
                    f"👨‍🏫 {prof} &nbsp;|&nbsp; "
                    f"📍 {aula.get('Local','---')} &nbsp;|&nbsp; "
                    f"🏫 {aula.get('Sala','---')}"
                    f"</div>",
                    unsafe_allow_html=True
                )


# ============================================
# RENDER PRINCIPAL
# ============================================

def render(base, user):
    """Renderiza interface do professor"""
    st.title("👨‍🏫 Área do Professor")
    st.caption(f"Bem-vindo(a), **{user['display_name']}**")

    t1, t2, t3 = st.tabs([
        "📚 Os Meus Alunos",
        "➕ Adicionar Aluno",
        "📅 Calendário"
    ])

    # ========================================
    # CARREGAR DADOS
    # ========================================
    try:
        aulas_raw = base.list_rows("Aulas")
        alunos_raw = base.list_rows("Alunos")
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return

    df_alunos = pd.DataFrame(alunos_raw) if alunos_raw else pd.DataFrame()
    df_aulas_todas = pd.DataFrame(aulas_raw) if aulas_raw else pd.DataFrame()

    if not df_aulas_todas.empty and 'Professor' in df_aulas_todas.columns:
        minhas_aulas = df_aulas_todas[df_aulas_todas['Professor'] == user['display_name']].copy()
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
            col1, col2, col3 = st.columns(3)
            col1.metric("👥 Total de Alunos", len(minhas_aulas))

            if 'Local' in minhas_aulas.columns:
                locais = minhas_aulas['Local'].value_counts()
                col2.metric("📍 Local mais frequente", locais.index[0] if not locais.empty else "---")

            recorrentes = 0
            if 'Recorrente' in minhas_aulas.columns:
                recorrentes = minhas_aulas['Recorrente'].apply(_normalizar_recorrente).sum()
            col3.metric("🔁 Aulas Recorrentes", int(recorrentes))

            st.divider()

            for _, aula in minhas_aulas.iterrows():
                nome_aluno = aula.get('Aluno', 'Sem nome')
                hora = aula.get('Hora', '---')
                sala = aula.get('Sala', '---')
                local = aula.get('Local', '---')
                dia = aula.get('Dia da Semana', '')
                recorrente = _normalizar_recorrente(aula.get('Recorrente', False))
                data_aula = aula.get('Data Aula', '')

                if dia and str(dia).strip():
                    horario_str = f"{dia} {hora}"
                elif data_aula and str(data_aula).strip():
                    horario_str = f"{str(data_aula)[:10]} {hora}"
                else:
                    horario_str = hora

                telefone, email = "---", "---"
                if not df_alunos.empty and 'Nome' in df_alunos.columns:
                    match = df_alunos[df_alunos['Nome'] == nome_aluno]
                    if not match.empty:
                        a = match.iloc[0]
                        telefone = str(a.get('Telefone', '') or '---').strip() or '---'
                        email = str(a.get('Email', '') or '---').strip() or '---'

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
                        contacto_aula = str(aula.get('Contacto', '') or '').strip()
                        if contacto_aula and contacto_aula != '---':
                            st.write(f"📱 **Contacto (aula):** {contacto_aula}")

                    with col_acao:
                        st.markdown("**⚙️ Ações**")
                        row_id = aula.get('_id')
                        confirm_key = f"confirm_remove_{row_id}"

                        if st.session_state.get(confirm_key, False):
                            st.warning("Tens a certeza?")
                            if st.button("✅ Sim", key=f"yes_{row_id}", use_container_width=True, type="primary"):
                                try:
                                    base.delete_row("Aulas", row_id)
                                    st.session_state.pop(confirm_key, None)
                                    st.success(f"✅ **{nome_aluno}** removido!")
                                    st.rerun()
                                except Exception as e_del:
                                    st.error(f"❌ Erro: {e_del}")
                            if st.button("❌ Não", key=f"no_{row_id}", use_container_width=True):
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

        if df_alunos.empty or 'Nome' not in df_alunos.columns:
            st.error("❌ Não foi possível carregar a lista de alunos da escola.")
            return

        nomes_ja_atribuidos = set()
        if not minhas_aulas.empty and 'Aluno' in minhas_aulas.columns:
            nomes_ja_atribuidos = set(minhas_aulas['Aluno'].dropna().tolist())

        todos_alunos = df_alunos['Nome'].dropna().sort_values().tolist()
        disponiveis = [n for n in todos_alunos if n not in nomes_ja_atribuidos]
        ja_atribuidos_lista = [n for n in todos_alunos if n in nomes_ja_atribuidos]

        st.info(f"📊 **{len(todos_alunos)}** alunos na escola · **{len(ja_atribuidos_lista)}** já nas tuas aulas · **{len(disponiveis)}** disponíveis")

        # ----------------------------------------
        # CONFIRMAÇÃO DE CONFLITO (fora do form)
        # ----------------------------------------
        if st.session_state.get('conflito_pendente', False):
            nova_aula = st.session_state.get('aula_pendente', {})
            conflitos = st.session_state.get('conflitos_info', [])

            st.error("⚠️ **Conflito de horário detectado!**")
            st.markdown("As seguintes aulas já existem neste horário e local:")

            for c in conflitos:
                st.markdown(
                    f"- 🕐 **{c['hora']}** | 📍 **{c['local']}** | "
                    f"👨‍🏫 {c['professor']} | 👤 {c['aluno']} | 📆 {c['tipo']}"
                )

            st.warning("Podes ter aulas sobrepostas — tens a certeza que queres continuar?")

            col_sim, col_nao = st.columns(2)
            with col_sim:
                if st.button("✅ Sim, confirmar mesmo assim", type="primary", use_container_width=True):
                    try:
                        base.append_row("Aulas", nova_aula)
                        st.session_state['conflito_pendente'] = False
                        st.session_state.pop('aula_pendente', None)
                        st.session_state.pop('conflitos_info', None)
                        st.success(f"✅ **{nova_aula.get('Aluno')}** adicionado com sucesso!")
                        st.balloons()
                        st.rerun()
                    except Exception as e_save:
                        st.error(f"❌ Erro ao guardar: {e_save}")
            with col_nao:
                if st.button("❌ Cancelar e escolher outro horário", use_container_width=True):
                    st.session_state['conflito_pendente'] = False
                    st.session_state.pop('aula_pendente', None)
                    st.session_state.pop('conflitos_info', None)
                    st.rerun()

            st.stop()

        # ----------------------------------------
        # FORMULÁRIO
        # ----------------------------------------
        if not disponiveis:
            st.success("✅ Todos os alunos da escola já estão nas tuas aulas!")
        else:
            pesquisa_aluno = st.text_input("🔍 Pesquisar aluno", placeholder="Escreve parte do nome...")
            disponiveis_filtrados = (
                [n for n in disponiveis if pesquisa_aluno.strip().lower() in n.lower()]
                if pesquisa_aluno.strip() else disponiveis
            )

            if not disponiveis_filtrados:
                st.warning(f"Nenhum aluno encontrado com '{pesquisa_aluno}'")
            else:
                with st.form("form_add_aluno"):
                    st.markdown("#### 👤 Selecionar Aluno")
                    aluno_escolhido = st.selectbox("Aluno*", options=disponiveis_filtrados)

                    if aluno_escolhido:
                        match = df_alunos[df_alunos['Nome'] == aluno_escolhido]
                        if not match.empty:
                            a = match.iloc[0]
                            parts = []
                            tel = str(a.get('Telefone', '') or '').strip()
                            eml = str(a.get('Email', '') or '').strip()
                            polo = str(a.get('Pólo da escola', '') or '').strip()
                            instr = str(a.get('Instrumento Pretendido', '') or str(a.get('Instrumentos', '') or '')).strip()
                            if tel: parts.append(f"📞 {tel}")
                            if eml: parts.append(f"📧 {eml}")
                            if polo: parts.append(f"📍 {polo}")
                            if instr: parts.append(f"🎷 {instr}")
                            if parts:
                                st.success("  |  ".join(parts))

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
                        elif recorrente_check and not dia_escolhido:
                            st.error("⚠️ Para aula recorrente é necessário selecionar o dia da semana")
                        else:
                            # Buscar contacto
                            contacto_aluno = ""
                            match_c = df_alunos[df_alunos['Nome'] == aluno_escolhido]
                            if not match_c.empty:
                                contacto_aluno = str(match_c.iloc[0].get('Telefone', '') or '').strip()

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

                            # ---- VERIFICAR CONFLITOS ----
                            conflitos = _verificar_conflitos(
                                df_aulas_todas,
                                hora_aula.strip(),
                                local_escolhido,
                                dia_escolhido if dia_escolhido else None,
                                data_especifica if not recorrente_check else None,
                                recorrente_check
                            )

                            if conflitos:
                                # Guardar em session_state e mostrar confirmação
                                st.session_state['conflito_pendente'] = True
                                st.session_state['aula_pendente'] = nova_aula
                                st.session_state['conflitos_info'] = conflitos
                                st.rerun()
                            else:
                                # Sem conflitos → guardar directamente
                                try:
                                    base.append_row("Aulas", nova_aula)
                                    st.success(f"✅ **{aluno_escolhido}** adicionado às tuas aulas!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e_add:
                                    st.error(f"❌ Erro ao adicionar: {e_add}")

        if ja_atribuidos_lista:
            st.divider()
            with st.expander(f"ℹ️ Alunos já nas tuas aulas ({len(ja_atribuidos_lista)})"):
                for n in sorted(ja_atribuidos_lista):
                    st.write(f"✅ {n}")

    # ========================================
    # TAB 3: CALENDÁRIO
    # ========================================
    with t3:
        st.subheader("📅 Calendário de Aulas")
        _render_calendario(df_aulas_todas)
