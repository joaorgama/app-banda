"""
Interface do Maestro - Portal BMO
"""
import streamlit as st
import pandas as pd
import calendar
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta, date
from app import (
    get_musicos_cached,
    get_eventos_cached,
    get_presencas_cached,
    get_faltas_ensaios_cached,
    get_aulas_cached
)

# ============================================
# HELPERS ENSAIOS
# ============================================
_DIAS_PT_MAP = {
    "Segunda-Feira": 0, "Terça-Feira": 1, "Quarta-Feira": 2,
    "Quinta-Feira": 3, "Sexta-Feira": 4, "Sábado": 5, "Domingo": 6,
}
_MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _sv(val):
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


def _hora_norm(val):
    s = _sv(val).strip().upper().replace('H', ':')
    if ':' in s:
        partes = s.split(':')
        try:
            return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
        except Exception:
            pass
    return s


def _datas_canceladas(ensaio):
    raw = _sv(ensaio.get('Datas Canceladas', ''))
    if not raw:
        return set()
    return set(d.strip() for d in raw.split(',') if d.strip())


def _get_ensaios_do_mes(ensaios, ano, mes):
    ensaios_por_dia = {}
    num_dias = calendar.monthrange(ano, mes)[1]
    for dia in range(1, num_dias + 1):
        data_dia     = date(ano, mes, dia)
        weekday      = data_dia.weekday()
        data_dia_str = data_dia.strftime('%Y-%m-%d')
        lista = []
        for e in ensaios:
            tipo = _sv(e.get('Tipo', 'Pontual'))
            if data_dia_str in _datas_canceladas(e):
                continue
            if tipo == 'Pontual':
                raw = _sv(e.get('Data', ''))
                if raw:
                    try:
                        if datetime.strptime(raw[:10], '%Y-%m-%d').date() == data_dia:
                            lista.append(e)
                    except Exception:
                        pass
            else:
                dia_sem = _sv(e.get('Dia da Semana', ''))
                if dia_sem not in _DIAS_PT_MAP or _DIAS_PT_MAP[dia_sem] != weekday:
                    continue
                raw_inicio = _sv(e.get('Data', ''))
                if raw_inicio:
                    try:
                        if data_dia < datetime.strptime(raw_inicio[:10], '%Y-%m-%d').date():
                            continue
                    except Exception:
                        pass
                raw_fim = _sv(e.get('Data Fim', ''))
                if raw_fim:
                    try:
                        if data_dia > datetime.strptime(raw_fim[:10], '%Y-%m-%d').date():
                            continue
                    except Exception:
                        pass
                lista.append(e)
        if lista:
            ensaios_por_dia[dia] = lista
    return ensaios_por_dia


