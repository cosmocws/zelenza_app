import streamlit as st
import pandas as pd
import os
from auth import authenticate

# Configuración inicial de la página
st.set_page_config(
    page_title="Zelenza CEX - Iberdrola",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inicializar_datos():
    """Inicializa los archivos de datos si no existen"""
    # Crear directorios necesarios
    os.makedirs("data", exist_ok=True)
    os.makedirs("modelos_facturas/iberdrola", exist_ok=True)
    os.makedirs("modelos_facturas/endesa", exist_ok=True)
    os.makedirs("modelos_facturas/naturgy", exist_ok=True)
    os.makedirs("modelos_facturas/otros", exist_ok=True)
    
    # Datos iniciales de electricidad si no existen
    if not os.path.exists("data/precios_luz.csv"):
        datos_luz = {
            'plan': ['IMPULSA 24h', 'ESTABLE', 'PLANAZO', 'HOGAR', 'ESPECIAL PLUS'],
            'precio_original_kwh': [0.173, 0.175, 0.189, 0.189, 0.148],
            'con_pi_kwh': [0.130, 0.140, 0.151, 0.151, 0.118],
            'sin_pi_kwh': [0.138, 0.149, 0.161, 0.161, 0.125],
            'punta': [0.116, 0.108, 0.108, 0.085, 0.108],
            'valle': [0.046, 0.046, 0.046, 0.046, 0.046],
            'total_potencia': [0.162, 0.154, 0.154, 0.131, 0.154]
        }
        pd.DataFrame(datos_luz).to_csv("data/precios_luz.csv", index=False)

def main():
    # Inicializar datos
    inicializar_datos()
    
    # Título principal
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    # Sistema de autenticación
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
    
    # Mostrar login si no está autenticado
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        mostrar_aplicacion_principal()

def mostrar_login():
    """Muestra la pantalla de login"""
    st.header("🔐 Iniciar Sesión")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("👤 Acceso Usuario")
        st.info("Para clientes y consultas")
        if st.button("Entrar como Usuario", use_container_width=True, type="secondary"):
            st.session_state.authenticated = True
            st.session_state.user_type = "user"
            st.session_state.username = "usuario"
            st.rerun()
    
    with col2:
        st.subheader("🔧 Acceso Administrador")
        st.info("Para gestión de precios y modelos")
        
        admin_user = st.text_input("Usuario Administrador")
        admin_pass = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar como Admin", use_container_width=True, type="primary"):
            if authenticate(admin_user, admin_pass):
                st.session_state.authenticated = True
                st.session_state.user_type = "admin"
                st.session_state.username = admin_user
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

def mostrar_aplicacion_principal():
    """Muestra la aplicación principal según el tipo de usuario"""
    # Sidebar con información del usuario
    st.sidebar.title("🔧 Panel de Navegación" if st.session_state.user_type == "admin" else "👤 Mi Cuenta")
    
    st.sidebar.write(f"**Usuario:** {st.session_state.username}")
    st.sidebar.write(f"**Tipo:** {'Administrador' if st.session_state.user_type == 'admin' else 'Usuario'}")
    
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Navegación principal
    if st.session_state.user_type == "admin":
        mostrar_panel_administrador()
    else:
        mostrar_panel_usuario()

def mostrar_panel_administrador():
    """Panel de administración"""
    st.header("🔧 Panel de Administración")
    
    tab1, tab2, tab3 = st.tabs(["⚡ Gestión Electricidad", "🔥 Gestión Gas", "📄 Modelos de Factura"])
    
    with tab1:
        gestion_electricidad()
    
    with tab2:
        gestion_gas()
    
    with tab3:
        gestion_modelos_factura()

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    st.header("👤 Portal del Cliente")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Consultar Facturas", 
        "⚡ Calculadora Diaria", 
        "📅 Calculadora Anual", 
        "🔥 Calculadora Gas"
    ])
    
    with tab1:
        consultar_modelos_factura()
    
    with tab2:
        calculadora_diaria()
    
    with tab3:
        calculadora_anual()
    
    with tab4:
        calculadora_gas()

