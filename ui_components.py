import streamlit as st
from datetime import datetime
import pytz

from config import COMUNIDADES_AUTONOMAS
from auth import authenticate, identificar_usuario_automatico
from database import cargar_config_sistema
from utils import obtener_hora_madrid

def mostrar_login():
    """Muestra la pantalla de login"""
    st.header("🔐 Acceso a la Plataforma")
    
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
            if authenticate(admin_user, admin_pass, "admin"):
                st.session_state.authenticated = True
                st.session_state.user_type = "admin"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            elif authenticate(admin_user, admin_pass, "user"):
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    from auth import verificar_sesion, es_super_usuario
    if not verificar_sesion():
        mostrar_login()
        return
    
    # Verificar si es super usuario
    if es_super_usuario(st.session_state.username):
        from super_users_functions import panel_super_usuario
        panel_super_usuario()
        return
    
    # ============================================
    # 1. PRIMERO: Panel personal del agente (si se solicitó desde sidebar)
    # ============================================
    if st.session_state.get('mostrar_panel_personal', False):
        try:
            from super_users_functions import mostrar_estadisticas_agente_personal
            mostrar_estadisticas_agente_personal(st.session_state.username)
            return  # IMPORTANTE: Salir aquí, no mostrar nada más
        except ImportError as e:
            st.error(f"No se pudo cargar el panel personal: {e}")
            st.session_state.mostrar_panel_personal = False
            st.rerun()
    
    # ============================================
    # 2. MOSTRAR LA ÚLTIMA MONITORIZACIÓN DEL USUARIO (NUEVO)
    # ============================================
    usuario_id = st.session_state.username
    
    try:
        # Importar la función de monitorización
        from user_functions import mostrar_ultima_monitorizacion_usuario
        
        # Mostrar la última monitorización
        monitorizacion_mostrada = mostrar_ultima_monitorizacion_usuario(usuario_id)
        
        # Si se mostró, añadir separador
        if monitorizacion_mostrada:
            st.markdown("---")
    except ImportError:
        # Si no existe la función, continuar sin mostrar monitorización
        st.info("ℹ️ La información de monitorizaciones no está disponible en este momento")
    except Exception as e:
        st.error(f"Error al cargar monitorización: {e}")
    
    # ============================================
    # 3. TERCERO: Contenido normal (pestañas) - SOLO si no estamos en panel personal
    # ============================================
    
    # IMPORTAR las funciones necesarias aquí
    from user_functions import (
        consultar_modelos_factura, comparativa_exacta,
        calculadora_gas, cups_naturgy, comparativa_estimada,
        gestion_pvd_usuario
    )
    
    # Ocultar el título y bienvenida para que no aparezca "None"
    # Solo mostrar directamente las pestañas
    
    # Cargar configuración de secciones
    from database import cargar_config_sistema
    config_sistema = cargar_config_sistema()
    secciones_activas = config_sistema.get('secciones_activas', {})
    
    # Si no hay configuración, activar todas por defecto
    if not secciones_activas:
        from config import SECCIONES_USUARIO
        secciones_activas = {seccion: True for seccion in SECCIONES_USUARIO.keys()}
    
    # PRIMERO: Mostrar el menú de comparativas (ANTES de las facturas)
    st.subheader("🧮 Comparativas")
    
    # Crear pestañas solo para secciones activas
    tabs = []
    tab_contents = []
    
    if secciones_activas.get('comparativa_exacta', True):
        tabs.append("⚡ Comparativa EXACTA")
        tab_contents.append(comparativa_exacta)
    
    if secciones_activas.get('comparativa_estimada', True):
        tabs.append("📅 Comparativa ESTIMADA")
        tab_contents.append(comparativa_estimada)
    
    if secciones_activas.get('calculadora_gas', True):
        tabs.append("🔥 Gas")
        tab_contents.append(calculadora_gas)
    
    if secciones_activas.get('pvd_usuario', True):
        tabs.append("👁️ PVD")
        tab_contents.append(gestion_pvd_usuario)
    
    if secciones_activas.get('cups_naturgy', True):
        tabs.append("📋 CUPS Naturgy")
        tab_contents.append(cups_naturgy)
    
    # Crear las pestañas dinámicamente
    if tabs:
        created_tabs = st.tabs(tabs)
        
        for i, tab in enumerate(created_tabs):
            with tab:
                tab_contents[i]()
    
    st.markdown("---")
    
    # SEGUNDO: Mostrar modelos de factura solo si está activa
    if secciones_activas.get('modelos_factura', True):
        consultar_modelos_factura()
    else:
        st.info("📄 La sección de modelos de factura no está disponible actualmente")