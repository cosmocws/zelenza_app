import os
import shutil
import json
import pandas as pd
from config import (
    PLANES_GAS_ESTRUCTURA, PMG_COSTE, PMG_IVA,
    USUARIOS_DEFAULT, PVD_CONFIG_DEFAULT,
    SISTEMA_CONFIG_DEFAULT, GRUPOS_PVD_CONFIG,
    SUPER_USER_CONFIG_DEFAULT
)
from utils import inicializar_directorios

def inicializar_datos():
    """Inicializa los archivos de datos con backup automático"""
    try:
        inicializar_directorios()
        
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
            "super_users.json": json.dumps(SUPER_USER_CONFIG_DEFAULT, indent=4),
            "registro_llamadas.json": json.dumps({}, indent=4),
            "config_sistema.json": json.dumps(SISTEMA_CONFIG_DEFAULT, indent=4)
        }
        
        for archivo, df_default in archivos_criticos.items():
            ruta_data = f"data/{archivo}"
            ruta_backup = f"data_backup/{archivo}"
            
            if not os.path.exists(ruta_data):
                if os.path.exists(ruta_backup):
                    try:
                        shutil.copy(ruta_backup, ruta_data)
                    except Exception as e:
                        print(f"Error restaurando {archivo}: {e}")
                else:
                    try:
                        if archivo.endswith('.json'):
                            with open(ruta_data, 'w', encoding='utf-8') as f:
                                f.write(df_default)
                        else:
                            df_default.to_csv(ruta_data, index=False, encoding='utf-8')
                    except Exception as e:
                        print(f"Error creando {archivo}: {e}")
            
            try:
                if os.path.exists(ruta_data):
                    shutil.copy(ruta_data, ruta_backup)
            except Exception as e:
                print(f"Error creando backup de {archivo}: {e}")
        
        # Backup de modelos de factura
        if os.path.exists("modelos_facturas") and os.listdir("modelos_facturas"):
            backup_folder = "data_backup/modelos_facturas"
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
            shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
    except Exception as e:
        print(f"Error crítico en inicialización: {e}")

# ==============================================
# FUNCIONES DE CARGA DE DATOS
# ==============================================

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
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/usuarios.json', 'data_backup/usuarios.json')
        return True
    except Exception as e:
        print(f"Error guardando usuarios: {e}")
        return False

