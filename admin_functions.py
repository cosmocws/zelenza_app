import streamlit as st
import pandas as pd
import json
import os
import uuid
import shutil
from datetime import datetime, timedelta
import pytz

from config import (
    COMUNIDADES_AUTONOMAS, PLANES_GAS_ESTRUCTURA, 
    PMG_COSTE, PMG_IVA, ESTADOS_PVD, GRUPOS_PVD_CONFIG
)
from database import (
    cargar_configuracion_usuarios, guardar_configuracion_usuarios,
    cargar_config_sistema, guardar_config_sistema,
    cargar_config_pvd, guardar_config_pvd,
    cargar_cola_pvd, guardar_cola_pvd
)
from pvd_system import (
    temporizador_pvd_mejorado, temporizador_pvd, actualizar_temporizadores_pvd,
    verificar_pausas_completadas, iniciar_siguiente_en_cola
)
from utils import obtener_hora_madrid, formatear_hora_madrid

# ==============================================
# FUNCIONES DE ADMINISTRACIÓN
# ==============================================

def gestion_electricidad():
    """Gestión de planes de electricidad"""
    st.subheader("⚡ Gestión de Planes de Electricidad")
    
    # Cargar datos actuales
    try:
        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
        if df_luz.empty:
            df_luz = pd.DataFrame(columns=[
                'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
                'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
                'comunidades_autonomas'
            ])
            st.info("📝 No hay planes configurados. ¡Crea el primero!")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.warning("⚠️ No hay datos de electricidad. ¡Crea tu primer plan!")
        df_luz = pd.DataFrame(columns=[
            'plan', 'precio_original_kwh', 'con_pi_kwh', 'sin_pi_kwh',
            'punta', 'valle', 'total_potencia', 'activo', 'umbral_especial_plus',
            'comunidades_autonomas'
        ])
    
    # Mostrar planes actuales
    st.write("### 📊 Planes Actuales")
    if not df_luz.empty:
        planes_activos = df_luz[df_luz['activo'] == True]
        planes_inactivos = df_luz[df_luz['activo'] == False]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**✅ Planes Activos**")
            for _, plan in planes_activos.iterrows():
                if st.button(f"📝 {plan['plan']}", key=f"edit_{plan['plan']}", use_container_width=True):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with col2:
            st.write("**❌ Planes Inactivos**")
            for _, plan in planes_inactivos.iterrows():
                if st.button(f"📝 {plan['plan']}", key=f"edit_inactive_{plan['plan']}", use_container_width=True):
                    st.session_state.editing_plan = plan.to_dict()
                    st.rerun()
        
        with col3:
            st.write("**📈 Resumen**")
            st.metric("Planes Activos", len(planes_activos))
            st.metric("Planes Inactivos", len(planes_inactivos))
            st.metric("Total Planes", len(df_luz))
    
    else:
        st.info("No hay planes configurados aún")
    
    # Formulario para añadir/editar
    st.write("### ➕ Añadir/✏️ Editar Plan")
    
    if 'editing_plan' not in st.session_state:
        st.session_state.editing_plan = None
    
    if st.session_state.editing_plan is not None:
        plan_actual = st.session_state.editing_plan
        st.warning(f"✏️ Editando: **{plan_actual['plan']}**")
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_plan = None
            st.rerun()
    
    with st.form("form_plan_electricidad"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.editing_plan is not None:
                nombre_plan = st.text_input("Nombre del Plan*", 
                                          value=st.session_state.editing_plan['plan'],
                                          disabled=True)
                st.info("⚠️ El nombre no se puede modificar al editar")
            else:
                nombre_plan = st.text_input("Nombre del Plan*", placeholder="Ej: IMPULSA 24h")
            
            precio_original = st.number_input("Precio Original kWh*", min_value=0.0, format="%.3f", 
                                            value=st.session_state.editing_plan.get('precio_original_kwh', 0.170) if st.session_state.editing_plan else 0.170)
            con_pi = st.number_input("Con PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan.get('con_pi_kwh', 0.130) if st.session_state.editing_plan else 0.130)
        
        with col2:
            sin_pi = st.number_input("Sin PI kWh*", min_value=0.0, format="%.3f",
                                   value=st.session_state.editing_plan.get('sin_pi_kwh', 0.138) if st.session_state.editing_plan else 0.138)
            punta = st.number_input("Punta €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan.get('punta', 0.116) if st.session_state.editing_plan else 0.116)
            valle = st.number_input("Valle €*", min_value=0.0, format="%.3f",
                                  value=st.session_state.editing_plan.get('valle', 0.046) if st.session_state.editing_plan else 0.046)
        
        with col3:
            total_potencia = punta + valle
            st.number_input("Total Potencia €*", min_value=0.0, format="%.3f",
                          value=total_potencia, disabled=True, key="total_potencia_display")
            st.caption("💡 Calculado automáticamente: Punta + Valle")
            
            activo = st.checkbox("Plan activo", 
                               value=st.session_state.editing_plan.get('activo', True) if st.session_state.editing_plan else True)
        
        # Comunidades autónomas
        st.write("### 🗺️ Comunidades Autónomas Disponibles")
        comunidades_actuales = []
        if st.session_state.editing_plan and 'comunidades_autonomas' in st.session_state.editing_plan:
            if pd.notna(st.session_state.editing_plan['comunidades_autonomas']):
                comunidades_actuales = st.session_state.editing_plan['comunidades_autonomas'].split(';')
        
        if not st.session_state.editing_plan:
            comunidades_actuales = ["Toda España"]
        
        comunidades_seleccionadas = st.multiselect(
            "Comunidades donde está disponible el plan:",
            COMUNIDADES_AUTONOMAS,
            default=comunidades_actuales,
            help="Selecciona las comunidades autónomas donde este plan está disponible"
        )
        
        submitted = st.form_submit_button(
            "💾 Guardar Cambios" if st.session_state.editing_plan else "➕ Crear Nuevo Plan", 
            type="primary"
        )
        
        if submitted:
            if not nombre_plan:
                st.error("❌ El nombre del plan es obligatorio")
            elif not comunidades_seleccionadas:
                st.error("❌ Debes seleccionar al menos una comunidad autónoma")
            else:
                nuevo_plan_data = {
                    'plan': nombre_plan,
                    'precio_original_kwh': precio_original,
                    'con_pi_kwh': con_pi,
                    'sin_pi_kwh': sin_pi,
                    'punta': punta,
                    'valle': valle,
                    'total_potencia': total_potencia,
                    'activo': activo,
                    'comunidades_autonomas': ';'.join(comunidades_seleccionadas)
                }
                
                if st.session_state.editing_plan is not None and 'umbral_especial_plus' in st.session_state.editing_plan:
                    nuevo_plan_data['umbral_especial_plus'] = st.session_state.editing_plan['umbral_especial_plus']
                else:
                    if "ESPECIAL PLUS" in nombre_plan.upper():
                        nuevo_plan_data['umbral_especial_plus'] = 15.00
                    else:
                        nuevo_plan_data['umbral_especial_plus'] = 0.00
                
                # Añadir o actualizar
                if nombre_plan in df_luz['plan'].values:
                    idx = df_luz[df_luz['plan'] == nombre_plan].index[0]
                    for key, value in nuevo_plan_data.items():
                        df_luz.at[idx, key] = value
                    st.success(f"✅ Plan '{nombre_plan}' actualizado correctamente")
                else:
                    df_luz = pd.concat([df_luz, pd.DataFrame([nuevo_plan_data])], ignore_index=True)
                    st.success(f"✅ Plan '{nombre_plan}' añadido correctamente")
                
                df_luz.to_csv("data/precios_luz.csv", index=False, encoding='utf-8')
                os.makedirs("data_backup", exist_ok=True)
                shutil.copy("data/precios_luz.csv", "data_backup/precios_luz.csv")
                
                st.session_state.editing_plan = None
                st.rerun()

def gestion_gas():
    """Gestión de planes de gas"""
    st.subheader("🔥 Gestión de Planes de Gas")
    
    # Cargar datos actuales
    try:
        with open('data/planes_gas.json', 'r', encoding='utf-8') as f:
            planes_gas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        planes_gas = PLANES_GAS_ESTRUCTURA
    
    # Configuración PMG
    st.write("### ⚙️ Configuración PMG (Pack Mantenimiento Gas)")
    
    col_pmg1, col_pmg2 = st.columns(2)
    with col_pmg1:
        pmg_coste = st.number_input("Coste PMG (€/mes):", value=PMG_COSTE, min_value=0.0, format="%.2f")
    with col_pmg2:
        pmg_iva = st.number_input("IVA PMG (%):", value=PMG_IVA * 100, min_value=0.0, max_value=100.0, format="%.1f") / 100
    
    if st.button("💾 Guardar Configuración PMG", key="guardar_pmg"):
        config_pmg = {"coste": pmg_coste, "iva": pmg_iva}
        with open('data/config_pmg.json', 'w', encoding='utf-8') as f:
            json.dump(config_pmg, f, indent=4, ensure_ascii=False)
        st.success("✅ Configuración PMG guardada")
    
    st.markdown("---")
    
    # Gestión de planes RL
    st.write("### 📊 Planes de Gas RL1, RL2, RL3")
    
    for rl, plan in planes_gas.items():
        with st.expander(f"**{rl}** - {plan['rango']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Términos CON PMG**")
                plan["termino_fijo_con_pmg"] = st.number_input(
                    f"Término fijo CON PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_con_{rl}"
                )
                plan["termino_variable_con_pmg"] = st.number_input(
                    f"Término variable CON PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_con_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_con_{rl}"
                )
            
            with col2:
                st.write("**Términos SIN PMG**")
                plan["termino_fijo_sin_pmg"] = st.number_input(
                    f"Término fijo SIN PMG (€/mes) - {rl}:",
                    value=float(plan["termino_fijo_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"fijo_sin_{rl}"
                )
                plan["termino_variable_sin_pmg"] = st.number_input(
                    f"Término variable SIN PMG (€/kWh) - {rl}:",
                    value=float(plan["termino_variable_sin_pmg"]),
                    min_value=0.0,
                    format="%.3f",
                    key=f"var_sin_{rl}"
                )
            
            plan["precio_original_kwh"] = st.number_input(
                f"Precio original kWh (€) - {rl}:",
                value=float(plan["precio_original_kwh"]),
                min_value=0.0,
                format="%.3f",
                key=f"precio_{rl}"
            )
            
            plan["activo"] = st.checkbox(f"Plan activo - {rl}", 
                                       value=plan["activo"],
                                       key=f"activo_{rl}")
    
    if st.button("💾 Guardar Todos los Planes de Gas", type="primary"):
        os.makedirs('data', exist_ok=True)
        with open('data/planes_gas.json', 'w', encoding='utf-8') as f:
            json.dump(planes_gas, f, indent=4, ensure_ascii=False)
        os.makedirs("data_backup", exist_ok=True)
        shutil.copy("data/planes_gas.json", "data_backup/planes_gas.json")
        st.success("✅ Todos los planes de gas guardados correctamente")
        st.rerun()

def gestion_usuarios():
    """Gestión de usuarios y grupos"""
    st.subheader("👥 Gestión de Usuarios y Grupos")
    
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    
    tab1, tab2, tab3 = st.tabs(["👤 Usuarios", "👥 Grupos", "➕ Crear Usuario"])
    
    with tab1:
        st.write("### 📊 Lista de Usuarios")
        
        for username, config in usuarios_config.items():
            if username == "admin":
                continue
                
            with st.expander(f"👤 {username} - {config.get('nombre', 'Sin nombre')}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("Nombre", value=config.get('nombre', ''), key=f"nombre_{username}")
                    
                    grupo_actual = config.get('grupo', '')
                    grupo_seleccionado = st.selectbox(
                        "Grupo",
                        [""] + list(grupos.keys()),
                        index=0 if not grupo_actual else (list(grupos.keys()).index(grupo_actual) + 1),
                        key=f"grupo_{username}"
                    )
                    
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
                    if grupo_seleccionado and grupo_seleccionado in grupos:
                        permisos = grupos[grupo_seleccionado]
                        st.write("**Permisos del grupo:**")
                        st.write(f"📈 Luz: {', '.join(permisos.get('planes_luz', []))}")
                        st.write(f"🔥 Gas: {', '.join(permisos.get('planes_gas', []))}")
                    
                    st.write("**Información:**")
                    st.write(f"📧 Username: `{username}`")
                    st.write(f"🔑 Tipo: {config.get('tipo', 'user')}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar", key=f"save_{username}"):
                            usuarios_config[username]['nombre'] = nuevo_nombre
                            usuarios_config[username]['grupo'] = grupo_seleccionado
                            
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
                        df_luz = pd.read_csv("data/precios_luz.csv", encoding='utf-8')
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
                nuevo_username = st.text_input("Username*", help="Nombre de usuario para el acceso")
                nuevo_nombre = st.text_input("Nombre completo*", help="Nombre real del usuario")
                grupo_usuario = st.selectbox("Grupo", [""] + list(grupos.keys()), help="Asigna un grupo de permisos")
            
            with col2:
                password_usuario = st.text_input("Contraseña*", type="password", help="Contraseña para acceso manual")
                confirm_password = st.text_input("Confirmar contraseña*", type="password", help="Repite la contraseña")
                
                tipo_usuario = st.selectbox("Tipo de usuario", ["user", "auto", "manual"], help="user: Usuario normal, auto: Autogenerado, manual: Creado manualmente")
                
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
                    planes_luz = "TODOS" if planes_luz_todos else []
                    planes_gas = ["RL1", "RL2", "RL3"] if planes_gas_todos else []
                    
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
                    st.success(f"✅ Usuario {nuevo_username} creado exitosamente")
                    
                    credenciales = f"Usuario: {nuevo_username}\nContraseña: {password_usuario}"
                    st.code(credenciales, language="text")
                    st.rerun()

def gestion_pvd_admin():
    """Administración del sistema PVD con grupos"""
    st.subheader("👁️ Administración PVD (Pausa Visual Dinámica)")
    
    hora_actual_madrid = obtener_hora_madrid().strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora del servidor (Madrid):** {hora_actual_madrid}")
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', GRUPOS_PVD_CONFIG)
    
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        if st.button("🔄 Actualizar Estado", key="refresh_admin", use_container_width=True, type="primary"):
            temporizador_pvd_mejorado._verificar_y_actualizar()
            st.rerun()
    with col_btn2:
        if st.button("📊 Actualizar Temporizadores", key="refresh_timers", use_container_width=True):
            temporizador_pvd_mejorado._verificar_y_actualizar()
            st.rerun()
    with col_btn3:
        if st.button("👥 Ver Grupos", key="ver_grupos", use_container_width=True):
            st.session_state.mostrar_grupos_pvd = not st.session_state.get('mostrar_grupos_pvd', False)
            st.rerun()
    with col_btn4:
        if st.button("🧹 Limpiar Completadas", key="clean_completed", use_container_width=True):
            fecha_limite = obtener_hora_madrid() - timedelta(days=1)
            cola_limpia = [p for p in cola_pvd if not (
                p['estado'] == 'COMPLETADO' and 
                'timestamp_fin' in p and
                datetime.fromisoformat(p['timestamp_fin']) < fecha_limite
            )]
            
            if len(cola_limpia) < len(cola_pvd):
                guardar_cola_pvd(cola_limpia)
                st.success(f"✅ Limpiadas {len(cola_pvd) - len(cola_limpia)} pausas antiguas")
                st.rerun()
            else:
                st.info("ℹ️ No hay pausas antiguas para limpiar")
    
    # Configuración del sistema PVD
    st.write("### ⚙️ Configuración General del Sistema PVD")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**🔧 Configuración Automática**")
        auto_finalizar = st.checkbox(
            "Finalización automática de pausas",
            value=config_pvd.get('auto_finalizar_pausa', True),
            help="Las pausas se finalizan automáticamente al completar su tiempo"
        )
        notificacion_auto = st.checkbox(
            "Notificación automática al siguiente",
            value=config_pvd.get('notificacion_automatica', True),
            help="Notifica automáticamente al siguiente en cola"
        )
    with col2:
        st.write("**⏱️ Temporizador Interno**")
        intervalo_temporizador = st.number_input(
            "Intervalo temporizador (segundos)",
            min_value=10,
            max_value=300,
            value=config_pvd.get('intervalo_temporizador', 60),
            help="Cada cuántos segundos se ejecuta el temporizador interno"
        )
        max_reintentos = st.number_input(
            "Máximo reintentos notificación",
            min_value=0,
            max_value=5,
            value=config_pvd.get('max_reintentos_notificacion', 2),
            help="Máximo número de reintentos de notificación"
        )
    
    if st.button("💾 Guardar Configuración PVD", type="primary", key="save_config_pvd"):
        config_pvd.update({
            'auto_finalizar_pausa': auto_finalizar,
            'notificacion_automatica': notificacion_auto,
            'intervalo_temporizador': intervalo_temporizador,
            'max_reintentos_notificacion': max_reintentos
        })
        guardar_config_pvd(config_pvd)
        st.success("✅ Configuración PVD guardada")
        st.rerun()
    
    # Mostrar grupos si está activado
    if st.session_state.get('mostrar_grupos_pvd', False):
        st.write("### 👥 Configuración de Grupos PVD")
        
        for grupo_id, config_grupo in grupos_config.items():
            estado = temporizador_pvd_mejorado.obtener_estado_grupo(grupo_id)
            
            with st.expander(f"**Grupo: {grupo_id}**", expanded=True):
                col_g1, col_g2, col_g3, col_g4 = st.columns(4)
                with col_g1:
                    nuevos_agentes = st.number_input(
                        "Agentes en grupo",
                        min_value=1,
                        max_value=100,
                        value=config_grupo.get('agentes_por_grupo', 10),
                        key=f"agentes_{grupo_id}"
                    )
                with col_g2:
                    nuevo_max = st.number_input(
                        "Máx. simultáneo",
                        min_value=1,
                        max_value=20,
                        value=config_grupo.get('maximo_simultaneo', 2),
                        key=f"max_{grupo_id}"
                    )
                with col_g3:
                    nueva_corta = st.number_input(
                        "Duración corta (min)",
                        min_value=1,
                        max_value=30,
                        value=config_grupo.get('duracion_corta', 5),
                        key=f"corta_{grupo_id}"
                    )
                with col_g4:
                    nueva_larga = st.number_input(
                        "Duración larga (min)",
                        min_value=1,
                        max_value=60,
                        value=config_grupo.get('duracion_larga', 10),
                        key=f"larga_{grupo_id}"
                    )
                
                # Estadísticas del grupo
                st.write(f"**📊 Estadísticas actuales:**")
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("En pausa", f"{estado['en_pausa']}/{nuevo_max}")
                with col_stat2:
                    st.metric("En espera", estado['en_espera'])
                with col_stat3:
                    st.metric("Completadas hoy", estado.get('completados_hoy', 0))
                
                if st.button("💾 Actualizar Grupo", key=f"update_grupo_pvd_{grupo_id}"):
                    grupos_config[grupo_id] = {
                        'agentes_por_grupo': nuevos_agentes,
                        'maximo_simultaneo': nuevo_max,
                        'duracion_corta': nueva_corta,
                        'duracion_larga': nueva_larga
                    }
                    
                    config_sistema['grupos_pvd'] = grupos_config
                    guardar_config_sistema(config_sistema)
                    
                    st.success(f"✅ Grupo {grupo_id} actualizado")
                    st.rerun()
        
        # Crear nuevo grupo PVD
        st.write("### ➕ Crear Nuevo Grupo PVD")
        nuevo_grupo_nombre = st.text_input("Nombre del nuevo grupo PVD")
        
        if st.button("Crear Grupo PVD") and nuevo_grupo_nombre:
            if nuevo_grupo_nombre not in grupos_config:
                grupos_config[nuevo_grupo_nombre] = {
                    'agentes_por_grupo': 10,
                    'maximo_simultaneo': 2,
                    'duracion_corta': 5,
                    'duracion_larga': 10
                }
                
                config_sistema['grupos_pvd'] = grupos_config
                guardar_config_sistema(config_sistema)
                
                st.success(f"✅ Grupo PVD {nuevo_grupo_nombre} creado")
                st.rerun()
            else:
                st.error("❌ El grupo PVD ya existe")

        # Borrar grupo PVD existente
        st.write("### 🗑️ Borrar Grupo PVD")
        grupos_existentes = list(grupos_config.keys())
        if grupos_existentes:
            grupo_a_borrar = st.selectbox(
                "Seleccionar grupo a borrar",
                grupos_existentes,
                key="borrar_grupo_pvd"
            )
    
            if st.button("🗑️ Borrar Grupo", key="borrar_grupo_btn", type="secondary"):
                if len(grupos_existentes) <= 1:
                    st.error("❌ No puedes borrar todos los grupos. Debe quedar al menos uno.")
                elif grupo_a_borrar == 'basico':
                    st.error("❌ No puedes borrar el grupo 'basico' (grupo por defecto).")
                else:
                    # Confirmación
                    confirmacion = st.text_input(f"Escribe 'BORRAR {grupo_a_borrar}' para confirmar")
                    if confirmacion == f"BORRAR {grupo_a_borrar}":
                        # Borrar grupo de la configuración
                        del grupos_config[grupo_a_borrar]
                        config_sistema['grupos_pvd'] = grupos_config
                        guardar_config_sistema(config_sistema)
                
                        # Actualizar usuarios que tenían ese grupo
                        usuarios_config = cargar_configuracion_usuarios()
                        usuarios_modificados = 0
                        for username, config in usuarios_config.items():
                            if config.get('grupo') == grupo_a_borrar:
                                usuarios_config[username]['grupo'] = 'basico'
                                usuarios_modificados += 1
                
                        if usuarios_modificados > 0:
                            guardar_configuracion_usuarios(usuarios_config)
                
                        st.success(f"✅ Grupo '{grupo_a_borrar}' borrado. {usuarios_modificados} usuarios asignados al grupo 'basico'.")
                        st.rerun()
                    elif confirmacion:
                        st.error("❌ Texto de confirmación incorrecto.")
        else:
            st.info("No hay grupos para borrar")
    
    # Estadísticas actuales
    st.markdown("---")
    st.write("### 📊 Estado Actual del Sistema")
    
    en_pausa = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO'])
    en_espera = len([p for p in cola_pvd if p['estado'] == 'ESPERANDO'])
    completados_hoy = len([p for p in cola_pvd if p['estado'] == 'COMPLETADO' and 
                          'timestamp_fin' in p and
                          datetime.fromisoformat(p['timestamp_fin']).date() == obtener_hora_madrid().date()])
    cancelados_hoy = len([p for p in cola_pvd if p['estado'] == 'CANCELADO' and 
                         'timestamp_solicitud' in p and
                         datetime.fromisoformat(p['timestamp_solicitud']).date() == obtener_hora_madrid().date()])
    
    temporizadores_activos = len(temporizador_pvd_mejorado.temporizadores_activos)
    notificaciones_pendientes = len(temporizador_pvd_mejorado.notificaciones_pendientes)
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5, col_stat6 = st.columns(6)
    with col_stat1:
        st.metric("👥 Agentes Activos", config_pvd.get('agentes_activos', 25))
    with col_stat2:
        st.metric("⏸️ En Pausa", f"{en_pausa}/{config_pvd.get('maximo_simultaneo', 3)}")
    with col_stat3:
        st.metric("⏳ En Espera", en_espera)
    with col_stat4:
        st.metric("✅ Completadas Hoy", completados_hoy)
    with col_stat5:
        st.metric("⏱️ Temporizadores", temporizadores_activos)
    with col_stat6:
        st.metric("🔔 Notificaciones", notificaciones_pendientes)
    
    # Información del temporizador automático
    st.info(f"⏱️ **Temporizador automático:** Ejecutándose cada {config_pvd.get('intervalo_temporizador', 60)} segundos")
    st.caption(f"Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
    
    # Pausas en curso
    st.markdown("---")
    st.write("### 📋 Pausas en Curso")
    
    pausas_en_curso = [p for p in cola_pvd if p['estado'] == 'EN_CURSO']
    
    if pausas_en_curso:
        for pausa in pausas_en_curso:
            with st.container():
                col_info, col_acciones = st.columns([3, 1])
                with col_info:
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                    tiempo_transcurrido = int((obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60)
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
                    st.progress(int(progreso))
                    
                    hora_inicio_madrid = formatear_hora_madrid(tiempo_inicio)
                    hora_fin_estimada = formatear_hora_madrid(tiempo_inicio + timedelta(minutes=duracion_minutos))
                    
                    grupo_info = f" | 👥 {pausa.get('grupo', 'N/A')}" if 'grupo' in pausa else ""
                    
                    st.write(f"**Agente:** {pausa.get('usuario_nombre', 'Desconocido')}{grupo_info}")
                    st.write(f"**Usuario ID:** {pausa['usuario_id']}")
                    st.write(f"**Duración:** {duracion_minutos} min ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
                    st.write(f"**Inició:** {hora_inicio_madrid} | **Finaliza:** {hora_fin_estimada}")
                    st.write(f"**Transcurrido:** {tiempo_transcurrido} min | **Restante:** {tiempo_restante} min")
                    
                    if tiempo_restante == 0:
                        st.warning("⏰ **Pausa finalizada automáticamente**")
                        if pausa.get('finalizado_auto', False):
                            st.success("✅ **SISTEMA:** Finalizado automáticamente por el temporizador")
                
                with col_acciones:
                    if st.button("✅ Finalizar", key=f"fin_{pausa['id']}", use_container_width=True):
                        pausa['estado'] = 'COMPLETADO'
                        pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                        guardar_cola_pvd(cola_pvd)
                        temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_pvd, config_pvd, pausa.get('grupo'))
                        st.success(f"✅ Pausa #{pausa['id']} finalizada manualmente")
                        st.rerun()
                    
                    if st.button("❌ Cancelar", key=f"cancel_{pausa['id']}", use_container_width=True):
                        pausa['estado'] = 'CANCELADO'
                        guardar_cola_pvd(cola_pvd)
                        st.warning(f"⚠️ Pausa #{pausa['id']} cancelada")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("🎉 No hay pausas activas en este momento")
    
    # Cola de espera
    if en_espera > 0:
        st.write("### 📝 Cola de Espera (Agrupada por Grupos)")
        
        # Agrupar por grupos
        grupos_espera = {}
        for pausa in cola_pvd:
            if pausa['estado'] == 'ESPERANDO':
                grupo = pausa.get('grupo', 'sin_grupo')
                if grupo not in grupos_espera:
                    grupos_espera[grupo] = []
                grupos_espera[grupo].append(pausa)
        
        for grupo, pausas_grupo in grupos_espera.items():
            pausas_grupo = sorted(pausas_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            with st.expander(f"**Grupo: {grupo}** ({len(pausas_grupo)} en espera)", expanded=True):
                for i, pausa in enumerate(pausas_grupo):
                    duracion_elegida = pausa.get('duracion_elegida', 'corta')
                    duracion_display = f"{config_pvd['duracion_corta']} min" if duracion_elegida == 'corta' else f"{config_pvd['duracion_larga']} min"
                    
                    tiempo_restante = temporizador_pvd_mejorado.obtener_tiempo_restante(pausa['usuario_id'])
                    
                    hora_solicitud = formatear_hora_madrid(pausa['timestamp_solicitud'])
                    
                    with st.container():
                        col_esp1, col_esp2, col_esp3, col_esp4, col_esp5, col_esp6 = st.columns([2, 2, 1, 2, 2, 1])
                        with col_esp1:
                            st.write(f"**#{i+1}** - {pausa.get('usuario_nombre', 'Desconocido')}")
                        with col_esp2:
                            st.write(f"🆔 {pausa['usuario_id'][:10]}...")
                        with col_esp3:
                            st.write(f"⏱️ {duracion_display}")
                        with col_esp4:
                            st.write(f"🕒 {hora_solicitud}")
                        with col_esp5:
                            if tiempo_restante is not None and tiempo_restante > 0:
                                st.write(f"⏳ ~{int(tiempo_restante)} min")
                            elif pausa.get('notificado', False):
                                st.write("🔔 Notificado")
                            else:
                                st.write("⏱️ Esperando")
                        with col_esp6:
                            # Obtener configuración del grupo para verificar espacios
                            config_grupo = grupos_config.get(grupo, {'maximo_simultaneo': 2})
                            max_grupo = config_grupo.get('maximo_simultaneo', 2)
                            
                            en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo])
                            
                            if en_pausa_grupo < max_grupo and i == 0:
                                if st.button("▶️ Iniciar", key=f"iniciar_{pausa['id']}", use_container_width=True):
                                    pausa['estado'] = 'EN_CURSO'
                                    pausa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                                    pausa['confirmado'] = True
                                    guardar_cola_pvd(cola_pvd)
                                    
                                    temporizador_pvd_mejorado.cancelar_temporizador(pausa['usuario_id'])
                                    
                                    st.success(f"✅ Pausa #{pausa['id']} iniciada manualmente")
                                    st.rerun()
                            else:
                                st.button("⏳ Esperando...", disabled=True, use_container_width=True)
                        
                        st.markdown("---")
    else:
        st.info("📭 No hay agentes en la cola de espera")
    
    # Información de temporizadores activos
    if temporizadores_activos > 0:
        st.write("### ⏱️ Temporizadores Activos")
        
        for usuario_id, temporizador in temporizador_pvd_mejorado.temporizadores_activos.items():
            if temporizador.get('activo', True):
                tiempo_restante = temporizador_pvd_mejorado.obtener_tiempo_restante(usuario_id)
                if tiempo_restante and tiempo_restante > 0:
                    with st.container():
                        col_temp1, col_temp2, col_temp3 = st.columns([3, 2, 1])
                        with col_temp1:
                            st.write(f"**Usuario:** {usuario_id}")
                            grupo = "N/A"
                            for pausa in cola_pvd:
                                if pausa['usuario_id'] == usuario_id:
                                    grupo = pausa.get('grupo', 'N/A')
                                    break
                            st.write(f"**Grupo:** {grupo}")
                        with col_temp2:
                            horas = int(tiempo_restante // 60)
                            minutos = int(tiempo_restante % 60)
                            if horas > 0:
                                tiempo_display = f"{horas}h {minutos}m"
                            else:
                                tiempo_display = f"{minutos}m"
                            st.write(f"**Restante:** {tiempo_display}")
                        with col_temp3:
                            if st.button("❌", key=f"cancel_temp_{usuario_id}", help="Cancelar temporizador"):
                                temporizador_pvd_mejorado.cancelar_temporizador(usuario_id)
                                st.rerun()

def gestion_modelos_factura():
    """Gestión de modelos de factura"""
    st.subheader("📄 Gestión de Modelos de Factura")
    
    os.makedirs("modelos_facturas", exist_ok=True)
    
    # Obtener empresas existentes
    empresas_existentes = []
    if os.path.exists("modelos_facturas"):
        empresas_existentes = [d for d in os.listdir("modelos_facturas") 
                             if os.path.isdir(os.path.join("modelos_facturas", d))]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### ➕ Crear Nueva Empresa")
        nueva_empresa = st.text_input("Nombre de la empresa", placeholder="Ej: MiEmpresa S.L.")
        
        if st.button("Crear Empresa") and nueva_empresa:
            carpeta_empresa = f"modelos_facturas/{nueva_empresa.lower().replace(' ', '_')}"
            os.makedirs(carpeta_empresa, exist_ok=True)
            
            # Backup
            if os.path.exists("modelos_facturas"):
                backup_folder = "data_backup/modelos_facturas"
                if os.path.exists(backup_folder):
                    shutil.rmtree(backup_folder)
                shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
            st.success(f"✅ Empresa '{nueva_empresa}' creada correctamente")
            st.rerun()
    
    with col2:
        st.write("### 📁 Empresas Existentes")
        if empresas_existentes:
            for empresa in empresas_existentes:
                st.write(f"**{empresa}**")
        else:
            st.info("No hay empresas creadas aún")
    
    # Subir modelos
    if empresas_existentes:
        st.write("### 📤 Subir Modelo de Factura")
        empresa_seleccionada = st.selectbox("Seleccionar Empresa", empresas_existentes)
        
        archivo = st.file_uploader("Subir modelo de factura", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if archivo is not None:
            carpeta_empresa = f"modelos_facturas/{empresa_seleccionada}"
            ruta_archivo = os.path.join(carpeta_empresa, archivo.name)
            with open(ruta_archivo, "wb") as f:
                f.write(archivo.getbuffer())
            
            # Backup
            backup_folder = "data_backup/modelos_facturas"
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
            shutil.copytree("modelos_facturas", backup_folder, dirs_exist_ok=True)
            
            st.success(f"✅ Modelo para {empresa_seleccionada} guardado correctamente")
            if archivo.type.startswith('image'):
                st.image(archivo, caption=f"Modelo de factura - {empresa_seleccionada}", use_container_width=True)

def gestion_excedentes():
    """Configuración de excedentes de placas solares"""
    st.subheader("☀️ Configuración de Excedentes Placas Solares")
    
    try:
        config_excedentes = pd.read_csv("data/config_excedentes.csv", encoding='utf-8')
        precio_actual = config_excedentes.iloc[0]['precio_excedente_kwh']
    except (FileNotFoundError, pd.errors.EmptyDataError):
        precio_actual = 0.06
        config_excedentes = pd.DataFrame([{'precio_excedente_kwh': precio_actual}])
        config_excedentes.to_csv("data/config_excedentes.csv", index=False, encoding='utf-8')
    
    st.info("Configura el precio que se paga por kWh de excedente de placas solares")
    
    with st.form("form_excedentes"):
        nuevo_precio = st.number_input(
            "Precio por kWh de excedente (€)",
            min_value=0.0,
            max_value=1.0,
            value=precio_actual,
            format="%.3f",
            help="Precio que se paga al cliente por cada kWh de excedente de placas solares"
        )
        
        if st.form_submit_button("💾 Guardar Precio", type="primary"):
            config_excedentes = pd.DataFrame([{'precio_excedente_kwh': nuevo_precio}])
            config_excedentes.to_csv("data/config_excedentes.csv", index=False, encoding='utf-8')
            os.makedirs("data_backup", exist_ok=True)
            shutil.copy("data/config_excedentes.csv", "data_backup/config_excedentes.csv")
            st.success(f"✅ Precio de excedente actualizado a {nuevo_precio}€/kWh")
            st.rerun()
    
    st.info(f"**Precio actual:** {precio_actual}€ por kWh de excedente")

def gestion_config_sistema():
    """Configuración del sistema"""
    st.subheader("⚙️ Configuración del Sistema")
    
    config_sistema = cargar_config_sistema()
    
    st.write("### 🔐 Configuración de Acceso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        login_automatico = st.checkbox(
            "Activar login automático",
            value=config_sistema.get("login_automatico_activado", True),
            help="Los usuarios pueden entrar automáticamente sin credenciales"
        )
    
    with col2:
        horas_duracion = st.number_input(
            "Duración de sesión (horas)",
            min_value=1,
            max_value=24,
            value=config_sistema.get("sesion_horas_duracion", 8),
            help="Tiempo que dura una sesión antes de expirar"
        )
    
    if st.button("💾 Guardar Configuración Sistema", type="primary"):
        config_sistema.update({
            "login_automatico_activado": login_automatico,
            "sesion_horas_duracion": horas_duracion
        })
        guardar_config_sistema(config_sistema)
        st.success("✅ Configuración del sistema guardada")
        st.rerun()

def sistema_pruebas_pvd():
    """Sistema de pruebas para el PVD - Solo para administradores"""
    st.subheader("🧪 Sistema de Pruebas PVD")
    st.warning("⚠️ **SOLO PARA PRUEBAS** - Esto afecta a la cola real")
    
    config_pvd = cargar_config_pvd()
    cola_pvd = cargar_cola_pvd()
    
    tab1, tab2, tab3 = st.tabs(["🚀 Simulación Rápida", "👥 Usuarios de Prueba", "⏱️ Prueba Notificaciones"])
    
    with tab1:
        st.write("### 🚀 Simulación Rápida de Cola")
        
        col_sim1, col_sim2, col_sim3 = st.columns(3)
        
        with col_sim1:
            if st.button("🧹 Limpiar TODA la cola", type="secondary", use_container_width=True):
                backup_file = f"data_backup/cola_pvd_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(cola_pvd, f, indent=4)
                
                cola_pvd = []
                guardar_cola_pvd(cola_pvd)
                st.success("✅ Cola limpiada. Backup guardado")
                st.rerun()
        
        with col_sim2:
            if st.button("⏭️ Avanzar tiempo 5 min", type="secondary", use_container_width=True):
                for pausa in cola_pvd:
                    if 'timestamp_solicitud' in pausa:
                        tiempo_original = datetime.fromisoformat(pausa['timestamp_solicitud'])
                        tiempo_nuevo = tiempo_original - timedelta(minutes=5)
                        pausa['timestamp_solicitud'] = tiempo_nuevo.isoformat()
                    
                    if 'timestamp_inicio' in pausa and pausa['timestamp_inicio']:
                        tiempo_original = datetime.fromisoformat(pausa['timestamp_inicio'])
                        tiempo_nuevo = tiempo_original - timedelta(minutes=5)
                        pausa['timestamp_inicio'] = tiempo_nuevo.isoformat()
                
                guardar_cola_pvd(cola_pvd)
                st.success("⏰ Tiempo avanzado 5 minutos")
                st.rerun()
        
        with col_sim3:
            if st.button("✅ Finalizar todas activas", type="secondary", use_container_width=True):
                for pausa in cola_pvd:
                    if pausa['estado'] == 'EN_CURSO':
                        pausa['estado'] = 'COMPLETADO'
                        pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                
                guardar_cola_pvd(cola_pvd)
                st.success("✅ Todas las pausas activas finalizadas")
                st.rerun()
    
    with tab2:
        st.write("### 👥 Crear Usuarios de Prueba")
        
        usuarios_prueba = [
            {"nombre": "Agente Prueba 1", "id": "test_agente1", "grupo": "basico"},
            {"nombre": "Agente Prueba 2", "id": "test_agente2", "grupo": "premium"},
            {"nombre": "Agente Prueba 3", "id": "test_agente3", "grupo": "empresa"},
            {"nombre": "Agente Prueba 4", "id": "test_agente4", "grupo": "basico"},
            {"nombre": "Agente Prueba 5", "id": "test_agente5", "grupo": "premium"}
        ]
        
        col_users1, col_users2 = st.columns(2)
        
        with col_users1:
            st.write("**Añadir a cola de espera:**")
            for usuario in usuarios_prueba[:3]:
                if st.button(f"➕ {usuario['nombre']} ({usuario['grupo']})", key=f"add_wait_{usuario['id']}", use_container_width=True):
                    nueva_pausa = {
                        'id': str(uuid.uuid4())[:8],
                        'usuario_id': usuario['id'],
                        'usuario_nombre': usuario['nombre'],
                        'duracion_elegida': 'corta',
                        'estado': 'ESPERANDO',
                        'timestamp_solicitud': obtener_hora_madrid().isoformat(),
                        'timestamp_inicio': None,
                        'timestamp_fin': None,
                        'grupo': usuario['grupo'],
                        'notificado': False,
                        'confirmado': False,
                        'es_prueba': True
                    }
                    
                    cola_pvd.append(nueva_pausa)
                    guardar_cola_pvd(cola_pvd)
                    st.success(f"✅ {usuario['nombre']} añadido a la cola del grupo {usuario['grupo']}")
                    st.rerun()
        
        with col_users2:
            st.write("**Añadir como pausa activa:**")
            for usuario in usuarios_prueba[3:]:
                if st.button(f"▶️ {usuario['nombre']} ({usuario['grupo']})", key=f"add_active_{usuario['id']}", use_container_width=True):
                    nueva_pausa = {
                        'id': str(uuid.uuid4())[:8],
                        'usuario_id': usuario['id'],
                        'usuario_nombre': usuario['nombre'],
                        'duracion_elegida': 'larga',
                        'estado': 'EN_CURSO',
                        'timestamp_solicitud': (obtener_hora_madrid() - timedelta(minutes=2)).isoformat(),
                        'timestamp_inicio': obtener_hora_madrid().isoformat(),
                        'timestamp_fin': None,
                        'grupo': usuario['grupo'],
                        'notificado': True,
                        'confirmado': True,
                        'es_prueba': True
                    }
                    
                    cola_pvd.append(nueva_pausa)
                    guardar_cola_pvd(cola_pvd)
                    st.success(f"✅ {usuario['nombre']} añadido como pausa activa en grupo {usuario['grupo']}")
                    st.rerun()
        
        st.write("**Estado actual de pruebas:**")
        pruebas_activas = [p for p in cola_pvd if p.get('es_prueba', False)]
        if pruebas_activas:
            for pausa in pruebas_activas:
                estado_display = ESTADOS_PVD.get(pausa['estado'], pausa['estado'])
                st.write(f"- **{pausa['usuario_nombre']}** ({pausa.get('grupo', 'N/A')}): {estado_display}")
        else:
            st.info("No hay pruebas activas")
    
    with tab3:
        st.write("### ⏱️ Prueba de Notificaciones")
        
        st.info("""
        **Prueba la notificación de confirmación directamente:**
        
        1. Haz clic en el botón "🔔 Probar Notificación"
        2. Verás una ventana emergente EN LA PÁGINA (no alerta del navegador)
        3. Haz clic en OK o Cancelar para probar
        """)
        
        if st.button("🔔 Probar Notificación de Confirmación", type="primary", use_container_width=True):
            st.markdown("""
            <script>
            const overlay = document.createElement('div');
            overlay.id = 'overlay-prueba-notificacion';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.85);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            
            overlay.innerHTML = `
                <div style="
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 30px;
                    border-radius: 15px;
                    text-align: center;
                    max-width: 500px;
                    width: 90%;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                    animation: pulse 1s infinite;
                    border: 3px solid white;
                ">
                    <h2 style="margin: 0 0 20px 0; font-size: 28px;">🎉 [PRUEBA] ¡ES TU TURNO!</h2>
                    <p style="font-size: 20px; margin: 15px 0; font-weight: bold;">Esta es una prueba de la notificación</p>
                    <p style="opacity: 0.9; margin-bottom: 25px; font-size: 16px;">Haz clic en OK para simular confirmación o Cancelar para probar rechazo</p>
                    
                    <div style="display: flex; gap: 20px; justify-content: center;">
                        <button id="btn-confirmar-prueba" style="
                            background: white;
                            color: #667eea;
                            border: none;
                            padding: 15px 40px;
                            border-radius: 10px;
                            font-size: 18px;
                            font-weight: bold;
                            cursor: pointer;
                            transition: transform 0.2s;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                        ">
                            ✅ OK - Simular Confirmación
                        </button>
                        
                        <button id="btn-cancelar-prueba" style="
                            background: #f44336;
                            color: white;
                            border: none;
                            padding: 15px 40px;
                            border-radius: 10px;
                            font-size: 18px;
                            font-weight: bold;
                            cursor: pointer;
                            transition: transform 0.2s;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                        ">
                            ❌ Cancelar - Simular Rechazo
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(overlay);
            
            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
            `;
            document.head.appendChild(style);
            
            document.getElementById('btn-confirmar-prueba').addEventListener('click', function() {
                document.body.removeChild(overlay);
                alert('✅ [PRUEBA] Confirmación exitosa. La pausa comenzaría ahora.');
            });
            
            document.getElementById('btn-cancelar-prueba').addEventListener('click', function() {
                document.body.removeChild(overlay);
                alert('⚠️ [PRUEBA] Confirmación cancelada. Seguirías en la cola.');
            });
            </script>
            """, unsafe_allow_html=True)
            
            st.success("✅ Notificación de prueba activada. Mira en la página principal (no en una alerta).")

def gestion_secciones_visibles():
    """Configuración de secciones visibles para usuarios"""
    st.subheader("👁️ Configuración de Secciones Visibles")
    
    config_sistema = cargar_config_sistema()
    from config import SECCIONES_USUARIO
    
    if 'secciones_activas' not in config_sistema:
        from config import SECCIONES_USUARIO
        config_sistema['secciones_activas'] = {seccion: True for seccion in SECCIONES_USUARIO.keys()}
    
    st.info("Activa o desactiva las secciones que los usuarios pueden ver en su panel")
    
    for seccion_id, seccion_config in SECCIONES_USUARIO.items():
        activo_actual = config_sistema['secciones_activas'].get(seccion_id, True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{seccion_config['nombre']}**")
            st.caption(seccion_config['descripcion'])
        with col2:
            estado = st.checkbox(
                "Activo",
                value=activo_actual,
                key=f"seccion_{seccion_id}",
                help=f"Mostrar {seccion_config['nombre']} a los usuarios"
            )
            config_sistema['secciones_activas'][seccion_id] = estado
    
    if st.button("💾 Guardar Configuración de Secciones", type="primary"):
        guardar_config_sistema(config_sistema)
        st.success("✅ Configuración de secciones guardada")
        st.rerun()

def mostrar_panel_administrador():
    """Panel de administración"""
    st.header("🔧 Panel de Administración")
    
    # Añadir pestaña de configuración de secciones
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "⚡ Electricidad", "🔥 Gas", "👥 Usuarios", "👁️ PVD", 
        "📄 Facturas", "☀️ Excedentes", "⚙️ Sistema", "👁️ Secciones", "🧪 Pruebas PVD"
    ])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_usuarios()
    with tab4:
        gestion_pvd_admin()
    with tab5:
        gestion_modelos_factura()
    with tab6:
        gestion_excedentes()
    with tab7:
        gestion_config_sistema()
    with tab8:  # NUEVA PESTAÑA
        gestion_secciones_visibles()
    with tab9:
        sistema_pruebas_pvd()