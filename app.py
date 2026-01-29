import streamlit as st
import pandas as pd
from seatable_api import Base

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io" # Se usar o servidor europeu, mantenha este.
API_TOKEN = st.secrets["SEATABLE_TOKEN"] # Vamos configurar isto no passo seguinte

# Função para conectar ao SeaTable
def get_base():
    base = Base(API_TOKEN, SERVER_URL)
    base.auth()
    return base

# --- INTERFACE ---
st.set_page_config(page_title="App Banda", page_icon="🎵")

st.title("🎵 Gestão da Banda")

# --- LOGIN ---
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

if st.session_state['user_role'] is None:
    st.header("Login")
    username_input = st.text_input("Utilizador")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Entrar"):
        try:
            base = get_base()
            # Busca utilizadores
            users = base.list_rows("Utilizadores")
            df_users = pd.DataFrame(users)
            
            # Verifica credenciais
            user_found = df_users[
                (df_users['Username'] == username_input) & 
                (df_users['Password'] == password_input)
            ]
            
            if not user_found.empty:
                st.session_state['user_role'] = user_found.iloc[0]['Funcao']
                st.session_state['username'] = user_found.iloc[0]['Username']
                st.success(f"Bem-vindo, {username_input}!")
                st.rerun()
            else:
                st.error("Utilizador ou Password errados.")
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")

# --- ÁREA LOGADA ---
else:
    role = st.session_state['user_role']
    user = st.session_state['username']
    
    st.sidebar.write(f"Logado como: **{user}** ({role})")
    if st.sidebar.button("Sair"):
        st.session_state['user_role'] = None
        st.rerun()

    base = get_base()

    # --- MENU DIREÇÃO ---
    if role == "Direcao":
        st.info("Painel de Administração")
        tab1, tab2 = st.tabs(["Eventos", "Adicionar Novo"])
        
        with tab1:
            rows = base.list_rows("Eventos")
            st.dataframe(pd.DataFrame(rows))
        
        with tab2:
            with st.form("novo_evento"):
                nome = st.text_input("Nome do Evento")
                data = st.date_input("Data")
                tipo = st.selectbox("Tipo", ["Ensaio", "Concerto"])
                desc = st.text_area("Descrição")
                submitted = st.form_submit_button("Guardar")
                if submitted:
                    base.append_row("Eventos", {
                        "Nome do Evento": nome,
                        "Data": str(data),
                        "Tipo": tipo,
                        "Descricao": desc
                    })
                    st.success("Evento criado!")

    # --- MENU MÚSICOS ---
    elif role == "Musico":
        st.subheader("📅 Próximos Eventos")
        rows = base.list_rows("Eventos")
        if rows:
            df = pd.DataFrame(rows)
            for index, row in df.iterrows():
                with st.expander(f"{row.get('Data', '')} - {row.get('Nome do Evento', '')}"):
                    st.write(f"**Tipo:** {row.get('Tipo', '')}")
                    st.write(f"**Detalhes:** {row.get('Descricao', '')}")
                    # Aqui poderia adicionar um campo de comentários no futuro
        else:
            st.write("Sem eventos agendados.")

    # --- MENU PROFESSORES ---
    elif role == "Professor":
        st.subheader(f"🏫 Aulas do Prof. {user}")
        
        # Filtra apenas as aulas deste professor
        # Nota: O SeaTable SQL seria mais eficiente, mas vamos filtrar no Python para simplificar
        rows = base.list_rows("Aulas")
        df = pd.DataFrame(rows)
        
        if not df.empty and 'Professor' in df.columns:
            meus_alunos = df[df['Professor'] == user]
            if not meus_alunos.empty:
                st.table(meus_alunos[['DiaHora', 'Aluno', 'Sala']])
            else:
                st.warning("Não tem aulas associadas a este nome de utilizador.")
        else:
            st.warning("Tabela de aulas vazia ou mal configurada.")
