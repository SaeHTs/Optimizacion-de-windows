"""🧹 Módulo 1: Limpieza de disco."""
import os
from concurrent.futures import ThreadPoolExecutor

from config import RUTA_CACHE_UPDATE, RUTA_PREFETCH, RUTAS_TEMPORALES
from utils import (
    confirmar,
    ejecutar_en_vivo,
    ejecutar_powershell,
    espacio_libre,
    fmt_bytes,
    pausa,
)


# ---------------------------------------------------------------- helpers
def _eliminar_contenido(ruta: str) -> tuple[int, int]:
    """Elimina el contenido de una carpeta en UNA sola pasada.

    Cuenta los bytes liberados mientras borra (scandir es más
    rápido que os.walk y evita la caminata previa de pre-conteo,
    que duplicaba el tiempo en carpetas con muchos archivos).
    """
    liberado = 0
    errores = 0
    try:
        entradas = list(os.scandir(ruta))
    except OSError:
        return 0, 0

    for entrada in entradas:
        try:
            if entrada.is_dir(follow_symlinks=False):
                # Recursión de una sola pasada por subcarpeta
                sub_liberado, sub_errores = _eliminar_contenido(entrada.path)
                liberado += sub_liberado
                errores += sub_errores
                try:
                    os.rmdir(entrada.path)
                except OSError:
                    errores += 1
            else:
                liberado += entrada.stat().st_size
                os.remove(entrada.path)
        except OSError:
            errores += 1

    return liberado, errores


# ---------------------------------------------------------------- operaciones
def limpiar_temporales(automatico: bool = False) -> None:
    """Elimina archivos temporales de usuario y de Windows.

    Las dos carpetas se procesan en parallo (más rápido en SSD).
    """
    print("\n🧹 Limpiando archivos temporales...")
    rutas = [os.path.expandvars(p) for p in RUTAS_TEMPORALES]
    rutas = [r for r in rutas if os.path.isdir(r)]
    if not rutas:
        print("  No hay carpetas temporales que limpiar.")
        return

    with ThreadPoolExecutor(max_workers=len(rutas)) as ejecutor:
        resultados = list(ejecutor.map(_eliminar_contenido, rutas))

    total = 0
    for ruta, (liberado, errores) in zip(rutas, resultados):
        total += liberado
        print(f"  • {ruta}: {fmt_bytes(liberado)} liberados"
              + (f" ({errores} archivos en uso)" if errores else ""))
    print(f"✅ Total liberado: {fmt_bytes(total)}")


def limpiar_prefetch(automatico: bool = False) -> None:
    """Elimina archivos de prefetch (Windows los reconstruye automáticamente)."""
    ruta = os.path.expandvars(RUTA_PREFETCH)
    print("\n🧹 Limpiando Prefetch...")
    if not automatico and not confirmar(
        "Se eliminarán los archivos de precarga (se regeneran solos). ¿Continuar?"
    ):
        print("   Operación cancelada.")
        return
    liberado, errores = _eliminar_contenido(ruta)
    print(f"✅ Prefetch limpiado: {fmt_bytes(liberado)} liberados"
          + (f" ({errores} errores)" if errores else ""))


def vaciar_papelera(automatico: bool = False) -> None:
    """Vacía la papelera de reciclaje de todas las unidades."""
    print("\n🗑️  Vaciando la papelera de reciclaje...")
    if not automatico and not confirmar("¿Vaciar la papelera de TODAS las unidades?"):
        print("   Operación cancelada.")
        return
    codigo, salida = ejecutar_powershell(
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
    )
    print("✅ Papelera vaciada." if codigo == 0 else f"⚠️  Sin cambios: {salida or 'ok'}")


def limpiar_cache_windows_update(automatico: bool = False) -> None:
    """Detiene Windows Update y elimina su caché de descargas."""
    print("\n🧹 Limpiando caché de Windows Update...")
    if not automatico and not confirmar(
        "Se detendrá temporalmente el servicio Windows Update. ¿Continuar?"
    ):
        print("   Operación cancelada.")
        return
    print("  Deteniendo servicios...")
    ejecutar_powershell("Stop-Service wuauserv -Force; Stop-Service bits -Force")
    ruta = os.path.expandvars(RUTA_CACHE_UPDATE)
    liberado, errores = _eliminar_contenido(ruta)
    print("  Reiniciando servicios...")
    ejecutar_powershell("Start-Service bits; Start-Service wuauserv")
    print(f"✅ Caché de Windows Update limpiada: {fmt_bytes(liberado)} liberados"
          + (f" ({errores} errores)" if errores else ""))


def limpiar_componentes_windows() -> None:
    """Ejecuta DISM para limpiar componentes obsoletos de Windows."""
    print("\n🧹 Limpiando componentes obsoletos de Windows (DISM)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo = ejecutar_en_vivo(
        "dism /Online /Cleanup-Image /StartComponentCleanup",
        tiempo_espera=1800,
    )
    print("✅ Limpieza de componentes finalizada."
          if codigo == 0 else "⚠️  Revisar el resultado de DISM.")


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Ejecuta TODA la limpieza sin preguntas intermedias."""
    print("\n" + "═" * 44)
    print("  ⚡ MODO AUTOMÁTICO — LIMPIEZA COMPLETA")
    print("═" * 44)
    limpiar_temporales(automatico=True)
    limpiar_prefetch(automatico=True)
    vaciar_papelera(automatico=True)
    limpiar_cache_windows_update(automatico=True)
    limpiar_componentes_windows()
    logger.info("Limpieza automática completada")


# ---------------------------------------------------------------- menú
def menu_limpieza(logger) -> None:
    espacio_antes = espacio_libre("C:")
    while True:
        print("\n" + "═" * 44)
        print("  🧹 LIMPIEZA DE DISCO")
        print("═" * 44)
        print("  1) 🗒️  Archivos temporales (usuario + Windows)")
        print("  2) ⚡ Prefetch")
        print("  3) 🗑️  Papelera de reciclaje")
        print("  4) 🔄 Caché de Windows Update")
        print("  5) 🧩 Componentes obsoletos (DISM)")
        print("  6) 🧼 TODO (limpieza completa)")
        print("  7) ⚡ MODO AUTOMÁTICO (sin preguntas)")
        print("  0) ⬅️  Volver")
        print("═" * 44)

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
        elif opcion == "7":
            modo_automatico(logger)
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
