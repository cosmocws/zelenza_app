import streamlit as st
import pandas as pd
import os
import shutil
import json
import uuid
from datetime import datetime, timedelta

# AL INICIO DEL ARCHIVO, después del main() pero ANTES del if __name__

# JavaScript para mantener estado
persist_js = """
<script>
// Guardar estado de autenticación en localStorage
function saveAuthState(username, userType) {
    localStorage.setItem('zelenza_auth_username', username || '');
    localStorage.setItem('zelenza_auth_type', userType || '');
    localStorage.setItem('zelenza_auth_time', Date.now());
}

// Cargar estado de autenticación
function loadAuthState() {
    const username = localStorage.getItem('zelenza_auth_username') || '';
    const userType = localStorage.getItem('zelenza_auth_type') || '';
    const authTime = parseInt(localStorage.getItem('zelenza_auth_time') || '0');
    const eightHours = 8 * 60 * 60 * 1000;
    
    // Verificar si la sesión expiró (8 horas)
    if (username && userType && (Date.now() - authTime) < eightHours) {
        // Sesión válida
        return {username: username, userType: userType};
    } else {
        // Sesión expirada, limpiar
        localStorage.removeItem('zelenza_auth_username');
        localStorage.removeItem('zelenza_auth_type');
        localStorage.removeItem('zelenza_auth_time');
        return null;
    }
}

// Inicializar
window.addEventListener('load', function() {
    const authState = loadAuthState();
    if (authState) {
        console.log('Sesión recuperada:', authState);
    }
});

// Ejecutar inmediatamente
(function() {
    const authState = loadAuthState();
    if (authState) {
        console.log('Sesión cargada al inicio:', authState);
    }
})();
</script>
"""

# Ejecutar el script de persistencia SOLO si estamos en el contexto principal
if __name__ == "__main__":
    st.components.v1.html(persist_js, height=0)  # ← CORREGIDO

# Configuración para mantener estado
if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.persist_login = True

# JavaScript para mantener estado
persist_js = """
<script>
// Guardar estado de autenticación en localStorage
function saveAuthState(username, userType) {
    localStorage.setItem('zelenza_auth_username', username || '');
    localStorage.setItem('zelenza_auth_type', userType || '');
    localStorage.setItem('zelenza_auth_time', Date.now());
}

// Cargar estado de autenticación
function loadAuthState() {
    const username = localStorage.getItem('zelenza_auth_username') || '';
    const userType = localStorage.getItem('zelenza_auth_type') || '';
    const authTime = parseInt(localStorage.getItem('zelenza_auth_time') || '0');
    const eightHours = 8 * 60 * 60 * 1000;
    
    // Verificar si la sesión expiró (8 horas)
    if (username && userType && (Date.now() - authTime) < eightHours) {
        // Sesión válida
        return {username: username, userType: userType};
    } else {
        // Sesión expirada, limpiar
        localStorage.removeItem('zelenza_auth_username');
        localStorage.removeItem('zelenza_auth_type');
        localStorage.removeItem('zelenza_auth_time');
        return null;
    }
}

// Inicializar
window.addEventListener('load', function() {
    const authState = loadAuthState();
    if (authState) {
        console.log('Sesión recuperada:', authState);
    }
});
</script>
"""

# Ejecutar el script de persistencia
st.components.v1.html(persist_js, height=0)

def verificar_sesion_persistente():
    """Verifica si hay una sesión guardada en localStorage"""
    js_code = """
    <script>
    // Guardar sesión al iniciar
    if (!window.sessionSaved) {
        window.sessionSaved = true;
        localStorage.setItem('zelenza_last_refresh', Date.now());
    }
    
    // Verificar si la página fue recargada
    const lastRefresh = localStorage.getItem('zelenza_last_refresh');
    const now = Date.now();
    const timeDiff = now - parseInt(lastRefresh || 0);
    
    // Si fue recargada en menos de 5 segundos, mantener sesión
    if (timeDiff < 5000 && !window.location.search.includes('session_reset')) {
        // Mantener sesión activa
        console.log('Sesión mantenida después de refresh');
    }
    
    // Actualizar timestamp
    localStorage.setItem('zelenza_last_refresh', now);
    </script>
    """
    st.components.v1.html(js_code, height=0)  # ← CORREGIDO

# LLAMAR esta función en main() después de inicializar datos:
def main():
    # RESTAURACIÓN AUTOMÁTICA AL INICIAR
    if os.path.exists("data_backup"):
        # Restaurar archivos CSV
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        # Restaurar modelos de factura
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas")
    
    inicializar_datos()
    
    # Verificar sesión persistente
    verificar_sesion_persistente()
    
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")

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

PVD_CONFIG_DEFAULT = {
    "agentes_activos": 25,  # Total de agentes trabajando
    "maximo_simultaneo": 3,  # Máximo que pueden estar en pausa a la vez
    "duracion_corta": 5,    # minutos - duración corta
    "duracion_larga": 10,   # minutos - duración larga  
    "sonido_activado": True
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

# Estados de la cola PVD
ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
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
    """Verifica si la sesión es válida (8 horas) - MEJORADA CON localStorage"""
    # Primero verificar session_state
    if not st.session_state.get('authenticated', False):
        # Intentar recuperar de localStorage
        try:
            # JavaScript para recuperar sesión
            recover_js = """
            <script>
            try {
                const username = localStorage.getItem('zelenza_auth_username');
                const userType = localStorage.getItem('zelenza_auth_type');
                const authTime = localStorage.getItem('zelenza_auth_time');
                
                if (username && userType && authTime) {
                    // Verificar no expirada (8 horas)
                    const eightHours = 8 * 60 * 60 * 1000;
                    const now = Date.now();
                    
                    if ((now - parseInt(authTime)) < eightHours) {
                        // Enviar a Streamlit
                        const input = document.createElement('input');
                        input.type = 'hidden';
                        input.id = 'recovered_session';
                        input.value = JSON.stringify({
                            username: username,
                            userType: userType
                        });
                        document.body.appendChild(input);
                        
                        // Disparar evento para que Streamlit lo detecte
                        const event = new Event('sessionRecovered');
                        document.dispatchEvent(event);
                    } else {
                        // Limpiar sesión expirada
                        localStorage.removeItem('zelenza_auth_username');
                        localStorage.removeItem('zelenza_auth_type');
                        localStorage.removeItem('zelenza_auth_time');
                    }
                }
            } catch(e) {
                console.log('Error recuperando sesión:', e);
            }
            </script>
            """
            st.components.v1.html(recover_js, height=0)  # ← CORREGIDO
            
            # Crear un botón oculto para forzar la recuperación
            if st.button("🔓 Recuperar sesión", key="recover_session", help="Click si tu sesión se perdió"):
                st.session_state.authenticated = True
                # Intenta recuperar usuario de alguna manera
                # (podrías usar cookies o parámetros URL)
                st.rerun()
                
        except Exception as e:
            print(f"Error en recuperación de sesión: {e}")
        
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
        
        # Limpiar localStorage también
        clear_js = """
        <script>
        localStorage.removeItem('zelenza_auth_username');
        localStorage.removeItem('zelenza_auth_type');
        localStorage.removeItem('zelenza_auth_time');
        </script>
        """
        st.components.v1.html(clear_js, height=0)  # ← CORREGIDO
        
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
    
    # Guardar estado en localStorage para persistencia
    if st.session_state.authenticated:
        save_js = f"""
        <script>
        localStorage.setItem('zelenza_auth_username', '{st.session_state.username}');
        localStorage.setItem('zelenza_auth_type', '{st.session_state.user_type}');
        localStorage.setItem('zelenza_auth_time', Date.now());
        </script>
        """
        st.components.v1.html(save_js, height=0)  # ← CORREGIDO
    
    return True

def mostrar_panel_usuario():
    """Panel del usuario normal - CORREGIDO"""
    # Primero verificar sesión
    if not verificar_sesion():
        mostrar_login()
        return
    
    # Mostrar información del usuario
    if st.session_state.username in cargar_configuracion_usuarios():
        config = cargar_configuracion_usuarios()[st.session_state.username]
        st.header(f"👤 {config.get('nombre', 'Usuario')}")
    else:
        st.header("👤 Portal del Cliente")
    
    # PRIMERA PANTALLA: Consultar modelos de factura
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Comparativas
    st.subheader("🧮 Comparativas")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Comparativa EXACTA", "📅 Comparativa ESTIMADA", "🔥 Gas", "👁️ PVD", "📋 CUPS Naturgy"])
    
    with tab1:
        comparativa_exacta()
    with tab2:
        comparativa_estimada()
    with tab3:
        calculadora_gas()
    with tab4:
        gestion_pvd_usuario()
    with tab5:
        cups_naturgy()

def mostrar_panel_administrador():
    """Panel de administración - CORREGIDO"""
    # Primero verificar sesión
    if not verificar_sesion():
        mostrar_login()
        return
    
    st.header("🔧 Panel de Administración")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⚡ Electricidad", "🔥 Gas", "👥 Usuarios", "👁️ PVD", 
        "📄 Facturas", "☀️ Excedentes", "⚙️ Sistema"
    ])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_usuarios()
    with tab4:
        gestion_pvd_admin()
    with tab5:
        gestion_modelos_factura()
    with tab6:
        gestion_excedentes()
    with tab7:
        gestion_config_sistema()

def main():
    # RESTAURACIÓN AUTOMÁTICA AL INICIAR
    if os.path.exists("data_backup"):
        # Restaurar archivos CSV
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        # Restaurar modelos de factura
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas")
    
    inicializar_datos()
    
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None

    if not st.session_state.authenticated:
        mostrar_login()
    else:
        # La verificación de sesión se hace dentro de cada panel
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

# Configuración de la página MEJORADA
st.set_page_config(
    page_title="Zelenza CEX - Iberdrola",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': 'https://www.example.com/bug',
        'About': '# Zelenza CEX v1.0'
    }
)

