import streamlit as st
import pandas as pd
import os
from auth import authenticate

# Configuración de la página
st.set_page_config(
    page_title="Zelenza CEX - Iberdrola",
    page_icon="⚡",
    layout="wide"
)

def inicializar_datos():
    """Inicializa los archivos de datos si no existen"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("modelos_facturas", exist_ok=True)
    
    if not os.path.exists("data/precios_luz.csv"):
        df_vacio = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo'
        ])
        df_vacio.to_csv("data/precios_luz.csv", index=False)

def main():
    inicializar_datos()
    
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        mostrar_aplicacion_principal()

def mostrar_login():
    """Muestra la pantalla de login"""
    st.header("🔐 Iniciar Sesión")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Acceso Usuario")
        if st.button("Entrar como Usuario", use_container_width=True, type="secondary"):
            st.session_state.authenticated = True
            st.session_state.user_type = "user"
            st.session_state.username = "usuario"
            st.rerun()
    
    with col2:
        st.subheader("🔧 Acceso Administrador")
        admin_user = st.text_input("Usuario Administrador")
        admin_pass = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar como Admin", use_container_width=True, type="primary"):
            if authenticate(admin_user, admin_pass, "admin"):
                st.session_state.authenticated = True
                st.session_state.user_type = "admin"
                st.session_state.username = admin_user
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

def mostrar_aplicacion_principal():
    """Muestra la aplicación principal según el tipo de usuario"""
    st.sidebar.title(f"{'🔧 Admin' if st.session_state.user_type == 'admin' else '👤 Usuario'}")
    st.sidebar.write(f"**Usuario:** {st.session_state.username}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
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
    
    tab1, tab2, tab3 = st.tabs(["⚡ Electricidad", "🔥 Gas", "📄 Facturas"])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_modelos_factura()

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    st.header("👤 Portal del Cliente")
    
    # PRIMERA PANTALLA: Consultar modelos de factura (como querías)
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Otras calculadoras
    st.subheader("🧮 Calculadoras")
    tab1, tab2, tab3 = st.tabs(["⚡ Calculadora Diaria", "📅 Calculadora Anual", "🔥 Calculadora Gas"])
    
    with tab1:
        calculadora_diaria_simple()
    with tab2:
        calculadora_anual_simple()
    with tab3:
        calculadora_gas()

# --- FUNCIONES DE ADMINISTRADOR (SIMPLIFICADAS) ---
def gestion_electricidad():
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
    # Reset temporal
    if st.button("🔄 Resetear datos"):
        df_vacio = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo'
        ])
        df_vacio.to_csv("data/precios_luz.csv", index=False)
        st.success("✅ Datos reseteados")
        st.rerun()
    
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        if df_luz.empty:
            st.info("📝 No hay planes configurados")
    except:
        st.warning("⚠️ No hay datos de electricidad")
        df_luz = pd.DataFrame()
    
    # Formulario para añadir planes
    st.write("### ➕ Añadir Plan")
    with st.form("form_plan"):
        nombre_plan = st.text_input("Nombre del Plan")
        precio_original = st.number_input("Precio Original kWh", min_value=0.0, format="%.3f", value=0.170)
        con_pi = st.number_input("Con PI kWh", min_value=0.0, format="%.3f", value=0.130)
        sin_pi = st.number_input("Sin PI kWh", min_value=0.0, format="%.3f", value=0.138)
        total_potencia = st.number_input("Total Potencia €", min_value=0.0, format="%.3f", value=0.162)
        activo = st.checkbox("Plan activo", value=True)
        
        if st.form_submit_button("Guardar Plan"):
            if nombre_plan:
                nuevo_plan = {
                    'plan': nombre_plan, 'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi, 'sin_pi_kwh': sin_pi, 
                    'punta': 0.116, 'valle': 0.046,  # Valores por defecto
                    'total_potencia': total_potencia, 'activo': activo
                }
                
                if df_luz.empty:
                    df_luz = pd.DataFrame([nuevo_plan])
                else:
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan])], ignore_index=True)
                
                df_luz.to_csv("data/precios_luz.csv", index=False)
                st.success(f"✅ Plan '{nombre_plan}' añadido")
                st.rerun()
    
    # Mostrar planes existentes
    if not df_luz.empty:
        st.write("### 📊 Planes Actuales")
        st.dataframe(df_luz, use_container_width=True)

def gestion_gas():
    st.subheader("🔥 Gestión de Planes de Gas")
    st.info("Funcionalidad en desarrollo...")

def gestion_modelos_factura():
    st.subheader("📄 Gestión de Modelos de Factura")
    
    empresas = ["Iberdrola", "Endesa", "Naturgy", "TotalEnergies", "Repsol", "EDP", "Otra"]
    empresa = st.selectbox("Seleccionar Empresa", empresas)
    
    archivo = st.file_uploader("Subir modelo de factura", type=['png', 'jpg', 'jpeg'])
    
    if archivo is not None:
        # Crear carpeta para la empresa si no existe
        carpeta_empresa = f"modelos_facturas/{empresa.lower()}"
        os.makedirs(carpeta_empresa, exist_ok=True)
        
        # Guardar archivo
        ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
        with open(ruta_archivo, "wb") as f:
            f.write(archivo.getbuffer())
        
        st.success(f"✅ Modelo para {empresa} guardado correctamente")
        st.image(archivo, caption=f"Modelo de factura - {empresa}", use_column_width=True)

# --- FUNCIONES DE USUARIO (SIN CÓDIGO POSTAL) ---
def consultar_modelos_factura():
    st.subheader("📊 Modelos de Factura")
    st.info("Selecciona tu compañía eléctrica para ver los modelos de factura")
    
    empresas = ["Iberdrola", "Endesa", "Naturgy", "TotalEnergies", "Repsol", "EDP", "Otra"]
    empresa_seleccionada = st.selectbox("Selecciona tu compañía eléctrica", empresas)
    
    # Mostrar modelos disponibles para esa empresa
    carpeta_empresa = f"modelos_facturas/{empresa_seleccionada.lower()}"
    
    if os.path.exists(carpeta_empresa):
        archivos = os.listdir(carpeta_empresa)
        if archivos:
            st.write(f"### 📋 Modelos disponibles para {empresa_seleccionada}:")
            
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta_empresa, archivo)
                st.write(f"**Modelo:** {archivo}")
                st.image(ruta_completa, use_column_width=True)
                st.markdown("---")
        else:
            st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa_seleccionada}")
            st.info("Contacta con el administrador para que suba modelos de referencia")
    else:
        st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa_seleccionada}")

def calculadora_diaria_simple():
    st.subheader("⚡ Calculadora Diaria")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dias = st.number_input("Días del período", min_value=1, value=30)
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3)
    
    with col2:
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0)
        tiene_pi = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"])
    
    if st.button("Calcular", type="primary"):
        st.success("✅ Cálculo completado (funcionalidad básica)")
        st.info("Los cálculos completos se activarán cuando solucionemos el error del código postal")

def calculadora_anual_simple():
    st.subheader("📅 Calculadora Anual")
    
    potencia = st.number_input("Potencia anual (kW)", min_value=1.0, value=3.3, key="pot_anual")
    consumo = st.number_input("Consumo anual (kWh)", min_value=0.0, value=7500.0, key="consumo_anual")
    tiene_pi = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"], key="pi_anual")
    
    if st.button("Calcular Anual", type="primary"):
        st.success("✅ Cálculo anual completado (funcionalidad básica)")

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Funcionalidad en desarrollo...")

if __name__ == "__main__":
    main()