import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import plotly.express as px

from database import (
    cargar_super_users, guardar_super_users,
    cargar_registro_llamadas, guardar_registro_llamadas,
    cargar_configuracion_usuarios, cargar_config_sistema
)
from utils import obtener_hora_madrid, formatear_hora_madrid


# ============================================================================
# FUNCIONES DE GESTIÓN DE SUPER USUARIOS (ADMIN)
# ============================================================================

def gestion_super_users_admin():
    """Panel de administración para gestionar super usuarios"""
    st.subheader("👑 Gestión de Super Usuarios")
    
    # Cargar datos
    super_users_config = cargar_super_users()
    usuarios_config = cargar_configuracion_usuarios()
    
    tab1, tab2, tab3, tab4 = st.tabs(["👑 Super Users", "👥 Agentes", "⚙️ Configuración", "🧹 Mantenimiento"])
    
    with tab1:
        _mostrar_panel_super_users(super_users_config, usuarios_config)
    
    with tab2:
        _mostrar_gestion_agentes(super_users_config, usuarios_config)
    
    with tab3:
        _mostrar_configuracion_metricas(super_users_config)
    
    with tab4:
        _mostrar_mantenimiento_sistema()


def _mostrar_panel_super_users(super_users_config, usuarios_config):
    """Muestra el panel de gestión de super usuarios"""
    st.write("### 👑 Lista de Super Usuarios")
    st.info("Los super usuarios pueden ver y gestionar métricas de agentes")
    
    super_users_list = super_users_config.get("super_users", [])
    
    col_lista1, col_lista2 = st.columns([2, 1])
    
    with col_lista1:
        _mostrar_lista_super_users(super_users_list, usuarios_config)
    
    with col_lista2:
        _mostrar_acciones_super_users()
    
    _gestionar_creacion_super_user(super_users_list, super_users_config, usuarios_config)
    _gestionar_eliminacion_super_user(super_users_list, super_users_config)


def _mostrar_lista_super_users(super_users_list, usuarios_config):
    """Muestra la lista de super usuarios actuales - ORDENADA ALFABÉTICAMENTE"""
    st.write("**Super usuarios actuales:**")
    if super_users_list:
        # Ordenar alfabéticamente por nombre de usuario
        super_users_sorted = sorted(super_users_list)
        
        for user in super_users_sorted:
            nombre = usuarios_config.get(user, {}).get('nombre', user)
            st.write(f"• **{user}** - {nombre}")
    else:
        st.info("No hay super usuarios configurados (solo admin)")


def _mostrar_acciones_super_users():
    """Muestra las acciones disponibles para super usuarios"""
    st.write("**Acciones:**")
    if st.button("➕ Añadir Super Usuario", use_container_width=True):
        st.session_state.creando_super_user = True
        st.rerun()


def _gestionar_creacion_super_user(super_users_list, super_users_config, usuarios_config):
    """Gestiona la creación de nuevos super usuarios"""
    if st.session_state.get('creando_super_user', False):
        st.write("### ➕ Añadir Nuevo Super Usuario")
        
        usuarios_disponibles = []
        for username, config in usuarios_config.items():
            if username != "admin" and username not in super_users_list:
                nombre = config.get('nombre', username)
                usuarios_disponibles.append((username, nombre))
        
        if not usuarios_disponibles:
            st.warning("No hay usuarios disponibles para añadir como super usuarios")
            if st.button("❌ Cancelar"):
                st.session_state.creando_super_user = False
                st.rerun()
        else:
            usuarios_options = [f"{user} - {nombre}" for user, nombre in usuarios_disponibles]
            
            usuario_seleccionado = st.selectbox(
                "Seleccionar usuario:",
                usuarios_options,
                help="Selecciona el usuario que será super usuario"
            )
            
            if usuario_seleccionado:
                username = usuario_seleccionado.split(" - ")[0]
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Confirmar", type="primary", use_container_width=True):
                        if username not in super_users_list:
                            super_users_list.append(username)
                            super_users_config["super_users"] = super_users_list
                            guardar_super_users(super_users_config)
                            st.success(f"✅ {username} añadido como super usuario")
                            st.session_state.creando_super_user = False
                            st.rerun()
                
                with col_btn2:
                    if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                        st.session_state.creando_super_user = False
                        st.rerun()


def _gestionar_eliminacion_super_user(super_users_list, super_users_config):
    """Gestiona la eliminación de super usuarios"""
    if super_users_list:
        st.write("---")
        st.write("### 🗑️ Quitar Super Usuario")
        
        usuario_a_quitar = st.selectbox(
            "Seleccionar usuario a quitar:",
            super_users_list,
            key="quitar_super_user"
        )
        
        if usuario_a_quitar:
            if st.button("🗑️ Quitar como Super Usuario", type="secondary", use_container_width=True):
                super_users_list.remove(usuario_a_quitar)
                super_users_config["super_users"] = super_users_list
                guardar_super_users(super_users_config)
                st.success(f"✅ {usuario_a_quitar} quitado como super usuario")
                st.rerun()


# ============================================================================
# GESTIÓN DE AGENTES - MODIFICADO CON OBJETIVOS PERSONALIZADOS
# ============================================================================

def _mostrar_gestion_agentes(super_users_config, usuarios_config):
    """Muestra la gestión de agentes CON OBJETIVOS PERSONALIZADOS"""
    st.write("### 👥 Gestión de Agentes")
    
    agentes = super_users_config.get("agentes", {})
    super_users_list = super_users_config.get("super_users", [])
    
    col_agentes1, col_agentes2 = st.columns(2)
    
    with col_agentes1:
        _mostrar_lista_agentes(agentes)
    
    with col_agentes2:
        _mostrar_acciones_agentes()
    
    _gestionar_adicion_agentes(super_users_config, usuarios_config, agentes, super_users_list)
    _gestionar_edicion_agentes(super_users_config, agentes, super_users_list)
    _gestionar_borrado_agente(super_users_config, agentes)


def _mostrar_lista_agentes(agentes):
    """Muestra la lista de agentes registrados CON OBJETIVOS Y ORDEN ALFABÉTICO"""
    st.write("**Agentes registrados:**")
    if agentes:
        # Ordenar agentes alfabéticamente por nombre de usuario (ID)
        agentes_ordenados = sorted(agentes.items(), key=lambda x: x[0])
        
        for agent_id, info in agentes_ordenados:
            estado = "✅ Activo" if info.get('activo', True) else "❌ Inactivo"
            grupo = info.get('grupo', 'Sin grupo')
            supervisor = info.get('supervisor', 'Sin asignar')
            objetivo_ventas = info.get('objetivo_ventas_mensual', 'No configurado')
            
            st.write(f"• **{agent_id}** - {info.get('nombre', 'Sin nombre')} ({estado})")
            st.write(f"  Grupo: {grupo} | Supervisor: {supervisor}")
            st.write(f"  Objetivo Ventas: {objetivo_ventas}")
    else:
        st.info("No hay agentes registrados")


def _mostrar_acciones_agentes():
    """Muestra las acciones disponibles para agentes"""
    st.write("**Añadir agentes:**")
    if st.button("➕ Añadir desde Usuarios", use_container_width=True):
        st.session_state.añadiendo_agentes = True
        st.rerun()


def _gestionar_adicion_agentes(super_users_config, usuarios_config, agentes, super_users_list):
    """Gestiona la adición de nuevos agentes"""
    if st.session_state.get('añadiendo_agentes', False):
        st.write("### ➕ Añadir Agentes desde Usuarios")
        
        usuarios_disponibles = []
        for username, config in usuarios_config.items():
            if username != "admin" and username not in agentes:
                nombre = config.get('nombre', username)
                grupo = config.get('grupo', 'Sin grupo')
                tipo = config.get('tipo', 'user')
                usuarios_disponibles.append({
                    'username': username,
                    'nombre': nombre,
                    'grupo': grupo,
                    'tipo': tipo
                })
        
        if not usuarios_disponibles:
            st.warning("No hay usuarios disponibles para añadir como agentes")
            if st.button("❌ Cancelar"):
                st.session_state.añadiendo_agentes = False
                st.rerun()
        else:
            df_usuarios = pd.DataFrame(usuarios_disponibles)
            df_usuarios['Seleccionar'] = False
            
            edited_df = st.data_editor(
                df_usuarios,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                    "username": "Usuario",
                    "nombre": "Nombre",
                    "grupo": "Grupo",
                    "tipo": "Tipo"
                },
                disabled=["username", "nombre", "grupo", "tipo"],
                hide_index=True,
                use_container_width=True
            )
            
            seleccionados = edited_df[edited_df['Seleccionar']]
            
            opciones_supervisor = ['Sin asignar'] + super_users_list
            supervisor_asignado = st.selectbox(
                "Asignar supervisor a los nuevos agentes:",
                opciones_supervisor,
                help="Selecciona el super usuario que supervisará estos agentes"
            )
            
            col_add1, col_add2 = st.columns(2)
            with col_add1:
                if st.button(f"✅ Añadir {len(seleccionados)} Agente(s)", type="primary", use_container_width=True):
                    if len(seleccionados) > 0:
                        for _, row in seleccionados.iterrows():
                            agentes[row['username']] = {
                                'nombre': row['nombre'],
                                'grupo': row['grupo'],
                                'tipo': row['tipo'],
                                'activo': True,
                                'supervisor': supervisor_asignado if supervisor_asignado != 'Sin asignar' else '',
                                'objetivo_ventas_mensual': 10,  # Valor por defecto
                                'fecha_registro': datetime.now().strftime("%Y-%m-%d")
                            }
                        
                        super_users_config["agentes"] = agentes
                        guardar_super_users(super_users_config)
                        
                        st.success(f"✅ {len(seleccionados)} agente(s) añadido(s)")
                        st.session_state.añadiendo_agentes = False
                        st.rerun()
                    else:
                        st.warning("Selecciona al menos un agente")
            
            with col_add2:
                if st.button("❌ Cancelar", type="secondary", use_container_width=True):
                    st.session_state.añadiendo_agentes = False
                    st.rerun()


def _gestionar_edicion_agentes(super_users_config, agentes, super_users_list):
    """Gestiona la edición de agentes existentes"""
    if agentes:
        st.write("---")
        st.write("### 🔧 Editar/Borrar Agentes")
        
        agentes_options = [f"{agent_id} - {info.get('nombre', 'Sin nombre')}" 
                         for agent_id, info in agentes.items()]
        
        agente_seleccionado = st.selectbox(
            "Seleccionar agente a editar/borrar:",
            agentes_options,
            key="select_agente_editar"
        )
        
        if agente_seleccionado:
            agent_id = agente_seleccionado.split(" - ")[0]
            info_agente = agentes[agent_id]
            
            with st.expander(f"✏️ Editar Agente: {info_agente.get('nombre', agent_id)}", expanded=True):
                _mostrar_formulario_edicion_agente(agent_id, info_agente, agentes, super_users_config, super_users_list)


