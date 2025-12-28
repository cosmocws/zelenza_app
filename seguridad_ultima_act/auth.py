import streamlit as st
from datetime import datetime  # <-- AÑADIR ESTE IMPORT
from database import cargar_configuracion_usuarios, cargar_config_sistema
from utils import generar_id_unico_usuario, obtener_hora_madrid
from config import TIMEZONE_MADRID

def authenticate(username, password, user_type):
    """Autentica al usuario de forma segura"""
    try:
        if not username or not password:
            return False
        
        usuarios_config = cargar_configuracion_usuarios()
        
        if user_type == "user":
            if username in usuarios_config:
                usuario = usuarios_config[username]
                if "password" in usuario:
                    return password == usuario["password"]
                else:
                    try:
                        return password == st.secrets.get("credentials", {}).get("user_password", "cliente123")
                    except:
                        return password == "cliente123"
            else:
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

def identificar_usuario_automatico():
    """Identifica automáticamente al usuario por su dispositivo"""
    # Primero verificar si ya tenemos sesión
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return st.session_state.username, st.session_state.user_config
    
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
        from database import guardar_configuracion_usuarios
        guardar_configuracion_usuarios(usuarios_config)
    
    return nuevo_username, usuarios_config[nuevo_username]

def verificar_sesion():
    """Verifica si la sesión es válida"""
    # Si no está autenticado, retornar False inmediatamente
    if not st.session_state.get('authenticated', False):
        return False
    
    # Si no hay login_time, establecerlo ahora
    if 'login_time' not in st.session_state:
        st.session_state.login_time = datetime.now()
        return True
    
    config_sistema = cargar_config_sistema()
    horas_duracion = config_sistema.get("sesion_horas_duracion", 8)
    
    # Calcular horas transcurridas
    if isinstance(st.session_state.login_time, str):
        # Convertir de string a datetime si es necesario
        try:
            login_time = datetime.fromisoformat(st.session_state.login_time)
        except:
            login_time = datetime.now()
    else:
        login_time = st.session_state.login_time
    
    horas_transcurridas = (datetime.now() - login_time).total_seconds() / 3600
    
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
            from pvd_system import temporizador_pvd_mejorado
            temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
        
        st.rerun()
        return False
    
    # Mostrar tiempo restante
    tiempo_restante = horas_duracion - horas_transcurridas
    horas = int(tiempo_restante)
    minutos = int((tiempo_restante - horas) * 60)
    
    st.sidebar.info(f"⏳ Sesión: {horas}h {minutos}m restantes")
    
    return True

def mantener_sesion():
    """Función para mantener la sesión activa durante autorefresh"""
    # Esta función se llama durante cada refresh para mantener la sesión
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        # Actualizar tiempo de sesión para evitar expiración durante autorefresh
        if 'login_time' in st.session_state:
            # No actualizamos el login_time, solo verificamos que no haya expirado
            pass
        return True
    return False