import streamlit as st
from datetime import datetime, timedelta
from utils import obtener_hora_madrid, formatear_hora_madrid
from database import cargar_cola_pvd, cargar_config_pvd, guardar_cola_pvd, cargar_config_sistema
from pvd_system import temporizador_pvd_mejorado

def calcular_tiempo_estimado_real(cola_pvd, config_pvd, grupo_usuario, usuario_id):
    """Calcula tiempo estimado real considerando pausas activas y tiempos restantes"""
    from datetime import datetime
    from utils import obtener_hora_madrid
    
    try:
        # 1. Obtener configuración del grupo
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2})
        max_simultaneo = config_grupo.get('maximo_simultaneo', 2)
        
        # 2. Pausas activas en el grupo
        pausas_activas = [p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario]
        
        # 3. Calcular EXACTAMENTE cuándo termina cada pausa activa
        tiempos_fin_pausas = []
        for pausa in pausas_activas:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_total = config_pvd.get('duracion_corta', 5) if duracion_elegida == 'corta' else config_pvd.get('duracion_larga', 10)
            
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
        
        # 4. Ordenar por tiempo restante (la que termina primero)
        tiempos_fin_pausas.sort(key=lambda x: x['tiempo_restante_minutos'])
        
        # 5. Posición del usuario en espera
        en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = 0
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['usuario_id'] == usuario_id:
                posicion = i + 1
                break
        
        if posicion == 0:
            return 0  # No está en espera
        
        # 6. Calcular espacios disponibles
        espacios_disponibles = max(0, max_simultaneo - len(pausas_activas))
        
        # 7. Si hay espacio y es el primero, puede entrar inmediatamente
        if espacios_disponibles > 0 and posicion == 1:
            return 0
        
        # 8. Si no hay espacio (ambos huecos ocupados)
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
                    # Calcular cuántas personas delante también están esperando
                    personas_delante = posicion - 1
                    
                    # Cada persona delante necesita que termine una pausa
                    # Si hay 2 pausas activas, cuando termine la primera, entra la primera persona
                    # Cuando termine la segunda, entra la segunda persona, etc.
                    
                    # Cuántas pausas necesita esperar
                    pausas_necesarias = min(personas_delante, len(tiempos_fin_pausas))
                    
                    if pausas_necesarias > 0:
                        # Tiempo hasta que terminen las pausas necesarias
                        tiempo_estimado = tiempos_fin_pausas[pausas_necesarias - 1]['tiempo_restante_minutos']
                        return max(1, int(tiempo_estimado + 0.5))
            
            # Si no hay información de pausas activas, usar duración promedio
            duracion_promedio = (config_pvd.get('duracion_corta', 5) + config_pvd.get('duracion_larga', 10)) / 2
            tiempo_estimado = (posicion * duracion_promedio) / max_simultaneo
            return max(1, int(tiempo_estimado + 0.5))
        
        # 9. Si hay espacio pero no es el primero
        if espacios_disponibles > 0 and posicion > 1:
            # Algunas personas delante entrarán inmediatamente (hasta llenar espacios)
            personas_que_entran_inmediatamente = min(posicion - 1, espacios_disponibles)
            personas_que_esperan = max(0, (posicion - 1) - personas_que_entran_inmediatamente)
            
            if personas_que_esperan == 0:
                # Todas las personas delante entran inmediatamente
                return 0
            else:
                # Necesita esperar a que terminen pausas para las personas que esperan
                if tiempos_fin_pausas and personas_que_esperan <= len(tiempos_fin_pausas):
                    tiempo_estimado = tiempos_fin_pausas[personas_que_esperan - 1]['tiempo_restante_minutos']
                    return max(1, int(tiempo_estimado + 0.5))
                else:
                    duracion_promedio = (config_pvd.get('duracion_corta', 5) + config_pvd.get('duracion_larga', 10)) / 2
                    tiempo_estimado = (personas_que_esperan * duracion_promedio) / max_simultaneo
                    return max(1, int(tiempo_estimado + 0.5))
        
        # 10. Caso por defecto (no debería llegar aquí)
        return 5
    
    except Exception as e:
        print(f"Error calculando tiempo estimado: {e}")
        # Valor por defecto seguro
        return 5  # 5 minutos por defecto

