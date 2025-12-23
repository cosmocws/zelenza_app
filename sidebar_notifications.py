import streamlit as st
from datetime import datetime
from utils import obtener_hora_madrid
from database import cargar_cola_pvd, cargar_config_pvd, guardar_cola_pvd
from pvd_system import temporizador_pvd_mejorado

def mostrar_notificacion_sidebar(usuario_id, grupo_usuario):
    """Muestra notificación en la barra lateral cuando es el turno del usuario"""
    
    cola_pvd = cargar_cola_pvd()
    config_pvd = cargar_config_pvd()
    
    # Buscar pausa del usuario en ESPERANDO
    pausa_usuario = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
            pausa_usuario = pausa
            break
    
    if not pausa_usuario:
        return False
    
    # Verificar si es el primero en su grupo
    en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
    en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
    
    if not en_espera_grupo or en_espera_grupo[0]['id'] != pausa_usuario['id']:
        return False
    
    # Verificar si hay espacio en el grupo
    from database import cargar_config_sistema
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2})
    max_grupo = config_grupo.get('maximo_simultaneo', 2)
    
    en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario])
    
    if en_pausa_grupo >= max_grupo:
        return False
    
    # ¡ES SU TURNO!
    st.sidebar.markdown("---")
    
    # Mostrar notificación grande en la barra lateral
    with st.sidebar.container():
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            border: 2px solid white;
            animation: pulse 2s infinite;
        ">
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown("### 🎯 ¡ES TU TURNO!")
        st.sidebar.markdown("**Tu pausa PVD está lista**")
        
        duracion_elegida = pausa_usuario.get('duracion_elegida', 'corta')
        duracion = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
        
        st.sidebar.write(f"⏱️ **Duración:** {duracion} minutos")
        st.sidebar.write(f"👥 **Grupo:** {grupo_usuario}")
        st.sidebar.write(f"🕒 **Hora:** {obtener_hora_madrid().strftime('%H:%M:%S')}")
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)
        
        # Botones de acción en la barra lateral
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("✅ **Comenzar**", key="sidebar_confirmar", use_container_width=True):
                pausa_usuario['estado'] = 'EN_CURSO'
                pausa_usuario['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                pausa_usuario['confirmado'] = True
                guardar_cola_pvd(cola_pvd)
                
                temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                
                st.sidebar.success("✅ Pausa iniciada")
                st.rerun()
        
        with col2:
            if st.button("❌ **Cancelar**", key="sidebar_cancelar", use_container_width=True):
                pausa_usuario['estado'] = 'CANCELADO'
                guardar_cola_pvd(cola_pvd)
                
                temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                
                st.sidebar.warning("❌ Turno cancelado")
                st.rerun()
        
        # Tiempo restante para confirmar
        if 'confirmacion_inicio' not in st.session_state:
            st.session_state.confirmacion_inicio = obtener_hora_madrid()
        
        tiempo_confirmacion = (obtener_hora_madrid() - st.session_state.confirmacion_inicio).total_seconds()
        minutos_restantes = max(0, 120 - tiempo_confirmacion) / 60
        
        st.sidebar.progress(min(100, (tiempo_confirmacion / 120) * 100))
        st.sidebar.caption(f"⏳ **Tiempo para confirmar:** {int(minutos_restantes)}:{int((minutos_restantes % 1) * 60):02d}")
        
        if tiempo_confirmacion > 120:
            st.sidebar.error("⏰ Tiempo agotado. Cancelando turno...")
            pausa_usuario['estado'] = 'CANCELADO'
            guardar_cola_pvd(cola_pvd)
            temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
            st.rerun()
    
    return True

def verificar_turno_sidebar():
    """Verifica si es el turno del usuario y muestra notificación en sidebar"""
    
    if not st.session_state.get('authenticated', False):
        return False
    
    if st.session_state.get('user_type') != 'user':
        return False
    
    from database import cargar_configuracion_usuarios
    usuarios_config = cargar_configuracion_usuarios()
    usuario_id = st.session_state.username
    
    if usuario_id not in usuarios_config:
        return False
    
    grupo_usuario = usuarios_config[usuario_id].get('grupo', 'basico')
    
    return mostrar_notificacion_sidebar(usuario_id, grupo_usuario)