# --- FUNCIONES DE ADMINISTRADOR ---
def gestion_electricidad():
    st.subheader("Gestión de Planes de Electricidad")
    st.info("Aquí podrás configurar los precios de los planes de electricidad")
    # (Implementaremos en el siguiente paso)

def gestion_gas():
    st.subheader("Gestión de Planes de Gas")
    st.info("Aquí podrás configurar los precios de los planes de gas")
    # (Implementaremos en el siguiente paso)

def gestion_modelos_factura():
    st.subheader("📄 Gestión de Modelos de Factura")
    
    # Lista completa de empresas disponibles
    EMPRESAS_ELECTRICAS = [
        "Iberdrola", "Endesa", "Naturgy", "TotalEnergies", 
        "Repsol", "EDP", "Viesgo", "Holaluz", "Factor Energía",
        "Octopus Energy", "Otra"
    ]
    
    empresa = st.selectbox("Seleccionar Empresa", EMPRESAS_ELECTRICAS)
    
    st.write(f"### Subir Modelo de Factura para {empresa}")
    
    archivo = st.file_uploader("Selecciona una imagen del modelo de factura", 
                              type=['png', 'jpg', 'jpeg'],
                              key=f"upload_{empresa}")
    
    if archivo is not None:
        # Crear carpeta si no existe
        carpeta_empresa = f"modelos_facturas/{empresa.lower().replace(' ', '_')}"
        os.makedirs(carpeta_empresa, exist_ok=True)
        
        # Guardar el archivo
        ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
        
        with open(ruta_archivo, "wb") as f:
            f.write(archivo.getbuffer())
        
        st.success(f"✅ Modelo de factura para {empresa} guardado correctamente")
        
        # Mostrar preview
        st.image(archivo, caption=f"Modelo de factura - {empresa}", use_column_width=True)

# --- FUNCIONES DE USUARIO ---
def consultar_modelos_factura():
    st.subheader("📊 Modelos de Factura")
    st.info("Consulta los modelos de factura para identificar los datos necesarios")
    
    # Misma lista de empresas que en admin
    EMPRESAS_ELECTRICAS = [
        "Iberdrola", "Endesa", "Naturgy", "TotalEnergies", 
        "Repsol", "EDP", "Viesgo", "Holaluz", "Factor Energía",
        "Octopus Energy", "Otra"
    ]
    
    empresa = st.selectbox("Selecciona tu compañía eléctrica", EMPRESAS_ELECTRICAS)
    
    # Mostrar modelos disponibles para esa empresa
    carpeta_empresa = f"modelos_facturas/{empresa.lower().replace(' ', '_')}"
    
    if os.path.exists(carpeta_empresa):
        archivos = os.listdir(carpeta_empresa)
        if archivos:
            st.write(f"### 📋 Modelos disponibles para {empresa}:")
            
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta_empresa, archivo)
                
                # Mostrar cada imagen en tamaño completo
                st.write(f"**Modelo:** {archivo}")
                st.image(ruta_completa, use_column_width=True)
                st.markdown("---")  # Línea separadora
        else:
            st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa}")
            st.info("Contacta con el administrador para que suba modelos de referencia")
    else:
        st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa}")

def calculadora_diaria():
    st.subheader("⚡ Calculadora Diaria de Electricidad")
    st.info("Calcula el coste para un período específico")
    # (Implementaremos en el siguiente paso)

def calculadora_anual():
    st.subheader("📅 Calculadora Anual de Electricidad")
    st.info("Calcula el coste anual estimado")
    # (Implementaremos en el siguiente paso)

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Calcula el coste de tu consumo de gas")
    # (Implementaremos en el siguiente paso)

if __name__ == "__main__":
    main()
