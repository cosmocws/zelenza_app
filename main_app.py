import streamlit as st
import pandas as pd
import os
import shutil
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
import base64
import io
import asyncio  # Añadido para manejo asíncrono

# ==============================================
# CONFIGURACIONES Y CONSTANTES
# ==============================================

COMUNIDADES_AUTONOMAS = [
    "Toda España",
    "Andalucía",
    "Aragón",
    "Asturias",
    "Baleares",
    "Canarias",
    "Cantabria",
    "Castilla-La Mancha",
    "Castilla y León",
    "Cataluña",
    "Comunidad Valenciana",
    "Extremadura",
    "Galicia",
    "Madrid",
    "Murcia",
    "Navarra",
    "País Vasco",
    "La Rioja",
    "Ceuta",
    "Melilla"
]

PLANES_GAS_ESTRUCTURA = {
    "RL1": {
        "precio_original_kwh": 0.045,
        "termino_variable_con_pmg": 0.038,
        "termino_variable_sin_pmg": 0.042,
        "termino_fijo_con_pmg": 8.5,
        "termino_fijo_sin_pmg": 9.2,
        "rango": "0-5000 kWh anuales",
        "activo": True
    },
    "RL2": {
        "precio_original_kwh": 0.043,
        "termino_variable_con_pmg": 0.036,
        "termino_variable_sin_pmg": 0.040,
        "termino_fijo_con_pmg": 12.0,
        "termino_fijo_sin_pmg": 13.0,
        "rango": "5000-15000 kWh anuales",
        "activo": True
    },
    "RL3": {
        "precio_original_kwh": 0.041,
        "termino_variable_con_pmg": 0.034,
        "termino_variable_sin_pmg": 0.038,
        "termino_fijo_con_pmg": 18.0,
        "termino_fijo_sin_pmg": 19.5,
        "rango": "15000-50000 kWh anuales",
        "activo": True
    }
}

PMG_COSTE = 9.95
PMG_IVA = 0.21

USUARIOS_DEFAULT = {
    "user": {
        "nombre": "Usuario Estándar",
        "password": "cliente123",
        "planes_luz": [],
        "planes_gas": ["RL1", "RL2", "RL3"],
        "tipo": "user"
    },
    "admin": {
        "nombre": "Administrador",
        "password": "admin123", 
        "planes_luz": "TODOS",
        "planes_gas": "TODOS",
        "tipo": "admin"
    }
}

PVD_CONFIG_DEFAULT = {
    "agentes_activos": 25,
    "maximo_simultaneo": 3,
    "duracion_corta": 5,
    "duracion_larga": 10,
    "sonido_activado": True
}

SISTEMA_CONFIG_DEFAULT = {
    "login_automatico_activado": True,
    "sesion_horas_duracion": 8,
    "grupos_usuarios": {
        "basico": {"planes_luz": ["PLAN_BASICO"], "planes_gas": ["RL1"]},
        "premium": {"planes_luz": ["TODOS"], "planes_gas": ["RL1", "RL2", "RL3"]},
        "empresa": {"planes_luz": ["PLAN_EMPRESA"], "planes_gas": ["RL2", "RL3"]}
    }
}

ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

# ==============================================
# NUEVO: SISTEMA DE TEMPORIZADOR PVD
# ==============================================

