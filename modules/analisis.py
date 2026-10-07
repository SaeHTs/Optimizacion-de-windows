"""🔍 Módulo 5: Análisis del sistema (dry-run).

Muestra qué ocupa espacio y qué haría el optimizador
SIN cambiar nada del sistema.
"""
import os
import shutil
import winreg
from concurrent.futures import ThreadPoolExecutor

from config import (
    ENTRADAS_INICIO_AUTO,
    RUTA_CACHE_UPDATE,
    RUTA_PREFETCH,
    RUTAS_TEMPORALES,
    SERVICIOS_OPCIONALES,
)
from modules.maintenance import _verificar_dism, _verificar_sfc
from modules.performance import CLAVE_EFECTOS, _estados_servicios
from modules.startup import CLAVES_INICIO, PREFIJO_DESHABILITADO
from utils import (
    ejecutar_comando,
    ejecutar_powershell,
    fmt_bytes,
    pausa,
)

# Rutas conocidas que ocupan espacio (algunas limpiables,
# otras solo informativas como Descargas)
RUTAS_LIMPIABLES = [
    ("Archivos temporales del usuario",
     os.path.expandvars("%TEMP%")),
    ("Temporales de Windows",
     os.path.expandvars(r"%WINDIR%\Temp")),
    ("Prefetch", os.path.expandvars(RUTA_PREFETCH)),
    ("Caché de Windows Update",
     os.path.expandvars(RUTA_CACHE_UPDATE)),
    ("Optimización de entrega (Update)",
     os.path.expandvars(
         r"%WINDIR%\SoftwareDistribution\DeliveryOptimization")),
    ("Descargas del usuario (informativo)",
     os.path.expandvars(r"%USERPROFILE%\Downloads")),
    ("Caché de Chrome",
     os.path.expandvars(
         r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache")),
    ("Caché de Edge",
     os.path.expandvars(
         r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache")),
    ("Caché de Firefox",
     os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")),
    ("Windows.old (actualización anterior)",
     os.path.expandvars(r"%SYSTEMDRIVE%\Windows.old")),
]

ARCHIVOS_SISTEMA = ("hiberfil.sys", "pagefile.sys", "swapfile.sys")

NOMBRES_EFECTOS = {
    0: "Windows decide",
    1: "Mejor apariencia",
    2: "Mejor rendimiento",
    3: "Personalizado",
}


# ---------------------------------------------------------------- helpers
def _tamano_recursivo(ruta: str) -> int:
    """Calcula el tamaño total de una carpeta (solo lectura)."""
    total = 0
    for dirpath, _, archivos in os.walk(ruta):
        for archivo in archivos:
            try:
                total += os.path.getsize(os.path.join(dirpath, archivo))
            except OSError:
                pass
    return total


def _tamano_papelera() -> int:
    """Tamaño de la papelera de reciclaje (vía COM de Windows)."""
    codigo, salida = ejecutar_powershell(
        "$sh = New-Object -ComObject Shell.Application; "
        "$rb = $sh.Namespace(0xA); "
        "$sum = ($rb.Items() | Measure-Object -Property Size -Sum).Sum; "
        "if ($null -eq $sum) { 0 } else { [math]::Round($sum) }"
    )
    try:
        return int(salida.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0


# ---------------------------------------------------------------- análisis
def analisis_espacio() -> None:
    """Muestra qué ocupa el espacio del disco."""
    print("\n🔍 Análisis de espacio en C:")
    print("   Escaneando (puede tardar 1-2 minutos)...")

    uso = shutil.disk_usage("C:")
    print(f"\n💾 Disco C:  {fmt_bytes(uso.total)} total · "
          f"{fmt_bytes(uso.used)} usado · {fmt_bytes(uso.free)} libre")

    # Carpetas principales de C:\ en paralelo
    try:
        principales = [
            entrada.path for entrada in os.scandir("C:\\")
            if entrada.is_dir()
        ]
    except OSError:
        principales = []

    if principales:
        with ThreadPoolExecutor(
            max_workers=min(8, len(principales))
        ) as ejecutor:
            tamanos = list(ejecutor.map(_tamano_recursivo, principales))
        ranking = sorted(
            zip(principales, tamanos), key=lambda par: -par[1]
        )[:10]
        print("\n📊 Carpetas que más ocupan:")
        for ruta, tamano in ranking:
            print(f"  {fmt_bytes(tamano):>10}  {ruta}")

    # Rutas limpiables conocidas
    print("\n🧹 Espacio recuperable conocido:")
    total_recuperable = 0
    for etiqueta, ruta in RUTAS_LIMPIABLES:
        if os.path.isdir(ruta):
            tamano = _tamano_recursivo(ruta)
            total_recuperable += tamano
            print(f"  {fmt_bytes(tamano):>10}  {etiqueta}")
    papelera = _tamano_papelera()
    total_recuperable += papelera
    print(f"  {fmt_bytes(papelera):>10}  🗑️  Papelera de reciclaje")
    print(f"\n✅ Total recuperable estimado: {fmt_bytes(total_recuperable)}")

    # Archivos del sistema (informativo)
    print("\n🖥️  Archivos del sistema (gestionados por Windows):")
    for nombre in ARCHIVOS_SISTEMA:
        ruta = os.path.join("C:\\", nombre)
        if os.path.exists(ruta):
            print(f"  {fmt_bytes(os.path.getsize(ruta)):>10}  {nombre}")


# ---------------------------------------------------------------- dry-run
def vista_previa(logger) -> None:
    """Muestra qué haría el optimizador SIN cambiar nada."""
    print("\n" + "═" * 44)
    print("  🔍 MODO ANÁLISIS — DRY-RUN")
    print("═" * 44)
    print("  ⚠️  No se cambiará nada del sistema.")

    # --- Limpieza ---
    print("\n🧹 LIMPIEZA — esto se limpiaría:")
    total = 0
    for plantilla in RUTAS_TEMPORALES:
        ruta = os.path.expandvars(plantilla)
        if os.path.isdir(ruta):
            tamano = _tamano_recursivo(ruta)
            total += tamano
            print(f"  • {ruta}: {fmt_bytes(tamano)}")
    for ruta, etiqueta in (
        (os.path.expandvars(RUTA_PREFETCH), "Prefetch"),
        (os.path.expandvars(RUTA_CACHE_UPDATE), "Caché de Windows Update"),
    ):
        if os.path.isdir(ruta):
            tamano = _tamano_recursivo(ruta)
            total += tamano
            print(f"  • {etiqueta}: {fmt_bytes(tamano)}")
    papelera = _tamano_papelera()
    total += papelera
    print(f"  • Papelera de reciclaje: {fmt_bytes(papelera)}")
    print(f"  📦 Total estimado: {fmt_bytes(total)}")

    # --- Inicio ---
    print("\n🚀 INICIO — entradas que se deshabilitarían:")
    encontradas = 0
    for ambito, prefijo in ENTRADAS_INICIO_AUTO:
        for etiqueta, raiz, clave in CLAVES_INICIO:
            if etiqueta != ambito:
                continue
            try:
                with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                    indice = 0
                    while True:
                        try:
                            nombre, _, _ = winreg.EnumValue(k, indice)
                            indice += 1
                        except OSError:
                            break
                        if (nombre.startswith(prefijo)
                                and not nombre.startswith(
                                    PREFIJO_DESHABILITADO)):
                            print(f"  ⏸️  [{etiqueta}] {nombre}")
                            encontradas += 1
            except FileNotFoundError:
                continue
    if encontradas == 0:
        print("  • Ninguna (no hay entradas seguras que tocar)")

    # --- Rendimiento ---
    print("\n⚡ RENDIMIENTO — cambios propuestos:")
    codigo, salida = ejecutar_comando("powercfg /getactivescheme")
    plan = salida.strip().splitlines()[-1] if salida.strip() else "?"
    print(f"  🔋 Plan actual: {plan}")
    print("    → se activaría: Alto rendimiento")
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, CLAVE_EFECTOS, 0, winreg.KEY_READ
        ) as k:
            valor, _ = winreg.QueryValueEx(k, "VisualFXSetting")
        print(f"  🎨 Efectos visuales: {NOMBRES_EFECTOS.get(valor, valor)}")
    except OSError:
        print("  🎨 Efectos visuales: valor por defecto")
    print("    → se ajustaría a: Mejor rendimiento")
    estados = _estados_servicios(list(SERVICIOS_OPCIONALES))
    activos = [n for n, e in estados.items() if e == "RUNNING"]
    print(f"  🔌 Servicios opcionales activos: "
          f"{len(activos)} de {len(SERVICIOS_OPCIONALES)}")
    for nombre in activos:
        print(f"    • {nombre} → se deshabilitaría")

    # --- Mantenimiento ---
    print("\n🔧 MANTENIMIENTO — verificación:")
    print("   (solo lectura, puede tardar 1-2 minutos)")
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_sfc = ejecutor.submit(_verificar_sfc)
        futuro_dism = ejecutor.submit(_verificar_dism)
        estado_sfc = futuro_sfc.result()
        estado_dism = futuro_dism.result()
    print(f"  SFC:  {'✅ íntegro' if estado_sfc == 'ok' else '⚠️  necesitaría reparación'}")
    print(f"  DISM: {'✅ almacén sano' if estado_dism == 'ok' else '⚠️  necesitaría reparación'}")
    print("  💾 Se optimizarían las unidades (TRIM en SSD / defrag en HDD)")

    logger.info("Vista previa (dry-run) generada")


# ---------------------------------------------------------------- menú
def menu_analisis(logger) -> None:
    while True:
        print("\n" + "═" * 44)
        print("  🔍 ANÁLISIS DEL SISTEMA")
        print("═" * 44)
        print("  1) 📊 Análisis de espacio en disco")
        print("  2) 🔍 Vista previa de optimización (dry-run)")
        print("  0) ⬅️  Volver")
        print("═" * 44)

        opcion = input("Seleccione una opción: ").strip()
        if opcion == "1":
            analisis_espacio()
        elif opcion == "2":
            vista_previa(logger)
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")
        pausa()
