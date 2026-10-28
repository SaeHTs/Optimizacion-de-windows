"""⚡ Módulo 3: Rendimiento general."""
import re
import winreg
from concurrent.futures import ThreadPoolExecutor

from config import (
    AJUSTES_GAMING,
    AJUSTES_PRIVACIDAD,
    PLANES_ENERGIA,
    POLITICAS_TELEMETRIA,
    SERVICIOS_AVANZADOS,
    SERVICIOS_CONDICIONALES,
    SERVICIOS_OPCIONALES,
    TAREAS_TELEMETRIA,
)
from utils import (
    confirmar,
    ejecutar_comando,
    ejecutar_powershell,
    es_laptop,
    pausa,
    proteger_cambios,
    tipo_unidad,
)
from i18n import tr

CLAVE_EFECTOS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"


# ---------------------------------------------------------------- energía
def listar_planes() -> None:
    """Muestra los planes de energía disponibles y el activo."""
    codigo, salida = ejecutar_comando("powercfg /list")
    print(tr("\n⚡ Planes de energía:"))
    print(salida if codigo == 0 else tr("⚠️  No se pudieron listar los planes."))


def activar_plan() -> None:
    """Activa un plan de energía predefinido."""
    listar_planes()
    print(tr("\n  1) Alto rendimiento"))
    print(tr("  2) Equilibrado (recomendado)"))
    print(tr("  3) Ahorro de energía"))
    opcion = input(tr("Seleccione un plan: ")).strip()
    alias = {"1": "SCHEME_MIN", "2": "SCHEME_BALANCED",
             "3": "SCHEME_MAX"}.get(opcion)
    if not alias:
        print(tr("❌ Opción no válida."))
        return
    if confirmar(tr("¿Activar el plan '{plan}'?").format(plan=PLANES_ENERGIA[alias])):
        codigo, salida = ejecutar_comando(f"powercfg /setactive {alias}")
        print(tr("✅ Plan '{plan}' activado.").format(plan=PLANES_ENERGIA[alias])
              if codigo == 0
              else tr("⚠️  No se pudo cambiar: {salida}").format(salida=salida))


# ---------------------------------------------------------------- visuales
def efectos_visuales(mejor_rendimiento: bool = True) -> None:
    """Ajusta los efectos visuales (2 = mejor rendimiento, 0 = Windows decide)."""
    valor = 2 if mejor_rendimiento else 0
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, CLAVE_EFECTOS, 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, valor)
        if mejor_rendimiento:
            print(tr("✅ Efectos visuales ajustados (priorizando rendimiento)."))
        else:
            print(tr("✅ Efectos visuales en modo automático."))
        print(tr("   Puede requerir cerrar sesión para aplicarse por completo."))
    except OSError as e:
        print(tr("❌ Error: {e}").format(e=e))


# ---------------------------------------------------------------- servicios
def _estado_servicio(nombre: str) -> str:
    """Devuelve el estado actual de un servicio (RUNNING/STOPPED/etc.)."""
    codigo, salida = ejecutar_comando(f'sc query "{nombre}"')
    if codigo != 0:
        return "?"
    for linea in salida.splitlines():
        # sc.exe localiza la etiqueta: "STATE" (EN) / "ESTADO" (ES);
        # los valores (RUNNING, STOPPED...) no se traducen.
        m = re.search(r"(?:STATE|ESTADO)\s*:\s*\d+\s+(\w+)", linea)
        if m:
            return m.group(1)
    return "?"


def estados_servicios(nombres: list[str]) -> dict[str, str]:
    """Consulta el estado de varios servicios en paralelo."""
    if not nombres:
        return {}
    with ThreadPoolExecutor(max_workers=min(len(nombres), 8)) as ejecutor:
        resultados = ejecutor.map(_estado_servicio, nombres)
    return dict(zip(nombres, resultados, strict=True))


