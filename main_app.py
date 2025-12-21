import streamlit as st
from config import *
from auth import *
from database import *
from ui_components import mostrar_login, mostrar_panel_usuario, modo_prueba_rapida_usuario
from admin_functions import mostrar_panel_administrador

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
            'About': '# Zelenza CEX v1.0 con PVD y Notificación de Confirmación'
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
    
    # Información sobre el sistema de confirmación
    st.info("""
    **🔔 SISTEMA PVD MEJORADO:**
    
    - **Funcionamiento automático** como antes
    - **Notificación de confirmación** cuando sea tu turno
    - **Debes hacer clic en OK** en la alerta del navegador
    - **La pausa empieza automáticamente** después de confirmar
    
    ⚠️ **Permite ventanas emergentes** para recibir la notificación
    """)
    
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
                from pvd_system import temporizador_pvd
                temporizador_pvd.cancelar_temporizador(st.session_state.username)
            
            st.rerun()
        
        st.sidebar.markdown("---")
        
        # Mostrar el panel correspondiente
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

if __name__ == "__main__":
    main()