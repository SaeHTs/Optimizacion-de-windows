"""🔧 Módulo 4: Mantenimiento del sistema."""
from concurrent.futures import ThreadPoolExecutor

from utils import (
    confirmar,
    ejecutar_comando,
    ejecutar_con_barra,
    etapa,
    pausa,
    proteger_cambios,
    tipo_unidad,
)
from i18n import tr

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
# CheckHealth devuelve código 0 aunque el almacén sea "reparable":
# el código de salida NO sirve para decidir; hay que leer el texto.
DISM_REPARABLE = (
    "repairable",
    "es reparable",
    "se puede reparar",
)


# ---------------------------------------------------------------- verificar
def verificar_sfc(silencioso: bool = False) -> str:
    """Verifica la integridad SIN reparar (más rápido que /scannow).

    Devuelve 'ok' si el sistema está íntegro, 'reparar' si no.
    Si ``silencioso`` es True, no imprime la salida del comando.
    """
    if not silencioso:
        print(tr("\n🔍 Verificando integridad del sistema (SFC verifyonly)..."))
        codigo, salida = ejecutar_con_barra(
            "sfc /verifyonly", tiempo_espera=900
        )
    else:
        codigo, salida = ejecutar_comando("sfc /verifyonly", tiempo_espera=900)
    texto = salida.lower()
    if any(marca in texto for marca in SFC_SANO):
        if not silencioso:
            print(tr("✅ SFC: sistema íntegro, sin violaciones."))
        return "ok"
    if not silencioso:
        print(tr("⚠️  SFC: se detectaron posibles problemas."))
    return "reparar"


def verificar_dism(silencioso: bool = False) -> str:
    """Verifica el almacén de componentes (CheckHealth, muy rápido).

    Si ``silencioso`` es True, no imprime la salida del comando.
    """
    if not silencioso:
        print(tr("\n🔍 Verificando almacén de componentes (DISM CheckHealth)..."))
        codigo, salida = ejecutar_con_barra(
            "DISM /Online /Cleanup-Image /CheckHealth", tiempo_espera=600
        )
    else:
        codigo, salida = ejecutar_comando(
            "DISM /Online /Cleanup-Image /CheckHealth", tiempo_espera=600
        )
    texto = salida.lower()
    if any(marca in texto for marca in DISM_REPARABLE):
        if not silencioso:
            print(tr("⚠️  DISM: almacén de componentes reparable."))
        return "reparar"
    if codigo == 0 or any(marca in texto for marca in DISM_SANO):
        if not silencioso:
            print(tr("✅ DISM: almacén de componentes sano."))
        return "ok"
    if not silencioso:
        print(tr("⚠️  DISM: corrupción en el almacén de componentes."))
    return "reparar"


# ---------------------------------------------------------------- operaciones
def reparar_sfc() -> None:
    """Ejecuta el comprobador de archivos del sistema."""
    print(tr("\n🔧 Comprobando archivos del sistema (SFC)..."))
    print(tr("   Puede tardar varios minutos, no cierres la ventana."))
    codigo, _ = ejecutar_con_barra("sfc /scannow", tiempo_espera=1800)
    print(tr("✅ SFC finalizado.") if codigo == 0
          else tr("⚠️  SFC reportó problemas; revisa el log."))


def reparar_dism() -> None:
    """Repara la imagen de Windows con DISM."""
    print(tr("\n🔧 Reparando la imagen de Windows (DISM)..."))
    print(tr("   Puede tardar varios minutos, no cierres la ventana."))
    codigo, _ = ejecutar_con_barra(
        "DISM /Online /Cleanup-Image /RestoreHealth", tiempo_espera=1800
    )
    print(tr("✅ DISM finalizado.") if codigo == 0
          else tr("⚠️  DISM reportó problemas."))


def optimizar_discos(automatico: bool = False) -> None:
    """Optimiza todas las unidades (TRIM en SSD / desfragmenta HDD).

    Detecta el tipo de cada unidad con `tipo_unidad()` y advierte
    según corresponda:
    - **HDD**: la desfragmentación reorganiza bloques físicos.
    - **SSD**: TRIM es casero; la defragmentación intensiva se evita.
    """
    print(tr("\n🔧 Optimizando unidades..."))

    # Detectar SSD/HDD y avisar del tipo de optimización a aplicar
    tipo = tipo_unidad("C:")
    if tipo == "SSD":
        print(tr("   💾 Unidad C: detectada como **SSD** → TRIM"))
        print(tr("      (seguro y rápido; no hay desgaste)"))
    elif tipo == "HDD":
        print(tr("   💾 Unidad C: detectada como **HDD** → desfragmentación"))
        print(tr("      (más lento, puede tardar mucho; mejora real)"))
    else:
        print(tr("   💾 No se pudo detectar el tipo (se aplica optimización normal)"))

    if not automatico and not confirmar(
        tr("¿Optimizar TODAS las unidades? (TRIM en SSD / desfragmentar HDD)")
    ):
        print(tr("   Operación cancelada."))
        return
    print(tr("   Puede tardar, según el tamaño de tus discos."))
    codigo, _ = ejecutar_con_barra("defrag /C /O /U", tiempo_espera=3600)
    print(tr("✅ Optimización de discos finalizada.")
          if codigo == 0 else tr("⚠️  Revisar el resultado de la optimización."))


