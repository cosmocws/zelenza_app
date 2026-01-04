import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import tempfile
import io
from database import cargar_registro_llamadas, guardar_registro_llamadas, cargar_super_users
import json
import hashlib

def calcular_hash_registro(registro):
    """Calcula un hash único para un registro"""
    # Crear string único con los datos relevantes
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
        if '\t' in first_line:
            separator = '\t'
            st.info("📄 Archivo detectado como separado por TABULACIONES")
        else:
            separator = ','
        
        # Leer el archivo
        df = pd.read_csv(tmp_path, sep=separator, encoding='utf-8')
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Verificar columnas necesarias
        columnas_requeridas = ['agente', 'tiempo_conversacion', 'resultado_elec', 'resultado_gas', 'fecha', 'hora', 'campanya']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            st.error(f"❌ Faltan columnas: {', '.join(columnas_faltantes)}")
            st.info("Columnas encontradas:")
            for col in df.columns:
                st.write(f"- {col}")
            return None
        
        # Limpiar datos de campaña
        df['campanya'] = df['campanya'].astype(str).str.strip()
        
        # Convertir fecha a formato estándar
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Filtrar filas con fecha inválida
        df = df.dropna(subset=['fecha'])
        
        # Añadir hash único para cada registro
        df['hash'] = df.apply(calcular_hash_registro, axis=1)
        
        # Mostrar campañas encontradas
        campanyas_unicas = df['campanya'].unique()
        st.success(f"✅ **Campañas detectadas ({len(campanyas_unicas)}):**")
        
        # Crear lista para mostrar
        for i, camp in enumerate(campanyas_unicas[:10]):
            st.write(f"{i+1}. {camp}")
        
        if len(campanyas_unicas) > 10:
            st.info(f"... y {len(campanyas_unicas) - 10} más")
        
        # Guardar datos en session_state para usar después
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
    """Cuenta ventas en un resultado (puede haber LUZ y GAS en la misma línea)"""
    if pd.isna(resultado_str):
        return 0
    
    resultado = str(resultado_str).upper()
    
    # Si es UTIL POSITIVO, cuenta 1 venta
    if 'UTIL POSITIVO' in resultado:
        # Verificar si hay indicadores de doble venta
        if ('LUZ' in resultado and 'GAS' in resultado) or ('DÚO' in resultado or 'DUO' in resultado):
            # Si menciona ambos o dice DÚO, son 2 ventas
            return 2
        else:
            # Solo una venta (podría ser luz o gas)
            return 1
    else:
        return 0