def gestionar_servicios(deshabilitar: bool = True,
                        automatico: bool = False) -> None:
    """Deshabilita o restaura los servicios opcionales de la lista.

    Al deshabilitar, registra el estado previo en ``logs/rollback.json``
    para que "Deshacer cambios" también restaure esta vía (menú 4/6
    y modo automático completo).
    """
    from modules import rollback

    nombres = list(SERVICIOS_OPCIONALES)
    accion = tr("Deshabilitar") if deshabilitar else tr("Restaurar (manual)")
    print(tr("\n🔧 {accion} servicios opcionales:").format(accion=accion))
    estados = estados_servicios(nombres)
    for nombre, descripcion in SERVICIOS_OPCIONALES.items():
        print(f"  • {nombre:<18} {descripcion:<45} [{estados.get(nombre, '?')}]")

    if not automatico and not confirmar(
            tr("¿{accion} los servicios seleccionados?").format(accion=accion)):
        print(tr("   Operación cancelada."))
        return

    # Estado previo de TODOS los servicios ANTES de tocar nada
    # (secuencial para que rollback quede consistente).
    if deshabilitar:
        for nombre in SERVICIOS_OPCIONALES:
            previo = _ps_inicio_servicio(nombre)
            if previo and previo.lower() != "disabled":
                rollback.registrar_servicio(nombre, previo)

    def _aplicar_un_servicio(nombre: str) -> tuple[str, int, str]:
        """Detiene y deshabilita un servicio. Devuelve (nombre, codigo, salida)."""
        ejecutar_comando(f'sc stop "{nombre}"', tiempo_espera=30)
        return ejecutar_comando(f'sc config "{nombre}" start= disabled',
                                tiempo_espera=30)

    def _restaurar_un_servicio(nombre: str) -> tuple[str, int, str]:
        """Vuelve un servicio a inicio manual."""
        return ejecutar_comando(f'sc config "{nombre}" start= demand',
                                tiempo_espera=30)

    # Aplicar cambios en paralelo (sc stop / sc config son independientes
    # entre servicios y es la parte lenta de la operación).
    aplicador = _aplicar_un_servicio if deshabilitar else _restaurar_un_servicio
    with ThreadPoolExecutor(max_workers=min(len(SERVICIOS_OPCIONALES), 8)) as executor:
        for nombre, (codigo, salida) in zip(
                SERVICIOS_OPCIONALES,
                executor.map(aplicador, SERVICIOS_OPCIONALES)):
            print(f"    {'✅' if codigo == 0 else '⚠️ '} {nombre}: "
                  f"{salida.strip().splitlines()[-1] if salida.strip() else 'ok'}")


# ---------------------------------------------------------------- avanzado (PowerShell, sin depender del idioma)
def _ps_inicio_servicio(nombre: str) -> str:
    """StartupType actual (Automatic/Manual/Disabled; "" si no existe)."""
    codigo, salida = ejecutar_powershell(
        f"(Get-Service -Name '{nombre}' -ErrorAction SilentlyContinue).StartType"
    )
    return salida.strip() if codigo == 0 else ""


def _ps_deshabilitar_servicio(nombre: str) -> bool:
    codigo, _ = ejecutar_powershell(
        f"Stop-Service -Name '{nombre}' -Force -ErrorAction SilentlyContinue; "
        f"Set-Service -Name '{nombre}' -StartupType Disabled -ErrorAction Stop"
    )
    return codigo == 0


def _hay_impresora() -> bool:
    codigo, salida = ejecutar_powershell(
        "(Get-Printer -ErrorAction SilentlyContinue | Measure-Object).Count"
    )
    try:
        return codigo == 0 and int(salida.strip()) > 0
    except ValueError:
        return True  # ante la duda, no ofrecer quitar la impresión


def _rdp_desactivado() -> bool:
    codigo, salida = ejecutar_powershell(
        "(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server'"
        " -Name fDenyTSConnections -ErrorAction SilentlyContinue).fDenyTSConnections"
    )
    return codigo == 0 and salida.strip() == "1"


def _condicion_cumple(detector: str) -> bool:
    if detector == "sin_impresora":
        return not _hay_impresora()
    if detector == "solo_ssd":
        return tipo_unidad("C:") == "SSD"
    if detector == "rdp_apagado":
        return _rdp_desactivado()
    return True  # siempre_avisar


def _catalogo_avanzado() -> list:
    """Servicios elegibles: seguros + condicionales que aplican a ESTE PC."""
    catalogo = [(n, d, None) for n, d in SERVICIOS_OPCIONALES.items()]
    catalogo += [(n, d, None) for n, d in SERVICIOS_AVANZADOS.items()]
    for nombre, (descripcion, detector, aviso) in SERVICIOS_CONDICIONALES.items():
        if _condicion_cumple(detector):
            catalogo.append((nombre, descripcion, aviso))
    return catalogo


