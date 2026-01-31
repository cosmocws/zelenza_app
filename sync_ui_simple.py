"""
Interfaz SIMPLE para sincronización usando github_api_sync.py
Sistema que YA FUNCIONABA anteriormente - VERSIÓN MEJORADA
Con lista COMPLETA de archivos específicos para sincronización individual
INCLUYE TODOS LOS ARCHIVOS COMO CRÍTICOS
"""

import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

# Importar TU sistema probado
try:
    from github_api_sync import GitHubSync, test_github_connection
    GITHUB_SYSTEM_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ No se puede importar github_api_sync: {e}")
    GITHUB_SYSTEM_AVAILABLE = False
except Exception as e:
    st.error(f"❌ Error importando github_api_sync: {e}")
    GITHUB_SYSTEM_AVAILABLE = False

def create_sync_instance():
    """Crea una instancia del sincronizador"""
    try:
        return GitHubSync()
    except ValueError as e:
        st.error(f"❌ {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Error creando GitHubSync: {str(e)}")
        return None

def get_all_files_list():
    """Obtiene TODOS los archivos de data/ y modelos_facturas/ con detalles"""
    all_files = []
    
    # Carpeta data/ - ARCHIVOS ESPECÍFICOS (basado en tu repositorio GitHub)
    if os.path.exists("data"):
        data_files = []
        for root, dirs, files in os.walk("data"):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, ".")
                
                # Obtener tamaño y fecha de modificación
                try:
                    size_bytes = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
                    
                    # Clasificar por tipo
                    if file.endswith('.json'):
                        file_type = "JSON"
                        icon = "📋"
                    elif file.endswith('.csv'):
                        file_type = "CSV"
                        icon = "📊"
                    elif file.endswith('.txt') or file.endswith('.log'):
                        file_type = "TXT"
                        icon = "📝"
                    elif file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg'):
                        file_type = "IMAGEN"
                        icon = "🖼️"
                    elif file.endswith('.pdf'):
                        file_type = "PDF"
                        icon = "📄"
                    else:
                        file_type = "OTRO"
                        icon = "📎"
                    
                    # Prioridad (todos son importantes ahora)
                    priority = 1  # TODOS son alta prioridad
                    
                    # Iconos especiales según nombre
                    if "usuarios" in file.lower():
                        icon = "👥"
                    elif "monitorizaciones" in file.lower():
                        icon = "📊"
                    elif "precios_luz" in file.lower() or "luz" in file.lower():
                        icon = "⚡"
                    elif "planes_gas" in file.lower() or "gas" in file.lower():
                        icon = "🔥"
                    elif "registro_llamadas" in file.lower() or "llamadas" in file.lower():
                        icon = "📞"
                    elif "config" in file.lower():
                        icon = "⚙️"
                    elif "excedentes" in file.lower():
                        icon = "☀️"
                    elif "pmg" in file.lower():
                        icon = "🔥"
                    elif "super" in file.lower():
                        icon = "👑"
                    elif "database" in file.lower():
                        icon = "🗄️"
                    elif "festivos" in file.lower():
                        icon = "🗓️"
                    elif "cola" in file.lower() or "pvd" in file.lower():
                        icon = "👁️"
                    elif "metricas" in file.lower():
                        icon = "📈"
                    elif "horarios" in file.lower():
                        icon = "⏰"
                    elif "ausencias" in file.lower():
                        icon = "🏃"
                    elif "ventas" in file.lower():
                        icon = "💰"
                    
                    data_files.append({
                        "path": rel_path,
                        "name": file,
                        "folder": root,
                        "size_kb": round(size_bytes / 1024, 2),
                        "modified": mod_date,
                        "type": file_type,
                        "icon": icon,
                        "priority": priority
                    })
                except:
                    pass
        
        # Ordenar por nombre
        data_files.sort(key=lambda x: x["name"].lower())
        all_files.extend(data_files)
    
    # Carpeta modelos_facturas/
    if os.path.exists("modelos_facturas"):
        modelos_files = []
        for root, dirs, files in os.walk("modelos_facturas"):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, ".")
                
                try:
                    size_bytes = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
                    
                    # Detectar tipo de archivo
                    if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg'):
                        file_type = "IMAGEN"
                        icon = "🖼️"
                    elif file.endswith('.pdf'):
                        file_type = "PDF"
                        icon = "📄"
                    else:
                        file_type = "OTRO"
                        icon = "📎"
                    
                    # Todos son alta prioridad
                    modelos_files.append({
                        "path": rel_path,
                        "name": file,
                        "folder": root,
                        "size_kb": round(size_bytes / 1024, 2),
                        "modified": mod_date,
                        "type": file_type,
                        "icon": icon,
                        "priority": 1
                    })
                except:
                    pass
        
        modelos_files.sort(key=lambda x: x["name"].lower())
        all_files.extend(modelos_files)
    
    return all_files

