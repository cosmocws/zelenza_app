import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from database import (
    cargar_super_users, guardar_super_users,
    cargar_registro_llamadas, guardar_registro_llamadas,
    cargar_configuracion_usuarios, cargar_config_sistema
)
from utils import obtener_hora_madrid, formatear_hora_madrid

def gestion_super_users_admin():
    """Panel de administración para gestionar super usuarios"""
    st.subheader("👑 Gestión de Super Usuarios")
    
    # Cargar datos
    super_users_config = cargar_super_users()
    usuarios_config = cargar_configuracion_usuarios()
    
    tab1, tab2, tab3 = st.tabs(["👑 Super Usuarios", "👥 Agentes", "⚙️ Configuración"])
    
    with tab1:
        st.write("### 👑 Lista de Super Usuarios")
        st.info("Los super usuarios pueden ver y gestionar métricas de agentes")
        
        # Lista actual de super usuarios
        super_users_list = super_users_config.get("super_users", [])
        
        col_lista1, col_lista2 = st.columns([2, 1])
        
        with col_lista1:
            st.write("**Super usuarios actuales:**")
            if super_users_list:
                for user in super_users_list:
                    nombre = usuarios_config.get(user, {}).get('nombre', user)
                    st.write(f"• **{user}** - {nombre}")
            else:
                st.info("No hay super usuarios configurados (solo admin)")
        
        with col_lista2:
            st.write("**Acciones:**")
            if st.button("➕ Añadir Super Usuario", use_container_width=True):
                st.session_state.creando_super_user = True
                st.rerun()
        
        # Formulario para añadir super usuario
        if st.session_state.get('creando_super_user', False):
            st.write("### ➕ Añadir Nuevo Super Usuario")
            
            # Lista de usuarios disponibles (excluyendo admin y super usuarios existentes)
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
        
        # Opción para quitar super usuario
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
    
    with tab2:
        st.write("### 👥 Gestión de Agentes")
        
        # Cargar agentes actuales
        agentes = super_users_config.get("agentes", {})
        super_users_list = super_users_config.get("super_users", [])
        
        col_agentes1, col_agentes2 = st.columns(2)
        
        with col_agentes1:
            st.write("**Agentes registrados:**")
            if agentes:
                for agent_id, info in agentes.items():
                    estado = "✅ Activo" if info.get('activo', True) else "❌ Inactivo"
                    grupo = info.get('grupo', 'Sin grupo')
                    supervisor = info.get('supervisor', 'Sin asignar')
                    st.write(f"• **{agent_id}** - {info.get('nombre', 'Sin nombre')} ({estado})")
                    st.write(f"  Grupo: {grupo} | Supervisor: {supervisor}")
            else:
                st.info("No hay agentes registrados")
        
        with col_agentes2:
            st.write("**Añadir agentes:**")
            if st.button("➕ Añadir desde Usuarios", use_container_width=True):
                st.session_state.añadiendo_agentes = True
                st.rerun()
        
        # Formulario para añadir agentes desde usuarios existentes
        if st.session_state.get('añadiendo_agentes', False):
            st.write("### ➕ Añadir Agentes desde Usuarios")
            
            # Usuarios disponibles (excluyendo admin y ya añadidos como agentes)
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
                # Mostrar tabla de usuarios disponibles
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
                
                # Contar seleccionados
                seleccionados = edited_df[edited_df['Seleccionar']]
                
                # Seleccionar supervisor para los nuevos agentes
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
        
        # Sección para editar/borrar agentes
        if agentes:
            st.write("---")
            st.write("### 🔧 Editar/Borrar Agentes")
            
            # Seleccionar agente a editar
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
                    col_edit1, col_edit2 = st.columns(2)
                    
                    with col_edit1:
                        # Información básica editable
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
                        # Verificar si el tipo actual está en la lista
                        if tipo_actual not in tipos_permitidos:
                            tipo_actual = 'user'  # Valor por defecto si no está en la lista

                        tipo_editado = st.selectbox(
                            "Tipo:",
                            tipos_permitidos,
                            index=tipos_permitidos.index(tipo_actual),
                            key=f"edit_tipo_{agent_id}"
                        )
                    
                    with col_edit2:
                        # Estado y supervisor
                        activo_editado = st.checkbox(
                            "Activo",
                            value=info_agente.get('activo', True),
                            key=f"edit_activo_{agent_id}"
                        )
                        
                        # Asignar supervisor
                        opciones_supervisor = ['Sin asignar'] + super_users_list
                        supervisor_actual = info_agente.get('supervisor', '')
                        
                        # Encontrar índice actual
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
                        
                        # Mostrar información de registro
                        if 'fecha_registro' in info_agente:
                            st.info(f"📅 Registrado: {info_agente['fecha_registro']}")
                    
                    # Botones de acción
                    col_btn_edit1, col_btn_edit2, col_btn_edit3 = st.columns(3)
                    
                    with col_btn_edit1:
                        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                            # Actualizar información del agente
                            agentes[agent_id] = {
                                'nombre': nombre_editado,
                                'grupo': grupo_editado,
                                'tipo': tipo_editado,
                                'activo': activo_editado,
                                'supervisor': supervisor_editado if supervisor_editado != 'Sin asignar' else '',
                                'fecha_registro': info_agente.get('fecha_registro', datetime.now().strftime("%Y-%m-%d")),
                                'fecha_actualizacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            super_users_config["agentes"] = agentes
                            guardar_super_users(super_users_config)
                            st.success(f"✅ Agente {nombre_editado} actualizado correctamente")
                            st.rerun()
                    
                    with col_btn_edit2:
                        # Ver historial del agente
                        if st.button("📊 Ver Historial", type="secondary", use_container_width=True):
                            st.session_state.ver_historial_agente = agent_id
                            st.rerun()
                    
                    with col_btn_edit3:
                        # Botón para borrar agente
                        if st.button("🗑️ Borrar Agente", type="secondary", use_container_width=True):
                            st.session_state.agente_a_borrar = agent_id
                            st.rerun()
        
        # Confirmación de borrado de agente
        if st.session_state.get('agente_a_borrar'):
            agent_id = st.session_state.agente_a_borrar
            info_agente = agentes.get(agent_id, {})
            nombre_agente = info_agente.get('nombre', agent_id)
            
            st.warning(f"⚠️ **CONFIRMAR BORRADO DEL AGENTE: {nombre_agente}**")
            
            # Cargar registro de llamadas para verificar datos históricos
            registro_llamadas = cargar_registro_llamadas()
            
            # Contar registros históricos del agente
            registros_historicos = 0
            for fecha_str, datos_dia in registro_llamadas.items():
                if agent_id in datos_dia:
                    registros_historicos += 1
            
            st.write(f"**📊 Este agente tiene:**")
            st.write(f"• {registros_historicos} día(s) de registro histórico")
            st.write(f"• Grupo: {info_agente.get('grupo', 'Sin grupo')}")
            st.write(f"• Supervisor: {info_agente.get('supervisor', 'Sin asignar')}")
            
            st.write("**⚠️ ADVERTENCIA:** Al borrar este agente:")
            st.write("1. Se eliminará permanentemente de la lista de agentes")
            st.write("2. Se perderán TODOS sus datos históricos de llamadas y ventas")
            st.write("3. Esta acción NO se puede deshacer")
            
            col_conf1, col_conf2 = st.columns(2)
            
            with col_conf1:
                if st.button("✅ **SÍ, BORRAR DEFINITIVAMENTE**", type="primary", use_container_width=True):
                    # Eliminar agente
                    del agentes[agent_id]
                    super_users_config["agentes"] = agentes
                    guardar_super_users(super_users_config)
                    
                    # Eliminar datos históricos del agente
                    for fecha_str, datos_dia in registro_llamadas.items():
                        if agent_id in datos_dia:
                            del registro_llamadas[fecha_str][agent_id]
                    
                    guardar_registro_llamadas(registro_llamadas)
                    
                    st.success(f"✅ Agente {nombre_agente} borrado correctamente")
                    st.success(f"✅ {registros_historicos} registros históricos eliminados")
                    
                    # Limpiar estado
                    st.session_state.agente_a_borrar = None
                    st.rerun()
            
            with col_conf2:
                if st.button("❌ **NO, CANCELAR**", type="secondary", use_container_width=True):
                    st.session_state.agente_a_borrar = None
                    st.info("❌ Borrado cancelado")
                    st.rerun()
    
    with tab3:
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
                "Target mensual de llamadas:",
                min_value=1,
                max_value=1000,
                value=config_actual.get("target_llamadas", 50)
            )
            
            target_ventas = st.number_input(
                "Target mensual de ventas:",
                min_value=1,
                max_value=500,
                value=config_actual.get("target_ventas", 10)
            )
        
        metrica = st.selectbox(
            "Métrica de eficiencia:",
            ["ratio", "total", "ponderado"],
            index=["ratio", "total", "ponderado"].index(config_actual.get("metrica_eficiencia", "ratio")),
            help="Ratio: ventas/llamadas | Total: sumatoria | Ponderado: (ventas*2 + llamadas*1)"
        )
        
        # Nueva opción: modo de visualización para super usuarios
        mostrar_solo_mis_agentes = st.checkbox(
            "Super usuarios ven solo sus agentes asignados",
            value=config_actual.get("mostrar_solo_mis_agentes", False),
            help="Si está activado, cada super usuario solo verá los agentes que tiene asignados"
        )
        
        if st.button("💾 Guardar Configuración", type="primary"):
            nueva_config = {
                "duracion_minima_llamada": duracion_minima,
                "periodo_mensual": periodo,
                "target_llamadas": target_llamadas,
                "target_ventas": target_ventas,
                "metrica_eficiencia": metrica,
                "mostrar_solo_mis_agentes": mostrar_solo_mis_agentes
            }
            
            super_users_config["configuracion"] = nueva_config
            guardar_super_users(super_users_config)
            st.success("✅ Configuración guardada")
            st.rerun()