def cargar_config_sistema():
    """Carga la configuración del sistema"""
    try:
        with open('data/config_sistema.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Asegurar que tiene todos los campos necesarios
        campos_requeridos = ["login_automatico_activado", "sesion_horas_duracion", 
                           "grupos_usuarios", "secciones_activas", "grupos_pvd"]
        
        for campo in campos_requeridos:
            if campo not in config:
                if campo == "grupos_pvd":
                    config[campo] = GRUPOS_PVD_CONFIG
                elif campo == "secciones_activas":
                    from config import SECCIONES_USUARIO
                    config[campo] = {seccion: True for seccion in SECCIONES_USUARIO.keys()}
                elif campo == "grupos_usuarios":
                    config[campo] = SISTEMA_CONFIG_DEFAULT.get("grupos_usuarios", {})
                else:
                    config[campo] = SISTEMA_CONFIG_DEFAULT.get(campo, True)
        
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        config = SISTEMA_CONFIG_DEFAULT.copy()
        config['grupos_pvd'] = GRUPOS_PVD_CONFIG
        
        # Inicializar secciones activas
        from config import SECCIONES_USUARIO
        config['secciones_activas'] = {seccion: True for seccion in SECCIONES_USUARIO.keys()}
        
        os.makedirs('data', exist_ok=True)
        with open('data/config_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return config

def guardar_config_sistema(config):
    """Guarda la configuración del sistema"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/config_sistema.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/config_sistema.json', 'data_backup/config_sistema.json')
        return True
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False

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
        
        campos_requeridos = ['agentes_activos', 'maximo_simultaneo', 'duracion_corta', 
                           'duracion_larga', 'sonido_activado', 'auto_finalizar_pausa',
                           'notificacion_automatica', 'intervalo_temporizador',
                           'max_reintentos_notificacion']
        
        for campo in campos_requeridos:
            if campo not in config:
                if campo == 'auto_finalizar_pausa':
                    config[campo] = True
                elif campo == 'notificacion_automatica':
                    config[campo] = True
                elif campo == 'intervalo_temporizador':
                    config[campo] = 60
                elif campo == 'max_reintentos_notificacion':
                    config[campo] = 2
                else:
                    config[campo] = PVD_CONFIG_DEFAULT.get(campo)
        
        if 'auto_refresh_interval' not in config:
            config['auto_refresh_interval'] = 60
        
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        return PVD_CONFIG_DEFAULT.copy()

def guardar_config_pvd(config):
    """Guarda la configuración PVD"""
    try:
        from config import PVD_CONFIG_DEFAULT
        campos_requeridos = ['agentes_activos', 'maximo_simultaneo', 'duracion_corta', 
                           'duracion_larga', 'sonido_activado', 'auto_finalizar_pausa',
                           'notificacion_automatica', 'intervalo_temporizador',
                           'max_reintentos_notificacion']
        
        for campo in campos_requeridos:
            if campo not in config:
                if campo == 'auto_finalizar_pausa':
                    config[campo] = True
                elif campo == 'notificacion_automatica':
                    config[campo] = True
                elif campo == 'intervalo_temporizador':
                    config[campo] = 60
                elif campo == 'max_reintentos_notificacion':
                    config[campo] = 2
                else:
                    config[campo] = PVD_CONFIG_DEFAULT.get(campo)
        
        if 'auto_refresh_interval' not in config:
            config['auto_refresh_interval'] = 60
        
        os.makedirs('data', exist_ok=True)
        with open('data/config_pvd.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/config_pvd.json', 'data_backup/config_pvd.json')
        return True
    except Exception as e:
        print(f"Error guardando configuración PVD: {e}")
        return False

def cargar_cola_pvd():
    """Carga la cola actual de PVD"""
    try:
        with open('data/cola_pvd.json', 'r', encoding='utf-8') as f:
            cola = json.load(f)
        
        # Asegurar que todas las pausas tienen campo 'grupo'
        for pausa in cola:
            if 'grupo' not in pausa:
                pausa['grupo'] = 'basico'
            if 'notificado' not in pausa:
                pausa['notificado'] = False
            if 'confirmado' not in pausa:
                pausa['confirmado'] = False
        
        return cola
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_cola_pvd(cola):
    """Guarda la cola PVD"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/cola_pvd.json', 'w', encoding='utf-8') as f:
            json.dump(cola, f, indent=4, ensure_ascii=False)
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/cola_pvd.json', 'data_backup/cola_pvd.json')
        return True
    except Exception as e:
        print(f"Error guardando cola PVD: {e}")
        return False

def cargar_super_users():
    """Carga la configuración de super usuarios"""
    try:
        with open('data/super_users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        from config import SUPER_USER_CONFIG_DEFAULT
        config = SUPER_USER_CONFIG_DEFAULT.copy()
        
        os.makedirs('data', exist_ok=True)
        with open('data/super_users.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return config

def guardar_super_users(config):
    """Guarda la configuración de super usuarios"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/super_users.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/super_users.json', 'data_backup/super_users.json')
        return True
    except Exception as e:
        print(f"Error guardando super users: {e}")
        return False

def cargar_registro_llamadas():
    """Carga el registro histórico de llamadas"""
    try:
        with open('data/registro_llamadas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Estructura: {fecha: {agent_id: {llamadas: X, ventas: Y}}}
        registro = {}
        os.makedirs('data', exist_ok=True)
        with open('data/registro_llamadas.json', 'w', encoding='utf-8') as f:
            json.dump(registro, f, indent=4, ensure_ascii=False)
        return registro

def guardar_registro_llamadas(registro):
    """Guarda el registro de llamadas"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/registro_llamadas.json', 'w', encoding='utf-8') as f:
            json.dump(registro, f, indent=4, ensure_ascii=False)
        
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/registro_llamadas.json', 'data_backup/registro_llamadas.json')
        return True
    except Exception as e:
        print(f"Error guardando registro llamadas: {e}")
        return False

# database.py (AGREGAR AL FINAL)

def crear_tabla_monitorizaciones():
    """Crea la tabla de monitorizaciones si no existe"""
    try:
        # Archivo de monitorizaciones
        monitorizaciones_path = 'data/monitorizaciones.json'
        if not os.path.exists(monitorizaciones_path):
            with open(monitorizaciones_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error creando tabla monitorizaciones: {e}")
        return False

def cargar_monitorizaciones():
    """Carga todas las monitorizaciones desde el archivo"""
    try:
        monitorizaciones_path = 'data/monitorizaciones.json'
        if not os.path.exists(monitorizaciones_path):
            crear_tabla_monitorizaciones()
            return {}
        
        with open(monitorizaciones_path, 'r', encoding='utf-8') as f:
            monitorizaciones = json.load(f)
        return monitorizaciones
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_monitorizaciones(monitorizaciones):
    """Guarda las monitorizaciones en el archivo"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/monitorizaciones.json', 'w', encoding='utf-8') as f:
            json.dump(monitorizaciones, f, indent=4, ensure_ascii=False)
        
        # Backup
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy('data/monitorizaciones.json', 'data_backup/monitorizaciones.json')
        return True
    except Exception as e:
        print(f"Error guardando monitorizaciones: {e}")
        return False

def agregar_monitorizacion(monitorizacion_data):
    """Agrega una nueva monitorización al archivo"""
    try:
        monitorizaciones = cargar_monitorizaciones()
        
        # Generar ID único
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        id_empleado = str(monitorizacion_data.get('id_empleado', ''))
        monitorizacion_id = f"MON_{timestamp}_{id_empleado}"
        
        # Agregar metadata
        monitorizacion_data['id_monitorizacion'] = monitorizacion_id
        monitorizacion_data['created_at'] = datetime.now().isoformat()
        
        # Guardar
        monitorizaciones[monitorizacion_id] = monitorizacion_data
        guardar_monitorizaciones(monitorizaciones)
        
        return monitorizacion_id
    except Exception as e:
        print(f"Error agregando monitorización: {e}")
        return None

def obtener_monitorizaciones_por_empleado(id_empleado):
    """Obtiene todas las monitorizaciones de un empleado"""
    try:
        monitorizaciones = cargar_monitorizaciones()
        resultado = []
        
        for mon_id, mon_data in monitorizaciones.items():
            if str(mon_data.get('id_empleado')) == str(id_empleado):
                resultado.append(mon_data)
        
        # Ordenar por fecha descendente
        resultado.sort(key=lambda x: x.get('fecha_monitorizacion', ''), reverse=True)
        return resultado
    except Exception as e:
        print(f"Error obteniendo monitorizaciones: {e}")
        return []

def obtener_ultima_monitorizacion_empleado(id_empleado):
    """Obtiene la última monitorización de un empleado"""
    monitorizaciones = obtener_monitorizaciones_por_empleado(id_empleado)
    if monitorizaciones:
        return monitorizaciones[0]
    return None

def obtener_agentes_pendientes_monitorizar():
    """Obtiene agentes que necesitan monitorización (más de 10 días sin monitorizar)"""
    try:
        from datetime import datetime, timedelta
        
        super_users_config = cargar_super_users()
        agentes = super_users_config.get("agentes", {})
        
        agentes_pendientes = []
        hoy = datetime.now().date()
        
        for agent_id, agente_info in agentes.items():
            if not agente_info.get('activo', True):
                continue
            
            # Obtener última monitorización
            ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
            
            if not ultima_mon:
                # Nunca monitorizado
                agentes_pendientes.append({
                    'id': agent_id,
                    'nombre': agente_info.get('nombre', agent_id),
                    'grupo': agente_info.get('grupo', 'Sin grupo'),
                    'ultima_fecha': None,
                    'dias_sin': float('inf'),
                    'estado': 'NUNCA MONITORIZADO'
                })
            else:
                fecha_ultima = datetime.strptime(ultima_mon.get('fecha_monitorizacion'), '%Y-%m-%d').date()
                dias_sin = (hoy - fecha_ultima).days
                
                if dias_sin >= 10:
                    agentes_pendientes.append({
                        'id': agent_id,
                        'nombre': agente_info.get('nombre', agent_id),
                        'grupo': agente_info.get('grupo', 'Sin grupo'),
                        'ultima_fecha': fecha_ultima.strftime('%d/%m/%Y'),
                        'dias_sin': dias_sin,
                        'estado': f'{dias_sin} DÍAS SIN'
                    })
        
        # Ordenar por prioridad
        agentes_pendientes.sort(key=lambda x: (
            x['ultima_fecha'] is None,
            -x['dias_sin'] if x['dias_sin'] != float('inf') else float('inf')
        ), reverse=True)
        
        return agentes_pendientes
    except Exception as e:
        print(f"Error obteniendo agentes pendientes: {e}")
        return []