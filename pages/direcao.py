"""
Interface da Direção - Portal BMO
"""
import streamlit as st
import pandas as pd
import calendar
from helpers import formatar_data_pt, converter_data_robusta
from datetime import datetime, timedelta, date
from cache import (
    get_musicos_cached,
    get_eventos_cached,
    get_presencas_cached,
    get_faltas_ensaios_cached,
    get_aulas_cached,
    get_utilizadores_cached
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


def _render_calendario_ensaios_admin(base, ensaios, faltas, musicos):
    hoje = date.today()
    dark = st.session_state.get('dark_mode', True)
    card_bg    = '#2a2a2a' if dark else '#fafafa'
    card_color = '#f5f5f5' if dark else '#1a1a1a'

    if 'adm_ens_ano' not in st.session_state:
        st.session_state['adm_ens_ano'] = hoje.year
    if 'adm_ens_mes' not in st.session_state:
        st.session_state['adm_ens_mes'] = hoje.month

    ano = st.session_state['adm_ens_ano']
    mes = st.session_state['adm_ens_mes']

    col_prev, col_titulo, col_hoje_btn, col_ref, col_next = st.columns([1, 3, 1, 1, 1])
    with col_prev:
        if st.button("◀ Anterior", use_container_width=True, key="adm_ens_prev"):
            if mes == 1:
                st.session_state['adm_ens_mes'] = 12
                st.session_state['adm_ens_ano'] = ano - 1
            else:
                st.session_state['adm_ens_mes'] = mes - 1
            st.rerun()
    with col_titulo:
        st.markdown(
            f"<h3 style='text-align:center;margin:0;padding:4px 0'>"
            f"{_MESES_PT[mes]} {ano}</h3>",
            unsafe_allow_html=True
        )
    with col_hoje_btn:
        if st.button("📅 Hoje", use_container_width=True, key="adm_ens_hoje"):
            st.session_state.update({'adm_ens_ano': hoje.year, 'adm_ens_mes': hoje.month})
            st.rerun()
    with col_ref:
        if st.button("🔄", use_container_width=True, key="adm_ens_refresh"):
            st.rerun()
    with col_next:
        if st.button("Próximo ▶", use_container_width=True, key="adm_ens_next"):
            if mes == 12:
                st.session_state['adm_ens_mes'] = 1
                st.session_state['adm_ens_ano'] = ano + 1
            else:
                st.session_state['adm_ens_mes'] = mes + 1
            st.rerun()

    ensaios_por_dia = _get_ensaios_do_mes(ensaios, ano, mes)

    cal_bg      = '#1e1e1e' if dark else '#ffffff'
    cal_border  = '#444'    if dark else '#ddd'
    cal_vazio   = '#2a2a2a' if dark else '#f5f5f5'
    cal_fds     = '#252525' if dark else '#fafafa'
    cal_hoje_bg = '#2d1a0e' if dark else '#fff8f5'
    num_color   = '#aaa'    if dark else '#555'

    css = f"""<style>
    .bmo-adm{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:8px}}
    .bmo-adm th{{background:#ff6b35;color:#fff;padding:8px 4px;text-align:center;font-weight:bold;font-size:.82rem}}
    .bmo-adm td{{border:1px solid {cal_border};padding:4px;vertical-align:top;height:90px;width:14.28%;font-size:.75rem;background:{cal_bg}}}
    .bmo-adm td.vazio{{background:{cal_vazio}}}
    .bmo-adm td.e-hoje{{background:{cal_hoje_bg};border:2px solid #ff6b35!important}}
    .bmo-adm td.fim-semana{{background:{cal_fds}}}
    .adm-num{{font-weight:bold;font-size:.88rem;color:{num_color};margin-bottom:2px}}
    .adm-num-hoje{{color:#ff6b35;font-size:.95rem;font-weight:bold}}
    .adm-pill{{display:block;padding:2px 5px;margin:1px 0;border-radius:4px;font-size:.66rem;
               color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    </style>"""

    html = css + '<table class="bmo-adm"><thead><tr>'
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
                         f'<div class="{"adm-num-hoje" if is_hoje else "adm-num"}">{dia}</div>')
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
                        html += (f'<span class="adm-pill" style="background:#ff6b35" '
                                 f'title="{nome}">'
                                 f'🥁 {hora} {nome[:8]}{badge}</span>')
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
        key="adm_ens_dia"
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
                cancel_key = f"cancel_dia_{eid}_{data_sel_str}"
                if st.button(f"🚫 Cancelar ensaio de {dia_sel} {_MESES_PT[mes]}",
                             key=cancel_key, use_container_width=True):
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