def panel_super_usuario():
    """Panel principal para super usuarios"""
    st.header("📊 Panel de Super Usuario")
    
    # Cargar datos
    super_users_config = cargar_super_users()
    configuracion = super_users_config.get("configuracion", {})
    username = st.session_state.get('username', '')
    
    # Filtrar agentes según configuración y supervisor actual
    agentes_completos = super_users_config.get("agentes", {})
    
    if configuracion.get("mostrar_solo_mis_agentes", False) and username:
        # Filtrar solo agentes asignados a este super usuario
        agentes = {k: v for k, v in agentes_completos.items() 
                  if v.get('supervisor', '') == username}
    else:
        # Mostrar todos los agentes (modo administrador)
        agentes = agentes_completos
    
    registro_llamadas = cargar_registro_llamadas()
    
    if not agentes:
        st.warning("⚠️ No hay agentes asignados a tu supervisión.")
        
        # Si está en modo filtrado pero no hay agentes, mostrar opción para ver todos
        if configuracion.get("mostrar_solo_mis_agentes", False) and username:
            if st.button("👁️ Ver todos los agentes"):
                # Cambiar temporalmente la configuración para ver todos
                st.session_state.modo_temporal_todos = True
                st.rerun()
        
        # Modo temporal para ver todos los agentes
        if st.session_state.get('modo_temporal_todos', False):
            agentes = agentes_completos
            if not agentes:
                st.warning("⚠️ No hay agentes configurados en el sistema. Contacta al administrador.")
                return
            else:
                st.info("👁️ **Modo temporal:** Viendo todos los agentes del sistema")
    else:
        # Si hay agentes, asegurarse de que no estamos en modo temporal
        st.session_state.modo_temporal_todos = False
    
    # CREAR PESTAÑAS (AGREGAR PESTAÑA DE IMPORTACIÓN)
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
        if username:  # Solo si hay un usuario identificado
            gestion_agentes_super_usuario_edicion(agentes, super_users_config, username)
        else:
            st.warning("⚠️ Debes iniciar sesión como super usuario para acceder a esta sección")
    
    with tab6:
        # Importar funcionalidad del analizador
        from llamadas_analyzer import interfaz_analisis_llamadas
        
        # Mostrar versión simplificada para super usuarios
        st.subheader("📥 Importar CSV de Llamadas")
        
        st.info("""
        **Importa datos de llamadas automáticamente al registro diario:**
        - 📞 Llamadas de más de 15 minutos se cuentan como "llamadas"
        - 💰 Cada "UTIL POSITIVO" cuenta como venta (pueden ser 2 si es DÚO)
        - 📅 Los datos se suman a los registros existentes
        """)
        
        # Opción para usar el analizador completo
        if st.button("🚀 Abrir Analizador Completo", type="primary"):
            st.session_state.mostrar_analizador_completo = True
        
        if st.session_state.get('mostrar_analizador_completo', False):
            # Mostrar interfaz completa del analizador
            interfaz_analisis_llamadas()
        else:
            # Mostrar versión simplificada
            uploaded_file = st.file_uploader(
                "📤 Sube archivo CSV/TXT de llamadas",
                type=['csv', 'txt'],
                help="Archivo con columnas: agente, tiempo_conversacion, resultado_elec, resultado_gas, fecha, campanya"
            )
            
            if uploaded_file is not None:
                # Analizar y importar directamente
                from llamadas_analyzer import analizar_csv_llamadas, importar_datos_a_registro
                
                with st.spinner("Analizando archivo..."):
                    df = analizar_csv_llamadas(uploaded_file)
                    
                    if df is not None:
                        # Mostrar vista previa
                        st.success("✅ Archivo cargado correctamente")
                        
                        # Estadísticas rápidas
                        llamadas_largas = len(df[df['tiempo_conversacion'] > 900])
                        agentes_unicos = df['agente'].nunique()
                        fechas_unicas = df['fecha'].nunique()
                        
                        # Contar ventas
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
                        
                        # Botón para importar
                        if st.button("📥 Importar Datos al Sistema", type="primary"):
                            with st.spinner("Importando datos..."):
                                exito, mensaje = importar_datos_a_registro(df, super_users_config)
                                
                                if exito:
                                    st.success("✅ Datos importados exitosamente")
                                    for linea in mensaje.split('\n'):
                                        if linea.strip():
                                            st.write(linea)
                                else:
                                    st.error(f"❌ Error: {mensaje}")

    with tab7:
        panel_monitorizaciones_super_usuario()

