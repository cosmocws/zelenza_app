import streamlit as st
import json
import os
import shutil
import uuid
from datetime import datetime

def inicializar_datos():
    """Inicializa los archivos de datos con backup automático"""
    import pandas as pd
    from modules.auth import USUARIOS_DEFAULT
    from modules.gas import PLANES_GAS_ESTRUCTURA, PMG_COSTE, PMG_IVA
    from modules.pvd import PVD_CONFIG_DEFAULT
    
    os.makedirs("data", exist_ok=True)
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # ARCHIVOS CRÍTICOS QUE QUEREMOS BACKUPEAR
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
        "cola_pvd.json": json.dumps([], indent=4)
    }
    
    for archivo, df_default in archivos_criticos.items():
        ruta_data = f"data/{archivo}"
        ruta_backup = f"data_backup/{archivo}"
        
        # Si no existe en data, intentar restaurar desde backup
        if not os.path.exists(ruta_data):
            if os.path.exists(ruta_backup):
                # RESTAURAR desde backup
                shutil.copy(ruta_backup, ruta_data)
                st.sidebar.success(f"✅ {archivo} restaurado desde backup")
            else:
                # Crear archivo por defecto
                if archivo.endswith('.json'):
                    with open(ruta_data, 'w') as f:
                        f.write(df_default)
                else:
                    df_default.to_csv(ruta_data, index=False)
        
        # SIEMPRE hacer backup de los datos actuales
        if os.path.exists(ruta_data):
            os.makedirs("data_backup", exist_ok=True)
            shutil.copy(ruta_data, ruta_backup)
    
    # BACKUP de modelos_facturas
    if os.path.exists("modelos_facturas") and os.listdir("modelos_facturas"):
        os.makedirs("data_backup", exist_ok=True)
        if os.path.exists("data_backup/modelos_facturas"):
            shutil.rmtree("data_backup/modelos_facturas")
        shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")

def cargar_configuracion_usuarios():
    """Carga la configuración de usuarios desde archivo"""
    from modules.auth import USUARIOS_DEFAULT
    
    try:
        with open('data/usuarios.json', 'r') as f:
            return json.load(f)
    except:
        # Crear archivo por defecto
        os.makedirs('data', exist_ok=True)
        with open('data/usuarios.json', 'w') as f:
            json.dump(USUARIOS_DEFAULT, f, indent=4)
        return USUARIOS_DEFAULT.copy()

def guardar_configuracion_usuarios(usuarios_config):
    """Guarda la configuración de usuarios"""
    os.makedirs('data', exist_ok=True)
    with open('data/usuarios.json', 'w') as f:
        json.dump(usuarios_config, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/usuarios.json', 'data_backup/usuarios.json')

def generar_id_unico_usuario():
    """Genera un ID único para el dispositivo del usuario"""
    # Usar session_state para almacenar el ID
    if 'device_id' not in st.session_state:
        # Crear nuevo ID único
        device_id = f"dev_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        st.session_state.device_id = device_id
    return st.session_state.device_id

def identificar_usuario_automatico():
    """Identifica automáticamente al usuario por su dispositivo"""
    device_id = generar_id_unico_usuario()
    
    # Cargar configuración de usuarios
    usuarios_config = cargar_configuracion_usuarios()
    
    # Buscar si ya existe este dispositivo
    for username, config in usuarios_config.items():
        if config.get('device_id') == device_id:
            return username, config
    
    # Si no existe, crear usuario automático
    nuevo_username = f"auto_{device_id[:8]}"
    
    if nuevo_username not in usuarios_config:
        usuarios_config[nuevo_username] = {
            "nombre": f"Usuario {device_id[:8]}",
            "device_id": device_id,
            "planes_luz": [],  # Por defecto sin planes
            "planes_gas": ["RL1", "RL2", "RL3"],  # Todos los planes de gas
            "tipo": "auto",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "password": "auto_login"
        }
        guardar_configuracion_usuarios(usuarios_config)
    
    return nuevo_username, usuarios_config[nuevo_username]

def filtrar_planes_por_usuario(df_planes, username, tipo_plan="luz"):
    """Filtra los planes según la configuración del usuario"""
    usuarios_config = cargar_configuracion_usuarios()
    
    if username not in usuarios_config:
        # Usuario automático sin config - mostrar todos por defecto
        return df_planes[df_planes['activo'] == True]
    
    config_usuario = usuarios_config[username]
    
    if tipo_plan == "luz":
        planes_permitidos = config_usuario.get("planes_luz", [])
    else:  # gas
        planes_permitidos = config_usuario.get("planes_gas", [])
    
    # Si está vacío, mostrar todos los planes activos
    if not planes_permitidos:
        return df_planes[df_planes['activo'] == True]
    
    # Si es "TODOS", mostrar todos los planes activos
    if planes_permitidos == "TODOS":
        return df_planes[df_planes['activo'] == True]
    
    # Filtrar por los planes específicos del usuario
    return df_planes[
        (df_planes['plan'].isin(planes_permitidos)) & 
        (df_planes['activo'] == True)
    ]

def enviar_notificacion_navegador(titulo, mensaje, icono="🔔"):
    """Envía una notificación del navegador al usuario"""
    notification_js = f"""
    <script>
    // Solicitar permiso para notificaciones (solo una vez)
    if ("Notification" in window) {{
        if (Notification.permission === "granted") {{
            new Notification("{titulo}", {{
                body: "{mensaje}",
                icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
            }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(permission => {{
                if (permission === "granted") {{
                    new Notification("{titulo}", {{
                        body: "{mensaje}",
                        icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
                    }});
                }}
            }});
        }}
    }}
    </script>
    """
    st.components.v1.html(notification_js, height=0)