"""
Interface do Maestro - Portal BMO
"""
import streamlit as st
import pandas as pd
import calendar
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta, date

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
                # Semanal, Período ou qualquer outro valor recorrente
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
                # Data Fim verificada SEMPRE que existir, independentemente do tipo
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

    # ---- Detalhe do dia ----
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

    # Métricas
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
    from app import (
        get_musicos_cached,
        get_eventos_cached,
        get_presencas_cached,
        get_faltas_ensaios_cached
    )
    st.title("🎼 Painel do Maestro")

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "🎼 Reportório",
        "📅 Agenda de Eventos",
        "🥁 Ensaios",
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
                            vao       = len([p for p in presencas_evento if p.get('Resposta') == 'Vou'])
                            nao_vao   = len([p for p in presencas_evento if p.get('Resposta') == 'Não Vou'])
                            talvez    = len([p for p in presencas_evento if p.get('Resposta') == 'Talvez'])
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
                                username_raw    = m.get('Username')
                                username        = str(username_raw).lower().strip() if username_raw and str(username_raw).strip() else str(m.get('Nome', '')).lower().strip()
                                instrumento_raw = m.get('Instrumento')
                                instrumento     = str(instrumento_raw).strip() if instrumento_raw and str(instrumento_raw).strip() else "Não definido"
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
