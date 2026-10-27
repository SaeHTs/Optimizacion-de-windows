"""🧹 Módulo 1: Limpieza de disco."""
import fnmatch
import os
from concurrent.futures import ThreadPoolExecutor

from config import (
    CACHE_NAVEGADORES,
    PATRON_MINIATURAS,
    PERFILES_FIREFOX,
    RUTA_CACHE_ENTREGA,
    RUTA_CACHE_UPDATE,
    RUTA_LOGS_CBS,
    RUTA_MINIATURAS,
    RUTA_MINIDUMP,
    RUTA_PREFETCH,
    RUTAS_TEMPORALES,
    SUBCARPETA_CACHE_FIREFOX,
)
from utils import (
    confirmar,
    ejecutar_con_barra,
    ejecutar_powershell,
    espacio_libre,
    etapa,
    fmt_bytes,
    pausa,
)
from i18n import tr


# ---------------------------------------------------------------- helpers
def _es_reparse_point(entrada: os.DirEntry) -> bool:
    """True si la entrada es un junction/link simbólico de directorio.

    En Windows, ``is_dir(follow_symlinks=False)`` devuelve True para los
    junctions: sin este chequeo el borrado descendería DENTRO del destino
    de la junction y eliminaría archivos fuera de la carpeta objetivo.
    """
    try:
        atributos = entrada.stat(follow_symlinks=False).st_file_attributes
    except (OSError, AttributeError):
        return entrada.is_symlink()
    return bool(atributos & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def _eliminar_contenido(ruta: str) -> tuple[int, int]:
    """Elimina el contenido de una carpeta en UNA sola pasada, iterativa.

    Cuenta los bytes liberados mientras borra (scandir es más
    rápido que os.walk y evita la caminata previa de pre-conteo,
    que duplicaba el tiempo en carpetas con muchos archivos).

    Iterativa (pila explícita) en lugar de recursiva: carpetas muy
    profundas no agotan la pila de llamadas de Python. Las junctions
    y enlaces simbólicos se omiten: borrar su contenido eliminaría
    archivos FUERA de la carpeta que se está limpiando.
    """
    liberado = 0
    errores = 0
    # Cada elemento de la pila es (iterador_de_entradas, ruta_carpeta)
    try:
        pila: list[tuple] = [(iter(os.scandir(ruta)), ruta)]
    except OSError:
        return 0, 0

    while pila:
        iterador, carpeta = pila[-1]
        try:
            entrada = next(iterador)
        except StopIteration:
            iterador.close()
            pila.pop()
            # Ya vacía: si no es la raíz pedida, intenta borrar la carpeta
            if carpeta != ruta:
                try:
                    os.rmdir(carpeta)
                except OSError:
                    errores += 1
            continue
        try:
            if entrada.is_dir(follow_symlinks=False):
                if _es_reparse_point(entrada):
                    # Junction/symlink a directorio: no descender (el
                    # contenido vive fuera de la carpeta que se limpia).
                    continue
                pila.append((iter(os.scandir(entrada.path)), entrada.path))
            else:
                tamano = entrada.stat().st_size
                os.remove(entrada.path)
                liberado += tamano  # solo suma si el borrado tuvo éxito
        except OSError:
            errores += 1

    return liberado, errores


def _eliminar_patron(carpeta: str, patron: str) -> tuple[int, int]:
    """Elimina solo los archivos de un nivel que coinciden con ``patron``.

    Pensado para casos como ``thumbcache_*.db`` donde no se debe
    borrar la carpeta completa, solo archivos concretos.
    Devuelve (bytes liberados, errores).
    """
    liberado = 0
    errores = 0
    try:
        entradas = list(os.scandir(carpeta))
    except OSError:
        return 0, 0
    for entrada in entradas:
        try:
            if entrada.is_file(follow_symlinks=False) and fnmatch.fnmatch(
                entrada.name, patron
            ):
                liberado += entrada.stat().st_size
                os.remove(entrada.path)
        except OSError:
            errores += 1
    return liberado, errores


def _nombre_navegador(ruta: str) -> str:
    """Nombre legible del navegador a partir de la ruta de caché."""
    texto = ruta.lower()
    if "firefox" in texto:
        return "Firefox"
    if "edge" in texto:
        return "Edge"
    if "chrome" in texto:
        return "Chrome"
    return os.path.basename(ruta)


# ---------------------------------------------------------------- operaciones
def limpiar_temporales(automatico: bool = False) -> None:
    """Elimina archivos temporales de usuario y de Windows.

    Las carpetas temporales se procesan en paralelo (más rápido en SSD).
    """
    print(tr("\n🧹 Limpiando archivos temporales..."))
    rutas = [os.path.expandvars(p) for p in RUTAS_TEMPORALES]
    rutas = [r for r in rutas if os.path.isdir(r)]
    if not rutas:
        print(tr("  No hay carpetas temporales que limpiar."))
        return

    with ThreadPoolExecutor(max_workers=len(rutas)) as ejecutor:
        resultados = list(ejecutor.map(_eliminar_contenido, rutas))

    total = 0
    for ruta, (liberado, errores) in zip(rutas, resultados, strict=True):
        total += liberado
        print(tr("  • {ruta}: {tamano} liberados").format(
            ruta=ruta, tamano=fmt_bytes(liberado))
            + (tr(" ({errores} archivos en uso)").format(errores=errores)
               if errores else ""))
    print(tr("✅ Total liberado: {tamano}").format(tamano=fmt_bytes(total)))


def limpiar_prefetch(automatico: bool = False) -> None:
    """Elimina archivos de prefetch (Windows los reconstruye automáticamente)."""
    ruta = os.path.expandvars(RUTA_PREFETCH)
    print(tr("\n🧹 Limpiando Prefetch..."))
    if not automatico and not confirmar(
        tr("Se eliminarán los archivos de precarga (se regeneran solos). "
           "¿Continuar?")
    ):
        print(tr("   Operación cancelada."))
        return
    liberado, errores = _eliminar_contenido(ruta)
    print(tr("✅ Prefetch limpiado: {tamano} liberados").format(
        tamano=fmt_bytes(liberado))
        + (tr(" ({errores} errores)").format(errores=errores)
           if errores else ""))


def vaciar_papelera(automatico: bool = False) -> None:
    """Vacía la papelera de reciclaje de todas las unidades."""
    print(tr("\n🗑️  Vaciando la papelera de reciclaje..."))
    if not automatico and not confirmar(tr("¿Vaciar la papelera de TODAS las unidades?")):
        print(tr("   Operación cancelada."))
        return
    codigo, salida = ejecutar_powershell(
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
    )
    print(tr("✅ Papelera vaciada.") if codigo == 0
          else tr("⚠️  Sin cambios: {salida}").format(salida=salida or 'ok'))


def limpiar_cache_windows_update(automatico: bool = False) -> None:
    """Detiene Windows Update y elimina su caché de descargas."""
    print(tr("\n🧹 Limpiando caché de Windows Update..."))
    if not automatico and not confirmar(
        tr("Se detendrá temporalmente el servicio Windows Update. "
           "¿Continuar?")
    ):
        print(tr("   Operación cancelada."))
        return
    print(tr("  Deteniendo servicios..."))
    ejecutar_powershell("Stop-Service wuauserv -Force; Stop-Service bits -Force")
    ruta = os.path.expandvars(RUTA_CACHE_UPDATE)
    liberado, errores = _eliminar_contenido(ruta)
    # Caché de optimización de entrega (puede ocupar GB)
    ruta_entrega = os.path.expandvars(RUTA_CACHE_ENTREGA)
    liberado_entrega, errores_entrega = _eliminar_contenido(ruta_entrega)
    liberado += liberado_entrega
    errores += errores_entrega
    print(tr("  Reiniciando servicios..."))
    ejecutar_powershell("Start-Service bits; Start-Service wuauserv")
    print(tr("✅ Caché de Windows Update limpiada: {tamano} liberados").format(
        tamano=fmt_bytes(liberado))
        + (tr(" ({errores} errores)").format(errores=errores)
           if errores else ""))


def limpiar_componentes_windows() -> None:
    """Ejecuta DISM para limpiar componentes obsoletos de Windows."""
    print(tr("\n🧹 Limpiando componentes obsoletos de Windows (DISM)..."))
    print(tr("   Puede tardar varios minutos, no cierres la ventana."))
    codigo, _ = ejecutar_con_barra(
        "dism /Online /Cleanup-Image /StartComponentCleanup",
        tiempo_espera=1800,
    )
    print(tr("✅ Limpieza de componentes finalizada.")
          if codigo == 0 else tr("⚠️  Revisar el resultado de DISM."))


def limpiar_cache_navegadores(automatico: bool = False) -> None:
    """Limpia SOLO la caché de Chrome, Edge y Firefox.

    No toca perfiles, cookies, historial ni contraseñas: la caché
    se reconstruye sola. Los archivos en uso (navegador abierto)
    se omiten automáticamente.
    """
    print(tr("\n🌐 Limpiando caché de navegadores..."))
    if not automatico and not confirmar(
        tr("Se limpiará la caché de Chrome, Edge y Firefox (nunca datos "
           "personales). Cierra los navegadores para mejor resultado. "
           "¿Continuar?")
    ):
        print(tr("   Operación cancelada."))
        return

    rutas = [os.path.expandvars(p) for p in CACHE_NAVEGADORES]

    # Firefox: recorrer perfiles dinámicos y apuntar a su subcarpeta cache2
    base_firefox = os.path.expandvars(PERFILES_FIREFOX)
    if os.path.isdir(base_firefox):
        try:
            for entrada in os.scandir(base_firefox):
                if entrada.is_dir(follow_symlinks=False):
                    rutas.append(
                        os.path.join(entrada.path, SUBCARPETA_CACHE_FIREFOX)
                    )
        except OSError:
            pass

    rutas = [r for r in rutas if os.path.isdir(r)]
    if not rutas:
        print(tr("  No se encontraron cachés de navegadores instalados."))
        return

    with ThreadPoolExecutor(max_workers=len(rutas)) as ejecutor:
        resultados = list(ejecutor.map(_eliminar_contenido, rutas))

    total = 0
    for ruta, (liberado, errores) in zip(rutas, resultados, strict=True):
        total += liberado
        print(tr("  • {navegador}: {tamano} liberados").format(
            navegador=_nombre_navegador(ruta), tamano=fmt_bytes(liberado))
            + (tr(" ({errores} archivos en uso)").format(errores=errores)
               if errores else ""))
    print(tr("✅ Caché de navegadores limpiada: {tamano} liberados").format(
        tamano=fmt_bytes(total)))


def limpiar_miniaturas(automatico: bool = False) -> None:
    """Elimina la caché de miniaturas (thumbcache) del Explorador.

    Solo borra los ``thumbcache_*.db``; Windows los recrea. Los que
    explorer.exe tenga abiertos se omiten.
    """
    print(tr("\n🖼️  Limpiando caché de miniaturas..."))
    ruta = os.path.expandvars(RUTA_MINIATURAS)
    if not os.path.isdir(ruta):
        print(tr("  No se encontró la carpeta de miniaturas."))
        return
    liberado, errores = _eliminar_patron(ruta, PATRON_MINIATURAS)
    if liberado == 0 and errores == 0:
        print(tr("  No había miniaturas que limpiar."))
        return
    print(tr("✅ Miniaturas limpiadas: {tamano} liberados").format(
        tamano=fmt_bytes(liberado))
        + (tr(" ({errores} en uso por el sistema)").format(errores=errores)
           if errores else ""))


def limpiar_logs(automatico: bool = False) -> None:
    """Borra logs antiguos de Windows (CBS) y volcados de memoria.

    El modo automático lo omite: los volcados y logs CBS son útiles
    para diagnosticar cuelgues recientes; se limpian solo a petición.
    """
    print(tr("\n📋 Limpiando logs antiguos y volcados..."))
    if not automatico and not confirmar(
        tr("Se eliminarán los registros CBS y los volcados de pantallazos "
           "azules (útiles para diagnóstico). ¿Continuar?")
    ):
        print(tr("   Operación cancelada."))
        return
    total = 0
    errores = 0
    for constante, nombre in (
        (RUTA_LOGS_CBS, tr("Logs CBS")),
        (RUTA_MINIDUMP, tr("Volcados de memoria")),
    ):
        ruta = os.path.expandvars(constante)
        if not os.path.isdir(ruta):
            continue
        liberado, fallos = _eliminar_contenido(ruta)
        total += liberado
        errores += fallos
        print(tr("  • {nombre}: {tamano} liberados").format(
            nombre=nombre, tamano=fmt_bytes(liberado)))
    print(tr("✅ Logs limpiados: {tamano} liberados").format(
        tamano=fmt_bytes(total))
        + (tr(" ({errores} errores)").format(errores=errores)
           if errores else ""))


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Ejecuta TODA la limpieza sin preguntas intermedias."""
    print("\n" + "═" * 44)
    print(tr("  ⚡ MODO AUTOMÁTICO — LIMPIEZA COMPLETA"))
    print("═" * 44)
    pasos = (
        (tr("Archivos temporales"),
         lambda: limpiar_temporales(automatico=True)),
        (tr("Prefetch"), lambda: limpiar_prefetch(automatico=True)),
        (tr("Papelera de reciclaje"),
         lambda: vaciar_papelera(automatico=True)),
        (tr("Caché de Windows Update"),
         lambda: limpiar_cache_windows_update(automatico=True)),
        (tr("Caché de navegadores"),
         lambda: limpiar_cache_navegadores(automatico=True)),
        (tr("Miniaturas del Explorador"),
         lambda: limpiar_miniaturas(automatico=True)),
        (tr("Componentes obsoletos (DISM)"), limpiar_componentes_windows),
    )
    total = len(pasos)
    for indice, (nombre, accion) in enumerate(pasos, start=1):
        accion()
        etapa(indice, total, nombre)
    # limpiar_logs NO entra en el modo automático: sus archivos
    # sirven para diagnosticar problemas recientes.
    logger.info(tr("Limpieza automática completada"))


# ---------------------------------------------------------------- menú
def menu_limpieza(logger) -> None:
    from ui import Color, separador, titulo_menu
    espacio_antes = espacio_libre("C:")
    while True:
        titulo_menu(tr("🧹 LIMPIEZA DE DISCO"), Color.VERDE)
        libre = espacio_libre("C:")
        if libre < 5 * 1024**3:
            print(tr("  🔴 ⚠️  Poco espacio libre: {libre} — ¡optimiza ya!")
                  .format(libre=fmt_bytes(libre)))
        elif libre < 15 * 1024**3:
            print(tr("  🟡 Espacio libre: {libre} — podrías liberar más")
                  .format(libre=fmt_bytes(libre)))
        else:
            print(tr("  🟢 Espacio libre: {libre}").format(libre=fmt_bytes(libre)))
        print()

        separador(tr("Caché y temporales"))
        print(tr("  1) 🗒️  Archivos temporales (usuario + Windows)"))
        print(tr("  2) ⚡ Prefetch"))
        print(tr("  3) 🗑️  Papelera de reciclaje"))
        print(tr("  4) 🔄 Caché de Windows Update"))

        separador(tr("Aplicaciones y sistema"))
        print(tr("  5) 🧩 Componentes obsoletos (DISM) (barra de progreso)"))
        print(tr("  6) 🌐 Caché de navegadores (Chrome/Edge/Firefox)"))
        print(tr("  7) 🖼️  Miniaturas del Explorador"))
        print(tr("  8) 📋 Logs antiguos y volcados"))

        separador(tr("Combinados"))
        print(tr("  9) 🧼 TODO (limpieza completa) (con barras)"))
        print(tr("  10) ⚡ MODO AUTOMÁTICO (sin preguntas) (con barras)"))
        print(tr("  0) ⬅️  Volver"))
        print("═" * 44)

        opcion = input(tr("Seleccione una opción: ")).strip()
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
            limpiar_cache_navegadores()
        elif opcion == "7":
            limpiar_miniaturas()
        elif opcion == "8":
            limpiar_logs()
        elif opcion == "9":
            if confirmar(tr("¿Ejecutar la limpieza completa?")):
                limpiar_temporales()
                limpiar_prefetch()
                vaciar_papelera()
                limpiar_cache_windows_update()
                limpiar_cache_navegadores()
                limpiar_miniaturas()
                limpiar_logs()  # con confirmación: son datos de diagnóstico
                limpiar_componentes_windows()
        elif opcion == "10":
            modo_automatico(logger)
        elif opcion == "0":
            break
        else:
            print(tr("❌ Opción no válida."))

        espacio_despues = espacio_libre("C:")
        ganado = espacio_despues - espacio_antes
        if ganado > 0:
            print(tr("\n💾 Espacio libre en C: ahora: {libre} "
                     "(+{ganado} liberados)")
                  .format(libre=fmt_bytes(espacio_despues),
                          ganado=fmt_bytes(ganado)))
        # La referencia pasa a ser el estado actual: el "+X liberados"
        # de la próxima acción mide solo lo liberado por esa acción.
        espacio_antes = espacio_despues
        logger.info(tr("Módulo de limpieza ejecutado: opción %s"), opcion)
        pausa()