def inicializar_datos():
    """Inicializa los archivos de datos con backup automático"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # ARCHIVOS CRÍTICOS QUE QUEREMOS BACKUPEAR
    archivos_criticos = {
        "precios_luz.csv": pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
            'comunidades_autonomas'
        ]),
        "config_excedentes.csv": pd.DataFrame([{'precio_excedente_kwh': 0.06}]),
        "planes_gas.json": json.dumps(PLANES_GAS_ESTRUCTURA, indent=4),
        "config_pmg.json": json.dumps({"coste": PMG_COSTE, "iva": PMG_IVA}, indent=4),
        "usuarios.json": json.dumps(USUARIOS_DEFAULT, indent=4),
        "config_pvd.json": json.dumps(PVD_CONFIG_DEFAULT, indent=4),
        "cola_pvd.json": json.dumps([], indent=4)
    }
    
    for archivo, df_default in archivos_criticos.items():
        ruta_data = f"data/{archivo}"
        ruta_backup = f"data_backup/{archivo}"
        
        # Si no existe en data, intentar restaurar desde backup
        if not os.path.exists(ruta_data):
            if os.path.exists(ruta_backup):
                # RESTAURAR desde backup
                shutil.copy(ruta_backup, ruta_data)
                st.sidebar.success(f"✅ {archivo} restaurado desde backup")
            else:
                # Crear archivo por defecto
                if archivo.endswith('.json'):
                    with open(ruta_data, 'w') as f:
                        f.write(df_default)
                else:
                    df_default.to_csv(ruta_data, index=False)
        
        # SIEMPRE hacer backup de los datos actuales
        if os.path.exists(ruta_data):
            os.makedirs("data_backup", exist_ok=True)
            shutil.copy(ruta_data, ruta_backup)
    
    # BACKUP de modelos_facturas
    if os.path.exists("modelos_facturas") and os.listdir("modelos_facturas"):
        os.makedirs("data_backup", exist_ok=True)
        if os.path.exists("data_backup/modelos_facturas"):
            shutil.rmtree("data_backup/modelos_facturas")
        shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")

# --- FUNCIONES DE GESTIÓN DE USUARIOS ---
def cargar_configuracion_usuarios():
    """Carga la configuración de usuarios desde archivo"""
    try:
        with open('data/usuarios.json', 'r') as f:
            return json.load(f)
    except:
        # Crear archivo por defecto
        os.makedirs('data', exist_ok=True)
        with open('data/usuarios.json', 'w') as f:
            json.dump(USUARIOS_DEFAULT, f, indent=4)
        return USUARIOS_DEFAULT.copy()

def guardar_configuracion_usuarios(usuarios_config):
    """Guarda la configuración de usuarios"""
    os.makedirs('data', exist_ok=True)
    with open('data/usuarios.json', 'w') as f:
        json.dump(usuarios_config, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/usuarios.json', 'data_backup/usuarios.json')

def generar_id_unico_usuario():
    """Genera un ID único para el dispositivo del usuario"""
    # Usar session_state para almacenar el ID
    if 'device_id' not in st.session_state:
        # Crear nuevo ID único
        device_id = f"dev_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        st.session_state.device_id = device_id
    return st.session_state.device_id

def identificar_usuario_automatico():
    """Identifica automáticamente al usuario por su dispositivo"""
    device_id = generar_id_unico_usuario()
    
    # Cargar configuración de usuarios
    usuarios_config = cargar_configuracion_usuarios()
    
    # Buscar si ya existe este dispositivo
    for username, config in usuarios_config.items():
        if config.get('device_id') == device_id:
            return username, config
    
    # Si no existe, crear usuario automático
    nuevo_username = f"auto_{device_id[:8]}"
    
    if nuevo_username not in usuarios_config:
        usuarios_config[nuevo_username] = {
            "nombre": f"Usuario {device_id[:8]}",
            "device_id": device_id,
            "planes_luz": [],  # Por defecto sin planes
            "planes_gas": ["RL1", "RL2", "RL3"],  # Todos los planes de gas
            "tipo": "auto",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "password": "auto_login"
        }
        guardar_configuracion_usuarios(usuarios_config)
    
    return nuevo_username, usuarios_config[nuevo_username]

def filtrar_planes_por_usuario(df_planes, username, tipo_plan="luz"):
    """Filtra los planes según la configuración del usuario"""
    usuarios_config = cargar_configuracion_usuarios()
    
    if username not in usuarios_config:
        # Usuario automático sin config - mostrar todos por defecto
        return df_planes[df_planes['activo'] == True]
    
    config_usuario = usuarios_config[username]
    
    if tipo_plan == "luz":
        planes_permitidos = config_usuario.get("planes_luz", [])
    else:  # gas
        planes_permitidos = config_usuario.get("planes_gas", [])
    
    # Si está vacío, mostrar todos los planes activos
    if not planes_permitidos:
        return df_planes[df_planes['activo'] == True]
    
    # Si es "TODOS", mostrar todos los planes activos
    if planes_permitidos == "TODOS":
        return df_planes[df_planes['activo'] == True]
    
    # Filtrar por los planes específicos del usuario
    return df_planes[
        (df_planes['plan'].isin(planes_permitidos)) & 
        (df_planes['activo'] == True)
    ]
    
def main():
    # RESTAURACIÓN AUTOMÁTICA AL INICIAR
    if os.path.exists("data_backup"):
        # Restaurar archivos CSV
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        # Restaurar modelos de factura
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas")
    
    inicializar_datos()
    
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""

    # Verificar sesión si está autenticado
    if st.session_state.get('authenticated', False):
        if not verificar_sesion():
            mostrar_login()
            return
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        mostrar_aplicacion_principal()

def mostrar_login():
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
                
                # Guardar en localStorage
                save_js = f"""
                <script>
                localStorage.setItem('zelenza_auth_username', '{username}');
                localStorage.setItem('zelenza_auth_type', 'user');
                localStorage.setItem('zelenza_auth_time', Date.now());
                </script>
                """
                st.components.v1.html(save_js, height=0)  # ← CORREGIDO
                
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
                
                # Guardar en localStorage
                save_js = f"""
                <script>
                localStorage.setItem('zelenza_auth_username', '{admin_user}');
                localStorage.setItem('zelenza_auth_type', 'admin');
                localStorage.setItem('zelenza_auth_time', Date.now());
                </script>
                """
                st.components.v1.html(save_js, height=0)  # ← CORREGIDO
                
                st.rerun()
            # Luego como usuario normal
            elif authenticate(admin_user, admin_pass, "user"):
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = admin_user
                st.session_state.login_time = datetime.now()
                
                # Guardar en localStorage
                save_js = f"""
                <script>
                localStorage.setItem('zelenza_auth_username', '{admin_user}');
                localStorage.setItem('zelenza_auth_type', 'user');
                localStorage.setItem('zelenza_auth_time', Date.now());
                </script>
                """
                st.components.v1.html(save_js, height=0)  # ← CORREGIDO
                
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

def mostrar_aplicacion_principal():
    """Muestra la aplicación principal según el tipo de usuario"""
    st.sidebar.title(f"{'🔧 Admin' if st.session_state.user_type == 'admin' else '👤 Usuario'}")
    st.sidebar.write(f"**Usuario:** {st.session_state.username}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        # Limpiar localStorage
        clear_js = """
        <script>
        localStorage.removeItem('zelenza_auth_username');
        localStorage.removeItem('zelenza_auth_type');
        localStorage.removeItem('zelenza_auth_time');
        </script>
        """
        st.components.v1.html(clear_js, height=0)  # ← CORREGIDO
        
        # Limpiar session_state
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.rerun()
    
    st.sidebar.markdown("---")
    
    if st.session_state.user_type == "admin":
        mostrar_panel_administrador()
    else:
        mostrar_panel_usuario()

def mostrar_panel_administrador():
    """Panel de administración"""
    st.header("🔧 Panel de Administración")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "⚡ Electricidad", "🔥 Gas", "👥 Usuarios", "👁️ PVD", 
        "📄 Facturas", "☀️ Excedentes", "⚙️ Sistema"
    ])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_usuarios()
    with tab4:
        gestion_pvd_admin()
    with tab5:
        gestion_modelos_factura()
    with tab6:
        gestion_excedentes()
    with tab7:
        gestion_config_sistema()

def gestion_config_sistema():
    st.subheader("⚙️ Configuración del Sistema")
    
    config_sistema = cargar_config_sistema()
    
    st.write("### 🔐 Configuración de Acceso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        login_automatico = st.checkbox(
            "Activar login automático",
            value=config_sistema.get("login_automatico_activado", True),
            help="Los usuarios pueden entrar automáticamente sin credenciales"
        )
    
    with col2:
        horas_duracion = st.number_input(
            "Duración de sesión (horas)",
            min_value=1,
            max_value=24,
            value=config_sistema.get("sesion_horas_duracion", 8),
            help="Tiempo que dura una sesión antes de expirar"
        )
    
    if st.button("💾 Guardar Configuración Sistema", type="primary"):
        config_sistema.update({
            "login_automatico_activado": login_automatico,
            "sesion_horas_duracion": horas_duracion
        })
        guardar_config_sistema(config_sistema)
        st.success("✅ Configuración del sistema guardada")
        st.rerun()
    
def gestion_usuarios():
    st.subheader("👥 Gestión de Usuarios y Grupos")
    
    # Cargar configuración
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    # Pestañas
    tab1, tab2, tab3 = st.tabs(["👤 Usuarios", "👥 Grupos", "➕ Crear Usuario"])
    
    with tab1:
        st.write("### 📊 Lista de Usuarios")
        
        for username, config in usuarios_config.items():
            if username == "admin":
                continue
                
            with st.expander(f"👤 {username} - {config.get('nombre', 'Sin nombre')}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("Nombre", value=config.get('nombre', ''), 
                                                 key=f"nombre_{username}")
                    
                    # Selección de grupo
                    grupo_actual = config.get('grupo', '')
                    grupo_seleccionado = st.selectbox(
                        "Grupo",
                        [""] + list(grupos.keys()),
                        index=0 if not grupo_actual else (list(grupos.keys()).index(grupo_actual) + 1),
                        key=f"grupo_{username}"
                    )
                    
                    # Campo para cambiar contraseña
                    st.write("**🔐 Cambiar contraseña:**")
                    nueva_password = st.text_input(
                        "Nueva contraseña",
                        type="password",
                        placeholder="Dejar vacío para no cambiar",
                        key=f"pass_{username}"
                    )
                    if nueva_password:
                        st.info("⚠️ La contraseña se cambiará al guardar")
                
                with col2:
                    # Mostrar permisos basados en grupo
                    if grupo_seleccionado and grupo_seleccionado in grupos:
                        permisos = grupos[grupo_seleccionado]
                        st.write("**Permisos del grupo:**")
                        st.write(f"📈 Luz: {', '.join(permisos.get('planes_luz', []))}")
                        st.write(f"🔥 Gas: {', '.join(permisos.get('planes_gas', []))}")
                    
                    # Información adicional del usuario
                    st.write("**Información:**")
                    st.write(f"📧 Username: `{username}`")
                    st.write(f"🔑 Tipo: {config.get('tipo', 'user')}")
                    
                    # Botones de acción
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar", key=f"save_{username}"):
                            usuarios_config[username]['nombre'] = nuevo_nombre
                            usuarios_config[username]['grupo'] = grupo_seleccionado
                            
                            # Actualizar contraseña si se proporcionó
                            if nueva_password:
                                usuarios_config[username]['password'] = nueva_password
                                st.success(f"✅ Contraseña actualizada para {username}")
                            
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} actualizado")
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Eliminar", key=f"del_{username}"):
                            del usuarios_config[username]
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} eliminado")
                            st.rerun()
    
    with tab2:
        st.write("### 👥 Gestión de Grupos")
        
        for grupo_nombre, permisos in grupos.items():
            with st.expander(f"**Grupo: {grupo_nombre}**", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Planes de Luz**")
                    try:
                        df_luz = pd.read_csv("data/precios_luz.csv")
                        planes_luz_disponibles = df_luz['plan'].tolist()
                    except:
                        planes_luz_disponibles = []
                    
                    planes_luz_actuales = permisos.get('planes_luz', [])
                    if planes_luz_actuales == ["TODOS"]:
                        planes_luz_actuales = planes_luz_disponibles
                    
                    planes_luz_seleccionados = st.multiselect(
                        "Planes de luz permitidos",
                        planes_luz_disponibles,
                        default=planes_luz_actuales,
                        key=f"grupo_luz_{grupo_nombre}"
                    )
                
                with col2:
                    st.write("**Planes de Gas**")
                    planes_gas_disponibles = ["RL1", "RL2", "RL3"]
                    planes_gas_actuales = permisos.get('planes_gas', [])
                    
                    planes_gas_seleccionados = st.multiselect(
                        "Planes de gas permitidos",
                        planes_gas_disponibles,
                        default=planes_gas_actuales,
                        key=f"grupo_gas_{grupo_nombre}"
                    )
                
                if st.button("💾 Actualizar Grupo", key=f"update_grupo_{grupo_nombre}"):
                    grupos[grupo_nombre] = {
                        "planes_luz": planes_luz_seleccionados,
                        "planes_gas": planes_gas_seleccionados
                    }
                    config_sistema['grupos_usuarios'] = grupos
                    guardar_config_sistema(config_sistema)
                    st.success(f"✅ Grupo {grupo_nombre} actualizado")
                    st.rerun()
        
        # Crear nuevo grupo
        st.write("### ➕ Crear Nuevo Grupo")
        nuevo_grupo_nombre = st.text_input("Nombre del nuevo grupo")
        
        if st.button("Crear Grupo") and nuevo_grupo_nombre:
            if nuevo_grupo_nombre not in grupos:
                grupos[nuevo_grupo_nombre] = {
                    "planes_luz": [],
                    "planes_gas": []
                }
                config_sistema['grupos_usuarios'] = grupos
                guardar_config_sistema(config_sistema)
                st.success(f"✅ Grupo {nuevo_grupo_nombre} creado")
                st.rerun()
            else:
                st.error("❌ El grupo ya existe")
    
    with tab3:
        st.write("### 👤 Crear Nuevo Usuario")
        
        with st.form("form_nuevo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_username = st.text_input("Username*", 
                                              help="Nombre de usuario para el acceso")
                nuevo_nombre = st.text_input("Nombre completo*", 
                                            help="Nombre real del usuario")
                grupo_usuario = st.selectbox("Grupo", [""] + list(grupos.keys()),
                                           help="Asigna un grupo de permisos")
            
            with col2:
                # Campo para contraseña
                password_usuario = st.text_input(
                    "Contraseña*", 
                    type="password",
                    help="Contraseña para acceso manual"
                )
                confirm_password = st.text_input(
                    "Confirmar contraseña*", 
                    type="password",
                    help="Repite la contraseña"
                )
                
                # Opciones adicionales
                tipo_usuario = st.selectbox(
                    "Tipo de usuario",
                    ["user", "auto", "manual"],
                    help="user: Usuario normal, auto: Autogenerado, manual: Creado manualmente"
                )
                
                # Checkbox para planes específicos
                st.write("**Planes especiales:**")
                planes_luz_todos = st.checkbox("Todos los planes de luz", value=True)
                planes_gas_todos = st.checkbox("Todos los planes de gas", value=True)
            
            submitted = st.form_submit_button("👤 Crear Usuario")
            
            if submitted:
                if not nuevo_username or not nuevo_nombre:
                    st.error("❌ Username y nombre son obligatorios")
                elif not password_usuario:
                    st.error("❌ La contraseña es obligatoria")
                elif password_usuario != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif nuevo_username in usuarios_config:
                    st.error("❌ El username ya existe")
                else:
                    # Configurar planes según selección
                    planes_luz = "TODOS" if planes_luz_todos else []
                    planes_gas = ["RL1", "RL2", "RL3"] if planes_gas_todos else []
                    
                    # Crear usuario
                    usuarios_config[nuevo_username] = {
                        "nombre": nuevo_nombre,
                        "password": password_usuario,
                        "grupo": grupo_usuario,
                        "tipo": tipo_usuario,
                        "planes_luz": planes_luz,
                        "planes_gas": planes_gas,
                        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "creado_por": st.session_state.username
                    }
                    
                    guardar_configuracion_usuarios(usuarios_config)
                    
                    # Mostrar resumen
                    st.success(f"✅ Usuario {nuevo_username} creado exitosamente")
                    st.info(f"""
                    **Resumen del usuario creado:**
                    - **Username:** `{nuevo_username}`
                    - **Nombre:** {nuevo_nombre}
                    - **Grupo:** {grupo_usuario if grupo_usuario else 'Ninguno'}
                    - **Tipo:** {tipo_usuario}
                    - **Contraseña:** {'✓ Configurada'}
                    - **Planes luz:** {'Todos' if planes_luz_todos else 'Específicos'}
                    - **Planes gas:** {'Todos' if planes_gas_todos else 'Específicos'}
                    """)
                    
                    # Mostrar credenciales
                    credenciales = f"Usuario: {nuevo_username}\nContraseña: {password_usuario}"
                    st.code(credenciales, language="text")
                    
                    st.rerun()

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    # Mostrar información del usuario
    if st.session_state.username in cargar_configuracion_usuarios():
        config = cargar_configuracion_usuarios()[st.session_state.username]
        st.header(f"👤 {config.get('nombre', 'Usuario')}")
    else:
        st.header("👤 Portal del Cliente")
    
    # PRIMERA PANTALLA: Consultar modelos de factura
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Comparativas
    st.subheader("🧮 Comparativas")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Comparativa EXACTA", "📅 Comparativa ESTIMADA", "🔥 Gas", "👁️ PVD", "📋 CUPS Naturgy"])
    
    with tab1:
        comparativa_exacta()
    with tab2:
        comparativa_estimada()
    with tab3:
        calculadora_gas()
    with tab4:
        gestion_pvd_usuario()
    with tab5:
        cups_naturgy()

# --- LISTA DE COMUNIDADES AUTÓNOMAS ---
COMUNIDADES_AUTONOMAS = [
    "Toda España",
    "Andalucía",
    "Aragón",
    "Asturias",
    "Baleares",
    "Canarias",
    "Cantabria",
    "Castilla-La Mancha",
    "Castilla y León",
    "Cataluña",
    "Comunidad Valenciana",
    "Extremadura",
    "Galicia",
    "Madrid",
    "Murcia",
    "Navarra",
    "País Vasco",
    "La Rioja",
    "Ceuta",
    "Melilla"
]

# --- ESTRUCTURA DE PLANES DE GAS ---
PLANES_GAS_ESTRUCTURA = {
    "RL1": {
        "precio_original_kwh": 0.045,
        "termino_variable_con_pmg": 0.038,
        "termino_variable_sin_pmg": 0.042,
        "termino_fijo_con_pmg": 8.5,
        "termino_fijo_sin_pmg": 9.2,
        "rango": "0-5000 kWh anuales",
        "activo": True
    },
    "RL2": {
        "precio_original_kwh": 0.043,
        "termino_variable_con_pmg": 0.036,
        "termino_variable_sin_pmg": 0.040,
        "termino_fijo_con_pmg": 12.0,
        "termino_fijo_sin_pmg": 13.0,
        "rango": "5000-15000 kWh anuales",
        "activo": True
    },
    "RL3": {
        "precio_original_kwh": 0.041,
        "termino_variable_con_pmg": 0.034,
        "termino_variable_sin_pmg": 0.038,
        "termino_fijo_con_pmg": 18.0,
        "termino_fijo_sin_pmg": 19.5,
        "rango": "15000-50000 kWh anuales",
        "activo": True
    }
}

# Configuración PMG
PMG_COSTE = 9.95
PMG_IVA = 0.21  # 21%

# --- FUNCIONES DE ADMINISTRADOR (ACTUALIZADAS) ---
def gestion_electricidad():
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
    # --- RESET TEMPORAL CON CONFIRMACIÓN ---
    st.error("🚨 RESET TEMPORAL DE DATOS")
    
    # Inicializar estado de confirmación de reset
    if 'show_reset_confirmation' not in st.session_state:
        st.session_state.show_reset_confirmation = False
    
    if not st.session_state.show_reset_confirmation:
        if st.button("🔄 Resetear datos a vacío (SOLO PRIMERA VEZ)", type="secondary"):
            st.session_state.show_reset_confirmation = True
            st.rerun()
    else:
        st.warning("⚠️ ¿ESTÁS SEGURO DE QUE QUIERES RESETEAR LOS DATOS?")
        st.error("🚨 ESTA ACCIÓN ELIMINARÁ TODOS LOS PLANES EXISTENTES Y NO SE PUEDE DESHACER")
        
        col_reset_confirm, col_reset_cancel = st.columns(2)
        with col_reset_confirm:
            if st.button("✅ SÍ, RESETEAR TODO", type="primary"):
                df_vacio = pd.DataFrame(columns=[
                    'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                    'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
                    'comunidades_autonomas'
                ])
                df_vacio.to_csv("data/precios_luz.csv", index=False)
                # Hacer backup también del reset
                os.makedirs("data_backup", exist_ok=True)
                df_vacio.to_csv("data_backup/precios_luz.csv", index=False)
                st.success("✅ Datos reseteados correctamente. Ahora puedes crear tus propios planes.")
                st.session_state.show_reset_confirmation = False
                # Limpiar también otros estados si existen
                if hasattr(st.session_state, 'editing_plan'):
                    st.session_state.editing_plan = None
                if hasattr(st.session_state, 'show_confirmation'):
                    st.session_state.show_confirmation = False
                st.rerun()
        
        with col_reset_cancel:
            if st.button("❌ Cancelar reset", type="secondary"):
                st.session_state.show_reset_confirmation = False
                st.info("Reset cancelado")
                st.rerun()
    # --- FIN RESET TEMPORAL CON CONFIRMACIÓN ---
    
    # Explicación del campo "activo"
    with st.expander("💡 ¿Qué significa 'Plan activo'?"):
        st.info("""
        **Plan Activo = ✅** → El plan aparece en las calculadoras para los usuarios
        **Plan Inactivo = ❌** → El plan NO aparece en las calculadoras (pero se mantiene en el sistema)
        
        *Útil para desactivar planes temporales o promociones finalizadas sin eliminarlos.*
        """)
    
    # Cargar datos actuales
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        # Si el DataFrame está vacío, crear uno nuevo
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
                'comunidades_autonomas'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
            'comunidades_autonomas'
        ])
    
    # Mostrar datos actuales con opción de edición
    st.write("### 📊 Planes Actuales")
    if not df_luz.empty:
        # Crear columnas para mostrar planes
        cols = st.columns(3)
        planes_activos = df_luz[df_luz['activo'] == True]
        planes_inactivos = df_luz[df_luz['activo'] == False]
        
        with cols[0]:
            st.write("**✅ Planes Activos**")
            for _, plan in planes_activos.iterrows():
                if st.button(
                    f"📝 {plan['plan']}", 
                    key=f"edit_{plan['plan']}",
                    use_container_width=True
                ):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with cols[1]:
            st.write("**❌ Planes Inactivos**")
            for _, plan in planes_inactivos.iterrows():
                if st.button(
                    f"📝 {plan['plan']}", 
                    key=f"edit_inactive_{plan['plan']}",
                    use_container_width=True
                ):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with cols[2]:
            st.write("**📈 Resumen**")
            st.metric("Planes Activos", len(planes_activos))
            st.metric("Planes Inactivos", len(planes_inactivos))
            st.metric("Total Planes", len(df_luz))
            
    else:
        st.info("No hay planes configurados aún")
    
    # Formulario para añadir/editar planes
    st.write("### ➕ Añadir/✏️ Editar Plan")
    
    # Inicializar estado de edición si no existe
    if 'editing_plan' not in st.session_state:
        st.session_state.editing_plan = None
    
    # Si estamos editando, mostrar info
    if st.session_state.editing_plan is not None:
        plan_actual = st.session_state.editing_plan
        st.warning(f"✏️ Editando: **{plan_actual['plan']}**")
        
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_plan = None
            st.rerun()
    
    # Inicializar estado de confirmación
    if 'show_confirmation' not in st.session_state:
        st.session_state.show_confirmation = False
    if 'pending_plan' not in st.session_state:
        st.session_state.pending_plan = None
    if 'pending_action' not in st.session_state:
        st.session_state.pending_action = None
    
    # FORMULARIO PRINCIPAL
    with st.form("form_plan_electricidad"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Si estamos editando, bloquear el nombre
            if st.session_state.editing_plan is not None:
                nombre_plan = st.text_input("Nombre del Plan*", 
                                          value=st.session_state.editing_plan['plan'],
                                          disabled=True)
                st.info("⚠️ El nombre no se puede modificar al editar")
            else:
                nombre_plan = st.text_input("Nombre del Plan*", placeholder="Ej: IMPULSA 24h")
            
            precio_original = st.number_input("Precio Original kWh*", min_value=0.0, format="%.3f", 
                                            value=st.session_state.editing_plan['precio_original_kwh'] if st.session_state.editing_plan else 0.170)
            con_pi = st.number_input("Con PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan['con_pi_kwh'] if st.session_state.editing_plan else 0.130)
        
        with col2:
            sin_pi = st.number_input("Sin PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan['sin_pi_kwh'] if st.session_state.editing_plan else 0.138)
            punta = st.number_input("Punta €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan['punta'] if st.session_state.editing_plan else 0.116)
            valle = st.number_input("Valle €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan['valle'] if st.session_state.editing_plan else 0.046)
        
        with col3:
            # Calcular automáticamente el total de potencia
            total_potencia = punta + valle
            st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                          value=total_potencia, disabled=True, key="total_potencia_display")
            st.caption("💡 Calculado automáticamente: Punta + Valle")
            
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan['activo'] if st.session_state.editing_plan else True)
        
        # NUEVO: Selección de comunidades autónomas
        st.write("### 🗺️ Comunidades Autónomas Disponibles")
        st.info("Selecciona en qué comunidades autónomas está disponible este plan")
        
        # Obtener comunidades actuales si estamos editando
        comunidades_actuales = []
        if st.session_state.editing_plan and 'comunidades_autonomas' in st.session_state.editing_plan:
            if pd.notna(st.session_state.editing_plan['comunidades_autonomas']):
                comunidades_actuales = st.session_state.editing_plan['comunidades_autonomas'].split(';')
        
        # Por defecto, seleccionar "Toda España" para nuevos planes
        if not st.session_state.editing_plan:
            comunidades_actuales = ["Toda España"]
        
        comunidades_seleccionadas = st.multiselect(
            "Comunidades donde está disponible el plan:",
            COMUNIDADES_AUTONOMAS,
            default=comunidades_actuales,
            help="Selecciona las comunidades autónomas donde este plan está disponible"
        )
        
        # Si no se selecciona ninguna, mostrar advertencia
        if not comunidades_seleccionadas:
            st.warning("⚠️ Debes seleccionar al menos una comunidad autónoma")
        
        # BOTÓN DE SUBMIT
        if st.session_state.editing_plan is not None:
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
            action_type = "actualizar"
        else:
            submitted = st.form_submit_button("➕ Crear Nuevo Plan", type="primary")
            action_type = "crear"
        
        if submitted:
            if not nombre_plan:
                st.error("❌ El nombre del plan es obligatorio")
            elif not comunidades_seleccionadas:
                st.error("❌ Debes seleccionar al menos una comunidad autónoma")
            else:
                # Preparar datos para confirmación
                nuevo_plan_data = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo,
                    'comunidades_autonomas': ';'.join(comunidades_seleccionadas)
                }
                
                # Si estamos editando, mantener el umbral existente
                if st.session_state.editing_plan is not None and 'umbral_especial_plus' in st.session_state.editing_plan:
                    nuevo_plan_data['umbral_especial_plus'] = st.session_state.editing_plan['umbral_especial_plus']
                else:
                    # Para nuevos planes, establecer umbral por defecto solo si es ESPECIAL PLUS
                    if "ESPECIAL PLUS" in nombre_plan.upper():
                        nuevo_plan_data['umbral_especial_plus'] = 15.00
                    else:
                        nuevo_plan_data['umbral_especial_plus'] = 0.00
                
                st.session_state.pending_plan = nuevo_plan_data
                st.session_state.pending_action = action_type
                st.session_state.show_confirmation = True
                st.rerun()
    
    # MOSTRAR CONFIRMACIÓN (FUERA DEL FORM)
    if st.session_state.show_confirmation:
        st.markdown("---")
        st.warning("⚠️ CONFIRMACIÓN REQUERIDA")
        
        if st.session_state.pending_action == "actualizar":
            st.write(f"¿Estás seguro de que quieres ACTUALIZAR el plan '{st.session_state.pending_plan['plan']}'?")
        else:
            st.write(f"¿Estás seguro de que quieres CREAR el nuevo plan '{st.session_state.pending_plan['plan']}'?")
        
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ Sí, confirmar", type="primary", key="confirm_yes"):
                # Ejecutar la acción
                nuevo_plan = st.session_state.pending_plan
                
                # Añadir o actualizar el plan
                if nuevo_plan['plan'] in df_luz['plan'].values:
                    # Actualizar plan existente
                    idx = df_luz[df_luz['plan'] == nuevo_plan['plan']].index[0]
                    for key, value in nuevo_plan.items():
                        df_luz.at[idx, key] = value
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' actualizado correctamente")
                else:
                    # Añadir nuevo plan
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan])], ignore_index=True)
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' añadido correctamente")
                
                # Guardar y hacer BACKUP
                df_luz.to_csv("data/precios_luz.csv", index=False)
                os.makedirs("data_backup", exist_ok=True)
                shutil.copy("data/precios_luz.csv", "data_backup/precios_luz.csv")
                
                st.session_state.editing_plan = None
                st.session_state.show_confirmation = False
                st.session_state.pending_plan = None
                st.session_state.pending_action = None
                st.rerun()
        
        with col_cancel:
            if st.button("❌ Cancelar", type="secondary", key="confirm_no"):
                st.session_state.show_confirmation = False
                st.session_state.pending_plan = None
                st.session_state.pending_action = None
                st.info("Operación cancelada")
                st.rerun()
    
    # --- NUEVA SECCIÓN: CONFIGURACIÓN UMBRAL ESPECIAL PLUS ---
    st.markdown("---")
    st.write("### 🎯 Configuración Especial - Plan ESPECIAL PLUS")
    
    with st.expander("💡 ¿Qué es el Umbral Especial PLUS?"):
        st.info("""
        **Regla ESPECIAL PLUS**: Este plan solo aparece si el máximo ahorro de otros planes es MENOR que este umbral.
        
        **Ejemplo**:
        - Umbral: 15€
        - Ahorro máximo otros planes: 17€ → ❌ ESPECIAL PLUS NO aparece (17 > 15)
        - Ahorro máximo otros planes: 14€ → ✅ ESPECIAL PLUS SÍ aparece (14 < 15)
        
        *Útil para mostrar planes con permanencia solo cuando el ahorro es limitado.*
        """)
    
    # Buscar si existe el plan ESPECIAL PLUS
    plan_especial_plus = None
    if not df_luz.empty:
        especial_plus_planes = df_luz[df_luz['plan'].str.contains('ESPECIAL PLUS', case=False, na=False)]
        if not especial_plus_planes.empty:
            plan_especial_plus = especial_plus_planes.iloc[0]
    
    if plan_especial_plus is not None:
        st.write(f"**Plan encontrado:** {plan_especial_plus['plan']}")
        
        # Formulario para configurar el umbral
        with st.form("form_umbral_especial_plus"):
            col_umb1, col_umb2 = st.columns([2, 1])
            
            with col_umb1:
                nuevo_umbral = st.number_input(
                    "Umbral de aparición (€)", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=float(plan_especial_plus.get('umbral_especial_plus', 15.00)),
                    format="%.2f",
                    help="El plan ESPECIAL PLUS aparecerá solo si el máximo ahorro de otros planes es menor a este valor"
                )
            
            with col_umb2:
                st.write("")  # Espacio vertical
                st.write("")  # Espacio vertical
                submitted_umbral = st.form_submit_button("💾 Guardar Umbral", type="primary")
            
            if submitted_umbral:
                # Actualizar el umbral en el plan ESPECIAL PLUS
                idx = df_luz[df_luz['plan'] == plan_especial_plus['plan']].index[0]
                df_luz.at[idx, 'umbral_especial_plus'] = nuevo_umbral
                df_luz.to_csv("data/precios_luz.csv", index=False)
                # Hacer BACKUP
                os.makedirs("data_backup", exist_ok=True)
                shutil.copy("data/precios_luz.csv", "data_backup/precios_luz.csv")
                st.success(f"✅ Umbral actualizado a {nuevo_umbral}€ para {plan_especial_plus['plan']}")
                st.rerun()
        
        # Mostrar estado actual
        umbral_actual = plan_especial_plus.get('umbral_especial_plus', 15.00)
        st.info(f"**Estado actual:** Umbral = {umbral_actual}€ | El plan aparecerá si el ahorro máximo es < {umbral_actual}€")
    
    else:
        st.warning("⚠️ No se encontró ningún plan 'ESPECIAL PLUS'")
        st.info("Para usar esta función, crea un plan que contenga 'ESPECIAL PLUS' en su nombre")
    
    # Opción para eliminar planes (FUERA DE CUALQUIER FORM)
    if not df_luz.empty and st.session_state.editing_plan is None and not st.session_state.show_confirmation:
        st.markdown("---")
        st.write("### 🗑️ Eliminar Plan")
        plan_a_eliminar = st.selectbox("Selecciona plan a eliminar", df_luz['plan'].unique())
        
        if st.button("Eliminar Plan Seleccionado", type="secondary"):
            st.session_state.pending_elimination = plan_a_eliminar
            st.rerun()
    
    # Confirmación para eliminación
    if hasattr(st.session_state, 'pending_elimination'):
        st.markdown("---")
        st.error("🚨 ELIMINACIÓN PERMANENTE")
        st.write(f"¿Estás seguro de que quieres ELIMINAR permanentemente el plan '{st.session_state.pending_elimination}'?")
        
        col_conf_del, col_can_del = st.columns(2)
        with col_conf_del:
            if st.button("✅ Sí, eliminar", type="primary"):
                df_luz = df_luz[df_luz['plan'] != st.session_state.pending_elimination]
                df_luz.to_csv("data/precios_luz.csv", index=False)
                # Hacer BACKUP
                os.makedirs("data_backup", exist_ok=True)
                shutil.copy("data/precios_luz.csv", "data_backup/precios_luz.csv")
                st.success(f"✅ Plan '{st.session_state.pending_elimination}' eliminado correctamente")
                if hasattr(st.session_state, 'pending_elimination'):
                    del st.session_state.pending_elimination
                st.rerun()
        
        with col_can_del:
            if st.button("❌ Cancelar eliminación"):
                if hasattr(st.session_state, 'pending_elimination'):
                    del st.session_state.pending_elimination
                st.info("Eliminación cancelada")
                st.rerun()

def gestion_gas():
    st.subheader("🔥 Gestión de Planes de Gas")
    
    # Cargar datos actuales
    try:
        with open('data/planes_gas.json', 'r') as f:
            planes_gas = json.load(f)
    except:
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    # Configuración PMG
    st.write("### ⚙️ Configuración PMG (Pack Mantenimiento Gas)")
    
    col_pmg1, col_pmg2 = st.columns(2)
    with col_pmg1:
        pmg_coste = st.number_input("Coste PMG (€/mes):", value=PMG_COSTE, min_value=0.0, format="%.2f")
    with col_pmg2:
        pmg_iva = st.number_input("IVA PMG (%):", value=PMG_IVA * 100, min_value=0.0, max_value=100.0, format="%.1f") / 100
    
    if st.button("💾 Guardar Configuración PMG", key="guardar_pmg"):
        config_pmg = {"coste": pmg_coste, "iva": pmg_iva}
        with open('data/config_pmg.json', 'w') as f:
            json.dump(config_pmg, f, indent=4)
        st.success("✅ Configuración PMG guardada")
    
    st.markdown("---")
    
    # Gestión de planes RL
    st.write("### 📊 Planes de Gas RL1, RL2, RL3")
    
    # Mostrar planes actuales
    for rl, plan in planes_gas.items():
        with st.expander(f"**{rl}** - {plan['rango']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Términos CON PMG**")
                plan["termino_fijo_con_pmg"] = st.number_input(
                    f"Término fijo CON PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_con_{rl}"
                )
                plan["termino_variable_con_pmg"] = st.number_input(
                    f"Término variable CON PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_con_{rl}"
                )
            
            with col2:
                st.write("**Términos SIN PMG**")
                plan["termino_fijo_sin_pmg"] = st.number_input(
                    f"Término fijo SIN PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_sin_{rl}"
                )
                plan["termino_variable_sin_pmg"] = st.number_input(
                    f"Término variable SIN PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_sin_{rl}"
                )
            
            plan["precio_original_kwh"] = st.number_input(
                f"Precio original kWh (€) - {rl}:",
                value=float(plan["precio_original_kwh"]),
                min_value=0.0,
                format="%.3f",
                key=f"precio_{rl}"
            )
            
            plan["activo"] = st.checkbox(f"Plan activo - {rl}", 
                                       value=plan["activo"],
                                       key=f"activo_{rl}")
    
    # Botón para guardar todos los planes
    if st.button("💾 Guardar Todos los Planes de Gas", type="primary"):
        # Asegurar directorio
        os.makedirs('data', exist_ok=True)
        
        with open('data/planes_gas.json', 'w') as f:
            json.dump(planes_gas, f, indent=4)
        
        # Hacer BACKUP
        os.makedirs("data_backup", exist_ok=True)
        shutil.copy("data/planes_gas.json", "data_backup/planes_gas.json")
        
        st.success("✅ Todos los planes de gas guardados correctamente")
        st.rerun()
    
    # Información de rangos
    st.markdown("---")
    st.write("### 📋 Rangos de Consumo Automáticos")
    st.info("""
    **RL1**: 0 - 5,000 kWh anuales  
    **RL2**: 5,001 - 15,000 kWh anuales  
    **RL3**: 15,001 - 50,000 kWh anuales
    
    *El RL se determina automáticamente según el consumo anual introducido*
    """)

# --- FUNCIONES PVD ---
def cargar_config_pvd():
    """Carga la configuración del sistema PVD con migración automática"""
    try:
        with open('data/config_pvd.json', 'r') as f:
            config = json.load(f)
            
        # MIGRACIÓN: Si existe el campo antiguo 'duracion_pvd', migrar a los nuevos campos
        if 'duracion_pvd' in config and 'duracion_corta' not in config:
            duracion_antigua = config['duracion_pvd']
            config['duracion_corta'] = duracion_antigua
            config['duracion_larga'] = duracion_antigua * 2  # La larga es el doble por defecto
            
            # Guardar la configuración migrada
            guardar_config_pvd(config)
            print(f"✅ Config PVD migrada: duracion_pvd={duracion_antigua} -> corta={duracion_antigua}, larga={duracion_antigua*2}")
        
        # Asegurar que todos los campos existan
        campos_requeridos = ['agentes_activos', 'maximo_simultaneo', 'duracion_corta', 'duracion_larga', 'sonido_activado']
        for campo in campos_requeridos:
            if campo not in config:
                config[campo] = PVD_CONFIG_DEFAULT[campo]
        
        return config
    except FileNotFoundError:
        # Si no existe el archivo, crear uno nuevo
        return PVD_CONFIG_DEFAULT.copy()
    except json.JSONDecodeError:
        # Si el archivo está corrupto
        return PVD_CONFIG_DEFAULT.copy()

def guardar_config_pvd(config):
    """Guarda la configuración PVD asegurando todos los campos"""
    # Asegurar que todos los campos estén presentes
    for campo, valor in PVD_CONFIG_DEFAULT.items():
        if campo not in config:
            config[campo] = valor
    
    os.makedirs('data', exist_ok=True)
    with open('data/config_pvd.json', 'w') as f:
        json.dump(config, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/config_pvd.json', 'data_backup/config_pvd.json')

def cargar_cola_pvd():
    """Carga la cola actual de PVD"""
    try:
        with open('data/cola_pvd.json', 'r') as f:
            return json.load(f)
    except:
        return []

def guardar_cola_pvd(cola):
    """Guarda la cola PVD"""
    os.makedirs('data', exist_ok=True)
    with open('data/cola_pvd.json', 'w') as f:
        json.dump(cola, f, indent=4)
    # Backup
    os.makedirs('data_backup', exist_ok=True)
    shutil.copy('data/cola_pvd.json', 'data_backup/cola_pvd.json')

def filtrar_planes_por_usuario(df_planes, username, tipo_plan="luz"):
    """Filtra los planes según el grupo del usuario"""
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    if username not in usuarios_config:
        return df_planes[df_planes['activo'] == True]
    
    config_usuario = usuarios_config[username]
    grupo_usuario = config_usuario.get('grupo')
    
    # Si no tiene grupo o el grupo no existe, usar configuración individual antigua
    if not grupo_usuario or grupo_usuario not in grupos:
        planes_permitidos = config_usuario.get(f"planes_{tipo_plan}", [])
    else:
        # Usar permisos del grupo
        permisos_grupo = grupos[grupo_usuario]
        planes_permitidos = permisos_grupo.get(f"planes_{tipo_plan}", [])
    
    # Si está vacío, mostrar todos los planes activos
    if not planes_permitidos:
        return df_planes[df_planes['activo'] == True]
    
    # Si es "TODOS" (en el caso de configuración antigua), mostrar todos
    if planes_permitidos == "TODOS":
        return df_planes[df_planes['activo'] == True]
    
    # Filtrar por los planes específicos
    return df_planes[
        (df_planes['plan'].isin(planes_permitidos)) & 
        (df_planes['activo'] == True)
    ]

# --- FUNCIONES PVD CORREGIDAS ---

def gestion_pvd_admin():
    st.subheader("👁️ Administración PVD (Pausa Visual Dinámica)")
    
    # Cargar configuración
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    # --- BOTÓN DE ACTUALIZAR MANUAL ---
    col_refresh1, col_refresh2 = st.columns([3, 1])
    with col_refresh1:
        st.write("")
    with col_refresh2:
        if st.button("🔄 Actualizar Estado", key="refresh_admin", use_container_width=True):
            # Verificar y completar pausas automáticamente
            verificar_pausas_completadas(cola_pvd, config_pvd)
            st.rerun()
    
    # --- CONFIGURACIÓN DEL SISTEMA ---
    st.write("### ⚙️ Configuración del Sistema para Agentes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📊 Capacidad del Centro**")
        agentes_activos = st.number_input(
            "Total de Agentes Trabajando",
            min_value=1,
            max_value=100,
            value=config_pvd['agentes_activos'],
            help="Número total de agentes que están trabajando actualmente en el call center"
        )
    
    with col2:
        st.write("**⏱️ Límites de Pausas**")
        maximo_simultaneo = st.number_input(
            "Máximo en Pausa Simultáneamente",
            min_value=1,
            max_value=50,
            value=config_pvd['maximo_simultaneo'],
            help="Máximo número de agentes que pueden estar en pausa al mismo tiempo. Los demás esperan en cola."
        )
    
    st.write("**🕐 Duración de Pausas**")
    col_dura1, col_dura2 = st.columns(2)
    with col_dura1:
        duracion_corta = st.number_input(
            "Duración Pausa Corta (minutos)",
            min_value=1,
            max_value=30,
            value=config_pvd['duracion_corta'],
            help="Duración de la pausa corta (ej: 5 minutos)"
        )
    with col_dura2:
        duracion_larga = st.number_input(
            "Duración Pausa Larga (minutos)",
            min_value=1,
            max_value=60,
            value=config_pvd['duracion_larga'],
            help="Duración de la pausa larga (ej: 10 minutos)"
        )
    
    sonido_activado = st.checkbox(
        "Activar sonido de notificación",
        value=config_pvd.get('sonido_activado', True),
        help="Reproduce sonido cuando sea el turno de un agente"
    )
    
    if st.button("💾 Guardar Configuración", type="primary"):
        config_pvd.update({
            'agentes_activos': agentes_activos,
            'maximo_simultaneo': maximo_simultaneo,
            'duracion_corta': duracion_corta,
            'duracion_larga': duracion_larga,
            'sonido_activado': sonido_activado
        })
        guardar_config_pvd(config_pvd)
        st.success("✅ Configuración PVD guardada")
        st.rerun()
    
    # --- VERIFICAR Y ACTUALIZAR ESTADO AUTOMÁTICAMENTE ---
    verificar_pausas_completadas(cola_pvd, config_pvd)
    
    # --- ESTADÍSTICAS ACTUALES ---
    st.markdown("---")
    st.write("### 📊 Estado Actual del Sistema")
    
    # Calcular estadísticas actualizadas
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
    completados_hoy = len([p for p in cola_pvd if p['estado'] == 'COMPLETADO' and 
                          datetime.fromisoformat(p.get('timestamp_fin', datetime.now().isoformat())).date() == datetime.now().date()])
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("👥 Agentes Trabajando", agentes_activos)
    with col_stat2:
        st.metric("⏸️ En Pausa Ahora", f"{en_pausa}/{maximo_simultaneo}")
    with col_stat3:
        st.metric("⏳ Esperando", en_espera)
    with col_stat4:
        st.metric("✅ Completadas Hoy", completados_hoy)
    
    # --- GESTIÓN DE PAUSAS ACTIVAS ---
    st.markdown("---")
    st.write("### 📋 Pausas en Curso")
    
    pausas_en_curso = [p for p in cola_pvd if p['estado'] == 'EN_CURSO']
    
    if pausas_en_curso:
        for pausa in pausas_en_curso:
            with st.container():
                col_info, col_acciones = st.columns([3, 1])
                
                with col_info:
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    # Barra de progreso
                    progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
                    st.progress(int(progreso))
                    
                    st.write(f"**Agente:** {pausa.get('usuario_nombre', 'Desconocido')}")
                    st.write(f"**Usuario ID:** {pausa['usuario_id']}")
                    st.write(f"**Duración:** {duracion_minutos} min ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
                    st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')} | **Restante:** {tiempo_restante} min")
                    
                    # Verificar si la pausa ha terminado
                    if tiempo_restante == 0:
                        st.warning("⏰ **Pausa finalizada automáticamente**")
                
                with col_acciones:
                    if st.button("✅ Finalizar", key=f"fin_{pausa['id']}"):
                        finalizar_pausa(pausa, cola_pvd)
                        st.rerun()
                    
                    if st.button("❌ Cancelar", key=f"cancel_{pausa['id']}"):
                        pausa['estado'] = 'CANCELADO'
                        guardar_cola_pvd(cola_pvd)
                        st.warning(f"⚠️ Pausa #{pausa['id']} cancelada")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("🎉 No hay pausas activas en este momento")
    
    # --- COLA DE ESPERA ---
    if en_espera > 0:
        st.write("### 📝 Cola de Espera")
        
        en_espera_lista = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        en_espera_ordenados = sorted(en_espera_lista, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        for i, pausa in enumerate(en_espera_ordenados):
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_display = f"{config_pvd['duracion_corta']} min" if duracion_elegida == 'corta' else f"{config_pvd['duracion_larga']} min"
            
            col_esp1, col_esp2, col_esp3, col_esp4 = st.columns([3, 2, 2, 1])
            with col_esp1:
                st.write(f"**#{i+1}** - {pausa.get('usuario_nombre', 'Desconocido')}")
            with col_esp2:
                st.write(f"🆔 {pausa['usuario_id']}")
            with col_esp3:
                st.write(f"⏱️ {duracion_display}")
            with col_esp4:
                if st.button("▶️ Iniciar", key=f"iniciar_{pausa['id']}"):
                    iniciar_pausa_desde_cola(pausa, cola_pvd, config_pvd)
                    st.rerun()
    
    # --- HISTORIAL RECIENTE ---
    st.markdown("---")
    st.write("### 📜 Historial Reciente (Últimas 10)")
    
    completados = [p for p in cola_pvd if p['estado'] == 'COMPLETADO']
    completados_recientes = sorted(completados, key=lambda x: x.get('timestamp_fin', ''), reverse=True)[:10]
    
    if completados_recientes:
        for pausa in completados_recientes:
            fecha_fin = datetime.fromisoformat(pausa.get('timestamp_fin', datetime.now().isoformat()))
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_display = "5 min" if duracion_elegida == 'corta' else "10 min"
            
            # Calcular tiempo transcurrido
            tiempo_finalizacion = fecha_fin.strftime('%H:%M:%S')
            st.write(f"**{tiempo_finalizacion}** - {pausa.get('usuario_nombre', 'Desconocido')} - {duracion_display}")
    else:
        st.info("No hay pausas completadas recientemente")
    
    # --- LIMPIAR HISTORIAL ---
    st.markdown("---")
    st.write("### 🧹 Mantenimiento")
    
    col_clean1, col_clean2 = st.columns(2)
    with col_clean1:
        if st.button("🗑️ Limpiar Historial Antiguo", type="secondary"):
            # Mantener solo activos y últimos 50 completados
            activos = [p for p in cola_pvd if p['estado'] in ['ESPERANDO', 'EN_CURSO']]
            completados = [p for p in cola_pvd if p['estado'] == 'COMPLETADO']
            completados = sorted(completados, key=lambda x: x.get('timestamp_fin', ''), reverse=True)[:50]
            nueva_cola = activos + completados
            guardar_cola_pvd(nueva_cola)
            st.success("✅ Historial limpiado (solo últimos 50 completados)")
            st.rerun()
    
    with col_clean2:
        if st.button("🔄 Reiniciar Sistema PVD", type="secondary"):
            # Cancelar todas las pausas activas
            for pausa in cola_pvd:
                if pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
                    pausa['estado'] = 'CANCELADO'
            guardar_cola_pvd(cola_pvd)
            st.warning("⚠️ Sistema PVD reiniciado - Todas las pausas canceladas")
            st.rerun()

def verificar_pausas_completadas(cola_pvd, config_pvd):
    """Verifica y finaliza automáticamente pausas que han terminado"""
    hubo_cambios = False
    
    for pausa in cola_pvd:
        if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
            
            if tiempo_transcurrido >= duracion_minutos:
                # Finalizar esta pausa
                pausa['estado'] = 'COMPLETADO'
                pausa['timestamp_fin'] = datetime.now().isoformat()
                hubo_cambios = True
                
                # Iniciar la siguiente en cola si hay espacio
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
    
    if hubo_cambios:
        guardar_cola_pvd(cola_pvd)
    
    return hubo_cambios

def iniciar_siguiente_en_cola(cola_pvd, config_pvd):
    """Inicia automáticamente la siguiente pausa en la cola si hay espacio"""
    # Contar pausas en curso
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    # Si hay espacio, iniciar la siguiente en cola
    if en_pausa < maximo:
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        if en_espera:
            siguiente = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))[0]
            siguiente['estado'] = 'EN_CURSO'
            siguiente['timestamp_inicio'] = datetime.now().isoformat()
            
            # Notificar al usuario
            if config_pvd.get('sonido_activado', True):
                notificar_inicio_pausa(siguiente, config_pvd)
            
            return True
    
    return False

def finalizar_pausa(pausa, cola_pvd):
    """Finaliza una pausa manualmente"""
    pausa['estado'] = 'COMPLETADO'
    pausa['timestamp_fin'] = datetime.now().isoformat()
    guardar_cola_pvd(cola_pvd)
    st.success(f"✅ Pausa #{pausa['id']} finalizada")

def iniciar_pausa_desde_cola(pausa, cola_pvd, config_pvd):
    """Inicia una pausa desde la cola de espera"""
    # Verificar si hay espacio
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    if en_pausa < maximo:
        pausa['estado'] = 'EN_CURSO'
        pausa['timestamp_inicio'] = datetime.now().isoformat()
        guardar_cola_pvd(cola_pvd)
        st.success(f"✅ Pausa #{pausa['id']} iniciada")
    else:
        st.error("❌ No hay espacio disponible. Espera a que termine alguna pausa.")

def notificar_inicio_pausa(pausa, config_pvd):
    """Envía notificación al usuario cuando su pausa inicia"""
    try:
        duracion_minutos = config_pvd['duracion_corta'] if pausa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
        mensaje = f"¡Tu pausa de {duracion_minutos} minutos ha comenzado! ⏰"
        
        # Notificación de navegador MEJORADA
        notification_js = f"""
        <script>
        // Solicitar permisos si no están concedidos
        if ("Notification" in window) {{
            if (Notification.permission === "granted") {{
                new Notification("Pausa Iniciada 🎉", {{
                    body: "{mensaje}",
                    icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png",
                    requireInteraction: true
                }});
                
                // También mostrar notificación en pantalla
                const notificationDiv = document.createElement('div');
                notificationDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4CAF50; color: white; padding: 15px; border-radius: 5px; z-index: 9999;';
                notificationDiv.innerHTML = '<strong>🎉 Pausa Iniciada</strong><br>{mensaje}';
                document.body.appendChild(notificationDiv);
                
                // Remover después de 5 segundos
                setTimeout(() => {{
                    notificationDiv.remove();
                }}, 5000);
                
            }} else if (Notification.permission !== "denied") {{
                Notification.requestPermission().then(permission => {{
                    if (permission === "granted") {{
                        new Notification("Pausa Iniciada 🎉", {{
                            body: "{mensaje}",
                            icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
                        }});
                    }}
                }});
            }}
        }}
        
        // Sonido de notificación (funciona sin HTTPS)
        function playSound() {{
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        }}
        
        // Intentar reproducir sonido
        try {{
            playSound();
        }} catch (e) {{
            console.log("Audio context no soportado:", e);
        }}
        
        // Alternativa: Audio HTML simple
        const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-alarm-digital-clock-beep-989.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => console.log("Audio falló:", e));
        </script>
        """
        st.components.v1.html(notification_js, height=0)
        
    except Exception as e:
        print(f"Error en notificación: {e}")
        # Notificación de fallback
        st.toast(f"🎉 ¡Pausa iniciada! {duracion_minutos} minutos", icon="⏰")

def solicitar_pausa(config_pvd, cola_pvd, duracion_elegida):
    """Solicita una pausa PVD para el usuario actual"""
    # Verificar límite diario de pausas del usuario
    pausas_hoy = len([p for p in cola_pvd 
                     if p['usuario_id'] == st.session_state.username and 
                     datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now().isoformat())).date() == datetime.now().date() and
                     p['estado'] != 'CANCELADO'])
    
    if pausas_hoy >= 5:
        st.warning(f"⚠️ Has alcanzado el límite de 5 pausas diarias")
        return False
    
    # Verificar si el usuario ya tiene una pausa activa o en espera
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            st.warning(f"⚠️ Ya tienes una pausa {ESTADOS_PVD.get(pausa['estado'])}. Espera a que termine.")
            return False
    
    # Crear nueva pausa
    nueva_pausa = {
        'id': str(uuid.uuid4())[:8],
        'usuario_id': st.session_state.username,
        'usuario_nombre': st.session_state.get('user_config', {}).get('nombre', 'Usuario'),
        'duracion_elegida': duracion_elegida,
        'estado': 'ESPERANDO',
        'timestamp_solicitud': datetime.now().isoformat(),
        'timestamp_inicio': None,
        'timestamp_fin': None
    }
    
    # Añadir a la cola
    cola_pvd.append(nueva_pausa)
    guardar_cola_pvd(cola_pvd)
    
    # Verificar si puede iniciar inmediatamente
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    maximo = config_pvd['maximo_simultaneo']
    
    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
    
    if en_pausa < maximo:
        st.success(f"✅ Pausa de {duracion_minutos} minutos iniciada inmediatamente")
        nueva_pausa['estado'] = 'EN_CURSO'
        nueva_pausa['timestamp_inicio'] = datetime.now().isoformat()
        
        # Notificar
        if config_pvd.get('sonido_activado', True):
            notificar_inicio_pausa(nueva_pausa, config_pvd)
    else:
        # Calcular posición en cola
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        st.info(f"⏳ Pausa solicitada. Posición en cola: #{en_espera}")
    
    guardar_cola_pvd(cola_pvd)
    return True

def enviar_notificacion_navegador(titulo, mensaje):
    """Envía notificación al navegador"""
    try:
        notification_js = f"""
        <script>
        if ("Notification" in window) {{
            if (Notification.permission === "granted") {{
                new Notification("{titulo}", {{
                    body: "{mensaje}",
                    icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
                }});
            }} else if (Notification.permission !== "denied") {{
                Notification.requestPermission().then(permission => {{
                    if (permission === "granted") {{
                        new Notification("{titulo}", {{
                            body: "{mensaje}",
                            icon: "https://cdn-icons-png.flaticon.com/512/1827/1827421.png"
                        }});
                    }}
                }});
            }}
        }}
        </script>
        """
        st.components.v1.html(notification_js, height=0)
    except Exception as e:
        print(f"Error en notificación navegador: {e}")

# REEMPLAZA el bloque del autorefresco en gestion_pvd_usuario():

def gestion_pvd_usuario():
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    # Verificar y actualizar estado automáticamente
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    verificar_pausas_completadas(cola_pvd, config_pvd)
    
    # --- CONFIGURACIÓN DE NOTIFICACIONES DEL USUARIO ---
    # Usar session_state para persistir las notificaciones
    if 'notificaciones_activas' not in st.session_state:
        st.session_state.notificaciones_activas = True
    if 'notificado_turno' not in st.session_state:
        st.session_state.notificado_turno = {}
    
    col_notif1, col_notif2 = st.columns([3, 1])
    with col_notif1:
        st.write("")
    with col_notif2:
        notif_activadas = st.checkbox(
            "🔔 Notificaciones",
            value=st.session_state.notificaciones_activas,
            key="toggle_notificaciones",
            help="Activar/desactivar notificaciones del navegador"
        )
        if notif_activadas != st.session_state.notificaciones_activas:
            st.session_state.notificaciones_activas = notif_activadas
            st.rerun()
    
    # --- BOTÓN DE ACTUALIZAR MANUAL ---
    col_ref1, col_ref2 = st.columns([3, 1])
    with col_ref1:
        # AUTO-REFRESCO con JavaScript
        auto_refresh_js = """
        <script>
        // Configurar autorefresco cada 30 segundos
        setTimeout(function() {
            window.location.reload();
        }, 30000);
        
        // Mostrar contador
        let timeLeft = 30;
        const timerElement = document.createElement('div');
        timerElement.style.cssText = 'position: fixed; top: 10px; right: 10px; background: #f0f2f6; padding: 5px 10px; border-radius: 5px; font-size: 12px; z-index: 1000;';
        document.body.appendChild(timerElement);
        
        function updateTimer() {
            timeLeft--;
            timerElement.textContent = `🕐 Auto-refresco en: ${timeLeft}s`;
            if (timeLeft <= 0) {
                timeLeft = 30;
            }
            setTimeout(updateTimer, 1000);
        }
        updateTimer();
        </script>
        """
        st.components.v1.html(auto_refresh_js, height=50)

    # Verificar si el agente ya tiene una pausa activa
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    # --- SI TIENE PAUSA ACTIVA ---
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.warning(f"⏳ **Tienes una pausa solicitada** - {estado_display}")
            
            # Mostrar información
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            # Calcular posición en cola
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = next((i+1 for i, p in enumerate(en_espera_ordenados) 
                           if p['id'] == usuario_pausa_activa['id']), 1)
            
            # Calcular pausas en curso
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            st.write(f"**Tu pausa:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Posición en cola:** #{posicion} de {len(en_espera)}")
            st.write(f"**Estado:** {en_pausa}/{maximo} pausas activas")
            
            # Verificar si es nuestro turno
            if posicion == 1 and en_pausa < maximo:
                st.success("🎯 **¡Próximo!** Serás el siguiente en salir a pausa")
                # Intentar iniciar automáticamente
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.rerun()
            else:
                tiempo_espera = ""
                if 'timestamp_solicitud' in usuario_pausa_activa:
                    tiempo_solicitud = datetime.fromisoformat(usuario_pausa_activa['timestamp_solicitud'])
                    minutos_esperando = (datetime.now() - tiempo_solicitud).seconds // 60
                    tiempo_espera = f" | Esperando: {minutos_esperando} min"
                
                st.info(f"📋 **En cola:** Posición #{posicion}{tiempo_espera}")
            
            # Botón para cancelar
            if st.button("❌ Cancelar mi pausa", type="secondary"):
                usuario_pausa_activa['estado'] = 'CANCELADO'
                guardar_cola_pvd(cola_pvd)
                st.success("✅ Pausa cancelada")
                st.rerun()
        
        elif usuario_pausa_activa['estado'] == 'EN_CURSO':
            st.success(f"✅ **Pausa en curso** - {estado_display}")
            
            # Obtener duración elegida
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(usuario_pausa_activa['timestamp_inicio'])
            tiempo_transcurrido = (datetime.now() - tiempo_inicio).seconds // 60
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            # Barra de progreso
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            col_tiempo1, col_tiempo2 = st.columns(2)
            with col_tiempo1:
                st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
            with col_tiempo2:
                st.metric("⏳ Restante", f"{tiempo_restante} min")
            
            st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')}")
            
            # Verificar si la pausa ha terminado
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada!** Puedes volver a solicitar otra si necesitas")
            
            # Botón para finalizar manualmente
            if st.button("✅ Finalizar pausa ahora", type="primary"):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now().isoformat()
                guardar_cola_pvd(cola_pvd)
                
                # Iniciar siguiente en cola
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                
                st.success("✅ Pausa completada")
                st.rerun()
    
    # --- SI NO TIENE PAUSA ACTIVA ---
    else:
        st.info("👁️ **Sistema de Pausas Visuales Dinámicas**")
        st.write("Toma una pausa para descansar la vista durante tu jornada")
        
        # Estadísticas actuales
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        maximo = config_pvd['maximo_simultaneo']
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("⏸️ En pausa", f"{en_pausa}/{maximo}")
        with col_stats2:
            st.metric("⏳ En espera", en_espera)
        with col_stats3:
            # Contar pausas del usuario hoy
            pausas_hoy = len([p for p in cola_pvd 
                            if p['usuario_id'] == st.session_state.username and 
                            datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now().isoformat())).date() == datetime.now().date() and
                            p['estado'] != 'CANCELADO'])
            st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
        
        # Verificar límite diario
        if pausas_hoy >= 5:
            st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
            st.info("Puedes tomar más pausas mañana")
        else:
            # Selección de duración
            st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
            
            # Mostrar estado actual
            espacios_libres = max(0, maximo - en_pausa)
            
            if espacios_libres > 0:
                st.success(f"✅ **HAY ESPACIO DISPONIBLE** - {espacios_libres} puesto(s) libre(s)")
            else:
                st.warning(f"⏳ **SISTEMA LLENO** - Hay {en_espera} persona(s) en cola. Te pondremos en espera.")
            
            col_dura1, col_dura2 = st.columns(2)
            with col_dura1:
                duracion_corta = config_pvd['duracion_corta']
                if st.button(
                    f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
                    use_container_width=True,
                    type="primary",
                    key="pausa_corta"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "corta")
                    st.rerun()
            
            with col_dura2:
                duracion_larga = config_pvd['duracion_larga']
                if st.button(
                    f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
                    use_container_width=True,
                    type="secondary",
                    key="pausa_larga"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "larga")
                    st.rerun()
    
    # --- VERIFICAR Y NOTIFICAR TURNO MEJORADO ---
    if config_pvd.get('sonido_activado', True) and st.session_state.get('notificaciones_activas', True):
        # Solo verificar si el usuario está en espera
        if usuario_pausa_activa and usuario_pausa_activa['estado'] == 'ESPERANDO':
            verificar_y_notificar_turno_pvd_mejorado(config_pvd, cola_pvd, usuario_pausa_activa)

def verificar_y_notificar_turno_pvd_mejorado(config_pvd, cola_pvd, usuario_pausa_activa):
    """Verifica mejorado si es el turno del usuario"""
    try:
        # Verificar si hay espacio
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        maximo = config_pvd['maximo_simultaneo']
        
        if en_pausa >= maximo:
            return False
        
        # Verificar si es el primero en la cola
        en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
        if not en_espera:
            return False
        
        en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        primer_en_cola = en_espera_ordenados[0]
        
        if primer_en_cola['id'] == usuario_pausa_activa['id']:
            # Usar session_state para evitar notificaciones repetidas
            notificacion_key = f"notificado_turno_{usuario_pausa_activa['id']}"
            
            if not st.session_state.get(notificacion_key, False):
                st.session_state[notificacion_key] = True
                
                # Notificar
                duracion_minutos = config_pvd['duracion_corta'] if usuario_pausa_activa.get('duracion_elegida', 'corta') == 'corta' else config_pvd['duracion_larga']
                
                # 1. Notificación del navegador
                titulo = "¡Es tu turno! ⏰"
                mensaje = f"Hay espacio para tu pausa de {duracion_minutos} minutos"
                enviar_notificacion_navegador(titulo, mensaje)
                
                # 2. Sonido
                audio_html = """
                <audio autoplay>
                    <source src="https://assets.mixkit.co/sfx/preview/mixkit-alarm-digital-clock-beep-989.mp3" type="audio/mpeg">
                </audio>
                <script>
                    var audio = document.querySelector('audio');
                    audio.volume = 0.7;
                    audio.play().catch(function(e) {
                        console.log('Audio error:', e);
                    });
                </script>
                """
                st.components.v1.html(audio_html, height=0)
                
                return True
    
    except Exception as e:
        print(f"Error en verificación de turno: {e}")
    
    return False

def gestion_modelos_factura():
    st.subheader("📄 Gestión de Modelos de Factura")
    
    # Crear carpeta principal si no existe
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # Obtener empresas existentes (carpetas creadas)
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### ➕ Crear Nueva Empresa")
        nueva_empresa = st.text_input("Nombre de la empresa", placeholder="Ej: MiEmpresa S.L.")
        
        if st.button("Crear Empresa") and nueva_empresa:
            # Crear carpeta para la nueva empresa
            carpeta_empresa = f"modelos_facturas/{nueva_empresa.lower().replace(' ', '_')}"
            os.makedirs(carpeta_empresa, exist_ok=True)
            # Hacer BACKUP
            if os.path.exists("modelos_facturas"):
                os.makedirs("data_backup", exist_ok=True)
                if os.path.exists("data_backup/modelos_facturas"):
                    shutil.rmtree("data_backup/modelos_facturas")
                shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
            st.success(f"✅ Empresa '{nueva_empresa}' creada correctamente")
            st.rerun()
    
    with col2:
        st.write("### 📁 Empresas Existentes")
        if empresas_existentes:
            for empresa in empresas_existentes:
                st.write(f"**{empresa}**")
        else:
            st.info("No hay empresas creadas aún")
    
    # Subir modelos para una empresa existente
    if empresas_existentes:
        st.write("### 📤 Subir Modelo de Factura")
        empresa_seleccionada = st.selectbox("Seleccionar Empresa", empresas_existentes)
        
        archivo = st.file_uploader("Subir modelo de factura", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if archivo is not None:
            # Guardar archivo
            carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
            ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
            with open(ruta_archivo, "wb") as f:
                f.write(archivo.getbuffer())
            
            # Hacer BACKUP
            if os.path.exists("modelos_facturas"):
                os.makedirs("data_backup", exist_ok=True)
                if os.path.exists("data_backup/modelos_facturas"):
                    shutil.rmtree("data_backup/modelos_facturas")
                shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
            
            st.success(f"✅ Modelo para {empresa_seleccionada} guardado correctamente")
            if archivo.type.startswith('image'):
                st.image(archivo, caption=f"Modelo de factura - {empresa_seleccionada}", use_container_width=True)
    
    # GESTIÓN Y ELIMINACIÓN DE EMPRESAS Y ARCHIVOS
    if empresas_existentes:
        st.write("### 🗑️ Gestión de Empresas y Archivos")
        
        empresa_gestion = st.selectbox("Seleccionar empresa para gestionar", empresas_existentes, key="gestion_empresa")
        carpeta_empresa = f"modelos_facturas/{empresa_gestion}"
        
        # Mostrar archivos de la empresa seleccionada
        archivos_empresa = os.listdir(carpeta_empresa) if os.path.exists(carpeta_empresa) else []
        
        if archivos_empresa:
            st.write(f"**Archivos en {empresa_gestion}:**")
            for archivo in archivos_empresa:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {archivo}")
                with col2:
                    if st.button("🗑️", key=f"del_{archivo}"):
                        ruta_archivo = os.path.join(carpeta_empresa, archivo)
                        os.remove(ruta_archivo)
                        # Hacer BACKUP después de eliminar
                        if os.path.exists("modelos_facturas"):
                            os.makedirs("data_backup", exist_ok=True)
                            if os.path.exists("data_backup/modelos_facturas"):
                                shutil.rmtree("data_backup/modelos_facturas")
                            shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                        st.success(f"✅ Archivo '{archivo}' eliminado")
                        st.rerun()
            
            # Botón para eliminar todos los archivos de la empresa
            if st.button("🗑️ Eliminar todos los archivos de esta empresa", type="secondary"):
                for archivo in archivos_empresa:
                    ruta_archivo = os.path.join(carpeta_empresa, archivo)
                    os.remove(ruta_archivo)
                # Hacer BACKUP después de eliminar
                if os.path.exists("modelos_facturas"):
                    os.makedirs("data_backup", exist_ok=True)
                    if os.path.exists("data_backup/modelos_facturas"):
                        shutil.rmtree("data_backup/modelos_facturas")
                    shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                st.success(f"✅ Todos los archivos de {empresa_gestion} eliminados")
                st.rerun()
        else:
            st.info(f"ℹ️ No hay archivos en {empresa_gestion}")
        
        # Botón para eliminar la empresa completa (solo si está vacía)
        st.markdown("---")
        if not archivos_empresa:
            if st.button("🗑️ Eliminar esta empresa", type="primary"):
                os.rmdir(carpeta_empresa)
                # Hacer BACKUP después de eliminar
                if os.path.exists("modelos_facturas"):
                    os.makedirs("data_backup", exist_ok=True)
                    if os.path.exists("data_backup/modelos_facturas"):
                        shutil.rmtree("data_backup/modelos_facturas")
                    shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                st.success(f"✅ Empresa '{empresa_gestion}' eliminada")
                st.rerun()
        else:
            st.warning("⚠️ No se puede eliminar la empresa porque tiene archivos. Elimina primero todos los archivos.")

def gestion_excedentes():
    """Gestión del pago por excedentes de placas solares"""
    st.subheader("☀️ Configuración de Excedentes Placas Solares")
    
    try:
        config_excedentes = pd.read_csv("data/config_excedentes.csv")
        precio_actual = config_excedentes.iloc[0]['precio_excedente_kwh']
    except (FileNotFoundError, pd.errors.EmptyDataError):
        precio_actual = 0.06
        config_excedentes = pd.DataFrame([{'precio_excedente_kwh': precio_actual}])
        config_excedentes.to_csv("data/config_excedentes.csv", index=False)
    
    st.info("Configura el precio que se paga por kWh de excedente de placas solares")
    
    with st.form("form_excedentes"):
        nuevo_precio = st.number_input(
            "Precio por kWh de excedente (€)",
            min_value=0.0,
            max_value=1.0,
            value=precio_actual,
            format="%.3f",
            help="Precio que se paga al cliente por cada kWh de excedente de placas solares"
        )
        
        if st.form_submit_button("💾 Guardar Precio", type="primary"):
            config_excedentes = pd.DataFrame([{'precio_excedente_kwh': nuevo_precio}])
            config_excedentes.to_csv("data/config_excedentes.csv", index=False)
            # Hacer BACKUP
            os.makedirs("data_backup", exist_ok=True)
            shutil.copy("data/config_excedentes.csv", "data_backup/config_excedentes.csv")
            st.success(f"✅ Precio de excedente actualizado a {nuevo_precio}€/kWh")
            st.rerun()
    
    st.info(f"**Precio actual:** {precio_actual}€ por kWh de excedente")

# --- FUNCIONES DE USUARIO (ACTUALIZADAS) ---
def consultar_modelos_factura():
    st.subheader("📊 Modelos de Factura")
    
    # Obtener empresas existentes (carpetas creadas por admin)
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    if not empresas_existentes:
        st.warning("⚠️ No hay modelos de factura disponibles")
        st.info("Contacta con el administrador para que configure los modelos de factura")
        return
    
    st.info("Selecciona tu compañía eléctrica para ver los modelos de factura")
    empresa_seleccionada = st.selectbox("Selecciona tu compañía eléctrica", empresas_existentes)
    
    # Mostrar modelos disponibles para esa empresa
    carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
    
    archivos = os.listdir(carpeta_empresa)
    if archivos:
        st.write(f"### 📋 Modelos disponibles para {empresa_seleccionada}:")
        
        for archivo in archivos:
            ruta_completa = os.path.join(carpeta_empresa, archivo)
            st.write(f"**Modelo:** {archivo}")
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                st.image(ruta_completa, use_container_width=True)
            st.markdown("---")
    else:
        st.warning(f"⚠️ No hay modelos de factura subidos para {empresa_seleccionada}")

def comparativa_exacta():
    st.subheader("⚡ Comparativa EXACTA")
    st.info("Compara tu consumo exacto con nuestros planes - Se muestran ambos precios CON y SIN Pack Iberdrola")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dias = st.number_input("Días del período", min_value=1, value=30, key="dias_exacta")
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_exacta")
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0, key="consumo_exacta")
    
    with col2:
        costo_actual = st.number_input("¿Cuánto pagaste? (€)", min_value=0.0, value=50.0, key="costo_exacta")
        
        # NUEVO: Selección de comunidad autónoma
        comunidad = st.selectbox(
            "Selecciona tu Comunidad Autónoma", 
            COMUNIDADES_AUTONOMAS,
            key="comunidad_exacta"
        )
        
        # Checkbox para excedentes de placas solares
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_exacta")
        excedente_kwh = 0.0
        if con_excedentes:
            excedente_kwh = st.number_input("kWh de excedente este mes", min_value=0.0, value=50.0, key="excedente_exacta")
    
    if st.button("🔍 Comparar", type="primary", key="comparar_exacta"):
        calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh)

def comparativa_estimada():
    st.subheader("📅 Comparativa ESTIMADA")
    st.info("Estima tu consumo anual con nuestros planes - Se muestran ambos precios CON y SIN Pack Iberdrola")
    
    col1, col2 = st.columns(2)
    
    with col1:
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_estimada")
        consumo_anual = st.number_input("Consumo anual estimado (kWh)", min_value=0.0, value=7500.0, key="consumo_estimada")
        # Lo que paga actualmente el cliente
        costo_mensual_actual = st.number_input("¿Cuánto pagas actualmente al mes? (€)", min_value=0.0, value=80.0, key="costo_actual_estimada")
    
    with col2:
        # NUEVO: Selección de comunidad autónoma
        comunidad = st.selectbox(
            "Selecciona tu Comunidad Autónoma", 
            COMUNIDADES_AUTONOMAS,
            key="comunidad_estimada"
        )
        
        # Checkbox para excedentes de placas solares
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_estimada")
        excedente_mensual_kwh = 0.0
        if con_excedentes:
            excedente_mensual_kwh = st.number_input("kWh de excedente mensual promedio", min_value=0.0, value=40.0, key="excedente_estimada")
    
    if st.button("📊 Calcular Estimación", type="primary", key="calcular_estimada"):
        calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh)

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    
    # Cargar planes de gas
    try:
        with open('data/planes_gas.json', 'r') as f:
            planes_gas = json.load(f)
    except:
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    # Cargar configuración PMG
    try:
        with open('data/config_pmg.json', 'r') as f:
            config_pmg = json.load(f)
        pmg_coste = config_pmg["coste"]
        pmg_iva = config_pmg["iva"]
    except:
        pmg_coste = PMG_COSTE
        pmg_iva = PMG_IVA
    
    st.info("Compara planes de gas con cálculo EXACTO o ESTIMADO - Se muestran ambos precios CON y SIN Pack Mantenimiento Gas")
    
    # Tipo de cálculo
    tipo_calculo = st.radio(
        "**Tipo de cálculo:**",
        ["📊 Estimación anual", "📈 Cálculo exacto mes actual"],
        horizontal=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if tipo_calculo == "📊 Estimación anual":
            consumo_anual = st.number_input(
                "**Consumo anual estimado (kWh):**", 
                min_value=0, value=5000, step=100
            )
            # Campo para lo que paga actualmente (anual)
            costo_actual_input = st.number_input(
                "**¿Cuánto pagas actualmente al año? (€):**",
                min_value=0.0, value=600.0, step=10.0,
                help="Introduce lo que pagas actualmente por gas al año"
            )
            costo_actual_anual = costo_actual_input
            costo_actual_mensual = costo_actual_anual / 12
            
        else:  # Cálculo exacto mes actual
            consumo_mes = st.number_input(
                "**Consumo del mes actual (kWh):**", 
                min_value=0, value=300, step=10
            )
            consumo_anual = consumo_mes * 12
            st.info(f"Consumo anual estimado: {consumo_anual:,.0f} kWh")
            
            # Campo para lo que pagó este mes
            costo_actual_input = st.number_input(
                "**¿Cuánto pagaste este mes? (€):**",
                min_value=0.0, value=50.0, step=5.0,
                help="Introduce lo que pagaste en tu última factura de gas"
            )
            costo_actual_mensual = costo_actual_input
            costo_actual_anual = costo_actual_mensual * 12
    
    with col2:
        # ELIMINAMOS el checkbox de PMG ya que mostraremos ambas opciones
        es_canarias = st.checkbox("**¿Ubicación en Canarias?**", 
                                 help="No aplica IVA en Canarias")
    
    # Determinar RL recomendado automáticamente
    rl_recomendado = determinar_rl_gas(consumo_anual)
    
    if st.button("🔄 Calcular Comparativa Gas", type="primary"):
        resultados = []
        
        usuarios_config = cargar_configuracion_usuarios()
        planes_permitidos = []
        if st.session_state.username in usuarios_config:
            config_usuario = usuarios_config[st.session_state.username]
            planes_permitidos = config_usuario.get("planes_gas", ["RL1", "RL2", "RL3"])
        else:
            planes_permitidos = ["RL1", "RL2", "RL3"]

        for rl, plan in planes_gas.items():
            if plan["activo"] and rl in planes_permitidos:
                # Calcular AMBAS opciones: CON PMG y SIN PMG
                for tiene_pmg in [True, False]:
                    coste_anual = calcular_coste_gas_completo(
                        plan, consumo_anual, tiene_pmg, es_canarias
                    )
                    coste_mensual = coste_anual / 12
                    
                    # Calcular ahorro vs precio original
                    coste_original = consumo_anual * plan["precio_original_kwh"]
                    ahorro_vs_original = coste_original - coste_anual
                    
                    # Calcular ahorro vs lo que paga actualmente
                    ahorro_vs_actual_anual = costo_actual_anual - coste_anual
                    ahorro_vs_actual_mensual = ahorro_vs_actual_anual / 12
                    
                    # Determinar si es el RL recomendado
                    recomendado = "✅" if rl == rl_recomendado else ""
                    
                    # Determinar estado del ahorro
                    if ahorro_vs_actual_anual > 0:
                        estado = "💚 Ahorras"
                    elif ahorro_vs_actual_anual == 0:
                        estado = "⚖️ Igual"
                    else:
                        estado = "🔴 Pagas más"
                    
                    # Información del PMG
                    pmg_info = '✅ CON' if tiene_pmg else '❌ SIN'
                    
                    # Información adicional
                    info_extra = ""
                    if tiene_pmg:
                        coste_pmg_anual = calcular_pmg(True, es_canarias)
                        info_extra = f" | 📦 PMG: {coste_pmg_anual/12:.2f}€/mes"
                    else:
                        info_extra = " | 📦 Sin PMG"
                    
                    # Información de precios
                    if tiene_pmg:
                        precio_variable = plan["termino_variable_con_pmg"]
                        precio_fijo = plan["termino_fijo_con_pmg"]
                    else:
                        precio_variable = plan["termino_variable_sin_pmg"]
                        precio_fijo = plan["termino_fijo_sin_pmg"]
                    
                    precio_display = f"Var: {precio_variable:.3f}€ | Fijo: {precio_fijo:.2f}€"
                    
                    resultados.append({
                        "Plan": rl,
                        "Pack Mantenimiento": pmg_info,
                        "Precios": precio_display,
                        "Rango": plan["rango"],
                        "Coste Mensual": f"€{coste_mensual:,.2f}",
                        "Coste Anual": f"€{coste_anual:,.2f}",
                        "Ahorro vs Actual Mes": f"€{ahorro_vs_actual_mensual:,.2f}",
                        "Ahorro vs Actual Año": f"€{ahorro_vs_actual_anual:,.2f}",
                        "Ahorro vs Original": f"€{ahorro_vs_original:,.2f}",
                        "Estado": estado,
                        "Recomendado": recomendado,
                        "Info Extra": info_extra
                    })
        
        # Mostrar resultados
        if resultados:
            # Mostrar métricas principales
            st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
            
            # Información del cálculo
            info_tipo = "ESTIMACIÓN ANUAL" if tipo_calculo == "📊 Estimación anual" else "CÁLCULO EXACTO"
            info_consumo = f"{consumo_anual:,.0f} kWh/año"
            info_costo_actual = f"€{costo_actual_anual:,.2f}/año (€{costo_actual_mensual:,.2f}/mes)"
            info_iva = "Sin IVA" if es_canarias else "Con IVA 21%"
            
            st.info(f"**Tipo:** {info_tipo} | **Consumo:** {info_consumo} | **Actual:** {info_costo_actual} | **IVA:** {info_iva}")
            
            # Encontrar el mejor plan (mayor ahorro anual)
            mejor_plan = max(resultados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
            
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💶 Actual Mensual", f"€{costo_actual_mensual:,.2f}")
            with col2:
                coste_mejor_mensual = float(mejor_plan['Coste Mensual'].replace('€', '').replace(',', ''))
                st.metric("💰 Mejor Mensual", f"€{coste_mejor_mensual:,.2f}")
            with col3:
                ahorro_mensual = float(mejor_plan['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
                st.metric("📈 Ahorro Mensual", f"€{ahorro_mensual:,.2f}", 
                         delta=f"€{ahorro_mensual:,.2f}" if ahorro_mensual > 0 else None)
            with col4:
                ahorro_anual = float(mejor_plan['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
                st.metric("🎯 Ahorro Anual", f"€{ahorro_anual:,.2f}")
            
            # Tabla comparativa completa
            st.dataframe(resultados, use_container_width=True)
            
            # Recomendación detallada
            # Encontrar todos los planes recomendados (CON y SIN PMG)
            planes_recomendados = [p for p in resultados if p['Recomendado'] == '✅']
            
            if planes_recomendados:
                # Encontrar el mejor entre los recomendados
                mejor_recomendado = max(planes_recomendados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
                
                ahorro_mensual_rec = float(mejor_recomendado['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
                ahorro_anual_rec = float(mejor_recomendado['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
                
                if ahorro_mensual_rec > 0:
                    mensaje = f"🎯 **MEJOR OPCIÓN**: {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG"
                    mensaje += f" - Ahorras {ahorro_mensual_rec:,.2f}€/mes ({ahorro_anual_rec:,.2f}€/año)"
                    if mejor_recomendado['Info Extra']:
                        mensaje += mejor_recomendado['Info Extra']
                    st.success(mensaje)
                elif ahorro_mensual_rec == 0:
                    st.info(f"ℹ️ Con {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG pagarías lo mismo que actualmente")
                else:
                    st.warning(f"⚠️ Con {mejor_recomendado['Plan']} {mejor_recomendado['Pack Mantenimiento']} PMG pagarías {abs(ahorro_mensual_rec):,.2f}€/mes más")
        
        else:
            st.warning("No hay planes de gas activos para mostrar")

def cups_naturgy():
    st.subheader("📋 CUPS Naturgy")
    
    st.info("Ejemplos de CUPS para trámites con Naturgy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🔥 CUPS Ejemplo Gas")
        cups_gas = "ES0217010103496537HH"
        st.code(cups_gas, language="text")
        
        # Botón para copiar CUPS Gas
        if st.button("📋 Copiar CUPS Gas", key="copy_gas", use_container_width=True):
            st.session_state.copied_gas = cups_gas
            st.success("✅ CUPS Gas copiado al portapapeles")
    
    with col2:
        st.write("### ⚡ CUPS Ejemplo Electricidad")
        cups_luz = "ES0031405120579007YM"
        st.code(cups_luz, language="text")
        
        # Botón para copiar CUPS Electricidad
        if st.button("📋 Copiar CUPS Electricidad", key="copy_luz", use_container_width=True):
            st.session_state.copied_luz = cups_luz
            st.success("✅ CUPS Electricidad copiado al portapapeles")
    
    st.markdown("---")
    
    st.write("### 🌐 Acceso Directo a Tarifa Plana Zen")
    
    # Crear el enlace que se abre en nueva pestaña
    url = "https://www.naturgy.es/hogar/luz_y_gas/tarifa_plana_zen"
    
    # Usar markdown para crear un enlace que se abre en nueva pestaña
    st.markdown(f"""
    <a href="{url}" target="_blank" style="text-decoration: none;">
        <button style="
            background-color: #00A0E3; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 5px; 
            font-size: 16px; 
            cursor: pointer;
            width: 100%;
        ">
            🚀 Abrir Tarifa Plana Zen de Naturgy
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    st.caption("💡 Se abrirá en una nueva pestaña (el usuario puede hacer Click derecho y buscar modo incógnito en caso de que no cargue correctamente)")

