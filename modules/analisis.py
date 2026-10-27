"""🔍 Módulo 5: Análisis del sistema (dry-run).

Muestra qué ocupa espacio y qué haría el optimizador
SIN cambiar nada del sistema.
"""
import os
import shutil
import winreg
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    CACHE_NAVEGADORES,
    ENTRADAS_INICIO_AUTO,
    PATRON_MINIATURAS,
    RUTA_CACHE_ENTREGA,
    RUTA_CACHE_UPDATE,
    RUTA_LOGS_CBS,
    RUTA_MINIATURAS,
    RUTA_MINIDUMP,
    RUTA_PREFETCH,
    RUTAS_TEMPORALES,
    SERVICIOS_OPCIONALES,
)
from modules.maintenance import verificar_dism, verificar_sfc
from modules.performance import CLAVE_EFECTOS, estados_servicios
from modules.startup import CLAVES_INICIO, PREFIJO_DESHABILITADO
from utils import (
    ejecutar_comando,
    ejecutar_powershell,
    etapa,
    fmt_bytes,
    pausa,
)
from i18n import registrar_recarga, tr

# Rutas conocidas que ocupan espacio (algunas limpiables,
# otras solo informativas como Descargas)
def _textos_rutas_limpiables() -> list:
    return [
        (tr("Archivos temporales del usuario"),
         os.path.expandvars("%TEMP%")),
        (tr("Temporales de Windows"),
         os.path.expandvars(r"%WINDIR%\Temp")),
        (tr("Prefetch"), os.path.expandvars(RUTA_PREFETCH)),
        (tr("Caché de Windows Update"),
         os.path.expandvars(RUTA_CACHE_UPDATE)),
        (tr("Optimización de entrega (Update)"),
         os.path.expandvars(
             r"%WINDIR%\SoftwareDistribution\DeliveryOptimization")),
        (tr("Descargas del usuario (informativo)"),
         os.path.expandvars(r"%USERPROFILE%\Downloads")),
        (tr("Caché de Chrome"),
         os.path.expandvars(
             r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache")),
        (tr("Caché de Edge"),
         os.path.expandvars(
             r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache")),
        (tr("Logs CBS (SFC/DISM)"),
         os.path.expandvars(RUTA_LOGS_CBS)),
        (tr("Volcados de memoria (minidump)"),
         os.path.expandvars(RUTA_MINIDUMP)),
        (tr("Windows.old (actualización anterior)"),
         os.path.expandvars(r"%SYSTEMDRIVE%\Windows.old")),
    ]


RUTAS_LIMPIABLES = _textos_rutas_limpiables()

ARCHIVOS_SISTEMA = ("hiberfil.sys", "pagefile.sys", "swapfile.sys")


def _textos_nombres_efectos() -> dict:
    return {
        0: tr("Windows decide"),
        1: tr("Mejor apariencia"),
        2: tr("Mejor rendimiento"),
        3: tr("Personalizado"),
    }


NOMBRES_EFECTOS = _textos_nombres_efectos()


# ------------------------------------------------------------ recarga i18n
def _refrescar_textos() -> None:
    """Recalcula las descripciones con el idioma activo (mutando las tablas)."""
    RUTAS_LIMPIABLES[:] = _textos_rutas_limpiables()
    NOMBRES_EFECTOS.clear()
    NOMBRES_EFECTOS.update(_textos_nombres_efectos())


registrar_recarga(_refrescar_textos)


# GUID de los planes conocidos (estable en cualquier idioma de Windows).
_GUIDS_PLANES = {
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "SCHEME_MIN",
    "381b4222-f694-41f0-9685-ff5bb260df2e": "SCHEME_BALANCED",
    "a1841308-3541-4fab-bc81-f71556f20b2a": "SCHEME_MAX",
}


def _nombre_plan_actual(salida_powercfg: str) -> str:
    """Nombre del plan activo, traducido al idioma de la app.

    Windows devuelve el nombre en SU idioma ("Alto rendimiento"); se busca
    por GUID, que sí es estable, y se muestra el alias traducido.
    """
    import re
    m = re.search(
        r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})",
        salida_powercfg or "",
    )
    if m:
        from config import PLANES_ENERGIA
        alias = _GUIDS_PLANES.get(m.group(1).lower())
        if alias:
            return PLANES_ENERGIA[alias]
    # plan desconocido: se muestra el nombre tal cual lo da Windows
    lineas = [l.strip() for l in (salida_powercfg or "").strip().splitlines() if l.strip()]
    return lineas[-1] if lineas else "?"


# ---------------------------------------------------------------- helpers
def tamano_recursivo(ruta: str) -> int:
    """Calcula el tamaño total de una carpeta (solo lectura).

    Recorre con ``os.scandir`` de forma iterativa: una sola consulta al
    sistema por entrada (``entry.stat()``) en vez de listar y luego llamar
    a ``getsize``. Sin recursión, para no agotar la pila en árboles muy
    profundos. Los enlaces simbólicos se omiten para no contar dos veces.
    """
    total = 0
    pendientes = [ruta]
    while pendientes:
        actual = pendientes.pop()
        try:
            with os.scandir(actual) as entradas:
                for entrada in entradas:
                    try:
                        if entrada.is_dir(follow_symlinks=False):
                            pendientes.append(entrada.path)
                        elif not entrada.is_symlink():
                            total += entrada.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def _tamano_patron(carpeta: str, patron: str) -> int:
    """Tamaño de los archivos de un nivel que coinciden con ``patron``."""
    import fnmatch
    total = 0
    try:
        entradas = os.scandir(carpeta)
    except OSError:
        return 0
    for entrada in entradas:
        try:
            if entrada.is_file(follow_symlinks=False) and fnmatch.fnmatch(
                entrada.name, patron
            ):
                total += entrada.stat().st_size
        except OSError:
            pass
    return total


def tamano_papelera() -> int:
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


def tamano_cache_firefox() -> int:
    """Tamaño de la caché de Firefox (solo carpetas cache2,
    no el perfil completo: marcadores, extensiones, etc.).

    cache2 está en %LOCALAPPDATA%, no en %APPDATA%: el primero es
    para datos locales regenerables y el segundo es itinerante.
    """
    base = os.path.expandvars(r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles")
    total = 0
    if not os.path.isdir(base):
        return 0
    for perfil in os.scandir(base):
        if perfil.is_dir(follow_symlinks=False):
            cache = os.path.join(perfil.path, "cache2")
            if os.path.isdir(cache):
                total += tamano_recursivo(cache)
    return total


def exportar_informe(archivo: str = "informe_optimizacion.txt") -> str:
    """Genera un archivo de texto con el análisis de espacio.

    Devuelve la ruta del archivo creado. El informe es estático
    (una instantánea del momento). Solo lectura.
    """
    from datetime import datetime

    lineas_informe = []
    lineas_informe.append("═" * 60)
    lineas_informe.append(
        tr("  Informe de Optimización — Optimizador Windows"))
    lineas_informe.append(tr("  Fecha: {fecha}").format(
        fecha=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    lineas_informe.append("═" * 60)

    uso = shutil.disk_usage("C:")
    lineas_informe.append("")
    lineas_informe.append(tr("💾 Disco C::"))
    lineas_informe.append(tr("   Usado: {usado} / {total}").format(
        usado=fmt_bytes(uso.used), total=fmt_bytes(uso.total)))
    lineas_informe.append(tr("   Libre: {libre}").format(
        libre=fmt_bytes(uso.free)))
    lineas_informe.append("")

    lineas_informe.append(tr("📊 Carpetas que más ocupan en C::"))
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
            tamanos = dict(zip(
                principales, ejecutor.map(tamano_recursivo, principales),
                strict=True,
            ))
        ranking = sorted(tamanos.items(), key=lambda par: -par[1])[:10]
        for ruta, tamano in ranking:
            lineas_informe.append(f"   {fmt_bytes(tamano):>10}  {ruta}")

    lineas_informe.append("")
    lineas_informe.append(tr("🧹 Espacio recuperable conocido:"))
    total_recuperable = 0
    for etiqueta, ruta in RUTAS_LIMPIABLES:
        if os.path.isdir(ruta):
            tamano = tamano_recursivo(ruta)
            total_recuperable += tamano
            lineas_informe.append(f"   {fmt_bytes(tamano):>10}  {etiqueta}")
    papelera = tamano_papelera()
    total_recuperable += papelera
    lineas_informe.append(
        tr("   {tamano:>10}  🗑️  Papelera de reciclaje").format(
            tamano=fmt_bytes(papelera)))
    firefox = tamano_cache_firefox()
    if firefox > 0:
        total_recuperable += firefox
        lineas_informe.append(
            tr("   {tamano:>10}  Caché de Firefox (cache2)").format(
                tamano=fmt_bytes(firefox)))
    miniaturas = _tamano_patron(
        os.path.expandvars(RUTA_MINIATURAS), PATRON_MINIATURAS
    )
    if miniaturas > 0:
        total_recuperable += miniaturas
        lineas_informe.append(
            tr("   {tamano:>10}  Miniaturas del Explorador").format(
                tamano=fmt_bytes(miniaturas)))

    lineas_informe.append("")
    lineas_informe.append(tr("📦 Total recuperable estimado: {total}").format(
        total=fmt_bytes(total_recuperable)))
    lineas_informe.append("")
    lineas_informe.append("═" * 60)
    lineas_informe.append(tr("  Generado por Optimizador Windows"))
    lineas_informe.append("  https://github.com/SaeHTs/Optimizacion-de-windows")
    lineas_informe.append("═" * 60)

    ruta_completa = os.path.abspath(archivo)
    with open(ruta_completa, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_informe))
    return ruta_completa


# ---------------------------------------------------------------- análisis
def analisis_espacio() -> None:
    """Muestra qué ocupa el espacio del disco."""
    print(tr("\n🔍 Análisis de espacio en C:"))
    print(tr("   Escaneando (puede tardar 1-2 minutos)..."))

    uso = shutil.disk_usage("C:")
    print(tr("\n💾 Disco C:  {total} total · {usado} usado · {libre} libre").format(
        total=fmt_bytes(uso.total), usado=fmt_bytes(uso.used),
        libre=fmt_bytes(uso.free)))

    # Carpetas principales de C:\ en paralelo
    try:
        principales = [
            entrada.path for entrada in os.scandir("C:\\")
            if entrada.is_dir()
        ]
    except OSError:
        principales = []

    if principales:
        # Escaneo en paralelo con progreso incremental real:
        # cada carpeta completada avanza la barra.
        resultados: dict[str, int] = {}
        with ThreadPoolExecutor(
            max_workers=min(8, len(principales))
        ) as ejecutor:
            futuros = {
                ejecutor.submit(tamano_recursivo, ruta): ruta
                for ruta in principales
            }
            total = len(futuros)
            for indice, futuro in enumerate(as_completed(futuros), start=1):
                resultados[futuros[futuro]] = futuro.result()
                etapa(indice, total,
                      tr("Escaneando {ruta}").format(ruta=futuros[futuro]))
        ranking = sorted(
            resultados.items(), key=lambda par: -par[1]
        )[:10]
        print(tr("\n📊 Carpetas que más ocupan:"))
        for ruta, tamano in ranking:
            print(f"  {fmt_bytes(tamano):>10}  {ruta}")

    # Rutas limpiables conocidas
    print(tr("\n🧹 Espacio recuperable conocido:"))
    total_recuperable = 0
    for etiqueta, ruta in RUTAS_LIMPIABLES:
        if os.path.isdir(ruta):
            tamano = tamano_recursivo(ruta)
            total_recuperable += tamano
            print(f"  {fmt_bytes(tamano):>10}  {etiqueta}")
    papelera = tamano_papelera()
    total_recuperable += papelera
    print(tr("  {tamano:>10}  🗑️  Papelera de reciclaje").format(
        tamano=fmt_bytes(papelera)))
    firefox = tamano_cache_firefox()
    if firefox > 0:
        total_recuperable += firefox
        print(tr("  {tamano:>10}  Caché de Firefox (cache2)").format(
            tamano=fmt_bytes(firefox)))
    miniaturas = _tamano_patron(
        os.path.expandvars(RUTA_MINIATURAS), PATRON_MINIATURAS
    )
    if miniaturas > 0:
        total_recuperable += miniaturas
        print(tr("  {tamano:>10}  Miniaturas del Explorador").format(
            tamano=fmt_bytes(miniaturas)))
    print(tr("\n✅ Total recuperable estimado: {total}").format(
        total=fmt_bytes(total_recuperable)))

    # Archivos del sistema (informativo)
    print(tr("\n🖥️  Archivos del sistema (gestionados por Windows):"))
    for nombre in ARCHIVOS_SISTEMA:
        ruta = os.path.join("C:\\", nombre)
        if os.path.exists(ruta):
            print(f"  {fmt_bytes(os.path.getsize(ruta)):>10}  {nombre}")


# ---------------------------------------------------------------- dry-run
def vista_previa(logger) -> None:
    """Muestra qué haría el optimizador SIN cambiar nada."""
    print("\n" + "═" * 50)
    print(tr("  🔍 MODO DRY-RUN — VISTA PREVIA DE OPTIMIZACIÓN"))
    print("═" * 50)
    print(tr("  ⚠️  No se cambiará nada del sistema.\n"))
    # Barra global: 4 etapas principales (limpia, inicio, rendimiento, mantenimiento)
    etapa(1, 4, tr("Limpieza (cálculo de espacio)"))

    # --- Limpieza ---
    print(tr("🧹 LIMPIEZA — Espacio que se liberaría:"))
    total = 0
    for plantilla in RUTAS_TEMPORALES:
        ruta = os.path.expandvars(plantilla)
        if os.path.isdir(ruta):
            nombre = os.path.basename(ruta) or ruta
            tamano = tamano_recursivo(ruta)
            total += tamano
            print(f"   • {nombre}: {fmt_bytes(tamano)}")
    for ruta, etiqueta in (
        (os.path.expandvars(RUTA_PREFETCH), tr("Prefetch")),
        (os.path.expandvars(RUTA_CACHE_UPDATE), tr("Caché de Windows Update")),
        (os.path.expandvars(RUTA_CACHE_ENTREGA), tr("Optimización de entrega")),
    ):
        if os.path.isdir(ruta):
            tamano = tamano_recursivo(ruta)
            total += tamano
            print(f"   • {etiqueta}: {fmt_bytes(tamano)}")
    papelera = tamano_papelera()
    total += papelera
    print(tr("   • Papelera de reciclaje: {tamano}").format(
        tamano=fmt_bytes(papelera)))

    # Nuevas limpiezas de la 1.6.0
    for plantilla in CACHE_NAVEGADORES:
        ruta = os.path.expandvars(plantilla)
        if os.path.isdir(ruta):
            tamano = tamano_recursivo(ruta)
            total += tamano
            print(tr("   • Caché de navegador: {tamano}").format(
                tamano=fmt_bytes(tamano)))
    firefox = tamano_cache_firefox()
    if firefox > 0:
        total += firefox
        print(tr("   • Caché de Firefox: {tamano}").format(
            tamano=fmt_bytes(firefox)))
    miniaturas = _tamano_patron(
        os.path.expandvars(RUTA_MINIATURAS), PATRON_MINIATURAS
    )
    if miniaturas > 0:
        total += miniaturas
        print(tr("   • Miniaturas: {tamano}").format(
            tamano=fmt_bytes(miniaturas)))
    print(tr("\n   📦 Total recuperable estimado: {total}\n").format(
        total=fmt_bytes(total)))

    etapa(2, 4, tr("Inicio (registro)"))

    # --- Inicio ---
    print(tr("🚀 INICIO — Entradas que se deshabilitarían:"))
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
                            print(f"   ⏸️  [{etiqueta}] {nombre}")
                            encontradas += 1
            except FileNotFoundError:
                continue
    if encontradas == 0:
        print(tr("   • Ninguna (no hay entradas seguras que tocar)"))

    etapa(3, 4, tr("Rendimiento (energía, visuales, servicios)"))

    # --- Rendimiento ---
    print(tr("\n⚡ RENDIMIENTO — Cambios propuestos:"))
    codigo, salida = ejecutar_comando("powercfg /getactivescheme")
    print(tr("   🔋 Plan actual: {plan}").format(plan=_nombre_plan_actual(salida)))
    print(tr("      → se activaría: Alto rendimiento"))
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, CLAVE_EFECTOS, 0, winreg.KEY_READ
        ) as k:
            valor, _ = winreg.QueryValueEx(k, "VisualFXSetting")
        print(tr("   🎨 Efectos visuales: {efecto}").format(
            efecto=NOMBRES_EFECTOS.get(valor, valor)))
    except OSError:
        print(tr("   🎨 Efectos visuales: valor por defecto"))
    print(tr("      → se ajustaría a: Mejor rendimiento"))
    estados = estados_servicios(list(SERVICIOS_OPCIONALES))
    activos = [n for n, e in estados.items() if e == "RUNNING"]
    print(tr("   🔌 Servicios opcionales activos: {activos} de {total}").format(
        activos=len(activos), total=len(SERVICIOS_OPCIONALES)))
    for nombre in activos:
        print(tr("      • {nombre} → se deshabilitaría").format(nombre=nombre))

    etapa(4, 4, tr("Mantenimiento (SFC + DISM)"))

    # --- Mantenimiento ---
    print(tr("\n🔧 MANTENIMIENTO — Verificación de integridad:"))
    print(tr("   (Solo lectura, puede tardar 1-2 minutos)"))
    print(tr("   ⏳ Verificando SFC y DISM en paralelo..."))
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_sfc = ejecutor.submit(verificar_sfc, silencioso=True)
        futuro_dism = ejecutor.submit(verificar_dism, silencioso=True)
        estado_sfc = futuro_sfc.result()
        estado_dism = futuro_dism.result()
    print(tr("   ✅ Verificación completada."))
    print(tr("   • SFC:  {estado}").format(
        estado=tr("✅ íntegro") if estado_sfc == "ok"
        else tr("⚠️  necesita reparación")))
    print(tr("   • DISM: {estado}").format(
        estado=tr("✅ almacén sano") if estado_dism == "ok"
        else tr("⚠️  necesita reparación")))
    print(tr("   💾 Se optimizarían las unidades (TRIM en SSD / defrag en HDD)"))

    print("\n" + "═" * 50)
    print(tr("  ✅ VISTA PREVIA COMPLETADA"))
    print("═" * 50)
    logger.info(tr("Vista previa (dry-run) generada"))


# ---------------------------------------------------------------- menú
def menu_analisis(logger) -> None:
    from ui import Color, separador, titulo_menu
    while True:
        titulo_menu(tr("🔍 ANÁLISIS DEL SISTEMA"), Color.AZUL)

        separador(tr("Sin cambios (solo lectura)"))
        print(tr("  1) 📊 Análisis de espacio en disco (con barras)"))
        print(tr("  2) 🔍 Vista previa de optimización (dry-run) (con barras)"))
        print(tr("  3) 📋 Exportar análisis a informe .txt"))
        print(tr("  0) ⬅️  Volver"))
        print("═" * 44)

        opcion = input(tr("Seleccione una opción: ")).strip()
        if opcion == "1":
            analisis_espacio()
        elif opcion == "2":
            vista_previa(logger)
        elif opcion == "3":
            print(tr("\n📋 Generando informe..."))
            ruta = exportar_informe()
            print(tr("✅ Informe guardado en: {ruta}").format(ruta=ruta))
            print(tr("   (Ábrelo con el Bloc de notas o editor de texto)"))
        elif opcion == "0":
            break
        else:
            print(tr("❌ Opción no válida."))
        pausa()
