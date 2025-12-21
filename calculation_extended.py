import streamlit as st
import pandas as pd
from datetime import datetime
from config import (
    ALQUILER_CONTADOR, PACK_IBERDROLA, IMPUESTO_ELECTRICO,
    DESCUENTO_PRIMERA_FACTURA, IVA, DIAS_ANUAL,
    COMUNIDADES_AUTONOMAS
)
from calculation import (
    calcular_plan_ahorro_automatico, filtrar_planes_por_usuario
)

def calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh=0.0):
    """Calcula comparación exacta con factura actual"""
    try:
        # Cargar datos
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        planes_activos = filtrar_planes_por_usuario(df_luz, st.session_state.username, "luz")
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Configuración de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando comparativa...")
        
        todos_resultados = []
        resultados_con_pi = []
        
        # Calcular para cada plan
        for _, plan in planes_activos.iterrows():
            # Verificar disponibilidad en comunidad
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in str(plan['plan']).upper()
            es_especial_plus = "ESPECIAL PLUS" in str(plan['plan']).upper()
            
            for tiene_pi in [True, False]:
                if es_ahorro_automatico:
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo, dias, tiene_pi, es_anual=False
                    )
                    
                    precio_kwh = "0.215€/0.105€*"
                    coste_consumo = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA * (dias / 30) if tiene_pi else 0.0
                    
                    if tiene_pi:
                        bonificacion_mensual = 10.00 * (dias / 30)
                    else:
                        bonificacion_mensual = 8.33 * (dias / 30)
                    
                else:
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA * (dias / 30)
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo = consumo * precio_kwh
                    bonificacion_mensual = 0.0
                
                coste_potencia = potencia * plan['total_potencia'] * dias
                ingreso_excedentes = excedente_kwh * precio_excedente
                
                subtotal_sin_excedentes = coste_consumo + coste_potencia
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes
                
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                coste_alquiler = ALQUILER_CONTADOR * (dias / 30)
                subtotal_final = subtotal_con_excedentes + coste_alquiler + coste_pack
                
                impuesto_electrico = subtotal_final * IMPUESTO_ELECTRICO
                
                if comunidad != "Canarias":
                    iva_total = (subtotal_final + impuesto_electrico) * IVA
                else:
                    iva_total = 0
                
                total_bruto = subtotal_final + impuesto_electrico + iva_total
                total_neto = total_bruto - DESCUENTO_PRIMERA_FACTURA - bonificacion_mensual
                total_nuevo = max(0, total_neto)
                
                ahorro = costo_actual - total_nuevo
                ahorro_anual = ahorro * (365 / dias)
                
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d a 0.105€"
                
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                if excedente_kwh > 0:
                    info_extra += f" | ☀️ {excedente_kwh}kWh excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes:.2f}€"
                
                if len(comunidades_plan) == 1 and 'Toda España' in comunidades_plan:
                    info_extra += " | 🗺️ Toda España"
                elif len(comunidades_plan) < 5:
                    info_extra += f" | 🗺️ {', '.join(comunidades_plan)}"
                else:
                    info_extra += f" | 🗺️ {len(comunidades_plan)} CCAA"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Coste Nuevo': round(total_nuevo, 2),
                    'Ahorro Mensual': round(ahorro, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # Filtrar resultados especial plus
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar mejor plan
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        # Mostrar resultados
        st.write("### 📊 RESULTADOS DE LA COMPARATIVA")
        
        st.info(f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo:** {consumo}kWh × Precio del plan
        - **Potencia:** {potencia}kW × {dias}días × Tarifa potencia
        - **Excedentes:** {excedente_kwh}kWh × {precio_excedente}€/kWh = {excedente_kwh * precio_excedente:.2f}€
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """)
        
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Coste Actual", f"{costo_actual}€")
        with col2:
            st.metric("💰 Coste Nuevo", f"{mejor_plan_con_pi['Coste Nuevo']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        df_resultados = pd.DataFrame(resultados_finales)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Coste Nuevo', 
                          'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # Recomendaciones
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
        
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning("ℹ️ Todos los planes CON Pack Iberdrola son más caros que tu factura actual")
            
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {str(e)}")

def calcular_estimacion_anual(potencia, consumo_anual, costo_mensual_actual, comunidad, excedente_mensual_kwh=0.0):
    """Calcula estimación anual para usuarios"""
    try:
        # Cargar datos
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        planes_activos = df_luz[df_luz['activo'] == True]
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return
        
        # Configuración de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando estimación anual...")
        
        # Calcular costo anual actual
        costo_anual_actual = costo_mensual_actual * 12
        excedente_anual_kwh = excedente_mensual_kwh * 12
        ingreso_excedentes_anual = excedente_anual_kwh * precio_excedente
        
        # Listas para resultados
        todos_resultados = []
        resultados_con_pi = []
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR DISPONIBILIDAD EN COMUNIDAD
            comunidades_plan = []
            if pd.notna(plan.get('comunidades_autonomas')):
                comunidades_plan = plan['comunidades_autonomas'].split(';')
            
            disponible_en_comunidad = (
                'Toda España' in comunidades_plan or 
                comunidad in comunidades_plan or
                not comunidades_plan
            )
            
            if not disponible_en_comunidad:
                continue
            
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in str(plan['plan']).upper()
            es_especial_plus = "ESPECIAL PLUS" in str(plan['plan']).upper()
            
            for tiene_pi in [True, False]:
                
                if es_ahorro_automatico:
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo_anual, DIAS_ANUAL, tiene_pi, es_anual=True
                    )
                    
                    precio_kwh = "0.215€/0.105€*"
                    coste_consumo_anual = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA if tiene_pi else 0.0
                    
                    if tiene_pi:
                        bonificacion_anual = 10.00 * 12
                    else:
                        bonificacion_anual = 8.33 * 12
                    
                else:
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo_anual = consumo_anual * precio_kwh
                    bonificacion_anual = 0.0
                
                # Cálculos
                coste_potencia_anual = potencia * plan['total_potencia'] * DIAS_ANUAL
                subtotal_sin_excedentes = coste_consumo_anual + coste_potencia_anual
                subtotal_con_excedentes = subtotal_sin_excedentes - ingreso_excedentes_anual
                
                if subtotal_con_excedentes < 0:
                    subtotal_con_excedentes = 0
                
                coste_alquiler_anual = ALQUILER_CONTADOR * 12
                subtotal_final_anual = subtotal_con_excedentes + coste_alquiler_anual + coste_pack
                
                impuesto_electrico_anual = subtotal_final_anual * IMPUESTO_ELECTRICO
                iva_anual = (subtotal_final_anual + impuesto_electrico_anual) * IVA
                
                total_bruto_anual = subtotal_final_anual + impuesto_electrico_anual + iva_anual
                total_neto_anual = total_bruto_anual - DESCUENTO_PRIMERA_FACTURA - bonificacion_anual
                total_anual = max(0, total_neto_anual)
                mensual = total_anual / 12
                
                # Calcular ahorro
                ahorro_anual = costo_anual_actual - total_anual
                ahorro_mensual = ahorro_anual / 12
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                precio_display = f"{precio_kwh}" if not es_ahorro_automatico else f"{precio_kwh}"
                
                info_extra = ""
                if es_ahorro_automatico:
                    if tiene_pi:
                        info_extra = f" | 🎁 +10€/mes bono"
                    else:
                        info_extra = f" | 🎁 +8.33€/mes bono"
                    info_extra += f" | 📊 {calculo_ahorro['dias_bajo_precio']}d/año a 0.105€"
                
                if es_especial_plus:
                    info_extra += " | 📍 Con permanencia"
                
                if excedente_mensual_kwh > 0:
                    info_extra += f" | ☀️ {excedente_mensual_kwh}kWh/mes excedentes"
                    info_extra += f" | 📉 -{ingreso_excedentes_anual/12:.2f}€/mes"
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_display,
                    'Mensual': round(mensual, 2),
                    'Anual': round(total_anual, 2),
                    'Ahorro Mensual': round(ahorro_mensual, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro_mensual > 0 else '🔴 Pagas más',
                    'Info Extra': info_extra,
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # Filtrar resultados CON PI según regla del Especial Plus
        ahorros_con_pi_no_especial = [r['Ahorro Mensual'] for r in resultados_con_pi if not r['es_especial_plus']]
        max_ahorro_con_pi = max(ahorros_con_pi_no_especial) if ahorros_con_pi_no_especial else 0
        
        resultados_con_pi_filtrados = []
        for resultado in resultados_con_pi:
            if not resultado['es_especial_plus']:
                resultados_con_pi_filtrados.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro_con_pi < umbral:
                    resultados_con_pi_filtrados.append(resultado)
        
        # Filtrar TODOS los resultados
        ahorros_no_especial = [r['Ahorro Mensual'] for r in todos_resultados if not r['es_especial_plus']]
        max_ahorro = max(ahorros_no_especial) if ahorros_no_especial else 0
        
        resultados_finales = []
        for resultado in todos_resultados:
            if not resultado['es_especial_plus']:
                resultados_finales.append(resultado)
            else:
                umbral = resultado['umbral_especial_plus']
                if max_ahorro < umbral:
                    resultados_finales.append(resultado)
        
        if not resultados_con_pi_filtrados:
            st.warning(f"ℹ️ No hay planes CON Pack Iberdrola disponibles para {comunidad}")
            return
        
        # Encontrar mejor plan
        mejor_plan_con_pi = max(resultados_con_pi_filtrados, key=lambda x: x['Ahorro Mensual'])
        mejor_plan_todos = max(resultados_finales, key=lambda x: x['Ahorro Mensual'])
        
        st.write("### 📊 ESTIMACIÓN ANUAL")
        
        info_text = f"""
        **🧮 Fórmula aplicada:** (Consumo + Potencia) - Excedentes
        
        - **Consumo anual:** {consumo_anual}kWh
        - **Potencia:** {potencia}kW
        - **Excedentes:** {excedente_mensual_kwh}kWh/mes × {precio_excedente}€/kWh = {excedente_mensual_kwh * precio_excedente * 12:.2f}€/año
        - **Comunidad:** {comunidad} {'(Sin IVA)' if comunidad == 'Canarias' else ''}
        - **Descuento bienvenida:** 5€
        - **🔒 Las métricas muestran solo planes CON Pack Iberdrola**
        """
        
        if excedente_mensual_kwh > 0:
            info_text += f"\n- **Excedentes anuales:** {excedente_anual_kwh}kWh × {precio_excedente}€ = {ingreso_excedentes_anual:.2f}€"
        
        st.info(info_text)
        
        # MÉTRICAS PRINCIPALES
        st.write("#### 💰 COMPARATIVA CON PACK IBERDROLA")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💶 Actual Mensual", f"{costo_mensual_actual}€")
        with col2:
            st.metric("💰 Nuevo Mensual", f"{mejor_plan_con_pi['Mensual']}€")
        with col3:
            st.metric("📈 Ahorro Mensual", f"{mejor_plan_con_pi['Ahorro Mensual']}€", 
                     delta=f"{mejor_plan_con_pi['Ahorro Mensual']}€" if mejor_plan_con_pi['Ahorro Mensual'] > 0 else None)
        with col4:
            st.metric("🎯 Ahorro Anual", f"{mejor_plan_con_pi['Ahorro Anual']}€")
        
        # TABLA COMPLETA
        st.write("#### 📋 TABLA COMPARATIVA COMPLETA")
        st.info("**Mostrando todas las opciones disponibles (CON y SIN Pack Iberdrola)**")
        
        df_resultados = pd.DataFrame(resultados_finales)
        df_resultados['orden_pi'] = df_resultados['Pack Iberdrola'].apply(lambda x: 0 if '✅ CON' in x else 1)
        df_resultados = df_resultados.sort_values(['orden_pi', 'Ahorro Mensual'], ascending=[True, False])
        df_resultados = df_resultados.drop('orden_pi', axis=1)
        
        columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 'Mensual', 
                          'Anual', 'Ahorro Mensual', 'Ahorro Anual', 'Estado', 'Info Extra']
        
        st.dataframe(df_resultados[columnas_mostrar], use_container_width=True)
        
        # RECOMENDACIONES
        if mejor_plan_con_pi['Ahorro Mensual'] > 0:
            mensaje_con_pi = f"🎯 **MEJOR CON PACK IBERDROLA**: {mejor_plan_con_pi['Plan']} - Ahorras {mejor_plan_con_pi['Ahorro Mensual']}€/mes ({mejor_plan_con_pi['Ahorro Anual']}€/año)"
            if mejor_plan_con_pi['Info Extra']:
                mensaje_con_pi += mejor_plan_con_pi['Info Extra']
            st.success(mensaje_con_pi)
            st.info(f"💡 Pagarías {mejor_plan_con_pi['Mensual']}€/mes normalmente")
        
        if mejor_plan_todos['Ahorro Mensual'] > 0 and mejor_plan_todos['tiene_pi'] == False:
            st.info(f"💡 **NOTA**: La opción SIN Pack Iberdrola '{mejor_plan_todos['Plan']}' ahorra {mejor_plan_todos['Ahorro Mensual']}€/mes más, pero no incluye el Pack Iberdrola")
        
        if mejor_plan_con_pi['Ahorro Mensual'] <= 0:
            st.warning(f"ℹ️ Todos los planes CON Pack Iberdrola son más caros que lo que pagas actualmente ({costo_mensual_actual}€/mes)")
        
    except Exception as e:
        st.error(f"❌ Error en el cálculo anual: {str(e)}")