def get_file_stats():
    """Obtiene estadísticas de archivos"""
    stats = {
        "data_files": 0,
        "modelos_files": 0,
        "data_size_mb": 0,
        "modelos_size_mb": 0
    }
    
    # Archivos en data/
    if os.path.exists("data"):
        data_files = list(Path("data").rglob("*"))
        stats["data_files"] = len([f for f in data_files if f.is_file()])
        stats["data_size_mb"] = sum(f.stat().st_size for f in data_files if f.is_file()) / (1024 * 1024)
    
    # Archivos en modelos_facturas/
    if os.path.exists("modelos_facturas"):
        modelos_files = list(Path("modelos_facturas").rglob("*"))
        stats["modelos_files"] = len([f for f in modelos_files if f.is_file()])
        stats["modelos_size_mb"] = sum(f.stat().st_size for f in modelos_files if f.is_file()) / (1024 * 1024)
    
    return stats

def get_all_critical_files():
    """Obtiene TODOS los archivos como críticos - BASADO EN TU REPOSITORIO GITHUB"""
    all_files = get_all_files_list()
    
    # Crear lista de archivos críticos con descripciones
    critical_files = []
    
    for file_info in all_files:
        file_path = file_info["path"]
        file_name = file_info["name"]
        icon = file_info["icon"]
        
        # Descripción según tipo de archivo
        description = ""
        
        if "monitorizaciones" in file_name.lower():
            description = "📊 Métricas de monitorización"
        elif "usuarios" in file_name.lower():
            description = "👥 Usuarios del sistema"
        elif "precios_luz" in file_name.lower():
            description = "⚡ Planes de electricidad"
        elif "planes_gas" in file_name.lower():
            description = "🔥 Planes de gas"
        elif "registro_llamadas" in file_name.lower():
            description = "📞 Registro de llamadas"
        elif "config_sistema" in file_name.lower():
            description = "⚙️ Configuración del sistema"
        elif "config_excedentes" in file_name.lower():
            description = "☀️ Configuración excedentes"
        elif "config_pmg" in file_name.lower():
            description = "🔥 Configuración PMG"
        elif "super_users" in file_name.lower():
            description = "👑 Super usuarios"
        elif "database.json" in file_name.lower():
            description = "🗄️ Base de datos principal"
        elif "festivos" in file_name.lower():
            description = "🗓️ Festivos nacionales y de empresa"
        elif "cola_pvd" in file_name.lower():
            description = "👁️ Colas del sistema PVD"
        elif "config_pvd" in file_name.lower():
            description = "⚙️ Configuración PVD"
        elif "metricas_agentes" in file_name.lower():
            description = "📈 Métricas de agentes"
        elif "horarios_agentes" in file_name.lower():
            description = "⏰ Horarios de agentes"
        elif "ausencias_agentes" in file_name.lower():
            description = "🏃 Ausencias de agentes"
        elif "ventas_agentes" in file_name.lower():
            description = "💰 Ventas de agentes"
        elif "planes_gas.json" in file_name.lower():
            description = "🔥 Planes de gas RL1, RL2, RL3"
        elif file_name.endswith('.csv'):
            description = "📊 Datos en formato CSV"
        elif file_name.endswith('.json'):
            description = "📋 Configuración JSON"
        elif file_name.endswith('.png') or file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
            description = "🖼️ Imagen/Modelo de factura"
        elif file_name.endswith('.pdf'):
            description = "📄 Documento PDF"
        elif file_name.endswith('.txt') or file_name.endswith('.log'):
            description = "📝 Archivo de texto/log"
        else:
            description = f"{icon} Archivo del sistema"
        
        # TODOS son importantes
        critical_files.append((file_path, description, True))
    
    return critical_files

