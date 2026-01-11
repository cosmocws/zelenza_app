import json
import os
from datetime import datetime, date
from typing import List, Dict
import streamlit as st

def cargar_festivos():
    """Carga los festivos desde el archivo JSON"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo_festivos = 'data/festivos.json'
        
        if os.path.exists(archivo_festivos):
            with open(archivo_festivos, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Crear estructura inicial con algunos festivos nacionales de España
            festivos_base = {
                "festivos": {
                    "2024": [
                        "2024-01-01",  # Año Nuevo
                        "2024-01-06",  # Reyes
                        "2024-03-29",  # Viernes Santo
                        "2024-05-01",  # Día del Trabajo
                        "2024-08-15",  # Asunción
                        "2024-10-12",  # Hispanidad
                        "2024-11-01",  # Todos los Santos
                        "2024-12-06",  # Constitución
                        "2024-12-25",  # Navidad
                    ],
                    "2025": [
                        "2024-01-01",  # Año Nuevo
                        "2024-01-06",  # Reyes
                        "2024-04-18",  # Viernes Santo
                        "2024-05-01",  # Día del Trabajo
                        "2024-08-15",  # Asunción
                        "2024-10-12",  # Hispanidad
                        "2024-11-01",  # Todos los Santos
                        "2024-12-06",  # Constitución
                        "2024-12-25",  # Navidad
                    ]
                },
                "festivos_regionales": {},  # Para festivos por comunidad
                "festivos_personalizados": {},  # Para festivos específicos de la empresa
                "metadata": {
                    "fecha_creacion": datetime.now().isoformat(),
                    "ultima_actualizacion": datetime.now().isoformat(),
                    "pais": "España"
                }
            }
            
            guardar_festivos(festivos_base)
            return festivos_base
            
    except Exception as e:
        st.error(f"Error cargando festivos: {e}")
        return {"festivos": {}, "festivos_regionales": {}, "festivos_personalizados": {}, "metadata": {}}

def guardar_festivos(festivos_data):
    """Guarda los festivos en archivo JSON"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo_festivos = 'data/festivos.json'
        
        # Actualizar metadata
        festivos_data["metadata"]["ultima_actualizacion"] = datetime.now().isoformat()
        
        with open(archivo_festivos, 'w', encoding='utf-8') as f:
            json.dump(festivos_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando festivos: {e}")
        return False

def es_festivo(fecha: date, festivos_data=None) -> bool:
    """Verifica si una fecha es festivo"""
    if festivos_data is None:
        festivos_data = cargar_festivos()
    
    fecha_str = fecha.strftime("%Y-%m-%d")
    año = str(fecha.year)
    
    # Verificar festivos nacionales
    if año in festivos_data.get("festivos", {}):
        if fecha_str in festivos_data["festivos"][año]:
            return True
    
    # Verificar festivos regionales (si se implementan)
    # Verificar festivos personalizados
    if "festivos_personalizados" in festivos_data:
        for categoria, festivos in festivos_data["festivos_personalizados"].items():
            if fecha_str in festivos:
                return True
    
    return False

def obtener_festivos_año(año: int, festivos_data=None) -> List[str]:
    """Obtiene todos los festivos de un año específico"""
    if festivos_data is None:
        festivos_data = cargar_festivos()
    
    año_str = str(año)
    festivos = []
    
    # Festivos nacionales
    if año_str in festivos_data.get("festivos", {}):
        festivos.extend(festivos_data["festivos"][año_str])
    
    # Festivos personalizados
    if "festivos_personalizados" in festivos_data:
        for categoria, lista_festivos in festivos_data["festivos_personalizados"].items():
            for festivo in lista_festivos:
                if festivo.startswith(año_str):
                    festivos.append(festivo)
    
    return sorted(list(set(festivos)))

def agregar_festivo(fecha: date, tipo="nacional", descripcion=""):
    """Agrega un nuevo festivo"""
    festivos_data = cargar_festivos()
    fecha_str = fecha.strftime("%Y-%m-%d")
    año = str(fecha.year)
    
    if tipo == "nacional":
        if año not in festivos_data["festivos"]:
            festivos_data["festivos"][año] = []
        
        if fecha_str not in festivos_data["festivos"][año]:
            festivos_data["festivos"][año].append(fecha_str)
            festivos_data["festivos"][año].sort()
    
    elif tipo == "personalizado":
        if "festivos_personalizados" not in festivos_data:
            festivos_data["festivos_personalizados"] = {}
        
        if "empresa" not in festivos_data["festivos_personalizados"]:
            festivos_data["festivos_personalizados"]["empresa"] = []
        
        festivo_info = {
            "fecha": fecha_str,
            "descripcion": descripcion,
            "tipo": "empresa"
        }
        
        festivos_data["festivos_personalizados"]["empresa"].append(festivo_info)
    
    return guardar_festivos(festivos_data)

def eliminar_festivo(fecha_str: str, año: str):
    """Elimina un festivo"""
    festivos_data = cargar_festivos()
    
    # Intentar eliminar de festivos nacionales
    if año in festivos_data.get("festivos", {}):
        if fecha_str in festivos_data["festivos"][año]:
            festivos_data["festivos"][año].remove(fecha_str)
    
    # Intentar eliminar de festivos personalizados
    if "festivos_personalizados" in festivos_data:
        for categoria, festivos in festivos_data["festivos_personalizados"].items():
            if isinstance(festivos, list):
                # Para listas simples de fechas
                if fecha_str in festivos:
                    festivos.remove(fecha_str)
            elif isinstance(festivos, list) and len(festivos) > 0 and isinstance(festivos[0], dict):
                # Para listas de diccionarios
                festivos_data["festivos_personalizados"][categoria] = [
                    f for f in festivos if f.get("fecha") != fecha_str
                ]
    
    return guardar_festivos(festivos_data)