import streamlit as st
import pandas as pd
import os
import shutil

def authenticate(username, password, user_type):
    try:
        if user_type == "user":
            return (username == st.secrets["credentials"]["user_username"] and 
                    password == st.secrets["credentials"]["user_password"])
        elif user_type == "admin":
            return (username == st.secrets["credentials"]["admin_username"] and 
                    password == st.secrets["credentials"]["admin_password"])
        return False
    except:
        # Fallback por si no hay secrets
        if user_type == "user":
            return username == "usuario" and password == "cliente123"
        elif user_type == "admin":
            return username == "admin" and password == "admin123"
        return False
        
# Configuración de la página
st.set_page_config(
    page_title="Zelenza CEX - Iberdrola",
    page_icon="⚡",
    layout="wide"
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
    "config_pmg.json": json.dumps({"coste": PMG_COSTE, "iva": PMG_IVA}, indent=4)
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
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        mostrar_aplicacion_principal()

def mostrar_login():
    st.header("🔐 Iniciar Sesión")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Acceso Usuario")
        user_user = st.text_input("Usuario", key="user_user")
        user_pass = st.text_input("Contraseña", type="password", key="user_pass")
        
        if st.button("Entrar como Usuario", use_container_width=True, type="secondary"):
            if authenticate(user_user, user_pass, "user"):
                st.session_state.authenticated = True
                st.session_state.user_type = "user"
                st.session_state.username = user_user
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    
    with col2:
        st.subheader("🔧 Acceso Administrador")
        admin_user = st.text_input("Usuario Administrador", key="admin_user")
        admin_pass = st.text_input("Contraseña", type="password", key="admin_pass")
        
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Electricidad", "🔥 Gas", "📄 Facturas", "☀️ Excedentes"])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_modelos_factura()
    with tab4:
        gestion_excedentes()

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    st.header("👤 Portal del Cliente")
    
    # PRIMERA PANTALLA: Consultar modelos de factura
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Comparativas
    st.subheader("🧮 Comparativas")
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Comparativa EXACTA", "📅 Comparativa ESTIMADA", "🔥 Gas", "📋 CUPS Naturgy"])
    
    with tab1:
        comparativa_exacta()
    with tab2:
        comparativa_estimada()
    with tab3:
        calculadora_gas()
    with tab4:
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
    
    st.info("Compara planes de gas con cálculo EXACTO o ESTIMADO")
    
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
        else:
            consumo_mes = st.number_input(
                "**Consumo del mes actual (kWh):**", 
                min_value=0, value=300, step=10
            )
            consumo_anual = consumo_mes * 12
            st.info(f"Consumo anual estimado: {consumo_anual:,.0f} kWh")
    
    with col2:
        tiene_pmg = st.checkbox("**¿Contratar PMG?**", value=True,
                               help="Pack Mantenimiento Gas - Mantenimiento y asistencia")
        es_canarias = st.checkbox("**¿Ubicación en Canarias?**", 
                                 help="No aplica IVA en Canarias")
    
    # Determinar RL recomendado automáticamente
    rl_recomendado = determinar_rl_gas(consumo_anual)
    
    if st.button("🔄 Calcular Comparativa Gas", type="primary"):
        resultados = []
        
        for rl, plan in planes_gas.items():
            if plan["activo"]:
                coste_anual = calcular_coste_gas_completo(
                    plan, consumo_anual, tiene_pmg, es_canarias
                )
                
                # Calcular ahorro vs precio original
                coste_original = consumo_anual * plan["precio_original_kwh"]
                ahorro = coste_original - coste_anual
                
                # Determinar si es recomendado
                recomendado = "✅" if rl == rl_recomendado else ""
                
                resultados.append({
                    "Plan": rl,
                    "Rango": plan["rango"],
                    "Coste Anual": f"€{coste_anual:,.2f}",
                    "Ahorro vs Original": f"€{ahorro:,.2f}",
                    "Recomendado": recomendado
                })
        
        # Mostrar resultados
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            st.dataframe(df_resultados, use_container_width=True)
            
            # Mostrar detalles del PMG
            coste_pmg_anual = calcular_pmg(tiene_pmg, es_canarias)
            if tiene_pmg:
                st.info(f"**📦 Coste PMG anual:** €{coste_pmg_anual:,.2f} ({pmg_coste}€/mes {'sin IVA' if es_canarias else 'con IVA'})")
            
            # Recomendación
            plan_recomendado = next((p for p in resultados if p['Recomendado'] == '✅'), None)
            if plan_recomendado:
                st.success(f"🎯 **RECOMENDACIÓN**: Plan {plan_recomendado['Plan']} - {plan_recomendado['Rango']} - Coste anual: {plan_recomendado['Coste Anual']}")

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
        
        st.success("🧮 Calculando comparativa...")
        
        # CONSTANTES
        ALQUILER_CONTADOR = 0.81  # €/mes
        PACK_IBERDROLA = 3.95  # €/mes (para cálculo CON PI)
        IMPUESTO_ELECTRICO = 0.0511  # 5.11%
        DESCUENTO_PRIMERA_FACTURA = 5.00  # €
        IVA = 0.21  # 21%
        
        # Primero calcular todos los planes para encontrar el máximo ahorro
        todos_resultados = []
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR SI EL PLAN ESTÁ DISPONIBLE EN LA COMUNIDAD SELECCIONADA
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan  # Por compatibilidad con planes antiguos
            )
            
            if not disponible_en_comunidad:
                continue  # Saltar planes no disponibles en esta comunidad
            
            # VERIFICAR SI ES PLAN AHORRO AUTOMÁTICO
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in plan['plan'].upper()
            # VERIFICAR SI ES PLAN ESPECIAL PLUS
            es_especial_plus = "ESPECIAL PLUS" in plan['plan'].upper()
            
            for tiene_pi in [True, False]:  # Calcular ambas opciones: CON y SIN PI
                
                if es_ahorro_automatico:
                    # --- CÁLCULO ESPECIAL PARA AHORRO AUTOMÁTICO ---
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo, dias, tiene_pi, es_anual=False
                    )
                    
                    precio_kwh = f"0.215€/0.105€*"
                    coste_consumo = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA * (dias / 30) if tiene_pi else 0.0
                    
                    # Bonificación mensual fija para Ahorro Automático
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
                    
                    coste_consumo = consumo * precio_kwh
                    bonificacion_mensual = 0.0  # Sin bonificación para planes normales
                
                # CÁLCULOS COMUNES PARA TODOS LOS PLANES
                coste_potencia = potencia * plan['total_potencia'] * dias
                coste_alquiler = ALQUILER_CONTADOR * (dias / 30)
                
                # Cálculo de excedentes (se resta del consumo y se suma como ingreso)
                ingreso_excedentes = excedente_kwh * precio_excedente
                consumo_neto = max(0, consumo - excedente_kwh)
                
                # Si hay excedentes, recalcular el coste de consumo
                if excedente_kwh > 0:
                    if es_ahorro_automatico:
                        # Para ahorro automático, recalcular con consumo neto
                        calculo_ahorro_neto = calcular_plan_ahorro_automatico(
                            plan, consumo_neto, dias, tiene_pi, es_anual=False
                        )
                        coste_consumo = calculo_ahorro_neto['coste_consumo']
                    else:
                        coste_consumo = consumo_neto * (plan['con_pi_kwh'] if tiene_pi else plan['sin_pi_kwh'])
                
                # SUBTOTAL
                subtotal = coste_consumo + coste_potencia + coste_alquiler + coste_pack
                
                # IMPUESTOS
                impuesto_electrico = subtotal * IMPUESTO_ELECTRICO
                iva_total = (subtotal + impuesto_electrico) * IVA
                
                # TOTAL (con descuento bienvenida, bonificación e ingreso por excedentes)
                total_bruto = subtotal + impuesto_electrico + iva_total
                total_neto = total_bruto - DESCUENTO_PRIMERA_FACTURA - bonificacion_mensual - ingreso_excedentes
                
                # Asegurar que no sea negativo
                total_nuevo = max(0, total_neto)
                
                # Calcular ahorro
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
                    info_extra += f" | ☀️ +{ingreso_excedentes:.2f}€ excedentes"
                
                # Información de disponibilidad por comunidad
                if len(comunidades_plan) == 1 and 'Toda España' in comunidades_plan:
                    info_extra += " | 🗺️ Toda España"
                elif len(comunidades_plan) < 5:
                    info_extra += f" | 🗺️ {', '.join(comunidades_plan)}"
                else:
                    info_extra += f" | 🗺️ {len(comunidades_plan)} CCAA"
                
                todos_resultados.append({
                    'plan_data': plan,
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Coste Nuevo': round(total_nuevo, 2),
                    'Ahorro Mensual': round(ahorro, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                })
        
        # Encontrar el MÁXIMO ahorro de todos los planes (excluyendo Especial Plus)
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        # FILTRAR resultados según regla del Especial Plus (SIN AVISOS)
        resultados_finales = []
        for resultado in todos_resultados:
            # Si NO es Especial Plus, siempre se muestra
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            # Si ES Especial Plus, solo se muestra si el máximo ahorro es MENOR que el umbral
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        # Mostrar resultados filtrados
        df_resultados = pd.DataFrame(resultados_finales)
        
        if df_resultados.empty:
            st.warning(f"ℹ️ No hay planes disponibles para {comunidad} según los criterios de filtrado")
            return
        
        # Encontrar mejor plan
        mejor_plan = df_resultados.loc[df_resultados['Ahorro Mensual'].idxmax()]
        
        st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
        
        # Información sobre comunidad y excedentes
        info_comunidad = f" | 🗺️ **Comunidad:** {comunidad}"
        if excedente_kwh > 0:
            st.info(f"💡 **Incluye descuento de 5€ de bienvenida** {info_comunidad} | ☀️ **Excedentes:** {excedente_kwh}kWh x {precio_excedente}€/kWh = +{excedente_kwh * precio_excedente:.2f}€ | Días: {dias} | Consumo neto: {max(0, consumo - excedente_kwh):.1f}kWh")
        else:
            st.info(f"💡 **Incluye descuento de 5€ de bienvenida** {info_comunidad} | Días: {dias} | Consumo: {consumo}kWh")
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Coste Actual", f"{costo_actual}€")
        with col2:
            st.metric("💰 Coste Nuevo", f"{mejor_plan['Coste Nuevo']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan['Ahorro Mensual']}€" if mejor_plan['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan['Ahorro Anual']}€")
        
        # Tabla comparativa
        st.dataframe(df_resultados[['Plan', 'Pack Iberdrola', 'Precio kWh', 'Coste Nuevo', 'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']], 
                    use_container_width=True)
        
        # Recomendación
        if mejor_plan['Ahorro Mensual'] > 0:
            mensaje = f"🎯 **MEJOR OPCIÓN**: {mejor_plan['Plan']} {mejor_plan['Pack Iberdrola']} Pack - Ahorras {mejor_plan['Ahorro Mensual']}€/mes ({mejor_plan['Ahorro Anual']}€/año)"
            if mejor_plan['Info Extra']:
                mensaje += mejor_plan['Info Extra']
            st.success(mensaje)
        else:
            st.warning("ℹ️ Todos los planes son más caros que tu factura actual")
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {e}")

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
        
        # Primero calcular todos los planes para encontrar el máximo ahorro
        todos_resultados = []
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR SI EL PLAN ESTÁ DISPONIBLE EN LA COMUNIDAD SELECCIONADA
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan  # Por compatibilidad con planes antiguos
            )
            
            if not disponible_en_comunidad:
                continue  # Saltar planes no disponibles en esta comunidad
            
            # VERIFICAR SI ES PLAN AHORRO AUTOMÁTICO
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in plan['plan'].upper()
            # VERIFICAR SI ES PLAN ESPECIAL PLUS
            es_especial_plus = "ESPECIAL PLUS" in plan['plan'].upper()
            
            for tiene_pi in [True, False]:  # Calcular ambas opciones: CON y SIN PI
                
                if es_ahorro_automatico:
                    # --- CÁLCULO ESPECIAL PARA AHORRO AUTOMÁTICO (ANUAL) ---
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo_anual, DIAS_ANUAL, tiene_pi, es_anual=True
                    )
                    
                    precio_kwh = f"0.215€/0.105€*"
                    coste_consumo_anual = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA if tiene_pi else 0.0
                    
                    # Bonificación anual fija para Ahorro Automático
                    if tiene_pi:
                        bonificacion_anual = 10.00 * 12  # 10€/mes con PI = 120€/año
                    else:
                        bonificacion_anual = 8.33 * 12   # 8.33€/mes sin PI = 100€/año
                    
                    # Información adicional para mostrar
                    info_extra = ""
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d/año a 0.105€"
                    
                else:
                    # --- CÁLCULO NORMAL PARA OTROS PLANES ---
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo_anual = consumo_anual * precio_kwh
                    bonificacion_anual = 0.0  # Sin bonificación para planes normales
                    info_extra = ""
                
                # Información adicional para Especial Plus
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                # CÁLCULOS COMUNES PARA TODOS LOS PLANES
                coste_potencia_anual = potencia * plan['total_potencia'] * DIAS_ANUAL
                coste_alquiler_anual = ALQUILER_CONTADOR
                
                # Cálculo de excedentes anuales
                excedente_anual_kwh = excedente_mensual_kwh * 12
                ingreso_excedentes_anual = excedente_anual_kwh * precio_excedente
                consumo_neto_anual = max(0, consumo_anual - excedente_anual_kwh)
                
                # Si hay excedentes, recalcular el coste de consumo
                if excedente_anual_kwh > 0:
                    if es_ahorro_automatico:
                        # Para ahorro automático, recalcular con consumo neto
                        calculo_ahorro_neto = calcular_plan_ahorro_automatico(
                            plan, consumo_neto_anual, DIAS_ANUAL, tiene_pi, es_anual=True
                        )
                        coste_consumo_anual = calculo_ahorro_neto['coste_consumo']
                    else:
                        coste_consumo_anual = consumo_neto_anual * (plan['con_pi_kwh'] if tiene_pi else plan['sin_pi_kwh'])
                
                # SUBTOTAL ANUAL
                subtotal_anual = coste_consumo_anual + coste_potencia_anual + coste_alquiler_anual + coste_pack
                
                # IMPUESTOS ANUALES
                impuesto_electrico_anual = subtotal_anual * IMPUESTO_ELECTRICO
                iva_anual = (subtotal_anual + impuesto_electrico_anual) * IVA
                
                # TOTAL ANUAL (con descuento bienvenida, bonificación e ingreso por excedentes)
                total_bruto_anual = subtotal_anual + impuesto_electrico_anual + iva_anual
                total_neto_anual = total_bruto_anual - DESCUENTO_PRIMERA_FACTURA - bonificacion_anual - ingreso_excedentes_anual
                
                # Asegurar que no sea negativo
                total_anual = max(0, total_neto_anual)
                mensual = total_anual / 12
                
                # Calcular ahorro vs actual
                ahorro_anual = costo_anual_actual - total_anual
                ahorro_mensual = ahorro_anual / 12
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh:.3f}€" if not isinstance(precio_kwh, str) else precio_kwh
                
                # Información adicional para excedentes
                if excedente_anual_kwh > 0:
                    info_extra += f" | ☀️ +{ingreso_excedentes_anual:.2f}€/año excedentes"
                
                # Información de disponibilidad por comunidad
                if len(comunidades_plan) == 1 and 'Toda España' in comunidades_plan:
                    info_extra += " | 🗺️ Toda España"
                elif len(comunidades_plan) < 5:
                    info_extra += f" | 🗺️ {', '.join(comunidades_plan)}"
                else:
                    info_extra += f" | 🗺️ {len(comunidades_plan)} CCAA"
                
                # Añadir a resultados
                todos_resultados.append({
                    'plan_data': plan,
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Mensual Normal': round(mensual, 2),
                    'Anual': round(total_anual, 2),
                    'Ahorro Mensual': round(ahorro_mensual, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro_mensual > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                })
        
        # Encontrar el MÁXIMO ahorro de todos los planes (excluyendo Especial Plus)
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        # FILTRAR resultados según regla del Especial Plus (SIN AVISOS)
        resultados_finales = []
        for resultado in todos_resultados:
            # Si NO es Especial Plus, siempre se muestra
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            # Si ES Especial Plus, solo se muestra si el máximo ahorro es MENOR que el umbral
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        # Mostrar resultados filtrados
        df_resultados = pd.DataFrame(resultados_finales)
        
        if df_resultados.empty:
            st.warning(f"ℹ️ No hay planes disponibles para {comunidad} según los criterios de filtrado")
            return
        
        # Encontrar plan más económico (mayor ahorro mensual)
        mejor_plan = df_resultados.loc[df_resultados['Ahorro Mensual'].idxmax()]
        
        st.write("### 📊 ESTIMACIÓN ANUAL")
        
        # Información sobre comunidad y excedentes
        info_comunidad = f" | 🗺️ **Comunidad:** {comunidad}"
        if excedente_mensual_kwh > 0:
            st.info(f"💡 **Incluye descuento de 5€ de bienvenida** {info_comunidad} | ☀️ **Excedentes:** {excedente_mensual_kwh}kWh/mes x {precio_excedente}€/kWh = +{excedente_mensual_kwh * precio_excedente * 12:.2f}€/año | Consumo neto anual: {max(0, consumo_anual - (excedente_mensual_kwh * 12)):.0f}kWh")
        else:
            st.info(f"💡 **Incluye descuento de 5€ de bienvenida** {info_comunidad} | Consumo anual: {consumo_anual}kWh")
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Actual Mensual", f"{costo_mensual_actual}€")
        with col2:
            st.metric("💰 Nuevo Mensual", f"{mejor_plan['Mensual Normal']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan['Ahorro Mensual']}€" if mejor_plan['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan['Ahorro Anual']}€")
        
        # Tabla comparativa
        st.dataframe(df_resultados[['Plan', 'Pack Iberdrola', 'Precio kWh', 'Mensual Normal', 'Anual', 'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']], 
                    use_container_width=True)
        
        # Recomendación
        if mejor_plan['Ahorro Mensual'] > 0:
            mensaje = f"🎯 **MEJOR OPCIÓN**: {mejor_plan['Plan']} {mejor_plan['Pack Iberdrola']} Pack"
            mensaje += f" - Ahorras {mejor_plan['Ahorro Mensual']}€/mes ({mejor_plan['Ahorro Anual']}€/año)"
            if mejor_plan['Info Extra']:
                mensaje += mejor_plan['Info Extra']
            st.success(mensaje)
            st.info(f"💡 Pagarías {mejor_plan['Mensual Normal']}€/mes normalmente")
        else:
            st.warning(f"ℹ️ Todos los planes son más caros que lo que pagas actualmente ({costo_mensual_actual}€/mes)")
        
        # Gráfico comparativo
        st.write("### 📈 Comparativa Visual (Coste Anual)")
        chart_data = df_resultados.set_index('Plan')['Anual']
        st.bar_chart(chart_data)
            
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
    """Calcula coste total de gas incluyendo PMG"""
    # Coste del gas
    if tiene_pmg:
        termino_fijo = plan["termino_fijo_con_pmg"]
        termino_variable = plan["termino_variable_con_pmg"]
    else:
        termino_fijo = plan["termino_fijo_sin_pmg"]
        termino_variable = plan["termino_variable_sin_pmg"]
    
    coste_fijo = termino_fijo * 12  # Anual
    coste_variable = consumo_kwh * termino_variable
    coste_gas = coste_fijo + coste_variable
    
    # Coste PMG
    coste_pmg = calcular_pmg(tiene_pmg, es_canarias)
    
    return coste_gas + coste_pmg

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