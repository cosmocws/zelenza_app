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
    
    # PRIMERA PANTALLA: Consultar modelos de factura
    consultar_modelos_factura()
    
    st.markdown("---")
    
    # Comparativas
    st.subheader("🧮 Comparativas")
    tab1, tab2, tab3 = st.tabs(["⚡ Comparativa EXACTA", "📅 Comparativa ESTIMADA", "🔥 Gas"])
    
    with tab1:
        comparativa_exacta()
    with tab2:
        comparativa_estimada()
    with tab3:
        calculadora_gas()

# --- FUNCIONES DE ADMINISTRADOR (SIMPLIFICADAS) ---
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
                    'punta', 'valle', 'total_potencia', 'activo'
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
    
    # Cargar datos actuales
    try:
        df_luz = pd.read_csv("data/precios_luz.csv")
        # Si el DataFrame está vacío, crear uno nuevo
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
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
                    'activo': activo
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

def comparativa_exacta():
    st.subheader("⚡ Comparativa EXACTA")
    st.info("Compara tu consumo exacto con nuestros planes - Se muestran ambos precios CON y SIN Pack Iberdrola")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dias = st.number_input("Días del período", min_value=1, value=30, key="dias_exacta")
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_exacta")
    
    with col2:
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0, key="consumo_exacta")
        costo_actual = st.number_input("¿Cuánto pagaste? (€)", min_value=0.0, value=50.0, key="costo_exacta")
    
    if st.button("🔍 Comparar", type="primary", key="comparar_exacta"):
        calcular_comparacion_exacta(dias, potencia, consumo, costo_actual)

def comparativa_estimada():
    st.subheader("📅 Comparativa ESTIMADA")
    st.info("Estima tu consumo anual con nuestros planes - Se muestran ambos precios CON y SIN Pack Iberdrola")
    
    col1, col2 = st.columns(2)
    
    with col1:
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_estimada")
        # NUEVO: Lo que paga actualmente el cliente
        costo_mensual_actual = st.number_input("¿Cuánto pagas actualmente al mes? (€)", min_value=0.0, value=80.0, key="costo_actual_estimada")
    
    with col2:
        consumo_anual = st.number_input("Consumo anual estimado (kWh)", min_value=0.0, value=7500.0, key="consumo_estimada")
    
    if st.button("📊 Calcular Estimación", type="primary", key="calcular_estimada"):
        calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual)

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Funcionalidad en desarrollo...")

