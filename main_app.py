import streamlit as st
import pandas as pd
import os
from auth import authenticate

# Lista de comunidades autónomas españolas
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
    
    # Crear archivo VACÍO de electricidad si no existe
    if not os.path.exists("data/precios_luz.csv"):
        df_vacio = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'comunidades',
            'pack_iberdrola'
        ])
        df_vacio.to_csv("data/precios_luz.csv", index=False)

def obtener_comunidad_por_cp(codigo_postal):
    """
    Determina la comunidad autónoma basándose en el código postal
    """
    try:
        cp = int(codigo_postal)
    except:
        return None
    
    # Mapeo mejorado de códigos postales a comunidades
    comunidades_cp = {
        "Andalucía": [range(1000, 2399), range(29000, 29999), range(41000, 41999)],
        "Aragón": [range(22000, 22999), range(50000, 50999)],
        "Asturias": [range(33000, 33999)],
        "Baleares": [range(7000, 7999)],
        "Canarias": [range(35000, 35999), range(38000, 38999)],
        "Cantabria": [range(39000, 39999)],
        "Castilla-La Mancha": [range(2000, 4999), range(13000, 13999), range(16000, 16999), range(19000, 19999)],
        "Castilla y León": [range(500, 999), range(9000, 4999), range(24000, 24999), range(37000, 37999), range(40000, 40999), range(42000, 42999), range(47000, 47999), range(49000, 49999)],
        "Cataluña": [range(8000, 8999), range(17000, 17999), range(25000, 25999), range(43000, 43999)],
        "Comunidad Valenciana": [range(3000, 6999), range(12000, 12999), range(46000, 46999)],
        "Extremadura": [range(6000, 6999), range(10000, 10999)],
        "Galicia": [range(15000, 15999), range(27000, 27999), range(32000, 32999), range(36000, 36999)],
        "Madrid": [range(28000, 28999)],
        "Murcia": [range(30000, 30999)],
        "Navarra": [range(31000, 31999)],
        "País Vasco": [range(100, 199), range(48000, 48999)],
        "La Rioja": [range(26000, 26999)],
        "Ceuta": [range(51000, 51999)],
        "Melilla": [range(52000, 52999)]
    }
    
    for comunidad, rangos in comunidades_cp.items():
        for rango in rangos:
            if cp in rango:
                return comunidad
    
    return None

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
                    'punta', 'valle', 'total_potencia', 'activo', 'comunidades',
                    'pack_iberdrola'
                ])
                df_vacio.to_csv("data/precios_luz.csv", index=False)
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
    
    # Cargar datos actuales - MANEJO MEJORADO PARA ARCHIVOS VACÍOS
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        # Si el DataFrame está vacío, crear uno nuevo
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo', 'comunidades',
                'pack_iberdrola'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'comunidades',
            'pack_iberdrola'
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
            total_potencia = st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                                           value=st.session_state.editing_plan['total_potencia'] if st.session_state.editing_plan else 0.162)
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan['activo'] if st.session_state.editing_plan else True)
            
            # NUEVO CAMPO: Pack Iberdrola
            pack_iberdrola = st.number_input("Pack Iberdrola (€)*", min_value=0.0, format="%.2f",
                                           value=st.session_state.editing_plan['pack_iberdrola'] if st.session_state.editing_plan else 3.95)
            st.caption("Precio mensual del Pack Iberdrola")
            
            # NUEVO CAMPO: Comunidades autónomas
            comunidades_default = ["Toda España"]
            if st.session_state.editing_plan:
                comunidades_value = st.session_state.editing_plan['comunidades']
                if isinstance(comunidades_value, list):
                    comunidades_default = comunidades_value
                elif isinstance(comunidades_value, str) and comunidades_value:
                    comunidades_default = [comunidades_value]
                comunidades_default = [c for c in comunidades_default if c in COMUNIDADES_AUTONOMAS]
            
            comunidades = st.multiselect(
                "Comunidades Autónomas*",
                options=COMUNIDADES_AUTONOMAS,
                default=comunidades_default
            )
            st.caption("Selecciona 'Toda España' o comunidades específicas")
        
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
            elif not comunidades:
                st.error("❌ Debes seleccionar al menos una comunidad autónoma")
            else:
                st.session_state.pending_plan = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo,
                    'comunidades': comunidades,
                    'pack_iberdrola': pack_iberdrola
                }
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
                nuevo_plan = st.session_state.pending_plan
                
                if nuevo_plan['plan'] in df_luz['plan'].values:
                    idx = df_luz[df_luz['plan'] == nuevo_plan['plan']].index[0]
                    for key, value in nuevo_plan.items():
                        df_luz.at[idx, key] = value
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' actualizado correctamente")
                else:
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan])], ignore_index=True)
                    st.success(f"✅ Plan '{nuevo_plan['plan']}' añadido correctamente")
                
                df_luz.to_csv("data/precios_luz.csv", index=False)
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
    
    # Opción para eliminar planes
    if not df_luz.empty and st.session_state.editing_plan is None and not st.session_state.show_confirmation:
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
    st.info("Funcionalidad en desarrollo...")