def gestion_registro_diario(agentes, registro_llamadas, configuracion):
    """Registro diario de llamadas y ventas"""
    st.subheader("📅 Registro Diario")
    
    # Seleccionar fecha
    fecha_hoy = datetime.now().date()
    fecha_seleccionada = st.date_input(
        "Fecha:",
        value=fecha_hoy,
        max_value=fecha_hoy
    )
    
    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
    
    # Obtener datos del día seleccionado
    datos_dia = registro_llamadas.get(fecha_str, {})
    
    st.write(f"### 📝 Registro para {fecha_seleccionada.strftime('%d/%m/%Y')}")
    
    # Opciones de ordenación
    col_orden1, col_orden2 = st.columns([1, 3])
    with col_orden1:
        orden_por = st.selectbox(
            "Ordenar por:",
            ["Username (ID)", "Nombre", "Grupo"],
            index=0,  # Por defecto ordenar por username
            key="orden_registro"
        )
    with col_orden2:
        st.caption("💡 Orden alfabético por username facilita encontrar agentes por su número (ej: 0001, 0002, etc.)")
    
    # Preparar lista de agentes ordenada
    agentes_lista = []
    for agent_id, info in agentes.items():
        if info.get('activo', True):  # Solo agentes activos
            agentes_lista.append({
                'id': agent_id,
                'nombre': info.get('nombre', agent_id),
                'grupo': info.get('grupo', 'Sin grupo')
            })
    
    # Ordenar según la opción seleccionada
    if orden_por == "Username (ID)":
        agentes_lista.sort(key=lambda x: x['id'])
    elif orden_por == "Nombre":
        agentes_lista.sort(key=lambda x: x['nombre'])
    elif orden_por == "Grupo":
        agentes_lista.sort(key=lambda x: (x['grupo'], x['id']))
    
    # Contador para estadísticas
    total_agentes = len(agentes_lista)
    agentes_con_datos = 0
    
    # Crear formulario para cada agente
    with st.form("form_registro_diario"):
        registros = []
        
        for i, agente in enumerate(agentes_lista, 1):
            agent_id = agente['id']
            nombre = agente['nombre']
            grupo = agente['grupo']
            
            # Obtener valores actuales
            datos_agente = datos_dia.get(agent_id, {"llamadas": 0, "ventas": 0})
            
            # Verificar si tiene datos previos
            tiene_datos_previos = datos_agente.get("llamadas", 0) > 0 or datos_agente.get("ventas", 0) > 0
            if tiene_datos_previos:
                agentes_con_datos += 1
            
            # Mostrar con número de orden
            col_agent1, col_agent2, col_agent3 = st.columns([4, 2, 2])
            
            with col_agent1:
                # Mostrar número de orden y username en pequeñito
                st.write(f"**#{i:03d} - {nombre}**")
                st.caption(f"🆔 {agent_id} | 👥 {grupo}")
                
                # Indicador visual si tiene datos previos
                if tiene_datos_previos:
                    st.caption("📝 Tiene datos previos")
            
            with col_agent2:
                llamadas = st.number_input(
                    f"Llamadas >{configuracion.get('duracion_minima_llamada', 15)}min",
                    min_value=0,
                    max_value=100,
                    value=datos_agente.get("llamadas", 0),
                    key=f"llamadas_{agent_id}_{fecha_str}",
                    help=f"Llamadas para {nombre} ({agent_id})"
                )
            
            with col_agent3:
                ventas = st.number_input(
                    "Ventas",
                    min_value=0,
                    max_value=50,
                    value=datos_agente.get("ventas", 0),
                    key=f"ventas_{agent_id}_{fecha_str}",
                    help=f"Ventas para {nombre} ({agent_id})"
                )
            
            # Línea separadora entre agentes (excepto el último)
            if i < total_agentes:
                st.markdown("---")
            
            registros.append({
                'agent_id': agent_id,
                'llamadas': llamadas,
                'ventas': ventas
            })
        
        # Estadísticas antes del botón de guardar
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("Total Agentes", total_agentes)
        with col_stats2:
            st.metric("Con Datos", agentes_con_datos)
        with col_stats3:
            st.metric("Sin Datos", total_agentes - agentes_con_datos)
        
        submitted = st.form_submit_button("💾 Guardar Registro Diario", type="primary")
        
        if submitted:
            # Actualizar registro
            if fecha_str not in registro_llamadas:
                registro_llamadas[fecha_str] = {}
            
            for registro in registros:
                registro_llamadas[fecha_str][registro['agent_id']] = {
                    'llamadas': registro['llamadas'],
                    'ventas': registro['ventas'],
                    'fecha': fecha_str,
                    'timestamp': datetime.now().isoformat()
                }
            
            guardar_registro_llamadas(registro_llamadas)
            st.success("✅ Registro diario guardado correctamente")
            st.rerun()

