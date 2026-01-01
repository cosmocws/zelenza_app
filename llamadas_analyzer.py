import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import tempfile
import io
from database import cargar_registro_llamadas, guardar_registro_llamadas

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
            return None
        
        # Limpiar datos de campaña
        df['campanya'] = df['campanya'].astype(str).str.strip()
        
        # Convertir fecha a formato estándar
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Filtrar filas con fecha inválida
        df = df.dropna(subset=['fecha'])
        
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
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📞 Llamadas totales", len(df_filtrado))
    with col2:
        st.metric("⏱️ Llamadas >15 min", len(df_llamadas_largas))
    with col3:
        # Total de ventas (sumando ventas individuales)
        ventas_totales = df_filtrado['ventas_totales'].sum()
        st.metric("💰 Ventas totales", int(ventas_totales))
    with col4:
        duracion_promedio = df_filtrado['duracion_minutos'].mean() if not df_filtrado['duracion_minutos'].isnull().all() else 0
        st.metric("⏱️ Duración promedio", f"{duracion_promedio:.1f} min")
    
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
    Importa los datos analizados al registro diario de super usuarios
    """
    if df_analizado.empty:
        return False, "No hay datos para importar"
    
    # Cargar registro actual
    registro_llamadas = cargar_registro_llamadas()
    
    # Obtener agentes del sistema
    agentes_sistema = super_users_config.get("agentes", {})
    
    # Contadores
    agentes_encontrados = []
    agentes_no_encontrados = []
    llamadas_importadas = 0
    ventas_importadas = 0
    
    # Procesar cada fila del análisis
    for _, row in df_analizado.iterrows():
        agente_id = str(row['agente']).strip()
        fecha_str = row['fecha']
        
        # Verificar si el agente existe en el sistema
        if agente_id in agentes_sistema:
            # Inicializar día si no existe
            if fecha_str not in registro_llamadas:
                registro_llamadas[fecha_str] = {}
            
            # Inicializar agente para el día si no existe
            if agente_id not in registro_llamadas[fecha_str]:
                registro_llamadas[fecha_str][agente_id] = {
                    'llamadas': 0,
                    'ventas': 0,
                    'fecha': fecha_str,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Agregar llamada si es >15 min (900 segundos)
            if row['tiempo_conversacion'] > 900:
                registro_llamadas[fecha_str][agente_id]['llamadas'] += 1
                llamadas_importadas += 1
            
            # Agregar ventas (pueden ser 0, 1 o 2 por línea)
            ventas_fila = int(row['ventas_totales'])
            if ventas_fila > 0:
                registro_llamadas[fecha_str][agente_id]['ventas'] += ventas_fila
                ventas_importadas += ventas_fila
            
            if agente_id not in agentes_encontrados:
                agentes_encontrados.append(agente_id)
        
        else:
            if agente_id not in agentes_no_encontrados:
                agentes_no_encontrados.append(agente_id)
    
    # Guardar cambios
    guardar_registro_llamadas(registro_llamadas)
    
    # Preparar mensaje de resumen
    mensaje = f"✅ **Importación completada:**\n"
    mensaje += f"- 📅 Fechas procesadas: {df_analizado['fecha'].nunique()}\n"
    mensaje += f"- 👥 Agentes encontrados: {len(agentes_encontrados)}\n"
    mensaje += f"- 📞 Llamadas >15min importadas: {llamadas_importadas}\n"
    mensaje += f"- 💰 Ventas importadas: {ventas_importadas}\n"
    
    if agentes_no_encontrados:
        mensaje += f"\n⚠️ **Agentes no encontrados en el sistema:**\n"
        for i, agente in enumerate(agentes_no_encontrados[:10]):
            mensaje += f"- {agente}\n"
        if len(agentes_no_encontrados) > 10:
            mensaje += f"- ... y {len(agentes_no_encontrados) - 10} más\n"
    
    return True, mensaje

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
            from database import cargar_super_users
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
            
            col_import1, col_import2 = st.columns(2)
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
                    from database import cargar_registro_llamadas
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
        
        **📈 Conteo de ventas mejorado:**
        - Cada "UTIL POSITIVO" = 1 venta
        - Si hay LUZ y GAS en la misma línea = 2 ventas
        - Se detectan "DÚO" o "DUO" = 2 ventas
        
        **📅 Compatibilidad:**
        - Las fechas del CSV deben estar en formato reconocible
        - Los nombres de agentes deben coincidir exactamente
        """)