def mostrar_info_detallada_pausas(cola_pvd, config_pvd, grupo_usuario):
    """Muestra información detallada de las pausas activas (para debug)"""
    from datetime import datetime
    from utils import obtener_hora_madrid
    
    pausas_activas = [p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario]
    
    if not pausas_activas:
        return "No hay pausas activas"
    
    info = "**Pausas activas:**\n"
    for i, pausa in enumerate(pausas_activas, 1):
        duracion_elegida = pausa.get('duracion_elegida', 'corta')
        duracion_total = config_pvd.get('duracion_corta', 5) if duracion_elegida == 'corta' else config_pvd.get('duracion_larga', 10)
        
        tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
        tiempo_fin = tiempo_inicio + timedelta(minutes=duracion_total)
        tiempo_restante = (tiempo_fin - obtener_hora_madrid()).total_seconds() / 60
        
        hora_fin_str = tiempo_fin.strftime('%H:%M')
        
        info += f"{i}. {pausa['usuario_nombre']} - "
        info += f"Termina a las {hora_fin_str} "
        info += f"(en {int(tiempo_restante)} min)\n"
    
    return info

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
    
    # Obtener configuración del grupo UNA SOLA VEZ
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2, 'agentes_por_grupo': 10})
    max_simultaneo_grupo = config_grupo.get('maximo_simultaneo', 2)
    
    # ============================================
    # CASO 1: USUARIO EN ESPERA
    # ============================================
    if pausa_usuario['estado'] == 'ESPERANDO':
        st.sidebar.markdown("---")
        
        # Calcular posición en el grupo
        en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = 0
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['id'] == pausa_usuario['id']:
                posicion = i + 1
                break
        
        if posicion == 0:
            return False  # No está en espera (no debería pasar)
        
        # Calcular espacios disponibles UNA SOLA VEZ
        en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario])
        espacios_disponibles_grupo = max(0, max_simultaneo_grupo - en_pausa_grupo)
        
        # Calcular tiempo estimado REAL
        tiempo_estimado = calcular_tiempo_estimado_real(cola_pvd, config_pvd, grupo_usuario, usuario_id)
        
        # Mostrar información de pausas activas (debug - opcional)
        # COMENTADO PARA PRODUCCIÓN, DESCOMENTAR PARA DEBUG
        # info_pausas = mostrar_info_detallada_pausas(cola_pvd, config_pvd, grupo_usuario)
        # st.sidebar.caption(info_pausas)
        
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
            st.sidebar.markdown(f"**Espacios libres:** {espacios_disponibles_grupo}/{max_simultaneo_grupo}")
            
            # Mostrar tiempo estimado MEJORADO
            if tiempo_estimado <= 0:
                st.sidebar.markdown(f"**Tiempo estimado:** < 1 minuto")
            elif tiempo_estimado == 1:
                st.sidebar.markdown(f"**Tiempo estimado:** ~1 minuto")
            else:
                st.sidebar.markdown(f"**Tiempo estimado:** ~{tiempo_estimado} minutos")
            
            st.sidebar.markdown("</div>", unsafe_allow_html=True)
            
            # Barra de progreso estimada (solo si hay tiempo estimado)
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
                    guardar_cola_pvd(cola_pvd)
                
                # Contador de 7 minutos INDIVIDUAL
                timer_key = f'confirmacion_inicio_{usuario_id}'
                
                if timer_key not in st.session_state:
                    # INICIO INDIVIDUAL DEL TEMPORIZADOR PARA ESTE USUARIO
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
                    if st.button("✅ **Confirmar**", key=f"sidebar_confirmar_{usuario_id}", use_container_width=True):
                        pausa_usuario['estado'] = 'EN_CURSO'
                        pausa_usuario['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                        pausa_usuario['confirmado'] = True
                        guardar_cola_pvd(cola_pvd)
                        
                        # Limpiar temporizador individual
                        timer_key = f'confirmacion_inicio_{usuario_id}'
                        if timer_key in st.session_state:
                            del st.session_state[timer_key]
                        
                        st.rerun()
                
                with col2:
                    if st.button("❌ **Cancelar**", key=f"sidebar_cancelar_{usuario_id}", use_container_width=True):
                        pausa_usuario['estado'] = 'CANCELADO'
                        pausa_usuario['motivo_cancelacion'] = 'cancelado_por_usuario'
                        guardar_cola_pvd(cola_pvd)
                        
                        # Limpiar temporizador individual
                        timer_key = f'confirmacion_inicio_{usuario_id}'
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
                    guardar_cola_pvd(cola_pvd)
                    
                    # Limpiar temporizador individual
                    timer_key = f'confirmacion_inicio_{usuario_id}'
                    if timer_key in st.session_state:
                        del st.session_state[timer_key]
                    
                    temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                    temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, grupo_usuario)
                    st.rerun()
            
            else:
                # Botón para cancelar mientras espera
                if st.button("❌ Cancelar espera", key=f"sidebar_cancelar_espera_{usuario_id}", use_container_width=True):
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
        duracion_minutos = config_pvd.get('duracion_corta', 5) if duracion_elegida == 'corta' else config_pvd.get('duracion_larga', 10)  # CORREGIDO: 5/10 no 7/14
        
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
            if st.button("⏹️ Finalizar ahora", key=f"sidebar_finalizar_{usuario_id}", use_container_width=True):
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