"""🔧 Módulo 4: Mantenimiento del sistema."""
from concurrent.futures import ThreadPoolExecutor

from utils import (
    confirmar,
    ejecutar_comando,
    ejecutar_en_vivo,
    ejecutar_en_vivo_capturado,
    pausa,
    proteger_cambios,
)

# Marcas de "sistema sano" en la salida (inglés y español)
SFC_SANO = (
    "did not find any integrity violations",
    "no encontró ninguna infracción",
    "no se encontró ninguna infracción",
)
DISM_SANO = (
    "no component store corruption",
    "no se detectó corrupción",
)


# ---------------------------------------------------------------- verificar
def _verificar_sfc() -> str:
    """Verifica la integridad SIN reparar (más rápido que /scannow).

    Devuelve 'ok' si el sistema está íntegro, 'reparar' si no.
    """
    print("\n🔍 Verificando integridad del sistema (SFC verifyonly)...")
    codigo, salida = ejecutar_en_vivo_capturado(
        "sfc /verifyonly", tiempo_espera=900
    )
    texto = salida.lower()
    if any(marca in texto for marca in SFC_SANO):
        print("✅ SFC: sistema íntegro, sin violaciones.")
        return "ok"
    print("⚠️  SFC: se detectaron posibles problemas.")
    return "reparar"


def _verificar_dism() -> str:
    """Verifica el almacén de componentes (CheckHealth, muy rápido)."""
    print("\n🔍 Verificando almacén de componentes (DISM CheckHealth)...")
    codigo, salida = ejecutar_en_vivo_capturado(
        "DISM /Online /Cleanup-Image /CheckHealth", tiempo_espera=600
    )
    texto = salida.lower()
    if codigo == 0 or any(marca in texto for marca in DISM_SANO):
        print("✅ DISM: almacén de componentes sano.")
        return "ok"
    print("⚠️  DISM: corrupción en el almacén de componentes.")
    return "reparar"


# ---------------------------------------------------------------- operaciones
def reparar_sfc() -> None:
    """Ejecuta el comprobador de archivos del sistema."""
    print("\n🔧 Comprobando archivos del sistema (SFC)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo = ejecutar_en_vivo("sfc /scannow", tiempo_espera=1800)
    print("✅ SFC finalizado." if codigo == 0
          else "⚠️  SFC reportó problemas; revisa el log.")


def reparar_dism() -> None:
    """Repara la imagen de Windows con DISM."""
    print("\n🔧 Reparando la imagen de Windows (DISM)...")
    print("   Puede tardar varios minutos, no cierres la ventana.")
    codigo = ejecutar_en_vivo(
        "DISM /Online /Cleanup-Image /RestoreHealth", tiempo_espera=1800
    )
    print("✅ DISM finalizado." if codigo == 0 else "⚠️  DISM reportó problemas.")


def optimizar_discos(automatico: bool = False) -> None:
    """Optimiza todas las unidades (TRIM en SSD / desfragmenta HDD)."""
    print("\n🔧 Optimizando unidades...")
    if not automatico and not confirmar(
        "¿Optimizar TODAS las unidades? (TRIM en SSD / desfragmentar HDD)"
    ):
        print("   Operación cancelada.")
        return
    print("   Puede tardar, según el tamaño de tus discos.")
    codigo = ejecutar_en_vivo("defrag /C /O /U", tiempo_espera=3600)
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


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Mantenimiento inteligente: verifica primero y solo
    repara lo que está dañado (mucho más rápido en PCs sanos).
    """
    print("\n" + "═" * 44)
    print("  ⚡ MODO AUTOMÁTICO — MANTENIMIENTO")
    print("═" * 44)
    print("  🔍 Verificación inteligente (solo repara si es necesario)")

    # 1) Verificaciones rápidas en paralelo (ambas son de solo
    #    lectura, por eso pueden correr a la vez)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_sfc = ejecutor.submit(_verificar_sfc)
        futuro_dism = ejecutor.submit(_verificar_dism)
        estado_sfc = futuro_sfc.result()
        estado_dism = futuro_dism.result()

    # 2) Reparar solo si es necesario. DISM primero: deja el
    #    almacén de componentes sano para que SFC acierte a
    #    la primera (si el almacén está dañado, SFC falla).
    if estado_dism == "reparar":
        reparar_dism()
    if estado_sfc == "reparar":
        reparar_sfc()
    if estado_dism == "ok" and estado_sfc == "ok":
        print("\n✅ Sistema íntegro: no fue necesario reparar nada.")

    # 3) Optimizar discos (TRIM en SSD / desfragmentar HDD)
    optimizar_discos(automatico=True)
    logger.info("Mantenimiento automático completado")


# ---------------------------------------------------------------- menú
def menu_mantenimiento(logger) -> None:
    while True:
        print("\n" + "═" * 44)
        print("  🔧 MANTENIMIENTO DEL SISTEMA")
        print("═" * 44)
        print("  1) 🛠️  Reparar archivos del sistema (SFC)")
        print("  2) 🩺 Reparar imagen de Windows (DISM)")
        print("  3) 💾 Optimizar unidades (HDD/SSD)")
        print("  4) 🧠 Comprobador de memoria RAM")
        print("  5) 🧼 Mantenimiento completo (SFC + DISM + discos)")
        print("  6) ⚡ MODO AUTOMÁTICO (inteligente: verifica primero)")
        print("  0) ⬅️  Volver")
        print("═" * 44)

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
        elif opcion == "6":
            proteger_cambios()
            modo_automatico(logger)
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")
        logger.info("Módulo de mantenimiento ejecutado: opción %s", opcion)
        pausa()