def _aplicar_deshabilitado(nombre: str) -> bool:
    """Deshabilita un servicio registrando antes su estado previo."""
    from modules import rollback
    previo = _ps_inicio_servicio(nombre)
    if not previo:
        print(tr("    ⚠️  {nombre}: no existe en este equipo").format(nombre=nombre))
        return False
    if previo.lower() == "disabled":
        print(tr("    ⏭️  {nombre}: ya estaba deshabilitado").format(nombre=nombre))
        return False
    rollback.registrar_servicio(nombre, previo)
    if _ps_deshabilitar_servicio(nombre):
        print(tr("    ✅ {nombre}: deshabilitado (reversible)").format(nombre=nombre))
        return True
    print(tr("    ⚠️  {nombre}: no se pudo deshabilitar").format(nombre=nombre))
    return False


def elegir_servicios_avanzado() -> None:
    """Lista los servicios elegibles y deja elegir cuáles deshabilitar."""
    catalogo = _catalogo_avanzado()
    print(tr("\n🧩 Servicios que puedes deshabilitar en ESTE equipo:"))
    for i, (nombre, descripcion, aviso) in enumerate(catalogo, start=1):
        extra = f" — {aviso}" if aviso else ""
        print(f"  {i}) {nombre:<18} {descripcion}{extra}")
    print(tr("  t) Todos   ·   0) Volver"))
    respuesta = input(
        tr("Elige números separados por coma (ej. 1,4): ")).strip().lower()
    if respuesta in ("", "0"):
        return
    if respuesta == "t":
        elegidos = catalogo
    else:
        try:
            elegidos = [catalogo[int(x) - 1]
                        for x in respuesta.split(",") if x.strip()]
        except (ValueError, IndexError):
            print(tr("❌ Selección no válida."))
            return
    if not elegidos:
        return
    print(tr("\nSe deshabilitarán {n} servicio(s) "
             "(reversible con la opción Deshacer).").format(n=len(elegidos)))
    if not confirmar(tr("¿Continuar?")):
        print(tr("   Operación cancelada."))
        return
    proteger_cambios()
    hechos = sum(1 for nombre, _, _ in elegidos if _aplicar_deshabilitado(nombre))
    print(tr("\n✅ {hechos} servicio(s) deshabilitados.").format(hechos=hechos))


def deshabilitar_tareas_telemetria(automatico: bool = False) -> None:
    """Desactiva las tareas programadas de telemetría/CEIP.

    Solo apunta en el rollback las tareas que se desactivaron de
    verdad: si una no existe, no queda basura en el registro.
    ``-ErrorAction Stop`` hace que el código de salida sea real
    (antes un error silenciado contaba como "✅ desactivada").
    """
    from modules import rollback
    print(tr("\n📡 Tareas de telemetría programadas:"))
    if not automatico and not confirmar(
        tr("¿Desactivar las tareas programadas de telemetría? (reversible)")
    ):
        print(tr("   Operación cancelada."))
        return
    hechas = 0
    for ruta, nombre in TAREAS_TELEMETRIA:
        # Si ya estaba desactivada, no se toca: registrarla haría que
        # 'Deshacer' la encendiera sin que la app la hubiera apagado.
        codigo, estado = ejecutar_powershell(
            f"(Get-ScheduledTask -TaskName '{nombre}' -TaskPath '{ruta}\\' "
            "-ErrorAction Stop).State"
        )
        if codigo == 0 and estado.strip().lower() == "disabled":
            print(tr("    ⏭️  {nombre}: ya estaba desactivada").format(nombre=nombre))
            continue
        codigo, _ = ejecutar_powershell(
            f"Disable-ScheduledTask -TaskName '{nombre}' -TaskPath '{ruta}\\' "
            "-ErrorAction Stop"
        )
        if codigo == 0:
            rollback.registrar_tarea(ruta, nombre)
            print(tr("    ✅ {nombre}: desactivada (reversible)").format(nombre=nombre))
            hechas += 1
        else:
            print(tr("    ⏭️  {nombre}: no encontrada o no se pudo desactivar")
                  .format(nombre=nombre))
    print(tr("✅ {hechas} tarea(s) de telemetría desactivadas.").format(hechas=hechas))


def aplicar_telemetria(automatico: bool = False) -> None:
    """Telemetría completa: tareas programadas + políticas de privacidad.

    Son dos mitades independientes: si una falla, la otra se intenta igual.
    Todo queda registrado para 'Deshacer cambios'.
    """
    print(tr("\n📡 Telemetría: tareas programadas y políticas"))
    print(tr("   Tareas a desactivar: {n}").format(n=len(TAREAS_TELEMETRIA)))
    print(tr("   Políticas a aplicar: {n}").format(n=len(POLITICAS_TELEMETRIA)))
    print(tr("   Todo reversible con 'Deshacer cambios'."))
    if not automatico and not confirmar(tr("¿Continuar?")):
        print(tr("   Operación cancelada."))
        return
    try:
        deshabilitar_tareas_telemetria(automatico=True)
    except Exception as e:  # una mitad no debe bloquear a la otra
        print(tr("    ⚠️  Tareas de telemetría: {e}").format(e=e))
    aplicados = _aplicar_ajustes_registro(POLITICAS_TELEMETRIA)
    print(tr("\n✅ {n} política(s) de privacidad aplicadas.").format(n=aplicados))


