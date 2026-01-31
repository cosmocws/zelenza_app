# agent_performance.py
"""
Funciones para cálculo de rendimiento de agentes - USANDO AGENT_CALCULATIONS.PY
"""

import streamlit as st
from datetime import datetime, date, timedelta
from agent_schedule_manager import (
    cargar_ventas_agentes, 
    cargar_horarios_agentes,
    cargar_ausencias_agentes,
    cargar_metricas_agentes
)
from database import cargar_registro_llamadas
from festivos_manager import cargar_festivos

def calcular_sph_acumulado_agente(agente_id, mes_key=None):
    """Calcula el SPH acumulado de un agente usando agent_calculations.py"""
    try:
        if mes_key is None:
            hoy = datetime.now()
            mes_key = f"{hoy.year}-{hoy.month:02d}"
        
        # Cargar todos los datos necesarios
        ventas_agentes = cargar_ventas_agentes()
        registro_llamadas = cargar_registro_llamadas()
        horarios_agentes = cargar_horarios_agentes()
        ausencias_agentes = cargar_ausencias_agentes()
        festivos_data = cargar_festivos()
        
        # Usar la función de agent_calculations.py
        from agent_calculations import calcular_sph_acumulado_mes
        sph_acumulado = calcular_sph_acumulado_mes(
            agente_id, 
            mes_key, 
            ventas_agentes, 
            registro_llamadas, 
            horarios_agentes, 
            ausencias_agentes, 
            festivos_data
        )
        
        # También calcular ventas y horas para mostrar detalles
        año, mes = map(int, mes_key.split("-"))
        hoy_date = datetime.now().date()
        fecha_inicio = date(año, mes, 1)
        fecha_fin = min(hoy_date, date(año, mes, 28) + timedelta(days=4))
        
        ventas_acumuladas = 0
        horas_efectivas_acumuladas = 0.0
        dias_laborables = 0
        
        # Calcular detalles adicionales
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            # Solo días laborables
            from festivos_manager import es_festivo
            if fecha_actual.weekday() < 5 and not es_festivo(fecha_actual, festivos_data):
                dias_laborables += 1
                
                # Ventas del día
                fecha_str = fecha_actual.strftime("%Y-%m-%d")
                ventas_dia = 0
                if (agente_id in ventas_agentes and 
                    fecha_str in ventas_agentes[agente_id].get("detalle_dias", {})):
                    ventas_dia = ventas_agentes[agente_id]["detalle_dias"][fecha_str].get("ventas", 0)
                
                # Si no hay en ventas_agentes, buscar en registro_llamadas
                if ventas_dia == 0 and fecha_str in registro_llamadas:
                    if agente_id in registro_llamadas[fecha_str]:
                        ventas_dia = registro_llamadas[fecha_str][agente_id].get("ventas", 0)
                
                ventas_acumuladas += ventas_dia
                
                # Horas del día (aproximadas)
                horas_trabajadas = 6.0  # Valor por defecto
                if agente_id in horarios_agentes:
                    dia_semana = fecha_actual.strftime("%A")
                    if dia_semana in horarios_agentes[agente_id]:
                        from agent_schedule_manager import obtener_horas_diarias
                        horas_trabajadas = obtener_horas_diarias(horarios_agentes[agente_id][dia_semana])
                
                # Restar ausencias
                if agente_id in ausencias_agentes and fecha_str in ausencias_agentes[agente_id]:
                    horas_perdidas = ausencias_agentes[agente_id][fecha_str].get("horas_perdidas", 0)
                    horas_trabajadas = max(0, horas_trabajadas - horas_perdidas)
                
                horas_efectivas_acumuladas += horas_trabajadas * 0.83
            
            fecha_actual += timedelta(days=1)
        
        return {
            "sph": sph_acumulado,
            "ventas": ventas_acumuladas,
            "horas_efectivas": round(horas_efectivas_acumuladas, 2),
            "dias_laborables": dias_laborables,
            "mes": mes_key
        }
        
    except Exception as e:
        print(f"Error calculando SPH acumulado para {agente_id}: {e}")
        return {
            "sph": 0.0,
            "ventas": 0,
            "horas_efectivas": 0.0,
            "dias_laborables": 0,
            "mes": mes_key or f"{datetime.now().year}-{datetime.now().month:02d}"
        }

def mostrar_performance_sidebar(usuario_id):
    """Muestra el rendimiento del agente en el sidebar"""
    try:
        # Cargar métricas para obtener objetivo SPH
        metricas = cargar_metricas_agentes()
        
        hoy = datetime.now()
        mes_key = f"{hoy.year}-{hoy.month:02d}"
        
        # Calcular SPH acumulado usando la nueva función
        datos_sph = calcular_sph_acumulado_agente(usuario_id, mes_key)
        
        # Verificar si es agente
        es_agente = (datos_sph["ventas"] > 0 or 
                    datos_sph["horas_efectivas"] > 0 or
                    (usuario_id in metricas and mes_key in metricas[usuario_id]))
        
        if not es_agente:
            return False
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Tu Rendimiento")
        
        # Obtener objetivo SPH
        sph_objetivo = 0.07  # Valor por defecto
        if usuario_id in metricas and mes_key in metricas[usuario_id]:
            sph_objetivo = metricas[usuario_id][mes_key].get("sph", 0.07)
        
        sph_actual = datos_sph["sph"]
        
        # Mostrar métricas
        col_sph1, col_sph2 = st.sidebar.columns(2)
        with col_sph1:
            st.sidebar.metric("🎯 SPH Objetivo", f"{sph_objetivo:.4f}")
        with col_sph2:
            delta = f"{(sph_actual - sph_objetivo):.4f}" if sph_actual > sph_objetivo else None
            st.sidebar.metric("📈 SPH Actual", f"{sph_actual:.4f}", delta=delta)
        
        # Barra de progreso
        if sph_objetivo > 0:
            progreso = min(100, (sph_actual / sph_objetivo) * 100)
            st.sidebar.progress(int(progreso))
        
        # Más estadísticas
        with st.sidebar.expander("📋 Detalles", expanded=False):
            st.write(f"**Ventas acumuladas:** {datos_sph['ventas']}")
            st.write(f"**Horas efectivas:** {datos_sph['horas_efectivas']}h")
            st.write(f"**Días laborables:** {datos_sph['dias_laborables']}")
            st.write(f"**Productividad requerida:** 83%")
            
            if datos_sph['ventas'] > 0:
                ventas_por_dia = datos_sph['ventas'] / max(1, datos_sph['dias_laborables'])
                st.write(f"**Ventas por día:** {ventas_por_dia:.1f}")
        
        # Estado
        if sph_actual >= sph_objetivo:
            st.sidebar.success("✅ ¡Superando objetivo!")
        elif sph_actual >= sph_objetivo * 0.8:
            st.sidebar.info("⚠️ Cerca del objetivo")
        else:
            st.sidebar.warning("📉 Por debajo del objetivo")
        
        return True
        
    except Exception as e:
        print(f"Error mostrando performance para {usuario_id}: {e}")
        return False