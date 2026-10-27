"""
Optimización - Herramienta de optimización del sistema operativo
Proveedor: Axiios_HTs | Versión: definida en ui.VERSION
Ejecutar como Administrador: python main.py
"""
import os
import sys

# Forzar UTF-8 con respaldo seguro: los emojis nunca crashean la app
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

from i18n import get_idioma, set_idioma, tr
from modules.config_gui import ConfigGUI


def main() -> None:
    # Idioma: preferencia guardada o detección automática de Windows.
    # Debe fijarse ANTES de importar módulos que muestran texto.
    cfg_idioma = ConfigGUI()
    set_idioma(cfg_idioma.datos.get("idioma", "auto"))

    if os.name != "nt":
        print(tr("❌ Esta herramienta solo funciona en Windows."))
        sys.exit(1)

    # Requisito: Python de 64 bits (amd64)
    if sys.maxsize <= 2**32:
        print(tr("❌ Esta herramienta requiere Python de 64 bits."))
        print(tr("   Instala Python de 64 bits (amd64) y vuelve a intentarlo."))
        sys.exit(1)

    # Lógica compartida: fuente única en modules/core.py
    from modules.core import reiniciar_como_admin, verificar_permisos

    from ui import activar_ansi, banner, mostrar_splash, titulo_ventana, Color

    activar_ansi()
    titulo_ventana()
    banner()

    if not verificar_permisos():
        print(tr("⚠️  Esta herramienta requiere permisos de Administrador."))
        respuesta = input(tr("¿Reiniciar como Administrador? (s/n): ")).strip().lower()
        if respuesta in ("s", "si", "sí", "y", "yes"):
            reiniciar_como_admin()
        else:
            print(tr("No se puede continuar sin permisos de Administrador."))
        sys.exit(0)

    # Importaciones diferidas (solo se usan dentro de Windows)
    from modules.analisis import menu_analisis
    from modules.core import (
        ejecutar_auto_completo,
        ejecutar_vista_previa,
    )
    from modules.disk_cleanup import menu_limpieza
    from modules.startup import menu_inicio
    from modules.performance import menu_rendimiento
    from modules.maintenance import menu_mantenimiento
    from utils import (
        confirmar,
        crear_punto_restauracion,
        info_sistema,
        pausa,
        proteger_cambios,
        setup_logger,
    )
    from ui import VERSION

    # Pantalla de inicio con la imagen del producto
    mostrar_splash()

    logger = setup_logger()
    logger.info(tr("=== Optimización iniciado (v%s) ==="), VERSION)

    while True:
        banner()
        print(f"  {Color.VERDE}{tr('1) 🧹 Limpieza de disco')}{Color.RESET}")
        print(f"  {Color.CIAN}{tr('2) 🚀 Optimizar programas de inicio')}{Color.RESET}")
        print(f"  {Color.AMARILLO}{tr('3) ⚡ Rendimiento general')}{Color.RESET}")
        print(f"  {Color.MAGENTA}{tr('4) 🔧 Mantenimiento del sistema')}{Color.RESET}")
        print(f"  {Color.GRIS}{'  ' + '─' * 40}{Color.RESET}")
        print(f"  {Color.AZUL}{tr('5) 🛡️  Crear punto de restauración')}{Color.RESET}")
        print(f"  {Color.AZUL}{tr('6) ℹ️  Información del sistema')}{Color.RESET}")
        print(f"  {Color.NEGRITA}{tr('7) ⚡ MODO AUTOMÁTICO (optimización completa)')} {Color.VERDE}{tr('(barras)')}{Color.RESET}")
        print(f"  {Color.AZUL}{tr('8) 🔍 Análisis del sistema (dry-run)')} {Color.VERDE}{tr('(barras)')}{Color.RESET}")
        print(f"  {Color.VERDE}{tr('9) 🎯 Perfiles de optimización (Equilibrado/Gaming/Privacidad)')}{Color.RESET}")
        print(f"  {Color.AMARILLO}{tr('10) ⏪ Deshacer cambios de optimización (reversible)')}{Color.RESET}")
        print(f"  {Color.CIAN}11) 🌐 Idioma / Language{Color.RESET}")
        print(f"  {Color.GRIS}  0) 🚪 {tr('Salir')}{Color.RESET}")
        print("═" * 50)

        opcion = input(tr("Seleccione una opción: ")).strip()

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
        elif opcion == "7":
            print(tr("\n⚡ MODO AUTOMÁTICO: ejecuta TODAS las optimizaciones."))
            print(tr("   Incluye SFC y DISM: puede tardar varios minutos."))
            print(tr("\n🔍 Paso 1/2 — VISTA PREVIA (dry-run) antes de continuar..."))
            ejecutar_vista_previa(logger)
            print("\n" + "═" * 50)
            if confirmar(tr("¿Proceder con la optimización completa mostrada?")):
                proteger_cambios()
                print(tr("\n🚀 Paso 2/2 — Ejecutando optimización completa..."))
                ejecutar_auto_completo(logger)
        elif opcion == "8":
            menu_analisis(logger)
        elif opcion == "9":
            from modules.performance import menu_perfiles
            menu_perfiles()
        elif opcion == "10":
            from modules.performance import deshacer_cambios
            deshacer_cambios()
        elif opcion == "11":
            nuevo = "en" if get_idioma() == "es" else "es"
            cfg_idioma.datos["idioma"] = nuevo
            cfg_idioma.guardar()
            set_idioma(nuevo)
            print(tr("🌐 Idioma cambiado a español."))
        elif opcion == "0":
            print(tr("👋 ¡Hasta luego!"))
            logger.info(tr("=== Optimización cerrado ==="))
            break
        else:
            print(tr("❌ Opción no válida."))
        pausa()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(tr("\n👋 Operación cancelada por el usuario."))
        sys.exit(0)
