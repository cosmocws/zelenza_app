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
        
        col_agentes1, col_agentes2 = st.columns(2)
        
        with col_agentes1:
            st.write("**Agentes registrados:**")
            if agentes:
                for agent_id, info in agentes.items():
                    estado = "✅ Activo" if info.get('activo', True) else "❌ Inactivo"
                    grupo = info.get('grupo', 'Sin grupo')
                    st.write(f"• **{agent_id}** - {info.get('nombre', 'Sin nombre')} ({estado}) - {grupo}")
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
        
        if st.button("💾 Guardar Configuración", type="primary"):
            nueva_config = {
                "duracion_minima_llamada": duracion_minima,
                "periodo_mensual": periodo,
                "target_llamadas": target_llamadas,
                "target_ventas": target_ventas,
                "metrica_eficiencia": metrica
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
    agentes = super_users_config.get("agentes", {})
    configuracion = super_users_config.get("configuracion", {})
    registro_llamadas = cargar_registro_llamadas()
    
    if not agentes:
        st.warning("⚠️ No hay agentes configurados. Contacta al administrador.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Registro Diario", "📊 Métricas Mensuales", "📈 Dashboard", "👥 Gestión Agentes"])
    
    with tab1:
        gestion_registro_diario(agentes, registro_llamadas, configuracion)
    
    with tab2:
        mostrar_metricas_mensuales(agentes, registro_llamadas, configuracion)
    
    with tab3:
        mostrar_dashboard(agentes, registro_llamadas, configuracion)
    
    with tab4:
        gestion_agentes_super_usuario(agentes, super_users_config)

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
    
    # Crear formulario para cada agente
    with st.form("form_registro_diario"):
        registros = []
        
        for agent_id, info in agentes.items():
            if info.get('activo', True):  # Solo agentes activos
                nombre = info.get('nombre', agent_id)
                grupo = info.get('grupo', 'Sin grupo')
                
                # Obtener valores actuales
                datos_agente = datos_dia.get(agent_id, {"llamadas": 0, "ventas": 0})
                
                col_agent1, col_agent2, col_agent3 = st.columns([3, 2, 2])
                
                with col_agent1:
                    st.write(f"**{nombre}**")
                    st.caption(f"Grupo: {grupo}")
                
                with col_agent2:
                    llamadas = st.number_input(
                        f"Llamadas >{configuracion.get('duracion_minima_llamada', 15)}min",
                        min_value=0,
                        max_value=100,
                        value=datos_agente.get("llamadas", 0),
                        key=f"llamadas_{agent_id}_{fecha_str}"
                    )
                
                with col_agent3:
                    ventas = st.number_input(
                        "Ventas",
                        min_value=0,
                        max_value=50,
                        value=datos_agente.get("ventas", 0),
                        key=f"ventas_{agent_id}_{fecha_str}"
                    )
                
                registros.append({
                    'agent_id': agent_id,
                    'llamadas': llamadas,
                    'ventas': ventas
                })
        
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
            for datos_agente in datos_dia.values():
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
    
    for fecha_str in sorted(registro_llamadas.keys())[-30:]:  # Últimos 30 días
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if fecha_inicio <= fecha <= fecha_fin:
            total_dia_llamadas = 0
            total_dia_ventas = 0
            
            for datos_agente in registro_llamadas[fecha_str].values():
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

def gestion_agentes_super_usuario(agentes, super_users_config):
    """Gestión de agentes desde el panel de super usuario"""
    st.subheader("👥 Gestión de Agentes")
    
    # Mostrar lista de agentes con opciones
    for agent_id, info in agentes.items():
        nombre = info.get('nombre', agent_id)
        grupo = info.get('grupo', 'Sin grupo')
        activo = info.get('activo', True)
        
        with st.expander(f"{'✅' if activo else '❌'} {nombre} ({grupo})", expanded=False):
            col_agent1, col_agent2 = st.columns(2)
            
            with col_agent1:
                st.write("**Información:**")
                st.write(f"• ID: {agent_id}")
                st.write(f"• Grupo: {grupo}")
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