def _aplicar_ajustes_registro(ajustes) -> int:
    from modules import rollback
    raices = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    aplicados = 0
    for descripcion, raiz, subclave, valor, dato in ajustes:
        try:
            with winreg.CreateKey(raices[raiz], subclave) as k:
                try:
                    previo, _ = winreg.QueryValueEx(k, valor)
                except OSError:
                    previo = None
                rollback.registrar_registro(raiz, subclave, valor, previo)
                winreg.SetValueEx(k, valor, 0, winreg.REG_DWORD, dato)
            print(f"    ✅ {descripcion}")
            aplicados += 1
        except OSError as e:
            print(f"    ⚠️  {descripcion}: {e}")
    return aplicados


def nombre_perfil(clave: str) -> str:
    """Nombre visible de un perfil, traducido al idioma activo.

    La clave interna ("equilibrado", "privacidad") nunca debe salir en
    pantalla: se traduce aqui, en el momento de mostrarla.
    """
    return {
        "equilibrado": tr("Equilibrado"),
        "gaming": tr("Gaming"),
        "privacidad": tr("Privacidad"),
    }.get(clave, clave)


def aplicar_perfil(nombre: str, automatico: bool = False) -> None:
    """Aplica un perfil de optimización (todo reversible).

    ``automatico=True`` salta las preguntas de consola (lo usa la GUI,
    que ya confirmó con sus propios diálogos).
    """
    base = [
        "DiagTrack", "dmwappushservice", "RetailDemo", "RemoteRegistry",
        "WMPNetworkSvc", "Fax", "wisvc", "MapsBroker", "WalletService",
    ]
    perfiles = {
        "equilibrado": (base, [], False),
        "gaming": (base + ["XblAuthManager", "XblGameSave", "XboxNetApiSvc",
                           "XboxGipSvc"], AJUSTES_GAMING, True),
        "privacidad": (base, AJUSTES_PRIVACIDAD, False),
    }
    if nombre not in perfiles:
        print(tr("❌ Perfil desconocido."))
        return
    servicios, ajustes, ofrecer_sysmain = perfiles[nombre]
    if nombre == "gaming" and _condicion_cumple("solo_ssd"):
        servicios = servicios + ["SysMain"]

    print(tr("\n🎯 Perfil '{nombre}':").format(nombre=nombre_perfil(nombre)))
    print(tr("   Servicios a deshabilitar: {n}").format(n=len(servicios)))
    print(tr("   Tareas de telemetría: sí"))
    if ajustes:
        print(tr("   Ajustes de registro: {n}").format(n=len(ajustes)))
    print(tr("   Todo reversible con la opción 'Deshacer cambios'."))
    if not automatico and not confirmar(tr("¿Aplicar este perfil?")):
        print(tr("   Operación cancelada."))
        return
    if not automatico:
        proteger_cambios()

    hechos = sum(1 for s in servicios if _aplicar_deshabilitado(s))
    deshabilitar_tareas_telemetria(automatico=True)
    if ajustes:
        _aplicar_ajustes_registro(ajustes)
    print(tr("\n✅ Perfil '{nombre}' aplicado ({hechos} servicios).")
          .format(nombre=nombre_perfil(nombre), hechos=hechos))
    print(tr("   Reinicia el equipo para aplicar todos los cambios."))


def menu_perfiles() -> None:
    """Elige un perfil predefinido de optimización."""
    print(tr("\n🎯 PERFILES DE OPTIMIZACIÓN (todo reversible):"))
    print(tr("  1) ⚖️  Equilibrado — telemetría y servicios obsoletos"))
    print(tr("  2) 🎮 Gaming — equilibrado + Xbox + Game DVR + Superfetch si es SSD"))
    print(tr("  3) 🕵️  Privacidad — equilibrado + publicidad/historial/Widgets/Copilot"))
    print(tr("  0) ⬅️  Volver"))
    opcion = input(tr("Elige un perfil: ")).strip()
    if opcion == "1":
        aplicar_perfil("equilibrado")
    elif opcion == "2":
        aplicar_perfil("gaming")
    elif opcion == "3":
        aplicar_perfil("privacidad")


