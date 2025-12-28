import streamlit as st
import os
import shutil
from datetime import datetime
from config import *
from auth import *
from database import *
from ui_components import mostrar_login, mostrar_panel_usuario
from admin_functions import mostrar_panel_administrador
from pvd_system import temporizador_pvd_mejorado
from utils import obtener_hora_madrid, formatear_hora_madrid
from sidebar_notifications import verificar_turno_sidebar

def main():
    """Función principal de la aplicación"""
    # Configuración de página
    st.set_page_config(
        page_title="Zelenza CEX - Iberdrola",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://www.example.com/help',
            'Report a bug': 'https://www.example.com/bug',
            'About': '# Zelenza CEX v2.0 con PVD Mejorado y Grupos'
        }
    )
    
    # Añadir estilos CSS
    st.markdown("""
    <style>
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
        100% { transform: scale(1); opacity: 1; }
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .sidebar-notification {
        animation: pulse 2s infinite, blink 3s infinite;
        border-left: 5px solid #00b09b !important;
    }
    
    .stButton > button {
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Estilo para notificaciones importantes en sidebar */
    .important-notification {
        background: linear-gradient(135deg, #00b09b, #96c93d) !important;
        color: white !important;
        padding: 10px !important;
        border-radius: 8px !important;
        margin: 10px 0 !important;
        text-align: center !important;
        font-weight: bold !important;
        animation: pulse 2s infinite !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar temporizador PVD en segundo plano
    if 'temporizador_iniciado' not in st.session_state:
        st.session_state.temporizador_iniciado = True
    
    # Mostrar información sobre el sistema mejorado
    st.title("⚡ Zelenza CEX - Calculadora Iberdrola")
    st.markdown("---")
    
    # Información sobre el sistema mejorado
    st.info("""
    **🔔 Objetivo: RETENER. Consecuencia: LA VENTA.**
    
    - **✅ No vendas un producto, ofrece la solución a un problema.**
    - **🔔 Detrás de cada objeción hay un cliente esperando ser convencido.**
    - **⏱️ La retención es la meta. La venta, su resultado natural.**
    - **👥 Tu voz es su guía. Tu confianza, su certeza.**
    - **🔄 Olvida el 'no' de ayer. Hoy hay un 'sí' nuevo esperándote.**
    """)
    
    # Restauración automática al iniciar
    if os.path.exists("data_backup"):
        for archivo in ["precios_luz.csv", "config_excedentes.csv"]:
            if os.path.exists(f"data_backup/{archivo}") and not os.path.exists(f"data/{archivo}"):
                shutil.copy(f"data_backup/{archivo}", f"data/{archivo}")
        
        if os.path.exists("data_backup/modelos_facturas") and not os.path.exists("modelos_facturas"):
            shutil.copytree("data_backup/modelos_facturas", "modelos_facturas", dirs_exist_ok=True)
    
    inicializar_datos()
    
    # Inicializar estado de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.login_time = None
        st.session_state.user_config = {}
        st.session_state.device_id = None
    
    # Verificar si ya está autenticado
    if st.session_state.get('authenticated', False):
        if not verificar_sesion():
            mostrar_login()
            return
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
        # ============================================
        # ✅ EJECUTAR VERIFICACIÓN DE TURNO EN SIDEBAR
        # ============================================
        if st.session_state.user_type == "user":
            verificar_turno_sidebar()

        # Barra lateral
        st.sidebar.title(f"{'🔧 Admin' if st.session_state.user_type == 'admin' else '👤 Usuario'}")
        st.sidebar.write(f"**Usuario:** {st.session_state.username}")
        
        # Mostrar nombre del usuario si está disponible
        if st.session_state.user_type == "user" and 'user_config' in st.session_state:
            nombre_usuario = st.session_state.user_config.get('nombre', '')
            if nombre_usuario:
                st.sidebar.write(f"**Nombre:** {nombre_usuario}")
        
        # Información de grupo si tiene
        if st.session_state.user_type == "user" and 'user_config' in st.session_state:
            grupo_usuario = st.session_state.user_config.get('grupo', '')
            if grupo_usuario:
                st.sidebar.write(f"**Grupo:** {grupo_usuario}")
                
                # Mostrar información del grupo PVD
                config_sistema = cargar_config_sistema()
                grupos_pvd = config_sistema.get('grupos_pvd', {})
                config_grupo = grupos_pvd.get(grupo_usuario, {})
                
                if config_grupo:
                    st.sidebar.write("**👥 Configuración PVD:**")
                    st.sidebar.write(f"• Agentes: {config_grupo.get('agentes_por_grupo', 10)}")
                    st.sidebar.write(f"• Máx. simultáneo: {config_grupo.get('maximo_simultaneo', 2)}")
                    st.sidebar.write(f"• Pausa corta: {config_grupo.get('duracion_corta', 5)} min")
                    st.sidebar.write(f"• Pausa larga: {config_grupo.get('duracion_larga', 10)} min")
        
        # Verificar si el usuario tiene turno pendiente en PVD
        if st.session_state.user_type == "user":
            cola_pvd = cargar_cola_pvd()
            config_pvd = cargar_config_pvd()
            
            # Buscar pausa del usuario en ESPERANDO
            pausa_usuario = None
            for pausa in cola_pvd:
                if pausa['usuario_id'] == st.session_state.username and pausa['estado'] == 'ESPERANDO':
                    pausa_usuario = pausa
                    break
            
            if pausa_usuario:
                # Obtener grupo del usuario
                from database import cargar_configuracion_usuarios
                usuarios_config = cargar_configuracion_usuarios()
                usuario_info = usuarios_config.get(st.session_state.username, {})
                grupo_usuario = usuario_info.get('grupo', 'basico')
                
                # Verificar si es el primero en su grupo
                en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo_usuario]
                en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                
                es_primero = False
                if en_espera_grupo and en_espera_grupo[0]['id'] == pausa_usuario['id']:
                    es_primero = True
                
                if es_primero:
                    # Verificar si hay espacio en el grupo
                    config_sistema = cargar_config_sistema()
                    grupos_pvd = config_sistema.get('grupos_pvd', {})
                    config_grupo = grupos_pvd.get(grupo_usuario, {'maximo_simultaneo': 2})
                    max_grupo = config_grupo.get('maximo_simultaneo', 2)
                    
                    en_pausa_grupo = len([p for p in cola_pvd if p['estado'] == 'EN_CURSO' and p.get('grupo') == grupo_usuario])
                    
                    if en_pausa_grupo < max_grupo:
                        # ¡ES SU TURNO! - Mostrar notificación en sidebar
                        st.sidebar.markdown("---")
                        
                        # Notificación destacada
                        st.sidebar.markdown("""
                        <div style="
                            background: linear-gradient(135deg, #00b09b, #96c93d);
                            color: white;
                            padding: 12px;
                            border-radius: 10px;
                            margin: 10px 0;
                            text-align: center;
                            font-weight: bold;
                            animation: pulse 2s infinite;
                            border: 2px solid white;
                        ">
                        🎯 ¡ES TU TURNO!<br>Confirma tu pausa PVD
                        </div>
                        """, unsafe_allow_html=True)
                        
                        duracion_elegida = pausa_usuario.get('duracion_elegida', 'corta')
                        duracion = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                        
                        st.sidebar.write(f"**⏱️ Duración:** {duracion} minutos")
                        st.sidebar.write(f"**👥 Grupo:** {grupo_usuario}")
                        st.sidebar.write(f"**📍 Posición:** #1 en la cola")
                        
                        # Inicializar tiempo de confirmación si no existe
                        if 'confirmacion_inicio_sidebar' not in st.session_state:
                            st.session_state.confirmacion_inicio_sidebar = obtener_hora_madrid()
                        
                        # Calcular tiempo restante
                        tiempo_confirmacion = (obtener_hora_madrid() - st.session_state.confirmacion_inicio_sidebar).total_seconds()
                        tiempo_restante = max(0, 120 - tiempo_confirmacion)  # 2 minutos
                        minutos = int(tiempo_restante // 60)
                        segundos = int(tiempo_restante % 60)
                        
                        # Barra de progreso CORREGIDA (valor entre 0 y 1)
                        progreso = min(1.0, tiempo_confirmacion / 120)
                        st.sidebar.progress(progreso)
                        st.sidebar.caption(f"⏳ **Tiempo para confirmar:** {minutos}:{segundos:02d}")
                        
                        # Botones de acción en sidebar
                        col_sb1, col_sb2 = st.sidebar.columns(2)
                        with col_sb1:
                            if st.button("✅ **Comenzar Pausa**", key="sidebar_confirmar_pausa", use_container_width=True, type="primary"):
                                pausa_usuario['estado'] = 'EN_CURSO'
                                pausa_usuario['timestamp_inicio'] = obtener_hora_madrid().isoformat()
                                pausa_usuario['confirmado'] = True
                                guardar_cola_pvd(cola_pvd)
                                
                                # Cancelar temporizador si existe
                                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                                
                                # Limpiar estado de confirmación
                                if 'confirmacion_inicio_sidebar' in st.session_state:
                                    del st.session_state.confirmacion_inicio_sidebar
                                
                                st.success("✅ Pausa confirmada e iniciada")
                                st.rerun()
                        
                        with col_sb2:
                            if st.button("❌ **Cancelar Turno**", key="sidebar_cancelar_pausa", use_container_width=True, type="secondary"):
                                pausa_usuario['estado'] = 'CANCELADO'
                                guardar_cola_pvd(cola_pvd)
                                
                                # Cancelar temporizador si existe
                                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                                
                                # Limpiar estado de confirmación
                                if 'confirmacion_inicio_sidebar' in st.session_state:
                                    del st.session_state.confirmacion_inicio_sidebar
                                
                                st.warning("❌ Turno cancelado")
                                st.rerun()
                        
                        # Verificar si se agotó el tiempo
                        if tiempo_confirmacion > 120:
                            st.sidebar.error("⏰ **Tiempo agotado** - Cancelando turno...")
                            pausa_usuario['estado'] = 'CANCELADO'
                            guardar_cola_pvd(cola_pvd)
                            
                            # Cancelar temporizador si existe
                            temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
                            
                            # Limpiar estado de confirmación
                            if 'confirmacion_inicio_sidebar' in st.session_state:
                                del st.session_state.confirmacion_inicio_sidebar
                            
                            st.rerun()
                
                # Si no es su turno, mostrar info normal
                elif not es_primero:
                    # Calcular posición
                    posicion = 1
                    for i, pausa in enumerate(en_espera_grupo):
                        if pausa['id'] == pausa_usuario['id']:
                            posicion = i + 1
                            break
                    
                    st.sidebar.markdown("---")
                    st.sidebar.write("**👁️ Estado PVD:**")
                    st.sidebar.info(f"⏳ En espera - Posición: #{posicion}")
                    st.sidebar.write(f"**👥 Grupo:** {grupo_usuario}")
                    
                    # Mostrar tiempo estimado si hay temporizador
                    tiempo_restante = temporizador_pvd_mejorado.obtener_tiempo_restante(st.session_state.username)
                    if tiempo_restante and tiempo_restante > 0:
                        st.sidebar.write(f"**⏱️ Tiempo estimado:** ~{int(tiempo_restante)} min")
            
            # Mostrar info de pausa en curso si existe
            else:
                # Buscar pausa en curso
                pausa_en_curso = None
                for pausa in cola_pvd:
                    if pausa['usuario_id'] == st.session_state.username and pausa['estado'] == 'EN_CURSO':
                        pausa_en_curso = pausa
                        break
                
                if pausa_en_curso:
                    st.sidebar.markdown("---")
                    st.sidebar.write("**👁️ Estado PVD:**")
                    st.sidebar.success(f"✅ Pausa en curso")
                    
                    # Calcular tiempo restante
                    duracion_elegida = pausa_en_curso.get('duracion_elegida', 'corta')
                    duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                    
                    tiempo_inicio = datetime.fromisoformat(pausa_en_curso['timestamp_inicio'])
                    tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60
                    tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                    
                    # Barra de progreso CORREGIDA
                    progreso = min(1.0, tiempo_transcurrido / duracion_minutos)
                    st.sidebar.progress(progreso)
                    st.sidebar.write(f"**⏳ Restante:** {int(tiempo_restante)} min")
        
        # Botón para cerrar sesión
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            # Limpiar sesión
            st.session_state.authenticated = False
            st.session_state.user_type = None
            st.session_state.username = ""
            st.session_state.login_time = None
            st.session_state.user_config = {}
            st.session_state.device_id = None
            
            # Cancelar temporizador si existe
            if 'username' in st.session_state:
                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
            
            st.rerun()
        
        # Mostrar información del temporizador automático
        st.sidebar.markdown("---")
        st.sidebar.caption(f"⏱️ Temporizador automático: 60s")
        st.sidebar.caption(f"🔄 Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
        
        # Botón para refrescar manualmente
        if st.sidebar.button("🔄 Refrescar página", use_container_width=True, key="refresh_manual"):
            st.rerun()
        
        # Mostrar el panel correspondiente
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()

if __name__ == "__main__":
    main()