def gestion_modelos_factura():
    st.subheader("📄 Gestión de Modelos de Factura")
    
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
        carpeta_empresa = f"modelos_facturas/{empresa.lower().replace(' ', '_')}"
        os.makedirs(carpeta_empresa, exist_ok=True)
        
        ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
        
        with open(ruta_archivo, "wb") as f:
            f.write(archivo.getbuffer())
        
        st.success(f"✅ Modelo de factura para {empresa} guardado correctamente")
        st.image(archivo, caption=f"Modelo de factura - {empresa}", use_column_width=True)

# --- FUNCIONES DE USUARIO ---
def consultar_modelos_factura():
    st.subheader("📊 Modelos de Factura")
    st.info("Consulta los modelos de factura para identificar los datos necesarios")
    
    EMPRESAS_ELECTRICAS = [
        "Iberdrola", "Endesa", "Naturgy", "TotalEnergies", 
        "Repsol", "EDP", "Viesgo", "Holaluz", "Factor Energía",
        "Octopus Energy", "Otra"
    ]
    
    empresa = st.selectbox("Selecciona tu compañía eléctrica", EMPRESAS_ELECTRICAS)
    
    carpeta_empresa = f"modelos_facturas/{empresa.lower().replace(' ', '_')}"
    
    if os.path.exists(carpeta_empresa):
        archivos = os.listdir(carpeta_empresa)
        if archivos:
            st.write(f"### 📋 Modelos disponibles para {empresa}:")
            
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta_empresa, archivo)
                st.write(f"**Modelo:** {archivo}")
                st.image(ruta_completa, use_column_width=True)
                st.markdown("---")
        else:
            st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa}")
            st.info("Contacta con el administrador para que suba modelos de referencia")
    else:
        st.warning(f"⚠️ No hay modelos de factura disponibles para {empresa}")

def calculadora_diaria():
    st.subheader("⚡ Calculadora Diaria de Electricidad")
    st.info("Calcula el coste para un período específico según tu ubicación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        codigo_postal = st.text_input("Código Postal*", placeholder="28001", max_length=5, key="cp_diario")
        dias = st.number_input("Días del período", min_value=1, value=30, key="dias_diario")
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_diario")
    
    with col2:
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0, key="consumo_diario")
        tiene_pi = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"], key="pi_diario")
        pack_iberdrola = st.radio("¿Pack Iberdrola?", ["Sí", "No"], key="pack_diario")
    
    if st.button("Calcular", type="primary", key="calcular_diario"):
        if not codigo_postal or not codigo_postal.isdigit() or len(codigo_postal) != 5:
            st.error("❌ Por favor, introduce un código postal válido (5 dígitos)")
        else:
            comunidad = obtener_comunidad_por_cp(codigo_postal)
            if comunidad:
                st.success(f"📍 Ubicación detectada: {comunidad}")
                calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, pack_iberdrola, codigo_postal, comunidad)
            else:
                st.error("❌ No se pudo determinar la comunidad autónoma. Usando cálculo general.")
                calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, pack_iberdrola, codigo_postal, "Toda España")

