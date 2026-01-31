"""
agent_calculations.py
Funciones para calcular métricas de agentes
"""

import pandas as pd
from datetime import datetime, date, timedelta

def calcular_sph_diario(agente_id, fecha, ventas_agentes, registro_llamadas, 
                        horarios_agentes, ausencias_agentes, festivos_data):
    """Versión mejorada que maneja ausencias consolidadas"""
    try:
        from festivos_manager import es_festivo
        
        fecha_date = fecha if isinstance(fecha, date) else fecha.date()
        fecha_str = fecha_date.strftime("%Y-%m-%d")
        
        # Solo días laborables
        if fecha_date.weekday() >= 5 or es_festivo(fecha_date, festivos_data):
            return 0.0
        
        # 1. Obtener ventas del día
        ventas_dia = 0
        if (agente_id in ventas_agentes and 
            fecha_str in ventas_agentes[agente_id].get("detalle_dias", {})):
            ventas_dia = ventas_agentes[agente_id]["detalle_dias"][fecha_str].get("ventas", 0)
        
        if ventas_dia == 0 and fecha_str in registro_llamadas:
            if agente_id in registro_llamadas[fecha_str]:
                ventas_dia = registro_llamadas[fecha_str][agente_id].get("ventas", 0)
        
        # 2. Horas según horario
        horas_trabajadas = 6.0  # Valor por defecto
        if agente_id in horarios_agentes:
            dia_semana = fecha_date.strftime("%A")
            if dia_semana in horarios_agentes[agente_id]:
                horas_trabajadas = obtener_horas_diarias(horarios_agentes[agente_id][dia_semana])
        
        # 3. Restar ausencias específicas de este día
        if agente_id in ausencias_agentes and fecha_str in ausencias_agentes[agente_id]:
            horas_perdidas = ausencias_agentes[agente_id][fecha_str].get("horas_perdidas", 0)
            horas_trabajadas = max(0, horas_trabajadas - horas_perdidas)
        
        # 4. Calcular horas efectivas
        horas_efectivas = horas_trabajadas * 0.83
        
        if horas_efectivas > 0:
            return round(ventas_dia / horas_efectivas, 4)
        else:
            return 0.0
        
    except Exception as e:
        print(f"Error en calcular_sph_diario para {agente_id}: {e}")
        return 0.0

def calcular_sph_acumulado_mes(agente_id, mes_key, ventas_agentes, registro_llamadas, 
                               horarios_agentes, ausencias_agentes, festivos_data):
    """Calcula el SPH acumulado de un agente en un mes - VERSIÓN MEJORADA"""
    try:
        # Parsear mes_key (formato: "2024-01")
        año, mes = map(int, mes_key.split("-"))
        
        # Obtener todas las fechas del mes hasta hoy
        hoy = datetime.now().date()
        fecha_inicio = date(año, mes, 1)
        fecha_fin = min(hoy, date(año, mes, 28) + timedelta(days=4))
        
        # ============================================
        # NUEVO: Calcular horas totales de ausencia del mes
        # ============================================
        horas_ausencias_mes = 0
        ausencias_consolidadas = []
        
        if agente_id in ausencias_agentes:
            for fecha_str, datos_ausencia in ausencias_agentes[agente_id].items():
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
                    if fecha.year == año and fecha.month == mes:
                        horas = datos_ausencia.get("horas_perdidas", 0)
                        
                        # Verificar si es una ausencia consolidada
                        if datos_ausencia.get("es_consolidado_mensual", False):
                            # Es una ausencia consolidada del mes
                            horas_ausencias_mes += horas
                            ausencias_consolidadas.append({
                                "fecha": fecha_str,
                                "horas": horas,
                                "consolidada": True
                            })
                        else:
                            # Ausencia normal (por fecha específica)
                            # Se procesará en el bucle de días
                            pass
                except:
                    continue
        
        # ============================================
        # Calcular SPH para cada día y acumular
        # ============================================
        ventas_acumuladas = 0
        horas_efectivas_acumuladas = 0.0
        dias_laborables_contados = 0
        
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            fecha_str = fecha_actual.strftime("%Y-%m-%d")
            
            # Solo procesar días laborables
            from festivos_manager import es_festivo
            es_laborable = (fecha_actual.weekday() < 5 and not es_festivo(fecha_actual, festivos_data))
            
            if es_laborable:
                dias_laborables_contados += 1
                
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
                
                # Horas trabajadas según horario
                horas_trabajadas = 0
                if agente_id in horarios_agentes:
                    dia_semana = fecha_actual.strftime("%A")
                    if dia_semana in horarios_agentes[agente_id]:
                        horas_trabajadas = obtener_horas_diarias(horarios_agentes[agente_id][dia_semana])
                    else:
                        horas_trabajadas = 6.0
                else:
                    horas_trabajadas = 6.0
                
                # RESTAR AUSENCIAS ESPECÍFICAS DE ESTE DÍA
                if agente_id in ausencias_agentes and fecha_str in ausencias_agentes[agente_id]:
                    horas_perdidas = ausencias_agentes[agente_id][fecha_str].get("horas_perdidas", 0)
                    horas_trabajadas = max(0, horas_trabajadas - horas_perdidas)
                
                # Calcular horas efectivas (83% de productividad)
                horas_efectivas = horas_trabajadas * 0.83
                horas_efectivas_acumuladas += horas_efectivas
            
            fecha_actual += timedelta(days=1)
        
        # ============================================
        # NUEVO: Distribuir horas de ausencias consolidadas
        # ============================================
        if ausencias_consolidadas and dias_laborables_contados > 0:
            # Calcular horas de ausencia por día laborable
            horas_ausencia_por_dia = horas_ausencias_mes / dias_laborables_contados
            
            # Ajustar horas efectivas acumuladas
            # Cada día laborable pierde horas_ausencia_por_dia * 0.83 de horas efectivas
            horas_efectivas_perdidas = horas_ausencias_mes * 0.83
            horas_efectivas_acumuladas = max(0, horas_efectivas_acumuladas - horas_efectivas_perdidas)
        
        # ============================================
        # Calcular SPH acumulado
        # ============================================
        if horas_efectivas_acumuladas > 0:
            sph_acumulado = ventas_acumuladas / horas_efectivas_acumuladas
            return round(sph_acumulado, 4)
        else:
            return 0.0
        
    except Exception as e:
        print(f"Error calculando SPH acumulado para {agente_id} en {mes_key}: {e}")
        return 0.0