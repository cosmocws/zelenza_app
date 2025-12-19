import streamlit as st
import pandas as pd
from modules.utils import filtrar_planes_por_usuario

# Constantes para cálculos
ALQUILER_CONTADOR = 0.81
PACK_IBERDROLA = 3.95
IMPUESTO_ELECTRICO = 0.0511
DESCUENTO_PRIMERA_FACTURA = 5.00
IVA = 0.21

def calcular_comparacion_exacta(dias, potencia, consumo, costo_actual, comunidad, excedente_kwh=0.0):
    """Calcula comparación exacta con factura actual - Muestra CON y SIN PI"""
    try:
        # Cargar planes activos
        df_luz = pd.read_csv("data/precios_luz.csv")
        planes_activos = filtrar_planes_por_usuario(df_luz, st.session_state.username, "luz")
        
        if planes_activos.empty:
            st.warning("⚠️ No hay planes configurados. Contacta con el administrador.")
            return None
        
        # Cargar precio de excedentes
        try:
            config_excedentes = pd.read_csv("data/config_excedentes.csv")
            precio_excedente = config_excedentes.iloc[0]['precio_excedente_kwh']
        except:
            precio_excedente = 0.06
        
        st.success("🧮 Calculando comparativa...")
        
        # Listas para resultados
        todos_resultados = []
        resultados_con_pi = []
        
        for _, plan in planes_activos.iterrows():
            
            # VERIFICAR SI EL PLAN ESTÁ DISPONIBLE EN LA COMUNIDAD SELECCIONADA
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
            
            # VERIFICAR SI ES PLAN ESPECIAL
            es_ahorro_automatico = "AHORRO AUTOMÁTICO" in plan['plan'].upper()
            es_especial_plus = "ESPECIAL PLUS" in plan['plan'].upper()
            
            for tiene_pi in [True, False]:
                
                if es_ahorro_automatico:
                    # CÁLCULO ESPECIAL PARA AHORRO AUTOMÁTICO
                    calculo_ahorro = calcular_plan_ahorro_automatico(
                        plan, consumo, dias, tiene_pi, es_anual=False
                    )
                    
                    precio_kwh = f"0.215€/0.105€*"
                    coste_consumo = calculo_ahorro['coste_consumo']
                    coste_pack = PACK_IBERDROLA * (dias / 30) if tiene_pi else 0.0
                    
                    # Bonificación mensual fija
                    if tiene_pi:
                        bonificacion_mensual = 10.00 * (dias / 30)
                    else:
                        bonificacion_mensual = 8.33 * (dias / 30)
                    
                else:
                    # CÁLCULO NORMAL
                    if tiene_pi:
                        precio_kwh = plan['con_pi_kwh']
                        coste_pack = PACK_IBERDROLA * (dias / 30)
                    else:
                        precio_kwh = plan['sin_pi_kwh']
                        coste_pack = 0.0
                    
                    coste_consumo = consumo * precio_kwh
                    bonificacion_mensual = 0.0
                
                # CALCULOS
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
                
                # Ahorro
                ahorro = costo_actual - total_nuevo
                ahorro_anual = ahorro * (365 / dias)
                
                # Información para mostrar
                pack_info = '✅ CON' if tiene_pi else '❌ SIN'
                
                resultado = {
                    'Plan': plan['plan'],
                    'Pack Iberdrola': pack_info,
                    'Precio kWh': precio_kwh,
                    'Coste Nuevo': round(total_nuevo, 2),
                    'Ahorro Mensual': round(ahorro, 2),
                    'Ahorro Anual': round(ahorro_anual, 2),
                    'Estado': '💚 Ahorras' if ahorro > 0 else '🔴 Pagas más',
                    'es_especial_plus': es_especial_plus,
                    'tiene_pi': tiene_pi,
                    'umbral_especial_plus': plan.get('umbral_especial_plus', 15.00)
                }
                
                todos_resultados.append(resultado)
                
                if tiene_pi:
                    resultados_con_pi.append(resultado)
        
        # ========== FALTA ESTA PARTE EN TU CÓDIGO ==========
        # Filtrar y mostrar resultados
        
        if not todos_resultados:
            st.warning("⚠️ No hay planes disponibles para tu comunidad autónoma.")
            return None
        
        # Filtrar resultados según si es Especial Plus
        resultados_filtrados = []
        
        # Separar planes Especial Plus de los demás
        especial_plus_resultados = [r for r in todos_resultados if r['es_especial_plus']]
        otros_resultados = [r for r in todos_resultados if not r['es_especial_plus']]
        
        # Para Especial Plus: mostrar solo el mejor (menor costo)
        if especial_plus_resultados:
            mejor_especial_plus = min(especial_plus_resultados, key=lambda x: x['Coste Nuevo'])
            resultados_filtrados.append(mejor_especial_plus)
        
        # Para otros planes: mostrar todos
        resultados_filtrados.extend(otros_resultados)
        
        # Ordenar por ahorro anual (de mayor a menor)
        resultados_filtrados.sort(key=lambda x: x['Ahorro Anual'], reverse=True)
        
        # Mostrar resultados en tabla
        if resultados_filtrados:
            # Crear DataFrame para mostrar
            df_resultados = pd.DataFrame(resultados_filtrados)
            
            # Seleccionar columnas para mostrar
            columnas_mostrar = ['Plan', 'Pack Iberdrola', 'Precio kWh', 
                               'Coste Nuevo', 'Ahorro Mensual', 'Ahorro Anual', 'Estado']
            
            st.subheader("📊 Resultados de la Comparativa")
            
            # Mostrar tabla
            st.dataframe(
                df_resultados[columnas_mostrar],
                use_container_width=True,
                hide_index=True
            )
            
            # Resumen
            mejor_plan = resultados_filtrados[0]
            st.success(f"✨ **Mejor opción:** {mejor_plan['Plan']} - Ahorro anual estimado: €{mejor_plan['Ahorro Anual']:,.2f}")
            
            # Mostrar detalles adicionales para planes especiales
            if mejor_plan['es_especial_plus']:
                st.info(f"📝 **Plan Especial Plus:** Umbral mínimo de ahorro garantizado: €{mejor_plan['umbral_especial_plus']} mensuales")
            
            return resultados_filtrados
        else:
            st.warning("⚠️ No se encontraron planes aplicables.")
            return None
        
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
        # ========== FIN DE LA PARTE FALTANTE ==========

