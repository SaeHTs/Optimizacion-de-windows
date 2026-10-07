"""
Optimizador de Windows - Herramienta de optimización del sistema operativo
Proveedor: Axiios_HTs | Versión: 1.0
Ejecutar como Administrador: python main.py
"""
import ctypes
import os
import sys

# Forzar UTF-8 con respaldo seguro: los emojis nunca crashean la app
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass


def es_administrador() -> bool:
    """Verifica si el proceso tiene permisos de Administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def reiniciar_como_admin() -> None:
    """Reinicia el script con privilegios de Administrador (UAC)."""
    argumentos = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, argumentos, None, 1)


def main() -> None:
    if os.name != "nt":
        print("❌ Esta herramienta solo funciona en Windows.")
        sys.exit(1)

    if not es_administrador():
        print("⚠️  Esta herramienta requiere permisos de Administrador.")
        respuesta = input("¿Reiniciar como Administrador? (s/n): ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            reiniciar_como_admin()
        else:
            print("No se puede continuar sin permisos de Administrador.")
        sys.exit(0)

    # Importaciones diferidas (solo se usan dentro de Windows)
    from modules.disk_cleanup import menu_limpieza
    from modules.startup import menu_inicio
    from modules.performance import menu_rendimiento
    from modules.maintenance import menu_mantenimiento
    from utils import (
        confirmar,
        crear_punto_restauracion,
        info_sistema,
        pausa,
        setup_logger,
    )

    logger = setup_logger()
    logger.info("=== Optimizador de Windows iniciado ===")

    while True:
        print("=" * 52)
        print("   🖥️  OPTIMIZADOR DE WINDOWS - Menú principal")
        print("=" * 52)
        print("  1) 🧹 Limpieza de disco")
        print("  2) 🚀 Optimizar programas de inicio")
        print("  3) ⚡ Rendimiento general")
        print("  4) 🔧 Mantenimiento del sistema")
        print("  5) 🛡️  Crear punto de restauración")
        print("  6) ℹ️  Información del sistema")
        print("  0) 🚪 Salir")
        print("=" * 52)

        opcion = input("Seleccione una opción: ").strip()

        if opcion == "1":
            menu_limpieza(logger)
        elif opcion == "2":
            menu_inicio(logger)
        elif opcion == "3":
            menu_rendimiento(logger)
        elif opcion == "4":
            menu_mantenimiento(logger)
        elif opcion == "5":
            crear_punto_restauracion()
        elif opcion == "6":
            info_sistema()
        elif opcion == "0":
            print("👋 ¡Hasta luego!")
            logger.info("=== Optimizador de Windows cerrado ===")
            break
        else:
            print("❌ Opción no válida.")
        pausa()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Operación cancelada por el usuario.")
        sys.exit(0)
