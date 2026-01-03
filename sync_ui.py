"""
Interfaz de usuario para sincronización TEMPORAL → GITHUB
"""

import streamlit as st
import os
from datetime import datetime
from sync_data_to_github import sync_manager, sync_now, get_status, auto_sync

def show_sync_panel():
    """Muestra el panel de control de sincronización"""
    st.subheader("🔄 Sincronización: TEMPORAL → GITHUB")
    
    st.info("""
    **🎯 OBJETIVO:** Guardar los datos de tu sesión temporal de Streamlit en GitHub PERMANENTEMENTE
    
    **📁 Archivos que se sincronizan:**
    - `config_excedentes.csv` - Precios excedentes
    - `config_pmg.json` - Configuración PMG
    - `config_sistema.json` - Configuración del sistema
    - `monitorizaciones.json` - Datos de monitorización
    - `planes_gas.json` - Planes de gas
    - `precios_luz.csv` - Planes de electricidad
    - `registro_llamadas.json` - Datos CSV importados
    - `super_users.json` - Super usuarios
    - `usuarios.json` - Usuarios del sistema
    """)
    
    # Estado actual
    status = get_status()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Archivos vigilados", status["total_files"])
    with col2:
        changed = len(status["changed_files"])
        st.metric("✏️ Modificados", changed)
    with col3:
        if status["next_sync_in"]:
            st.metric("⏰ Próximo auto-sync", status["next_sync_in"])
        else:
            st.metric("⏰ Auto-sync", "Cada 1 hora")
    
    # Archivos modificados
    if status["changed_files"]:
        st.warning(f"⚠️ **{len(status['changed_files'])} archivos modificados sin sincronizar:**")
        for file in status["changed_files"][:5]:
            st.write(f"• `{os.path.basename(file)}`")
        if len(status["changed_files"]) > 5:
            st.write(f"• ... y {len(status['changed_files']) - 5} más")
    else:
        st.success("✅ Todos los archivos están sincronizados")
    
    st.markdown("---")
    
    # Botones de acción
    st.write("### ⚡ Acciones de Sincronización")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🚀 **SINCRONIZAR TODO**", type="primary", use_container_width=True):
            with st.spinner("Sincronizando todos los archivos..."):
                success_count, total_files, results = sync_now(force=True)
                
                if success_count > 0:
                    st.success(f"✅ {success_count}/{total_files} archivos guardados en GitHub")
                    st.balloons()
                    
                    # Mostrar detalles
                    with st.expander("📊 Ver detalles"):
                        for result in results:
                            st.write(result)
                else:
                    st.error("❌ No se pudo sincronizar ningún archivo")
    
    with col_btn2:
        if st.button("📤 **Solo Modificados**", type="secondary", use_container_width=True):
            with st.spinner("Sincronizando archivos modificados..."):
                success_count, total_files, results = sync_now(force=False)
                
                if total_files > 0:
                    if success_count > 0:
                        st.success(f"✅ {success_count}/{total_files} archivos sincronizados")
                    else:
                        st.warning(f"⚠️ {total_files} archivos modificados pero no se pudieron sincronizar")
                    
                    with st.expander("📝 Ver resultados"):
                        for result in results:
                            st.write(result)
                else:
                    st.info("ℹ️ No hay archivos modificados para sincronizar")
    
    with col_btn3:
        if st.button("🔄 **Forzar Auto-Sync**", type="secondary", use_container_width=True):
            # Resetear tiempo para forzar auto-sync
            sync_manager.last_sync_time = None
            success, message = auto_sync()
            
            if success:
                st.success(message)
            else:
                st.info(message)
    
    st.markdown("---")
    
    # Sincronización por archivo
    st.write("### 📁 Sincronización por Archivo")
    
    # Listar archivos con estado
    files_status = []
    for file_path in sync_manager.target_files:
        exists = os.path.exists(file_path)
        if exists:
            size = os.path.getsize(file_path)
            modified = file_path in status["changed_files"]
            
            files_status.append({
                "archivo": os.path.basename(file_path),
                "tamaño": f"{size:,} bytes",
                "estado": "✏️ Modificado" if modified else "✅ Sincronizado",
                "ruta": file_path
            })
    
    if files_status:
        # Mostrar tabla
        for file_info in files_status:
            col_file1, col_file2, col_file3, col_file4 = st.columns([3, 2, 2, 1])
            
            with col_file1:
                st.write(f"**{file_info['archivo']}**")
            
            with col_file2:
                st.write(file_info['tamaño'])
            
            with col_file3:
                if file_info['estado'] == "✏️ Modificado":
                    st.warning(file_info['estado'])
                else:
                    st.success(file_info['estado'])
            
            with col_file4:
                if file_info['estado'] == "✏️ Modificado":
                    if st.button("⬆️", key=f"sync_{file_info['archivo']}", help="Sincronizar este archivo"):
                        success, message = sync_manager.sync_single_file(
                            file_info['ruta'], 
                            f"Sincronización manual: {file_info['archivo']}"
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
        # Limpiar logs
        if st.button("🧹 Limpiar Logs Antiguos", use_container_width=True):
            log_files = ["logs/data_sync.log", "logs/auto_sync_summary.log"]
            cleared = 0
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    # Mantener solo últimas 1000 líneas
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    if len(lines) > 1000:
                        with open(log_file, "w", encoding="utf-8") as f:
                            f.writelines(lines[-1000:])
                        cleared += 1
            
            if cleared > 0:
                st.success(f"✅ {cleared} logs limpiados")
            else:
                st.info("ℹ️ No hay logs para limpiar")
    
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