def modo_perfil_equilibrado(logger) -> None:
    """Aplica el perfil equilibrado sin preguntas (compatibilidad GUI)."""
    modo_perfil_auto("equilibrado", logger)


def modo_perfil_auto(nombre: str, logger) -> None:
    """Aplica un perfil sin preguntas de consola (lo llama la GUI)."""
    print(tr("\n🎯 Perfil {nombre} (automático desde GUI)")
          .format(nombre=nombre_perfil(nombre).upper()))
    aplicar_perfil(nombre, automatico=True)
    logger.info(tr("Perfil %s aplicado (GUI)"), nombre_perfil(nombre))


def deshacer_cambios(automatico: bool = False) -> None:
    """Restaura todos los cambios registrados por los perfiles/selector.

    ``automatico=True`` salta la pregunta de consola (la GUI ya confirmó).
    """
    from modules import rollback
    print(tr("\n⏪ DESHACER CAMBIOS"))
    if not rollback.hay_cambios():
        print(tr("  No hay cambios registrados que deshacer."))
        return
    print(tr("  Se restaurarán servicios, tareas y valores de registro."))
    if not automatico and not confirmar(tr("¿Deshacer todos los cambios registrados?")):
        print(tr("   Operación cancelada."))
        return
    ok, errores = rollback.deshacer()
    print(tr("\n✅ Restaurados {ok} cambio(s)").format(ok=ok)
          + (tr(" ({errores} con error)").format(errores=errores) if errores else ""))


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Optimiza el rendimiento: energía, visuales y servicios.

    En laptops se usa el plan "Equilibrado" (ahorra batería);
    en desktop se usa "Alto rendimiento".
    """
    print("\n" + "═" * 44)
    print(tr("  ⚡ MODO AUTOMÁTICO — RENDIMIENTO"))
    print("═" * 44)
    if es_laptop():
        alias = "SCHEME_BALANCED"
        print(tr("  💻 Laptop detectada → plan Equilibrado (ahorra batería)."))
    else:
        alias = "SCHEME_MIN"
        print(tr("  🖥️  Desktop detectado → plan Alto rendimiento."))
    codigo, _ = ejecutar_comando(f"powercfg /setactive {alias}")
    print(tr("    {estado} Plan '{plan}'").format(
        estado="✅" if codigo == 0 else "⚠️ ", plan=PLANES_ENERGIA[alias]))
    efectos_visuales(mejor_rendimiento=True)
    gestionar_servicios(deshabilitar=True, automatico=True)
    logger.info(tr("Optimización automática de rendimiento completada"))


# ---------------------------------------------------------------- menú
def menu_rendimiento(logger) -> None:
    from ui import Color, separador, titulo_menu
    while True:
        titulo_menu(tr("⚡ RENDIMIENTO GENERAL"), Color.AMARILLO)

        separador(tr("Energía y visuales"))
        print(tr("  1) 🔋 Planes de energía"))
        print(tr("  2) 🎨 Efectos visuales (priorizar rendimiento)"))
        print(tr("  3) 🎨 Restaurar efectos visuales (automático)"))

        separador(tr("Servicios"))
        print(tr("  4) 🔌 Deshabilitar servicios opcionales"))
        print(tr("  5) 🔌 Restaurar servicios opcionales"))

        separador(tr("Combinado"))
        print(tr("  6) ⚡ MODO AUTOMÁTICO (energía + visuales + servicios)"))

        separador(tr("Servicios y procesos (reversible)"))
        print(tr("  7) 🧩 Elegir servicios a deshabilitar (detecta este PC)"))
        print(tr("  8) 📡 Desactivar telemetría (tareas y políticas)"))
        print(tr("  9) 🎯 Perfiles (Equilibrado / Gaming / Privacidad)"))
        print(tr("  10) ⏪ Deshacer cambios de optimización"))
        print(tr("  0) ⬅️  Volver"))
        print("═" * 44)

        opcion = input(tr("Seleccione una opción: ")).strip()
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
        elif opcion == "6":
            proteger_cambios()
            modo_automatico(logger)
        elif opcion == "7":
            elegir_servicios_avanzado()
        elif opcion == "8":
            aplicar_telemetria()
        elif opcion == "9":
            menu_perfiles()
        elif opcion == "10":
            deshacer_cambios()
        elif opcion == "0":
            break
        else:
            print(tr("❌ Opción no válida."))
        logger.info(tr("Módulo de rendimiento ejecutado: opción %s"), opcion)
        pausa()