def mostrar_metricas_mensuales(agentes, registro_llamadas, configuracion):
    """Muestra métricas mensuales de agentes"""
    st.subheader("📊 Métricas Mensuales")
    
    # Seleccionar periodo
    col_periodo1, col_periodo2 = st.columns(2)
    
    with col_periodo1:
        periodo_tipo = configuracion.get("periodo_mensual", "calendario")
        if periodo_tipo == "calendario":
            # Mes natural - usar un enfoque diferente
            st.write("**Seleccionar mes:**")
            
            # Crear selector de año y mes
            año_actual = datetime.now().year
            mes_actual = datetime.now().month
            
            col_anio, col_mes = st.columns(2)
            
            with col_anio:
                año_seleccionado = st.selectbox(
                    "Año:",
                    range(año_actual - 1, año_actual + 2),
                    index=1,  # año actual por defecto
                    key="selector_anio"
                )
            
            with col_mes:
                meses = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ]
                mes_seleccionado = st.selectbox(
                    "Mes:",
                    meses,
                    index=mes_actual - 1,
                    key="selector_mes"
                )
                mes_numero = meses.index(mes_seleccionado) + 1
            
            # Calcular fechas
            fecha_inicio = datetime(año_seleccionado, mes_numero, 1).date()
            fecha_fin = (fecha_inicio + relativedelta(months=1)) - timedelta(days=1)
            
            st.info(f"**Periodo:** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
            
        else:
            # Rolling 30 días
            dias_atras = st.number_input("Últimos N días:", min_value=7, max_value=90, value=30)
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=dias_atras)
            
            st.info(f"**Periodo (rolling):** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    with col_periodo2:
        st.write("**Targets:**")
        st.write(f"• Llamadas: {configuracion.get('target_llamadas', 50)}")
        st.write(f"• Ventas: {configuracion.get('target_ventas', 10)}")
    
    # Calcular métricas para el periodo
    st.write("### 📈 Métricas del Período")
    
    metricas_agentes = []
    
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            nombre = info.get('nombre', agent_id)
            grupo = info.get('grupo', 'Sin grupo')
            supervisor = info.get('supervisor', 'Sin asignar')
            
            # Calcular totales del periodo
            total_llamadas = 0
            total_ventas = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        total_llamadas += datos_dia[agent_id].get("llamadas", 0)
                        total_ventas += datos_dia[agent_id].get("ventas", 0)
            
            # Calcular métricas
            target_llamadas = configuracion.get("target_llamadas", 50)
            target_ventas = configuracion.get("target_ventas", 10)
            
            cumplimiento_llamadas = (total_llamadas / target_llamadas * 100) if target_llamadas > 0 else 0
            cumplimiento_ventas = (total_ventas / target_ventas * 100) if target_ventas > 0 else 0
            
            # Calcular eficiencia según métrica seleccionada
            metrica_tipo = configuracion.get("metrica_eficiencia", "ratio")
            eficiencia = 0
            
            if metrica_tipo == "ratio":
                eficiencia = (total_ventas / total_llamadas * 100) if total_llamadas > 0 else 0
            elif metrica_tipo == "total":
                eficiencia = total_ventas * 10 + total_llamadas  # Ponderación
            elif metrica_tipo == "ponderado":
                eficiencia = total_ventas * 2 + total_llamadas
            
            metricas_agentes.append({
                'Agente': nombre,
                'Grupo': grupo,
                'Supervisor': supervisor,
                'Llamadas': total_llamadas,
                'Ventas': total_ventas,
                'Ratio (%)': f"{(total_ventas/total_llamadas*100):.1f}" if total_llamadas > 0 else "0.0",
                'Cump. Llamadas (%)': f"{cumplimiento_llamadas:.1f}",
                'Cump. Ventas (%)': f"{cumplimiento_ventas:.1f}",
                'Eficiencia': f"{eficiencia:.1f}",
                'Estado': '✅' if cumplimiento_llamadas >= 100 and cumplimiento_ventas >= 100 else '⚠️'
            })
    
    # Mostrar tabla
    if metricas_agentes:
        df_metricas = pd.DataFrame(metricas_agentes)
        
        # Ordenar por eficiencia
        df_metricas['Eficiencia_num'] = df_metricas['Eficiencia'].str.replace('%', '').astype(float)
        df_metricas = df_metricas.sort_values('Eficiencia_num', ascending=False)
        df_metricas = df_metricas.drop('Eficiencia_num', axis=1)
        
        st.dataframe(df_metricas, use_container_width=True)
        
        # Exportar opciones
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            csv = df_metricas.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"metricas_{fecha_inicio}_{fecha_fin}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_export2:
            if st.button("📊 Generar Gráficos", use_container_width=True):
                st.session_state.mostrar_graficos = True
                st.rerun()
        
        # Gráficos si están activados
        if st.session_state.get('mostrar_graficos', False):
            mostrar_graficos_metricas(df_metricas)
    else:
        st.info("No hay datos para el período seleccionado")

def mostrar_dashboard(agentes, registro_llamadas, configuracion):
    """Dashboard interactivo de métricas"""
    st.subheader("📈 Dashboard de Desempeño")
    
    # Mostrar información de contexto
    username = st.session_state.get('username', '')
    st.info(f"👑 **Supervisor:** {username} | 👥 **Agentes supervisados:** {len(agentes)}")
    
    # Métricas generales
    st.write("### 📊 Métricas Globales")
    
    # Calcular métricas del mes actual
    fecha_inicio = datetime.now().date().replace(day=1)
    fecha_fin = datetime.now().date()
    
    total_llamadas = 0
    total_ventas = 0
    agentes_activos = sum(1 for a in agentes.values() if a.get('activo', True))
    
    for fecha_str, datos_dia in registro_llamadas.items():
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            for agent_id, datos_agente in datos_dia.items():
                if agent_id in agentes:  # Solo contar agentes supervisados
                    total_llamadas += datos_agente.get("llamadas", 0)
                    total_ventas += datos_agente.get("ventas", 0)
    
    # Mostrar KPIs
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    with col_kpi1:
        st.metric("👥 Agentes Activos", agentes_activos)
    
    with col_kpi2:
        st.metric("📞 Llamadas Total", total_llamadas)
    
    with col_kpi3:
        st.metric("💰 Ventas Total", total_ventas)
    
    with col_kpi4:
        ratio = (total_ventas / total_llamadas * 100) if total_llamadas > 0 else 0
        st.metric("📈 Ratio Conversión", f"{ratio:.1f}%")
    
    # Gráfico de tendencia diaria
    st.write("### 📅 Tendencia Diaria")
    
    # Preparar datos para gráfico
    fechas = []
    llamadas_diarias = []
    ventas_diarias = []
    
    # Obtener últimos 30 días
    fecha_hoy = datetime.now().date()
    fecha_30_dias_atras = fecha_hoy - timedelta(days=30)
    
    for fecha_str in sorted(registro_llamadas.keys()):
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_30_dias_atras <= fecha <= fecha_hoy:
            total_dia_llamadas = 0
            total_dia_ventas = 0
            
            for agent_id, datos_agente in registro_llamadas[fecha_str].items():
                if agent_id in agentes:  # Solo contar agentes supervisados
                    total_dia_llamadas += datos_agente.get("llamadas", 0)
                    total_dia_ventas += datos_agente.get("ventas", 0)
            
            fechas.append(fecha.strftime("%d/%m"))
            llamadas_diarias.append(total_dia_llamadas)
            ventas_diarias.append(total_dia_ventas)
    
    if fechas:
        # Crear DataFrame para el gráfico
        df_tendencia = pd.DataFrame({
            'Fecha': fechas,
            'Llamadas': llamadas_diarias,
            'Ventas': ventas_diarias
        })
        
        # Mostrar gráfico usando st.line_chart
        st.line_chart(df_tendencia.set_index('Fecha'))
    else:
        st.info("No hay datos de tendencia para los últimos 30 días")
    
    # Ranking de agentes
    st.write("### 🏆 Ranking de Agentes (Este Mes)")
    
    ranking_data = []
    
    for agent_id, info in agentes.items():
        if info.get('activo', True):
            nombre = info.get('nombre', agent_id)
            
            # Calcular métricas del mes
            llamadas_mes = 0
            ventas_mes = 0
            
            for fecha_str, datos_dia in registro_llamadas.items():
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                if fecha_inicio <= fecha <= fecha_fin:
                    if agent_id in datos_dia:
                        llamadas_mes += datos_dia[agent_id].get("llamadas", 0)
                        ventas_mes += datos_dia[agent_id].get("ventas", 0)
            
            if llamadas_mes > 0:
                ratio = (ventas_mes / llamadas_mes * 100)
                
                ranking_data.append({
                    'Agente': nombre,
                    'Llamadas': llamadas_mes,
                    'Ventas': ventas_mes,
                    'Ratio': f"{ratio:.1f}%",
                    'Puntos': ventas_mes * 10 + llamadas_mes
                })
    
    if ranking_data:
        df_ranking = pd.DataFrame(ranking_data)
        df_ranking = df_ranking.sort_values('Puntos', ascending=False)
        
        # Mostrar top 10
        st.dataframe(df_ranking.head(10), use_container_width=True)
    else:
        st.info("No hay datos de ranking para este mes")

def gestion_agentes_super_usuario(agentes, super_users_config):
    """Gestión de agentes desde el panel de super usuario"""
    st.subheader("👥 Gestión de Agentes")
    
    username = st.session_state.get('username', '')
    
    # Mostrar información del super usuario actual
    if username:
        st.info(f"👑 **Supervisor actual:** {username}")
    
    # Contadores
    agentes_activos = sum(1 for a in agentes.values() if a.get('activo', True))
    agentes_inactivos = len(agentes) - agentes_activos
    
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        st.metric("✅ Agentes Activos", agentes_activos)
    with col_stats2:
        st.metric("❌ Agentes Inactivos", agentes_inactivos)
    
    # Mostrar lista de agentes con opciones
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        supervisor = info.get('supervisor', 'Sin asignar')
        activo = info.get('activo', True)
        
        with st.expander(f"{'✅' if activo else '❌'} {nombre} ({grupo}) - Supervisor: {supervisor}", expanded=False):
            col_agent1, col_agent2 = st.columns(2)
            
            with col_agent1:
                st.write("**Información:**")
                st.write(f"• ID: {agent_id}")
                st.write(f"• Grupo: {grupo}")
                st.write(f"• Supervisor: {supervisor}")
                st.write(f"• Estado: {'Activo' if activo else 'Inactivo'}")
                st.write(f"• Tipo: {info.get('tipo', 'user')}")
                
                if 'fecha_registro' in info:
                    st.write(f"• Registrado: {info['fecha_registro']}")
            
            with col_agent2:
                st.write("**Acciones:**")
                
                # Toggle activo/inactivo
                nuevo_estado = st.checkbox("Activo", value=activo, key=f"activo_{agent_id}")
                
                if nuevo_estado != activo:
                    if st.button("💾 Actualizar Estado", key=f"update_estado_{agent_id}"):
                        agentes[agent_id]['activo'] = nuevo_estado
                        super_users_config["agentes"] = agentes
                        guardar_super_users(super_users_config)
                        st.success(f"✅ Estado actualizado para {nombre}")
                        st.rerun()
                
                # Ver historial
                if st.button("📊 Ver Historial", key=f"historial_{agent_id}"):
                    st.session_state.ver_historial_agente = agent_id
                    st.rerun()
    
    # Ver historial de agente específico
    if st.session_state.get('ver_historial_agente'):
        agent_id = st.session_state.ver_historial_agente
        info = agentes.get(agent_id, {})
        nombre = info.get('nombre', agent_id)
        
        st.write(f"### 📊 Historial de {nombre}")
        
        # Cargar registro de llamadas
        registro_llamadas = cargar_registro_llamadas()
        
        # Filtrar datos del agente
        datos_agente = []
        
        for fecha_str, datos_dia in registro_llamadas.items():
            if agent_id in datos_dia:
                datos = datos_dia[agent_id]
                datos_agente.append({
                    'Fecha': fecha_str,
                    'Llamadas': datos.get('llamadas', 0),
                    'Ventas': datos.get('ventas', 0)
                })
        
        if datos_agente:
            df_historial = pd.DataFrame(datos_agente)
            df_historial = df_historial.sort_values('Fecha', ascending=False)
            
            st.dataframe(df_historial, use_container_width=True)
            
            # Calcular totales
            total_llamadas = df_historial['Llamadas'].sum()
            total_ventas = df_historial['Ventas'].sum()
            
            col_tot1, col_tot2, col_tot3 = st.columns(3)
            with col_tot1:
                st.metric("Total Llamadas", total_llamadas)
            with col_tot2:
                st.metric("Total Ventas", total_ventas)
            with col_tot3:
                ratio = (total_ventas / total_llamadas * 100) if total_llamadas > 0 else 0
                st.metric("Ratio", f"{ratio:.1f}%")
        else:
            st.info("No hay datos históricos para este agente")
        
        if st.button("← Volver a lista"):
            st.session_state.ver_historial_agente = None
            st.rerun()

def gestion_agentes_super_usuario_edicion(agentes, super_users_config, super_user_actual):
    """Gestión de agentes para super usuarios (edición limitada)"""
    st.subheader("🔧 Edición de Mis Agentes")
    
    # Filtrar agentes asignados a este super usuario
    agentes_asignados = {k: v for k, v in agentes.items() 
                        if v.get('supervisor', '') == super_user_actual}
    
    if not agentes_asignados:
        st.info(f"ℹ️ No tienes agentes asignados como supervisor. Los agentes asignados a ti aparecerán aquí.")
        return
    
    st.info(f"👑 **Supervisor:** {super_user_actual} | 👥 **Agentes asignados:** {len(agentes_asignados)}")
    
    # Seleccionar agente a editar
    agentes_options = [f"{agent_id} - {info.get('nombre', 'Sin nombre')}" 
                      for agent_id, info in agentes_asignados.items()]
    
    agente_seleccionado = st.selectbox(
        "Seleccionar agente a editar:",
        agentes_options,
        key="select_agente_super_editar"
    )
    
    if agente_seleccionado:
        agent_id = agente_seleccionado.split(" - ")[0]
        info_agente = agentes[agent_id]
        
        st.write(f"### ✏️ Editar agente: {info_agente.get('nombre', agent_id)}")
        
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            # Super usuario solo puede editar información básica
            nombre_editado = st.text_input(
                "Nombre:",
                value=info_agente.get('nombre', ''),
                key=f"super_nombre_{agent_id}"
            )
            
            grupo_editado = st.text_input(
                "Grupo:",
                value=info_agente.get('grupo', ''),
                key=f"super_grupo_{agent_id}"
            )
        
        with col_edit2:
            # Solo puede cambiar estado activo/inactivo
            activo_editado = st.checkbox(
                "Activo",
                value=info_agente.get('activo', True),
                key=f"super_activo_{agent_id}"
            )
            
            # Mostrar información de solo lectura
            st.info(f"🆔 **Usuario ID:** {agent_id}")
            st.info(f"👤 **Tipo:** {info_agente.get('tipo', 'user')}")
            st.info(f"👑 **Supervisor:** {info_agente.get('supervisor', 'Sin asignar')}")
            
            if 'fecha_registro' in info_agente:
                st.caption(f"📅 Registrado: {info_agente['fecha_registro']}")
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                # Actualizar solo campos permitidos
                agentes[agent_id]['nombre'] = nombre_editado
                agentes[agent_id]['grupo'] = grupo_editado
                agentes[agent_id]['activo'] = activo_editado
                agentes[agent_id]['fecha_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Actualizar en la configuración completa
                super_users_config_completo = cargar_super_users()
                super_users_config_completo["agentes"] = agentes
                guardar_super_users(super_users_config_completo)
                
                st.success(f"✅ Agente {nombre_editado} actualizado correctamente")
                st.rerun()
        
        with col_btn2:
            if st.button("📊 Ver Historial Completo", type="secondary", use_container_width=True):
                st.session_state.ver_historial_agente = agent_id
                st.rerun()
        
        with col_btn3:
            if st.button("🔄 Reiniciar Métricas", type="secondary", use_container_width=True):
                st.warning("⚠️ Esta acción reiniciará las métricas del mes actual para este agente")
                
                # Confirmación
                col_conf1, col_conf2 = st.columns(2)
                with col_conf1:
                    if st.button("✅ Sí, reiniciar"):
                        # Aquí podrías agregar lógica para reiniciar métricas
                        st.success(f"✅ Métricas de {info_agente.get('nombre', agent_id)} reiniciadas")
                        st.rerun()
                with col_conf2:
                    if st.button("❌ No, cancelar"):
                        st.rerun()

def mostrar_graficos_metricas(df_metricas):
    """Muestra gráficos de métricas"""
    st.write("### 📊 Visualización de Datos")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        # Gráfico de barras para llamadas
        df_llamadas = df_metricas[['Agente', 'Llamadas']].copy()
        df_llamadas['Llamadas'] = df_llamadas['Llamadas'].astype(int)
        st.bar_chart(df_llamadas.set_index('Agente'))
        st.caption("Llamadas por Agente")
    
    with col_graf2:
        # Gráfico de barras para ventas
        df_ventas = df_metricas[['Agente', 'Ventas']].copy()
        df_ventas['Ventas'] = df_ventas['Ventas'].astype(int)
        st.bar_chart(df_ventas.set_index('Agente'))
        st.caption("Ventas por Agente")
    
    # Gráfico de ratio
    st.write("#### 📈 Ratio de Conversión")
    df_ratio = df_metricas[['Agente', 'Ratio (%)']].copy()
    df_ratio['Ratio (%)'] = df_ratio['Ratio (%)'].str.replace('%', '').astype(float)
    st.line_chart(df_ratio.set_index('Agente'))

# super_users_functions.py (AGREGAR ESTAS FUNCIONES AL FINAL)

def panel_monitorizaciones_super_usuario():
    """Panel de monitorizaciones integrado en super users"""
    
    st.subheader("📊 Sistema de Monitorizaciones")
    
    # Cargar agentes del supervisor
    super_users_config = cargar_super_users()
    username = st.session_state.get('username', '')
    
    # Filtrar agentes asignados a este supervisor
    agentes_completos = super_users_config.get("agentes", {})
    configuracion = super_users_config.get("configuracion", {})
    
    if configuracion.get("mostrar_solo_mis_agentes", False) and username:
        agentes = {k: v for k, v in agentes_completos.items() 
                  if v.get('supervisor', '') == username}
    else:
        agentes = agentes_completos
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Nueva Monitorización", 
        "🔔 Agentes Pendientes", 
        "📋 Historial",
        "👤 Monitorización Agente"
    ])
    
    with tab1:
        mostrar_formulario_monitorizacion(agentes)
    
    with tab2:
        mostrar_agentes_pendientes_monitorizar(agentes)
    
    with tab3:
        mostrar_historial_monitorizaciones(agentes)
    
    with tab4:
        mostrar_monitorizacion_agente_especifico()

