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
    USANDO github_api_sync.py (EL SISTEMA QUE SÍ FUNCIONA)
    """
    try:
        # Verificar si somos admin y tenemos credenciales
        if (st.session_state.get('user_type') == 'admin' and 
            all(key in st.secrets for key in ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"])):
            
            from github_api_sync import GitHubSync
            
            def background_worker():
                """Worker que ejecuta sync cada hora"""
                print("🔄 Worker sync automático iniciado (cada 1 hora)")
                
                while True:
                    try:
                        # Esperar 5 minutos al inicio para que la app cargue
                        time.sleep(300)
                        
                        # Crear instancia del sincronizador
                        sync = GitHubSync()
                        
                        # Sincronizar TODO
                        print("🔁 Ejecutando sync automático...")
                        results = sync.sync_to_github(
                            commit_message=f"Auto-sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        
                        if results["success"] > 0:
                            print(f"✅ Auto-sync: {results['success']}/{results['total']} archivos")
                        else:
                            print(f"⚠️ Auto-sync: {results['failed']} fallos")
                        
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
    USANDO github_api_sync.py
    """
    try:
        if (st.session_state.get('user_type') == 'admin' and 
            all(key in st.secrets for key in ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"])):
            
            from github_api_sync import GitHubSync
            
            sync = GitHubSync()
            print("📥 Intentando cargar datos desde GitHub...")
            
            # Intentar descargar TODO desde GitHub
            results = sync.sync_from_github()
            
            if results.get("success", False) is not False:
                loaded_count = results.get("success", 0)
                if loaded_count > 0:
                    print(f"✅ {loaded_count} archivos cargados desde GitHub")
                    return True
                else:
                    print("ℹ️ No había datos nuevos en GitHub")
                    return False
            
    except Exception as e:
        print(f"⚠️ No se pudieron cargar datos de GitHub: {e}")
    
    return False

def sync_all_data_now():
    """
    Sincroniza TODOS los datos ahora mismo (manual)
    USANDO github_api_sync.py
    """
    try:
        from github_api_sync import GitHubSync
        
        sync = GitHubSync()
        results = sync.sync_to_github(
            commit_message=f"Sync manual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        if results["success"] > 0:
            return True, f"✅ {results['success']}/{results['total']} archivos guardados en GitHub"
        else:
            return False, "❌ No se pudo sincronizar ningún archivo"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def mostrar_panel_reparacion_objetivos():
    """Panel para reparar el archivo de objetivos"""
    from super_users_functions import mostrar_panel_reparacion_objetivos as mostrar_reparacion
    mostrar_reparacion()

def mostrar_todas_las_alertas():
    """Muestra todas las alertas del sistema"""
    st.header("📋 Todas las Alertas")
    st.info("Esta función está en desarrollo. Aquí se mostrarán todas las alertas del sistema.")
    
    if st.button("← Volver al Panel", type="secondary", use_container_width=True):
        st.session_state.mostrar_todas_alertas = False
        st.rerun()

def mostrar_sidebar_comun():
    """Configura elementos comunes en el sidebar"""
    # Logo y título
    st.sidebar.image("logo.png", width=100) if os.path.exists("logo.png") else None
    st.sidebar.title("Zelenza")
    
    # Información del usuario
    username = st.session_state.get('username', '')
    user_type = st.session_state.get('user_type', '')
    
    if username:
        st.sidebar.write(f"👤 **{username}**")
        st.sidebar.caption(f"Tipo: {user_type}")
        
        # Mostrar nombre del usuario si está disponible
        if user_type == "user" and 'user_config' in st.session_state:
            nombre_usuario = st.session_state.user_config.get('nombre', '')
            if nombre_usuario:
                st.sidebar.write(f"**Nombre:** {nombre_usuario}")
        
        # Información de grupo si tiene (IMPORTANTE para PVD)
        if user_type == "user" and 'user_config' in st.session_state:
            grupo_usuario = st.session_state.user_config.get('grupo', '')
            if grupo_usuario:
                st.sidebar.write(f"**Grupo:** {grupo_usuario}")
    
    # ============================================
    # ✅ EJECUTAR VERIFICACIÓN DE TURNO EN SIDEBAR (solo para usuarios normales)
    # ============================================
    if user_type == "user":
        verificar_turno_sidebar()
    
    # ============================================
    # ALERTAS PENDIENTE SMS EN SIDEBAR
    # ============================================
    # Solo para super users y admin
    if user_type in ["admin", "supervisor", "super_user"]:
        try:
            # Importar la función específica para alertas SMS
            from super_users_functions import mostrar_alertas_sms_en_sidebar
            mostrar_alertas_sms_en_sidebar()
        except Exception as e:
            st.sidebar.error(f"❌ Error al cargar alertas SMS: {e}")
    
    # ============================================
    # PANEL DE OBJETIVOS EN SIDEBAR
    # ============================================
    try:
        from super_users_functions import mostrar_panel_objetivos_sidebar
        mostrar_panel_objetivos_sidebar()
    except Exception as e:
        # Silenciar errores si el módulo no existe
        pass
    
    # ============================================
    # ALERTAS EN SIDEBAR (regulares)
    # ============================================
    try:
        from super_users_functions import mostrar_alertas_sidebar
        mostrar_alertas_sidebar()
    except:
        pass
    
    # ============================================
    # 🔄 SISTEMA DE SINCRONIZACIÓN AUTOMÁTICA (solo admin)
    # ============================================
    if user_type == "admin":
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
                # Mostrar estado del sync
                try:
                    # Verificar última sincronización en logs
                    log_file = "logs/github_sync.log"
                    if os.path.exists(log_file):
                        with open(log_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        
                        if lines:
                            # Buscar última línea de éxito
                            last_success = None
                            for line in reversed(lines):
                                if "SUCCESS" in line or "✅" in line:
                                    last_success = line.split(" - ")[0] if " - " in line else "Reciente"
                                    break
                            
                            if last_success:
                                st.sidebar.success(f"✅ Sincronizado")
                                st.sidebar.caption(f"Último: {last_success}")
                            else:
                                st.sidebar.info("🔧 Pendiente")
                        else:
                            st.sidebar.info("📭 Sin sync aún")
                    else:
                        st.sidebar.info("🔧 Sync disponible")
                        
                except:
                    st.sidebar.info("🔧 Sync disponible")
            
            # 4. Info del próximo auto-sync
            st.sidebar.caption("🔄 Auto-sync: cada 1 hora")
            
            # 5. Enlace a panel de sync avanzado
            st.sidebar.markdown("---")
            if st.sidebar.button("⚙️ Panel Sync Avanzado", use_container_width=True):
                st.session_state.show_sync_panel = True
                st.rerun()
        
        else:
            # Si no hay credenciales GitHub
            st.sidebar.warning("⚠️ GitHub no configurado")
            st.sidebar.caption("Configura GITHUB_TOKEN en secrets.toml")
    
    # Navegación
    st.sidebar.markdown("---")
    st.sidebar.write("### 📱 Navegación")
    
    # Botón para panel personal (si está autenticado)
    if username and user_type in ["admin", "supervisor", "super_user"]:
        if st.sidebar.button("👤 Mi Panel Personal", use_container_width=True):
            st.session_state.mostrar_panel_personal = True
            st.rerun()
    
    # Botón para volver al inicio
    if st.sidebar.button("🏠 Inicio", use_container_width=True):
        # Limpiar estados de página especial
        for key in ['mostrar_panel_personal', 'mostrar_gestion_alertas', 
                   'mostrar_todas_alertas', 'mostrar_reparacion_objetivos', 'show_sync_panel',
                   'mostrar_panel_alertas_sms']:
            if key in st.session_state:
                st.session_state[key] = False
        st.rerun()
    
    # Cerrar sesión
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
        # Limpiar sesión
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None
        st.session_state.user_config = {}
        st.session_state.device_id = None
        
        # Cancelar temporizador si existe
        if 'username' in st.session_state:
            try:
                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
            except:
                pass
        
        st.rerun()

def mostrar_contenido_principal():
    """Muestra el contenido principal según el tipo de usuario"""
    user_type = st.session_state.get('user_type', '')
    
    if user_type == "admin":
        mostrar_panel_administrador()
    elif user_type in ["supervisor", "super_user"]:
        # Importar aquí para evitar circular imports
        from super_users_functions import panel_super_usuario
        panel_super_usuario()
    else:
        # Para usuarios normales y agentes
        mostrar_panel_usuario()

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
        return
    
    # ============================================
    # MANEJADOR DE PÁGINAS ESPECIALES
    # ============================================
    
    # 1. Panel personal del usuario (solo para admin/super)
    if st.session_state.get('mostrar_panel_personal', False):
        try:
            from super_users_functions import mostrar_panel_personal_completo
            mostrar_panel_personal_completo()
            return
        except ImportError:
            st.error("Panel personal no disponible")
            st.session_state.mostrar_panel_personal = False
            st.rerun()
    
    # 2. Gestión de alertas descartadas
    if st.session_state.get('mostrar_gestion_alertas', False):
        try:
            from super_users_functions import mostrar_gestion_alertas_descartadas
            mostrar_gestion_alertas_descartadas()
            return
        except ImportError:
            st.error("Gestión de alertas no disponible")
            st.session_state.mostrar_gestion_alertas = False
            st.rerun()
    
    # 3. Ver todas las alertas
    if st.session_state.get('mostrar_todas_alertas', False):
        mostrar_todas_las_alertas()
        return
    
    # 4. Reparación de objetivos
    if st.session_state.get('mostrar_reparacion_objetivos', False):
        mostrar_panel_reparacion_objetivos()
        return
    
    # 5. Panel de alertas SMS
    if st.session_state.get('mostrar_panel_alertas_sms', False):
        try:
            from super_users_functions import panel_alertas_sms_completo
            panel_alertas_sms_completo()
            
            # Botón para volver
            if st.button("← Volver al Panel", type="secondary", use_container_width=True):
                st.session_state.mostrar_panel_alertas_sms = False
                st.rerun()
            return
        except ImportError:
            st.error("Panel de alertas SMS no disponible")
            st.session_state.mostrar_panel_alertas_sms = False
            st.rerun()
    
    # 6. Panel de sync avanzado
    if st.session_state.get('show_sync_panel', False):
        try:
            from sync_ui_simple import show_sync_panel_simple
            
            # Mostrar título y botón de volver arriba
            col_title, col_back = st.columns([3, 1])
            with col_title:
                st.subheader("⚙️ Panel de Sincronización Avanzada")
            with col_back:
                if st.button("← Volver", type="secondary"):
                    st.session_state.show_sync_panel = False
                    st.rerun()
            
            st.markdown("---")
            
            # Mostrar el panel
            show_sync_panel_simple()
            
            # Botón para volver abajo también
            st.markdown("---")
            if st.button("← Volver al Panel Principal", type="secondary", use_container_width=True):
                st.session_state.show_sync_panel = False
                st.rerun()
                
        except ImportError as e:
            st.error("❌ **Panel de sincronización no disponible**")
            st.info("""
            **Para solucionar:**
            1. Asegúrate de que `sync_ui_simple.py` existe en tu repositorio
            2. Contiene la función `show_sync_panel_simple()`
            3. Tienes el archivo `github_api_sync.py`
            
            **Archivos necesarios para sync:**
            ```
            github_api_sync.py     # Motor de sincronización
            sync_ui_simple.py      # Interfaz de usuario
            ```
            """)
            
            if st.button("← Volver al Panel Principal", type="secondary", use_container_width=True):
                st.session_state.show_sync_panel = False
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error en panel de sync: {str(e)[:100]}")
            
            if st.button("← Volver al Panel Principal", type="secondary", use_container_width=True):
                st.session_state.show_sync_panel = False
                st.rerun()
        
        return
    
    # ============================================
    # CONFIGURACIÓN DEL SIDEBAR
    # ============================================
    mostrar_sidebar_comun()
    
    # ============================================
    # MOSTRAR CONTENIDO PRINCIPAL
    # ============================================
    mostrar_contenido_principal()

if __name__ == "__main__":
    main()