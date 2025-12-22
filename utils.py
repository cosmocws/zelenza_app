import os
import shutil
import json
import uuid
from datetime import datetime, timedelta
import pytz
from config import TIMEZONE_MADRID

def obtener_hora_madrid():
    """Obtiene la hora actual en Madrid"""
    return datetime.now(pytz.timezone('Europe/Madrid'))

def convertir_a_madrid(fecha_hora):
    """Convierte cualquier fecha/hora a zona horaria de Madrid"""
    try:
        if isinstance(fecha_hora, str):
            fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
        
        if fecha_hora.tzinfo is None:
            fecha_hora = pytz.utc.localize(fecha_hora)
        
        return fecha_hora.astimezone(TIMEZONE_MADRID)
    except Exception as e:
        print(f"Error convirtiendo a Madrid: {e}")
        return obtener_hora_madrid()

def formatear_hora_madrid(fecha_hora):
    """Formatea una fecha/hora a hora de Madrid"""
    try:
        if isinstance(fecha_hora, str):
            try:
                fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
            except:
                from dateutil import parser
                fecha_hora = parser.parse(fecha_hora)
        
        if fecha_hora.tzinfo is None:
            fecha_hora = pytz.utc.localize(fecha_hora).astimezone(TIMEZONE_MADRID)
        else:
            fecha_hora = fecha_hora.astimezone(TIMEZONE_MADRID)
        
        return fecha_hora.strftime('%H:%M:%S')
    except Exception as e:
        print(f"Error formateando hora: {e}")
        return "00:00:00"

def generar_id_unico_usuario():
    """Genera un ID único para el dispositivo del usuario con persistencia"""
    import streamlit as st
    
    # Usar session_state como respaldo
    if 'device_id' not in st.session_state:
        device_id = f"dev_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        st.session_state.device_id = device_id
    
    return st.session_state.get('device_id', f"dev_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}")

def inicializar_directorios():
    """Inicializa los directorios necesarios"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("data_backup", exist_ok=True)
    os.makedirs("modelos_facturas", exist_ok=True)

def crear_autorefresh_safe():
    """Crea un sistema de autorefresh que no pierde la sesión"""
    import streamlit as st
    import time
    
    # Esta función sería llamada desde el main loop
    current_time = time.time()
    
    if 'last_autorefresh' not in st.session_state:
        st.session_state.last_autorefresh = current_time
    
    # Verificar si ha pasado 60 segundos
    if current_time - st.session_state.last_autorefresh > 60:
        st.session_state.last_autorefresh = current_time
        return True
    
    return False