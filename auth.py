# auth.py
import streamlit as st

# Credenciales de administrador
ADMIN_CREDENTIALS = {
    "usuario": "admin",
    "contraseña": "admin123"
}

def authenticate(username, password, user_type):
    """Autentica al usuario según el tipo"""
    if not username or not password:
        return False
    
    if user_type == "admin":
        return (username == ADMIN_CREDENTIALS["usuario"] and 
                password == ADMIN_CREDENTIALS["contraseña"])
    else:
        # Para usuario normal, cualquier credencial funciona
        return True

def check_auth():
    """Verifica si el usuario está autenticado"""
    return st.session_state.get('authenticated', False)