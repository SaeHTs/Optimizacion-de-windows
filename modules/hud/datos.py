"""Datos reales del sistema para el centro de mando.

Nada de valores de ejemplo: todo sale de `modules/analisis.py`,
`modules/startup.py`, `config.py` y `psutil` (opcional, ya declarado en
`requirements.txt`). Si un dato no se puede medir, se devuelve `None`
y la interfaz lo dice; nunca se inventa una cifra.

El análisis lento (disco, programas de inicio) se lanza en un hilo
aparte; RAM y CPU se refrescan con `Sondeo` cada pocos segundos.
"""
import os
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime

# --------------------------------------------------------------- salud
# Pesos de la penalización. Suman 100 para que la salud vaya de 0 a 100.
# Ajustar aquí cambia el reparto sin tocar la interfaz.
PESO_DISCO = 30
PESO_INICIO = 20
PESO_RAM = 25
PESO_MANTENIMIENTO = 25

# Ram del anillo de RAM: por debajo no penaliza, y a partir de ahí sube
# linealmente hasta el tope.
RAM_MINIMA = 50.0
RAM_MAXIMA = 90.0

# Días para llegar al tope de penalización por mantenimiento atrasado.
DIAS_MANTENIMIENTO_TOPE = 30

_PATRON_LOG = re.compile(r"^optimizador-(\d{4}-\d{2}-\d{2})\.log$")

# Caché de la comprobación de psutil (None = aún no comprobado).
_PSUTIL: bool | None = None


def penalizacion_disco(gb: float | None) -> int:
    """0-30 puntos: 2 puntos por GB recuperable, con tope."""
    if not gb or gb <= 0:
        return 0
    return min(PESO_DISCO, int(gb * 2))


def penalizacion_inicio(entradas: int | None) -> int:
    """0-20 puntos: 5 puntos por programa de inicio deshabilitable."""
    if not entradas or entradas <= 0:
        return 0
    return min(PESO_INICIO, entradas * 5)


def penalizacion_ram(pct: float | None) -> int:
    """0-25 puntos: sin penalizar hasta el 50 % de uso, tope al 90 %."""
    if pct is None or pct <= RAM_MINIMA:
        return 0
    if pct >= RAM_MAXIMA:
        return PESO_RAM
    proporcion = (pct - RAM_MINIMA) / (RAM_MAXIMA - RAM_MINIMA)
    return int(round(proporcion * PESO_RAM))


