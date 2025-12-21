import pandas as pd
import streamlit as st
from config import (
    ALQUILER_CONTADOR, PACK_IBERDROLA, IMPUESTO_ELECTRICO,
    DESCUENTO_PRIMERA_FACTURA, IVA, DIAS_ANUAL
)
from database import cargar_configuracion_usuarios

def determinar_rl_gas(consumo_anual):
    """Determina automáticamente el RL según consumo anual"""
    if consumo_anual <= 5000:
        return "RL1"
    elif consumo_anual <= 15000:
        return "RL2"
    else:
        return "RL3"

def calcular_pmg(tiene_pmg, es_canarias=False):
    """Calcula el coste del PMG con/sin IVA"""
    # Importar las constantes de PMG
    from config import PMG_COSTE, PMG_IVA
    
    if not tiene_pmg:
        return 0
    
    coste_pmg = PMG_COSTE
    if not es_canarias:
        coste_pmg *= (1 + PMG_IVA)
    
    return coste_pmg * 12

def calcular_coste_gas_completo(plan, consumo_kwh, tiene_pmg=True, es_canarias=False):
    """Calcula coste total de gas incluyendo PMG e IVA"""
    # Importar las constantes de PMG
    from config import PMG_IVA
    
    if tiene_pmg:
        termino_fijo = plan["termino_fijo_con_pmg"]
        termino_variable = plan["termino_variable_con_pmg"]
    else:
        termino_fijo = plan["termino_fijo_sin_pmg"]
        termino_variable = plan["termino_variable_sin_pmg"]
    
    coste_fijo = termino_fijo * 12
    coste_variable = consumo_kwh * termino_variable
    coste_gas_sin_iva = coste_fijo + coste_variable
    
    if not es_canarias:
        coste_gas_con_iva = coste_gas_sin_iva * (1 + PMG_IVA)
    else:
        coste_gas_con_iva = coste_gas_sin_iva
    
    coste_pmg = calcular_pmg(tiene_pmg, es_canarias)
    
    return coste_gas_con_iva + coste_pmg

def calcular_plan_ahorro_automatico(plan, consumo, dias, tiene_pi=False, es_anual=False):
    """Calcula el coste para el Plan Ahorro Automático"""
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
        'dias_precio_normal': dias_precio_normal,
        'consumo_bajo_precio': consumo_bajo_precio,
        'consumo_precio_normal': consumo_precio_normal
    }

def filtrar_planes_por_usuario(df_planes, username, tipo_plan="luz"):
    """Filtra los planes según la configuración del usuario"""
    if df_planes.empty:
        return df_planes
    
    usuarios_config = cargar_configuracion_usuarios()
    from database import cargar_config_sistema
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    if username not in usuarios_config:
        return df_planes[df_planes['activo'] == True]
    
    config_usuario = usuarios_config[username]
    grupo_usuario = config_usuario.get('grupo')
    
    if not grupo_usuario or grupo_usuario not in grupos:
        planes_permitidos = config_usuario.get(f"planes_{tipo_plan}", [])
    else:
        permisos_grupo = grupos[grupo_usuario]
        planes_permitidos = permisos_grupo.get(f"planes_{tipo_plan}", [])
    
    if not planes_permitidos:
        return df_planes[df_planes['activo'] == True]
    
    if planes_permitidos == "TODOS":
        return df_planes[df_planes['activo'] == True]
    
    return df_planes[
        (df_planes['plan'].isin(planes_permitidos)) & 
        (df_planes['activo'] == True)
    ]