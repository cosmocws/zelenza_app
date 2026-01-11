import streamlit as st
from datetime import datetime, timedelta

from utils import obtener_hora_madrid, formatear_hora_madrid
from database import (
    cargar_configuracion_usuarios, 
    cargar_cola_pvd_grupo, 
    guardar_cola_pvd_grupo,
    cargar_config_pvd, 
    obtener_todas_colas_pvd,
    consolidar_colas_pvd,
    cargar_config_sistema
)
from pvd_system import temporizador_pvd_mejorado

# ==============================================
# FUNCIONES DE CÁLCULO DE TIEMPOS
# ==============================================

def calcular_tiempo_estimado_real(grupo_usuario, usuario_id):
    """Calcula tiempo estimado real considerando pausas activas y tiempos restantes (nuevo sistema)"""
    try:
        # 1. Cargar datos necesarios
        config_pvd = cargar_config_pvd()
        todas_colas = obtener_todas_colas_pvd()
        
        if grupo_usuario not in todas_colas:
            return 5  # Grupo no encontrado, valor por defecto
        
        cola_grupo = todas_colas[grupo_usuario]
        
        # 2. Obtener configuración del grupo
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        config_grupo = grupos_config.get(grupo_usuario, {
            'maximo_simultaneo': 2,
            'duracion_corta': 5,
            'duracion_larga': 10
        })
        max_simultaneo = config_grupo.get('maximo_simultaneo', 2)
        
        # 3. Pausas activas en el grupo
        pausas_activas = [p for p in cola_grupo if p['estado'] == 'EN_CURSO']
        
        # 4. Calcular EXACTAMENTE cuándo termina cada pausa activa
        tiempos_fin_pausas = []
        for pausa in pausas_activas:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            
            # Usar configuración del grupo
            duracion_total = (config_grupo['duracion_corta'] 
                            if duracion_elegida == 'corta' 
                            else config_grupo['duracion_larga'])
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_fin = tiempo_inicio + timedelta(minutes=duracion_total)
            tiempo_restante = (tiempo_fin - obtener_hora_madrid()).total_seconds() / 60
            
            # Solo considerar pausas que aún no han terminado
            if tiempo_restante > 0:
                tiempos_fin_pausas.append({
                    'pausa_id': pausa['id'],
                    'usuario': pausa['usuario_nombre'],
                    'tiempo_restante_minutos': tiempo_restante,
                    'hora_fin': tiempo_fin
                })
        
        # 5. Ordenar por tiempo restante (la que termina primero)
        tiempos_fin_pausas.sort(key=lambda x: x['tiempo_restante_minutos'])
        
        # 6. Posición del usuario en espera
        en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
        en_espera_grupo = sorted(en_espera_grupo, 
                                key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = 0
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['usuario_id'] == usuario_id:
                posicion = i + 1
                break
        
        if posicion == 0:
            return 0  # No está en espera
        
        # 7. Calcular espacios disponibles
        espacios_disponibles = max(0, max_simultaneo - len(pausas_activas))
        
        # 8. Si hay espacio y es el primero, puede entrar inmediatamente
        if espacios_disponibles > 0 and posicion == 1:
            return 0
        
        # 9. Si no hay espacio (todos los huecos ocupados)
        if espacios_disponibles <= 0:
            # Necesita esperar a que termine una pausa
            if tiempos_fin_pausas:
                # Tomar la pausa que termine PRIMERO
                tiempo_primera_pausa = tiempos_fin_pausas[0]['tiempo_restante_minutos']
                
                # Si es el primero en la cola, su tiempo es el de la primera pausa que termine
                if posicion == 1:
                    return max(1, int(tiempo_primera_pausa + 0.5))
                
                # Si no es el primero, necesita esperar más
                else:
                    # Cuántas personas delante también están esperando
                    personas_delante = posicion - 1
                    
                    # Cuántas pausas necesita esperar
                    pausas_necesarias = min(personas_delante, len(tiempos_fin_pausas))
                    
                    if pausas_necesarias > 0:
                        # Tiempo hasta que terminen las pausas necesarias
                        tiempo_estimado = tiempos_fin_pausas[pausas_necesarias - 1]['tiempo_restante_minutos']
                        return max(1, int(tiempo_estimado + 0.5))
            
            # Si no hay información de pausas activas, usar duración promedio del grupo
            duracion_promedio = (config_grupo['duracion_corta'] + config_grupo['duracion_larga']) / 2
            tiempo_estimado = (posicion * duracion_promedio) / max_simultaneo
            return max(1, int(tiempo_estimado + 0.5))
        
        # 10. Si hay espacio pero no es el primero
        if espacios_disponibles > 0 and posicion > 1:
            # Algunas personas delante entrarán inmediatamente
            personas_que_entran_inmediatamente = min(posicion - 1, espacios_disponibles)
            personas_que_esperan = max(0, (posicion - 1) - personas_que_entran_inmediatamente)
            
            if personas_que_esperan == 0:
                # Todas las personas delante entran inmediatamente
                return 0
            else:
                # Necesita esperar a que terminen pausas
                if tiempos_fin_pausas and personas_que_esperan <= len(tiempos_fin_pausas):
                    tiempo_estimado = tiempos_fin_pausas[personas_que_esperan - 1]['tiempo_restante_minutos']
                    return max(1, int(tiempo_estimado + 0.5))
                else:
                    duracion_promedio = (config_grupo['duracion_corta'] + config_grupo['duracion_larga']) / 2
                    tiempo_estimado = (personas_que_esperan * duracion_promedio) / max_simultaneo
                    return max(1, int(tiempo_estimado + 0.5))
        
        # 11. Caso por defecto
        return 5
    
    except Exception as e:
        print(f"Error calculando tiempo estimado para grupo {grupo_usuario}: {e}")
        return 5  # Valor por defecto seguro

def mostrar_info_detallada_pausas(grupo_usuario):
    """Muestra información detallada de las pausas activas en un grupo (para debug)"""
    try:
        todas_colas = obtener_todas_colas_pvd()
        
        if grupo_usuario not in todas_colas:
            return "No hay datos para este grupo"
        
        cola_grupo = todas_colas[grupo_usuario]
        pausas_activas = [p for p in cola_grupo if p['estado'] == 'EN_CURSO']
        
        if not pausas_activas:
            return "No hay pausas activas en este grupo"
        
        # Obtener configuración del grupo
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        config_grupo = grupos_config.get(grupo_usuario, {
            'duracion_corta': 5,
            'duracion_larga': 10
        })
        
        info = "**Pausas activas:**\n"
        for i, pausa in enumerate(pausas_activas, 1):
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_total = (config_grupo['duracion_corta'] 
                            if duracion_elegida == 'corta' 
                            else config_grupo['duracion_larga'])
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_fin = tiempo_inicio + timedelta(minutes=duracion_total)
            tiempo_restante = (tiempo_fin - obtener_hora_madrid()).total_seconds() / 60
            
            hora_fin_str = tiempo_fin.strftime('%H:%M')
            
            info += f"{i}. {pausa['usuario_nombre']} - "
            info += f"Termina a las {hora_fin_str} "
            info += f"(en {int(tiempo_restante)} min)\n"
        
        return info
    
    except Exception as e:
        return f"Error mostrando información: {e}"

# ==============================================
# FUNCIONES DE NOTIFICACIONES SIDEBAR
# ==============================================

def mostrar_notificacion_sidebar(usuario_id, grupo_usuario):
    """Muestra notificación en la barra lateral con información actualizada (nuevo sistema)"""
    
    try:
        # 1. Cargar datos del grupo específico
        cola_grupo = cargar_cola_pvd_grupo(grupo_usuario)
        config_pvd = cargar_config_pvd()
        config_sistema = cargar_config_sistema()
        
        # 2. Buscar pausa del usuario en ESPERANDO o EN_CURSO
        pausa_usuario = None
        for pausa in cola_grupo:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
                pausa_usuario = pausa
                break
        
        if not pausa_usuario:
            # No hay pausa activa para este usuario
            st.sidebar.markdown("---")
            st.sidebar.info("👁️ **Sin pausa activa**")
            return False
        
        # 3. Obtener configuración del grupo
        grupos_config = config_sistema.get('grupos_pvd', {})
        config_grupo = grupos_config.get(grupo_usuario, {
            'maximo_simultaneo': 2,
            'duracion_corta': 5,
            'duracion_larga': 10
        })
        max_simultaneo_grupo = config_grupo.get('maximo_simultaneo', 2)
        
        # ============================================
        # CASO 1: USUARIO EN ESPERA
        # ============================================
        if pausa_usuario['estado'] == 'ESPERANDO':
            st.sidebar.markdown("---")
            
            # Calcular posición en el grupo
            en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
            en_espera_grupo = sorted(en_espera_grupo, 
                                    key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = 0
            for i, pausa in enumerate(en_espera_grupo):
                if pausa['id'] == pausa_usuario['id']:
                    posicion = i + 1
                    break
            
            if posicion == 0:
                return False  # No está en espera
            
            # Calcular espacios disponibles
            en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            espacios_disponibles_grupo = max(0, max_simultaneo_grupo - en_pausa_grupo)
            
            # Calcular tiempo estimado REAL
            tiempo_estimado = calcular_tiempo_estimado_real(grupo_usuario, usuario_id)
            
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
                st.sidebar.markdown(f"**Grupo:** {grupo_usuario}")
                st.sidebar.markdown(f"**Posición:** #{posicion}")
                st.sidebar.markdown(f"**Personas delante:** {posicion-1}")
                st.sidebar.markdown(f"**Espacios libres:** {espacios_disponibles_grupo}/{max_simultaneo_grupo}")
                
                # Mostrar tiempo estimado
                if tiempo_estimado <= 0:
                    st.sidebar.markdown(f"**Tiempo estimado:** < 1 minuto")
                elif tiempo_estimado == 1:
                    st.sidebar.markdown(f"**Tiempo estimado:** ~1 minuto")
                else:
                    st.sidebar.markdown(f"**Tiempo estimado:** ~{tiempo_estimado} minutos")
                
                st.sidebar.markdown("</div>", unsafe_allow_html=True)
                
                # Barra de progreso estimada
                if tiempo_estimado > 0:
                    progreso_max = 30  # máximo 30 minutos para la barra
                    progreso = min(100, (tiempo_estimado / progreso_max) * 100)
                    st.sidebar.progress(int(100 - progreso))
                
                # Verificar si es su turno
                if posicion == 1 and espacios_disponibles_grupo > 0:
                    st.sidebar.success("🎯 **¡ES TU TURNO!**")
                    
                    # Mostrar alerta para confirmar
                    if not pausa_usuario.get('notificado', False):
                        pausa_usuario['notificado'] = True
                        pausa_usuario['timestamp_notificacion'] = obtener_hora_madrid().isoformat()
                        guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                    
                    # Contador de 7 minutos INDIVIDUAL
                    timer_key = f'confirmacion_inicio_{usuario_id}_{grupo_usuario}'
                    
                    if timer_key not in st.session_state:
                        st.session_state[timer_key] = obtener_hora_madrid()
                    
                    tiempo_transcurrido = (obtener_hora_madrid() - st.session_state[timer_key]).total_seconds()
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
                        if st.button("✅ **Confirmar**", 
                                   key=f"sidebar_confirmar_{usuario_id}_{grupo_usuario}", 
                                   use_container_width=True):
                            pausa_usuario['estado'] = 'EN_CURSO'
                            pausa_usuario['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                            pausa_usuario['confirmado'] = True
                            guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                            
                            # Limpiar temporizador individual
                            if timer_key in st.session_state:
                                del st.session_state[timer_key]
                            
                            # Notificar al siguiente en este grupo
                            if hasattr(temporizador_pvd_mejorado, '_iniciar_siguiente_automatico_grupo'):
                                temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_usuario)
                            
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ **Cancelar**", 
                                   key=f"sidebar_cancelar_{usuario_id}_{grupo_usuario}", 
                                   use_container_width=True):
                            pausa_usuario['estado'] = 'CANCELADO'
                            pausa_usuario['motivo_cancelacion'] = 'cancelado_por_usuario'
                            guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                            
                            # Limpiar temporizador individual
                            if timer_key in st.session_state:
                                del st.session_state[timer_key]
                            
                            temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                            st.rerun()
                    
                    # Verificar si se agotó el tiempo (7 MINUTOS INDIVIDUALES)
                    if tiempo_transcurrido > 420:
                        st.sidebar.error("⏰ **¡Tiempo agotado!**")
                        pausa_usuario['estado'] = 'CANCELADO'
                        pausa_usuario['motivo_cancelacion'] = 'tiempo_confirmacion_expirado'
                        pausa_usuario['timestamp_cancelacion'] = obtener_hora_madrid().isoformat()
                        guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                        
                        # Limpiar temporizador individual
                        if timer_key in st.session_state:
                            del st.session_state[timer_key]
                        
                        temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                        
                        # Notificar al siguiente
                        if hasattr(temporizador_pvd_mejorado, '_iniciar_siguiente_automatico_grupo'):
                            temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_usuario)
                        
                        st.rerun()
                
                else:
                    # Botón para cancelar mientras espera
                    if st.button("❌ Cancelar espera", 
                               key=f"sidebar_cancelar_espera_{usuario_id}_{grupo_usuario}", 
                               use_container_width=True):
                        pausa_usuario['estado'] = 'CANCELADO'
                        guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                        temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                        st.rerun()
            
            return True
        
        # ============================================
        # CASO 2: USUARIO EN PAUSA (EN_CURSO)
        # ============================================
        elif pausa_usuario['estado'] == 'EN_CURSO':
            st.sidebar.markdown("---")
            
            duracion_elegida = pausa_usuario.get('duracion_elegida', 'corta')
            
            # Usar configuración del grupo
            duracion_minutos = (config_grupo['duracion_corta'] 
                              if duracion_elegida == 'corta' 
                              else config_grupo['duracion_larga'])
            
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
                st.sidebar.markdown(f"**Grupo:** {grupo_usuario}")
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
                if st.button("⏹️ Finalizar ahora", 
                           key=f"sidebar_finalizar_{usuario_id}_{grupo_usuario}", 
                           use_container_width=True):
                    pausa_usuario['estado'] = 'COMPLETADO'
                    pausa_usuario['timestamp_fin'] = obtener_hora_madrid().isoformat()
                    guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                    
                    # Notificar al siguiente en este grupo
                    if hasattr(temporizador_pvd_mejorado, '_iniciar_siguiente_automatico_grupo'):
                        temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_usuario)
                    
                    st.rerun()
            
            return True
        
        return False
    
    except Exception as e:
        print(f"Error en mostrar_notificacion_sidebar: {e}")
        return False

