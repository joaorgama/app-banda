"""
Interface do Músico - Portal BMO
"""
import streamlit as st
import time
import requests
from helpers import formatar_data_pt, converter_data_robusta
from seatable_conn import add_presenca
from datetime import datetime, timedelta

def render(base, user):

    # Carregar dados do músico ANTES do título para usar na saudação
    try:
        musicos = base.list_rows("Musicos")
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

    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📅 Agenda",
        "👤 Meus Dados",
        "🎷 Instrumento",
        "🎼 Reportório",
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
            eventos   = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")

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
                                st.rerun()

                        if c2.button("❌ Não Vou", key=f"nao_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Não Vou"):
                                st.info("Ausência registada")
                                st.rerun()

                        if c3.button("❓ Talvez", key=f"talvez_{e['_id']}", use_container_width=True):
                            if add_presenca(base, e['_id'], user['username'], "Talvez"):
                                st.warning("Resposta registada como 'Talvez'")
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
    # TAB 5: GALERIA
    # ========================================
    with t5:
        st.subheader("🖼️ Galeria de Eventos")

        def _extrair_file_id(url):
            """Extrai o file ID de um URL do Google Drive"""
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

        def _carregar_imagem(url):
            """
            Tenta carregar a imagem do Google Drive.
            1ª tentativa: thumbnail URL (mais rápido)
            2ª tentativa: download direto via requests (mais robusto)
            """
            if not url:
                return None, url

            file_id = _extrair_file_id(url)

            if file_id:
                # 1ª tentativa: thumbnail
                thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
                try:
                    resp = requests.get(thumb_url, timeout=8)
                    if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
                        return resp.content, url
                except Exception:
                    pass

                # 2ª tentativa: download direto
                try:
                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    resp = requests.get(download_url, timeout=10, allow_redirects=True)
                    if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
                        return resp.content, url
                except Exception:
                    pass

                return None, url

            # URL não é Google Drive — passa diretamente ao st.image
            return "direct", url

        try:
            eventos_gal        = base.list_rows("Eventos")
            eventos_com_cartaz = [e for e in eventos_gal if e.get('Cartaz')]

            if not eventos_com_cartaz:
                st.info("📭 Nenhum cartaz disponível no momento")
            else:
                cols = st.columns(3)
                for i, ev in enumerate(eventos_com_cartaz):
                    with cols[i % 3]:
                        img_data, url_original = _carregar_imagem(ev['Cartaz'])
                        try:
                            if img_data == "direct":
                                st.image(
                                    url_original,
                                    caption=ev.get('Nome do Evento', 'Evento'),
                                    use_column_width=True
                                )
                            elif img_data:
                                st.image(
                                    img_data,
                                    caption=ev.get('Nome do Evento', 'Evento'),
                                    use_column_width=True
                                )
                            else:
                                st.warning("⚠️ Não foi possível carregar o cartaz")
                                st.link_button("🔗 Ver Cartaz", url_original, use_container_width=True)
                        except Exception:
                            st.warning("⚠️ Não foi possível carregar o cartaz")
                            st.link_button("🔗 Ver Cartaz", url_original, use_container_width=True)
                        st.caption(formatar_data_pt(ev.get('Data')))

        except Exception as e:
            st.error(f"Erro ao carregar galeria: {e}")

    # ========================================
    # TAB 6: MENSAGENS
    # ========================================
    with t6:
        from mensagens import render_chat
        render_chat(base, user, pode_apagar=False)

    # ========================================
    # TAB 7: ANIVERSÁRIOS
    # ========================================
    with t7:
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
                        'instrumento':      m.get('Instrumento', 'N/D')
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
