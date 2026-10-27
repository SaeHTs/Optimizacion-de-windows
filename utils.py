"""Utilidades compartidas: ejecución de comandos, logs, seguridad."""
import functools
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

from i18n import tr

# En el exe congelado, __file__ apunta a la carpeta temporal _MEIxxxx
# (se borra al salir): el log debe ir junto al ejecutable.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Un archivo de log por día dentro de la carpeta logs/ junto al
# ejecutable/script. Si la carpeta no se puede crear (ej. Program
# Files protegido), se usa optimizador.log como antes.
LOG_DIR = os.path.join(BASE_DIR, "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_FILE = os.path.join(
        LOG_DIR, f"optimizador-{datetime.now():%Y-%m-%d}.log"
    )
except OSError:  # pragma: no cover
    LOG_FILE = os.path.join(BASE_DIR, "optimizador.log")


# ---------------------------------------------------------------- comandos
def ejecutar_comando(comando: str, tiempo_espera: int = 60) -> tuple[int, str]:
    """Ejecuta un comando del sistema y devuelve (código de salida, salida de texto)."""
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=tiempo_espera,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        salida = (resultado.stdout or "") + (resultado.stderr or "")
        return resultado.returncode, salida.strip()
    except subprocess.TimeoutExpired:
        return -1, tr("⏱️  La operación excedió el tiempo de espera.")
    except Exception as e:  # pragma: no cover
        return -1, tr("❌ Error al ejecutar: {e}").format(e=e)


def ejecutar_powershell(script: str, tiempo_espera: int = 600) -> tuple[int, str]:
    """Ejecuta un script de PowerShell evitando la política de ejecución."""
    return ejecutar_comando(
        f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{script}"',
        tiempo_espera,
    )


def ejecutar_en_vivo_capturado(
    comando: str, tiempo_espera: int = 600
) -> tuple[int, str]:
    """Ejecuta mostrando la salida en vivo y además la devuelve.

    Útil para operaciones largas cuyo resultado hay que analizar
    (por ejemplo, sfc /verifyonly).
    """
    proceso = None
    lineas: list[str] = []
    try:
        proceso = subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if proceso.stdout:
            for linea in proceso.stdout:
                if linea.strip():
                    lineas.append(linea)
                    print(f"   {linea.rstrip()}")
        proceso.wait(timeout=tiempo_espera)
        return proceso.returncode if proceso.returncode is not None else -1, "".join(lineas)
    except subprocess.TimeoutExpired:
        if proceso:
            proceso.kill()
        return -1, "".join(lineas)
    except Exception:
        return -1, "".join(lineas)


def ejecutar_en_vivo(comando: str, tiempo_espera: int = 600) -> int:
    """Ejecuta un comando mostrando la salida en vivo.

    Más rápido en percepción: el usuario ve el progreso
    al instante. Solo devuelve el código de salida.
    """
    codigo, _ = ejecutar_en_vivo_capturado(comando, tiempo_espera)
    return codigo


# ---------------------------------------------------------------- barra de progreso
def etapa(actual: int, total: int, nombre: str, ancho: int = 28) -> None:
    """Muestra el avance por pasos de una operación multi-etapa.

    - Consola interactiva: dibuja ``[████░░░░] 3/7 · Papelera``.
    - GUI (no tty): emite ``Progreso: N%``, que ``gui._Redireccion``
      captura para alimentar la barra visual real (ttk.Progressbar),
      más una línea descriptiva de la etapa.

    Usar en flujos largos compuestos por operaciones que no reportan
    porcentaje propio (limpieza de carpetas, análisis, modo automático).
    """
    actual = max(0, min(actual, total))
    porcentaje = int(actual * 100 / total) if total else 100
    interactivo = getattr(sys.stdout, "isatty", lambda: False)()
    if interactivo:
        lleno = int(ancho * porcentaje / 100)
        barra = "█" * lleno + "░" * (ancho - lleno)
        print(f"  [{barra}] {actual}/{total} · {nombre}")
    else:
        print(f"Progreso: {porcentaje}%")
        print(f"   {tr('Etapa')} {actual}/{total}: {nombre}")


