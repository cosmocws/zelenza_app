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
            'punta', 'valle', 'total_potencia', 'activo', 'comunidades'
        ])
        df_vacio.to_csv("data/precios_luz.csv", index=False)

def obtener_comunidad_por_cp(codigo_postal):
    """
    Determina la comunidad autónoma basándose en el código postal
    (Simplificado - en producción usarías una base de datos completa)
    """
    try:
        cp = int(codigo_postal)
    except:
        return None
    
    # Mapeo simplificado de códigos postales a comunidades
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
    
    # --- RESET TEMPORAL - ELIMINAR DESPUÉS ---
    st.error("🚨 RESET TEMPORAL DE DATOS")
    if st.button("🔄 Resetear datos a vacío (SOLO PRIMERA VEZ)"):
        df_vacio = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'comunidades'
        ])
        df_vacio.to_csv("data/precios_luz.csv", index=False)
        st.success("✅ Datos reseteados. Ahora puedes crear tus propios planes.")
        st.rerun()
    # --- FIN RESET TEMPORAL ---
    
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
                'punta', 'valle', 'total_potencia', 'activo', 'comunidades'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'comunidades'
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
            
            # NUEVO CAMPO: Comunidades autónomas
            # Manejar el caso cuando comunidades es string (legado) o lista
            comunidades_default = ["Toda España"]
            if st.session_state.editing_plan:
                if isinstance(st.session_state.editing_plan['comunidades'], list):
                    comunidades_default = st.session_state.editing_plan['comunidades']
                elif st.session_state.editing_plan['comunidades'] and isinstance(st.session_state.editing_plan['comunidades'], str):
                    # Convertir string a lista si es necesario
                    comunidades_default = [st.session_state.editing_plan['comunidades']]
            
            comunidades = st.multiselect(
                "Comunidades Autónomas*",
                options=COMUNIDADES_AUTONOMAS,
                default=comunidades_default
            )
            st.caption("Selecciona 'Toda España' o comunidades específicas")
        
        # Botón de envío del formulario
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
                # Preparar datos para confirmación
                st.session_state.pending_plan = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo,
                    'comunidades': comunidades
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
                
                # Guardar y limpiar estado
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
    
    # Opción para eliminar planes (FUERA DE CUALQUIER FORM)
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
    st.info("Calcula el coste para un período específico según tu ubicación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        codigo_postal = st.text_input("Código Postal*", placeholder="28001", max_length=5)
        dias = st.number_input("Días del período", min_value=1, value=30)
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3)
    
    with col2:
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0)
        tiene_pi = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"])
    
    # Validar código postal
    if st.button("Calcular", type="primary"):
        if not codigo_postal or not codigo_postal.isdigit() or len(codigo_postal) != 5:
            st.error("❌ Por favor, introduce un código postal válido (5 dígitos)")
        else:
            # Aquí irá la lógica de cálculo filtrada por comunidad autónoma
            comunidad = obtener_comunidad_por_cp(codigo_postal)
            if comunidad:
                st.success(f"📍 Ubicación detectada: {comunidad}")
                calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, codigo_postal, comunidad)
            else:
                st.error("❌ No se pudo determinar la comunidad autónoma. Usando cálculo general.")
                calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, codigo_postal, "Toda España")

def calculadora_anual():
    st.subheader("📅 Calculadora Anual de Electricidad")
    st.info("Calcula el coste anual estimado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        codigo_postal = st.text_input("Código Postal*", placeholder="28001", max_length=5, key="cp_anual")
        potencia_anual = st.number_input("Potencia contratada anual (kW)", min_value=1.0, value=3.3, key="pot_anual")
    
    with col2:
        consumo_anual = st.number_input("Consumo anual (kWh)", min_value=0.0, value=7500.0)
        tiene_pi_anual = st.radio("¿Tiene Pensión Igualatoria?", ["Sí", "No"], key="pi_anual")
    
    if st.button("Calcular Anual", type="primary"):
        if not codigo_postal or not codigo_postal.isdigit() or len(codigo_postal) != 5:
            st.error("❌ Por favor, introduce un código postal válido (5 dígitos)")
        else:
            comunidad = obtener_comunidad_por_cp(codigo_postal)
            if comunidad:
                st.success(f"📍 Ubicación detectada: {comunidad}")
                calcular_electricidad_anual(potencia_anual, consumo_anual, tiene_pi_anual, codigo_postal, comunidad)
            else:
                st.error("❌ No se pudo determinar la comunidad autónoma. Usando cálculo general.")
                calcular_electricidad_anual(potencia_anual, consumo_anual, tiene_pi_anual, codigo_postal, "Toda España")

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Calcula el coste de tu consumo de gas")
    
    consumo_gas = st.number_input("Consumo de gas (kWh)", min_value=0.0, value=1000.0)
    tipo_red = st.selectbox("Tipo de Red Local", ["RL1", "RL2", "RL3"])
    tiene_pmg = st.radio("¿Tiene PMG?", ["Sí", "No"])
    
    if st.button("Calcular Gas", type="primary"):
        calcular_gas(consumo_gas, tipo_red, tiene_pmg)

# Funciones de cálculo (placeholder)
def calcular_electricidad_diaria(dias, potencia, consumo, tiene_pi, codigo_postal, comunidad):
    st.info("🔧 Cálculos en desarrollo...")
    st.write(f"Parámetros recibidos: {dias} días, {potencia} kW, {consumo} kWh, PI: {tiene_pi}")
    st.write(f"Ubicación: CP {codigo_postal} - {comunidad}")
    # Aquí implementaremos la lógica basada en tu tabla

def calcular_electricidad_anual(potencia, consumo, tiene_pi, codigo_postal, comunidad):
    st.info("🔧 Cálculos anuales en desarrollo...")
    st.write(f"Parámetros recibidos: {potencia} kW, {consumo} kWh, PI: {tiene_pi}")
    st.write(f"Ubicación: CP {codigo_postal} - {comunidad}")

def calcular_gas(consumo, tipo_red, tiene_pmg):
    st.info("🔧 Cálculos de gas en desarrollo...")

if __name__ == "__main__":
    main()