def diagnostico_memoria() -> None:
    """Programa el comprobador de memoria de Windows al reiniciar."""
    print(tr("\n🔧 Comprobador de memoria de Windows..."))
    if not confirmar(tr("¿Reiniciar ahora para analizar la memoria RAM?")):
        print(tr("   Operación cancelada."))
        return
    print(tr("   El equipo se reiniciará y analizará la RAM..."))
    ejecutar_comando("mdsched /restart")


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Mantenimiento inteligente: verifica primero y solo
    repara lo que está dañado (mucho más rápido en PCs sanos).
    """
    print("\n" + "═" * 44)
    print(tr("  ⚡ MODO AUTOMÁTICO — MANTENIMIENTO"))
    print("═" * 44)
    print(tr("  🔍 Verificación inteligente (solo repara si es necesario)"))

    # 1) Verificaciones rápidas en paralelo (ambas son de solo
    #    lectura, por eso pueden correr a la vez)
    print(tr("   ⏳ Verificando integridad del sistema (SFC + DISM)..."))
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_sfc = ejecutor.submit(verificar_sfc, silencioso=True)
        futuro_dism = ejecutor.submit(verificar_dism, silencioso=True)
        estado_sfc = futuro_sfc.result()
        estado_dism = futuro_dism.result()
    print(tr("   ✅ Verificación completada."))
    etapa(1, 4, tr("Verificación SFC + DISM"))

    # 2) Reparar solo si es necesario. DISM primero: deja el
    #    almacén de componentes sano para que SFC acierte a
    #    la primera (si el almacén está dañado, SFC falla).
    if estado_dism == "reparar":
        reparar_dism()
    etapa(2, 4, tr("Reparación DISM")
          + (tr(" (aplicada)") if estado_dism == "reparar"
             else tr(" (no necesaria)")))
    if estado_sfc == "reparar":
        reparar_sfc()
    etapa(3, 4, tr("Reparación SFC")
          + (tr(" (aplicada)") if estado_sfc == "reparar"
             else tr(" (no necesaria)")))
    if estado_dism == "ok" and estado_sfc == "ok":
        print(tr("\n✅ Sistema íntegro: no fue necesario reparar nada."))

    # 3) Optimizar discos (TRIM en SSD / desfragmentar HDD)
    optimizar_discos(automatico=True)
    etapa(4, 4, tr("Optimización de unidades"))
    logger.info(tr("Mantenimiento automático completado"))


# ---------------------------------------------------------------- menú
def menu_mantenimiento(logger) -> None:
    from ui import Color, separador, titulo_menu
    while True:
        titulo_menu(tr("🔧 MANTENIMIENTO DEL SISTEMA"), Color.MAGENTA)

        separador(tr("Reparación (con barra de progreso)"))
        print(tr("  1) 🛠️  Reparar archivos del sistema (SFC)"))
        print(tr("  2) 🩺 Reparar imagen de Windows (DISM)"))

        separador(tr("Unidades y memoria"))
        print(tr("  3) 💾 Optimizar unidades (HDD/SSD) (con barra)"))
        print(tr("  4) 🧠 Comprobador de memoria RAM"))

        separador(tr("Combinados"))
        print(tr("  5) 🧼 Mantenimiento completo (SFC + DISM + discos)"))
        print(tr("  6) ⚡ MODO AUTOMÁTICO (inteligente: verifica primero) (con barras)"))
        print(tr("  0) ⬅️  Volver"))
        print("═" * 44)

        opcion = input(tr("Seleccione una opción: ")).strip()
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
            if confirmar(tr("¿Ejecutar el mantenimiento completo?")):
                reparar_sfc()
                reparar_dism()
                optimizar_discos()
        elif opcion == "6":
            proteger_cambios()
            modo_automatico(logger)
        elif opcion == "0":
            break
        else:
            print(tr("❌ Opción no válida."))
        logger.info(tr("Módulo de mantenimiento ejecutado: opción %s"), opcion)
        pausa()
