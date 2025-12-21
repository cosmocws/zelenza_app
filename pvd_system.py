import streamlit as st
import uuid
from datetime import datetime, timedelta
from utils import obtener_hora_madrid, formatear_hora_madrid
from config import ESTADOS_PVD, TIMEZONE_MADRID
from database import cargar_config_pvd, cargar_cola_pvd, guardar_cola_pvd
import pytz

# ==============================================
# TEMPORIZADOR PVD EN TIEMPO REAL
# ==============================================

class TemporizadorPVD:
    """Clase para manejar temporizadores de cuenta atrás en PVD"""
    
    def __init__(self):
        self.temporizadores_activos = {}
        self.notificaciones_pendientes = {}
        self.avisos_enviados = set()
    
    def calcular_tiempo_estimado_entrada(self, cola_pvd, config_pvd, usuario_id):
        """Calcula el tiempo estimado para que un usuario entre en PVD"""
        try:
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion_usuario = None
            for i, pausa in enumerate(en_espera_ordenados):
                if pausa['usuario_id'] == usuario_id:
                    posicion_usuario = i + 1
                    break
            
            if posicion_usuario is None:
                return None
            
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            if posicion_usuario == 1 and en_pausa < maximo:
                return 0
            
            tiempo_estimado_minutos = 0
            
            pausas_en_curso = [p for p in cola_pvd if p['estado'] == 'EN_CURSO']
            for pausa in pausas_en_curso:
                if 'timestamp_inicio' in pausa:
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    tiempo_estimado_minutos += tiempo_restante
            
            personas_antes = posicion_usuario - 1
            for i in range(personas_antes):
                if i < len(en_espera_ordenados):
                    duracion_elegida = en_espera_ordenados[i].get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    tiempo_estimado_minutos += duracion_minutos
            
            return int(tiempo_estimado_minutos)
            
        except Exception as e:
            print(f"Error calculando tiempo estimado: {e}")
            return None
    
    def enviar_aviso_cola(self, usuario_id, posicion, tiempo_estimado):
        """Envía un aviso cuando el usuario está próximo en la cola"""
        try:
            if tiempo_estimado <= 5 and tiempo_estimado > 0:
                aviso_key = f"{usuario_id}_aviso_5min"
                if aviso_key not in self.avisos_enviados:
                    self.notificaciones_pendientes[usuario_id] = {
                        'timestamp': obtener_hora_madrid(),
                        'mensaje': f'⚠️ ATENCIÓN: Quedan {tiempo_estimado} minutos para tu pausa',
                        'tipo': 'aviso',
                        'hora_madrid': obtener_hora_madrid().strftime('%H:%M:%S')
                    }
                    self.avisos_enviados.add(aviso_key)
                    print(f"[PVD] Aviso enviado a {usuario_id}: {tiempo_estimado} minutos restantes")
                    return True
            
            elif tiempo_estimado <= 1 and tiempo_estimado >= 0:
                aviso_key = f"{usuario_id}_aviso_1min"
                if aviso_key not in self.avisos_enviados:
                    self.notificaciones_pendientes[usuario_id] = {
                        'timestamp': obtener_hora_madrid(),
                        'mensaje': '🔔 ¡ATENCIÓN! Tu pausa está a punto de comenzar',
                        'tipo': 'urgente',
                        'hora_madrid': obtener_hora_madrid().strftime('%H:%M:%S')
                    }
                    self.avisos_enviados.add(aviso_key)
                    print(f"[PVD] Aviso urgente enviado a {usuario_id}")
                    return True
                    
            return False
        except Exception as e:
            print(f"Error enviando aviso de cola: {e}")
            return False
    
    def iniciar_temporizador_usuario(self, usuario_id, tiempo_minutos):
        """Inicia un temporizador para un usuario específico"""
        try:
            tiempo_fin = obtener_hora_madrid() + timedelta(minutes=tiempo_minutos)
            self.temporizadores_activos[usuario_id] = {
                'tiempo_inicio': obtener_hora_madrid(),
                'tiempo_fin': tiempo_fin,
                'tiempo_total_minutos': tiempo_minutos,
                'activo': True,
                'hora_entrada_estimada': tiempo_fin.strftime('%H:%M'),
                'hora_madrid_inicio': obtener_hora_madrid().strftime('%H:%M:%S'),
                'avisos_enviados': []
            }
            
            print(f"[PVD] Temporizador iniciado para {usuario_id}: {tiempo_minutos} minutos")
            return True
        except Exception as e:
            print(f"Error iniciando temporizador: {e}")
            return False
    
    def obtener_tiempo_restante(self, usuario_id):
        """Obtiene el tiempo restante para un usuario en minutos"""
        if usuario_id not in self.temporizadores_activos:
            return None
        
        temporizador = self.temporizadores_activos[usuario_id]
        
        if not temporizador['activo']:
            return None
        
        tiempo_restante = temporizador['tiempo_fin'] - obtener_hora_madrid()
        
        if tiempo_restante.total_seconds() <= 0:
            temporizador['activo'] = False
            return 0
        
        return max(0, tiempo_restante.total_seconds() / 60)
    
    def obtener_tiempo_restante_segundos(self, usuario_id):
        """Obtiene el tiempo restante para un usuario en segundos"""
        minutos = self.obtener_tiempo_restante(usuario_id)
        if minutos is None:
            return None
        return int(minutos * 60)
    
    def obtener_hora_entrada_estimada(self, usuario_id):
        """Obtiene la hora estimada de entrada"""
        if usuario_id in self.temporizadores_activos:
            return self.temporizadores_activos[usuario_id].get('hora_entrada_estimada', '--:--')
        return None
    
    def verificar_notificaciones_pendientes(self, usuario_id):
        """Verifica si hay notificaciones pendientes para un usuario"""
        if usuario_id in self.notificaciones_pendientes:
            notificacion = self.notificaciones_pendientes.pop(usuario_id)
            
            if notificacion.get('tipo') == 'turno':
                self.avisos_enviados = {a for a in self.avisos_enviados if not a.startswith(f"{usuario_id}_")}
            
            return notificacion
        return None
    
    def cancelar_temporizador(self, usuario_id):
        """Cancela el temporizador de un usuario"""
        if usuario_id in self.temporizadores_activos:
            self.temporizadores_activos[usuario_id]['activo'] = False
            del self.temporizadores_activos[usuario_id]
            
            self.avisos_enviados = {a for a in self.avisos_enviados if not a.startswith(f"{usuario_id}_")}
            
            print(f"[PVD] Temporizador cancelado para {usuario_id}")
            return True
        return False

