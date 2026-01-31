"""
agent_calculations.py
Funciones para calcular métricas de agentes
"""

import pandas as pd
from datetime import datetime, date, timedelta

def calcular_sph_diario(agente_id, fecha, ventas_agentes, registro_llamadas, horarios_agentes, ausencias_agentes, festivos_data):
    """Calcula el SPH de un agente para un día específico"""
    try:
        from agent_schedule_manager import obtener_horas_diarias
        from festivos_manager import es_festivo
        
        fecha_date = fecha if isinstance(fecha, date) else fecha.date()
        fecha_str = fecha_date.strftime("%Y-%m-%d")
        
        # 1. Obtener ventas del día
        ventas_dia = 0
        if (agente_id in ventas_agentes and 
            fecha_str in ventas_agentes[agente_id].get("detalle_dias", {})):
            ventas_dia = ventas_agentes[agente_id]["detalle_dias"][fecha_str].get("ventas", 0)
        
        # Si no hay en ventas_agentes, buscar en registro_llamadas
        if ventas_dia == 0 and fecha_str in registro_llamadas:
            if agente_id in registro_llamadas[fecha_str]:
                ventas_dia = registro_llamadas[fecha_str][agente_id].get("ventas", 0)
        
        # 2. Obtener horas trabajadas
        horas_trabajadas = 0
        
        if agente_id in horarios_agentes:
            dia_semana = fecha_date.strftime("%A")
            if dia_semana in horarios_agentes[agente_id]:
                horas_trabajadas = obtener_horas_diarias(horarios_agentes[agente_id][dia_semana])
            else:
                horas_trabajadas = 6.0  # Valor por defecto
        else:
            horas_trabajadas = 6.0
        
        # 3. Restar ausencias
        if agente_id in ausencias_agentes and fecha_str in ausencias_agentes[agente_id]:
            horas_perdidas = ausencias_agentes[agente_id][fecha_str].get("horas_perdidas", 0)
            horas_trabajadas = max(0, horas_trabajadas - horas_perdidas)
        
        # 4. Solo días laborables
        if fecha_date.weekday() >= 5 or es_festivo(fecha_date, festivos_data):
            return 0.0  # No hay SPH en días no laborables
        
        # 5. Calcular SPH (83% de productividad)
        horas_efectivas = horas_trabajadas * 0.83
        
        if horas_efectivas > 0:
            sph = ventas_dia / horas_efectivas
            return round(sph, 4)
        else:
            return 0.0
        
    except Exception as e:
        print(f"Error calculando SPH diario para {agente_id} en {fecha}: {e}")
        return 0.0

def calcular_sph_acumulado_mes(agente_id, mes_key, ventas_agentes, registro_llamadas, horarios_agentes, ausencias_agentes, festivos_data):
    """Calcula el SPH acumulado de un agente en un mes"""
    try:
        # Parsear mes_key (formato: "2024-01")
        año, mes = map(int, mes_key.split("-"))
        
        # Obtener todas las fechas del mes hasta hoy
        hoy = datetime.now().date()
        fecha_inicio = date(año, mes, 1)
        fecha_fin = min(hoy, date(año, mes, 28) + timedelta(days=4))
        
        # Calcular SPH para cada día y acumular
        ventas_acumuladas = 0
        horas_efectivas_acumuladas = 0.0
        
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            sph_diario = calcular_sph_diario(agente_id, fecha_actual, ventas_agentes, 
                                            registro_llamadas, horarios_agentes, 
                                            ausencias_agentes, festivos_data)
            
            # Obtener ventas y horas del día para acumular
            fecha_str = fecha_actual.strftime("%Y-%m-%d")
            
            # Ventas del día
            ventas_dia = 0
            if (agente_id in ventas_agentes and 
                fecha_str in ventas_agentes[agente_id].get("detalle_dias", {})):
                ventas_dia = ventas_agentes[agente_id]["detalle_dias"][fecha_str].get("ventas", 0)
            
            # Si no hay en ventas_agentes, buscar en registro_llamadas
            if ventas_dia == 0 and fecha_str in registro_llamadas:
                if agente_id in registro_llamadas[fecha_str]:
                    ventas_dia = registro_llamadas[fecha_str][agente_id].get("ventas", 0)
            
            ventas_acumuladas += ventas_dia
            
            # Horas efectivas del día
            horas_trabajadas = 0
            if agente_id in horarios_agentes:
                dia_semana = fecha_actual.strftime("%A")
                if dia_semana in horarios_agentes[agente_id]:
                    horas_trabajadas = obtener_horas_diarias(horarios_agentes[agente_id][dia_semana])
                else:
                    horas_trabajadas = 6.0
            else:
                horas_trabajadas = 6.0
            
            # Restar ausencias
            if agente_id in ausencias_agentes and fecha_str in ausencias_agentes[agente_id]:
                horas_perdidas = ausencias_agentes[agente_id][fecha_str].get("horas_perdidas", 0)
                horas_trabajadas = max(0, horas_trabajadas - horas_perdidas)
            
            # Solo días laborables
            from festivos_manager import es_festivo
            if fecha_actual.weekday() < 5 and not es_festivo(fecha_actual, festivos_data):
                horas_efectivas_acumuladas += horas_trabajadas * 0.83
            
            fecha_actual += timedelta(days=1)
        
        # Calcular SPH acumulado
        if horas_efectivas_acumuladas > 0:
            sph_acumulado = ventas_acumuladas / horas_efectivas_acumuladas
            return round(sph_acumulado, 4)
        else:
            return 0.0
        
    except Exception as e:
        print(f"Error calculando SPH acumulado para {agente_id} en {mes_key}: {e}")
        return 0.0