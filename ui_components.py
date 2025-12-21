import streamlit as st
from datetime import datetime
import pytz
import json  # <-- AÑADIR ESTA LÍNEA

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
    from auth import verificar_sesion
    if not verificar_sesion():
        mostrar_login()
        return
    
    from user_functions import (
        consultar_modelos_factura, comparativa_exacta,
        calculadora_gas, cups_naturgy, comparativa_estimada,
        gestion_pvd_usuario
    )
    
    # Mostrar información del usuario
    from database import cargar_configuracion_usuarios
    if st.session_state.username in cargar_configuracion_usuarios():
        config = cargar_configuracion_usuarios()[st.session_state.username]
        st.header(f"👤 {config.get('nombre', 'Usuario')}")
    else:
        st.header("👤 Portal del Cliente")
    
    # Cargar configuración de secciones
    from database import cargar_config_sistema
    config_sistema = cargar_config_sistema()
    secciones_activas = config_sistema.get('secciones_activas', {})
    from config import SECCIONES_USUARIO
    
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

def modo_prueba_rapida_usuario():
    """Modo de prueba rápida para usuarios normales (oculto)"""
    if 'modo_prueba_activado' not in st.session_state:
        st.session_state.modo_prueba_activado = False
    
    codigo_prueba = st.text_input("🔐 Código de prueba (dejar vacío para modo normal)", type="password")
    
    if codigo_prueba == "testpvd123":
        st.session_state.modo_prueba_activado = True
        st.success("✅ Modo prueba activado")
    
    if codigo_prueba == "salir":
        st.session_state.modo_prueba_activado = False
        st.info("Modo prueba desactivado")
    
    if st.session_state.modo_prueba_activado:
        st.warning("🧪 **MODO PRUEBA ACTIVADO** - Datos de prueba")
        
        from database import cargar_config_pvd, cargar_cola_pvd
        from pvd_system import temporizador_pvd
        from datetime import datetime, timedelta
        import pytz
        
        config_pvd = cargar_config_pvd()
        cola_pvd = cargar_cola_pvd()
        
        with st.expander("🧪 Panel de Control de Prueba", expanded=True):
            col_test1, col_test2, col_test3 = st.columns(3)
            
            with col_test1:
                if st.button("🎯 Simular Ser Primero", type="primary", use_container_width=True):
                    st.success("✅ Ahora eres el primero en la cola")
            
            with col_test2:
                if st.button("⏱️ Simular Tiempo Cumplido", type="secondary", use_container_width=True):
                    temporizador_pvd.iniciar_temporizador_usuario(st.session_state.username, 0.1)
                    st.success("✅ Temporizador configurado a 6 segundos")
            
            with col_test3:
                if st.button("🔔 Probar Notificación", type="secondary", use_container_width=True):
                    st.markdown("""
                    <script>
                    setTimeout(function() {
                        const confirmar = confirm('🎉 [PRUEBA] ¡ES TU TURNO!\\n\\nPrueba de notificación.\\n\\nHaz clic en OK para probar.');
                        if (confirmar) {
                            alert('✅ Prueba exitosa');
                        }
                    }, 1000);
                    </script>
                    """, unsafe_allow_html=True)
                    st.info("🔔 Notificación de prueba activada")
        
        st.write("**Estado simulado:**")
        st.write(f"- Posición en cola: #1 (simulado)")
        st.write(f"- Tiempo estimado: 0-2 minutos (simulado)")
        st.write(f"- Estado: ESPERANDO (simulado)")
        
        return True
    
    return False