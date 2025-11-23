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
            'total_potencia': [0.162, 0.154, 0.154, 0.131, 0.154],
            'activo': [True, True, True, True, True]
        }
        pd.DataFrame(datos_luz).to_csv("data/precios_luz.csv", index=False)
        st.sidebar.success("✅ Datos iniciales de electricidad creados")

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
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
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
        st.success("✅ Datos de electricidad cargados correctamente")
    except FileNotFoundError:
        st.warning("⚠️ No hay datos de electricidad. Se crearán datos iniciales.")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo'
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
            total_potencia = st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                                           value=st.session_state.editing_plan['total_potencia'] if st.session_state.editing_plan else 0.162)
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan['activo'] if st.session_state.editing_plan else True)
        
        # Botones diferentes según si estamos editando o creando
        if st.session_state.editing_plan is not None:
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
            action_type = "actualizar"
            action_message = f"¿Estás seguro de que quieres ACTUALIZAR el plan '{nombre_plan}'?"
        else:
            submitted = st.form_submit_button("➕ Crear Nuevo Plan", type="primary")
            action_type = "crear"
            action_message = f"¿Estás seguro de que quieres CREAR el nuevo plan '{nombre_plan}'?"
        
        if submitted:
            if not nombre_plan:
                st.error("❌ El nombre del plan es obligatorio")
            else:
                # Mostrar confirmación
                with st.container():
                    st.warning("⚠️ CONFIRMACIÓN REQUERIDA")
                    st.write(action_message)
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Sí, confirmar", type="primary"):
                            # Crear nuevo registro
                            nuevo_plan = {
                                'plan': nombre_plan,
                                'precio_original_kwh': precio_original,
                                'con_pi_kwh': con_pi,
                                'sin_pi_kwh': sin_pi,
                                'punta': punta,
                                'valle': valle,
                                'total_potencia': total_potencia,
                                'activo': activo
                            }
                            
                            # Añadir o actualizar el plan
                            if nombre_plan in df_luz['plan'].values:
                                # Actualizar plan existente
                                idx = df_luz[df_luz['plan'] == nombre_plan].index[0]
                                for key, value in nuevo_plan.items():
                                    df_luz.at[idx, key] = value
                                st.success(f"✅ Plan '{nombre_plan}' actualizado correctamente")
                            else:
                                # Añadir nuevo plan
                                df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan])], ignore_index=True)
                                st.success(f"✅ Plan '{nombre_plan}' añadido correctamente")
                            
                            # Guardar y limpiar estado
                            df_luz.to_csv("data/precios_luz.csv", index=False)
                            st.session_state.editing_plan = None
                            st.rerun()
                    
                    with col_cancel:
                        if st.button("❌ Cancelar"):
                            st.info("Operación cancelada")
    
    # Opción para eliminar planes
    if not df_luz.empty and st.session_state.editing_plan is None:
        st.write("### 🗑️ Eliminar Plan")
        plan_a_eliminar = st.selectbox("Selecciona plan a eliminar", df_luz['plan'].unique())
        
        if st.button("Eliminar Plan Seleccionado", type="secondary"):
            with st.container():
                st.error("🚨 ELIMINACIÓN PERMANENTE")
                st.write(f"¿Estás seguro de que quieres ELIMINAR permanentemente el plan '{plan_a_eliminar}'?")
                
                col_conf_del, col_can_del = st.columns(2)
                with col_conf_del:
                    if st.button("✅ Sí, eliminar", type="primary"):
                        df_luz = df_luz[df_luz['plan'] != plan_a_eliminar]
                        df_luz.to_csv("data/precios_luz.csv", index=False)
                        st.success(f"✅ Plan '{plan_a_eliminar}' eliminado correctamente")
                        st.rerun()
                
                with col_can_del:
                    if st.button("❌ Cancelar eliminación"):
                        st.info("Eliminación cancelada")

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
