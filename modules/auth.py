import streamlit as st
import json
import os
import shutil
import uuid
from datetime import datetime
from modules.utils import cargar_configuracion_usuarios, identificar_usuario_automatico

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

SISTEMA_CONFIG_DEFAULT = {
    "login_automatico_activado": True,
    "sesion_horas_duracion": 8,
    "grupos_usuarios": {
        "basico": {"planes_luz": ["PLAN_BASICO"], "planes_gas": ["RL1"]},
        "premium": {"planes_luz": ["TODOS"], "planes_gas": ["RL1", "RL2", "RL3"]},
        "empresa": {"planes_luz": ["PLAN_EMPRESA"], "planes_gas": ["RL2", "RL3"]}
    }
}

def authenticate(username, password, user_type):
    try:
        # Cargar usuarios desde archivo
        usuarios_config = cargar_configuracion_usuarios()
        
        if user_type == "user":
            # Verificar si el usuario existe
            if username in usuarios_config:
                usuario = usuarios_config[username]
                # CAMBIO: Siempre verificar contra la contraseña guardada
                if "password" in usuario:
                    return password == usuario["password"]
                else:
                    # Para compatibilidad con versiones antiguas
                    try:
                        return password == st.secrets["credentials"]["user_password"]
                    except:
                        return password == "cliente123"
            else:
                # Usuario estándar por defecto
                try:
                    return (username == st.secrets["credentials"]["user_username"] and 
                            password == st.secrets["credentials"]["user_password"])
                except:
                    return username == "usuario" and password == "cliente123"
                    
        elif user_type == "admin":
            try:
                return (username == st.secrets["credentials"]["admin_username"] and 
                        password == st.secrets["credentials"]["admin_password"])
            except:
                return username == "admin" and password == "admin123"
                
        return False
    except Exception as e:
        st.error(f"Error en autenticación: {e}")
        return False

def cargar_config_sistema():
    """Carga la configuración del sistema"""
    try:
        with open('data/config_sistema.json', 'r') as f:
            return json.load(f)
    except:
        # Crear archivo por defecto
        os.makedirs('data', exist_ok=True)
        with open('data/config_sistema.json', 'w') as f:
            json.dump(SISTEMA_CONFIG_DEFAULT, f, indent=4)
        return SISTEMA_CONFIG_DEFAULT.copy()

def guardar_config_sistema(config):
    """Guarda la configuración del sistema"""
    os.makedirs('data', exist_ok=True)
    with open('data/config_sistema.json', 'w') as f:
        json.dump(config, f, indent=4)

def verificar_sesion():
    """Verifica si la sesión es válida (8 horas) - CORREGIDO"""
    if not st.session_state.get('authenticated', False):
        return False
    
    # Si no hay tiempo de login, crear uno
    if 'login_time' not in st.session_state:
        st.session_state.login_time = datetime.now()
        return True
    
    # Calcular horas transcurridas
    horas_transcurridas = (datetime.now() - st.session_state.login_time).total_seconds() / 3600
    
    # Cargar configuración del sistema
    config_sistema = cargar_config_sistema()
    horas_duracion = config_sistema.get("sesion_horas_duracion", 8)
    
    # Verificar si ha expirado
    if horas_transcurridas >= horas_duracion:
        st.warning("⏰ Tu sesión ha expirado. Por favor, vuelve a iniciar sesión.")
        
        # Limpiar sesión
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None
        
        # Forzar rerun para mostrar login
        st.rerun()
        return False
    
    # Actualizar tiempo restante en sidebar
    tiempo_restante = horas_duracion - horas_transcurridas
    horas = int(tiempo_restante)
    minutos = int((tiempo_restante - horas) * 60)
    
    st.sidebar.info(f"⏳ Sesión expira en: {horas}h {minutos}m")
    
    return True

def mostrar_login():
    """Muestra la pantalla de login"""
    st.header("🔐 Acceso a la Plataforma")
    
    # Cargar configuración del sistema
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
            # Primero intentar como admin
            if authenticate(admin_user, admin_pass, "admin"):
                st.session_state.authenticated = True
                st.session_state.user_type = "admin"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            # Luego como usuario normal
            elif authenticate(admin_user, admin_pass, "user"):
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

def cerrar_sesion():
    """Cierra la sesión actual"""
    st.session_state.authenticated = False
    st.session_state.user_type = None
    st.session_state.username = ""
    st.session_state.login_time = None
    st.rerun()