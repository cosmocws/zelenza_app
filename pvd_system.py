import streamlit as st
from datetime import datetime, timedelta
import json
import threading
import time
import uuid

from utils import obtener_hora_madrid, formatear_hora_madrid
from database import (
    cargar_config_pvd, 
    cargar_cola_pvd_grupo, 
    guardar_cola_pvd_grupo,
    cargar_configuracion_usuarios, 
    cargar_config_sistema,
    obtener_todas_colas_pvd,
    consolidar_colas_pvd,
    limpiar_todas_colas_antiguas
)

# ==============================================
# CLASE PRINCIPAL TEMPORIZADOR PVD MEJORADO
# ==============================================

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
            # 1. Cargar configuración
            config_pvd = cargar_config_pvd()
            
            # 2. Limpiar pausas bloqueadas en TODOS los grupos
            todas_colas = obtener_todas_colas_pvd()
            limpieza_realizada = False
            
            for grupo_id, cola_grupo in todas_colas.items():
                if self._limpiar_pausas_bloqueadas_grupo(grupo_id, cola_grupo):
                    guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                    limpieza_realizada = True
            
            # 3. Verificar pausas finalizadas automáticamente
            if config_pvd.get('auto_finalizar_pausa', True):
                for grupo_id, cola_grupo in todas_colas.items():
                    if self._finalizar_pausas_completadas_grupo(grupo_id, cola_grupo, config_pvd):
                        guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                        limpieza_realizada = True
            
            # 4. Verificar notificaciones pendientes
            if config_pvd.get('notificacion_automatica', True):
                for grupo_id, cola_grupo in todas_colas.items():
                    if self._enviar_notificaciones_pendientes_grupo(grupo_id, cola_grupo, config_pvd):
                        guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                        limpieza_realizada = True
            
            # 5. Actualizar grupos
            self._actualizar_grupos()
            
            # 6. Limpieza automática de datos antiguos
            if limpieza_realizada:
                limpiar_todas_colas_antiguas()
            
            self.ultima_actualizacion = datetime.now()
            
        except Exception as e:
            print(f"Error en verificación automática: {e}")
    
    def _limpiar_pausas_bloqueadas_grupo(self, grupo_id, cola_grupo):
        """Limpia pausas que están bloqueadas en estado ESPERANDO en un grupo específico"""
        ahora = obtener_hora_madrid()
        modificado = False
        
        for pausa in cola_grupo:
            if pausa['estado'] == 'ESPERANDO':
                # Verificar si lleva mucho tiempo esperando confirmación
                tiempo_solicitud = datetime.fromisoformat(pausa['timestamp_solicitud'])
                tiempo_espera = (ahora - tiempo_solicitud).total_seconds() / 60  # minutos
                
                # Si lleva más de 10 minutos esperando y no ha sido notificado
                if tiempo_espera > 10 and not pausa.get('notificado', False):
                    # Verificar si es el primero en su grupo
                    en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
                    en_espera_grupo = sorted(en_espera_grupo, 
                                            key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                    
                    if en_espera_grupo and en_espera_grupo[0]['id'] == pausa['id']:
                        # Está bloqueado como primero en cola
                        pausa['estado'] = 'CANCELADO'
                        pausa['motivo_cancelacion'] = 'bloqueado_sin_notificar'
                        pausa['timestamp_cancelacion'] = ahora.isoformat()
                        modificado = True
                
                # Si ha sido notificado pero lleva más de 7 minutos esperando confirmación
                elif pausa.get('notificado', False) and 'timestamp_notificacion' in pausa:
                    tiempo_notificacion = datetime.fromisoformat(pausa['timestamp_notificacion'])
                    tiempo_desde_notificacion = (ahora - tiempo_notificacion).total_seconds() / 60
                    
                    if tiempo_desde_notificacion > 7:  # 7 minutos desde notificación
                        pausa['estado'] = 'CANCELADO'
                        pausa['motivo_cancelacion'] = 'confirmacion_expirada'
                        pausa['timestamp_cancelacion'] = ahora.isoformat()
                        modificado = True
                        
                        # Cancelar temporizador si existe
                        self.cancelar_temporizador(pausa['usuario_id'])
        
        return modificado
    
    def _finalizar_pausas_completadas_grupo(self, grupo_id, cola_grupo, config_pvd):
        """Finaliza pausas que han completado su tiempo automáticamente en un grupo"""
        modificado = False
        
        # Obtener configuración del grupo para duraciones
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        config_grupo = grupos_config.get(grupo_id, {
            'duracion_corta': 5,
            'duracion_larga': 10
        })
        
        for pausa in cola_grupo:
            if pausa['estado'] == 'EN_CURSO':
                duracion_elegida = pausa.get('duracion_elegida', 'corta')
                
                # Usar duración del grupo específico
                duracion_minutos = (config_grupo['duracion_corta'] 
                                  if duracion_elegida == 'corta' 
                                  else config_grupo['duracion_larga'])
                
                tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60
                
                if tiempo_transcurrido >= duracion_minutos:
                    # Finalizar pausa automáticamente
                    pausa['estado'] = 'COMPLETADO'
                    pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                    pausa['finalizado_auto'] = True
                    modificado = True
                    
                    # Iniciar siguiente automáticamente en este grupo
                    self._iniciar_siguiente_automatico_grupo(grupo_id)
        
        return modificado
    
    def _iniciar_siguiente_automatico_grupo(self, grupo_id):
        """Marca como disponible al siguiente en la cola del grupo específico"""
        try:
            cola_grupo = cargar_cola_pvd_grupo(grupo_id)
            
            # Obtener configuración del grupo
            config_sistema = cargar_config_sistema()
            grupos_config = config_sistema.get('grupos_pvd', {})
            config_grupo = grupos_config.get(grupo_id, {'maximo_simultaneo': 2})
            max_grupo = config_grupo.get('maximo_simultaneo', 2)
            
            # Contar pausas activas en este grupo
            en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            
            if en_pausa_grupo < max_grupo:
                # Buscar siguiente en cola del mismo grupo
                en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
                en_espera_grupo = sorted(en_espera_grupo, 
                                        key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_grupo:
                    siguiente = en_espera_grupo[0]
                    # Marcar como listo para ser notificado
                    siguiente['notificado'] = False
                    siguiente['listo_para_confirmar'] = True
                    siguiente['timestamp_disponible'] = obtener_hora_madrid().isoformat()
                    
                    guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error iniciando siguiente automático en grupo {grupo_id}: {e}")
            return False
    
    def _enviar_notificaciones_pendientes_grupo(self, grupo_id, cola_grupo, config_pvd):
        """Envía notificaciones a usuarios que están en cola en un grupo específico"""
        modificado = False
        config_sistema = cargar_config_sistema()
        grupos_config = config_sistema.get('grupos_pvd', {})
        
        # Obtener configuración del grupo
        config_grupo = grupos_config.get(grupo_id, {'maximo_simultaneo': 2})
        max_grupo = config_grupo.get('maximo_simultaneo', 2)
        
        # Contar pausas activas en este grupo
        en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
        
        for pausa in cola_grupo:
            if pausa['estado'] == 'ESPERANDO' and not pausa.get('notificado', False):
                # Verificar si es el primero en la cola de su grupo
                en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
                en_espera_grupo = sorted(en_espera_grupo, 
                                        key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_grupo and en_espera_grupo[0]['id'] == pausa['id']:
                    # Verificar si hay espacio en pausas para este grupo
                    if en_pausa_grupo < max_grupo:
                        # Programar notificación
                        self.programar_notificacion_usuario(pausa['usuario_id'])
                        pausa['notificado'] = True
                        pausa['timestamp_notificacion'] = obtener_hora_madrid().isoformat()
                        pausa['notificar_sidebar'] = True
                        modificado = True
        
        return modificado
    
    def _actualizar_grupos(self):
        """Actualiza la información de grupos activos"""
        try:
            todas_colas = obtener_todas_colas_pvd()
            config_sistema = cargar_config_sistema()
            grupos_config = config_sistema.get('grupos_pvd', {})
            
            grupos = {}
            hoy = obtener_hora_madrid().date()
            
            # Inicializar grupos desde configuración
            for grupo_id in grupos_config.keys():
                grupos[grupo_id] = {
                    'usuarios': [],
                    'en_pausa': 0,
                    'en_espera': 0,
                    'completados_hoy': 0,
                    'max_simultaneo': grupos_config[grupo_id].get('maximo_simultaneo', 2)
                }
            
            # Contar pausas por grupo
            for grupo_id, cola_grupo in todas_colas.items():
                if grupo_id not in grupos:
                    grupos[grupo_id] = {
                        'usuarios': [],
                        'en_pausa': 0,
                        'en_espera': 0,
                        'completados_hoy': 0,
                        'max_simultaneo': 2
                    }
                
                for pausa in cola_grupo:
                    usuario_id = pausa['usuario_id']
                    
                    if usuario_id not in grupos[grupo_id]['usuarios']:
                        grupos[grupo_id]['usuarios'].append(usuario_id)
                    
                    if pausa['estado'] == 'EN_CURSO':
                        grupos[grupo_id]['en_pausa'] += 1
                    elif pausa['estado'] == 'ESPERANDO':
                        grupos[grupo_id]['en_espera'] += 1
                    elif pausa['estado'] == 'COMPLETADO':
                        # Verificar si fue hoy
                        if 'timestamp_fin' in pausa:
                            try:
                                fecha_fin = datetime.fromisoformat(pausa['timestamp_fin']).date()
                                if fecha_fin == hoy:
                                    grupos[grupo_id]['completados_hoy'] += 1
                            except:
                                pass
            
            self.grupos_activos = grupos
            
        except Exception as e:
            print(f"Error actualizando grupos: {e}")
    
    # ==============================================
    # MÉTODOS PÚBLICOS
    # ==============================================
    
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
            'completados_hoy': 0,
            'max_simultaneo': 2
        })
    
    def iniciar_temporizador_usuario(self, usuario_id, duracion_minutos):
        """Inicia un temporizador para un usuario"""
        self.temporizadores_activos[usuario_id] = {
            'tipo': 'espera',
            'inicio': obtener_hora_madrid(),
            'duracion': duracion_minutos
        }
    
    def solicitar_pausa(self, duracion_tipo, grupo=None):
        """Solicita una pausa PVD para el usuario actual"""
        try:
            if not st.session_state.get('authenticated', False):
                return False
            
            # Obtener usuario actual
            usuario_id = st.session_state.username
            
            # Obtener grupo del usuario si no se especifica
            if grupo is None:
                usuarios_config = cargar_configuracion_usuarios()
                grupo = usuarios_config.get(usuario_id, {}).get('grupo', 'basico')
            
            # Cargar cola del grupo específico
            cola_grupo = cargar_cola_pvd_grupo(grupo)
            
            # Verificar límite diario (máximo 5 pausas)
            hoy = obtener_hora_madrid().date()
            pausas_hoy = len([p for p in cola_grupo 
                            if p['usuario_id'] == usuario_id and 
                            'timestamp_solicitud' in p and
                            datetime.fromisoformat(p['timestamp_solicitud']).date() == hoy and
                            p['estado'] != 'CANCELADO'])
            
            if pausas_hoy >= 5:
                st.error("⚠️ Has alcanzado el límite de 5 pausas diarias")
                return False
            
            # Obtener nombre del usuario
            usuarios_config = cargar_configuracion_usuarios()
            usuario_nombre = usuarios_config.get(usuario_id, {}).get('nombre', usuario_id)
            
            # Crear nueva pausa
            nueva_pausa = {
                'id': str(uuid.uuid4())[:8],
                'usuario_id': usuario_id,
                'usuario_nombre': usuario_nombre,
                'duracion_elegida': duracion_tipo,
                'estado': 'ESPERANDO',
                'timestamp_solicitud': obtener_hora_madrid().isoformat(),
                'timestamp_inicio': None,
                'timestamp_fin': None,
                'grupo': grupo,
                'notificado': False,
                'confirmado': False
            }
            
            cola_grupo.append(nueva_pausa)
            guardar_cola_pvd_grupo(grupo, cola_grupo)
            
            # Calcular tiempo estimado
            tiempo_estimado = self.calcular_tiempo_estimado_grupo(grupo, usuario_id)
            
            if tiempo_estimado is not None:
                self.iniciar_temporizador_usuario(usuario_id, tiempo_estimado)
            
            return True
            
        except Exception as e:
            print(f"Error solicitando pausa: {e}")
            return False
    
    def calcular_tiempo_estimado_grupo(self, grupo_id, usuario_id):
        """Calcula tiempo estimado considerando grupos"""
        try:
            cola_grupo = cargar_cola_pvd_grupo(grupo_id)
            
            if not cola_grupo:
                return 0
            
            # Obtener configuración del grupo
            config_sistema = cargar_config_sistema()
            grupos_config = config_sistema.get('grupos_pvd', {})
            config_grupo = grupos_config.get(grupo_id, {
                'maximo_simultaneo': 2,
                'duracion_corta': 5,
                'duracion_larga': 10
            })
            max_grupo = config_grupo.get('maximo_simultaneo', 2)
            
            # Contar pausas activas en el grupo
            en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            
            # Contar espera en el grupo
            en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
            en_espera_grupo = sorted(en_espera_grupo, 
                                    key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            # Encontrar posición del usuario
            posicion = None
            for i, pausa in enumerate(en_espera_grupo):
                if pausa['usuario_id'] == usuario_id:
                    posicion = i + 1
                    break
            
            if posicion is None:
                return None
            
            # Usar duración corta como base para estimación
            tiempo_base = config_grupo.get('duracion_corta', 5)
            
            if en_pausa_grupo < max_grupo:
                # Hay espacio disponible
                if posicion == 1:
                    return 0  # Próximo en entrar
                else:
                    # Esperar que terminen las pausas actuales
                    return (posicion - 1) * tiempo_base
            else:
                # Grupo lleno - calcular tiempo basado en pausas restantes
                pausas_antes = max(0, posicion - 1)
                tiempo_estimado = pausas_antes * tiempo_base
                return max(0, tiempo_estimado)
                
        except Exception as e:
            print(f"Error calculando tiempo estimado para grupo {grupo_id}: {e}")
            return 5  # Valor por defecto seguro

# Instancia global del temporizador mejorado
temporizador_pvd_mejorado = TemporizadorPVDMejorado()

# ==============================================
# FUNCIONES DE COMPATIBILIDAD
# ==============================================

# Alias para compatibilidad con código existente
temporizador_pvd = temporizador_pvd_mejorado

def solicitar_pausa(config_pvd, cola_pvd, duracion_tipo, grupo=None):
    """Función de compatibilidad para solicitar pausa"""
    return temporizador_pvd_mejorado.solicitar_pausa(duracion_tipo, grupo)

def calcular_tiempo_estimado_grupo(cola_pvd, config_pvd, grupo, usuario_id):
    """Función de compatibilidad para calcular tiempo estimado"""
    return temporizador_pvd_mejorado.calcular_tiempo_estimado_grupo(grupo, usuario_id)

def verificar_confirmacion_pvd(usuario_id, cola_pvd, config_pvd):
    """Función de compatibilidad para verificar confirmación"""
    try:
        # Obtener grupo del usuario
        usuarios_config = cargar_configuracion_usuarios()
        grupo = usuarios_config.get(usuario_id, {}).get('grupo', 'basico')
        
        # Cargar cola del grupo
        cola_grupo = cargar_cola_pvd_grupo(grupo)
        
        for pausa in cola_grupo:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                # Verificar si es el primero en su grupo
                en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
                en_espera_grupo = sorted(en_espera_grupo, 
                                        key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                if en_espera_grupo and en_espera_grupo[0]['id'] == pausa['id']:
                    # Verificar si hay espacio en el grupo
                    config_sistema = cargar_config_sistema()
                    grupos_config = config_sistema.get('grupos_pvd', {})
                    config_grupo = grupos_config.get(grupo, {'maximo_simultaneo': 2})
                    max_grupo = config_grupo.get('maximo_simultaneo', 2)
                    
                    en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
                    
                    if en_pausa_grupo < max_grupo:
                        return True
        
        return False
        
    except Exception as e:
        print(f"Error verificando confirmación PVD: {e}")
        return False

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Función de compatibilidad para verificar pausas completadas"""
    # Esta función ahora maneja todas las colas
    todas_colas = obtener_todas_colas_pvd()
    modificado = False
    
    for grupo_id, cola_grupo in todas_colas.items():
        if temporizador_pvd_mejorado._finalizar_pausas_completadas_grupo(grupo_id, cola_grupo, config_pvd):
            guardar_cola_pvd_grupo(grupo_id, cola_grupo)
            modificado = True
    
    return modificado

def iniciar_siguiente_en_cola(cola_pvd, config_pvd):
    """Función de compatibilidad para iniciar siguiente en cola"""
    # Esta función ahora maneja la cola consolidada
    cola_consolidada = consolidar_colas_pvd()
    grupos = set(p.get('grupo', 'basico') for p in cola_consolidada)
    
    for grupo in grupos:
        temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo)
    
    return True

def actualizar_temporizadores_pvd():
    """Función de compatibilidad para actualizar temporizadores"""
    temporizador_pvd_mejorado._verificar_y_actualizar()

# ==============================================
# FUNCIONES DE VISUALIZACIÓN
# ==============================================

# Estados PVD
ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

def crear_temporizador_html_simplificado(minutos_restantes, usuario_id):
    """Crea un temporizador visual en HTML/JavaScript SIN notificaciones del navegador"""
    
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
    
    function actualizarHora() {{
        const ahora = new Date();
        const hora = ahora.getHours().toString().padStart(2, '0');
        const minutos = ahora.getMinutes().toString().padStart(2, '0');
        const segundos = ahora.getSeconds().toString().padStart(2, '0');
        document.getElementById('hora-actual').textContent = hora + ':' + minutos + ':' + segundos;
    }}
    
    function actualizarTemporizador() {{
        if (!temporizadorActivo) return;
        
        segundosRestantes--;
        
        if (segundosRestantes <= 0) {{
            document.getElementById('contador').textContent = '🎯 ¡TU TURNO!';
            document.getElementById('contador').style.color = '#ff9900';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
            
            // Mostrar mensaje para recargar la página
            document.getElementById('estado-temporizador').textContent = '🎯 ¡TURNO!';
            document.getElementById('estado-temporizador').style.color = '#ff9900';
            document.getElementById('estado-temporizador').style.fontWeight = 'bold';
            
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