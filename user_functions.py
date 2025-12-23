import streamlit as st
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz

from config import COMUNIDADES_AUTONOMAS
from calculation import (
    calcular_plan_ahorro_automatico, determinar_rl_gas,
    calcular_coste_gas_completo, calcular_pmg, filtrar_planes_por_usuario
)
from database import (
    cargar_configuracion_usuarios, cargar_config_pvd, cargar_cola_pvd,
    guardar_cola_pvd, cargar_config_sistema
)
from pvd_system import (
    temporizador_pvd_mejorado, temporizador_pvd, verificar_confirmacion_pvd, 
    actualizar_temporizadores_pvd, solicitar_pausa, ESTADOS_PVD,
    calcular_tiempo_estimado_grupo, crear_temporizador_html_simplificado
)
from utils import obtener_hora_madrid, formatear_hora_madrid

# ==============================================
# FUNCIONES DE USUARIO
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
                # CORRECCIÓN: Quitar use_container_width o usar width en su lugar
                st.image(ruta_completa, width=600)  # <-- CORREGIDO
            st.markdown("---")
    else:
        st.warning(f"⚠️ No hay modelos de factura subidos para {empresa_seleccionada}")

# También necesitamos importar las funciones de cálculo extendido
from calculation_extended import calcular_comparacion_exacta, calcular_estimacion_anual

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
        calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh)

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
                for tiene_pmg in [True, False]:
                    coste_anual = calcular_coste_gas_completo(plan, consumo_anual, tiene_pmg, es_canarias)
                    coste_mensual = coste_anual / 12
                    
                    coste_original = consumo_anual * plan["precio_original_kwh"]
                    ahorro_vs_original = coste_original - coste_anual
                    
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
        
        if resultados:
            st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
            
            info_tipo = "ESTIMACIÓN ANUAL" if tipo_calculo == "📊 Estimación anual" else "CÁLCULO EXACTO"
            info_consumo = f"{consumo_anual:,.0f} kWh/año"
            info_costo_actual = f"€{costo_actual_anual:,.2f}/año (€{costo_actual_mensual:,.2f}/mes)"
            info_iva = "Sin IVA" if es_canarias else "Con IVA 21%"
            
            st.info(f"**Tipo:** {info_tipo} | **Consumo:** {info_consumo} | **Actual:** {info_costo_actual} | **IVA:** {info_iva}")
            
            mejor_plan = max(resultados, key=lambda x: float(x['Ahorro vs Actual Año'].replace('€', '').replace(',', '')))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💶 Actual Mensual", f"€{costo_actual_mensual:,.2f}")
            with col2:
                coste_mejor_mensual = float(mejor_plan['Coste Mensual'].replace('€', '').replace(',', ''))
                st.metric("💰 Mejor Mensual", f"€{coste_mejor_mensual:,.2f}")
            with col3:
                ahorro_mensual = float(mejor_plan['Ahorro vs Actual Mes'].replace('€', '').replace(',', ''))
                st.metric("📈 Ahorro Mensual", f"€{ahorro_mensual:,.2f}", delta=f"€{ahorro_mensual:,.2f}" if ahorro_mensual > 0 else None)
            with col4:
                ahorro_anual = float(mejor_plan['Ahorro vs Actual Año'].replace('€', '').replace(',', ''))
                st.metric("🎯 Ahorro Anual", f"€{ahorro_anual:,.2f}")
            
            st.dataframe(resultados, use_container_width=True)
            
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
        
        else:
            st.warning("No hay planes de gas activos para mostrar")