def mostrar_formulario_monitorizacion(agentes):
    """Formulario para crear nuevas monitorizaciones"""
    
    st.write("### 📝 Registrar Nueva Monitorización")
    
    if not agentes:
        st.warning("No tienes agentes asignados para monitorizar")
        return
    
    # Opción 1: Cargar PDF
    st.write("#### 📄 Opción 1: Cargar PDF de Monitorización")
    
    uploaded_file = st.file_uploader(
        "Sube el PDF de monitorización",
        type=['pdf'],
        help="Sube el PDF generado después de una monitorización"
    )
    
    if uploaded_file is not None:
        # Simular análisis del PDF
        from monitorizacion_utils import analizar_pdf_monitorizacion
        datos_pdf = analizar_pdf_monitorizacion(uploaded_file)
        
        with st.expander("Ver datos extraídos del PDF", expanded=True):
            st.json(datos_pdf)
        
        # Pre-llenar formulario con datos del PDF
        for key, value in datos_pdf.items():
            if key not in st.session_state:
                st.session_state[f"mon_{key}"] = value
    
    st.write("#### ✍️ Opción 2: Ingreso Manual")
    
    with st.form("form_monitorizacion"):
        # Seleccionar agente
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
            agentes_opciones
        )
        
        # Extraer ID del agente
        agent_id = agente_seleccionado.split(" - ")[0]
        
        col_fecha1, col_fecha2 = st.columns(2)
        
        with col_fecha1:
            fecha_monitorizacion = st.date_input(
                "Fecha de Monitorización:",
                value=datetime.now().date()
            )
        
        with col_fecha2:
            # Fecha próxima (14 días por defecto)
            fecha_proxima = st.date_input(
                "Fecha próxima monitorización:",
                value=datetime.now().date() + timedelta(days=14)
            )
        
        # Notas principales
        col_nota1, col_nota2 = st.columns(2)
        
        with col_nota1:
            nota_global = st.number_input(
                "Nota Global (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_nota_global', 0.0)),
                step=0.5
            )
        
        with col_nota2:
            objetivo = st.number_input(
                "Objetivo (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_objetivo', 85.0)),
                step=0.5
            )
        
        st.write("##### 📊 Puntuaciones por Área")
        
        col_areas1, col_areas2 = st.columns(2)
        
        with col_areas1:
            experiencia = st.number_input(
                "Experiencia (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_experiencia', 0.0)),
                step=0.5
            )
            
            comunicacion = st.number_input(
                "Comunicación (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_comunicacion', 0.0)),
                step=0.5
            )
            
            deteccion = st.number_input(
                "Detección (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_deteccion', 0.0)),
                step=0.5
            )
        
        with col_areas2:
            habilidades_venta = st.number_input(
                "Habilidades de Venta (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_habilidades_venta', 0.0)),
                step=0.5
            )
            
            resolucion_objeciones = st.number_input(
                "Resolución Objeciones (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_resolucion_objeciones', 0.0)),
                step=0.5
            )
            
            cierre_contacto = st.number_input(
                "Cierre Contacto (%):",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.get('mon_cierre_contacto', 0.0)),
                step=0.5
            )
        
        # Feedback y plan
        st.write("##### 💬 Feedback y Plan de Acción")
        
        feedback = st.text_area(
            "Feedback para el agente:",
            value=st.session_state.get('mon_feedback', ''),
            height=100
        )
        
        plan_accion = st.text_area(
            "Plan de acción específico:",
            value=st.session_state.get('mon_plan_accion', ''),
            height=100
        )
        
        # Puntos clave
        puntos_clave = st.multiselect(
            "Puntos clave identificados:",
            ["LOPD", "Comunicación", "Cierre de venta", "Argumentación", 
             "Resolución objeciones", "Proceso venta", "Escucha activa", "Otros"],
            default=st.session_state.get('mon_puntos_clave', [])
        )
        
        submitted = st.form_submit_button("💾 Guardar Monitorización", type="primary")
        
        if submitted:
            monitorizacion_data = {
                'id_empleado': agent_id,
                'fecha_monitorizacion': fecha_monitorizacion.strftime('%Y-%m-%d'),
                'nota_global': nota_global,
                'objetivo': objetivo,
                'experiencia': experiencia,
                'comunicacion': comunicacion,
                'deteccion': deteccion,
                'habilidades_venta': habilidades_venta,
                'resolucion_objeciones': resolucion_objeciones,
                'cierre_contacto': cierre_contacto,
                'feedback': feedback,
                'plan_accion': plan_accion,
                'puntos_clave': puntos_clave,
                'fecha_proxima_monitorizacion': fecha_proxima.strftime('%Y-%m-%d')
            }
            
            from monitorizacion_utils import guardar_monitorizacion_completa
            
            if guardar_monitorizacion_completa(monitorizacion_data, st.session_state.username):
                st.success("✅ Monitorización guardada exitosamente")
                
                # Limpiar estado
                for key in ['mon_nota_global', 'mon_objetivo', 'mon_experiencia', 
                          'mon_comunicacion', 'mon_deteccion', 'mon_habilidades_venta',
                          'mon_resolucion_objeciones', 'mon_cierre_contacto',
                          'mon_feedback', 'mon_plan_accion', 'mon_puntos_clave']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.rerun()

