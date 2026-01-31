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
    
# Añadir al final del archivo, antes del cierre

# ==============================================
# FUNCIONES DE VENTAS REALES
# ==============================================

def cargar_ventas_agentes() -> Dict:
    """Carga las ventas reales de los agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_sales.json'
        
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            ventas_base = {}
            guardar_ventas_agentes(ventas_base)
            return ventas_base
            
    except Exception as e:
        st.error(f"Error cargando ventas: {e}")
        return {}

def guardar_ventas_agentes(ventas_data: Dict) -> bool:
    """Guarda las ventas de agentes"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = 'data/agent_sales.json'
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(ventas_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando ventas: {e}")
        return False

def actualizar_ventas_agente(agente_id: str, fecha_str: str, ventas_reales: int):
    """Actualiza las ventas reales de un agente para una fecha específica"""
    try:
        ventas = cargar_ventas_agentes()
        
        # Parsear la fecha para obtener mes
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        mes_key = f"{fecha.year}-{fecha.month:02d}"
        
        if agente_id not in ventas:
            ventas[agente_id] = {}
        
        if mes_key not in ventas[agente_id]:
            ventas[agente_id][mes_key] = {
                "ventas_reales": 0,
                "detalle_dias": {}
            }
        
        # Sumar ventas al mes
        ventas[agente_id][mes_key]["ventas_reales"] += ventas_reales
        
        # Guardar detalle por día
        if "detalle_dias" not in ventas[agente_id][mes_key]:
            ventas[agente_id][mes_key]["detalle_dias"] = {}
        
        if fecha_str not in ventas[agente_id][mes_key]["detalle_dias"]:
            ventas[agente_id][mes_key]["detalle_dias"][fecha_str] = 0
        
        ventas[agente_id][mes_key]["detalle_dias"][fecha_str] += ventas_reales
        
        guardar_ventas_agentes(ventas)
        return True
    except Exception as e:
        st.error(f"Error actualizando ventas: {e}")
        return False

def obtener_resumen_agente_mes(agente_id: str, año: int, mes: int, 
                               horarios: Dict, ausencias: Dict, 
                               metricas: Dict, ventas: Dict,
                               festivos_data: Dict) -> Dict:
    """Obtiene un resumen completo del agente para un mes específico"""
    try:
        # Calcular objetivo
        sph_objetivo = metricas.get(agente_id, {}).get(f"{año}-{mes:02d}", {}).get("sph", 0.07)
        
        objetivo_info = calcular_objetivo_mes(agente_id, año, mes, sph_objetivo,
                                              horarios, ausencias, festivos_data)
        
        # Obtener ventas reales del mes
        ventas_mes_key = f"{año}-{mes:02d}"
        ventas_reales = 0
        if agente_id in ventas and ventas_mes_key in ventas[agente_id]:
            ventas_reales = ventas[agente_id][ventas_mes_key].get("ventas_reales", 0)
        
        # Calcular SPH real
        horas_efectivas = objetivo_info.get("horas_efectivas", 0)
        sph_real = 0
        if horas_efectivas > 0 and ventas_reales > 0:
            sph_real = ventas_reales / horas_efectivas
        
        # Calcular porcentaje de objetivo
        porcentaje_objetivo = 0
        objetivo_final = objetivo_info.get("objetivo_calculado", 0)
        if objetivo_final > 0:
            porcentaje_objetivo = (ventas_reales / objetivo_final) * 100
        
        # Calcular diferencia y estado
        diferencia = ventas_reales - objetivo_final
        
        if ventas_reales >= objetivo_final:
            estado = "✅ Cumple"
            color_estado = "green"
        elif ventas_reales >= objetivo_final * 0.8:
            estado = "⚠️ Cerca"
            color_estado = "orange"
        else:
            estado = "❌ Por debajo"
            color_estado = "red"
        
        return {
            "agente_id": agente_id,
            "mes": ventas_mes_key,
            "sph_objetivo": sph_objetivo,
            "sph_real": round(sph_real, 4),
            "horas_totales": round(objetivo_info.get("horas_totales_mes", 0), 1),
            "horas_efectivas": round(objetivo_info.get("horas_efectivas", 0), 1),
            "objetivo": objetivo_final,
            "ventas_reales": ventas_reales,
            "diferencia": diferencia,
            "porcentaje_objetivo": round(porcentaje_objetivo, 1),
            "dias_ausentes": objetivo_info.get("dias_ausentes", 0),
            "estado": estado,
            "color_estado": color_estado
        }
        
    except Exception as e:
        print(f"Error en obtener_resumen_agente_mes para {agente_id}: {e}")
        return None

# ==============================================
# FUNCIONES DE SINCRONIZACIÓN AUTOMÁTICA
# ==============================================

def sincronizar_ventas_con_github():
    """Sincroniza el archivo de ventas con GitHub"""
    try:
        # Intentar importar el módulo de GitHub
        try:
            from github_sync_simple import GitHubSyncSimple
        except ImportError:
            # Intentar la otra versión
            from github_api_sync import GitHubSync
        
        ventas = cargar_ventas_agentes()
        
        # Guardar archivo temporalmente
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as tmp:
            json.dump(ventas, tmp, indent=4, ensure_ascii=False)
            temp_path = tmp.name
        
        try:
            # Intentar con GitHubSyncSimple primero
            try:
                sync = GitHubSyncSimple()
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                success, message = sync.upload_file(
                    "data/agent_sales.json",
                    content,
                    "Sync automática de ventas de agentes"
                )
                
                if success:
                    print(f"✅ Ventas sincronizadas: {message}")
                    return True
                else:
                    print(f"❌ Error: {message}")
                    return False
                    
            except Exception as e1:
                print(f"Primer método falló: {e1}")
                
                # Intentar con GitHubSync
                try:
                    sync = GitHubSync()
                    success = sync.upload_file(
                        temp_path,
                        "data/agent_sales.json",
                        "Sync automática de ventas de agentes"
                    )
                    
                    if success:
                        print("✅ Ventas sincronizadas con GitHubSync")
                        return True
                    else:
                        print("❌ Error con GitHubSync")
                        return False
                        
                except Exception as e2:
                    print(f"Segundo método también falló: {e2}")
                    return False
                    
        finally:
            # Limpiar archivo temporal
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"Error general en sincronizar_ventas_con_github: {e}")
        return False