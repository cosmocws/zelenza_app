import streamlit as st
import pandas as pd
import json
import os
import uuid
import shutil
from datetime import datetime, timedelta
import pytz
from pathlib import Path

# ==============================================
# IMPORTS DE MÓDULOS PROPIOS
# ==============================================

# Funciones de otros módulos
from super_users_functions import gestion_super_users_admin
from llamadas_analyzer import interfaz_analisis_llamadas
from festivos_manager import (
    guardar_festivos, cargar_festivos, agregar_festivo, eliminar_festivo
)

# Configuraciones
from config import (
    COMUNIDADES_AUTONOMAS, PLANES_GAS_ESTRUCTURA, 
    PMG_COSTE, PMG_IVA, ESTADOS_PVD, GRUPOS_PVD_CONFIG,
    SECCIONES_USUARIO
)

# Base de datos
from database import (
    cargar_configuracion_usuarios, guardar_configuracion_usuarios,
    cargar_config_sistema, guardar_config_sistema,
    cargar_config_pvd, guardar_config_pvd,
    cargar_cola_pvd_grupo, guardar_cola_pvd_grupo,
    obtener_todas_colas_pvd, consolidar_colas_pvd,
    limpiar_todas_colas_antiguas
)

# Sistema PVD
from pvd_system import temporizador_pvd_mejorado

# Utilidades
from utils import obtener_hora_madrid, formatear_hora_madrid

# ==============================================
# FUNCIONES DE GESTIÓN DE PLANES
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
        
        # Campo para umbral del Especial Plus
        st.write("### ⚙️ Configuración Especial Plus (si aplica)")
        
        es_especial_plus = "ESPECIAL PLUS" in nombre_plan.upper() if nombre_plan else False
        
        if es_especial_plus or (st.session_state.editing_plan and 
                               "ESPECIAL PLUS" in str(st.session_state.editing_plan.get('plan', '')).upper()):
            
            if st.session_state.editing_plan:
                umbral_actual = st.session_state.editing_plan.get('umbral_especial_plus', 15.00)
            else:
                umbral_actual = 15.00
            
            umbral_especial_plus = st.number_input(
                "Umbral Especial Plus (€)",
                min_value=0.0,
                max_value=100.0,
                value=umbral_actual,
                step=0.5,
                format="%.2f",
                help="Ahorro mínimo mensual necesario para mostrar el plan Especial Plus"
            )
            
            st.info(f"ℹ️ El plan Especial Plus solo se mostrará si el mejor plan normal ahorra menos de {umbral_especial_plus}€/mes")
        else:
            umbral_especial_plus = 0.00
            st.info("ℹ️ Este no es un plan Especial Plus (no aplica umbral)")
        
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
                    'comunidades_autonomas': ';'.join(comunidades_seleccionadas),
                    'umbral_especial_plus': umbral_especial_plus
                }
                
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

# ==============================================
# FUNCIONES DE GESTIÓN DE USUARIOS Y GRUPOS
# ==============================================

def gestion_usuarios():
    """Gestión de usuarios y grupos"""
    st.subheader("👥 Gestión de Usuarios y Grupos")
    
    usuarios_config = cargar_configuracion_usuarios()
    config_sistema = cargar_config_sistema()
    grupos = config_sistema.get("grupos_usuarios", {})
    grupos_pvd = config_sistema.get("grupos_pvd", {})
    
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Usuarios", "👥 Grupos Usuarios", "⚙️ Grupos PVD", "➕ Crear Usuario"])
    
    with tab1:
        _gestion_usuarios_tab(usuarios_config, grupos_pvd)
    
    with tab2:
        _gestion_grupos_usuarios_tab(usuarios_config, grupos, config_sistema, grupos_pvd)
    
    with tab3:
        _gestion_grupos_pvd_tab(usuarios_config, grupos_pvd, grupos, config_sistema)
    
    with tab4:
        _crear_usuario_tab(usuarios_config, grupos_pvd)

