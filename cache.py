"""
cache.py — Funções de cache partilhadas (leitura SeaTable).
Importar daqui em app.py E nos módulos de página para evitar circular imports.
"""
import streamlit as st
import sys
from pathlib import Path

_dir = Path(__file__).parent
for _p in [str(_dir / "utils"), str(_dir / "pages")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from seatable_conn import get_base as _get_base

@st.cache_resource(show_spinner=False)
def _base():
    return _get_base()

@st.cache_resource(ttl=300, show_spinner=False)
def get_utilizadores_cached():
    return _base().list_rows("Utilizadores")

@st.cache_resource(ttl=300, show_spinner=False)
def get_musicos_cached():
    return _base().list_rows("Musicos")

@st.cache_resource(ttl=300, show_spinner=False)
def get_eventos_cached():
    return _base().list_rows("Eventos")

@st.cache_resource(ttl=300, show_spinner=False)
def get_presencas_cached():
    return _base().list_rows("Presencas")

@st.cache_resource(ttl=300, show_spinner=False)
def get_aulas_cached():
    return _base().list_rows("Aulas")

@st.cache_resource(ttl=300, show_spinner=False)
def get_faltas_ensaios_cached():
    return _base().list_rows("Faltas_Ensaios")
