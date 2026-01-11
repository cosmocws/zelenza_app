import streamlit as st
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz

from config import COMUNIDADES_AUTONOMAS
from calculation import (
    calcular_plan_ahorro_automatico, determinar_rl_gas,
    calcular_coste_gas_completo, calcular_pmg
)
from database import (
    cargar_configuracion_usuarios, 
    cargar_config_pvd, 
    cargar_config_sistema,
    cargar_cola_pvd_grupo,
    guardar_cola_pvd_grupo,
    obtener_todas_colas_pvd
)
from pvd_system import (
    temporizador_pvd_mejorado,
    solicitar_pausa,
    crear_temporizador_html_simplificado
)
from utils import obtener_hora_madrid, formatear_hora_madrid

# ==============================================
# FUNCIONES DE VISUALIZACIÓN
# ==============================================

# Estados PVD para usuarios
ESTADOS_PVD_USUARIO = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

# ==============================================
# FUNCIONES DE MODELOS DE FACTURA
# ==============================================

def consultar_modelos_factura():
    """Consultar modelos de factura para usuarios"""
    st.subheader("📊 Modelos de Factura")
    
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
    
    carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
    archivos = os.listdir(carpeta_empresa)
    
    if archivos:
        st.write(f"### 📋 Modelos disponibles para {empresa_seleccionada}:")
        for archivo in archivos:
            ruta_completa = os.path.join(carpeta_empresa, archivo)
            st.write(f"**Modelo:** {archivo}")
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                st.image(ruta_completa, width=600)
            elif archivo.lower().endswith('.pdf'):
                st.write(f"📄 Archivo PDF disponible para descargar")
                with open(ruta_completa, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Descargar PDF",
                        data=pdf_file,
                        file_name=archivo,
                        mime="application/pdf"
                    )
            st.markdown("---")
    else:
        st.warning(f"⚠️ No hay modelos de factura subidos para {empresa_seleccionada}")

# ==============================================
# FUNCIONES DE COMPARATIVAS
# ==============================================

def comparativa_exacta():
    """Comparativa exacta para usuarios"""
    st.subheader("⚡ Comparativa EXACTA")
    st.info("Compara tu consumo exacto con nuestros planes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dias = st.number_input("Días del período", min_value=1, value=30, key="dias_exacta")
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_exacta")
        consumo = st.number_input("Consumo (kWh)", min_value=0.0, value=250.0, key="consumo_exacta")
    
    with col2:
        costo_actual = st.number_input("¿Cuánto pagaste? (€)", min_value=0.0, value=50.0, key="costo_exacta")
        comunidad = st.selectbox("Selecciona tu Comunidad Autónoma", COMUNIDADES_AUTONOMAS, key="comunidad_exacta")
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_exacta")
        excedente_kwh = 0.0
        if con_excedentes:
            excedente_kwh = st.number_input("kWh de excedente este mes", min_value=0.0, value=50.0, key="excedente_exacta")
    
    if st.button("🔍 Comparar", type="primary", key="comparar_exacta"):
        from calculation_extended import calcular_comparacion_exacta
        calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh)

def comparativa_estimada():
    """Comparativa estimada para usuarios"""
    st.subheader("📅 Comparativa ESTIMADA")
    st.info("Estima tu consumo anual con nuestros planes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        potencia = st.number_input("Potencia contratada (kW)", min_value=1.0, value=3.3, key="potencia_estimada")
        consumo_anual = st.number_input("Consumo anual estimado (kWh)", min_value=0.0, value=7500.0, key="consumo_estimada")
        costo_mensual_actual = st.number_input("¿Cuánto pagas actualmente al mes? (€)", min_value=0.0, value=80.0, key="costo_actual_estimada")
    
    with col2:
        comunidad = st.selectbox("Selecciona tu Comunidad Autónoma", COMUNIDADES_AUTONOMAS, key="comunidad_estimada")
        con_excedentes = st.checkbox("¿Tienes excedentes de placas solares?", key="excedentes_estimada")
        excedente_mensual_kwh = 0.0
        if con_excedentes:
            excedente_mensual_kwh = st.number_input("kWh de excedente mensual promedio", min_value=0.0, value=40.0, key="excedente_estimada")
    
    if st.button("📊 Calcular Estimación", type="primary", key="calcular_estimada"):
        from calculation_extended import calcular_estimacion_anual
        calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh)

# ==============================================
# FUNCIONES DE CÁLCULO DE GAS
# ==============================================