def _dibujar_barra(porcentaje: int, ancho: int = 30) -> None:
    """Dibuja una barra de progreso en la consola (sin salto de línea)."""
    porcentaje = max(0, min(100, porcentaje))
    lleno = int(ancho * porcentaje / 100)
    barra = "█" * lleno + "░" * (ancho - lleno)
    print(f"\r   [{barra}] {porcentaje:3d}%", end="", flush=True)


def ejecutar_con_barra(
    comando: str, tiempo_espera: int = 1800
) -> tuple[int, str]:
    """Ejecuta un comando y muestra una barra de progreso.

    Extrae el porcentaje de la salida del comando (ej. "11%") y lo
    muestra como una barra visual en consola. En entornos no
    interactivos (GUI), muestra mensajes de progreso cada 10%.

    Devuelve (código de salida, salida completa).
    """
    proceso = None
    lineas: list[str] = []
    ultimo_mostrado = -1
    patron = re.compile(r"(\d+)%")
    interactivo = getattr(sys.stdout, "isatty", lambda: False)()
    try:
        proceso = subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if proceso.stdout:
            for linea in proceso.stdout:
                lineas.append(linea)
                match = patron.search(linea)
                if match:
                    porcentaje = int(match.group(1))
                    if interactivo:
                        _dibujar_barra(porcentaje)
                    elif porcentaje % 10 == 0 and porcentaje != ultimo_mostrado:
                        print(f"   Progreso: {porcentaje}%")
                        ultimo_mostrado = porcentaje
                elif linea.strip():
                    if interactivo:
                        # Limpia la línea de la barra antes de imprimir texto
                        print(f"\r{' ' * 60}\r   {linea.rstrip()}")
                    else:
                        print(f"   {linea.rstrip()}")
        proceso.wait(timeout=tiempo_espera)
    except subprocess.TimeoutExpired:
        if proceso:
            proceso.kill()
        return -1, "".join(lineas)
    except Exception:  # pragma: no cover
        return -1, "".join(lineas)
    finally:
        if interactivo:
            print()  # Salto de línea final tras la barra
    return (proceso.returncode if proceso.returncode is not None else -1), "".join(lineas)


# ---------------------------------------------------------------- logging
def setup_logger() -> logging.Logger:
    """Configura el logger del proyecto (log por fecha en logs/)."""
    logger = logging.getLogger("OptimizadorWindows")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        manejador = logging.FileHandler(LOG_FILE, encoding="utf-8")
    except OSError:
        # Carpeta del exe de solo lectura (Escritorio con "Acceso
        # controlado a carpetas", unidad de red...): caer a %TEMP%
        # antes que crashear el arranque del programa.
        try:
            fallback = os.path.join(
                tempfile.gettempdir(),
                f"optimizador-{datetime.now():%Y-%m-%d}.log",
            )
            manejador = logging.FileHandler(fallback, encoding="utf-8")
            print(tr("⚠️  Logs: sin permisos junto al programa; usando {ruta}").format(ruta=fallback))
        except OSError:  # pragma: no cover
            manejador = logging.NullHandler()
    manejador.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(manejador)
    return logger


# ---------------------------------------------------------------- helpers
def confirmar(mensaje: str) -> bool:
    """Pide confirmación al usuario (s/n)."""
    respuesta = input(f"⚠️  {mensaje} {tr('(s/n)')}: ").strip().lower()
    return respuesta in ("s", "si", "sí", "y", "yes")


def pausa() -> None:
    input(tr("\nPresiona Enter para continuar..."))


def fmt_bytes(num: float) -> str:
    """Formatea bytes a una unidad legible."""
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.1f} {unidad}"
        num /= 1024
    return f"{num:.1f} PB"


def espacio_libre(unidad: str = "C:") -> int:
    """Devuelve el espacio libre en bytes de la unidad indicada."""
    try:
        return shutil.disk_usage(unidad).free
    except Exception:
        return 0


