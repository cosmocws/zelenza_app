import pytz

# Secciones disponibles para usuarios
SECCIONES_USUARIO = {
    "comparativa_exacta": {
        "nombre": "⚡ Comparativa EXACTA",
        "descripcion": "Compara tu consumo exacto con nuestros planes",
        "activo": True
    },
    "comparativa_estimada": {
        "nombre": "📅 Comparativa ESTIMADA", 
        "descripcion": "Estima tu consumo anual con nuestros planes",
        "activo": True
    },
    "calculadora_gas": {
        "nombre": "🔥 Calculadora Gas",
        "descripcion": "Calcula el coste de gas con nuestros planes",
        "activo": True
    },
    "pvd_usuario": {
        "nombre": "👁️ Sistema PVD",
        "descripcion": "Sistema de Pausas Visuales Dinámicas",
        "activo": True
    },
    "cups_naturgy": {
        "nombre": "📋 CUPS Naturgy",
        "descripcion": "Ejemplos de CUPS para trámites",
        "activo": True
    },
    "modelos_factura": {
        "nombre": "📄 Modelos de Factura",
        "descripcion": "Consultar modelos de factura",
        "activo": True
    }
}

SISTEMA_CONFIG_DEFAULT = {
    "login_automatico_activado": True,
    "sesion_horas_duracion": 8,
    "grupos_usuarios": {
        "basico": {"planes_luz": ["PLAN_BASICO"], "planes_gas": ["RL1"]},
        "premium": {"planes_luz": ["TODOS"], "planes_gas": ["RL1", "RL2", "RL3"]},
        "empresa": {"planes_luz": ["PLAN_EMPRESA"], "planes_gas": ["RL2", "RL3"]}
    },
    "secciones_activas": {  # NUEVO: Control de secciones visibles
        "comparativa_exacta": True,
        "comparativa_estimada": True,
        "calculadora_gas": True,
        "pvd_usuario": True,
        "cups_naturgy": True,
        "modelos_factura": True
    }
}

# ==============================================
# CONFIGURACIÓN DEL AUTO-REFRESH
# ==============================================
AUTO_REFRESH_INTERVAL = 60  # Segundos

# Configuración de zona horaria
TIMEZONE_MADRID = pytz.timezone('Europe/Madrid')

# ==============================================
# CONSTANTES
# ==============================================

COMUNIDADES_AUTONOMAS = [
    "Toda España",
    "Andalucía",
    "Aragón",
    "Asturias",
    "Baleares",
    "Canarias",
    "Cantabria",
    "Castilla-La Mancha",
    "Castilla y León",
    "Cataluña",
    "Comunidad Valenciana",
    "Extremadura",
    "Galicia",
    "Madrid",
    "Murcia",
    "Navarra",
    "País Vasco",
    "La Rioja",
    "Ceuta",
    "Melilla"
]

PLANES_GAS_ESTRUCTURA = {
    "RL1": {
        "precio_original_kwh": 0.045,
        "termino_variable_con_pmg": 0.038,
        "termino_variable_sin_pmg": 0.042,
        "termino_fijo_con_pmg": 8.5,
        "termino_fijo_sin_pmg": 9.2,
        "rango": "0-5000 kWh anuales",
        "activo": True
    },
    "RL2": {
        "precio_original_kwh": 0.043,
        "termino_variable_con_pmg": 0.036,
        "termino_variable_sin_pmg": 0.040,
        "termino_fijo_con_pmg": 12.0,
        "termino_fijo_sin_pmg": 13.0,
        "rango": "5000-15000 kWh anuales",
        "activo": True
    },
    "RL3": {
        "precio_original_kwh": 0.041,
        "termino_variable_con_pmg": 0.034,
        "termino_variable_sin_pmg": 0.038,
        "termino_fijo_con_pmg": 18.0,
        "termino_fijo_sin_pmg": 19.5,
        "rango": "15000-50000 kWh anuales",
        "activo": True
    }
}

PMG_COSTE = 9.95
PMG_IVA = 0.21

USUARIOS_DEFAULT = {
    "user": {
        "nombre": "Usuario Estándar",
        "password": "cliente123",
        "planes_luz": [],
        "planes_gas": ["RL1", "RL2", "RL3"],
        "tipo": "user"
    },
    "admin": {
        "nombre": "Administrador",
        "password": "admin123", 
        "planes_luz": "TODOS",
        "planes_gas": "TODOS",
        "tipo": "admin"
    }
}

PVD_CONFIG_DEFAULT = {
    "agentes_activos": 25,
    "maximo_simultaneo": 3,
    "duracion_corta": 5,
    "duracion_larga": 10,
    "sonido_activado": True,
    "auto_refresh_interval": 60
}

SISTEMA_CONFIG_DEFAULT = {
    "login_automatico_activado": True,
    "sesion_horas_duracion": 8,
    "grupos_usuarios": {
        "basico": {"planes_luz": ["PLAN_BASICO"], "planes_gas": ["RL1"]},
        "premium": {"planes_luz": ["TODOS"], "planes_gas": ["RL1", "RL2", "RL3"]},
        "empresa": {"planes_luz": ["PLAN_EMPRESA"], "planes_gas": ["RL2", "RL3"]}
    }
}

ESTADOS_PVD = {
    "ESPERANDO": "⏳ Esperando",
    "EN_CURSO": "▶️ En PVD",
    "COMPLETADO": "✅ Completado",
    "CANCELADO": "❌ Cancelado"
}

# Constantes de cálculo
ALQUILER_CONTADOR = 0.81
PACK_IBERDROLA = 3.95
IMPUESTO_ELECTRICO = 0.0511
DESCUENTO_PRIMERA_FACTURA = 5.00
IVA = 0.21
DIAS_ANUAL = 365