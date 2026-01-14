import streamlit as st
import pandas as pd
import os
from datetime import datetime
import tempfile
import io
from database import cargar_registro_llamadas, guardar_registro_llamadas, cargar_super_users
import json
import hashlib


def calcular_hash_registro(registro):
    """Calcula un hash único para un registro"""
    datos_str = f"{registro['agente']}_{registro['fecha']}_{registro['tiempo_conversacion']}_{registro.get('ventas_totales', 0)}"
    return hashlib.md5(datos_str.encode()).hexdigest()


def analizar_csv_llamadas(uploaded_file):
    """
    Analiza un CSV de llamadas con la estructura específica de Zelenza
    """
    # Guardar el archivo en session_state para persistencia
    if uploaded_file is not None:
        st.session_state.uploaded_file_data = uploaded_file.getvalue()
        st.session_state.uploaded_file_name = uploaded_file.name
    
    # Usar datos de session_state si available
    if 'uploaded_file_data' in st.session_state and uploaded_file is None:
        uploaded_file = io.BytesIO(st.session_state.uploaded_file_data)
        uploaded_file.name = st.session_state.get('uploaded_file_name', 'archivo.csv')
    
    if uploaded_file is None:
        st.error("❌ No hay archivo cargado. Por favor, sube un archivo CSV.")
        return None
    
    # Crear un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Leer archivo para detectar separador
        with open(tmp_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
        
        # Detectar separador
        separator = '\t' if '\t' in first_line else ','
        if separator == '\t':
            st.info("📄 Archivo detectado como separado por TABULACIONES")
        
        # Leer el archivo
        df = pd.read_csv(tmp_path, sep=separator, encoding='utf-8')
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Verificar columnas necesarias
        columnas_requeridas = ['agente', 'tiempo_conversacion', 'resultado_elec', 
                               'resultado_gas', 'fecha', 'hora', 'campanya']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            st.error(f"❌ Faltan columnas: {', '.join(columnas_faltantes)}")
            st.info("Columnas encontradas:")
            for col in df.columns:
                st.write(f"- {col}")
            return None
        
        # Asegurar columnas de motivo
        df['motivo_elec'] = df.get('motivo_elec', '')
        df['motivo_gas'] = df.get('motivo_gas', '')
        
        # Limpiar datos
        df['campanya'] = df['campanya'].astype(str).str.strip()
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.dropna(subset=['fecha'])
        
        # Añadir hash único
        df['hash'] = df.apply(calcular_hash_registro, axis=1)
        
        # Mostrar campañas encontradas
        campanyas_unicas = df['campanya'].unique()
        st.success(f"✅ **Campañas detectadas ({len(campanyas_unicas)}):**")
        
        for i, camp in enumerate(campanyas_unicas[:10]):
            st.write(f"{i+1}. {camp}")
        
        if len(campanyas_unicas) > 10:
            st.info(f"... y {len(campanyas_unicas) - 10} más")
        
        # Guardar datos en session_state
        st.session_state.df_original = df
        st.session_state.campanyas_unicas = campanyas_unicas
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al leer archivo: {str(e)}")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def contar_ventas_resultado(resultado_str):
    """Cuenta ventas en un resultado (compatibilidad)"""
    if pd.isna(resultado_str):
        return 0
    
    resultado = str(resultado_str).upper()
    
    if 'PENDIENTE SMS' in resultado:
        return 0
    
    if 'UTIL POSITIVO' in resultado:
        if ('LUZ' in resultado and 'GAS' in resultado) or ('DÚO' in resultado or 'DUO' in resultado):
            return 2
        else:
            return 1
    
    return 0


def detectar_pendientes_sms_mejorado(row):
    """Detecta si hay ventas pendientes de SMS en resultado o motivo"""
    ventas_pendientes = 0
    
    # Revisar electricidad
    resultado_elec = str(row.get('resultado_elec', '')).upper() if pd.notna(row.get('resultado_elec')) else ''
    motivo_elec = str(row.get('motivo_elec', '')).upper() if pd.notna(row.get('motivo_elec')) else ''
    
    # Revisar gas
    resultado_gas = str(row.get('resultado_gas', '')).upper() if pd.notna(row.get('resultado_gas')) else ''
    motivo_gas = str(row.get('motivo_gas', '')).upper() if pd.notna(row.get('motivo_gas')) else ''
    
    # Función para verificar si hay PENDIENTE SMS
    def tiene_pendiente_sms(resultado, motivo):
        return 'PENDIENTE SMS' in resultado or 'PENDIENTE SMS' in motivo
    
    # Contar ventas pendientes en electricidad
    if tiene_pendiente_sms(resultado_elec, motivo_elec):
        if ('LUZ' in resultado_elec and 'GAS' in resultado_elec) or ('DÚO' in resultado_elec or 'DUO' in resultado_elec):
            ventas_pendientes += 2
        else:
            ventas_pendientes += 1
    
    # Contar ventas pendientes en gas
    if tiene_pendiente_sms(resultado_gas, motivo_gas) and ventas_pendientes < 2:
        ventas_pendientes += 1
    
    return ventas_pendientes > 0, ventas_pendientes


def contar_ventas_resultado_mejorado(resultado_str, motivo_str=None):
    """Cuenta ventas en un resultado, considerando PENDIENTE SMS en motivo"""
    if pd.isna(resultado_str):
        return 0
    
    resultado = str(resultado_str).upper()
    motivo = str(motivo_str).upper() if motivo_str and pd.notna(motivo_str) else ''
    
    if 'PENDIENTE SMS' in resultado or 'PENDIENTE SMS' in motivo:
        return 0
    
    if 'UTIL POSITIVO' in resultado:
        if ('LUZ' in resultado and 'GAS' in resultado) or ('DÚO' in resultado or 'DUO' in resultado):
            return 2
        else:
            return 1
    
    return 0

def verificar_si_procesada(hash_registro):
    """Verifica si una alerta ya fue procesada"""
    try:
        from database import cargar_alertas_sms
        alertas = cargar_alertas_sms()
        
        alerta_id = f"sms_{hash_registro}"
        return alerta_id in alertas
        
    except:
        return False

def mapear_agente_a_sistema(agente_csv, super_users_config):
    """
    Mapea un agente del CSV al sistema usando la misma lógica que la importación
    """
    agentes_sistema = super_users_config.get("agentes", {})

    # Preparar búsqueda flexible (igual que en importar_datos_a_registro)
    busqueda_agentes = {}

    for agent_id in agentes_sistema.keys():
        agent_id_str = str(agent_id).strip().upper()
        
        # Variantes de búsqueda
        busqueda_agentes[agent_id_str] = agent_id
        
        if len(agent_id_str) >= 4:
            busqueda_agentes[agent_id_str[-4:]] = agent_id
        
        if agent_id_str.startswith('TZS'):
            busqueda_agentes[agent_id_str[3:]] = agent_id
        
        solo_numeros = ''.join(filter(str.isdigit, agent_id_str))
        if solo_numeros and solo_numeros != agent_id_str:
            busqueda_agentes[solo_numeros] = agent_id

    # También buscar por nombre
    for agent_id, info in agentes_sistema.items():
        nombre = str(info.get('nombre', '')).strip().upper()
        if nombre:
            busqueda_agentes[nombre] = agent_id

    # Buscar coincidencia FLEXIBLE (igual que en importar_datos_a_registro)
    agente_csv_upper = str(agente_csv).strip().upper()

    # 1. Búsqueda exacta
    if agente_csv_upper in busqueda_agentes:
        return busqueda_agentes[agente_csv_upper], agentes_sistema.get(busqueda_agentes[agente_csv_upper], {}).get('nombre', '')

    # 2. Quitar "TZS" si está presente
    if agente_csv_upper.startswith('TZS'):
        agente_sin_tzs = agente_csv_upper[3:]
        if agente_sin_tzs in busqueda_agentes:
            return busqueda_agentes[agente_sin_tzs], agentes_sistema.get(busqueda_agentes[agente_sin_tzs], {}).get('nombre', '')

    # 3. Solo números
    numeros_csv = ''.join(filter(str.isdigit, agente_csv_upper))
    if numeros_csv:
        for key, agent_id in busqueda_agentes.items():
            numeros_key = ''.join(filter(str.isdigit, key))
            if numeros_key and numeros_csv == numeros_key:
                return agent_id, agentes_sistema.get(agent_id, {}).get('nombre', '')

    # 4. Búsqueda por contenido
    for key, agent_id in busqueda_agentes.items():
        if key in agente_csv_upper or agente_csv_upper in key:
            return agent_id, agentes_sistema.get(agent_id, {}).get('nombre', '')

    return None, None

def verificar_venta_en_registro(agente_sistema, fecha_str):
    """Verifica si una venta está en el registro diario"""
    try:
        from database import cargar_registro_llamadas
        
        registro = cargar_registro_llamadas()
        
        if fecha_str in registro and agente_sistema in registro[fecha_str]:
            ventas = registro[fecha_str][agente_sistema].get('ventas', 0)
            return ventas, True
        return 0, False
    except:
        return 0, False

def realizar_analisis(df_filtrado, nombre_analisis):
    """Realiza el análisis sobre datos filtrados"""
    if df_filtrado.empty:
        st.warning(f"⚠️ No hay datos para {nombre_analisis}")
        return None
    
    # Crear ID único con timestamp
    import time
    import random
    timestamp_ms = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    analisis_id = f"{nombre_analisis.replace(' ', '_')}_{timestamp_ms}_{random_suffix}"
    
    # ==============================================
    # FUNCIÓN LOCAL PARA MAPEAR AGENTES
    # ==============================================
    def mapear_agente_a_sistema_local(agente_csv, super_users_config):
        """Mapea un agente del CSV al sistema (versión local)"""
        agentes_sistema = super_users_config.get("agentes", {})
        
        # Preparar búsqueda flexible
        busqueda_agentes = {}
        
        for agent_id in agentes_sistema.keys():
            agent_id_str = str(agent_id).strip().upper()
            
            busqueda_agentes[agent_id_str] = agent_id
            
            if len(agent_id_str) >= 4:
                busqueda_agentes[agent_id_str[-4:]] = agent_id
            
            if agent_id_str.startswith('TZS'):
                busqueda_agentes[agent_id_str[3:]] = agent_id
            
            solo_numeros = ''.join(filter(str.isdigit, agent_id_str))
            if solo_numeros and solo_numeros != agent_id_str:
                busqueda_agentes[solo_numeros] = agent_id
        
        # También buscar por nombre
        for agent_id, info in agentes_sistema.items():
            nombre = str(info.get('nombre', '')).strip().upper()
            if nombre:
                busqueda_agentes[nombre] = agent_id
        
        # Buscar coincidencia
        agente_csv_upper = str(agente_csv).strip().upper()
        
        # 1. Búsqueda exacta
        if agente_csv_upper in busqueda_agentes:
            return busqueda_agentes[agente_csv_upper], agentes_sistema.get(busqueda_agentes[agente_csv_upper], {}).get('nombre', '')
        
        # 2. Quitar "TZS"
        if agente_csv_upper.startswith('TZS'):
            agente_sin_tzs = agente_csv_upper[3:]
            if agente_sin_tzs in busqueda_agentes:
                return busqueda_agentes[agente_sin_tzs], agentes_sistema.get(busqueda_agentes[agente_sin_tzs], {}).get('nombre', '')
        
        # 3. Solo números
        numeros_csv = ''.join(filter(str.isdigit, agente_csv_upper))
        if numeros_csv:
            for key, agent_id in busqueda_agentes.items():
                numeros_key = ''.join(filter(str.isdigit, key))
                if numeros_key and numeros_csv == numeros_key:
                    return agent_id, agentes_sistema.get(agent_id, {}).get('nombre', '')
        
        # 4. Búsqueda por contenido
        for key, agent_id in busqueda_agentes.items():
            if key in agente_csv_upper or agente_csv_upper in key:
                return agent_id, agentes_sistema.get(agent_id, {}).get('nombre', '')
        
        return None, None
    
    # ==============================================
    # FUNCIÓN PARA PROCESAR ALERTA INDIVIDUAL
    # ==============================================
    def procesar_alerta_individual(datos, estado="confirmado"):
        """Procesa una alerta individual con mapeo correcto de agente Y actualiza registro diario"""
        try:
            from database import agregar_varias_alertas_sms, cargar_super_users, cargar_registro_llamadas, guardar_registro_llamadas
            
            # Cargar configuración para mapear agente
            super_users_config = cargar_super_users()
            
            # Mapear agente del CSV al sistema
            agente_sistema, nombre_agente = mapear_agente_a_sistema_local(datos['agente'], super_users_config)
            
            if agente_sistema is None:
                agente_sistema = datos['agente']
                nombre_agente = "No encontrado en sistema"
                st.warning(f"⚠️ Agente '{datos['agente']}' no encontrado en el sistema")
            
            ventas_finales = datos['ventas_pendientes'] if estado == "confirmado" else 0
            
            # ==============================================
            # 1. ACTUALIZAR REGISTRO DIARIO si se confirma
            # ==============================================
            if estado == "confirmado" and ventas_finales > 0 and agente_sistema:
                try:
                    registro_llamadas = cargar_registro_llamadas()
                    fecha_str = datos['fecha']
                    
                    # Inicializar estructuras si no existen
                    if fecha_str not in registro_llamadas:
                        registro_llamadas[fecha_str] = {}
                    
                    if agente_sistema not in registro_llamadas[fecha_str]:
                        registro_llamadas[fecha_str][agente_sistema] = {
                            'llamadas_totales': 0,
                            'llamadas_15min': 0,
                            'ventas': 0,
                            'fecha': fecha_str,
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    # SUMAR VENTAS al registro
                    registro_llamadas[fecha_str][agente_sistema]['ventas'] += ventas_finales
                    
                    # Contar como llamada larga si la duración > 15 min
                    if datos.get('duracion_minutos', 0) > 15:
                        registro_llamadas[fecha_str][agente_sistema]['llamadas_15min'] += 1
                    
                    # Guardar registro actualizado
                    guardar_registro_llamadas(registro_llamadas)
                    
                    st.info(f"📈 {ventas_finales} venta(s) agregada(s) al registro diario de {agente_sistema} ({fecha_str})")
                    
                except Exception as e:
                    st.error(f"Error actualizando registro diario: {e}")
            
            # ==============================================
            # 2. CREAR ALERTA SMS
            # ==============================================
            alerta = {
                'id': f"sms_{datos['hash']}",
                'tipo': 'pendiente_sms',
                'agente_csv': datos['agente'],
                'agente_sistema': agente_sistema,
                'nombre_agente': nombre_agente,
                'fecha': datos['fecha'],
                'hora': datos['hora'],
                'duracion_minutos': datos['duracion_minutos'],
                'duracion_segundos': int(datos['duracion_minutos'] * 60),
                'resultado_elec': datos['resultado_elec'],
                'resultado_gas': datos['resultado_gas'],
                'motivo_elec': datos.get('motivo_elec', ''),
                'motivo_gas': datos.get('motivo_gas', ''),
                'ventas_pendientes': datos['ventas_pendientes'],
                'ventas_finales': ventas_finales,
                'campanya': datos['campanya'],
                'timestamp_deteccion': datetime.now().isoformat(),
                'hash_registro': datos['hash'],
                'detalles': f"Procesado manualmente como {estado}",
                'estado': estado,
                'opcion_seleccionada': f"SMS {'Contestado' if estado == 'confirmado' else 'No Contestado'}",
                'revisado_manual': True,
                'timestamp_revision': datetime.now().isoformat(),
                'mapeo_correcto': agente_sistema != datos['agente'],
                'actualizado_registro': estado == "confirmado" and ventas_finales > 0
            }
            
            nuevas_agregadas = agregar_varias_alertas_sms([alerta])
            
            if nuevas_agregadas > 0:
                st.success(f"✅ Alerta procesada: {datos['agente']} → {agente_sistema} ({nombre_agente})")
                st.success(f"💰 {ventas_finales} venta(s) {'confirmada(s)' if estado == 'confirmado' else 'rechazada(s)'}")
            return nuevas_agregadas > 0
            
        except Exception as e:
            st.error(f"Error procesando alerta individual: {e}")
            return False
    
    # ==============================================
    # FUNCIÓN PARA PROCESAR TODAS LAS ALERTAS
    # ==============================================
    def procesar_todas_alertas(pendientes_sms_data, estado="confirmado"):
        """Procesa todas las alertas de una vez con mapeo correcto Y actualiza registro diario"""
        try:
            from database import agregar_varias_alertas_sms, cargar_super_users, cargar_registro_llamadas, guardar_registro_llamadas
            
            super_users_config = cargar_super_users()
            
            alertas = []
            mapeos_realizados = []
            ventas_totales_confirmadas = 0
            actualizaciones_registro = []
            
            # Cargar registro una sola vez para optimizar
            if estado == "confirmado":
                registro_llamadas = cargar_registro_llamadas()
            
            for datos in pendientes_sms_data:
                agente_sistema, nombre_agente = mapear_agente_a_sistema_local(datos['agente'], super_users_config)
                
                if agente_sistema is None:
                    agente_sistema = datos['agente']
                    nombre_agente = "No encontrado"
                
                ventas_finales = datos['ventas_pendientes'] if estado == "confirmado" else 0
                
                # ==============================================
                # ACTUALIZAR REGISTRO DIARIO si se confirma
                # ==============================================
                if estado == "confirmado" and ventas_finales > 0 and agente_sistema:
                    try:
                        fecha_str = datos['fecha']
                        
                        # Inicializar estructuras si no existen
                        if fecha_str not in registro_llamadas:
                            registro_llamadas[fecha_str] = {}
                        
                        if agente_sistema not in registro_llamadas[fecha_str]:
                            registro_llamadas[fecha_str][agente_sistema] = {
                                'llamadas_totales': 0,
                                'llamadas_15min': 0,
                                'ventas': 0,
                                'fecha': fecha_str,
                                'timestamp': datetime.now().isoformat()
                            }
                        
                        # SUMAR VENTAS al registro
                        registro_llamadas[fecha_str][agente_sistema]['ventas'] += ventas_finales
                        ventas_totales_confirmadas += ventas_finales
                        
                        # Contar como llamada larga si la duración > 15 min
                        if datos.get('duracion_minutos', 0) > 15:
                            registro_llamadas[fecha_str][agente_sistema]['llamadas_15min'] += 1
                        
                        actualizaciones_registro.append(f"{agente_sistema} ({fecha_str}): +{ventas_finales} venta(s)")
                        
                    except Exception as e:
                        st.error(f"Error actualizando registro para {agente_sistema}: {e}")
                
                # Crear alerta
                alerta = {
                    'id': f"sms_{datos['hash']}",
                    'tipo': 'pendiente_sms',
                    'agente_csv': datos['agente'],
                    'agente_sistema': agente_sistema,
                    'nombre_agente': nombre_agente,
                    'fecha': datos['fecha'],
                    'hora': datos['hora'],
                    'duracion_minutos': datos['duracion_minutos'],
                    'duracion_segundos': int(datos['duracion_minutos'] * 60),
                    'resultado_elec': datos['resultado_elec'],
                    'resultado_gas': datos['resultado_gas'],
                    'motivo_elec': datos.get('motivo_elec', ''),
                    'motivo_gas': datos.get('motivo_gas', ''),
                    'ventas_pendientes': datos['ventas_pendientes'],
                    'ventas_finales': ventas_finales,
                    'campanya': datos['campanya'],
                    'timestamp_deteccion': datetime.now().isoformat(),
                    'hash_registro': datos['hash'],
                    'detalles': f"Procesado automáticamente como {estado}",
                    'estado': estado,
                    'opcion_seleccionada': f"SMS {'Contestado' if estado == 'confirmado' else 'No Contestado'}",
                    'revisado_manual': False,
                    'procesamiento_automatico': True,
                    'mapeo_correcto': agente_sistema != datos['agente'],
                    'actualizado_registro': estado == "confirmado" and ventas_finales > 0
                }
                alertas.append(alerta)
                
                if agente_sistema != datos['agente']:
                    mapeos_realizados.append(f"{datos['agente']} → {agente_sistema}")
            
            # Guardar registro actualizado si hubo cambios
            if estado == "confirmado" and actualizaciones_registro:
                guardar_registro_llamadas(registro_llamadas)
                st.success(f"📈 Registro diario actualizado: {ventas_totales_confirmadas} venta(s) totales")
                
                # Mostrar resumen de actualizaciones
                with st.expander("📋 Ver detalles de actualización", expanded=False):
                    for actualizacion in actualizaciones_registro[:10]:
                        st.write(f"- {actualizacion}")
                    if len(actualizaciones_registro) > 10:
                        st.write(f"... y {len(actualizaciones_registro) - 10} más")
            
            # Guardar alertas
            nuevas_agregadas = agregar_varias_alertas_sms(alertas)
            
            if nuevas_agregadas > 0:
                st.session_state[f'procesadas_{estado}'] = len(alertas)
                
                # Mostrar resumen
                st.success(f"✅ Procesadas {len(alertas)} alertas SMS")
                if estado == "confirmado":
                    st.success(f"💰 {ventas_totales_confirmadas} venta(s) confirmada(s) y agregada(s) al registro")
                else:
                    st.info(f"❌ {len(alertas)} alertas marcadas como no contestadas")
                
                # Mostrar mapeos
                if mapeos_realizados:
                    st.info(f"📋 **Mapeos realizados ({len(mapeos_realizados)}):**")
                    for mapeo in mapeos_realizados[:5]:
                        st.write(f"- {mapeo}")
                    if len(mapeos_realizados) > 5:
                        st.write(f"... y {len(mapeos_realizados) - 5} más")
                
                return True
            return False
            
        except Exception as e:
            st.error(f"Error procesando alertas: {e}")
            return False
    
    # ==============================================
    # FUNCIÓN PARA MOSTRAR MODAL DE EDICIÓN
    # ==============================================
    def mostrar_modal_edicion(datos, index, analisis_id_local):
        """Muestra un modal simple para edición detallada"""
        with st.expander(f"✏️ Editar detalles de la llamada #{index+1}", expanded=True):
            st.write("**Edición avanzada:**")
            
            from database import cargar_super_users
            super_users_config = cargar_super_users()
            
            agente_sistema, nombre_agente = mapear_agente_a_sistema_local(datos['agente'], super_users_config)
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**Agente CSV:** `{datos['agente']}`")
            with col_info2:
                if agente_sistema and agente_sistema != datos['agente']:
                    st.success(f"**→ Sistema:** `{agente_sistema}` ({nombre_agente})")
                elif agente_sistema:
                    st.info(f"**→ Sistema:** `{agente_sistema}` (sin cambio)")
                else:
                    st.warning("**→ Sistema:** No encontrado")
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                agente_edit = st.text_input("Agente (CSV)", 
                                          value=datos['agente'],
                                          key=f"edit_agente_{analisis_id_local}_{index}")
                
                fecha_edit = st.date_input("Fecha", 
                                        value=datetime.strptime(datos['fecha'], '%Y-%m-%d').date() 
                                        if datos['fecha'] else datetime.now().date(),
                                        key=f"edit_fecha_{analisis_id_local}_{index}")
            
            with col2:
                duracion_edit = st.number_input("Duración (min)", 
                                            value=float(datos['duracion_minutos']),
                                            min_value=0.0,
                                            max_value=120.0,
                                            step=0.5,
                                            key=f"edit_duracion_{analisis_id_local}_{index}")
                
                ventas_pendientes_edit = st.number_input("Ventas pendientes",
                                                    value=int(datos['ventas_pendientes']),
                                                    min_value=0,
                                                    max_value=2,
                                                    key=f"edit_ventas_{analisis_id_local}_{index}")
            
            estado_edit = st.radio("Estado final:",
                                options=["confirmado", "rechazado", "pendiente"],
                                index=0 if datos.get('estado') == 'confirmado' else 1 if datos.get('estado') == 'rechazado' else 2,
                                key=f"edit_estado_{analisis_id_local}_{index}",
                                horizontal=True)
            
            if st.button("💾 Guardar cambios", 
                       key=f"save_edit_{analisis_id_local}_{index}",
                       use_container_width=True):
                datos_editados = datos.copy()
                datos_editados['agente'] = agente_edit
                datos_editados['fecha'] = fecha_edit.strftime('%Y-%m-%d')
                datos_editados['duracion_minutos'] = duracion_edit
                datos_editados['ventas_pendientes'] = ventas_pendientes_edit
                
                procesar_alerta_individual(datos_editados, estado=estado_edit)
                st.success("¡Cambios guardados!")
                st.rerun()
    
    # ==============================================
    # CÓDIGO PRINCIPAL DE ANÁLISIS
    # ==============================================
    
    # Limpiar datos
    df_filtrado['tiempo_conversacion'] = pd.to_numeric(df_filtrado['tiempo_conversacion'], errors='coerce')
    df_filtrado['resultado_elec'] = df_filtrado['resultado_elec'].astype(str).str.strip()
    df_filtrado['resultado_gas'] = df_filtrado['resultado_gas'].astype(str).str.strip()
    
    # Asegurar columnas de motivo
    df_filtrado['motivo_elec'] = df_filtrado.get('motivo_elec', '')
    df_filtrado['motivo_gas'] = df_filtrado.get('motivo_gas', '')
    
    # Calcular ventas
    df_filtrado['ventas_elec'] = df_filtrado.apply(
        lambda row: contar_ventas_resultado_mejorado(row['resultado_elec'], row.get('motivo_elec')), 
        axis=1
    )
    df_filtrado['ventas_gas'] = df_filtrado.apply(
        lambda row: contar_ventas_resultado_mejorado(row['resultado_gas'], row.get('motivo_gas')), 
        axis=1
    )
    df_filtrado['ventas_totales'] = df_filtrado['ventas_elec'] + df_filtrado['ventas_gas']
    df_filtrado['tiene_venta'] = df_filtrado['ventas_totales'] > 0
    df_filtrado['duracion_minutos'] = df_filtrado['tiempo_conversacion'] / 60
    
    # Llamadas largas (>15 min = 900 segundos)
    df_llamadas_largas = df_filtrado[df_filtrado['tiempo_conversacion'] > 900].copy()
    
    # Detectar pendientes SMS
    pendientes_sms_data = []
    for idx, row in df_filtrado.iterrows():
        tiene_pendiente, ventas_pendientes = detectar_pendientes_sms_mejorado(row)
        
        if tiene_pendiente:
            pendientes_sms_data.append({
                'agente': row['agente'],
                'fecha': row['fecha'],
                'hora': row['hora'],
                'resultado_elec': row['resultado_elec'],
                'resultado_gas': row['resultado_gas'],
                'motivo_elec': row.get('motivo_elec', ''),
                'motivo_gas': row.get('motivo_gas', ''),
                'ventas_pendientes': ventas_pendientes,
                'tiempo_conversacion': row['tiempo_conversacion'],
                'duracion_minutos': round(row['duracion_minutos'], 1),
                'campanya': row['campanya'],
                'hash': row['hash']
            })
    
    # Calcular estadísticas
    total_llamadas = len(df_filtrado)
    total_agentes = df_filtrado['agente'].nunique()
    media_llamadas_por_agente = total_llamadas / total_agentes if total_agentes > 0 else 0
    llamadas_largas = len(df_llamadas_largas)
    ventas_totales = df_filtrado['ventas_totales'].sum()
    duracion_promedio = df_filtrado['duracion_minutos'].mean() if not df_filtrado['duracion_minutos'].isnull().all() else 0
    
    # Mostrar estadísticas
    st.subheader(f"📊 Análisis: {nombre_analisis}")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("📞 Llamadas totales", total_llamadas)
    with col2:
        st.metric("⏱️ Llamadas >15 min", llamadas_largas)
    with col3:
        st.metric("💰 Ventas totales", int(ventas_totales))
    with col4:
        st.metric("⏱️ Duración promedio", f"{duracion_promedio:.1f} min")
    with col5:
        st.metric("👥 Media llamadas/agente", f"{media_llamadas_por_agente:.1f}")
    with col6:
        total_pendientes = len(pendientes_sms_data)
        ventas_pendientes = sum(item['ventas_pendientes'] for item in pendientes_sms_data)
        delta = f"{int(ventas_pendientes)} ventas" if ventas_pendientes > 0 else None
        st.metric("⏳ Pendientes SMS", int(total_pendientes), delta=delta)
    
    # Mostrar alerta si hay pendientes SMS
    if pendientes_sms_data:
        st.warning(f"⚠️ **{total_pendientes} llamadas con PENDIENTE SMS detectadas ({ventas_pendientes} ventas pendientes)**")
        
        # Guardar en session_state para uso posterior
        st.session_state.pendientes_sms = pendientes_sms_data
        
        # Inicializar set de alertas procesadas si no existe
        if 'alertas_procesadas' not in st.session_state:
            st.session_state.alertas_procesadas = set()
        
        # Mostrar tabla de pendientes
        with st.expander("📋 Ver detalles de pendientes SMS", expanded=False):
            # Crear DataFrame con información de mapeo
            df_pendientes = pd.DataFrame(pendientes_sms_data)
            
            # Cargar configuración para mapear
            from database import cargar_super_users
            super_users_config = cargar_super_users()
            
            # Añadir columna de mapeo
            mapeos = []
            for _, row in df_pendientes.iterrows():
                agente_sistema, nombre_agente = mapear_agente_a_sistema_local(row['agente'], super_users_config)
                if agente_sistema and agente_sistema != row['agente']:
                    mapeos.append(f"→ {agente_sistema}")
                else:
                    mapeos.append("")
            
            df_pendientes['Mapeo'] = mapeos
            
            # Añadir columna de estado actual
            estados = []
            for _, row in df_pendientes.iterrows():
                alerta_id = f"sms_{row['hash']}"
                
                # Verificar si ya fue procesada en esta sesión
                if alerta_id in st.session_state.alertas_procesadas:
                    estados.append("✅ Confirmada")
                # Verificar si ya está en el sistema
                elif verificar_si_procesada(row['hash']):
                    estados.append("✓ Procesada")
                else:
                    estados.append("⏳ Pendiente")
            
            df_pendientes['Estado Actual'] = estados
            
            df_pendientes_display = df_pendientes[['agente', 'Mapeo', 'Estado Actual', 'fecha', 'hora', 'duracion_minutos', 
                                                   'resultado_elec', 'resultado_gas', 'ventas_pendientes']].copy()
            df_pendientes_display.columns = ['Agente (CSV)', '→ Sistema', 'Estado', 'Fecha', 'Hora', 'Duración (min)', 
                                             'Resultado Elec', 'Resultado Gas', 'Ventas Pendientes']
            
            # Resaltar filas según estado
            def highlight_estado(row):
                """
                Resalta filas según su estado
                row es una fila de df_pendientes_display, que tiene estas columnas:
                ['Agente (CSV)', '→ Sistema', 'Estado', 'Fecha', 'Hora', 'Duración (min)', 
                'Resultado Elec', 'Resultado Gas', 'Ventas Pendientes']
                """
                # Verificar si la fila tiene mapeo (columna '→ Sistema' no vacía)
                tiene_mapeo = row['→ Sistema'] and str(row['→ Sistema']).strip() != ''
                
                if row['Estado'] == "✅ Confirmada":
                    return ['background-color: #d4edda'] * len(row)  # Verde claro
                elif tiene_mapeo:
                    return ['background-color: #fff3cd'] * len(row)  # Amarillo claro para mapeo
                return [''] * len(row)
            
            st.dataframe(
                df_pendientes_display.style.apply(highlight_estado, axis=1), 
                use_container_width=True
            )
            
            st.info("💡 **Nota:** Estas ventas NO se importarán automáticamente. Requieren confirmación manual.")
            
            # ==============================================
            # PROCESAMIENTO DE PENDIENTES SMS
            # ==============================================
            st.divider()
            st.subheader("📝 Procesar Pendientes SMS")
            
            # Opción 1: Procesar todas automáticamente
            st.write("**Opción rápida:**")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Todas como Confirmadas", 
                           help="Marcar todas las SMS como contestadas y contar ventas",
                           use_container_width=True,
                           key=f"confirm_all_{analisis_id}"):
                    if procesar_todas_alertas(pendientes_sms_data, estado="confirmado"):
                        # Marcar todas como procesadas en session_state
                        for datos in pendientes_sms_data:
                            alerta_id = f"sms_{datos['hash']}"
                            st.session_state.alertas_procesadas.add(alerta_id)
                        st.success("¡Todas las alertas procesadas como confirmadas!")
                        st.rerun()
            
            with col2:
                if st.button("❌ Todas como No Contestadas", 
                           help="Marcar todas las SMS como no contestadas",
                           use_container_width=True,
                           key=f"reject_all_{analisis_id}"):
                    if procesar_todas_alertas(pendientes_sms_data, estado="rechazado"):
                        st.success("¡Todas las alertas procesadas como no contestadas!")
                        st.rerun()
            
            st.divider()
            st.write("**Opción detallada:** Procesar una por una")
            
            # Formulario simple y directo
            for i, datos in enumerate(pendientes_sms_data):
                with st.container():
                    st.markdown(f"---")
                    st.write(f"**Llamada #{i+1}**")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.write(f"**Agente:** {datos['agente']}")
                    with col_b:
                        st.write(f"**Fecha:** {datos['fecha']}")
                    with col_c:
                        st.write(f"**Hora:** {datos['hora']}")
                    
                    st.write(f"**Ventas pendientes:** {datos['ventas_pendientes']}")
                    st.write(f"**Duración:** {datos['duracion_minutos']} minutos")
                    
                    # Verificar si ya está procesada
                    alerta_id = f"sms_{datos['hash']}"
                    procesada_en_sistema = verificar_si_procesada(datos['hash'])
                    procesada_en_sesion = alerta_id in st.session_state.alertas_procesadas
                    ya_procesada = procesada_en_sistema or procesada_en_sesion
                    
                    # Botones de acción
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if not ya_procesada:
                            if st.button(f"✅ Confirmar", 
                                       key=f"confirm_{analisis_id}_{i}_{datos['hash']}",
                                       use_container_width=True):
                                if procesar_alerta_individual(datos, estado="confirmado"):
                                    st.session_state.alertas_procesadas.add(alerta_id)
                                    st.success(f"Llamada #{i+1} confirmada")
                                    st.rerun()
                        else:
                            if procesada_en_sesion:
                                st.success("✅ Confirmada en esta sesión")
                            else:
                                st.success("✓ Ya procesada")
                    
                    with col_btn2:
                        if not ya_procesada:
                            if st.button(f"❌ Rechazar", 
                                       key=f"reject_{analisis_id}_{i}_{datos['hash']}",
                                       use_container_width=True):
                                if procesar_alerta_individual(datos, estado="rechazado"):
                                    st.session_state.alertas_procesadas.add(alerta_id)
                                    st.success(f"Llamada #{i+1} rechazada")
                                    st.rerun()
                        else:
                            st.info("✓ Ya procesada")
                    
                    with col_btn3:
                        # Botón para editar
                        if st.button(f"📝 Editar", 
                                   key=f"edit_{analisis_id}_{i}_{datos['hash']}",
                                   use_container_width=True):
                            mostrar_modal_edicion(datos, i, analisis_id)
    
    # ==============================================
    # ANÁLISIS POR AGENTE
    # ==============================================
    st.subheader("👥 Resumen por Agente")
    
    agentes_analisis = []
    for agente in df_filtrado['agente'].unique():
        df_agente = df_filtrado[df_filtrado['agente'] == agente]
        df_agente_largas = df_agente[df_agente['tiempo_conversacion'] > 900]
        
        llamadas_totales = len(df_agente)
        llamadas_largas = len(df_agente_largas)
        ventas_agente = df_agente['ventas_totales'].sum()
        ventas_largas = df_agente_largas['ventas_totales'].sum() if not df_agente_largas.empty else 0
        
        agentes_analisis.append({
            'Agente': agente,
            'Llamadas Totales': llamadas_totales,
            'Llamadas >15 min': llamadas_largas,
            'Ventas Totales': int(ventas_agente),
            'Ventas >15 min': int(ventas_largas),
            'Tasa Conversión Total': f"{(ventas_agente/llamadas_totales*100):.1f}%" if llamadas_totales > 0 else "0%",
            'Tasa Conversión Largas': f"{(ventas_largas/llamadas_largas*100):.1f}%" if llamadas_largas > 0 else "0%"
        })
    
    if agentes_analisis:
        df_resultados = pd.DataFrame(agentes_analisis)
        df_resultados = df_resultados.sort_values('Ventas Totales', ascending=False)
        st.dataframe(df_resultados, use_container_width=True)
    
    # ==============================================
    # VENTAS DESDE LLAMADAS LARGAS
    # ==============================================
    df_ventas_largas = df_llamadas_largas[df_llamadas_largas['tiene_venta']]
    
    if not df_ventas_largas.empty:
        st.subheader(f"✅ Ventas desde Llamadas Largas: {int(df_ventas_largas['ventas_totales'].sum())}")
        
        df_detalle = df_ventas_largas[['agente', 'duracion_minutos', 'resultado_elec', 
                                       'resultado_gas', 'ventas_totales', 'fecha', 'hora']].copy()
        df_detalle['duracion_minutos'] = df_detalle['duracion_minutos'].round(1)
        df_detalle = df_detalle.sort_values('duracion_minutos', ascending=False)
        df_detalle.columns = ['Agente', 'Duración (min)', 'Resultado Elec', 'Resultado Gas', 'Ventas', 'Fecha', 'Hora']
        
        st.dataframe(df_detalle.head(10), use_container_width=True)
    
    return df_filtrado

def importar_datos_a_registro(df_analizado, super_users_config):
    """
    Importa los datos analizados al registro diario
    """
    if df_analizado.empty:
        return False, "No hay datos para importar"
    
    # Cargar registro actual
    registro_llamadas = cargar_registro_llamadas()
    
    # Obtener agentes del sistema
    agentes_sistema = super_users_config.get("agentes", {})
    
    # Contadores
    total_lineas_csv = len(df_analizado)
    lineas_procesadas = 0
    lineas_no_procesadas = 0
    llamadas_totales_importadas = 0
    llamadas_largas_importadas = 0
    ventas_importadas = 0
    
    agentes_encontrados_lista = []
    agentes_no_encontrados_set = set()
    coincidencias_unicas = set()
    
    # Preparar búsqueda flexible
    busqueda_agentes = {}
    
    for agent_id in agentes_sistema.keys():
        agent_id_str = str(agent_id).strip().upper()
        
        # Variantes de búsqueda
        busqueda_agentes[agent_id_str] = agent_id
        
        if len(agent_id_str) >= 4:
            busqueda_agentes[agent_id_str[-4:]] = agent_id
        
        if agent_id_str.startswith('TZS'):
            busqueda_agentes[agent_id_str[3:]] = agent_id
        
        solo_numeros = ''.join(filter(str.isdigit, agent_id_str))
        if solo_numeros and solo_numeros != agent_id_str:
            busqueda_agentes[solo_numeros] = agent_id
    
    # También buscar por nombre
    for agent_id, info in agentes_sistema.items():
        nombre = str(info.get('nombre', '')).strip().upper()
        if nombre:
            busqueda_agentes[nombre] = agent_id
    
    # Procesar CADA línea del CSV
    for idx, row in df_analizado.iterrows():
        agente_csv = str(row['agente']).strip()
        agente_csv_upper = agente_csv.upper()
        fecha_str = row['fecha']
        
        # Buscar coincidencia FLEXIBLE
        agente_encontrado = None
        
        # 1. Búsqueda exacta
        if agente_csv_upper in busqueda_agentes:
            agente_encontrado = busqueda_agentes[agente_csv_upper]
        
        # 2. Búsqueda por contenido
        if not agente_encontrado:
            for key, agent_id in busqueda_agentes.items():
                if key in agente_csv_upper or agente_csv_upper in key:
                    agente_encontrado = agent_id
                    break
        
        # 3. Búsqueda por números
        if not agente_encontrado:
            numeros_csv = ''.join(filter(str.isdigit, agente_csv))
            if numeros_csv:
                for key, agent_id in busqueda_agentes.items():
                    numeros_key = ''.join(filter(str.isdigit, key))
                    if numeros_key and numeros_csv == numeros_key:
                        agente_encontrado = agent_id
                        break
        
        if agente_encontrado:
            lineas_procesadas += 1
            
            # Inicializar estructuras
            if fecha_str not in registro_llamadas:
                registro_llamadas[fecha_str] = {}
            
            if agente_encontrado not in registro_llamadas[fecha_str]:
                registro_llamadas[fecha_str][agente_encontrado] = {
                    'llamadas_totales': 0,
                    'llamadas_15min': 0,
                    'ventas': 0,
                    'fecha': fecha_str,
                    'timestamp': datetime.now().isoformat()
                }
            
            # CONTAR LLAMADA TOTAL
            registro_llamadas[fecha_str][agente_encontrado]['llamadas_totales'] += 1
            llamadas_totales_importadas += 1
            
            # Contar si es llamada larga
            if row['tiempo_conversacion'] > 900:
                registro_llamadas[fecha_str][agente_encontrado]['llamadas_15min'] += 1
                llamadas_largas_importadas += 1
            
            # Sumar ventas
            ventas_fila = int(row['ventas_totales'])
            if ventas_fila > 0:
                registro_llamadas[fecha_str][agente_encontrado]['ventas'] += ventas_fila
                ventas_importadas += ventas_fila
            
            # Guardar coincidencia única
            coincidencia = f"{agente_csv} → {agente_encontrado}"
            if coincidencia not in coincidencias_unicas:
                coincidencias_unicas.add(coincidencia)
                agentes_encontrados_lista.append(coincidencia)
        
        else:
            lineas_no_procesadas += 1
            agentes_no_encontrados_set.add(agente_csv)
    
    # Guardar cambios
    guardar_registro_llamadas(registro_llamadas)
    
    # Preparar mensaje
    mensaje = f"✅ **IMPORTACIÓN - DIAGNÓSTICO DETALLADO**\n"
    mensaje += "=" * 50 + "\n"
    mensaje += f"📊 **TOTAL CSV:** {total_lineas_csv} líneas\n"
    mensaje += f"✅ **Procesadas:** {lineas_procesadas} líneas\n"
    mensaje += f"❌ **NO procesadas:** {lineas_no_procesadas} líneas\n"
    mensaje += f"📞 **Llamadas importadas:** {llamadas_totales_importadas}\n"
    mensaje += f"⏱️ **Llamadas >15min:** {llamadas_largas_importadas}\n"
    mensaje += f"💰 **Ventas:** {ventas_importadas}\n"
    
    # VERIFICACIÓN CRÍTICA
    mensaje += "\n🔍 **VERIFICACIÓN:**\n"
    if llamadas_totales_importadas == lineas_procesadas:
        mensaje += f"✅ Llamadas importadas = Líneas procesadas ({llamadas_totales_importadas})\n"
    else:
        mensaje += f"❌ ERROR: Llamadas ({llamadas_totales_importadas}) ≠ Líneas ({lineas_procesadas})\n"
    
    if lineas_procesadas + lineas_no_procesadas == total_lineas_csv:
        mensaje += f"✅ Suma líneas = Total CSV ({total_lineas_csv})\n"
    else:
        mensaje += f"❌ ERROR: Suma ({lineas_procesadas + lineas_no_procesadas}) ≠ Total ({total_lineas_csv})\n"
    
    # Agentes encontrados
    mensaje += f"\n👥 **Agentes con coincidencia:** {len(agentes_encontrados_lista)}\n"
    if agentes_encontrados_lista:
        for i, coinc in enumerate(agentes_encontrados_lista[:10]):
            mensaje += f"  {i+1}. {coinc}\n"
        if len(agentes_encontrados_lista) > 10:
            mensaje += f"  ... y {len(agentes_encontrados_lista) - 10} más\n"
    
    # Agentes NO encontrados
    mensaje += f"\n⚠️ **Agentes SIN coincidencia:** {len(agentes_no_encontrados_set)}\n"
    if agentes_no_encontrados_set:
        for ej in list(agentes_no_encontrados_set)[:5]:
            mensaje += f"  - '{ej}'\n"
        
        mensaje += f"\n💡 **¿Por qué no se encuentran?**\n"
        mensaje += f"1. Los IDs no coinciden (ej: '0733' vs 'TZS0733')\n"
        mensaje += f"2. Agentes no están configurados en Super Users\n"
        mensaje += f"3. Errores de formato en el CSV\n"
        
        mensaje += f"\n📋 **Agentes configurados en el sistema ({len(agentes_sistema)}):**\n"
        for i, (agent_id, info) in enumerate(list(agentes_sistema.items())[:10]):
            nombre = info.get('nombre', 'Sin nombre')
            mensaje += f"  {i+1}. `{agent_id}`: {nombre}\n"
        if len(agentes_sistema) > 10:
            mensaje += f"  ... y {len(agentes_sistema) - 10} más\n"
    
    return True, mensaje


def mostrar_depuracion_agentes(df_analizado, super_users_config):
    """Muestra información de depuración para coincidencia de agentes"""
    st.subheader("🔍 Depuración: Coincidencia de Agentes")
    
    # Obtener agentes
    agentes_csv = sorted(df_analizado['agente'].astype(str).str.strip().unique())
    agentes_sistema = super_users_config.get("agentes", {})
    
    # Mostrar comparación
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📄 Agentes en el CSV:**")
        for i, agente in enumerate(agentes_csv[:20]):
            st.write(f"{i+1}. `{agente}`")
        if len(agentes_csv) > 20:
            st.info(f"... y {len(agentes_csv) - 20} más")
    
    with col2:
        st.write("**📊 Agentes en el sistema:**")
        for i, (agent_id, info) in enumerate(list(agentes_sistema.items())[:20]):
            nombre = info.get('nombre', 'Sin nombre')
            st.write(f"{i+1}. `{agent_id}`: {nombre}")
        if len(agentes_sistema) > 20:
            st.info(f"... y {len(agentes_sistema) - 20} más")
    
    # Coincidencias
    coincidencias_directas = []
    coincidencias_parciales = []
    sin_coincidencia = []
    
    for agente_csv in agentes_csv:
        agente_csv_clean = str(agente_csv).upper()
        encontrado = False
        
        # Búsqueda exacta
        for agent_id in agentes_sistema.keys():
            if str(agent_id).upper() == agente_csv_clean:
                coincidencias_directas.append(f"`{agente_csv}` → `{agent_id}`")
                encontrado = True
                break
        
        # Búsqueda parcial
        if not encontrado:
            for agent_id in agentes_sistema.keys():
                agent_id_clean = str(agent_id).upper()
                if (agente_csv_clean in agent_id_clean or 
                    agent_id_clean in agente_csv_clean or
                    agente_csv_clean[-4:] == agent_id_clean[-4:]):
                    coincidencias_parciales.append(f"`{agente_csv}` → `{agent_id}`")
                    encontrado = True
                    break
        
        if not encontrado:
            sin_coincidencia.append(agente_csv)
    
    # Mostrar resultados
    if coincidencias_directas:
        st.success(f"✅ **Coincidencias exactas ({len(coincidencias_directas)}):**")
        for coincidencia in coincidencias_directas[:10]:
            st.write(f"- {coincidencia}")
    
    if coincidencias_parciales:
        st.warning(f"⚠️ **Coincidencias parciales ({len(coincidencias_parciales)}):**")
        for coincidencia in coincidencias_parciales[:10]:
            st.write(f"- {coincidencia}")
    
    if sin_coincidencia:
        st.error(f"❌ **Sin coincidencia ({len(sin_coincidencia)}):**")
        for agente in sin_coincidencia[:10]:
            st.write(f"- `{agente}`")


def verificar_agentes_con_alerta(df_analizado, super_users_config):
    """Verifica agentes que necesitan alerta por baja actividad"""
    st.subheader("🔔 Sistema de Alertas por Baja Actividad")
    
    configuracion = super_users_config.get("configuracion", {})
    umbral_alerta = configuracion.get("umbral_alertas_llamadas", 20)
    minimo_llamadas_dia = configuracion.get("minimo_llamadas_dia", 50)
    
    # Calcular media
    total_llamadas = len(df_analizado)
    total_agentes = df_analizado['agente'].nunique()
    media_llamadas_por_agente = total_llamadas / total_agentes if total_agentes > 0 else 0
    
    st.info(f"**📊 Estadísticas generales:**")
    st.info(f"- Media de llamadas por agente: {media_llamadas_por_agente:.1f}")
    st.info(f"- Umbral de alerta: {umbral_alerta}% por debajo de la media")
    st.info(f"- Mínimo para considerar activo: {minimo_llamadas_dia} llamadas/día")
    
    # Analizar cada agente
    agentes_alerta = []
    agentes_ok = []
    
    for agente in df_analizado['agente'].unique():
        df_agente = df_analizado[df_analizado['agente'] == agente]
        llamadas_agente = len(df_agente)
        
        # Calcular diferencia con la media
        diferencia_porcentaje = 0
        if media_llamadas_por_agente > 0:
            diferencia_porcentaje = ((llamadas_agente - media_llamadas_por_agente) / media_llamadas_por_agente * 100)
        
        # Determinar si necesita alerta
        necesita_alerta = diferencia_porcentaje < -umbral_alerta
        
        # Verificar si está activo
        dias_con_datos = df_agente['fecha'].nunique()
        llamadas_por_dia = llamadas_agente / dias_con_datos if dias_con_datos > 0 else 0
        activo = llamadas_por_dia >= minimo_llamadas_dia
        
        agente_info = {
            'Agente': agente,
            'Llamadas Totales': llamadas_agente,
            'Días con Datos': dias_con_datos,
            'Llamadas/Día': f"{llamadas_por_dia:.1f}",
            'vs Media (%)': f"{diferencia_porcentaje:.1f}%",
            'Activo': '✅' if activo else '⚠️',
            'Alerta': '🔔' if necesita_alerta else '✅'
        }
        
        if necesita_alerta:
            agentes_alerta.append(agente_info)
        else:
            agentes_ok.append(agente_info)
    
    # Mostrar agentes con alerta
    if agentes_alerta:
        st.warning(f"### ⚠️ **{len(agentes_alerta)} Agentes Necesitan Atención**")
        st.write("Están por debajo del umbral de alerta:")
        
        df_alerta = pd.DataFrame(agentes_alerta)
        df_alerta = df_alerta.sort_values('vs Media (%)')
        st.dataframe(df_alerta, use_container_width=True)
        
        st.write("**💡 Recomendaciones:**")
        st.write("1. Revisar actividad de estos agentes")
        st.write("2. Verificar posibles problemas técnicos")
        st.write("3. Considerar capacitación adicional")
        st.write("4. Establecer objetivos personalizados")
    else:
        st.success("🎉 **Todos los agentes están dentro del rango esperado**")
    
    # Mostrar resumen
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Agentes Totales", total_agentes)
    with col2:
        st.metric("Con Alerta", len(agentes_alerta))
    with col3:
        st.metric("Sin Alerta", len(agentes_ok))


def comprobador_actividad_diaria(df_analizado):
    """Comprueba qué agentes están trabajando (mínimo 50 llamadas/día)"""
    st.subheader("📊 Comprobador de Actividad Diaria")
    
    MINIMO_LLAMADAS_DIA = 50
    
    # Agrupar por agente y fecha
    actividad = df_analizado.groupby(['agente', 'fecha']).size().reset_index(name='llamadas')
    
    resumen_agentes = []
    
    for agente in actividad['agente'].unique():
        df_agente = actividad[actividad['agente'] == agente]
        
        dias_totales = df_agente['fecha'].nunique()
        dias_trabajando = len(df_agente[df_agente['llamadas'] >= MINIMO_LLAMADAS_DIA])
        dias_no_trabajando = dias_totales - dias_trabajando
        
        porcentaje_trabajando = (dias_trabajando / dias_totales * 100) if dias_totales > 0 else 0
        
        resumen_agentes.append({
            'Agente': agente,
            'Días Totales': dias_totales,
            'Días Trabajando': dias_trabajando,
            'Días No Trabajando': dias_no_trabajando,
            '% Trabajando': f"{porcentaje_trabajando:.1f}%",
            'Estado': '✅' if porcentaje_trabajando >= 80 else '⚠️' if porcentaje_trabajando >= 50 else '❌'
        })
    
    if resumen_agentes:
        df_resumen = pd.DataFrame(resumen_agentes)
        df_resumen = df_resumen.sort_values('% Trabajando', ascending=False)
        
        st.write(f"**📈 Actividad diaria (mínimo {MINIMO_LLAMADAS_DIA} llamadas/día):**")
        st.dataframe(df_resumen, use_container_width=True)
        
        # Estadísticas
        total_agentes = len(resumen_agentes)
        agentes_ok = len([a for a in resumen_agentes if a['Estado'] == '✅'])
        agentes_alerta = len([a for a in resumen_agentes if a['Estado'] == '⚠️'])
        agentes_critico = len([a for a in resumen_agentes if a['Estado'] == '❌'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Óptimos", agentes_ok)
        with col2:
            st.metric("⚠️ Necesitan atención", agentes_alerta)
        with col3:
            st.metric("❌ Críticos", agentes_critico)
        
        # Mostrar agentes críticos
        agentes_criticos_lista = [a for a in resumen_agentes if a['Estado'] == '❌']
        if agentes_criticos_lista:
            st.warning("### 🔴 Agentes con Baja Actividad Crítica")
            st.write("Estos agentes trabajan menos del 50% de los días:")
            
            for agente in agentes_criticos_lista:
                st.write(f"- **{agente['Agente']}**: {agente['Días Trabajando']}/{agente['Días Totales']} días ({agente['% Trabajando']})")
        
        # Gráfico de actividad
        st.write("### 📊 Distribución de Actividad")
        import plotly.express as px
        
        estados_counts = {
            '✅ Óptimos (>80%)': agentes_ok,
            '⚠️ Atención (50-79%)': agentes_alerta,
            '❌ Críticos (<50%)': agentes_critico
        }
        
        fig = px.pie(
            names=list(estados_counts.keys()),
            values=list(estados_counts.values()),
            title='Distribución de Agentes por Nivel de Actividad',
            color_discrete_sequence=['green', 'orange', 'red']
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para analizar actividad diaria")


def interfaz_analisis_llamadas():
    """Interfaz principal del analizador"""
    st.subheader("📊 Analizador de Llamadas Telefónicas - Zelenza")
    
    # Inicializar session_state
    if 'analisis_realizado' not in st.session_state:
        st.session_state.analisis_realizado = False
    if 'df_cargado' not in st.session_state:
        st.session_state.df_cargado = None
    if 'df_analizado_actual' not in st.session_state:
        st.session_state.df_analizado_actual = None
    
    # Paso 1: Subir archivo
    uploaded_file = st.file_uploader(
        "1. 📤 Sube tu archivo CSV/TXT de llamadas",
        type=['csv', 'txt'],
        help="Archivo separado por tabulaciones con columna 'campanya'"
    )
    
    # Procesar archivo
    if uploaded_file is not None and not st.session_state.analisis_realizado:
        with st.spinner("📂 Cargando y procesando archivo..."):
            df = analizar_csv_llamadas(uploaded_file)
            if df is not None:
                st.session_state.df_cargado = df
                st.session_state.analisis_realizado = True
                st.rerun()
    
    # Mostrar opciones de análisis si hay datos cargados
    if st.session_state.df_cargado is not None:
        df = st.session_state.df_cargado
        
        if 'campanyas_unicas' not in st.session_state:
            st.session_state.campanyas_unicas = df['campanya'].astype(str).str.strip().unique()
        
        campanyas = st.session_state.campanyas_unicas
        
        st.subheader("2. 🎯 Selecciona qué analizar")
        
        # Crear opciones de análisis
        opciones = ["📊 TODAS las campañas"]
        
        # Buscar campañas específicas
        captacion_encontrada = False
        quality_encontrada = False
        
        for camp in campanyas:
            camp_upper = str(camp).upper()
            if 'CAPTACION DUAL ZELEN' in camp_upper and not captacion_encontrada:
                opciones.append(f"📞 {camp}")
                captacion_encontrada = True
            elif 'QUALITY DIF ZELENZA' in camp_upper and not quality_encontrada:
                opciones.append(f"🎯 {camp}")
                quality_encontrada = True
        
        # Añadir otras campañas
        otras_campanyas = 0
        for camp in campanyas:
            camp_str = str(camp)
            if f"📞 {camp}" not in opciones and f"🎯 {camp}" not in opciones and otras_campanyas < 3:
                opciones.append(f"📋 {camp[:40]}..." if len(camp_str) > 40 else f"📋 {camp}")
                otras_campanyas += 1
        
        # Opciones adicionales
        if len(campanyas) >= 2:
            opciones.append("🔄 COMPARAR campañas principales")
        
        opciones.append("🔔 Verificar alertas de actividad")
        opciones.append("📊 Comprobar actividad diaria")
        
        # Selector
        seleccion = st.selectbox("Elige una opción de análisis:", opciones, key="selector_campanya")
        
        # Botón para aplicar análisis
        if st.button("🔍 Aplicar análisis", type="primary", key="aplicar_analisis"):
            with st.spinner("Analizando datos..."):
                if "TODAS" in seleccion:
                    df_analizado = realizar_analisis(df, "TODAS las campañas")
                    st.session_state.df_analizado_actual = df_analizado
                
                elif "COMPARAR" in seleccion and len(campanyas) >= 2:
                    st.subheader("🔄 Comparativa entre Campañas")
                    
                    camp1 = campanyas[0] if len(campanyas) > 0 else ""
                    camp2 = campanyas[1] if len(campanyas) > 1 else ""
                    
                    if camp1 and camp2:
                        df_camp1 = df[df['campanya'] == camp1].copy()
                        df_camp2 = df[df['campanya'] == camp2].copy()
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{camp1[:30]}...**" if len(camp1) > 30 else f"**{camp1}**")
                            if not df_camp1.empty:
                                llamadas1 = len(df_camp1)
                                ventas1 = df_camp1.apply(
                                    lambda row: contar_ventas_resultado(row['resultado_elec']) + 
                                              contar_ventas_resultado(row['resultado_gas']), 
                                    axis=1
                                ).sum()
                                st.metric("Llamadas", llamadas1)
                                st.metric("Ventas", int(ventas1))
                                st.metric("Tasa", f"{(ventas1/llamadas1*100):.1f}%" if llamadas1 > 0 else "0%")
                        
                        with col2:
                            st.write(f"**{camp2[:30]}...**" if len(camp2) > 30 else f"**{camp2}**")
                            if not df_camp2.empty:
                                llamadas2 = len(df_camp2)
                                ventas2 = df_camp2.apply(
                                    lambda row: contar_ventas_resultado(row['resultado_elec']) + 
                                              contar_ventas_resultado(row['resultado_gas']), 
                                    axis=1
                                ).sum()
                                st.metric("Llamadas", llamadas2)
                                st.metric("Ventas", int(ventas2))
                                st.metric("Tasa", f"{(ventas2/llamadas2*100):.1f}%" if llamadas2 > 0 else "0%")
                
                elif "🔔 Verificar alertas de actividad" in seleccion:
                    super_users_config = cargar_super_users()
                    verificar_agentes_con_alerta(df, super_users_config)
                
                elif "📊 Comprobar actividad diaria" in seleccion:
                    comprobador_actividad_diaria(df)
                
                else:
                    # Análisis de campaña específica
                    campanya_seleccionada = seleccion[2:]
                    df_filtrado = None
                    
                    for camp in campanyas:
                        if str(camp) == campanya_seleccionada or campanya_seleccionada in str(camp):
                            df_filtrado = df[df['campanya'] == camp].copy()
                            break
                    
                    if df_filtrado is not None and not df_filtrado.empty:
                        df_analizado = realizar_analisis(df_filtrado, campanya_seleccionada)
                        st.session_state.df_analizado_actual = df_analizado
                    else:
                        st.error(f"No se encontró la campaña: {campanya_seleccionada}")
        
        # Importar datos al sistema
        if st.session_state.df_analizado_actual is not None and not st.session_state.df_analizado_actual.empty:
            st.subheader("3. 📥 Importar al Sistema de Agentes")
            
            # Mostrar mensaje sobre pendientes SMS
            if 'pendientes_sms' in st.session_state and st.session_state.pendientes_sms:
                total_pendientes = len(st.session_state.pendientes_sms)
                ventas_pendientes = sum(item['ventas_pendientes'] for item in st.session_state.pendientes_sms)
                
                st.info(f"💡 **Nota:** Hay {total_pendientes} ventas PENDIENTE SMS ({ventas_pendientes} ventas) que NO se importarán automáticamente. "
                        f"Aparecerán como alertas en el sidebar de Super Users para confirmación manual.")
            
            # Cargar configuración
            super_users_config = cargar_super_users()
            
            # Vista previa
            with st.expander("📋 Vista previa de datos a importar", expanded=True):
                df_preview = st.session_state.df_analizado_actual[['agente', 'fecha', 'tiempo_conversacion', 'ventas_totales']].copy()
                df_preview['Llamada >15min'] = df_preview['tiempo_conversacion'] > 900
                df_preview['Agente'] = df_preview['agente']
                df_preview['Fecha'] = df_preview['fecha']
                df_preview['Ventas'] = df_preview['ventas_totales']
                df_preview = df_preview[['Agente', 'Fecha', 'Llamada >15min', 'Ventas']]
                st.dataframe(df_preview.head(20), use_container_width=True)
                
                # Estadísticas rápidas
                llamadas_largas = len(st.session_state.df_analizado_actual[st.session_state.df_analizado_actual['tiempo_conversacion'] > 900])
                ventas_totales = st.session_state.df_analizado_actual['ventas_totales'].sum()
                agentes_unicos = st.session_state.df_analizado_actual['agente'].nunique()
                fechas_unicas = st.session_state.df_analizado_actual['fecha'].nunique()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("👥 Agentes", agentes_unicos)
                with col2:
                    st.metric("📅 Fechas", fechas_unicas)
                with col3:
                    st.metric("📞 Llamadas >15min", llamadas_largas)
                with col4:
                    st.metric("💰 Ventas", int(ventas_totales))
            
            # Confirmación de importación
            st.info("💡 **Importará:** Llamadas >15min y ventas al registro diario de agentes")
            st.warning("⚠️ Los datos existentes para las mismas fechas y agentes serán sumados, no reemplazados.")
            st.info("🔄 Se evitan duplicados mediante sistema de hashes")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📥 Importar Datos", type="primary", use_container_width=True):
                    with st.spinner("Importando datos al sistema..."):
                        exito, mensaje = importar_datos_a_registro(
                            st.session_state.df_analizado_actual, 
                            super_users_config
                        )
                        
                        if exito:
                            st.success("✅ Datos importados exitosamente")
                            for linea in mensaje.split('\n'):
                                if linea.strip():
                                    st.write(linea)
                        else:
                            st.error(f"❌ Error al importar: {mensaje}")
            
            with col2:
                if st.button("🧹 Limpiar y Probar", type="secondary", use_container_width=True):
                    registro_actual = cargar_registro_llamadas()
                    agentes_sistema = super_users_config.get("agentes", {})
                    agentes_csv = st.session_state.df_analizado_actual['agente'].unique()
                    
                    st.info("🔍 **Prueba de coincidencia de agentes:**")
                    
                    coincidentes = []
                    no_coincidentes = []
                    
                    for agente in agentes_csv:
                        if str(agente).strip() in agentes_sistema:
                            coincidentes.append(agente)
                        else:
                            no_coincidentes.append(agente)
                    
                    col_test1, col_test2 = st.columns(2)
                    with col_test1:
                        st.success(f"✅ Coincidentes: {len(coincidentes)}")
                        for i, agente in enumerate(coincidentes[:5]):
                            st.write(f"- {agente}")
                    
                    with col_test2:
                        if no_coincidentes:
                            st.warning(f"⚠️ No encontrados: {len(no_coincidentes)}")
                            for i, agente in enumerate(no_coincidentes[:5]):
                                st.write(f"- {agente}")
            
            with col3:
                if st.button("🔍 Depurar agentes", type="secondary", use_container_width=True):
                    mostrar_depuracion_agentes(st.session_state.df_analizado_actual, super_users_config)
        
        # Botones de control
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Cargar nuevo archivo", type="secondary"):
                st.session_state.analisis_realizado = False
                st.session_state.df_cargado = None
                st.session_state.df_analizado_actual = None
                if 'uploaded_file_data' in st.session_state:
                    del st.session_state.uploaded_file_data
                st.rerun()
        
        with col2:
            if st.button("📊 Ir a Panel Super Users", type="secondary"):
                st.session_state.mostrar_panel_super_usuario = True
                st.rerun()
    
    # Información de ayuda
    with st.expander("📋 ¿Cómo usar el analizador e importar datos?"):
        st.write("""
        **📊 Análisis:**
        1. 📤 **Sube tu archivo CSV/TXT** (separado por tabulaciones)
        2. 🎯 **Elige una opción** de análisis
        3. 🔍 **Haz clic en 'Aplicar análisis'** para ver resultados
        
        **📥 Importación al sistema:**
        1. **Los agentes del CSV deben coincidir** con los IDs del sistema de super users
        2. **Se importarán automáticamente:**
           - Llamadas de más de 15 minutos (900 segundos)
           - Ventas detectadas (cada UTIL POSITIVO cuenta)
           - Se suman a los datos existentes (no reemplazan)
        
        **🔄 Sistema de deduplicación:**
        - Cada registro tiene un hash único
        - Registros duplicados se ignoran automáticamente
        - Solo se actualiza si hay más datos que los existentes
        
        **📈 Conteo de ventas mejorado:**
        - Cada "UTIL POSITIVO" = 1 venta
        - Si hay LUZ y GAS en la misma línea = 2 ventas
        - Se detectan "DÚO" o "DUO" = 2 ventas
        
        **🔔 Sistema de alertas:**
        - Detecta agentes por debajo del umbral configurado
        - Calcula media de llamadas por agente
        - Muestra alertas para agentes que necesitan atención
        
        **📊 Comprobador de actividad:**
        - Verifica si agentes trabajan mínimo 50 llamadas/día
        - Calcula porcentaje de días trabajando
        - Clasifica agentes por nivel de actividad
        
        **📅 Compatibilidad:**
        - Las fechas del CSV deben estar en formato reconocible
        - Los nombres de agentes deben coincidir exactamente
        """)