@functools.lru_cache(maxsize=16)
def tipo_unidad(unidad: str = "C:") -> str:
    """Devuelve 'SSD', 'HDD' o '?' según el tipo medio de la unidad.

    Mapea la letra de unidad a su disco físico (Get-Partition →
    Get-Disk → Get-PhysicalDisk), así discos mixtos no se confunden.
    Solo lectura — no modifica nada. Se cachea: el tipo de disco no
    cambia mientras la app está abierta y cada consulta lanza PowerShell.
    """
    letra = unidad.rstrip(":").strip().upper()
    if len(letra) != 1 or not letra.isalpha():
        return "?"
    codigo, salida = ejecutar_powershell(
        f"(Get-Partition -DriveLetter {letra} | Get-Disk | Get-PhysicalDisk"
        " | Select-Object -ExpandProperty MediaType -Unique) -join ' '"
    )
    if codigo != 0 or not salida:
        return "?"
    texto = salida.strip().lower()
    if "ssd" in texto or "nvme" in texto:
        return "SSD"
    if "hdd" in texto:
        return "HDD"
    return "?"


@functools.lru_cache(maxsize=1)
def es_laptop() -> bool:
    """Devuelve True si el equipo tiene batería (es una laptop).

    Solo lectura: consulta Win32_Battery sin modificar nada. Se cachea
    porque el hardware no cambia y cada consulta lanza PowerShell.
    """
    codigo, salida = ejecutar_powershell(
        "Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty Name"
    )
    return codigo == 0 and salida.strip() != ""


def crear_punto_restauracion() -> bool:
    """Crea un punto de restauración del sistema (requiere admin y Restaurar sistema activado)."""
    print(tr("🛡️  Creando punto de restauración..."))
    codigo, salida = ejecutar_powershell(
        "Checkpoint-Computer -Description 'Optimizador Windows' -RestorePointType MODIFY_SETTINGS"
    )
    if codigo == 0:
        print(tr("✅ Punto de restauración creado correctamente."))
        return True
    print(tr("⚠️  No se pudo crear el punto de restauración."))
    print(tr("   Detalle: {detalle}").format(detalle=salida or tr("Sin detalles")))
    print(tr("   (Puede que 'Protección del sistema' esté desactivada en esta unidad)"))
    return False


def proteger_cambios() -> None:
    """Ofrece crear un punto de restauración antes de cambios importantes."""
    if confirmar(tr("¿Crear un punto de restauración antes de continuar?")):
        crear_punto_restauracion()


def info_sistema() -> None:
    """Muestra un resumen básico del sistema."""
    print(tr("\nℹ️  Información del sistema"))
    print("-" * 40)
    try:
        import psutil

        import platform

        etapa(1, 3, tr("Sistema operativo"))
        print(tr("  Sistema:   {so}").format(
            so=f"{platform.system()} {platform.release()} ({platform.version()})"))
        print(tr("  CPU:       {cpu}").format(cpu=platform.processor() or tr("Desconocida")))
        etapa(2, 3, tr("Memoria y disco"))
        memoria = psutil.virtual_memory()
        disco = shutil.disk_usage("C:")
        print(tr("  Memoria:   {total} total / {disponible} disponible").format(
            total=fmt_bytes(memoria.total),
            disponible=fmt_bytes(memoria.available)))
        print(tr("  Disco C::  {total} total / {libre} libre").format(
            total=fmt_bytes(disco.total),
            libre=fmt_bytes(disco.free)))
        etapa(3, 3, tr("Tiempo de actividad"))
        print(tr("  Uptime:    {tiempo}").format(
            tiempo=datetime.now() - datetime.fromtimestamp(psutil.boot_time())))
    except ImportError:
        etapa(1, 1, tr("Consultando systeminfo (puede tardar)"))
        codigo, salida = ejecutar_comando("systeminfo")
        print(salida)
    print("-" * 40)