def _render_gestao_ensaios(base, ensaios, faltas, musicos):
    """Sub-secção de criação e edição de ensaios"""

    with st.expander("➕ Criar Novo Ensaio", expanded=False):
        with st.form("form_novo_ensaio"):
            col1, col2 = st.columns(2)
            with col1:
                novo_nome  = st.text_input("Nome do Ensaio*", placeholder="Ex: Ensaio Semanal")
                novo_tipo  = st.selectbox("Tipo*", ["Semanal", "Período", "Pontual"])
                novo_hora  = st.text_input("Hora*", placeholder="Ex: 21:00")
                novo_local = st.text_input("Local", placeholder="Ex: Sede da Banda")
            with col2:
                dias_opts  = ["", "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                              "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
                novo_dia   = st.selectbox("Dia da Semana (Semanal/Período)", options=dias_opts)
                novo_data  = st.date_input("Data / Data de Início*", value=date.today())
                novo_data_fim = st.date_input(
                    "Data de Fim (só para Período)",
                    value=date.today() + timedelta(days=90)
                )

            st.caption("* Campos obrigatórios")
            if st.form_submit_button("✅ Criar Ensaio", use_container_width=True, type="primary"):
                if not novo_nome.strip() or not novo_hora.strip():
                    st.error("⚠️ Nome e Hora são obrigatórios")
                elif novo_tipo in ('Semanal', 'Período') and not novo_dia:
                    st.error("⚠️ Para ensaios Semanal ou Período é necessário escolher o Dia da Semana")
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

        edit_key = f"edit_ensaio_{eid}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        with st.expander(f"{icon} {nome} — {hora} | {subtitulo}"):
            if st.session_state[edit_key]:
                st.markdown("#### ✏️ Editar Ensaio")
                with st.form(f"form_edit_ensaio_{eid}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_nome  = st.text_input("Nome*", value=nome)
                        e_tipo  = st.selectbox("Tipo*", ["Semanal", "Período", "Pontual"],
                                               index=["Semanal", "Período", "Pontual"].index(tipo)
                                               if tipo in ["Semanal", "Período", "Pontual"] else 0)
                        e_hora  = st.text_input("Hora*", value=hora)
                        e_local = st.text_input("Local", value=local)
                    with ec2:
                        dias_opts2 = ["", "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                                      "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"]
                        e_dia = st.selectbox("Dia da Semana",
                                             options=dias_opts2,
                                             index=dias_opts2.index(dia) if dia in dias_opts2 else 0)
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
                    if st.button("✏️ Editar", key=f"btn_edit_ens_{eid}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()

                    if tipo in ('Semanal', 'Período') and datas_canc:
                        if st.button("📋 Ver cancelamentos", key=f"ver_canc_{eid}", use_container_width=True):
                            st.session_state[f"show_canc_{eid}"] = not st.session_state.get(f"show_canc_{eid}", False)
                            st.rerun()

                    confirm_del_key = f"confirm_del_ens_{eid}"
                    if st.session_state.get(confirm_del_key, False):
                        st.warning("Apagar este ensaio?")
                        if st.button("✅ Sim", key=f"yes_del_ens_{eid}", use_container_width=True, type="primary"):
                            try:
                                base.delete_row("Ensaios", eid)
                                st.session_state.pop(confirm_del_key, None)
                                st.success("✅ Ensaio apagado!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Erro: {ex}")
                        if st.button("❌ Não", key=f"no_del_ens_{eid}", use_container_width=True):
                            st.session_state[confirm_del_key] = False
                            st.rerun()
                    else:
                        if st.button("🗑️ Apagar", key=f"del_ens_{eid}", use_container_width=True):
                            st.session_state[confirm_del_key] = True
                            st.rerun()

                if st.session_state.get(f"show_canc_{eid}", False) and datas_canc:
                    st.markdown("**🚫 Datas Canceladas (clica para repor):**")
                    for dc in sorted(datas_canc):
                        if st.button(f"↩️ Repor {dc}", key=f"repor_{eid}_{dc}", use_container_width=True):
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

# ============================================
# HELPERS GALERIA
# ============================================

def _extrair_file_id(url):
    url = str(url).strip()
    if 'drive.google.com/file/d/' in url:
        try:
            return url.split('/file/d/')[1].split('/')[0]
        except Exception:
            return None
    if 'drive.google.com/open?id=' in url:
        try:
            return url.split('open?id=')[1].split('&')[0]
        except Exception:
            return None
    return None

def _url_imagem_direta(url):
    if not url:
        return None
    file_id = _extrair_file_id(url)
    if file_id:
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    return str(url).strip()


def render(base, user):
    st.title("📊 Painel da Direção")

   

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
                            get_eventos_cached.clear()
                            st.success(f"✅ Evento **{nome}** criado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        st.divider()

        try:
            eventos   = get_eventos_cached()
            presencas = get_presencas_cached()
            musicos   = get_musicos_cached()

            if not eventos:
                st.info("📭 Nenhum evento criado")
            else:
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
                                            get_eventos_cached.clear()
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
                                vao       = len([p for p in pres_evento if p.get('Resposta') == 'Vou'])
                                nao_vao   = len([p for p in pres_evento if p.get('Resposta') == 'Não Vou'])
                                talvez    = len([p for p in pres_evento if p.get('Resposta') == 'Talvez'])
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
                                        get_eventos_cached.clear()
                                        st.success("Evento removido!")
                                        st.rerun()
                                    except Exception as e_error:
                                        st.error(f"Erro: {e_error}")

                            st.divider()

                            if musicos:
                                st.subheader("🎼 Presenças por Músico")
                                pres_evento    = [p for p in presencas if p.get('EventoID') == e['_id']]
                                respostas_dict = {}
                                for p in pres_evento:
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
    # TAB 2: ENSAIOS
    # ========================================
    with t2:
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
                _render_calendario_ensaios_admin(base, ensaios, faltas, musicos)

                st.divider()
                hoje_m = date.today()
                total_faltas_mes = sum(
                    1 for f in faltas
                    if _sv(f.get('Data', ''))[:7] == hoje_m.strftime('%Y-%m')
                )
                c1, c2, c3 = st.columns(3)
                c1.metric("🥁 Ensaios configurados", len(ensaios))
                c2.metric("⚠️ Faltas este mês", total_faltas_mes)
                musicos_com_falta = len(set(
                    _sv(f.get('Username', ''))
                    for f in faltas
                    if _sv(f.get('Data', ''))[:7] == hoje_m.strftime('%Y-%m')
                ))
                c3.metric("👤 Músicos com falta", musicos_com_falta)

        with sub2:
            _render_gestao_ensaios(base, ensaios, faltas, musicos)

    # ========================================
    # TAB 3: INVENTÁRIO DE INSTRUMENTOS
    # ========================================
    with t3:
        st.subheader("🎷 Inventário de Instrumentos")
        try:
            musicos = get_musicos_cached()
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
    # TAB 4: ESCOLA DE MÚSICA
    # ========================================
    with t4:
        st.subheader("🏫 Aulas da Escola")
        try:
            aulas = get_aulas_cached()
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
    # TAB 5: STATUS GERAL
    # ========================================
    with t5:
        st.subheader("📊 Status dos Músicos")
        try:
            musicos = get_musicos_cached()
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
                col1.metric("Total Músicos",      len(status_list))
                col2.metric("✅ Fichas Completas", completos)
                col3.metric("⚠️ Incompletas",     len(status_list) - completos)
                st.divider()
                st.dataframe(df_status, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erro: {e}")

    # ========================================
    # TAB 6: MENSAGENS
    # ========================================
    with t6:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=True)

    # ========================================
    # TAB 7: ANIVERSÁRIOS
    # ========================================
    with t7:
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

    # ========================================
    # TAB 8: GESTÃO DE UTILIZADORES
    # ========================================
    with t8:
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
            utilizadores = get_utilizadores_cached()
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
                    users_nomes      = [f"{u.get('Nome')} ({u.get('Username')})" for u in utilizadores]
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
                            get_utilizadores_cached.clear()
                            st.success(f"✅ Password de **{user_row.get('Nome')}** resetada para '1234'!")
                            st.info("💡 O utilizador será obrigado a mudar a password no próximo login.")
                            st.rerun()
                        except Exception as e_reset:
                            st.error(f"❌ Erro ao resetar password: {e_reset}")
        except Exception as e:
            st.error(f"Erro ao carregar utilizadores: {e}")

    # ========================================
    # TAB 9: GESTÃO DE MÚSICOS
    # ========================================
    with t9:
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
                                "Telefone":    novo_telefone.strip()    if novo_telefone    else "",
                                "Email":       novo_email.strip()       if novo_email       else "",
                                "Morada":      novo_morada.strip()      if novo_morada      else "",
                                "Instrumento": novo_instrumento.strip() if novo_instrumento else "",
                                "Obs":         novo_obs.strip()         if novo_obs         else "",
                            }
                            if novo_nascimento:
                                dados_musico["Data de Nascimento"]  = str(novo_nascimento)
                            if novo_ingresso:
                                dados_musico["Data Ingresso Banda"] = str(novo_ingresso)
                            base.append_row("Musicos", dados_musico)
                            get_musicos_cached.clear()
                            st.success(f"✅ Músico **{novo_nome}** adicionado com sucesso!")
                            st.info("💡 Lembra-te de ir a **Utilizadores → Sincronizar Músicos** para criar a conta de acesso.")
                            st.rerun()
                        except Exception as e_add:
                            st.error(f"❌ Erro ao adicionar músico: {e_add}")

        st.divider()

        try:
            musicos = get_musicos_cached()
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
                                                "Nome":                edit_nome.strip(),
                                                "Telefone":            edit_telefone.strip(),
                                                "Email":               edit_email.strip(),
                                                "Morada":              edit_morada.strip(),
                                                "Instrumento":         edit_instrumento.strip(),
                                                "Obs":                 edit_obs.strip(),
                                                "Data de Nascimento":  str(edit_nasc)     if edit_nasc     else "",
                                                "Data Ingresso Banda": str(edit_ingresso) if edit_ingresso else "",
                                            })
                                            get_musicos_cached.clear()
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

    # ========================================
    # TAB 10: GALERIA
    # ========================================
    with t10:
        st.subheader("🖼️ Galeria de Eventos")
        try:
            eventos_gal = get_eventos_cached()
            if not eventos_gal:
                st.info("Nenhum evento registado.")
            else:
                com_cartaz = [e for e in eventos_gal if str(e.get('Cartaz', '') or '').strip()]
                sem_cartaz = [e for e in eventos_gal if not str(e.get('Cartaz', '') or '').strip()]

                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Eventos", len(eventos_gal))
                col2.metric("Com Cartaz", len(com_cartaz))
                col3.metric("Sem Cartaz", len(sem_cartaz))

                st.divider()

                if com_cartaz:
                    st.markdown("### 📸 Cartazes Disponíveis")
                    cols_gal = st.columns(3)
                    for i, ev in enumerate(com_cartaz):
                        eid      = ev['_id']
                        nome_ev  = ev.get('Nome do Evento', 'Evento')
                        data_ev  = formatar_data_pt(ev.get('Data', ''))
                        img_url  = _url_imagem_direta(ev.get('Cartaz', ''))
                        edit_key    = f"gal_edit_{eid}"
                        confirm_key = f"gal_confirm_rem_{eid}"

                        with cols_gal[i % 3]:
                            if img_url:
                                st.markdown(
                                    f'<img src="{img_url}" alt="{nome_ev}" '
                                    f'style="width:100%;border-radius:8px;margin-bottom:4px">',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.warning("⚠️ Cartaz indisponível")

                            st.caption(f"**{nome_ev}**  \n{data_ev}")

                            col_e, col_r = st.columns(2)
                            with col_e:
                                if st.button("✏️ Editar", key=f"gal_btn_edit_{eid}", use_container_width=True):
                                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                                    st.rerun()
                            with col_r:
                                if st.button("🗑️ Remover", key=f"gal_btn_rem_{eid}", use_container_width=True):
                                    st.session_state[confirm_key] = True
                                    st.rerun()

                            if st.session_state.get(confirm_key, False):
                                st.warning("Remover este cartaz?")
                                cc1, cc2 = st.columns(2)
                                with cc1:
                                    if st.button("Sim", key=f"gal_sim_rem_{eid}", use_container_width=True, type="primary"):
                                        try:
                                            base.update_row("Eventos", eid, {"Cartaz": ""})
                                            get_eventos_cached.clear()
                                            st.session_state.pop(confirm_key, None)
                                            st.success("Cartaz removido!")
                                            st.rerun()
                                        except Exception as ex:
                                            st.error(f"Erro: {ex}")
                                with cc2:
                                    if st.button("Não", key=f"gal_nao_rem_{eid}", use_container_width=True):
                                        st.session_state.pop(confirm_key, None)
                                        st.rerun()

                            if st.session_state.get(edit_key, False):
                                with st.form(f"form_gal_edit_{eid}"):
                                    nova_url = st.text_input(
                                        "Nova URL do Cartaz",
                                        value=str(ev.get('Cartaz', '') or ''),
                                        placeholder="https://drive.google.com/file/d/..."
                                    )
                                    col_s, col_c = st.columns(2)
                                    with col_s:
                                        guardar = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                                    with col_c:
                                        cancelar = st.form_submit_button("Cancelar", use_container_width=True)
                                    if guardar:
                                        try:
                                            base.update_row("Eventos", eid, {"Cartaz": nova_url.strip()})
                                            get_eventos_cached.clear()
                                            st.session_state[edit_key] = False
                                            st.success("✅ Cartaz atualizado!")
                                            st.rerun()
                                        except Exception as ex:
                                            st.error(f"Erro: {ex}")
                                    if cancelar:
                                        st.session_state[edit_key] = False
                                        st.rerun()

                if sem_cartaz:
                    st.divider()
                    st.markdown("### 📋 Eventos sem Cartaz")
                    for ev in sem_cartaz:
                        eid     = ev['_id']
                        nome_ev = ev.get('Nome do Evento', 'Evento')
                        data_ev = formatar_data_pt(ev.get('Data', ''))
                        with st.expander(f"📅 {data_ev} — {nome_ev}"):
                            with st.form(f"form_gal_add_{eid}"):
                                nova_url = st.text_input(
                                    "URL do Cartaz",
                                    placeholder="https://drive.google.com/file/d/..."
                                )
                                if st.form_submit_button("➕ Adicionar Cartaz", use_container_width=True, type="primary"):
                                    if not nova_url.strip():
                                        st.error("Introduza uma URL válida")
                                    else:
                                        try:
                                            base.update_row("Eventos", eid, {"Cartaz": nova_url.strip()})
                                            get_eventos_cached.clear()
                                            st.success(f"✅ Cartaz adicionado a '{nome_ev}'!")
                                            st.rerun()
                                        except Exception as ex:
                                            st.error(f"Erro: {ex}")

        except Exception as e:
            st.error(f"❌ Erro ao carregar galeria: {e}")
