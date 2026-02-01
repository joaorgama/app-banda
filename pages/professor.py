"""
Interface do Professor - Portal BMO
"""
import streamlit as st
import pandas as pd

def render(base, user):
    """Renderiza interface do professor"""
    st.title("👨‍🏫 Gestão de Alunos")
    
    # ========================================
    # ADICIONAR NOVO ALUNO
    # ========================================
    with st.expander("➕ Registar Novo Aluno", expanded=False):
        with st.form("add_aluno"):
            st.write("**Dados do Aluno**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo*", placeholder="Ex: João Silva")
                horario = st.text_input("Horário*", placeholder="Ex: Terça 16:00")
            
            with col2:
                contacto = st.text_input("Contacto", placeholder="912345678 ou email")
                sala = st.text_input("Sala", placeholder="Ex: Sala 3")
            
            st.caption("* Campos obrigatórios")
            
            if st.form_submit_button("✅ Confirmar Registo", use_container_width=True):
                if not nome or not horario:
                    st.error("⚠️ Preencha pelo menos o nome e horário")
                else:
                    try:
                        base.append_row("Aulas", {
                            "Professor": user['display_name'],
                            "Aluno": nome,
                            "Contacto": contacto,
                            "DiaHora": horario,
                            "Sala": sala
                        })
                        st.success(f"✅ Aluno **{nome}** registado com sucesso!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao registar aluno: {e}")
    
    st.divider()
    
    # ========================================
    # LISTAR MEUS ALUNOS
    # ========================================
    st.subheader("📚 Meus Alunos")
    
    try:
        aulas_raw = base.list_rows("Aulas")
        
        if not aulas_raw:
            st.info("📭 Ainda não tem alunos registados")
        else:
            df_aulas = pd.DataFrame(aulas_raw)
            meus_alunos = df_aulas[df_aulas['Professor'] == user['display_name']]
            
            if meus_alunos.empty:
                st.info("📭 Ainda não tem alunos registados")
            else:
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Alunos", len(meus_alunos))
                
                # Contar por sala
                salas = meus_alunos['Sala'].value_counts()
                if not salas.empty:
                    col2.metric("Sala mais usada", salas.index[0])
                
                # Contar com contacto
                com_contacto = meus_alunos['Contacto'].notna().sum()
                col3.metric("Com Contacto", com_contacto)
                
                st.divider()
                
                # Tabela de alunos
                st.dataframe(
                    meus_alunos[['Aluno', 'Contacto', 'DiaHora', 'Sala']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Aluno": st.column_config.TextColumn("👤 Aluno", width="large"),
                        "Contacto": st.column_config.TextColumn("📞 Contacto", width="medium"),
                        "DiaHora": st.column_config.TextColumn("🕐 Horário", width="medium"),
                        "Sala": st.column_config.TextColumn("🏫 Sala", width="small")
                    }
                )
                
                st.divider()
                
                # ========================================
                # REMOVER ALUNO
                # ========================================
                with st.expander("🗑️ Remover Aluno"):
                    st.warning("⚠️ Esta ação não pode ser desfeita!")
                    
                    alunos_list = sorted(meus_alunos['Aluno'].tolist())
                    aluno_remover = st.selectbox(
                        "Selecione o aluno a remover:",
                        options=alunos_list,
                        help="Escolha o aluno que deseja remover da lista"
                    )
                    
                    # Mostrar dados do aluno selecionado
                    if aluno_remover:
                        dados_aluno = meus_alunos[meus_alunos['Aluno'] == aluno_remover].iloc[0]
                        st.info(f"**Horário:** {dados_aluno['DiaHora']} | **Sala:** {dados_aluno['Sala']}")
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        if st.button("⚠️ Confirmar Remoção", type="primary", use_container_width=True):
                            try:
                                row_id = meus_alunos[meus_alunos['Aluno'] == aluno_remover].iloc[0]['_id']
                                base.delete_row("Aulas", row_id)
                                st.success(f"✅ Aluno **{aluno_remover}** removido!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao remover: {e}")
                    
                    with col2:
                        if st.button("❌ Cancelar", use_container_width=True):
                            st.info("Operação cancelada")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar alunos: {e}")
