"""
Interface do Músico - Portal BMO
"""
import streamlit as st
import time
import calendar
from helpers import formatar_data_pt, converter_data_robusta
from seatable_conn import add_presenca
from datetime import datetime, date, timedelta

# ============================================
# CONSTANTES ENSAIOS
# ============================================
_DIAS_PT_MAP = {
    "Segunda-Feira": 0, "Terça-Feira": 1, "Quarta-Feira": 2,
    "Quinta-Feira": 3, "Sexta-Feira": 4, "Sábado": 5, "Domingo": 6,
}
_MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# ============================================
# HELPERS ENSAIOS
# ============================================

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
            elif tipo in ('Semanal', 'Período'):
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
                if tipo == 'Período':
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


def _render_calendario_ensaios(base, ensaios, faltas, user):
    hoje = date.today()
    dark = st.session_state.get('dark_mode', True)
    card_bg    = '#2a2a2a' if dark else '#fafafa'
    card_color = '#f5f5f5' if dark else '#1a1a1a'

    if 'ens_ano' not in st.session_state:
        st.session_state['ens_ano'] = hoje.year
    if 'ens_mes' not in st.session_state:
        st.session_state['ens_mes'] = hoje.month

    ano = st.session_state['ens_ano']
    mes = st.session_state['ens_mes']

    col_prev, col_titulo, col_hoje_btn, col_ref, col_next = st.columns([1, 3, 1, 1, 1])
    with col_prev:
        if st.button("◀ Anterior", use_container_width=True, key="ens_prev"):
            if mes == 1:
                st.session_state['ens_mes'] = 12
                st.session_state['ens_ano'] = ano - 1
            else:
                st.session_state['ens_mes'] = mes - 1
            st.rerun()
    with col_titulo:
        st.markdown(
            f"<h3 style='text-align:center;margin:0;padding:4px 0'>"
            f"{_MESES_PT[mes]} {ano}</h3>",
            unsafe_allow_html=True
        )
    with col_hoje_btn:
        if st.button("📅 Hoje", use_container_width=True, key="ens_hoje"):
            st.session_state.update({'ens_ano': hoje.year, 'ens_mes': hoje.month})
            st.rerun()
    with col_ref:
        if st.button("🔄", use_container_width=True, key="ens_refresh"):
            st.rerun()
    with col_next:
        if st.button("Próximo ▶", use_container_width=True, key="ens_next"):
            if mes == 12:
                st.session_state['ens_mes'] = 1
                st.session_state['ens_ano'] = ano + 1
            else:
                st.session_state['ens_mes'] = mes + 1
            st.rerun()

    ensaios_por_dia = _get_ensaios_do_mes(ensaios, ano, mes)

    # Set de faltas do músico neste mês: "EnsaioID_YYYY-MM-DD"
    faltas_set = set()
    for f in faltas:
        if _sv(f.get('Username', '')) == user['username']:
            faltas_set.add(f"{_sv(f.get('EnsaioID',''))}_{_sv(f.get('Data',''))[:10]}")

    # ---- CSS e HTML do calendário ----
    cal_bg      = '#1e1e1e' if dark else '#ffffff'
    cal_border  = '#444'    if dark else '#ddd'
    cal_vazio   = '#2a2a2a' if dark else '#f5f5f5'
    cal_fds     = '#252525' if dark else '#fafafa'
    cal_hoje_bg = '#2d1a0e' if dark else '#fff8f5'
    num_color   = '#aaa'    if dark else '#555'

    css = f"""<style>
    .bmo-ens{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:8px}}
    .bmo-ens th{{background:#ff6b35;color:#fff;padding:8px 4px;text-align:center;font-weight:bold;font-size:.82rem}}
    .bmo-ens td{{border:1px solid {cal_border};padding:4px;vertical-align:top;height:90px;width:14.28%;font-size:.75rem;background:{cal_bg}}}
    .bmo-ens td.vazio{{background:{cal_vazio}}}
    .bmo-ens td.e-hoje{{background:{cal_hoje_bg};border:2px solid #ff6b35!important}}
    .bmo-ens td.fim-semana{{background:{cal_fds}}}
    .ens-num{{font-weight:bold;font-size:.88rem;color:{num_color};margin-bottom:2px}}
    .ens-num-hoje{{color:#ff6b35;font-size:.95rem;font-weight:bold}}
    .ens-pill{{display:block;padding:2px 5px;margin:1px 0;border-radius:4px;font-size:.66rem;
               color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    </style>"""

    html = css + '<table class="bmo-ens"><thead><tr>'
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
                         f'<div class="{"ens-num-hoje" if is_hoje else "ens-num"}">{dia}</div>')
                if dia in ensaios_por_dia:
                    for e in sorted(ensaios_por_dia[dia], key=lambda x: _hora_norm(x.get('Hora', ''))):
                        hora      = _hora_norm(e.get('Hora', ''))
                        nome      = _sv(e.get('Nome', 'Ensaio'))
                        eid       = _sv(e.get('_id', ''))
                        data_str  = date(ano, mes, dia).strftime('%Y-%m-%d')
                        tem_falta = f"{eid}_{data_str}" in faltas_set
                        cor   = '#e74c3c' if tem_falta else '#ff6b35'
                        label = f"{'❌' if tem_falta else '🥁'} {hora} {nome[:10]}"
                        html += (f'<span class="ens-pill" style="background:{cor}" '
                                 f'title="{nome}">{label}</span>')
                html += '</td>'
        html += '</tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # Legenda
    st.markdown(
        "<div style='margin:6px 0;font-size:.8rem'>"
        "<span style='background:#ff6b35;color:#fff;padding:2px 8px;border-radius:4px;margin-right:8px'>"
        "🥁 Ensaio</span>"
        "<span style='background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px'>"
        "❌ Marquei falta</span></div>",
        unsafe_allow_html=True
    )

    # ---- Detalhe do dia ----
    st.divider()
    st.markdown("#### 🔍 Detalhe e Presenças")

    dias_lista = sorted(ensaios_por_dia.keys())
    if not dias_lista:
        st.info("Nenhum ensaio encontrado neste mês.")
        return

    dia_sel = st.selectbox(
        "Selecionar dia:",
        options=dias_lista,
        format_func=lambda d: f"{d} de {_MESES_PT[mes]} — {len(ensaios_por_dia[d])} ensaio(s)",
        key="ens_dia_detalhe"
    )

    if dia_sel:
        data_sel     = date(ano, mes, dia_sel)
        data_sel_str = data_sel.strftime('%Y-%m-%d')

        for e in sorted(ensaios_por_dia[dia_sel], key=lambda x: _hora_norm(x.get('Hora', ''))):
            eid      = _sv(e.get('_id', ''))
            hora     = _hora_norm(e.get('Hora', '---'))
            nome     = _sv(e.get('Nome', 'Ensaio'))
            tipo     = _sv(e.get('Tipo', ''))
            local    = _sv(e.get('Local', ''))
            falta_key = f"{eid}_{data_sel_str}"
            tem_falta = falta_key in faltas_set

            tipo_icon = {'Semanal': '🔁', 'Período': '📆', 'Pontual': '📌'}.get(tipo, '🥁')

            st.markdown(
                f"<div style='border-left:4px solid #ff6b35;padding:8px 12px;margin:6px 0;"
                f"background:{card_bg};border-radius:0 8px 8px 0;color:{card_color};'>"
                f"{tipo_icon} 🕐 <b>{hora}</b> &nbsp;|&nbsp; 🥁 <b>{nome}</b>"
                f"{'&nbsp;|&nbsp; 📍 ' + local if local else ''}"
                f"</div>",
                unsafe_allow_html=True
            )

            if tem_falta:
                motivo_reg = ''
                falta_row_id = None
                for f in faltas:
                    if (_sv(f.get('Username', '')) == user['username'] and
                            _sv(f.get('EnsaioID', '')) == eid and
                            _sv(f.get('Data', ''))[:10] == data_sel_str):
                        motivo_reg   = _sv(f.get('Motivo', ''))
                        falta_row_id = f.get('_id')
                        break

                st.warning(f"❌ Marcaste falta{f' — *{motivo_reg}*' if motivo_reg else ''}")
                if st.button("↩️ Cancelar falta", key=f"cancel_{eid}_{data_sel_str}",
                             use_container_width=True):
                    if falta_row_id:
                        try:
                            base.delete_row("Faltas_Ensaios", falta_row_id)
                            get_faltas_ensaios_cached.clear()
                            st.success("✅ Falta cancelada!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Erro: {ex}")
            else:
                if data_sel < hoje:
                    st.info("✅ Ensaio já decorreu")
                else:
                    with st.expander("⚠️ Não posso ir a este ensaio"):
                        with st.form(f"form_falta_{eid}_{data_sel_str}"):
                            motivo_input = st.text_input(
                                "Motivo (opcional)",
                                placeholder="Ex: trabalho, viagem...",
                                key=f"mot_{eid}_{data_sel_str}"
                            )
                            if st.form_submit_button("✉️ Confirmar falta", use_container_width=True,
                                                     type="primary"):
                                try:
                                    base.append_row("Faltas_Ensaios", {
                                        "EnsaioID": eid,
                                        "Data":     data_sel_str,
                                        "Username": user['username'],
                                        "Motivo":   motivo_input.strip(),
                                    })
                                    get_faltas_ensaios_cached.clear()
                                    st.success("✅ Falta registada!")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Erro: {ex}")

    # ---- Métricas ----
    st.divider()
    total_mes = sum(len(v) for v in ensaios_por_dia.values())
    faltas_mes = sum(
        1 for f in faltas
        if _sv(f.get('Username', '')) == user['username']
        and _sv(f.get('Data', ''))[:7] == f"{ano:04d}-{mes:02d}"
    )
    c1, c2 = st.columns(2)
    c1.metric("🥁 Ensaios neste mês", total_mes)
    c2.metric("❌ As minhas faltas", faltas_mes)