class TemporizadorPVD:
    """Clase para manejar temporizadores de cuenta atrás en PVD"""
    
    def __init__(self):
        self.temporizadores_activos = {}
        self.notificaciones_pendientes = {}
    
    def calcular_tiempo_estimado_entrada(self, cola_pvd, config_pvd, usuario_id):
        """Calcula el tiempo estimado para que un usuario entre en PVD"""
        try:
            # Filtrar usuarios en espera ordenados por tiempo de solicitud
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            # Encontrar posición del usuario
            posicion_usuario = None
            for i, pausa in enumerate(en_espera_ordenados):
                if pausa['usuario_id'] == usuario_id:
                    posicion_usuario = i + 1
                    break
            
            if posicion_usuario is None:
                return None
            
            # Calcular tiempo estimado basado en pausas en curso
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            # Si hay espacio disponible y es el primero en cola
            if posicion_usuario == 1 and en_pausa < maximo:
                return 0  # Entra inmediatamente
            
            # Calcular tiempo estimado
            tiempo_estimado_minutos = 0
            
            # Sumar tiempo de pausas actuales que faltan por terminar
            pausas_en_curso = [p for p in cola_pvd if p['estado'] == 'EN_CURSO']
            for pausa in pausas_en_curso:
                if 'timestamp_inicio' in pausa:
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    tiempo_estimado_minutos += tiempo_restante
            
            # Sumar tiempo de personas antes en la cola
            personas_antes = posicion_usuario - 1
            for i in range(personas_antes):
                if i < len(en_espera_ordenados):
                    duracion_elegida = en_espera_ordenados[i].get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    tiempo_estimado_minutos += duracion_minutos
            
            return tiempo_estimado_minutos
            
        except Exception as e:
            print(f"Error calculando tiempo estimado: {e}")
            return None
    
    def iniciar_temporizador_usuario(self, usuario_id, tiempo_minutos):
        """Inicia un temporizador para un usuario específico"""
        try:
            tiempo_fin = datetime.now() + timedelta(minutes=tiempo_minutos)
            self.temporizadores_activos[usuario_id] = {
                'tiempo_inicio': datetime.now(),
                'tiempo_fin': tiempo_fin,
                'tiempo_total_minutos': tiempo_minutos,
                'activo': True
            }
            
            # Programar notificación automática
            self.programar_notificacion(usuario_id, tiempo_minutos)
            
            return True
        except Exception as e:
            print(f"Error iniciando temporizador: {e}")
            return False
    
    def programar_notificacion(self, usuario_id, tiempo_minutos):
        """Programa una notificación para cuando el temporizador llegue a 0"""
        try:
            # Usar threading para la notificación automática
            def notificar_cuando_termine():
                time.sleep(tiempo_minutos * 60)  # Convertir minutos a segundos
                
                # Verificar si el temporizador sigue activo
                if usuario_id in self.temporizadores_activos:
                    if self.temporizadores_activos[usuario_id]['activo']:
                        # Marcar como notificación pendiente
                        self.notificaciones_pendientes[usuario_id] = {
                            'timestamp': datetime.now(),
                            'mensaje': '¡Es tu turno para la pausa PVD!'
                        }
                        
                        # Eliminar temporizador
                        del self.temporizadores_activos[usuario_id]
            
            # Iniciar el thread
            thread = threading.Thread(target=notificar_cuando_termine, daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            print(f"Error programando notificación: {e}")
            return False
    
    def obtener_tiempo_restante(self, usuario_id):
        """Obtiene el tiempo restante para un usuario"""
        if usuario_id not in self.temporizadores_activos:
            return None
        
        temporizador = self.temporizadores_activos[usuario_id]
        
        if not temporizador['activo']:
            return None
        
        tiempo_restante = temporizador['tiempo_fin'] - datetime.now()
        
        if tiempo_restante.total_seconds() <= 0:
            # Tiempo completado
            temporizador['activo'] = False
            return 0
        
        return max(0, int(tiempo_restante.total_seconds() // 60))  # Minutos restantes
    
    def verificar_notificaciones_pendientes(self, usuario_id):
        """Verifica si hay notificaciones pendientes para un usuario"""
        if usuario_id in self.notificaciones_pendientes:
            notificacion = self.notificaciones_pendientes.pop(usuario_id)
            return notificacion
        return None
    
    def cancelar_temporizador(self, usuario_id):
        """Cancela el temporizador de un usuario"""
        if usuario_id in self.temporizadores_activos:
            self.temporizadores_activos[usuario_id]['activo'] = False
            del self.temporizadores_activos[usuario_id]
            return True
        return False

# Instancia global del temporizador
temporizador_pvd = TemporizadorPVD()

# ==============================================
# FUNCIONES DE INICIALIZACIÓN Y BACKUP
# ==============================================

def inicializar_datos():
    """Inicializa los archivos de datos con backup automático"""
    try:
        os.makedirs("data", exist_ok=True)
        os.makedirs("data_backup", exist_ok=True)  # Crear antes de usar
        os.makedirs("modelos_facturas", exist_ok=True)
        
        archivos_criticos = {
            "precios_luz.csv": pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
                'comunidades_autonomas'
            ]),
            "config_excedentes.csv": pd.DataFrame([{'precio_excedente_kwh': 0.06}]),
            "planes_gas.json": json.dumps(PLANES_GAS_ESTRUCTURA, indent=4),
            "config_pmg.json": json.dumps({"coste": PMG_COSTE, "iva": PMG_IVA}, indent=4),
            "usuarios.json": json.dumps(USUARIOS_DEFAULT, indent=4),
            "config_pvd.json": json.dumps(PVD_CONFIG_DEFAULT, indent=4),
            "cola_pvd.json": json.dumps([], indent=4),
            "config_sistema.json": json.dumps(SISTEMA_CONFIG_DEFAULT, indent=4)
        }
        
        for archivo, df_default in archivos_criticos.items():
            ruta_data = f"data/{archivo}"
            ruta_backup = f"data_backup/{archivo}"
            
            # Verificar si existe el archivo de datos
            if not os.path.exists(ruta_data):
                # Intentar restaurar desde backup
                if os.path.exists(ruta_backup):
                    try:
                        shutil.copy(ruta_backup, ruta_data)
                        st.sidebar.success(f"✅ {archivo} restaurado desde backup")
                    except Exception as e:
                        st.sidebar.warning(f"⚠️ Error restaurando {archivo}: {e}")
                else:
                    # Crear archivo nuevo con datos por defecto
                    try:
                        if archivo.endswith('.json'):
                            with open(ruta_data, 'w', encoding='utf-8') as f:
                                f.write(df_default)
                        else:
                            df_default.to_csv(ruta_data, index=False, encoding='utf-8')
                    except Exception as e:
                        st.sidebar.error(f"❌ Error creando {archivo}: {e}")
            
            # Crear backup del archivo actual
            try:
                if os.path.exists(ruta_data):
                    shutil.copy(ruta_data, ruta_backup)
            except Exception as e:
                st.sidebar.warning(f"⚠️ Error creando backup de {archivo}: {e}")
        
        # Backup de modelos de factura
        if os.path.exists("modelos_facturas") and os.listdir("modelos_facturas"):
            backup_folder = "data_backup/modelos_facturas"
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
            shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
    except Exception as e:
        st.error(f"❌ Error crítico en inicialización: {e}")

# ==============================================
# FUNCIONES DE AUTENTICACIÓN Y SESIÓN
# ==============================================

def authenticate(username, password, user_type):
    """Autentica al usuario de forma segura"""
    try:
        # Verificar credenciales básicas
        if not username or not password:
            return False
        
        usuarios_config = cargar_configuracion_usuarios()
        
        if user_type == "user":
            if username in usuarios_config:
                usuario = usuarios_config[username]
                # Verificar contraseña almacenada
                if "password" in usuario:
                    # Comparación segura de contraseñas
                    return password == usuario["password"]
                else:
                    # Fallback a contraseña por defecto
                    try:
                        return password == st.secrets.get("credentials", {}).get("user_password", "cliente123")
                    except:
                        return password == "cliente123"
            else:
                # Usuario por defecto
                try:
                    return (username == st.secrets.get("credentials", {}).get("user_username", "usuario") and 
                            password == st.secrets.get("credentials", {}).get("user_password", "cliente123"))
                except:
                    return username == "usuario" and password == "cliente123"
                    
        elif user_type == "admin":
            try:
                return (username == st.secrets.get("credentials", {}).get("admin_username", "admin") and 
                        password == st.secrets.get("credentials", {}).get("admin_password", "admin123"))
            except:
                return username == "admin" and password == "admin123"
                
        return False
    except Exception as e:
        st.error(f"Error en autenticación: {e}")
        return False

def cargar_configuracion_usuarios():
    """Carga la configuración de usuarios desde archivo"""
    try:
        with open('data/usuarios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        os.makedirs('data', exist_ok=True)
        with open('data/usuarios.json', 'w', encoding='utf-8') as f:
            json.dump(USUARIOS_DEFAULT, f, indent=4, ensure_ascii=False)
        return USUARIOS_DEFAULT.copy()

def guardar_configuracion_usuarios(usuarios_config):
    """Guarda la configuración de usuarios de forma segura"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/usuarios.json', 'w', encoding='utf-8') as f:
            json.dump(usuarios_config, f, indent=4, ensure_ascii=False)
        
        # Backup
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/usuarios.json', 'data_backup/usuarios.json')
        return True
    except Exception as e:
        st.error(f"Error guardando usuarios: {e}")
        return False

def cargar_config_sistema():
    """Carga la configuración del sistema"""
    try:
        with open('data/config_sistema.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        os.makedirs('data', exist_ok=True)
        with open('data/config_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(SISTEMA_CONFIG_DEFAULT, f, indent=4, ensure_ascii=False)
        return SISTEMA_CONFIG_DEFAULT.copy()

def guardar_config_sistema(config):
    """Guarda la configuración del sistema"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/config_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando configuración: {e}")
        return False

def verificar_sesion():
    """Verifica si la sesión es válida"""
    if not st.session_state.get('authenticated', False):
        return False
    
    if 'login_time' not in st.session_state:
        st.session_state.login_time = datetime.now()
        return True
    
    config_sistema = cargar_config_sistema()
    horas_duracion = config_sistema.get("sesion_horas_duracion", 8)
    
    horas_transcurridas = (datetime.now() - st.session_state.login_time).total_seconds() / 3600
    
    if horas_transcurridas >= horas_duracion:
        st.warning("⏰ Tu sesión ha expirado. Por favor, vuelve a iniciar sesión.")
        
        # Limpiar sesión
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None
        st.session_state.user_config = {}
        
        # Cancelar temporizador si existe
        if 'username' in st.session_state:
            temporizador_pvd.cancelar_temporizador(st.session_state.username)
        
        st.rerun()
        return False
    
    # Mostrar tiempo restante
    tiempo_restante = horas_duracion - horas_transcurridas
    horas = int(tiempo_restante)
    minutos = int((tiempo_restante - horas) * 60)
    
    st.sidebar.info(f"⏳ Sesión: {horas}h {minutos}m restantes")
    
    return True

# ==============================================
# FUNCIONES DE USUARIOS Y PERMISOS
# ==============================================

def generar_id_unico_usuario():
    """Genera un ID único para el dispositivo del usuario"""
    if 'device_id' not in st.session_state:
        device_id = f"dev_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        st.session_state.device_id = device_id
    return st.session_state.device_id

def identificar_usuario_automatico():
    """Identifica automáticamente al usuario por su dispositivo"""
    device_id = generar_id_unico_usuario()
    usuarios_config = cargar_configuracion_usuarios()
    
    # Buscar usuario por device_id
    for username, config in usuarios_config.items():
        if config.get('device_id') == device_id:
            return username, config
    
    # Crear nuevo usuario automático
    nuevo_username = f"auto_{device_id[:8]}"
    
    if nuevo_username not in usuarios_config:
        usuarios_config[nuevo_username] = {
            "nombre": f"Usuario {device_id[:8]}",
            "device_id": device_id,
            "planes_luz": [],
            "planes_gas": ["RL1", "RL2", "RL3"],
            "tipo": "auto",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "password": "auto_login"
        }
        guardar_configuracion_usuarios(usuarios_config)
    
    return nuevo_username, usuarios_config[nuevo_username]

def filtrar_planes_por_usuario(df_planes, username, tipo_plan="luz"):
    """Filtra los planes según la configuración del usuario"""
    if df_planes.empty:
        return df_planes
    
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    if username not in usuarios_config:
        return df_planes[df_planes['activo'] == True]
    
    config_usuario = usuarios_config[username]
    grupo_usuario = config_usuario.get('grupo')
    
    # Determinar planes permitidos
    if not grupo_usuario or grupo_usuario not in grupos:
        planes_permitidos = config_usuario.get(f"planes_{tipo_plan}", [])
    else:
        permisos_grupo = grupos[grupo_usuario]
        planes_permitidos = permisos_grupo.get(f"planes_{tipo_plan}", [])
    
    if not planes_permitidos:
        return df_planes[df_planes['activo'] == True]
    
    if planes_permitidos == "TODOS":
        return df_planes[df_planes['activo'] == True]
    
    return df_planes[
        (df_planes['plan'].isin(planes_permitidos)) & 
        (df_planes['activo'] == True)
    ]

# ==============================================
# FUNCIONES DE PVD (CON TEMPORIZADOR AÑADIDO)
# ==============================================

def cargar_config_pvd():
    """Carga la configuración del sistema PVD"""
    try:
        with open('data/config_pvd.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Migración de versiones antiguas
        if 'duracion_pvd' in config and 'duracion_corta' not in config:
            duracion_antigua = config['duracion_pvd']
            config['duracion_corta'] = duracion_antigua
            config['duracion_larga'] = duracion_antigua * 2
            guardar_config_pvd(config)
        
        # Verificar campos requeridos
        campos_requeridos = ['agentes_activos', 'maximo_simultaneo', 'duracion_corta', 'duracion_larga', 'sonido_activado']
        for campo in campos_requeridos:
            if campo not in config:
                config[campo] = PVD_CONFIG_DEFAULT[campo]
        
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        return PVD_CONFIG_DEFAULT.copy()

def guardar_config_pvd(config):
    """Guarda la configuración PVD"""
    try:
        for campo, valor in PVD_CONFIG_DEFAULT.items():
            if campo not in config:
                config[campo] = valor
        
        os.makedirs('data', exist_ok=True)
        with open('data/config_pvd.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        # Backup
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/config_pvd.json', 'data_backup/config_pvd.json')
        return True
    except Exception as e:
        st.error(f"Error guardando configuración PVD: {e}")
        return False

def cargar_cola_pvd():
    """Carga la cola actual de PVD"""
    try:
        with open('data/cola_pvd.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_cola_pvd(cola):
    """Guarda la cola PVD"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/cola_pvd.json', 'w', encoding='utf-8') as f:
            json.dump(cola, f, indent=4, ensure_ascii=False)
        
        # Backup
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/cola_pvd.json', 'data_backup/cola_pvd.json')
        return True
    except Exception as e:
        st.error(f"Error guardando cola PVD: {e}")
        return False

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Verifica y finaliza automáticamente pausas que han terminado"""
    hubo_cambios = False
    
    for pausa in cola_pvd:
        if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).total_seconds() / 60
            
            if tiempo_transcurrido >= duracion_minutos:
                pausa['estado'] = 'COMPLETADO'
                pausa['timestamp_fin'] = datetime.now().isoformat()
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
            siguiente = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))[0]
            siguiente['estado'] = 'EN_CURSO'
            siguiente['timestamp_inicio'] = datetime.now().isoformat()
            
            # NUEVO: Cancelar temporizador del usuario
            temporizador_pvd.cancelar_temporizador(siguiente['usuario_id'])
            
            if config_pvd.get('sonido_activado', True):
                notificar_inicio_pausa(siguiente, config_pvd)
            
            guardar_cola_pvd(cola_pvd)
            return True
    
    return False

def notificar_inicio_pausa(pausa, config_pvd):
    """Envía notificación al usuario cuando su pausa inicia"""
    try:
        duracion_minutos = config_pvd['duracion_corta'] if pausa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
        mensaje = f"¡Tu pausa de {duracion_minutos} minutos ha comenzado! ⏰"
        
        # Notificación segura sin HTML peligroso
        st.toast(f"🎉 {mensaje}", icon="⏰")
        
    except Exception as e:
        st.warning(f"Error en notificación: {e}")

# ==============================================
# NUEVA FUNCIÓN: ACTUALIZAR TEMPORIZADORES PVD
# ==============================================

def actualizar_temporizadores_pvd():
    """Actualiza los temporizadores PVD para usuarios en cola"""
    try:
        config_pvd = cargar_config_pvd()
        cola_pvd = cargar_cola_pvd()
        
        # Verificar notificaciones pendientes
        if 'username' in st.session_state:
            notificacion = temporizador_pvd.verificar_notificaciones_pendientes(st.session_state.username)
            if notificacion:
                st.toast(f"🔔 {notificacion['mensaje']}", icon="🎯")
        
        # Para cada usuario en espera, calcular y actualizar temporizador
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        
        for pausa in en_espera:
            usuario_id = pausa['usuario_id']
            
            # Calcular tiempo estimado
            tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, usuario_id)
            
            if tiempo_estimado is not None and tiempo_estimado > 0:
                # Verificar si ya tiene un temporizador activo
                tiempo_restante = temporizador_pvd.obtener_tiempo_restante(usuario_id)
                
                if tiempo_restante is None or abs(tiempo_restante - tiempo_estimado) > 1:
                    # Actualizar temporizador
                    temporizador_pvd.cancelar_temporizador(usuario_id)
                    temporizador_pvd.iniciar_temporizador_usuario(usuario_id, tiempo_estimado)
            
            elif tiempo_estimado == 0:
                # Entrada inmediata - cancelar temporizador si existe
                temporizador_pvd.cancelar_temporizador(usuario_id)
        
        return True
    except Exception as e:
        print(f"Error actualizando temporizadores: {e}")
        return False

