"""
Funções para sistema de mensagens/chat
"""
import streamlit as st
from datetime import datetime

def adicionar_mensagem(base, username, nome_display, mensagem):
    """
    Adiciona uma mensagem ao chat
    """
    if not mensagem or not mensagem.strip():
        return False, "Mensagem vazia"
    
    try:
        agora = datetime.now()
        base.append_row("Mensagens", {
            "Username": username,
            "Nome": nome_display,
            "Mensagem": mensagem.strip(),
            "Data": str(agora.date()),
            "Hora": agora.strftime("%H:%M")
        })
        return True, "Mensagem enviada!"
    except Exception as e:
        return False, f"Erro ao enviar: {e}"

def listar_mensagens(base):
    """
    Lista todas as mensagens ordenadas por data/hora
    """
    try:
        mensagens = base.list_rows("Mensagens")
        
        # Debug
        if not mensagens:
            return []
        
        # Ordenar por data e hora (mais recentes no topo)
        mensagens_ordenadas = sorted(
            mensagens,
            key=lambda x: (
                x.get('Data', '1900-01-01'),
                x.get('Hora', '00:00')
            ),
            reverse=True
        )
        return mensagens_ordenadas
    except Exception as e:
        st.error(f"Erro ao carregar mensagens: {e}")
        return []

def apagar_mensagem(base, mensagem_id):
    """
    Apaga uma mensagem (apenas Direção)
    """
    try:
        base.delete_row("Mensagens", mensagem_id)
        return True, "Mensagem apagada"
    except Exception as e:
        return False, f"Erro ao apagar: {e}"

def render_chat(base, user, pode_apagar=False):
    """
    Renderiza interface do chat
    Args:
        base: conexão SeaTable
        user: info do utilizador
        pode_apagar: True se pode apagar mensagens (Direção)
    """
    st.subheader("💬 Mural de Mensagens")
    
    # ========================================
    # ENVIAR NOVA MENSAGEM
    # ========================================
    with st.expander("✏️ Escrever Mensagem", expanded=False):
        with st.form("nova_mensagem", clear_on_submit=True):
            mensagem = st.text_area(
                "Mensagem",
                placeholder="Escreva aqui a sua mensagem...",
                height=100,
                max_chars=500
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"Será enviada como: **{user['display_name']}**")
            with col2:
                enviado = st.form_submit_button("📤 Enviar", use_container_width=True)
            
            if enviado:
                if mensagem and mensagem.strip():
                    sucesso, msg = adicionar_mensagem(
                        base,
                        user['username'],
                        user['display_name'],
                        mensagem
                    )
                    if sucesso:
                        st.success("✅ Mensagem enviada!")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("⚠️ Escreva uma mensagem primeiro!")
    
    st.divider()
    
    # ========================================
    # LISTAR MENSAGENS
    # ========================================
    
    try:
        mensagens = listar_mensagens(base)
        
        if not mensagens or len(mensagens) == 0:
            st.info("📭 Ainda não há mensagens. Seja o primeiro a escrever!")
        else:
            st.caption(f"📊 Total de mensagens: {len(mensagens)}")
            
            # Filtro por autor (opcional)
            autores = sorted(list(set([m.get('Nome', 'Desconhecido') for m in mensagens if m.get('Nome')])))
            
            if autores:
                col_filtro1, col_filtro2 = st.columns([2, 2])
                with col_filtro1:
                    filtro_autor = st.multiselect(
                        "Filtrar por autor:",
                        options=autores,
                        default=autores,
                        key="filtro_mensagens"
                    )
                
                with col_filtro2:
                    if pode_apagar:
                        st.caption("⚠️ Pode apagar mensagens")
                
                st.divider()
                
                # Mostrar mensagens
                mensagens_visiveis = 0
                for msg in mensagens:
                    nome = msg.get('Nome', 'Desconhecido')
                    
                    # Aplicar filtro
                    if nome not in filtro_autor:
                        continue
                    
                    mensagens_visiveis += 1
                    
                    data = msg.get('Data', '')
                    hora = msg.get('Hora', '')
                    texto = msg.get('Mensagem', '')
                    
                    # Formatação da data
                    try:
                        from helpers import formatar_data_pt
                        data_formatada = formatar_data_pt(data)
                    except:
                        data_formatada = data
                    
                    # Card da mensagem
                    with st.container():
                        col1, col2 = st.columns([5, 1])
                        
                        with col1:
                            # Cabeçalho
                            st.markdown(f"**{nome}** · *{data_formatada} às {hora}*")
                            # Mensagem
                            st.write(texto)
                        
                        with col2:
                            # Botão apagar (só para Direção)
                            if pode_apagar:
                                if st.button("🗑️", key=f"del_msg_{msg['_id']}", help="Apagar mensagem"):
                                    sucesso, resultado = apagar_mensagem(base, msg['_id'])
                                    if sucesso:
                                        st.success("Apagada!")
                                        st.rerun()
                                    else:
                                        st.error(resultado)
                        
                        st.divider()
                
                if mensagens_visiveis == 0:
                    st.info("Nenhuma mensagem encontrada com os filtros selecionados")
            
            else:
                st.warning("⚠️ Mensagens sem autor definido")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar chat: {str(e)}")
        st.exception(e)
