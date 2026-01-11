import os
import shutil
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from config import (
    PLANES_GAS_ESTRUCTURA, PMG_COSTE, PMG_IVA,
    USUARIOS_DEFAULT, PVD_CONFIG_DEFAULT,
    SISTEMA_CONFIG_DEFAULT, GRUPOS_PVD_CONFIG,
    SUPER_USER_CONFIG_DEFAULT
)
from utils import inicializar_directorios

MONITORIZACIONES_FILE = 'data/monitorizaciones.json'

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
            "cola_pvd.json": json.dumps([], indent=4),  # Mantener para compatibilidad
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
    
    # Inicializar archivo de alertas SMS
    inicializar_archivo_alertas_sms()

def inicializar_archivo_alertas_sms():
    """Inicializa el archivo de alertas SMS si no existe"""
    try:
        archivo = 'data/alertas_sms.json'
        
        if not os.path.exists(archivo):
            os.makedirs('data', exist_ok=True)
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            print("✅ Archivo de alertas SMS creado")
        
        return True
    except Exception as e:
        print(f"Error inicializando archivo de alertas SMS: {e}")
        return False

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

# ==============================================
# FUNCIONES DE COLAS PVD POR GRUPOS (NUEVO SISTEMA)
# ==============================================

def cargar_cola_pvd_grupo(grupo_id):
    """Carga la cola PVD específica de un grupo"""
    try:
        file_path = Path(f"data/pvd_cola_{grupo_id}.json")
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                cola = json.load(f)
            
            # Limpiar pausas completadas de días anteriores
            cola_limpia = _limpiar_cola_antigua(cola)
            if len(cola_limpia) < len(cola):
                guardar_cola_pvd_grupo(grupo_id, cola_limpia)
                return cola_limpia
            
            return cola
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    # Si no existe, crear estructura vacía
    return []

