"""🔧 Módulo 4: Mantenimiento del sistema."""
from utils import (
    confirmar,
    ejecutar_comando,
    pausa,
    proteger_cambios,
)


# ---------------------------------------------------------------- operaciones
def reparar_sfc() -> None:
    """Ejecuta el comprobador de archivos del sistema."""
    print("\n🔧 Comprobando archivos del sistema (SFC)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo, salida = ejecutar_comando("sfc /scannow", tiempo_espera=1800)
    if salida:
        for linea in salida.splitlines():
            if linea.strip():
                print(f"   {linea}")
    print("✅ SFC finalizado." if codigo == 0 else "⚠️  SFC reportó problemas; revisa el log.")


def reparar_dism() -> None:
    """Repara la imagen de Windows con DISM."""
    print("\n🔧 Reparando la imagen de Windows (DISM)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo, salida = ejecutar_comando(
        "DISM /Online /Cleanup-Image /RestoreHealth", tiempo_espera=1800
    )
    if salida:
        for linea in salida.splitlines():
            if linea.strip():
                print(f"   {linea}")
    print("✅ DISM finalizado." if codigo == 0 else "⚠️  DISM reportó problemas.")


def optimizar_discos() -> None:
    """Optimiza todas las unidades (desfragmenta HDD, TRIM en SSD)."""
    print("\n🔧 Optimizando unidades...")
    if not confirmar("¿Optimizar TODAS las unidades? (TRIM en SSD / desfragmentar HDD)"):
        print("   Operación cancelada.")
        return
    print("   Puede tardar, según el tamaño de tus discos.")
    codigo, salida = ejecutar_comando("defrag /C /O /U", tiempo_espera=3600)
    if salida:
        for linea in salida.splitlines():
            if linea.strip():
                print(f"   {linea}")
    print("✅ Optimización de discos finalizada."
          if codigo == 0 else "⚠️  Revisar el resultado de la optimización.")


def diagnostico_memoria() -> None:
    """Programa el comprobador de memoria de Windows al reiniciar."""
    print("\n🔧 Comprobador de memoria de Windows...")
    if not confirmar("¿Reiniciar ahora para analizar la memoria RAM?"):
        print("   Operación cancelada.")
        return
    print("   El equipo se reiniciará y analizará la RAM...")
    ejecutar_comando("mdsched /restart")


# ---------------------------------------------------------------- menú
def menu_mantenimiento(logger) -> None:
    while True:
        print("\n" + "=" * 44)
        print("  🔧 MANTENIMIENTO DEL SISTEMA")
        print("=" * 44)
        print("  1) 🛠️  Reparar archivos del sistema (SFC)")
        print("  2) 🩺 Reparar imagen de Windows (DISM)")
        print("  3) 💾 Optimizar unidades (HDD/SSD)")
        print("  4) 🧠 Comprobador de memoria RAM")
        print("  5) 🧼 Mantenimiento completo (SFC + DISM + discos)")
        print("  0) ⬅️  Volver")
        print("=" * 44)

        opcion = input("Seleccione una opción: ").strip()
        if opcion == "1":
            reparar_sfc()
        elif opcion == "2":
            reparar_dism()
        elif opcion == "3":
            optimizar_discos()
        elif opcion == "4":
            diagnostico_memoria()
        elif opcion == "5":
            proteger_cambios()
            if confirmar("¿Ejecutar el mantenimiento completo?"):
                reparar_sfc()
                reparar_dism()
                optimizar_discos()
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")
        logger.info("Módulo de mantenimiento ejecutado: opción %s", opcion)
        pausa()