def calculadora_anual():
    st.subheader("📅 Calculadora Anual de Electricidad")
    st.info("Calcula el coste anual estimado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        codigo_postal = st.text_input("Código Postal*", placeholder="28001", max_length=5, key="cp_anual")
        potencia_anual = st.number_input("Potencia contratada anual (kW)", min_value=1.0, value=3.3, key="pot_anual")
    
    with col2:
        consumo_anual = st.number_input("Consumo anual (kWh)", min_value=0.0, value=7500.0, key="consumo_anual")
        tiene_pi_anual = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"], key="pi_anual")
        pack_iberdrola_anual = st.radio("¿Pack Iberdrola?", ["Sí", "No"], key="pack_anual")
    
    if st.button("Calcular Anual", type="primary", key="calcular_anual"):
        if not codigo_postal or not codigo_postal.isdigit() or len(codigo_postal) != 5:
            st.error("❌ Por favor, introduce un código postal válido (5 dígitos)")
        else:
            comunidad = obtener_comunidad_por_cp(codigo_postal)
            if comunidad:
                st.success(f"📍 Ubicación detectada: {comunidad}")
                calcular_electricidad_anual(potencia_anual, consumo_anual, tiene_pi_anual, pack_iberdrola_anual, codigo_postal, comunidad)
            else:
                st.error("❌ No se pudo determinar la comunidad autónoma. Usando cálculo general.")
                calcular_electricidad_anual(potencia_anual, consumo_anual, tiene_pi_anual, pack_iberdrola_anual, codigo_postal, "Toda España")

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Calcula el coste de tu consumo de gas")
    
    consumo_gas = st.number_input("Consumo de gas (kWh)", min_value=0.0, value=1000.0)
    tipo_red = st.selectbox("Tipo de Red Local", ["RL1", "RL2", "RL3"])
    tiene_pmg = st.radio("¿Tiene PMG?", ["Sí", "No"])
    
    if st.button("Calcular Gas", type="primary"):
        calcular_gas(consumo_gas, tipo_red, tiene_pmg)

# --- FUNCIONES DE CÁLCULO REALES ---
def calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, pack_iberdrola, codigo_postal, comunidad):
    st.success("🧮 Calculando costes...")
    
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_disponibles = df_luz[
            (df_luz['activo'] == True) & 
            (
                (df_luz['comunidades'].apply(lambda x: 'Toda España' in x if isinstance(x, list) else x == 'Toda España')) |
                (df_luz['comunidades'].apply(lambda x: comunidad in x if isinstance(x, list) else x == comunidad))
            )
        ]
        
        if planes_disponibles.empty:
            st.warning("⚠️ No hay planes disponibles para tu comunidad autónoma")
            return
        
        st.write(f"### 📊 Resultados para {dias} días en {comunidad}")
        
        ALQUILER_CONTADOR = 0.81
        FINANCIACION_BONO_SOCIAL = 0.03
        IMPUESTO_ELECTRICO = 0.0511
        DESCUENTO_PRIMERA_FACTURA = 5.00
        
        iva_porcentaje = 0.0 if comunidad == "Canarias" else 0.21
        
        resultados = []
        
        for _, plan in planes_disponibles.iterrows():
            if tiene_pi == "Sí":
                precio_kwh = plan['con_pi_kwh']
                coste_pack = plan['pack_iberdrola'] if pack_iberdrola == "Sí" else 0.0
            else:
                precio_kwh = plan['sin_pi_kwh'] 
                coste_pack = 0.0
            
            coste_consumo = consumo * precio_kwh
            coste_potencia = potencia * plan['total_potencia'] * dias
            coste_alquiler = ALQUILER_CONTADOR * (dias / 30)
            coste_financiacion = FINANCIACION_BONO_SOCIAL * dias
            coste_pack_total = coste_pack * (dias / 30)
            
            subtotal = coste_consumo + coste_potencia + coste_alquiler + coste_financiacion + coste_pack_total
            impuesto_electrico = subtotal * IMPUESTO_ELECTRICO
            iva = (subtotal + impuesto_electrico) * iva_porcentaje
            total = subtotal + impuesto_electrico + iva - DESCUENTO_PRIMERA_FACTURA
            
            resultados.append({
                'Plan': plan['plan'],
                'Consumo': round(coste_consumo, 2),
                'Potencia': round(coste_potencia, 2),
                'Alquiler': round(coste_alquiler, 2),
                'Bono Social': round(coste_financiacion, 2),
                'Pack Iberdrola': round(coste_pack_total, 2),
                'Subtotal': round(subtotal, 2),
                'Imp. Eléctrico': round(impuesto_electrico, 2),
                'IVA': round(iva, 2),
                'Descuento': -DESCUENTO_PRIMERA_FACTURA,
                'TOTAL': round(total, 2) if total > 0 else 0
            })
        
        df_resultados = pd.DataFrame(resultados)
        st.dataframe(df_resultados, use_container_width=True)
        
        if not df_resultados.empty:
            mejor_plan = df_resultados.loc[df_resultados['TOTAL'].idxmin()]
            st.success(f"🎯 **MEJOR OPCIÓN**: {mejor_plan['Plan']} - {mejor_plan['TOTAL']}€ total")
            
            st.write("### 📈 Comparativa de Planes")
            chart_data = df_resultados.set_index('Plan')['TOTAL']
            st.bar_chart(chart_data)
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {str(e)}")