# Instancia global del temporizador
temporizador_pvd = TemporizadorPVD()

# ==============================================
# FUNCIONES PVD
# ==============================================

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Verifica y finaliza automáticamente pausas que han terminado"""
    hubo_cambios = False
    
    for pausa in cola_pvd:
        if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_inicio_madrid = tiempo_inicio.astimezone(TIMEZONE_MADRID) if tiempo_inicio.tzinfo else TIMEZONE_MADRID.localize(tiempo_inicio)
            tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio_madrid).total_seconds() / 60
            
            if tiempo_transcurrido >= duracion_minutos:
                pausa['estado'] = 'COMPLETADO'
                pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                hubo_cambios = True
    
    if hubo_cambios:
        guardar_cola_pvd(cola_pvd)
        iniciar_siguiente_en_cola(cola_pvd, config_pvd)
    
    return hubo_cambios

def iniciar_siguiente_en_cola(cola_pvd, config_pvd):
    """Inicia automáticamente la siguiente pausa en la cola si hay espacio"""
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    if en_pausa < maximo:
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        if en_espera:
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            siguiente = en_espera_ordenados[0]
            
            if siguiente.get('confirmado', False):
                siguiente['estado'] = 'EN_CURSO'
                siguiente['timestamp_inicio'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
                
                temporizador_pvd.cancelar_temporizador(siguiente['usuario_id'])
                
                if config_pvd.get('sonido_activado', True):
                    notificar_inicio_pausa(siguiente, config_pvd)
                
                guardar_cola_pvd(cola_pvd)
                return True
            else:
                siguiente['notificado_en'] = obtener_hora_madrid().isoformat()
                guardar_cola_pvd(cola_pvd)
                print(f"[PVD] Usuario {siguiente['usuario_id']} necesita confirmar antes de empezar")
                return False
    
    return False

def notificar_inicio_pausa(pausa, config_pvd):
    """Envía notificación al usuario cuando su pausa inicia"""
    try:
        duracion_minutos = config_pvd['duracion_corta'] if pausa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
        mensaje = f"¡Tu pausa de {duracion_minutos} minutos ha comenzado! ⏰"
        st.toast(f"🎉 {mensaje}", icon="⏰")
    except Exception as e:
        st.warning(f"Error en notificación: {e}")

def verificar_confirmacion_pvd(usuario_id, cola_pvd, config_pvd):
    """Verifica si el usuario ha confirmado su pausa y la inicia si es necesario"""
    try:
        for pausa in cola_pvd:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
                en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_ordenados and en_espera_ordenados[0]['usuario_id'] == usuario_id:
                    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
                    maximo = config_pvd['maximo_simultaneo']
                    
                    if en_pausa < maximo:
                        tiempo_solicitud = datetime.fromisoformat(pausa['timestamp_solicitud'])
                        tiempo_actual = obtener_hora_madrid()
                        
                        if (tiempo_actual - tiempo_solicitud).total_seconds() > 30:
                            if 'notificado_en' not in pausa:
                                pausa['notificado_en'] = tiempo_actual.isoformat()
                                guardar_cola_pvd(cola_pvd)
                                return True
                break
        
        return False
    except Exception as e:
        print(f"Error verificando confirmación: {e}")
        return False

def actualizar_temporizadores_pvd():
    """Actualiza los temporizadores PVD para usuarios en cola"""
    try:
        config_pvd = cargar_config_pvd()
        cola_pvd = cargar_cola_pvd()
        
        hubo_cambios = verificar_pausas_completadas(cola_pvd, config_pvd)
        
        if 'username' in st.session_state:
            notificacion = temporizador_pvd.verificar_notificaciones_pendientes(st.session_state.username)
            if notificacion:
                hora_notificacion = formatear_hora_madrid(notificacion['timestamp'])
                tipo = notificacion.get('tipo', 'turno')
                
                if tipo == 'turno':
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #00b09b, #96c93d);
                        color: white;
                        padding: 25px;
                        border-radius: 15px;
                        margin: 20px 0;
                        text-align: center;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
                        border: 3px solid #ffffff;
                        animation: pulse 2s infinite;
                    ">
                        <h2 style="margin: 0 0 15px 0; font-size: 28px;">🎉 ¡ES TU TURNO!</h2>
                        <p style="font-size: 20px; margin: 10px 0;">{notificacion['mensaje']}</p>
                        <p style="opacity: 0.9; font-size: 16px;">Hora: {hora_notificacion}</p>
                        <p style="margin-top: 15px; font-size: 14px;">Confirma cuando estés listo para empezar tu pausa</p>
                        
                        <button onclick="window.location.reload();" style="
                            background: white;
                            color: #00b09b;
                            border: none;
                            padding: 12px 30px;
                            border-radius: 8px;
                            font-size: 16px;
                            font-weight: bold;
                            cursor: pointer;
                            margin-top: 20px;
                            transition: transform 0.2s;
                        " onmouseover="this.style.transform='scale(1.05)'" 
                        onmouseout="this.style.transform='scale(1)'">
                            ✅ Confirmar y Empezar Pausa
                        </button>
                    </div>
                    
                    <style>
                    @keyframes pulse {{
                        0% {{ transform: scale(1); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
                        50% {{ transform: scale(1.02); box-shadow: 0 10px 30px rgba(0,176,155,0.4); }}
                        100% {{ transform: scale(1); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }}
                    }}
                    </style>
                    """, unsafe_allow_html=True)
                    
                    with st.container():
                        st.warning("📢 **¡ATENCIÓN! Tu pausa PVD está lista**")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ Confirmar y Empezar Pausa", type="primary", use_container_width=True):
                                for pausa in cola_pvd:
                                    if (pausa['usuario_id'] == st.session_state.username and 
                                        pausa['estado'] == 'ESPERANDO'):
                                        pausa['estado'] = 'EN_CURSO'
                                        pausa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                                        guardar_cola_pvd(cola_pvd)
                                        st.success("✅ Pausa confirmada y comenzada")
                                        st.rerun()
                                        break
                        
                        with col_btn2:
                            if st.button("⏰ Más Tarde", type="secondary", use_container_width=True):
                                for pausa in cola_pvd:
                                    if (pausa['usuario_id'] == st.session_state.username and 
                                        pausa['estado'] == 'ESPERANDO'):
                                        pausa['timestamp_solicitud'] = obtener_hora_madrid().isoformat()
                                        guardar_cola_pvd(cola_pvd)
                                        st.info("⏰ Pausa pospuesta 5 minutos. Se te notificará nuevamente.")
                                        st.rerun()
                                        break
                    
                    st.markdown(f"""
                    <script>
                    setTimeout(function() {{
                        const confirmado = localStorage.getItem('pvd_confirmado_{st.session_state.username}');
                        if (!confirmado) {{
                            window.location.reload();
                        }}
                    }}, 60000);
                    </script>
                    """, unsafe_allow_html=True)
                    
                elif tipo in ['aviso', 'urgente']:
                    st.warning(f"**{notificacion['mensaje']}** ({hora_notificacion})")
        
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        for i, pausa in enumerate(en_espera_ordenados):
            usuario_id = pausa['usuario_id']
            posicion = i + 1
            
            tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, usuario_id)
            
            if tiempo_estimado is not None:
                tiempo_restante_actual = temporizador_pvd.obtener_tiempo_restante(usuario_id)
                
                if tiempo_estimado > 0:
                    if tiempo_restante_actual is None or abs(tiempo_restante_actual - tiempo_estimado) > 2:
                        temporizador_pvd.cancelar_temporizador(usuario_id)
                        temporizador_pvd.iniciar_temporizador_usuario(usuario_id, tiempo_estimado)
                        temporizador_pvd.enviar_aviso_cola(usuario_id, posicion, tiempo_estimado)
                
                elif tiempo_estimado == 0:
                    ultima_notificacion_key = f"{usuario_id}_ultima_notif"
                    ahora = obtener_hora_madrid()
                    
                    if ultima_notificacion_key not in temporizador_pvd.notificaciones_pendientes:
                        temporizador_pvd.notificaciones_pendientes[ultima_notificacion_key] = ahora
                        
                        notificar = True
                        if usuario_id in temporizador_pvd.notificaciones_pendientes:
                            ultima = temporizador_pvd.notificaciones_pendientes.get(usuario_id, {})
                            if isinstance(ultima, dict) and 'timestamp' in ultima:
                                tiempo_ultima = datetime.fromisoformat(ultima['timestamp'])
                                if (ahora - tiempo_ultima).total_seconds() < 30:
                                    notificar = False
                        
                        if notificar:
                            temporizador_pvd.notificaciones_pendientes[usuario_id] = {
                                'timestamp': ahora.isoformat(),
                                'mensaje': '¡Es tu turno para la pausa PVD! Confirma cuando estés listo.',
                                'tipo': 'turno',
                                'hora_madrid': ahora.strftime('%H:%M:%S')
                            }
                    
                    temporizador_pvd.cancelar_temporizador(usuario_id)
        
        usuarios_en_espera = [p['usuario_id'] for p in en_espera]
        for usuario_id in list(temporizador_pvd.temporizadores_activos.keys()):
            if usuario_id not in usuarios_en_espera:
                temporizador_pvd.cancelar_temporizador(usuario_id)
        
        if hubo_cambios:
            guardar_cola_pvd(cola_pvd)
        
        return True
    except Exception as e:
        print(f"Error actualizando temporizadores: {e}")
        return False