def mostrar_agentes_pendientes_monitorizar(agentes):
    """Muestra agentes que necesitan ser monitorizados"""
    
    st.write("### 🔔 Agentes Pendientes de Monitorización")
    
    from database import obtener_agentes_pendientes_monitorizar
    
    agentes_pendientes = obtener_agentes_pendientes_monitorizar()
    
    if not agentes_pendientes:
        st.success("🎉 Todos los agentes están al día")
        return
    
    # Filtrar solo agentes de este supervisor
    agentes_supervisor = {a['id'] for a in agentes_pendientes if a['id'] in agentes}
    agentes_pendientes = [a for a in agentes_pendientes if a['id'] in agentes_supervisor]
    
    if not agentes_pendientes:
        st.info("Tus agentes están todos al día")
        return
    
    # Estadísticas
    total = len(agentes_pendientes)
    nunca_monitorizados = sum(1 for a in agentes_pendientes if a['ultima_fecha'] is None)
    
    col_stats1, col_stats2 = st.columns(2)
    
    with col_stats1:
        st.metric("Total Pendientes", total)
    
    with col_stats2:
        st.metric("Nunca Monitorizados", nunca_monitorizados)
    
    # Tabla de agentes
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
    
    # Botón para crear monitorización rápida
    if st.button("📝 Crear Monitorización Rápida", type="primary"):
        st.session_state.crear_monitorizacion_rapida = True
        st.rerun()

def mostrar_historial_monitorizaciones(agentes):
    """Muestra historial de monitorizaciones"""
    
    st.write("### 📋 Historial de Monitorizaciones")
    
    # Seleccionar agente
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
        
        from database import obtener_monitorizaciones_por_empleado
        monitorizaciones = obtener_monitorizaciones_por_empleado(agent_id)
        
        if not monitorizaciones:
            st.info("No hay monitorizaciones para este agente")
            return
        
        # Estadísticas
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
        
        # Tabla de historial
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
    
    from database import cargar_super_users, obtener_ultima_monitorizacion_empleado
    
    super_users_config = cargar_super_users()
    agentes = super_users_config.get("agentes", {})
    
    # Seleccionar agente
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
        
        ultima_mon = obtener_ultima_monitorizacion_empleado(agent_id)
        
        if not ultima_mon:
            st.info("Este agente no tiene monitorizaciones registradas")
            return
        
        # Mostrar información
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
        
        # Puntuaciones
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
        
        # Feedback y plan
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