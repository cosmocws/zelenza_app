import streamlit as st
import os
import shutil
from modules.auth import (
    mostrar_login, verificar_sesion, 
    cargar_config_sistema, cerrar_sesion
)
from modules.utils import inicializar_datos
from modules.electricity import gestion_electricidad
from modules.gas import gestion_gas
from modules.users import gestion_usuarios
from modules.pvd import gestion_pvd_admin, gestion_pvd_usuario
from modules.invoices import gestion_modelos_factura, consultar_modelos_factura
from modules.config import gestion_excedentes, gestion_config_sistema
from modules.calculators import (
    calcular_comparacion_exacta, calcular_estimacion_anual,
    calcular_coste_gas_completo, determinar_rl_gas, calcular_pmg
)
from modules.electricity import COMUNIDADES_AUTONOMAS

# Configuración de la página
st.set_page_config(
    page_title="Zelenza CEX - Iberdrola",
    page_icon="⚡",
    layout="wide"
)

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

def mostrar_panel_administrador():
    """Panel de administración"""
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

def mostrar_panel_usuario():
    """Panel del usuario normal"""
    # Primero verificar sesión
    if not verificar_sesion():
        mostrar_login()
        return
    
    # Mostrar información del usuario
    from modules.utils import cargar_configuracion_usuarios
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
        
        # Selección de comunidad autónoma
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
        costo_mensual_actual = st.number_input("¿Cuánto pagas actualmente al mes? (€)", min_value=0.0, value=80.0, key="costo_actual_estimada")
    
    with col2:
        # Selección de comunidad autónoma
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
    
    import json
    from modules.gas import PLANES_GAS_ESTRUCTURA, PMG_COSTE, PMG_IVA
    
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
        es_canarias = st.checkbox("**¿Ubicación en Canarias?**", 
                                 help="No aplica IVA en Canarias")
    
    # Determinar RL recomendado automáticamente
    rl_recomendado = determinar_rl_gas(consumo_anual)
    
    if st.button("🔄 Calcular Comparativa Gas", type="primary"):
        from modules.utils import cargar_configuracion_usuarios
        
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

if __name__ == "__main__":
    main()