"""Configuración: rutas, servicios seguros y planes de energía."""

# ------------------------------------------------------------ rutas
# Carpetas cuyo contenido se puede limpiar (variables de entorno permitidas)
RUTAS_TEMPORALES = [
    "%TEMP%",                              # Archivos temporales del usuario
    "%WINDIR%\\Temp",                      # Archivos temporales de Windows
]

RUTA_PREFETCH = "%WINDIR%\\Prefetch"       # Windows lo reconstruye solo
RUTA_CACHE_UPDATE = "%WINDIR%\\SoftwareDistribution\\Download"

# ------------------------------------------------------------ servicios
# Servicios considerados seguros de deshabilitar en un equipo doméstico típico.
# Clave: nombre del servicio -> descripción para mostrar al usuario.
SERVICIOS_OPCIONALES = {
    "DiagTrack":         "Telemetría (Connected User Experiences and Telemetry)",
    "dmwappushservice":  "Servicio WAP Push de Microsoft",
    "RetailDemo":        "Modo demo minorista",
    "RemoteRegistry":    "Registro remoto",
    "WMPNetworkSvc":     "Uso compartido de red de Windows Media Player",
    "Fax":               "Servicio de fax",
}

# ------------------------------------------------------------ energía
# Aliases reconocidos por powercfg /setactive
PLANES_ENERGIA = {
    "SCHEME_MIN":      "Alto rendimiento",
    "SCHEME_BALANCED": "Equilibrado (recomendado)",
    "SCHEME_MAX":      "Ahorro de energía",
}
