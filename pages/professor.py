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

# Mapa numérico para locais — comparação robusta sem depender de strings do SeaTable
LOCAL_MAP = {"oeiras": 1, "algés": 2, "alges": 2, "outro": 3}

# ============================================
# HELPERS
# ============================================

def _sv(val):
    """
    Normaliza qualquer valor do SeaTable para string limpa.
    SeaTable pode devolver:
      - string:  "Oeiras"
      - lista de strings: ["Oeiras"]
      - lista de dicts:   [{"id":"x","name":"Oeiras","color":"#fff"}]
      - dict:    {"id":"x","name":"Oeiras"}
      - None / bool / int
    """
    if val is None:
        return ''
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, dict):
        return str(val.get('name', val.get('value', ''))).strip()
    if isinstance(val, list):
        if not val:
            return ''
        item = val[0]
        if isinstance(item, dict):
            return str(item.get('name', item.get('value', ''))).strip()
        return str(item).strip()
    return str(val).strip()


def _local_id(val):
    """
    Converte nome de local para ID numérico (1=Oeiras, 2=Algés, 3=Outro).
    Comparação robusta: case-insensitive, sem acentos alternativos.
    Devolve 0 se não reconhecido.
    """
    s = _sv(val).lower().strip()
    return LOCAL_MAP.get(s, 0)


def _hora_norm(val):
    """Normaliza hora: '16:00 ', '16:0', '16h00' → '16:00'"""
    s = _sv(val).strip().replace('h', ':').replace('H', ':')
    # Garantir formato HH:MM
    if ':' in s:
        partes = s.split(':')
        try:
            return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
        except Exception:
            pass
    return s