# ==============================================
# FUNCIÓN MODIFICADA: SOLICITAR PAUSA (CON TEMPORIZADOR)
# ==============================================

def solicitar_pausa(config_pvd, cola_pvd, duracion_elegida):
    """Solicita una pausa PVD para el usuario actual (con temporizador)"""
    # Verificar límite diario
    pausas_hoy = len([p for p in cola_pvd 
                     if p['usuario_id'] == st.session_state.username and 
                     datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now().isoformat())).date() == datetime.now().date() and
                     p['estado'] != 'CANCELADO'])
    
    if pausas_hoy >= 5:
        st.warning(f"⚠️ Has alcanzado el límite de 5 pausas diarias")
        return False
    
    # Verificar si ya tiene pausa activa
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            st.warning(f"⚠️ Ya tienes una pausa {ESTADOS_PVD.get(pausa['estado'])}. Espera a que termine.")
            return False
    
    # Crear nueva pausa
    nueva_pausa = {
        'id': str(uuid.uuid4())[:8],
        'usuario_id': st.session_state.username,
        'usuario_nombre': st.session_state.get('user_config', {}).get('nombre', 'Usuario'),
        'duracion_elegida': duracion_elegida,
        'estado': 'ESPERANDO',
        'timestamp_solicitud': datetime.now().isoformat(),
        'timestamp_inicio': None,
        'timestamp_fin': None
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
        nueva_pausa['timestamp_inicio'] = datetime.now().isoformat()
        
        if config_pvd.get('sonido_activado', True):
            notificar_inicio_pausa(nueva_pausa, config_pvd)
    else:
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        st.info(f"⏳ Pausa solicitada. Posición en cola: #{en_espera}")
        
        # NUEVO: Iniciar temporizador para este usuario
        tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, st.session_state.username)
        if tiempo_estimado and tiempo_estimado > 0:
            temporizador_pvd.iniciar_temporizador_usuario(st.session_state.username, tiempo_estimado)
            st.info(f"⏱️ Tiempo estimado de espera: {tiempo_estimado} minutos")
    
    guardar_cola_pvd(cola_pvd)
    return True

# ==============================================
# FUNCIONES DE CÁLCULO (SIN CAMBIOS)
# ==============================================

def determinar_rl_gas(consumo_anual):
    """Determina automáticamente el RL según consumo anual"""
    if consumo_anual <= 5000:
        return "RL1"
    elif consumo_anual <= 15000:
        return "RL2"
    else:
        return "RL3"

def calcular_pmg(tiene_pmg, es_canarias=False):
    """Calcula el coste del PMG con/sin IVA"""
    if not tiene_pmg:
        return 0
    
    coste_pmg = PMG_COSTE
    if not es_canarias:
        coste_pmg *= (1 + PMG_IVA)
    
    return coste_pmg * 12

def calcular_coste_gas_completo(plan, consumo_kwh, tiene_pmg=True, es_canarias=False):
    """Calcula coste total de gas incluyendo PMG e IVA"""
    if tiene_pmg:
        termino_fijo = plan["termino_fijo_con_pmg"]
        termino_variable = plan["termino_variable_con_pmg"]
    else:
        termino_fijo = plan["termino_fijo_sin_pmg"]
        termino_variable = plan["termino_variable_sin_pmg"]
    
    coste_fijo = termino_fijo * 12
    coste_variable = consumo_kwh * termino_variable
    coste_gas_sin_iva = coste_fijo + coste_variable
    
    if not es_canarias:
        coste_gas_con_iva = coste_gas_sin_iva * (1 + PMG_IVA)
    else:
        coste_gas_con_iva = coste_gas_sin_iva
    
    coste_pmg = calcular_pmg(tiene_pmg, es_canarias)
    
    return coste_gas_con_iva + coste_pmg

def calcular_plan_ahorro_automatico(plan, consumo, dias, tiene_pi=False, es_anual=False):
    """Calcula el coste para el Plan Ahorro Automático"""
    if es_anual:
        total_dias = 365
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    else:
        total_dias = dias
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    
    consumo_diario = consumo / total_dias
    consumo_bajo_precio = consumo_diario * dias_bajo_precio
    consumo_precio_normal = consumo_diario * dias_precio_normal
    
    precio_normal = 0.215
    precio_bajo = 0.105
    
    coste_consumo_normal = consumo_precio_normal * precio_normal
    coste_consumo_bajo = consumo_bajo_precio * precio_bajo
    coste_consumo_total = coste_consumo_normal + coste_consumo_bajo
    
    return {
        'coste_consumo': coste_consumo_total,
        'dias_bajo_precio': dias_bajo_precio,
        'dias_precio_normal': dias_precio_normal,
        'consumo_bajo_precio': consumo_bajo_precio,
        'consumo_precio_normal': consumo_precio_normal
    }

def calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh=0.0):
    """Calcula comparación exacta con factura actual"""
    try:
        # Cargar datos
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        planes_activos = filtrar_planes_por_usuario(df_luz, st.session_state.username, "luz")
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Configuración de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando comparativa...")
        
        # Constantes
        ALQUILER_CONTADOR = 0.81
        PACK_IBERDROLA = 3.95
        IMPUESTO_ELECTRICO = 0.0511
        DESCUENTO_PRIMERA_FACTURA = 5.00
        IVA = 0.21
        
        todos_resultados = []
        resultados_con_pi = []
        
        # Calcular para cada plan
        for _, plan in planes_activos.iterrows():
            # Verificar disponibilidad en comunidad
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in str(plan['plan']).upper()
            es_especial_plus = "ESPECIAL PLUS" in str(plan['plan']).upper()
            
            for tiene_pi in [True, False]:
                if es_ahorro_automatico:
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo, dias, tiene_pi, es_anual=False
                    )
                    
                    precio_kwh = "0.215€/0.105€*"
                    coste_consumo = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA * (dias / 30) if tiene_pi else 0.0
                    
                    if tiene_pi:
                        bonificacion_mensual = 10.00 * (dias / 30)
                    else:
                        bonificacion_mensual = 8.33 * (dias / 30)
                    
                else:
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA * (dias / 30)
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo = consumo * precio_kwh
                    bonificacion_mensual = 0.0
                
                coste_potencia = potencia * plan['total_potencia'] * dias
                ingreso_excedentes = excedente_kwh * precio_excedente
                
                subtotal_sin_excedentes = coste_consumo + coste_potencia
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes
                
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                coste_alquiler = ALQUILER_CONTADOR * (dias / 30)
                subtotal_final = subtotal_con_excedentes + coste_alquiler + coste_pack
                
                impuesto_electrico = subtotal_final * IMPUESTO_ELECTRICO
                
                if comunidad != "Canarias":
                    iva_total = (subtotal_final + impuesto_electrico) * IVA
                else:
                    iva_total = 0
                
                total_bruto = subtotal_final + impuesto_electrico + iva_total
                total_neto = total_bruto - DESCUENTO_PRIMERA_FACTURA - bonificacion_mensual
                total_nuevo = max(0, total_neto)
                
                ahorro = costo_actual - total_nuevo
                ahorro_anual = ahorro * (365 / dias)
                
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d a 0.105€"
                
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                if excedente_kwh > 0:
                    info_extra += f" | ☀️ {excedente_kwh}kWh excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes:.2f}€"
                
                if len(comunidades_plan) == 1 and 'Toda España' in comunidades_plan:
                    info_extra += " | 🗺️ Toda España"
                elif len(comunidades_plan) < 5:
                    info_extra += f" | 🗺️ {', '.join(comunidades_plan)}"
                else:
                    info_extra += f" | 🗺️ {len(comunidades_plan)} CCAA"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Coste Nuevo': round(total_nuevo, 2),
                    'Ahorro Mensual': round(ahorro, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # Filtrar resultados especial plus
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar mejor plan
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        # Mostrar resultados
        st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
        
        st.info(f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo:** {consumo}kWh × Precio del plan
        - **Potencia:** {potencia}kW × {dias}días × Tarifa potencia
        - **Excedentes:** {excedente_kwh}kWh × {precio_excedente}€/kWh = {excedente_kwh * precio_excedente:.2f}€
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """)
        
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Coste Actual", f"{costo_actual}€")
        with col2:
            st.metric("💰 Coste Nuevo", f"{mejor_plan_con_pi['Coste Nuevo']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        df_resultados = pd.DataFrame(resultados_finales)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Coste Nuevo', 
                          'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # Recomendaciones
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
        
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning("ℹ️ Todos los planes CON Pack Iberdrola son más caros que tu factura actual")
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {str(e)}")

# ==============================================
# FUNCIONES DE INTERFAZ DE USUARIO
# ==============================================

def mostrar_login():
    """Muestra la pantalla de login"""
    st.header("🔐 Acceso a la Plataforma")
    
    config_sistema = cargar_config_sistema()
    login_automatico_activado = config_sistema.get("login_automatico_activado", True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚪 Acceso Automático")
        
        if login_automatico_activado:
            st.info("El acceso automático está ACTIVADO")
            if st.button("Entrar Automáticamente", use_container_width=True, type="primary"):
                username, user_config = identificar_usuario_automatico()
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = username
                st.session_state.user_config = user_config
                st.session_state.login_time = datetime.now()
                
                st.success(f"✅ Identificado como: {user_config['nombre']}")
                st.rerun()
        else:
            st.warning("El acceso automático está DESACTIVADO por el administrador")
            st.info("Usa el formulario de acceso manual")
    
    with col2:
        st.subheader("🔧 Acceso Manual")
        admin_user = st.text_input("Usuario", key="admin_user")
        admin_pass = st.text_input("Contraseña", type="password", key="admin_pass")
        
        if st.button("Entrar", use_container_width=True, type="secondary"):
            if authenticate(admin_user, admin_pass, "admin"):
                st.session_state.authenticated = True
                st.session_state.user_type = "admin"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            elif authenticate(admin_user, admin_pass, "user"):
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

# ==============================================
# FUNCIÓN MODIFICADA: GESTIÓN PVD USUARIO (CON TEMPORIZADOR)
# ==============================================

def gestion_pvd_usuario():
    """Sistema de Pausas Visuales para usuarios con temporizador en tiempo real"""
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    # NUEVO: Actualizar temporizadores automáticamente
    actualizar_temporizadores_pvd()
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    verificar_pausas_completadas(cola_pvd, config_pvd)
    
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
            help="Activar/desactivar notificaciones"
        )
        if notif_activadas != st.session_state.notificaciones_activas:
            st.session_state.notificaciones_activas = notif_activadas
            st.rerun()
    
    # NUEVO: JavaScript para actualización automática
    auto_refresh_js = """
    <script>
    // Actualizar cada 30 segundos
    setTimeout(function() {
        window.location.reload();
    }, 30000);
    </script>
    """
    st.components.v1.html(auto_refresh_js, height=0)
    
    if st.button("🔄 Actualizar Ahora", use_container_width=True, type="primary"):
        st.rerun()

    # Buscar pausa activa del usuario
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.warning(f"⏳ **Tienes una pausa solicitada** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = next((i+1 for i, p in enumerate(en_espera_ordenados) 
                           if p['id'] == usuario_pausa_activa['id']), 1)
            
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            st.write(f"**Tu pausa:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Posición en cola:** #{posicion} de {len(en_espera)}")
            st.write(f"**Estado:** {en_pausa}/{maximo} pausas activas")
            
            # NUEVO: Mostrar temporizador de cuenta atrás
            tiempo_restante = temporizador_pvd.obtener_tiempo_restante(st.session_state.username)
            
            if tiempo_restante is not None:
                col_timer1, col_timer2 = st.columns(2)
                with col_timer1:
                    if tiempo_restante > 0:
                        # Mostrar temporizador visual
                        tiempo_total = temporizador_pvd.temporizadores_activos.get(st.session_state.username, {}).get('tiempo_total_minutos', tiempo_restante)
                        progreso = max(0, min(100, 100 * (1 - (tiempo_restante / max(tiempo_total, 1)))))
                        st.progress(int(progreso))
                        
                        # Mostrar tiempo en formato legible
                        horas = tiempo_restante // 60
                        minutos = tiempo_restante % 60
                        
                        if horas > 0:
                            tiempo_display = f"{horas}h {minutos}m"
                        else:
                            tiempo_display = f"{minutos}m"
                        
                        st.metric("⏱️ Tiempo restante estimado", tiempo_display)
                    else:
                        st.success("🎯 **¡Es tu turno!** Tu pausa debería iniciar en cualquier momento")
                
                with col_timer2:
                    # Información adicional del temporizador
                    if tiempo_restante > 0:
                        st.write("**⏳ Entrada estimada:**")
                        tiempo_entrada = datetime.now() + timedelta(minutes=tiempo_restante)
                        st.write(f"🕒 {tiempo_entrada.strftime('%H:%M')}")
                    else:
                        st.write("**🚀 Entrada inminente**")
            
            if posicion == 1 and en_pausa < maximo:
                st.success("🎯 **¡Próximo!** Serás el siguiente en salir a pausa")
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.rerun()
            else:
                tiempo_espera = ""
                if 'timestamp_solicitud' in usuario_pausa_activa:
                    tiempo_solicitud = datetime.fromisoformat(usuario_pausa_activa['timestamp_solicitud'])
                    minutos_esperando = (datetime.now() - tiempo_solicitud).seconds // 60
                    tiempo_espera = f" | Esperando: {minutos_esperando} min"
                
                st.info(f"📋 **En cola:** Posición #{posicion}{tiempo_espera}")
            
            if st.button("❌ Cancelar mi pausa", type="secondary", key="cancel_my_pause"):
                usuario_pausa_activa['estado'] = 'CANCELADO'
                guardar_cola_pvd(cola_pvd)
                
                # NUEVO: Cancelar temporizador
                temporizador_pvd.cancelar_temporizador(st.session_state.username)
                
                st.success("✅ Pausa cancelada")
                st.rerun()
        
        elif usuario_pausa_activa['estado'] == 'EN_CURSO':
            st.success(f"✅ **Pausa en curso** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(usuario_pausa_activa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            col_tiempo1, col_tiempo2 = st.columns(2)
            with col_tiempo1:
                st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
            with col_tiempo2:
                st.metric("⏳ Restante", f"{tiempo_restante} min")
            
            st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')}")
            
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada!** Puedes volver a solicitar otra si necesitas")
            
            if st.button("✅ Finalizar pausa ahora", type="primary", key="finish_pause_now"):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now().isoformat()
                guardar_cola_pvd(cola_pvd)
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.success("✅ Pausa completada")
                st.rerun()
    
    else:
        st.info("👁️ **Sistema de Pausas Visuales Dinámicas**")
        st.write("Toma una pausa para descansar la vista durante tu jornada")
        
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
                            datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now().isoformat())).date() == datetime.now().date() and
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
                
                # NUEVO: Calcular tiempo estimado si hay cola
                if en_espera > 0:
                    tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, st.session_state.username)
                    if tiempo_estimado and tiempo_estimado > 0:
                        st.info(f"⏱️ **Tiempo estimado de espera:** {tiempo_estimado} minutos")
            else:
                st.warning(f"⏳ **SISTEMA LLENO** - Hay {en_espera} persona(s) en cola. Te pondremos en espera.")
                
                # NUEVO: Calcular tiempo estimado
                tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, st.session_state.username)
                if tiempo_estimado and tiempo_estimado > 0:
                    st.info(f"⏱️ **Tiempo estimado de espera:** {tiempo_estimado} minutos")
            
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

# ==============================================
# FUNCIONES DE GESTIÓN (SIN CAMBIOS)
# ==============================================

def gestion_electricidad():
    """Gestión de planes de electricidad"""
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
    # Cargar datos actuales
    try:
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
                'comunidades_autonomas'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
            'comunidades_autonomas'
        ])
    
    # Mostrar planes actuales
    st.write("### 📊 Planes Actuales")
    if not df_luz.empty:
        planes_activos = df_luz[df_luz['activo'] == True]
        planes_inactivos = df_luz[df_luz['activo'] == False]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**✅ Planes Activos**")
            for _, plan in planes_activos.iterrows():
                if st.button(f"📝 {plan['plan']}", key=f"edit_{plan['plan']}", use_container_width=True):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with col2:
            st.write("**❌ Planes Inactivos**")
            for _, plan in planes_inactivos.iterrows():
                if st.button(f"📝 {plan['plan']}", key=f"edit_inactive_{plan['plan']}", use_container_width=True):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with col3:
            st.write("**📈 Resumen**")
            st.metric("Planes Activos", len(planes_activos))
            st.metric("Planes Inactivos", len(planes_inactivos))
            st.metric("Total Planes", len(df_luz))
    
    else:
        st.info("No hay planes configurados aún")
    
    # Formulario para añadir/editar
    st.write("### ➕ Añadir/✏️ Editar Plan")
    
    if 'editing_plan' not in st.session_state:
        st.session_state.editing_plan = None
    
    if st.session_state.editing_plan is not None:
        plan_actual = st.session_state.editing_plan
        st.warning(f"✏️ Editando: **{plan_actual['plan']}**")
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_plan = None
            st.rerun()
    
    with st.form("form_plan_electricidad"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.editing_plan is not None:
                nombre_plan = st.text_input("Nombre del Plan*", 
                                          value=st.session_state.editing_plan['plan'],
                                          disabled=True)
                st.info("⚠️ El nombre no se puede modificar al editar")
            else:
                nombre_plan = st.text_input("Nombre del Plan*", placeholder="Ej: IMPULSA 24h")
            
            precio_original = st.number_input("Precio Original kWh*", min_value=0.0, format="%.3f", 
                                            value=st.session_state.editing_plan.get('precio_original_kwh', 0.170) if st.session_state.editing_plan else 0.170)
            con_pi = st.number_input("Con PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan.get('con_pi_kwh', 0.130) if st.session_state.editing_plan else 0.130)
        
        with col2:
            sin_pi = st.number_input("Sin PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan.get('sin_pi_kwh', 0.138) if st.session_state.editing_plan else 0.138)
            punta = st.number_input("Punta €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan.get('punta', 0.116) if st.session_state.editing_plan else 0.116)
            valle = st.number_input("Valle €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan.get('valle', 0.046) if st.session_state.editing_plan else 0.046)
        
        with col3:
            total_potencia = punta + valle
            st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                          value=total_potencia, disabled=True, key="total_potencia_display")
            st.caption("💡 Calculado automáticamente: Punta + Valle")
            
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan.get('activo', True) if st.session_state.editing_plan else True)
        
        # Comunidades autónomas
        st.write("### 🗺️ Comunidades Autónomas Disponibles")
        comunidades_actuales = []
        if st.session_state.editing_plan and 'comunidades_autonomas' in st.session_state.editing_plan:
            if pd.notna(st.session_state.editing_plan['comunidades_autonomas']):
                comunidades_actuales = st.session_state.editing_plan['comunidades_autonomas'].split(';')
        
        if not st.session_state.editing_plan:
            comunidades_actuales = ["Toda España"]
        
        comunidades_seleccionadas = st.multiselect(
            "Comunidades donde está disponible el plan:",
            COMUNIDADES_AUTONOMAS,
            default=comunidades_actuales,
            help="Selecciona las comunidades autónomas donde este plan está disponible"
        )
        
        submitted = st.form_submit_button(
            "💾 Guardar Cambios" if st.session_state.editing_plan else "➕ Crear Nuevo Plan", 
            type="primary"
        )
        
        if submitted:
            if not nombre_plan:
                st.error("❌ El nombre del plan es obligatorio")
            elif not comunidades_seleccionadas:
                st.error("❌ Debes seleccionar al menos una comunidad autónoma")
            else:
                nuevo_plan_data = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo,
                    'comunidades_autonomas': ';'.join(comunidades_seleccionadas)
                }
                
                if st.session_state.editing_plan is not None and 'umbral_especial_plus' in st.session_state.editing_plan:
                    nuevo_plan_data['umbral_especial_plus'] = st.session_state.editing_plan['umbral_especial_plus']
                else:
                    if "ESPECIAL PLUS" in nombre_plan.upper():
                        nuevo_plan_data['umbral_especial_plus'] = 15.00
                    else:
                        nuevo_plan_data['umbral_especial_plus'] = 0.00
                
                # Añadir o actualizar
                if nombre_plan in df_luz['plan'].values:
                    idx = df_luz[df_luz['plan'] == nombre_plan].index[0]
                    for key, value in nuevo_plan_data.items():
                        df_luz.at[idx, key] = value
                    st.success(f"✅ Plan '{nombre_plan}' actualizado correctamente")
                else:
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan_data])], ignore_index=True)
                    st.success(f"✅ Plan '{nombre_plan}' añadido correctamente")
                
                df_luz.to_csv("data/precios_luz.csv", index=False, encoding='utf-8')
                os.makedirs("data_backup", exist_ok=True)
                shutil.copy("data/precios_luz.csv", "data_backup/precios_luz.csv")
                
                st.session_state.editing_plan = None
                st.rerun()

def gestion_gas():
    """Gestión de planes de gas"""
    st.subheader("🔥 Gestión de Planes de Gas")
    
    # Cargar datos actuales
    try:
        with open('data/planes_gas.json', 'r', encoding='utf-8') as f:
            planes_gas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    # Configuración PMG
    st.write("### ⚙️ Configuración PMG (Pack Mantenimiento Gas)")
    
    col_pmg1, col_pmg2 = st.columns(2)
    with col_pmg1:
        pmg_coste = st.number_input("Coste PMG (€/mes):", value=PMG_COSTE, min_value=0.0, format="%.2f")
    with col_pmg2:
        pmg_iva = st.number_input("IVA PMG (%):", value=PMG_IVA * 100, min_value=0.0, max_value=100.0, format="%.1f") / 100
    
    if st.button("💾 Guardar Configuración PMG", key="guardar_pmg"):
        config_pmg = {"coste": pmg_coste, "iva": pmg_iva}
        with open('data/config_pmg.json', 'w', encoding='utf-8') as f:
            json.dump(config_pmg, f, indent=4, ensure_ascii=False)
        st.success("✅ Configuración PMG guardada")
    
    st.markdown("---")
    
    # Gestión de planes RL
    st.write("### 📊 Planes de Gas RL1, RL2, RL3")
    
    for rl, plan in planes_gas.items():
        with st.expander(f"**{rl}** - {plan['rango']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Términos CON PMG**")
                plan["termino_fijo_con_pmg"] = st.number_input(
                    f"Término fijo CON PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_con_{rl}"
                )
                plan["termino_variable_con_pmg"] = st.number_input(
                    f"Término variable CON PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_con_{rl}"
                )
            
            with col2:
                st.write("**Términos SIN PMG**")
                plan["termino_fijo_sin_pmg"] = st.number_input(
                    f"Término fijo SIN PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_sin_{rl}"
                )
                plan["termino_variable_sin_pmg"] = st.number_input(
                    f"Término variable SIN PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_sin_{rl}"
                )
            
            plan["precio_original_kwh"] = st.number_input(
                f"Precio original kWh (€) - {rl}:",
                value=float(plan["precio_original_kwh"]),
                min_value=0.0,
                format="%.3f",
                key=f"precio_{rl}"
            )
            
            plan["activo"] = st.checkbox(f"Plan activo - {rl}", 
                                       value=plan["activo"],
                                       key=f"activo_{rl}")
    
    if st.button("💾 Guardar Todos los Planes de Gas", type="primary"):
        os.makedirs('data', exist_ok=True)
        with open('data/planes_gas.json', 'w', encoding='utf-8') as f:
            json.dump(planes_gas, f, indent=4, ensure_ascii=False)
        os.makedirs("data_backup", exist_ok=True)
        shutil.copy("data/planes_gas.json", "data_backup/planes_gas.json")
        st.success("✅ Todos los planes de gas guardados correctamente")
        st.rerun()

# ==============================================
# FUNCIÓN MODIFICADA: GESTIÓN PVD ADMIN (CON INFO DE TEMPORIZADOR)
# ==============================================

def gestion_pvd_admin():
    """Administración del sistema PVD con información de temporizadores"""
    st.subheader("👁️ Administración PVD (Pausa Visual Dinámica)")
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    if st.button("🔄 Actualizar Estado", key="refresh_admin", use_container_width=True):
        verificar_pausas_completadas(cola_pvd, config_pvd)
        st.rerun()
    
    # Configuración del sistema
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
            help="Máximo número de agentes que pueden estar en pausa al mismo tiempo"
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
    
    # Estadísticas actuales
    st.markdown("---")
    st.write("### 📊 Estado Actual del Sistema")
    
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
    completados_hoy = len([p for p in cola_pvd if p['estado'] == 'COMPLETADO' and 
                          datetime.fromisoformat(p.get('timestamp_fin', datetime.now().isoformat())).date() == datetime.now().date()])
    
    # NUEVO: Contar temporizadores activos
    temporizadores_activos = len(temporizador_pvd.temporizadores_activos)
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
    with col_stat1:
        st.metric("👥 Agentes Trabajando", agentes_activos)
    with col_stat2:
        st.metric("⏸️ En Pausa Ahora", f"{en_pausa}/{maximo_simultaneo}")
    with col_stat3:
        st.metric("⏳ Esperando", en_espera)
    with col_stat4:
        st.metric("✅ Completadas Hoy", completados_hoy)
    with col_stat5:
        st.metric("⏱️ Temporizadores", temporizadores_activos)
    
    # Pausas en curso
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
                    
                    progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
                    st.progress(int(progreso))
                    
                    st.write(f"**Agente:** {pausa.get('usuario_nombre', 'Desconocido')}")
                    st.write(f"**Usuario ID:** {pausa['usuario_id']}")
                    st.write(f"**Duración:** {duracion_minutos} min ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
                    st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')} | **Restante:** {tiempo_restante} min")
                    
                    if tiempo_restante == 0:
                        st.warning("⏰ **Pausa finalizada automáticamente**")
                
                with col_acciones:
                    if st.button("✅ Finalizar", key=f"fin_{pausa['id']}"):
                        pausa['estado'] = 'COMPLETADO'
                        pausa['timestamp_fin'] = datetime.now().isoformat()
                        guardar_cola_pvd(cola_pvd)
                        st.success(f"✅ Pausa #{pausa['id']} finalizada")
                        st.rerun()
                    
                    if st.button("❌ Cancelar", key=f"cancel_{pausa['id']}"):
                        pausa['estado'] = 'CANCELADO'
                        guardar_cola_pvd(cola_pvd)
                        st.warning(f"⚠️ Pausa #{pausa['id']} cancelada")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("🎉 No hay pausas activas en este momento")
    
    # Cola de espera
    if en_espera > 0:
        st.write("### 📝 Cola de Espera")
        en_espera_lista = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        en_espera_ordenados = sorted(en_espera_lista, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        for i, pausa in enumerate(en_espera_ordenados):
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_display = f"{config_pvd['duracion_corta']} min" if duracion_elegida == 'corta' else f"{config_pvd['duracion_larga']} min"
            
            # NUEVO: Obtener información del temporizador
            tiempo_restante = temporizador_pvd.obtener_tiempo_restante(pausa['usuario_id'])
            info_temporizador = ""
            
            if tiempo_restante is not None:
                if tiempo_restante > 0:
                    horas = tiempo_restante // 60
                    minutos = tiempo_restante % 60
                    if horas > 0:
                        info_temporizador = f"⏱️ {horas}h {minutos}m"
                    else:
                        info_temporizador = f"⏱️ {minutos}m"
                else:
                    info_temporizador = "🎯 ¡Turno!"
            
            col_esp1, col_esp2, col_esp3, col_esp4, col_esp5 = st.columns([2, 2, 2, 2, 1])
            with col_esp1:
                st.write(f"**#{i+1}** - {pausa.get('usuario_nombre', 'Desconocido')}")
            with col_esp2:
                st.write(f"🆔 {pausa['usuario_id']}")
            with col_esp3:
                st.write(f"⏱️ {duracion_display}")
            with col_esp4:
                st.write(info_temporizador)
            with col_esp5:
                if st.button("▶️ Iniciar", key=f"iniciar_{pausa['id']}"):
                    # Verificar si hay espacio
                    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
                    if en_pausa < config_pvd['maximo_simultaneo']:
                        pausa['estado'] = 'EN_CURSO'
                        pausa['timestamp_inicio'] = datetime.now().isoformat()
                        guardar_cola_pvd(cola_pvd)
                        
                        # Cancelar temporizador
                        temporizador_pvd.cancelar_temporizador(pausa['usuario_id'])
                        
                        st.success(f"✅ Pausa #{pausa['id']} iniciada")
                        st.rerun()
                    else:
                        st.error("❌ No hay espacio disponible")

def gestion_modelos_factura():
    """Gestión de modelos de factura"""
    st.subheader("📄 Gestión de Modelos de Factura")
    
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # Obtener empresas existentes
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### ➕ Crear Nueva Empresa")
        nueva_empresa = st.text_input("Nombre de la empresa", placeholder="Ej: MiEmpresa S.L.")
        
        if st.button("Crear Empresa") and nueva_empresa:
            carpeta_empresa = f"modelos_facturas/{nueva_empresa.lower().replace(' ', '_')}"
            os.makedirs(carpeta_empresa, exist_ok=True)
            
            # Backup
            if os.path.exists("modelos_facturas"):
                backup_folder = "data_backup/modelos_facturas"
                if os.path.exists(backup_folder):
                    shutil.rmtree(backup_folder)
                shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
            st.success(f"✅ Empresa '{nueva_empresa}' creada correctamente")
            st.rerun()
    
    with col2:
        st.write("### 📁 Empresas Existentes")
        if empresas_existentes:
            for empresa in empresas_existentes:
                st.write(f"**{empresa}**")
        else:
            st.info("No hay empresas creadas aún")
    
    # Subir modelos
    if empresas_existentes:
        st.write("### 📤 Subir Modelo de Factura")
        empresa_seleccionada = st.selectbox("Seleccionar Empresa", empresas_existentes)
        
        archivo = st.file_uploader("Subir modelo de factura", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if archivo is not None:
            carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
            ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
            with open(ruta_archivo, "wb") as f:
                f.write(archivo.getbuffer())
            
            # Backup
            backup_folder = "data_backup/modelos_facturas"
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
            shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
            st.success(f"✅ Modelo para {empresa_seleccionada} guardado correctamente")
            if archivo.type.startswith('image'):
                st.image(archivo, caption=f"Modelo de factura - {empresa_seleccionada}", use_container_width=True)

def consultar_modelos_factura():
    """Consultar modelos de factura para usuarios"""
    st.subheader("📊 Modelos de Factura")
    
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    if not empresas_existentes:
        st.warning("⚠️ No hay modelos de factura disponibles")
        st.info("Contacta con el administrador para que configure los modelos de factura")
        return
    
    st.info("Selecciona tu compañía eléctrica para ver los modelos de factura")
    empresa_seleccionada = st.selectbox("Selecciona tu compañía eléctrica", empresas_existentes)
    
    carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
    archivos = os.listdir(carpeta_empresa)
    
    if archivos:
        st.write(f"### 📋 Modelos disponibles para {empresa_seleccionada}:")
        for archivo in archivos:
            ruta_completa = os.path.join(carpeta_empresa, archivo)
            st.write(f"**Modelo:** {archivo}")
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                st.image(ruta_completa, use_container_width=True)
            st.markdown("---")
    else:
        st.warning(f"⚠️ No hay modelos de factura subidos para {empresa_seleccionada}")

def comparativa_exacta():
    """Comparativa exacta para usuarios"""
    st.subheader("⚡ Comparativa EXACTA")
    st.info("Compara tu consumo exacto con nuestros planes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dias = st.number_input("Días del período", min_value=1, value=30, key="dias_exacta")
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_exacta")
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0, key="consumo_exacta")
    
    with col2:
        costo_actual = st.number_input("¿Cuánto pagaste? (€)", min_value=0.0, value=50.0, key="costo_exacta")
        comunidad = st.selectbox("Selecciona tu Comunidad Autónoma", COMUNIDADES_AUTONOMAS, key="comunidad_exacta")
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_exacta")
        excedente_kwh = 0.0
        if con_excedentes:
            excedente_kwh = st.number_input("kWh de excedente este mes", min_value=0.0, value=50.0, key="excedente_exacta")
    
    if st.button("🔍 Comparar", type="primary", key="comparar_exacta"):
        calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh)

def calculadora_gas():
    """Calculadora de gas para usuarios"""
    st.subheader("🔥 Calculadora de Gas")
    
    try:
        with open('data/planes_gas.json', 'r', encoding='utf-8') as f:
            planes_gas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    try:
        with open('data/config_pmg.json', 'r', encoding='utf-8') as f:
            config_pmg = json.load(f)
        pmg_coste = config_pmg["coste"]
        pmg_iva = config_pmg["iva"]
    except (FileNotFoundError, json.JSONDecodeError):
        pmg_coste = PMG_COSTE
        pmg_iva = PMG_IVA
    
    st.info("Compara planes de gas con cálculo EXACTO o ESTIMADO")
    
    tipo_calculo = st.radio("**Tipo de cálculo:**", ["📊 Estimación anual", "📈 Cálculo exacto mes actual"], horizontal=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if tipo_calculo == "📊 Estimación anual":
            consumo_anual = st.number_input("**Consumo anual estimado (kWh):**", min_value=0, value=5000, step=100)
            costo_actual_input = st.number_input("**¿Cuánto pagas actualmente al año? (€):**", min_value=0.0, value=600.0, step=10.0)
            costo_actual_anual = costo_actual_input
            costo_actual_mensual = costo_actual_anual / 12
        else:
            consumo_mes = st.number_input("**Consumo del mes actual (kWh):**", min_value=0, value=300, step=10)
            consumo_anual = consumo_mes * 12
            st.info(f"Consumo anual estimado: {consumo_anual:,.0f} kWh")
            costo_actual_input = st.number_input("**¿Cuánto pagaste este mes? (€):**", min_value=0.0, value=50.0, step=5.0)
            costo_actual_mensual = costo_actual_input
            costo_actual_anual = costo_actual_mensual * 12
    
    with col2:
        es_canarias = st.checkbox("**¿Ubicación en Canarias?**", help="No aplica IVA en Canarias")
    
    rl_recomendado = determinar_rl_gas(consumo_anual)
    
    if st.button("🔄 Calcular Comparativa Gas", type="primary"):
        resultados = []
        usuarios_config = cargar_configuracion_usuarios()
        planes_permitidos = []
        
        if st.session_state.username in usuarios_config:
            config_usuario = usuarios_config[st.session_state.username]
            planes_permitidos = config_usuario.get("planes_gas", ["RL1", "RL2", "RL3"])
        else:
            planes_permitidos = ["RL1", "RL2", "RL3"]
        
        for rl, plan in planes_gas.items():
            if plan["activo"] and rl in planes_permitidos:
                for tiene_pmg in [True, False]:
                    coste_anual = calcular_coste_gas_completo(plan, consumo_anual, tiene_pmg, es_canarias)
                    coste_mensual = coste_anual / 12
                    
                    coste_original = consumo_anual * plan["precio_original_kwh"]
                    ahorro_vs_original = coste_original - coste_anual
                    
                    ahorro_vs_actual_anual = costo_actual_anual - coste_anual
                    ahorro_vs_actual_mensual = ahorro_vs_actual_anual / 12
                    
                    recomendado = "✅" if rl == rl_recomendado else ""
                    
                    if ahorro_vs_actual_anual > 0:
                        estado = "💚 Ahorras"
                    elif ahorro_vs_actual_anual == 0:
                        estado = "⚖️ Igual"
                    else:
                        estado = "🔴 Pagas más"
                    
                    pmg_info = '✅ CON' if tiene_pmg else '❌ SIN'
                    info_extra = ""
                    
                    if tiene_pmg:
                        coste_pmg_anual = calcular_pmg(True, es_canarias)
                        info_extra = f" | 📦 PMG: {coste_pmg_anual/12:.2f}€/mes"
                    else:
                        info_extra = " | 📦 Sin PMG"
                    
                    if tiene_pmg:
                        precio_variable = plan["termino_variable_con_pmg"]
                        precio_fijo = plan["termino_fijo_con_pmg"]
                    else:
                        precio_variable = plan["termino_variable_sin_pmg"]
                        precio_fijo = plan["termino_fijo_sin_pmg"]
                    
                    precio_display = f"Var: {precio_variable:.3f}€ | Fijo: {precio_fijo:.2f}€"
                    
                    resultados.append({
                        "Plan": rl,
                        "Pack Mantenimiento": pmg_info,
                        "Precios": precio_display,
                        "Rango": plan["rango"],
                        "Coste Mensual": f"€{coste_mensual:,.2f}",
                        "Coste Anual": f"€{coste_anual:,.2f}",
                        "Ahorro vs Actual Mes": f"€{ahorro_vs_actual_mensual:,.2f}",
                        "Ahorro vs Actual Año": f"€{ahorro_vs_actual_anual:,.2f}",
                        "Ahorro vs Original": f"€{ahorro_vs_original:,.2f}",
                        "Estado": estado,
                        "Recomendado": recomendado,
                        "Info Extra": info_extra
                    })
        
        if resultados:
            st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
            
            info_tipo = "ESTIMACIÓN ANUAL" if tipo_calculo == "📊 Estimación anual" else "CÁLCULO EXACTO"
            info_consumo = f"{consumo_anual:,.0f} kWh/año"
            info_costo_actual = f"€{costo_actual_anual:,.2f}/año (€{costo_actual_mensual:,.2f}/mes)"
            info_iva = "Sin IVA" if es_canarias else "Con IVA 21%"
            
            st.info(f"**Tipo:** {info_tipo} | **Consumo:** {info_consumo} | **Actual:** {info_costo_actual} | **IVA:** {info_iva}")
            
            mejor_plan = max(resultados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💶 Actual Mensual", f"€{costo_actual_mensual:,.2f}")
            with col2:
                coste_mejor_mensual = float(mejor_plan['Coste Mensual'].replace('€', '').replace(',', ''))
                st.metric("💰 Mejor Mensual", f"€{coste_mejor_mensual:,.2f}")
            with col3:
                ahorro_mensual = float(mejor_plan['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
                st.metric("📈 Ahorro Mensual", f"€{ahorro_mensual:,.2f}", delta=f"€{ahorro_mensual:,.2f}" if ahorro_mensual > 0 else None)
            with col4:
                ahorro_anual = float(mejor_plan['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
                st.metric("🎯 Ahorro Anual", f"€{ahorro_anual:,.2f}")
            
            st.dataframe(resultados, use_container_width=True)
            
            planes_recomendados = [p for p in resultados if p['Recomendado'] == '✅']
            
            if planes_recomendados:
                mejor_recomendado = max(planes_recomendados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
                ahorro_mensual_rec = float(mejor_recomendado['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
                ahorro_anual_rec = float(mejor_recomendado['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
                
                if ahorro_mensual_rec > 0:
                    mensaje = f"🎯 **MEJOR OPCIÓN**: {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG"
                    mensaje += f" - Ahorras {ahorro_mensual_rec:,.2f}€/mes ({ahorro_anual_rec:,.2f}€/año)"
                    if mejor_recomendado['Info Extra']:
                        mensaje += mejor_recomendado['Info Extra']
                    st.success(mensaje)
                elif ahorro_mensual_rec == 0:
                    st.info(f"ℹ️ Con {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG pagarías lo mismo que actualmente")
                else:
                    st.warning(f"⚠️ Con {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG pagarías {abs(ahorro_mensual_rec):,.2f}€/mes más")
        
        else:
            st.warning("No hay planes de gas activos para mostrar")

def cups_naturgy():
    """Mostrar CUPS de ejemplo para Naturgy"""
    st.subheader("📋 CUPS Naturgy")
    
    st.info("Ejemplos de CUPS para trámites con Naturgy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🔥 CUPS Ejemplo Gas")
        cups_gas = "ES0217010103496537HH"
        st.code(cups_gas, language="text")
        
        if st.button("📋 Copiar CUPS Gas", key="copy_gas", use_container_width=True):
            st.session_state.copied_gas = cups_gas
            st.success("✅ CUPS Gas copiado al portapapeles")
    
    with col2:
        st.write("### ⚡ CUPS Ejemplo Electricidad")
        cups_luz = "ES0031405120579007YM"
        st.code(cups_luz, language="text")
        
        if st.button("📋 Copiar CUPS Electricidad", key="copy_luz", use_container_width=True):
            st.session_state.copied_luz = cups_luz
            st.success("✅ CUPS Electricidad copiado al portapapeles")
    
    st.markdown("---")
    st.write("### 🌐 Acceso Directo a Tarifa Plana Zen")
    
    url = "https://www.naturgy.es/hogar/luz_y_gas/tarifa_plana_zen"
    
    st.markdown(f"""
    <a href="{url}" target="_blank" style="text-decoration: none;">
        <button style="
            background-color: #00A0E3; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 5px; 
            font-size: 16px; 
            cursor: pointer;
            width: 100%;
        ">
            🚀 Abrir Tarifa Plana Zen de Naturgy
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    st.caption("💡 Se abrirá en una nueva pestaña")

def gestion_usuarios():
    """Gestión de usuarios y grupos"""
    st.subheader("👥 Gestión de Usuarios y Grupos")
    
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    tab1, tab2, tab3 = st.tabs(["👤 Usuarios", "👥 Grupos", "➕ Crear Usuario"])
    
    with tab1:
        st.write("### 📊 Lista de Usuarios")
        
        for username, config in usuarios_config.items():
            if username == "admin":
                continue
                
            with st.expander(f"👤 {username} - {config.get('nombre', 'Sin nombre')}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("Nombre", value=config.get('nombre', ''), key=f"nombre_{username}")
                    
                    grupo_actual = config.get('grupo', '')
                    grupo_seleccionado = st.selectbox(
                        "Grupo",
                        [""] + list(grupos.keys()),
                        index=0 if not grupo_actual else (list(grupos.keys()).index(grupo_actual) + 1),
                        key=f"grupo_{username}"
                    )
                    
                    st.write("**🔐 Cambiar contraseña:**")
                    nueva_password = st.text_input(
                        "Nueva contraseña",
                        type="password",
                        placeholder="Dejar vacío para no cambiar",
                        key=f"pass_{username}"
                    )
                    if nueva_password:
                        st.info("⚠️ La contraseña se cambiará al guardar")
                
                with col2:
                    if grupo_seleccionado and grupo_seleccionado in grupos:
                        permisos = grupos[grupo_seleccionado]
                        st.write("**Permisos del grupo:**")
                        st.write(f"📈 Luz: {', '.join(permisos.get('planes_luz', []))}")
                        st.write(f"🔥 Gas: {', '.join(permisos.get('planes_gas', []))}")
                    
                    st.write("**Información:**")
                    st.write(f"📧 Username: `{username}`")
                    st.write(f"🔑 Tipo: {config.get('tipo', 'user')}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar", key=f"save_{username}"):
                            usuarios_config[username]['nombre'] = nuevo_nombre
                            usuarios_config[username]['grupo'] = grupo_seleccionado
                            
                            if nueva_password:
                                usuarios_config[username]['password'] = nueva_password
                                st.success(f"✅ Contraseña actualizada para {username}")
                            
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} actualizado")
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Eliminar", key=f"del_{username}"):
                            del usuarios_config[username]
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} eliminado")
                            st.rerun()
    
    with tab2:
        st.write("### 👥 Gestión de Grupos")
        
        for grupo_nombre, permisos in grupos.items():
            with st.expander(f"**Grupo: {grupo_nombre}**", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Planes de Luz**")
                    try:
                        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
                        planes_luz_disponibles = df_luz['plan'].tolist()
                    except:
                        planes_luz_disponibles = []
                    
                    planes_luz_actuales = permisos.get('planes_luz', [])
                    if planes_luz_actuales == ["TODOS"]:
                        planes_luz_actuales = planes_luz_disponibles
                    
                    planes_luz_seleccionados = st.multiselect(
                        "Planes de luz permitidos",
                        planes_luz_disponibles,
                        default=planes_luz_actuales,
                        key=f"grupo_luz_{grupo_nombre}"
                    )
                
                with col2:
                    st.write("**Planes de Gas**")
                    planes_gas_disponibles = ["RL1", "RL2", "RL3"]
                    planes_gas_actuales = permisos.get('planes_gas', [])
                    
                    planes_gas_seleccionados = st.multiselect(
                        "Planes de gas permitidos",
                        planes_gas_disponibles,
                        default=planes_gas_actuales,
                        key=f"grupo_gas_{grupo_nombre}"
                    )
                
                if st.button("💾 Actualizar Grupo", key=f"update_grupo_{grupo_nombre}"):
                    grupos[grupo_nombre] = {
                        "planes_luz": planes_luz_seleccionados,
                        "planes_gas": planes_gas_seleccionados
                    }
                    config_sistema['grupos_usuarios'] = grupos
                    guardar_config_sistema(config_sistema)
                    st.success(f"✅ Grupo {grupo_nombre} actualizado")
                    st.rerun()
        
        # Crear nuevo grupo
        st.write("### ➕ Crear Nuevo Grupo")
        nuevo_grupo_nombre = st.text_input("Nombre del nuevo grupo")
        
        if st.button("Crear Grupo") and nuevo_grupo_nombre:
            if nuevo_grupo_nombre not in grupos:
                grupos[nuevo_grupo_nombre] = {
                    "planes_luz": [],
                    "planes_gas": []
                }
                config_sistema['grupos_usuarios'] = grupos
                guardar_config_sistema(config_sistema)
                st.success(f"✅ Grupo {nuevo_grupo_nombre} creado")
                st.rerun()
            else:
                st.error("❌ El grupo ya existe")
    
    with tab3:
        st.write("### 👤 Crear Nuevo Usuario")
        
        with st.form("form_nuevo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_username = st.text_input("Username*", help="Nombre de usuario para el acceso")
                nuevo_nombre = st.text_input("Nombre completo*", help="Nombre real del usuario")
                grupo_usuario = st.selectbox("Grupo", [""] + list(grupos.keys()), help="Asigna un grupo de permisos")
            
            with col2:
                password_usuario = st.text_input("Contraseña*", type="password", help="Contraseña para acceso manual")
                confirm_password = st.text_input("Confirmar contraseña*", type="password", help="Repite la contraseña")
                
                tipo_usuario = st.selectbox("Tipo de usuario", ["user", "auto", "manual"], help="user: Usuario normal, auto: Autogenerado, manual: Creado manualmente")
                
                st.write("**Planes especiales:**")
                planes_luz_todos = st.checkbox("Todos los planes de luz", value=True)
                planes_gas_todos = st.checkbox("Todos los planes de gas", value=True)
            
            submitted = st.form_submit_button("👤 Crear Usuario")
            
            if submitted:
                if not nuevo_username or not nuevo_nombre:
                    st.error("❌ Username y nombre son obligatorios")
                elif not password_usuario:
                    st.error("❌ La contraseña es obligatoria")
                elif password_usuario != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif nuevo_username in usuarios_config:
                    st.error("❌ El username ya existe")
                else:
                    planes_luz = "TODOS" if planes_luz_todos else []
                    planes_gas = ["RL1", "RL2", "RL3"] if planes_gas_todos else []
                    
                    usuarios_config[nuevo_username] = {
                        "nombre": nuevo_nombre,
                        "password": password_usuario,
                        "grupo": grupo_usuario,
                        "tipo": tipo_usuario,
                        "planes_luz": planes_luz,
                        "planes_gas": planes_gas,
                        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "creado_por": st.session_state.username
                    }
                    
                    guardar_configuracion_usuarios(usuarios_config)
                    st.success(f"✅ Usuario {nuevo_username} creado exitosamente")
                    
                    credenciales = f"Usuario: {nuevo_username}\nContraseña: {password_usuario}"
                    st.code(credenciales, language="text")
                    st.rerun()

def gestion_excedentes():
    """Configuración de excedentes de placas solares"""
    st.subheader("☀️ Configuración de Excedentes Placas Solares")
    
    try:
        config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
        precio_actual = config_excedentes.iloc[0]['precio_excedente_kwh']
    except (FileNotFoundError, pd.errors.EmptyDataError):
        precio_actual = 0.06
        config_excedentes = pd.DataFrame([{'precio_excedente_kwh': precio_actual}])
        config_excedentes.to_csv("data/config_excedentes.csv", index=False, encoding='utf-8')
    
    st.info("Configura el precio que se paga por kWh de excedente de placas solares")
    
    with st.form("form_excedentes"):
        nuevo_precio = st.number_input(
            "Precio por kWh de excedente (€)",
            min_value=0.0,
            max_value=1.0,
            value=precio_actual,
            format="%.3f",
            help="Precio que se paga al cliente por cada kWh de excedente de placas solares"
        )
        
        if st.form_submit_button("💾 Guardar Precio", type="primary"):
            config_excedentes = pd.DataFrame([{'precio_excedente_kwh': nuevo_precio}])
            config_excedentes.to_csv("data/config_excedentes.csv", index=False, encoding='utf-8')
            os.makedirs("data_backup", exist_ok=True)
            shutil.copy("data/config_excedentes.csv", "data_backup/config_excedentes.csv")
            st.success(f"✅ Precio de excedente actualizado a {nuevo_precio}€/kWh")
            st.rerun()
    
    st.info(f"**Precio actual:** {precio_actual}€ por kWh de excedente")

def gestion_config_sistema():
    """Configuración del sistema"""
    st.subheader("⚙️ Configuración del Sistema")
    
    config_sistema = cargar_config_sistema()
    
    st.write("### 🔐 Configuración de Acceso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        login_automatico = st.checkbox(
            "Activar login automático",
            value=config_sistema.get("login_automatico_activado", True),
            help="Los usuarios pueden entrar automáticamente sin credenciales"
        )
    
    with col2:
        horas_duracion = st.number_input(
            "Duración de sesión (horas)",
            min_value=1,
            max_value=24,
            value=config_sistema.get("sesion_horas_duracion", 8),
            help="Tiempo que dura una sesión antes de expirar"
        )
    
    if st.button("💾 Guardar Configuración Sistema", type="primary"):
        config_sistema.update({
            "login_automatico_activado": login_automatico,
            "sesion_horas_duracion": horas_duracion
        })
        guardar_config_sistema(config_sistema)
        st.success("✅ Configuración del sistema guardada")
        st.rerun()

def calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh=0.0):
    """Calcula estimación anual para usuarios"""
    try:
        # Cargar datos
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        planes_activos = df_luz[df_luz['activo'] == True]
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Configuración de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando estimación anual...")
        
        # Constantes
        ALQUILER_CONTADOR = 0.81 * 12
        PACK_IBERDROLA = 3.95 * 12
        IMPUESTO_ELECTRICO = 0.0511
        DESCUENTO_PRIMERA_FACTURA = 5.00
        IVA = 0.21
        DIAS_ANUAL = 365
        
        # Calcular costo anual actual
        costo_anual_actual = costo_mensual_actual * 12
        excedente_anual_kwh = excedente_mensual_kwh * 12
        ingreso_excedentes_anual = excedente_anual_kwh * precio_excedente
        
        # Listas para resultados
        todos_resultados = []
        resultados_con_pi = []
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR DISPONIBILIDAD EN COMUNIDAD
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in str(plan['plan']).upper()
            es_especial_plus = "ESPECIAL PLUS" in str(plan['plan']).upper()
            
            for tiene_pi in [True, False]:
                
                if es_ahorro_automatico:
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo_anual, DIAS_ANUAL, tiene_pi, es_anual=True
                    )
                    
                    precio_kwh = "0.215€/0.105€*"
                    coste_consumo_anual = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA if tiene_pi else 0.0
                    
                    if tiene_pi:
                        bonificacion_anual = 10.00 * 12
                    else:
                        bonificacion_anual = 8.33 * 12
                    
                else:
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo_anual = consumo_anual * precio_kwh
                    bonificacion_anual = 0.0
                
                # Cálculos
                coste_potencia_anual = potencia * plan['total_potencia'] * DIAS_ANUAL
                subtotal_sin_excedentes = coste_consumo_anual + coste_potencia_anual
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes_anual
                
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                coste_alquiler_anual = ALQUILER_CONTADOR
                subtotal_final_anual = subtotal_con_excedentes + coste_alquiler_anual + coste_pack
                
                impuesto_electrico_anual = subtotal_final_anual * IMPUESTO_ELECTRICO
                iva_anual = (subtotal_final_anual + impuesto_electrico_anual) * IVA
                
                total_bruto_anual = subtotal_final_anual + impuesto_electrico_anual + iva_anual
                total_neto_anual = total_bruto_anual - DESCUENTO_PRIMERA_FACTURA - bonificacion_anual
                total_anual = max(0, total_neto_anual)
                mensual = total_anual / 12
                
                # Calcular ahorro
                ahorro_anual = costo_anual_actual - total_anual
                ahorro_mensual = ahorro_anual / 12
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d/año a 0.105€"
                
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                if excedente_mensual_kwh > 0:
                    info_extra += f" | ☀️ {excedente_mensual_kwh}kWh/mes excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes_anual/12:.2f}€/mes"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Mensual': round(mensual, 2),
                    'Anual': round(total_anual, 2),
                    'Ahorro Mensual': round(ahorro_mensual, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro_mensual > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # Filtrar resultados CON PI según regla del Especial Plus
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        # Filtrar TODOS los resultados
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar mejor plan
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        st.write("### 📊 ESTIMACIÓN ANUAL")
        
        info_text = f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo anual:** {consumo_anual}kWh
        - **Potencia:** {potencia}kW
        - **Excedentes:** {excedente_mensual_kwh}kWh/mes × {precio_excedente}€/kWh = {excedente_mensual_kwh * precio_excedente * 12:.2f}€/año
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """
        
        if excedente_mensual_kwh > 0:
            info_text += f"\n- **Excedentes anuales:** {excedente_anual_kwh}kWh × {precio_excedente}€ = {ingreso_excedentes_anual:.2f}€"
        
        st.info(info_text)
        
        # MÉTRICAS PRINCIPALES
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Actual Mensual", f"{costo_mensual_actual}€")
        with col2:
            st.metric("💰 Nuevo Mensual", f"{mejor_plan_con_pi['Mensual']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        # TABLA COMPLETA
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        df_resultados = pd.DataFrame(resultados_finales)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Mensual', 
                          'Anual', 'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # RECOMENDACIONES
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
            st.info(f"💡 Pagarías {mejor_plan_con_pi['Mensual']}€/mes normalmente")
        
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes más, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning(f"ℹ️ Todos los planes CON Pack Iberdrola son más caros que lo que pagas actualmente ({costo_mensual_actual}€/mes)")
        
    except Exception as e:
        st.error(f"❌ Error en el cálculo anual: {str(e)}")

def comparativa_estimada():
    """Comparativa estimada para usuarios"""
    st.subheader("📅 Comparativa ESTIMADA")
    st.info("Estima tu consumo anual con nuestros planes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_estimada")
        consumo_anual = st.number_input("Consumo anual estimado (kWh)", min_value=0.0, value=7500.0, key="consumo_estimada")
        costo_mensual_actual = st.number_input("¿Cuánto pagas actualmente al mes? (€)", min_value=0.0, value=80.0, key="costo_actual_estimada")
    
    with col2:
        comunidad = st.selectbox("Selecciona tu Comunidad Autónoma", COMUNIDADES_AUTONOMAS, key="comunidad_estimada")
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_estimada")
        excedente_mensual_kwh = 0.0
        if con_excedentes:
            excedente_mensual_kwh = st.number_input("kWh de excedente mensual promedio", min_value=0.0, value=40.0, key="excedente_estimada")
    
    if st.button("📊 Calcular Estimación", type="primary", key="calcular_estimada"):
        calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh)

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    if not verificar_sesion():
        mostrar_login()
        return
    
    # Mostrar información del usuario
    if st.session_state.username in cargar_configuracion_usuarios():
        config = cargar_configuracion_usuarios()[st.session_state.username]
        st.header(f"👤 {config.get('nombre', 'Usuario')}")
    else:
        st.header("👤 Portal del Cliente")
    
    # PRIMERA PANTALLA: Consultar modelos de factura
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Comparativas
    st.subheader("🧮 Comparativas")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Comparativa EXACTA", "📅 Comparativa ESTIMADA", "🔥 Gas", "👁️ PVD", "📋 CUPS Naturgy"])
    
    with tab1:
        comparativa_exacta()
    with tab2:
        comparativa_estimada()
    with tab3:
        calculadora_gas()
    with tab4:
        gestion_pvd_usuario()
    with tab5:
        cups_naturgy()

def mostrar_panel_administrador():
    """Panel de administración"""
    if not verificar_sesion():
        mostrar_login()
        return
    
    st.header("🔧 Panel de Administración")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⚡ Electricidad", "🔥 Gas", "👥 Usuarios", "👁️ PVD", 
        "📄 Facturas", "☀️ Excedentes", "⚙️ Sistema"
    ])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_usuarios()
    with tab4:
        gestion_pvd_admin()
    with tab5:
        gestion_modelos_factura()
    with tab6:
        gestion_excedentes()
    with tab7:
        gestion_config_sistema()

def main():
    """Función principal de la aplicación"""
    # Configuración de página
    st.set_page_config(
        page_title="Zelenza CEX - Iberdrola",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://www.example.com/help',
            'Report a bug': 'https://www.example.com/bug',
            'About': '# Zelenza CEX v1.0 con Temporizador PVD'
        }
    )
    
    # Restauración automática al iniciar
    if os.path.exists("data_backup"):
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas", dirs_exist_ok=True)
    
    inicializar_datos()
    
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    # Inicializar estado de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None
        st.session_state.user_config = {}
        st.session_state.device_id = None
    
    # Verificar si ya está autenticado
    if st.session_state.get('authenticated', False):
        if not verificar_sesion():
            mostrar_login()
            return
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        # Barra lateral
        st.sidebar.title(f"{'🔧 Admin' if st.session_state.user_type == 'admin' else '👤 Usuario'}")
        st.sidebar.write(f"**Usuario:** {st.session_state.username}")
        
        # Mostrar nombre del usuario si está disponible
        if st.session_state.user_type == "user" and 'user_config' in st.session_state:
            nombre_usuario = st.session_state.user_config.get('nombre', '')
            if nombre_usuario:
                st.sidebar.write(f"**Nombre:** {nombre_usuario}")
        
        # Información de grupo si tiene
        if st.session_state.user_type == "user" and 'user_config' in st.session_state:
            grupo_usuario = st.session_state.user_config.get('grupo', '')
            if grupo_usuario:
                st.sidebar.write(f"**Grupo:** {grupo_usuario}")
        
        # Botón para cerrar sesión
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            # Limpiar sesión
            st.session_state.authenticated = False
            st.session_state.user_type = None
            st.session_state.username = ""
            st.session_state.login_time = None
            st.session_state.user_config = {}
            st.session_state.device_id = None
            
            # Cancelar temporizador si existe
            if 'username' in st.session_state:
                temporizador_pvd.cancelar_temporizador(st.session_state.username)
            
            st.rerun()
        
        st.sidebar.markdown("---")
        
        # Mostrar el panel correspondiente
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

# ==============================================
# EJECUCIÓN PRINCIPAL
# ==============================================

if __name__ == "__main__":
    main()