def calcular_plan_ahorro_automatico(plan, consumo, dias, tiene_pi=False, es_anual=False):
    """
    Calcula el coste para el Plan Ahorro Automático
    """
    if es_anual:
        total_dias = 365
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    else:
        total_dias = dias
        dias_bajo_precio = int((2 / 7) * total_dias)
        dias_precio_normal = total_dias - dias_bajo_precio
    
    consumo_diario = consumo / total_dias
    consumo_bajo_precio = consumo_diario * dias_bajo_precio
    consumo_precio_normal = consumo_diario * dias_precio_normal
    
    precio_normal = 0.215
    precio_bajo = 0.105
    
    coste_consumo_normal = consumo_precio_normal * precio_normal
    coste_consumo_bajo = consumo_bajo_precio * precio_bajo
    coste_consumo_total = coste_consumo_normal + coste_consumo_bajo
    
    return {
        'coste_consumo': coste_consumo_total,
        'dias_bajo_precio': dias_bajo_precio,
        'dias_precio_normal': dias_precio_normal
    }

def calcular_estimacion_anual(parametros):
    """
    Calcula estimación anual - Función requerida por app.py
    """
    try:
        st.info("📈 Calculando estimación anual...")
        
        # Extraer parámetros
        consumo_mensual = parametros.get('consumo_mensual', 0)
        potencia = parametros.get('potencia', 0)
        comunidad = parametros.get('comunidad', '')
        costo_actual_mensual = parametros.get('costo_actual', 0)
        
        # Estimación básica
        consumo_anual = consumo_mensual * 12
        costo_actual_anual = costo_actual_mensual * 12
        
        # Cálculo simplificado
        pack_anual = PACK_IBERDROLA * 12
        alquiler_anual = ALQUILER_CONTADOR * 12
        coste_potencia_anual = potencia * 0.12 * 365  # Aproximación
        
        # Estimación de consumo anual (precio promedio)
        precio_promedio_kwh = 0.18
        coste_consumo_anual = consumo_anual * precio_promedio_kwh
        
        # Total estimado
        subtotal = coste_consumo_anual + coste_potencia_anual + alquiler_anual + pack_anual
        impuesto = subtotal * IMPUESTO_ELECTRICO
        
        if comunidad != "Canarias":
            iva = (subtotal + impuesto) * IVA
        else:
            iva = 0
        
        total_estimado_anual = subtotal + impuesto + iva
        ahorro_potencial = costo_actual_anual - total_estimado_anual
        
        return {
            'consumo_anual_kwh': round(consumo_anual, 2),
            'costo_actual_anual': round(costo_actual_anual, 2),
            'costo_estimado_anual': round(total_estimado_anual, 2),
            'ahorro_potencial_anual': round(ahorro_potencial, 2),
            'ahorro_mensual_promedio': round(ahorro_potencial / 12, 2)
        }
        
    except Exception as e:
        st.error(f"Error en estimación anual: {e}")
        return None

# Funciones para gas
def determinar_rl_gas(consumo_anual):
    """Determina automáticamente el RL según consumo anual"""
    if consumo_anual <= 5000:
        return "RL1"
    elif consumo_anual <= 15000:
        return "RL2"
    else:
        return "RL3"

# Constantes para gas (si no tienes modules.gas)
PMG_COSTE = 3.42  # €/mes
PMG_IVA = 0.21  # 21% IVA (excepto Canarias)

def calcular_pmg(tiene_pmg, es_canarias=False):
    """Calcula el coste del PMG con/sin IVA"""
    if not tiene_pmg:
        return 0
    
    coste_pmg = PMG_COSTE
    if not es_canarias:
        coste_pmg *= (1 + PMG_IVA)
    
    return coste_pmg * 12  # Anual

def calcular_coste_gas_completo(plan, consumo_kwh, tiene_pmg=True, es_canarias=False):
    """Calcula coste total de gas incluyendo PMG e IVA"""
    try:
        # Coste del gas (sin IVA todavía)
        if tiene_pmg:
            termino_fijo = plan.get("termino_fijo_con_pmg", 0)
            termino_variable = plan.get("termino_variable_con_pmg", 0)
        else:
            termino_fijo = plan.get("termino_fijo_sin_pmg", 0)
            termino_variable = plan.get("termino_variable_sin_pmg", 0)
        
        coste_fijo = termino_fijo * 12
        coste_variable = consumo_kwh * termino_variable
        coste_gas_sin_iva = coste_fijo + coste_variable
        
        # Aplicar IVA al gas (excepto Canarias)
        if not es_canarias:
            coste_gas_con_iva = coste_gas_sin_iva * (1 + PMG_IVA)
        else:
            coste_gas_con_iva = coste_gas_sin_iva
        
        # Coste PMG
        coste_pmg = calcular_pmg(tiene_pmg, es_canarias)
        
        return coste_gas_con_iva + coste_pmg
        
    except Exception as e:
        st.error(f"Error calculando coste gas: {e}")
        return 0