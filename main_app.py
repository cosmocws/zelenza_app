import streamlit as st
import os
import shutil
from datetime import datetime, timedelta
import time
from config import *
from auth import *
from database import *
from ui_components import mostrar_login, mostrar_panel_usuario
from admin_functions import mostrar_panel_administrador
from pvd_system import temporizador_pvd_mejorado
from utils import obtener_hora_madrid, formatear_hora_madrid

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
    
    # INICIALIZACIÓN DE SESIÓN
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.last_refresh = time.time()
        st.session_state.refresh_counter = 60
    
    # SISTEMA DE AUTOREFRESH SUAVE
    current_time = time.time()
    time_diff = current_time - st.session_state.last_refresh
    st.session_state.refresh_counter = max(0, 60 - int(time_diff))
    
    # Mostrar contador de autorefresh en sidebar
    with st.sidebar:
        if st.session_state.refresh_counter <= 5:
            st.warning(f"🔄 Refrescando en: {st.session_state.refresh_counter}s")
        else:
            st.info(f"🔄 Siguiente refresh: {st.session_state.refresh_counter}s")
        
        if st.button("🔄 Refrescar ahora", use_container_width=True):
            st.rerun()
    
    # Ejecutar autorefresh cada 60 segundos
    if time_diff > 60:
        st.session_state.last_refresh = current_time
        st.rerun()
    
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
    
    # INICIALIZAR ESTADO DE SESIÓN CON VALORES POR DEFECTO
    session_defaults = {
        'authenticated': False,
        'user_type': None,
        'username': "",
        'login_time': None,
        'user_config': {},
        'device_id': None
    }
    
    for key, default_value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # Verificar si ya está autenticado
    if st.session_state.get('authenticated', False):
        if not verificar_sesion():
            mostrar_login()
            return
    
    if not st.session_state.authenticated:
        mostrar_login()
    else:
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
        
        # Botón para cerrar sesión
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            # Limpiar sesión
            for key in session_defaults.keys():
                st.session_state[key] = session_defaults[key]
            
            # Cancelar temporizador si existe
            if 'username' in st.session_state:
                temporizador_pvd_mejorado.cancelar_temporizador(st.session_state.username)
            
            st.rerun()
        
        # Información del sistema PVD
        if st.session_state.user_type == "user":
            cola_pvd = cargar_cola_pvd()
            
            # Buscar pausas del usuario
            pausas_usuario = [p for p in cola_pvd if p['usuario_id'] == st.session_state.username]
            pausas_activas = [p for p in pausas_usuario if p['estado'] in ['ESPERANDO', 'EN_CURSO']]
            
            if pausas_activas:
                st.sidebar.markdown("---")
                st.sidebar.write("**👁️ Estado PVD:**")
                
                for pausa in pausas_activas:
                    estado_display = ESTADOS_PVD.get(pausa['estado'], pausa['estado'])
                    
                    if pausa['estado'] == 'ESPERANDO':
                        st.sidebar.warning(f"⏳ {estado_display}")
                        
                        # Calcular posición
                        grupo = pausa.get('grupo', 'basico')
                        en_espera_grupo = [p for p in cola_pvd if p['estado'] == 'ESPERANDO' and p.get('grupo') == grupo]
                        en_espera_grupo = sorted(en_espera_grupo, key=lambda x: datetime.fromisoformat(x['timestamp_solicitud']))
                        
                        posicion = next((i+1 for i, p in enumerate(en_espera_grupo) 
                                       if p['id'] == pausa['id']), 1)
                        
                        st.sidebar.write(f"Posición: #{posicion}")
                        
                        tiempo_restante = temporizador_pvd_mejorado.obtener_tiempo_restante(st.session_state.username)
                        if tiempo_restante and tiempo_restante > 0:
                            st.sidebar.write(f"Tiempo estimado: ~{int(tiempo_restante)} min")
                    
                    elif pausa['estado'] == 'EN_CURSO':
                        st.sidebar.success(f"✅ {estado_display}")
                        
                        # Calcular tiempo restante
                        config_pvd = cargar_config_pvd()
                        duracion_elegida = pausa.get('duracion_elegida', 'corta')
                        duracion_minutos = config_pvd['duracion_corta'] if duracion_elegida == 'corta' else config_pvd['duracion_larga']
                        
                        tiempo_inicio = datetime.fromisoformat(pausa['timestamp_inicio'])
                        tiempo_transcurrido = (obtener_hora_madrid() - tiempo_inicio).total_seconds() / 60
                        tiempo_restante = max(0, duracion_minutos - tiempo_transcurrido)
                        
                        st.sidebar.write(f"Restante: {int(tiempo_restante)} min")
        
        # Mostrar información del temporizador automático
        st.sidebar.markdown("---")
        st.sidebar.caption(f"⏱️ Temporizador automático: 60s")
        st.sidebar.caption(f"🔄 Última ejecución: {formatear_hora_madrid(temporizador_pvd_mejorado.ultima_actualizacion)}")
        
        # Mostrar el panel correspondiente
        if st.session_state.user_type == "admin":
            mostrar_panel_administrador()
        else:
            mostrar_panel_usuario()
        
        # JavaScript para autoreflash visual (sin recargar sesión)
        st.markdown("""
        <script>
        // Contador visual para el usuario
        let visualCounter = 60;
        const counterElement = document.createElement('div');
        counterElement.style.position = 'fixed';
        counterElement.style.bottom = '10px';
        counterElement.style.right = '10px';
        counterElement.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        counterElement.style.color = 'white';
        counterElement.style.padding = '5px 10px';
        counterElement.style.borderRadius = '5px';
        counterElement.style.fontSize = '12px';
        counterElement.style.zIndex = '9999';
        counterElement.innerHTML = `🔄 Auto-refresh: ${visualCounter}s`;
        document.body.appendChild(counterElement);
        
        setInterval(() => {
            visualCounter--;
            if (visualCounter <= 0) {
                visualCounter = 60;
            }
            counterElement.innerHTML = `🔄 Auto-refresh: ${visualCounter}s`;
        }, 1000);
        </script>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()