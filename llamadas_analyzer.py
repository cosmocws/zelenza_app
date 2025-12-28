import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import tempfile
import io

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

def realizar_analisis(df_filtrado, nombre_analisis):
    """Realiza el análisis sobre datos filtrados"""
    
    if df_filtrado.empty:
        st.warning(f"⚠️ No hay datos para {nombre_analisis}")
        return
    
    # Limpiar datos
    df_filtrado['tiempo_conversacion'] = pd.to_numeric(df_filtrado['tiempo_conversacion'], errors='coerce')
    df_filtrado['resultado_elec'] = df_filtrado['resultado_elec'].astype(str).str.strip().str.upper()
    df_filtrado['resultado_gas'] = df_filtrado['resultado_gas'].astype(str).str.strip().str.upper()
    
    # Detectar ventas
    df_filtrado['venta'] = df_filtrado.apply(
        lambda x: 'SI' if ('UTIL POSITIVO' in str(x['resultado_elec']) or 
                          'UTIL POSITIVO' in str(x['resultado_gas'])) else 'NO', 
        axis=1
    )
    
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
        ventas_totales = len(df_filtrado[df_filtrado['venta'] == 'SI'])
        st.metric("💰 Ventas totales", ventas_totales)
    with col4:
        duracion_promedio = df_filtrado['duracion_minutos'].mean() if not df_filtrado['duracion_minutos'].isnull().all() else 0
        st.metric("⏱️ Duración promedio", f"{duracion_promedio:.1f} min")
    
    if df_llamadas_largas.empty:
        st.warning("⚠️ No hay llamadas de más de 15 minutos")
        return
    
    # Análisis por agente
    st.subheader("👥 Agentes con Llamadas Largas (>15 min)")
    
    agentes_analisis = []
    for agente in df_llamadas_largas['agente'].unique():
        llamadas_agente = df_llamadas_largas[df_llamadas_largas['agente'] == agente]
        ventas_agente = len(llamadas_agente[llamadas_agente['venta'] == 'SI'])
        
        agentes_analisis.append({
            'Agente': agente,
            'Llamadas >15 min': len(llamadas_agente),
            'Ventas >15 min': ventas_agente,
            'Tasa Conversión': f"{(ventas_agente/len(llamadas_agente)*100):.1f}%" if len(llamadas_agente) > 0 else "0%",
            'Duración Promedio (min)': f"{llamadas_agente['duracion_minutos'].mean():.1f}",
            'Duración Máxima (min)': f"{llamadas_agente['duracion_minutos'].max():.1f}"
        })
    
    if agentes_analisis:
        df_resultados = pd.DataFrame(agentes_analisis)
        df_resultados = df_resultados.sort_values('Llamadas >15 min', ascending=False)
        st.dataframe(df_resultados, use_container_width=True)
    
    # Ventas desde llamadas largas
    df_ventas_largas = df_llamadas_largas[df_llamadas_largas['venta'] == 'SI']
    
    if not df_ventas_largas.empty:
        st.subheader(f"✅ Ventas desde Llamadas Largas: {len(df_ventas_largas)}")
        
        # Mostrar detalles
        columnas_mostrar = ['agente', 'duracion_minutos', 'resultado_elec', 'resultado_gas', 'fecha', 'hora']
        df_detalle = df_ventas_largas[columnas_mostrar].copy()
        df_detalle['duracion_minutos'] = df_detalle['duracion_minutos'].round(1)
        df_detalle = df_detalle.sort_values('duracion_minutos', ascending=False)
        df_detalle.columns = ['Agente', 'Duración (min)', 'Resultado Elec', 'Resultado Gas', 'Fecha', 'Hora']
        
        st.dataframe(df_detalle.head(10), use_container_width=True)

def interfaz_analisis_llamadas():
    """Interfaz principal del analizador"""
    
    st.subheader("📊 Analizador de Llamadas Telefónicas - Zelenza")
    
    # Inicializar session_state si no existe
    if 'analisis_realizado' not in st.session_state:
        st.session_state.analisis_realizado = False
    if 'df_cargado' not in st.session_state:
        st.session_state.df_cargado = None
    
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
                    realizar_analisis(df, "TODAS las campañas")
                
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
                                ventas1 = len(df_camp1[
                                    df_camp1['resultado_elec'].str.contains('UTIL POSITIVO', na=False) |
                                    df_camp1['resultado_gas'].str.contains('UTIL POSITIVO', na=False)
                                ])
                                st.metric("Llamadas", llamadas1)
                                st.metric("Ventas", ventas1)
                                st.metric("Tasa", f"{(ventas1/llamadas1*100):.1f}%" if llamadas1 > 0 else "0%")
                        
                        with col2:
                            st.write(f"**{camp2[:30]}...**" if len(camp2) > 30 else f"**{camp2}**")
                            if not df_camp2.empty:
                                llamadas2 = len(df_camp2)
                                ventas2 = len(df_camp2[
                                    df_camp2['resultado_elec'].str.contains('UTIL POSITIVO', na=False) |
                                    df_camp2['resultado_gas'].str.contains('UTIL POSITIVO', na=False)
                                ])
                                st.metric("Llamadas", llamadas2)
                                st.metric("Ventas", ventas2)
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
                        realizar_analisis(df_filtrado, campanya_seleccionada)
                    else:
                        st.error(f"No se encontró la campaña: {campanya_seleccionada}")
        
        # Botón para resetear
        if st.button("🔄 Cargar nuevo archivo", type="secondary"):
            st.session_state.analisis_realizado = False
            st.session_state.df_cargado = None
            if 'uploaded_file_data' in st.session_state:
                del st.session_state.uploaded_file_data
            st.rerun()
    
    # Información de ayuda
    with st.expander("📋 ¿Cómo usar el analizador?"):
        st.write("""
        **Pasos:**
        1. 📤 **Sube tu archivo CSV/TXT** (separado por tabulaciones)
        2. 🎯 **Elige una opción** de análisis en el selector
        3. 🔍 **Haz clic en 'Aplicar análisis'** para ver los resultados
        
        **Campañas comunes:**
        - 📞 **CAPTACION DUAL ZELEN**: Captación de nuevos clientes
        - 🎯 **QUALITY DIF ZELENZA**: Calidad y diferenciación
        
        **Métricas clave:**
        - ⏱️ **Llamadas >15 min**: Llamadas de más de 900 segundos
        - 💰 **Ventas**: Llamadas con resultado "UTIL POSITIVO"
        - 🎯 **Tasa conversión**: % de llamadas largas que terminan en venta
        """)