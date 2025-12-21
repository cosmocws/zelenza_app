import streamlit as st
from datetime import datetime
from utils import obtener_hora_madrid

def crear_temporizador_html(minutos_restantes, usuario_id):
    """Crea un temporizador visual en HTML/JavaScript con notificación de confirmación"""
    
    segundos_totales = minutos_restantes * 60
    
    html_code = f"""
    <div id="temporizador-pvd" style="
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        border: 2px solid #00b4d8;
        position: relative;
        overflow: hidden;
    ">
        <div style="position: absolute; top: 10px; right: 10px; font-size: 12px; opacity: 0.8;">
            🕒 <span id="hora-actual">00:00:00</span>
        </div>
        
        <h3 style="margin: 0 0 15px 0; color: #00b4d8; font-size: 22px;">
            ⏱️ TEMPORIZADOR PVD
        </h3>
        
        <div id="contador" style="
            font-size: 48px;
            font-weight: bold;
            margin: 15px 0;
            color: #4cc9f0;
            text-shadow: 0 0 10px rgba(76, 201, 240, 0.5);
        ">
            {minutos_restantes:02d}:00
        </div>
        
        <div style="
            background: #1f4068;
            height: 20px;
            border-radius: 10px;
            margin: 20px 0;
            overflow: hidden;
        ">
            <div id="barra-progreso" style="
                background: linear-gradient(90deg, #4cc9f0, #4361ee);
                height: 100%;
                width: 0%;
                border-radius: 10px;
                transition: width 1s ease, background 0.5s ease;
            "></div>
        </div>
        
        <div id="mensaje-confirmacion" style="
            display: none;
            background: linear-gradient(135deg, #00b09b, #96c93d);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            font-weight: bold;
            animation: fadeIn 0.5s ease;
        ">
            ✅ Confirmación recibida. Tu pausa comenzará en breve.
        </div>
        
        <div style="
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.9;
        ">
            <div>🆔 {usuario_id[:8]}...</div>
            <div id="tiempo-restante-texto">Restante: {minutos_restantes} min</div>
            <div id="estado-temporizador">⏳ En espera</div>
        </div>
    </div>
    
    <script>
    let segundosRestantes = {segundos_totales};
    const segundosTotales = {segundos_totales};
    let temporizadorActivo = true;
    let notificacionMostrada = false;
    
    function actualizarHora() {{
        const ahora = new Date();
        const hora = ahora.getHours().toString().padStart(2, '0');
        const minutos = ahora.getMinutes().toString().padStart(2, '0');
        const segundos = ahora.getSeconds().toString().padStart(2, '0');
        document.getElementById('hora-actual').textContent = hora + ':' + minutos + ':' + segundos;
    }}
    
    function mostrarNotificacionOverlay() {{
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.id = 'overlay-notificacion-pvd';
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
                background: linear-gradient(135deg, #00b09b, #96c93d);
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
                <h2 style="margin: 0 0 20px 0; font-size: 28px;">🎉 ¡ES TU TURNO!</h2>
                <p style="font-size: 20px; margin: 15px 0; font-weight: bold;">Tu pausa PVD está por comenzar</p>
                <p style="opacity: 0.9; margin-bottom: 25px; font-size: 16px;">Haz clic en OK para confirmar que estás listo</p>
                
                <div style="display: flex; gap: 20px; justify-content: center;">
                    <button id="btn-confirmar-pvd-overlay" style="
                        background: white;
                        color: #00b09b;
                        border: none;
                        padding: 15px 40px;
                        border-radius: 10px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: transform 0.2s;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                    ">
                        ✅ OK - Empezar Pausa
                    </button>
                    
                    <button id="btn-cancelar-pvd-overlay" style="
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
                        ❌ Cancelar
                    </button>
                </div>
                
                <p style="margin-top: 20px; font-size: 14px; opacity: 0.8;">Esta notificación aparecerá automáticamente</p>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}
        `;
        document.head.appendChild(style);
        
        document.getElementById('btn-confirmar-pvd-overlay').addEventListener('click', function() {{
            document.getElementById('contador').textContent = '✅ CONFIRMADO';
            document.getElementById('contador').style.color = '#00ff00';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #00ff00, #00cc00)';
            
            document.getElementById('mensaje-confirmacion').style.display = 'block';
            
            document.body.removeChild(overlay);
            
            try {{
                const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-correct-answer-tone-2870.mp3');
                audio.volume = 0.3;
                audio.play();
            }} catch(e) {{}}
            
            temporizadorActivo = false;
            
            setTimeout(() => {{
                window.location.reload();
            }}, 5000);
        }});
        
        document.getElementById('btn-cancelar-pvd-overlay').addEventListener('click', function() {{
            document.body.removeChild(overlay);
            
            const mensajeCancel = document.createElement('div');
            mensajeCancel.style.cssText = `
                background: #f44336;
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                text-align: center;
            `;
            mensajeCancel.textContent = '⚠️ Pausa cancelada. Seguirás en la cola.';
            
            const temporizadorDiv = document.getElementById('temporizador-pvd');
            temporizadorDiv.appendChild(mensajeCancel);
            
            setTimeout(() => {{
                window.location.reload();
            }}, 3000);
        }});
        
        return true;
    }}
    
    function actualizarTemporizador() {{
        if (!temporizadorActivo) return;
        
        segundosRestantes--;
        
        if (segundosRestantes <= 0) {{
            document.getElementById('contador').textContent = '🎯 ¡TU TURNO!';
            document.getElementById('contador').style.color = '#ff9900';
            document.getElementById('barra-progreso').style.width = '100%';
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
            
            if (!notificacionMostrada) {{
                mostrarNotificacionOverlay();
                notificacionMostrada = true;
            }}
            
            return;
        }}
        
        const minutos = Math.floor(segundosRestantes / 60);
        const segundos = segundosRestantes % 60;
        document.getElementById('contador').textContent = 
            minutos.toString().padStart(2, '0') + ':' + 
            segundos.toString().padStart(2, '0');
        
        const progreso = 100 * (1 - (segundosRestantes / segundosTotales));
        document.getElementById('barra-progreso').style.width = progreso + '%';
        
        if (segundosRestantes <= 300 && segundosRestantes > 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff9900, #ff6600)';
        }} else if (segundosRestantes <= 60) {{
            document.getElementById('barra-progreso').style.background = 'linear-gradient(90deg, #ff3300, #cc0000)';
        }}
        
        actualizarHora();
        
        setTimeout(actualizarTemporizador, 1000);
    }}
    
    actualizarHora();
    actualizarTemporizador();
    </script>
    """
    
    return html_code

def enviar_notificacion_browser(mensaje, tipo="info"):
    """Envía una notificación al navegador"""
    try:
        if tipo == "success":
            icon = "✅"
            color = "#00b09b"
        elif tipo == "warning":
            icon = "⚠️"
            color = "#ff9900"
        elif tipo == "error":
            icon = "❌"
            color = "#ff3300"
        else:
            icon = "ℹ️"
            color = "#4cc9f0"
        
        st.markdown(f"""
        <script>
        if (Notification.permission === "granted") {{
            new Notification("{icon} Zelenza PVD", {{
                body: "{mensaje}",
                icon: "https://img.icons8.com/color/96/000000/clock--v1.png"
            }});
        }}
        </script>
        """, unsafe_allow_html=True)
        
        return True
    except Exception as e:
        print(f"Error enviando notificación: {e}")
        return False