def show_sync_panel():
    """Muestra el panel de sincronización SIMPLE y FUNCIONAL"""
    
    st.subheader("🔄 Sincronización con GitHub")
    st.caption("Sincroniza archivos específicos o todos a la vez")
    
    # ============================================
    # 1. VERIFICAR CONFIGURACIÓN Y CONEXIÓN
    # ============================================
    st.write("### 1. 🔍 Verificar Configuración")
    
    # Verificar si el sistema está disponible
    if not GITHUB_SYSTEM_AVAILABLE:
        st.error("""
        ❌ **Sistema de sincronización no disponible**
        
        El archivo `github_api_sync.py` no se puede cargar.
        Asegúrate de que existe en tu repositorio.
        """)
        return
    
    # Probar conexión
    col_test1, col_test2 = st.columns([3, 1])
    
    with col_test1:
        st.write("**Estado de conexión:**")
    
    with col_test2:
        if st.button("🔌 Probar Conexión", type="secondary", use_container_width=True):
            success, message = test_github_connection()
            if success:
                st.success(message)
            else:
                st.error(message)
    
    # Crear instancia para verificar configuración
    sync = create_sync_instance()
    if sync is None:
        st.error("""
        ⚠️ **Configuración incompleta**
        
        **Para solucionar:**
        1. Ve a **Streamlit Cloud → Settings → Secrets**
        2. Añade estas variables:
        
        ```toml
        GITHUB_TOKEN = "ghp_tu_token_aqui"
        GITHUB_REPO_OWNER = "cosmocws"
        GITHUB_REPO_NAME = "zelenza_app"
        ```
        
        3. Guarda y reinicia la app
        """)
        return
    
    st.success("✅ Configuración de GitHub verificada")
    
    # ============================================
    # 2. ESTADÍSTICAS Y ESTADO
    # ============================================
    st.write("### 2. 📊 Estado Actual")
    
    # Obtener estadísticas
    stats = get_file_stats()
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("📁 Archivos en data/", stats["data_files"])
        if stats["data_size_mb"] > 0:
            st.caption(f"{stats['data_size_mb']:.1f} MB")
    
    with col_stat2:
        st.metric("📄 Modelos facturas", stats["modelos_files"])
        if stats["modelos_size_mb"] > 0:
            st.caption(f"{stats['modelos_size_mb']:.1f} MB")
    
    with col_stat3:
        # Contar archivos modificados recientemente (últimas 24h)
        modified_count = 0
        cutoff = datetime.now().timestamp() - 86400  # 24 horas
        
        for folder in ["data/", "modelos_facturas/"]:
            if os.path.exists(folder):
                for file_path in Path(folder).rglob("*"):
                    if file_path.is_file():
                        try:
                            if file_path.stat().st_mtime > cutoff:
                                modified_count += 1
                        except:
                            pass
        
        st.metric("✏️ Modificados recientemente", modified_count)
    
    with col_stat4:
        # Leer último log
        log_file = "logs/github_sync.log"
        last_sync = "Nunca"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    for line in reversed(lines):
                        if "SUCCESS" in line or "INFO" in line:
                            parts = line.split(" - ")
                            if len(parts) > 0:
                                last_sync = parts[0]
                                break
        
        st.metric("🕒 Última sincronización", last_sync[:10] if last_sync != "Nunca" else "Nunca")
    
    # ============================================
    # 3. TODOS LOS ARCHIVOS COMO CRÍTICOS - ACCESO DIRECTO
    # ============================================
    st.write("### 3. ⚡ TODOS LOS ARCHIVOS - Sincronización Individual")
    st.info("""
    **¡ATENCIÓN!** Todos los archivos son considerados **CRÍTICOS**.
    Puedes sincronizar individualmente cualquier archivo haciendo clic en su botón.
    """)
    
    # Obtener TODOS los archivos críticos
    critical_files = get_all_critical_files()
    
    if not critical_files:
        st.warning("📂 No se encontraron archivos para sincronizar")
    else:
        # Dividir archivos por tipo para mejor organización
        json_files = [(path, desc, imp) for path, desc, imp in critical_files if path.endswith('.json')]
        csv_files = [(path, desc, imp) for path, desc, imp in critical_files if path.endswith('.csv')]
        image_files = [(path, desc, imp) for path, desc, imp in critical_files if any(path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])]
        pdf_files = [(path, desc, imp) for path, desc, imp in critical_files if path.endswith('.pdf')]
        other_files = [(path, desc, imp) for path, desc, imp in critical_files if not any(path.endswith(ext) for ext in ['.json', '.csv', '.png', '.jpg', '.jpeg', '.pdf'])]
        
        # Pestañas por tipo de archivo
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            f"📋 JSON ({len(json_files)})",
            f"📊 CSV ({len(csv_files)})",
            f"🖼️ Imágenes ({len(image_files)})",
            f"📄 PDF ({len(pdf_files)})",
            f"📎 Otros ({len(other_files)})"
        ])
        
        # Función para mostrar archivos en una cuadrícula
        def show_files_grid(files_list, tab_name):
            if not files_list:
                st.info(f"No hay archivos {tab_name} para mostrar")
                return
            
            # Mostrar en cuadrícula de 3 columnas
            cols = st.columns(3)
            
            for idx, (file_path, description, important) in enumerate(files_list):
                with cols[idx % 3]:
                    with st.container():
                        file_name = os.path.basename(file_path)
                        
                        # Estilo para TODOS (todos importantes)
                        st.markdown(f"""
                        <div style='
                            background-color: #fff3cd; 
                            padding: 12px; 
                            border-radius: 8px; 
                            border-left: 6px solid #ffc107;
                            margin-bottom: 15px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            height: 220px;
                            display: flex;
                            flex-direction: column;
                            justify-content: space-between;
                        '>
                        """, unsafe_allow_html=True)
                        
                        # Icono según tipo
                        if file_name.endswith('.json'):
                            icon = "📋"
                            file_type = "JSON"
                        elif file_name.endswith('.csv'):
                            icon = "📊"
                            file_type = "CSV"
                        elif file_name.endswith('.png') or file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
                            icon = "🖼️"
                            file_type = "Imagen"
                        elif file_name.endswith('.pdf'):
                            icon = "📄"
                            file_type = "PDF"
                        elif file_name.endswith('.txt') or file_name.endswith('.log'):
                            icon = "📝"
                            file_type = "Texto"
                        else:
                            icon = "📎"
                            file_type = "Archivo"
                        
                        # Información del archivo
                        st.write(f"<h4 style='margin: 0;'>{icon} {file_name}</h4>", unsafe_allow_html=True)
                        st.write(f"<p style='font-size: 12px; color: #666; margin: 5px 0;'>{description}</p>", unsafe_allow_html=True)
                        
                        # Detalles del archivo
                        try:
                            size_kb = os.path.getsize(file_path) / 1024
                            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            st.write(f"<div style='font-size: 11px; color: #888;'>", unsafe_allow_html=True)
                            st.write(f"📏 **Tamaño:** {size_kb:.1f} KB")
                            st.write(f"🕒 **Modificado:** {mod_time.strftime('%d/%m %H:%M')}")
                            st.write(f"📁 **Tipo:** {file_type}")
                            st.write("</div>", unsafe_allow_html=True)
                        except:
                            pass
                        
                        # Botón de sincronización
                        sync_button = st.button(
                            f"⬆️ Sincronizar", 
                            key=f"critical_{file_path.replace('/', '_')}", 
                            use_container_width=True,
                            type="primary"
                        )
                        
                        if sync_button:
                            try:
                                sync_instance = GitHubSync()
                                commit_msg = f"Sync archivo crítico: {file_name}"
                                
                                success = sync_instance.upload_file(
                                    local_path=file_path,
                                    github_path=file_path,
                                    commit_message=commit_msg
                                )
                                
                                if success:
                                    st.success(f"✅ {file_name} sincronizado")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error sincronizando {file_name}")
                            
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)[:50]}")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
        
        # Mostrar cada pestaña
        with tab1:
            show_files_grid(json_files, "JSON")
        
        with tab2:
            show_files_grid(csv_files, "CSV")
        
        with tab3:
            show_files_grid(image_files, "Imágenes")
        
        with tab4:
            show_files_grid(pdf_files, "PDF")
        
        with tab5:
            show_files_grid(other_files, "Otros")
    
    # ============================================
    # 4. ACCIONES MASIVAS (TODO A LA VEZ)
    # ============================================
    st.markdown("---")
    st.write("### 4. 🚀 Sincronización Masiva")
    
    col_mass1, col_mass2 = st.columns(2)
    
    with col_mass1:
        # BOTÓN PRINCIPAL: SUBIR TODO A GITHUB
        if st.button("🚀 **SUBIR TODO A GITHUB AHORA**", 
                    type="primary", 
                    use_container_width=True,
                    help="Sincroniza TODOS los archivos locales con GitHub"):
            
            with st.spinner("🔄 Sincronizando con GitHub..."):
                try:
                    # Crear nueva instancia para esta operación
                    sync_op = GitHubSync()
                    
                    # Ejecutar sincronización COMPLETA
                    results = sync_op.sync_to_github(
                        commit_message=f"Sync completa: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    
                    # Mostrar resultados
                    st.markdown("---")
                    st.subheader("📊 Resultados de la sincronización")
                    
                    if results["success"] > 0:
                        st.success(f"✅ **{results['success']}/{results['total']} archivos sincronizados exitosamente**")
                        st.balloons()
                        
                        # Resumen por tipos
                        json_count = sum(1 for d in results["details"] if "✅" in d and d.endswith('.json"'))
                        csv_count = sum(1 for d in results["details"] if "✅" in d and d.endswith('.csv"'))
                        image_count = sum(1 for d in results["details"] if "✅" in d and any(ext in d for ext in ['.png', '.jpg', '.jpeg']))
                        
                        col_res1, col_res2, col_res3 = st.columns(3)
                        with col_res1:
                            st.metric("📋 Archivos JSON", json_count)
                        with col_res2:
                            st.metric("📊 Archivos CSV", csv_count)
                        with col_res3:
                            st.metric("🖼️ Imágenes", image_count)
                        
                        # Mostrar primeros 15 detalles
                        with st.expander("📝 Ver primeros 15 detalles"):
                            for detail in results["details"][:15]:
                                if "✅" in detail:
                                    st.success(detail)
                                elif "❌" in detail:
                                    st.error(detail)
                                else:
                                    st.info(detail)
                        
                        if len(results["details"]) > 15:
                            st.write(f"... y {len(results['details']) - 15} más")
                    
                    else:
                        st.error(f"❌ No se pudo sincronizar ningún archivo")
                        
                        if results.get("failed", 0) > 0:
                            with st.expander("🔍 Ver primeros 10 errores"):
                                for detail in results["details"][:10]:
                                    if "❌" in detail:
                                        st.error(detail)
                
                except Exception as e:
                    st.error(f"❌ Error durante la sincronización: {str(e)}")
    
    with col_mass2:
        # BOTÓN SECUNDARIO: DESCARGAR DESDE GITHUB
        st.warning("⚠️ **ADVERTENCIA:** Esto sobrescribirá archivos locales")
        
        if st.button("⬇️ **DESCARGAR TODO DESDE GITHUB**", 
                    type="secondary", 
                    use_container_width=True,
                    help="Descarga TODOS los archivos desde GitHub (sobrescribe locales)"):
            
            with st.spinner("⬇️ Descargando desde GitHub..."):
                try:
                    sync_download = GitHubSync()
                    results = sync_download.sync_from_github()
                    
                    if results.get("success", False) is False:
                        st.error(f"❌ Error en la descarga: {results.get('error', 'Desconocido')}")
                    else:
                        st.success(f"✅ **{results['success']}/{results['total']} archivos descargados**")
                        
                        # Mostrar estadísticas de descarga
                        json_dl = sum(1 for d in results["details"] if "✅" in d and d.endswith('.json"'))
                        csv_dl = sum(1 for d in results["details"] if "✅" in d and d.endswith('.csv"'))
                        
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.metric("📋 JSON descargados", json_dl)
                        with col_dl2:
                            st.metric("📊 CSV descargados", csv_dl)
                        
                        with st.expander("📋 Ver primeros 10 detalles"):
                            for detail in results["details"][:10]:
                                if "✅" in detail:
                                    st.success(detail)
                                else:
                                    st.error(detail)
                
                except Exception as e:
                    st.error(f"❌ Error durante la descarga: {str(e)}")
    
    # ============================================
    # 5. BUSCADOR DE ARCHIVOS ESPECÍFICOS
    # ============================================
    st.markdown("---")
    st.write("### 5. 🔍 Buscar Archivo Específico")
    
    # Buscador
    search_term = st.text_input("Buscar archivo por nombre:", placeholder="Ej: usuarios, monitorizaciones, etc.")
    
    if search_term:
        # Filtrar archivos críticos por término de búsqueda
        filtered_files = [(path, desc, imp) for path, desc, imp in critical_files 
                         if search_term.lower() in os.path.basename(path).lower()]
        
        if filtered_files:
            st.write(f"**📁 {len(filtered_files)} archivo(s) encontrados:**")
            
            for file_path, description, important in filtered_files:
                col_search1, col_search2, col_search3, col_search4 = st.columns([3, 2, 2, 1])
                
                with col_search1:
                    file_name = os.path.basename(file_path)
                    st.write(f"**{file_name}**")
                    st.caption(description)
                
                with col_search2:
                    if os.path.exists(file_path):
                        size_kb = os.path.getsize(file_path) / 1024
                        st.write(f"📏 {size_kb:.1f} KB")
                    else:
                        st.write("❌ No existe")
                
                with col_search3:
                    if os.path.exists(file_path):
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        st.caption(f"🕒 {mod_time.strftime('%d/%m %H:%M')}")
                
                with col_search4:
                    if os.path.exists(file_path):
                        if st.button("⬆️", key=f"search_{file_path}", help=f"Sincronizar {file_name}"):
                            try:
                                sync_search = GitHubSync()
                                commit_msg = f"Sync búsqueda: {file_name}"
                                
                                success = sync_search.upload_file(
                                    local_path=file_path,
                                    github_path=file_path,
                                    commit_message=commit_msg
                                )
                                
                                if success:
                                    st.success(f"✅ {file_name} sincronizado")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error sincronizando {file_name}")
                            
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)[:50]}")
        else:
            st.info(f"🔍 No se encontraron archivos con '{search_term}'")
    
    # ============================================
    # 6. LOGS E INFORMACIÓN
    # ============================================
    st.markdown("---")
    st.write("### 6. 📜 Historial y Logs")
    
    # Mostrar últimos logs
    log_file = "logs/github_sync.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if lines:
            # Contar por tipo
            success_count = sum(1 for line in lines if "SUCCESS" in line)
            error_count = sum(1 for line in lines if "ERROR" in line)
            
            col_log1, col_log2, col_log3 = st.columns(3)
            with col_log1:
                st.metric("📄 Total líneas", len(lines))
            with col_log2:
                st.metric("✅ Éxitos", success_count)
            with col_log3:
                st.metric("❌ Errores", error_count)
            
            # Mostrar últimas 10 operaciones
            st.write("**Últimas 10 operaciones:**")
            for line in reversed(lines[-10:]):
                if "SUCCESS" in line:
                    st.success(line.strip())
                elif "ERROR" in line:
                    st.error(line.strip())
                elif "WARNING" in line:
                    st.warning(line.strip())
                else:
                    st.info(line.strip())
        else:
            st.info("📭 El archivo de log está vacío")
    else:
        st.info("📂 No hay historial de sincronizaciones aún")
    
    # ============================================
    # 7. RESUMEN DE ARCHIVOS MÁS IMPORTANTES
    # ============================================
    st.markdown("---")
    st.write("### 7. 🏆 Archivos Más Modificados (Últimas 24h)")
    
    # Obtener archivos modificados recientemente
    recently_modified = []
    cutoff = datetime.now().timestamp() - 86400  # 24 horas
    
    for folder in ["data/", "modelos_facturas/"]:
        if os.path.exists(folder):
            for file_path in Path(folder).rglob("*"):
                if file_path.is_file():
                    try:
                        mod_time = file_path.stat().st_mtime
                        if mod_time > cutoff:
                            # Convertir a días/horas/minutos
                            hours_ago = (datetime.now().timestamp() - mod_time) / 3600
                            
                            if hours_ago < 1:
                                time_ago = f"{int(hours_ago * 60)} min"
                            elif hours_ago < 24:
                                time_ago = f"{int(hours_ago)} h"
                            else:
                                time_ago = f"{int(hours_ago / 24)} días"
                            
                            recently_modified.append({
                                "path": str(file_path),
                                "name": file_path.name,
                                "hours_ago": hours_ago,
                                "time_ago": time_ago,
                                "size_kb": file_path.stat().st_size / 1024
                            })
                    except:
                        pass
    
    if recently_modified:
        # Ordenar por más reciente
        recently_modified.sort(key=lambda x: x["hours_ago"])
        
        # Mostrar top 10
        st.write(f"**📈 Top {min(10, len(recently_modified))} archivos modificados recientemente:**")
        
        for i, file_info in enumerate(recently_modified[:10]):
            col_top1, col_top2, col_top3, col_top4 = st.columns([4, 2, 2, 1])
            
            with col_top1:
                st.write(f"**{i+1}. {file_info['name']}**")
                st.caption(f"`{file_info['path']}`")
            
            with col_top2:
                st.write(f"⏱️ Hace {file_info['time_ago']}")
            
            with col_top3:
                st.write(f"📏 {file_info['size_kb']:.1f} KB")
            
            with col_top4:
                if st.button("⬆️", key=f"top_{i}"):
                    try:
                        sync_top = GitHubSync()
                        commit_msg = f"Sync reciente: {file_info['name']}"
                        
                        success = sync_top.upload_file(
                            local_path=file_info["path"],
                            github_path=file_info["path"],
                            commit_message=commit_msg
                        )
                        
                        if success:
                            st.success(f"✅ {file_info['name']} sincronizado")
                            st.rerun()
                        else:
                            st.error(f"❌ Error sincronizando")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)[:50]}")
    else:
        st.info("📭 No hay archivos modificados en las últimas 24 horas")

# Para usar en admin_functions.py
def show_sync_panel_simple():
    """Función para llamar desde admin_functions.py"""
    show_sync_panel()