def crear_temporizador_html_simplificado(minutos_restantes, usuario_id):
    """Crea un temporizador visual en HTML/JavaScript SIN notificaciones del navegador"""
    
    segundos_totales = minutos_restantes * 60
    
    html_code = f"""
    <div id="temporizador-pvd" style="
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        border: 2px solid #00b4d8;
        position: relative;
        overflow: hidden;
    ">
        <div style="position: absolute; top: 10px; right: 10px; font-size: 12px; opacity: 0.8;">
            🕒 <span id="hora-actual">00:00:00</span>
        </div>
        
        <h3 style="margin: 0 0 15px 0; color: #00b4d8; font-size: 22px;">
            ⏱️ TEMPORIZADOR PVD
        </h3>
        
        <div id="contador" style="
            font-size: 48px;
            font-weight: bold;
            margin: 15px 0;
            color: #4cc9f0;
            text-shadow: 0 0 10px rgba(76, 201, 240, 0.5);
        ">
            {minutos_restantes:02d}:00
        </div>
        
        <div style="
            background: #1f4068;
            height: 20px;
            border-radius: 10px;
            margin: 20px 0;
            overflow: hidden;
        ">
            <div id="barra-progreso" style="
                background: linear-gradient(90deg, #4cc9f0, #4361ee);
                height: 100%;
                width: 0%;
                border-radius: 10px;
                transition: width 1s ease, background 0.5s ease;
            "></div>
        </div>
        
        <div style="
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.9;
        ">
            <div>🆔 {usuario_id[:8]}...</div>
            <div id="tiempo-restante-texto">Restante: {minutos_restantes} min</div>
            <div id="estado-temporizador">⏳ En espera</div>
        </div>
    </div>
    
    <script>
    let segundosRestantes = {segundos_totales};
    const segundosTotales = {segundos_totales};
    let temporizadorActivo = true;
    
    function actualizarHora() {{
        const ahora = new Date();
        const hora = ahora.getHours().toString().padStart(2, '0');
        const minutos = ahora.getMinutes().toString().padStart(2, '0');
        const segundos = ahora.getSeconds().toString().padStart(2, '0');
        document.getElementById('hora-actual').textContent = hora + ':' + minutos + ':' + segundos;
    }}
    
    function actualizarTemporizador() {{
        if (!temporizadorActivo) return;
        
        segundosRestantes--;
        
        if (segundosRestantes <= 0) {{
            document.getElementById('contador').textContent = '🎯 ¡TU TURNO!';
            document.getElementById('contador').style.color = '#ff9900';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
            
            // Mostrar mensaje para recargar la página
            document.getElementById('estado-temporizador').textContent = '🎯 ¡TURNO!';
            document.getElementById('estado-temporizador').style.color = '#ff9900';
            document.getElementById('estado-temporizador').style.fontWeight = 'bold';
            
            return;
        }}
        
        const minutos = Math.floor(segundosRestantes / 60);
        const segundos = segundosRestantes % 60;
        document.getElementById('contador').textContent = 
            minutos.toString().padStart(2, '0') + ':' + 
            segundos.toString().padStart(2, '0');
        
        const progreso = 100 * (1 - (segundosRestantes / segundosTotales));
        document.getElementById('barra-progreso').style.width = progreso + '%';
        
        if (segundosRestantes <= 300 && segundosRestantes > 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
        }} else if (segundosRestantes <= 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff3300, #cc0000)';
        }}
        
        actualizarHora();
        
        setTimeout(actualizarTemporizador, 1000);
    }}
    
    actualizarHora();
    actualizarTemporizador();
    </script>
    """
    
    return html_code

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
            st.session_state.copied_gas = cups_gas
            st.success("✅ CUPS Gas copiado al portapapeles")
    
    with col2:
        st.write("### ⚡ CUPS Ejemplo Electricidad")
        cups_luz = "ES0031405120579007YM"
        st.code(cups_luz, language="text")
        
        if st.button("📋 Copiar CUPS Electricidad", key="copy_luz", use_container_width=True):
            st.session_state.copied_luz = cups_luz
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
        calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh)