# --- FUNCIONES DE CÁLCULO (MANTENIDAS) ---
def calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh=0.0):
    """Calcula comparación exacta con factura actual - Muestra CON y SIN PI"""
    try:
        # Cargar planes activos
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_activos = filtrar_planes_por_usuario(df_luz, st.session_state.username, "luz")
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Cargar precio de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv")
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando comparativa...")
        
        # CONSTANTES
        ALQUILER_CONTADOR = 0.81  # €/mes
        PACK_IBERDROLA = 3.95  # €/mes (para cálculo CON PI)
        IMPUESTO_ELECTRICO = 0.0511  # 5.11%
        DESCUENTO_PRIMERA_FACTURA = 5.00  # €
        IVA = 0.21  # 21%
        
        # Primero calcular todos los planes para encontrar el máximo ahorro
        todos_resultados = []
        resultados_con_pi = []  # <--- NUEVA LISTA PARA FILTRAR SOLO CON PI
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR SI EL PLAN ESTÁ DISPONIBLE EN LA COMUNIDAD SELECCIONADA
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            # VERIFICAR SI ES PLAN AHORRO AUTOMÁTICO
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in plan['plan'].upper()
            # VERIFICAR SI ES PLAN ESPECIAL PLUS
            es_especial_plus = "ESPECIAL PLUS" in plan['plan'].upper()
            
            for tiene_pi in [True, False]:  # Calcular ambas opciones
                
                if es_ahorro_automatico:
                    # --- CÁLCULO ESPECIAL PARA AHORRO AUTOMÁTICO ---
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo, dias, tiene_pi, es_anual=False
                    )
                    
                    precio_kwh = f"0.215€/0.105€*"
                    # X: Coste consumo total (sin restar excedentes todavía)
                    coste_consumo = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA * (dias / 30) if tiene_pi else 0.0
                    
                    # Bonificación mensual fija
                    if tiene_pi:
                        bonificacion_mensual = 10.00 * (dias / 30)  # 10€/mes con PI
                    else:
                        bonificacion_mensual = 8.33 * (dias / 30)   # 25€/trimestre = 8.33€/mes sin PI
                    
                else:
                    # --- CÁLCULO NORMAL PARA OTROS PLANES ---
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA * (dias / 30)
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    # X: Coste consumo total (sin restar excedentes todavía)
                    coste_consumo = consumo * precio_kwh
                    bonificacion_mensual = 0.0
                
                # ===============================================
                # **CÁLCULO CORREGIDO SEGÚN TU EXPLICACIÓN**
                # ===============================================
                
                # Z: Coste potencia
                coste_potencia = potencia * plan['total_potencia'] * dias
                
                # Y: Ingreso por excedentes
                ingreso_excedentes = excedente_kwh * precio_excedente
                
                # ===============================================
                # **FÓRMULA CORRECTA: (X + Z) - Y**
                # ===============================================
                subtotal_sin_excedentes = coste_consumo + coste_potencia
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes
                
                # Asegurar que no sea negativo
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                # Coste alquiler contador
                coste_alquiler = ALQUILER_CONTADOR * (dias / 30)
                
                # Coste pack Iberdrola
                subtotal_final = subtotal_con_excedentes + coste_alquiler + coste_pack
                
                # IMPUESTOS (sobre subtotal final)
                impuesto_electrico = subtotal_final * IMPUESTO_ELECTRICO
                
                # Aplicar IVA excepto en Canarias
                if comunidad != "Canarias":
                    iva_total = (subtotal_final + impuesto_electrico) * IVA
                else:
                    iva_total = 0
                
                # TOTAL BRUTO
                total_bruto = subtotal_final + impuesto_electrico + iva_total
                
                # Aplicar descuento de bienvenida y bonificación
                total_neto = total_bruto - DESCUENTO_PRIMERA_FACTURA - bonificacion_mensual
                
                # Asegurar que no sea negativo
                total_nuevo = max(0, total_neto)
                
                # Calcular ahorro vs factura actual
                ahorro = costo_actual - total_nuevo
                ahorro_anual = ahorro * (365 / dias)
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                # Información adicional para Ahorro Automático
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d a 0.105€"
                
                # Información adicional para Especial Plus
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                # Información adicional para excedentes
                if excedente_kwh > 0:
                    info_extra += f" | ☀️ {excedente_kwh}kWh excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes:.2f}€"
                
                # Información de disponibilidad por comunidad
                if len(comunidades_plan) == 1 and 'Toda España' in comunidades_plan:
                    info_extra += " | 🗺️ Toda España"
                elif len(comunidades_plan) < 5:
                    info_extra += f" | 🗺️ {', '.join(comunidades_plan)}"
                else:
                    info_extra += f" | 🗺️ {len(comunidades_plan)} CCAA"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Coste Nuevo': round(total_nuevo, 2),
                    'Ahorro Mensual': round(ahorro, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,  # <--- NUEVO CAMPO PARA FILTRAR
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                # <--- GUARDAR SOLO LOS CON PI PARA LAS MÉTRICAS
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # ===============================================
        # **FILTRAR PARA MÉTRICAS (SOLO CON PI)**
        # ===============================================
        
        # Encontrar el MÁXIMO ahorro de planes CON PI (excluyendo Especial Plus)
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        # Filtrar resultados CON PI según regla del Especial Plus
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        # ===============================================
        # **FILTRAR PARA TABLA COMPLETA (CON Y SIN PI)**
        # ===============================================
        
        # Encontrar el MÁXIMO ahorro de todos los planes (excluyendo Especial Plus)
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        # Filtrar TODOS los resultados según regla del Especial Plus
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        # Verificar que tenemos resultados CON PI
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar MEJOR plan CON PI (para métricas)
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        
        # Encontrar MEJOR plan de todos (para tabla)
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
        
        # Explicación de la fórmula
        st.info(f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo:** {consumo}kWh × Precio del plan
        - **Potencia:** {potencia}kW × {dias}días × Tarifa potencia
        - **Excedentes:** {excedente_kwh}kWh × {precio_excedente}€/kWh = {excedente_kwh * precio_excedente:.2f}€
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """)
        
        # ===============================================
        # **MÉTRICAS PRINCIPALES (SOLO CON PI)**
        # ===============================================
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Coste Actual", f"{costo_actual}€")
        with col2:
            st.metric("💰 Coste Nuevo", f"{mejor_plan_con_pi['Coste Nuevo']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        # ===============================================
        # **TABLA COMPLETA (CON Y SIN PI)**
        # ===============================================
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        # Convertir a DataFrame para mostrar
        df_resultados = pd.DataFrame(resultados_finales)
        
        # Ordenar por mejor ahorro (primero CON PI, luego SIN PI)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Coste Nuevo', 
                          'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # ===============================================
        # **RECOMENDACIONES SEPARADAS**
        # ===============================================
        
        # Recomendación CON PI
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
        
        # Recomendación GENERAL (puede ser SIN PI si es mejor)
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning("ℹ️ Todos los planes CON Pack Iberdrola son más caros que tu factura actual")
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {e}")
        import traceback
        st.error(traceback.format_exc())

def calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh=0.0):
    """Calcula estimación anual - Muestra CON y SIN PI con ahorro vs actual"""
    try:
        # Cargar planes activos
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_activos = df_luz[df_luz['activo'] == True]
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Cargar precio de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv")
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando estimación anual...")
        
        # CONSTANTES
        ALQUILER_CONTADOR = 0.81 * 12  # €/año
        PACK_IBERDROLA = 3.95 * 12  # €/año (para cálculo CON PI)
        IMPUESTO_ELECTRICO = 0.0511  # 5.11%
        DESCUENTO_PRIMERA_FACTURA = 5.00  # € (solo primera factura)
        IVA = 0.21  # 21%
        DIAS_ANUAL = 365
        
        # Calcular costo anual actual del cliente
        costo_anual_actual = costo_mensual_actual * 12
        
        # Calcular excedentes anuales
        excedente_anual_kwh = excedente_mensual_kwh * 12
        ingreso_excedentes_anual = excedente_anual_kwh * precio_excedente
        
        # Listas para resultados
        todos_resultados = []
        resultados_con_pi = []  # <--- NUEVA LISTA
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR SI EL PLAN ESTÁ DISPONIBLE EN LA COMUNIDAD SELECCIONADA
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            # VERIFICAR SI ES PLAN AHORRO AUTOMÁTICO
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in plan['plan'].upper()
            # VERIFICAR SI ES PLAN ESPECIAL PLUS
            es_especial_plus = "ESPECIAL PLUS" in plan['plan'].upper()
            
            for tiene_pi in [True, False]:
                
                if es_ahorro_automatico:
                    # CÁLCULO ESPECIAL PARA AHORRO AUTOMÁTICO
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo_anual, DIAS_ANUAL, tiene_pi, es_anual=True
                    )
                    
                    precio_kwh = "0.215€/0.105€*"
                    # X: Coste consumo total
                    coste_consumo_anual = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA if tiene_pi else 0.0
                    
                    # Bonificación anual
                    if tiene_pi:
                        bonificacion_anual = 10.00 * 12  # 120€/año
                    else:
                        bonificacion_anual = 8.33 * 12   # 100€/año
                    
                else:
                    # CÁLCULO NORMAL
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    # X: Coste consumo total
                    coste_consumo_anual = consumo_anual * precio_kwh
                    bonificacion_anual = 0.0
                
                # ===============================================
                # **CÁLCULO CORREGIDO: (X + Z) - Y**
                # ===============================================
                
                # Z: Coste potencia anual
                coste_potencia_anual = potencia * plan['total_potencia'] * DIAS_ANUAL
                
                # Y: Ingreso por excedentes anual
                # ingreso_excedentes_anual ya calculado arriba
                
                # FÓRMULA: (Consumo + Potencia) - Excedentes
                subtotal_sin_excedentes = coste_consumo_anual + coste_potencia_anual
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes_anual
                
                # Asegurar que no sea negativo
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                # Coste alquiler contador anual
                coste_alquiler_anual = ALQUILER_CONTADOR
                
                # Coste pack Iberdrola
                subtotal_final_anual = subtotal_con_excedentes + coste_alquiler_anual + coste_pack
                
                # IMPUESTOS
                impuesto_electrico_anual = subtotal_final_anual * IMPUESTO_ELECTRICO
                iva_anual = (subtotal_final_anual + impuesto_electrico_anual) * IVA
                
                # TOTAL BRUTO ANUAL
                total_bruto_anual = subtotal_final_anual + impuesto_electrico_anual + iva_anual
                
                # Aplicar descuentos
                total_neto_anual = total_bruto_anual - DESCUENTO_PRIMERA_FACTURA - bonificacion_anual
                
                total_anual = max(0, total_neto_anual)
                mensual = total_anual / 12
                
                # Calcular ahorro vs actual
                ahorro_anual = costo_anual_actual - total_anual
                ahorro_mensual = ahorro_anual / 12
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                # Información adicional
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d/año a 0.105€"
                
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                if excedente_mensual_kwh > 0:
                    info_extra += f" | ☀️ {excedente_mensual_kwh}kWh/mes excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes_anual/12:.2f}€/mes"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Mensual': round(mensual, 2),
                    'Anual': round(total_anual, 2),
                    'Ahorro Mensual': round(ahorro_mensual, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro_mensual > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,  # <--- NUEVO CAMPO
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                # <--- GUARDAR SOLO LOS CON PI
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # ===============================================
        # **FILTRAR PARA MÉTRICAS (SOLO CON PI)**
        # ===============================================
        
        # Filtrar resultados CON PI según regla del Especial Plus
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        # ===============================================
        # **FILTRAR PARA TABLA COMPLETA**
        # ===============================================
        
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        # Verificar que tenemos resultados CON PI
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar MEJOR plan CON PI (para métricas)
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        
        # Encontrar MEJOR plan de todos (para tabla)
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        st.write("### 📊 ESTIMACIÓN ANUAL")
        
        # Explicación
        info_text = f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo anual:** {consumo_anual}kWh
        - **Potencia:** {potencia}kW
        - **Excedentes:** {excedente_mensual_kwh}kWh/mes × {precio_excedente}€/kWh = {excedente_mensual_kwh * precio_excedente * 12:.2f}€/año
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """
        
        if excedente_mensual_kwh > 0:
            info_text += f"\n- **Excedentes anuales:** {excedente_anual_kwh}kWh × {precio_excedente}€ = {ingreso_excedentes_anual:.2f}€"
        
        st.info(info_text)
        
        # ===============================================
        # **MÉTRICAS PRINCIPALES (SOLO CON PI)**
        # ===============================================
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Actual Mensual", f"{costo_mensual_actual}€")
        with col2:
            st.metric("💰 Nuevo Mensual", f"{mejor_plan_con_pi['Mensual']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        # ===============================================
        # **TABLA COMPLETA (CON Y SIN PI)**
        # ===============================================
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        df_resultados = pd.DataFrame(resultados_finales)
        
        # Ordenar por mejor ahorro (primero CON PI, luego SIN PI)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Mensual', 
                          'Anual', 'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # ===============================================
        # **RECOMENDACIONES**
        # ===============================================
        
        # Recomendación CON PI
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
            st.info(f"💡 Pagarías {mejor_plan_con_pi['Mensual']}€/mes normalmente")
        
        # Si la mejor opción general es SIN PI
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes más, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning(f"ℹ️ Todos los planes CON Pack Iberdrola son más caros que lo que pagas actualmente ({costo_mensual_actual}€/mes)")
        
    except Exception as e:
        st.error(f"❌ Error en el cálculo anual: {e}")

# --- FUNCIONES DE CÁLCULO PARA GAS ---
def determinar_rl_gas(consumo_anual):
    """Determina automáticamente el RL según consumo anual"""
    if consumo_anual <= 5000:
        return "RL1"
    elif consumo_anual <= 15000:
        return "RL2"
    else:
        return "RL3"

def calcular_pmg(tiene_pmg, es_canarias=False):
    """Calcula el coste del PMG con/sin IVA"""
    if not tiene_pmg:
        return 0
    
    coste_pmg = PMG_COSTE
    if not es_canarias:
        coste_pmg *= (1 + PMG_IVA)
    
    return coste_pmg * 12  # Anualizado

def calcular_coste_gas_completo(plan, consumo_kwh, tiene_pmg=True, es_canarias=False):
    """Calcula coste total de gas incluyendo PMG e IVA"""
    # Coste del gas (sin IVA todavía)
    if tiene_pmg:
        termino_fijo = plan["termino_fijo_con_pmg"]
        termino_variable = plan["termino_variable_con_pmg"]
    else:
        termino_fijo = plan["termino_fijo_sin_pmg"]
        termino_variable = plan["termino_variable_sin_pmg"]
    
    coste_fijo = termino_fijo * 12  # Anual
    coste_variable = consumo_kwh * termino_variable
    coste_gas_sin_iva = coste_fijo + coste_variable
    
    # Aplicar IVA al gas (excepto Canarias)
    if not es_canarias:
        coste_gas_con_iva = coste_gas_sin_iva * (1 + PMG_IVA)
    else:
        coste_gas_con_iva = coste_gas_sin_iva
    
    # Coste PMG (ya incluye IVA según la función calcular_pmg)
    coste_pmg = calcular_pmg(tiene_pmg, es_canarias)
    
    return coste_gas_con_iva + coste_pmg

def calcular_plan_ahorro_automatico(plan, consumo, dias, tiene_pi=False, es_anual=False):
    """
    Calcula el coste para el Plan Ahorro Automático
    Tiene precio variable (sin bonificación trimestral ahora)
    """
    # Estimación: 2 días/semana a precio bajo, 5 días/semana a precio normal
    if es_anual:
        total_dias = 365
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    else:
        total_dias = dias
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    
    # Estimación de consumo diario
    consumo_diario = consumo / total_dias
    
    # Consumo a cada precio
    consumo_bajo_precio = consumo_diario * dias_bajo_precio
    consumo_precio_normal = consumo_diario * dias_precio_normal
    
    # Precios del plan
    precio_normal = 0.215  # €/kWh
    precio_bajo = 0.105   # €/kWh (2 días/semana)
    
    # Coste de consumo
    coste_consumo_normal = consumo_precio_normal * precio_normal
    coste_consumo_bajo = consumo_bajo_precio * precio_bajo
    coste_consumo_total = coste_consumo_normal + coste_consumo_bajo
    
    return {
        'coste_consumo': coste_consumo_total,
        'dias_bajo_precio': dias_bajo_precio,
        'dias_precio_normal': dias_precio_normal,
        'consumo_bajo_precio': consumo_bajo_precio,
        'consumo_precio_normal': consumo_precio_normal
    }

if __name__ == "__main__":
    main()