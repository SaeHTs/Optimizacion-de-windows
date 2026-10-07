"""🧹 Módulo 1: Limpieza de disco."""
import os
import shutil

from config import RUTA_CACHE_UPDATE, RUTA_PREFETCH, RUTAS_TEMPORALES
from utils import (
    confirmar,
    ejecutar_comando,
    ejecutar_powershell,
    espacio_libre,
    fmt_bytes,
    pausa,
)


# ---------------------------------------------------------------- helpers
def _tamano_carpeta(ruta: str) -> int:
    """Calcula el tamaño total de una carpeta en bytes."""
    total = 0
    for dirpath, _, archivos in os.walk(ruta):
        for archivo in archivos:
            try:
                total += os.path.getsize(os.path.join(dirpath, archivo))
            except OSError:
                pass
    return total


def _eliminar_contenido(ruta: str) -> tuple[int, int]:
    """Elimina el contenido de una carpeta. Devuelve (bytes liberados, errores)."""
    liberado = _tamano_carpeta(ruta)
    errores = 0
    for dirpath, dirnames, archivos in os.walk(ruta):
        for archivo in archivos:
            try:
                os.remove(os.path.join(dirpath, archivo))
            except OSError:
                errores += 1
        for subcarpeta in dirnames:
            try:
                shutil.rmtree(os.path.join(dirpath, subcarpeta))
            except OSError:
                errores += 1
    return liberado, errores


# ---------------------------------------------------------------- operaciones
def limpiar_temporales() -> None:
    """Elimina archivos temporales de usuario y de Windows."""
    print("\n🧹 Limpiando archivos temporales...")
    total_liberado = 0
    for plantilla in RUTAS_TEMPORALES:
        ruta = os.path.expandvars(plantilla)
        if not os.path.isdir(ruta):
            continue
        liberado, errores = _eliminar_contenido(ruta)
        total_liberado += liberado
        print(f"  • {ruta}: {fmt_bytes(liberado)} liberados"
              + (f" ({errores} archivos en uso)" if errores else ""))
    print(f"✅ Total liberado: {fmt_bytes(total_liberado)}")


def limpiar_prefetch() -> None:
    """Elimina archivos de prefetch (Windows los reconstruye automáticamente)."""
    ruta = os.path.expandvars(RUTA_PREFETCH)
    print("\n🧹 Limpiando Prefetch...")
    if not confirmar("Se eliminarán los archivos de precarga (se regeneran solos). ¿Continuar?"):
        print("   Operación cancelada.")
        return
    liberado, errores = _eliminar_contenido(ruta)
    print(f"✅ Prefetch limpiado: {fmt_bytes(liberado)} liberados")


def vaciar_papelera() -> None:
    """Vacía la papelera de reciclaje de todas las unidades."""
    print("\n🗑️  Vaciando la papelera de reciclaje...")
    if not confirmar("¿Vaciar la papelera de TODAS las unidades?"):
        print("   Operación cancelada.")
        return
    codigo, salida = ejecutar_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    print("✅ Papelera vaciada." if codigo == 0 else f"⚠️  Sin cambios: {salida or 'ok'}")


def limpiar_cache_windows_update() -> None:
    """Detiene Windows Update y elimina su caché de descargas."""
    print("\n🧹 Limpiando caché de Windows Update...")
    if not confirmar("Se detendrá temporalmente el servicio Windows Update. ¿Continuar?"):
        print("   Operación cancelada.")
        return
    print("  Deteniendo servicios...")
    ejecutar_comando("net stop wuauserv")
    ejecutar_comando("net stop bits")
    ruta = os.path.expandvars(RUTA_CACHE_UPDATE)
    liberado, errores = _eliminar_contenido(ruta)
    print("  Reiniciando servicios...")
    ejecutar_comando("net start bits")
    ejecutar_comando("net start wuauserv")
    print(f"✅ Caché de Windows Update limpiada: {fmt_bytes(liberado)} liberados")


def limpiar_componentes_windows() -> None:
    """Ejecuta DISM para limpiar componentes obsoletos de Windows."""
    print("\n🧹 Limpiando componentes obsoletos de Windows (DISM)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo, salida = ejecutar_comando(
        "dism /Online /Cleanup-Image /StartComponentCleanup", tiempo_espera=1800
    )
    if salida:
        print(f"   {salida}")
    print("✅ Limpieza de componentes finalizada." if codigo == 0 else "⚠️  Revisar el resultado de DISM.")


# ---------------------------------------------------------------- menú
def menu_limpieza(logger) -> None:
    espacio_antes = espacio_libre("C:")
    while True:
        print("\n" + "=" * 44)
        print("  🧹 LIMPIEZA DE DISCO")
        print("=" * 44)
        print("  1) 🗒️  Archivos temporales (usuario + Windows)")
        print("  2) ⚡ Prefetch")
        print("  3) 🗑️  Papelera de reciclaje")
        print("  4) 🔄 Caché de Windows Update")
        print("  5) 🧩 Componentes obsoletos (DISM)")
        print("  6) 🧼 TODO (limpieza completa)")
        print("  0) ⬅️  Volver")
        print("=" * 44)

        opcion = input("Seleccione una opción: ").strip()
        if opcion == "1":
            limpiar_temporales()
        elif opcion == "2":
            limpiar_prefetch()
        elif opcion == "3":
            vaciar_papelera()
        elif opcion == "4":
            limpiar_cache_windows_update()
        elif opcion == "5":
            limpiar_componentes_windows()
        elif opcion == "6":
            if confirmar("¿Ejecutar la limpieza completa?"):
                limpiar_temporales()
                limpiar_prefetch()
                vaciar_papelera()
                limpiar_cache_windows_update()
                limpiar_componentes_windows()
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")

        espacio_despues = espacio_libre("C:")
        ganado = espacio_despues - espacio_antes
        if ganado > 0:
            print(f"\n💾 Espacio libre en C: ahora: {fmt_bytes(espacio_despues)} "
                  f"(+{fmt_bytes(ganado)} liberados)")
        logger.info("Módulo de limpieza ejecutado: opción %s", opcion)
        pausa()