def _mostrar_formulario_edicion_agente(agent_id, info_agente, agentes, super_users_config, super_users_list):
    """Muestra el formulario para editar un agente CON OBJETIVO DE VENTAS"""
    col_edit1, col_edit2 = st.columns(2)
    
    with col_edit1:
        nombre_editado = st.text_input(
            "Nombre:",
            value=info_agente.get('nombre', ''),
            key=f"edit_nombre_{agent_id}"
        )
        
        grupo_editado = st.text_input(
            "Grupo:",
            value=info_agente.get('grupo', ''),
            key=f"edit_grupo_{agent_id}"
        )
        
        tipos_permitidos = ["user", "agent", "supervisor", "admin", "manual"]
        tipo_actual = info_agente.get('tipo', 'user')
        if tipo_actual not in tipos_permitidos:
            tipo_actual = 'user'

        tipo_editado = st.selectbox(
            "Tipo:",
            tipos_permitidos,
            index=tipos_permitidos.index(tipo_actual),
            key=f"edit_tipo_{agent_id}"
        )
    
    with col_edit2:
        activo_editado = st.checkbox(
            "Activo",
            value=info_agente.get('activo', True),
            key=f"edit_activo_{agent_id}"
        )
        
        # OBJETIVO DE VENTAS PERSONALIZADO
        objetivo_actual = info_agente.get('objetivo_ventas_mensual', 10)
        objetivo_editado = st.number_input(
            "Objetivo Ventas Mensual:",
            min_value=0,
            max_value=500,
            value=objetivo_actual,
            key=f"edit_objetivo_{agent_id}",
            help="Ventas objetivo específicas para este agente"
        )
        
        opciones_supervisor = ['Sin asignar'] + super_users_list
        supervisor_actual = info_agente.get('supervisor', '')
        
        if supervisor_actual in opciones_supervisor:
            index_supervisor = opciones_supervisor.index(supervisor_actual)
        else:
            index_supervisor = 0
        
        supervisor_editado = st.selectbox(
            "Supervisor asignado:",
            opciones_supervisor,
            index=index_supervisor,
            key=f"edit_supervisor_{agent_id}"
        )
        
        if 'fecha_registro' in info_agente:
            st.info(f"📅 Registrado: {info_agente['fecha_registro']}")
    
    col_btn_edit1, col_btn_edit2, col_btn_edit3 = st.columns(3)
    
    with col_btn_edit1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            agentes[agent_id] = {
                'nombre': nombre_editado,
                'grupo': grupo_editado,
                'tipo': tipo_editado,
                'activo': activo_editado,
                'supervisor': supervisor_editado if supervisor_editado != 'Sin asignar' else '',
                'objetivo_ventas_mensual': objetivo_editado,  # Guardar objetivo personalizado
                'fecha_registro': info_agente.get('fecha_registro', datetime.now().strftime("%Y-%m-%d")),
                'fecha_actualizacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            super_users_config["agentes"] = agentes
            guardar_super_users(super_users_config)
            st.success(f"✅ Agente {nombre_editado} actualizado correctamente")
            st.rerun()
    
    with col_btn_edit2:
        if st.button("📊 Ver Historial", type="secondary", use_container_width=True):
            st.session_state.ver_historial_agente = agent_id
            st.rerun()
    
    with col_btn_edit3:
        if st.button("🗑️ Borrar Agente", type="secondary", use_container_width=True):
            st.session_state.agente_a_borrar = agent_id
            st.rerun()


def _gestionar_borrado_agente(super_users_config, agentes):
    """Gestiona el borrado de agentes"""
    if st.session_state.get('agente_a_borrar'):
        agent_id = st.session_state.agente_a_borrar
        info_agente = agentes.get(agent_id, {})
        nombre_agente = info_agente.get('nombre', agent_id)
        
        st.warning(f"⚠️ **CONFIRMAR BORRADO DEL AGENTE: {nombre_agente}**")
        
        registro_llamadas = cargar_registro_llamadas()
        
        registros_historicos = 0
        for fecha_str, datos_dia in registro_llamadas.items():
            if agent_id in datos_dia:
                registros_historicos += 1
        
        st.write(f"**📊 Este agente tiene:**")
        st.write(f"• {registros_historicos} día(s) de registro histórico")
        st.write(f"• Grupo: {info_agente.get('grupo', 'Sin grupo')}")
        st.write(f"• Supervisor: {info_agente.get('supervisor', 'Sin asignar')}")
        st.write(f"• Objetivo ventas: {info_agente.get('objetivo_ventas_mensual', 'No configurado')}")
        
        st.write("**⚠️ ADVERTENCIA:** Al borrar este agente:")
        st.write("1. Se eliminará permanentemente de la lista de agentes")
        st.write("2. Se perderán TODOS sus datos históricos de llamadas y ventas")
        st.write("3. Esta acción NO se puede deshacer")
        
        col_conf1, col_conf2 = st.columns(2)
        
        with col_conf1:
            if st.button("✅ **SÍ, BORRAR DEFINITIVAMENTE**", type="primary", use_container_width=True):
                del agentes[agent_id]
                super_users_config["agentes"] = agentes
                guardar_super_users(super_users_config)
                
                for fecha_str, datos_dia in registro_llamadas.items():
                    if agent_id in datos_dia:
                        del registro_llamadas[fecha_str][agent_id]
                
                guardar_registro_llamadas(registro_llamadas)
                
                st.success(f"✅ Agente {nombre_agente} borrado correctamente")
                st.success(f"✅ {registros_historicos} registros históricos eliminados")
                
                st.session_state.agente_a_borrar = None
                st.rerun()
        
        with col_conf2:
            if st.button("❌ **NO, CANCELAR**", type="secondary", use_container_width=True):
                st.session_state.agente_a_borrar = None
                st.info("❌ Borrado cancelado")
                st.rerun()


# ============================================================================
# CONFIGURACIÓN DE MÉTRICAS
# ============================================================================

def _mostrar_configuracion_metricas(super_users_config):
    """Muestra la configuración de métricas CON OBJETIVOS SEPARADOS"""
    st.write("### ⚙️ Configuración de Métricas")
    
    config_actual = super_users_config.get("configuracion", {})
    
    col_conf1, col_conf2 = st.columns(2)
    
    with col_conf1:
        duracion_minima = st.number_input(
            "Duración mínima llamada (minutos):",
            min_value=1,
            max_value=60,
            value=config_actual.get("duracion_minima_llamada", 15)
        )
        
        periodo = st.selectbox(
            "Periodo mensual:",
            ["calendario", "rolling_30"],
            index=0 if config_actual.get("periodo_mensual", "calendario") == "calendario" else 1,
            help="Calendario: mes natural | Rolling: últimos 30 días"
        )
    
    with col_conf2:
        target_llamadas = st.number_input(
            "Target mensual de llamadas (por agente):",
            min_value=1,
            max_value=1000,
            value=config_actual.get("target_llamadas", 50),
            help="Cada agente debe hacer X llamadas >15min al mes"
        )
        
        # 🎯 OBJETIVO GLOBAL DE CAMPAÑA (NO POR AGENTE)
        target_ventas_global = st.number_input(
            "🎯 Target mensual VENTAS (Campaña Total):",
            min_value=1,
            max_value=10000,
            value=config_actual.get("target_ventas_global", 100),
            help="Objetivo TOTAL de ventas para toda la campaña/equipo"
        )
    
    metrica = st.selectbox(
        "Métrica de eficiencia:",
        ["ratio", "total", "ponderado"],
        index=["ratio", "total", "ponderado"].index(config_actual.get("metrica_eficiencia", "ratio")),
        help="Ratio: ventas/llamadas | Total: sumatoria | Ponderado: (ventas*2 + llamadas*1)"
    )
    
    mostrar_solo_mis_agentes = st.checkbox(
        "Super usuarios ven solo sus agentes asignados",
        value=config_actual.get("mostrar_solo_mis_agentes", False),
        help="Si está activado, cada super usuario solo verá los agentes que tiene asignados"
    )
    
    st.write("### 🔔 Configuración de Alertas")
    
    col_alert1, col_alert2 = st.columns(2)
    
    with col_alert1:
        umbral_alertas_llamadas = st.number_input(
            "Umbral alertas llamadas (%):",
            min_value=1,
            max_value=100,
            value=config_actual.get("umbral_alertas_llamadas", 20),
            help="Porcentaje por debajo de la media que activa alerta"
        )
    
    with col_alert2:
        minimo_llamadas_dia = st.number_input(
            "Mínimo llamadas/día para media:",
            min_value=0,
            max_value=500,
            value=config_actual.get("minimo_llamadas_dia", 50),
            help="Mínimo de llamadas diarias para considerar en cálculo de media"
        )
    
    if st.button("💾 Guardar Configuración", type="primary"):
        nueva_config = {
            "duracion_minima_llamada": duracion_minima,
            "periodo_mensual": periodo,
            "target_llamadas": target_llamadas,
            "target_ventas_global": target_ventas_global,  # ⬅️ CAMBIADO DE 'target_ventas'
            "metrica_eficiencia": metrica,
            "mostrar_solo_mis_agentes": mostrar_solo_mis_agentes,
            "umbral_alertas_llamadas": umbral_alertas_llamadas,
            "minimo_llamadas_dia": minimo_llamadas_dia
        }
        
        super_users_config["configuracion"] = nueva_config
        guardar_super_users(super_users_config)
        st.success("✅ Configuración guardada")
        st.rerun()


# ============================================================================
# MANTENIMIENTO DEL SISTEMA
# ============================================================================

def _mostrar_mantenimiento_sistema():
    """Muestra las opciones de mantenimiento del sistema"""
    st.write("### 🧹 Mantenimiento del Sistema")
    
    col_mant1, col_mant2 = st.columns(2)
    
    with col_mant1:
        st.write("**Reiniciar métricas:**")
        st.warning("Esta acción eliminará todos los datos históricos de llamadas y ventas")
        
        if st.button("🔄 Reiniciar TODAS las métricas", type="secondary", use_container_width=True):
            st.session_state.confirmar_reinicio = True
    
    with col_mant2:
        st.write("**Exportar/Importar:**")
        if st.button("📤 Exportar datos completos", use_container_width=True):
            exportar_datos_completos()
        
        if st.button("📥 Importar backup", use_container_width=True):
            st.session_state.importar_backup = True
    
    if st.session_state.get('confirmar_reinicio', False):
        _confirmar_reinicio_metricas()


def _confirmar_reinicio_metricas():
    """Confirma el reinicio de métricas"""
    st.error("⚠️ **CONFIRMAR REINICIO COMPLETO**")
    st.write("Esta acción **NO SE PUEDE DESHACER** y eliminará:")
    st.write("1. 📊 Todas las métricas históricas de llamadas")
    st.write("2. 💰 Todas las métricas históricas de ventas")
    st.write("3. 📅 Todos los registros diarios")
    st.write("4. 🔄 Se mantendrán solo los agentes configurados")
    
    col_conf_r1, col_conf_r2 = st.columns(2)
    
    with col_conf_r1:
        if st.button("✅ SÍ, REINICIAR TODO", type="primary", use_container_width=True):
            registro_llamadas = {}
            guardar_registro_llamadas(registro_llamadas)
            st.success("✅ Todas las métricas reiniciadas")
            st.session_state.confirmar_reinicio = False
            st.rerun()
    
    with col_conf_r2:
        if st.button("❌ NO, CANCELAR", type="secondary", use_container_width=True):
            st.session_state.confirmar_reinicio = False
            st.rerun()


def exportar_datos_completos():
    """Exporta todos los datos del sistema"""
    registro_llamadas = cargar_registro_llamadas()
    super_users_config = cargar_super_users()
    
    datos_exportar = {
        "registro_llamadas": registro_llamadas,
        "super_users_config": super_users_config,
        "fecha_exportacion": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    json_str = json.dumps(datos_exportar, indent=2, default=str)
    
    st.download_button(
        label="📥 Descargar backup completo",
        data=json_str,
        file_name=f"backup_super_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


# ============================================================================
# PANEL DE SUPER USUARIO - CON OBJETIVOS DE VENTAS
# ============================================================================

def panel_super_usuario():
    """Panel principal para super usuarios CON OBJETIVOS DE VENTAS"""
    
    # Manejo de páginas especiales de alertas
    if st.session_state.get('mostrar_gestion_alertas', False):
        mostrar_gestion_alertas_descartadas()
        return
    
    if st.session_state.get('mostrar_todas_alertas', False):
        st.header("📋 Todas las Alertas")
        st.warning("Función 'mostrar_todas_las_alertas' no implementada")
        if st.button("← Volver al Panel"):
            st.session_state.mostrar_todas_alertas = False
            st.rerun()
        return
    
    st.header("📊 Panel de Super Usuario")
    
    super_users_config = cargar_super_users()
    configuracion = super_users_config.get("configuracion", {})
    username = st.session_state.get('username', '')
    
    agentes_completos = super_users_config.get("agentes", {})
    
    if configuracion.get("mostrar_solo_mis_agentes", False) and username:
        agentes = {k: v for k, v in agentes_completos.items() 
                  if v.get('supervisor', '') == username}
    else:
        agentes = agentes_completos
    
    registro_llamadas = cargar_registro_llamadas()
    
    if not agentes:
        st.warning("⚠️ No hay agentes asignados a tu supervisión.")
        
        if configuracion.get("mostrar_solo_mis_agentes", False) and username:
            if st.button("👁️ Ver todos los agentes"):
                st.session_state.modo_temporal_todos = True
                st.rerun()
        
        if st.session_state.get('modo_temporal_todos', False):
            agentes = agentes_completos
            if not agentes:
                st.warning("⚠️ No hay agentes configurados en el sistema. Contacta al administrador.")
                return
            else:
                st.info("👁️ **Modo temporal:** Viendo todos los agentes del sistema")
    else:
        st.session_state.modo_temporal_todos = False
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📅 Registro Diario", "📊 Métricas Mensuales", "📈 Dashboard", 
        "👥 Mis Agentes", "🔧 Editar Agentes", "📥 Importar CSV", "📊 Monitorizaciones"
    ])
    
    with tab1:
        gestion_registro_diario(agentes, registro_llamadas, configuracion)
    
    with tab2:
        mostrar_metricas_mensuales(agentes, registro_llamadas, configuracion)
    
    with tab3:
        mostrar_dashboard(agentes, registro_llamadas, configuracion)
    
    with tab4:
        gestion_agentes_super_usuario(agentes, super_users_config)
    
    with tab5:
        if username:
            gestion_agentes_super_usuario_edicion(agentes, super_users_config, username)
        else:
            st.warning("⚠️ Debes iniciar sesión como super usuario para acceder a esta sección")
    
    with tab6:
        _mostrar_importacion_csv()
    
    with tab7:
        panel_monitorizaciones_super_usuario()


def _mostrar_importacion_csv():
    """Muestra la interfaz de importación de CSV"""
    st.subheader("📥 Importar CSV de Llamadas")
    
    st.info("""
    **Importa datos de llamadas automáticamente al registro diario:**
    - 📞 Llamadas de más de 15 minutos se cuentan como "llamadas"
    - 💰 Cada "UTIL POSITIVO" cuenta como venta (pueden ser 2 si es DÚO)
    - 📅 Los datos se suman a los registros existentes
    """)
    
    if st.button("🚀 Abrir Analizador Completo", type="primary"):
        st.session_state.mostrar_analizador_completo = True
    
    if st.session_state.get('mostrar_analizador_completo', False):
        from llamadas_analyzer import interfaz_analisis_llamadas
        interfaz_analisis_llamadas()
    else:
        _mostrar_importacion_simplificada()


def _mostrar_importacion_simplificada():
    """Muestra la versión simplificada de importación"""
    uploaded_file = st.file_uploader(
        "📤 Sube archivo CSV/TXT de llamadas",
        type=['csv', 'txt'],
        help="Archivo con columnas: agente, tiempo_conversacion, resultado_elec, resultado_gas, fecha, campanya"
    )
    
    if uploaded_file is not None:
        from llamadas_analyzer import analizar_csv_llamadas, importar_datos_a_registro
        
        with st.spinner("Analizando archivo..."):
            df = analizar_csv_llamadas(uploaded_file)
            
            if df is not None:
                st.success("✅ Archivo cargado correctamente")
                
                _mostrar_estadisticas_importacion(df)
                
                if st.button("📥 Importar Datos al Sistema", type="primary"):
                    with st.spinner("Importando datos..."):
                        super_users_config = cargar_super_users()
                        exito, mensaje = importar_datos_a_registro(df, super_users_config)
                        
                        if exito:
                            st.success("✅ Datos importados exitosamente")
                            for linea in mensaje.split('\n'):
                                if linea.strip():
                                    st.write(linea)
                        else:
                            st.error(f"❌ Error: {mensaje}")


def _mostrar_estadisticas_importacion(df):
    """Muestra estadísticas del archivo a importar"""
    llamadas_largas = len(df[df['tiempo_conversacion'] > 900])
    agentes_unicos = df['agente'].nunique()
    fechas_unicas = df['fecha'].nunique()
    
    def contar_ventas_fila(row):
        ventas = 0
        if 'UTIL POSITIVO' in str(row.get('resultado_elec', '')).upper():
            ventas += 1
        if 'UTIL POSITIVO' in str(row.get('resultado_gas', '')).upper():
            ventas += 1
        return ventas
    
    df['ventas_totales'] = df.apply(contar_ventas_fila, axis=1)
    ventas_totales = df['ventas_totales'].sum()
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("👥 Agentes", agentes_unicos)
    with col_stats2:
        st.metric("📅 Fechas", fechas_unicas)
    with col_stats3:
        st.metric("📞 Llamadas >15min", llamadas_largas)
    with col_stats4:
        st.metric("💰 Ventas", int(ventas_totales))


# ============================================================================
# GESTIÓN DE REGISTRO DIARIO
# ============================================================================

def gestion_registro_diario(agentes, registro_llamadas, configuracion):
    """Registro diario de llamadas y ventas - Con AMBOS tipos de llamadas"""
    st.subheader("📅 Registro Diario - Tabla")
    
    fecha_hoy = datetime.now().date()
    fecha_seleccionada = st.date_input(
        "Fecha:",
        value=fecha_hoy,
        max_value=fecha_hoy,
        key="fecha_registro_diario"
    )
    
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    datos_dia = registro_llamadas.get(fecha_str, {})
    
    st.write(f"### 📝 Registro para {fecha_seleccionada.strftime('%d/%m/%Y')}")
    
    datos_tabla = _obtener_datos_tabla_registro(agentes, datos_dia)
    
    _mostrar_editor_registro_diario(datos_tabla, fecha_str, registro_llamadas)


def _obtener_datos_tabla_registro(agentes, datos_dia):
    """Obtiene los datos para la tabla de registro diario"""
    datos_tabla = []
    
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            nombre = info.get('nombre', agent_id)
            grupo = info.get('grupo', 'Sin grupo')
            
            datos_registro = datos_dia.get(agent_id, {
                "llamadas_totales": 0,
                "llamadas_15min": 0,
                "ventas": 0
            })
            
            datos_tabla.append({
                'ID': agent_id,
                'Nombre': nombre,
                'Grupo': grupo,
                'Llamadas Totales': int(datos_registro.get('llamadas_totales', 0)),
                'Llamadas >15min': int(datos_registro.get('llamadas_15min', 0)),
                'Ventas': int(datos_registro.get('ventas', 0))
            })
    
    return datos_tabla


def _mostrar_editor_registro_diario(datos_tabla, fecha_str, registro_llamadas):
    """Muestra el editor de registro diario"""
    df_tabla = pd.DataFrame(datos_tabla)
    df_tabla = df_tabla.sort_values('ID')
    
    st.write("**Tabla de registro diario:**")
    
    column_config = {
        'ID': st.column_config.TextColumn('ID', disabled=True),
        'Nombre': st.column_config.TextColumn('Nombre', disabled=True),
        'Grupo': st.column_config.TextColumn('Grupo', disabled=True),
        'Llamadas Totales': st.column_config.NumberColumn(
            'Llamadas Totales',
            min_value=0,
            max_value=500,
            step=1,
            required=True,
            help="Total de llamadas del agente (todas las líneas)"
        ),
        'Llamadas >15min': st.column_config.NumberColumn(
            'Llamadas >15min',
            min_value=0,
            max_value=500,
            step=1,
            required=True,
            help="Solo llamadas de más de 15 minutos"
        ),
        'Ventas': st.column_config.NumberColumn(
            'Ventas',
            min_value=0,
            max_value=100,
            step=1,
            required=True
        )
    }
    
    edited_df = st.data_editor(
        df_tabla,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key=f"editor_registro_{fecha_str}"
    )
    
    _mostrar_estadisticas_registro(edited_df)
    
    if st.button("💾 Guardar Registro Diario", type="primary", use_container_width=True):
        _guardar_registro_diario(edited_df, fecha_str, registro_llamadas)


def _mostrar_estadisticas_registro(edited_df):
    """Muestra estadísticas del registro diario"""
    total_llamadas_totales = edited_df['Llamadas Totales'].sum()
    total_llamadas_15min = edited_df['Llamadas >15min'].sum()
    total_ventas = edited_df['Ventas'].sum()
    
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    with col_stats1:
        st.metric("Total Agentes", len(edited_df))
    with col_stats2:
        st.metric("Llamadas Totales", int(total_llamadas_totales))
    with col_stats3:
        st.metric("Llamadas >15min", int(total_llamadas_15min))
    with col_stats4:
        st.metric("Ventas", int(total_ventas))
    
    if total_llamadas_totales > 0:
        porcentaje = (total_llamadas_15min / total_llamadas_totales * 100)
        st.info(f"📊 **{porcentaje:.1f}%** de las llamadas son >15min")


def _guardar_registro_diario(edited_df, fecha_str, registro_llamadas):
    """Guarda el registro diario en el sistema"""
    if fecha_str not in registro_llamadas:
        registro_llamadas[fecha_str] = {}
    
    for _, row in edited_df.iterrows():
        agent_id = row['ID']
        registro_llamadas[fecha_str][agent_id] = {
            'llamadas_totales': int(row['Llamadas Totales']),
            'llamadas_15min': int(row['Llamadas >15min']),
            'ventas': int(row['Ventas']),
            'fecha': fecha_str,
            'timestamp': datetime.now().isoformat()
        }
    
    guardar_registro_llamadas(registro_llamadas)
    st.success("✅ Registro diario guardado correctamente")
    st.rerun()


# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_media_llamadas_diarias(registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia=50):
    """Calcula la media de llamadas diarias excluyendo días con menos del mínimo"""
    llamadas_por_dia = []
    
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            total_llamadas_dia = sum(datos.get('llamadas', 0) for datos in datos_dia.values())
            
            if total_llamadas_dia >= minimo_llamadas_dia:
                llamadas_por_dia.append(total_llamadas_dia)
    
    if not llamadas_por_dia:
        return 0
    
    return sum(llamadas_por_dia) / len(llamadas_por_dia)


def calcular_media_llamadas_por_agente(agentes, registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia=50):
    """Calcula la media de llamadas por agente"""
    total_llamadas = 0
    total_agentes = 0
    
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            llamadas_agente = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        llamadas_agente += datos_dia[agent_id].get("llamadas", 0)
            
            total_llamadas += llamadas_agente
            total_agentes += 1
    
    return total_llamadas / total_agentes if total_agentes > 0 else 0


def filtrar_dias_validos(agente_id, registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia=50):
    """
    Filtra solo los días donde el agente superó el mínimo de llamadas
    
    Returns:
        dict: {fecha_str: {llamadas_totales: X, llamadas_15min: Y, ventas: Z}}
    """
    dias_validos = {}
    
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        if fecha_inicio <= fecha <= fecha_fin:
            if agente_id in datos_dia:
                datos_agente = datos_dia[agente_id]
                llamadas_dia = datos_agente.get('llamadas_totales', 0)
                
                if llamadas_dia >= minimo_llamadas_dia:
                    dias_validos[fecha_str] = {
                        'llamadas_totales': datos_agente.get('llamadas_totales', 0),
                        'llamadas_15min': datos_agente.get('llamadas_15min', 0),
                        'ventas': datos_agente.get('ventas', 0)
                    }
    
    return dias_validos


# ============================================================================
# MÉTRICAS MENSUALES - CON OBJETIVOS PERSONALIZADOS
# ============================================================================

def mostrar_metricas_mensuales(agentes, registro_llamadas, configuracion):
    """Muestra métricas mensuales de agentes CON OBJETIVOS SEPARADOS"""
    st.subheader("📊 Métricas Mensuales - Días Válidos (>X llamadas/día)")
    
    minimo_llamadas_dia = configuracion.get("minimo_llamadas_dia", 50)
    st.info(f"ℹ️ **Nota:** Solo se consideran días con ≥ {minimo_llamadas_dia} llamadas totales")
    
    col_periodo1, col_periodo2 = st.columns(2)
    
    with col_periodo1:
        periodo_tipo = configuracion.get("periodo_mensual", "calendario")
        if periodo_tipo == "calendario":
            fecha_inicio, fecha_fin = _obtener_periodo_calendario()
        else:
            fecha_inicio, fecha_fin = _obtener_periodo_rolling()
    
    with col_periodo2:
        _mostrar_configuracion_metricas_panel(configuracion, fecha_inicio, fecha_fin)
    
    st.write("### 📈 Cálculo con Días Válidos")
    
    datos_agentes, estadisticas = _calcular_metricas_dias_validos(
        agentes, registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia, configuracion
    )
    
    _mostrar_estadisticas_filtrado(estadisticas, minimo_llamadas_dia)
    
    if estadisticas['agentes_con_datos_validos'] == 0:
        st.warning(f"⚠️ No hay agentes con días válidos (≥ {minimo_llamadas_dia} llamadas/día) en el período seleccionado")
        return
    
    _mostrar_estadisticas_globales(estadisticas, configuracion)
    
    metricas_agentes = _calcular_metricas_individuales(
        datos_agentes, estadisticas, configuracion, agentes
    )
    
    if metricas_agentes:
        _mostrar_tabla_metricas(metricas_agentes, fecha_inicio, fecha_fin, minimo_llamadas_dia)
    else:
        st.info("No hay datos para el período seleccionado")


def _obtener_periodo_calendario():
    """Obtiene el período calendario seleccionado"""
    año_actual = datetime.now().year
    mes_actual = datetime.now().month
    
    col_anio, col_mes = st.columns(2)
    
    with col_anio:
        año_seleccionado = st.selectbox(
            "Año:",
            range(año_actual - 1, año_actual + 2),
            index=1,
            key="selector_anio_metricas"
        )
    
    with col_mes:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agusto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_seleccionado = st.selectbox("Mes:", meses, index=mes_actual - 1, key="selector_mes_metricas")
        mes_numero = meses.index(mes_seleccionado) + 1
    
    fecha_inicio = datetime(año_seleccionado, mes_numero, 1).date()
    fecha_fin = (fecha_inicio + relativedelta(months=1)) - timedelta(days=1)
    
    st.info(f"**Periodo:** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    return fecha_inicio, fecha_fin


def _obtener_periodo_rolling():
    """Obtiene el período rolling seleccionado"""
    dias_atras = st.number_input("Últimos N días:", min_value=7, max_value=90, value=30, key="dias_rolling")
    fecha_fin = datetime.now().date()
    fecha_inicio = fecha_fin - timedelta(days=dias_atras)
    
    st.info(f"**Periodo (rolling):** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    return fecha_inicio, fecha_fin


def _mostrar_configuracion_metricas_panel(configuracion, fecha_inicio, fecha_fin):
    """Muestra la configuración de métricas en el panel"""
    st.write("**Configuración:**")
    target_llamadas = configuracion.get('target_llamadas', 50)
    target_ventas_global = configuracion.get('target_ventas_global', 100)
    st.write(f"• Target llamadas >15min/agente: {target_llamadas}")
    st.write(f"• 🎯 Target ventas CAMPAÑA: {target_ventas_global}")
    st.write(f"• Mínimo llamadas/día: {configuracion.get('minimo_llamadas_dia', 50)}")
    
    total_dias_periodo = (fecha_fin - fecha_inicio).days + 1
    st.write(f"• Días en periodo: {total_dias_periodo}")


def _calcular_metricas_dias_validos(agentes, registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia, configuracion=None):
    """Calcula métricas considerando solo días válidos CON OBJETIVOS DESDE JSON"""
    datos_agentes = []
    total_llamadas_totales_periodo = 0
    total_llamadas_15min_periodo = 0
    total_ventas_periodo = 0
    total_objetivo_individual = 0  # Suma de objetivos individuales desde JSON
    agentes_con_datos_validos = 0
    total_dias_validos = 0
    agentes_sin_dias_validos = []
    
    # Cargar objetivos desde JSON
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    
    for agent_id, info in agentes.items():
        if not info.get('activo', True):
            continue
        
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        supervisor = info.get('supervisor', 'Sin asignar')
        
        dias_validos_agente = filtrar_dias_validos(
            agent_id, registro_llamadas, fecha_inicio, fecha_fin, minimo_llamadas_dia
        )
        
        if not dias_validos_agente:
            agentes_sin_dias_validos.append({
                'id': agent_id,
                'nombre': nombre,
                'dias_validos': 0
            })
            continue
        
        llamadas_totales_agente = 0
        llamadas_15min_agente = 0
        ventas_agente = 0
        
        for fecha_str, datos_dia in dias_validos_agente.items():
            llamadas_totales_agente += datos_dia['llamadas_totales']
            llamadas_15min_agente += datos_dia['llamadas_15min']
            ventas_agente += datos_dia['ventas']
        
        dias_con_datos = len(dias_validos_agente)
        
        total_llamadas_totales_periodo += llamadas_totales_agente
        total_llamadas_15min_periodo += llamadas_15min_agente
        total_ventas_periodo += ventas_agente
        total_dias_validos += dias_con_datos
        agentes_con_datos_validos += 1
        
        # Obtener objetivo INDIVIDUAL desde JSON
        objetivo_individual = objetivos_dict.get(agent_id, 10)
        total_objetivo_individual += objetivo_individual
        
        datos_agentes.append({
            'agent_id': agent_id,
            'nombre': nombre,
            'grupo': grupo,
            'supervisor': supervisor,
            'objetivo_individual': objetivo_individual,
            'llamadas_totales': llamadas_totales_agente,
            'llamadas_15min': llamadas_15min_agente,
            'ventas': ventas_agente,
            'dias_validos': dias_con_datos,
            'dias_validos_list': list(dias_validos_agente.keys())
        })
    
    estadisticas = {
        'total_llamadas_totales_periodo': total_llamadas_totales_periodo,
        'total_llamadas_15min_periodo': total_llamadas_15min_periodo,
        'total_ventas_periodo': total_ventas_periodo,
        'total_objetivo_individual': total_objetivo_individual,
        'agentes_con_datos_validos': agentes_con_datos_validos,
        'total_dias_validos': total_dias_validos,
        'agentes_sin_dias_validos': agentes_sin_dias_validos,
        'total_agentes': len(agentes)
    }
    
    return datos_agentes, estadisticas


def _mostrar_estadisticas_filtrado(estadisticas, minimo_llamadas_dia):
    """Muestra estadísticas del filtrado por días válidos"""
    col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
    
    with col_stats1:
        st.metric("Agentes Activos", estadisticas['total_agentes'])
    
    with col_stats2:
        st.metric("Con días válidos", estadisticas['agentes_con_datos_validos'])
    
    with col_stats3:
        st.metric("Sin días válidos", len(estadisticas['agentes_sin_dias_validos']))
    
    with col_stats4:
        st.metric("Total días válidos", estadisticas['total_dias_validos'])
    
    if estadisticas['agentes_sin_dias_validos']:
        with st.expander(f"👀 Ver {len(estadisticas['agentes_sin_dias_validos'])} agentes sin días válidos (menos de {minimo_llamadas_dia} llamadas/día)"):
            for agente in estadisticas['agentes_sin_dias_validos'][:20]:
                st.write(f"- **{agente['id']}** ({agente['nombre']}): {agente['dias_validos']} días válidos")


def _mostrar_estadisticas_globales(estadisticas, configuracion):
    """Muestra estadísticas globales de métricas CON OBJETIVOS SEPARADOS"""
    # Calcular medias globales
    media_llamadas_totales = estadisticas['total_llamadas_totales_periodo'] / estadisticas['agentes_con_datos_validos']
    media_llamadas_15min = estadisticas['total_llamadas_15min_periodo'] / estadisticas['agentes_con_datos_validos']
    
    porcentaje_global_15min = (
        (estadisticas['total_llamadas_15min_periodo'] / estadisticas['total_llamadas_totales_periodo'] * 100) 
        if estadisticas['total_llamadas_totales_periodo'] > 0 else 0
    )
    
    media_dias_validos = estadisticas['total_dias_validos'] / estadisticas['agentes_con_datos_validos']
    
    # 🎯 OBJETIVOS DIFERENCIADOS
    target_global_campana = configuracion.get('target_ventas_global', 100) if configuracion else 100
    total_objetivo_individual = estadisticas['total_objetivo_individual']
    total_ventas = estadisticas['total_ventas_periodo']
    
    # Progreso vs objetivos
    progreso_vs_global = (total_ventas / target_global_campana * 100) if target_global_campana > 0 else 0
    progreso_vs_individual = (total_ventas / total_objetivo_individual * 100) if total_objetivo_individual > 0 else 0
    
    st.write("### 📊 Estadísticas Globales (Solo Días Válidos)")
    
    col_glob1, col_glob2, col_glob3, col_glob4 = st.columns(4)
    
    with col_glob1:
        st.metric("📅 Días válidos/agente", f"{media_dias_validos:.1f}")
    
    with col_glob2:
        st.metric("📞 Media Totales/agente", f"{media_llamadas_totales:.1f}")
    
    with col_glob3:
        st.metric("⏱️ Media >15min/agente", f"{media_llamadas_15min:.1f}")
    
    with col_glob4:
        st.metric("📊 % Eficiencia global", f"{porcentaje_global_15min:.1f}%")
    
    # 🎯 SECCIÓN DE OBJETIVOS
    st.write("### 🎯 Progreso vs Objetivos")
    
    col_obj1, col_obj2 = st.columns(2)
    
    with col_obj1:
        st.metric("🎯 vs Objetivo Campaña", f"{total_ventas}/{target_global_campana}")
        st.caption(f"{progreso_vs_global:.1f}%")
        ventas_restantes_global = max(0, target_global_campana - total_ventas)
        st.caption(f"Faltan: {ventas_restantes_global}")
    
    with col_obj2:
        st.metric("📊 vs Objetivos Individuales", f"{total_ventas}/{total_objetivo_individual}")
        st.caption(f"{progreso_vs_individual:.1f}%")
        ventas_restantes_individual = max(0, total_objetivo_individual - total_ventas)
        st.caption(f"Faltan: {ventas_restantes_individual}")


def _calcular_metricas_individuales(datos_agentes, estadisticas, configuracion, agentes):
    """Calcula métricas individuales para cada agente CON OBJETIVOS DESDE JSON"""
    metricas_agentes = []
    
    # 🎯 OBJETIVOS DIFERENCIADOS
    target_llamadas = configuracion.get('target_llamadas', 50)
    target_ventas_global = configuracion.get('target_ventas_global', 100)
    
    for datos in datos_agentes:
        agent_id = datos['agent_id']
        info_agente = agentes.get(agent_id, {})
        
        # Obtener objetivo individual desde datos (ya cargado desde JSON)
        objetivo_individual = datos.get('objetivo_individual', 10)
        
        llamadas_totales = datos['llamadas_totales']
        llamadas_15min = datos['llamadas_15min']
        ventas = datos['ventas']
        dias_validos = datos['dias_validos']
        
        # Promedios diarios
        llamadas_diarias_promedio = llamadas_totales / dias_validos if dias_validos > 0 else 0
        llamadas_15min_diarias_promedio = llamadas_15min / dias_validos if dias_validos > 0 else 0
        
        # Porcentajes
        porcentaje_15min = (llamadas_15min / llamadas_totales * 100) if llamadas_totales > 0 else 0
        
        # Cumplimiento CON OBJETIVOS DIFERENCIADOS
        cumplimiento_llamadas = (llamadas_15min / target_llamadas * 100) if target_llamadas > 0 else 0
        cumplimiento_ventas_individual = (ventas / objetivo_individual * 100) if objetivo_individual > 0 else 0
        
        # Contribución al objetivo global
        contribucion_global = (ventas / target_ventas_global * 100) if target_ventas_global > 0 else 0
        
        # Ratio y eficiencia
        ratio_conversion = (ventas / llamadas_15min * 100) if llamadas_15min > 0 else 0
        
        metrica_tipo = configuracion.get("metrica_eficiencia", "ratio")
        if metrica_tipo == "ratio":
            eficiencia = ratio_conversion
        elif metrica_tipo == "total":
            eficiencia = ventas * 10 + llamadas_15min
        elif metrica_tipo == "ponderado":
            eficiencia = ventas * 2 + llamadas_15min
        
        # Estados
        estado_general = '✅' if cumplimiento_llamadas >= 100 and cumplimiento_ventas_individual >= 100 else '⚠️'
        
        metricas_agentes.append({
            'ID': datos['agent_id'],
            'Agente': datos['nombre'],
            'Grupo': datos['grupo'],
            'Supervisor': datos['supervisor'],
            'Objetivo Individual': objetivo_individual,
            'Días Válidos': dias_validos,
            'Llamadas Totales': llamadas_totales,
            'Llamadas >15min': llamadas_15min,
            'Ventas': ventas,
            'Llamadas/Día': f"{llamadas_diarias_promedio:.1f}",
            '>15min/Día': f"{llamadas_15min_diarias_promedio:.1f}",
            '% >15min': f"{porcentaje_15min:.1f}%",
            'Cump. Llamadas (%)': f"{cumplimiento_llamadas:.1f}%",
            'Cump. Ventas Ind. (%)': f"{cumplimiento_ventas_individual:.1f}%",
            'Contrib. Global (%)': f"{contribucion_global:.1f}%",
            'Ventas Restantes': max(0, objetivo_individual - ventas),
            'Ratio (%)': f"{ratio_conversion:.1f}%",
            'Eficiencia': f"{eficiencia:.1f}",
            'Estado': estado_general,
            '_dias_validos': dias_validos,
            '_llamadas_totales': llamadas_totales,
            '_llamadas_15min': llamadas_15min,
            '_ventas': ventas,
            '_objetivo_individual': objetivo_individual,
            '_porcentaje_15min': porcentaje_15min,
            '_ratio': ratio_conversion,
            '_eficiencia': eficiencia
        })
    
    return metricas_agentes


def _mostrar_tabla_metricas(metricas_agentes, fecha_inicio, fecha_fin, minimo_llamadas_dia):
    """Muestra la tabla de métricas con opciones de ordenación"""
    df_metricas = pd.DataFrame(metricas_agentes)
    df_metricas = df_metricas.sort_values('ID')
    
    col_orden1, col_orden2 = st.columns([2, 1])
    with col_orden1:
        orden_seleccionado = st.selectbox(
            "Ordenar por:",
            [
                'ID', 
                'Agente',
                'Días Válidos',
                'Llamadas Totales', 
                'Llamadas >15min', 
                'Ventas', 
                'Objetivo Ventas',
                'Ventas Restantes',
                '% >15min', 
                'Cump. Ventas (%)',
                'Ratio (%)',
                'Eficiencia'
            ],
            key="orden_metricas"
        )
    
    orden_mapping = {
        'ID': 'ID',
        'Agente': 'Agente',
        'Días Válidos': '_dias_validos',
        'Llamadas Totales': '_llamadas_totales',
        'Llamadas >15min': '_llamadas_15min',
        'Ventas': '_ventas',
        'Objetivo Ventas': '_objetivo_individual',
        'Ventas Restantes': lambda x: x['_objetivo_individual'] - x['_ventas'],
        '% >15min': '_porcentaje_15min',
        'Cump. Ventas (%)': lambda x: (x['_ventas'] / x['_objetivo_individual'] * 100) if x['_objetivo_individual'] > 0 else 0,
        'Ratio (%)': '_ratio',
        'Eficiencia': '_eficiencia'
    }
    
    if orden_seleccionado in orden_mapping:
        if callable(orden_mapping[orden_seleccionado]):
            df_metricas['_temp_sort'] = df_metricas.apply(orden_mapping[orden_seleccionado], axis=1)
            df_metricas = df_metricas.sort_values('_temp_sort', ascending=False)
            df_metricas = df_metricas.drop('_temp_sort', axis=1)
        else:
            col_orden = orden_mapping[orden_seleccionado]
            if orden_seleccionado in ['Llamadas Totales', 'Llamadas >15min', 'Ventas', 'Días Válidos', 'Objetivo Ventas']:
                df_metricas = df_metricas.sort_values(col_orden, ascending=False)
            else:
                df_metricas = df_metricas.sort_values(col_orden, ascending=False)
    
    st.dataframe(df_metricas.drop(columns=['_dias_validos', '_llamadas_totales', '_llamadas_15min', 
                                         '_ventas', '_objetivo_individual', '_porcentaje_15min', 
                                         '_ratio', '_eficiencia']), 
                use_container_width=True)
    
    _mostrar_opciones_exportacion(df_metricas, fecha_inicio, fecha_fin, minimo_llamadas_dia)


def _mostrar_opciones_exportacion(df_metricas, fecha_inicio, fecha_fin, minimo_llamadas_dia):
    """Muestra opciones de exportación y visualización"""
    col_export1, col_export2 = st.columns(2)
    with col_export1:
        csv = df_metricas.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"metricas_{fecha_inicio}_{fecha_fin}_min{minimo_llamadas_dia}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_export2:
        if st.button("📊 Generar Gráficos", use_container_width=True):
            st.session_state.mostrar_graficos = True
            st.rerun()
    
    if st.session_state.get('mostrar_graficos', False):
        mostrar_graficos_metricas(df_metricas)


# ============================================================================
# DASHBOARD - MODIFICADO CON OBJETIVOS DE VENTAS
# ============================================================================

def mostrar_dashboard(agentes, registro_llamadas, configuracion):
    """Dashboard interactivo de métricas CON OBJETIVOS DE VENTAS"""
    st.subheader("📈 Dashboard de Desempeño")
    
    username = st.session_state.get('username', '')
    st.info(f"👑 **Supervisor:** {username} | 👥 **Agentes supervisados:** {len(agentes)}")
    
    col_periodo1, col_periodo2 = st.columns(2)
    
    with col_periodo1:
        periodo = st.selectbox(
            "Periodo del dashboard:",
            ["Este mes", "Últimos 7 días", "Últimos 30 días", "Personalizado"],
            key="periodo_dashboard"
        )
    
    fecha_hoy = datetime.now().date()
    
    if periodo == "Este mes":
        fecha_inicio = fecha_hoy.replace(day=1)
        fecha_fin = fecha_hoy
    elif periodo == "Últimos 7 días":
        fecha_inicio = fecha_hoy - timedelta(days=7)
        fecha_fin = fecha_hoy
    elif periodo == "Últimos 30 días":
        fecha_inicio = fecha_hoy - timedelta(days=30)
        fecha_fin = fecha_hoy
    else:
        col_fecha1, col_fecha2 = st.columns(2)
        with col_fecha1:
            fecha_inicio = st.date_input("Fecha inicio", value=fecha_hoy - timedelta(days=30))
        with col_fecha2:
            fecha_fin = st.date_input("Fecha fin", value=fecha_hoy)
    
    _mostrar_kpis_dashboard(agentes, registro_llamadas, fecha_inicio, fecha_fin, configuracion)
    _mostrar_tendencia_diaria(agentes, registro_llamadas, fecha_inicio, fecha_fin)
    _mostrar_ranking_agentes(agentes, registro_llamadas, fecha_inicio, fecha_fin, configuracion)
    _mostrar_comparacion_llamadas(agentes, registro_llamadas, fecha_inicio, fecha_fin)


def _mostrar_kpis_dashboard(agentes, registro_llamadas, fecha_inicio, fecha_fin, configuracion):
    """Muestra los KPIs del dashboard CON OBJETIVOS INDIVIDUALES DESDE JSON"""
    st.write("### 📊 Métricas Globales")
    
    total_llamadas_15min = 0
    total_llamadas_totales = 0
    total_ventas = 0
    total_objetivo_individual = 0  # Suma de objetivos individuales desde JSON
    agentes_activos = sum(1 for a in agentes.values() if a.get('activo', True))
    
    # Cargar objetivos individuales desde JSON
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            for agent_id, datos_agente in datos_dia.items():
                if agent_id in agentes:
                    total_llamadas_15min += datos_agente.get("llamadas_15min", 0)
                    total_llamadas_totales += datos_agente.get("llamadas_totales", 0)
                    total_ventas += datos_agente.get("ventas", 0)
    
    # 🎯 OBJETIVOS DIFERENCIADOS
    target_global_campana = configuracion.get('target_ventas_global', 100) if configuracion else 100
    
    # Calcular objetivo total individual (suma de objetivos personales desde JSON)
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            # Obtener objetivo desde JSON, si no existe usar 10 por defecto
            objetivo_individual = objetivos_dict.get(agent_id, 10)
            total_objetivo_individual += objetivo_individual
    
    # Cálculos de métricas
    media_llamadas_agente_15min = total_llamadas_15min / len(agentes) if agentes else 0
    porcentaje_15min = (total_llamadas_15min / total_llamadas_totales * 100) if total_llamadas_totales > 0 else 0
    ratio = (total_ventas / total_llamadas_15min * 100) if total_llamadas_15min > 0 else 0
    
    # 🎯 PROGRESO vs OBJETIVO GLOBAL DE CAMPAÑA
    progreso_vs_global = (total_ventas / target_global_campana * 100) if target_global_campana > 0 else 0
    ventas_restantes_global = max(0, target_global_campana - total_ventas)
    
    # 📊 PROGRESO vs OBJETIVOS INDIVIDUALES SUMADOS
    progreso_vs_individual = (total_ventas / total_objetivo_individual * 100) if total_objetivo_individual > 0 else 0
    ventas_restantes_individual = max(0, total_objetivo_individual - total_ventas)
    
    # Mostrar KPIs
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    
    with col_kpi1:
        st.metric("👥 Agentes Activos", agentes_activos)
        st.caption(f"Target llamadas/agente: {configuracion.get('target_llamadas', 50) if configuracion else 50}")
    
    with col_kpi2:
        st.metric("📞 Llamadas >15min", total_llamadas_15min)
        st.caption(f"({total_llamadas_totales} totales)")
    
    with col_kpi3:
        # 🎯 OBJETIVO GLOBAL DE CAMPAÑA
        st.metric("🎯 Ventas / Obj. Campaña", f"{total_ventas} / {target_global_campana}")
        st.caption(f"{progreso_vs_global:.1f}% - Faltan: {ventas_restantes_global}")
    
    with col_kpi4:
        # 📊 OBJETIVOS INDIVIDUALES SUMADOS DESDE JSON
        st.metric("📊 Ventas / Obj. Individual", f"{total_ventas} / {total_objetivo_individual}")
        st.caption(f"{progreso_vs_individual:.1f}% - Faltan: {ventas_restantes_individual}")
    
    with col_kpi5:
        st.metric("📈 Ratio Conversión", f"{ratio:.1f}%")
        st.caption(f"{porcentaje_15min:.1f}% llamadas >15min")
    
    # 🎯 BARRAS DE PROGRESO DIFERENCIADAS
    st.write("### 📊 Progreso de Ventas")
    
    col_prog1, col_prog2 = st.columns(2)
    
    with col_prog1:
        # Progreso vs Objetivo Global de Campaña
        st.write("**🎯 vs Objetivo Campaña**")
        progreso_global = min(progreso_vs_global / 100, 1.0)
        st.progress(progreso_global)
        
        if progreso_vs_global < 50:
            color_global = "red"
        elif progreso_vs_global < 80:
            color_global = "orange"
        else:
            color_global = "green"
        
        st.markdown(f"""
        <div style="text-align: center;">
            <span style="color: {color_global}; font-weight: bold;">{progreso_vs_global:.1f}%</span> 
            ({total_ventas} de {target_global_campana} ventas)
        </div>
        """, unsafe_allow_html=True)
        
        # Promedio por agente para alcanzar objetivo global
        if agentes_activos > 0:
            promedio_necesario = ventas_restantes_global / agentes_activos
            st.caption(f"📊 Cada agente debe vender: {promedio_necesario:.1f} más")
    
    with col_prog2:
        # Progreso vs Objetivos Individuales Sumados DESDE JSON
        st.write("**📊 vs Objetivos Individuales**")
        progreso_individual = min(progreso_vs_individual / 100, 1.0)
        st.progress(progreso_individual)
        
        if progreso_vs_individual < 50:
            color_individual = "red"
        elif progreso_vs_individual < 80:
            color_individual = "orange"
        else:
            color_individual = "green"
        
        st.markdown(f"""
        <div style="text-align: center;">
            <span style="color: {color_individual}; font-weight: bold;">{progreso_vs_individual:.1f}%</span> 
            ({total_ventas} de {total_objetivo_individual} ventas)
        </div>
        """, unsafe_allow_html=True)
        
        # Información sobre objetivos individuales
        objetivo_promedio = total_objetivo_individual / len(agentes) if agentes else 0
        st.caption(f"📋 {len(agentes)} agentes | Obj. promedio: {objetivo_promedio:.1f}")


def _mostrar_tendencia_diaria(agentes, registro_llamadas, fecha_inicio, fecha_fin):
    """Muestra la tendencia diaria de llamadas"""
    st.write("### 📅 Tendencia Diaria (Llamadas >15min)")
    
    fechas = []
    llamadas_diarias_15min = []
    ventas_diarias = []
    
    for fecha_str in sorted(registro_llamadas.keys()):
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            total_dia_llamadas_15min = 0
            total_dia_ventas = 0
            
            for agent_id, datos_agente in registro_llamadas[fecha_str].items():
                if agent_id in agentes:
                    total_dia_llamadas_15min += datos_agente.get("llamadas_15min", 0)
                    total_dia_ventas += datos_agente.get("ventas", 0)
            
            fechas.append(fecha.strftime("%d/%m"))
            llamadas_diarias_15min.append(total_dia_llamadas_15min)
            ventas_diarias.append(total_dia_ventas)
    
    if fechas:
        df_tendencia = pd.DataFrame({
            'Fecha': fechas,
            'Llamadas >15min': llamadas_diarias_15min,
            'Ventas': ventas_diarias
        })
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_tendencia['Fecha'],
            y=df_tendencia['Llamadas >15min'],
            mode='lines+markers',
            name='Llamadas >15min',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=df_tendencia['Fecha'],
            y=df_tendencia['Ventas'],
            mode='lines+markers',
            name='Ventas',
            line=dict(color='green', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Tendencia Diaria - Llamadas >15min',
            xaxis_title='Fecha',
            yaxis_title='Llamadas >15min',
            yaxis2=dict(
                title='Ventas',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de tendencia para el período seleccionado")


def _mostrar_ranking_agentes(agentes, registro_llamadas, fecha_inicio, fecha_fin, configuracion):
    """Muestra el ranking de agentes CON OBJETIVOS INDIVIDUALES DESDE JSON"""
    st.write("### 🏆 Ranking de Agentes (Basado en Llamadas >15min)")
    
    ranking_data = []
    total_llamadas_15min = 0
    agentes_contados = 0
    
    # Cargar objetivos individuales desde JSON
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    
    # Primero calcular la media de llamadas >15min
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            for agent_id, datos_agente in datos_dia.items():
                if agent_id in agentes:
                    total_llamadas_15min += datos_agente.get("llamadas_15min", 0)
                    agentes_contados += 1
    
    media_llamadas_agente_15min = total_llamadas_15min / max(agentes_contados, 1)
    
    # Ahora calcular ranking individual
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            nombre = info.get('nombre', agent_id)
            
            llamadas_periodo_15min = 0
            ventas_periodo = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        llamadas_periodo_15min += datos_dia[agent_id].get("llamadas_15min", 0)
                        ventas_periodo += datos_dia[agent_id].get("ventas", 0)
            
            if llamadas_periodo_15min > 0:
                ratio = (ventas_periodo / llamadas_periodo_15min * 100)
                diferencia_media = 0
                
                if media_llamadas_agente_15min > 0:
                    diferencia_media = ((llamadas_periodo_15min - media_llamadas_agente_15min) / media_llamadas_agente_15min * 100)
                
                umbral_alerta = configuracion.get("umbral_alertas_llamadas", 20)
                estado_media = ""
                if diferencia_media < -umbral_alerta:
                    estado_media = "⚠️"
                elif diferencia_media > 0:
                    estado_media = "✅"
                else:
                    estado_media = "➖"
                
                # Obtener objetivo individual desde JSON
                objetivo_agente = objetivos_dict.get(agent_id, 10)
                ventas_restantes = max(0, objetivo_agente - ventas_periodo)
                
                # Calcular cumplimiento del objetivo individual
                cumplimiento_objetivo = (ventas_periodo / objetivo_agente * 100) if objetivo_agente > 0 else 0
                
                ranking_data.append({
                    'ID': agent_id,
                    'Agente': nombre,
                    'Llamadas >15min': llamadas_periodo_15min,
                    'Ventas': ventas_periodo,
                    'Objetivo': objetivo_agente,
                    'Cump. Objetivo': f"{cumplimiento_objetivo:.1f}%",
                    'Ventas Restantes': ventas_restantes,
                    'Ratio': f"{ratio:.1f}%",
                    'vs Media': f"{diferencia_media:.1f}%",
                    'Estado': estado_media,
                    'Puntos': ventas_periodo * 10 + llamadas_periodo_15min
                })
    
    if ranking_data:
        df_ranking = pd.DataFrame(ranking_data)
        df_ranking = df_ranking.sort_values('Puntos', ascending=False)
        
        st.write("**Top 10 Agentes:**")
        st.dataframe(df_ranking.head(10), use_container_width=True)
        
        # Mostrar agentes que superan su objetivo individual
        agentes_superan_objetivo = df_ranking[df_ranking['Cump. Objetivo'].apply(lambda x: float(x.replace('%', '')) >= 100)]
        if not agentes_superan_objetivo.empty:
            st.success("### 🎉 Agentes que Superan su Objetivo Individual")
            st.write("Estos agentes ya han alcanzado o superado su objetivo personal:")
            st.dataframe(agentes_superan_objetivo[['ID', 'Agente', 'Ventas', 'Objetivo', 'Cump. Objetivo']], 
                        use_container_width=True)
        
        agentes_alerta = df_ranking[df_ranking['Estado'] == '⚠️']
        if not agentes_alerta.empty:
            st.warning("### 🔔 Agentes Necesitan Atención (vs Media de >15min)")
            st.write("Estos agentes están por debajo del umbral de alerta en llamadas >15min:")
            st.dataframe(agentes_alerta[['ID', 'Agente', 'Llamadas >15min', 'vs Media']], use_container_width=True)
    else:
        st.info("No hay datos de ranking para el período seleccionado")


def _mostrar_comparacion_llamadas(agentes, registro_llamadas, fecha_inicio, fecha_fin):
    """Muestra comparación entre llamadas totales y >15min"""
    st.write("### 📊 Comparación: Llamadas Totales vs >15min")
    
    comparacion_data = []
    
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            nombre = info.get('nombre', agent_id)
            
            llamadas_totales_periodo = 0
            llamadas_15min_periodo = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        llamadas_totales_periodo += datos_dia[agent_id].get("llamadas_totales", 0)
                        llamadas_15min_periodo += datos_dia[agent_id].get("llamadas_15min", 0)
            
            if llamadas_totales_periodo > 0:
                porcentaje = (llamadas_15min_periodo / llamadas_totales_periodo * 100)
                
                comparacion_data.append({
                    'Agente': nombre,
                    'Llamadas Totales': llamadas_totales_periodo,
                    'Llamadas >15min': llamadas_15min_periodo,
                    '% >15min': f"{porcentaje:.1f}%"
                })
    
    if comparacion_data:
        df_comparacion = pd.DataFrame(comparacion_data)
        df_comparacion = df_comparacion.sort_values('% >15min')
        
        st.write("**Agentes con menor % de llamadas >15min:**")
        st.dataframe(df_comparacion.head(5), use_container_width=True)


# ============================================================================
# GESTIÓN DE AGENTES PARA SUPER USUARIOS
# ============================================================================

def gestion_agentes_super_usuario(agentes, super_users_config):
    """Gestión de agentes desde el panel de super usuario - VERSIÓN MEJORADA"""
    st.subheader("👥 Gestión de Mis Agentes")
    
    username = st.session_state.get('username', '')
    
    if username:
        st.info(f"👑 **Supervisor actual:** {username}")
    
    agentes_activos = sum(1 for a in agentes.values() if a.get('activo', True))
    agentes_inactivos = len(agentes) - agentes_activos
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("✅ Agentes Activos", agentes_activos)
    with col_stats2:
        st.metric("❌ Agentes Inactivos", agentes_inactivos)
    with col_stats3:
        # Contar agentes con monitorización reciente
        agentes_con_monitorizacion = contar_agentes_con_monitorizacion_reciente(agentes)
        st.metric("📊 Con Monitorización", agentes_con_monitorizacion)
    
    _mostrar_lista_agentes_mejorada(agentes, super_users_config, "supervisor")


def _mostrar_lista_agentes_mejorada(agentes, super_users_config, context=""):
    """Muestra lista mejorada de agentes con controles rápidos"""
    st.write("### 📋 Lista de Agentes")
    
    if not agentes:
        st.info("No hay agentes asignados a tu supervisión")
        return
    
    # Inicializar archivo de objetivos (asegurarse que existe)
    objetivos_data = inicializar_archivo_objetivos()
    
    # Si hay un error, mostrar mensaje
    if not objetivos_data:
        st.error("❌ No se pudo cargar el archivo de objetivos. Usando valores por defecto.")
        objetivos_dict = {}
    else:
        objetivos_dict = objetivos_data.get("objetivos", {})
    
    # Cargar información de monitorizaciones
    info_monitorizaciones = obtener_info_monitorizaciones_agentes(agentes.keys())
    
    # Crear tabla de datos con objetivos desde JSON
    datos_tabla = []
    
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        supervisor = info.get('supervisor', 'Sin asignar')
        activo = info.get('activo', True)
        
        # Obtener objetivo desde JSON, si no existe usar 10 por defecto
        objetivo_ventas = objetivos_dict.get(agent_id, 10)
        
        tipo = info.get('tipo', 'user')
        
        # Obtener info de monitorización
        mon_info = info_monitorizaciones.get(agent_id, {})
        icono_monitorizacion = mon_info.get('icono', '📭')
        tooltip_monitorizacion = mon_info.get('tooltip', 'Sin monitorización')
        fecha_monitorizacion = mon_info.get('fecha', '')
        nota_monitorizacion = mon_info.get('nota', 0)
        
        datos_tabla.append({
            'ID': agent_id,
            'Agente': nombre,
            'Grupo': grupo,
            'Tipo': tipo,
            'Estado': activo,
            'Objetivo Ventas': objetivo_ventas,  # Desde JSON
            'Monitorización': icono_monitorizacion,
            'Fecha Monitorización': fecha_monitorizacion,
            'Nota Monitorización': nota_monitorizacion,
            'Supervisor': supervisor,
            '_info_completa': info
        })
    
    # Crear DataFrame
    df_agentes = pd.DataFrame(datos_tabla)
    
    # Configurar columnas para el editor
    column_config = {
        'ID': st.column_config.TextColumn('ID', disabled=True),
        'Agente': st.column_config.TextColumn('Agente', disabled=True),
        'Grupo': st.column_config.TextColumn('Grupo', disabled=True),
        'Tipo': st.column_config.TextColumn('Tipo', disabled=True),
        'Estado': st.column_config.CheckboxColumn(
            'Activo',
            help="Activar/desactivar agente",
            default=True
        ),
        'Objetivo Ventas': st.column_config.NumberColumn(
            'Objetivo Ventas',
            min_value=0,
            max_value=500,
            step=1,
            help="Ventas objetivo mensuales - Edita y haz clic en Guardar",
            required=True
        ),
        'Monitorización': st.column_config.TextColumn(
            '📊',
            help="Última monitorización",
            disabled=True
        ),
        'Fecha Monitorización': st.column_config.TextColumn(
            'Fecha',
            disabled=True
        ),
        'Nota Monitorización': st.column_config.NumberColumn(
            'Nota',
            format="%.1f%%",
            disabled=True
        ),
        'Supervisor': st.column_config.TextColumn('Supervisor', disabled=True)
    }
    
    # Mostrar editor
    st.write("**📝 Edita el 'Objetivo Ventas' directamente y haz clic en 'Guardar Cambios':**")
    
    edited_df = st.data_editor(
        df_agentes,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key=f"editor_lista_agentes_{context}"
    )
    
    # Botones de acción
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True, 
                    key=f"btn_guardar_{context}"):
            _guardar_objetivos_desde_tabla(edited_df, context)
    
    with col_btn2:
        if st.button("📊 Ver Detalles Completos", type="secondary", use_container_width=True,
                    key=f"btn_detalles_{context}"):
            st.session_state.mostrar_detalles_agentes = True
            st.rerun()
    
    with col_btn3:
        if st.button("⚙️ Gestionar Objetivos", type="secondary", use_container_width=True,
                    key=f"btn_gestion_objetivos_{context}"):
            st.session_state.mostrar_gestion_objetivos = True
            st.rerun()
    
    # Mostrar gestión de objetivos si se solicita
    if st.session_state.get('mostrar_gestion_objetivos', False):
        _mostrar_gestion_objetivos_avanzada(agentes, context)
    
    # Mostrar detalles si se solicita
    if st.session_state.get('mostrar_detalles_agentes', False):
        _mostrar_detalles_completos_agentes(agentes, objetivos_dict)


def _guardar_objetivos_desde_tabla(edited_df, context):
    """Guarda los objetivos editados en la tabla al archivo JSON"""
    cambios_realizados = False
    objetivos_a_actualizar = {}
    cambios_detallados = []
    
    username = st.session_state.get('username', 'sistema')
    
    # Cargar objetivos actuales para comparar
    objetivos_actuales = cargar_objetivos_ventas()
    objetivos_dict = objetivos_actuales.get("objetivos", {})
    
    for _, row in edited_df.iterrows():
        agent_id = row['ID']
        nuevo_objetivo = int(row['Objetivo Ventas'])
        
        # Obtener objetivo anterior
        objetivo_anterior = objetivos_dict.get(agent_id, 10)
        
        # Verificar si hay cambio
        if nuevo_objetivo != objetivo_anterior:
            objetivos_a_actualizar[agent_id] = nuevo_objetivo
            cambios_detallados.append(f"**{agent_id}**: {objetivo_anterior} → {nuevo_objetivo}")
            cambios_realizados = True
    
    if cambios_realizados:
        # Actualizar múltiples objetivos
        if actualizar_multiples_objetivos(objetivos_a_actualizar, username):
            st.success(f"✅ {len(objetivos_a_actualizar)} objetivos actualizados correctamente")
            
            with st.expander("📋 Ver cambios realizados", expanded=True):
                for detalle in cambios_detallados:
                    st.write(detalle)
            
            # Forzar recarga
            st.rerun()
        else:
            st.error("❌ Error al guardar los objetivos")
    else:
        st.info("ℹ️ No se realizaron cambios en los objetivos")


def _mostrar_gestion_objetivos_avanzada(agentes, context):
    """Muestra panel avanzado para gestión de objetivos"""
    st.write("### ⚙️ Gestión Avanzada de Objetivos")
    
    # Cargar datos
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    
    # Estadísticas
    total_agentes = len(agentes)
    agentes_con_objetivo = len([a for a in agentes.keys() if a in objetivos_dict])
    objetivo_promedio = sum(objetivos_dict.values()) / len(objetivos_dict) if objetivos_dict else 0
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Agentes", total_agentes)
    with col_stats2:
        st.metric("Con objetivo", agentes_con_objetivo)
    with col_stats3:
        st.metric("Promedio", f"{objetivo_promedio:.1f}")
    
    # Tabla para edición masiva
    st.write("#### 📊 Edición Masiva de Objetivos")
    
    datos_masivos = []
    for agent_id, info in agentes.items():
        datos_masivos.append({
            'ID': agent_id,
            'Agente': info.get('nombre', agent_id),
            'Grupo': info.get('grupo', 'Sin grupo'),
            'Objetivo Actual': objetivos_dict.get(agent_id, 10),
            'Nuevo Objetivo': objetivos_dict.get(agent_id, 10)  # Editable
        })
    
    df_masivo = pd.DataFrame(datos_masivos)
    
    # Editor masivo
    edited_masivo = st.data_editor(
        df_masivo,
        column_config={
            'ID': st.column_config.TextColumn('ID', disabled=True),
            'Agente': st.column_config.TextColumn('Agente', disabled=True),
            'Grupo': st.column_config.TextColumn('Grupo', disabled=True),
            'Objetivo Actual': st.column_config.NumberColumn('Actual', disabled=True),
            'Nuevo Objetivo': st.column_config.NumberColumn(
                'Nuevo',
                min_value=0,
                max_value=500,
                step=1,
                help="Nuevo objetivo de ventas"
            )
        },
        hide_index=True,
        use_container_width=True,
        key=f"editor_masivo_objetivos_{context}"
    )
    
    # Aplicar cambios masivos
    if st.button("🚀 Aplicar Cambios Masivos", type="primary", use_container_width=True):
        cambios_masivos = {}
        for _, row in edited_masivo.iterrows():
            agent_id = row['ID']
            nuevo_objetivo = int(row['Nuevo Objetivo'])
            objetivo_actual = row['Objetivo Actual']
            
            if nuevo_objetivo != objetivo_actual:
                cambios_masivos[agent_id] = nuevo_objetivo
        
        if cambios_masivos:
            username = st.session_state.get('username', 'sistema')
            if actualizar_multiples_objetivos(cambios_masivos, username):
                st.success(f"✅ {len(cambios_masivos)} objetivos actualizados masivamente")
                st.rerun()
            else:
                st.error("❌ Error al actualizar objetivos")
        else:
            st.info("ℹ️ No hay cambios para aplicar")
    
    # Exportar/Importar
    st.write("#### 📥 Exportar/Importar Objetivos")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # Exportar a CSV
        if st.button("📤 Exportar a CSV", use_container_width=True):
            csv_data = df_masivo.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_data,
                file_name=f"objetivos_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col_exp2:
        # Importar desde CSV
        uploaded_file = st.file_uploader(
            "Subir CSV con objetivos",
            type=['csv'],
            key=f"upload_objetivos_{context}"
        )
        
        if uploaded_file is not None:
            try:
                df_importar = pd.read_csv(uploaded_file)
                st.write("**Vista previa:**")
                st.dataframe(df_importar.head(), use_container_width=True)
                
                if st.button("📥 Importar Objetivos", type="primary"):
                    # Procesar importación
                    cambios_importados = {}
                    for _, row in df_importar.iterrows():
                        if 'ID' in row and 'Nuevo Objetivo' in row:
                            agent_id = str(row['ID'])
                            nuevo_objetivo = int(row['Nuevo Objetivo'])
                            cambios_importados[agent_id] = nuevo_objetivo
                    
                    if cambios_importados:
                        username = st.session_state.get('username', 'sistema')
                        if actualizar_multiples_objetivos(cambios_importados, username):
                            st.success(f"✅ {len(cambios_importados)} objetivos importados")
                            st.rerun()
                        else:
                            st.error("❌ Error al importar objetivos")
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {e}")
    
    # Historial de cambios
    if objetivos_data.get("historico"):
        st.write("#### 📜 Historial de Cambios (Últimos 10)")
        
        historico_reciente = []
        for agent_id, cambios in objetivos_data["historico"].items():
            for cambio in cambios[-5:]:  # Últimos 5 por agente
                historico_reciente.append({
                    'Fecha': cambio.get('fecha', ''),
                    'Agente': agent_id,
                    'De': cambio.get('objetivo_anterior', 'N/A'),
                    'A': cambio.get('objetivo_nuevo', 'N/A'),
                    'Usuario': cambio.get('usuario', 'sistema')
                })
        
        if historico_reciente:
            # Ordenar por fecha más reciente
            historico_reciente.sort(key=lambda x: x['Fecha'], reverse=True)
            df_historico = pd.DataFrame(historico_reciente[:10])  # Solo 10 más recientes
            st.dataframe(df_historico, use_container_width=True)
    
    # Botón para volver
    if st.button("← Volver a lista", type="secondary", use_container_width=True):
        st.session_state.mostrar_gestion_objetivos = False
        st.rerun()


def obtener_info_monitorizaciones_agentes(agentes_ids):
    """Obtiene información de monitorizaciones para una lista de agentes"""
    try:
        from database import obtener_ultima_monitorizacion_empleado
        
        info_monitorizaciones = {}
        
        for agent_id in agentes_ids:
            ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
            
            if ultima_mon:
                fecha_mon = ultima_mon.get('fecha_monitorizacion', '')
                nota = ultima_mon.get('nota_global', 0)
                objetivo = ultima_mon.get('objetivo', 85)
                
                # Determinar icono según nota
                if nota >= objetivo:
                    icono = "✅"  # Cumple objetivo
                elif nota >= objetivo * 0.8:
                    icono = "⚠️"  # Cerca del objetivo
                else:
                    icono = "❌"  # Lejos del objetivo
                
                # Calcular días desde la monitorización
                try:
                    fecha_mon_dt = datetime.strptime(fecha_mon, '%Y-%m-%d')
                    dias_desde = (datetime.now() - fecha_mon_dt).days
                    
                    if dias_desde < 7:
                        icono = "🟢"  # Reciente (menos de 7 días)
                    elif dias_desde < 30:
                        icono = "🟡"  # Moderado (menos de 30 días)
                    else:
                        icono = "🔴"  # Antigua (más de 30 días)
                        
                except:
                    pass
                
                info_monitorizaciones[agent_id] = {
                    'icono': icono,
                    'tooltip': f"{fecha_mon} - Nota: {nota}% (Objetivo: {objetivo}%)",
                    'fecha': fecha_mon,
                    'nota': nota
                }
            else:
                info_monitorizaciones[agent_id] = {
                    'icono': '📭',
                    'tooltip': 'Sin monitorización',
                    'fecha': '',
                    'nota': 0
                }
        
        return info_monitorizaciones
        
    except ImportError:
        # Si no hay módulo de monitorizaciones, retornar datos vacíos
        return {agent_id: {'icono': '📭', 'tooltip': 'Módulo no disponible', 'fecha': '', 'nota': 0} 
                for agent_id in agentes_ids}


def contar_agentes_con_monitorizacion_reciente(agentes, dias_reciente=30):
    """Cuenta agentes con monitorización reciente"""
    try:
        from database import obtener_ultima_monitorizacion_empleado
        
        contador = 0
        
        for agent_id in agentes.keys():
            ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
            
            if ultima_mon and ultima_mon.get('fecha_monitorizacion'):
                try:
                    fecha_mon = datetime.strptime(ultima_mon['fecha_monitorizacion'], '%Y-%m-%d')
                    dias_desde = (datetime.now() - fecha_mon).days
                    
                    if dias_desde <= dias_reciente:
                        contador += 1
                except:
                    pass
        
        return contador
        
    except ImportError:
        return 0


def _mostrar_detalles_completos_agentes(agentes, objetivos_dict):
    """Muestra detalles completos de todos los agentes"""
    st.write("### 📊 Detalles Completos de Agentes")
    
    # Cargar objetivos
    if objetivos_dict is None:
        objetivos_data = cargar_objetivos_ventas()
        objetivos_dict = objetivos_data.get("objetivos", {})
    
    # Crear datos para tabla detallada
    datos_detallados = []
    
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        supervisor = info.get('supervisor', 'Sin asignar')
        activo = info.get('activo', True)
        
        # Obtener objetivo desde JSON
        objetivo_ventas = objetivos_dict.get(agent_id, 10)
        
        tipo = info.get('tipo', 'user')
        
        # Obtener ventas del mes actual
        registro_llamadas = cargar_registro_llamadas()
        fecha_inicio = datetime.now().date().replace(day=1)
        fecha_fin = datetime.now().date()
        
        ventas_mes = 0
        llamadas_mes = 0
        
        for fecha_str, datos_dia in registro_llamadas.items():
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_inicio <= fecha <= fecha_fin:
                if agent_id in datos_dia:
                    ventas_mes += datos_dia[agent_id].get("ventas", 0)
                    llamadas_mes += datos_dia[agent_id].get("llamadas_15min", 0)
        
        # Calcular progreso
        progreso = (ventas_mes / objetivo_ventas * 100) if objetivo_ventas > 0 else 0
        ventas_restantes = max(0, objetivo_ventas - ventas_mes)
        
        datos_detallados.append({
            'ID': agent_id,
            'Agente': nombre,
            'Estado': '✅ Activo' if activo else '❌ Inactivo',
            'Objetivo': objetivo_ventas,
            'Ventas Mes': ventas_mes,
            'Progreso': f"{progreso:.1f}%",
            'Faltan': ventas_restantes,
            'Llamadas >15min': llamadas_mes,
            'Grupo': grupo,
            'Tipo': tipo,
            'Supervisor': supervisor
        })
    
    df_detallado = pd.DataFrame(datos_detallados)
    
    # Ordenar por progreso (descendente)
    df_detallado = df_detallado.sort_values('Progreso', ascending=False, 
                                          key=lambda col: pd.to_numeric(col.str.replace('%', ''), errors='coerce'))
    
    st.dataframe(df_detallado, use_container_width=True)
    
    # Botón para volver
    if st.button("← Volver a lista simple", type="secondary"):
        st.session_state.mostrar_detalles_agentes = False
        st.rerun()


# ============================================================================
# EDICIÓN DE AGENTES PARA SUPER USUARIOS
# ============================================================================

def gestion_agentes_super_usuario_edicion(agentes, super_users_config, super_user_actual):
    """Gestión de agentes para super usuarios (edición limitada) - VERSIÓN MEJORADA"""
    st.subheader("🔧 Edición de Mis Agentes")
    
    agentes_asignados = {k: v for k, v in agentes.items() 
                        if v.get('supervisor', '') == super_user_actual}
    
    if not agentes_asignados:
        st.info(f"ℹ️ No tienes agentes asignados como supervisor. Los agentes asignados a ti aparecerán aquí.")
        return
    
    st.info(f"👑 **Supervisor:** {super_user_actual} | 👥 **Agentes asignados:** {len(agentes_asignados)}")
    
    # Usar la misma lista mejorada pero filtrada por supervisor
    agentes_filtrados = {k: v for k, v in agentes.items() 
                        if v.get('supervisor', '') == super_user_actual}
    
    # Reutilizar la función mejorada
    _mostrar_lista_agentes_mejorada(agentes_filtrados, super_users_config, "edicion")
    
    # Agregar opciones adicionales específicas para super usuarios
    st.write("---")
    st.write("### ⚙️ Opciones Adicionales")
    
    col_opc1, col_opc2 = st.columns(2)
    
    with col_opc1:
        if st.button("📤 Exportar Datos de Mis Agentes", use_container_width=True):
            exportar_datos_mis_agentes(agentes_asignados)
    
    with col_opc2:
        if st.button("📧 Enviar Recordatorio a Todos", use_container_width=True):
            st.info("Función de envío de recordatorios en desarrollo")


def exportar_datos_mis_agentes(agentes):
    """Exporta datos de los agentes del super usuario actual"""
    datos_exportar = []
    
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        activo = info.get('activo', True)
        objetivo_ventas = info.get('objetivo_ventas_mensual', 10)
        
        # Obtener ventas del mes
        registro_llamadas = cargar_registro_llamadas()
        fecha_inicio = datetime.now().date().replace(day=1)
        fecha_fin = datetime.now().date()
        
        ventas_mes = 0
        for fecha_str, datos_dia in registro_llamadas.items():
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_inicio <= fecha <= fecha_fin:
                if agent_id in datos_dia:
                    ventas_mes += datos_dia[agent_id].get("ventas", 0)
        
        datos_exportar.append({
            'ID': agent_id,
            'Nombre': nombre,
            'Grupo': grupo,
            'Estado': 'Activo' if activo else 'Inactivo',
            'Objetivo Ventas': objetivo_ventas,
            'Ventas Mes Actual': ventas_mes,
            'Progreso': f"{(ventas_mes / objetivo_ventas * 100) if objetivo_ventas > 0 else 0:.1f}%",
            'Ventas Restantes': max(0, objetivo_ventas - ventas_mes)
        })
    
    df_exportar = pd.DataFrame(datos_exportar)
    csv = df_exportar.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"mis_agentes_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


# ============================================================================
# GRÁFICOS DE MÉTRICAS
# ============================================================================

def mostrar_graficos_metricas(df_metricas):
    """Muestra gráficos de métricas - COMPLETA con ambos tipos de llamadas"""
    st.write("### 📊 Visualización de Datos")
    
    # Verificar columnas disponibles
    columnas_requeridas = ['Llamadas >15min', 'Llamadas Totales', 'Agente']
    for col in columnas_requeridas:
        if col not in df_metricas.columns:
            st.error(f"❌ Falta columna: {col}")
            st.write("Columnas disponibles:", df_metricas.columns.tolist())
            return
    
    # Crear columnas numéricas para gráficos
    df_metricas['Llamadas_15min_num'] = pd.to_numeric(df_metricas['Llamadas >15min'], errors='coerce')
    df_metricas['Llamadas_totales_num'] = pd.to_numeric(df_metricas['Llamadas Totales'], errors='coerce')
    
    # Crear columna de Ventas numérica si existe
    if 'Ventas' in df_metricas.columns:
        df_metricas['Ventas_num'] = pd.to_numeric(df_metricas['Ventas'], errors='coerce')
    
    # Crear columna de Objetivo numérica si existe
    columna_objetivo = None
    if 'Objetivo Individual' in df_metricas.columns:
        columna_objetivo = 'Objetivo Individual'
        df_metricas['Objetivo_num'] = pd.to_numeric(df_metricas['Objetivo Individual'], errors='coerce')
    elif 'Objetivo Ventas' in df_metricas.columns:
        columna_objetivo = 'Objetivo Ventas'
        df_metricas['Objetivo_num'] = pd.to_numeric(df_metricas['Objetivo Ventas'], errors='coerce')
    
    _mostrar_comparacion_llamadas_grafico(df_metricas)
    
    if 'Ventas' in df_metricas.columns and columna_objetivo:
        _mostrar_ventas_objetivo_grafico(df_metricas)
    
    _mostrar_porcentaje_15min_grafico(df_metricas)
    
    if 'Ventas' in df_metricas.columns:
        _mostrar_ventas_grafico(df_metricas)
    
    _mostrar_resumen_estadistico(df_metricas)
    _mostrar_tabla_resumen(df_metricas)


def _mostrar_comparacion_llamadas_grafico(df_metricas):
    """Muestra gráfico de comparación de llamadas"""
    st.write("#### 📞 Comparación: Llamadas Totales vs >15min")
    
    df_metricas['Llamadas_15min_num'] = pd.to_numeric(df_metricas['Llamadas >15min'], errors='coerce')
    df_metricas['Llamadas_totales_num'] = pd.to_numeric(df_metricas['Llamadas Totales'], errors='coerce')
    df_metricas['%_15min'] = (df_metricas['Llamadas_15min_num'] / df_metricas['Llamadas_totales_num'] * 100).round(1)
    
    fig_comparacion = go.Figure()
    
    fig_comparacion.add_trace(go.Bar(
        x=df_metricas['Agente'],
        y=df_metricas['Llamadas_totales_num'],
        name='Llamadas Totales',
        marker_color='lightblue',
        text=df_metricas['Llamadas Totales'],
        textposition='auto'
    ))
    
    fig_comparacion.add_trace(go.Bar(
        x=df_metricas['Agente'],
        y=df_metricas['Llamadas_15min_num'],
        name='Llamadas >15min',
        marker_color='orange',
        text=df_metricas['Llamadas >15min'],
        textposition='auto'
    ))
    
    for i, row in df_metricas.iterrows():
        fig_comparacion.add_annotation(
            x=row['Agente'],
            y=row['Llamadas_totales_num'] + max(df_metricas['Llamadas_totales_num']) * 0.02,
            text=f"{row['%_15min']:.1f}%",
            showarrow=False,
            font=dict(size=10)
        )
    
    fig_comparacion.update_layout(
        title='Comparación de Llamadas: Totales vs >15min',
        xaxis_title='Agente',
        yaxis_title='Número de Llamadas',
        barmode='group',
        xaxis_tickangle=-45,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_comparacion, use_container_width=True)


def _mostrar_ventas_objetivo_grafico(df_metricas):
    """Muestra gráfico de ventas vs objetivo - CORREGIDO"""
    # Verificar qué columnas de objetivo existen
    columna_objetivo = None
    if 'Objetivo Individual' in df_metricas.columns:
        columna_objetivo = 'Objetivo Individual'
    elif 'Objetivo Ventas' in df_metricas.columns:
        columna_objetivo = 'Objetivo Ventas'
    
    if 'Ventas' in df_metricas.columns and columna_objetivo:
        st.write("#### 🎯 Ventas vs Objetivo")
        
        df_metricas['Ventas_num'] = pd.to_numeric(df_metricas['Ventas'], errors='coerce')
        df_metricas['Objetivo_num'] = pd.to_numeric(df_metricas[columna_objetivo], errors='coerce')
        df_metricas['Progreso'] = (df_metricas['Ventas_num'] / df_metricas['Objetivo_num'] * 100).round(1)
        
        df_ventas_objetivo = df_metricas.sort_values('Progreso', ascending=False)
        
        fig_objetivo = go.Figure()
        
        fig_objetivo.add_trace(go.Bar(
            x=df_ventas_objetivo['Agente'],
            y=df_ventas_objetivo['Objetivo_num'],
            name='Objetivo',
            marker_color='lightgray',
            text=df_ventas_objetivo[columna_objetivo],
            textposition='auto'
        ))
        
        fig_objetivo.add_trace(go.Bar(
            x=df_ventas_objetivo['Agente'],
            y=df_ventas_objetivo['Ventas_num'],
            name='Ventas Actuales',
            marker_color='lightgreen',
            text=df_ventas_objetivo['Ventas'],
            textposition='auto'
        ))
        
        for i, row in df_ventas_objetivo.iterrows():
            fig_objetivo.add_annotation(
                x=row['Agente'],
                y=max(row['Objetivo_num'], row['Ventas_num']) + max(df_ventas_objetivo['Objetivo_num']) * 0.05,
                text=f"{row['Progreso']:.1f}%",
                showarrow=False,
                font=dict(size=10)
            )
        
        fig_objetivo.update_layout(
            title=f'Ventas vs Objetivo por Agente',
            xaxis_title='Agente',
            yaxis_title='Ventas',
            barmode='overlay',
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_objetivo, use_container_width=True)
        
        # Mostrar agentes que cumplen objetivo
        agentes_cumplen = df_metricas[df_metricas['Progreso'] >= 100]
        if not agentes_cumplen.empty:
            st.success(f"✅ {len(agentes_cumplen)} agentes cumplen o superan su objetivo")
            st.dataframe(agentes_cumplen[['Agente', 'Ventas', columna_objetivo, 'Progreso']], 
                        use_container_width=True)
    else:
        st.info("No hay datos de objetivos disponibles para graficar")
        if 'Ventas' not in df_metricas.columns:
            st.warning("Falta columna 'Ventas'")
        if 'Objetivo Individual' not in df_metricas.columns and 'Objetivo Ventas' not in df_metricas.columns:
            st.warning("Falta columna de objetivos")


def _mostrar_porcentaje_15min_grafico(df_metricas):
    """Muestra gráfico de porcentaje >15min"""
    st.write("#### 📊 Eficiencia: % Llamadas >15min")
    
    if '% >15min' not in df_metricas.columns:
        df_metricas['%_15min_calc'] = df_metricas['%_15min']
    else:
        df_metricas['%_15min_calc'] = pd.to_numeric(
            df_metricas['% >15min'].str.replace('%', ''), 
            errors='coerce'
        )
    
    df_porcentaje = df_metricas.sort_values('%_15min_calc', ascending=False)
    
    fig_porcentaje = go.Figure()
    
    colores_eficiencia = []
    for valor in df_porcentaje['%_15min_calc']:
        if pd.isna(valor):
            colores_eficiencia.append('gray')
        elif valor < 20:
            colores_eficiencia.append('red')
        elif valor < 40:
            colores_eficiencia.append('orange')
        elif valor < 60:
            colores_eficiencia.append('yellow')
        else:
            colores_eficiencia.append('green')
    
    fig_porcentaje.add_trace(go.Bar(
        x=df_porcentaje['Agente'],
        y=df_porcentaje['%_15min_calc'],
        name='% >15min',
        marker_color=colores_eficiencia,
        text=[f"{x:.1f}%" for x in df_porcentaje['%_15min_calc']],
        textposition='auto'
    ))
    
    fig_porcentaje.add_hline(y=30, line_dash="dot", line_color="orange", 
                           annotation_text="Umbral 30%", annotation_position="right")
    fig_porcentaje.add_hline(y=50, line_dash="dash", line_color="green", 
                           annotation_text="Objetivo 50%", annotation_position="right")
    
    fig_porcentaje.update_layout(
        title='Porcentaje de Llamadas >15min por Agente',
        xaxis_title='Agente',
        yaxis_title='Porcentaje %',
        yaxis=dict(ticksuffix='%', range=[0, 100]),
        xaxis_tickangle=-45
    )
    
    st.plotly_chart(fig_porcentaje, use_container_width=True)


def _mostrar_ventas_grafico(df_metricas):
    """Muestra gráfico de ventas"""
    if 'Ventas' in df_metricas.columns:
        st.write("#### 💰 Ventas por Agente")
        
        df_metricas['Ventas_num'] = pd.to_numeric(df_metricas['Ventas'], errors='coerce')
        df_ventas = df_metricas.sort_values('Ventas_num', ascending=False)
        
        fig_ventas = go.Figure()
        
        fig_ventas.add_trace(go.Bar(
            x=df_ventas['Agente'],
            y=df_ventas['Ventas_num'],
            name='Ventas',
            marker_color='lightgreen',
            text=df_ventas['Ventas'],
            textposition='auto'
        ))
        
        fig_ventas.update_layout(
            title='Ventas por Agente',
            xaxis_title='Agente',
            yaxis_title='Ventas',
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig_ventas, use_container_width=True)


def _mostrar_resumen_estadistico(df_metricas):
    """Muestra resumen estadístico - CORREGIDO"""
    st.write("#### 📈 Resumen Estadístico")
    
    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    
    with col_res1:
        total_llamadas_15min = df_metricas['Llamadas_15min_num'].sum()
        total_llamadas_totales = df_metricas['Llamadas_totales_num'].sum()
        st.metric("📞 Llamadas >15min", int(total_llamadas_15min))
        st.caption(f"de {int(total_llamadas_totales)} totales")
    
    with col_res2:
        porcentaje_global = (total_llamadas_15min / total_llamadas_totales * 100) if total_llamadas_totales > 0 else 0
        st.metric("📊 % Global >15min", f"{porcentaje_global:.1f}%")
        
        media_15min = df_metricas['Llamadas_15min_num'].mean()
        st.caption(f"Media: {media_15min:.1f}/agente")
    
    with col_res3:
        if 'Ventas_num' in df_metricas.columns:
            total_ventas = df_metricas['Ventas_num'].sum()
            st.metric("💰 Ventas Totales", int(total_ventas))
            
            ratio = (total_ventas / total_llamadas_15min * 100) if total_llamadas_15min > 0 else 0
            st.caption(f"Ratio: {ratio:.1f}%")
    
    with col_res4:
        # Verificar qué columna de objetivo usar
        columna_objetivo_num = None
        if 'Objetivo_num' in df_metricas.columns:
            columna_objetivo_num = 'Objetivo_num'
        elif 'Objetivo_individual_num' in df_metricas.columns:
            columna_objetivo_num = 'Objetivo_individual_num'
        
        if columna_objetivo_num and 'Ventas_num' in df_metricas.columns:
            total_objetivo = df_metricas[columna_objetivo_num].sum()
            total_ventas = df_metricas['Ventas_num'].sum()
            progreso_global = (total_ventas / total_objetivo * 100) if total_objetivo > 0 else 0
            st.metric("🎯 Progreso Global", f"{progreso_global:.1f}%")
            
            ventas_restantes = max(0, total_objetivo - total_ventas)
            st.caption(f"Faltan: {ventas_restantes}")
        else:
            st.metric("🎯 Progreso", "N/A")
            st.caption("Sin datos de objetivos")


def _mostrar_tabla_resumen(df_metricas):
    """Muestra tabla resumen de métricas - CORREGIDO para usar 'Objetivo Individual'"""
    st.write("#### 📋 Tabla Resumen de Métricas")
    
    # Verificar qué columnas existen realmente
    columnas_disponibles = df_metricas.columns.tolist()
    
    # Columnas básicas que deberían existir
    columnas_base = ['Agente', 'Llamadas Totales', 'Llamadas >15min', 'Ventas']
    
    # Añadir columnas condicionalmente
    columnas_resumen = []
    
    for col in columnas_base:
        if col in columnas_disponibles:
            columnas_resumen.append(col)
    
    # Añadir % >15min si existe (puede tener diferente nombre)
    if '% >15min' in columnas_disponibles:
        columnas_resumen.append('% >15min')
    elif '%_15min' in columnas_disponibles:
        columnas_resumen.append('%_15min')
    
    # Añadir Objetivo Individual (no Objetivo Ventas)
    if 'Objetivo Individual' in columnas_disponibles:
        columnas_resumen.append('Objetivo Individual')
    elif 'Objetivo Ventas' in columnas_disponibles:
        columnas_resumen.append('Objetivo Ventas')
    
    # Añadir Ventas Restantes
    if 'Ventas Restantes' in columnas_disponibles:
        columnas_resumen.append('Ventas Restantes')
    
    # Añadir Cump. Ventas (%) si existe
    if 'Cump. Ventas Ind. (%)' in columnas_disponibles:
        columnas_resumen.append('Cump. Ventas Ind. (%)')
    elif 'Cump. Ventas (%)' in columnas_disponibles:
        columnas_resumen.append('Cump. Ventas (%)')
    
    # Crear DataFrame resumen
    df_resumen = df_metricas[columnas_resumen].copy()
    
    # Formatear porcentajes si existen
    if '% >15min' in df_resumen.columns:
        df_resumen['% >15min'] = df_resumen['% >15min'].apply(
            lambda x: f"{float(str(x).replace('%', '')):.1f}%" if pd.notna(x) else "0.0%"
        )
    elif '%_15min' in df_resumen.columns:
        df_resumen['% >15min'] = df_resumen['%_15min'].apply(
            lambda x: f"{float(x):.1f}%" if pd.notna(x) else "0.0%"
        )
    
    # Ordenar por Ventas (descendente)
    if 'Ventas' in df_resumen.columns:
        df_resumen = df_resumen.sort_values('Ventas', ascending=False)
    
    st.dataframe(df_resumen, use_container_width=True)


# ============================================================================
# MONITORIZACIONES
# ============================================================================

def panel_monitorizaciones_super_usuario():
    """Panel de monitorizaciones integrado en super users"""
    
    st.subheader("📊 Sistema de Monitorizaciones")
    
    super_users_config = cargar_super_users()
    username = st.session_state.get('username', '')
    
    agentes_completos = super_users_config.get("agentes", {})
    configuracion = super_users_config.get("configuracion", {})
    
    if configuracion.get("mostrar_solo_mis_agentes", False) and username:
        agentes = {k: v for k, v in agentes_completos.items() 
                  if v.get('supervisor', '') == username}
    else:
        agentes = agentes_completos
    
    # AÑADIR PESTAÑA PARA ELIMINAR
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Nueva Monitorización", 
        "🔔 Agentes Pendientes", 
        "📋 Historial",
        "👤 Monitorización Agente",
        "🗑️ Eliminar Monitorizaciones"
    ])
    
    with tab1:
        mostrar_formulario_monitorizacion(agentes)
    
    with tab2:
        mostrar_agentes_pendientes_monitorizar(agentes)
    
    with tab3:
        mostrar_historial_monitorizaciones(agentes)
    
    with tab4:
        mostrar_monitorizacion_agente_especifico()
    
    with tab5:
        _eliminar_monitorizaciones_agente()


def mostrar_formulario_monitorizacion(agentes):
    """Formulario para crear nuevas monitorizaciones"""
    
    st.write("### 📝 Registrar Nueva Monitorización")
    
    if not agentes:
        st.warning("No tienes agentes asignados para monitorizar")
        return
    
    st.write("#### 📄 Opción 1: Cargar PDF de Monitorización")
    
    uploaded_file = st.file_uploader(
        "Sube el PDF de monitorización",
        type=['pdf'],
        help="Sube el PDF generado después de una monitorización",
        key="pdf_monitorizacion"
    )

    if uploaded_file is not None:
        try:
            from monitorizacion_utils import analizar_pdf_monitorizacion
            datos_pdf = analizar_pdf_monitorizacion(uploaded_file)
            
            with st.expander("Ver datos extraídos del PDF", expanded=True):
                st.json(datos_pdf)
            
            # AÑADIR BOTÓN PARA PASAR DATOS AL FORMULARIO MANUAL
            st.write("### 📋 Transferir datos al formulario")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                # En la sección donde transfieres datos del PDF:
                if st.button("📋 Pasar datos al formulario", type="primary", use_container_width=True):
                    # Guardar todos los datos del PDF en session_state
                    # PERO NO LIMPIAR EL FORMULARIO EXISTENTE
                    for key, value in datos_pdf.items():
                        # Solo guardamos si no es el ID de empleado
                        if key != 'id_empleado':
                            # Y NO transferimos fecha_proxima_monitorizacion porque NO EXISTE
                            if key != 'fecha_proxima_monitorizacion':  # ¡AÑADE ESTA LÍNEA!
                                st.session_state[f"mon_{key}"] = value
                    
                    # Mostrar confirmación
                    st.success("✅ Datos del PDF transferidos al formulario manual!")
                    # NO hacer rerun aquí para que el usuario pueda ver los cambios
            
            with col2:
                if st.button("🧹 Limpiar solo datos del PDF", type="secondary", use_container_width=True):
                    # Limpiar solo los datos del PDF, no el formulario completo
                    for key in list(st.session_state.keys()):
                        if key.startswith('mon_'):
                            del st.session_state[key]
                    st.success("✅ Datos del PDF limpiados!")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Limpiar TODO el formulario", type="secondary", use_container_width=True):
                    # Limpiar todo: datos PDF y selección de agente
                    for key in list(st.session_state.keys()):
                        if key.startswith('mon_') or key.startswith('form_mon_'):
                            del st.session_state[key]
                    st.session_state.pop('datos_formulario_temporal', None)
                    st.success("✅ Formulario completamente limpiado!")
                    st.rerun()
            
            # Muestra qué datos se van a pasar (excepto ID empleado)
            st.write("**Datos que se transferirán al formulario:**")
            datos_a_pasar = {k: v for k, v in datos_pdf.items() if k != 'id_empleado'}
            for key, value in datos_a_pasar.items():
                if value is not None and value != "":
                    st.write(f"• **{key}:** {value}")
            
            # Mostrar puntos clave detectados automáticamente
            if 'puntos_clave' in datos_pdf and datos_pdf['puntos_clave']:
                st.write("**🔑 Puntos clave detectados automáticamente:**")
                for punto in datos_pdf['puntos_clave']:
                    st.write(f"- {punto}")
            
        except ImportError:
            st.info("Funcionalidad de análisis de PDF no disponible")
    
    st.write("#### ✍️ Opción 2: Ingreso Manual")
    
    OPCIONES_PUNTOS_CLAVE = [
        # Puntos clave ya existentes
        "LOPD", "Comunicación", "Cierre de venta", "Argumentación", 
        "Resolución objeciones", "Proceso venta", "Escucha activa", "Tono",
        "Estructura", "Detección", "Habilidades venta", "Verificación", "Otros",
        
        # NUEVOS puntos clave de tu función
        "Actividad",  # 1.2 D
        "Sondeo",  # 2.1 A, 2.4 C, 3.1 A
        "Oportunidad venta",  # 2.2 A, 2.2 C
        "Resumen beneficios",  # 2.2 B, 2.4 A
        "Gestión BBDD",  # 2.2 F, 2.4 D, 2.4 E
        "Textos legales",  # 3.1 D
        "Argumentación ¡CUIDADO!",  # 3.1 B, 3.1 C, 3.1 F, 3.2 B
        "Textos legales ¡CUIDADO!",  # 3.1 E
        "LOPD ¡CUIDADO!",  # 3.1 G
        "Sondeo ¡CUIDADO!",  # 3.2 A
        "Gestión BBDD ¡CUIDADO!"  # 3.2 C
    ]
    
    with st.form("form_monitorizacion", clear_on_submit=True):
        # Datos que vamos a recoger
        datos_formulario = {}
        
        # 1. Seleccionar agente (manualmente, el ID del PDF no se pasa)
        agentes_opciones = []
        for agent_id, info in agentes.items():
            if info.get('activo', True):
                nombre = info.get('nombre', agent_id)
                grupo = info.get('grupo', 'Sin grupo')
                agentes_opciones.append(f"{agent_id} - {nombre} ({grupo})")
        
        if not agentes_opciones:
            st.warning("No hay agentes activos disponibles")
            return
        
        agente_seleccionado = st.selectbox(
            "Seleccionar Agente:",
            agentes_opciones,
            key="form_mon_agente"
        )
        
        if agente_seleccionado:
            datos_formulario['agente_id'] = agente_seleccionado.split(" - ")[0]
        
        # 2. Fechas (usar datos del PDF si existen)
        col_fecha1, col_fecha2 = st.columns(2)
        
        with col_fecha1:
            # Obtener fecha del PDF si existe, si no usar hoy
            fecha_pdf_str = st.session_state.get('mon_fecha_monitorizacion')
            if fecha_pdf_str:
                try:
                    fecha_pdf = datetime.strptime(fecha_pdf_str, '%Y-%m-%d').date()
                    fecha_default = fecha_pdf
                except:
                    fecha_default = datetime.now().date()
            else:
                fecha_default = datetime.now().date()
            
            fecha_monitorizacion = st.date_input(
                "Fecha de Monitorización:",
                value=fecha_default,
                key="form_mon_fecha"
            )
            datos_formulario['fecha_monitorizacion'] = fecha_monitorizacion.strftime('%Y-%m-%d')
        

        with col_fecha2:
            # ================================================
            # FECHA PRÓXIMA MONITORIZACIÓN
            # ================================================
            # NOTA: Esta fecha NO EXISTE en el PDF de monitorización
            # Es una fecha que el supervisor debe define
            # Usar un valor por defecto razonable: 14 días desde hoy
            # o 14 días desde la fecha de monitorización si está disponible
            fecha_mon = None
            if 'fecha_monitorizacion' in datos_formulario:
                try:
                    fecha_mon = datetime.strptime(datos_formulario['fecha_monitorizacion'], '%Y-%m-%d').date()
                except:
                    fecha_mon = datetime.now().date()
            else:
                fecha_mon = datetime.now().date()
            
            # Calcular fecha default: 14 días desde la fecha de monitorización
            fecha_default = fecha_mon + timedelta(days=14)
            
            fecha_proxima = st.date_input(
                "Fecha próxima monitorización *:",
                value=fecha_default,
                key="form_mon_fecha_proxima",
                help="* Esta fecha NO viene en el PDF. Define cuándo será la próxima monitorización."
            )
            
            # Guardar la fecha seleccionada por el usuario
            datos_formulario['fecha_proxima_monitorizacion'] = fecha_proxima.strftime('%Y-%m-%d')
            
            # Mostrar ayuda claramente
            st.caption("ℹ️ Esta fecha se programa manualmente para la próxima revisión")
        
        # 3. Nota y objetivo (usar datos del PDF si existen)
        col_nota1, col_nota2 = st.columns(2)
        
        with col_nota1:
            nota_pdf = st.session_state.get('mon_nota_global')
            nota_global = st.number_input(
                "Nota Global (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(nota_pdf) if nota_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_nota_global"
            )
            datos_formulario['nota_global'] = nota_global
        
        with col_nota2:
            objetivo_pdf = st.session_state.get('mon_objetivo', 85.0)
            objetivo = st.number_input(
                "Objetivo (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(objetivo_pdf),
                step=0.5,
                key="form_mon_objetivo"
            )
            datos_formulario['objetivo'] = objetivo
        
        # 4. Puntuaciones por área (usar datos del PDF si existen)
        st.write("##### 📊 Puntuaciones por Área")
        
        col_areas1, col_areas2 = st.columns(2)
        
        with col_areas1:
            experiencia_pdf = st.session_state.get('mon_experiencia')
            experiencia = st.number_input(
                "Experiencia (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(experiencia_pdf) if experiencia_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_experiencia"
            )
            datos_formulario['experiencia'] = experiencia
            
            comunicacion_pdf = st.session_state.get('mon_comunicacion')
            comunicacion = st.number_input(
                "Comunicación (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(comunicacion_pdf) if comunicacion_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_comunicacion"
            )
            datos_formulario['comunicacion'] = comunicacion
            
            deteccion_pdf = st.session_state.get('mon_deteccion')
            deteccion = st.number_input(
                "Detección (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(deteccion_pdf) if deteccion_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_deteccion"
            )
            datos_formulario['deteccion'] = deteccion
        
        with col_areas2:
            habilidades_pdf = st.session_state.get('mon_habilidades_venta')
            habilidades_venta = st.number_input(
                "Habilidades de Venta (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(habilidades_pdf) if habilidades_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_habilidades_venta"
            )
            datos_formulario['habilidades_venta'] = habilidades_venta
            
            resolucion_pdf = st.session_state.get('mon_resolucion_objeciones')
            resolucion_objeciones = st.number_input(
                "Resolución Objeciones (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(resolucion_pdf) if resolucion_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_resolucion_objeciones"
            )
            datos_formulario['resolucion_objeciones'] = resolucion_objeciones
            
            cierre_pdf = st.session_state.get('mon_cierre_contacto')
            cierre_contacto = st.number_input(
                "Cierre Contacto (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(cierre_pdf) if cierre_pdf is not None else 0.0,
                step=0.5,
                key="form_mon_cierre_contacto"
            )
            datos_formulario['cierre_contacto'] = cierre_contacto
        
        # 5. Feedback y plan de acción SEPARADOS (usar datos del PDF si existen)
        st.write("##### 💬 Feedback para el Agente")
        
        feedback_pdf = st.session_state.get('mon_feedback', '')
        feedback = st.text_area(
            "Escribe el feedback específico para el agente:",
            value=feedback_pdf,
            height=120,
            key="form_mon_feedback",
            help="Comentarios específicos sobre lo que hizo bien/mal, áreas de mejora, etc."
        )
        datos_formulario['feedback'] = feedback
        
        st.write("##### 🎯 Plan de Acción Específico")
        
        plan_accion_pdf = st.session_state.get('mon_plan_accion', '')
        plan_accion = st.text_area(
            "Escribe el plan de acción específico:",
            value=plan_accion_pdf,
            height=120,
            key="form_mon_plan_accion",
            help="Acciones concretas que debe tomar el agente para mejorar"
        )
        datos_formulario['plan_accion'] = plan_accion
        
        # 6. Puntos clave (usar datos del PDF si existen)
        puntos_clave_pdf = st.session_state.get('mon_puntos_clave', [])
        
        # Filtrar solo los valores que están en las opciones válidas
        valores_validos = [v for v in puntos_clave_pdf if v in OPCIONES_PUNTOS_CLAVE]
        
        puntos_clave = st.multiselect(
            "Puntos clave identificados:",
            OPCIONES_PUNTOS_CLAVE,
            default=valores_validos,
            key="form_mon_puntos_clave"
        )
        datos_formulario['puntos_clave'] = puntos_clave
        
        # 7. Botón de submit CON PREVENCIÓN DE DOBLE CLICK
        submitted = st.form_submit_button("💾 Guardar Monitorización", type="primary", use_container_width=True)

    # 8. Procesar fuera del formulario con validación mejorada
    if submitted:
        # **VALIDACIÓN ANTES DE PROCESAR**
        if not datos_formulario.get('agente_id'):
            st.error("❌ Debe seleccionar un agente")
            st.stop()
        
        if datos_formulario.get('nota_global', 0) == 0:
            st.warning("⚠️ La nota global es 0. ¿Estás seguro de que los datos son correctos?")
        
        # **VERIFICAR SI LOS DATOS SON VÁLIDOS** (no todos en 0)
        campos_numericos = ['nota_global', 'experiencia', 'comunicacion', 'deteccion']
        todos_cero = all(datos_formulario.get(campo, 0) == 0 for campo in campos_numericos)
        
        if todos_cero:
            st.error("❌ Todos los valores numéricos están en 0. ¿Estás seguro de que quieres guardar?")
            col_si, col_no = st.columns(2)
            with col_si:
                if st.button("✅ Sí, guardar de todos modos"):
                    # Continuar con el procesamiento
                    pass
            with col_no:
                if st.button("❌ No, cancelar"):
                    st.stop()
            return
        
        # **PROCESAR SOLO UNA VEZ**
        _procesar_formulario_monitorizacion(datos_formulario)


def _procesar_formulario_monitorizacion(datos_formulario):
    """Procesa los datos del formulario de monitorización"""
    if not datos_formulario or 'agente_id' not in datos_formulario:
        st.error("Debe seleccionar un agente para continuar")
        return False
    
    try:
        from monitorizacion_utils import guardar_monitorizacion_completa
        
        username = st.session_state.get('username', '')
        
        # VERIFICA QUE LA FECHA PRÓXIMA ESTÉ PRESENTE
        fecha_proxima = datos_formulario.get('fecha_proxima_monitorizacion')
        if not fecha_proxima:
            # Si no está, calcular automáticamente
            from datetime import datetime, timedelta
            fecha_mon = datos_formulario.get('fecha_monitorizacion')
            if fecha_mon:
                try:
                    fecha_mon_dt = datetime.strptime(fecha_mon, '%Y-%m-%d')
                    fecha_proxima = (fecha_mon_dt + timedelta(days=14)).strftime('%Y-%m-%d')
                except:
                    fecha_proxima = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
            else:
                fecha_proxima = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        
        monitorizacion_data = {
            'id_empleado': datos_formulario['agente_id'],
            'fecha_monitorizacion': datos_formulario.get('fecha_monitorizacion'),
            'fecha_proxima_monitorizacion': fecha_proxima,  # ¡AQUÍ!
            'nota_global': datos_formulario.get('nota_global', 0),
            'objetivo': datos_formulario.get('objetivo', 85),
            'experiencia': datos_formulario.get('experiencia', 0),
            'comunicacion': datos_formulario.get('comunicacion', 0),
            'deteccion': datos_formulario.get('deteccion', 0),
            'habilidades_venta': datos_formulario.get('habilidades_venta', 0),
            'resolucion_objeciones': datos_formulario.get('resolucion_objeciones', 0),
            'cierre_contacto': datos_formulario.get('cierre_contacto', 0),
            'feedback': datos_formulario.get('feedback', ''),
            'plan_accion': datos_formulario.get('plan_accion', ''),
            'puntos_clave': datos_formulario.get('puntos_clave', [])
        }
        
        # DEBUG: Mostrar qué datos se van a guardar
        st.info(f"📅 Fecha próxima a guardar: {fecha_proxima}")
        
        exito = guardar_monitorizacion_completa(monitorizacion_data, username)
        
        if exito:
            st.success("✅ Monitorización guardada exitosamente")
            # Limpiar session_state
            for key in list(st.session_state.keys()):
                if key.startswith('mon_') or key.startswith('form_mon_'):
                    del st.session_state[key]
            st.session_state.datos_transferidos = False
            st.rerun()
            return True
        else:
            st.error("❌ Error al guardar la monitorización")
            return False
            
    except Exception as e:
        st.error(f"❌ Error al procesar monitorización: {str(e)}")
        return False


def _eliminar_monitorizaciones_agente():
    """Elimina monitorizaciones de un agente específico"""
    st.write("### 🗑️ Eliminar Monitorizaciones de Agente")
    
    super_users_config = cargar_super_users()
    agentes = super_users_config.get("agentes", {})
    
    agentes_opciones = []
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        agentes_opciones.append(f"{agent_id} - {nombre} ({grupo})")
    
    if not agentes_opciones:
        st.warning("No hay agentes disponibles")
        return
    
    agente_seleccionado = st.selectbox(
        "Seleccionar Agente:",
        agentes_opciones,
        key="eliminar_mon_agente"
    )
    
    if agente_seleccionado:
        agent_id = agente_seleccionado.split(" - ")[0]
        
        try:
            from database import (
                obtener_monitorizaciones_por_empleado,
                eliminar_monitorizaciones_empleado
            )
            
            # Obtener historial actual
            monitorizaciones = obtener_monitorizaciones_por_empleado(agent_id)
            
            if not monitorizaciones:
                st.info("Este agente no tiene monitorizaciones")
                return
            
            total_monitorizaciones = len(monitorizaciones)
            ultima_fecha = max(m.get('fecha_monitorizacion', '') for m in monitorizaciones)
            
            st.warning(f"⚠️ **ADVERTENCIA:** Vas a eliminar TODAS las monitorizaciones de {agente_seleccionado.split(' - ')[1]}")
            st.write(f"**📊 Datos a eliminar:**")
            st.write(f"• Total monitorizaciones: {total_monitorizaciones}")
            st.write(f"• Última monitorización: {ultima_fecha}")
            st.write(f"• Agente ID: {agent_id}")
            
            col_conf1, col_conf2 = st.columns(2)
            
            with col_conf1:
                if st.button("✅ **ELIMINAR TODAS LAS MONITORIZACIONES**", type="primary", use_container_width=True):
                    eliminadas = eliminar_monitorizaciones_empleado(agent_id)
                    if eliminadas:
                        st.success(f"✅ {eliminadas} monitorizaciones eliminadas para {agente_seleccionado.split(' - ')[1]}")
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar monitorizaciones")
            
            with col_conf2:
                if st.button("❌ **CANCELAR**", type="secondary", use_container_width=True):
                    st.info("Operación cancelada")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


# ============================================================================
# ALERTAS DE MONITORIZACIÓN
# ============================================================================

def calcular_alertas_monitorizaciones_pendientes(agentes):
    """Calcula alertas para agentes que tienen monitorización programada para hoy"""
    from datetime import datetime
    
    alertas = []
    hoy = datetime.now().date()
    
    try:
        from database import obtener_ultima_monitorizacion_empleado
        
        for agent_id, info in agentes.items():
            if not info.get('activo', True):
                continue
            
            ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
            
            if ultima_mon and ultima_mon.get('fecha_proxima_monitorizacion'):
                try:
                    fecha_proxima = datetime.strptime(
                        ultima_mon['fecha_proxima_monitorizacion'], 
                        '%Y-%m-%d'
                    ).date()
                    
                    # Si la monitorización es para hoy o ya pasó la fecha
                    if fecha_proxima == hoy:
                        alerta_id = f"monitorizacion_hoy_{agent_id}_{hoy}"
                        
                        alertas.append({
                            'id': alerta_id,
                            'agente_id': agent_id,
                            'agente_nombre': info.get('nombre', agent_id),
                            'grupo': info.get('grupo', 'Sin grupo'),
                            'tipo': 'monitorizacion_hoy',
                            'fecha_monitorizacion': ultima_mon.get('fecha_monitorizacion', ''),
                            'fecha_proxima': ultima_mon.get('fecha_proxima_monitorizacion', ''),
                            'nota_anterior': ultima_mon.get('nota_global', 0),
                            'prioridad': 'alta',  # Hoy es alta prioridad
                            'mensaje': f"✅ Monitorización programada para HOY",
                            'explicacion': f"Última monitorización: {ultima_mon.get('fecha_monitorizacion', 'N/A')} - Nota: {ultima_mon.get('nota_global', 0)}%"
                        })
                    
                    elif fecha_proxima < hoy:
                        # Si la fecha ya pasó (atrasada)
                        dias_atraso = (hoy - fecha_proxima).days
                        alerta_id = f"monitorizacion_atrasada_{agent_id}_{fecha_proxima}"
                        
                        alertas.append({
                            'id': alerta_id,
                            'agente_id': agent_id,
                            'agente_nombre': info.get('nombre', agent_id),
                            'grupo': info.get('grupo', 'Sin grupo'),
                            'tipo': 'monitorizacion_atrasada',
                            'fecha_proxima': ultima_mon.get('fecha_proxima_monitorizacion', ''),
                            'dias_atraso': dias_atraso,
                            'nota_anterior': ultima_mon.get('nota_global', 0),
                            'prioridad': 'urgente',  # Atrasada es urgente
                            'mensaje': f"⚠️ Monitorización ATRASADA {dias_atraso} día(s)",
                            'explicacion': f"Debía ser el {fecha_proxima.strftime('%d/%m/%Y')} - {dias_atraso} día(s) atrasada"
                        })
                    
                except Exception as e:
                    continue
    
    except ImportError as e:
        print(f"Error importando módulo de monitorizaciones: {e}")
    except Exception as e:
        print(f"Error calculando alertas de monitorización: {e}")
    
    # Ordenar: primero las atrasadas (urgente), luego las de hoy (alta)
    alertas_ordenadas = []
    alertas_ordenadas.extend([a for a in alertas if a['prioridad'] == 'urgente'])
    alertas_ordenadas.extend([a for a in alertas if a['prioridad'] == 'alta'])
    
    return alertas_ordenadas


# ============================================================================
# MOSTRAR ALERTAS COMBINADAS EN SIDEBAR
# ============================================================================

def mostrar_alertas_sidebar():
    """Muestra alertas de agentes en el sidebar SOLO MONITORIZACIONES"""
    
    username = st.session_state.get('username', '')
    if not username:
        return
    
    # Cargar alertas ya descartadas previamente
    alertas_descartadas = cargar_alertas_descartadas(username)
    
    super_users_config = cargar_super_users()
    configuracion = super_users_config.get("configuracion", {})
    
    agentes_completos = super_users_config.get("agentes", {})
    
    if username == "admin":
        agentes = agentes_completos
    elif username in super_users_config.get("super_users", []):
        if configuracion.get("mostrar_solo_mis_agentes", False):
            agentes = {k: v for k, v in agentes_completos.items() 
                      if v.get('supervisor', '') == username}
        else:
            agentes = agentes_completos
    else:
        return
    
    # ==============================================
    # CALCULAR SOLO ALERTAS DE MONITORIZACIONES
    # ==============================================
    alertas_monitorizaciones = calcular_alertas_monitorizaciones_pendientes(agentes)
    
    # Filtrar solo alertas que NO han sido descartadas
    alertas_activas = [a for a in alertas_monitorizaciones if a['id'] not in alertas_descartadas]
    
    if alertas_activas:
        with st.sidebar:
            st.write("---")
            st.subheader(f"🔔 Alertas ({len(alertas_activas)})")
            
            alertas_a_descartar = []
            
            for alerta in alertas_activas[:8]:  # Mostrar más alertas
                # Estilos diferentes según tipo de alerta
                if alerta['tipo'] == 'monitorizacion_hoy':
                    st.success(f"📅 {alerta['agente_nombre']}")
                    st.caption(f"✅ {alerta['mensaje']}")
                    st.caption(f"📊 Nota anterior: {alerta['nota_anterior']}%")
                    
                elif alerta['tipo'] == 'monitorizacion_atrasada':
                    st.error(f"⏰ {alerta['agente_nombre']}")
                    st.caption(f"⚠️ {alerta['mensaje']}")
                    st.caption(f"📅 Fecha programada: {alerta['fecha_proxima']}")
                
                # Checkbox para descartar
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption("")
                with col2:
                    descartar = st.checkbox(
                        "✓",
                        key=f"descartar_{alerta['id']}",
                        help="Marcar para descartar esta alerta permanentemente"
                    )
                    
                    if descartar:
                        alertas_a_descartar.append(alerta['id'])
                
                st.write("---")
            
            # BOTÓN PARA DESCARTAR ALERTAS SELECCIONADAS
            if alertas_a_descartar:
                if st.button("✅ Descartar alertas seleccionadas", use_container_width=True, 
                           type="primary", key="btn_descartar_alertas"):
                    for alerta_id in alertas_a_descartar:
                        guardar_alerta_descartada(username, alerta_id)
                    
                    st.success(f"✅ {len(alertas_a_descartar)} alerta(s) descartada(s)")
                    st.rerun()
            
            # Contadores por tipo
            monitorizaciones_hoy = len([a for a in alertas_activas if a['tipo'] == 'monitorizacion_hoy'])
            monitorizaciones_atrasadas = len([a for a in alertas_activas if a['tipo'] == 'monitorizacion_atrasada'])
            
            # Mostrar resumen
            if monitorizaciones_hoy > 0 or monitorizaciones_atrasadas > 0:
                with st.expander("📊 Resumen de alertas", expanded=False):
                    if monitorizaciones_hoy > 0:
                        st.write(f"📅 **Monitorizaciones hoy:** {monitorizaciones_hoy}")
                    if monitorizaciones_atrasadas > 0:
                        st.write(f"⏰ **Monitorizaciones atrasadas:** {monitorizaciones_atrasadas}")
            
            # Si hay más de 8 alertas
            if len(alertas_activas) > 8:
                st.caption(f"... y {len(alertas_activas) - 8} alertas más")
            
            # BOTÓN PARA VER TODAS LAS ALERTAS
            if st.button("📋 Ver todas las alertas", use_container_width=True, key="btn_ver_todas_alertas"):
                st.session_state.mostrar_todas_alertas = True
                st.rerun()
            
            # BOTÓN PARA GESTIONAR ALERTAS DESCARTADAS
            if st.button("🧹 Gestionar alertas descartadas", use_container_width=True, key="btn_gestionar_alertas"):
                st.session_state.mostrar_gestion_alertas = True
                st.rerun()
    
    # Si no hay alertas activas pero sí hay alertas descartadas
    elif alertas_descartadas:
        with st.sidebar:
            st.write("---")
            st.success("✅ No hay alertas nuevas")
            
            if st.button("🗑️ Ver alertas descartadas", use_container_width=True, key="btn_ver_descartadas"):
                st.session_state.mostrar_gestion_alertas = True
                st.rerun()


def cargar_alertas_descartadas(username):
    """Carga las alertas que el usuario ha descartado permanentemente"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = f"data/alertas_descartadas_{username}.json"
        
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error cargando alertas descartadas: {e}")
        return []


def guardar_alerta_descartada(username, alerta_id):
    """Guarda una alerta como descartada permanentemente por el usuario"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo = f"data/alertas_descartadas_{username}.json"
        
        alertas_descartadas = cargar_alertas_descartadas(username)
        
        if alerta_id not in alertas_descartadas:
            alertas_descartadas.append(alerta_id)
            
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(alertas_descartadas, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error guardando alerta descartada: {e}")
        return False


def limpiar_alertas_descartadas(username):
    """Limpia TODAS las alertas descartadas por el usuario (las borra permanentemente)"""
    try:
        archivo = f"data/alertas_descartadas_{username}.json"
        if os.path.exists(archivo):
            os.remove(archivo)
            return True
        return False
    except Exception as e:
        print(f"Error limpiando alertas descartadas: {e}")
        return False


def mostrar_gestion_alertas_descartadas():
    """Muestra página para gestionar alertas descartadas"""
    st.header("🗑️ Gestión de Alertas Descartadas")
    
    username = st.session_state.get('username', '')
    if not username:
        st.warning("⚠️ Debes iniciar sesión")
        return
    
    # Cargar alertas descartadas
    alertas_descartadas_ids = cargar_alertas_descartadas(username)
    
    if not alertas_descartadas_ids:
        st.success("✅ No tienes alertas descartadas")
        
        if st.button("← Volver", type="secondary", use_container_width=True):
            st.session_state.mostrar_gestion_alertas = False
            st.rerun()
        
        return
    
    st.write(f"### Tienes {len(alertas_descartadas_ids)} alertas descartadas")
    
    # Mostrar lista de alertas descartadas
    with st.expander("📋 Ver lista de alertas descartadas", expanded=True):
        for i, alerta_id in enumerate(alertas_descartadas_ids[:30]):  # Mostrar solo 30
            st.write(f"{i+1}. `{alerta_id}`")
        
        if len(alertas_descartadas_ids) > 30:
            st.info(f"... y {len(alertas_descartadas_ids) - 30} más")
    
    st.write("---")
    
    # Estadísticas
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        st.metric("Total descartadas", len(alertas_descartadas_ids))
    
    with col_stats2:
        # Intentar extraer cuántos agentes únicos hay en las alertas
        agentes_unicos = set()
        for alerta_id in alertas_descartadas_ids:
            # El ID contiene el agent_id al principio
            partes = alerta_id.split('_')
            if partes:
                agentes_unicos.add(partes[0])
        
        st.metric("Agentes afectados", len(agentes_unicos))
    
    with col_stats3:
        # Fecha de la primera alerta (si hay)
        if alertas_descartadas_ids:
            # Las alertas tienen fecha en el ID
            st.metric("Primera alerta", alertas_descartadas_ids[0].split('_')[1][:8])
    
    st.write("### ⚙️ Opciones de Gestión")
    
    col_opc1, col_opc2, col_opc3 = st.columns(3)
    
    with col_opc1:
        if st.button("🗑️ **ELIMINAR TODAS**", type="primary", use_container_width=True,
                    help="Elimina permanentemente TODAS las alertas descartadas"):
            if limpiar_alertas_descartadas(username):
                st.success("✅ Todas las alertas descartadas han sido eliminadas")
                st.session_state.mostrar_gestion_alertas = False
                st.rerun()
            else:
                st.error("❌ Error al eliminar alertas descartadas")
    
    with col_opc2:
        if st.button("🔄 **RESTAURAR TODAS**", type="secondary", use_container_width=True,
                    help="Elimina el registro de alertas descartadas (volverán a aparecer)"):
            if limpiar_alertas_descartadas(username):
                st.success("✅ Alertas descartadas restauradas (volverán a aparecer)")
                st.session_state.mostrar_gestion_alertas = False
                st.rerun()
    
    with col_opc3:
        if st.button("← **VOLVER**", type="secondary", use_container_width=True):
            st.session_state.mostrar_gestion_alertas = False
            st.rerun()
    
    st.info("""
    **ℹ️ Nota:** 
    - **Eliminar todas**: Borra permanentemente el registro de alertas descartadas
    - **Restaurar todas**: Las alertas descartadas volverán a aparecer como nuevas
    - Las alertas se recalculan automáticamente cada vez que se carga la página
    """)


# ============================================================================
# FUNCIONES AUXILIARES DE MONITORIZACIONES
# ============================================================================

def mostrar_agentes_pendientes_monitorizar(agentes):
    """Muestra agentes que necesitan ser monitorizados"""
    
    st.write("### 🔔 Agentes Pendientes de Monitorización")
    
    try:
        from database import obtener_agentes_pendientes_monitorizar
        agentes_pendientes = obtener_agentes_pendientes_monitorizar()
    except:
        agentes_pendientes = []
    
    if not agentes_pendientes:
        st.success("🎉 Todos los agentes están al día")
        return
    
    agentes_supervisor = {a['id'] for a in agentes_pendientes if a['id'] in agentes}
    agentes_pendientes = [a for a in agentes_pendientes if a['id'] in agentes_supervisor]
    
    if not agentes_pendientes:
        st.info("Tus agentes están todos al día")
        return
    
    total = len(agentes_pendientes)
    nunca_monitorizados = sum(1 for a in agentes_pendientes if a['ultima_fecha'] is None)
    
    col_stats1, col_stats2 = st.columns(2)
    
    with col_stats1:
        st.metric("Total Pendientes", total)
    
    with col_stats2:
        st.metric("Nunca Monitorizados", nunca_monitorizados)
    
    st.write("##### 📋 Lista de Agentes Pendientes")
    
    datos_tabla = []
    for agente in agentes_pendientes:
        datos_tabla.append({
            'ID': agente['id'],
            'Nombre': agente['nombre'],
            'Grupo': agente['grupo'],
            'Última Monitorización': agente['ultima_fecha'] or "NUNCA",
            'Días sin': agente['dias_sin'] if agente['dias_sin'] != float('inf') else "∞",
            'Estado': agente['estado']
        })
    
    df = pd.DataFrame(datos_tabla)
    st.dataframe(df, use_container_width=True)
    
    if st.button("📝 Crear Monitorización Rápida", type="primary"):
        st.session_state.crear_monitorizacion_rapida = True
        st.rerun()


def mostrar_historial_monitorizaciones(agentes):
    """Muestra historial de monitorizaciones"""
    
    st.write("### 📋 Historial de Monitorizaciones")
    
    agentes_opciones = []
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        agentes_opciones.append(f"{agent_id} - {nombre} ({grupo})")
    
    if not agentes_opciones:
        st.warning("No hay agentes disponibles")
        return
    
    agente_seleccionado = st.selectbox(
        "Seleccionar Agente:",
        agentes_opciones,
        key="historial_agente"
    )
    
    if agente_seleccionado:
        agent_id = agente_seleccionado.split(" - ")[0]
        
        try:
            from database import obtener_monitorizaciones_por_empleado
            monitorizaciones = obtener_monitorizaciones_por_empleado(agent_id)
        except:
            monitorizaciones = []
        
        if not monitorizaciones:
            st.info("No hay monitorizaciones para este agente")
            return
        
        total = len(monitorizaciones)
        promedio = sum(m.get('nota_global', 0) for m in monitorizaciones) / total
        mejor = max(m.get('nota_global', 0) for m in monitorizaciones)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            st.metric("Total Monitorizaciones", total)
        
        with col_stat2:
            st.metric("Promedio Nota", f"{promedio:.1f}%")
        
        with col_stat3:
            st.metric("Mejor Nota", f"{mejor}%")
        
        datos_tabla = []
        for mon in monitorizaciones:
            datos_tabla.append({
                'Fecha': mon.get('fecha_monitorizacion', ''),
                'Nota Global': f"{mon.get('nota_global', 0)}%",
                'Objetivo': f"{mon.get('objetivo', 85)}%",
                'Próxima': mon.get('fecha_proxima_monitorizacion', 'No programada'),
                'Feedback': '✅' if mon.get('feedback') else '❌',
                'Plan': '✅' if mon.get('plan_accion') else '❌'
            })
        
        df = pd.DataFrame(datos_tabla)
        st.dataframe(df, use_container_width=True)


def mostrar_monitorizacion_agente_especifico():
    """Muestra la monitorización de un agente específico"""
    
    st.write("### 👤 Ver Monitorización de Agente")
    
    super_users_config = cargar_super_users()
    agentes = super_users_config.get("agentes", {})
    
    agentes_opciones = []
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        agentes_opciones.append(f"{agent_id} - {nombre} ({grupo})")
    
    if not agentes_opciones:
        st.warning("No hay agentes disponibles")
        return
    
    agente_seleccionado = st.selectbox(
        "Seleccionar Agente para ver su monitorización:",
        agentes_opciones,
        key="ver_monitorizacion_agente"
    )
    
    if agente_seleccionado:
        agent_id = agente_seleccionado.split(" - ")[0]
        
        try:
            from database import obtener_ultima_monitorizacion_empleado
            ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
        except:
            ultima_mon = None
        
        if not ultima_mon:
            st.info("Este agente no tiene monitorizaciones registradas")
            return
        
        st.write(f"#### 📊 Monitorización de {agente_seleccionado.split(' - ')[1]}")
        
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
                fecha_prox_dt = datetime.strptime(fecha_prox, '%Y-%m-%d')
                hoy = datetime.now().date()
                dias_restantes = (fecha_prox_dt.date() - hoy).days
                st.metric("Próxima", fecha_prox, delta=f"{dias_restantes} días")
        
        st.write("##### 📈 Puntuaciones por Área")
        
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
        
        if ultima_mon.get('feedback'):
            st.write("##### 💬 Feedback")
            st.write(ultima_mon.get('feedback'))
        
        if ultima_mon.get('plan_accion'):
            st.write("##### 🎯 Plan de Acción")
            st.write(ultima_mon.get('plan_accion'))
        
        if ultima_mon.get('puntos_clave'):
            st.write("##### 🔑 Puntos Clave")
            for punto in ultima_mon.get('puntos_clave'):
                st.write(f"- {punto}")


# ============================================================================
# FUNCIÓN PARA PANEL DE USUARIO (AGENTE) - OBJETIVOS PERSONALES
# ============================================================================

def mostrar_panel_usuario_con_objetivos():
    """Panel de usuario que muestra objetivos personales de ventas DESDE JSON"""
    username = st.session_state.get('username', '')
    
    if not username:
        return
    
    # Verificar si el usuario quiere mostrar/ocultar objetivos
    mostrar_objetivos_key = f"mostrar_objetivos_{username}"
    if mostrar_objetivos_key not in st.session_state:
        st.session_state[mostrar_objetivos_key] = True
    
    super_users_config = cargar_super_users()
    agentes = super_users_config.get("agentes", {})
    configuracion = super_users_config.get("configuracion", {})
    
    # Cargar objetivos desde JSON
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    
    if username in agentes:
        info_agente = agentes[username]
        
        # Obtener objetivo individual desde JSON
        objetivo_individual = objetivos_dict.get(username, 10)
        objetivo_global = configuracion.get('target_ventas_global', 100)
        
        # Calcular ventas del mes actual
        registro_llamadas = cargar_registro_llamadas()
        fecha_inicio = datetime.now().date().replace(day=1)
        fecha_fin = datetime.now().date()
        
        ventas_mes = 0
        for fecha_str, datos_dia in registro_llamadas.items():
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_inicio <= fecha <= fecha_fin:
                if username in datos_dia:
                    ventas_mes += datos_dia[username].get("ventas", 0)
        
        # Calcular progreso individual
        progreso_individual = (ventas_mes / objetivo_individual * 100) if objetivo_individual > 0 else 0
        ventas_restantes_individual = max(0, objetivo_individual - ventas_mes)
        
        # Calcular contribución al objetivo global
        contribucion_global = (ventas_mes / objetivo_global * 100) if objetivo_global > 0 else 0
        
        # Mostrar/ocultar controles
        col_controles1, col_controles2 = st.columns([3, 1])
        
        with col_controles1:
            st.write(f"### 🎯 Mis Objetivos de Ventas")
        
        with col_controles2:
            mostrar = st.checkbox(
                "Mostrar",
                value=st.session_state[mostrar_objetivos_key],
                key=f"toggle_objetivos_{username}",
                label_visibility="collapsed"
            )
            st.session_state[mostrar_objetivos_key] = mostrar
        
        if mostrar:
            # OBJETIVO INDIVIDUAL DESDE JSON
            st.write("#### 📊 Mi Objetivo Personal")
            col_ind1, col_ind2, col_ind3 = st.columns(3)
            
            with col_ind1:
                st.metric("Objetivo Mensual", objetivo_individual)
            
            with col_ind2:
                st.metric("Ventas Actuales", ventas_mes)
            
            with col_ind3:
                st.metric("Faltan", ventas_restantes_individual)
            
            # Barra de progreso individual
            st.progress(min(progreso_individual / 100, 1.0))
            
            if progreso_individual < 50:
                color = "red"
            elif progreso_individual < 80:
                color = "orange"
            else:
                color = "green"
            
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="color: {color}; font-weight: bold;">{progreso_individual:.1f}%</span> 
                ({ventas_mes} de {objetivo_individual} ventas)
            </div>
            """, unsafe_allow_html=True)
            
            # OBJETIVO GLOBAL (información)
            st.write("#### 🎯 Objetivo de Campaña")
            col_glob1, col_glob2 = st.columns(2)
            
            with col_glob1:
                st.metric("Objetivo Campaña", objetivo_global)
            
            with col_glob2:
                st.metric("Mi Contribución", f"{contribucion_global:.1f}%")
            
            # Días restantes en el mes
            dias_en_mes = (fecha_fin - fecha_inicio).days + 1
            dias_transcurridos = (datetime.now().date() - fecha_inicio).days + 1
            dias_restantes = dias_en_mes - dias_transcurridos
            
            st.caption(f"📅 Días restantes: {dias_restantes} | Ventas/día necesarias: {ventas_restantes_individual / max(dias_restantes, 1):.1f}")
    else:
        # Si no es agente, mostrar solo objetivo global
        objetivo_global = configuracion.get('target_ventas_global', 100)
        
        st.write(f"### 🎯 Objetivo Global de Campaña")
        st.metric("Objetivo Campaña", objetivo_global)
        st.info("No estás registrado como agente. Contacta con un administrador.")


# ============================================================================
# FUNCIÓN AUXILIAR PARA ALERTAS SIMPLIFICADAS (SOLO MONITORIZACIONES)
# ============================================================================

def calcular_alertas_media_llamadas(agentes, configuracion):
    """Función simplificada que retorna lista vacía para compatibilidad"""
    # Esta función se mantiene por compatibilidad con el código existente
    # pero siempre retorna lista vacía ya que no queremos alertas de llamadas
    return []


# ============================================================================
# GESTIÓN DE OBJETIVOS DE VENTAS EN ARCHIVO JSON SEPARADO
# ============================================================================

def cargar_objetivos_ventas():
    """Carga los objetivos de ventas desde un archivo JSON separado"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo_objetivos = 'data/objetivos_ventas.json'
        
        if os.path.exists(archivo_objetivos):
            # Verificar si el archivo no está vacío
            if os.path.getsize(archivo_objetivos) > 0:
                with open(archivo_objetivos, 'r', encoding='utf-8') as f:
                    contenido = f.read().strip()
                    if contenido:  # Verificar que no sea solo espacios en blanco
                        return json.loads(contenido)
            
            # Si el archivo está vacío o tiene solo espacios, crear estructura nueva
            print(f"Archivo {archivo_objetivos} está vacío, creando estructura nueva")
            
        # Crear estructura base si el archivo no existe o está vacío
        objetivos_base = {
            "objetivos": {},  # agent_id: objetivo_mensual
            "historico": {},  # Para guardar cambios históricos
            "metadata": {
                "fecha_creacion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat()
            }
        }
        
        # Guardar estructura base
        with open(archivo_objetivos, 'w', encoding='utf-8') as f:
            json.dump(objetivos_base, f, indent=4, ensure_ascii=False)
        
        return objetivos_base
        
    except json.JSONDecodeError as e:
        st.error(f"Error de JSON en objetivos_ventas.json: {e}")
        print(f"Error de JSON: {e}")
        # Si hay error de JSON, crear archivo nuevo
        return _crear_archivo_objetivos_nuevo()
    except Exception as e:
        st.error(f"Error cargando objetivos: {e}")
        print(f"Error general: {e}")
        return _crear_archivo_objetivos_nuevo()


def _crear_archivo_objetivos_nuevo():
    """Crea un nuevo archivo de objetivos si hay error"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo_objetivos = 'data/objetivos_ventas.json'
        
        objetivos_base = {
            "objetivos": {},
            "historico": {},
            "metadata": {
                "fecha_creacion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat()
            }
        }
        
        with open(archivo_objetivos, 'w', encoding='utf-8') as f:
            json.dump(objetivos_base, f, indent=4, ensure_ascii=False)
        
        print(f"Archivo {archivo_objetivos} creado exitosamente")
        return objetivos_base
    except Exception as e:
        st.error(f"Error crítico creando archivo de objetivos: {e}")
        # Retornar estructura mínima en memoria
        return {
            "objetivos": {},
            "historico": {},
            "metadata": {
                "fecha_creacion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat()
            }
        }


def inicializar_archivo_objetivos():
    """Inicializa el archivo de objetivos si no existe o está corrupto"""
    try:
        # Primero, intentar cargar para ver si existe y es válido
        objetivos_data = cargar_objetivos_ventas()
        
        # Verificar estructura básica
        if not isinstance(objetivos_data, dict):
            print("Estructura de objetivos inválida, recreando...")
            return _crear_archivo_objetivos_nuevo()
        
        # Verificar que tenga las claves básicas
        claves_requeridas = ["objetivos", "historico", "metadata"]
        for clave in claves_requeridas:
            if clave not in objetivos_data:
                print(f"Falta clave '{clave}' en objetivos, recreando...")
                return _crear_archivo_objetivos_nuevo()
        
        print("Archivo de objetivos cargado correctamente")
        return objetivos_data
        
    except Exception as e:
        print(f"Error inicializando archivo de objetivos: {e}")
        return _crear_archivo_objetivos_nuevo()


def guardar_objetivos_ventas(objetivos_data):
    """Guarda los objetivos de ventas en archivo JSON"""
    try:
        os.makedirs('data', exist_ok=True)
        archivo_objetivos = 'data/objetivos_ventas.json'
        
        # Actualizar metadata
        objetivos_data["metadata"]["ultima_actualizacion"] = datetime.now().isoformat()
        
        with open(archivo_objetivos, 'w', encoding='utf-8') as f:
            json.dump(objetivos_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando objetivos: {e}")
        return False


def obtener_objetivo_agente(agent_id, default=10):
    """Obtiene el objetivo de ventas de un agente específico"""
    objetivos_data = cargar_objetivos_ventas()
    return objetivos_data.get("objetivos", {}).get(agent_id, default)


def actualizar_objetivo_agente(agent_id, nuevo_objetivo, usuario_que_modifica=""):
    """Actualiza el objetivo de un agente y guarda histórico"""
    objetivos_data = cargar_objetivos_ventas()
    
    # Obtener objetivo anterior
    objetivo_anterior = objetivos_data.get("objetivos", {}).get(agent_id, 10)
    
    # Actualizar objetivo
    objetivos_data.setdefault("objetivos", {})[agent_id] = nuevo_objetivo
    
    # Guardar en histórico
    registro_historico = {
        "fecha": datetime.now().isoformat(),
        "agente": agent_id,
        "objetivo_anterior": objetivo_anterior,
        "objetivo_nuevo": nuevo_objetivo,
        "usuario": usuario_que_modifica or "sistema"
    }
    
    # Inicializar histórico si no existe
    if "historico" not in objetivos_data:
        objetivos_data["historico"] = {}
    
    # Agregar al histórico del agente
    if agent_id not in objetivos_data["historico"]:
        objetivos_data["historico"][agent_id] = []
    
    objetivos_data["historico"][agent_id].append(registro_historico)
    
    # Limitar histórico a últimos 50 cambios
    if len(objetivos_data["historico"][agent_id]) > 50:
        objetivos_data["historico"][agent_id] = objetivos_data["historico"][agent_id][-50:]
    
    return guardar_objetivos_ventas(objetivos_data)


def actualizar_multiples_objetivos(objetivos_dict, usuario_que_modifica=""):
    """Actualiza múltiples objetivos a la vez"""
    objetivos_data = cargar_objetivos_ventas()
    
    for agent_id, nuevo_objetivo in objetivos_dict.items():
        # Actualizar objetivo
        objetivos_data.setdefault("objetivos", {})[agent_id] = nuevo_objetivo
        
        # Guardar en histórico (simplificado para batch)
        registro_historico = {
            "fecha": datetime.now().isoformat(),
            "agente": agent_id,
            "objetivo_nuevo": nuevo_objetivo,
            "usuario": usuario_que_modifica or "batch_update",
            "tipo": "batch_update"
        }
        
        if "historico" not in objetivos_data:
            objetivos_data["historico"] = {}
        
        if agent_id not in objetivos_data["historico"]:
            objetivos_data["historico"][agent_id] = []
        
        objetivos_data["historico"][agent_id].append(registro_historico)
    
    return guardar_objetivos_ventas(objetivos_data)


# ============================================================================
# FUNCIONES DE DÍAS LABORABLES
# ============================================================================

def calcular_dias_laborables(fecha_inicio: date, fecha_fin: date, incluir_festivos=True) -> int:
    """Calcula los días laborables (lunes a viernes) entre dos fechas excluyendo festivos"""
    from festivos_manager import cargar_festivos, es_festivo
    
    dias_totales = (fecha_fin - fecha_inicio).days + 1
    dias_laborables = 0
    
    if incluir_festivos:
        festivos_data = cargar_festivos()
    
    for i in range(dias_totales):
        fecha_actual = fecha_inicio + timedelta(days=i)
        
        # Verificar si es fin de semana
        if fecha_actual.weekday() >= 5:  # 5=Sábado, 6=Domingo
            continue
        
        # Verificar si es festivo
        if incluir_festivos and es_festivo(fecha_actual, festivos_data):
            continue
        
        dias_laborables += 1
    
    return dias_laborables


def obtener_dias_laborables_info(fecha_inicio: date, fecha_fin: date):
    """Obtiene información detallada sobre días laborables"""
    from festivos_manager import cargar_festivos, es_festivo
    
    festivos_data = cargar_festivos()
    dias_info = []
    
    dias_totales = (fecha_fin - fecha_inicio).days + 1
    
    for i in range(dias_totales):
        fecha_actual = fecha_inicio + timedelta(days=i)
        dia_semana = fecha_actual.weekday()
        
        es_fin_semana = dia_semana >= 5
        es_festivo_flag = es_festivo(fecha_actual, festivos_data) if not es_fin_semana else False
        es_laborable = not es_fin_semana and not es_festivo_flag
        
        dias_info.append({
            'fecha': fecha_actual,
            'dia_semana': dia_semana,
            'nombre_dia': fecha_actual.strftime('%A'),
            'es_fin_semana': es_fin_semana,
            'es_festivo': es_festivo_flag,
            'es_laborable': es_laborable,
            'numero_dia': fecha_actual.day
        })
    
    return dias_info


def calcular_dias_laborables_transcurridos(fecha_inicio, fecha_hoy):
    """Calcula días laborables transcurridos desde inicio del mes hasta hoy"""
    return calcular_dias_laborables(fecha_inicio, fecha_hoy)


def calcular_dias_laborables_restantes(fecha_hoy, fecha_fin_mes):
    """Calcula días laborables restantes desde hoy hasta fin de mes"""
    # Añadir 1 día para incluir hoy si es laborable
    fecha_siguiente = fecha_hoy + timedelta(days=1)
    if fecha_siguiente <= fecha_fin_mes:
        return calcular_dias_laborables(fecha_siguiente, fecha_fin_mes)
    return 0


def obtener_total_dias_laborables_mes(fecha_inicio, fecha_fin_mes):
    """Calcula total de días laborables en el mes"""
    return calcular_dias_laborables(fecha_inicio, fecha_fin_mes)


# ============================================================================
# PANEL DE OBJETIVOS EN SIDEBAR
# ============================================================================

def mostrar_panel_objetivos_sidebar():
    """Muestra el panel de objetivos personales en el sidebar CON DÍAS LABORABLES"""
    username = st.session_state.get('username', '')
    
    if not username:
        return
    
    with st.sidebar:
        st.write("---")
        st.subheader("🎯 Mi Progreso")
        
        # Cargar datos necesarios
        super_users_config = cargar_super_users()
        agentes = super_users_config.get("agentes", {})
        configuracion = super_users_config.get("configuracion", {})
        
        # Cargar objetivos desde JSON
        objetivos_data = cargar_objetivos_ventas()
        objetivos_dict = objetivos_data.get("objetivos", {})
        
        if username in agentes:
            info_agente = agentes[username]
            
            # Obtener objetivo individual desde JSON
            objetivo_individual = objetivos_dict.get(username, 10)
            objetivo_global = configuracion.get('target_ventas_global', 100)
            
            # Fechas importantes
            fecha_hoy = datetime.now().date()
            fecha_inicio_mes = fecha_hoy.replace(day=1)
            
            # Calcular fin de mes
            from dateutil.relativedelta import relativedelta
            fecha_fin_mes = (fecha_inicio_mes + relativedelta(months=1)) - relativedelta(days=1)
            
            # Calcular días laborables
            dias_laborables_transcurridos = calcular_dias_laborables_transcurridos(fecha_inicio_mes, fecha_hoy)
            dias_laborables_restantes = calcular_dias_laborables_restantes(fecha_hoy, fecha_fin_mes)
            total_laborables_mes = obtener_total_dias_laborables_mes(fecha_inicio_mes, fecha_fin_mes)
            
            # Calcular ventas del mes actual
            registro_llamadas = cargar_registro_llamadas()
            
            ventas_mes = 0
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio_mes <= fecha <= fecha_hoy:
                    if username in datos_dia:
                        ventas_mes += datos_dia[username].get("ventas", 0)
            
            # Calcular progreso
            progreso_individual = (ventas_mes / objetivo_individual * 100) if objetivo_individual > 0 else 0
            ventas_restantes = max(0, objetivo_individual - ventas_mes)
            
            # Ventas por día laborable necesarias
            ventas_dia_laborable_necesarias = ventas_restantes / max(dias_laborables_restantes, 1)
            
            # Mostrar métricas principales
            col_met1, col_met2 = st.columns(2)
            
            with col_met1:
                st.metric(
                    "Mi Objetivo",
                    objetivo_individual,
                    help="Objetivo personal de ventas este mes"
                )
            
            with col_met2:
                st.metric(
                    "Ventas Actuales",
                    ventas_mes,
                    help="Ventas realizadas este mes"
                )
            
            # Barra de progreso
            st.write("**Progreso:**")
            progreso_normalizado = min(progreso_individual / 100, 1.0)
            st.progress(progreso_normalizado)
            
            # Texto de progreso
            if progreso_individual < 50:
                emoji = "🔴"
                color = "red"
            elif progreso_individual < 80:
                emoji = "🟡"
                color = "orange"
            elif progreso_individual < 100:
                emoji = "🟢"
                color = "green"
            else:
                emoji = "🎉"
                color = "darkgreen"
            
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="color: {color}; font-weight: bold; font-size: 16px;">
                    {emoji} {progreso_individual:.1f}%
                </span>
                <br>
                <span style="font-size: 12px;">
                    {ventas_mes} de {objetivo_individual} ventas
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Información de días laborables
            st.write("**📅 Días laborables:**")
            col_dias1, col_dias2 = st.columns(2)
            
            with col_dias1:
                st.metric("Trabajados", dias_laborables_transcurridos)
            
            with col_dias2:
                st.metric("Restantes", dias_laborables_restantes)
            
            # Información adicional
            with st.expander("📊 Detalles", expanded=False):
                # Ventas restantes
                st.write(f"**Ventas restantes:** {ventas_restantes}")
                
                # Días laborables totales
                st.write(f"**Total días laborables mes:** {total_laborables_mes}")
                
                # Ventas por día laborable necesarias
                st.write(f"**Ventas/día laborable necesarias:** {ventas_dia_laborable_necesarias:.1f}")
                
                # Contribución al objetivo global
                contribucion_global = (ventas_mes / objetivo_global * 100) if objetivo_global > 0 else 0
                st.write(f"**Contribución campaña:** {contribucion_global:.1f}%")
                
                # Hoy es laborable?
                es_laborable_hoy = fecha_hoy.weekday() < 5
                st.write(f"**Hoy es laborable:** {'✅ Sí' if es_laborable_hoy else '❌ No'}")
            
            # Enlace rápido para ver detalles completos
            st.write("---")
            if st.button("📊 **Ver mi panel completo de estadísticas**", 
                        use_container_width=True, 
                        type="primary",  # Hacerlo más visible
                        help="Ver todas tus estadísticas, ventas, días laborables y progreso detallado"):
                st.session_state.mostrar_panel_personal = True
                st.rerun()
        
        else:
            # Si no es agente, mostrar solo objetivo global
            objetivo_global = configuracion.get('target_ventas_global', 100)
            
            st.metric(
                "🎯 Objetivo Campaña",
                objetivo_global,
                help="Objetivo global de ventas de la campaña"
            )

# En super_users_functions.py, añade esta función:

def mostrar_alertas_sms_en_sidebar():
    """Muestra las alertas SMS pendientes en el sidebar"""
    try:
        from database import cargar_alertas_sms
        
        alertas = cargar_alertas_sms()
        alertas_pendientes = [a for a in alertas.values() if a.get('estado') in ['pendiente', 'confirmado', 'rechazado']]
        
        if alertas_pendientes:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📱 Alertas SMS Pendientes")
            
            # Mostrar contador
            total_pendientes = len([a for a in alertas_pendientes if a.get('estado') == 'pendiente'])
            total_confirmadas = len([a for a in alertas_pendientes if a.get('estado') == 'confirmado'])
            total_rechazadas = len([a for a in alertas_pendientes if a.get('estado') == 'rechazado'])
            
            col1, col2, col3 = st.sidebar.columns(3)
            with col1:
                st.metric("⏳", total_pendientes, help="Pendientes de revisar")
            with col2:
                st.metric("✅", total_confirmadas, help="Confirmadas")
            with col3:
                st.metric("❌", total_rechazadas, help="Rechazadas")
            
            # Botón para ir a la sección
            if st.sidebar.button("📋 Ver todas las alertas", use_container_width=True):
                st.session_state.mostrar_alertas_sms = True
                st.rerun()
            
            return True
        return False
        
    except Exception as e:
        st.sidebar.error(f"Error cargando alertas: {e}")
        return False
    
def mostrar_estadisticas_agente_personal(username):
    """Muestra panel personal del agente con estadísticas, objetivos y días laborables"""
    from datetime import datetime, date, timedelta
    
    # Botón para volver (arriba a la derecha)
    col_title, col_back = st.columns([3, 1])
    with col_title:
        st.subheader("📊 Mi Panel Personal")
    with col_back:
        if st.button("← Volver", type="secondary", use_container_width=True):
            st.session_state.mostrar_panel_personal = False
            st.rerun()
    
    st.markdown("---")
    
    # Verificar si las funciones de días laborables están disponibles
    try:
        # Importar si no están en el scope global
        from super_users_functions import (
            calcular_dias_laborables_transcurridos,
            calcular_dias_laborables_restantes,
            obtener_total_dias_laborables_mes
        )
    except ImportError:
        # Si no existen, crear funciones básicas
        def calcular_dias_laborables_transcurridos(inicio, hoy):
            # Simulación básica - contar días de lunes a viernes
            return (hoy - inicio).days
        
        def calcular_dias_laborables_restantes(hoy, fin):
            return (fin - hoy).days
        
        def obtener_total_dias_laborables_mes(inicio, fin):
            return (fin - inicio).days + 1
    
    # 1. Cargar objetivos desde JSON (sistema principal)
    objetivos_data = cargar_objetivos_ventas()
    objetivos_dict = objetivos_data.get("objetivos", {})
    objetivo_individual = objetivos_dict.get(username, 10)
    
    # 2. Fechas del mes
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)
    fin_mes = (inicio_mes.replace(month=inicio_mes.month+1, day=1) - timedelta(days=1))
    
    # 3. Días laborables
    dias_transcurridos = calcular_dias_laborables_transcurridos(inicio_mes, hoy)
    dias_restantes = calcular_dias_laborables_restantes(hoy, fin_mes)
    total_dias = obtener_total_dias_laborables_mes(inicio_mes, fin_mes)
    
    # 4. Ventas del mes
    registro_llamadas = cargar_registro_llamadas()
    ventas_mes = 0
    llamadas_mes = 0
    
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if inicio_mes <= fecha <= hoy:
            if username in datos_dia:
                ventas_mes += datos_dia[username].get("ventas", 0)
                llamadas_mes += datos_dia[username].get("llamadas_15min", 0)
    
    # 5. Calcular métricas
    progreso = (ventas_mes / objetivo_individual * 100) if objetivo_individual > 0 else 0
    ventas_restantes = max(0, objetivo_individual - ventas_mes)
    ventas_dia_necesarias = ventas_restantes / max(dias_restantes, 1)
    ratio_ventas = (ventas_mes / llamadas_mes * 100) if llamadas_mes > 0 else 0
    
    # 6. Mostrar KPI principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Mi Objetivo", objetivo_individual)
    
    with col2:
        st.metric("💰 Ventas Mes", ventas_mes)
    
    with col3:
        st.metric("📞 Llamadas >15min", llamadas_mes)
    
    with col4:
        st.metric("📈 Ratio", f"{ratio_ventas:.1f}%")
    
    # 7. Progreso vs objetivo
    st.write("#### 📊 Progreso del Mes")
    progreso_normalizado = min(progreso / 100, 1.0)
    st.progress(progreso_normalizado)
    
    col_prog1, col_prog2, col_prog3 = st.columns(3)
    with col_prog1:
        st.metric("Progreso", f"{progreso:.1f}%")
    with col_prog2:
        st.metric("Ventas Restantes", ventas_restantes)
    with col_prog3:
        st.metric("Días Restantes", dias_restantes)
    
    # 8. Días laborables
    st.write("#### 📅 Días Laborables")
    st.info(f"""
    - **Días laborables transcurridos:** {dias_transcurridos} de {total_dias}
    - **Días laborables restantes:** {dias_restantes}
    - **Ventas necesarias por día laborable:** {ventas_dia_necesarias:.2f}
    """)
    
    # 9. Performance diaria
    if dias_transcurridos > 0:
        ventas_por_dia = ventas_mes / dias_transcurridos
        st.write(f"**📈 Ventas por día laborable:** {ventas_por_dia:.2f}")
        
        if ventas_por_dia < ventas_dia_necesarias:
            st.warning(f"⚠️ Necesitas aumentar el ritmo de {ventas_por_dia:.2f} a {ventas_dia_necesarias:.2f} ventas/día")
        else:
            st.success(f"✅ Vas bien! Mantén el ritmo de {ventas_por_dia:.2f} ventas/día")