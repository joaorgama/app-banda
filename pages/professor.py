import streamlit as st
import pandas as pd

def render(base, user):
    """Renderiza interface do professor"""
    st.title("👨‍🏫 Gestão de Alunos")
    
    # Adicionar novo aluno
    with st.expander("➕ Registar Novo Aluno"):
        with st.form("add_aluno"):
            nome = st.text_input("Nome do Aluno")
            contacto = st.text_input("Contacto")
            horario = st.text_input("Horário (ex: Sexta 16:00)")
            sala = st.text_input("Sala")
            
            if st.form_submit_button("Confirmar Registo", use_container_width=True):
                if nome and horario:
                    try:
                        base.append_row("Aulas", {
                            "Professor": user['display_name'],
                            "Aluno": nome,
                            "Contacto": contacto,
                            "DiaHora": horario,
                            "Sala": sala
                        })
                        st.success(f"✅ Aluno {nome} registado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                else:
                    st.warning("⚠️ Preencha pelo menos o nome e horário")
    
    # Listar alunos
    st.subheader("Meus Alunos")
    aulas_raw = base.list_rows("Aulas")
    
    if aulas_raw:
        df_aulas = pd.DataFrame(aulas_raw)
        meus_alunos = df_aulas[df_aulas['Professor'] == user['display_name']]
        
        if not meus_alunos.empty:
            # Mostrar tabela
            st.dataframe(
                meus_alunos[['Aluno', 'Contacto', 'DiaHora', 'Sala']],
                use_container_width=True,
                hide_index=True
            )
            
            # Remover aluno
            with st.expander("🗑️ Remover Aluno"):
                alunos_list = meus_alunos['Aluno'].tolist()
                aluno_remover = st.selectbox("Selecione o aluno:", options=alunos_list)
                
                if st.button("⚠️ Confirmar Remoção", type="primary"):
                    try:
                        row_id = meus_alunos[meus_alunos['Aluno'] == aluno_remover].iloc[0]['_id']
                        base.delete_row("Aulas", row_id)
                        st.success(f"✅ Aluno {aluno_remover} removido!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
        else:
            st.info("📭 Ainda não tem alunos registados")
    else:
        st.info("📭 Nenhum aluno na base de dados")