def calculadora_gas():
    """Calculadora de gas para usuarios"""
    st.subheader("🔥 Calculadora de Gas")
    
    try:
        with open('data/planes_gas.json', 'r', encoding='utf-8') as f:
            planes_gas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        from config import PLANES_GAS_ESTRUCTURA
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    try:
        with open('data/config_pmg.json', 'r', encoding='utf-8') as f:
            config_pmg = json.load(f)
        pmg_coste = config_pmg["coste"]
        pmg_iva = config_pmg["iva"]
    except (FileNotFoundError, json.JSONDecodeError):
        from config import PMG_COSTE, PMG_IVA
        pmg_coste = PMG_COSTE
        pmg_iva = PMG_IVA
    
    st.info("Compara planes de gas con cálculo EXACTO o ESTIMADO")
    
    tipo_calculo = st.radio("**Tipo de cálculo:**", ["📊 Estimación anual", "📈 Cálculo exacto mes actual"], horizontal=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if tipo_calculo == "📊 Estimación anual":
            consumo_anual = st.number_input("**Consumo anual estimado (kWh):**", min_value=0, value=5000, step=100)
            costo_actual_input = st.number_input("**¿Cuánto pagas actualmente al año? (€):**", min_value=0.0, value=600.0, step=10.0)
            costo_actual_anual = costo_actual_input
            costo_actual_mensual = costo_actual_anual / 12
        else:
            consumo_mes = st.number_input("**Consumo del mes actual (kWh):**", min_value=0, value=300, step=10)
            consumo_anual = consumo_mes * 12
            st.info(f"Consumo anual estimado: {consumo_anual:,.0f} kWh")
            costo_actual_input = st.number_input("**¿Cuánto pagaste este mes? (€):**", min_value=0.0, value=50.0, step=5.0)
            costo_actual_mensual = costo_actual_input
            costo_actual_anual = costo_actual_mensual * 12
    
    with col2:
        es_canarias = st.checkbox("**¿Ubicación en Canarias?**", help="No aplica IVA en Canarias")
    
    rl_recomendado = determinar_rl_gas(consumo_anual)
    
    if st.button("🔄 Calcular Comparativa Gas", type="primary"):
        # Obtener planes permitidos para el usuario
        resultados = _obtener_resultados_gas_usuario(planes_gas, consumo_anual, es_canarias, rl_recomendado)
        
        if resultados:
            _mostrar_resultados_gas(resultados, tipo_calculo, consumo_anual, costo_actual_anual, costo_actual_mensual, es_canarias)
        else:
            st.warning("⚠️ No hay planes de gas activos o permitidos para mostrar")
            st.info("Contacta con el administrador para obtener acceso a los planes")

def _obtener_resultados_gas_usuario(planes_gas, consumo_anual, es_canarias, rl_recomendado):
    """Obtiene resultados de gas permitidos para el usuario actual"""
    try:
        # Obtener información del usuario y permisos
        usuarios_config = cargar_configuracion_usuarios()
        config_sistema = cargar_config_sistema()
        grupos = config_sistema.get("grupos_usuarios", {})
        
        usuario_id = st.session_state.username
        grupo_usuario = ""
        planes_permitidos = []
        
        if usuario_id in usuarios_config:
            config_usuario = usuarios_config[usuario_id]
            grupo_usuario = config_usuario.get('grupo', '')
            
            if grupo_usuario and grupo_usuario in grupos:
                # Usar planes del grupo
                permisos_grupo = grupos[grupo_usuario]
                planes_permitidos = permisos_grupo.get("planes_gas", [])
            else:
                # Usar planes específicos del usuario
                planes_permitidos = config_usuario.get("planes_gas", [])
        else:
            # Usuario no existe en configuración
            planes_permitidos = []
        
        # Si planes_permitidos está vacío, intentar usar "TODOS"
        if not planes_permitidos:
            # Verificar si el usuario tiene permisos especiales
            if usuario_id in usuarios_config:
                permisos_usuario = usuarios_config[usuario_id]
                if "planes_gas" in permisos_usuario:
                    planes_permitidos = permisos_usuario["planes_gas"]
        
        # Si aún está vacío, usar todos los planes
        if not planes_permitidos or planes_permitidos == "TODOS":
            planes_permitidos = ["RL1", "RL2", "RL3"]
        
        # Filtrar planes activos y permitidos
        resultados = []
        for rl, plan in planes_gas.items():
            if rl not in planes_permitidos or not plan["activo"]:
                continue
            
            # Calcular con y sin PMG
            for tiene_pmg in [True, False]:
                resultado = _calcular_resultado_gas(
                    rl, plan, consumo_anual, tiene_pmg, es_canarias, rl_recomendado
                )
                if resultado:
                    resultados.append(resultado)
        
        return resultados
        
    except Exception as e:
        st.error(f"Error obteniendo planes de gas: {e}")
        return []

def _calcular_resultado_gas(rl, plan, consumo_anual, tiene_pmg, es_canarias, rl_recomendado):
    """Calcula un resultado individual de gas"""
    try:
        coste_anual = calcular_coste_gas_completo(plan, consumo_anual, tiene_pmg, es_canarias)
        coste_mensual = coste_anual / 12
        
        coste_original = consumo_anual * plan["precio_original_kwh"]
        ahorro_vs_original = coste_original - coste_anual
        
        # Obtener costo actual del usuario (simplificado)
        costo_actual_anual = consumo_anual * 0.12  # Estimación
        ahorro_vs_actual_anual = costo_actual_anual - coste_anual
        ahorro_vs_actual_mensual = ahorro_vs_actual_anual / 12
        
        recomendado = "✅" if rl == rl_recomendado else ""
        
        if ahorro_vs_actual_anual > 0:
            estado = "💚 Ahorras"
        elif ahorro_vs_actual_anual == 0:
            estado = "⚖️ Igual"
        else:
            estado = "🔴 Pagas más"
        
        pmg_info = '✅ CON' if tiene_pmg else '❌ SIN'
        info_extra = ""
        
        if tiene_pmg:
            coste_pmg_anual = calcular_pmg(True, es_canarias)
            info_extra = f" | 📦 PMG: {coste_pmg_anual/12:.2f}€/mes"
        else:
            info_extra = " | 📦 Sin PMG"
        
        precio_variable = plan["termino_variable_con_pmg"] if tiene_pmg else plan["termino_variable_sin_pmg"]
        precio_fijo = plan["termino_fijo_con_pmg"] if tiene_pmg else plan["termino_fijo_sin_pmg"]
        
        precio_display = f"Var: {precio_variable:.3f}€ | Fijo: {precio_fijo:.2f}€"
        
        return {
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
        }
    except Exception as e:
        print(f"Error calculando resultado gas para {rl}: {e}")
        return None

def _mostrar_resultados_gas(resultados, tipo_calculo, consumo_anual, costo_actual_anual, costo_actual_mensual, es_canarias):
    """Muestra los resultados de gas"""
    st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
    
    info_tipo = "ESTIMACIÓN ANUAL" if tipo_calculo == "📊 Estimación anual" else "CÁLCULO EXACTO"
    info_consumo = f"{consumo_anual:,.0f} kWh/año"
    info_costo_actual = f"€{costo_actual_anual:,.2f}/año (€{costo_actual_mensual:,.2f}/mes)"
    info_iva = "Sin IVA" if es_canarias else "Con IVA 21%"
    
    st.info(f"**Tipo:** {info_tipo} | **Consumo:** {info_consumo} | **Actual:** {info_costo_actual} | **IVA:** {info_iva}")
    
    # Encontrar mejor plan
    mejor_plan = max(resultados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💶 Actual Mensual", f"€{costo_actual_mensual:,.2f}")
    with col2:
        coste_mejor_mensual = float(mejor_plan['Coste Mensual'].replace('€', '').replace(',', ''))
        st.metric("💰 Mejor Mensual", f"€{coste_mejor_mensual:,.2f}")
    with col3:
        ahorro_mensual = float(mejor_plan['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
        delta_mensual = f"€{ahorro_mensual:,.2f}" if ahorro_mensual > 0 else None
        st.metric("📈 Ahorro Mensual", f"€{ahorro_mensual:,.2f}", delta=delta_mensual)
    with col4:
        ahorro_anual = float(mejor_plan['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
        delta_anual = f"€{ahorro_anual:,.2f}" if ahorro_anual > 0 else None
        st.metric("🎯 Ahorro Anual", f"€{ahorro_anual:,.2f}", delta=delta_anual)
    
    st.dataframe(resultados, use_container_width=True)
    
    # Mostrar recomendación
    planes_recomendados = [p for p in resultados if p['Recomendado'] == '✅']
    if planes_recomendados:
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

# ==============================================
# FUNCIONES DE CUPS NATURGY
# ==============================================

def cups_naturgy():
    """Mostrar CUPS de ejemplo para Naturgy"""
    st.subheader("📋 CUPS Naturgy")
    
    st.info("Ejemplos de CUPS para trámites con Naturgy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🔥 CUPS Ejemplo Gas")
        cups_gas = "ES0217010103496537HH"
        st.code(cups_gas, language="text")
        
        if st.button("📋 Copiar CUPS Gas", key="copy_gas", use_container_width=True):
            st.success("✅ CUPS Gas copiado al portapapeles")
    
    with col2:
        st.write("### ⚡ CUPS Ejemplo Electricidad")
        cups_luz = "ES0031405120579007YM"
        st.code(cups_luz, language="text")
        
        if st.button("📋 Copiar CUPS Electricidad", key="copy_luz", use_container_width=True):
            st.success("✅ CUPS Electricidad copiado al portapapeles")
    
    st.markdown("---")
    st.write("### 🌐 Acceso Directo a Tarifa Plana Zen")
    
    url = "https://www.naturgy.es/hogar/luz_y_gas/tarifa_plana_zen"
    
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
    
    st.caption("💡 Se abrirá en una nueva pestaña")

# ==============================================
# FUNCIONES DE GESTIÓN PVD USUARIO
# ==============================================

def gestion_pvd_usuario():
    """Sistema de Pausas Visuales para usuarios con grupos - CONFIRMACIÓN OBLIGATORIA"""
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    config_pvd = cargar_config_pvd()
    usuarios_config = cargar_configuracion_usuarios()
    
    # Obtener grupo del usuario
    usuario_id = st.session_state.username
    grupo_usuario = usuarios_config.get(usuario_id, {}).get('grupo', 'basico')
    
    # Cargar cola del grupo específico
    cola_grupo = cargar_cola_pvd_grupo(grupo_usuario)
    
    # Obtener configuración del grupo
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {
        'maximo_simultaneo': 2,
        'duracion_corta': 5,
        'duracion_larga': 10,
        'agentes_por_grupo': 10
    })
    
    # Botones de control
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("🔄 Actualizar Ahora", use_container_width=True, type="primary", key="refresh_pvd_now"):
            temporizador_pvd_mejorado._verificar_y_actualizar()
            st.rerun()
    with col_btn2:
        if st.button("📊 Ver Estado Cola", use_container_width=True, key="ver_estado_cola"):
            en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            en_espera_grupo = len([p for p in cola_grupo if p['estado'] == 'ESPERANDO'])
            st.info(f"**Grupo {grupo_usuario}:** {en_pausa_grupo}/{config_grupo.get('maximo_simultaneo', 2)} en pausa, {en_espera_grupo} en espera")
    with col_btn3:
        if st.button("👥 Ver mi Grupo", use_container_width=True, key="ver_grupo"):
            st.info(f"**Grupo:** {grupo_usuario}")
            st.write(f"**Agentes en grupo:** {config_grupo.get('agentes_por_grupo', 10)}")
            st.write(f"**Máximo simultáneo:** {config_grupo.get('maximo_simultaneo', 2)}")
            st.write(f"**Duración corta:** {config_grupo.get('duracion_corta', 5)} min")
            st.write(f"**Duración larga:** {config_grupo.get('duracion_larga', 10)} min")
    
    hora_actual_madrid = obtener_hora_madrid().strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora actual (Madrid):** {hora_actual_madrid}")
    
    # Estadísticas del grupo
    en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
    en_espera_grupo = len([p for p in cola_grupo if p['estado'] == 'ESPERANDO'])
    max_simultaneo_grupo = config_grupo.get('maximo_simultaneo', 2)
    espacios_disponibles_grupo = max_simultaneo_grupo - en_pausa_grupo
    
    # Calcular pausas hoy del usuario
    hoy = obtener_hora_madrid().date()
    pausas_hoy = len([p for p in cola_grupo 
                     if p['usuario_id'] == usuario_id and 
                     'timestamp_solicitud' in p and
                     datetime.fromisoformat(p['timestamp_solicitud']).date() == hoy and
                     p['estado'] != 'CANCELADO'])
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("👥 Tu Grupo", grupo_usuario)
    with col_stats2:
        st.metric("⏸️ En pausa", f"{en_pausa_grupo}/{max_simultaneo_grupo}")
    with col_stats3:
        st.metric("⏳ En espera", en_espera_grupo)
    with col_stats4:
        st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
    
    # Verificar si tiene pausa activa
    usuario_pausa_activa = None
    for pausa in cola_grupo:
        if pausa['usuario_id'] == usuario_id and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    if usuario_pausa_activa:
        _mostrar_pausa_activa_usuario(usuario_pausa_activa, cola_grupo, grupo_usuario, config_grupo, espacios_disponibles_grupo)
    else:
        _mostrar_formulario_solicitud_pausa(config_pvd, cola_grupo, grupo_usuario, pausas_hoy, espacios_disponibles_grupo, en_espera_grupo)
    
    # Información sobre el sistema
    _mostrar_info_sistema_pvd()

def _mostrar_pausa_activa_usuario(pausa, cola_grupo, grupo_usuario, config_grupo, espacios_disponibles):
    """Muestra información de pausa activa del usuario"""
    estado_display = ESTADOS_PVD_USUARIO.get(pausa['estado'], pausa['estado'])
    
    usuario_id = st.session_state.username

    if pausa['estado'] == 'ESPERANDO':
        st.warning(f"⏳ **Tienes una pausa solicitada** - Grupo: {grupo_usuario}")
        
        # Calcular posición en el grupo
        en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = 1
        for i, pausa_item in enumerate(en_espera_grupo):
            if pausa_item['id'] == pausa['id']:
                posicion = i + 1
                break
        
        with st.expander("📊 Información de tu pausa en espera", expanded=True):
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
            with col_info1:
                st.metric("Posición en grupo", f"#{posicion}")
            with col_info2:
                st.metric("Personas en grupo", len(en_espera_grupo))
            with col_info3:
                st.metric("Espacios libres", espacios_disponibles)
            with col_info4:
                # Calcular tiempo estimado
                tiempo_estimado = _calcular_tiempo_estimado_grupo(cola_grupo, grupo_usuario, usuario_id, config_grupo)
                if tiempo_estimado is None:
                    st.metric("Tiempo estimado", "N/A")
                elif tiempo_estimado == 0:
                    st.metric("Tiempo estimado", "¡Ahora!")
                elif tiempo_estimado <= 1:
                    st.metric("Tiempo estimado", "< 1 min")
                else:
                    st.metric("Tiempo estimado", f"~{tiempo_estimado} min")
            
            # Verificar si es su turno
            if posicion == 1 and espacios_disponibles > 0:
                st.success("🎯 **¡ES TU TURNO PARA LA PAUSA!**")
                _mostrar_confirmacion_turno(pausa, cola_grupo, grupo_usuario)
            else:
                # Botón para cancelar si no es su turno
                if st.button("❌ Cancelar mi pausa", type="secondary", use_container_width=True, key="cancelar_pausa_espera"):
                    pausa['estado'] = 'CANCELADO'
                    guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
                    temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                    st.success("✅ Pausa cancelada")
                    st.rerun()
    
    elif pausa['estado'] == 'EN_CURSO':
        st.success(f"✅ **Pausa en curso** - {estado_display}")
        
        duracion_elegida = pausa.get('duracion_elegida', 'corta')
        duracion_minutos = config_grupo['duracion_corta'] if duracion_elegida == 'corta' else config_grupo['duracion_larga']
        
        tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
        hora_actual = obtener_hora_madrid()
        tiempo_transcurrido = int((hora_actual - tiempo_inicio).total_seconds() / 60)
        tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
        
        progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
        st.progress(int(progreso))
        
        col_tiempo1, col_tiempo2 = st.columns(2)
        with col_tiempo1:
            st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
        with col_tiempo2:
            st.metric("⏳ Restante", f"{tiempo_restante} min")
        
        hora_fin_estimada = tiempo_inicio + timedelta(minutes=duracion_minutos)
        
        st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
        st.write(f"**Inició:** {tiempo_inicio.strftime('%H:%M:%S')}")
        st.write(f"**Finaliza:** {hora_fin_estimada.strftime('%H:%M:%S')}")
        
        # Botón para finalizar manualmente
        if st.button("✅ Finalizar pausa ahora", type="primary", key="finish_pause_now", use_container_width=True):
            pausa['estado'] = 'COMPLETADO'
            pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
            guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
            temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_usuario)
            st.success("✅ Pausa completada manualmente")
            st.rerun()

def _mostrar_confirmacion_turno(pausa, cola_grupo, grupo_usuario):
    """Muestra confirmación de turno para el usuario"""
    st.markdown("---")
    st.warning("### ⚠️ **DEBES CONFIRMAR TU PAUSA**")
    st.write("**Tienes 7 minutos para confirmar que estás listo para comenzar.**")
    
    # Configuración del grupo
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {
        'duracion_corta': 5,
        'duracion_larga': 10
    })
    
    duracion_elegida = pausa.get('duracion_elegida', 'corta')
    duracion_minutos = config_grupo['duracion_corta'] if duracion_elegida == 'corta' else config_grupo['duracion_larga']
    
    st.info(f"**Duración de pausa:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
    
    # Contador de tiempo para confirmar
    timer_key = f'confirmacion_inicio_{st.session_state.username}_{grupo_usuario}'
    
    if timer_key not in st.session_state:
        st.session_state[timer_key] = obtener_hora_madrid()
    
    tiempo_transcurrido = (obtener_hora_madrid() - st.session_state[timer_key]).total_seconds()
    segundos_restantes = max(0, 420 - tiempo_transcurrido)  # 7 minutos = 420 segundos
    
    # Barra de progreso
    porcentaje = min(100, (tiempo_transcurrido / 420) * 100)
    st.progress(int(porcentaje))
    
    # Mostrar tiempo restante
    if segundos_restantes > 300:
        minutos = int(segundos_restantes / 60)
        st.caption(f"⏳ **Tiempo para confirmar:** {minutos} minutos")
    elif segundos_restantes > 60:
        minutos = int(segundos_restantes / 60)
        segundos = int(segundos_restantes % 60)
        st.caption(f"⏳ **Tiempo para confirmar:** {minutos}:{segundos:02d} minutos")
    elif segundos_restantes > 10:
        st.caption(f"⏳ **Tiempo para confirmar:** {int(segundos_restantes)} segundos")
    else:
        st.error("⏰ **¡ÚLTIMOS SEGUNDOS!**")
    
    # Verificar si se agotó el tiempo
    if tiempo_transcurrido > 420:  # 7 minutos
        st.error("⏰ **¡TIEMPO AGOTADO!** No confirmaste en 7 minutos")
        
        # Cancelar pausa automáticamente
        pausa['estado'] = 'CANCELADO'
        pausa['motivo_cancelacion'] = 'tiempo_confirmacion_expirado'
        pausa['timestamp_cancelacion'] = obtener_hora_madrid().isoformat()
        
        # Limpiar temporizador
        temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
        
        # Limpiar estado de confirmación
        if timer_key in st.session_state:
            del st.session_state[timer_key]
        
        # Guardar cambios
        guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
        
        # Iniciar siguiente automáticamente
        temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_usuario)
        
        st.warning("🔄 **Turno cancelado automáticamente** (por inactividad de 7 minutos)")
        st.rerun()
    
    # Botones de confirmación
    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        if st.button("✅ **SÍ, COMENZAR PAUSA AHORA**", 
                   type="primary", 
                   use_container_width=True,
                   key=f"confirmar_pausa_si_{pausa['id']}"):
            
            # Iniciar pausa SOLO SI EL USUARIO CONFIRMA
            pausa['estado'] = 'EN_CURSO'
            pausa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
            pausa['confirmado'] = True
            
            # Limpiar estado de confirmación
            if timer_key in st.session_state:
                del st.session_state[timer_key]
            
            # Guardar cambios
            guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
            
            st.success("✅ **Pausa confirmada e iniciada.** ¡Disfruta de tu descanso!")
            st.rerun()
    
    with col_conf2:
        if st.button("❌ **NO, CANCELAR MI TURNO**",
                   type="secondary",
                   use_container_width=True,
                   key=f"cancelar_turno_no_{pausa['id']}"):
            
            pausa['estado'] = 'CANCELADO'
            pausa['motivo_cancelacion'] = 'usuario_rechazo'
            
            # Limpiar temporizador
            temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
            
            # Limpiar estado de confirmación
            if timer_key in st.session_state:
                del st.session_state[timer_key]
            
            # Guardar cambios
            guardar_cola_pvd_grupo(grupo_usuario, cola_grupo)
            
            st.warning("❌ **Turno cancelado.** Has sido eliminado de la cola.")
            st.rerun()

def _mostrar_formulario_solicitud_pausa(config_pvd, cola_grupo, grupo_usuario, pausas_hoy, espacios_disponibles, en_espera_grupo):
    """Muestra formulario para solicitar pausa si no tiene una activa"""
    usuario_id = st.session_state.username
    
    st.info("👁️ **Sistema de Pausas Visuales Dinámicas por Grupos**")
    st.write(f"**Grupo asignado:** {grupo_usuario}")
    
    if pausas_hoy >= 5:
        st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
        st.info("Puedes tomar más pausas mañana")
        return
    
    # Mostrar estado del grupo
    if espacios_disponibles > 0:
        st.success(f"✅ **HAY ESPACIO DISPONIBLE EN TU GRUPO** - {espacios_disponibles} puesto(s) libre(s)")
    else:
        st.warning(f"⏳ **GRUPO LLENO** - Hay {en_espera_grupo} persona(s) en espera en tu grupo")
    
    st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
    
    # Obtener configuraciones del grupo
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {
        'duracion_corta': 5,
        'duracion_larga': 10
    })
    
    duracion_corta = config_grupo.get('duracion_corta', 5)
    duracion_larga = config_grupo.get('duracion_larga', 10)
    
    col_dura1, col_dura2 = st.columns(2)
    with col_dura1:
        if st.button(
            f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
            use_container_width=True,
            type="primary",
            key="pausa_corta_grupo"
        ):
            # CORREGIDO: Usar el método de la instancia temporizador_pvd_mejorado
            if temporizador_pvd_mejorado.solicitar_pausa("corta", grupo_usuario):
                st.success("✅ Pausa solicitada. Estás en la cola de tu grupo.")
                st.rerun()
    
    with col_dura2:
        if st.button(
            f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
            use_container_width=True,
            type="secondary",
            key="pausa_larga_grupo"
        ):
            # CORREGIDO: Usar el método de la instancia temporizador_pvd_mejorado
            if temporizador_pvd_mejorado.solicitar_pausa("larga", grupo_usuario):
                st.success("✅ Pausa solicitada. Estás en la cola de tu grupo.")
                st.rerun()

def _calcular_tiempo_estimado_grupo(cola_grupo, grupo_id, usuario_id, config_grupo):
    """Calcula tiempo estimado REAL basado en horas de finalización de pausas en curso"""
    try:
        # 1. Encontrar la pausa del usuario en ESPERANDO
        pausa_usuario = None
        for pausa in cola_grupo:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                pausa_usuario = pausa
                break
        
        if not pausa_usuario:
            return None  # Usuario no tiene pausa en espera
        
        # 2. Encontrar posición en la cola de ESPERANDO
        en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = None
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['id'] == pausa_usuario['id']:
                posicion = i + 1
                break
        
        if posicion is None:
            return None
        
        # 3. Calcular espacios disponibles en el grupo
        en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
        max_simultaneo = config_grupo.get('maximo_simultaneo', 2)
        espacios_disponibles = max_simultaneo - en_pausa_grupo
        
        # 4. Si hay espacios disponibles y eres el primero, puedes entrar ahora
        if posicion == 1 and espacios_disponibles > 0:
            return 0  # ¡Puede entrar inmediatamente!
        
        # 5. Si no hay espacios disponibles, calcular cuándo se liberará el próximo espacio
        if espacios_disponibles == 0:
            # Buscar la pausa EN_CURSO que terminará primero
            ahora = obtener_hora_madrid()
            proximo_termino = None
            
            for pausa in cola_grupo:
                if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    
                    # Obtener duración según configuración del grupo
                    if duracion_elegida == 'corta':
                        duracion_minutos = config_grupo.get('duracion_corta', 5)
                    else:
                        duracion_minutos = config_grupo.get('duracion_larga', 10)
                    
                    # Calcular cuándo termina
                    tiempo_fin = tiempo_inicio + timedelta(minutes=duracion_minutos)
                    
                    # Si aún no ha terminado
                    if tiempo_fin > ahora:
                        minutos_restantes = (tiempo_fin - ahora).total_seconds() / 60
                        
                        # Guardar el tiempo más corto
                        if proximo_termino is None or minutos_restantes < proximo_termino:
                            proximo_termino = minutos_restantes
            
            if proximo_termino is not None:
                # Si eres el primero en espera, entrarás cuando se libere el primer espacio
                if posicion == 1:
                    return int(proximo_termino)
                else:
                    # Si hay más personas delante, cada una ocupará un espacio por duración completa
                    # Calcular cuántas "vueltas" necesitas esperar
                    personas_delante = posicion - 1
                    
                    # Cada persona delante toma una pausa completa
                    # Necesitamos estimar la duración promedio
                    duracion_corta = config_grupo.get('duracion_corta', 5)
                    duracion_larga = config_grupo.get('duracion_larga', 10)
                    duracion_promedio = (duracion_corta + duracion_larga) / 2
                    
                    # El tiempo total es: 
                    # - Tiempo hasta que se libere el primer espacio (proximo_termino)
                    # - Más el tiempo de las personas delante (cada una toma ~duracion_promedio minutos)
                    # Pero debemos considerar que solo max_simultaneo personas pueden estar en pausa a la vez
                    
                    # Personas que entrarán en la primera "ronda" después de que se libere espacio
                    personas_en_primera_ronda = min(personas_delante, max_simultaneo)
                    
                    # Tiempo estimado = tiempo para liberar espacio + (posicion-1) * duracion_promedio / max_simultaneo
                    tiempo_estimado = proximo_termino + (personas_delante * duracion_promedio / max_simultaneo)
                    
                    return max(1, int(tiempo_estimado))
        
        # 6. Si hay espacios disponibles pero no eres el primero
        if espacios_disponibles > 0 and posicion > 1:
            # Las personas delante entrarán primero
            # Calcular duración promedio
            duracion_corta = config_grupo.get('duracion_corta', 5)
            duracion_larga = config_grupo.get('duracion_larga', 10)
            duracion_promedio = (duracion_corta + duracion_larga) / 2
            
            # Personas delante que entrarán antes que tú
            personas_que_entran_antes = min(posicion - 1, espacios_disponibles)
            
            # Cada persona tomará aproximadamente duracion_promedio minutos
            tiempo_estimado = personas_que_entran_antes * duracion_promedio
            
            return max(1, int(tiempo_estimado))
        
        # 7. Si no se pudo calcular, devolver estimación por defecto
        return 5  # Valor por defecto seguro
        
    except Exception as e:
        print(f"Error calculando tiempo estimado REAL para grupo {grupo_id}: {e}")
        # Fallback: estimación simple
        return _calcular_estimacion_simple(cola_grupo, grupo_id, usuario_id, config_grupo)

def _calcular_estimacion_simple(cola_grupo, grupo_id, usuario_id, config_grupo):
    """Estimación simple de fallback"""
    try:
        # Encontrar posición del usuario
        en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
        
        posicion = None
        for i, pausa in enumerate(en_espera_grupo):
            if pausa['usuario_id'] == usuario_id:
                posicion = i + 1
                break
        
        if posicion is None:
            return None
        
        # Contar pausas en curso
        en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
        max_simultaneo = config_grupo.get('maximo_simultaneo', 2)
        
        if posicion == 1 and en_pausa_grupo < max_simultaneo:
            return 0
        
        # Ver pausas en curso y sus tiempos restantes
        ahora = obtener_hora_madrid()
        tiempos_restantes = []
        
        for pausa in cola_grupo:
            if pausa['estado'] == 'EN_CURSO' and 'timestamp_inicio' in pausa:
                tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                duracion_elegida = pausa.get('duracion_elegida', 'corta')
                duracion_minutos = config_grupo['duracion_corta'] if duracion_elegida == 'corta' else config_grupo['duracion_larga']
                
                tiempo_fin = tiempo_inicio + timedelta(minutes=duracion_minutos)
                
                if tiempo_fin > ahora:
                    minutos_restantes = max(0, (tiempo_fin - ahora).total_seconds() / 60)
                    tiempos_restantes.append(minutos_restantes)
        
        # Ordenar tiempos restantes
        tiempos_restantes.sort()
        
        # Calcular estimación basada en posición
        personas_delante = posicion - 1
        
        if personas_delante < len(tiempos_restantes):
            # El usuario entrará cuando se libere uno de los espacios actuales
            return int(tiempos_restantes[personas_delante])
        else:
            # Necesita esperar más tiempo
            duracion_promedio = (config_grupo.get('duracion_corta', 5) + config_grupo.get('duracion_larga', 10)) / 2
            espacios_faltantes = personas_delante - len(tiempos_restantes)
            tiempo_adicional = (espacios_faltantes / max_simultaneo) * duracion_promedio
            
            tiempo_base = tiempos_restantes[-1] if tiempos_restantes else 0
            return int(tiempo_base + tiempo_adicional)
            
    except Exception as e:
        print(f"Error en estimación simple para {usuario_id}: {e}")
        return 5  # Valor por defecto seguro

def _mostrar_info_sistema_pvd():
    """Muestra información sobre el sistema PVD"""
    st.markdown("---")
    st.info("""
    **⚙️ Sistema Automático Mejorado:**

    - **✅ Confirmación obligatoria**: Debes confirmar cuando sea tu turno
    - **⏰ 7 minutos para confirmar**: Tienes 7 minutos para confirmar tu pausa
    - **✅ Cancelación automática**: Si no confirmas en 7 minutos, se cancela automáticamente
    - **✅ Finalización automática**: Las pausas se finalizan solas al terminar el tiempo
    - **🔄 Temporizador interno**: El sistema verifica cada 60 segundos
    - **👥 Gestión por grupos**: Cada grupo tiene sus propios espacios y configuración

    **📢 ¿Cómo funciona?**
    1. Solicita una pausa (Corta o Larga según tu grupo)
    2. Espera tu turno en la cola de tu grupo
    3. **Cuando sea tu turno, verás una ALERTA preguntando si confirmas**
    4. **DEBES CONFIRMAR** para comenzar tu pausa - NO comienza automáticamente
    5. **Tienes 7 minutos para confirmar**
    6. Si no confirmas en 7 minutos, se cancela automáticamente
    7. La pausa termina automáticamente

    **🔄 Recuerda:**
    - La página NO se refresca automáticamente
    - Haz clic en **🔄 Actualizar Ahora** para ver cambios
    - Si te ausentas, tu pausa se cancelará automáticamente después de 7 minutos
    - Cada grupo tiene duraciones diferentes (consulta tu configuración)
    """)

# ==============================================
# FUNCIÓN DE TEMPORIZADOR PVD
# ==============================================

def mostrar_temporizador_pvd_usuario():
    """Muestra temporizador PVD para usuarios con turno disponible"""
    try:
        usuario_id = st.session_state.username
        
        # Obtener grupo del usuario
        usuarios_config = cargar_configuracion_usuarios()
        grupo_usuario = usuarios_config.get(usuario_id, {}).get('grupo', 'basico')
        
        # Cargar cola del grupo
        cola_grupo = cargar_cola_pvd_grupo(grupo_usuario)
        
        # Verificar si el usuario tiene una pausa en espera que está lista para comenzar
        pausa_usuario = None
        for pausa in cola_grupo:
            if pausa['usuario_id'] == usuario_id and pausa['estado'] == 'ESPERANDO':
                pausa_usuario = pausa
                break
        
        if pausa_usuario:
            # Verificar si es el primero en la cola
            en_espera_grupo = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
            en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            if en_espera_grupo and en_espera_grupo[0]['id'] == pausa_usuario['id']:
                # Verificar si hay espacio en el grupo
                config_sistema = cargar_config_sistema()
                grupos_config = config_sistema.get('grupos_pvd', {})
                config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2})
                max_grupo = config_grupo.get('maximo_simultaneo', 2)
                
                en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
                
                if en_pausa_grupo < max_grupo:
                    # Calcular tiempo estimado si hay temporizador
                    tiempo_estimado = temporizador_pvd_mejorado.obtener_tiempo_restante(usuario_id)
                    if tiempo_estimado:
                        # Mostrar temporizador visual
                        st.markdown(crear_temporizador_html_simplificado(int(tiempo_estimado), usuario_id), unsafe_allow_html=True)
                        return True
        
        return False
        
    except Exception as e:
        print(f"Error mostrando temporizador PVD para usuario: {e}")
        return False

