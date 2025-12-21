import streamlit as st
from datetime import datetime, timedelta
import json
import threading
import time
from utils import obtener_hora_madrid, formatear_hora_madrid
from database import cargar_config_pvd, cargar_cola_pvd, guardar_cola_pvd, cargar_configuracion_usuarios, cargar_config_sistema
import uuid

class TemporizadorPVDMejorado:
    """Clase mejorada para manejar temporizadores PVD con grupos"""
    
    def __init__(self):
        self.temporizadores_activos = {}  # {usuario_id: {tipo: 'pausa'/'cola', inicio: tiempo, duracion: minutos}}
        self.notificaciones_pendientes = {}  # {usuario_id: {timestamp: tiempo, reintentos: 0}}
        self.grupos_activos = {}  # {grupo_id: {usuarios: [], max_simultaneo: X}}
        self.ultima_actualizacion = datetime.now()
        self._iniciar_temporizador_background()
    
    def _iniciar_temporizador_background(self):
        """Inicia el temporizador en segundo plano que se ejecuta cada 60 segundos"""
        def background_task():
            while True:
                try:
                    time.sleep(60)  # Esperar 60 segundos
                    self._verificar_y_actualizar()
                except Exception as e:
                    print(f"Error en temporizador background: {e}")
        
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
    
    def _verificar_y_actualizar(self):
        """Verifica y actualiza estados automáticamente"""
        try:
            # Verificar pausas finalizadas automáticamente
            cola_pvd = cargar_cola_pvd()
            config_pvd = cargar_config_pvd()
            
            if config_pvd.get('auto_finalizar_pausa', True):
                self._finalizar_pausas_completadas(cola_pvd, config_pvd)
            
            # Verificar notificaciones pendientes
            if config_pvd.get('notificacion_automatica', True):
                self._enviar_notificaciones_pendientes(cola_pvd, config_pvd)
            
            # Actualizar grupos
            self._actualizar_grupos()
            
            self.ultima_actualizacion = datetime.now()
            
        except Exception as e:
            print(f"Error en verificación automática: {e}")
    
    def _finalizar_pausas_completadas(self, cola_pvd, config_pvd):
        """Finaliza pausas que han completado su tiempo automáticamente"""
        modificado = False
        
        for pausa in cola_pvd:
            if pausa['estado'] == 'EN_CURSO':
                duracion_elegida = pausa.get('duracion_elegida', 'corta')
                duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                
                tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60
                
                if tiempo_transcurrido >= duracion_minutos:
                    # Finalizar pausa automáticamente
                    pausa['estado'] = 'COMPLETADO'
                    pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                    pausa['finalizado_auto'] = True
                    modificado = True
                    
                    # Iniciar siguiente automáticamente
                    self._iniciar_siguiente_automatico(cola_pvd, config_pvd, pausa.get('grupo'))
        
        if modificado:
            guardar_cola_pvd(cola_pvd)
    
    def _iniciar_siguiente_automatico(self, cola_pvd, config_pvd, grupo=None):
        """Inicia automáticamente al siguiente en la cola después de finalizar una pausa"""
        # Obtener configuración de grupos
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        
        if grupo and grupo in grupos_config:
            max_grupo = grupos_config[grupo].get('maximo_simultaneo', 2)
            en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo])
            
            if en_pausa_grupo < max_grupo:
                # Buscar siguiente en cola del mismo grupo
                en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo]
                en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_grupo:
                    siguiente = en_espera_grupo[0]
                    siguiente['estado'] = 'EN_CURSO'
                    siguiente['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                    siguiente['notificado'] = True
                    siguiente['confirmado'] = True  # Se asume confirmación automática
                    
                    # Programar notificación para este usuario
                    self.programar_notificacion_usuario(siguiente['usuario_id'])
                    
                    guardar_cola_pvd(cola_pvd)
                    return True
        
        # Si no hay grupo o no funciona por grupo, usar sistema general
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        maximo_simultaneo = config_pvd['maximo_simultaneo']
        
        if en_pausa < maximo_simultaneo:
            # Buscar siguiente en cola general
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            if en_espera:
                siguiente = en_espera[0]
                siguiente['estado'] = 'EN_CURSO'
                siguiente['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                siguiente['notificado'] = True
                siguiente['confirmado'] = True
                
                # Programar notificación para este usuario
                self.programar_notificacion_usuario(siguiente['usuario_id'])
                
                guardar_cola_pvd(cola_pvd)
                return True
        
        return False
    
    def _enviar_notificaciones_pendientes(self, cola_pvd, config_pvd):
        """Envía notificaciones a usuarios que están en cola"""
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        
        for pausa in cola_pvd:
            if pausa['estado'] == 'ESPERANDO' and not pausa.get('notificado', False):
                grupo = pausa.get('grupo', 'basico')
                
                # Verificar si es el primero en la cola de su grupo
                en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo]
                en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_grupo and en_espera_grupo[0]['id'] == pausa['id']:
                    # Verificar si hay espacio en pausas para este grupo
                    config_grupo = grupos_config.get(grupo, {'maximo_simultaneo': 2})
                    max_grupo = config_grupo.get('maximo_simultaneo', 2)
                    
                    en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo])
                    
                    if en_pausa_grupo < max_grupo:
                        # Programar notificación
                        self.programar_notificacion_usuario(pausa['usuario_id'])
                        pausa['notificado'] = True
                        pausa['timestamp_notificacion'] = obtener_hora_madrid().isoformat()
                        guardar_cola_pvd(cola_pvd)
    
    def _actualizar_grupos(self):
        """Actualiza la información de grupos activos"""
        usuarios_config = cargar_configuracion_usuarios()
        cola_pvd = cargar_cola_pvd()
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        
        grupos = {}
        
        # Inicializar grupos desde configuración
        for grupo_id in grupos_config.keys():
            grupos[grupo_id] = {
                'usuarios': [],
                'en_pausa': 0,
                'en_espera': 0,
                'completados_hoy': 0
            }
        
        # Contar pausas por grupo
        for pausa in cola_pvd:
            if pausa['estado'] in ['ESPERANDO', 'EN_CURSO', 'COMPLETADO']:
                usuario_id = pausa['usuario_id']
                grupo = usuarios_config.get(usuario_id, {}).get('grupo', 'basico')
                
                if grupo not in grupos:
                    grupos[grupo] = {
                        'usuarios': [],
                        'en_pausa': 0,
                        'en_espera': 0,
                        'completados_hoy': 0
                    }
                
                if usuario_id not in grupos[grupo]['usuarios']:
                    grupos[grupo]['usuarios'].append(usuario_id)
                
                if pausa['estado'] == 'EN_CURSO':
                    grupos[grupo]['en_pausa'] += 1
                elif pausa['estado'] == 'ESPERANDO':
                    grupos[grupo]['en_espera'] += 1
                elif pausa['estado'] == 'COMPLETADO':
                    # Verificar si fue hoy
                    if 'timestamp_fin' in pausa:
                        try:
                            fecha_fin = datetime.fromisoformat(pausa['timestamp_fin']).date()
                            if fecha_fin == obtener_hora_madrid().date():
                                grupos[grupo]['completados_hoy'] += 1
                        except:
                            pass
        
        self.grupos_activos = grupos
    
    def programar_notificacion_usuario(self, usuario_id, tiempo_minutos=1):
        """Programa una notificación para un usuario"""
        self.notificaciones_pendientes[usuario_id] = {
            'timestamp': obtener_hora_madrid(),
            'reintentos': 0,
            'estado': 'pendiente',
            'usuario_id': usuario_id
        }
    
    def obtener_tiempo_restante(self, usuario_id):
        """Obtiene tiempo restante para un usuario"""
        if usuario_id in self.temporizadores_activos:
            temporizador = self.temporizadores_activos[usuario_id]
            tiempo_transcurrido = (obtener_hora_madrid() - temporizador['inicio']).total_seconds() / 60
            tiempo_restante = max(0, temporizador['duracion'] - tiempo_transcurrido)
            return tiempo_restante
        return None
    
    def cancelar_temporizador(self, usuario_id):
        """Cancela el temporizador de un usuario"""
        if usuario_id in self.temporizadores_activos:
            del self.temporizadores_activos[usuario_id]
        if usuario_id in self.notificaciones_pendientes:
            del self.notificaciones_pendientes[usuario_id]
    
    def obtener_estado_grupo(self, grupo_id):
        """Obtiene el estado de un grupo específico"""
        return self.grupos_activos.get(grupo_id, {
            'usuarios': [],
            'en_pausa': 0,
            'en_espera': 0,
            'completados_hoy': 0
        })
    
    def iniciar_temporizador_usuario(self, usuario_id, duracion_minutos):
        """Inicia un temporizador para un usuario"""
        self.temporizadores_activos[usuario_id] = {
            'tipo': 'espera',
            'inicio': obtener_hora_madrid(),
            'duracion': duracion_minutos
        }