def calcular_electricidad_anual(potencia, consumo, tiene_pi, pack_iberdrola, codigo_postal, comunidad):
    st.success("🧮 Calculando coste anual...")
    
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_disponibles = df_luz[
            (df_luz['activo'] == True) & 
            (
                (df_luz['comunidades'].apply(lambda x: 'Toda España' in x if isinstance(x, list) else x == 'Toda España')) |
                (df_luz['comunidades'].apply(lambda x: comunidad in x if isinstance(x, list) else x == comunidad))
            )
        ]
        
        if planes_disponibles.empty:
            st.warning("⚠️ No hay planes disponibles para tu comunidad autónoma")
            return
        
        st.write(f"### 📊 Resultados Anuales para {comunidad}")
        
        ALQUILER_CONTADOR = 0.81
        FINANCIACION_BONO_SOCIAL = 0.03
        IMPUESTO_ELECTRICO = 0.0511
        DESCUENTO_PRIMERA_FACTURA = 5.00
        DIAS_ANUAL = 365
        
        iva_porcentaje = 0.0 if comunidad == "Canarias" else 0.21
        
        resultados = []
        
        for _, plan in planes_disponibles.iterrows():
            if tiene_pi == "Sí":
                precio_kwh = plan['con_pi_kwh']
                coste_pack = plan['pack_iberdrola'] if pack_iberdrola == "Sí" else 0.0
            else:
                precio_kwh = plan['sin_pi_kwh'] 
                coste_pack = 0.0
            
            coste_consumo_anual = consumo * precio_kwh
            coste_potencia_anual = potencia * plan['total_potencia'] * DIAS_ANUAL
            coste_alquiler_anual = ALQUILER_CONTADOR * 12
            coste_financiacion_anual = FINANCIACION_BONO_SOCIAL * DIAS_ANUAL
            coste_pack_anual = coste_pack * 12
            
            subtotal_anual = coste_consumo_anual + coste_potencia_anual + coste_alquiler_anual + coste_financiacion_anual + coste_pack_anual
            impuesto_electrico_anual = subtotal_anual * IMPUESTO_ELECTRICO
            iva_anual = (subtotal_anual + impuesto_electrico_anual) * iva_porcentaje
            total_anual = subtotal_anual + impuesto_electrico_anual + iva_anual - DESCUENTO_PRIMERA_FACTURA
            mensual = total_anual / 12
            
            resultados.append({
                'Plan': plan['plan'],
                'Consumo Anual': round(coste_consumo_anual, 2),
                'Potencia Anual': round(coste_potencia_anual, 2),
                'Alquiler Anual': round(coste_alquiler_anual, 2),
                'Bono Social Anual': round(coste_financiacion_anual, 2),
                'Pack Iberdrola Anual': round(coste_pack_anual, 2),
                'Subtotal Anual': round(subtotal_anual, 2),
                'Imp. Eléctrico Anual': round(impuesto_electrico_anual, 2),
                'IVA Anual': round(iva_anual, 2),
                'Descuento': -DESCUENTO_PRIMERA_FACTURA,
                'Total Anual': round(total_anual, 2) if total_anual > 0 else 0,
                'Mensual': round(mensual, 2)
            })
        
        df_resultados = pd.DataFrame(resultados)
        st.dataframe(df_resultados, use_container_width=True)
        
        if not df_resultados.empty:
            mejor_plan = df_resultados.loc[df_resultados['Total Anual'].idxmin()]
            st.success(f"🎯 **MEJOR OPCIÓN ANUAL**: {mejor_plan['Plan']}")
            st.info(f"💶 **{mejor_plan['Total Anual']}€/año** ({mejor_plan['Mensual']}€/mes)")
            
            st.write("### 📈 Comparativa Anual")
            chart_data = df_resultados.set_index('Plan')['Total Anual']
            st.bar_chart(chart_data)
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo anual: {str(e)}")

def calcular_gas(consumo, tipo_red, tiene_pmg):
    st.info("🔧 Calculadora de Gas en desarrollo...")
    st.write("### 📊 Parámetros introducidos:")
    st.write(f"- **Consumo**: {consumo} kWh")
    st.write(f"- **Tipo Red**: {tipo_red}")
    st.write(f"- **PMG**: {tiene_pmg}")
    st.warning("⚠️ Los cálculos de gas estarán disponibles pronto")

if __name__ == "__main__":
    main()