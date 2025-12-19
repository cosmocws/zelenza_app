import streamlit as st
import os
import shutil

def gestion_modelos_factura():
    st.subheader("📄 Gestión de Modelos de Factura")
    
    # Crear carpeta principal si no existe
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # Obtener empresas existentes (carpetas creadas)
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### ➕ Crear Nueva Empresa")
        nueva_empresa = st.text_input("Nombre de la empresa", placeholder="Ej: MiEmpresa S.L.")
        
        if st.button("Crear Empresa") and nueva_empresa:
            # Crear carpeta para la nueva empresa
            carpeta_empresa = f"modelos_facturas/{nueva_empresa.lower().replace(' ', '_')}"
            os.makedirs(carpeta_empresa, exist_ok=True)
            # Hacer BACKUP
            if os.path.exists("modelos_facturas"):
                os.makedirs("data_backup", exist_ok=True)
                if os.path.exists("data_backup/modelos_facturas"):
                    shutil.rmtree("data_backup/modelos_facturas")
                shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
            st.success(f"✅ Empresa '{nueva_empresa}' creada correctamente")
            st.rerun()
    
    with col2:
        st.write("### 📁 Empresas Existentes")
        if empresas_existentes:
            for empresa in empresas_existentes:
                st.write(f"**{empresa}**")
        else:
            st.info("No hay empresas creadas aún")
    
    # Subir modelos para una empresa existente
    if empresas_existentes:
        st.write("### 📤 Subir Modelo de Factura")
        empresa_seleccionada = st.selectbox("Seleccionar Empresa", empresas_existentes)
        
        archivo = st.file_uploader("Subir modelo de factura", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if archivo is not None:
            # Guardar archivo
            carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
            ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
            with open(ruta_archivo, "wb") as f:
                f.write(archivo.getbuffer())
            
            # Hacer BACKUP
            if os.path.exists("modelos_facturas"):
                os.makedirs("data_backup", exist_ok=True)
                if os.path.exists("data_backup/modelos_facturas"):
                    shutil.rmtree("data_backup/modelos_facturas")
                shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
            
            st.success(f"✅ Modelo para {empresa_seleccionada} guardado correctamente")
            if archivo.type.startswith('image'):
                st.image(archivo, caption=f"Modelo de factura - {empresa_seleccionada}", use_container_width=True)
    
    # GESTIÓN Y ELIMINACIÓN DE EMPRESAS Y ARCHIVOS
    if empresas_existentes:
        st.write("### 🗑️ Gestión de Empresas y Archivos")
        
        empresa_gestion = st.selectbox("Seleccionar empresa para gestionar", empresas_existentes, key="gestion_empresa")
        carpeta_empresa = f"modelos_facturas/{empresa_gestion}"
        
        # Mostrar archivos de la empresa seleccionada
        archivos_empresa = os.listdir(carpeta_empresa) if os.path.exists(carpeta_empresa) else []
        
        if archivos_empresa:
            st.write(f"**Archivos en {empresa_gestion}:**")
            for archivo in archivos_empresa:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {archivo}")
                with col2:
                    if st.button("🗑️", key=f"del_{archivo}"):
                        ruta_archivo = os.path.join(carpeta_empresa, archivo)
                        os.remove(ruta_archivo)
                        # Hacer BACKUP después de eliminar
                        if os.path.exists("modelos_facturas"):
                            os.makedirs("data_backup", exist_ok=True)
                            if os.path.exists("data_backup/modelos_facturas"):
                                shutil.rmtree("data_backup/modelos_facturas")
                            shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                        st.success(f"✅ Archivo '{archivo}' eliminado")
                        st.rerun()
            
            # Botón para eliminar todos los archivos de la empresa
            if st.button("🗑️ Eliminar todos los archivos de esta empresa", type="secondary"):
                for archivo in archivos_empresa:
                    ruta_archivo = os.path.join(carpeta_empresa, archivo)
                    os.remove(ruta_archivo)
                # Hacer BACKUP después de eliminar
                if os.path.exists("modelos_facturas"):
                    os.makedirs("data_backup", exist_ok=True)
                    if os.path.exists("data_backup/modelos_facturas"):
                        shutil.rmtree("data_backup/modelos_facturas")
                    shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                st.success(f"✅ Todos los archivos de {empresa_gestion} eliminados")
                st.rerun()
        else:
            st.info(f"ℹ️ No hay archivos en {empresa_gestion}")
        
        # Botón para eliminar la empresa completa (solo si está vacía)
        st.markdown("---")
        if not archivos_empresa:
            if st.button("🗑️ Eliminar esta empresa", type="primary"):
                os.rmdir(carpeta_empresa)
                # Hacer BACKUP después de eliminar
                if os.path.exists("modelos_facturas"):
                    os.makedirs("data_backup", exist_ok=True)
                    if os.path.exists("data_backup/modelos_facturas"):
                        shutil.rmtree("data_backup/modelos_facturas")
                    shutil.copytree("modelos_facturas", "data_backup/modelos_facturas")
                st.success(f"✅ Empresa '{empresa_gestion}' eliminada")
                st.rerun()
        else:
            st.warning("⚠️ No se puede eliminar la empresa porque tiene archivos. Elimina primero todos los archivos.")

def consultar_modelos_factura():
    st.subheader("📊 Modelos de Factura")
    
    # Obtener empresas existentes (carpetas creadas por admin)
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    if not empresas_existentes:
        st.warning("⚠️ No hay modelos de factura disponibles")
        st.info("Contacta con el administrador para que configure los modelos de factura")
        return
    
    st.info("Selecciona tu compañía eléctrica para ver los modelos de factura")
    empresa_seleccionada = st.selectbox("Selecciona tu compañía eléctrica", empresas_existentes)
    
    # Mostrar modelos disponibles para esa empresa
    carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
    
    archivos = os.listdir(carpeta_empresa)
    if archivos:
        st.write(f"### 📋 Modelos disponibles para {empresa_seleccionada}:")
        
        for archivo in archivos:
            ruta_completa = os.path.join(carpeta_empresa, archivo)
            st.write(f"**Modelo:** {archivo}")
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                st.image(ruta_completa, use_container_width=True)
            st.markdown("---")
    else:
        st.warning(f"⚠️ No hay modelos de factura subidos para {empresa_seleccionada}")