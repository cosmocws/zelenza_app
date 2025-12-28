import streamlit as st
from datetime import datetime, timedelta
from utils import obtener_hora_madrid, formatear_hora_madrid
from database import cargar_cola_pvd, cargar_config_pvd, guardar_cola_pvd, cargar_config_sistema
from pvd_system import temporizador_pvd_mejorado

def mostrar_notificacion_sidebar(usuario_id, grupo_usuario):
    """Muestra notificación en la barra lateral con información actualizada"""
    
    cola_pvd = cargar_cola_pvd()
    config_pvd = cargar_config_pvd()
    config_sistema = cargar_config_sistema()
    
    # Buscar pausa del usuario en ESPERANDO o EN_CURSO
    pausa_usuario = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == usuario_id and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            pausa_usuario = pausa
            break
    
    if not pausa_usuario:
        # No hay pausa activa para este usuario
        st.sidebar.markdown("---")
        st.sidebar.info("👁️ **Sin pausa activa**")
        return False
    
    # Obtener configuración del grupo
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2, 'agentes_por_grupo': 10})
    
    # ============================================
    # CASO 1: USUARIO EN ESPERA
    # ============================================
    if pausa_usuario['estado'] == 'ESPERANDO':
        st.sidebar.markdown("---")
        
        # Calcular posición en el grupo
        en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = 1
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['id'] == pausa_usuario['id']:
                posicion = i + 1
                break
        
        # Calcular tiempo estimado
        en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario])
        max_simultaneo = config_grupo.get('maximo_simultaneo', 2)
        espacios_disponibles = max_simultaneo - en_pausa_grupo
        
        # Calcular tiempo estimado
        duracion_promedio = (config_pvd.get('duracion_corta', 7) + config_pvd.get('duracion_larga', 14)) / 2
        tiempo_estimado = 0
        
        if posicion == 1 and espacios_disponibles > 0:
            tiempo_estimado = 0  # Podría entrar inmediatamente
        elif posicion > 1:
            personas_delante = posicion - 1
            tiempo_estimado = (personas_delante * duracion_promedio) / max_simultaneo if max_simultaneo > 0 else duracion_promedio
            tiempo_estimado = max(1, int(tiempo_estimado))
        
        # Mostrar información de espera
        with st.sidebar.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                color: white;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                border: 2px solid #00b4d8;
            ">
            """, unsafe_allow_html=True)
            
            st.sidebar.markdown("### ⏳ **EN ESPERA**")
            st.sidebar.markdown(f"**Posición en grupo:** #{posicion}")
            st.sidebar.markdown(f"**Personas delante:** {posicion-1}")
            st.sidebar.markdown(f"**Espacios libres:** {espacios_disponibles}/{max_simultaneo}")
            
            if tiempo_estimado <= 1:
                st.sidebar.markdown(f"**Tiempo estimado:** < 1 minuto")
            else:
                st.sidebar.markdown(f"**Tiempo estimado:** ~{tiempo_estimado} minutos")
            
            st.sidebar.markdown("</div>", unsafe_allow_html=True)
            
            # Barra de progreso estimada
            if tiempo_estimado > 0:
                progreso_max = 30  # máximo 30 minutos para la barra
                progreso = min(100, (tiempo_estimado / progreso_max) * 100)
                st.sidebar.progress(int(100 - progreso))
            
            # Verificar si es su turno
            if posicion == 1 and espacios_disponibles > 0:
                st.sidebar.success("🎯 **¡ES TU TURNO!**")
                
                # Mostrar alerta para confirmar
                if not pausa_usuario.get('notificado', False):
                    pausa_usuario['notificado'] = True
                    pausa_usuario['timestamp_notificacion'] = obtener_hora_madrid().isoformat()
                    guardar_cola_pvd(cola_pvd)
                
                # Contador de 7 minutos INDIVIDUAL
                if 'confirmacion_inicio' not in st.session_state:
                    # INICIO INDIVIDUAL DEL TEMPORIZADOR PARA ESTE USUARIO
                    st.session_state.confirmacion_inicio = obtener_hora_madrid()
                    st.session_state.usuario_confirmando = usuario_id
                
                tiempo_transcurrido = (obtener_hora_madrid() - st.session_state.confirmacion_inicio).total_seconds()
                segundos_restantes = max(0, 420 - tiempo_transcurrido)  # 7 minutos = 420 segundos
                
                # Barra de progreso (7 minutos)
                porcentaje = min(100, (tiempo_transcurrido / 420) * 100)
                st.sidebar.progress(int(porcentaje))
                
                minutos_restantes = int(segundos_restantes // 60)
                segundos = int(segundos_restantes % 60)
                
                if segundos_restantes > 60:
                    st.sidebar.caption(f"⏳ **Tiempo para confirmar:** {minutos_restantes}:{segundos:02d}")
                else:
                    st.sidebar.caption(f"⏳ **Tiempo para confirmar:** {segundos_restantes} segundos")
                
                # Botones de confirmación
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("✅ **Confirmar**", key="sidebar_confirmar_btn", use_container_width=True):
                        pausa_usuario['estado'] = 'EN_CURSO'
                        pausa_usuario['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                        pausa_usuario['confirmado'] = True
                        guardar_cola_pvd(cola_pvd)
                        
                        if 'confirmacion_inicio' in st.session_state:
                            del st.session_state.confirmacion_inicio
                        
                        st.rerun()
                
                with col2:
                    if st.button("❌ **Cancelar**", key="sidebar_cancelar_btn", use_container_width=True):
                        pausa_usuario['estado'] = 'CANCELADO'
                        pausa_usuario['motivo_cancelacion'] = 'cancelado_por_usuario'
                        guardar_cola_pvd(cola_pvd)
                        
                        if 'confirmacion_inicio' in st.session_state:
                            del st.session_state.confirmacion_inicio
                        
                        temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                        st.rerun()
                
                # Verificar si se agotó el tiempo (7 MINUTOS INDIVIDUALES)
                if tiempo_transcurrido > 420:
                    st.sidebar.error("⏰ **¡Tiempo agotado!**")
                    pausa_usuario['estado'] = 'CANCELADO'
                    pausa_usuario['motivo_cancelacion'] = 'tiempo_confirmacion_expirado'
                    pausa_usuario['timestamp_cancelacion'] = obtener_hora_madrid().isoformat()
                    guardar_cola_pvd(cola_pvd)
                    
                    if 'confirmacion_inicio' in st.session_state:
                        del st.session_state.confirmacion_inicio
                    
                    temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                    temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, grupo_usuario)
                    st.rerun()
            
            else:
                # Botón para cancelar mientras espera
                if st.button("❌ Cancelar espera", key="sidebar_cancelar_espera", use_container_width=True):
                    pausa_usuario['estado'] = 'CANCELADO'
                    guardar_cola_pvd(cola_pvd)
                    temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                    st.rerun()
        
        return True
    
    # ============================================
    # CASO 2: USUARIO EN PAUSA (EN_CURSO)
    # ============================================
    elif pausa_usuario['estado'] == 'EN_CURSO':
        st.sidebar.markdown("---")
        
        duracion_elegida = pausa_usuario.get('duracion_elegida', 'corta')
        duracion_minutos = config_pvd.get('duracion_corta', 7) if duracion_elegida == 'corta' else config_pvd.get('duracion_larga', 14)
        
        tiempo_inicio = datetime.fromisoformat(pausa_usuario['timestamp_inicio'])
        hora_actual = obtener_hora_madrid()
        tiempo_transcurrido = int((hora_actual - tiempo_inicio).total_seconds() / 60)
        tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
        
        # Mostrar información de pausa en curso
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
            ">
            """, unsafe_allow_html=True)
            
            st.sidebar.markdown("### ✅ **PAUSA EN CURSO**")
            st.sidebar.markdown(f"**Tipo:** {'Corta' if duracion_elegida == 'corta' else 'Larga'}")
            st.sidebar.markdown(f"**Tiempo restante:** {tiempo_restante} minutos")
            
            st.sidebar.markdown("</div>", unsafe_allow_html=True)
            
            # Barra de progreso de la pausa
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.sidebar.progress(int(progreso))
            
            # Hora de finalización estimada
            hora_fin = tiempo_inicio + timedelta(minutes=duracion_minutos)
            st.sidebar.caption(f"⏰ **Finaliza a las:** {hora_fin.strftime('%H:%M')}")
            
            # Botón para finalizar manualmente
            if st.button("⏹️ Finalizar ahora", key="sidebar_finalizar_btn", use_container_width=True):
                pausa_usuario['estado'] = 'COMPLETADO'
                pausa_usuario['timestamp_fin'] = obtener_hora_madrid().isoformat()
                guardar_cola_pvd(cola_pvd)
                temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, grupo_usuario)
                st.rerun()
        
        return True
    
    return False

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