"""
Componente de aniversários - Portal BMO
"""
import streamlit as st
from helpers import calcular_aniversarios, formatar_data_pt

def render_aniversarios(base):
    """
    Renderiza widget de aniversários próximos
    """
    st.subheader("🎂 Aniversários Próximos")
    
    try:
        musicos = base.list_rows("Musicos")
        
        if not musicos:
            st.info("📭 Sem dados de músicos")
            return
        
        # Calcular aniversários nos próximos 15 dias
        aniversarios = calcular_aniversarios(musicos, dias=15)
        
        if not aniversarios:
            st.info("🎈 Não há aniversários nos próximos 15 dias")
        else:
            st.caption(f"📊 {len(aniversarios)} aniversário(s) nos próximos 15 dias")
            
            for aniv in aniversarios:
                nome = aniv['nome']
                dias = aniv['dias_faltam']
                idade = aniv['idade']
                data_aniv = aniv['data_aniversario']
                instrumento = aniv['instrumento']
                
                # Determinar emoji e mensagem
                if dias == 0:
                    emoji = "🎉"
                    msg_dias = "**HOJE!**"
                    tipo = "success"
                elif dias == 1:
                    emoji = "🎂"
                    msg_dias = "**Amanhã**"
                    tipo = "warning"
                else:
                    emoji = "🎈"
                    msg_dias = f"Em {dias} dias"
                    tipo = "info"
                
                # Card do aniversário
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"{emoji} **{nome}** {msg_dias}")
                        st.caption(f"📅 {formatar_data_pt(str(data_aniv))} • {idade} anos • 🎷 {instrumento}")
                    
                    with col2:
                        if dias == 0:
                            st.success("HOJE")
                        elif dias <= 3:
                            st.warning(f"{dias}d")
                        else:
                            st.info(f"{dias}d")
                    
                    st.divider()
    
    except Exception as e:
        st.error(f"Erro ao carregar aniversários: {e}")