def solicitar_pausa(config_pvd, cola_pvd, duracion_elegida):
    """Solicita una pausa PVD para el usuario actual - FUNCIONAMIENTO AUTOMÁTICO"""
    pausas_hoy = len([p for p in cola_pvd 
                     if p['usuario_id'] == st.session_state.username and 
                     datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now(pytz.timezone('Europe/Madrid')).isoformat())).date() == datetime.now(pytz.timezone('Europe/Madrid')).date() and
                     p['estado'] != 'CANCELADO'])
    
    if pausas_hoy >= 5:
        st.warning(f"⚠️ Has alcanzado el límite de 5 pausas diarias")
        return False
    
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            estado_display = ESTADOS_PVD.get(pausa['estado'], pausa['estado'])
            st.warning(f"⚠️ Ya tienes una pausa {estado_display}. Espera a que termine.")
            return False
    
    nueva_pausa = {
        'id': str(uuid.uuid4())[:8],
        'usuario_id': st.session_state.username,
        'usuario_nombre': st.session_state.get('user_config', {}).get('nombre', 'Usuario'),
        'duracion_elegida': duracion_elegida,
        'estado': 'ESPERANDO',
        'timestamp_solicitud': datetime.now(pytz.timezone('Europe/Madrid')).isoformat(),
        'timestamp_inicio': None,
        'timestamp_fin': None,
        'confirmado': False
    }
    
    cola_pvd.append(nueva_pausa)
    guardar_cola_pvd(cola_pvd)
    
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
    
    if en_pausa < maximo:
        st.success(f"✅ Pausa de {duracion_minutos} minutos iniciada inmediatamente")
        nueva_pausa['estado'] = 'EN_CURSO'
        nueva_pausa['timestamp_inicio'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
        
        if config_pvd.get('sonido_activado', True):
            st.toast(f"🎉 ¡Pausa iniciada! {duracion_minutos} minutos", icon="⏰")
    else:
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        en_espera_lista = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        en_espera_ordenados = sorted(en_espera_lista, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        posicion = next((i+1 for i, p in enumerate(en_espera_ordenados) if p['id'] == nueva_pausa['id']), en_espera)
        
        st.info(f"⏳ Pausa solicitada. **Posición en cola: #{posicion}**")
        
        st.info("""
        **🔔 NOTIFICACIÓN DE CONFIRMACIÓN:**
        
        Cuando sea tu turno, recibirás:
        1. **Una alerta en el navegador** pidiendo confirmación
        2. **Debes hacer clic en OK** para empezar tu pausa
        3. **Si haces clic en Cancelar**, seguirás en la cola
        
        ¡Mantén esta pestaña abierta para recibir la notificación!
        """)
        
        tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, st.session_state.username)
        
        if tiempo_estimado and tiempo_estimado > 0:
            temporizador_pvd.iniciar_temporizador_usuario(st.session_state.username, tiempo_estimado)
            
            hora_entrada = (datetime.now(pytz.timezone('Europe/Madrid')) + timedelta(minutes=tiempo_estimado)).strftime('%H:%M')
            
            with st.expander("📋 Información de tu temporizador", expanded=True):
                col_temp1, col_temp2 = st.columns(2)
                with col_temp1:
                    st.metric("⏱️ Tiempo estimado", f"{tiempo_estimado} minutos")
                with col_temp2:
                    st.metric("🕒 Entrada estimada", hora_entrada)
        else:
            st.warning("⚠️ No se pudo calcular el tiempo estimado. Se actualizará en la página principal.")
    
    guardar_cola_pvd(cola_pvd)
    
    if st.button("👁️ Ver mi temporizador PVD", type="primary", use_container_width=True):
        st.rerun()
    
    return True