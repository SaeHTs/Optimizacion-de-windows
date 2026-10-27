"""Configuración: rutas, servicios seguros y planes de energía.

NOTA i18n: las descripciones visibles al usuario se traducen con tr(). Las
tablas se construyen al importarse, así que el idioma debe fijarse
(i18n.set_idioma) ANTES de importar este módulo; además, al cambiar de
idioma en caliente se recalculan con `_refrescar_textos()`.
"""
from i18n import registrar_recarga, tr

# ------------------------------------------------------------ rutas
# Carpetas cuyo contenido se puede limpiar (variables de entorno permitidas)
RUTAS_TEMPORALES = [
    "%TEMP%",                              # Archivos temporales del usuario
    "%WINDIR%\\Temp",                      # Archivos temporales de Windows
]

RUTA_PREFETCH = "%WINDIR%\\Prefetch"       # Windows lo reconstruye solo
RUTA_CACHE_UPDATE = "%WINDIR%\\SoftwareDistribution\\Download"
RUTA_CACHE_ENTREGA = "%WINDIR%\\SoftwareDistribution\\DeliveryOptimization"

# ------------------------------------------------------------ navegadores
# Solo carpetas de CACHÉ de código/datos. NUNCA perfiles, cookies,
# historial ni contraseñas. Todo lo que se borra se regenera solo.
CACHE_NAVEGADORES = [
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache",
    "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Code Cache",
    "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache",
    "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Code Cache",
]
# Firefox usa perfiles dinámicos: se recorre esta carpeta y se limpia
# la subcarpeta "cache2" de cada perfil encontrado.
PERFILES_FIREFOX = "%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles"
SUBCARPETA_CACHE_FIREFOX = "cache2"

# ------------------------------------------------------------ miniaturas
# thumbcache_*.db dentro de esta carpeta (iconos/miniaturas; se regeneran)
RUTA_MINIATURAS = "%LOCALAPPDATA%\\Microsoft\\Windows\\Explorer"
PATRON_MINIATURAS = "thumbcache_*.db"

# ------------------------------------------------------------ logs y volcados
# Logs del sistema CBS (SFC/DISM) y volcados de pantallazos azules.
RUTA_LOGS_CBS = "%WINDIR%\\Logs\\CBS"
RUTA_MINIDUMP = "%WINDIR%\\Minidump"

# ------------------------------------------------------------ servicios
# Servicios considerados seguros de deshabilitar en un equipo doméstico típico.
# Clave: nombre del servicio -> descripción para mostrar al usuario.
def _textos_servicios_opcionales() -> dict:
    return {
        "DiagTrack":         tr("Telemetría (Connected User Experiences and Telemetry)"),
        "dmwappushservice":  tr("Servicio WAP Push de Microsoft"),
        "RetailDemo":        tr("Modo demo minorista"),
        "RemoteRegistry":    tr("Registro remoto"),
        "WMPNetworkSvc":     tr("Uso compartido de red de Windows Media Player"),
        "Fax":               tr("Servicio de fax"),
    }


SERVICIOS_OPCIONALES = _textos_servicios_opcionales()

# ------------------------------------------------------------ inicio
# Entradas de inicio seguras de deshabilitar en modo automático
# (coinciden por prefijo: actualizadores y helpers del sistema)
# NOTA: el primer elemento es el identificador de hive del registro
# (datos, no texto de usuario): NO se traduce.
ENTRADAS_INICIO_AUTO = [
    ("Usuario", "MicrosoftEdgeAutoLaunch"),   # auto-lanzador de Edge
    ("Equipo 32-bit", "SunJavaUpdateSched"),  # programador de Java
]

# ------------------------------------------------------------ servicios avanzados
# Servicios del ecosistema Windows seguros de deshabilitar en un equipo
# doméstico típico (ADEMÁS de los de SERVICIOS_OPCIONALES).
def _textos_servicios_avanzados() -> dict:
    return {
        "wisvc":           tr("Windows Insider (programa de pruebas)"),
        "MapsBroker":      tr("Administrador de mapas descargados"),
        "WalletService":   tr("Billetera de Windows"),
        "PhoneSvc":        tr("Vínculo con el teléfono (Phone Link)"),
        "XblAuthManager":  tr("Xbox Live (autenticación)"),
        "XblGameSave":     tr("Xbox Live (partidas guardadas)"),
        "XboxNetApiSvc":   tr("Xbox Live (red)"),
        "XboxGipSvc":      tr("Xbox (periféricos)"),
    }