def realizar_analisis(df_filtrado, nombre_analisis):
    """Realiza el análisis sobre datos filtrados"""
    
    if df_filtrado.empty:
        st.warning(f"⚠️ No hay datos para {nombre_analisis}")
        return None
    
    # Limpiar datos
    df_filtrado['tiempo_conversacion'] = pd.to_numeric(df_filtrado['tiempo_conversacion'], errors='coerce')
    df_filtrado['resultado_elec'] = df_filtrado['resultado_elec'].astype(str).str.strip()
    df_filtrado['resultado_gas'] = df_filtrado['resultado_gas'].astype(str).str.strip()
    
    # Calcular ventas por llamada (pueden ser 0, 1 o 2 ventas por línea)
    df_filtrado['ventas_elec'] = df_filtrado['resultado_elec'].apply(contar_ventas_resultado)
    df_filtrado['ventas_gas'] = df_filtrado['resultado_gas'].apply(contar_ventas_resultado)
    df_filtrado['ventas_totales'] = df_filtrado['ventas_elec'] + df_filtrado['ventas_gas']
    
    # Llamadas con venta (al menos 1 venta)
    df_filtrado['tiene_venta'] = df_filtrado['ventas_totales'] > 0
    
    df_filtrado['duracion_minutos'] = df_filtrado['tiempo_conversacion'] / 60
    
    # Llamadas largas (>15 min = 900 segundos)
    df_llamadas_largas = df_filtrado[df_filtrado['tiempo_conversacion'] > 900].copy()
    
    # Estadísticas
    st.subheader(f"📊 Análisis: {nombre_analisis}")
    
    # CALCULAR NUEVO KPI: Media de llamadas por agente
    total_llamadas = len(df_filtrado)
    total_agentes = df_filtrado['agente'].nunique()
    media_llamadas_por_agente = total_llamadas / total_agentes if total_agentes > 0 else 0
    
    # Contar llamadas largas
    llamadas_largas = len(df_llamadas_largas)
    
    # Calcular ventas totales
    ventas_totales = df_filtrado['ventas_totales'].sum()
    
    # Calcular duración promedio
    duracion_promedio = df_filtrado['duracion_minutos'].mean() if not df_filtrado['duracion_minutos'].isnull().all() else 0
    
    # ACTUALIZAR LAS COLUMNAS: Añadir una quinta columna para el nuevo KPI
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📞 Llamadas totales", total_llamadas)
    with col2:
        st.metric("⏱️ Llamadas >15 min", llamadas_largas)
    with col3:
        st.metric("💰 Ventas totales", int(ventas_totales))
    with col4:
        st.metric("⏱️ Duración promedio", f"{duracion_promedio:.1f} min")
    with col5:
        # NUEVO KPI: Media de llamadas por agente
        st.metric("👥 Media llamadas/agente", f"{media_llamadas_por_agente:.1f}")
    
    # Análisis por agente
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
    
    # Ventas desde llamadas largas
    df_ventas_largas = df_llamadas_largas[df_llamadas_largas['tiene_venta'] == True]
    
    if not df_ventas_largas.empty:
        st.subheader(f"✅ Ventas desde Llamadas Largas: {int(df_ventas_largas['ventas_totales'].sum())}")
        
        # Mostrar detalles
        columnas_mostrar = ['agente', 'duracion_minutos', 'resultado_elec', 'resultado_gas', 'ventas_totales', 'fecha', 'hora']
        df_detalle = df_ventas_largas[columnas_mostrar].copy()
        df_detalle['duracion_minutos'] = df_detalle['duracion_minutos'].round(1)
        df_detalle = df_detalle.sort_values('duracion_minutos', ascending=False)
        df_detalle.columns = ['Agente', 'Duración (min)', 'Resultado Elec', 'Resultado Gas', 'Ventas', 'Fecha', 'Hora']
        
        st.dataframe(df_detalle.head(10), use_container_width=True)
    
    return df_filtrado

