"""
Interface do Músico - Portal BMO
"""
import streamlit as st
from helpers import formatar_data_pt
from datetime import datetime

def render(base, user):
    """Renderiza interface do músico"""
    st.title("👤 Portal do Músico")
    
    # TESTE: 7 tabs simples
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📅 Agenda",
        "👤 Meus Dados",
        "🎷 Instrumento",
        "🎼 Reportório",
        "🖼️ Galeria",
        "💬 Mensagens",
        "🎂 Aniversários"
    ])
    
    with t1:
        st.write("Tab 1 - Agenda")
    
    with t2:
        st.write("Tab 2 - Dados")
    
    with t3:
        st.write("Tab 3 - Instrumento")
    
    with t4:
        st.write("Tab 4 - Reportório")
    
    with t5:
        st.write("Tab 5 - Galeria")
    
    with t6:
        st.write("Tab 6 - Mensagens")
    
    with t7:
        st.success("🎂 TAB DE ANIVERSÁRIOS FUNCIONA!")
        st.balloons()
