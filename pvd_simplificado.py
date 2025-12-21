import streamlit as st
import uuid
from datetime import datetime, timedelta
import pytz
from utils import obtener_hora_madrid, formatear_hora_madrid
from config import ESTADOS_PVD, TIMEZONE_MADRID
from database import cargar_config_pvd, cargar_cola_pvd, guardar_cola_pvd

# ==============================================
# PVD SIMPLIFICADO - SIN SONIDOS, CON NOTIFICACIÓN VISUAL
# ==============================================

class PVDSimplificado:
    """Sistema PVD simplificado con notificación visual grande"""
    
    def __init__(self):
        self.turnos_pendientes = {}
    
    def verificar_turno_usuario(self, usuario_id, cola_pvd, config_pvd):
        """Verifica si es el turno del usuario"""
        try:
            # Buscar pausa del usuario en ESPERANDO
            pausa_usuario = None
            for pausa in cola_pvd:
                if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                    pausa_usuario = pausa
                    break
            
            if not pausa_usuario:
                return False
            
            # Verificar si es el primero en la cola
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            if not en_espera_ordenados or en_espera_ordenados[0]['usuario_id'] != usuario_id:
                return False
            
            # Verificar si hay espacio disponible
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            if en_pausa >= maximo:
                return False
            
            # ¡ES EL TURNO DEL USUARIO!
            return True
            
        except Exception as e:
            print(f"Error verificando turno: {e}")
            return False
    
    def iniciar_pausa_usuario(self, usuario_id, cola_pvd, config_pvd):
        """Inicia la pausa del usuario"""
        try:
            for pausa in cola_pvd:
                if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                    pausa['estado'] = 'EN_CURSO'
                    pausa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                    pausa['confirmado'] = True
                    
                    guardar_cola_pvd(cola_pvd)
                    
                    # Cancelar cualquier turno pendiente
                    if usuario_id in self.turnos_pendientes:
                        del self.turnos_pendientes[usuario_id]
                    
                    st.success(f"✅ Pausa iniciada. Duración: {config_pvd['duracion_corta'] if pausa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']} minutos")
                    return True
            return False
        except Exception as e:
            print(f"Error iniciando pausa: {e}")
            return False
    
    def cancelar_turno_usuario(self, usuario_id, cola_pvd):
        """Cancela el turno del usuario y pasa al siguiente"""
        try:
            for pausa in cola_pvd:
                if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                    # Mover al final de la cola
                    pausa['timestamp_solicitud'] = obtener_hora_madrid().isoformat()
                    pausa['cancelado_en'] = obtener_hora_madrid().isoformat()
                    
                    guardar_cola_pvd(cola_pvd)
                    
                    # Cancelar turno pendiente
                    if usuario_id in self.turnos_pendientes:
                        del self.turnos_pendientes[usuario_id]
                    
                    st.info("⏭️ Turno cancelado. Has sido movido al final de la cola.")
                    return True
            return False
        except Exception as e:
            print(f"Error cancelando turno: {e}")
            return False
    
    def mostrar_notificacion_turno(self, usuario_id, cola_pvd, config_pvd):
        """Muestra la notificación visual grande del turno"""
        if not self.verificar_turno_usuario(usuario_id, cola_pvd, config_pvd):
            return False
        
        # Marcar que ya mostramos la notificación
        if usuario_id in self.turnos_pendientes:
            return True
        
        self.turnos_pendientes[usuario_id] = obtener_hora_madrid()
        
        # Mostrar notificación grande
        st.markdown("""
        <style>
        .turno-notification {
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: white;
            padding: 40px;
            border-radius: 20px;
            margin: 30px 0;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0,0,0,0.3);
            border: 5px solid #ffffff;
            animation: pulse 2s infinite;
            position: relative;
            z-index: 100;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 15px 35px rgba(0,0,0,0.3); }
            50% { transform: scale(1.02); box-shadow: 0 20px 40px rgba(0,176,155,0.5); }
            100% { transform: scale(1); box-shadow: 0 15px 35px rgba(0,0,0,0.3); }
        }
        
        .turno-title {
            font-size: 42px;
            font-weight: bold;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .turno-message {
            font-size: 24px;
            margin-bottom: 30px;
            opacity: 0.95;
        }
        
        .turno-buttons {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
        }
        
        .btn-confirmar {
            background: white;
            color: #00b09b;
            border: none;
            padding: 20px 50px;
            border-radius: 15px;
            font-size: 22px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        
        .btn-confirmar:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 25px rgba(0,0,0,0.3);
        }
        
        .btn-cancelar {
            background: #f44336;
            color: white;
            border: none;
            padding: 20px 50px;
            border-radius: 15px;
            font-size: 22px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        
        .btn-cancelar:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 25px rgba(244,67,54,0.4);
        }
        
        .turno-info {
            margin-top: 25px;
            font-size: 18px;
            opacity: 0.9;
            font-style: italic;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Obtener información de la pausa
        pausa_info = None
        for pausa in cola_pvd:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                pausa_info = pausa
                break
        
        duracion = config_pvd['duracion_corta']
        if pausa_info and pausa_info.get('duracion_elegida') == 'larga':
            duracion = config_pvd['duracion_larga']
        
        # Mostrar la notificación
        st.markdown(f"""
        <div class="turno-notification">
            <div class="turno-title">🎉 ¡ES TU TURNO PARA LA PAUSA PVD!</div>
            <div class="turno-message">Tu pausa de {duracion} minutos está lista para comenzar</div>
            
            <div class="turno-info">
                ⏱️ Duración: {duracion} minutos<br>
                📍 Posición: #1 en la cola<br>
                🕒 Hora: {obtener_hora_madrid().strftime('%H:%M:%S')}
            </div>
            
            <div class="turno-buttons">
                <button class="btn-confirmar" onclick="window.confirmarPausa()">✅ Aceptar y Empezar</button>
                <button class="btn-cancelar" onclick="window.cancelarPausa()">❌ Cancelar (Estoy en llamada)</button>
            </div>
            
            <div class="turno-info">
                Si cancelas, pasarás al final de la cola y se notificará al siguiente agente.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # JavaScript para manejar los botones
        st.markdown("""
        <script>
        // Función para confirmar la pausa
        window.confirmarPausa = function() {
            // Crear un elemento input hidden para simular un botón click
            const confirmBtn = document.createElement('input');
            confirmBtn.type = 'hidden';
            confirmBtn.id = 'confirmar_pausa_js';
            document.body.appendChild(confirmBtn);
            
            // Disparar el evento de Streamlit
            const event = new Event('input', { bubbles: true });
            confirmBtn.dispatchEvent(event);
            
            // Mostrar mensaje
            alert('✅ Pausa confirmada. ¡Que descanses!');
            
            // Recargar la página
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        };
        
        // Función para cancelar la pausa
        window.cancelarPausa = function() {
            // Crear un elemento input hidden para simular un botón click
            const cancelBtn = document.createElement('input');
            cancelBtn.type = 'hidden';
            cancelBtn.id = 'cancelar_pausa_js';
            document.body.appendChild(cancelBtn);
            
            // Disparar el evento de Streamlit
            const event = new Event('input', { bubbles: true });
            cancelBtn.dispatchEvent(event);
            
            // Mostrar mensaje
            alert('⏭️ Turno cancelado. Has sido movido al final de la cola.');
            
            // Recargar la página
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        };
        </script>
        """, unsafe_allow_html=True)
        
        # Botones de Streamlit para manejar la lógica
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirmar y Empezar Pausa", type="primary", use_container_width=True, key="confirmar_pausa_real"):
                if self.iniciar_pausa_usuario(usuario_id, cola_pvd, config_pvd):
                    st.rerun()
        
        with col2:
            if st.button("❌ Cancelar Turno (Estoy en llamada)", type="secondary", use_container_width=True, key="cancelar_pausa_real"):
                if self.cancelar_turno_usuario(usuario_id, cola_pvd):
                    st.rerun()
        
        return True

# Instancia global del PVD simplificado
pvd_simplificado = PVDSimplificado()

# ==============================================
# FUNCIONES DE GESTIÓN PVD SIMPLIFICADO
# ==============================================

def gestion_pvd_usuario_simplificada():
    """Sistema de Pausas Visuales simplificado"""
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    # Botones de acción
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("🔄 Actualizar Estado", use_container_width=True, type="primary"):
            st.rerun()
    with col_btn2:
        if st.button("📊 Ver Estado Cola", use_container_width=True):
            st.rerun()
    with col_btn3:
        if st.button("⏱️ Mi Temporizador", use_container_width=True):
            st.rerun()
    
    hora_actual_madrid = datetime.now(pytz.timezone('Europe/Madrid')).strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora actual (Madrid):** {hora_actual_madrid}")
    
    # 1. PRIMERO: Verificar si es el turno del usuario
    if pvd_simplificado.mostrar_notificacion_turno(st.session_state.username, cola_pvd, config_pvd):
        # Si está mostrando la notificación, no mostrar nada más
        return
    
    # 2. Verificar si el usuario tiene pausa activa o en espera
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.info(f"⏳ **Tienes una pausa solicitada** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            # Calcular posición en cola
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = 1
            for i, pausa in enumerate(en_espera_ordenados):
                if pausa['id'] == usuario_pausa_activa['id']:
                    posicion = i + 1
                    break
            
            # Estadísticas
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            with st.expander("📊 Información de tu pausa", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📍 Posición", f"#{posicion}")
                with col2:
                    st.metric("⏱️ Duración", f"{duracion_minutos} min")
                with col3:
                    st.metric("🎯 Estado", estado_display)
                
                st.write(f"**Tiempo estimado:** Calculando...")
                st.write(f"**Personas en espera:** {len(en_espera)}")
                st.write(f"**Pausas activas:** {en_pausa}/{maximo}")
                
                if posicion == 1:
                    st.success("🎯 **¡Eres el siguiente en la cola!**")
                    st.info("Cuando haya espacio disponible, verás una notificación grande para confirmar.")
                
                # Botón para cancelar
                if st.button("❌ Cancelar mi pausa", type="secondary", use_container_width=True):
                    usuario_pausa_activa['estado'] = 'CANCELADO'
                    guardar_cola_pvd(cola_pvd)
                    
                    if st.session_state.username in pvd_simplificado.turnos_pendientes:
                        del pvd_simplificado.turnos_pendientes[st.session_state.username]
                    
                    st.success("✅ Pausa cancelada")
                    st.rerun()
        
        elif usuario_pausa_activa['estado'] == 'EN_CURSO':
            st.success(f"✅ **Pausa en curso** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(usuario_pausa_activa['timestamp_inicio'])
            
            # Convertir a hora Madrid
            tiempo_inicio_madrid = tiempo_inicio
            if tiempo_inicio.tzinfo:
                tiempo_inicio_madrid = tiempo_inicio.astimezone(pytz.timezone('Europe/Madrid'))
            else:
                tiempo_inicio_madrid = pytz.timezone('Europe/Madrid').localize(tiempo_inicio)
            
            hora_actual_madrid = datetime.now(pytz.timezone('Europe/Madrid'))
            tiempo_transcurrido = int((hora_actual_madrid - tiempo_inicio_madrid).total_seconds() / 60)
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            # Barra de progreso
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            # Información
            col_tiempo1, col_tiempo2 = st.columns(2)
            with col_tiempo1:
                st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
            with col_tiempo2:
                st.metric("⏳ Restante", f"{tiempo_restante} min")
            
            hora_fin_estimada = tiempo_inicio_madrid + timedelta(minutes=duracion_minutos)
            
            st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {tiempo_inicio_madrid.strftime('%H:%M:%S')} (hora Madrid)")
            st.write(f"**Finaliza:** {hora_fin_estimada.strftime('%H:%M:%S')} (hora Madrid)")
            
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada!**")
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
                guardar_cola_pvd(cola_pvd)
                st.rerun()
            
            if st.button("✅ Finalizar pausa ahora", type="primary", use_container_width=True):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
                guardar_cola_pvd(cola_pvd)
                st.success("✅ Pausa completada")
                st.rerun()
    
    else:
        # Usuario no tiene pausa activa
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
            pausas_hoy = len([p for p in cola_pvd 
                            if p['usuario_id'] == st.session_state.username and 
                            datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now(pytz.timezone('Europe/Madrid')).isoformat())).date() == datetime.now(pytz.timezone('Europe/Madrid')).date() and
                            p['estado'] != 'CANCELADO'])
            st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
        
        if pausas_hoy >= 5:
            st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
            st.info("Puedes tomar más pausas mañana")
        else:
            st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
            
            espacios_libres = max(0, maximo - en_pausa)
            
            if espacios_libres > 0:
                st.success(f"✅ **HAY ESPACIO DISPONIBLE** - {espacios_libres} puesto(s) libre(s)")
            else:
                st.warning(f"⏳ **SISTEMA LLENO** - Hay {en_espera} persona(s) en cola")
            
            col_dura1, col_dura2 = st.columns(2)
            with col_dura1:
                duracion_corta = config_pvd['duracion_corta']
                if st.button(
                    f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
                    use_container_width=True,
                    type="primary",
                    key="pausa_corta_simple"
                ):
                    solicitar_pausa_simplificada(config_pvd, cola_pvd, "corta")
                    st.rerun()
            
            with col_dura2:
                duracion_larga = config_pvd['duracion_larga']
                if st.button(
                    f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
                    use_container_width=True,
                    type="secondary",
                    key="pausa_larga_simple"
                ):
                    solicitar_pausa_simplificada(config_pvd, cola_pvd, "larga")
                    st.rerun()

def solicitar_pausa_simplificada(config_pvd, cola_pvd, duracion_elegida):
    """Solicita una pausa PVD simplificada"""
    # Verificar límite diario
    pausas_hoy = len([p for p in cola_pvd 
                     if p['usuario_id'] == st.session_state.username and 
                     datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now(pytz.timezone('Europe/Madrid')).isoformat())).date() == datetime.now(pytz.timezone('Europe/Madrid')).date() and
                     p['estado'] != 'CANCELADO'])
    
    if pausas_hoy >= 5:
        st.warning(f"⚠️ Has alcanzado el límite de 5 pausas diarias")
        return False
    
    # Verificar si ya tiene pausa activa
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            estado_display = ESTADOS_PVD.get(pausa['estado'], pausa['estado'])
            st.warning(f"⚠️ Ya tienes una pausa {estado_display}. Espera a que termine.")
            return False
    
    # Crear nueva pausa
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
    
    # Verificar si puede iniciar inmediatamente
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
    
    if en_pausa < maximo:
        st.success(f"✅ Pausa de {duracion_minutos} minutos iniciada inmediatamente")
        nueva_pausa['estado'] = 'EN_CURSO'
        nueva_pausa['timestamp_inicio'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
        guardar_cola_pvd(cola_pvd)
    else:
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        st.info(f"⏳ Pausa solicitada. **Posición en cola: #{en_espera}**")
        st.info("**Cuando sea tu turno, verás una notificación grande en pantalla para confirmar.**")
    
    return True