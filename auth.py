# auth.py
import streamlit as st
import os

# Credenciales de administrador - SEGURAS con variables de entorno
def get_admin_credentials():
    """Obtiene credenciales desde variables de entorno o usa valores por defecto"""
    return {
        "usuario": os.getenv('ADMIN_USER', 'zelenza_admin'),
        "contraseña": os.getenv('ADMIN_PASS', 'cambia_esta_contraseña_2024')
    }

def authenticate(username, password):
    """Autentica al administrador"""
    if not username or not password:
        return False
    
    credentials = get_admin_credentials()
    return (username == credentials["usuario"] and 
            password == credentials["contraseña"])

def check_admin_auth():
    """Verifica si el usuario actual es administrador"""
    return (st.session_state.get('authenticated', False) and 
            st.session_state.get('user_type') == 'admin')

# Lista de empresas para usar en toda la app
EMPRESAS_ELECTRICAS = [
    "Iberdrola", "Endesa", "Naturgy", "TotalEnergies", 
    "Repsol", "EDP", "Viesgo", "Holaluz", "Factor Energía",
    "Octopus Energy", "Otra"
]
