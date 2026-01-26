import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import streamlit as st

# ==============================================
# FUNCIONES DE HORARIOS
# ==============================================

def cargar_horarios_agentes() -> Dict:
    """Carga los horarios de los agentes desde JSON"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_schedules.json'
        
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Asegurar que todos los agentes tengan todos los días
                dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
                for agente_id, horario in data.items():
                    for dia in dias_semana:
                        if dia not in horario:
                            horario[dia] = {"inicio": "15:00", "fin": "21:00"}
                return data
        else:
            # Estructura inicial vacía
            horarios_base = {}
            guardar_horarios_agentes(horarios_base)
            return horarios_base
            
    except Exception as e:
        st.error(f"Error cargando horarios: {e}")
        return {}

def guardar_horarios_agentes(horarios_data: Dict) -> bool:
    """Guarda los horarios de agentes en JSON"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_schedules.json'
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(horarios_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando horarios: {e}")
        return False

def crear_horario_por_defecto() -> Dict:
    """Crea un horario por defecto (de 15:00 a 21:00 todos los días)"""
    dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    return {
        dia: {"inicio": "15:00", "fin": "21:00"}
        for dia in dias_semana
    }

def obtener_horas_diarias(horario_dia: Dict) -> float:
    """Calcula las horas trabajadas en un día específico"""
    try:
        inicio = datetime.strptime(horario_dia["inicio"], "%H:%M")
        fin = datetime.strptime(horario_dia["fin"], "%H:%M")
        
        # Manejar casos donde fin sea al día siguiente
        if fin < inicio:
            fin += timedelta(days=1)
        
        diferencia = fin - inicio
        return diferencia.total_seconds() / 3600  # Convertir a horas
    except:
        return 0

# ==============================================
# FUNCIONES DE AUSENCIAS
# ==============================================

def cargar_ausencias_agentes() -> Dict:
    """Carga las ausencias de los agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_absences.json'
        
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            ausencias_base = {}
            guardar_ausencias_agentes(ausencias_base)
            return ausencias_base
            
    except Exception as e:
        st.error(f"Error cargando ausencias: {e}")
        return {}

def guardar_ausencias_agentes(ausencias_data: Dict) -> bool:
    """Guarda las ausencias de agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_absences.json'
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(ausencias_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando ausencias: {e}")
        return False

# ==============================================
# FUNCIONES DE MÉTRICAS (SPH Y OBJETIVOS)
# ==============================================

def cargar_metricas_agentes() -> Dict:
    """Carga las métricas de los agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_metrics.json'
        
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            metricas_base = {}
            guardar_metricas_agentes(metricas_base)
            return metricas_base
            
    except Exception as e:
        st.error(f"Error cargando métricas: {e}")
        return {}

def guardar_metricas_agentes(metricas_data: Dict) -> bool:
    """Guarda las métricas de agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_metrics.json'
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(metricas_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando métricas: {e}")
        return False

# ==============================================
# FUNCIONES DE CÁLCULO DE OBJETIVOS
# ==============================================

def calcular_horas_mes(agente_id: str, año: int, mes: int, 
                       horarios: Dict, ausencias: Dict, festivos_data: Dict) -> float:
    """Calcula las horas totales que trabaja un agente en un mes específico"""
    from festivos_manager import es_festivo
    
    if agente_id not in horarios:
        return 0
    
    horas_totales = 0
    dias_semana_map = {
        0: "Lunes", 1: "Martes", 2: "Miercoles",
        3: "Jueves", 4: "Viernes"
    }
    
    # Iterar por todos los días del mes
    fecha_actual = date(año, mes, 1)
    ultimo_dia_mes = (fecha_actual.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    while fecha_actual <= ultimo_dia_mes:
        # Solo considerar días laborables (Lunes a Viernes)
        if fecha_actual.weekday() < 5:  # 0=Lunes, 4=Viernes
            dia_semana = dias_semana_map[fecha_actual.weekday()]
            
            # Verificar si es festivo
            if es_festivo(fecha_actual, festivos_data):
                pass  # No sumar horas si es festivo
            else:
                # Verificar si el agente está ausente ese día
                fecha_str = fecha_actual.strftime("%Y-%m-%d")
                if (agente_id in ausencias and 
                    fecha_str in ausencias[agente_id]):
                    pass  # No sumar horas si está ausente
                else:
                    # Sumar horas del día
                    if dia_semana in horarios[agente_id]:
                        horas_dia = obtener_horas_diarias(horarios[agente_id][dia_semana])
                        horas_totales += horas_dia
        
        fecha_actual += timedelta(days=1)
    
    return horas_totales

def calcular_objetivo_mes(agente_id: str, año: int, mes: int, 
                          sph: float, horarios: Dict, 
                          ausencias: Dict, festivos_data: Dict) -> Dict:
    """Calcula el objetivo mensual para un agente"""
    
    horas_totales = calcular_horas_mes(agente_id, año, mes, horarios, ausencias, festivos_data)
    
    # Calcular horas efectivas (83%)
    horas_efectivas = horas_totales * 0.83
    
    # Calcular objetivo base
    objetivo_decimal = horas_efectivas * sph
    
    # Redondear según regla (0.51 para arriba)
    if objetivo_decimal - int(objetivo_decimal) >= 0.51:
        objetivo_final = int(objetivo_decimal) + 1
    else:
        objetivo_final = int(objetivo_decimal)
    
    # Contar días ausentes
    fecha_actual = date(año, mes, 1)
    ultimo_dia_mes = (fecha_actual.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    dias_ausentes = 0
    
    while fecha_actual <= ultimo_dia_mes:
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        if (agente_id in ausencias and 
            fecha_str in ausencias[agente_id] and
            fecha_actual.weekday() < 5):  # Solo días laborables
            dias_ausentes += 1
        fecha_actual += timedelta(days=1)
    
    return {
        "horas_totales_mes": round(horas_totales, 2),
        "horas_efectivas": round(horas_efectivas, 2),
        "sph": sph,
        "objetivo_calculado": objetivo_final,
        "dias_ausentes": dias_ausentes,
        "mes": f"{año}-{mes:02d}"
    }

# ==============================================
# FUNCIONES DE CALENDARIO VISUAL
# ==============================================

def obtener_calendario_mes_agente(agente_id: str, año: int, mes: int, 
                                  horarios: Dict, ausencias: Dict, festivos_data: Dict) -> List[Dict]:
    """Genera un calendario visual para un agente"""
    from festivos_manager import es_festivo
    
    dias_semana_map = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    
    # Crear calendario
    fecha_actual = date(año, mes, 1)
    ultimo_dia_mes = (fecha_actual.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    calendario = []
    while fecha_actual <= ultimo_dia_mes:
        dia_info = {
            "fecha": fecha_actual,
            "dia_semana": fecha_actual.weekday(),
            "es_laborable": fecha_actual.weekday() < 5,
            "es_festivo": es_festivo(fecha_actual, festivos_data),
            "esta_ausente": False,
            "horas": 0
        }
        
        # Verificar si es día laborable
        if dia_info["es_laborable"] and not dia_info["es_festivo"]:
            dia_semana_nombre = dias_semana_map[fecha_actual.weekday()]
            
            # Verificar ausencia
            fecha_str = fecha_actual.strftime("%Y-%m-%d")
            if (agente_id in ausencias and 
                fecha_str in ausencias[agente_id]):
                dia_info["esta_ausente"] = True
                dia_info["motivo_ausencia"] = ausencias[agente_id][fecha_str].get("motivo", "Ausencia")
            elif agente_id in horarios and dia_semana_nombre in horarios[agente_id]:
                # Calcular horas del día
                dia_info["horas"] = obtener_horas_diarias(horarios[agente_id][dia_semana_nombre])
                dia_info["horario"] = horarios[agente_id][dia_semana_nombre]
        
        calendario.append(dia_info)
        fecha_actual += timedelta(days=1)
    
    return calendario

# ==============================================
# FUNCIONES UTILITARIAS
# ==============================================

def obtener_dias_laborables_mes(año: int, mes: int, festivos_data: Dict) -> int:
    """Cuenta los días laborables en un mes (excluyendo festivos)"""
    from festivos_manager import es_festivo
    
    fecha_actual = date(año, mes, 1)
    ultimo_dia_mes = (fecha_actual.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    dias_laborables = 0
    while fecha_actual <= ultimo_dia_mes:
        if fecha_actual.weekday() < 5:  # Lunes a Viernes
            if not es_festivo(fecha_actual, festivos_data):
                dias_laborables += 1
        fecha_actual += timedelta(days=1)
    
    return dias_laborables

def calcular_horas_por_dia_agente(agente_id: str, horarios: Dict) -> Dict:
    """Calcula las horas por día para un agente"""
    dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    resultado = {}
    
    if agente_id in horarios:
        for dia in dias_semana:
            if dia in horarios[agente_id]:
                resultado[dia] = obtener_horas_diarias(horarios[agente_id][dia])
    
    return resultado

def obtener_agentes_con_horarios(usuarios_config: Dict) -> List[str]:
    """Obtiene la lista de agentes que pueden tener horarios"""
    agentes = []
    for username, config in usuarios_config.items():
        if username == "admin":
            continue
        # Considerar cualquier usuario como potencial agente
        agentes.append(username)
    return agentes