def guardar_cola_pvd_grupo(grupo_id, cola_data):
    """Guarda la cola PVD específica de un grupo"""
    try:
        os.makedirs('data', exist_ok=True)
        file_path = Path(f"data/pvd_cola_{grupo_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cola_data, f, indent=4, ensure_ascii=False)
        
        # Backup
        backup_path = Path(f"data_backup/pvd_cola_{grupo_id}.json")
        os.makedirs('data_backup', exist_ok=True)
        shutil.copy(file_path, backup_path)
        return True
    except Exception as e:
        print(f"Error guardando cola PVD grupo {grupo_id}: {e}")
        return False

def obtener_todas_colas_pvd():
    """Obtiene todas las colas PVD de todos los grupos"""
    colas = {}
    data_dir = Path("data")
    
    if data_dir.exists():
        for file_path in data_dir.glob("pvd_cola_*.json"):
            grupo_id = file_path.stem.replace("pvd_cola_", "")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    colas[grupo_id] = json.load(f)
            except:
                colas[grupo_id] = []
    
    # Si no hay colas por grupo, usar la cola consolidada (compatibilidad)
    if not colas:
        cola_consolidada = cargar_cola_pvd()
        if cola_consolidada:
            colas['basico'] = cola_consolidada
    
    return colas

def consolidar_colas_pvd():
    """Consolida todas las colas en un solo archivo (para compatibilidad)"""
    todas_colas = obtener_todas_colas_pvd()
    cola_consolidada = []
    
    for grupo_id, cola_grupo in todas_colas.items():
        for pausa in cola_grupo:
            pausa_con_grupo = pausa.copy()
            pausa_con_grupo['grupo'] = grupo_id
            cola_consolidada.append(pausa_con_grupo)
    
    return cola_consolidada

def _limpiar_cola_antigua(cola_data):
    """Limpia pausas completadas de días anteriores"""
    from datetime import datetime, timedelta
    
    hoy = datetime.now().date()
    cola_limpia = []
    
    for pausa in cola_data:
        estado = pausa.get('estado', '')
        
        # Mantener pausas en curso o esperando
        if estado in ['EN_CURSO', 'ESPERANDO']:
            cola_limpia.append(pausa)
            continue
        
        # Para pausas completadas o canceladas, verificar fecha
        if estado in ['COMPLETADO', 'CANCELADO']:
            try:
                fecha_key = 'timestamp_fin' if estado == 'COMPLETADO' else 'timestamp_solicitud'
                if fecha_key in pausa:
                    fecha_pausa = datetime.fromisoformat(pausa[fecha_key]).date()
                    # Mantener solo si es de hoy
                    if fecha_pausa == hoy:
                        cola_limpia.append(pausa)
            except:
                # Si hay error al parsear fecha, mantener por seguridad
                cola_limpia.append(pausa)
                continue
    
    return cola_limpia

def limpiar_todas_colas_antiguas():
    """Limpia todas las colas PVD de datos antiguos"""
    try:
        todas_colas = obtener_todas_colas_pvd()
        for grupo_id, cola_grupo in todas_colas.items():
            cola_limpia = _limpiar_cola_antigua(cola_grupo)
            if len(cola_limpia) < len(cola_grupo):
                guardar_cola_pvd_grupo(grupo_id, cola_limpia)
                print(f"✅ Cola {grupo_id}: {len(cola_grupo) - len(cola_limpia)} pausas antiguas limpiadas")
        return True
    except Exception as e:
        print(f"Error limpiando colas antiguas: {e}")
        return False

# Función de compatibilidad (mantener para código existente)
def cargar_cola_pvd():
    """Carga la cola actual de PVD (compatibilidad)"""
    # Usar el sistema de colas por grupos
    colas_por_grupo = obtener_todas_colas_pvd()
    
    # Consolidar todas las colas
    cola_consolidada = []
    for grupo_id, cola_grupo in colas_por_grupo.items():
        for pausa in cola_grupo:
            pausa_con_grupo = pausa.copy()
            pausa_con_grupo['grupo'] = grupo_id
            cola_consolidada.append(pausa_con_grupo)
    
    return cola_consolidada

def guardar_cola_pvd(cola):
    """Guarda la cola PVD (compatibilidad)"""
    # Separar por grupos y guardar en archivos separados
    try:
        colas_por_grupo = {}
        
        for pausa in cola:
            grupo = pausa.get('grupo', 'basico')
            if grupo not in colas_por_grupo:
                colas_por_grupo[grupo] = []
            colas_por_grupo[grupo].append(pausa)
        
        # Guardar cada grupo
        for grupo_id, cola_grupo in colas_por_grupo.items():
            guardar_cola_pvd_grupo(grupo_id, cola_grupo)
        
        return True
    except Exception as e:
        print(f"Error guardando cola PVD (compatibilidad): {e}")
        return False

# ==============================================
# FUNCIONES DE SUPER USUARIOS
# ==============================================

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

# ==============================================
# FUNCIONES DE REGISTRO DE LLAMADAS
# ==============================================

def cargar_registro_llamadas():
    """Carga el registro histórico de llamadas"""
    try:
        with open('data/registro_llamadas.json', 'r', encoding='utf-8') as f:
            registro = json.load(f)
        
        # MIGRACIÓN: Asegurar que los registros antiguos tengan ambos campos
        for fecha_str, datos_dia in registro.items():
            for agent_id, datos_agente in datos_dia.items():
                if 'llamadas' in datos_agente and 'llamadas_totales' not in datos_agente:
                    # Los datos antiguos solo tienen "llamadas" (que son las >15min)
                    datos_agente['llamadas_totales'] = 0  # Inicializar totales
                    datos_agente['llamadas_15min'] = datos_agente.pop('llamadas')  # Renombrar
                elif 'llamadas_15min' not in datos_agente:
                    datos_agente['llamadas_15min'] = datos_agente.get('llamadas', 0)
                    datos_agente['llamadas_totales'] = datos_agente.get('llamadas_totales', 0)
        
        return registro
    except (FileNotFoundError, json.JSONDecodeError):
        # Estructura: {fecha: {agent_id: {llamadas_totales: X, llamadas_15min: Y, ventas: Z}}}
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

# ==============================================
# FUNCIONES DE MONITORIZACIONES
# ==============================================

def crear_tabla_monitorizaciones():
    """Crea la tabla de monitorizaciones si no existe"""
    try:
        if not os.path.exists(MONITORIZACIONES_FILE):
            os.makedirs(os.path.dirname(MONITORIZACIONES_FILE), exist_ok=True)
            with open(MONITORIZACIONES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error creando tabla monitorizaciones: {e}")
        return False

def cargar_monitorizaciones():
    """Carga todas las monitorizaciones desde el archivo JSON"""
    try:
        crear_tabla_monitorizaciones()
        
        with open(MONITORIZACIONES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir de dict a lista si es necesario
        if isinstance(data, dict):
            # Estructura: {id: monitorizacion_data}
            return data
        elif isinstance(data, list):
            # Convertir lista a dict
            monitorizaciones_dict = {}
            for item in data:
                mon_id = item.get('id_monitorizacion')
                if mon_id:
                    monitorizaciones_dict[mon_id] = item
                else:
                    # Generar ID si no existe
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    mon_id = f"MON_{timestamp}_{item.get('id_empleado', 'UNK')}"
                    item['id_monitorizacion'] = mon_id
                    monitorizaciones_dict[mon_id] = item
            return monitorizaciones_dict
        else:
            return {}
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error cargando monitorizaciones: {e}")
        return {}

def guardar_monitorizaciones(monitorizaciones):
    """Guarda las monitorizaciones en el archivo JSON"""
    try:
        os.makedirs(os.path.dirname(MONITORIZACIONES_FILE), exist_ok=True)
        with open(MONITORIZACIONES_FILE, 'w', encoding='utf-8') as f:
            json.dump(monitorizaciones, f, indent=4, ensure_ascii=False)
        
        # Backup
        backup_file = f"data_backup/{os.path.basename(MONITORIZACIONES_FILE)}"
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(monitorizaciones, f, indent=4, ensure_ascii=False)
            
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
                fecha_str = ultima_mon.get('fecha_monitorizacion')
                if fecha_str:
                    try:
                        fecha_ultima = datetime.strptime(fecha_str, '%Y-%m-%d').date()
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
                    except:
                        # Error al parsear fecha
                        agentes_pendientes.append({
                            'id': agent_id,
                            'nombre': agente_info.get('nombre', agent_id),
                            'grupo': agente_info.get('grupo', 'Sin grupo'),
                            'ultima_fecha': 'Fecha inválida',
                            'dias_sin': float('inf'),
                            'estado': 'ERROR FECHA'
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

def eliminar_monitorizaciones_empleado(empleado_id: str, keep_last: bool = False) -> int:
    """Elimina monitorizaciones de un empleado"""
    try:
        monitorizaciones = cargar_monitorizaciones()
        
        if not monitorizaciones:
            return 0
        
        # Filtrar monitorizaciones del empleado
        monitorizaciones_empleado = {}
        otras_monitorizaciones = {}
        
        for mon_id, mon_data in monitorizaciones.items():
            if str(mon_data.get('id_empleado')) == str(empleado_id):
                monitorizaciones_empleado[mon_id] = mon_data
            else:
                otras_monitorizaciones[mon_id] = mon_data
        
        if not monitorizaciones_empleado:
            return 0
        
        if keep_last:
            # Encontrar la última monitorización por fecha
            monitorizaciones_list = list(monitorizaciones_empleado.values())
            monitorizaciones_list.sort(
                key=lambda x: x.get('fecha_monitorizacion', ''),
                reverse=True
            )
            
            if monitorizaciones_list:
                # Mantener solo la última
                ultima_id = monitorizaciones_list[0].get('id_monitorizacion')
                if ultima_id:
                    # Eliminar todas excepto la última
                    for mon_id in list(monitorizaciones_empleado.keys()):
                        if mon_id != ultima_id:
                            del monitorizaciones_empleado[mon_id]
                    
                    # Combinar de nuevo
                    nuevas_monitorizaciones = {**otras_monitorizaciones, **monitorizaciones_empleado}
                else:
                    # No se puede identificar la última, eliminar todas
                    nuevas_monitorizaciones = otras_monitorizaciones
            else:
                nuevas_monitorizaciones = otras_monitorizaciones
        else:
            # Eliminar todas
            nuevas_monitorizaciones = otras_monitorizaciones
        
        # Calcular cuántas se eliminaron
        eliminadas = len(monitorizaciones) - len(nuevas_monitorizaciones)
        
        if eliminadas > 0:
            guardar_monitorizaciones(nuevas_monitorizaciones)
        
        return eliminadas
        
    except Exception as e:
        print(f"Error eliminando monitorizaciones: {e}")
        return 0

def actualizar_monitorizacion(monitorizacion_id, nuevos_datos):
    """Actualiza una monitorización existente"""
    try:
        monitorizaciones = cargar_monitorizaciones()
        
        if monitorizacion_id not in monitorizaciones:
            return False
        
        # Preservar el ID y metadata original
        nuevos_datos['id_monitorizacion'] = monitorizacion_id
        if 'created_at' not in nuevos_datos:
            nuevos_datos['created_at'] = monitorizaciones[monitorizacion_id].get('created_at')
        
        nuevos_datos['updated_at'] = datetime.now().isoformat()
        
        # Actualizar
        monitorizaciones[monitorizacion_id] = nuevos_datos
        guardar_monitorizaciones(monitorizaciones)
        
        return True
    except Exception as e:
        print(f"Error actualizando monitorización: {e}")
        return False

def obtener_monitorizacion_por_id(monitorizacion_id):
    """Obtiene una monitorización específica por su ID"""
    try:
        monitorizaciones = cargar_monitorizaciones()
        return monitorizaciones.get(monitorizacion_id)
    except Exception as e:
        print(f"Error obteniendo monitorización por ID: {e}")
        return None

# ==============================================
# FUNCIONES DE ESTADÍSTICAS Y MÉTRICAS
# ==============================================

def obtener_estadisticas_llamadas_diarias(fecha_inicio=None, fecha_fin=None):
    """
    Obtiene estadísticas de llamadas diarias para un período específico
    
    Args:
        fecha_inicio: Fecha de inicio (datetime.date)
        fecha_fin: Fecha de fin (datetime.date)
    
    Returns:
        dict: Estadísticas de llamadas por día
    """
    try:
        from datetime import datetime, date, timedelta
        
        # Si no se especifican fechas, usar últimos 30 días
        if fecha_inicio is None:
            fecha_fin = date.today()
            fecha_inicio = fecha_fin - timedelta(days=30)
        elif fecha_fin is None:
            fecha_fin = date.today()
        
        # Cargar registro de llamadas
        registro_llamadas = cargar_registro_llamadas()
        
        # Preparar estructura para estadísticas
        estadisticas = {
            'fechas': [],
            'llamadas_totales': [],
            'ventas_totales': [],
            'agentes_activos': [],
            'media_llamadas_por_agente': [],
            'media_ventas_por_agente': []
        }
        
        # Procesar cada día en el rango
        current_date = fecha_inicio
        while current_date <= fecha_fin:
            fecha_str = current_date.strftime('%Y-%m-%d')
            
            if fecha_str in registro_llamadas:
                datos_dia = registro_llamadas[fecha_str]
                
                # Calcular totales del día
                llamadas_dia = sum(datos.get('llamadas', 0) for datos in datos_dia.values())
                ventas_dia = sum(datos.get('ventas', 0) for datos in datos_dia.values())
                agentes_dia = len(datos_dia)
                
                # Calcular medias
                media_llamadas = llamadas_dia / agentes_dia if agentes_dia > 0 else 0
                media_ventas = ventas_dia / agentes_dia if agentes_dia > 0 else 0
                
                # Agregar a estadísticas
                estadisticas['fechas'].append(fecha_str)
                estadisticas['llamadas_totales'].append(llamadas_dia)
                estadisticas['ventas_totales'].append(ventas_dia)
                estadisticas['agentes_activos'].append(agentes_dia)
                estadisticas['media_llamadas_por_agente'].append(round(media_llamadas, 2))
                estadisticas['media_ventas_por_agente'].append(round(media_ventas, 2))
            else:
                # Día sin datos
                estadisticas['fechas'].append(fecha_str)
                estadisticas['llamadas_totales'].append(0)
                estadisticas['ventas_totales'].append(0)
                estadisticas['agentes_activos'].append(0)
                estadisticas['media_llamadas_por_agente'].append(0)
                estadisticas['media_ventas_por_agente'].append(0)
            
            # Siguiente día
            current_date += timedelta(days=1)
        
        # Calcular estadísticas globales del período
        total_llamadas = sum(estadisticas['llamadas_totales'])
        total_ventas = sum(estadisticas['ventas_totales'])
        dias_con_datos = len([x for x in estadisticas['llamadas_totales'] if x > 0])
        total_dias = len(estadisticas['fechas'])
        
        # Agregar resumen
        estadisticas['resumen'] = {
            'periodo': f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
            'total_llamadas': total_llamadas,
            'total_ventas': total_ventas,
            'dias_con_datos': dias_con_datos,
            'total_dias': total_dias,
            'media_llamadas_diaria': round(total_llamadas / dias_con_datos, 2) if dias_con_datos > 0 else 0,
            'media_ventas_diaria': round(total_ventas / dias_con_datos, 2) if dias_con_datos > 0 else 0,
            'porcentaje_dias_con_datos': round((dias_con_datos / total_dias) * 100, 1)
        }
        
        return estadisticas
        
    except Exception as e:
        print(f"Error obteniendo estadísticas de llamadas diarias: {e}")
        # Retornar estructura vacía en caso de error
        return {
            'fechas': [],
            'llamadas_totales': [],
            'ventas_totales': [],
            'agentes_activos': [],
            'media_llamadas_por_agente': [],
            'media_ventas_por_agente': [],
            'resumen': {
                'periodo': '',
                'total_llamadas': 0,
                'total_ventas': 0,
                'dias_con_datos': 0,
                'total_dias': 0,
                'media_llamadas_diaria': 0,
                'media_ventas_diaria': 0,
                'porcentaje_dias_con_datos': 0
            }
        }

def obtener_metricas_agentes_por_periodo(fecha_inicio, fecha_fin, super_users_config=None):
    """
    Obtiene métricas de agentes para un período específico
    
    Args:
        fecha_inicio: Fecha de inicio (datetime.date)
        fecha_fin: Fecha de fin (datetime.date)
        super_users_config: Configuración de super usuarios (opcional)
    
    Returns:
        list: Lista de diccionarios con métricas de cada agente
    """
    try:
        from datetime import datetime
        
        if super_users_config is None:
            super_users_config = cargar_super_users()
        
        agentes = super_users_config.get("agentes", {})
        registro_llamadas = cargar_registro_llamadas()
        configuracion = super_users_config.get("configuracion", {})
        
        metricas_agentes = []
        
        for agent_id, info in agentes.items():
            if not info.get('activo', True):
                continue
            
            nombre = info.get('nombre', agent_id)
            grupo = info.get('grupo', 'Sin grupo')
            supervisor = info.get('supervisor', 'Sin asignar')
            
            # Calcular totales del periodo
            total_llamadas = 0
            total_ventas = 0
            dias_con_datos = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        llamadas_dia = datos_dia[agent_id].get("llamadas", 0)
                        ventas_dia = datos_dia[agent_id].get("ventas", 0)
                        
                        total_llamadas += llamadas_dia
                        total_ventas += ventas_dia
                        
                        if llamadas_dia > 0 or ventas_dia > 0:
                            dias_con_datos += 1
            
            # Calcular métricas
            target_llamadas = configuracion.get("target_llamadas", 50)
            target_ventas = configuracion.get("target_ventas", 10)
            
            cumplimiento_llamadas = (total_llamadas / target_llamadas * 100) if target_llamadas > 0 else 0
            cumplimiento_ventas = (total_ventas / target_ventas * 100) if target_ventas > 0 else 0
            
            # Calcular ratio de conversión
            ratio_conversion = (total_ventas / total_llamadas * 100) if total_llamadas > 0 else 0
            
            # Calcular llamadas diarias promedio
            total_dias = (fecha_fin - fecha_inicio).days + 1
            llamadas_diarias_promedio = total_llamadas / dias_con_datos if dias_con_datos > 0 else 0
            
            metricas_agentes.append({
                'id': agent_id,
                'nombre': nombre,
                'grupo': grupo,
                'supervisor': supervisor,
                'total_llamadas': total_llamadas,
                'total_ventas': total_ventas,
                'dias_con_datos': dias_con_datos,
                'total_dias_periodo': total_dias,
                'cumplimiento_llamadas': round(cumplimiento_llamadas, 1),
                'cumplimiento_ventas': round(cumplimiento_ventas, 1),
                'ratio_conversion': round(ratio_conversion, 1),
                'llamadas_diarias_promedio': round(llamadas_diarias_promedio, 2),
                'activo': info.get('activo', True)
            })
        
        return metricas_agentes
        
    except Exception as e:
        print(f"Error obteniendo métricas de agentes: {e}")
        return []

def obtener_agentes_por_supervisor(supervisor_id):
    """
    Obtiene los agentes asignados a un supervisor específico
    
    Args:
        supervisor_id: ID del supervisor
    
    Returns:
        dict: Diccionario con agentes del supervisor
    """
    try:
        super_users_config = cargar_super_users()
        agentes = super_users_config.get("agentes", {})
        
        agentes_supervisor = {}
        for agent_id, info in agentes.items():
            if info.get('supervisor') == supervisor_id:
                agentes_supervisor[agent_id] = info
        
        return agentes_supervisor
    except Exception as e:
        print(f"Error obteniendo agentes por supervisor: {e}")
        return {}

def obtener_resumen_periodo(fecha_inicio, fecha_fin):
    """
    Obtiene un resumen de métricas para un período
    
    Args:
        fecha_inicio: Fecha de inicio (datetime.date)
        fecha_fin: Fecha de fin (datetime.date)
    
    Returns:
        dict: Resumen de métricas del período
    """
    try:
        from datetime import datetime
        
        super_users_config = cargar_super_users()
        registro_llamadas = cargar_registro_llamadas()
        
        total_llamadas = 0
        total_ventas = 0
        total_agentes_activos = 0
        dias_con_datos = 0
        
        # Contar agentes activos
        agentes = super_users_config.get("agentes", {})
        total_agentes_activos = sum(1 for a in agentes.values() if a.get('activo', True))
        
        # Calcular totales del período
        for fecha_str, datos_dia in registro_llamadas.items():
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_inicio <= fecha <= fecha_fin:
                llamadas_dia = sum(datos.get('llamadas', 0) for datos in datos_dia.values())
                ventas_dia = sum(datos.get('ventas', 0) for datos in datos_dia.values())
                
                total_llamadas += llamadas_dia
                total_ventas += ventas_dia
                
                if llamadas_dia > 0 or ventas_dia > 0:
                    dias_con_datos += 1
        
        total_dias = (fecha_fin - fecha_inicio).days + 1
        
        # Calcular medias
        media_llamadas_diaria = total_llamadas / dias_con_datos if dias_con_datos > 0 else 0
        media_ventas_diaria = total_ventas / dias_con_datos if dias_con_datos > 0 else 0
        media_llamadas_por_agente = total_llamadas / total_agentes_activos if total_agentes_activos > 0 else 0
        media_ventas_por_agente = total_ventas / total_agentes_activos if total_agentes_activos > 0 else 0
        
        # Calcular ratio de conversión
        ratio_conversion = (total_ventas / total_llamadas * 100) if total_llamadas > 0 else 0
        
        return {
            'periodo': f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
            'total_dias': total_dias,
            'dias_con_datos': dias_con_datos,
            'total_llamadas': total_llamadas,
            'total_ventas': total_ventas,
            'total_agentes_activos': total_agentes_activos,
            'media_llamadas_diaria': round(media_llamadas_diaria, 2),
            'media_ventas_diaria': round(media_ventas_diaria, 2),
            'media_llamadas_por_agente': round(media_llamadas_por_agente, 2),
            'media_ventas_por_agente': round(media_ventas_por_agente, 2),
            'ratio_conversion': round(ratio_conversion, 2),
            'porcentaje_dias_con_datos': round((dias_con_datos / total_dias) * 100, 1) if total_dias > 0 else 0
        }
        
    except Exception as e:
        print(f"Error obteniendo resumen del período: {e}")
        return {}

# ==============================================
# FUNCIONES DE ALERTAS SMS
# ==============================================

def cargar_alertas_sms():
    """Carga las alertas SMS pendientes"""
    try:
        archivo = 'data/alertas_sms.json'
        
        # Crear archivo si no existe
        if not os.path.exists(archivo):
            os.makedirs('data', exist_ok=True)
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
            return {}
        
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
            if contenido:
                return json.loads(contenido)
            else:
                return {}
                
    except Exception as e:
        print(f"Error cargando alertas SMS: {e}")
        return {}

def guardar_alertas_sms(alertas):
    """Guarda las alertas SMS"""
    try:
        archivo = 'data/alertas_sms.json'
        os.makedirs('data', exist_ok=True)
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(alertas, f, indent=4, ensure_ascii=False)
        
        # Backup
        backup_file = 'data_backup/alertas_sms.json'
        os.makedirs('data_backup', exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(alertas, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error guardando alertas SMS: {e}")
        return False

def agregar_alerta_sms(alerta_data):
    """Agrega una nueva alerta SMS"""
    try:
        alertas = cargar_alertas_sms()
        
        # Verificar si ya existe
        alerta_id = alerta_data.get('id')
        if alerta_id and alerta_id in alertas:
            # Actualizar si ya existe
            alertas[alerta_id].update(alerta_data)
        else:
            # Crear ID si no existe
            if not alerta_id:
                import hashlib
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                data_str = f"{alerta_data.get('agente','')}_{alerta_data.get('fecha','')}_{timestamp}"
                alerta_id = f"sms_{hashlib.md5(data_str.encode()).hexdigest()[:10]}"
                alerta_data['id'] = alerta_id
            
            # Agregar timestamp si no existe
            if 'timestamp' not in alerta_data:
                alerta_data['timestamp'] = datetime.now().isoformat()
            
            alertas[alerta_id] = alerta_data
        
        guardar_alertas_sms(alertas)
        return alerta_id
    except Exception as e:
        print(f"Error agregando alerta SMS: {e}")
        return None

def agregar_varias_alertas_sms(lista_alertas):
    """Agrega múltiples alertas SMS de una vez - VERSIÓN MEJORADA"""
    try:
        alertas = cargar_alertas_sms()
        nuevas = 0
        actualizadas = 0
        
        for alerta_data in lista_alertas:
            alerta_id = alerta_data.get('id')
            
            if alerta_id:
                if alerta_id in alertas:
                    # Actualizar si ya existe (preservar datos importantes)
                    alerta_existente = alertas[alerta_id]
                    
                    # Mantener confirmaciones previas si las hay
                    if alerta_existente.get('estado') == 'completado' and alerta_data.get('estado') != 'completado':
                        # No sobrescribir alertas ya completadas
                        continue
                    
                    # Combinar datos
                    alerta_data['timestamp_creacion'] = alerta_existente.get('timestamp_creacion', alerta_data.get('timestamp_revision'))
                    if 'confirmado_por' in alerta_existente:
                        alerta_data['confirmado_por'] = alerta_existente['confirmado_por']
                    if 'timestamp_confirmacion' in alerta_existente:
                        alerta_data['timestamp_confirmacion'] = alerta_existente['timestamp_confirmacion']
                    
                    alertas[alerta_id] = alerta_data
                    actualizadas += 1
                else:
                    # Agregar timestamp de creación
                    if 'timestamp_creacion' not in alerta_data:
                        alerta_data['timestamp_creacion'] = datetime.now().isoformat()
                    
                    alertas[alerta_id] = alerta_data
                    nuevas += 1
        
        guardar_alertas_sms(alertas)
        
        if nuevas > 0 or actualizadas > 0:
            print(f"✅ Alertas SMS: {nuevas} nuevas, {actualizadas} actualizadas")
        
        return nuevas + actualizadas
    except Exception as e:
        print(f"❌ Error agregando múltiples alertas SMS: {e}")
        return 0

def procesar_alerta_sms_completada(alerta_id, ventas_finales, llamadas_totales=1, llamadas_largas=0):
    """
    Procesa una alerta SMS completada y la agrega al registro de llamadas
    
    Args:
        alerta_id: ID de la alerta
        ventas_finales: Número de ventas a contar
        llamadas_totales: Número de llamadas a agregar (default: 1)
        llamadas_largas: Número de llamadas largas a agregar (default: 0)
    
    Returns:
        bool: True si se procesó correctamente
    """
    try:
        from datetime import datetime
        
        # Cargar la alerta
        alertas = cargar_alertas_sms()
        if alerta_id not in alertas:
            print(f"❌ Alerta {alerta_id} no encontrada")
            return False
        
        alerta = alertas[alerta_id]
        
        # Verificar que no esté ya procesada
        if alerta.get('procesada_registro') == True:
            print(f"⚠️ Alerta {alerta_id} ya fue procesada anteriormente")
            return False
        
        # Cargar registro de llamadas
        registro_llamadas = cargar_registro_llamadas()
        
        # Obtener datos de la alerta
        agente = alerta.get('agente')
        fecha_str = alerta.get('fecha')
        
        if not agente or not fecha_str:
            print(f"❌ Datos incompletos en alerta {alerta_id}")
            return False
        
        # Inicializar estructuras si no existen
        if fecha_str not in registro_llamadas:
            registro_llamadas[fecha_str] = {}
        
        if agente not in registro_llamadas[fecha_str]:
            registro_llamadas[fecha_str][agente] = {
                'llamadas_totales': 0,
                'llamadas_15min': 0,
                'ventas': 0,
                'fecha': fecha_str,
                'timestamp': datetime.now().isoformat()
            }
        
        # Agregar datos al registro
        registro_llamadas[fecha_str][agente]['llamadas_totales'] += llamadas_totales
        registro_llamadas[fecha_str][agente]['llamadas_15min'] += llamadas_largas
        registro_llamadas[fecha_str][agente]['ventas'] += ventas_finales
        
        # Marcar alerta como procesada
        alerta['procesada_registro'] = True
        alerta['ventas_registradas'] = ventas_finales
        alerta['llamadas_registradas'] = llamadas_totales
        alerta['llamadas_largas_registradas'] = llamadas_largas
        alerta['timestamp_procesamiento'] = datetime.now().isoformat()
        
        # Actualizar estado si aún no estaba completado
        if alerta.get('estado') != 'completado':
            alerta['estado'] = 'completado'
        
        # Guardar cambios
        guardar_alertas_sms(alertas)
        guardar_registro_llamadas(registro_llamadas)
        
        print(f"✅ Alerta {alerta_id} procesada: {ventas_finales} ventas registradas")
        return True
        
    except Exception as e:
        print(f"❌ Error procesando alerta SMS: {e}")
        return False

def obtener_alertas_sms_para_procesar():
    """
    Obtiene alertas SMS listas para procesar en el registro
    
    Returns:
        list: Alertas con estado 'confirmado' o 'rechazado' pero no procesadas aún
    """
    try:
        alertas = cargar_alertas_sms()
        
        alertas_para_procesar = []
        
        for alerta_id, alerta_data in alertas.items():
            estado = alerta_data.get('estado')
            procesada = alerta_data.get('procesada_registro', False)
            
            # Buscar alertas que estén confirmadas o rechazadas pero no procesadas
            if estado in ['confirmado', 'rechazado'] and not procesada:
                alertas_para_procesar.append({
                    'id': alerta_id,
                    **alerta_data
                })
        
        # Ordenar por fecha
        alertas_para_procesar.sort(key=lambda x: x.get('fecha', ''))
        
        return alertas_para_procesar
        
    except Exception as e:
        print(f"❌ Error obteniendo alertas para procesar: {e}")
        return []
    
def procesar_multiples_alertas_sms(lista_alerta_ids):
    """
    Procesa múltiples alertas SMS de una vez
    
    Args:
        lista_alerta_ids: Lista de IDs de alertas a procesar
    
    Returns:
        dict: Resultados del procesamiento
    """
    try:
        resultados = {
            'total': len(lista_alerta_ids),
            'exitosos': 0,
            'fallidos': 0,
            'ventas_totales': 0,
            'llamadas_totales': 0,
            'detalles': []
        }
        
        for alerta_id in lista_alerta_ids:
            # Cargar alerta específica
            alertas = cargar_alertas_sms()
            if alerta_id not in alertas:
                resultados['detalles'].append({
                    'id': alerta_id,
                    'estado': 'error',
                    'mensaje': 'Alerta no encontrada'
                })
                resultados['fallidos'] += 1
                continue
            
            alerta = alertas[alerta_id]
            
            # Determinar parámetros según estado
            estado = alerta.get('estado')
            
            if estado == 'confirmado':
                ventas_finales = alerta.get('ventas_finales', alerta.get('ventas_pendientes', 0))
                llamadas_largas = 1 if alerta.get('duracion_segundos', 0) > 900 else 0
            elif estado == 'rechazado':
                ventas_finales = 0
                llamadas_largas = 1 if alerta.get('duracion_segundos', 0) > 900 else 0
            else:
                # No procesar alertas en otros estados
                resultados['detalles'].append({
                    'id': alerta_id,
                    'estado': 'omitido',
                    'mensaje': f'Estado no procesable: {estado}'
                })
                continue
            
            # Procesar la alerta
            exito = procesar_alerta_sms_completada(
                alerta_id=alerta_id,
                ventas_finales=ventas_finales,
                llamadas_totales=1,
                llamadas_largas=llamadas_largas
            )
            
            if exito:
                resultados['exitosos'] += 1
                resultados['ventas_totales'] += ventas_finales
                resultados['llamadas_totales'] += 1
                resultados['detalles'].append({
                    'id': alerta_id,
                    'estado': 'procesado',
                    'mensaje': f'{ventas_finales} ventas registradas'
                })
            else:
                resultados['fallidos'] += 1
                resultados['detalles'].append({
                    'id': alerta_id,
                    'estado': 'error',
                    'mensaje': 'Error en procesamiento'
                })
        
        return resultados
        
    except Exception as e:
        print(f"❌ Error procesando múltiples alertas: {e}")
        return {
            'total': len(lista_alerta_ids),
            'exitosos': 0,
            'fallidos': len(lista_alerta_ids),
            'ventas_totales': 0,
            'llamadas_totales': 0,
            'detalles': [],
            'error': str(e)
        }