def _gestion_usuarios_tab(usuarios_config, grupos_pvd):
    """Pestaña de gestión de usuarios individuales"""
    st.write("### 📊 Lista de Usuarios")
    
    for username, config in usuarios_config.items():
        if username == "admin":
            continue
            
        with st.expander(f"👤 {username} - {config.get('nombre', 'Sin nombre')}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_nombre = st.text_input("Nombre", value=config.get('nombre', ''), key=f"nombre_{username}")
                
                grupo_actual = config.get('grupo', '')
                grupos_pvd_lista = list(grupos_pvd.keys())
                grupo_seleccionado = st.selectbox(
                    "Grupo PVD",
                    [""] + grupos_pvd_lista,
                    index=0 if not grupo_actual else (grupos_pvd_lista.index(grupo_actual) + 1 if grupo_actual in grupos_pvd_lista else 0),
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
                if grupo_seleccionado and grupo_seleccionado in grupos_pvd:
                    config_grupo = grupos_pvd[grupo_seleccionado]
                    st.write("**Configuración PVD del grupo:**")
                    st.write(f"👥 Agentes: {config_grupo.get('agentes_por_grupo', 10)}")
                    st.write(f"⏸️ Máx. simultáneo: {config_grupo.get('maximo_simultaneo', 2)}")
                    st.write(f"⏱️ Pausa corta: {config_grupo.get('duracion_corta', 5)} min")
                    st.write(f"⏱️ Pausa larga: {config_grupo.get('duracion_larga', 10)} min")
                
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

def _gestion_grupos_usuarios_tab(usuarios_config, grupos, config_sistema, grupos_pvd):
    """Pestaña de gestión de grupos de usuarios"""
    st.write("### 👥 Gestión de Grupos de Usuarios")
    
    if 'grupo_usuarios_a_borrar' not in st.session_state:
        st.session_state.grupo_usuarios_a_borrar = None
    
    # Mostrar confirmación de borrado si hay uno pendiente
    if st.session_state.grupo_usuarios_a_borrar:
        _mostrar_confirmacion_borrado_grupo_usuarios(usuarios_config, grupos, config_sistema, grupos_pvd)
    
    # Lista de grupos existentes
    for grupo_nombre, permisos in grupos.items():
        with st.expander(f"**Grupo: {grupo_nombre}**", expanded=True):
            _mostrar_edicion_grupo_usuarios(grupo_nombre, permisos, grupos, config_sistema, usuarios_config)
    
    # Crear nuevo grupo de usuarios
    _crear_nuevo_grupo_usuarios(grupos, config_sistema, grupos_pvd)

def _mostrar_confirmacion_borrado_grupo_usuarios(usuarios_config, grupos, config_sistema, grupos_pvd):
    """Muestra confirmación para borrar grupo de usuarios"""
    grupo_a_borrar = st.session_state.grupo_usuarios_a_borrar
    grupos_basicos = ["basico", "premium", "empresa"]
    
    if grupo_a_borrar in grupos_basicos:
        st.error(f"❌ No puedes borrar el grupo '{grupo_a_borrar}' (grupo básico del sistema)")
        st.session_state.grupo_usuarios_a_borrar = None
        st.rerun()
    
    st.warning(f"⚠️ **CONFIRMAR BORRADO DEL GRUPO DE USUARIOS: {grupo_a_borrar}**")
    
    usuarios_en_grupo = [username for username, config in usuarios_config.items() 
                        if config.get('grupo') == grupo_a_borrar]
    
    st.write(f"**📊 Este grupo tiene {len(usuarios_en_grupo)} usuario(s):**")
    if usuarios_en_grupo:
        for i, usuario in enumerate(usuarios_en_grupo[:5]):
            st.write(f"• {usuario}")
        if len(usuarios_en_grupo) > 5:
            st.write(f"• ... y {len(usuarios_en_grupo) - 5} más")
    
    st.write("**⚠️ ADVERTENCIA:** Al borrar este grupo:")
    st.write("1. Todos sus usuarios perderán su grupo asignado (quedarán sin grupo)")
    st.write("2. Se perderá la configuración de permisos del grupo")
    st.write("3. Esta acción NO se puede deshacer")
    
    col_conf1, col_conf2, col_conf3 = st.columns(3)
    
    with col_conf1:
        unique_key = f"confirm_delete_usuarios_{grupo_a_borrar}"
        if st.button("✅ **SÍ, BORRAR GRUPO**", 
                    type="primary", 
                    use_container_width=True,
                    key=unique_key):
            # Borrar grupo de usuarios
            if grupo_a_borrar in grupos:
                del grupos[grupo_a_borrar]
                config_sistema['grupos_usuarios'] = grupos
            
            # Borrar también grupo PVD si existe
            if grupo_a_borrar in grupos_pvd:
                del grupos_pvd[grupo_a_borrar]
                config_sistema['grupos_pvd'] = grupos_pvd
                st.success(f"✅ Grupo PVD '{grupo_a_borrar}' también borrado")
            
            guardar_config_sistema(config_sistema)
            
            # Quitar grupo de los usuarios
            usuarios_modificados = 0
            for username in usuarios_en_grupo:
                usuarios_config[username]['grupo'] = ''  # Queda sin grupo
                usuarios_modificados += 1
            
            if usuarios_modificados > 0:
                guardar_configuracion_usuarios(usuarios_config)
            
            st.success(f"✅ Grupo de usuarios '{grupo_a_borrar}' borrado correctamente")
            st.success(f"✅ {usuarios_modificados} usuario(s) quedaron sin grupo asignado")
            
            st.session_state.grupo_usuarios_a_borrar = None
            st.rerun()
    
    with col_conf2:
        cancel_key = f"cancel_delete_usuarios_{grupo_a_borrar}"
        if st.button("❌ **NO, CANCELAR**", 
                    type="secondary", 
                    use_container_width=True,
                    key=cancel_key):
            st.session_state.grupo_usuarios_a_borrar = None
            st.info("❌ Borrado cancelado")
            st.rerun()
    
    with col_conf3:
        if len(usuarios_en_grupo) > 0:
            st.metric("Usuarios afectados", len(usuarios_en_grupo))
        else:
            st.info("No hay usuarios en este grupo")
    
    st.write("---")
    st.info("**Nota:** Los usuarios sin grupo tendrán acceso a TODOS los planes disponibles.")

def _mostrar_edicion_grupo_usuarios(grupo_nombre, permisos, grupos, config_sistema, usuarios_config):
    """Muestra interfaz de edición para un grupo de usuarios"""
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
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Actualizar Grupo", key=f"update_grupo_{grupo_nombre}"):
            grupos[grupo_nombre] = {
                "planes_luz": planes_luz_seleccionados,
                "planes_gas": planes_gas_seleccionados
            }
            config_sistema['grupos_usuarios'] = grupos
            guardar_config_sistema(config_sistema)
            st.success(f"✅ Grupo {grupo_nombre} actualizado")
            st.rerun()
    
    with col_btn2:
        usuarios_en_grupo = [username for username, config in usuarios_config.items() 
                           if config.get('grupo') == grupo_nombre]
        
        grupos_basicos = ["basico", "premium", "empresa"]
        es_basico = grupo_nombre in grupos_basicos
        
        if not es_basico:
            delete_key = f"delete_grupo_usuarios_{grupo_nombre}"
            if st.button("🗑️ Borrar Grupo", 
                       key=delete_key, 
                       type="secondary"):
                st.session_state.grupo_usuarios_a_borrar = grupo_nombre
                st.rerun()
        else:
            st.caption("⚠️ Grupo básico del sistema")

def _crear_nuevo_grupo_usuarios(grupos, config_sistema, grupos_pvd):
    """Interfaz para crear nuevo grupo de usuarios"""
    st.write("### ➕ Crear Nuevo Grupo de Usuarios")
    nuevo_grupo_nombre = st.text_input("Nombre del nuevo grupo", key="nuevo_grupo_usuarios")
    
    # Configuración PVD para el nuevo grupo
    st.write("#### ⚙️ Configuración PVD para el Nuevo Grupo")
    
    col_conf_pvd1, col_conf_pvd2 = st.columns(2)
    with col_conf_pvd1:
        agentes_por_grupo = st.number_input(
            "Agentes en grupo",
            min_value=1,
            max_value=100,
            value=10,
            key="agentes_nuevo_grupo"
        )
        maximo_simultaneo = st.number_input(
            "Máximo simultáneo",
            min_value=1,
            max_value=20,
            value=2,
            key="max_simultaneo_nuevo_grupo"
        )
    with col_conf_pvd2:
        duracion_corta = st.number_input(
            "Duración corta (min)",
            min_value=1,
            max_value=30,
            value=5,
            key="corta_nuevo_grupo"
        )
        duracion_larga = st.number_input(
            "Duración larga (min)",
            min_value=1,
            max_value=60,
            value=10,
            key="larga_nuevo_grupo"
        )
    
    col_nuevo1, col_nuevo2 = st.columns(2)
    with col_nuevo1:
        if st.button("Crear Grupo Vacío", key="crear_grupo_vacio"):
            if not nuevo_grupo_nombre:
                st.error("❌ El nombre del grupo es obligatorio")
            elif nuevo_grupo_nombre in grupos:
                st.error("❌ El grupo ya existe")
            else:
                # Crear grupo de usuarios
                grupos[nuevo_grupo_nombre] = {
                    "planes_luz": [],
                    "planes_gas": []
                }
                config_sistema['grupos_usuarios'] = grupos
                
                # Crear grupo PVD automáticamente
                grupos_pvd[nuevo_grupo_nombre] = {
                    'agentes_por_grupo': agentes_por_grupo,
                    'maximo_simultaneo': maximo_simultaneo,
                    'duracion_corta': duracion_corta,
                    'duracion_larga': duracion_larga
                }
                config_sistema['grupos_pvd'] = grupos_pvd
                
                guardar_config_sistema(config_sistema)
                st.success(f"✅ Grupo {nuevo_grupo_nombre} creado (vacío)")
                st.success(f"✅ Grupo PVD '{nuevo_grupo_nombre}' creado automáticamente")
                st.rerun()
    
    with col_nuevo2:
        if st.button("Crear Grupo con Todos los Permisos", key="crear_grupo_todos"):
            if not nuevo_grupo_nombre:
                st.error("❌ El nombre del grupo es obligatorio")
            elif nuevo_grupo_nombre in grupos:
                st.error("❌ El grupo ya existe")
            else:
                # Crear grupo de usuarios con todos los permisos
                grupos[nuevo_grupo_nombre] = {
                    "planes_luz": "TODOS",
                    "planes_gas": ["RL1", "RL2", "RL3"]
                }
                config_sistema['grupos_usuarios'] = grupos
                
                # Crear grupo PVD automáticamente
                grupos_pvd[nuevo_grupo_nombre] = {
                    'agentes_por_grupo': agentes_por_grupo,
                    'maximo_simultaneo': maximo_simultaneo,
                    'duracion_corta': duracion_corta,
                    'duracion_larga': duracion_larga
                }
                config_sistema['grupos_pvd'] = grupos_pvd
                
                guardar_config_sistema(config_sistema)
                st.success(f"✅ Grupo {nuevo_grupo_nombre} creado con todos los permisos")
                st.success(f"✅ Grupo PVD '{nuevo_grupo_nombre}' creado automáticamente")
                st.rerun()
    
    st.write("---")
    st.info("""
    **📋 Notas sobre grupos de usuarios:**
    - **Grupos básicos:** basico, premium, empresa - no se pueden borrar
    - **Permisos:** Controlan qué planes pueden ver los usuarios del grupo
    - **Sin grupo:** Los usuarios sin grupo ven TODOS los planes disponibles
    - **Al borrar:** Los usuarios del grupo borrado quedan sin grupo asignado
    - **Recomendación:** Reasigna usuarios antes de borrar grupos
    """)

def _gestion_grupos_pvd_tab(usuarios_config, grupos_pvd, grupos, config_sistema):
    """Pestaña de gestión de grupos PVD"""
    st.write("### ⚙️ Gestión de Grupos PVD")
    st.info("Configura los grupos para el sistema de Pausas Visuales Dinámicas")
    
    if 'editing_grupo_pvd' not in st.session_state:
        st.session_state.editing_grupo_pvd = None
    
    if 'grupo_pvd_a_borrar' not in st.session_state:
        st.session_state.grupo_pvd_a_borrar = None
    
    # Mostrar grupos PVD existentes
    st.write("#### 📊 Grupos PVD Existentes")
    
    if not grupos_pvd:
        st.info("📝 No hay grupos PVD configurados. ¡Crea el primero!")
    else:
        col_grupos1, col_grupos2, col_grupos3 = st.columns(3)
        
        with col_grupos1:
            st.write("**✅ Grupos Activos**")
            for grupo_id in grupos_pvd.keys():
                if grupo_id == 'basico':
                    st.button(f"⚙️ {grupo_id} (sistema)", 
                            key=f"edit_{grupo_id}",
                            use_container_width=True,
                            disabled=True,
                            help="Grupo por defecto del sistema")
                else:
                    if st.button(f"⚙️ {grupo_id}", 
                            key=f"edit_{grupo_id}",
                            use_container_width=True):
                        st.session_state.editing_grupo_pvd = grupo_id
                        st.rerun()
        
        with col_grupos2:
            st.write("**📈 Estadísticas**")
            usuarios_por_grupo = {}
            for username, config in usuarios_config.items():
                grupo = config.get('grupo', '')
                if grupo:
                    if grupo not in usuarios_por_grupo:
                        usuarios_por_grupo[grupo] = 0
                    usuarios_por_grupo[grupo] += 1
            
            for grupo_id, config in grupos_pvd.items():
                usuarios = usuarios_por_grupo.get(grupo_id, 0)
                st.write(f"• **{grupo_id}:** {usuarios} usuarios")
        
        with col_grupos3:
            st.write("**⚡ Acciones Rápidas**")
            for grupo_id in grupos_pvd.keys():
                if grupo_id != 'basico':
                    if st.button(f"🗑️ {grupo_id}", 
                            key=f"del_btn_pvd_{grupo_id}",
                            use_container_width=True,
                            type="secondary"):
                        st.session_state.grupo_pvd_a_borrar = grupo_id
                        st.rerun()
    
    # Formulario para añadir/editar grupo PVD
    st.write("#### ➕ Añadir/✏️ Editar Grupo PVD")
    
    if st.session_state.editing_grupo_pvd is not None:
        grupo_actual = st.session_state.editing_grupo_pvd
        config_actual = grupos_pvd[grupo_actual]
        st.warning(f"✏️ Editando: **{grupo_actual}**")
        if st.button("❌ Cancelar Edición"):
            st.session_state.editing_grupo_pvd = None
            st.rerun()
    else:
        config_actual = {
            'agentes_por_grupo': 10,
            'maximo_simultaneo': 2,
            'duracion_corta': 5,
            'duracion_larga': 10
        }
    
    with st.form("form_grupo_pvd"):
        if st.session_state.editing_grupo_pvd is not None:
            nombre_grupo = st.text_input("Nombre del Grupo*", 
                                    value=st.session_state.editing_grupo_pvd,
                                    disabled=True)
            st.info("⚠️ El nombre no se puede modificar al editar")
        else:
            nombre_grupo = st.text_input("Nombre del Grupo*", placeholder="Ej: premium, capta, etc.")
        
        col_conf1, col_conf2 = st.columns(2)
        
        with col_conf1:
            agentes_por_grupo = st.number_input(
                "Agentes en grupo*",
                min_value=1,
                max_value=100,
                value=config_actual.get('agentes_por_grupo', 10),
                help="Número total de agentes en este grupo"
            )
            
            maximo_simultaneo = st.number_input(
                "Máximo simultáneo*",
                min_value=1,
                max_value=20,
                value=config_actual.get('maximo_simultaneo', 2),
                help="Máximo número de pausas simultáneas en este grupo"
            )
        
        with col_conf2:
            duracion_corta = st.number_input(
                "Duración corta (min)*",
                min_value=1,
                max_value=30,
                value=config_actual.get('duracion_corta', 5),
                help="Duración de la pausa corta en minutos"
            )
            
            duracion_larga = st.number_input(
                "Duración larga (min)*",
                min_value=1,
                max_value=60,
                value=config_actual.get('duracion_larga', 10),
                help="Duración de la pausa larga en minutos"
            )
        
        submitted = st.form_submit_button(
            "💾 Guardar Cambios" if st.session_state.editing_grupo_pvd else "➕ Crear Nuevo Grupo", 
            type="primary"
        )
        
        if submitted:
            if not nombre_grupo:
                st.error("❌ El nombre del grupo es obligatorio")
            else:
                nuevo_grupo_data = {
                    'agentes_por_grupo': agentes_por_grupo,
                    'maximo_simultaneo': maximo_simultaneo,
                    'duracion_corta': duracion_corta,
                    'duracion_larga': duracion_larga
                }
                
                # Añadir o actualizar
                grupos_pvd[nombre_grupo] = nuevo_grupo_data
                config_sistema['grupos_pvd'] = grupos_pvd
                guardar_config_sistema(config_sistema)
                
                if st.session_state.editing_grupo_pvd:
                    st.success(f"✅ Grupo '{nombre_grupo}' actualizado correctamente")
                else:
                    st.success(f"✅ Grupo '{nombre_grupo}' creado correctamente")
                
                st.session_state.editing_grupo_pvd = None
                st.rerun()
    
    # Sistema de borrado con confirmación PARA GRUPOS PVD
    if 'grupo_pvd_a_borrar' in st.session_state and st.session_state.grupo_pvd_a_borrar:
        _mostrar_confirmacion_borrado_grupo_pvd(usuarios_config, grupos_pvd, grupos, config_sistema)
    
    st.info("""
    **📋 Notas sobre grupos PVD:**
    - Cada grupo tiene su propia configuración de pausas
    - Los usuarios se asignan a grupos en la pestaña "Usuarios"
    - El grupo 'basico' es el grupo por defecto y no se puede borrar
    - Al borrar un grupo, sus usuarios se reasignan automáticamente al grupo 'basico'
    """)

def _mostrar_confirmacion_borrado_grupo_pvd(usuarios_config, grupos_pvd, grupos, config_sistema):
    """Muestra confirmación para borrar grupo PVD"""
    grupo_a_borrar = st.session_state.grupo_pvd_a_borrar
    
    if grupo_a_borrar == 'basico':
        st.error("❌ No puedes borrar el grupo 'basico' (grupo por defecto del sistema)")
        st.session_state.grupo_pvd_a_borrar = None
        st.rerun()
    elif len(grupos_pvd) <= 1:
        st.error("❌ No puedes borrar todos los grupos. Debe quedar al menos uno.")
        st.session_state.grupo_pvd_a_borrar = None
        st.rerun()
    
    st.warning(f"⚠️ **CONFIRMAR BORRADO DEL GRUPO PVD: {grupo_a_borrar}**")
    
    usuarios_en_grupo = []
    for username, config in usuarios_config.items():
        if config.get('grupo') == grupo_a_borrar:
            usuarios_en_grupo.append(username)
    
    st.write(f"**📊 Este grupo tiene {len(usuarios_en_grupo)} usuario(s):**")
    if usuarios_en_grupo:
        for i, usuario in enumerate(usuarios_en_grupo[:5]):
            st.write(f"• {usuario}")
        if len(usuarios_en_grupo) > 5:
            st.write(f"• ... y {len(usuarios_en_grupo) - 5} más")
    
    st.write("**⚠️ ADVERTENCIA:** Al borrar este grupo PVD:")
    st.write("1. Todos sus usuarios serán reasignados al grupo 'basico'")
    st.write("2. Se perderá la configuración específica del grupo")
    st.write("3. Esta acción NO se puede deshacer")
    
    col_conf1, col_conf2, col_conf3 = st.columns(3)
    
    with col_conf1:
        unique_key = f"confirm_delete_pvd_{grupo_a_borrar}"
        if st.button("✅ **SÍ, BORRAR GRUPO**", 
                    type="primary", 
                    use_container_width=True,
                    key=unique_key):
            # Borrar grupo PVD
            if grupo_a_borrar in grupos_pvd:
                del grupos_pvd[grupo_a_borrar]
                config_sistema['grupos_pvd'] = grupos_pvd
            
            # También borrar grupo de usuarios si existe
            if grupo_a_borrar in grupos:
                del grupos[grupo_a_borrar]
                config_sistema['grupos_usuarios'] = grupos
                st.success(f"✅ Grupo de usuarios '{grupo_a_borrar}' también borrado")
            
            guardar_config_sistema(config_sistema)
            
            # Reasignar usuarios al grupo 'basico'
            usuarios_modificados = 0
            for username, config in usuarios_config.items():
                if config.get('grupo') == grupo_a_borrar:
                    usuarios_config[username]['grupo'] = 'basico'
                    usuarios_modificados += 1
            
            if usuarios_modificados > 0:
                guardar_configuracion_usuarios(usuarios_config)
            
            st.success(f"✅ Grupo PVD '{grupo_a_borrar}' borrado correctamente")
            st.success(f"✅ {usuarios_modificados} usuario(s) reasignados al grupo 'basico'")
            
            st.session_state.grupo_pvd_a_borrar = None
            st.session_state.editing_grupo_pvd = None
            st.rerun()
    
    with col_conf2:
        cancel_key = f"cancel_delete_pvd_{grupo_a_borrar}"
        if st.button("❌ **NO, CANCELAR**", 
                    type="secondary", 
                    use_container_width=True,
                    key=cancel_key):
            st.session_state.grupo_pvd_a_borrar = None
            st.info("❌ Borrado cancelado")
            st.rerun()
    
    with col_conf3:
        if len(usuarios_en_grupo) > 0:
            st.metric("Usuarios a reasignar", len(usuarios_en_grupo))
        else:
            st.info("No hay usuarios en este grupo")

def _crear_usuario_tab(usuarios_config, grupos_pvd):
    """Pestaña para crear nuevo usuario"""
    st.write("### 👤 Crear Nuevo Usuario")
    
    with st.form("form_nuevo_usuario"):
        col1, col2 = st.columns(2)
        
        with col1:
            nuevo_username = st.text_input("Username*", help="Nombre de usuario para el acceso")
            nuevo_nombre = st.text_input("Nombre completo*", help="Nombre real del usuario")
            
            grupos_pvd_lista = list(grupos_pvd.keys())
            grupo_usuario = st.selectbox("Grupo PVD", [""] + grupos_pvd_lista, help="Asigna un grupo PVD")
        
        with col2:
            password_usuario = st.text_input("Contraseña*", type="password", help="Contraseña para acceso manual")
            confirm_password = st.text_input("Confirmar contraseña*", type="password", help="Repite la contraseña")
            
            tipo_usuario = st.selectbox("Tipo de usuario", ["user", "auto", "manual"], 
                                       help="user: Usuario normal, auto: Autogenerado, manual: Creado manualmente")
            
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

# ==============================================
# FUNCIONES DE GESTIÓN PVD (PAUSAS VISUALES DINÁMICAS)
# ==============================================

def gestion_pvd_admin():
    """Administración del sistema PVD con grupos"""
    st.subheader("👁️ Administración PVD (Pausa Visual Dinámica)")
    
    hora_actual_madrid = obtener_hora_madrid().strftime('%H:%M:%S')
    st.caption(f"🕒 **Hora del servidor (Madrid):** {hora_actual_madrid}")
    
    config_pvd = cargar_config_pvd()
    todas_colas = obtener_todas_colas_pvd()
    cola_consolidada = consolidar_colas_pvd()
    config_sistema = cargar_config_sistema()
    grupos_config = config_sistema.get('grupos_pvd', GRUPOS_PVD_CONFIG)
    
    # Botones de control
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
        if st.button("🧹 Limpiar Todas las Colas", key="clean_all_colas", use_container_width=True):
            if limpiar_todas_colas_antiguas():
                st.success("✅ Todas las colas PVD limpiadas de datos antiguos")
                st.rerun()
            else:
                st.error("❌ Error al limpiar colas")
    
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
    
    # Enlace a gestión de grupos PVD
    st.write("### 👥 Gestión de Grupos PVD")
    st.info("La gestión de grupos PVD se ha movido a la pestaña **👥 Usuarios** → **⚙️ Grupos PVD**")
    
    if st.button("👥 Ir a Gestión de Grupos PVD", key="ir_grupos_pvd"):
        st.session_state.active_admin_tab = "Usuarios"
        st.rerun()
    
    # Estadísticas actuales
    st.markdown("---")
    st.write("### 📊 Estado Actual del Sistema")
    
    # Calcular estadísticas usando todas_colas en lugar de cola_pvd
    en_pausa = 0
    en_espera = 0
    completados_hoy = 0
    cancelados_hoy = 0
    hoy = obtener_hora_madrid().date()
    
    for grupo_id, cola_grupo in todas_colas.items():
        en_pausa += len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
        en_espera += len([p for p in cola_grupo if p['estado'] == 'ESPERANDO'])
        
        for pausa in cola_grupo:
            if pausa['estado'] == 'COMPLETADO' and 'timestamp_fin' in pausa:
                try:
                    fecha_fin = datetime.fromisoformat(pausa['timestamp_fin']).date()
                    if fecha_fin == hoy:
                        completados_hoy += 1
                except:
                    pass
            
            if pausa['estado'] == 'CANCELADO' and 'timestamp_solicitud' in pausa:
                try:
                    fecha_solicitud = datetime.fromisoformat(pausa['timestamp_solicitud']).date()
                    if fecha_solicitud == hoy:
                        cancelados_hoy += 1
                except:
                    pass
    
    temporizadores_activos = len(temporizador_pvd_mejorado.temporizadores_activos)
    notificaciones_pendientes = len(temporizador_pvd_mejorado.notificaciones_pendientes)
    
    col_stat1, col_stat2, col_stat3, col_stat4, col_stat5, col_stat6 = st.columns(6)
    with col_stat1:
        st.metric("👥 Grupos Activos", len(todas_colas))
    with col_stat2:
        st.metric("⏸️ En Pausa", en_pausa)
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
    if hasattr(temporizador_pvd_mejorado, 'ultima_actualizacion'):
        st.caption(f"Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
    
    # Pausas en curso
    st.markdown("---")
    st.write("### 📋 Pausas en Curso")
    
    hay_pausas_activas = False
    for grupo_id, cola_grupo in todas_colas.items():
        pausas_en_curso = [p for p in cola_grupo if p['estado'] == 'EN_CURSO']
        if pausas_en_curso:
            hay_pausas_activas = True
            st.write(f"#### 👥 Grupo: {grupo_id}")
            for pausa in pausas_en_curso:
                _mostrar_pausa_en_curso_grupo(pausa, grupo_id, cola_grupo, config_pvd, grupos_config)
    
    if not hay_pausas_activas:
        st.info("🎉 No hay pausas activas en este momento")
    
    # Cola de espera
    if en_espera > 0:
        _mostrar_cola_espera_grupos(todas_colas, config_pvd, temporizador_pvd_mejorado, grupos_config)
    else:
        st.info("📭 No hay agentes en la cola de espera")
    
    # Temporizadores activos
    if temporizadores_activos > 0:
        _mostrar_temporizadores_activos_grupos(temporizador_pvd_mejorado, todas_colas)


def _mostrar_pausa_en_curso_grupo(pausa, grupo_id, cola_grupo, config_pvd, grupos_config):
    """Muestra información de una pausa en curso para un grupo específico"""
    with st.container():
        col_info, col_acciones = st.columns([3, 1])
        with col_info:
            duracion_elegida = pausa.get('duracion_elegida', 'corta')
            
            # Usar configuración del grupo si existe
            if grupo_id in grupos_config:
                duracion_minutos = (grupos_config[grupo_id]['duracion_corta'] 
                                  if duracion_elegida == 'corta' 
                                  else grupos_config[grupo_id]['duracion_larga'])
                max_simultaneo = grupos_config[grupo_id]['maximo_simultaneo']
            else:
                duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                max_simultaneo = config_pvd.get('maximo_simultaneo', 3)
            
            tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
            tiempo_transcurrido = int((obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60)
            tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
            
            progreso = min(100, (tiempo_transcurrido / duracion_minutos) * 100)
            st.progress(int(progreso))
            
            hora_inicio_madrid = formatear_hora_madrid(tiempo_inicio)
            hora_fin_estimada = formatear_hora_madrid(tiempo_inicio + timedelta(minutes=duracion_minutos))
            
            # Contar pausas activas en este grupo
            pausas_activas_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            
            st.write(f"**Agente:** {pausa.get('usuario_nombre', 'Desconocido')}")
            st.write(f"**Grupo:** {grupo_id} ({pausas_activas_grupo}/{max_simultaneo} activos)")
            st.write(f"**Usuario ID:** {pausa['usuario_id']}")
            st.write(f"**Duración:** {duracion_minutos} min ({'Corta' if duracion_elegida == 'corta' else 'Larga'})")
            st.write(f"**Inició:** {hora_inicio_madrid} | **Finaliza:** {hora_fin_estimada}")
            st.write(f"**Transcurrido:** {tiempo_transcurrido} min | **Restante:** {tiempo_restante} min")
            
            if tiempo_restante == 0:
                st.warning("⏰ **Pausa finalizada automáticamente**")
        
        with col_acciones:
            if st.button("✅ Finalizar", key=f"fin_{pausa['id']}_{grupo_id}", use_container_width=True):
                pausa['estado'] = 'COMPLETADO'
                pausa['timestamp_fin'] = obtener_hora_madrid().isoformat()
                guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                
                # Notificar al siguiente en este grupo (si existe la función)
                if hasattr(temporizador_pvd_mejorado, '_iniciar_siguiente_automatico_grupo'):
                    temporizador_pvd_mejorado._iniciar_siguiente_automatico_grupo(grupo_id)
                else:
                    # Fallback a función antigua
                    from database import consolidar_colas_pvd
                    todas_colas_temp = obtener_todas_colas_pvd()
                    cola_consolidada = consolidar_colas_pvd()
                    temporizador_pvd_mejorado._iniciar_siguiente_automatico(cola_consolidada, config_pvd, grupo_id)
                
                st.success(f"✅ Pausa #{pausa['id']} finalizada manualmente")
                st.rerun()
            
            if st.button("❌ Cancelar", key=f"cancel_{pausa['id']}_{grupo_id}", use_container_width=True):
                pausa['estado'] = 'CANCELADO'
                guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                st.warning(f"⚠️ Pausa #{pausa['id']} cancelada")
                st.rerun()
        
        st.markdown("---")


def _mostrar_cola_espera_grupos(todas_colas, config_pvd, temporizador, grupos_config):
    """Muestra la cola de espera de pausas por grupos"""
    st.write("### 📝 Cola de Espera (Agrupada por Grupos)")
    
    # Procesar cada grupo
    for grupo_id, cola_grupo in todas_colas.items():
        pausas_espera = [p for p in cola_grupo if p['estado'] == 'ESPERANDO']
        
        if pausas_espera:
            pausas_espera = sorted(pausas_espera, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
            
            with st.expander(f"**Grupo: {grupo_id}** ({len(pausas_espera)} en espera)", expanded=True):
                for i, pausa in enumerate(pausas_espera):
                    _mostrar_pausa_en_espera_grupo(pausa, i, grupo_id, cola_grupo, config_pvd, temporizador, grupos_config)


def _mostrar_pausa_en_espera_grupo(pausa, indice, grupo_id, cola_grupo, config_pvd, temporizador, grupos_config):
    """Muestra información de una pausa en espera para un grupo específico"""
    duracion_elegida = pausa.get('duracion_elegida', 'corta')
    
    # Usar configuración del grupo
    if grupo_id in grupos_config:
        duracion_corta = grupos_config[grupo_id]['duracion_corta']
        duracion_larga = grupos_config[grupo_id]['duracion_larga']
        max_simultaneo = grupos_config[grupo_id]['maximo_simultaneo']
    else:
        duracion_corta = config_pvd['duracion_corta']
        duracion_larga = config_pvd['duracion_larga']
        max_simultaneo = config_pvd.get('maximo_simultaneo', 3)
    
    duracion_display = f"{duracion_corta} min" if duracion_elegida == 'corta' else f"{duracion_larga} min"
    tiempo_restante = temporizador.obtener_tiempo_restante(pausa['usuario_id'])
    hora_solicitud = formatear_hora_madrid(pausa['timestamp_solicitud'])
    
    with st.container():
        col_esp1, col_esp2, col_esp3, col_esp4, col_esp5, col_esp6 = st.columns([2, 2, 1, 2, 2, 1])
        with col_esp1:
            st.write(f"**#{indice+1}** - {pausa.get('usuario_nombre', 'Desconocido')}")
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
            # Contar pausas activas en este grupo
            en_pausa_grupo = len([p for p in cola_grupo if p['estado'] == 'EN_CURSO'])
            
            if en_pausa_grupo < max_simultaneo and indice == 0:
                if st.button("▶️ Iniciar", 
                             key=f"iniciar_{grupo_id}_{pausa['id']}_{indice}",  # Añadí indice para más unicidad
                             use_container_width=True):
                    pausa['estado'] = 'EN_CURSO'
                    pausa['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                    pausa['confirmado'] = True
                    guardar_cola_pvd_grupo(grupo_id, cola_grupo)
                    
                    temporizador.cancelar_temporizador(pausa['usuario_id'])
                    
                    st.success(f"✅ Pausa #{pausa['id']} iniciada manualmente")
                    st.rerun()
            else:
                st.button("⏳ Esperando...", 
                          disabled=True, 
                          use_container_width=True,
                          key=f"esperando_{grupo_id}_{pausa['id']}_{indice}")  # KEY AÑADIDA AQUÍ
        
        st.markdown("---")

def _mostrar_temporizadores_activos_grupos(temporizador, todas_colas):
    """Muestra información de temporizadores activos por grupos"""
    st.write("### ⏱️ Temporizadores Activos")
    
    for usuario_id, temp_info in temporizador.temporizadores_activos.items():
        if temp_info.get('activo', True):
            tiempo_restante = temporizador.obtener_tiempo_restante(usuario_id)
            if tiempo_restante and tiempo_restante > 0:
                with st.container():
                    col_temp1, col_temp2, col_temp3 = st.columns([3, 2, 1])
                    with col_temp1:
                        st.write(f"**Usuario:** {usuario_id}")
                        # Buscar el grupo del usuario
                        grupo = "N/A"
                        for grupo_id, cola_grupo in todas_colas.items():
                            for pausa in cola_grupo:
                                if pausa['usuario_id'] == usuario_id:
                                    grupo = grupo_id
                                    break
                            if grupo != "N/A":
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
                            temporizador.cancelar_temporizador(usuario_id)
                            st.rerun()

# ==============================================
# FUNCIONES DE GESTIÓN DE FACTURAS Y MODELOS
# ==============================================

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

# ==============================================
# FUNCIONES DE CONFIGURACIÓN DEL SISTEMA
# ==============================================

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

def gestion_secciones_visibles():
    """Configuración de secciones visibles para usuarios"""
    st.subheader("👁️ Configuración de Secciones Visibles")
    
    config_sistema = cargar_config_sistema()
    
    if 'secciones_activas' not in config_sistema:
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

# ==============================================
# FUNCIONES DE GESTIÓN DE FESTIVOS
# ==============================================

def gestion_festivos():
    """Panel de administración para gestionar festivos"""
    st.subheader("🗓️ Gestión de Festivos")
    
    # Cargar festivos actuales
    festivos_data = cargar_festivos()
    
    tab1, tab2, tab3 = st.tabs(["📅 Ver Festivos", "➕ Añadir Festivo", "⚙️ Configuración"])
    
    with tab1:
        _mostrar_festivos_actuales(festivos_data)
    
    with tab2:
        _añadir_nuevo_festivo()
    
    with tab3:
        _configuracion_festivos(festivos_data)

def _mostrar_festivos_actuales(festivos_data):
    """Muestra los festivos actuales"""
    st.write("### 📋 Festivos Nacionales (España)")
    
    año_actual = datetime.now().year
    años = list(festivos_data.get("festivos", {}).keys())
    
    if not años:
        st.info("No hay festivos configurados")
        return
    
    # Selector de año
    año_seleccionado = st.selectbox(
        "Seleccionar año:",
        años,
        index=años.index(str(año_actual)) if str(año_actual) in años else 0
    )
    
    if año_seleccionado in festivos_data.get("festivos", {}):
        festivos_año = festivos_data["festivos"][año_seleccionado]
        
        if festivos_año:
            st.write(f"**Festivos {año_seleccionado}:**")
            
            datos_tabla = []
            for fecha_str in sorted(festivos_año):
                try:
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
                    datos_tabla.append({
                        'Fecha': fecha.strftime("%d/%m/%Y"),
                        'Día': fecha.strftime("%A"),
                        'Festivo': _obtener_nombre_festivo(fecha)
                    })
                except:
                    datos_tabla.append({'Fecha': fecha_str, 'Día': 'N/A', 'Festivo': 'Desconocido'})
            
            df_festivos = pd.DataFrame(datos_tabla)
            st.dataframe(df_festivos, use_container_width=True)
            
            # Opción para eliminar festivo
            st.write("### 🗑️ Eliminar Festivo")
            festivos_options = [f"{row['Fecha']} - {row['Festivo']}" for _, row in df_festivos.iterrows()]
            
            festivo_a_eliminar = st.selectbox(
                "Seleccionar festivo a eliminar:",
                festivos_options
            )
            
            if festivo_a_eliminar and st.button("Eliminar Festivo", type="secondary"):
                fecha_str = festivo_a_eliminar.split(" - ")[0]
                fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
                fecha_iso = fecha_dt.strftime("%Y-%m-%d")
                
                if eliminar_festivo(fecha_iso, año_seleccionado):
                    st.success(f"✅ Festivo eliminado: {fecha_str}")
                    st.rerun()
                else:
                    st.error("❌ Error al eliminar festivo")
        else:
            st.info(f"No hay festivos configurados para {año_seleccionado}")
    
    # Festivos personalizados
    if festivos_data.get("festivos_personalizados"):
        st.write("### 🏢 Festivos de Empresa")
        
        for categoria, festivos in festivos_data["festivos_personalizados"].items():
            if festivos:
                st.write(f"**{categoria.title()}:**")
                for festivo in festivos:
                    if isinstance(festivo, dict):
                        st.write(f"- {festivo.get('fecha')}: {festivo.get('descripcion', 'Sin descripción')}")
                    else:
                        st.write(f"- {festivo}")

def _obtener_nombre_festivo(fecha):
    """Obtiene el nombre del festivo basado en la fecha"""
    festivos_nombres = {
        "01-01": "Año Nuevo",
        "01-06": "Día de Reyes",
        "03-19": "San José",
        "05-01": "Día del Trabajador",
        "07-25": "Santiago Apóstol",
        "08-15": "Asunción de la Virgen",
        "10-12": "Día de la Hispanidad",
        "11-01": "Todos los Santos",
        "12-06": "Día de la Constitución",
        "12-08": "Inmaculada Concepción",
        "12-25": "Navidad"
    }
    
    clave = fecha.strftime("%m-%d")
    return festivos_nombres.get(clave, "Festivo nacional")

def _añadir_nuevo_festivo():
    """Interfaz para añadir nuevo festivo"""
    from festivos_manager import agregar_festivo
    
    st.write("### ➕ Añadir Nuevo Festivo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fecha_festivo = st.date_input(
            "Fecha del festivo:",
            value=datetime.now().date()
        )
    
    with col2:
        tipo_festivo = st.selectbox(
            "Tipo de festivo:",
            ["nacional", "personalizado"]
        )
    
    descripcion = st.text_input(
        "Descripción (opcional):",
        help="Ej: 'Puente de la empresa', 'Día de formación', etc."
    )
    
    if st.button("✅ Añadir Festivo", type="primary"):
        if agregar_festivo(fecha_festivo, tipo_festivo, descripcion):
            st.success(f"✅ Festivo añadido: {fecha_festivo.strftime('%d/%m/%Y')}")
            st.rerun()
        else:
            st.error("❌ Error al añadir festivo")

def _configuracion_festivos(festivos_data):
    """Configuración avanzada de festivos"""
    st.write("### ⚙️ Configuración Avanzada")
    
    # Importar/Exportar festivos
    st.write("#### 📥 Importar/Exportar")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # Exportar festivos
        if st.button("📤 Exportar Festivos a JSON", use_container_width=True):
            json_str = json.dumps(festivos_data, indent=4, ensure_ascii=False, default=str)
            st.download_button(
                label="📥 Descargar JSON",
                data=json_str,
                file_name=f"festivos_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    with col_exp2:
        # Importar festivos
        uploaded_file = st.file_uploader(
            "Subir JSON de festivos",
            type=['json'],
            key="upload_festivos"
        )
        
        if uploaded_file is not None:
            try:
                nuevos_festivos = json.load(uploaded_file)
                st.write("**Vista previa:**")
                st.json(nuevos_festivos)
                
                if st.button("📥 Importar Festivos", type="primary"):
                    if guardar_festivos(nuevos_festivos):
                        st.success("✅ Festivos importados correctamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al importar festivos")
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {e}")
    
    # Resetear festivos
    st.write("#### 🔄 Resetear Festivos")
    st.warning("Esta acción restaurará los festivos nacionales de España por defecto.")
    
    if st.button("🔄 Restaurar Festivos por Defecto", type="secondary"):
        from festivos_manager import cargar_festivos
        import os
        archivo_festivos = 'data/festivos.json'
        if os.path.exists(archivo_festivos):
            os.remove(archivo_festivos)
        
        cargar_festivos()  # Esto creará el archivo con valores por defecto
        st.success("✅ Festivos restaurados a valores por defecto")
        st.rerun()

# ==============================================
# FUNCIÓN PRINCIPAL DEL PANEL DE ADMINISTRACIÓN
# ==============================================

def mostrar_panel_administrador():
    """Panel de administración"""
    st.header("🔧 Panel de Administración")

    # 12 pestañas
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
        "⚡ Electricidad", "🔥 Gas", "👥 Usuarios", "👑 Super Users", "👁️ PVD", 
        "📄 Facturas", "☀️ Excedentes", "⚙️ Sistema", "👁️ Secciones", 
        "📊 Analizador Llamadas", "Festivos", "🔄 GitHub Sync"
    ])
    
    with tab1:
        gestion_electricidad()
    with tab2:
        gestion_gas()
    with tab3:
        gestion_usuarios()
    with tab4:
        gestion_super_users_admin()
    with tab5:
        gestion_pvd_admin()
    with tab6:
        gestion_modelos_factura()
    with tab7:
        gestion_excedentes()
    with tab8:
        gestion_config_sistema()
    with tab9:
        gestion_secciones_visibles()
    with tab10:
        interfaz_analisis_llamadas()
    with tab11:
        gestion_festivos()
    with tab12:
        try:
            from sync_ui_simple import show_sync_panel_simple
            show_sync_panel_simple()
        except ImportError:
            st.error("❌ No se puede cargar el módulo de sincronización")
            st.info("Asegúrate de que `sync_ui_simple.py` existe en tu repositorio")