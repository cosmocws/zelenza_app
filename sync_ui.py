"""
Interfaz de usuario para sincronización TEMPORAL → GITHUB
Versión CORREGIDA - Muestra errores claramente
"""

import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path
from sync_data_to_github import sync_manager, sync_now, get_status, auto_sync, get_file_stats

def show_sync_panel():
    """Muestra el panel de control de sincronización - CORREGIDO"""
    st.subheader("🔄 Sincronización: TEMPORAL → GITHUB")
    
    # Verificar configuración de GitHub primero
    status = get_status()
    
    # Mostrar advertencia si GitHub no está disponible
    if not status.get("github_available", True):
        st.error("""
        ⚠️ **GITHUB NO CONFIGURADO O NO DISPONIBLE**
        
        **Para solucionar:**
        1. Ve a **Streamlit Cloud → Settings → Secrets**
        2. Añade estas líneas:
        
        ```toml
        GITHUB_TOKEN = "ghp_tu_token_aqui"
        GITHUB_REPO_OWNER = "tu_usuario_github"
        GITHUB_REPO_NAME = "tu_repositorio"
        ```
        
        3. **IMPORTANTE:** El token debe ser un **CLASSIC TOKEN** con permiso `repo`
        4. Guarda y reinicia la app
        """)
        
        # Botón para probar conexión manualmente
        if st.button("🔄 Probar Conexión Manualmente"):
            try:
                from github_sync_completo import test_github_config
                success, message = test_github_config()
                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        return  # No mostrar el resto si GitHub no está disponible
    
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
    - **TODO lo demás en `data/` y `modelos_facturas/`**
    """)
    
    # Estado actual
    stats = get_file_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 Archivos en data/", stats.get("data_files", 0))
        if stats.get("data_size_mb", 0) > 0:
            st.caption(f"{stats.get('data_size_mb', 0)} MB")
    with col2:
        st.metric("📄 Facturas", stats.get("modelos_files", 0))
        if stats.get("modelos_size_mb", 0) > 0:
            st.caption(f"{stats.get('modelos_size_mb', 0)} MB")
    with col3:
        changed = len(status.get("changed_files", []))
        st.metric("✏️ Modificados", changed)
    with col4:
        if status.get("next_sync_in"):
            st.metric("⏰ Próximo sync", status["next_sync_in"])
        else:
            st.metric("⏰ Auto-sync", "Cada 1 hora")
    
    # Archivos modificados
    changed_files = status.get("changed_files", [])
    if changed_files:
        st.warning(f"⚠️ **{len(changed_files)} archivos modificados sin sincronizar:**")
        
        # Agrupar por tipo
        data_files = [f for f in changed_files if "data/" in f]
        modelos_files = [f for f in changed_files if "modelos_facturas/" in f]
        
        # Mostrar primeros 3 de cada tipo
        if data_files:
            st.write("**📂 data/:**")
            for file in data_files[:3]:
                file_display = file.replace("data/", "")
                st.write(f"• `{file_display}`")
            if len(data_files) > 3:
                st.write(f"• ... y {len(data_files) - 3} más")
        
        if modelos_files:
            st.write("**📄 modelos_facturas/:**")
            for file in modelos_files[:3]:
                file_display = file.replace("modelos_facturas/", "")
                st.write(f"• `{file_display}`")
            if len(modelos_files) > 3:
                st.write(f"• ... y {len(modelos_files) - 3} más")
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
                        for result in results[:15]:  # Mostrar primeros 15
                            if "✅" in result:
                                st.success(result)
                            elif "❌" in result:
                                st.error(result)
                            else:
                                st.info(result)
                        if len(results) > 15:
                            st.write(f"... y {len(results) - 15} más")
                elif total_files > 0 and success_count == 0:
                    st.error(f"❌ 0/{total_files} archivos sincronizados. TODOS fallaron.")
                    with st.expander("📋 Ver errores"):
                        for result in results:
                            st.error(result)
                else:
                    st.info("ℹ️ No se encontraron archivos para sincronizar")
    
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
                            if "✅" in result:
                                st.success(result)
                            elif "❌" in result:
                                st.error(result)
                            else:
                                st.info(result)
                else:
                    st.info("ℹ️ No hay archivos modificados para sincronizar")
    
    with col_btn3:
        if st.button("🔄 **Forzar Auto-Sync**", type="secondary", use_container_width=True):
            success, message = auto_sync()
            
            if success:
                st.success(message)
            else:
                st.info(message)
    
    st.markdown("---")
    
    # Verificar archivos importantes específicos
    st.write("### ✅ Verificar Archivos Clave")
    
    archivos_importantes = {
        "data/monitorizaciones.json": "📊 Métricas de monitorización",
        "data/usuarios.json": "👥 Usuarios del sistema",
        "data/precios_luz.csv": "⚡ Planes de electricidad",
        "data/planes_gas.json": "🔥 Planes de gas",
        "data/config_sistema.json": "⚙️ Configuración del sistema"
    }
    
    for archivo, descripcion in archivos_importantes.items():
        col_check1, col_check2, col_check3 = st.columns([3, 1, 1])
        
        with col_check1:
            nombre_corto = os.path.basename(archivo)
            st.write(f"**{nombre_corto}**")
            st.caption(descripcion)
        
        with col_check2:
            if os.path.exists(archivo):
                size = os.path.getsize(archivo)
                st.success(f"✅ {size/1024:.1f} KB")
            else:
                st.error("❌ No existe")
        
        with col_check3:
            if os.path.exists(archivo) and archivo in changed_files:
                if st.button("⬆️", key=f"sync_{nombre_corto}"):
                    from sync_data_to_github import sync_file
                    success, message = sync_file(archivo)
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
        # Información de GitHub
        try:
            from github_sync_completo import test_github_config
            success, message = test_github_config()
            
            if success:
                st.success("✅ GitHub: Conectado")
                # Mostrar info (oculta token)
                if "GITHUB_TOKEN" in st.secrets:
                    token = st.secrets["GITHUB_TOKEN"]
                    token_preview = token[:4] + "..." + token[-4:]
                    st.caption(f"Token: {token_preview}")
                if "GITHUB_REPO_OWNER" in st.secrets and "GITHUB_REPO_NAME" in st.secrets:
                    st.caption(f"Repo: {st.secrets['GITHUB_REPO_OWNER']}/{st.secrets['GITHUB_REPO_NAME']}")
            else:
                st.error(f"❌ GitHub: {message}")
        except Exception as e:
            st.error(f"❌ Error probando GitHub: {str(e)}")
    
    # Historial
    st.write("### 📜 Historial de Sincronizaciones")
    
    log_file = "logs/data_sync.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if lines:
            # Mostrar últimos 10
            st.write(f"**Últimas 10 sincronizaciones (de {len(lines)} total):**")
            for line in reversed(lines[-10:]):
                if "✅" in line:
                    st.success(line.strip())
                elif "❌" in line:
                    st.error(line.strip())
                else:
                    st.info(line.strip())
        else:
            st.info("📭 El archivo de log está vacío")
    else:
        st.info("📂 No hay historial de sincronizaciones aún")
    
    # Información IMPORTANTE
    st.markdown("---")
    st.write("### ⚠️ ¿Sigue sin funcionar?")
    
    with st.expander("🔧 Solución de problemas"):
        st.write("""
        **1. Verifica los Secrets en Streamlit Cloud:**
        - Ve a **Settings → Secrets**
        - Asegúrate de tener EXACTAMENTE:
        
        ```toml
        GITHUB_TOKEN = "ghp_tu_token_aqui"
        GITHUB_REPO_OWNER = "tu_usuario_github"
        GITHUB_REPO_NAME = "nombre_del_repositorio"
        ```
        
        **2. Verifica el token de GitHub:**
        - Debe ser un **CLASSIC TOKEN** (no fine-grained)
        - Debe tener permiso **`repo`** (solo repo, nada más)
        - Ve a GitHub → Settings → Developer settings → Personal access tokens
        
        **3. Verifica el repositorio:**
        - Debe existir en GitHub
        - Debes tener permisos de escritura
        - Nombre EXACTO, mayúsculas/minúsculas
        
        **4. Reinicia la app de Streamlit:**
        - Ve a **Manage app → Settings**
        - Haz clic en **"Redeploy"** o **"Restart"**
        
        **5. Si NADA funciona:**
        Usa el sistema de backup manual que ya implementamos.
        """)