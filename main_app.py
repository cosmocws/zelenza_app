import streamlit as st
import os
import shutil
import time
import threading
from datetime import datetime
from config import *
from auth import *
from database import *
from ui_components import mostrar_login, mostrar_panel_usuario
from admin_functions import mostrar_panel_administrador
from pvd_system import temporizador_pvd_mejorado
from utils import obtener_hora_madrid, formatear_hora_madrid
from sidebar_notifications import verificar_turno_sidebar

def start_background_sync():
    """
    Inicia el sync automático en segundo plano (cada 1 hora)
    Solo para admin y si hay credenciales GitHub
    """
    try:
        # Verificar si somos admin y tenemos credenciales
        if (st.session_state.get('user_type') == 'admin' and 
            all(key in st.secrets for key in ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"])):
            
            from sync_data_to_github import sync_manager
            
            def background_worker():
                """Worker que ejecuta sync cada hora"""
                print("🔄 Worker sync automático iniciado (cada 1 hora)")
                
                while True:
                    try:
                        # Esperar 5 minutos al inicio para que la app cargue
                        time.sleep(300)
                        
                        # Verificar cambios y sync si es necesario
                        changed_files = sync_manager.check_for_changes()
                        
                        if changed_files:
                            print(f"📁 {len(changed_files)} archivos modificados, auto-sync...")
                            success_count, total_files, results = sync_manager.sync_all_changed_files()
                            
                            if success_count > 0:
                                print(f"✅ Auto-sync: {success_count}/{total_files} archivos")
                            else:
                                print(f"⚠️ Auto-sync falló para {len(changed_files)} archivos")
                        
                        # Esperar 1 hora
                        time.sleep(3600)
                        
                    except Exception as e:
                        print(f"❌ Error en worker sync: {e}")
                        time.sleep(300)  # Esperar 5 minutos si hay error
            
            # Iniciar thread en segundo plano
            thread = threading.Thread(target=background_worker, daemon=True)
            thread.start()
            
            print("✅ Sync automático iniciado (cada 1 hora)")
            return True
            
    except Exception as e:
        print(f"⚠️ No se pudo iniciar sync automático: {e}")
    
    return False

def load_data_from_github_on_start():
    """
    Carga datos desde GitHub al iniciar la app
    Solo si somos admin y hay credenciales
    """
    try:
        if (st.session_state.get('user_type') == 'admin' and 
            all(key in st.secrets for key in ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"])):
            
            from github_sync_completo import GitHubSyncCompleto
            
            # Archivos importantes a cargar
            important_files = [
                "data/registro_llamadas.json",
                "data/planes_gas.json",
                "data/precios_luz.csv",
                "data/config_excedentes.csv",
                "data/usuarios.json",
                "data/super_users.json"
            ]
            
            sync = GitHubSyncCompleto()
            loaded_count = 0
            
            for file_path in important_files:
                # Si no existe o está vacío, cargar de GitHub
                if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
                    try:
                        # Crear directorio si no existe
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # Intentar descargar
                        success, message = sync.download_file(file_path, file_path)
                        if success:
                            print(f"📥 Cargado de GitHub: {file_path}")
                            loaded_count += 1
                    except:
                        pass  # Continuar con el siguiente archivo
            
            if loaded_count > 0:
                print(f"✅ {loaded_count} archivos cargados desde GitHub")
            
            return loaded_count > 0
            
    except Exception as e:
        print(f"⚠️ No se pudieron cargar datos de GitHub: {e}")
    
    return False

def sync_all_data_now():
    """
    Sincroniza TODOS los datos ahora mismo (manual)
    """
    try:
        from sync_data_to_github import sync_now
        
        success_count, total_files, results = sync_now(force=True)
        
        if success_count > 0:
            return True, f"✅ {success_count}/{total_files} archivos guardados en GitHub"
        else:
            return False, "❌ No se pudo sincronizar ningún archivo"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

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

    from super_users_functions import mostrar_alertas_sidebar
    mostrar_alertas_sidebar()
        
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
    
    /* Estilo para botón de sync */
    .sync-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
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
        
        # ============================================
        # 🔄 SISTEMA DE SINCRONIZACIÓN AUTOMÁTICA
        # ============================================
        
        # Solo para admin
        if st.session_state.user_type == "admin":
            st.sidebar.markdown("---")
            st.sidebar.write("**💾 Sync con GitHub**")
            
            # Verificar credenciales GitHub
            github_configured = all(key in st.secrets for key in ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"])
            
            if github_configured:
                # 1. Iniciar sync automático en segundo plano (solo una vez)
                if 'background_sync_started' not in st.session_state:
                    if start_background_sync():
                        st.session_state.background_sync_started = True
                
                # 2. Cargar datos desde GitHub al iniciar (solo una vez)
                if 'github_data_loaded' not in st.session_state:
                    if load_data_from_github_on_start():
                        st.session_state.github_data_loaded = True
                
                # 3. Botón de sync manual
                col_sync1, col_sync2 = st.sidebar.columns(2)
                
                with col_sync1:
                    if st.sidebar.button("💾 Guardar Todo", 
                                        use_container_width=True,
                                        type="primary",
                                        help="Guarda TODOS los datos en GitHub ahora"):
                        
                        with st.spinner("Guardando en GitHub..."):
                            success, message = sync_all_data_now()
                            
                            if success:
                                st.sidebar.success(message)
                                st.balloons()
                            else:
                                st.sidebar.error(message)
                        
                        st.rerun()
                
                with col_sync2:
                    # Estado del sync
                    try:
                        from sync_data_to_github import get_status
                        status = get_status()
                        
                        if status["changed_files"]:
                            changed_count = len(status["changed_files"])
                            st.sidebar.warning(f"✏️ {changed_count} modificados")
                        else:
                            st.sidebar.success("✅ Sincronizado")
                            
                    except:
                        st.sidebar.info("🔧 Sync disponible")
                
                # 4. Info del próximo auto-sync
                try:
                    from sync_data_to_github import get_status
                    status = get_status()
                    
                    if status.get("next_sync_in"):
                        st.sidebar.caption(f"⏰ Próximo auto-sync: {status['next_sync_in']}")
                    else:
                        st.sidebar.caption("🔄 Auto-sync: cada 1 hora")
                        
                except:
                    pass
                
                # 5. Enlace a panel de sync avanzado
                st.sidebar.markdown("---")
                if st.sidebar.button("⚙️ Panel Sync Avanzado", use_container_width=True):
                    st.session_state.show_sync_panel = True
                    st.rerun()
                
            else:
                # Si no hay credenciales GitHub
                st.sidebar.warning("⚠️ GitHub no configurado")
                st.sidebar.caption("Configura GITHUB_TOKEN en secrets.toml")
        
        # ============================================
        # BOTONES GENERALES
        # ============================================
        
        st.sidebar.markdown("---")
        
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
        
        # ============================================
        # MOSTRAR PANEL CORRESPONDIENTE
        # ============================================
        
        # Verificar si hay que mostrar panel de sync avanzado
        if st.session_state.get('show_sync_panel', False):
            try:
                from sync_ui import show_sync_panel
                show_sync_panel()
                
                # Botón para volver
                if st.button("← Volver al Panel Principal"):
                    st.session_state.show_sync_panel = False
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error cargando panel de sync: {e}")
                st.session_state.show_sync_panel = False
                st.rerun()
        
        # Panel normal
        elif st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

if __name__ == "__main__":
    main()