"""
Interfaz SIMPLE para sincronización usando github_api_sync.py
Sistema que YA FUNCIONABA anteriormente
"""

import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path

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

def show_sync_panel():
    """Muestra el panel de sincronización SIMPLE y FUNCIONAL"""
    
    st.subheader("🔄 Sincronización con GitHub")
    st.caption("Usando el sistema original que YA funcionaba")
    
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
    # 3. ACCIONES PRINCIPALES (SIMPLE Y DIRECTO)
    # ============================================
    st.write("### 3. 🚀 Acciones de Sincronización")
    
    st.info("""
    **📁 ¿Qué se sincroniza?**
    - ✅ **TODA** la carpeta `data/` (incluyendo `monitorizaciones.json`)
    - ✅ **TODA** la carpeta `modelos_facturas/`
    - ✅ **TODO** lo que haya dentro de estas carpetas
    """)
    
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
                    commit_message=f"Sync manual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Mostrar resultados
                st.markdown("---")
                st.subheader("📊 Resultados de la sincronización")
                
                if results["success"] > 0:
                    st.success(f"✅ **{results['success']}/{results['total']} archivos sincronizados exitosamente**")
                    st.balloons()
                    
                    # Resumen por carpetas
                    data_count = sum(1 for d in results["details"] if "data/" in d and "✅" in d)
                    modelos_count = sum(1 for d in results["details"] if "modelos_facturas/" in d and "✅" in d)
                    
                    col_res1, col_res2 = st.columns(2)
                    with col_res1:
                        st.metric("📂 Archivos en data/", data_count)
                    with col_res2:
                        st.metric("📄 Modelos de factura", modelos_count)
                    
                    # Mostrar archivos importantes específicamente
                    st.write("#### 📋 Archivos clave sincronizados:")
                    
                    important_files = [
                        "monitorizaciones.json",
                        "usuarios.json", 
                        "precios_luz.csv",
                        "planes_gas.json",
                        "registro_llamadas.json"
                    ]
                    
                    for file in important_files:
                        if any(f"✅ {file}" in detail for detail in results["details"]):
                            st.success(f"• `{file}`")
                        elif any(f"❌ {file}" in detail for detail in results["details"]):
                            st.error(f"• `{file}` (falló)")
                    
                    # Botón para ver todos los detalles
                    with st.expander("📝 Ver todos los detalles"):
                        for detail in results["details"]:
                            if "✅" in detail:
                                st.success(detail)
                            elif "❌" in detail:
                                st.error(detail)
                            else:
                                st.info(detail)
                
                else:
                    st.error(f"❌ No se pudo sincronizar ningún archivo")
                    
                    if results.get("failed", 0) > 0:
                        with st.expander("🔍 Ver errores"):
                            for detail in results["details"]:
                                if "❌" in detail:
                                    st.error(detail)
            
            except Exception as e:
                st.error(f"❌ Error durante la sincronización: {str(e)}")
    
    # BOTÓN SECUNDARIO: DESCARGAR DESDE GITHUB
    st.write("---")
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
                    
                    with st.expander("📋 Ver detalles de descarga"):
                        for detail in results["details"][:20]:  # Mostrar primeros 20
                            if "✅" in detail:
                                st.success(detail)
                            else:
                                st.error(detail)
                        
                        if len(results["details"]) > 20:
                            st.write(f"... y {len(results['details']) - 20} más")
            
            except Exception as e:
                st.error(f"❌ Error durante la descarga: {str(e)}")
    
    # ============================================
    # 4. SINCRONIZACIÓN POR ARCHIVOS ESPECÍFICOS
    # ============================================
    st.write("### 4. 📁 Sincronizar Archivos Específicos")
    
    # Lista de archivos importantes
    important_files = [
        ("data/monitorizaciones.json", "📊 Métricas de monitorización"),
        ("data/usuarios.json", "👥 Usuarios del sistema"),
        ("data/precios_luz.csv", "⚡ Planes de electricidad"),
        ("data/planes_gas.json", "🔥 Planes de gas"),
        ("data/registro_llamadas.json", "📞 Registro de llamadas"),
        ("data/config_sistema.json", "⚙️ Configuración del sistema")
    ]
    
    for file_path, description in important_files:
        if os.path.exists(file_path):
            col_file1, col_file2, col_file3 = st.columns([3, 2, 1])
            
            with col_file1:
                file_name = os.path.basename(file_path)
                st.write(f"**{file_name}**")
                st.caption(description)
            
            with col_file2:
                size_kb = os.path.getsize(file_path) / 1024
                st.write(f"{size_kb:.1f} KB")
                # Verificar si fue modificado recientemente
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                st.caption(f"Modificado: {modified_time.strftime('%H:%M')}")
            
            with col_file3:
                if st.button("⬆️", key=f"sync_{file_name}", help=f"Sincronizar {file_name}"):
                    try:
                        sync_single = GitHubSync()
                        commit_msg = f"Sync manual: {file_name}"
                        
                        success = sync_single.upload_file(
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
    
    # ============================================
    # 5. LOGS E INFORMACIÓN
    # ============================================
    st.write("### 5. 📜 Historial y Logs")
    
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
    # 6. INFORMACIÓN TÉCNICA Y DEBUG
    # ============================================
    with st.expander("🔧 Información técnica y debugging"):
        st.write("**Configuración actual:**")
        
        config_info = {
            "Repositorio": f"{sync.repo_owner}/{sync.repo_name}",
            "Rama": sync.branch,
            "Token": f"{sync.token[:8]}...{sync.token[-4:]}" if sync.token else "No configurado",
            "Carpetas a sincronizar": ", ".join(sync.sync_folders),
            "Archivo de log": sync.log_file
        }
        
        for key, value in config_info.items():
            st.write(f"• **{key}:** {value}")
        
        # Botón para verificar estructura de carpetas
        if st.button("📁 Verificar estructura local"):
            st.write("**Estructura de `data/`:**")
            if os.path.exists("data"):
                for root, dirs, files in os.walk("data"):
                    level = root.replace("data", "").count(os.sep)
                    indent = " " * 4 * level
                    st.write(f"{indent}📁 {os.path.basename(root) or 'data/'}")
                    subindent = " " * 4 * (level + 1)
                    for file in files[:10]:  # Mostrar solo primeros 10 archivos
                        st.write(f"{subindent}📄 {file}")
                    if len(files) > 10:
                        st.write(f"{subindent}... y {len(files) - 10} más")

# Para usar en admin_functions.py
def show_sync_panel_simple():
    """Función para llamar desde admin_functions.py"""
    show_sync_panel()