SERVICIOS_AVANZADOS = _textos_servicios_avanzados()


# Condicionales: solo se ofrecen cuando el DETECTOR dice que aplica.
# clave interna -> (nombre del servicio, detector, aviso)
def _textos_servicios_condicionales() -> dict:
    return {
        "Spooler": (tr("Cola de impresión (Print Spooler)"), "sin_impresora",
                    tr("¡Solo sin impresoras! También cierra la vía PrintNightmare.")),
        "WSearch": (tr("Indexado de búsqueda de Windows"), "siempre_avisar",
                    tr("El menú Inicio seguirá buscando, pero más lento.")),
        "SysMain": (tr("Superfetch / precarga"), "solo_ssd",
                    tr("En SSD no aporta; en HDD puede ayudar (no se ofrece allí).")),
        "TermService": (tr("Escritorio remoto (RDP)"), "rdp_apagado",
                        tr("Solo se ofrece si RDP ya está desactivado en el sistema.")),
    }


SERVICIOS_CONDICIONALES = _textos_servicios_condicionales()

# Tareas programadas de telemetría/CEIP: seguras de deshabilitar.
TAREAS_TELEMETRIA = [
    (r"\Microsoft\Windows\Customer Experience Improvement Program", "Consolidator"),
    (r"\Microsoft\Windows\Customer Experience Improvement Program", "UsbCeip"),
    (r"\Microsoft\Windows\Application Experience", "Microsoft Compatibility Appraiser"),
    (r"\Microsoft\Windows\Application Experience", "ProgramDataUpdater"),
    (r"\Microsoft\Windows\Autochk", "Proxy"),
]

# Ajustes de privacidad y gaming (registro). (descripción, raiz, subclave, valor, dato)
RAIZ_HKCU = "HKCU"
RAIZ_HKLM = "HKLM"
def _textos_ajustes_privacidad() -> list:
    return [
        (tr("ID de publicidad"), RAIZ_HKCU, r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
        (tr("Experiencias personalizadas"), RAIZ_HKCU, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesWithDiagnosticDataEnabled", 0),
        (tr("Historial de actividad"), RAIZ_HKLM, r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", 0),
        (tr("Bing en el menú Inicio"), RAIZ_HKCU, r"SOFTWARE\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 1),
        (tr("Widgets (noticias e intereses)"), RAIZ_HKLM, r"SOFTWARE\Policies\Microsoft\Windows\Dsh", "AllowNewsAndInterests", 0),
        (tr("Copilot en la barra de tareas"), RAIZ_HKCU, r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
    ]


AJUSTES_PRIVACIDAD = _textos_ajustes_privacidad()


def _textos_ajustes_gaming() -> list:
    return [
        (tr("Game DVR (captura de la app)"), RAIZ_HKCU, r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
        (tr("Game DVR (sistema)"), RAIZ_HKCU, r"System\GameConfigStore", "GameDVR_Enabled", 0),
    ]


AJUSTES_GAMING = _textos_ajustes_gaming()

# ------------------------------------------------------------ energía
# Aliases reconocidos por powercfg /setactive
def _textos_planes_energia() -> dict:
    return {
        "SCHEME_MIN":      tr("Alto rendimiento"),
        "SCHEME_BALANCED": tr("Equilibrado (recomendado)"),
        "SCHEME_MAX":      tr("Ahorro de energía"),
    }


PLANES_ENERGIA = _textos_planes_energia()


# ------------------------------------------------------------ recarga i18n
def _refrescar_textos() -> None:
    """Recalcula las descripciones con el idioma activo.

    Se MUTAN las tablas (no se reasignan) a propósito: otros módulos hacen
    `from config import PLANES_ENERGIA` y deben seguir viendo la tabla viva,
    no una copia congelada en el idioma del import.
    """
    SERVICIOS_OPCIONALES.clear()
    SERVICIOS_OPCIONALES.update(_textos_servicios_opcionales())
    SERVICIOS_AVANZADOS.clear()
    SERVICIOS_AVANZADOS.update(_textos_servicios_avanzados())
    SERVICIOS_CONDICIONALES.clear()
    SERVICIOS_CONDICIONALES.update(_textos_servicios_condicionales())
    AJUSTES_PRIVACIDAD[:] = _textos_ajustes_privacidad()
    AJUSTES_GAMING[:] = _textos_ajustes_gaming()
    PLANES_ENERGIA.clear()
    PLANES_ENERGIA.update(_textos_planes_energia())


registrar_recarga(_refrescar_textos)
