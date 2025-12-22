import streamlit as st
from datetime import datetime
import time
import json

class SessionManager:
    """Gestor de sesiones para mantener autenticación durante autorefresh"""
    
    def __init__(self):
        self.session_timeout = 8 * 3600  # 8 horas en segundos
        self.autorefresh_interval = 60  # 60 segundos
        
    def init_session(self):
        """Inicializa la sesión si no existe"""
        default_values = {
            'authenticated': False,
            'user_type': None,
            'username': '',
            'login_time': None,
            'user_config': {},
            'device_id': None,
            'last_refresh': time.time(),
            'session_id': self.generate_session_id()
        }
        
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def generate_session_id(self):
        """Genera un ID de sesión único"""
        import uuid
        return str(uuid.uuid4())
    
    def login(self, username, user_type, user_config=None):
        """Inicia sesión de usuario"""
        st.session_state.authenticated = True
        st.session_state.user_type = user_type
        st.session_state.username = username
        st.session_state.login_time = datetime.now()
        st.session_state.user_config = user_config or {}
        
        # Guardar en localStorage del navegador para persistencia
        self.save_to_localstorage()
    
    def logout(self):
        """Cierra sesión de usuario"""
        keys_to_clear = ['authenticated', 'user_type', 'username', 'login_time', 'user_config']
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = None
        
        # Limpiar localStorage
        self.clear_localstorage()
    
    def save_to_localstorage(self):
        """Guarda datos de sesión en localStorage del navegador"""
        # Preparar datos de sesión
        session_data = {
            'authenticated': st.session_state.get('authenticated', False),
            'username': st.session_state.get('username', ''),
            'user_type': st.session_state.get('user_type', None),
        }
        
        # Convertir login_time a string si existe
        login_time = st.session_state.get('login_time')
        if login_time:
            if isinstance(login_time, datetime):
                session_data['login_time'] = login_time.isoformat()
            else:
                session_data['login_time'] = str(login_time)
        else:
            session_data['login_time'] = None
        
        # Convertir a JSON de forma segura
        session_json = json.dumps(session_data)
        
        # Crear script para guardar en localStorage
        script = f"""
        <script>
        // Guardar sesión en localStorage
        localStorage.setItem('zelenza_session', '{session_json.replace("'", "\\'")}');
        </script>
        """
        
        st.markdown(script, unsafe_allow_html=True)
    
    def restore_from_localstorage(self):
        """Restaura sesión desde localStorage del navegador"""
        try:
            # Crear script para leer de localStorage
            script = """
            <script>
            // Leer sesión desde localStorage
            const sessionData = localStorage.getItem('zelenza_session');
            if (sessionData) {
                // Pasar datos a un elemento oculto
                const input = document.createElement('input');
                input.type = 'hidden';
                input.id = 'localStorageData';
                input.value = sessionData;
                document.body.appendChild(input);
                
                // Disparar evento para que Streamlit lo capture
                input.dispatchEvent(new Event('input'));
            }
            </script>
            """
            
            st.markdown(script, unsafe_allow_html=True)
            
        except Exception as e:
            print(f"Error restaurando sesión: {e}")
    
    def clear_localstorage(self):
        """Limpia localStorage del navegador"""
        script = """
        <script>
        // Limpiar sesión en localStorage
        localStorage.removeItem('zelenza_session');
        </script>
        """
        st.markdown(script, unsafe_allow_html=True)
    
    def check_autorefresh(self):
        """Verifica si es tiempo de hacer autorefresh"""
        current_time = time.time()
        last_refresh = st.session_state.get('last_refresh', current_time)
        
        if current_time - last_refresh >= self.autorefresh_interval:
            st.session_state.last_refresh = current_time
            return True
        
        return False
    
    def is_session_valid(self):
        """Verifica si la sesión es válida"""
        if not st.session_state.get('authenticated', False):
            return False
        
        login_time = st.session_state.get('login_time')
        if not login_time:
            return False
        
        # Convertir a datetime si es string
        if isinstance(login_time, str):
            try:
                login_time = datetime.fromisoformat(login_time.replace('Z', '+00:00'))
            except:
                return False
        
        # Verificar si ha expirado
        time_diff = (datetime.now() - login_time).total_seconds()
        return time_diff < self.session_timeout

# Instancia global del gestor de sesiones
session_manager = SessionManager()