import streamlit as st
import os
import shutil
from datetime import datetime
from config import *
from auth import *
from database import *
from ui_components import mostrar_login, mostrar_panel_usuario
from admin_functions import mostrar_panel_administrador
from pvd_system import temporizador_pvd_mejorado
from utils import obtener_hora_madrid, formatear_hora_madrid
from sidebar_notifications import verificar_turno_sidebar

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
            'About': '# Zelenza CEX v2.0 con PVD Mejorado y Grupos'
        }
    )
    
    # Añadir estilos CSS
    st.markdown("""
    <style>
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
        100% { transform: scale(1); opacity: 1; }
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .sidebar-notification {
        animation: pulse 2s infinite, blink 3s infinite;
        border-left: 5px solid #00b09b !important;
    }
    
    .stButton > button {
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Estilo para notificaciones importantes en sidebar */
    .important-notification {
        background: linear-gradient(135deg, #00b09b, #96c93d) !important;
        color: white !important;
        padding: 10px !important;
        border-radius: 8px !important;
        margin: 10px 0 !important;
        text-align: center !important;
        font-weight: bold !important;
        animation: pulse 2s infinite !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar temporizador PVD en segundo plano
    if 'temporizador_iniciado' not in st.session_state:
        st.session_state.temporizador_iniciado = True
    
    # Mostrar información sobre el sistema mejorado
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    # Información sobre el sistema mejorado
    st.info("""
    **🔔 Objetivo: RETENER. Consecuencia: LA VENTA.**
    
    - **✅ No vendas un producto, ofrece la solución a un problema.**
    - **🔔 Detrás de cada objeción hay un cliente esperando ser convencido.**
    - **⏱️ La retención es la meta. La venta, su resultado natural.**
    - **👥 Tu voz es su guía. Tu confianza, su certeza.**
    - **🔄 Olvida el 'no' de ayer. Hoy hay un 'sí' nuevo esperándote.**
    """)
    
    # Restauración automática al iniciar
    if os.path.exists("data_backup"):
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas", dirs_exist_ok=True)
    
    inicializar_datos()
    
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
    
    # Si no está autenticado, mostrar login
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        # ============================================
        # ✅ EJECUTAR VERIFICACIÓN DE TURNO EN SIDEBAR
        # ============================================
        if st.session_state.user_type == "user":
            verificar_turno_sidebar()

        # Barra lateral simple
        st.sidebar.title(f"{'🔧 Admin' if st.session_state.user_type == 'admin' else '👤 Usuario'}")
        st.sidebar.write(f"**Usuario:** {st.session_state.username}")
        
        # Mostrar nombre del usuario si está disponible
        if st.session_state.user_type == "user" and 'user_config' in st.session_state:
            nombre_usuario = st.session_state.user_config.get('nombre', '')
            if nombre_usuario:
                st.sidebar.write(f"**Nombre:** {nombre_usuario}")
        
        # Información de grupo si tiene (IMPORTANTE para PVD)
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
                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
            
            st.rerun()
        
        # Mostrar información del temporizador automático
        st.sidebar.markdown("---")
        st.sidebar.caption(f"⏱️ Temporizador automático: 60s")
        st.sidebar.caption(f"🔄 Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
        
        # Botón para refrescar manualmente
        if st.sidebar.button("🔄 Refrescar página", use_container_width=True, key="refresh_manual"):
            st.rerun()
        
        # Mostrar el panel correspondiente
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

if __name__ == "__main__":
    main()