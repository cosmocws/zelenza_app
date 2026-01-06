# monitorizacion_utils.py
import streamlit as st
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configuración global - ACTUALIZADA CON TODOS LOS PUNTOS CLAVE
OPCIONES_PUNTOS_CLAVE = [
    # Originales
    "LOPD", "Comunicación", "Cierre de venta", "Argumentación", 
    "Resolución objeciones", "Proceso venta", "Escucha activa", "Tono",
    "Estructura", "Detección", "Habilidades venta", "Verificación", "Otros",
    
    # Nuevos de la función de detección SI/NO
    "Actitud",
    "Sondeo",
    "Oportunidad venta",
    "Resumen beneficios",
    "Gestión BBDD",
    "Textos legales",
    "Argumentación ¡CUIDADO!",
    "Textos legales ¡CUIDADO!",
    "LOPD ¡CUIDADO!",
    "Sondeo ¡CUIDADO!",
    "Gestión BBDD ¡CUIDADO!"
]

def check_ocr_dependencies() -> List[str]:
    """Verifica si las dependencias de OCR están instaladas"""
    missing_deps = []
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing_deps.append("PyMuPDF (pip install PyMuPDF)")
    
    return missing_deps

def analizar_pdf_monitorizacion(uploaded_file) -> Dict[str, Any]:
    """
    Analiza el PDF de monitorización y extrae los datos
    """
    missing = check_ocr_dependencies()
    if missing:
        st.error(f"❌ Faltan dependencias: {', '.join(missing)}")
        st.info("Ejecuta: pip install PyMuPDF")
        return _datos_ejemplo_desarrollo()
    
    try:
        import fitz  # PyMuPDF
        
        # Leer el PDF
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Extraer texto de todas las páginas
        texto_completo = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            texto_completo += page.get_text() + "\n"
        
        doc.close()
        
        if not texto_completo.strip():
            st.warning("⚠️ No se pudo extraer texto del PDF.")
            return _datos_ejemplo_desarrollo()
        
        # Analizar el texto extraído
        datos_extraidos = _crear_estructura_datos_vacia()
        return _analizar_texto_monitorizacion(texto_completo, datos_extraidos)
        
    except Exception as e:
        st.error(f"❌ Error al analizar PDF: {str(e)}")
        return _datos_ejemplo_desarrollo()

def _crear_estructura_datos_vacia() -> Dict[str, Any]:
    """Crea una estructura vacía para los datos extraídos"""
    return {
        'id_empleado': None,
        'fecha_monitorizacion': None,
        'nota_global': None,
        'objetivo': 85.0,
        'experiencia': None,
        'comunicacion': None,
        'deteccion': None,
        'habilidades_venta': None,
        'resolucion_objeciones': None,
        'cierre_contacto': None,
        'feedback': "",
        'plan_accion': "",
        'puntos_clave': []
    }

