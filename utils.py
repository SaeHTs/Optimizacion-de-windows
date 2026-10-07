"""Utilidades compartidas: ejecución de comandos, logs, seguridad."""
import ctypes
import logging
import os
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "optimizador.log")


# ---------------------------------------------------------------- comandos
def ejecutar_comando(comando: str, tiempo_espera: int = 600) -> tuple[int, str]:
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
        return -1, "⏱️  La operación excedió el tiempo de espera."
    except Exception as e:  # pragma: no cover
        return -1, f"❌ Error al ejecutar: {e}"


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


# ---------------------------------------------------------------- logging
def setup_logger() -> logging.Logger:
    """Configura el logger del proyecto (archivo optimizador.log)."""
    logger = logging.getLogger("OptimizadorWindows")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    manejador = logging.FileHandler(LOG_FILE, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(manejador)
    return logger


# ---------------------------------------------------------------- helpers
def confirmar(mensaje: str) -> bool:
    """Pide confirmación al usuario (s/n)."""
    respuesta = input(f"⚠️  {mensaje} (s/n): ").strip().lower()
    return respuesta in ("s", "si", "sí", "y", "yes")


def pausa() -> None:
    input("\nPresiona Enter para continuar...")


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


def crear_punto_restauracion() -> bool:
    """Crea un punto de restauración del sistema (requiere admin y Restaurar sistema activado)."""
    print("🛡️  Creando punto de restauración...")
    codigo, salida = ejecutar_powershell(
        "Checkpoint-Computer -Description 'Optimizador Windows' -RestorePointType MODIFY_SETTINGS"
    )
    if codigo == 0:
        print("✅ Punto de restauración creado correctamente.")
        return True
    print("⚠️  No se pudo crear el punto de restauración.")
    print(f"   Detalle: {salida or 'Sin detalles'}")
    print("   (Puede que 'Protección del sistema' esté desactivada en esta unidad)")
    return False


def proteger_cambios() -> None:
    """Ofrece crear un punto de restauración antes de cambios importantes."""
    if confirmar("¿Crear un punto de restauración antes de continuar?"):
        crear_punto_restauracion()


def info_sistema() -> None:
    """Muestra un resumen básico del sistema."""
    print("\nℹ️  Información del sistema")
    print("-" * 40)
    try:
        import psutil

        import platform

        print(f"  Sistema:   {platform.system()} {platform.release()} ({platform.version()})")
        print(f"  CPU:       {platform.processor() or 'Desconocida'}")
        print(f"  Memoria:   {fmt_bytes(psutil.virtual_memory().total)} total / "
              f"{fmt_bytes(psutil.virtual_memory().available)} disponible")
        print(f"  Disco C::  {fmt_bytes(shutil.disk_usage('C:').total)} total / "
              f"{fmt_bytes(shutil.disk_usage('C:').free)} libre")
        print(f"  Uptime:    {datetime.now() - datetime.fromtimestamp(psutil.boot_time())}")
    except ImportError:
        codigo, salida = ejecutar_comando("systeminfo")
        print(salida)
    print("-" * 40)
