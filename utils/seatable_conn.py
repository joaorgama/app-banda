"""
Funções de conexão e operações com SeaTable
"""
import streamlit as st
from seatable_api import Base
import time

SERVER_URL = "https://cloud.seatable.io"

def get_base():
    """
    Estabelece conexão com SeaTable com retry automático
    Returns: Base object ou None em caso de erro
    """
    try:
        api_token = st.secrets["SEATABLE_TOKEN"]
    except:
        st.error("❌ Token SEATABLE_TOKEN não encontrado nas secrets")
        return None
    
    for tentativa in range(3):
        try:
            base = Base(api_token, SERVER_URL)
            base.auth()
            return base
        except Exception as e:
            if tentativa == 2:  # última tentativa
                st.error(f"❌ Erro ao conectar ao SeaTable: {str(e)}")
                st.info("💡 Verifique se o token está correto nas secrets")
            time.sleep(1)
    
    return None

def safe_delete_presenca(base, event_id, username):
    """
    Remove presença de forma segura (sem SQL direto)
    Args:
        base: SeaTable Base object
        event_id: ID do evento
        username: Username do utilizador
    Returns: True se removeu, False se não encontrou ou erro
    """
    try:
        presencas = base.list_rows("Presencas")
        if not presencas:
            return False
        
        for p in presencas:
            if p.get('EventoID') == event_id and p.get('Username') == username:
                base.delete_row("Presencas", p['_id'])
                return True
        
        return False
    except Exception as e:
        st.error(f"Erro ao remover presença: {e}")
        return False

def add_presenca(base, event_id, username, resposta):
    """
    Adiciona ou atualiza presença de um músico num evento
    Args:
        base: SeaTable Base object
        event_id: ID do evento
        username: Username do músico
        resposta: "Vou", "Não Vou" ou "Talvez"
    Returns: True se sucesso, False se erro
    """
    try:
        # Remove presença anterior se existir
        safe_delete_presenca(base, event_id, username)
        
        # Adiciona nova presença
        base.append_row("Presencas", {
            "EventoID": event_id,
            "Username": username,
            "Resposta": resposta
        })
        return True
    except Exception as e:
        st.error(f"Erro ao registar presença: {e}")
        return False

def get_presencas_evento(base, event_id):
    """
    Obtém todas as presenças de um evento específico
    Returns: Lista de dicionários com as presenças
    """
    try:
        presencas = base.list_rows("Presencas")
        if not presencas:
            return []
        return [p for p in presencas if p.get('EventoID') == event_id]
    except:
        return []