def importar_datos_a_registro(df_analizado, super_users_config):
    """
    Importa los datos analizados al registro diario
    CORRECCIÓN: Cuenta TODAS las líneas, no solo las procesadas
    """
    import streamlit as st
    from datetime import datetime
    
    if df_analizado.empty:
        return False, "No hay datos para importar"
    
    # Cargar registro actual
    registro_llamadas = cargar_registro_llamadas()
    
    # Obtener agentes del sistema
    agentes_sistema = super_users_config.get("agentes", {})
    
    # Contadores REALES
    total_lineas_csv = len(df_analizado)  # ESTO ES 4239
    lineas_procesadas = 0
    lineas_no_procesadas = 0
    llamadas_totales_importadas = 0  # Debería ser 4239 si todo va bien
    llamadas_largas_importadas = 0
    ventas_importadas = 0
    
    agentes_encontrados_lista = []
    agentes_no_encontrados_set = set()
    coincidencias_unicas = set()  # Para evitar duplicados en la lista
    
    # Preparar búsqueda flexible
    # Crear diccionario de búsqueda por diferentes variantes
    busqueda_agentes = {}
    
    for agent_id in agentes_sistema.keys():
        agent_id_str = str(agent_id).strip().upper()
        
        # Variante 1: ID completo
        busqueda_agentes[agent_id_str] = agent_id
        
        # Variante 2: Solo últimos dígitos (si tiene al menos 4)
        if len(agent_id_str) >= 4:
            ultimos_4 = agent_id_str[-4:]
            busqueda_agentes[ultimos_4] = agent_id
        
        # Variante 3: Sin prefijos comunes
        if agent_id_str.startswith('TZS'):
            sin_tzs = agent_id_str[3:]
            busqueda_agentes[sin_tzs] = agent_id
        
        # Variante 4: Solo números
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
            # Extraer números del agente CSV
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
            
            # CONTAR LLAMADA TOTAL (CADA LÍNEA ES UNA LLAMADA)
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
    
    # PREPARAR MENSAJE CLARO
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
        # Mostrar algunos ejemplos
        ejemplos = list(agentes_no_encontrados_set)[:5]
        for ej in ejemplos:
            mensaje += f"  - '{ej}'\n"
        
        # Sugerencias
        mensaje += f"\n💡 **¿Por qué no se encuentran?**\n"
        mensaje += f"1. Los IDs no coinciden (ej: '0733' vs 'TZS0733')\n"
        mensaje += f"2. Agentes no están configurados en Super Users\n"
        mensaje += f"3. Errores de formato en el CSV\n"
        
        # Mostrar agentes disponibles en el sistema
        mensaje += f"\n📋 **Agentes configurados en el sistema ({len(agentes_sistema)}):**\n"
        for i, (agent_id, info) in enumerate(list(agentes_sistema.items())[:10]):
            nombre = info.get('nombre', 'Sin nombre')
            mensaje += f"  {i+1}. `{agent_id}`: {nombre}\n"
        if len(agentes_sistema) > 10:
            mensaje += f"  ... y {len(agentes_sistema) - 10} más\n"
    
    return True, mensaje

def verificacion_rapida_importacion():
    """Verificación rápida de qué está pasando en la importación"""
    
    st.subheader("🔍 Verificación Rápida de Importación")
    
    if 'df_analizado_actual' not in st.session_state:
        st.warning("No hay datos CSV cargados")
        return
    
    df = st.session_state.df_analizado_actual
    from database import cargar_super_users
    super_users_config = cargar_super_users()
    agentes_sistema = super_users_config.get("agentes", {})
    
    st.write(f"### 📊 Datos del CSV:")
    st.write(f"- Total líneas: {len(df)}")
    
    # Contar agentes únicos en CSV
    agentes_csv = df['agente'].unique()
    st.write(f"- Agentes únicos en CSV: {len(agentes_csv)}")
    
    # Verificar coincidencias rápidas
    coincidencias = 0
    no_coincidencias = []
    
    for agente_csv in agentes_csv[:50]:  # Revisar primeros 50
        agente_str = str(agente_csv).strip().upper()
        encontrado = False
        
        for agent_id in agentes_sistema.keys():
            if (agente_str == str(agent_id).upper() or
                agente_str in str(agent_id).upper() or
                str(agent_id).upper() in agente_str):
                coincidencias += 1
                encontrado = True
                break
        
        if not encontrado:
            no_coincidencias.append(agente_str)
    
    st.write(f"### 🔗 Coincidencias (primeros 50 agentes):")
    st.write(f"- Con coincidencia: {coincidencias}")
    st.write(f"- Sin coincidencia: {len(no_coincidencias)}")
    
    if no_coincidencias:
        st.write("**Ejemplos sin coincidencia:**")
        for ej in no_coincidencias[:10]:
            st.write(f"- '{ej}'")