def _render_calendario_maestro(base, ensaios, faltas, musicos):
    hoje = date.today()
    dark = st.session_state.get('dark_mode', True)
    card_bg    = '#2a2a2a' if dark else '#fafafa'
    card_color = '#f5f5f5' if dark else '#1a1a1a'

    if 'mae_ens_ano' not in st.session_state:
        st.session_state['mae_ens_ano'] = hoje.year
    if 'mae_ens_mes' not in st.session_state:
        st.session_state['mae_ens_mes'] = hoje.month

    ano = st.session_state['mae_ens_ano']
    mes = st.session_state['mae_ens_mes']

    col_prev, col_titulo, col_hoje_btn, col_ref, col_next = st.columns([1, 3, 1, 1, 1])
    with col_prev:
        if st.button("◀ Anterior", use_container_width=True, key="mae_ens_prev"):
            if mes == 1:
                st.session_state['mae_ens_mes'] = 12
                st.session_state['mae_ens_ano'] = ano - 1
            else:
                st.session_state['mae_ens_mes'] = mes - 1
            st.rerun()
    with col_titulo:
        st.markdown(
            f"<h3 style='text-align:center;margin:0;padding:4px 0'>"
            f"{_MESES_PT[mes]} {ano}</h3>",
            unsafe_allow_html=True
        )
    with col_hoje_btn:
        if st.button("📅 Hoje", use_container_width=True, key="mae_ens_hoje"):
            st.session_state.update({'mae_ens_ano': hoje.year, 'mae_ens_mes': hoje.month})
            st.rerun()
    with col_ref:
        if st.button("🔄", use_container_width=True, key="mae_ens_refresh"):
            st.rerun()
    with col_next:
        if st.button("Próximo ▶", use_container_width=True, key="mae_ens_next"):
            if mes == 12:
                st.session_state['mae_ens_mes'] = 1
                st.session_state['mae_ens_ano'] = ano + 1
            else:
                st.session_state['mae_ens_mes'] = mes + 1
            st.rerun()

    ensaios_por_dia = _get_ensaios_do_mes(ensaios, ano, mes)

    cal_bg      = '#1e1e1e' if dark else '#ffffff'
    cal_border  = '#444'    if dark else '#ddd'
    cal_vazio   = '#2a2a2a' if dark else '#f5f5f5'
    cal_fds     = '#252525' if dark else '#fafafa'
    cal_hoje_bg = '#2d1a0e' if dark else '#fff8f5'
    num_color   = '#aaa'    if dark else '#555'

    css = f"""<style>
    .bmo-mae{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:8px}}
    .bmo-mae th{{background:#ff6b35;color:#fff;padding:8px 4px;text-align:center;font-weight:bold;font-size:.82rem}}
    .bmo-mae td{{border:1px solid {cal_border};padding:4px;vertical-align:top;height:90px;width:14.28%;font-size:.75rem;background:{cal_bg}}}
    .bmo-mae td.vazio{{background:{cal_vazio}}}
    .bmo-mae td.e-hoje{{background:{cal_hoje_bg};border:2px solid #ff6b35!important}}
    .bmo-mae td.fim-semana{{background:{cal_fds}}}
    .mae-num{{font-weight:bold;font-size:.88rem;color:{num_color};margin-bottom:2px}}
    .mae-num-hoje{{color:#ff6b35;font-size:.95rem;font-weight:bold}}
    .mae-pill{{display:block;padding:2px 5px;margin:1px 0;border-radius:4px;font-size:.66rem;
               color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    </style>"""

    html = css + '<table class="bmo-mae"><thead><tr>'
    for d in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html += f'<th>{d}</th>'
    html += '</tr></thead><tbody>'

    for semana in calendar.monthcalendar(ano, mes):
        html += '<tr>'
        for idx, dia in enumerate(semana):
            if dia == 0:
                html += '<td class="vazio"></td>'
            else:
                is_hoje  = date(ano, mes, dia) == hoje
                td_class = 'e-hoje' if is_hoje else ('fim-semana' if idx >= 5 else '')
                html += (f'<td class="{td_class}">'
                         f'<div class="{"mae-num-hoje" if is_hoje else "mae-num"}">{dia}</div>')
                if dia in ensaios_por_dia:
                    for e in sorted(ensaios_por_dia[dia], key=lambda x: _hora_norm(x.get('Hora', ''))):
                        hora     = _hora_norm(e.get('Hora', ''))
                        nome     = _sv(e.get('Nome', 'Ensaio'))
                        data_str = date(ano, mes, dia).strftime('%Y-%m-%d')
                        n_faltas = sum(
                            1 for f in faltas
                            if _sv(f.get('EnsaioID', '')) == _sv(e.get('_id', ''))
                            and _sv(f.get('Data', ''))[:10] == data_str
                        )
                        badge = f" ⚠️{n_faltas}" if n_faltas > 0 else ""
                        html += (f'<span class="mae-pill" style="background:#ff6b35" '
                                 f'title="{nome}">🥁 {hora} {nome[:8]}{badge}</span>')
                html += '</td>'
        html += '</tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🔍 Detalhe do Dia")
    dias_lista = sorted(ensaios_por_dia.keys())
    if not dias_lista:
        st.info("Nenhum ensaio neste mês.")
        return

    dia_sel = st.selectbox(
        "Selecionar dia:",
        options=dias_lista,
        format_func=lambda d: f"{d} de {_MESES_PT[mes]} — {len(ensaios_por_dia[d])} ensaio(s)",
        key="mae_ens_dia"
    )

    if dia_sel:
        data_sel     = date(ano, mes, dia_sel)
        data_sel_str = data_sel.strftime('%Y-%m-%d')

        for e in sorted(ensaios_por_dia[dia_sel], key=lambda x: _hora_norm(x.get('Hora', ''))):
            eid   = _sv(e.get('_id', ''))
            hora  = _hora_norm(e.get('Hora', '---'))
            nome  = _sv(e.get('Nome', 'Ensaio'))
            tipo  = _sv(e.get('Tipo', ''))
            local = _sv(e.get('Local', ''))
            tipo_icon = {'Semanal': '🔁', 'Período': '📆', 'Pontual': '📌'}.get(tipo, '🥁')

            st.markdown(
                f"<div style='border-left:4px solid #ff6b35;padding:8px 12px;margin:6px 0;"
                f"background:{card_bg};border-radius:0 8px 8px 0;color:{card_color};'>"
                f"{tipo_icon} 🕐 <b>{hora}</b> &nbsp;|&nbsp; 🥁 <b>{nome}</b>"
                f"{'&nbsp;|&nbsp; 📍 ' + local if local else ''}"
                f"</div>",
                unsafe_allow_html=True
            )

            faltas_dia = [
                f for f in faltas
                if _sv(f.get('EnsaioID', '')) == eid
                and _sv(f.get('Data', ''))[:10] == data_sel_str
            ]

            if faltas_dia:
                st.markdown(f"**⚠️ {len(faltas_dia)} músico(s) registaram falta:**")
                for f in faltas_dia:
                    username = _sv(f.get('Username', ''))
                    motivo   = _sv(f.get('Motivo', ''))
                    nome_mus = username
                    for m in musicos:
                        if str(m.get('Username', '')).lower() == username.lower():
                            nome_mus = m.get('Nome', username)
                            break
                    st.markdown(
                        f"<div style='padding:4px 10px;margin:2px 0;background:#e74c3c22;"
                        f"border-radius:6px;border-left:3px solid #e74c3c;color:{card_color}'>"
                        f"❌ <b>{nome_mus}</b>"
                        f"{'  — ' + motivo if motivo else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("✅ Sem faltas registadas para este ensaio")

            if tipo in ('Semanal', 'Período'):
                if st.button(
                    f"🚫 Cancelar ensaio de {dia_sel} {_MESES_PT[mes]}",
                    key=f"mae_cancel_{eid}_{data_sel_str}",
                    use_container_width=True
                ):
                    try:
                        datas_cancel = _datas_canceladas(e)
                        datas_cancel.add(data_sel_str)
                        base.update_row("Ensaios", eid, {
                            "Datas Canceladas": ", ".join(sorted(datas_cancel))
                        })
                        st.success(f"✅ Ensaio de {data_sel_str} cancelado!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro: {ex}")

    st.divider()
    total_mes = sum(len(v) for v in ensaios_por_dia.values())
    faltas_mes = sum(
        1 for f in faltas
        if _sv(f.get('Data', ''))[:7] == f"{ano:04d}-{mes:02d}"
    )
    musicos_com_falta = len(set(
        _sv(f.get('Username', ''))
        for f in faltas
        if _sv(f.get('Data', ''))[:7] == f"{ano:04d}-{mes:02d}"
    ))
    c1, c2, c3 = st.columns(3)
    c1.metric("🥁 Ensaios neste mês",  total_mes)
    c2.metric("⚠️ Faltas este mês",    faltas_mes)
    c3.metric("👤 Músicos com falta",  musicos_com_falta)


def _render_gestao_ensaios_maestro(base, ensaios, faltas, musicos):

    with st.expander("➕ Criar Novo Ensaio", expanded=False):
        with st.form("form_mae_novo_ensaio"):
            col1, col2 = st.columns(2)
            with col1:
                novo_nome  = st.text_input("Nome do Ensaio*", placeholder="Ex: Ensaio Semanal")
                novo_tipo  = st.selectbox("Tipo*", ["Semanal", "Período", "Pontual"])
                novo_hora  = st.text_input("Hora*", placeholder="Ex: 21:00")
                novo_local = st.text_input("Local", placeholder="Ex: Sede da Banda")
            with col2:
                dias_opts = ["", "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                             "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
                novo_dia      = st.selectbox("Dia da Semana (Semanal/Período)", options=dias_opts)
                novo_data     = st.date_input("Data / Data de Início*", value=date.today())
                novo_data_fim = st.date_input(
                    "Data de Fim (só para Período)",
                    value=date.today() + timedelta(days=90)
                )
            st.caption("* Campos obrigatórios")

            if st.form_submit_button("✅ Criar Ensaio", use_container_width=True, type="primary"):
                if not novo_nome.strip() or not novo_hora.strip():
                    st.error("⚠️ Nome e Hora são obrigatórios")
                elif novo_tipo in ('Semanal', 'Período') and not novo_dia:
                    st.error("⚠️ Para Semanal ou Período é necessário escolher o Dia da Semana")
                else:
                    dados = {
                        "Nome":             novo_nome.strip(),
                        "Tipo":             novo_tipo,
                        "Hora":             _hora_norm(novo_hora),
                        "Local":            novo_local.strip(),
                        "Data":             str(novo_data),
                        "Dia da Semana":    novo_dia if novo_tipo in ('Semanal', 'Período') else "",
                        "Data Fim":         str(novo_data_fim) if novo_tipo == 'Período' else "",
                        "Datas Canceladas": "",
                    }
                    try:
                        base.append_row("Ensaios", dados)
                        st.success(f"✅ Ensaio **{novo_nome}** criado!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro: {ex}")

    st.divider()

    if not ensaios:
        st.info("📭 Nenhum ensaio criado ainda.")
        return

    st.markdown(f"**{len(ensaios)} ensaio(s) configurado(s)**")
    tipos_icon = {'Semanal': '🔁', 'Período': '📆', 'Pontual': '📌'}

    for e in ensaios:
        eid        = _sv(e.get('_id', ''))
        nome       = _sv(e.get('Nome', 'Ensaio'))
        tipo       = _sv(e.get('Tipo', 'Pontual'))
        hora       = _hora_norm(e.get('Hora', ''))
        local      = _sv(e.get('Local', ''))
        dia        = _sv(e.get('Dia da Semana', ''))
        data       = _sv(e.get('Data', ''))[:10]
        dfim       = _sv(e.get('Data Fim', ''))[:10]
        datas_canc = _datas_canceladas(e)
        icon       = tipos_icon.get(tipo, '🥁')

        subtitulo = f"{dia} a partir de {data}" if tipo == 'Semanal' else \
                    f"{dia} de {data} a {dfim}"  if tipo == 'Período'  else data

        edit_key = f"mae_edit_ensaio_{eid}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        with st.expander(f"{icon} {nome} — {hora} | {subtitulo}"):
            if st.session_state[edit_key]:
                st.markdown("#### ✏️ Editar Ensaio")
                with st.form(f"form_mae_edit_ensaio_{eid}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_nome  = st.text_input("Nome*", value=nome)
                        e_tipo  = st.selectbox(
                            "Tipo*", ["Semanal", "Período", "Pontual"],
                            index=["Semanal", "Período", "Pontual"].index(tipo)
                            if tipo in ["Semanal", "Período", "Pontual"] else 0
                        )
                        e_hora  = st.text_input("Hora*", value=hora)
                        e_local = st.text_input("Local", value=local)
                    with ec2:
                        dias_opts2 = ["", "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                                      "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
                        e_dia = st.selectbox(
                            "Dia da Semana",
                            options=dias_opts2,
                            index=dias_opts2.index(dia) if dia in dias_opts2 else 0
                        )
                        try:
                            data_val = datetime.strptime(data, '%Y-%m-%d').date() if data else date.today()
                        except Exception:
                            data_val = date.today()
                        e_data = st.date_input("Data / Início", value=data_val)
                        try:
                            dfim_val = datetime.strptime(dfim, '%Y-%m-%d').date() if dfim else date.today() + timedelta(days=90)
                        except Exception:
                            dfim_val = date.today() + timedelta(days=90)
                        e_dfim = st.date_input("Data de Fim (Período)", value=dfim_val)

                    cs, cc = st.columns(2)
                    with cs:
                        guardar_e  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                    with cc:
                        cancelar_e = st.form_submit_button("❌ Cancelar", use_container_width=True)

                    if guardar_e:
                        if not e_nome.strip() or not e_hora.strip():
                            st.error("⚠️ Nome e Hora são obrigatórios")
                        else:
                            try:
                                base.update_row("Ensaios", eid, {
                                    "Nome":          e_nome.strip(),
                                    "Tipo":          e_tipo,
                                    "Hora":          _hora_norm(e_hora),
                                    "Local":         e_local.strip(),
                                    "Dia da Semana": e_dia if e_tipo in ('Semanal', 'Período') else "",
                                    "Data":          str(e_data),
                                    "Data Fim":      str(e_dfim) if e_tipo == 'Período' else "",
                                })
                                st.session_state[edit_key] = False
                                st.success("✅ Ensaio atualizado!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro: {ex}")
                    if cancelar_e:
                        st.session_state[edit_key] = False
                        st.rerun()

            else:
                col_info, col_acoes = st.columns([3, 1])
                with col_info:
                    st.write(f"**Tipo:** {icon} {tipo}")
                    st.write(f"**Hora:** {hora}")
                    if local:
                        st.write(f"**Local:** {local}")
                    if tipo in ('Semanal', 'Período'):
                        st.write(f"**Dia:** {dia}")
                        st.write(f"**Início:** {data}")
                    if tipo == 'Período':
                        st.write(f"**Fim:** {dfim}")
                    if tipo == 'Pontual':
                        st.write(f"**Data:** {data}")
                    if datas_canc:
                        st.caption(f"🚫 Datas canceladas: {', '.join(sorted(datas_canc))}")

                with col_acoes:
                    if st.button("✏️ Editar", key=f"mae_btn_edit_ens_{eid}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()

                    if tipo in ('Semanal', 'Período') and datas_canc:
                        if st.button("📋 Cancelamentos", key=f"mae_ver_canc_{eid}", use_container_width=True):
                            k = f"mae_show_canc_{eid}"
                            st.session_state[k] = not st.session_state.get(k, False)
                            st.rerun()

                    confirm_del_key = f"mae_confirm_del_ens_{eid}"
                    if st.session_state.get(confirm_del_key, False):
                        st.warning("Apagar este ensaio?")
                        if st.button("✅ Sim", key=f"mae_yes_del_ens_{eid}", use_container_width=True, type="primary"):
                            try:
                                base.delete_row("Ensaios", eid)
                                st.session_state.pop(confirm_del_key, None)
                                st.success("✅ Ensaio apagado!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro: {ex}")
                        if st.button("❌ Não", key=f"mae_no_del_ens_{eid}", use_container_width=True):
                            st.session_state[confirm_del_key] = False
                            st.rerun()
                    else:
                        if st.button("🗑️ Apagar", key=f"mae_del_ens_{eid}", use_container_width=True):
                            st.session_state[confirm_del_key] = True
                            st.rerun()

                if st.session_state.get(f"mae_show_canc_{eid}", False) and datas_canc:
                    st.markdown("**🚫 Datas Canceladas (clica para repor):**")
                    for dc in sorted(datas_canc):
                        if st.button(f"↩️ Repor {dc}", key=f"mae_repor_{eid}_{dc}", use_container_width=True):
                            try:
                                novas = datas_canc - {dc}
                                base.update_row("Ensaios", eid, {
                                    "Datas Canceladas": ", ".join(sorted(novas))
                                })
                                st.success(f"✅ Ensaio de {dc} reposto!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro: {ex}")


# ============================================
# RENDER PRINCIPAL
# ============================================

def render(base, user):
    st.title("🎼 Painel do Maestro")

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
    "🎼 Reportório",
    "📅 Agenda de Eventos",
    "🥁 Ensaios",
    "🖼️ Galeria",
    "💬 Mensagens",
    "🎂 Aniversários",
    "👥 Alunos",
    "🎺 Músicos"
])


    # ========================================
    # TAB 1: REPORTÓRIO
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
            5. **Cole** esse link no campo "Link" ao adicionar a obra

            ---

            #### 📄 **Para adicionar partitura em PDF:**
            **Opção 1 - Se o PDF está na internet:**
            1. **Abra** a página onde está o PDF
            2. **Clique com o botão direito** no link do PDF
            3. Escolha **"Copiar endereço do link"**
            4. **Cole** no campo "Link"

            **Opção 2 - Se o PDF está no seu computador:**
            1. **Carregue** o PDF para o Google Drive
            2. **Clique com botão direito** no ficheiro
            3. Escolha **"Obter link"** e ative "Qualquer pessoa com o link pode ver"
            4. **Copie** o link e **cole** no campo "Link"
            """)

        with st.expander("➕ Adicionar Nova Obra", expanded=False):
            with st.form("add_repertorio"):
                nome_obra  = st.text_input("Nome da Obra*",  placeholder="Ex: Radetzky March")
                compositor = st.text_input("Compositor*",    placeholder="Ex: Johann Strauss")
                link       = st.text_input("Link (YouTube ou Partitura)", placeholder="https://...")

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
                                        elif '.pdf' in lnk.lower() or 'drive.google' in lnk.lower():
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
            eventos   = get_eventos_cached()
            presencas = get_presencas_cached()
            musicos   = get_musicos_cached()

            if not eventos:
                st.info("📭 Nenhum evento agendado")
            else:
                def _data_sort(ev):
                    try:
                        return datetime.strptime(str(ev.get('Data', ''))[:10], "%Y-%m-%d").date()
                    except Exception:
                        return datetime.max.date()

                eventos = sorted(eventos, key=_data_sort)

                for e in eventos:
                    eid = e['_id']
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
                        presencas_evento = [p for p in presencas if p.get('EventoID') == eid]

                        if presencas_evento:
                            vao       = len([p for p in presencas_evento if p.get('Resposta') == 'Vou'])
                            nao_vao   = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vou'])
                            talvez    = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
                            pendentes = len(musicos) - len(presencas_evento)
                            cs1, cs2, cs3, cs4 = st.columns(4)
                            cs1.metric("✅ Vão",       vao)
                            cs2.metric("❌ Não Vão",   nao_vao)
                            cs3.metric("❓ Talvez",    talvez)
                            cs4.metric("⏳ Pendentes", pendentes)
                        else:
                            st.info("⏳ Sem respostas ainda")

                        if musicos:
                            st.divider()
                            respostas_dict = {}
                            for p in presencas_evento:
                                up = p.get('Username')
                                if up:
                                    respostas_dict[str(up).lower().strip()] = p.get('Resposta')

                            lista_musicos = []
                            for m in musicos:
                                ur  = m.get('Username')
                                un  = str(ur).lower().strip() if ur and str(ur).strip() else str(m.get('Nome', '')).lower().strip()
                                ir  = m.get('Instrumento')
                                ins = str(ir).strip() if ir and str(ir).strip() else "Não definido"
                                lista_musicos.append({
                                    'Nome':        m.get('Nome', 'Desconhecido'),
                                    'Instrumento': ins,
                                    'Resposta':    respostas_dict.get(un, 'Pendente')
                                })

                            df_musicos = pd.DataFrame(lista_musicos).sort_values(['Instrumento', 'Nome'])

                            filtro_resp = st.multiselect(
                                "Filtrar por resposta:",
                                options=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                default=['Vou', 'Não Vou', 'Talvez', 'Pendente'],
                                key=f"filtro_resp_maestro_{eid}"
                            )
                            df_f = df_musicos[df_musicos['Resposta'].isin(filtro_resp)].copy()
                            df_f['Estado'] = df_f['Resposta'].apply(
                                lambda r: {'Vou': '✅ Vou', 'Não Vou': '❌ Não Vou', 'Talvez': '❓ Talvez'}.get(r, '⏳ Pendente')
                            )
                            st.dataframe(df_f[['Nome', 'Instrumento', 'Estado']],
                                         use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

    # ========================================
    # TAB 3: ENSAIOS
    # ========================================
    with t3:
        st.subheader("🥁 Gestão de Ensaios")
        try:
            ensaios = base.list_rows("Ensaios")
            faltas  = get_faltas_ensaios_cached()
            musicos = get_musicos_cached()
        except Exception as ex:
            st.error(f"Erro ao carregar ensaios: {ex}")
            ensaios, faltas, musicos = [], [], []

        sub1, sub2 = st.tabs(["📅 Calendário", "⚙️ Gerir Ensaios"])
        with sub1:
            if not ensaios:
                st.info("📭 Nenhum ensaio criado. Vai a **⚙️ Gerir Ensaios** para criar.")
            else:
                _render_calendario_maestro(base, ensaios, faltas, musicos)
        with sub2:
            _render_gestao_ensaios_maestro(base, ensaios, faltas, musicos)

    # ========================================
    # TAB 4: GALERIA
    # ========================================
    with t4:
        st.subheader("🖼️ Galeria de Eventos")
        try:
            eventos_gal        = get_eventos_cached()
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
    # TAB 5: MENSAGENS
    # ========================================
    with t5:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=False)

    # ========================================
    # TAB 6: ANIVERSÁRIOS
    # ========================================
    with t6:
        st.subheader("🎂 Aniversários")
        try:
            musicos = get_musicos_cached()
            if not musicos:
                st.info("📭 Sem dados de músicos")
            else:
                hoje       = datetime.now().date()
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
                            'nome':          m.get('Nome', 'Desconhecido'),
                            'data_aniversario': aniv,
                            'dias_faltam':   (aniv - hoje).days,
                            'idade':         hoje.year - data_nasc.year,
                            'instrumento':   m.get('Instrumento', 'ND')
                        })
                aniversarios.sort(key=lambda x: x['dias_faltam'])

                if not aniversarios:
                    st.info("Não há aniversários nos próximos 15 dias")
                else:
                    st.caption(f"{len(aniversarios)} aniversário(s) nos próximos 15 dias")
                    for aniv in aniversarios:
                        dias = aniv['dias_faltam']
                        emoji, msg = ('🎉', 'HOJE!') if dias == 0 else \
                                     ('🔔', 'Amanhã') if dias == 1 else \
                                     ('📅', f"Em {dias} dias")
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"{emoji} **{aniv['nome']}** — {msg}")
                            st.caption(f"{formatar_data_pt(str(aniv['data_aniversario']))} · {aniv['idade']} anos · {aniv['instrumento']}")
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

    # ========================================
    # TAB 7: ALUNOS
    # ========================================
    with t7:
        st.subheader("👥 Alunos da Escola")

        # --- Carregar lista de professores da BD ---
        try:
            lista_professores = base.list_rows("Professores")
            nomes_professores = [""] + sorted([
                str(p.get("Nome", "")).strip()
                for p in lista_professores
                if str(p.get("Nome", "")).strip()
            ])
        except Exception:
            lista_professores = []
            nomes_professores = [""]

        # --- Gerir Professores ---
        with st.expander("👨‍🏫 Gerir Lista de Professores", expanded=False):
            col_add, col_list = st.columns([1, 2])

            with col_add:
                st.markdown("**Adicionar Professor**")
                with st.form("form_add_professor"):
                    novo_prof_nome  = st.text_input("Nome*", placeholder="Ex: Prof. António")
                    novo_prof_inst  = st.text_input("Instrumento", placeholder="Ex: Clarinete, Trompete")
                    novo_prof_email = st.text_input("Email", placeholder="")
                    novo_prof_tel   = st.text_input("Telefone", placeholder="")
                    if st.form_submit_button("➕ Adicionar", use_container_width=True, type="primary"):
                        if not novo_prof_nome.strip():
                            st.error("O nome é obrigatório")
                        else:
                            try:
                                base.append_row("Professores", {
                                    "Nome":        novo_prof_nome.strip(),
                                    "Instrumento": novo_prof_inst.strip(),
                                    "Email":       novo_prof_email.strip(),
                                    "Telefone":    novo_prof_tel.strip(),
                                })
                                st.success(f"✅ Professor {novo_prof_nome} adicionado!")
                                st.rerun()
                            except Exception as ep:
                                st.error(f"Erro: {ep}")

            with col_list:
                st.markdown("**Professores Registados**")
                if not lista_professores:
                    st.info("Nenhum professor registado ainda.")
                else:
                    for p in lista_professores:
                        pid    = p.get("_id", "")
                        pnome  = str(p.get("Nome", "") or "")
                        pinst  = str(p.get("Instrumento", "") or "---")
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.write(f"👨‍🏫 **{pnome}** — {pinst}")
                        with col_b:
                            confirm_key_p = f"confirm_del_prof_{pid}"
                            if st.session_state.get(confirm_key_p, False):
                                if st.button("✅", key=f"yes_del_prof_{pid}", help="Confirmar"):
                                    try:
                                        base.delete_row("Professores", pid)
                                        st.session_state.pop(confirm_key_p, None)
                                        st.success("Removido!")
                                        st.rerun()
                                    except Exception as ep:
                                        st.error(f"Erro: {ep}")
                            else:
                                if st.button("🗑️", key=f"del_prof_{pid}", help="Remover professor"):
                                    st.session_state[confirm_key_p] = True
                                    st.rerun()

        st.divider()

        # --- Adicionar Novo Aluno ---
        with st.expander("➕ Adicionar Novo Aluno", expanded=False):
            with st.form("form_mae_novo_aluno"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome     = st.text_input("Nome Completo*", placeholder="Ex: João Silva")
                    novo_telefone = st.text_input("Telefone", placeholder="Ex: 912345678")
                    novo_email    = st.text_input("Email", placeholder="Ex: joao@email.com")
                    novo_morada   = st.text_input("Morada", placeholder="Ex: Rua X, Lisboa")
                    novo_encarr   = st.text_input("Encarregado de Educacao", placeholder="Ex: Maria Silva")
                with col2:
                    novo_instrumento = st.text_input("Instrumento Pretendido", placeholder="Ex: Clarinete")
                    novo_polo        = st.selectbox("Pólo da Escola", ["", "Algés", "Oeiras", "Outro"])
                    novo_professor   = st.selectbox(
                        "Professor de Instrumento",
                        options=nomes_professores,
                        help="Deixar vazio se o aluno ainda só tem Formação Musical"
                    )
                    try:
                        novo_nascimento = st.date_input("Data de Nascimento", value=None,
                                                        min_value=datetime(1920, 1, 1).date(),
                                                        max_value=datetime.now().date())
                    except Exception:
                        novo_nascimento = None
                    try:
                        novo_inicio = st.date_input("Data de Ingresso", value=datetime.now().date(),
                                                    min_value=datetime(1900, 1, 1).date(),
                                                    max_value=datetime.now().date())
                    except Exception:
                        novo_inicio = datetime.now().date()
                    novo_obs = st.text_area("Observações", placeholder="Notas adicionais...", height=80)

                if not novo_professor:
                    st.caption("ℹ️ Sem professor atribuído — aluno em Formação Musical")

                st.caption("* Campos obrigatórios")
                if st.form_submit_button("✅ Adicionar Aluno", use_container_width=True, type="primary"):
                    if not novo_nome.strip():
                        st.error("⚠️ O nome é obrigatório")
                    else:
                        try:
                            dados_aluno = {
                                "Nome":                    novo_nome.strip(),
                                "Telefone":                novo_telefone.strip() if novo_telefone else "",
                                "Email":                   novo_email.strip() if novo_email else "",
                                "Morada":                  novo_morada.strip() if novo_morada else "",
                                "Encarregado de Educacao": novo_encarr.strip() if novo_encarr else "",
                                "Instrumento Pretendido":  novo_instrumento.strip() if novo_instrumento else "",
                                "Pólo da escola":          novo_polo if novo_polo else "",
                                "Professor":               novo_professor if novo_professor else "",
                                "Obs":                     novo_obs.strip() if novo_obs else "",
                            }
                            if novo_nascimento:
                                dados_aluno["Data de Nascimento"] = str(novo_nascimento)
                            if novo_inicio:
                                dados_aluno["Data de Ingresso na ..."] = str(novo_inicio)
                            base.append_row("Alunos", dados_aluno)
                            st.success(f"✅ Aluno **{novo_nome}** adicionado!")
                            st.rerun()
                        except Exception as e_add:
                            st.error(f"Erro: {e_add}")

        st.divider()

        # --- Lista de Alunos ---
        try:
            alunos = base.list_rows("Alunos")
            if not alunos:
                st.info("📭 Nenhum aluno registado")
            else:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total de Alunos", len(alunos))
                polos = [str(a.get("Pólo da escola", "") or "").strip() for a in alunos]
                col2.metric("Pólo Algés",  sum(1 for p in polos if "algés" in p.lower() or "alges" in p.lower()))
                col3.metric("Pólo Oeiras", sum(1 for p in polos if "oeiras" in p.lower()))
                col4.metric("Com Professor", sum(1 for a in alunos if str(a.get("Professor", "") or "").strip()))

                st.divider()

                col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                with col_p1:
                    pesquisa = st.text_input("🔍 Pesquisar aluno", placeholder="Nome, instrumento ou professor...")
                with col_p2:
                    filtro_polo = st.selectbox("Filtrar por pólo", ["Todos", "Algés", "Oeiras", "Outro", "Sem pólo"])
                with col_p3:
                    filtro_prof = st.selectbox("Professor", ["Todos", "Com professor", "Só Formação Musical"])

                alunos_filtrados = alunos
                if pesquisa.strip():
                    termo = pesquisa.strip().lower()
                    alunos_filtrados = [
                        a for a in alunos_filtrados
                        if termo in str(a.get("Nome", "")).lower()
                        or termo in str(a.get("Instrumento Pretendido", "")).lower()
                        or termo in str(a.get("Professor", "")).lower()
                        or termo in str(a.get("Encarregado de Educacao", "")).lower()
                    ]
                if filtro_polo != "Todos":
                    if filtro_polo == "Sem pólo":
                        alunos_filtrados = [a for a in alunos_filtrados if not str(a.get("Pólo da escola", "") or "").strip()]
                    else:
                        alunos_filtrados = [
                            a for a in alunos_filtrados
                            if filtro_polo.lower() in str(a.get("Pólo da escola", "") or "").lower()
                        ]
                if filtro_prof == "Com professor":
                    alunos_filtrados = [a for a in alunos_filtrados if str(a.get("Professor", "") or "").strip()]
                elif filtro_prof == "Só Formação Musical":
                    alunos_filtrados = [a for a in alunos_filtrados if not str(a.get("Professor", "") or "").strip()]

                st.caption(f"A mostrar {len(alunos_filtrados)} de {len(alunos)} alunos")
                st.divider()

                for a in alunos_filtrados:
                    aid        = a.get("_id", "")
                    aluno_nome = a.get("Nome", "Sem nome")
                    aluno_inst = a.get("Instrumento Pretendido", "---")
                    aluno_polo = a.get("Pólo da escola", "---")
                    aluno_prof = str(a.get("Professor", "") or "")
                    fase_label = f"👨‍🏫 {aluno_prof}" if aluno_prof else "🎼 Formação Musical"

                    edit_key_a = f"mae_edit_aluno_{aid}"
                    if edit_key_a not in st.session_state:
                        st.session_state[edit_key_a] = False

                    with st.expander(f"👤 {aluno_nome} — {aluno_inst} | {aluno_polo} | {fase_label}"):
                        if st.session_state[edit_key_a]:
                            st.markdown("#### ✏️ Editar Aluno")
                            with st.form(f"form_mae_edit_aluno_{aid}"):
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    e_nome     = st.text_input("Nome Completo*", value=str(a.get("Nome", "") or ""))
                                    e_telefone = st.text_input("Telefone", value=str(a.get("Telefone", "") or ""))
                                    e_email    = st.text_input("Email", value=str(a.get("Email", "") or ""))
                                    e_morada   = st.text_input("Morada", value=str(a.get("Morada", "") or ""))
                                    e_encarr   = st.text_input("Encarregado de Educacao",
                                                               value=str(a.get("Encarregado de Educacao", "") or ""))
                                with ec2:
                                    e_instr  = st.text_input("Instrumento Pretendido",
                                                             value=str(a.get("Instrumento Pretendido", "") or ""))
                                    polos_opts = ["", "Algés", "Oeiras", "Outro"]
                                    polo_atual = str(a.get("Pólo da escola", "") or "")
                                    e_polo   = st.selectbox("Pólo da Escola", polos_opts,
                                                            index=polos_opts.index(polo_atual) if polo_atual in polos_opts else 0)
                                    prof_atual = str(a.get("Professor", "") or "")
                                    e_prof = st.selectbox(
                                        "Professor de Instrumento",
                                        options=nomes_professores,
                                        index=nomes_professores.index(prof_atual) if prof_atual in nomes_professores else 0,
                                        help="Deixar vazio se o aluno ainda só tem Formação Musical"
                                    )
                                    nasc_raw = a.get("Data de Nascimento")
                                    try:
                                        nasc_val = datetime.strptime(str(nasc_raw)[:10], "%Y-%m-%d").date() if nasc_raw else None
                                    except Exception:
                                        nasc_val = None
                                    e_nasc = st.date_input("Data de Nascimento", value=nasc_val,
                                                           min_value=datetime(1920, 1, 1).date(),
                                                           max_value=datetime.now().date())
                                    ing_raw = a.get("Data de Ingresso na ...")
                                    try:
                                        ing_val = datetime.strptime(str(ing_raw)[:10], "%Y-%m-%d").date() if ing_raw else datetime.now().date()
                                    except Exception:
                                        ing_val = datetime.now().date()
                                    e_ing = st.date_input("Data de Ingresso", value=ing_val,
                                                          min_value=datetime(1900, 1, 1).date(),
                                                          max_value=datetime.now().date())
                                    e_obs = st.text_area("Observações", value=str(a.get("Obs", "") or ""), height=80)

                                if not e_prof:
                                    st.caption("ℹ️ Sem professor — aluno em Formação Musical")

                                col_s, col_c = st.columns(2)
                                with col_s:
                                    guardar_a  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                                with col_c:
                                    cancelar_a = st.form_submit_button("❌ Cancelar", use_container_width=True)

                                if guardar_a:
                                    if not e_nome.strip():
                                        st.error("⚠️ O nome é obrigatório")
                                    else:
                                        try:
                                            base.update_row("Alunos", aid, {
                                                "Nome":                    e_nome.strip(),
                                                "Telefone":                e_telefone.strip(),
                                                "Email":                   e_email.strip(),
                                                "Morada":                  e_morada.strip(),
                                                "Encarregado de Educacao": e_encarr.strip(),
                                                "Instrumento Pretendido":  e_instr.strip(),
                                                "Pólo da escola":          e_polo,
                                                "Professor":               e_prof if e_prof else "",
                                                "Data de Nascimento":      str(e_nasc) if e_nasc else "",
                                                "Data de Ingresso na ...": str(e_ing) if e_ing else "",
                                                "Obs":                     e_obs.strip(),
                                            })
                                            st.session_state[edit_key_a] = False
                                            st.success("✅ Aluno atualizado!")
                                            st.rerun()
                                        except Exception as e_upd:
                                            st.error(f"Erro: {e_upd}")
                                if cancelar_a:
                                    st.session_state[edit_key_a] = False
                                    st.rerun()
                        else:
                            col1, col2, col3 = st.columns([3, 3, 1])
                            with col1:
                                st.write(f"📞 **Telefone:** {a.get('Telefone') or '---'}")
                                st.write(f"📧 **Email:** {a.get('Email') or '---'}")
                                st.write(f"🏠 **Morada:** {a.get('Morada') or '---'}")
                                st.write(f"👨‍👩‍👦 **Enc. Educação:** {a.get('Encarregado de Educacao') or '---'}")
                            with col2:
                                nasc = converter_data_robusta(a.get("Data de Nascimento"))
                                ing  = converter_data_robusta(a.get("Data de Ingresso na ..."))
                                st.write(f"🎂 **Nascimento:** {formatar_data_pt(str(nasc)) if nasc else '---'}")
                                st.write(f"📅 **Ingresso:** {formatar_data_pt(str(ing)) if ing else '---'}")
                                st.write(f"🎵 **Instrumento:** {a.get('Instrumento Pretendido') or '---'}")
                                if aluno_prof:
                                    st.write(f"👨‍🏫 **Professor:** {aluno_prof}")
                                else:
                                    st.write("🎼 **Fase:** Formação Musical")
                                if a.get("Obs"):
                                    st.write(f"📝 **Obs:** {a.get('Obs')}")
                            with col3:
                                if st.button("✏️ Editar", key=f"mae_btn_edit_a_{aid}", use_container_width=True):
                                    st.session_state[edit_key_a] = True
                                    st.rerun()
                                confirm_del_a = f"mae_confirm_del_aluno_{aid}"
                                if st.session_state.get(confirm_del_a, False):
                                    st.warning("Apagar?")
                                    if st.button("✅ Sim", key=f"mae_yes_del_a_{aid}",
                                                 use_container_width=True, type="primary"):
                                        try:
                                            base.delete_row("Alunos", aid)
                                            st.session_state.pop(confirm_del_a, None)
                                            st.success("✅ Removido!")
                                            st.rerun()
                                        except Exception as e_del:
                                            st.error(f"Erro: {e_del}")
                                    if st.button("❌ Não", key=f"mae_no_del_a_{aid}", use_container_width=True):
                                        st.session_state[confirm_del_a] = False
                                        st.rerun()
                                else:
                                    if st.button("🗑️ Apagar", key=f"mae_del_a_{aid}", use_container_width=True):
                                        st.session_state[confirm_del_a] = True
                                        st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao carregar alunos: {e}")

    # ========================================
    # TAB 8: MÚSICOS (consulta)
    # ========================================
    with t8:
        st.subheader("🎺 Músicos da Banda")

        try:
            musicos = get_musicos_cached()

            if not musicos:
                st.info("📭 Sem músicos registados")
            else:
                # Métricas rápidas
                instrumentos = [str(m.get("Instrumento", "") or "").strip() for m in musicos]
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Músicos", len(musicos))
                col2.metric("Instrumentos Diferentes", len(set(i for i in instrumentos if i)))
                col3.metric("Com Instrumento Próprio",
                            sum(1 for m in musicos if str(m.get("Instrumento Proprio", "") or "").strip()))

                st.divider()

                # Pesquisa e filtros
                col_p1, col_p2 = st.columns([3, 1])
                with col_p1:
                    pesquisa_m = st.text_input("🔍 Pesquisar músico",
                                               placeholder="Nome, instrumento ou username...")
                with col_p2:
                    lista_inst = sorted(set(i for i in instrumentos if i))
                    filtro_inst = st.selectbox("Instrumento", ["Todos"] + lista_inst)

                musicos_f = musicos
                if pesquisa_m.strip():
                    termo = pesquisa_m.strip().lower()
                    musicos_f = [
                        m for m in musicos_f
                        if termo in str(m.get("Nome", "")).lower()
                        or termo in str(m.get("Instrumento", "")).lower()
                        or termo in str(m.get("Username", "")).lower()
                    ]
                if filtro_inst != "Todos":
                    musicos_f = [
                        m for m in musicos_f
                        if str(m.get("Instrumento", "") or "").strip() == filtro_inst
                    ]

                # Ordenar por instrumento e nome
                musicos_f = sorted(musicos_f, key=lambda m: (
                    str(m.get("Instrumento", "") or ""),
                    str(m.get("Nome", "") or "")
                ))

                st.caption(f"A mostrar {len(musicos_f)} de {len(musicos)} músicos")
                st.divider()

                for m in musicos_f:
                    nome     = str(m.get("Nome", "---") or "---")
                    inst     = str(m.get("Instrumento", "---") or "---")
                    username = str(m.get("Username", "") or "")
                    morada   = str(m.get("Morada", "") or "")
                    email    = str(m.get("Email", "") or "")
                    telefone = str(m.get("Telefone", "") or "")
                    marca    = str(m.get("Marca", "") or "")
                    modelo   = str(m.get("Modelo", "") or "")
                    num_serie = str(m.get("Num Serie", "") or "")
                    inst_proprio = str(m.get("Instrumento Proprio", "") or "")
                    data_nasc = converter_data_robusta(m.get("Data de Nascimento"))
                    data_ing  = converter_data_robusta(m.get("Data Ingresso Banda"))
                    obs       = str(m.get("Obs", "") or "")

                    inst_label = f"🎵 {inst}" if inst != "---" else "🎵 Sem instrumento"

                    with st.expander(f"🎺 {nome} — {inst_label}"):
                        col1, col2, col3 = st.columns([3, 3, 2])

                        with col1:
                            st.write(f"👤 **Username:** {username or '---'}")
                            st.write(f"📞 **Telefone:** {telefone or '---'}")
                            st.write(f"📧 **Email:** {email or '---'}")
                            st.write(f"🏠 **Morada:** {morada or '---'}")

                        with col2:
                            st.write(f"🎂 **Nascimento:** {formatar_data_pt(str(data_nasc)) if data_nasc else '---'}")
                            st.write(f"📅 **Ingresso na Banda:** {formatar_data_pt(str(data_ing)) if data_ing else '---'}")
                            if obs:
                                st.write(f"📝 **Obs:** {obs}")

                        with col3:
                            st.markdown("**🎷 Instrumento**")
                            st.write(f"Tipo: **{inst}**")
                            if marca:
                                st.write(f"Marca: {marca}")
                            if modelo:
                                st.write(f"Modelo: {modelo}")
                            if num_serie:
                                st.write(f"Nº Série: {num_serie}")
                            if inst_proprio:
                                st.success("✅ Instrumento próprio")
                            else:
                                st.caption("🏛️ Instrumento da banda")

                        # Foto se existir
                        foto = m.get("Foto")
                        if foto:
                            try:
                                if isinstance(foto, list) and foto:
                                    st.image(foto[0], width=100)
                                elif isinstance(foto, str) and foto.startswith("http"):
                                    st.image(foto, width=100)
                            except Exception:
                                pass

        except Exception as e:
            st.error(f"❌ Erro ao carregar músicos: {e}")
