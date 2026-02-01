import streamlit as st
from seatable_api import Base
import time

SERVER_URL = "https://cloud.seatable.io"

def get_base():
    """Estabelece conexão com SeaTable com retry"""
    api_token = st.secrets["SEATABLE_TOKEN"]
    for i in range(3):
        try:
            base = Base(api_token, SERVER_URL)
            base.auth()
            return base
        except Exception as e:
            if i == 2:  # última tentativa
                st.error(f"Erro ao conectar: {e}")
            time.sleep(1)
    return None

def safe_delete_presenca(base, event_id, username):
    """Remove presença de forma segura"""
    try:
        presencas = base.list_rows("Presencas")
        for p in presencas:
            if p.get('EventoID') == event_id and p.get('Username') == username:
                base.delete_row("Presencas", p['_id'])
                return True
        return False
    except Exception as e:
        st.error(f"Erro ao remover presença: {e}")
        return False

def add_presenca(base, event_id, username, resposta):
    """Adiciona/atualiza presença"""
    try:
        # Remove presença anterior
        safe_delete_presenca(base, event_id, username)
        # Adiciona nova
        base.append_row("Presencas", {
            "EventoID": event_id,
            "Username": username,
            "Resposta": resposta
        })
        return True
    except Exception as e:
        st.error(f"Erro ao registar presença: {e}")
        return False
