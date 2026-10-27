"""Módulo central para la lógica compartida entre consola y GUI.

Contiene funciones puras que pueden ser utilizadas tanto por `main.py`
como por `gui.py` para evitar la duplicación de código.
"""
import ctypes
import sys

from i18n import tr


def verificar_permisos() -> bool:
    """Verifica si el proceso tiene permisos de Administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def reiniciar_como_admin() -> None:
    """Reinicia el script con privilegios de Administrador (UAC).

    En el exe empaquetado (frozen) no hay argumentos de script que
    relanzar: se reinicia el ejecutable tal cual.
    """
    if getattr(sys, "frozen", False):
        argumentos = ""
    else:
        partes = []
        for arg in sys.argv:
            # Escapar comillas dobles para evitar romper la línea de comandos
            arg_seguro = str(arg).replace('"', '\\"')
            partes.append(f'"{arg_seguro}"')
        argumentos = " ".join(partes)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, argumentos, None, 1
    )


def ejecutar_vista_previa(logger) -> None:
    """Ejecuta la vista previa (dry-run) de la optimización."""
    from modules.analisis import vista_previa
    vista_previa(logger)


def ejecutar_auto_completo(logger) -> None:
    """Ejecuta la secuencia completa de optimización.

    Muestra una barra de progreso por etapas (4 módulos) para que el
    usuario vea el avance global además del porcentaje de cada comando.
    """
    from utils import etapa

    from modules.disk_cleanup import modo_automatico as auto_limpieza
    from modules.startup import modo_automatico as auto_inicio
    from modules.performance import modo_automatico as auto_rendimiento
    from modules.maintenance import modo_automatico as auto_mantenimiento

    modulos = (
        (tr("🧹 Limpieza de disco"), auto_limpieza),
        (tr("🚀 Programas de inicio"), auto_inicio),
        (tr("⚡ Rendimiento general"), auto_rendimiento),
        (tr("🔧 Mantenimiento del sistema"), auto_mantenimiento),
    )
    total = len(modulos)
    etapa(0, total, tr("Iniciando optimización completa"))
    for indice, (nombre, funcion) in enumerate(modulos, start=1):
        print(f"\n━━ {nombre} ━━")
        funcion(logger)
        etapa(indice, total, nombre)

    print(tr("\n✅ Optimización COMPLETA finalizada."))
    print(tr("   Reinicia el equipo para aplicar todos los cambios."))
