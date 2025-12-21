import streamlit as st
import os
import pandas as pd
import json  # <-- AÑADIR ESTA LÍNEA
from datetime import datetime, timedelta
import pytz

from config import COMUNIDADES_AUTONOMAS
from calculation import (
    calcular_plan_ahorro_automatico, determinar_rl_gas,
    calcular_coste_gas_completo, calcular_pmg, filtrar_planes_por_usuario
)
from database import (
    cargar_configuracion_usuarios, cargar_config_pvd, cargar_cola_pvd,
    guardar_cola_pvd
)
from pvd_system import (
    temporizador_pvd, verificar_confirmacion_pvd, actualizar_temporizadores_pvd,
    solicitar_pausa, ESTADOS_PVD
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
                st.image(ruta_completa, use_container_width=True)
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
    """Sistema de Pausas Visuales para usuarios"""
    # Usar el PVD simplificado
    from pvd_simplificado import gestion_pvd_usuario_simplificada
    return gestion_pvd_usuario_simplificada()

def gestion_pvd_usuario_antigua():
    """Sistema de Pausas Visuales para usuarios con notificación de confirmación"""
    st.subheader("👁️ Sistema de Pausas Visuales (PVD)")
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Actualizar Ahora", use_container_width=True, type="primary", key="refresh_pvd_now"):
            st.rerun()
    with col_btn2:
        if st.button("📊 Actualizar Temporizadores", use_container_width=True, key="refresh_timers_user"):
            actualizar_temporizadores_pvd()
            st.rerun()
    
    hora_actual_madrid = datetime.now(pytz.timezone('Europe/Madrid')).strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora actual (Madrid):** {hora_actual_madrid}")
    
    actualizar_temporizadores_pvd()
    
    if verificar_confirmacion_pvd(st.session_state.username, cola_pvd, config_pvd):
        st.markdown("""
        <script>
        window.addEventListener('load', function() {
            setTimeout(function() {
                const overlay = document.createElement('div');
                overlay.id = 'overlay-notificacion-pvd';
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.85);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                `;
                
                overlay.innerHTML = `
                    <div style="
                        background: linear-gradient(135deg, #00b09b, #96c93d);
                        color: white;
                        padding: 30px;
                        border-radius: 15px;
                        text-align: center;
                        max-width: 500px;
                        width: 90%;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                        animation: pulse 1s infinite;
                        border: 3px solid white;
                    ">
                        <h2 style="margin: 0 0 20px 0; font-size: 28px;">🎉 ¡ES TU TURNO!</h2>
                        <p style="font-size: 20px; margin: 15px 0; font-weight: bold;">Tu pausa PVD está por comenzar</p>
                        <p style="opacity: 0.9; margin-bottom: 25px; font-size: 16px;">Haz clic en OK para confirmar que estás listo</p>
                        
                        <div style="display: flex; gap: 20px; justify-content: center;">
                            <button id="btn-confirmar-pvd-overlay" style="
                                background: white;
                                color: #00b09b;
                                border: none;
                                padding: 15px 40px;
                                border-radius: 10px;
                                font-size: 18px;
                                font-weight: bold;
                                cursor: pointer;
                                transition: transform 0.2s;
                                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                            ">
                                ✅ OK - Empezar Pausa
                            </button>
                            
                            <button id="btn-cancelar-pvd-overlay" style="
                                background: #f44336;
                                color: white;
                                border: none;
                                padding: 15px 40px;
                                border-radius: 10px;
                                font-size: 18px;
                                font-weight: bold;
                                cursor: pointer;
                                transition: transform 0.2s;
                                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                            ">
                                ❌ Cancelar
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(overlay);
                
                const style = document.createElement('style');
                style.innerHTML = `
                    @keyframes pulse {
                        0% { transform: scale(1); }
                        50% { transform: scale(1.05); }
                        100% { transform: scale(1); }
                    }
                `;
                document.head.appendChild(style);
                
                document.getElementById('btn-confirmar-pvd-overlay').addEventListener('click', function() {
                    document.body.removeChild(overlay);
                    setTimeout(function() {
                        window.location.reload();
                    }, 2000);
                });
                
                document.getElementById('btn-cancelar-pvd-overlay').addEventListener('click', function() {
                    document.body.removeChild(overlay);
                    setTimeout(function() {
                        window.location.reload();
                    }, 3000);
                });
                
            }, 1000);
        });
        </script>
        """, unsafe_allow_html=True)
        
        st.warning("""
        **🔔 ¡ATENCIÓN!**
        
        Deberías estar viendo una ventana emergente EN LA PÁGIMA pidiendo confirmación.
        
        Si no la ves:
        1. La página se recargará automáticamente
        2. Haz clic en OK cuando aparezca
        3. La pausa comenzará automáticamente
        """)
    
    usuario_pausa_activa = None
    for pausa in cola_pvd:
        if pausa['usuario_id'] == st.session_state.username and pausa['estado'] in ['ESPERANDO', 'EN_CURSO']:
            usuario_pausa_activa = pausa
            break
    
    if usuario_pausa_activa:
        estado_display = ESTADOS_PVD.get(usuario_pausa_activa['estado'], usuario_pausa_activa['estado'])
        
        if usuario_pausa_activa['estado'] == 'ESPERANDO':
            st.warning(f"⏳ **Tienes una pausa solicitada** - {estado_display}")
            
            duracion_elegida = usuario_pausa_activa.get('duracion_elegida', 'corta')
            duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
            
            en_espera = [p for p in cola_pvd if p['estado'] == 'ESPERANDO']
            en_espera_ordenados = sorted(en_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            posicion = next((i+1 for i, p in enumerate(en_espera_ordenados) 
                           if p['id'] == usuario_pausa_activa['id']), 1)
            
            en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
            maximo = config_pvd['maximo_simultaneo']
            
            tiempo_restante = temporizador_pvd.obtener_tiempo_restante(st.session_state.username)
            
            if tiempo_restante is not None and tiempo_restante > 0:
                st.markdown("### ⏱️ TEMPORIZADOR PARA TU PAUSA")
                
                # Importar la función crear_temporizador_html
                from notifications import crear_temporizador_html
                temporizador_html = crear_temporizador_html(int(tiempo_restante), st.session_state.username)
                st.components.v1.html(temporizador_html, height=280)
                
                with st.expander("📊 Información detallada", expanded=True):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("Posición en cola", f"#{posicion}")
                    with col_info2:
                        st.metric("Personas esperando", len(en_espera))
                    with col_info3:
                        st.metric("Pausas activas", f"{en_pausa}/{maximo}")
                    
                    hora_entrada_estimada = (datetime.now(pytz.timezone('Europe/Madrid')) + timedelta(minutes=tiempo_restante)).strftime('%H:%M')
                    st.info(f"**Hora estimada de entrada:** {hora_entrada_estimada} (hora Madrid)")
                    
                    if 'notificado_en' in usuario_pausa_activa:
                        st.success("✅ **Ya se te notificó** - Debes confirmar cuando veas la alerta")
                    
                    if tiempo_restante <= 5:
                        st.warning(f"🔔 **Atención:** Quedan {int(tiempo_restante)} minutos. ¡Prepárate para la notificación!")
                
                if posicion == 1 and en_pausa < maximo:
                    from pvd_system import iniciar_siguiente_en_cola
                    if iniciar_siguiente_en_cola(cola_pvd, config_pvd):
                        st.success("✅ **¡Pausa iniciada automáticamente!**")
                        st.rerun()
                
                if st.button("❌ Cancelar mi pausa", type="secondary", use_container_width=True, key="cancelar_pausa_temporizador"):
                    usuario_pausa_activa['estado'] = 'CANCELADO'
                    guardar_cola_pvd(cola_pvd)
                    temporizador_pvd.cancelar_temporizador(st.session_state.username)
                    st.success("✅ Pausa cancelada")
                    st.rerun()
                    
            elif tiempo_restante == 0:
                st.markdown("### 🎯 ¡ES TU TURNO!")
                
                st.balloons()
                
                with st.container():
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #00b09b, #96c93d);
                        color: white;
                        padding: 30px;
                        border-radius: 15px;
                        text-align: center;
                        margin: 20px 0;
                    ">
                        <h2 style="margin: 0; font-size: 32px;">🎉 ¡TU TURNO HA LLEGADO!</h2>
                        <p style="font-size: 20px; margin: 15px 0;">Debes confirmar cuando veas la alerta en tu navegador</p>
                        <p style="opacity: 0.9;">La pausa comenzará automáticamente después de tu confirmación</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.info("""
                **📢 Deberías ver o haber visto:**
                - Una **alerta/ventana emergente** en tu navegador
                - Con el mensaje: **"¡ES TU TURNO PARA LA PAUSA PVD!"**
                - Y botones: **OK (Confirmar)** y **Cancelar**
                
                **¿Qué hacer?**
                1. Haz clic en **OK** para confirmar
                2. La pausa comenzará automáticamente
                3. Si haces clic en **Cancelar**, seguirás en la cola
                
                **Si no ves la alerta:**
                - Permite **ventanas emergentes** para este sitio
                - Actualiza la página
                - La alerta aparecerá de nuevo
                """)
                
                st.markdown("""
                <script>
                setTimeout(function() {
                    window.location.reload();
                }, 30000);
                </script>
                """, unsafe_allow_html=True)
                
            else:
                st.info("⏳ Calculando tiempo estimado...")
                
                tiempo_estimado = temporizador_pvd.calcular_tiempo_estimado_entrada(cola_pvd, config_pvd, st.session_state.username)
                
                if tiempo_estimado and tiempo_estimado > 0:
                    if not temporizador_pvd.obtener_tiempo_restante(st.session_state.username):
                        temporizador_pvd.iniciar_temporizador_usuario(st.session_state.username, tiempo_estimado)
                        st.rerun()
                else:
                    st.warning("No se pudo calcular el tiempo estimado. Por favor, actualiza la página.")
        
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
            
            hora_actual_madrid = datetime.now(pytz.timezone('Europe/Madrid'))
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
            
            if tiempo_restante == 0:
                st.success("🎉 **¡Pausa completada!** Puedes volver a solicitar otra si necesitas")
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
                guardar_cola_pvd(cola_pvd)
                from pvd_system import iniciar_siguiente_en_cola
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.rerun()
            
            if st.button("✅ Finalizar pausa ahora", type="primary", key="finish_pause_now", use_container_width=True):
                usuario_pausa_activa['estado'] = 'COMPLETADO'
                usuario_pausa_activa['timestamp_fin'] = datetime.now(pytz.timezone('Europe/Madrid')).isoformat()
                guardar_cola_pvd(cola_pvd)
                from pvd_system import iniciar_siguiente_en_cola
                iniciar_siguiente_en_cola(cola_pvd, config_pvd)
                st.success("✅ Pausa completada")
                st.rerun()
    
    else:
        st.info("👁️ **Sistema de Pausas Visuales Dinámicas**")
        st.write("Toma una pausa para descansar la vista durante tu jornada")
        
        en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
        en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
        maximo = config_pvd['maximo_simultaneo']
        
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("⏸️ En pausa", f"{en_pausa}/{maximo}")
        with col_stats2:
            st.metric("⏳ En espera", en_espera)
        with col_stats3:
            pausas_hoy = len([p for p in cola_pvd 
                            if p['usuario_id'] == st.session_state.username and 
                            datetime.fromisoformat(p.get('timestamp_solicitud', datetime.now(pytz.timezone('Europe/Madrid')).isoformat())).date() == datetime.now(pytz.timezone('Europe/Madrid')).date() and
                            p['estado'] != 'CANCELADO'])
            st.metric("📅 Tus pausas hoy", f"{pausas_hoy}/5")
        
        if pausas_hoy >= 5:
            st.warning(f"⚠️ **Límite diario alcanzado** - Has tomado {pausas_hoy} pausas hoy")
            st.info("Puedes tomar más pausas mañana")
        else:
            st.write("### ⏱️ ¿Cuánto tiempo necesitas descansar?")
            
            espacios_libres = max(0, maximo - en_pausa)
            
            if espacios_libres > 0:
                st.success(f"✅ **HAY ESPACIO DISPONIBLE** - {espacios_libres} puesto(s) libre(s)")
            else:
                st.warning(f"⏳ **SISTEMA LLENO** - Hay {en_espera} persona(s) en cola. Te pondremos en espera.")
            
            col_dura1, col_dura2 = st.columns(2)
            with col_dura1:
                duracion_corta = config_pvd['duracion_corta']
                if st.button(
                    f"☕ **Pausa Corta**\n\n{duracion_corta} minutos\n\nIdeal para estirar",
                    use_container_width=True,
                    type="primary",
                    key="pausa_corta"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "corta")
                    st.rerun()
            
            with col_dura2:
                duracion_larga = config_pvd['duracion_larga']
                if st.button(
                    f"🌿 **Pausa Larga**\n\n{duracion_larga} minutos\n\nIdeal para desconectar",
                    use_container_width=True,
                    type="secondary",
                    key="pausa_larga"
                ):
                    solicitar_pausa(config_pvd, cola_pvd, "larga")
                    st.rerun()