import streamlit as st
import pandas as pd
from seatable_api import Base
import hashlib
import time
from datetime import datetime, timedelta
import re

# --- CONFIGURAÇÃO ---
SERVER_URL = "https://cloud.seatable.io"
API_TOKEN = st.secrets["SEATABLE_TOKEN"]
DEFAULT_PASS = "1234"

def get_base():
    for i in range(3):
        try:
            base = Base(API_TOKEN, SERVER_URL); base.auth()
            return base
        except: time.sleep(1)
    return None

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def converter_data_robusta(valor):
    if not valor or str(valor) in ['None', 'nan', '']: return None
    if isinstance(valor, (datetime, pd.Timestamp)): return valor.date()
    str_data = str(valor).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
        try: return datetime.strptime(str_data.split(' ')[0].split('T')[0], fmt).date()
        except: continue
    return None

def formatar_data_pt(valor):
    dt = converter_data_robusta(valor)
    return dt.strftime('%d/%m/%Y') if dt else "---"

st.set_page_config(page_title="BMO Portal", page_icon="🎵", layout="wide")

if 'auth_status' not in st.session_state: 
    st.session_state.update({'auth_status': False, 'user_info': {}, 'must_change_pass': False})

base = get_base()

# --- LOGIN ---
if base and not st.session_state['auth_status']:
    st.header("🎵 Portal da Banda Municipal de Oeiras")
    with st.form("login"):
        u_in = st.text_input("Utilizador").strip().lower()
        p_in = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Entrar"):
            df_u = pd.DataFrame(base.list_rows("Utilizadores"))
            match = df_u[df_u['Username'].str.lower() == u_in] if not df_u.empty else pd.DataFrame()
            if not match.empty:
                row = match.iloc[0]
                stored_p = str(row.get('Password', DEFAULT_PASS))
                if (p_in == stored_p) or (hash_password(p_in) == stored_p):
                    st.session_state.update({
                        'auth_status': True, 
                        'must_change_pass': (stored_p == DEFAULT_PASS), 
                        'user_info': {'username': u_in, 'display_name': row.get('Nome', u_in), 'role': row['Funcao'], 'row_id': row['_id']}
                    })
                    st.rerun()
                else: st.error("Password incorreta.")
            else: st.error("Utilizador não encontrado.")

# --- ÁREA LOGADA ---
elif st.session_state['auth_status']:
    user = st.session_state['user_info']
    st.sidebar.title("🎵 BMO")
    st.sidebar.write(f"Olá, **{user['display_name']}**")
    if st.sidebar.button("🚪 Sair"): 
        st.session_state.clear()
        st.rerun()

    # --- PERFIL PROFESSOR (COM CALENDÁRIO) ---
    if user['role'] == "Professor":
        st.header("👨‍🏫 Portal do Professor")
        t_mapa, t_alunos = st.tabs(["📅 Mapa de Ocupação ⭐", "👥 Meus Alunos"])

        with t_mapa:
            local_sel = st.radio("Local:", ["Algés", "Oeiras"], horizontal=True)
            
            # Criar grelha do calendário (Corrigindo o erro da imagem image_70f5ba.png)
            hoje = datetime.now()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            colunas = [(inicio_semana + timedelta(days=i)).strftime('%a %d/%m') for i in range(14)]
            horas = [f"{h:02d}:00" for h in range(8, 22)]
            df_cal = pd.DataFrame("", index=horas, columns=colunas)

            # Preencher com dados do SeaTable (Aulas)
            aulas_raw = base.list_rows("Aulas")
            if aulas_raw:
                for a in aulas_raw:
                    # Só mostra se for no local selecionado
                    if a.get('Local') == local_sel or a.get('Sala') == local_sel:
                        dia_txt = str(a.get('Dia da Semana', '')).split(' ')[0] # Ex: "Sexta"
                        hora_txt = str(a.get('Hora', '')) # Ex: "20:00"
                        
                        # Lógica para marcar no mapa
                        for col in colunas:
                            # Simplificação: se o dia da semana bater com a coluna
                            if dia_txt.lower() in col.lower():
                                if hora_txt in horas:
                                    is_mine = (a.get('Professor') == user['display_name'])
                                    prefixo = "⭐ " if is_mine else ""
                                    df_cal.at[hora_txt, col] = f"{prefixo}{a.get('Professor')}"

            st.dataframe(df_cal, use_container_width=True)

        with t_alunos:
            # Listagem de alunos com proteção contra tabelas vazias
            aulas_raw = base.list_rows("Aulas")
            if aulas_raw:
                df_aulas = pd.DataFrame(aulas_raw)
                # Verifica se as colunas existem antes de filtrar para evitar o KeyError
                cols_necessarias = ['Professor', 'Aluno', 'Contacto', 'DiaHora', 'Sala']
                if all(c in df_aulas.columns for c in cols_necessarias):
                    meus = df_aulas[df_aulas['Professor'] == user['display_name']]
                    if not meus.empty:
                        st.table(meus[['Aluno', 'Contacto', 'DiaHora', 'Sala']])
                        
                        aluno_rem = st.selectbox("Remover Aluno:", meus['Aluno'].unique())
                        if st.button("Confirmar Remoção"):
                            rid = meus[meus['Aluno'] == aluno_rem].iloc[0]['_id']
                            base.delete_row("Aulas", rid)
                            st.rerun()
                    else:
                        st.info("Não tem alunos registados.")
                else:
                    st.error("Erro: A tabela 'Aulas' no SeaTable não tem as colunas corretas.")
            else:
                st.info("A tabela de aulas está vazia.")

    # --- PERFIL DIREÇÃO (CORREÇÃO KEYERROR) ---
    elif user['role'] == "Direcao":
        st.header("📋 Painel de Direção")
        # Proteção contra erro de colunas inexistentes na visualização geral
        rows = base.list_rows("Aulas")
        if rows:
            df_geral = pd.DataFrame(rows)
            cols_direcao = ['Professor', 'Aluno', 'DiaHora', 'Sala']
            # Filtra apenas as colunas que realmente existem
            cols_validas = [c for c in cols_direcao if c in df_geral.columns]
            st.dataframe(df_geral[cols_validas], use_container_width=True)
        else:
            st.warning("Nenhuma aula registada no sistema.")
