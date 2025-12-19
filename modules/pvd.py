import streamlit as st
import json
import os
import shutil
from datetime import datetime
from modules.utils import enviar_notificacion_navegador

PVD_CONFIG_DEFAULT = {
    "agentes_activos": 25,  # Total de agentes trabajando
    "maximo_simultaneo": 3,  # Máximo que pueden estar en pausa a la vez
    "duracion_corta": 5,    # minutos - duración corta
    "duracion_larga": 10,   # minutos - duración larga  
    "sonido_activado": True
}

# Estados de la cola PVD
ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

def cargar_config_pvd():
    """Carga la configuración del sistema PVD con migración automática"""
    try:
        with open('data/config_pvd.json', 'r') as f:
            config = json.load(f)
            
        # MIGRACIÓN: Si existe el campo antiguo 'duracion_pvd', migrar a los nuevos campos
        if 'duracion_pvd' in config and 'duracion_corta' not in config:
            duracion_antigua = config['duracion_pvd']
            config['duracion_corta'] = duracion_antigua
            config['duracion_larga'] = duracion_antigua * 2  # La larga es el doble por defecto
            
            # Guardar la configuración migrada
            guardar_config_pvd(config)
            print(f"✅ Config PVD migrada: duracion_pvd={duracion_antigua} -> corta={duracion_antigua}, larga={duracion_antigua*2}")
        
        # Asegurar que todos los campos existan
        campos_requeridos = ['agentes_activos', 'maximo_simultaneo', 'duracion_corta', 'duracion_larga', 'sonido_activado']
        for campo in campos_requeridos:
            if campo not in config:
                config[campo] = PVD_CONFIG_DEFAULT[campo]
        
        return config
    except FileNotFoundError:
        # Si no existe el archivo, crear uno nuevo
        return PVD_CONFIG_DEFAULT.copy()
    except json.JSONDecodeError:
        # Si el archivo está corrupto
        return PVD_CONFIG_DEFAULT.copy()

