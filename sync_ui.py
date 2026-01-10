"""
Interfaz de usuario para sincronización TEMPORAL → GITHUB
"""

import streamlit as st
import os
from datetime import datetime
from sync_data_to_github import sync_manager, sync_now, get_status, auto_sync, get_file_stats

def show_sync_panel():
    """Muestra el panel de control de sincronización"""
    st.subheader("🔄 Sincronización COMPLETA: TEMPORAL → GITHUB")
    
    st.info("""
    **🎯 OBJETIVO:** Guardar TODOS los datos de tu sesión temporal de Streamlit en GitHub PERMANENTEMENTE
    
    **📁 TODOS los archivos que se sincronizan:**
    
    **📂 Carpeta `data/` (COMPLETA):**
    - ✅ `config_excedentes.csv` - Precios excedentes
    - ✅ `config_pmg.json` - Configuración PMG  
    - ✅ `config_sistema.json` - Configuración del sistema
    - ✅ `monitorizaciones.json` - Datos de monitorización
    - ✅ `planes_gas.json` - Planes de gas
    - ✅ `precios_luz.csv` - Planes de electricidad
    - ✅ `registro_llamadas.json` - Datos CSV importados
    - ✅ `super_users.json` - Super usuarios
    - ✅ `usuarios.json` - Usuarios del sistema
    - ✅ **TODO lo demás en `data/`**
    
    **📂 Carpeta `modelos_facturas/` (COMPLETA):**
    - ✅ **TODOS los modelos de factura de todas las empresas**
    - ✅ **TODAS las imágenes y PDFs**
    """)
    
    # Obtener estadísticas
    stats = get_file_stats()
    status = get_status()
    
    # Mostrar estadísticas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📂 Archivos en data/", stats["data_files"])
        st.caption(f"{stats['data_size_mb']} MB")
    with col2:
        st.metric("📄 Archivos facturas", stats["modelos_files"])
        st.caption(f"{stats['modelos_size_mb']} MB")
    with col3:
        changed = len(status.get("changed_files", []))
        st.metric("✏️ Modificados", changed)
    with col4:
        if status.get("next_sync_in"):
            st.metric("⏰ Próximo auto-sync", status["next_sync_in"])
        else:
            st.metric("⏰ Auto-sync", "Cada 1 hora")
    
    # Archivos modificados
    changed_files = status.get("changed_files", [])
    if changed_files:
        st.warning(f"⚠️ **{len(changed_files)} archivos modificados sin sincronizar:**")
        
        # Agrupar por carpeta
        data_files = [f for f in changed_files if "data/" in f]
        modelos_files = [f for f in changed_files if "modelos_facturas/" in f]
        
        if data_files:
            st.write("**📂 data/:**")
            for file in data_files[:5]:
                file_display = file.replace("data/", "")
                st.write(f"• `{file_display}`")
            if len(data_files) > 5:
                st.write(f"• ... y {len(data_files) - 5} más en data/")
        
        if modelos_files:
            st.write("**📄 modelos_facturas/:**")
            for file in modelos_files[:3]:
                file_display = file.replace("modelos_facturas/", "")
                st.write(f"• `{file_display}`")
            if len(modelos_files) > 3:
                st.write(f"• ... y {len(modelos_files) - 3} más en modelos_facturas/")
    else:
        st.success("✅ Todos los archivos están sincronizados")
    
    st.markdown("---")
    
    # Botones de acción
    st.write("### ⚡ Acciones de Sincronización")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🚀 **SINCRONIZAR TODO AHORA**", type="primary", use_container_width=True):
            with st.spinner("Sincronizando TODOS los archivos..."):
                success_count, total_files, results = sync_now(force=True)
                
                if success_count > 0:
                    st.success(f"✅ {success_count}/{total_files} archivos guardados en GitHub")
                    st.balloons()
                    
                    # Mostrar detalles
                    with st.expander("📊 Ver detalles completos"):
                        for result in results[:20]:  # Mostrar primeros 20
                            if "✅" in result:
                                st.success(result)
                            elif "❌" in result:
                                st.error(result)
                            else:
                                st.info(result)
                        if len(results) > 20:
                            st.write(f"... y {len(results) - 20} más")
                else:
                    st.error("❌ No se pudo sincronizar ningún archivo")
    
    with col_btn2:
        if st.button("📤 **Solo Archivos Modificados**", type="secondary", use_container_width=True):
            with st.spinner("Sincronizando solo archivos modificados..."):
                success_count, total_files, results = sync_now(force=False)
                
                if total_files > 0:
                    if success_count > 0:
                        st.success(f"✅ {success_count}/{total_files} archivos sincronizados")
                    else:
                        st.warning(f"⚠️ {total_files} archivos modificados pero no se pudieron sincronizar")
                    
                    with st.expander("📝 Ver resultados"):
                        for result in results[:10]:
                            if "✅" in result:
                                st.success(result)
                            elif "❌" in result:
                                st.error(result)
                            else:
                                st.info(result)
                else:
                    st.info("ℹ️ No hay archivos modificados para sincronizar")
    
    with col_btn3:
        if st.button("🔄 **Forzar Auto-Sync Ahora**", type="secondary", use_container_width=True):
            # Resetear tiempo para forzar auto-sync
            if hasattr(sync_manager, 'last_sync_time'):
                sync_manager.last_sync_time = None
            success, message = auto_sync()
            
            if success:
                st.success(message)
            else:
                st.info(message)
    
    st.markdown("---")
    
    # Listar archivos más importantes
    st.write("### 📋 Archivos Principales para Sincronizar")
    
    # Archivos clave de data/
    important_files = [
        "data/monitorizaciones.json",
        "data/usuarios.json", 
        "data/super_users.json",
        "data/precios_luz.csv",
        "data/planes_gas.json",
        "data/config_sistema.json"
    ]
    
    # Verificar cada archivo
    for file_path in important_files:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            size_kb = size / 1024
            
            col_file1, col_file2, col_file3, col_file4 = st.columns([3, 1, 1, 1])
            
            with col_file1:
                st.write(f"**{file_name}**")
            
            with col_file2:
                st.write(f"{size_kb:.1f} KB")
            
            with col_file3:
                if file_path in changed_files:
                    st.warning("✏️ Modificado")
                else:
                    st.success("✅ Sincronizado")
            
            with col_file4:
                if file_path in changed_files:
                    if st.button("⬆️", key=f"sync_{file_name}", help="Sincronizar este archivo"):
                        success, message = sync_manager.sync_single_file(
                            file_path, 
                            f"Sincronización manual: {file_name}"
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
    
    st.markdown("---")
    
    # Configuración
    st.write("### ⚙️ Configuración")
    
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        # Intervalo de auto-sync
        interval_hours = st.number_input(
            "Intervalo auto-sync (horas)",
            min_value=0.5,
            max_value=24.0,
            value=1.0,
            step=0.5,
            help="Cada cuántas horas se ejecuta el auto-sync automático"
        )
        
        if interval_hours != sync_manager.sync_interval / 3600:
            sync_manager.sync_interval = interval_hours * 3600
            st.success(f"✅ Intervalo actualizado: cada {interval_hours}h")
    
    with col_config2:
        # Verificar configuración de GitHub
        st.write("**🔑 Configuración GitHub:**")
        
        required_secrets = ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"]
        missing = [s for s in required_secrets if s not in st.secrets]
        
        if missing:
            st.error(f"❌ Faltan: {', '.join(missing)}")
        else:
            st.success("✅ Configuración OK")
            
            # Mostrar info (oculta token)
            token_preview = st.secrets["GITHUB_TOKEN"][:4] + "..." + st.secrets["GITHUB_TOKEN"][-4:]
            st.caption(f"Token: {token_preview}")
            st.caption(f"Repo: {st.secrets['GITHUB_REPO_OWNER']}/{st.secrets['GITHUB_REPO_NAME']}")
    
    # Historial
    st.write("### 📜 Historial de Sincronizaciones")
    
    log_file = "logs/data_sync.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if lines:
            st.write(f"**Total registros:** {len(lines)}")
            
            # Mostrar últimos 10
            st.write("**Últimas 10 sincronizaciones:**")
            for line in reversed(lines[-10:]):
                if "✅" in line:
                    st.success(line.strip())
                elif "❌" in line:
                    st.error(line.strip())
                else:
                    st.info(line.strip())
    else:
        st.info("📭 No hay historial de sincronizaciones aún")
    
    # Información importante
    st.markdown("---")
    st.write("### ⚠️ Información Importante")
    
    st.warning("""
    **📝 ¿Por qué se pierden los datos?**
    
    Streamlit Cloud tiene sesiones TEMPORALES. Cuando:
    1. 🕒 Pasas 24h sin usar la app
    2. 🔄 Reinicias la app manualmente
    3. ⚡ Streamlit hace mantenimiento
    
    **TODOS los datos se pierden** a menos que los hayas sincronizado con GitHub.
    
    **✅ SOLUCIÓN:** Usa el botón **🚀 SINCRONIZAR TODO AHORA** después de:
    - Crear nuevos usuarios
    - Modificar planes de luz/gas  
    - Subir modelos de factura
    - Cualquier cambio importante
    """)