# ==============================================
# FUNCIÓN PRINCIPAL DE USUARIO
# ==============================================

def main_usuario():
    """Función principal para usuarios"""
    if not st.session_state.get('authenticated', False):
        st.warning("⚠️ No estás autenticado")
        return
    
    # Mostrar temporizador si está disponible
    if mostrar_temporizador_pvd_usuario():
        st.markdown("---")
    
    # Menú de opciones para usuarios
    opciones_usuario = [
        "📊 Modelos de Factura",
        "⚡ Comparativa EXACTA", 
        "📅 Comparativa ESTIMADA",
        "🔥 Calculadora de Gas",
        "📋 CUPS Naturgy",
        "👁️ Sistema de Pausas Visuales (PVD)"
    ]
    
    seleccion = st.selectbox(
        "Selecciona una opción:",
        opciones_usuario,
        key="menu_usuario"
    )
    
    # Ejecutar la función seleccionada
    if seleccion == "📊 Modelos de Factura":
        consultar_modelos_factura()
    elif seleccion == "⚡ Comparativa EXACTA":
        comparativa_exacta()
    elif seleccion == "📅 Comparativa ESTIMADA":
        comparativa_estimada()
    elif seleccion == "🔥 Calculadora de Gas":
        calculadora_gas()
    elif seleccion == "📋 CUPS Naturgy":
        cups_naturgy()
    elif seleccion == "👁️ Sistema de Pausas Visuales (PVD)":
        gestion_pvd_usuario()

# ==============================================
# EJECUCIÓN SI SE EJECUTA DIRECTAMENTE
# ==============================================

if __name__ == "__main__":
    # Configurar página
    st.set_page_config(
        page_title="Zelenza - Panel Usuario",
        page_icon="👤",
        layout="wide"
    )
    
    # Verificar autenticación
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        main_usuario()
    else:
        st.error("🔒 Acceso no autorizado. Por favor, inicia sesión.")