def mostrar_depuracion_agentes(df_analizado, super_users_config):
    """Muestra información de depuración para coincidencia de agentes"""
    
    st.subheader("🔍 Depuración: Coincidencia de Agentes")
    
    # Obtener agentes del CSV
    agentes_csv = sorted(df_analizado['agente'].astype(str).str.strip().unique())
    
    # Obtener agentes del sistema
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
    
    # Coincidencias directas
    st.write("### 🔍 Búsqueda de coincidencias")
    
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
        
        if not encontrado:
            # Búsqueda parcial
            for agent_id in agentes_sistema.keys():
                agent_id_clean = str(agent_id).upper()
                # Buscar similitudes
                if (agente_csv_clean in agent_id_clean or 
                    agent_id_clean in agente_csv_clean or
                    agente_csv_clean[-4:] == agent_id_clean[-4:]):  # Últimos 4 dígitos
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
    
    # Obtener configuración
    configuracion = super_users_config.get("configuracion", {})
    umbral_alerta = configuracion.get("umbral_alertas_llamadas", 20)
    minimo_llamadas_dia = configuracion.get("minimo_llamadas_dia", 50)
    
    # Calcular media de llamadas por agente
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
        
        # Verificar si está activo (más del mínimo diario)
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
        
        # Recomendaciones
        st.write("**💡 Recomendaciones:**")
        st.write("1. Revisar actividad de estos agentes")
        st.write("2. Verificar posibles problemas técnicos")
        st.write("3. Considerar capacitación adicional")
        st.write("4. Establecer objetivos personalizados")
    else:
        st.success("🎉 **Todos los agentes están dentro del rango esperado**")
    
    # Mostrar resumen general
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
    
    # Configuración
    MINIMO_LLAMADAS_DIA = 50
    
    # Agrupar por agente y fecha
    actividad = df_analizado.groupby(['agente', 'fecha']).size().reset_index(name='llamadas')
    
    # Contar días trabajando vs no trabajando
    resumen_agentes = []
    
    for agente in actividad['agente'].unique():
        df_agente = actividad[actividad['agente'] == agente]
        
        dias_totales = df_agente['fecha'].nunique()
        dias_trabajando = len(df_agente[df_agente['llamadas'] >= MINIMO_LLAMADAS_DIA])
        dias_no_trabajando = dias_totales - dias_trabajando
        
        # Calcular porcentaje
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
        
        # Mostrar tabla
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
        
        # Mostrar detalles para agentes críticos
        agentes_criticos_lista = [a for a in resumen_agentes if a['Estado'] == '❌']
        if agentes_criticos_lista:
            st.warning("### 🔴 Agentes con Baja Actividad Crítica")
            st.write("Estos agentes trabajan menos del 50% de los días:")
            
            for agente in agentes_criticos_lista:
                st.write(f"- **{agente['Agente']}**: {agente['Días Trabajando']}/{agente['Días Totales']} días ({agente['% Trabajando']})")
        
        # Gráfico de actividad
        st.write("### 📊 Distribución de Actividad")
        
        # Preparar datos para gráfico
        estados_counts = {
            '✅ Óptimos (>80%)': agentes_ok,
            '⚠️ Atención (50-79%)': agentes_alerta,
            '❌ Críticos (<50%)': agentes_critico
        }
        
        import plotly.express as px
        
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
    
    # Inicializar session_state si no existe
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
    
    # Procesar archivo cuando se sube
    if uploaded_file is not None and not st.session_state.analisis_realizado:
        with st.spinner("📂 Cargando y procesando archivo..."):
            df = analizar_csv_llamadas(uploaded_file)
            if df is not None:
                st.session_state.df_cargado = df
                st.session_state.analisis_realizado = True
                st.rerun()  # Forzar rerun para mostrar opciones
    
    # Mostrar opciones de análisis si hay datos cargados
    if st.session_state.df_cargado is not None:
        df = st.session_state.df_cargado
        
        # Obtener campañas únicas
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
        
        # Añadir otras campañas (máximo 5)
        otras_campanyas = 0
        for camp in campanyas:
            camp_str = str(camp)
            if f"📞 {camp}" not in opciones and f"🎯 {camp}" not in opciones and otras_campanyas < 3:
                opciones.append(f"📋 {camp[:40]}..." if len(camp_str) > 40 else f"📋 {camp}")
                otras_campanyas += 1
        
        # Si hay al menos 2 campañas, añadir opción de comparar
        if len(campanyas) >= 2:
            opciones.append("🔄 COMPARAR campañas principales")
        
        # Opciones adicionales de análisis
        opciones.append("🔔 Verificar alertas de actividad")
        opciones.append("📊 Comprobar actividad diaria")
        
        # Selector que NO causa rerun inmediato
        seleccion = st.selectbox(
            "Elige una opción de análisis:",
            opciones,
            key="selector_campanya"
        )
        
        # Botón para aplicar la selección
        if st.button("🔍 Aplicar análisis", type="primary", key="aplicar_analisis"):
            with st.spinner("Analizando datos..."):
                
                if "TODAS" in seleccion:
                    df_analizado = realizar_analisis(df, "TODAS las campañas")
                    st.session_state.df_analizado_actual = df_analizado
                
                elif "COMPARAR" in seleccion and len(campanyas) >= 2:
                    st.subheader("🔄 Comparativa entre Campañas")
                    
                    # Comparar las dos primeras campañas encontradas
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
                    # Cargar configuración de super users
                    super_users_config = cargar_super_users()
                    verificar_agentes_con_alerta(df, super_users_config)
                
                elif "📊 Comprobar actividad diaria" in seleccion:
                    comprobador_actividad_diaria(df)
                
                else:
                    # Extraer el nombre real de la campaña (quitando el emoji)
                    campanya_seleccionada = seleccion[2:]  # Quitar emoji + espacio
                    
                    # Buscar coincidencia exacta o parcial
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
        
        # Importar datos al sistema de super usuarios
        if st.session_state.df_analizado_actual is not None and not st.session_state.df_analizado_actual.empty:
            st.subheader("3. 📥 Importar al Sistema de Agentes")
            
            # Cargar configuración de super usuarios
            super_users_config = cargar_super_users()
            
            # Mostrar vista previa de lo que se importará
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
                
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                with col_stats1:
                    st.metric("👥 Agentes", agentes_unicos)
                with col_stats2:
                    st.metric("📅 Fechas", fechas_unicas)
                with col_stats3:
                    st.metric("📞 Llamadas >15min", llamadas_largas)
                with col_stats4:
                    st.metric("💰 Ventas", int(ventas_totales))
            
            # Confirmación de importación
            st.info("💡 **Importará:** Llamadas >15min y ventas al registro diario de agentes")
            st.warning("⚠️ **Advertencia:** Los datos existentes para las mismas fechas y agentes serán sumados, no reemplazados.")
            st.info("🔄 **Deduplicación:** Se evitan duplicados mediante sistema de hashes")
            
            col_import1, col_import2, col_import3 = st.columns(3)
            with col_import1:
                if st.button("📥 Importar Datos", type="primary", use_container_width=True):
                    with st.spinner("Importando datos al sistema..."):
                        exito, mensaje = importar_datos_a_registro(
                            st.session_state.df_analizado_actual, 
                            super_users_config
                        )
                        
                        if exito:
                            st.success("✅ Datos importados exitosamente")
                            # Mostrar mensaje detallado
                            for linea in mensaje.split('\n'):
                                if linea.strip():
                                    st.write(linea)
                        else:
                            st.error(f"❌ Error al importar: {mensaje}")
            
            with col_import2:
                if st.button("🧹 Limpiar y Probar", type="secondary", use_container_width=True):
                    # Probar importación sin guardar
                    registro_actual = cargar_registro_llamadas()
                    
                    # Simular importación
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
            
            with col_import3:
                if st.button("🔍 Depurar agentes", type="secondary", use_container_width=True):
                    mostrar_depuracion_agentes(st.session_state.df_analizado_actual, super_users_config)
        
        # Botones de control
        col_control1, col_control2 = st.columns(2)
        with col_control1:
            if st.button("🔄 Cargar nuevo archivo", type="secondary"):
                st.session_state.analisis_realizado = False
                st.session_state.df_cargado = None
                st.session_state.df_analizado_actual = None
                if 'uploaded_file_data' in st.session_state:
                    del st.session_state.uploaded_file_data
                st.rerun()
        
        with col_control2:
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