def gestion_pvd_usuario():
    """Sistema de Pausas Visuales para usuarios con grupos - CONFIRMACIÓN OBLIGATORIA"""
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")

    # Verificar si ya se está mostrando notificación en sidebar
    if 'mostrar_notificacion_sidebar' in st.session_state and st.session_state.mostrar_notificacion_sidebar:
        st.info("🎯 **¡Tienes una notificación en la barra lateral!**")
        st.write("Por favor, revisa la barra lateral de la izquierda para confirmar o cancelar tu turno.")
        st.markdown("---")
        # Mostrar botón para ir directamente
        if st.button("👈 Ir a la barra lateral", use_container_width=True):
            st.markdown('<script>document.querySelector(\'[data-testid="stSidebar"]\').scrollIntoView();</script>', unsafe_allow_html=True)
        return
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    usuarios_config = cargar_configuracion_usuarios()
    
    # Obtener grupo del usuario
    grupo_usuario = usuarios_config.get(st.session_state.username, {}).get('grupo', 'basico')
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', {})
    config_grupo = grupos_config.get(grupo_usuario, {'maximo_simultaneo': 2, 'agentes_por_grupo': 10})
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("🔄 Actualizar Ahora", use_container_width=True, type="primary", key="refresh_pvd_now"):
            st.rerun()
    with col_btn2:
        if st.button("📊 Ver Estado Cola", use_container_width=True, key="ver_estado_cola"):
            # Mostrar estado de la cola
            en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario])
            en_espera_grupo = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario])
            st.info(f"**Grupo {grupo_usuario}:** {en_pausa_grupo}/{config_grupo.get('maximo_simultaneo', 2)} en pausa, {en_espera_grupo} en espera")
    with col_btn3:
        if st.button("👥 Ver mi Grupo", use_container_width=True, key="ver_grupo"):
            st.info(f"**Grupo:** {grupo_usuario}")
            st.write(f"**Agentes en grupo:** {config_grupo.get('agentes_por_grupo', 10)}")
            st.write(f"**Máximo simultáneo:** {config_grupo.get('maximo_simultaneo', 2)}")
    
    hora_actual_madrid = obtener_hora_madrid().strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora actual (Madrid):** {hora_actual_madrid}")
    
    # EJECUTAR VERIFICACIÓN AUTOMÁTICA DEL TEMPORIZADOR
    actualizar_temporizadores_pvd()
    
    # Estadísticas del grupo
    estado_grupo = temporizador_pvd_mejorado.obtener_estado_grupo(grupo_usuario)
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("👥 Tu Grupo", grupo_usuario)
    with col_stats2:
        st.metric("⏸️ En pausa", f"{estado_grupo['en_pausa']}/{config_grupo.get('maximo_simultaneo', 2)}")
    with col_stats3:
        st.metric("⏳ En espera", estado_grupo['en_espera'])
    with col_stats4:
        pausas_hoy = len([p for p in cola_pvd 
                        if p['usuario_id'] == st.session_state.username and 
                        'timestamp_solicitud' in p and
                        datetime.fromisoformat(p['timestamp_solicitud']).date() == obtener_hora_madrid().date() and
                        p['estado'] != 'CANCELADO'])
        st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
    
    # Verificar si tiene pausa activa
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.warning(f"⏳ **Tienes una pausa solicitada** - Grupo: {grupo_usuario}")
            
            # Calcular posición en el grupo
            en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
            en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = next((i+1 for i, p in enumerate(en_espera_grupo) 
                           if p['id'] == usuario_pausa_activa['id']), 1)
            
            tiempo_restante = temporizador_pvd_mejorado.obtener_tiempo_restante(st.session_state.username)
            
            # IMPORTANTE: VERIFICAR SI ES SU TURNO - MOSTRAR PREGUNTA
            if posicion == 1 and estado_grupo['en_pausa'] < config_grupo.get('maximo_simultaneo', 2):
                # ¡ES SU TURNO! - MOSTRAR PREGUNTA DE CONFIRMACIÓN
                st.markdown("### 🎯 ¡ES TU TURNO! - NECESITAS CONFIRMAR")
                
                st.balloons()
                
                # Mostrar alerta grande
                st.warning("""
                ⚠️ **¡ATENCIÓN!**
                
                **¡Es tu turno para la pausa PVD!**
                
                **Debes confirmar que estás listo para comenzar.**
                
                Si no confirmas en 2 minutos, pasarás al final de la cola.
                """)
                
                # Obtener información de la pausa
                duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
                duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                
                st.info(f"**Duración de pausa:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
                
                # BOTONES DE CONFIRMACIÓN
                col_conf1, col_conf2 = st.columns(2)
                with col_conf1:
                    if st.button("✅ **SÍ, COMENZAR PAUSA AHORA**", 
                               type="primary", 
                               use_container_width=True,
                               key="confirmar_pausa_si"):
                        # Iniciar pausa SOLO SI EL USUARIO CONFIRMA
                        usuario_pausa_activa['estado'] = 'EN_CURSO'
                        usuario_pausa_activa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                        usuario_pausa_activa['confirmado'] = True
                        guardar_cola_pvd(cola_pvd)
                        st.success("✅ **Pausa confirmada e iniciada.** ¡Disfruta de tu descanso!")
                        st.rerun()
                
                with col_conf2:
                    if st.button("❌ **NO, CANCELAR MI TURNO**",
                               type="secondary",
                               use_container_width=True,
                               key="cancelar_turno_no"):
                        usuario_pausa_activa['estado'] = 'CANCELADO'
                        guardar_cola_pvd(cola_pvd)
                        temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                        st.warning("❌ **Turno cancelado.** Has sido eliminado de la cola.")
                        st.rerun()
                
                # Contador de tiempo para confirmar
                if 'confirmacion_inicio' not in st.session_state:
                    st.session_state.confirmacion_inicio = obtener_hora_madrid()
                
                tiempo_confirmacion = (obtener_hora_madrid() - st.session_state.confirmacion_inicio).total_seconds()
                minutos_restantes_confirmacion = max(0, 120 - tiempo_confirmacion) / 60  # 2 minutos para confirmar
                
                st.progress(min(100, (tiempo_confirmacion / 120) * 100))
                st.caption(f"⏳ **Tiempo para confirmar:** {int(minutos_restantes_confirmacion)} minutos y {int((minutos_restantes_confirmacion % 1) * 60)} segundos")
                
                if tiempo_confirmacion > 120:  # 2 minutos sin confirmar
                    st.error("⏰ **Tiempo de confirmación agotado.** Pasando al siguiente en cola...")
                    usuario_pausa_activa['estado'] = 'CANCELADO'
                    guardar_cola_pvd(cola_pvd)
                    temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                    st.rerun()
            
            else:
                # No es su turno aún - mostrar información normal
                with st.expander("📊 Información de tu pausa en espera", expanded=True):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("Posición en grupo", f"#{posicion}")
                    with col_info2:
                        st.metric("Personas en grupo", len(en_espera_grupo))
                    with col_info3:
                        espacios_libres = max(0, config_grupo.get('maximo_simultaneo', 2) - estado_grupo['en_pausa'])
                        st.metric("Espacios libres", espacios_libres)
                    
                    if tiempo_restante and tiempo_restante > 0:
                        st.info(f"⏱️ **Tiempo estimado:** ~{int(tiempo_restante)} minutos")
                    else:
                        st.info("⏱️ **Tiempo estimado:** Calculando...")
                
                # Botón para cancelar
                if st.button("❌ Cancelar mi pausa", type="secondary", use_container_width=True, key="cancelar_pausa_espera"):
                    usuario_pausa_activa['estado'] = 'CANCELADO'
                    guardar_cola_pvd(cola_pvd)
                    temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                    st.success("✅ Pausa cancelada")
                    st.rerun()
        
        elif usuario_pausa_activa['estado'] == 'EN_CURSO':
            st.success(f"✅ **Pausa en curso** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            tiempo_inicio = datetime.fromisoformat(usuario_pausa_activa['timestamp_inicio'])
            
            tiempo_inicio_madrid = tiempo_inicio
            if tiempo_inicio.tzinfo:
                tiempo_inicio_madrid = tiempo_inicio.astimezone(pytz.timezone('Europe/Madrid'))
            else:
                tiempo_inicio_madrid = pytz.timezone('Europe/Madrid').localize(tiempo_inicio)
            
            hora_actual_madrid = obtener_hora_madrid()
            tiempo_transcurrido = int((hora_actual_madrid - tiempo_inicio_madrid).total_seconds() / 60)
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            col_tiempo1, col_tiempo2 = st.columns(2)
            with col_tiempo1:
                st.metric("⏱️ Transcurrido", f"{tiempo_transcurrido} min")
            with col_tiempo2:
                st.metric("⏳ Restante", f"{tiempo_restante} min")
            
            hora_fin_estimada = tiempo_inicio_madrid + timedelta(minutes=duracion_minutos)
            
            st.write(f"**Duración total:** {duracion_minutos} minutos ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {tiempo_inicio_madrid.strftime('%H:%M:%S')} (hora Madrid)")
            st.write(f"**Finaliza:** {hora_fin_estimada.strftime('%H:%M:%S')} (hora Madrid)")
            
            # NOTA: La finalización ahora es automática gracias al temporizador de 60 segundos
            
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada automáticamente!** El sistema ha finalizado tu pausa.")
                
                # Si por alguna razón no se actualizó automáticamente, forzar la actualización
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                guardar_cola_pvd(cola_pvd)
                temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, grupo_usuario)
                st.rerun()
            
            if st.button("✅ Finalizar pausa ahora", type="primary", key="finish_pause_now", use_container_width=True):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                guardar_cola_pvd(cola_pvd)
                temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, grupo_usuario)
                st.success("✅ Pausa completada manualmente")
                st.rerun()
    
    else:
        # Usuario no tiene pausa activa - puede solicitar una
        st.info("👁️ **Sistema de Pausas Visuales Dinámicas por Grupos**")
        st.write(f"**Grupo asignado:** {grupo_usuario}")
        
        if pausas_hoy >= 5:
            st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
            st.info("Puedes tomar más pausas mañana")
        else:
            espacios_libres_grupo = max(0, config_grupo.get('maximo_simultaneo', 2) - estado_grupo['en_pausa'])
            
            if espacios_libres_grupo > 0:
                st.success(f"✅ **HAY ESPACIO DISPONIBLE EN TU GRUPO** - {espacios_libres_grupo} puesto(s) libre(s)")
            else:
                st.warning(f"⏳ **GRUPO LLENO** - Hay {estado_grupo['en_espera']} persona(s) en espera en tu grupo")
            
            st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
            
            col_dura1, col_dura2 = st.columns(2)
            with col_dura1:
                duracion_corta = config_pvd.get('duracion_corta', 5)
                if st.button(
                    f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
                    use_container_width=True,
                    type="primary",
                    key="pausa_corta_grupo"
                ):
                    if solicitar_pausa(config_pvd, cola_pvd, "corta", grupo_usuario):
                        st.success("✅ Pausa solicitada. Estás en la cola de tu grupo.")
                        st.rerun()
            
            with col_dura2:
                duracion_larga = config_pvd.get('duracion_larga', 10)
                if st.button(
                    f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
                    use_container_width=True,
                    type="secondary",
                    key="pausa_larga_grupo"
                ):
                    if solicitar_pausa(config_pvd, cola_pvd, "larga", grupo_usuario):
                        st.success("✅ Pausa solicitada. Estás en la cola de tu grupo.")
                        st.rerun()
    
    # Información sobre el sistema
    st.markdown("---")
    st.info("""
    **⚙️ Sistema Automático Mejorado:**
    
    - **✅ Confirmación obligatoria**: Debes confirmar cuando sea tu turno
    - **✅ Finalización automática**: Las pausas se finalizan solas al terminar el tiempo
    - **🔄 Temporizador interno**: El sistema verifica cada 60 segundos
    - **👥 Gestión por grupos**: Cada grupo tiene sus propios espacios y configuración
    - **🔄 Sin autorefresh**: La página NO se actualiza automáticamente
    
    **📢 ¿Cómo funciona?**
    1. Solicita una pausa (corta o larga)
    2. Espera tu turno en la cola de tu grupo
    3. **Cuando sea tu turno, verás una ALERTA GRANDE preguntando si confirmas**
    4. **DEBES CONFIRMAR** para comenzar tu pausa - NO comienza automáticamente
    5. Si no confirmas en 2 minutos, pierdes tu turno
    6. La pausa termina automáticamente
    
    **⚠️ IMPORTANTE:**
    - La página NO se refresca automáticamente
    - Debes hacer clic en **🔄 Actualizar Ahora** para ver cambios
    """)