def _analizar_texto_monitorizacion(texto: str, datos_extraidos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza el texto extraído del PDF y extrae los datos de monitorización
    """
    try:
        # Normalizar texto
        texto_normalizado = texto
        texto_upper = texto.upper()
        
        # ========== ID EMPLEADO ==========
        patron_id = r'ID\s*EMPLEADO\s*(\d+)'
        match_id = re.search(patron_id, texto_upper)
        if match_id:
            datos_extraidos['id_empleado'] = int(match_id.group(1))
        
        # ========== FECHA MONITORIZACIÓN ==========
        patron_fecha = r'FECHA\s*MONITORIZACI[OÓ]N\s*(\d+)[-/](\d+)'
        match_fecha = re.search(patron_fecha, texto_upper)
        if match_fecha:
            try:
                dia = int(match_fecha.group(1))
                mes = int(match_fecha.group(2))
                año = datetime.now().year
                
                if mes > datetime.now().month:
                    año -= 1
                
                datos_extraidos['fecha_monitorizacion'] = f"{año:04d}-{mes:02d}-{dia:02d}"
            except:
                pass
        
        # ========== NOTA GLOBAL ==========
        patron_nota = r'NOTA\s*GLOBAL\s*([\d,]+)%'
        match_nota = re.search(patron_nota, texto_normalizado)
        if match_nota:
            try:
                nota_str = match_nota.group(1).replace(',', '.')
                datos_extraidos['nota_global'] = float(nota_str)
            except:
                pass
        
        # ========== OBJETIVO ==========
        patron_objetivo = r'OBJETIVO\s*(\d+)%'
        match_objetivo = re.search(patron_objetivo, texto_upper)
        if match_objetivo:
            try:
                datos_extraidos['objetivo'] = float(match_objetivo.group(1))
            except:
                datos_extraidos['objetivo'] = 85.0
        
        # ========== PUNTUACIONES POR ÁREA ==========
        
        # EXPERIENCIA
        patron_experiencia = r'1\.\s*EXPERIENCIA\s*([\d,]+)%'
        match_exp = re.search(patron_experiencia, texto_normalizado)
        if match_exp:
            try:
                exp_str = match_exp.group(1).replace(',', '.')
                datos_extraidos['experiencia'] = float(exp_str)
            except:
                pass
        
        # COMUNICACIÓN
        patron_comunicacion = r'1\.1\.\s*COMUNICACI[OÓ]N\s*(\d+)%'
        match_com = re.search(patron_comunicacion, texto_normalizado)
        if match_com:
            try:
                datos_extraidos['comunicacion'] = float(match_com.group(1))
            except:
                pass
        
        # DETECCIÓN
        patron_deteccion = r'2\.1\s*DETECCI[OÓ]N\s*(\d+)%'
        match_det = re.search(patron_deteccion, texto_upper)
        if match_det:
            try:
                datos_extraidos['deteccion'] = float(match_det.group(1))
            except:
                pass
        
        # HABILIDADES DE VENTA
        patron_habilidades = r'2\.2\s*HABILIDADES\s*DE\s*VENTA\s*(\d+)%'
        match_hab = re.search(patron_habilidades, texto_upper)
        if match_hab:
            try:
                datos_extraidos['habilidades_venta'] = float(match_hab.group(1))
            except:
                pass
        
        # RESOLUCIÓN DE OBJECIONES
        patron_objeciones = r'2\.3\s*RESOLUCI[OÓ]N\s*DE\s*OBJECIONES\s*(\d+)%'
        match_obj = re.search(patron_objeciones, texto_upper)
        if match_obj:
            try:
                datos_extraidos['resolucion_objeciones'] = float(match_obj.group(1))
            except:
                pass
        
        # CIERRE DE CONTACTO
        patron_cierre = r'2\.4\s*CIERRE\s*DE\s*CONTACTO\s*(\d+)%'
        match_cierre = re.search(patron_cierre, texto_upper)
        if match_cierre:
            try:
                datos_extraidos['cierre_contacto'] = float(match_cierre.group(1))
            except:
                pass
        
        # ========== DETECTAR PUNTOS CLAVE AUTOMÁTICAMENTE ==========
        puntos_clave = _detectar_puntos_clave_automatico(texto_normalizado)
        datos_extraidos['puntos_clave'] = puntos_clave
        
        # ========== SEPARAR FEEDBACK Y PLAN DE ACCIÓN ==========
        if 'FECHA Y FIRMA' in texto_normalizado:
            partes = texto_normalizado.split('FECHA Y FIRMA', 1)
        else:
            partes = [""]
            if 'VERIFICACIÓN DE VENTA' in texto_normalizado:
                partes = texto_normalizado.rsplit('VERIFICACIÓN DE VENTA', 1)
            elif 'PROCESO DE VENTA' in texto_normalizado:
                partes = texto_normalizado.rsplit('PROCESO DE VENTA', 1)
        
        if len(partes) > 1:
            texto_feedback = partes[1].strip()
            
            feedback, plan_accion = _separar_feedback_plan_accion(texto_feedback)
            
            datos_extraidos['feedback'] = feedback[:2000] if feedback else ""
            datos_extraidos['plan_accion'] = plan_accion[:2000] if plan_accion else ""
        
        # Validar datos mínimos
        if datos_extraidos['id_empleado'] is None:
            st.warning("⚠️ No se pudo extraer el ID de empleado del PDF")
        
        return datos_extraidos
        
    except Exception as e:
        st.error(f"❌ Error al analizar texto: {str(e)}")
        return _datos_ejemplo_desarrollo()
    
def _detectar_puntos_clave_automatico(texto: str) -> List[str]:
    """Detecta puntos clave automáticamente basándose en respuestas SI/NO del PDF"""
    puntos_clave = []
    
    # Preprocesar el texto: buscar las respuestas correctamente
    # Dividir por líneas para analizar mejor
    lineas = texto.split('\n')
    
    # Mapeo de preguntas a puntos clave
    mapeo_preguntas = {
        # ========== SECCIÓN 1.1 ==========
        '1.1 A)': ("Tono", r'1\.1\s*A\)\s*Utiliza un estilo comunicativo.*?\s*(SI|NO|N/A)', 1),
        '1.1 B)': ("Estructura", r'1\.1\s*B\)\s*No construye un mensaje.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 1.2 ==========
        '1.2 A)': ("Argumentación", r'1\.2\s*A\)\s*Perjudica.*?\s*(SI|NO|N/A)', 1),
        '1.2 B)': ("Tono", r'1\.2\s*B\)\s*Presiona.*?\s*(SI|NO|N/A)', 1),
        '1.2 C)': ("Escucha activa", r'1\.2\s*C\)\s*No escucha.*?\s*(SI|NO|N/A)', 1),
        '1.2 D)': ("Actitud", r'1\.2\s*D\)\s*Su actitud.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 2.1 ==========
        '2.1 A)': ("Sondeo", r'2\.1\s*A\)\s*No sondea.*?\s*(SI|NO|N/A)', 1),
        '2.1 B)': ("Detección", r'2\.1\s*B\)\s*No identifica.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 2.2 ==========
        '2.2 A)': ("Oportunidad venta", r'2\.2\s*A\)\s*No presenta.*?\s*(SI|NO|N/A)', 1),
        '2.2 B)': ("Resumen beneficios", r'2\.2\s*B\)\s*No usa técnicas.*?\s*(SI|NO|N/A)', 1),
        '2.2 C)': ("Oportunidad venta", r'2\.2\s*C\)\s*No aprovecha.*?\s*(SI|NO|N/A)', 1),
        '2.2 D)': ("Argumentación", r'2\.2\s*D\)\s*Utiliza argumentos.*?\s*(SI|NO|N/A)', 1),
        '2.2 E)': ("Cierre de venta", r'2\.2\s*E\)\s*No lanza.*?\s*(SI|NO|N/A)', 1),
        '2.2 F)': ("Gestión BBDD", r'2\.2\s*F\)\s*No realiza.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 2.3 ==========
        '2.3 A)': ("Resolución objeciones", r'2\.3\s*A\)\s*No responde.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 2.4 ==========
        '2.4 A)': ("Resumen beneficios", r'2\.4\s*A\)\s*Cuando es necesario.*?\s*(SI|NO|N/A)', 1),
        '2.4 B)': ("Resolución objeciones", r'2\.4\s*B\)\s*No informa.*?\s*(SI|NO|N/A)', 1),
        '2.4 C)': ("Sondeo", r'2\.4\s*C\)\s*No propone.*?\s*(SI|NO|N/A)', 1),
        '2.4 D)': ("Gestión BBDD", r'2\.4\s*D\)\s*No tipifica.*?\s*(SI|NO|N/A)', 1),
        '2.4 E)': ("Gestión BBDD", r'2\.4\s*E\)\s*No tipifica.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 3.1 ==========
        '3.1 A)': ("Sondeo", r'3\.1\s*A\)\s*Realiza.*?\s*(SI|NO|N/A)', 1),
        '3.1 B)': ("Argumentación ¡CUIDADO!", r'3\.1\s*B\)\s*Ofrece.*?\s*(SI|NO|N/A)', 1),
        '3.1 C)': ("Argumentación ¡CUIDADO!", r'3\.1\s*C\)\s*Utiliza.*?\s*(SI|NO|N/A)', 1),
        '3.1 D)': ("Textos legales", r'3\.1\s*D\)\s*No sigue.*?\s*(SI|NO|N/A)', 1),
        '3.1 E)': ("Textos legales ¡CUIDADO!", r'3\.1\s*E\)\s*No lee.*?\s*(SI|NO|N/A)', 1),
        '3.1 F)': ("Argumentación ¡CUIDADO!", r'3\.1\s*F\)\s*No explica.*?\s*(SI|NO|N/A)', 1),
        '3.1 G)': ("LOPD ¡CUIDADO!", r'3\.1\s*G\)\s*No informa.*?\s*(SI|NO|N/A)', 1),
        
        # ========== SECCIÓN 3.2 ==========
        '3.2 A)': ("Sondeo ¡CUIDADO!", r'3\.2\s*A\)\s*No identifica.*?\s*(SI|NO|N/A)', 1),
        '3.2 B)': ("Argumentación ¡CUIDADO!", r'3\.2\s*B\)\s*No informa.*?\s*(SI|NO|N/A)', 1),
        '3.2 C)': ("Gestión BBDD ¡CUIDADO!", r'3\.2\s*C\)\s*No gestiona.*?\s*(SI|NO|N/A)', 1),
    }
    
    # Buscar cada pregunta específicamente
    for pregunta_id, (punto_clave, patron, grupo_respuesta) in mapeo_preguntas.items():
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if match:
            respuesta = match.group(grupo_respuesta).upper()
            if respuesta == 'SI':
                puntos_clave.append(punto_clave)
    
    # Eliminar duplicados manteniendo orden
    puntos_unicos = []
    for punto in puntos_clave:
        if punto not in puntos_unicos:
            puntos_unicos.append(punto)
    
    return puntos_unicos

def _separar_feedback_plan_accion(texto_feedback: str) -> tuple[str, str]:
    """Separa el feedback del plan de acción"""
    feedback = texto_feedback
    plan_accion = ""
    
    separadores = [
        'LOPD Sigue así',
        'Plan de acción:',
        'Acciones:',
        'Para mejorar:',
        'Próximos pasos:',
        'Vamos a:',
        'Recomendaciones:',
        'Acciones a tomar:'
    ]
    
    for separador in separadores:
        if separador in texto_feedback:
            partes = texto_feedback.split(separador, 1)
            if len(partes) > 1:
                feedback = partes[0].strip()
                plan_accion = separador + " " + partes[1].strip()
                break
    
    if not plan_accion:
        lineas = texto_feedback.split('\n')
        if len(lineas) > 3:
            mitad = len(lineas) // 2
            feedback = '\n'.join(lineas[:mitad]).strip()
            plan_accion = '\n'.join(lineas[mitad:]).strip()
        else:
            feedback = texto_feedback
            plan_accion = ""
    
    return feedback, plan_accion

def _datos_ejemplo_desarrollo() -> Dict[str, Any]:
    """Retorna datos de ejemplo para desarrollo"""
    return {
        'id_empleado': 1556,
        'fecha_monitorizacion': '2024-01-05',
        'nota_global': 31.67,
        'objetivo': 85.0,
        'experiencia': 80.0,
        'comunicacion': 50.0,
        'deteccion': 50.0,
        'habilidades_venta': 67.0,
        'resolucion_objeciones': 100.0,
        'cierre_contacto': 100.0,
        'feedback': "T250891. LOPD SI, Buena entrada. Necesitamos ser más claros en lo que vamos a hacer y cómo lo vamos a hacer. En este tipo de llamadas, que parece que el cliente nos va 'tomando el pelo', tenemos que cambiar a un tono mucho más serio y seguir la estructura de la argumentación bien, o podemos perder las riendas de la llamada.",
        'plan_accion': "1. Cambiar a tono más serio cuando el cliente no muestra interés real\n2. Seguir la estructura de argumentación paso a paso\n3. Ser más claro al explicar la comparativa de precios\n4. Practicar el manejo de objeciones comunes\n5. Si no hay mejora, agradecer y finalizar la llamada profesionalmente",
        'puntos_clave': ["Sondeo", "Resumen beneficios"]  # Lo que detectaría del PDF real
    }

def guardar_monitorizacion_completa(monitorizacion_data: Dict[str, Any], supervisor_id: str) -> bool:
    """Guarda una monitorización completa"""
    try:
        from database import agregar_monitorizacion, obtener_monitorizaciones_por_empleado
        
        # **PREVENCIÓN DE DOBLE GUARDADO**
        if 'ultima_monitorizacion_guardada' in st.session_state:
            tiempo_transcurrido = (datetime.now() - st.session_state.ultima_monitorizacion_guardada).seconds
            if tiempo_transcurrido < 3:
                st.warning("⚠️ Por favor espera unos segundos antes de guardar de nuevo")
                return False
        
        # **VALIDACIÓN DE DATOS REQUERIDOS**
        campos_requeridos = ['id_empleado', 'fecha_monitorizacion']
        for campo in campos_requeridos:
            if not monitorizacion_data.get(campo):
                st.error(f"❌ Campo requerido faltante: {campo}")
                return False
        
        # **VERIFICAR SI YA EXISTE UNA MONITORIZACIÓN PARA ESTA FECHA**
        existentes = obtener_monitorizaciones_por_empleado(monitorizacion_data['id_empleado'])
        for existente in existentes:
            if existente.get('fecha_monitorizacion') == monitorizacion_data['fecha_monitorizacion']:
                st.warning(f"⚠️ Ya existe una monitorización para este agente en la fecha {monitorizacion_data['fecha_monitorizacion']}")
                return False
        
        # **PROCESAMIENTO DE DATOS**
        if 'feedback' not in monitorizacion_data:
            monitorizacion_data['feedback'] = ""
        
        if 'plan_accion' not in monitorizacion_data:
            monitorizacion_data['plan_accion'] = ""
        
        # Convertir campos numéricos
        campos_numericos = [
            'nota_global', 'objetivo', 'experiencia', 'comunicacion',
            'deteccion', 'habilidades_venta', 'resolucion_objeciones',
            'cierre_contacto'
        ]
        
        for campo in campos_numericos:
            if campo in monitorizacion_data:
                try:
                    valor = monitorizacion_data[campo]
                    if valor is None or valor == '':
                        monitorizacion_data[campo] = 0.0
                    else:
                        monitorizacion_data[campo] = float(valor)
                except (ValueError, TypeError):
                    monitorizacion_data[campo] = 0.0
        
        # Validar y limpiar puntos clave
        puntos_clave = monitorizacion_data.get('puntos_clave', [])
        if isinstance(puntos_clave, str):
            puntos_clave = [p.strip() for p in puntos_clave.split(',') if p.strip()]
        
        puntos_validos = [p for p in puntos_clave if p in OPCIONES_PUNTOS_CLAVE]
        monitorizacion_data['puntos_clave'] = puntos_validos
        
        # Agregar metadata
        monitorizacion_data['supervisor_id'] = supervisor_id
        monitorizacion_data['fecha_creacion'] = datetime.now().isoformat()
        
        # Calcular fecha próxima
        if 'fecha_monitorizacion' in monitorizacion_data and monitorizacion_data['fecha_monitorizacion']:
            try:
                fecha_actual = datetime.strptime(monitorizacion_data['fecha_monitorizacion'], '%Y-%m-%d')
                fecha_proxima = fecha_actual + timedelta(days=14)
                monitorizacion_data['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
            except:
                fecha_proxima = datetime.now() + timedelta(days=14)
                monitorizacion_data['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
        else:
            fecha_proxima = datetime.now() + timedelta(days=14)
            monitorizacion_data['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
        
        # **GUARDAR EN BASE DE DATOS**
        monitorizacion_id = agregar_monitorizacion(monitorizacion_data)
        
        if monitorizacion_id:
            # Limpiar session state
            keys_to_clean = []
            for key in st.session_state.keys():
                if (key.startswith('mon_') or 
                    key.startswith('form_mon_') or 
                    key.startswith('datos_formulario') or
                    key == 'datos_transferidos' or
                    key == 'ultima_transferencia'):
                    keys_to_clean.append(key)
            
            for key in keys_to_clean:
                st.session_state.pop(key, None)
            
            st.session_state.pop('last_monitorizacion_submit', None)
            st.session_state.pop('monitorizacion_en_progreso', None)
            
            st.success(f"✅ Monitorización guardada exitosamente!")
            
            import time
            time.sleep(1.5)
            st.rerun()
            
            return True
        else:
            st.error("❌ Error al guardar en la base de datos")
            return False
            
    except Exception as e:
        st.error(f"❌ Error al guardar monitorización: {str(e)}")
        return False

# Funciones auxiliares para el panel de agentes
def mostrar_monitorizacion_agente(usuario_id: str) -> bool:
    """Muestra la ÚLTIMA monitorización del agente en su panel"""
    try:
        from database import obtener_ultima_monitorizacion_empleado
        
        ultima_mon = obtener_ultima_monitorizacion_empleado(usuario_id)
        
        if not ultima_mon:
            from database import obtener_monitorizaciones_por_empleado
            todas = obtener_monitorizaciones_por_empleado(usuario_id)
            
            if not todas:
                return False
            
            todas.sort(key=lambda x: x.get('fecha_monitorizacion', ''), reverse=True)
            ultima_mon = todas[0]
        
        st.markdown("---")
        st.subheader("📊 Tu Última Monitorización")
        
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
                try:
                    fecha_prox_dt = datetime.strptime(fecha_prox, '%Y-%m-%d')
                    hoy = datetime.now().date()
                    dias_restantes = (fecha_prox_dt.date() - hoy).days
                    st.metric("Próxima", fecha_prox, delta=f"{dias_restantes} días")
                except:
                    st.metric("Próxima", fecha_prox)
        
        st.write("#### 📈 Puntuaciones por Área")
        
        areas = [
            ("Experiencia", ultima_mon.get('experiencia')),
            ("Comunicación", ultima_mon.get('comunicacion')),
            ("Detección", ultima_mon.get('deteccion')),
            ("Habilidades de Venta", ultima_mon.get('habilidades_venta')),
            ("Resolución Objeciones", ultima_mon.get('resolucion_objeciones')),
            ("Cierre Contacto", ultima_mon.get('cierre_contacto'))
        ]
        
        cols = st.columns(3)
        for idx, (area, puntaje) in enumerate(areas):
            if puntaje is not None:
                with cols[idx % 3]:
                    progress = puntaje / 100
                    st.progress(progress)
                    st.caption(f"{area}: {puntaje}%")
        
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
        
    except Exception as e:
        st.error(f"❌ Error al mostrar monitorización: {str(e)}")
        return False