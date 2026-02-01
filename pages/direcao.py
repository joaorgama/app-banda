"""
Interface da Direção - Portal BMO
"""
import streamlit as st
import pandas as pd
from helpers import formatar_data_pt
from datetime import datetime

def render(base, user):
    """Renderiza interface da direção"""
    st.title("📊 Painel da Direção")
    
    t1, t2, t3, t4 = st.tabs([
        "📅 Eventos",
        "🎷 Inventário",
        "🏫 Escola",
        "📊 Status Geral"
    ])
    
    # ========================================
    # TAB 1: GESTÃO DE EVENTOS
    # ========================================
    with t1:
        st.subheader("📅 Gestão de Eventos")
        
        # Criar novo evento
        with st.expander("➕ Criar Novo Evento", expanded=False):
            with st.form("novo_evento"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome do Evento*", placeholder="Ex: Concerto de Natal")
                    data = st.date_input("Data*", min_value=datetime.now())
                
                with col2:
                    hora = st.text_input("Hora*", placeholder="Ex: 21:00")
                    tipo = st.selectbox("Tipo", ["Concerto", "Ensaio", "Actuação", "Outro"])
                
                descricao = st.text_area("Descrição", placeholder="Descrição do evento...")
                cartaz_url = st.text_input("URL do Cartaz", placeholder="https://...")
                
                if st.form_submit_button("✅ Criar Evento", use_container_width=True):
                    if not nome or not data or not hora:
                        st.error("⚠️ Preencha todos os campos obrigatórios")
                    else:
                        try:
                            base.append_row("Eventos", {
                                "Nome do Evento": nome,
                                "Data": str(data),
                                "Hora": hora,
                                "Tipo": tipo,
                                "Descricao": descricao,
                                "Cartaz": cartaz_url
                            })
                            st.success(f"✅ Evento **{nome}** criado!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
        
        st.divider()
        
        # Listar eventos
        try:
            eventos = base.list_rows("Eventos")
            presencas = base.list_rows("Presencas")
            
            if not eventos:
                st.info("📭 Nenhum evento criado")
            else:
                st.write(f"**Total de eventos:** {len(eventos)}")
                
                for e in eventos:
                    with st.expander(f"📝 {e.get('Nome do Evento')} - {formatar_data_pt(e.get('Data'))}"):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**Data:** {formatar_data_pt(e.get('Data'))}")
                            st.write(f"**Hora:** {e.get('Hora', '---')}")
                            st.write(f"**Tipo:** {e.get('Tipo', 'Concerto')}")
                        
                        with col2:
                            # Estatísticas
                            pres_evento = [p for p in presencas if p.get('EventoID') == e['_id']]
                            vao = len([p for p in pres_evento if p.get('Resposta') == 'Vou'])
                            st.metric("✅ Confirmados", vao)
                        
                        with col3:
                            if st.button("🗑️ Apagar", key=f"del_ev_{e['_id']}", type="secondary"):
                                try:
                                    base.delete_row("Eventos", e['_id'])
                                    st.success("Evento removido!")
                                    st.rerun()
                                except Exception as e_error:
                                    st.error(f"Erro: {e_error}")
        
        except Exception as e:
            st.error(f"Erro: {e}")
    
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
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                
                total_inst = df_mus['Instrumento'].notna().sum()
                proprios = df_mus['Instrumento Proprio'].sum() if 'Instrumento Proprio' in df_mus.columns else 0
                banda = total_inst - proprios
                
                col1.metric("Total Instrumentos", total_inst)
                col2.metric("Próprios", proprios)
                col3.metric("Da Banda", banda)
                
                st.divider()
                
                # Tabela
                colunas_mostrar = ['Nome', 'Instrumento', 'Marca', 'Num Serie']
                colunas_existentes = [c for c in colunas_mostrar if c in df_mus.columns]
                
                if colunas_existentes:
                    st.dataframe(
                        df_mus[colunas_existentes],
                        use_container_width=True,
                        hide_index=True
                    )
        
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
                
                # Estatísticas
                col1, col2 = st.columns(2)
                
                total_alunos = len(df_aulas)
                professores = df_aulas['Professor'].nunique() if 'Professor' in df_aulas.columns else 0
                
                col1.metric("Total de Alunos", total_alunos)
                col2.metric("Professores Ativos", professores)
                
                st.divider()
                
                # Tabela
                colunas_mostrar = ['Professor', 'Aluno', 'DiaHora', 'Sala']
                colunas_existentes = [c for c in colunas_mostrar if c in df_aulas.columns]
                
                if colunas_existentes:
                    st.dataframe(
                        df_aulas[colunas_existentes],
                        use_container_width=True,
                        hide_index=True
                    )
        
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
                    nome = m.get('Nome', '---')
                    tem_telefone = bool(m.get('Telefone'))
                    tem_email = bool(m.get('Email'))
                    tem_morada = bool(m.get('Morada'))
                    
                    # Calcular completude
                    campos_preenchidos = sum([tem_telefone, tem_email, tem_morada])
                    percentagem = int((campos_preenchidos / 3) * 100)
                    
                    status_list.append({
                        "Nome": nome,
                        "📞 Telefone": "✅" if tem_telefone else "❌",
                        "📧 Email": "✅" if tem_email else "❌",
                        "🏠 Morada": "✅" if tem_morada else "❌",
                        "Completude": f"{percentagem}%"
                    })
                
                df_status = pd.DataFrame(status_list)
                
                # Métricas
                completos = len([s for s in status_list if s["Completude"] == "100%"])
                incompletos = len(status_list) - completos
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Músicos", len(status_list))
                col2.metric("✅ Fichas Completas", completos)
                col3.metric("⚠️ Incompletas", incompletos)
                
                st.divider()
                
                # Tabela
                st.dataframe(
                    df_status,
                    use_container_width=True,
                    hide_index=True
                )
        
        except Exception as e:
            st.error(f"Erro: {e}")