# ==============================================
# FUNCIÓN PRINCIPAL MODIFICADA PARA SIDEBAR
# ==============================================

def verificar_turno_sidebar():
    """Verifica si es el turno del usuario y muestra notificación en sidebar - CON BOTÓN REFRESCAR ARRIBA"""
    
    try:
        if not st.session_state.get('authenticated', False):
            return False
        
        # MOSTRAR BOTÓN DE REFRESCAR PRIMERO (PARTE SUPERIOR DEL SIDEBAR)
        st.sidebar.markdown("---")
        if st.sidebar.button("🔄 **Refrescar página**", 
                           use_container_width=True, 
                           type="secondary",
                           key="refresh_manual_top"):
            st.rerun()
        
        if st.session_state.get('user_type') != 'user':
            return False
        
        usuarios_config = cargar_configuracion_usuarios()
        usuario_id = st.session_state.username
        
        if usuario_id not in usuarios_config:
            return False
        
        grupo_usuario = usuarios_config[usuario_id].get('grupo', 'basico')
        
        # Llamar a la función de notificación (la línea original se mantiene)
        return mostrar_notificacion_sidebar(usuario_id, grupo_usuario)
    
    except Exception as e:
        print(f"Error en verificar_turno_sidebar: {e}")
        return False

# ==============================================
# FUNCIONES PARA SUPER USERS (MANTENIDAS)
# ==============================================