def guardar_config_pvd(config):
    """Guarda la configuración PVD asegurando todos los campos"""
    # Asegurar que todos los campos estén presentes
    for campo, valor in PVD_CONFIG_DEFAULT.items():
        if campo not in config:
            config[campo] = valor
    
    os.makedirs('data', exist_ok=True)
    with open('data/config_pvd.json', 'w') as f:
        json.dump(config, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/config_pvd.json', 'data_backup/config_pvd.json')

def cargar_cola_pvd():
    """Carga la cola actual de PVD"""
    try:
        with open('data/cola_pvd.json', 'r') as f:
            return json.load(f)
    except:
        return []

def guardar_cola_pvd(cola):
    """Guarda la cola PVD"""
    os.makedirs('data', exist_ok=True)
    with open('data/cola_pvd.json', 'w') as f:
        json.dump(cola, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/cola_pvd.json', 'data_backup/cola_pvd.json')

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Verifica y finaliza automáticamente pausas que han terminado"""
    hubo_cambios = False
    
    for pausa in cola_pvd:
        if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
            
            if tiempo_transcurrido >= duracion_minutos:
                # Finalizar esta pausa
                pausa['estado'] = 'COMPLETADO'
                pausa['timestamp_fin'] = datetime.now().isoformat()
                hubo_cambios = True
                
                # Iniciar la siguiente en cola si hay espacio
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
    
    if hubo_cambios:
        guardar_cola_pvd(cola_pvd)
    
    return hubo_cambios

def iniciar_siguiente_en_cola(cola_pvd, config_pvd):
    """Inicia automáticamente la siguiente pausa en la cola si hay espacio"""
    # Contar pausas en curso
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    # Si hay espacio, iniciar la siguiente en cola
    if en_pausa < maximo:
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        if en_espera:
            siguiente = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))[0]
            siguiente['estado'] = 'EN_CURSO'
            siguiente['timestamp_inicio'] = datetime.now().isoformat()
            
            # Notificar al usuario
            if config_pvd.get('sonido_activado', True):
                notificar_inicio_pausa(siguiente, config_pvd)
            
            return True
    
    return False

def finalizar_pausa(pausa, cola_pvd):
    """Finaliza una pausa manualmente"""
    pausa['estado'] = 'COMPLETADO'
    pausa['timestamp_fin'] = datetime.now().isoformat()
    guardar_cola_pvd(cola_pvd)
    st.success(f"✅ Pausa #{pausa['id']} finalizada")

def iniciar_pausa_desde_cola(pausa, cola_pvd, config_pvd):
    """Inicia una pausa desde la cola de espera"""
    # Verificar si hay espacio
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    if en_pausa < maximo:
        pausa['estado'] = 'EN_CURSO'
        pausa['timestamp_inicio'] = datetime.now().isoformat()
        guardar_cola_pvd(cola_pvd)
        st.success(f"✅ Pausa #{pausa['id']} iniciada")
    else:
        st.error("❌ No hay espacio disponible. Espera a que termine alguna pausa.")

def notificar_inicio_pausa(pausa, config_pvd):
    """Envía notificación al usuario cuando su pausa inicia"""
    try:
        duracion_minutos = config_pvd['duracion_corta'] if pausa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
        mensaje = f"¡Tu pausa de {duracion_minutos} minutos ha comenzado! ⏰"
        
        # Notificación de navegador
        notification_js = f"""
        <script>
        if ("Notification" in window) {{
            if (Notification.permission === "granted") {{
                new Notification("Pausa Iniciada 🎉", {{
                    body: "{mensaje}",
                    icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
                }});
            }}
        }}
        </script>
        """
        st.components.v1.html(notification_js, height=0)
        
    except Exception as e:
        print(f"Error en notificación: {e}")

def solicitar_pausa(config_pvd, cola_pvd, duracion_elegida):
    """Solicita una nueva pausa visual - SIEMPRE permite solicitud"""
    # Generar nuevo ID
    nuevo_id = max([p['id'] for p in cola_pvd], default=0) + 1
    
    # Obtener duración en minutos
    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
    
    # Verificar si hay espacio inmediato
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
    
    estado_inicial = 'EN_CURSO' if en_pausa < maximo else 'ESPERANDO'
    
    nuevo_pvd = {
        'id': nuevo_id,
        'usuario_id': st.session_state.username,
        'usuario_nombre': st.session_state.get('user_config', {}).get('nombre', 'Usuario'),
        'estado': estado_inicial,
        'duracion_elegida': duracion_elegida,
        'duracion_minutos': duracion_minutos,
        'timestamp_solicitud': datetime.now().isoformat(),
    }
    
    # Si va directamente a pausa, añadir timestamp de inicio
    if estado_inicial == 'EN_CURSO':
        nuevo_pvd['timestamp_inicio'] = datetime.now().isoformat()
        mensaje = f"✅ **¡Pausa iniciada inmediatamente!** Tienes {duracion_minutos} minutos"
        
        # Notificación de inicio inmediato
        if st.session_state.get('notificaciones_activas', True):
            enviar_notificacion_navegador(
                "Pausa iniciada 🎉", 
                f"Tu pausa de {duracion_minutos} minutos ha comenzado",
                "✅"
            )
    else:
        posicion_en_cola = en_espera + 1
        mensaje = f"✅ **Pausa solicitada** - Estás en cola (posición #{posicion_en_cola}). Te avisaremos cuando haya espacio."
        
        # Notificación de estar en cola
        if st.session_state.get('notificaciones_activas', True):
            enviar_notificacion_navegador(
                "Pausa solicitada ⏳", 
                f"Estás en cola (posición #{posicion_en_cola}). Te avisaremos cuando sea tu turno",
                "📋"
            )
    
    cola_pvd.append(nuevo_pvd)
    guardar_cola_pvd(cola_pvd)
    
    st.success(mensaje)
    if estado_inicial == 'EN_CURSO':
        st.balloons()

def verificar_y_notificar_turno_pvd_mejorado(config_pvd, cola_pvd, usuario_pausa_activa):
    """Verifica mejorado si es el turno del usuario"""
    try:
        # Verificar si hay espacio
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        maximo = config_pvd['maximo_simultaneo']
        
        if en_pausa >= maximo:
            return False
        
        # Verificar si es el primero en la cola
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        if not en_espera:
            return False
        
        en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        primer_en_cola = en_espera_ordenados[0]
        
        if primer_en_cola['id'] == usuario_pausa_activa['id']:
            # Usar session_state para evitar notificaciones repetidas
            notificacion_key = f"notificado_turno_{usuario_pausa_activa['id']}"
            
            if not st.session_state.get(notificacion_key, False):
                st.session_state[notificacion_key] = True
                
                # Notificar
                duracion_minutos = config_pvd['duracion_corta'] if usuario_pausa_activa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
                
                # 1. Notificación del navegador
                titulo = "¡Es tu turno! ⏰"
                mensaje = f"Hay espacio para tu pausa de {duracion_minutos} minutos"
                enviar_notificacion_navegador(titulo, mensaje)
                
                # 2. Sonido
                audio_html = """
                <audio autoplay>
                    <source src="https://assets.mixkit.co/sfx/preview/mixkit-alarm-digital-clock-beep-989.mp3" type="audio/mpeg">
                </audio>
                <script>
                    var audio = document.querySelector('audio');
                    audio.volume = 0.7;
                    audio.play().catch(function(e) {
                        console.log('Audio error:', e);
                    });
                </script>
                """
                st.components.v1.html(audio_html, height=0)
                
                return True
    
    except Exception as e:
        print(f"Error en verificación de turno: {e}")
    
    return False

def gestion_pvd_admin():
    st.subheader("👁️ Administración PVD (Pausa Visual Dinámica)")
    
    # Cargar configuración
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    # --- BOTÓN DE ACTUALIZAR MANUAL ---
    col_refresh1, col_refresh2 = st.columns([3, 1])
    with col_refresh1:
        st.write("")
    with col_refresh2:
        if st.button("🔄 Actualizar Estado", key="refresh_admin", use_container_width=True):
            # Verificar y completar pausas automáticamente
            verificar_pausas_completadas(cola_pvd, config_pvd)
            st.rerun()
    
    # --- CONFIGURACIÓN DEL SISTEMA ---
    st.write("### ⚙️ Configuración del Sistema para Agentes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📊 Capacidad del Centro**")
        agentes_activos = st.number_input(
            "Total de Agentes Trabajando",
            min_value=1,
            max_value=100,
            value=config_pvd['agentes_activos'],
            help="Número total de agentes que están trabajando actualmente en el call center"
        )
    
    with col2:
        st.write("**⏱️ Límites de Pausas**")
        maximo_simultaneo = st.number_input(
            "Máximo en Pausa Simultáneamente",
            min_value=1,
            max_value=50,
            value=config_pvd['maximo_simultaneo'],
            help="Máximo número de agentes que pueden estar en pausa al mismo tiempo. Los demás esperan en cola."
        )
    
    st.write("**🕐 Duración de Pausas**")
    col_dura1, col_dura2 = st.columns(2)
    with col_dura1:
        duracion_corta = st.number_input(
            "Duración Pausa Corta (minutos)",
            min_value=1,
            max_value=30,
            value=config_pvd['duracion_corta'],
            help="Duración de la pausa corta (ej: 5 minutos)"
        )
    with col_dura2:
        duracion_larga = st.number_input(
            "Duración Pausa Larga (minutos)",
            min_value=1,
            max_value=60,
            value=config_pvd['duracion_larga'],
            help="Duración de la pausa larga (ej: 10 minutos)"
        )
    
    sonido_activado = st.checkbox(
        "Activar sonido de notificación",
        value=config_pvd.get('sonido_activado', True),
        help="Reproduce sonido cuando sea el turno de un agente"
    )
    
    if st.button("💾 Guardar Configuración", type="primary"):
        config_pvd.update({
            'agentes_activos': agentes_activos,
            'maximo_simultaneo': maximo_simultaneo,
            'duracion_corta': duracion_corta,
            'duracion_larga': duracion_larga,
            'sonido_activado': sonido_activado
        })
        guardar_config_pvd(config_pvd)
        st.success("✅ Configuración PVD guardada")
        st.rerun()
    
    # --- VERIFICAR Y ACTUALIZAR ESTADO AUTOMÁTICAMENTE ---
    verificar_pausas_completadas(cola_pvd, config_pvd)
    
    # --- ESTADÍSTICAS ACTUALES ---
    st.markdown("---")
    st.write("### 📊 Estado Actual del Sistema")
    
    # Calcular estadísticas actualizadas
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
    completados_hoy = len([p for p in cola_pvd if p['estado'] == 'COMPLETADO' and 
                          datetime.fromisoformat(p.get('timestamp_fin', datetime.now().isoformat())).date() == datetime.now().date()])
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("👥 Agentes Trabajando", agentes_activos)
    with col_stat2:
        st.metric("⏸️ En Pausa Ahora", f"{en_pausa}/{maximo_simultaneo}")
    with col_stat3:
        st.metric("⏳ Esperando", en_espera)
    with col_stat4:
        st.metric("✅ Completadas Hoy", completados_hoy)
    
    # --- GESTIÓN DE PAUSAS ACTIVAS ---
    st.markdown("---")
    st.write("### 📋 Pausas en Curso")
    
    pausas_en_curso = [p for p in cola_pvd if p['estado'] == 'EN_CURSO']
    
    if pausas_en_curso:
        for pausa in pausas_en_curso:
            with st.container():
                col_info, col_acciones = st.columns([3, 1])
                
                with col_info:
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    # Barra de progreso
                    progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
                    st.progress(int(progreso))
                    
                    st.write(f"**Agente:** {pausa.get('usuario_nombre', 'Desconocido')}")
                    st.write(f"**Usuario ID:** {pausa['usuario_id']}")
                    st.write(f"**Duración:** {duracion_minutos} min ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
                    st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')} | **Restante:** {tiempo_restante} min")
                    
                    # Verificar si la pausa ha terminado
                    if tiempo_restante == 0:
                        st.warning("⏰ **Pausa finalizada automáticamente**")
                
                with col_acciones:
                    if st.button("✅ Finalizar", key=f"fin_{pausa['id']}"):
                        finalizar_pausa(pausa, cola_pvd)
                        st.rerun()
                    
                    if st.button("❌ Cancelar", key=f"cancel_{pausa['id']}"):
                        pausa['estado'] = 'CANCELADO'
                        guardar_cola_pvd(cola_pvd)
                        st.warning(f"⚠️ Pausa #{pausa['id']} cancelada")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("🎉 No hay pausas activas en este momento")
    
    # --- COLA DE ESPERA ---
    if en_espera > 0:
        st.write("### 📝 Cola de Espera")
        
        en_espera_lista = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        en_espera_ordenados = sorted(en_espera_lista, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        for i, pausa in enumerate(en_espera_ordenados):
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_display = f"{config_pvd['duracion_corta']} min" if duracion_elegida == 'corta' else f"{config_pvd['duracion_larga']} min"
            
            col_esp1, col_esp2, col_esp3, col_esp4 = st.columns([3, 2, 2, 1])
            with col_esp1:
                st.write(f"**#{i+1}** - {pausa.get('usuario_nombre', 'Desconocido')}")
            with col_esp2:
                st.write(f"🆔 {pausa['usuario_id']}")
            with col_esp3:
                st.write(f"⏱️ {duracion_display}")
            with col_esp4:
                if st.button("▶️ Iniciar", key=f"iniciar_{pausa['id']}"):
                    iniciar_pausa_desde_cola(pausa, cola_pvd, config_pvd)
                    st.rerun()
    
    # --- HISTORIAL RECIENTE ---
    st.markdown("---")
    st.write("### 📜 Historial Reciente (Últimas 10)")
    
    completados = [p for p in cola_pvd if p['estado'] == 'COMPLETADO']
    completados_recientes = sorted(completados, key=lambda x: x.get('timestamp_fin', ''), reverse=True)[:10]
    
    if completados_recientes:
        for pausa in completados_recientes:
            fecha_fin = datetime.fromisoformat(pausa.get('timestamp_fin', datetime.now().isoformat()))
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_display = "5 min" if duracion_elegida == 'corta' else "10 min"
            
            # Calcular tiempo transcurrido
            tiempo_finalizacion = fecha_fin.strftime('%H:%M:%S')
            st.write(f"**{tiempo_finalizacion}** - {pausa.get('usuario_nombre', 'Desconocido')} - {duracion_display}")
    else:
        st.info("No hay pausas completadas recientemente")
    
    # --- LIMPIAR HISTORIAL ---
    st.markdown("---")
    st.write("### 🧹 Mantenimiento")
    
    col_clean1, col_clean2 = st.columns(2)
    with col_clean1:
        if st.button("🗑️ Limpiar Historial Antiguo", type="secondary"):
            # Mantener solo activos y últimos 50 completados
            activos = [p for p in cola_pvd if p['estado'] in ['ESPERANDO', 'EN_CURSO']]
            completados = [p for p in cola_pvd if p['estado'] == 'COMPLETADO']
            completados = sorted(completados, key=lambda x: x.get('timestamp_fin', ''), reverse=True)[:50]
            nueva_cola = activos + completados
            guardar_cola_pvd(nueva_cola)
            st.success("✅ Historial limpiado (solo últimos 50 completados)")
            st.rerun()
    
    with col_clean2:
        if st.button("🔄 Reiniciar Sistema PVD", type="secondary"):
            # Cancelar todas las pausas activas
            for pausa in cola_pvd:
                if pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
                    pausa['estado'] = 'CANCELADO'
            guardar_cola_pvd(cola_pvd)
            st.warning("⚠️ Sistema PVD reiniciado - Todas las pausas canceladas")
            st.rerun()

def gestion_pvd_usuario():
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    # Verificar y actualizar estado automáticamente
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    verificar_pausas_completadas(cola_pvd, config_pvd)
    
    # --- CONFIGURACIÓN DE NOTIFICACIONES DEL USUARIO ---
    if 'notificaciones_activas' not in st.session_state:
        st.session_state.notificaciones_activas = True
    
    col_notif1, col_notif2 = st.columns([3, 1])
    with col_notif1:
        st.write("")
    with col_notif2:
        notif_activadas = st.checkbox(
            "🔔 Notificaciones",
            value=st.session_state.notificaciones_activas,
            key="toggle_notificaciones",
            help="Activar/desactivar notificaciones del navegador"
        )
        if notif_activadas != st.session_state.notificaciones_activas:
            st.session_state.notificaciones_activas = notif_activadas
            if notif_activadas:
                st.success("Notificaciones activadas")
            else:
                st.warning("Notificaciones desactivadas")
            st.rerun()
    
    # --- BOTÓN DE ACTUALIZAR MANUAL ---
    col_ref1, col_ref2 = st.columns([3, 1])
    with col_ref1:
        st.write("")
    with col_ref2:
        if st.button("🔄 Actualizar", key="refresh_pvd", use_container_width=True):
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    # --- REFRESCO AUTOMÁTICO ---
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    tiempo_transcurrido = (datetime.now() - st.session_state.last_refresh).seconds
    
    # Mostrar contador de refresco
    tiempo_restante = max(0, 30 - tiempo_transcurrido)  # Reducido a 30 segundos
    if tiempo_restante > 0:
        st.caption(f"🕐 Auto-refresco en: {tiempo_restante} segundos")
    
    if tiempo_transcurrido > 30:  # Refresco cada 30 segundos
        st.session_state.last_refresh = datetime.now()
        st.rerun()

    # Verificar si el agente ya tiene una pausa activa
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    # --- SI TIENE PAUSA ACTIVA ---
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.warning(f"⏳ **Tienes una pausa solicitada** - {estado_display}")
            
            # Mostrar información
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            # Calcular posición en cola
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = next((i+1 for i, p in enumerate(en_espera_ordenados) 
                           if p['id'] == usuario_pausa_activa['id']), 1)
            
            # Calcular pausas en curso
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            st.write(f"**Tu pausa:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Posición en cola:** #{posicion} de {len(en_espera)}")
            st.write(f"**Estado:** {en_pausa}/{maximo} pausas activas")
            
            # Verificar si es nuestro turno
            if posicion == 1 and en_pausa < maximo:
                st.success("🎯 **¡Próximo!** Serás el siguiente en salir a pausa")
                # Intentar iniciar automáticamente
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.rerun()
            else:
                tiempo_espera = ""
                if 'timestamp_solicitud' in usuario_pausa_activa:
                    tiempo_solicitud = datetime.fromisoformat(usuario_pausa_activa['timestamp_solicitud'])
                    minutos_esperando = (datetime.now() - tiempo_solicitud).seconds // 60
                    tiempo_espera = f" | Esperando: {minutos_esperando} min"
                
                st.info(f"📋 **En cola:** Posición #{posicion}{tiempo_espera}")
            
            # Botón para cancelar
            if st.button("❌ Cancelar mi pausa", type="secondary"):
                usuario_pausa_activa['estado'] = 'CANCELADO'
                guardar_cola_pvd(cola_pvd)
                st.success("✅ Pausa cancelada")
                st.rerun()
        
        elif usuario_pausa_activa['estado'] == 'EN_CURSO':
            st.success(f"✅ **Pausa en curso** - {estado_display}")
            
            # Obtener duración elegida
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(usuario_pausa_activa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            # Barra de progreso
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            col_tiempo1, col_tiempo2 = st.columns(2)
            with col_tiempo1:
                st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
            with col_tiempo2:
                st.metric("⏳ Restante", f"{tiempo_restante} min")
            
            st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')}")
            
            # Verificar si la pausa ha terminado
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada!** Puedes volver a solicitar otra si necesitas")
            
            # Botón para finalizar manualmente
            if st.button("✅ Finalizar pausa ahora", type="primary"):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now().isoformat()
                guardar_cola_pvd(cola_pvd)
                
                # Iniciar siguiente en cola
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                
                st.success("✅ Pausa completada")
                st.rerun()
    
    # --- SI NO TIENE PAUSA ACTIVA ---
    else:
        st.info("👁️ **Sistema de Pausas Visuales Dinámicas**")
        st.write("Toma una pausa para descansar la vista durante tu jornada")
        
        # Estadísticas actuales
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        maximo = config_pvd['maximo_simultaneo']
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("⏸️ En pausa", f"{en_pausa}/{maximo}")
        with col_stats2:
            st.metric("⏳ En espera", en_espera)
        with col_stats3:
            # Contar pausas del usuario hoy
            pausas_hoy = len([p for p in cola_pvd 
                            if p['usuario_id'] == st.session_state.username and 
                            datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now().isoformat())).date() == datetime.now().date() and
                            p['estado'] != 'CANCELADO'])
            st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
        
        # Verificar límite diario
        if pausas_hoy >= 5:
            st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
            st.info("Puedes tomar más pausas mañana")
        else:
            # Selección de duración
            st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
            
            # Mostrar estado actual
            espacios_libres = max(0, maximo - en_pausa)
            
            if espacios_libres > 0:
                st.success(f"✅ **HAY ESPACIO DISPONIBLE** - {espacios_libres} puesto(s) libre(s)")
            else:
                st.warning(f"⏳ **SISTEMA LLENO** - Hay {en_espera} persona(s) en cola. Te pondremos en espera.")
            
            col_dura1, col_dura2 = st.columns(2)
            with col_dura1:
                duracion_corta = config_pvd['duracion_corta']
                if st.button(
                    f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
                    use_container_width=True,
                    type="primary",
                    key="pausa_corta"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "corta")
                    st.rerun()
            
            with col_dura2:
                duracion_larga = config_pvd['duracion_larga']
                if st.button(
                    f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
                    use_container_width=True,
                    type="secondary",
                    key="pausa_larga"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "larga")
                    st.rerun()
    
    # --- VERIFICAR Y NOTIFICAR TURNO MEJORADO ---
    if config_pvd.get('sonido_activado', True) and st.session_state.get('notificaciones_activas', True):
        # Solo verificar si el usuario está en espera
        if usuario_pausa_activa and usuario_pausa_activa['estado'] == 'ESPERANDO':
            verificar_y_notificar_turno_pvd_mejorado(config_pvd, cola_pvd, usuario_pausa_activa)