def penalizacion_mantenimiento(dias: int | None) -> int:
    """0-25 puntos según los días desde el último mantenimiento.

    Sin registros (`None`) no penaliza: no se puede afirmar que el
    equipo esté abandonado solo porque no haya logs.
    """
    if dias is None or dias <= 0:
        return 0
    return min(PESO_MANTENIMIENTO, (dias * PESO_MANTENIMIENTO) // DIAS_MANTENIMIENTO_TOPE)


def calcular_salud(
    gb: float | None,
    entradas: int | None,
    ram_pct: float | None,
    dias: int | None,
) -> int:
    """Salud del PC de 0 a 100 (100 = nada que optimizar).

    Fórmula documentada: se suman las cuatro penalizaciones y se resta
    del total. Cada peso está arriba, junto a su tramo.
    """
    total = (
        penalizacion_disco(gb)
        + penalizacion_inicio(entradas)
        + penalizacion_ram(ram_pct)
        + penalizacion_mantenimiento(dias)
    )
    return max(0, min(100, 100 - total))


# --------------------------------------------------------------- medición
def _carpeta_logs() -> str:
    """Carpeta de logs del producto (depende de si está empaquetado)."""
    from utils import LOG_DIR

    return LOG_DIR


def dias_desde_ultimo_log(base_logs: str | None = None) -> int | None:
    """Días desde el log de optimización más reciente.

    Es el único registro real de "cuándo se hizo mantenimiento" que
    tiene el proyecto: un fichero por día en `logs/`. Sin ficheros,
    devuelve `None`.
    """
    carpeta = base_logs if base_logs is not None else _carpeta_logs()
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return None

    fechas = []
    for nombre in nombres:
        coincidencia = _PATRON_LOG.match(nombre)
        if not coincidencia:
            continue
        try:
            fechas.append(datetime.strptime(coincidencia.group(1), "%Y-%m-%d").date())
        except ValueError:  # fecha imposible en el nombre: se ignora
            continue
    if not fechas:
        return None
    return max(0, (date.today() - max(fechas)).days)


def escanear_disco() -> float:
    """GB recuperables por la limpieza (solo lectura).

    Reutiliza los mismos cálculos que el test de efectividad y la vista
    previa, para que las tres cifras coincidan siempre.
    """
    from config import (
        CACHE_NAVEGADORES,
        RUTA_CACHE_ENTREGA,
        RUTA_CACHE_UPDATE,
        RUTA_PREFETCH,
        RUTAS_TEMPORALES,
    )
    from modules.analisis import (
        tamano_cache_firefox,
        tamano_papelera,
        tamano_recursivo,
    )

    plantillas = (
        list(RUTAS_TEMPORALES)
        + [RUTA_PREFETCH, RUTA_CACHE_UPDATE, RUTA_CACHE_ENTREGA]
        + list(CACHE_NAVEGADORES)
    )
    liberable = 0
    for plantilla in plantillas:
        ruta = os.path.expandvars(plantilla)
        if os.path.isdir(ruta):
            liberable += tamano_recursivo(ruta)
    liberable += tamano_papelera() + tamano_cache_firefox()
    return liberable / (1024 ** 3)


def contar_inicio() -> int:
    """Entradas de inicio seguras que aún están activas."""
    import winreg

    from config import ENTRADAS_INICIO_AUTO
    from modules.startup import CLAVES_INICIO, PREFIJO_DESHABILITADO

    total = 0
    for ambito, prefijo in ENTRADAS_INICIO_AUTO:
        for etiqueta, raiz, clave in CLAVES_INICIO:
            if etiqueta != ambito:
                continue
            try:
                with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                    indice = 0
                    while True:
                        try:
                            nombre, _, _ = winreg.EnumValue(k, indice)
                            indice += 1
                        except OSError:
                            break
                        if (nombre.startswith(prefijo)
                                and not nombre.startswith(PREFIJO_DESHABILITADO)):
                            total += 1
            except FileNotFoundError:
                continue
    return total


def hay_psutil() -> bool:
    """True si psutil está disponible (dependencia opcional).

    El resultado se guarda: se consulta en cada refresco del panel y no
    tiene sentido reintentar la importación cada 1,5 segundos.
    """
    global _PSUTIL
    if _PSUTIL is None:
        try:
            import psutil  # noqa: F401
            _PSUTIL = True
        except ImportError:
            _PSUTIL = False
    return _PSUTIL


def leer_ram_cpu() -> tuple[float, float] | None:
    """(RAM %, CPU %) del sistema, o None si psutil no está instalado."""
    if not hay_psutil():
        return None
    import psutil
    try:
        return psutil.virtual_memory().percent, psutil.cpu_percent(interval=None)
    except Exception:  # pragma: no cover - psutil roto o sin permisos
        return None

# --------------------------------------------------------------- instantánea
@dataclass
class Instantanea:
    """Foto de los datos del HUD en un momento dado."""

    gb: float | None = None
    inicio: int | None = None
    dias: int | None = None
    ram: float | None = None
    cpu: float | None = None
    salud: int = 100
    completa: bool = False


def recolectar() -> Instantanea:
    """Mide lo lento (disco, inicio, mantenimiento). Usar en un hilo."""
    from modules.hud.datos import dias_desde_ultimo_log as _dias

    gb = escanear_disco()
    inicio = contar_inicio()
    dias = _dias()
    return Instantanea(
        gb=gb,
        inicio=inicio,
        dias=dias,
        salud=calcular_salud(gb, inicio, None, dias),
        completa=True,
    )


class Sondeo:
    """Hilo que refresca RAM y CPU cada `intervalo` segundos.

    Lee de `psutil` en un hilo aparte para que la ventana nunca se
    congele y para no medir CPU dentro del bucle de eventos de Tk.
    """

    def __init__(self, intervalo: float = 1.5) -> None:
        self.intervalo = intervalo
        self.ultimo: tuple[float, float] | None = None
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def _bucle(self) -> None:
        while not self._parar.is_set():
            datos = leer_ram_cpu()
            if datos is not None:
                self.ultimo = datos
            # wait() en vez de sleep(): detener() no espera al intervalo.
            self._parar.wait(self.intervalo)

    def detener(self) -> None:
        self._parar.set()
        self._hilo = None