def mostrar_sidebar_super_user():
    """Muestra el sidebar con alertas y opciones para Super Users"""
    
    st.sidebar.title("🔔 Panel Super User")
    
    # Botón de refrescar también para super users
    if st.sidebar.button("🔄 Refrescar página", 
                        use_container_width=True, 
                        type="secondary",
                        key="refresh_super_user"):
        st.rerun()
    
    # Cargar alertas
    from super_users_functions import obtener_alertas_pendientes, cargar_super_users
    
    alertas = obtener_alertas_pendientes()
    super_users_config = cargar_super_users()
    
    # Mostrar número de alertas pendientes
    if alertas:
        alertas_pendientes = [a for a in alertas.values() if a['estado'] == 'pendiente']
        st.sidebar.markdown(f"### ⚠️ Alertas Pendientes: **{len(alertas_pendientes)}**")
        
        # Mostrar cada alerta
        for alerta_id, alerta in list(alertas.items())[:5]:  # Mostrar primeras 5
            if alerta['estado'] == 'pendiente':
                with st.sidebar.expander(f"🔴 {alerta['agente']} - {alerta['fecha']}", expanded=False):
                    st.write(f"**Tipo:** {alerta['tipo']}")
                    st.write(f"**Hora:** {alerta['hora']}")
                    st.write(f"**Duración:** {alerta['duracion']}")
                    st.write(f"**Ventas Pendientes:** {alerta['ventas_pendientes']}")
                    
                    if alerta['resultado_elec']:
                        st.write(f"**Resultado Elec:** {alerta['resultado_elec']}")
                    if alerta['motivo_elec']:
                        st.write(f"**Motivo Elec:** {alerta['motivo_elec']}")
                    if alerta['resultado_gas']:
                        st.write(f"**Resultado Gas:** {alerta['resultado_gas']}")
                    if alerta['motivo_gas']:
                        st.write(f"**Motivo Gas:** {alerta['motivo_gas']}")
                    
                    # Botones de acción
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirmar", key=f"confirm_{alerta_id}"):
                            from super_users_functions import confirmar_venta_sms
                            if confirmar_venta_sms(alerta_id, st.session_state.get('usuario_actual')):
                                st.success("Venta confirmada!")
                                st.rerun()
                    
                    with col2:
                        if st.button("❌ Rechazar", key=f"reject_{alerta_id}"):
                            from super_users_functions import rechazar_venta_sms
                            if rechazar_venta_sms(alerta_id, st.session_state.get('usuario_actual')):
                                st.success("Venta rechazada!")
                                st.rerun()
        
        # Enlace para ver todas las alertas
        if len(alertas_pendientes) > 5:
            st.sidebar.info(f"💡 Hay {len(alertas_pendientes) - 5} alertas más. Ve a 'Gestionar Alertas' para ver todas.")
    
    else:
        st.sidebar.success("✅ No hay alertas pendientes")
    
    # Opciones del sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones")
    
    if st.sidebar.button("📋 Gestionar Alertas", use_container_width=True):
        st.session_state.mostrar_gestion_alertas = True
        st.rerun()
    
    if st.sidebar.button("👥 Gestionar Agentes", use_container_width=True):
        st.session_state.mostrar_gestion_agentes = True
        st.rerun()
    
    if st.sidebar.button("⚙️ Configuración", use_container_width=True):
        st.session_state.mostrar_configuracion = True
        st.rerun()

# ==============================================
# FUNCIÓN PARA ACTUALIZAR MAIN_APP.PY
# ==============================================

def eliminar_mensaje_refresco_automatico():
    """Elimina el mensaje falso de refresco automático cada 60s"""
    # Esta función NO hace nada, simplemente indica que el mensaje debe eliminarse
    # El mensaje falso estaba en main_app.py en estas líneas:
    # st.sidebar.caption(f"⏱️ Temporizador automático: 60s")
    # st.sidebar.caption(f"🔄 Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
    pass