# --- FUNCIONES DE CÁLCULO REALES ---
def calcular_comparacion_exacta(dias, potencia, consumo, costo_actual):
    """Calcula comparación exacta con factura actual - Muestra CON y SIN PI"""
    try:
        # Cargar planes activos
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_activos = df_luz[df_luz['activo'] == True]
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        st.success("🧮 Calculando comparativa...")
        
        # CONSTANTES
        ALQUILER_CONTADOR = 0.81  # €/mes
        PACK_IBERDROLA = 3.95  # €/mes (para cálculo CON PI)
        IMPUESTO_ELECTRICO = 0.0511  # 5.11%
        DESCUENTO_PRIMERA_FACTURA = 5.00  # € (SÍ incluimos descuento bienvenida)
        IVA = 0.21  # 21% (para península)
        
        resultados = []
        
        for _, plan in planes_activos.iterrows():
            # CALCULAR AMBAS OPCIONES: CON PI y SIN PI
            
            # --- OPCIÓN CON PACK IBERDROLA ---
            precio_kwh_con = plan['con_pi_kwh']
            coste_pack_con = PACK_IBERDROLA * (dias / 30)
            
            coste_consumo_con = consumo * precio_kwh_con
            coste_potencia_con = potencia * plan['total_potencia'] * dias
            coste_alquiler_con = ALQUILER_CONTADOR * (dias / 30)
            
            subtotal_con = coste_consumo_con + coste_potencia_con + coste_alquiler_con + coste_pack_con
            impuesto_electrico_con = subtotal_con * IMPUESTO_ELECTRICO
            iva_total_con = (subtotal_con + impuesto_electrico_con) * IVA
            total_nuevo_con = subtotal_con + impuesto_electrico_con + iva_total_con - DESCUENTO_PRIMERA_FACTURA
            
            ahorro_con = costo_actual - total_nuevo_con
            ahorro_anual_con = ahorro_con * (365 / dias)  # Proyección anual
            
            # --- OPCIÓN SIN PACK IBERDROLA ---
            precio_kwh_sin = plan['sin_pi_kwh']
            coste_pack_sin = 0.0
            
            coste_consumo_sin = consumo * precio_kwh_sin
            coste_potencia_sin = potencia * plan['total_potencia'] * dias
            coste_alquiler_sin = ALQUILER_CONTADOR * (dias / 30)
            
            subtotal_sin = coste_consumo_sin + coste_potencia_sin + coste_alquiler_sin + coste_pack_sin
            impuesto_electrico_sin = subtotal_sin * IMPUESTO_ELECTRICO
            iva_total_sin = (subtotal_sin + impuesto_electrico_sin) * IVA
            total_nuevo_sin = subtotal_sin + impuesto_electrico_sin + iva_total_sin - DESCUENTO_PRIMERA_FACTURA
            
            ahorro_sin = costo_actual - total_nuevo_sin
            ahorro_anual_sin = ahorro_sin * (365 / dias)  # Proyección anual
            
            # Añadir ambas opciones a resultados
            resultados.append({
                'Plan': plan['plan'],
                'Pack Iberdrola': '✅ CON',
                'Precio kWh': f"{precio_kwh_con:.3f}€",
                'Coste Nuevo': round(total_nuevo_con, 2),
                'Ahorro Mensual': round(ahorro_con, 2),
                'Ahorro Anual': round(ahorro_anual_con, 2),
                'Estado': '💚 Ahorras' if ahorro_con > 0 else '🔴 Pagas más'
            })
            
            resultados.append({
                'Plan': plan['plan'],
                'Pack Iberdrola': '❌ SIN', 
                'Precio kWh': f"{precio_kwh_sin:.3f}€",
                'Coste Nuevo': round(total_nuevo_sin, 2),
                'Ahorro Mensual': round(ahorro_sin, 2),
                'Ahorro Anual': round(ahorro_anual_sin, 2),
                'Estado': '💚 Ahorras' if ahorro_sin > 0 else '🔴 Pagas más'
            })
        
        # Mostrar resultados
        df_resultados = pd.DataFrame(resultados)
        
        # Encontrar mejor plan (mayor ahorro mensual)
        mejor_plan = df_resultados.loc[df_resultados['Ahorro Mensual'].idxmax()]
        
        st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
        st.info(f"💡 **Incluye descuento de 5€ de bienvenida** | Días: {dias} | Consumo: {consumo}kWh")
        
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
        st.dataframe(df_resultados, use_container_width=True)
        
        # Recomendación
        if mejor_plan['Ahorro Mensual'] > 0:
            st.success(f"🎯 **MEJOR OPCIÓN**: {mejor_plan['Plan']} {mejor_plan['Pack Iberdrola']} Pack - Ahorras {mejor_plan['Ahorro Mensual']}€/mes ({mejor_plan['Ahorro Anual']}€/año)")
        else:
            st.warning("ℹ️ Todos los planes son más caros que tu factura actual")
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {e}")

def calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual):
    """Calcula estimación anual - Muestra CON y SIN PI con ahorro vs actual"""
    try:
        # Cargar planes activos
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_activos = df_luz[df_luz['activo'] == True]
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
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
        
        resultados = []
        
        for _, plan in planes_activos.iterrows():
            # CALCULAR AMBAS OPCIONES: CON PI y SIN PI
            
            # --- OPCIÓN CON PACK IBERDROLA ---
            precio_kwh_con = plan['con_pi_kwh']
            coste_pack_con = PACK_IBERDROLA
            
            coste_consumo_anual_con = consumo_anual * precio_kwh_con
            coste_potencia_anual_con = potencia * plan['total_potencia'] * DIAS_ANUAL
            coste_alquiler_anual_con = ALQUILER_CONTADOR
            
            subtotal_anual_con = coste_consumo_anual_con + coste_potencia_anual_con + coste_alquiler_anual_con + coste_pack_con
            impuesto_electrico_anual_con = subtotal_anual_con * IMPUESTO_ELECTRICO
            iva_anual_con = (subtotal_anual_con + impuesto_electrico_anual_con) * IVA
            total_anual_con = subtotal_anual_con + impuesto_electrico_anual_con + iva_anual_con - DESCUENTO_PRIMERA_FACTURA
            mensual_con = total_anual_con / 12
            
            # Calcular ahorro vs actual
            ahorro_anual_con = costo_anual_actual - total_anual_con
            ahorro_mensual_con = ahorro_anual_con / 12
            
            # --- OPCIÓN SIN PACK IBERDROLA ---
            precio_kwh_sin = plan['sin_pi_kwh']
            coste_pack_sin = 0.0
            
            coste_consumo_anual_sin = consumo_anual * precio_kwh_sin
            coste_potencia_anual_sin = potencia * plan['total_potencia'] * DIAS_ANUAL
            coste_alquiler_anual_sin = ALQUILER_CONTADOR
            
            subtotal_anual_sin = coste_consumo_anual_sin + coste_potencia_anual_sin + coste_alquiler_anual_sin + coste_pack_sin
            impuesto_electrico_anual_sin = subtotal_anual_sin * IMPUESTO_ELECTRICO
            iva_anual_sin = (subtotal_anual_sin + impuesto_electrico_anual_sin) * IVA
            total_anual_sin = subtotal_anual_sin + impuesto_electrico_anual_sin + iva_anual_sin - DESCUENTO_PRIMERA_FACTURA
            mensual_sin = total_anual_sin / 12
            
            # Calcular ahorro vs actual
            ahorro_anual_sin = costo_anual_actual - total_anual_sin
            ahorro_mensual_sin = ahorro_anual_sin / 12
            
            # Añadir ambas opciones a resultados
            resultados.append({
                'Plan': plan['plan'],
                'Pack Iberdrola': '✅ CON',
                'Precio kWh': f"{precio_kwh_con:.3f}€",
                'Mensual Normal': round(mensual_con, 2),
                'Anual': round(total_anual_con, 2),
                'Ahorro Mensual': round(ahorro_mensual_con, 2),
                'Ahorro Anual': round(ahorro_anual_con, 2),
                'Estado': '💚 Ahorras' if ahorro_mensual_con > 0 else '🔴 Pagas más'
            })
            
            resultados.append({
                'Plan': plan['plan'],
                'Pack Iberdrola': '❌ SIN',
                'Precio kWh': f"{precio_kwh_sin:.3f}€", 
                'Mensual Normal': round(mensual_sin, 2),
                'Anual': round(total_anual_sin, 2),
                'Ahorro Mensual': round(ahorro_mensual_sin, 2),
                'Ahorro Anual': round(ahorro_anual_sin, 2),
                'Estado': '💚 Ahorras' if ahorro_mensual_sin > 0 else '🔴 Pagas más'
            })
        
        # Mostrar resultados
        df_resultados = pd.DataFrame(resultados)
        
        # Encontrar plan más económico (mayor ahorro mensual)
        mejor_plan = df_resultados.loc[df_resultados['Ahorro Mensual'].idxmax()]
        
        st.write("### 📊 ESTIMACIÓN ANUAL")
        st.info(f"💡 **Incluye descuento de 5€ de bienvenida** | Consumo anual: {consumo_anual}kWh")
        
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
        st.dataframe(df_resultados, use_container_width=True)
        
        # Recomendación
        if mejor_plan['Ahorro Mensual'] > 0:
            st.success(f"🎯 **MEJOR OPCIÓN**: {mejor_plan['Plan']} {mejor_plan['Pack Iberdrola']} Pack")
            st.info(f"💡 Ahorras {mejor_plan['Ahorro Mensual']}€/mes ({mejor_plan['Ahorro Anual']}€/año) - Pagarías {mejor_plan['Mensual Normal']}€/mes")
        else:
            st.warning(f"ℹ️ Todos los planes son más caros que lo que pagas actualmente ({costo_mensual_actual}€/mes)")
        
        # Gráfico comparativo
        st.write("### 📈 Comparativa Visual (Coste Anual)")
        chart_data = df_resultados.set_index('Plan')['Anual']
        st.bar_chart(chart_data)
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo anual: {e}")

def calculadora_gas():
    st.subheader("🔥 Calculadora de Gas")
    st.info("Funcionalidad en desarrollo...")

if __name__ == "__main__":
    main()