# ============================================
# RENDER PRINCIPAL
# ============================================

def render(base, user):
    from cache import (
        get_musicos_cached,
        get_eventos_cached,
        get_presencas_cached,
        get_faltas_ensaios_cached
    )

    # Carregar dados do músico ANTES do título para usar na saudação
    try:
        musicos = get_musicos_cached()
        m_row = next((r for r in musicos if str(r.get('Username', '')).lower() == user['username']), None)
    except:
        m_row = None
        musicos = []

    # Título + saudação personalizada
    st.title("👤 Portal do Músico")

    if m_row:
        nome_completo = str(m_row.get('Nome', '')).strip()
        partes = nome_completo.split()
        if len(partes) >= 2:
            saudacao = f"{partes[0]} {partes[-1]}"
        elif partes:
            saudacao = partes[0]
        else:
            saudacao = user['username']
        st.markdown(f"👋 Olá, **{saudacao}**!")
    else:
        st.error("❌ Erro ao carregar dados do músico")

    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "📅 Agenda",
        "👤 Meus Dados",
        "🎷 Instrumento",
        "🎼 Reportório",
        "🥁 Ensaios",
        "🖼️ Galeria",
        "💬 Mensagens",
        "🎂 Aniversários"
    ])

    # ========================================
    # TAB 1: AGENDA DE EVENTOS
    # ========================================
    with t1:
        st.subheader("📅 Próximos Eventos")

        try:
            eventos   = get_eventos_cached()
            presencas = get_presencas_cached()

            if not eventos:
                st.info("📭 Nenhum evento agendado no momento")
            else:
                def _data_sort(ev):
                    try:
                        return datetime.strptime(str(ev.get('Data', ''))[:10], "%Y-%m-%d").date()
                    except Exception:
                        return datetime.max.date()

                eventos = sorted(eventos, key=_data_sort)

                for e in eventos:
                    data_evento = formatar_data_pt(e.get('Data'))
                    nome_evento = e.get('Nome do Evento', 'Sem nome')

                    with st.expander(f"📅 {data_evento} - {nome_evento}"):
                        resp_atual = next(
                            (p['Resposta'] for p in presencas
                             if p.get('EventoID') == e['_id'] and p.get('Username') == user['username']),
                            "Pendente"
                        )

                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.write(f"**Hora:** {e.get('Hora', '---')}")
                            st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")

                        with col2:
                            if resp_atual == "Vou":
                                st.success(f"**Estado:** ✅ {resp_atual}")
                            elif resp_atual == "Não Vou":
                                st.error(f"**Estado:** ❌ {resp_atual}")
                            elif resp_atual == "Talvez":
                                st.warning(f"**Estado:** ❓ {resp_atual}")
                            else:
                                st.info(f"**Estado:** ⏳ {resp_atual}")

                        if e.get('Descricao'):
                            st.markdown(f"*{e.get('Descricao')}*")

                        st.divider()
                        st.write("**Confirmar presença:**")
                        c1, c2, c3 = st.columns(3)

                        if c1.button("✅ Vou", key=f"vou_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Vou"):
                                st.success("✅ Presença confirmada!")
                                get_presencas_cached.clear()
                                st.rerun()

                        if c2.button("❌ Não Vou", key=f"nao_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Não Vou"):
                                st.info("Ausência registada")
                                get_presencas_cached.clear()
                                st.rerun()

                        if c3.button("❓ Talvez", key=f"talvez_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Talvez"):
                                st.warning("Resposta registada como 'Talvez'")
                                get_presencas_cached.clear()
                                st.rerun()

        except Exception as e:
            st.error(f"Erro ao carregar agenda: {e}")

    # ========================================
    # TAB 2: DADOS PESSOAIS
    # ========================================
    with t2:
        st.subheader("📋 Ficha Pessoal")

        if not m_row:
            st.warning("⚠️ Ficha de músico não encontrada na base de dados")
        else:
            with st.form("ficha_pessoal"):
                col1, col2 = st.columns(2)

                with col1:
                    tel = st.text_input(
                        "📞 Telemóvel",
                        value=str(m_row.get('Telefone', '')).replace('.0', ''),
                        help="Formato: 912345678"
                    )
                    nasc = st.date_input(
                        "🎂 Data de Nascimento",
                        value=converter_data_robusta(m_row.get('Data de Nascimento')) or datetime(1990, 1, 1),
                        min_value=datetime(1940, 1, 1),
                        max_value=datetime.now()
                    )

                with col2:
                    mail = st.text_input(
                        "📧 Email",
                        value=str(m_row.get('Email', '')),
                        help="Email válido para contactos"
                    )

                mor = st.text_area(
                    "🏠 Morada Completa",
                    value=str(m_row.get('Morada', '')),
                    height=100,
                    help="Rua, Código Postal, Localidade"
                )

                if st.form_submit_button("💾 Guardar Alterações", use_container_width=True):
                    try:
                        base.update_row("Musicos", m_row['_id'], {
                            "Telefone":           tel,
                            "Email":              mail,
                            "Morada":             mor,
                            "Data de Nascimento": str(nasc)
                        })
                        get_musicos_cached.clear()
                        st.success("✅ Dados atualizados com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar: {e}")

    # ========================================
    # TAB 3: INSTRUMENTO
    # ========================================
    with t3:
        st.subheader("🎷 Gestão de Instrumento")

        if not m_row:
            st.warning("⚠️ Dados não encontrados")
        else:
            with st.form("instrumento"):
                prop = st.checkbox(
                    "Instrumento Próprio",
                    value=m_row.get('Instrumento Proprio', False),
                    help="Marque se o instrumento é seu (não da banda)"
                )

                st.divider()

                inst = st.text_input(
                    "Instrumento*",
                    value=m_row.get('Instrumento', ''),
                    help="Ex: Trompete, Trombone, Clarinete, Bombardino"
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    marc = st.text_input(
                        "Marca",
                        value=m_row.get('Marca', ''),
                        disabled=prop,
                        help="Marca do instrumento da banda"
                    )
                with col2:
                    modelo = st.text_input(
                        "Modelo",
                        value=m_row.get('Modelo', ''),
                        disabled=prop,
                        help="Modelo do instrumento da banda"
                    )
                with col3:
                    seri = st.text_input(
                        "Nº de Série",
                        value=m_row.get('Num Serie', ''),
                        disabled=prop,
                        help="Número de série do instrumento da banda"
                    )

                if prop:
                    st.info("ℹ️ Como usa instrumento próprio, não precisa preencher marca, modelo e série")
                else:
                    st.caption("Preencha os dados do instrumento fornecido pela banda")

                if st.form_submit_button("💾 Atualizar Instrumento", use_container_width=True):
                    if not inst:
                        st.error("⚠️ O campo Instrumento é obrigatório")
                    else:
                        try:
                            base.update_row("Musicos", m_row['_id'], {
                                "Instrumento Proprio": prop,
                                "Instrumento":         inst,
                                "Marca":               marc   if not prop else "",
                                "Modelo":              modelo if not prop else "",
                                "Num Serie":           seri   if not prop else ""
                            })
                            get_musicos_cached.clear()
                            st.success("✅ Instrumento atualizado!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

    # ========================================
    # TAB 4: REPORTÓRIO
    # ========================================
    with t4:
        st.subheader("🎼 Reportório da Banda")

        try:
            repertorio = base.list_rows("Repertorio")

            if not repertorio:
                st.info("📭 Nenhuma obra no reportório atual")
            else:
                search = st.text_input("🔍 Pesquisar obra ou compositor", "")

                for r in repertorio:
                    nome_obra  = r.get('Nome da Obra', 'S/ Nome')
                    compositor = r.get('Compositor', '---')

                    if search.lower() in nome_obra.lower() or search.lower() in compositor.lower() or not search:
                        with st.expander(f"🎼 {nome_obra}"):
                            st.write(f"**Compositor:** {compositor}")

                            link = r.get('Links', '')
                            if link:
                                if "youtube" in link.lower() or "youtu.be" in link.lower():
                                    st.video(link)
                                else:
                                    st.link_button("🔗 Abrir Partitura", link, use_container_width=True)
                            else:
                                st.info("Sem partitura disponível")

        except Exception as e:
            st.error(f"Erro ao carregar reportório: {e}")

    # ========================================
    # TAB 5: ENSAIOS
    # ========================================
    with t5:
        st.subheader("🥁 Calendário de Ensaios")

        try:
            ensaios = base.list_rows("Ensaios")
            faltas  = get_faltas_ensaios_cached()
        except Exception as e:
            st.error(f"Erro ao carregar ensaios: {e}")
            ensaios = []
            faltas  = []

        if not ensaios:
            st.info("📭 Nenhum ensaio agendado no momento.")
        else:
            _render_calendario_ensaios(base, ensaios, faltas, user)

    # ========================================
    # TAB 6: GALERIA
    # ========================================
    with t6:
        st.subheader("🖼️ Galeria de Eventos")

        def _extrair_file_id(url):
            url = str(url).strip()
            if "drive.google.com/file/d/" in url:
                try:
                    return url.split("/file/d/")[1].split("/")[0]
                except Exception:
                    return None
            if "drive.google.com/open?id=" in url:
                try:
                    return url.split("open?id=")[1].split("&")[0]
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

        try:
            eventos_gal        = get_eventos_cached()
            eventos_com_cartaz = [e for e in eventos_gal if e.get('Cartaz')]

            if not eventos_com_cartaz:
                st.info("📭 Nenhum cartaz disponível no momento")
            else:
                cols = st.columns(3)
                for i, ev in enumerate(eventos_com_cartaz):
                    with cols[i % 3]:
                        img_url = _url_imagem_direta(ev['Cartaz'])
                        nome_ev = ev.get('Nome do Evento', 'Evento')
                        data_ev = formatar_data_pt(ev.get('Data'))

                        if img_url:
                            st.markdown(
                                f'<img src="{img_url}" alt="{nome_ev}" '
                                f'style="width:100%; border-radius:8px; margin-bottom:4px;">',
                                unsafe_allow_html=True
                            )
                            st.caption(f"{nome_ev}")
                        else:
                            st.warning("⚠️ Cartaz indisponível")
                            st.link_button("🔗 Ver Cartaz", ev['Cartaz'], use_container_width=True)

                        st.caption(data_ev)

        except Exception as e:
            st.error(f"Erro ao carregar galeria: {e}")

    # ========================================
    # TAB 7: MENSAGENS
    # ========================================
    with t7:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=False)

    # ========================================
    # TAB 8: ANIVERSÁRIOS
    # ========================================
    with t8:
        st.subheader("🎂 Aniversários")

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
                        'nome':             m.get('Nome', 'Desconhecido'),
                        'data_aniversario': aniversario_este_ano,
                        'dias_faltam':      dias_faltam,
                        'idade':            idade,
                        'instrumento':      (lambda v: v.split(' - ')[0].strip() if v else 'N/D')(str(m.get('Instrumento', '') or '').strip())
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
                        if dias == 0:    st.success("HOJE")
                        elif dias <= 3:  st.warning(f"{dias}d")
                        else:            st.info(f"{dias}d")

                    st.divider()