# Instancia global del temporizador mejorado
temporizador_pvd_mejorado = TemporizadorPVDMejorado()

# Funciones de compatibilidad (para mantener el código existente)
temporizador_pvd = temporizador_pvd_mejorado

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Verifica y finaliza pausas completadas (compatibilidad)"""
    return temporizador_pvd_mejorado._finalizar_pausas_completadas(cola_pvd, config_pvd)

def iniciar_siguiente_en_cola(cola_pvd, config_pvd):
    """Inicia al siguiente en la cola (compatibilidad)"""
    return temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd)

def solicitar_pausa(config_pvd, cola_pvd, duracion_tipo, grupo=None):
    """Solicita una pausa PVD con soporte para grupos"""
    from database import guardar_cola_pvd
    
    # Obtener grupo del usuario si no se especifica
    if grupo is None:
        usuarios_config = cargar_configuracion_usuarios()
        grupo = usuarios_config.get(st.session_state.username, {}).get('grupo', 'basico')
    
    # Verificar límite diario
    pausas_hoy = len([p for p in cola_pvd 
                     if p['usuario_id'] == st.session_state.username and 
                     'timestamp_solicitud' in p and
                     datetime.fromisoformat(p['timestamp_solicitud']).date() == obtener_hora_madrid().date() and
                     p['estado'] != 'CANCELADO'])
    
    if pausas_hoy >= 5:
        st.error("⚠️ Has alcanzado el límite de 5 pausas diarias")
        return False
    
    # Crear nueva pausa
    nueva_pausa = {
        'id': str(uuid.uuid4())[:8],
        'usuario_id': st.session_state.username,
        'usuario_nombre': st.session_state.user_config.get('nombre', st.session_state.username),
        'duracion_elegida': duracion_tipo,
        'estado': 'ESPERANDO',
        'timestamp_solicitud': obtener_hora_madrid().isoformat(),
        'timestamp_inicio': None,
        'timestamp_fin': None,
        'grupo': grupo,
        'notificado': False,
        'confirmado': False
    }
    
    cola_pvd.append(nueva_pausa)
    guardar_cola_pvd(cola_pvd)
    
    # Calcular tiempo estimado
    tiempo_estimado = calcular_tiempo_estimado_grupo(cola_pvd, config_pvd, grupo, st.session_state.username)
    
    if tiempo_estimado is not None:
        temporizador_pvd_mejorado.iniciar_temporizador_usuario(st.session_state.username, tiempo_estimado)
    
    return True

def calcular_tiempo_estimado_grupo(cola_pvd, config_pvd, grupo, usuario_id):
    """Calcula tiempo estimado considerando grupos"""
    # Obtener configuración del grupo
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo, {'maximo_simultaneo': 2})
    max_grupo = config_grupo.get('maximo_simultaneo', 2)
    
    # Contar pausas activas en el grupo
    en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo])
    
    # Contar espera en el grupo
    en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo]
    en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
    
    # Encontrar posición del usuario
    posicion = None
    for i, pausa in enumerate(en_espera_grupo):
        if pausa['usuario_id'] == usuario_id:
            posicion = i + 1
            break
    
    if posicion is None:
        return None
    
    # Calcular tiempo estimado basado en pausas activas
    tiempo_por_pausa = config_pvd['duracion_corta']  # Usar duración corta como base
    
    if en_pausa_grupo < max_grupo:
        # Hay espacio disponible - podría entrar pronto
        if posicion == 1:
            return 0  # Próximo en entrar
        else:
            # Esperar que terminen las pausas actuales
            return (posicion - 1) * tiempo_por_pausa
    else:
        # Grupo lleno - calcular tiempo basado en pausas restantes
        pausas_antes = max(0, posicion - 1)
        tiempo_estimado = pausas_antes * tiempo_por_pausa
        return max(0, tiempo_estimado)

def verificar_confirmacion_pvd(usuario_id, cola_pvd, config_pvd):
    """Verifica si un usuario necesita confirmar su pausa"""
    for pausa in cola_pvd:
        if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
            # Verificar si es el primero en su grupo y hay espacio
            grupo = pausa.get('grupo', 'basico')
            
            # Obtener configuración del grupo
            config_sistema = cargar_config_sistema()
            grupos_config = config_sistema.get('grupos_pvd', {})
            config_grupo = grupos_config.get(grupo, {'maximo_simultaneo': 2})
            max_grupo = config_grupo.get('maximo_simultaneo', 2)
            
            # Verificar si es primero en su grupo
            en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo]
            en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            if en_espera_grupo and en_espera_grupo[0]['id'] == pausa['id']:
                # Verificar si hay espacio
                en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo])
                
                if en_pausa_grupo < max_grupo:
                    return True
    
    return False

def actualizar_temporizadores_pvd():
    """Función de compatibilidad para actualizar temporizadores"""
    temporizador_pvd_mejorado._verificar_y_actualizar()

# Estados PVD
ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

def crear_temporizador_html(minutos_restantes, usuario_id):
    """Crea un temporizador visual en HTML/JavaScript con notificación de confirmación"""
    
    segundos_totales = minutos_restantes * 60
    
    html_code = f"""
    <div id="temporizador-pvd" style="
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        border: 2px solid #00b4d8;
        position: relative;
        overflow: hidden;
    ">
        <div style="position: absolute; top: 10px; right: 10px; font-size: 12px; opacity: 0.8;">
            🕒 <span id="hora-actual">00:00:00</span>
        </div>
        
        <h3 style="margin: 0 0 15px 0; color: #00b4d8; font-size: 22px;">
            ⏱️ TEMPORIZADOR PVD
        </h3>
        
        <div id="contador" style="
            font-size: 48px;
            font-weight: bold;
            margin: 15px 0;
            color: #4cc9f0;
            text-shadow: 0 0 10px rgba(76, 201, 240, 0.5);
        ">
            {minutos_restantes:02d}:00
        </div>
        
        <div style="
            background: #1f4068;
            height: 20px;
            border-radius: 10px;
            margin: 20px 0;
            overflow: hidden;
        ">
            <div id="barra-progreso" style="
                background: linear-gradient(90deg, #4cc9f0, #4361ee);
                height: 100%;
                width: 0%;
                border-radius: 10px;
                transition: width 1s ease, background 0.5s ease;
            "></div>
        </div>
        
        <div id="mensaje-confirmacion" style="
            display: none;
            background: linear-gradient(135deg, #00b09b, #96c93d);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            font-weight: bold;
            animation: fadeIn 0.5s ease;
        ">
            ✅ Confirmación recibida. Tu pausa comenzará en breve.
        </div>
        
        <div style="
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.9;
        ">
            <div>🆔 {usuario_id[:8]}...</div>
            <div id="tiempo-restante-texto">Restante: {minutos_restantes} min</div>
            <div id="estado-temporizador">⏳ En espera</div>
        </div>
    </div>
    
    <script>
    let segundosRestantes = {segundos_totales};
    const segundosTotales = {segundos_totales};
    let temporizadorActivo = true;
    let notificacionMostrada = false;
    
    function actualizarHora() {{
        const ahora = new Date();
        const hora = ahora.getHours().toString().padStart(2, '0');
        const minutos = ahora.getMinutes().toString().padStart(2, '0');
        const segundos = ahora.getSeconds().toString().padStart(2, '0');
        document.getElementById('hora-actual').textContent = hora + ':' + minutos + ':' + segundos;
    }}
    
    function mostrarNotificacionOverlay() {{
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.id = 'overlay-notificacion-pvd';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.85);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        
        overlay.innerHTML = `
            <div style="
                background: linear-gradient(135deg, #00b09b, #96c93d);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                max-width: 500px;
                width: 90%;
                box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                animation: pulse 1s infinite;
                border: 3px solid white;
            ">
                <h2 style="margin: 0 0 20px 0; font-size: 28px;">🎉 ¡ES TU TURNO!</h2>
                <p style="font-size: 20px; margin: 15px 0; font-weight: bold;">Tu pausa PVD está por comenzar</p>
                <p style="opacity: 0.9; margin-bottom: 25px; font-size: 16px;">Haz clic en OK para confirmar que estás listo</p>
                
                <div style="display: flex; gap: 20px; justify-content: center;">
                    <button id="btn-confirmar-pvd-overlay" style="
                        background: white;
                        color: #00b09b;
                        border: none;
                        padding: 15px 40px;
                        border-radius: 10px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: transform 0.2s;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                    ">
                        ✅ OK - Empezar Pausa
                    </button>
                    
                    <button id="btn-cancelar-pvd-overlay" style="
                        background: #f44336;
                        color: white;
                        border: none;
                        padding: 15px 40px;
                        border-radius: 10px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: transform 0.2s;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                    ">
                        ❌ Cancelar
                    </button>
                </div>
                
                <p style="margin-top: 20px; font-size: 14px; opacity: 0.8;">Esta notificación aparecerá automáticamente</p>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}
        `;
        document.head.appendChild(style);
        
        document.getElementById('btn-confirmar-pvd-overlay').addEventListener('click', function() {{
            document.getElementById('contador').textContent = '✅ CONFIRMADO';
            document.getElementById('contador').style.color = '#00ff00';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #00ff00, #00cc00)';
            
            document.getElementById('mensaje-confirmacion').style.display = 'block';
            
            document.body.removeChild(overlay);
            
            try {{
                const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-correct-answer-tone-2870.mp3');
                audio.volume = 0.3;
                audio.play();
            }} catch(e) {{}}
            
            temporizadorActivo = false;
            
            setTimeout(() => {{
                window.location.reload();
            }}, 5000);
        }});
        
        document.getElementById('btn-cancelar-pvd-overlay').addEventListener('click', function() {{
            document.body.removeChild(overlay);
            
            const mensajeCancel = document.createElement('div');
            mensajeCancel.style.cssText = `
                background: #f44336;
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                text-align: center;
            `;
            mensajeCancel.textContent = '⚠️ Pausa cancelada. Seguirás en la cola.';
            
            const temporizadorDiv = document.getElementById('temporizador-pvd');
            temporizadorDiv.appendChild(mensajeCancel);
            
            setTimeout(() => {{
                window.location.reload();
            }}, 3000);
        }});
        
        return true;
    }}
    
    function actualizarTemporizador() {{
        if (!temporizadorActivo) return;
        
        segundosRestantes--;
        
        if (segundosRestantes <= 0) {{
            document.getElementById('contador').textContent = '🎯 ¡TU TURNO!';
            document.getElementById('contador').style.color = '#ff9900';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
            
            if (!notificacionMostrada) {{
                mostrarNotificacionOverlay();
                notificacionMostrada = true;
            }}
            
            return;
        }}
        
        const minutos = Math.floor(segundosRestantes / 60);
        const segundos = segundosRestantes % 60;
        document.getElementById('contador').textContent = 
            minutos.toString().padStart(2, '0') + ':' + 
            segundos.toString().padStart(2, '0');
        
        const progreso = 100 * (1 - (segundosRestantes / segundosTotales));
        document.getElementById('barra-progreso').style.width = progreso + '%';
        
        if (segundosRestantes <= 300 && segundosRestantes > 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
        }} else if (segundosRestantes <= 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff3300, #cc0000)';
        }}
        
        actualizarHora();
        
        setTimeout(actualizarTemporizador, 1000);
    }}
    
    actualizarHora();
    actualizarTemporizador();
    </script>
    """
    
    return html_code

def enviar_notificacion_browser(mensaje, tipo="info"):
    """Envía una notificación al navegador"""
    try:
        if tipo == "success":
            icon = "✅"
            color = "#00b09b"
        elif tipo == "warning":
            icon = "⚠️"
            color = "#ff9900"
        elif tipo == "error":
            icon = "❌"
            color = "#ff3300"
        else:
            icon = "ℹ️"
            color = "#4cc9f0"
        
        st.markdown(f"""
        <script>
        if (Notification.permission === "granted") {{
            new Notification("{icon} Zelenza PVD", {{
                body: "{mensaje}",
                icon: "https://img.icons8.com/color/96/000000/clock--v1.png"
            }});
        }}
        </script>
        """, unsafe_allow_html=True)
        
        return True
    except Exception as e:
        print(f"Error enviando notificación: {e}")
        return False