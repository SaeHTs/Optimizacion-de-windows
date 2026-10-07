"""⚡ Módulo 3: Rendimiento general."""
import re
import winreg

from config import PLANES_ENERGIA, SERVICIOS_OPCIONALES
from utils import (
    confirmar,
    ejecutar_comando,
    pausa,
    proteger_cambios,
)

CLAVE_EFECTOS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"


# ---------------------------------------------------------------- energía
def listar_planes() -> None:
    """Muestra los planes de energía disponibles y el activo."""
    codigo, salida = ejecutar_comando("powercfg /list")
    print("\n⚡ Planes de energía:")
    print(salida if codigo == 0 else "⚠️  No se pudieron listar los planes.")


def activar_plan() -> None:
    """Activa un plan de energía predefinido."""
    listar_planes()
    print("\n  1) Alto rendimiento")
    print("  2) Equilibrado (recomendado)")
    print("  3) Ahorro de energía")
    opcion = input("Seleccione un plan: ").strip()
    alias = {"1": "SCHEME_MIN", "2": "SCHEME_BALANCED", "3": "SCHEME_MAX"}.get(opcion)
    if not alias:
        print("❌ Opción no válida.")
        return
    if confirmar(f"¿Activar el plan '{PLANES_ENERGIA[alias]}'?"):
        codigo, salida = ejecutar_comando(f"powercfg /setactive {alias}")
        print(f"✅ Plan '{PLANES_ENERGIA[alias]}' activado."
              if codigo == 0 else f"⚠️  No se pudo cambiar: {salida}")


# ---------------------------------------------------------------- visuales
def efectos_visuales(mejor_rendimiento: bool = True) -> None:
    """Ajusta los efectos visuales (2 = mejor rendimiento, 0 = Windows decide)."""
    valor = 2 if mejor_rendimiento else 0
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, CLAVE_EFECTOS, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, valor)
        print("✅ Efectos visuales ajustados "
              + "(priorizando rendimiento)." if mejor_rendimiento
              else "✅ Efectos visuales en modo automático.")
        print("   Puede requerir cerrar sesión para aplicarse por completo.")
    except OSError as e:
        print(f"❌ Error: {e}")


# ---------------------------------------------------------------- servicios
def _estado_servicio(nombre: str) -> str:
    """Devuelve el estado actual de un servicio (RUNNING/STOPPED/etc.)."""
    codigo, salida = ejecutar_comando(f'sc query "{nombre}"')
    if codigo != 0:
        return "?"
    for linea in salida.splitlines():
        if "STATE" in linea:
            m = re.search(r"STATE\s*:\s*\d+\s+(\w+)", linea)
            if m:
                return m.group(1)
    return "?"


def gestionar_servicios(deshabilitar: bool = True) -> None:
    """Deshabilita o restaura los servicios opcionales de la lista."""
    accion = "Deshabilitar" if deshabilitar else "Restaurar (manual)"
    print(f"\n🔧 {accion} servicios opcionales:")
    for nombre, descripcion in SERVICIOS_OPCIONALES.items():
        estado = _estado_servicio(nombre)
        print(f"  • {nombre:<18} {descripcion:<45} [{estado}]")

    if not confirmar(f"¿{accion} los servicios seleccionados?"):
        print("   Operación cancelada.")
        return

    for nombre, descripcion in SERVICIOS_OPCIONALES.items():
        if deshabilitar:
            print(f"  ⏸️  Deteniendo {nombre}...")
            ejecutar_comando(f'sc stop "{nombre}"')
            codigo, salida = ejecutar_comando(f'sc config "{nombre}" start= disabled')
        else:
            codigo, salida = ejecutar_comando(f'sc config "{nombre}" start= demand')
        print(f"    {'✅' if codigo == 0 else '⚠️ '} {nombre}: "
              f"{salida.strip().splitlines()[-1] if salida.strip() else 'ok'}")


# ---------------------------------------------------------------- menú
def menu_rendimiento(logger) -> None:
    while True:
        print("\n" + "=" * 44)
        print("  ⚡ RENDIMIENTO GENERAL")
        print("=" * 44)
        print("  1) 🔋 Planes de energía")
        print("  2) 🎨 Efectos visuales (priorizar rendimiento)")
        print("  3) 🎨 Restaurar efectos visuales (automático)")
        print("  4) 🔌 Deshabilitar servicios opcionales")
        print("  5) 🔌 Restaurar servicios opcionales")
        print("  0) ⬅️  Volver")
        print("=" * 44)

        opcion = input("Seleccione una opción: ").strip()
        if opcion == "1":
            activar_plan()
        elif opcion == "2":
            proteger_cambios()
            efectos_visuales(mejor_rendimiento=True)
        elif opcion == "3":
            efectos_visuales(mejor_rendimiento=False)
        elif opcion == "4":
            proteger_cambios()
            gestionar_servicios(deshabilitar=True)
        elif opcion == "5":
            gestionar_servicios(deshabilitar=False)
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")
        logger.info("Módulo de rendimiento ejecutado: opción %s", opcion)
        pausa()
