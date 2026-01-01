# monitorizacion_utils.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import re

def analizar_pdf_monitorizacion(uploaded_file):
    """
    Analiza el PDF de monitorización y extrae los datos
    Para desarrollo, simulamos la extracción
    """
    # Esta función simula el análisis del PDF
    # En producción, implementarías OCR aquí
    
    datos_extraidos = {
        'id_empleado': 1316,
        'fecha_monitorizacion': '2024-12-29',
        'nota_global': 93.5,
        'objetivo': 85.0,
        'experiencia': 85.0,
        'comunicacion': 100.0,
        'deteccion': 100.0,
        'habilidades_venta': 50.0,
        'resolucion_objeciones': 100.0,
        'cierre_contacto': 100.0,
        'gestion_venta': 100.0,
        'proceso_venta': 100.0,
        'verificacion_venta': None,
        'feedback': "LOPD SI. Buena entrada y buen sondeo inicial...",
        'puntos_clave': ["LOPD", "Cierre de venta", "Argumentación"]
    }
    
    return datos_extraidos

def guardar_monitorizacion_completa(monitorizacion_data, supervisor_id):
    """Guarda una monitorización completa"""
    from database import agregar_monitorizacion
    
    try:
        # Validar datos requeridos
        if 'id_empleado' not in monitorizacion_data:
            st.error("ID de empleado es requerido")
            return False
        
        # Convertir campos numéricos
        campos_numericos = ['nota_global', 'objetivo', 'experiencia', 'comunicacion',
                          'deteccion', 'habilidades_venta', 'resolucion_objeciones',
                          'cierre_contacto', 'gestion_venta', 'proceso_venta']
        
        for campo in campos_numericos:
            if campo in monitorizacion_data and monitorizacion_data[campo] is not None:
                try:
                    monitorizacion_data[campo] = float(monitorizacion_data[campo])
                except:
                    monitorizacion_data[campo] = 0.0
        
        # Agregar metadata
        monitorizacion_data['supervisor_id'] = supervisor_id
        monitorizacion_data['fecha_creacion'] = datetime.now().isoformat()
        
        # Calcular fecha próxima (14 días después)
        if 'fecha_monitorizacion' in monitorizacion_data:
            try:
                fecha_actual = datetime.strptime(monitorizacion_data['fecha_monitorizacion'], '%Y-%m-%d')
                fecha_proxima = fecha_actual + timedelta(days=14)
                monitorizacion_data['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
            except:
                fecha_proxima = datetime.now() + timedelta(days=14)
                monitorizacion_data['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
        
        # Guardar
        monitorizacion_id = agregar_monitorizacion(monitorizacion_data)
        
        if monitorizacion_id:
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Error al guardar monitorización: {str(e)}")
        return False

def mostrar_monitorizacion_agente(usuario_id):
    """Muestra la monitorización del agente en su panel"""
    from database import obtener_ultima_monitorizacion_empleado
    
    ultima_mon = obtener_ultima_monitorizacion_empleado(usuario_id)
    
    if not ultima_mon:
        return False
    
    st.markdown("---")
    st.subheader("📊 Tu Última Monitorización")
    
    # Información principal
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nota = ultima_mon.get('nota_global', 0)
        objetivo = ultima_mon.get('objetivo', 85)
        st.metric("Nota Global", f"{nota}%", 
                 delta=f"{nota - objetivo:.1f}%" if objetivo else None)
    
    with col2:
        fecha = ultima_mon.get('fecha_monitorizacion', '')
        st.metric("Fecha", fecha)
    
    with col3:
        fecha_prox = ultima_mon.get('fecha_proxima_monitorizacion', '')
        if fecha_prox:
            fecha_prox_dt = datetime.strptime(fecha_prox, '%Y-%m-%d')
            hoy = datetime.now().date()
            dias_restantes = (fecha_prox_dt.date() - hoy).days
            st.metric("Próxima", fecha_prox, delta=f"{dias_restantes} días")
    
    # Puntuaciones por área
    st.write("#### 📈 Puntuaciones por Área")
    
    areas = [
        ("Experiencia", ultima_mon.get('experiencia')),
        ("Comunicación", ultima_mon.get('comunicacion')),
        ("Detección", ultima_mon.get('deteccion')),
        ("Habilidades de Venta", ultima_mon.get('habilidades_venta')),
        ("Resolución Objeciones", ultima_mon.get('resolucion_objeciones')),
        ("Cierre Contacto", ultima_mon.get('cierre_contacto')),
        ("Gestión Venta", ultima_mon.get('gestion_venta')),
        ("Proceso Venta", ultima_mon.get('proceso_venta'))
    ]
    
    cols = st.columns(3)
    for idx, (area, puntaje) in enumerate(areas):
        if puntaje is not None:
            with cols[idx % 3]:
                progress = puntaje / 100
                color = "green" if puntaje >= 80 else "orange" if puntaje >= 70 else "red"
                st.progress(progress)
                st.caption(f"{area}: {puntaje}%")
    
    # Feedback y plan de acción
    feedback = ultima_mon.get('feedback', '')
    plan_accion = ultima_mon.get('plan_accion', '')
    puntos_clave = ultima_mon.get('puntos_clave', [])
    
    if feedback:
        with st.expander("📝 Feedback recibido", expanded=True):
            st.write(feedback)
    
    if plan_accion:
        with st.expander("🎯 Plan de acción", expanded=True):
            st.write(plan_accion)
    
    if puntos_clave:
        st.write("#### 🔑 Puntos clave a mejorar:")
        for punto in puntos_clave:
            st.write(f"- {punto}")
    
    return True