def _normalizar_recorrente(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, list):
        val = val[0] if val else False
    if isinstance(val, dict):
        val = val.get('name', val.get('value', False))
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
                dia_semana = _sv(aula.get('Dia da Semana', ''))
                if dia_semana not in DIAS_PT_MAP or DIAS_PT_MAP[dia_semana] != weekday:
                    continue

                data_inicio_raw = _sv(aula.get('Data Inicio', ''))
                if data_inicio_raw:
                    try:
                        data_inicio = datetime.strptime(data_inicio_raw[:10], '%Y-%m-%d').date()
                        if data_dia < data_inicio:
                            continue
                    except Exception:
                        pass
                else:
                    ctime_raw = _sv(aula.get('_ctime', ''))
                    if ctime_raw:
                        try:
                            data_criacao = datetime.strptime(ctime_raw[:10], '%Y-%m-%d').date()
                            if data_dia < data_criacao:
                                continue
                        except Exception:
                            pass

                aulas_do_dia.append(aula)
            else:
                data_raw = _sv(aula.get('Data Aula', ''))
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
    Verifica conflitos de horário e local.
    Usa IDs numéricos para local e hora normalizada — robusto contra variações do SeaTable.
    """
    conflitos = []
    if df_aulas.empty:
        return conflitos

    hora_norm  = _hora_norm(hora)
    local_id   = _local_id(local)

    # Sem local reconhecido, não conseguimos comparar — avisar mesmo assim
    if local_id == 0:
        return conflitos

    for _, aula in df_aulas.iterrows():
        aula_hora_norm = _hora_norm(aula.get('Hora', ''))
        aula_local_id  = _local_id(aula.get('Local', ''))

        # ✅ Comparação numérica para local + hora normalizada
        if aula_hora_norm != hora_norm or aula_local_id != local_id or aula_local_id == 0:
            continue

        aula_recorrente = _normalizar_recorrente(aula.get('Recorrente', False))
        aula_dia        = _sv(aula.get('Dia da Semana', ''))

        if recorrente and dia_semana:
            if aula_recorrente:
                if aula_dia == dia_semana:
                    conflitos.append({
                        'professor': _sv(aula.get('Professor', '')) or '---',
                        'aluno':     _sv(aula.get('Aluno', ''))     or '---',
                        'tipo':      f"Recorrente ({aula_dia})",
                        'hora':      aula_hora_norm,
                        'local':     _sv(aula.get('Local', ''))     or '---',
                    })
            else:
                data_raw = _sv(aula.get('Data Aula', ''))
                if data_raw and dia_semana in DIAS_PT_MAP:
                    try:
                        d = datetime.strptime(data_raw[:10], '%Y-%m-%d').date()
                        if d.weekday() == DIAS_PT_MAP[dia_semana]:
                            conflitos.append({
                                'professor': _sv(aula.get('Professor', '')) or '---',
                                'aluno':     _sv(aula.get('Aluno', ''))     or '---',
                                'tipo':      f"Data específica {data_raw[:10]}",
                                'hora':      aula_hora_norm,
                                'local':     _sv(aula.get('Local', ''))     or '---',
                            })
                    except Exception:
                        pass

        elif not recorrente and data_especifica:
            weekday_nova = data_especifica.weekday()
            if aula_recorrente:
                if aula_dia in DIAS_PT_MAP and DIAS_PT_MAP[aula_dia] == weekday_nova:
                    conflitos.append({
                        'professor': _sv(aula.get('Professor', '')) or '---',
                        'aluno':     _sv(aula.get('Aluno', ''))     or '---',
                        'tipo':      f"Recorrente ({aula_dia})",
                        'hora':      aula_hora_norm,
                        'local':     _sv(aula.get('Local', ''))     or '---',
                    })
            else:
                data_raw = _sv(aula.get('Data Aula', ''))
                if data_raw[:10] == str(data_especifica)[:10]:
                    conflitos.append({
                        'professor': _sv(aula.get('Professor', '')) or '---',
                        'aluno':     _sv(aula.get('Aluno', ''))     or '---',
                        'tipo':      f"Data específica {data_raw[:10]}",
                        'hora':      aula_hora_norm,
                        'local':     _sv(aula.get('Local', ''))     or '---',
                    })

    return conflitos


def _render_bloco_conflito(base):
    """Mostra bloco de confirmação de conflito pendente. Retorna True se existe."""
    if not st.session_state.get('conflito_pendente', False):
        return False

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
        if st.button("✅ Sim, confirmar mesmo assim", type="primary",
                     use_container_width=True, key="conflito_sim"):
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
        if st.button("❌ Cancelar e escolher outro horário",
                     use_container_width=True, key="conflito_nao"):
            st.session_state['conflito_pendente'] = False
            st.session_state.pop('aula_pendente', None)
            st.session_state.pop('conflitos_info', None)
            st.rerun()

    return True


def _render_calendario(df_aulas):
    """Renderiza calendário mensal navegável."""
    hoje = date.today()

    if 'cal_ano' not in st.session_state:
        st.session_state['cal_ano'] = hoje.year
    if 'cal_mes' not in st.session_state:
        st.session_state['cal_mes'] = hoje.month

    ano = st.session_state['cal_ano']
    mes = st.session_state['cal_mes']

    col_prev, col_titulo, col_hoje_btn, col_ref, col_next = st.columns([1, 3, 1, 1, 1])
    with col_prev:
        if st.button("◀ Anterior", use_container_width=True, key="cal_prev"):
            st.session_state['cal_mes'] = 12 if mes == 1 else mes - 1
            if mes == 1:
                st.session_state['cal_ano'] = ano - 1
            st.rerun()
    with col_titulo:
        st.markdown(
            f"<h3 style='text-align:center; margin:0; padding:4px 0'>"
            f"{MESES_PT[mes]} {ano}</h3>",
            unsafe_allow_html=True
        )
    with col_hoje_btn:
        if st.button("📅 Hoje", use_container_width=True, key="cal_hoje"):
            st.session_state['cal_ano'] = hoje.year
            st.session_state['cal_mes'] = hoje.month
            st.rerun()
    with col_ref:
        if st.button("🔄", use_container_width=True, key="cal_refresh", help="Atualizar"):
            st.rerun()
    with col_next:
        if st.button("Próximo ▶", use_container_width=True, key="cal_next"):
            st.session_state['cal_mes'] = 1 if mes == 12 else mes + 1
            if mes == 12:
                st.session_state['cal_ano'] = ano + 1
            st.rerun()

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        locais_disp = ["Todos"]
        if not df_aulas.empty and 'Local' in df_aulas.columns:
            locais_disp += sorted(set(_sv(v) for v in df_aulas['Local'].dropna() if _sv(v)))
        filtro_local = st.selectbox("📍 Filtrar por Local", locais_disp, key="cal_loc")
    with col_f2:
        profs_disp = ["Todos"]
        if not df_aulas.empty and 'Professor' in df_aulas.columns:
            profs_disp += sorted(set(_sv(v) for v in df_aulas['Professor'].dropna() if _sv(v)))
        filtro_prof = st.selectbox("👨‍🏫 Filtrar por Professor", profs_disp, key="cal_prof")

    df_fil = df_aulas.copy() if not df_aulas.empty else pd.DataFrame()
    if not df_fil.empty:
        if filtro_local != "Todos" and 'Local' in df_fil.columns:
            df_fil = df_fil[df_fil['Local'].apply(_sv) == filtro_local]
        if filtro_prof != "Todos" and 'Professor' in df_fil.columns:
            df_fil = df_fil[df_fil['Professor'].apply(_sv) == filtro_prof]

    profs_todos = sorted(set(_sv(v) for v in df_aulas['Professor'].dropna() if _sv(v))) if not df_aulas.empty and 'Professor' in df_aulas.columns else []
    cores_prof = {p: CORES_PROFESSORES[i % len(CORES_PROFESSORES)] for i, p in enumerate(profs_todos)}

    aulas_por_dia = _get_aulas_do_mes(df_fil, ano, mes)

    css = """
    <style>
    .bmo-cal { width:100%; border-collapse:collapse; table-layout:fixed; margin-top:8px; }
    .bmo-cal th { background:#ff6b35; color:white; padding:8px 4px; text-align:center; font-weight:bold; font-size:0.82rem; }
    .bmo-cal td { border:1px solid #ddd; padding:4px; vertical-align:top; height:90px; width:14.28%; font-size:0.75rem; background:#fff; }
    .bmo-cal td.vazio { background:#f5f5f5; }
    .bmo-cal td.e-hoje { background:#fff8f5; border:2px solid #ff6b35 !important; }
    .bmo-cal td.fim-semana { background:#fafafa; }
    .cal-num { font-weight:bold; font-size:0.88rem; color:#555; margin-bottom:2px; }
    .cal-num-hoje { color:#ff6b35; font-size:0.95rem; font-weight:bold; }
    .aula-pill { display:block; padding:2px 5px; margin:1px 0; border-radius:4px; font-size:0.68rem; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .bmo-legenda { display:flex; flex-wrap:wrap; gap:10px; margin:8px 0 4px 0; }
    .bmo-leg-item { display:flex; align-items:center; gap:5px; font-size:0.8rem; }
    .bmo-leg-dot { width:11px; height:11px; border-radius:50%; display:inline-block; flex-shrink:0; }
    </style>
    """

    leg_html = '<div class="bmo-legenda">' + ''.join(
        f'<div class="bmo-leg-item"><span class="bmo-leg-dot" style="background:{cor}"></span>{prof}</div>'
        for prof, cor in cores_prof.items()
    ) + '</div>'

    cal_matrix = calendar.monthcalendar(ano, mes)
    html = css + leg_html + '<table class="bmo-cal"><thead><tr>'
    for d in ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]:
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
                is_fds  = idx >= 5
                td_class = 'e-hoje' if is_hoje else ('fim-semana' if is_fds else '')
                html += f'<td class="{td_class}"><div class="{"cal-num-hoje" if is_hoje else "cal-num"}">{dia}</div>'
                if dia in aulas_por_dia:
                    for aula in sorted(aulas_por_dia[dia], key=lambda a: _hora_norm(a.get('Hora',''))):
                        prof  = _sv(aula.get('Professor', ''))
                        aluno = _sv(aula.get('Aluno', ''))
                        hora  = _hora_norm(aula.get('Hora', ''))
                        local = _sv(aula.get('Local', ''))
                        cor   = cores_prof.get(prof, '#888888')
                        html += (f'<span class="aula-pill" style="background:{cor}" '
                                 f'title="{hora} | {aluno} | {prof} | {local}">'
                                 f'{hora} {aluno[:12]}</span>')
                html += '</td>'
        html += '</tr>'

    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    st.divider()
    total_ocorrencias = sum(len(v) for v in aulas_por_dia.values())
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Dias com aulas", len(aulas_por_dia))
    col2.metric("🎵 Ocorrências no mês", total_ocorrencias)
    if aulas_por_dia:
        dia_cheio = max(aulas_por_dia, key=lambda d: len(aulas_por_dia[d]))
        col3.metric("🔥 Dia mais ocupado", f"{dia_cheio} {MESES_PT[mes][:3]}")

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
            for aula in sorted(aulas_por_dia[dia_sel], key=lambda a: _hora_norm(a.get('Hora',''))):
                prof = _sv(aula.get('Professor','---')) or '---'
                cor  = cores_prof.get(prof, '#888')
                rec_str = "🔁" if _normalizar_recorrente(aula.get('Recorrente', False)) else "📌"
                st.markdown(
                    f"<div style='border-left:4px solid {cor}; padding:6px 10px; margin:4px 0;"
                    f"background:#fafafa; border-radius:0 6px 6px 0'>"
                    f"{rec_str} 🕐 <b>{_hora_norm(aula.get('Hora','---'))}</b> &nbsp;|&nbsp; "
                    f"👤 {_sv(aula.get('Aluno','---')) or '---'} &nbsp;|&nbsp; "
                    f"👨‍🏫 {prof} &nbsp;|&nbsp; "
                    f"📍 {_sv(aula.get('Local','---')) or '---'} &nbsp;|&nbsp; "
                    f"🏫 {_sv(aula.get('Sala','---')) or '---'}"
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

    t1, t2, t3, t4 = st.tabs([
        "📚 Os Meus Alunos",
        "➕ Adicionar Aluno",
        "📆 Aula Extra",
        "📅 Calendário"
    ])

    try:
        aulas_raw  = base.list_rows("Aulas")
        alunos_raw = base.list_rows("Alunos")
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return

    df_alunos      = pd.DataFrame(alunos_raw)  if alunos_raw  else pd.DataFrame()
    df_aulas_todas = pd.DataFrame(aulas_raw)   if aulas_raw   else pd.DataFrame()

    if not df_aulas_todas.empty and 'Professor' in df_aulas_todas.columns:
        minhas_aulas = df_aulas_todas[
            df_aulas_todas['Professor'].apply(_sv) == user['display_name']
        ].copy()
    else:
        minhas_aulas = pd.DataFrame()

    # ========================================
    # TAB 1: OS MEUS ALUNOS
    # ========================================
    with t1:
        st.subheader("📚 Os Meus Alunos")

        if minhas_aulas.empty:
            st.info("📭 Ainda não tem alunos. Use **➕ Adicionar Aluno** para começar.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("👥 Total de Registos", len(minhas_aulas))
            if 'Local' in minhas_aulas.columns:
                locais = minhas_aulas['Local'].apply(_sv).value_counts()
                col2.metric("📍 Local mais frequente", locais.index[0] if not locais.empty else "---")
            recorrentes = minhas_aulas['Recorrente'].apply(_normalizar_recorrente).sum() if 'Recorrente' in minhas_aulas.columns else 0
            col3.metric("🔁 Aulas Recorrentes", int(recorrentes))

            st.divider()

            for _, aula in minhas_aulas.iterrows():
                nome_aluno  = _sv(aula.get('Aluno', ''))   or 'Sem nome'
                hora        = _hora_norm(aula.get('Hora', '')) or '---'
                sala        = _sv(aula.get('Sala', ''))    or '---'
                local       = _sv(aula.get('Local', ''))   or '---'
                dia         = _sv(aula.get('Dia da Semana', ''))
                recorrente  = _normalizar_recorrente(aula.get('Recorrente', False))
                data_aula   = _sv(aula.get('Data Aula', ''))
                data_inicio = _sv(aula.get('Data Inicio', ''))
                row_id      = aula.get('_id')

                horario_str = f"{dia} {hora}" if dia else (f"{data_aula[:10]} {hora}" if data_aula else hora)

                telefone, email = "---", "---"
                if not df_alunos.empty and 'Nome' in df_alunos.columns:
                    match = df_alunos[df_alunos['Nome'].apply(_sv) == nome_aluno]
                    if not match.empty:
                        telefone = _sv(match.iloc[0].get('Telefone', '')) or '---'
                        email    = _sv(match.iloc[0].get('Email', ''))    or '---'

                tipo_badge = "🔁 Recorrente" if recorrente else "📌 Pontual"
                edit_key   = f"edit_aula_{row_id}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False

                with st.expander(f"🎵 {nome_aluno} — {horario_str} | {local} | {tipo_badge}"):
                    if st.session_state[edit_key] and recorrente:
                        st.markdown("#### ✏️ Editar Aula Recorrente")
                        with st.form(f"form_edit_aula_{row_id}"):
                            c1, c2 = st.columns(2)
                            with c1:
                                dias_opts = ["","Segunda-Feira","Terça-Feira","Quarta-Feira",
                                             "Quinta-Feira","Sexta-Feira","Sábado","Domingo"]
                                novo_dia  = st.selectbox("Dia da Semana*", options=dias_opts,
                                                         index=dias_opts.index(dia) if dia in dias_opts else 0)
                                nova_hora = st.text_input("Hora*", value=hora)
                                try:
                                    di_val = datetime.strptime(data_inicio[:10], '%Y-%m-%d').date() if data_inicio else date.today()
                                except Exception:
                                    di_val = date.today()
                                nova_di = st.date_input("Data de Início", value=di_val)
                            with c2:
                                local_opts = ["Oeiras","Algés","Outro"]
                                novo_local = st.selectbox("Local", options=local_opts,
                                                          index=local_opts.index(local) if local in local_opts else 0)
                                nova_sala  = st.text_input("Sala", value=sala if sala != '---' else '')
                            cs, cc = st.columns(2)
                            with cs:
                                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                            with cc:
                                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
                            if guardar:
                                if not novo_dia or not nova_hora.strip():
                                    st.error("⚠️ Dia e Hora são obrigatórios")
                                else:
                                    try:
                                        base.update_row("Aulas", row_id, {
                                            "Dia da Semana": novo_dia,
                                            "Hora": nova_hora.strip(),
                                            "Local": novo_local,
                                            "Sala": nova_sala.strip(),
                                            "Data Inicio": str(nova_di),
                                        })
                                        st.session_state[edit_key] = False
                                        st.success("✅ Aula atualizada!")
                                        st.rerun()
                                    except Exception as e_upd:
                                        st.error(f"❌ Erro: {e_upd}")
                            if cancelar:
                                st.session_state[edit_key] = False
                                st.rerun()
                    else:
                        col_info, col_contacto, col_acao = st.columns([3, 3, 1])
                        with col_info:
                            st.markdown("**📅 Horário**")
                            st.write(f"🕐 **Hora:** {hora}")
                            if dia: st.write(f"📆 **Dia:** {dia}")
                            if data_aula: st.write(f"📅 **Data:** {data_aula[:10]}")
                            if data_inicio: st.write(f"▶️ **Início:** {data_inicio[:10]}")
                            st.write(f"🏫 **Sala:** {sala}")
                            st.write(f"📍 **Local:** {local}")
                            st.write(f"🔁 **Recorrente:** {'Sim' if recorrente else 'Não'}")
                        with col_contacto:
                            st.markdown("**📞 Contacto do Aluno**")
                            st.write(f"📞 **Telefone:** {telefone}")
                            st.write(f"📧 **Email:** {email}")
                            contacto_aula = _sv(aula.get('Contacto', ''))
                            if contacto_aula and contacto_aula != '---':
                                st.write(f"📱 **Contacto (aula):** {contacto_aula}")
                        with col_acao:
                            st.markdown("**⚙️ Ações**")
                            confirm_key = f"confirm_remove_{row_id}"
                            if recorrente:
                                if st.button("✏️ Editar", key=f"edit_btn_{row_id}", use_container_width=True):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                            if st.session_state.get(confirm_key, False):
                                st.warning("Tens a certeza?")
                                if st.button("✅ Sim", key=f"yes_{row_id}", use_container_width=True, type="primary"):
                                    try:
                                        base.delete_row("Aulas", row_id)
                                        st.session_state.pop(confirm_key, None)
                                        st.success("✅ Removido!")
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
        st.caption("Para registar um aluno com aula semanal recorrente.")

        if df_alunos.empty or 'Nome' not in df_alunos.columns:
            st.error("❌ Não foi possível carregar a lista de alunos da escola.")
            return

        nomes_ja_atribuidos = set()
        if not minhas_aulas.empty and 'Aluno' in minhas_aulas.columns:
            rec_mask = minhas_aulas['Recorrente'].apply(_normalizar_recorrente)
            nomes_ja_atribuidos = set(minhas_aulas[rec_mask]['Aluno'].apply(_sv).dropna().tolist())

        todos_alunos        = df_alunos['Nome'].apply(_sv).dropna().sort_values().tolist()
        disponiveis         = [n for n in todos_alunos if n not in nomes_ja_atribuidos]
        ja_atribuidos_lista = [n for n in todos_alunos if n in nomes_ja_atribuidos]

        st.info(
            f"📊 **{len(todos_alunos)}** alunos na escola · "
            f"**{len(ja_atribuidos_lista)}** já com aula recorrente · "
            f"**{len(disponiveis)}** disponíveis"
        )

        if _render_bloco_conflito(base):
            st.stop()

        if not disponiveis:
            st.success("✅ Todos os alunos da escola já têm aula recorrente contigo!")
        else:
            pesquisa = st.text_input("🔍 Pesquisar aluno", placeholder="Escreve parte do nome...", key="pesq_novo")
            disp_fil = [n for n in disponiveis if pesquisa.strip().lower() in n.lower()] if pesquisa.strip() else disponiveis

            if not disp_fil:
                st.warning(f"Nenhum aluno encontrado com '{pesquisa}'")
            else:
                with st.form("form_add_aluno"):
                    aluno_escolhido = st.selectbox("Aluno*", options=disp_fil)
                    if aluno_escolhido:
                        match = df_alunos[df_alunos['Nome'].apply(_sv) == aluno_escolhido]
                        if not match.empty:
                            a = match.iloc[0]
                            parts = []
                            for campo, icone in [('Telefone','📞'),('Email','📧'),('Pólo da escola','📍')]:
                                v = _sv(a.get(campo, ''))
                                if v: parts.append(f"{icone} {v}")
                            instr = _sv(a.get('Instrumento Pretendido','')) or _sv(a.get('Instrumentos',''))
                            if instr: parts.append(f"🎷 {instr}")
                            if parts: st.success("  |  ".join(parts))

                    st.markdown("#### 📅 Dados da Aula Recorrente")
                    c1, c2 = st.columns(2)
                    with c1:
                        dias_semana = ["","Segunda-Feira","Terça-Feira","Quarta-Feira",
                                       "Quinta-Feira","Sexta-Feira","Sábado","Domingo"]
                        dia_escolhido   = st.selectbox("Dia da Semana*", options=dias_semana)
                        hora_aula       = st.text_input("Hora*", placeholder="Ex: 16:00")
                        data_inicio_rec = st.date_input("Data de Início*", value=date.today())
                    with c2:
                        local_opcoes    = ["Oeiras","Algés","Outro"]
                        local_escolhido = st.selectbox("Local", options=local_opcoes)
                        sala_aula       = st.text_input("Sala", placeholder="Ex: Sala 3")

                    st.caption("* Campos obrigatórios")

                    if st.form_submit_button("✅ Adicionar Aluno", use_container_width=True, type="primary"):
                        hora_norm_input = _hora_norm(hora_aula)
                        if not hora_norm_input:
                            st.error("⚠️ A hora da aula é obrigatória")
                        elif not dia_escolhido:
                            st.error("⚠️ O dia da semana é obrigatório")
                        else:
                            contacto_aluno = _sv(df_alunos[df_alunos['Nome'].apply(_sv) == aluno_escolhido].iloc[0].get('Telefone','')) if not df_alunos[df_alunos['Nome'].apply(_sv) == aluno_escolhido].empty else ""
                            nova_aula = {
                                "Professor": user['display_name'], "Aluno": aluno_escolhido,
                                "Hora": hora_norm_input, "Sala": sala_aula.strip(),
                                "Contacto": contacto_aluno, "Local": local_escolhido,
                                "Dia da Semana": dia_escolhido, "Recorrente": True,
                                "Data Inicio": str(data_inicio_rec),
                            }
                            conflitos = _verificar_conflitos(df_aulas_todas, hora_norm_input, local_escolhido, dia_escolhido, None, True)
                            if conflitos:
                                st.session_state.update({'conflito_pendente': True, 'aula_pendente': nova_aula, 'conflitos_info': conflitos})
                                st.rerun()
                            else:
                                try:
                                    base.append_row("Aulas", nova_aula)
                                    st.success(f"✅ **{aluno_escolhido}** adicionado às tuas aulas!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e_add:
                                    st.error(f"❌ Erro: {e_add}")

        if ja_atribuidos_lista:
            st.divider()
            with st.expander(f"ℹ️ Alunos com aula recorrente ({len(ja_atribuidos_lista)})"):
                for n in sorted(ja_atribuidos_lista):
                    st.write(f"✅ {n}")

    # ========================================
    # TAB 3: AULA EXTRA
    # ========================================
    with t3:
        st.subheader("📆 Marcar Aula Extra")
        st.caption("Marca uma aula pontual para um aluno que já está na tua lista.")

        if minhas_aulas.empty or 'Aluno' not in minhas_aulas.columns:
            st.info("📭 Ainda não tens alunos. Adiciona primeiro na aba **➕ Adicionar Aluno**.")
        else:
            if _render_bloco_conflito(base):
                st.stop()

            alunos_meus = sorted(minhas_aulas['Aluno'].apply(_sv).dropna().unique().tolist())

            with st.form("form_aula_extra"):
                aluno_extra = st.selectbox("Selecionar Aluno*", options=alunos_meus)
                if aluno_extra and not df_alunos.empty and 'Nome' in df_alunos.columns:
                    me = df_alunos[df_alunos['Nome'].apply(_sv) == aluno_extra]
                    if not me.empty:
                        parts_e = []
                        tel_e = _sv(me.iloc[0].get('Telefone',''))
                        eml_e = _sv(me.iloc[0].get('Email',''))
                        if tel_e: parts_e.append(f"📞 {tel_e}")
                        if eml_e: parts_e.append(f"📧 {eml_e}")
                        if parts_e: st.info("  |  ".join(parts_e))

                st.markdown("#### 📅 Dados da Aula Extra")
                c1, c2 = st.columns(2)
                with c1:
                    data_extra = st.date_input("Data da Aula*", value=date.today())
                    hora_extra = st.text_input("Hora*", placeholder="Ex: 17:00")
                with c2:
                    local_extra = st.selectbox("Local", options=["Oeiras","Algés","Outro"], key="local_extra")
                    sala_extra  = st.text_input("Sala", placeholder="Ex: Sala 1", key="sala_extra")

                st.caption("* Campos obrigatórios")

                if st.form_submit_button("✅ Marcar Aula Extra", use_container_width=True, type="primary"):
                    hora_norm_extra = _hora_norm(hora_extra)
                    if not hora_norm_extra:
                        st.error("⚠️ A hora é obrigatória")
                    else:
                        contacto_extra = ""
                        mx = df_alunos[df_alunos['Nome'].apply(_sv) == aluno_extra] if not df_alunos.empty else pd.DataFrame()
                        if not mx.empty:
                            contacto_extra = _sv(mx.iloc[0].get('Telefone',''))

                        nova_aula_extra = {
                            "Professor": user['display_name'], "Aluno": aluno_extra,
                            "Hora": hora_norm_extra, "Sala": sala_extra.strip(),
                            "Contacto": contacto_extra, "Local": local_extra,
                            "Dia da Semana": "", "Recorrente": False,
                            "Data Aula": str(data_extra), "Data Inicio": str(data_extra),
                        }
                        conflitos_e = _verificar_conflitos(df_aulas_todas, hora_norm_extra, local_extra, None, data_extra, False)
                        if conflitos_e:
                            st.session_state.update({'conflito_pendente': True, 'aula_pendente': nova_aula_extra, 'conflitos_info': conflitos_e})
                            st.rerun()
                        else:
                            try:
                                base.append_row("Aulas", nova_aula_extra)
                                st.success(f"✅ Aula extra marcada para **{aluno_extra}** em {data_extra.strftime('%d/%m/%Y')} às {hora_norm_extra}!")
                                st.balloons()
                                st.rerun()
                            except Exception as e_extra:
                                st.error(f"❌ Erro: {e_extra}")

    # ========================================
    # TAB 4: CALENDÁRIO
    # ========================================
    with t4:
        st.subheader("📅 Calendário de Aulas")
        _render_calendario(df_aulas_todas)
