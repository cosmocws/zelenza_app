import streamlit as st
import json
import os
import shutil
from datetime import datetime
from modules.auth import cargar_config_sistema, guardar_config_sistema
from modules.utils import cargar_configuracion_usuarios, guardar_configuracion_usuarios

def gestion_usuarios():
    st.subheader("👥 Gestión de Usuarios y Grupos")
    
    # Cargar configuración
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    # Pestañas
    tab1, tab2, tab3 = st.tabs(["👤 Usuarios", "👥 Grupos", "➕ Crear Usuario"])
    
    with tab1:
        st.write("### 📊 Lista de Usuarios")
        
        for username, config in usuarios_config.items():
            if username == "admin":
                continue
                
            with st.expander(f"👤 {username} - {config.get('nombre', 'Sin nombre')}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("Nombre", value=config.get('nombre', ''), 
                                                 key=f"nombre_{username}")
                    
                    # Selección de grupo
                    grupo_actual = config.get('grupo', '')
                    grupo_seleccionado = st.selectbox(
                        "Grupo",
                        [""] + list(grupos.keys()),
                        index=0 if not grupo_actual else (list(grupos.keys()).index(grupo_actual) + 1),
                        key=f"grupo_{username}"
                    )
                    
                    # Campo para cambiar contraseña
                    st.write("**🔐 Cambiar contraseña:**")
                    nueva_password = st.text_input(
                        "Nueva contraseña",
                        type="password",
                        placeholder="Dejar vacío para no cambiar",
                        key=f"pass_{username}"
                    )
                    if nueva_password:
                        st.info("⚠️ La contraseña se cambiará al guardar")
                
                with col2:
                    # Mostrar permisos basados en grupo
                    if grupo_seleccionado and grupo_seleccionado in grupos:
                        permisos = grupos[grupo_seleccionado]
                        st.write("**Permisos del grupo:**")
                        st.write(f"📈 Luz: {', '.join(permisos.get('planes_luz', []))}")
                        st.write(f"🔥 Gas: {', '.join(permisos.get('planes_gas', []))}")
                    
                    # Información adicional del usuario
                    st.write("**Información:**")
                    st.write(f"📧 Username: `{username}`")
                    st.write(f"🔑 Tipo: {config.get('tipo', 'user')}")
                    
                    # Botones de acción
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar", key=f"save_{username}"):
                            usuarios_config[username]['nombre'] = nuevo_nombre
                            usuarios_config[username]['grupo'] = grupo_seleccionado
                            
                            # Actualizar contraseña si se proporcionó
                            if nueva_password:
                                usuarios_config[username]['password'] = nueva_password
                                st.success(f"✅ Contraseña actualizada para {username}")
                            
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} actualizado")
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Eliminar", key=f"del_{username}"):
                            del usuarios_config[username]
                            guardar_configuracion_usuarios(usuarios_config)
                            st.success(f"✅ Usuario {username} eliminado")
                            st.rerun()
    
    with tab2:
        st.write("### 👥 Gestión de Grupos")
        
        for grupo_nombre, permisos in grupos.items():
            with st.expander(f"**Grupo: {grupo_nombre}**", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Planes de Luz**")
                    try:
                        df_luz = pd.read_csv("data/precios_luz.csv")
                        planes_luz_disponibles = df_luz['plan'].tolist()
                    except:
                        planes_luz_disponibles = []
                    
                    planes_luz_actuales = permisos.get('planes_luz', [])
                    if planes_luz_actuales == ["TODOS"]:
                        planes_luz_actuales = planes_luz_disponibles
                    
                    planes_luz_seleccionados = st.multiselect(
                        "Planes de luz permitidos",
                        planes_luz_disponibles,
                        default=planes_luz_actuales,
                        key=f"grupo_luz_{grupo_nombre}"
                    )
                
                with col2:
                    st.write("**Planes de Gas**")
                    planes_gas_disponibles = ["RL1", "RL2", "RL3"]
                    planes_gas_actuales = permisos.get('planes_gas', [])
                    
                    planes_gas_seleccionados = st.multiselect(
                        "Planes de gas permitidos",
                        planes_gas_disponibles,
                        default=planes_gas_actuales,
                        key=f"grupo_gas_{grupo_nombre}"
                    )
                
                if st.button("💾 Actualizar Grupo", key=f"update_grupo_{grupo_nombre}"):
                    grupos[grupo_nombre] = {
                        "planes_luz": planes_luz_seleccionados,
                        "planes_gas": planes_gas_seleccionados
                    }
                    config_sistema['grupos_usuarios'] = grupos
                    guardar_config_sistema(config_sistema)
                    st.success(f"✅ Grupo {grupo_nombre} actualizado")
                    st.rerun()
        
        # Crear nuevo grupo
        st.write("### ➕ Crear Nuevo Grupo")
        nuevo_grupo_nombre = st.text_input("Nombre del nuevo grupo")
        
        if st.button("Crear Grupo") and nuevo_grupo_nombre:
            if nuevo_grupo_nombre not in grupos:
                grupos[nuevo_grupo_nombre] = {
                    "planes_luz": [],
                    "planes_gas": []
                }
                config_sistema['grupos_usuarios'] = grupos
                guardar_config_sistema(config_sistema)
                st.success(f"✅ Grupo {nuevo_grupo_nombre} creado")
                st.rerun()
            else:
                st.error("❌ El grupo ya existe")
    
    with tab3:
        st.write("### 👤 Crear Nuevo Usuario")
        
        with st.form("form_nuevo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_username = st.text_input("Username*", 
                                              help="Nombre de usuario para el acceso")
                nuevo_nombre = st.text_input("Nombre completo*", 
                                            help="Nombre real del usuario")
                grupo_usuario = st.selectbox("Grupo", [""] + list(grupos.keys()),
                                           help="Asigna un grupo de permisos")
            
            with col2:
                # Campo para contraseña
                password_usuario = st.text_input(
                    "Contraseña*", 
                    type="password",
                    help="Contraseña para acceso manual"
                )
                confirm_password = st.text_input(
                    "Confirmar contraseña*", 
                    type="password",
                    help="Repite la contraseña"
                )
                
                # Opciones adicionales
                tipo_usuario = st.selectbox(
                    "Tipo de usuario",
                    ["user", "auto", "manual"],
                    help="user: Usuario normal, auto: Autogenerado, manual: Creado manualmente"
                )
                
                # Checkbox para planes específicos
                st.write("**Planes especiales:**")
                planes_luz_todos = st.checkbox("Todos los planes de luz", value=True)
                planes_gas_todos = st.checkbox("Todos los planes de gas", value=True)
            
            submitted = st.form_submit_button("👤 Crear Usuario")
            
            if submitted:
                if not nuevo_username or not nuevo_nombre:
                    st.error("❌ Username y nombre son obligatorios")
                elif not password_usuario:
                    st.error("❌ La contraseña es obligatoria")
                elif password_usuario != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                elif nuevo_username in usuarios_config:
                    st.error("❌ El username ya existe")
                else:
                    # Configurar planes según selección
                    planes_luz = "TODOS" if planes_luz_todos else []
                    planes_gas = ["RL1", "RL2", "RL3"] if planes_gas_todos else []
                    
                    # Crear usuario
                    usuarios_config[nuevo_username] = {
                        "nombre": nuevo_nombre,
                        "password": password_usuario,
                        "grupo": grupo_usuario,
                        "tipo": tipo_usuario,
                        "planes_luz": planes_luz,
                        "planes_gas": planes_gas,
                        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "creado_por": st.session_state.username
                    }
                    
                    guardar_configuracion_usuarios(usuarios_config)
                    
                    # Mostrar resumen
                    st.success(f"✅ Usuario {nuevo_username} creado exitosamente")
                    st.info(f"""
                    **Resumen del usuario creado:**
                    - **Username:** `{nuevo_username}`
                    - **Nombre:** {nuevo_nombre}
                    - **Grupo:** {grupo_usuario if grupo_usuario else 'Ninguno'}
                    - **Tipo:** {tipo_usuario}
                    - **Contraseña:** {'✓ Configurada'}
                    - **Planes luz:** {'Todos' if planes_luz_todos else 'Específicos'}
                    - **Planes gas:** {'Todos' if planes_gas_todos else 'Específicos'}
                    """)
                    
                    # Mostrar credenciales
                    credenciales = f"Usuario: {nuevo_username}\nContraseña: {password_usuario}"
                    st.code(credenciales, language="text")
                    
                    st.rerun()