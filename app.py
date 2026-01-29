import streamlit as st
import pandas as pd
from seatable_api import Base

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]

# Função para conectar ao SeaTable SEM cache para garantir dados frescos
def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

st.set_page_config(page_title="App Banda", page_icon="🎵")

# --- BOTÃO DE REFRESH NA BARRA LATERAL ---
if st.sidebar.button("🔄 Atualizar Dados"):
    st.rerun()

st.title("🎵 Gestão da Banda")

# ... (Mantenha a parte do Login igual até chegar à área dos Professores) ...

# --- MENU PROFESSORES (Versão otimizada) ---
elif role == "Professor":
    st.subheader(f"🏫 Aulas do Prof. {user}")
    
    with st.spinner('A carregar horários...'):
        base = get_base()
        rows = base.list_rows("Aulas")
        df = pd.DataFrame(rows)
    
    if not df.empty and 'Professor' in df.columns:
        # Filtro rigoroso: remove espaços em branco para evitar erros de digitação
        df['Professor'] = df['Professor'].str.strip()
        meus_alunos = df[df['Professor'] == user.strip()]
        
        if not meus_alunos.empty:
            # Seleciona apenas as colunas que existem para evitar erro
            colunas_visiveis = [c for c in ['DiaHora', 'Aluno', 'Sala'] if c in meus_alunos.columns]
            st.table(meus_alunos[colunas_visiveis])
        else:
            st.warning(f"Não foram encontradas aulas para o utilizador: {user}")
            st.info("Verifique se o nome na coluna 'Professor' da tabela 'Aulas' é exatamente igual ao seu Username.")
    else:
        st.error("A tabela 'Aulas' não foi encontrada ou não tem a coluna 'Professor'.")
