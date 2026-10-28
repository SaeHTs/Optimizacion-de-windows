"""Pruebas de la telemetría ampliada: tareas programadas y políticas.

No tocan el sistema: comprueban los datos que se aplicarán (rutas, claves y
tipos) y que el flujo llama a las dos mitades sin volver a preguntar.
"""
import config
from modules import performance


# ------------------------------------------------------------------ datos
def test_las_tareas_ampliadas_estan_en_la_lista():
    claves = {(ruta, nombre) for ruta, nombre in config.TAREAS_TELEMETRIA}
    assert (r"\Microsoft\Windows\Feedback\Siuf", "DmClient") in claves
    assert (r"\Microsoft\Windows\Feedback\Siuf",
            "DmClientOnScenarioDownload") in claves
    assert (r"\Microsoft\Windows\Windows Error Reporting",
            "QueueReporting") in claves
    assert (r"\Microsoft\Windows\DiskDiagnostic",
            "Microsoft-Windows-DiskDiagnosticDataCollector") in claves
    assert (r"\Microsoft\Windows\PI", "Sqm-Tasks") in claves


def test_no_hay_tareas_duplicadas_y_son_de_windows():
    claves = [(ruta, nombre) for ruta, nombre in config.TAREAS_TELEMETRIA]
    assert len(claves) == len(set(claves)), "hay tareas repetidas"
    for ruta, nombre in claves:
        assert ruta.startswith("\\Microsoft\\Windows\\"), ruta
        assert nombre and "\\" not in nombre, nombre


def test_las_politicas_son_dword_validos_y_unicos():
    vistos = set()
    for descripcion, raiz, subclave, valor, dato in config.POLITICAS_TELEMETRIA:
        assert descripcion, "política sin descripción"
        assert raiz in ("HKCU", "HKLM"), raiz
        assert subclave and valor, (subclave, valor)
        assert isinstance(dato, int) and dato in (0, 1), dato
        clave = (raiz, subclave, valor)
        assert clave not in vistos, "política repetida: %s" % (clave,)
        vistos.add(clave)


def test_las_politicas_esperadas_estan():
    claves = {(raiz, subclave, valor)
              for _, raiz, subclave, valor, _ in config.POLITICAS_TELEMETRIA}
    assert claves == {
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
         "AllowTelemetry"),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
         "Start_TrackProgs"),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion"
                 r"\ContentDeliveryManager", "SystemPaneSuggestionsEnabled"),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion"
                 r"\ContentDeliveryManager", "SilentInstalledAppsEnabled"),
        ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion"
                 r"\ContentDeliveryManager", "SoftLandingEnabled"),
        ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
         "DisableWindowsConsumerFeatures"),
    }


# ------------------------------------------------------------------ flujo
def test_las_politicas_siguen_al_idioma():
    """La tabla se recalcula al cambiar de idioma, no se queda congelada."""
    import i18n

    i18n.set_idioma("en")
    try:
        assert config.POLITICAS_TELEMETRIA[0][0] == "Diagnostics: required data only"
    finally:
        i18n.set_idioma("es")
    assert config.POLITICAS_TELEMETRIA[0][0] == "Diagnóstico: solo datos necesarios"


def _espia(monkeypatch, llamadas):
    monkeypatch.setattr(
        performance, "deshabilitar_tareas_telemetria",
        lambda automatico=False: llamadas.append(("tareas", automatico)))
    monkeypatch.setattr(
        performance, "_aplicar_ajustes_registro",
        lambda ajustes: (llamadas.append(("politicas", ajustes)), len(ajustes))[1])


def test_aplicar_telemetria_hace_tareas_y_politicas(monkeypatch):
    llamadas = []
    _espia(monkeypatch, llamadas)

    performance.aplicar_telemetria(automatico=True)

    assert [c[0] for c in llamadas] == ["tareas", "politicas"]
    assert llamadas[0][1] is True, "las tareas no deben volver a preguntar"
    assert llamadas[1][1] is config.POLITICAS_TELEMETRIA


def test_cancelar_no_aplica_nada(monkeypatch):
    llamadas = []
    _espia(monkeypatch, llamadas)
    monkeypatch.setattr(performance, "confirmar", lambda *a, **k: False)

    performance.aplicar_telemetria()

    assert llamadas == []


def test_si_falla_una_parte_la_otra_sigue(monkeypatch):
    """Un fallo en las tareas no debe impedir aplicar las políticas."""
    llamadas = []

    def tareas_roto(automatico=False):
        llamadas.append(("tareas", automatico))
        raise RuntimeError("PowerShell no disponible")

    monkeypatch.setattr(performance, "deshabilitar_tareas_telemetria", tareas_roto)
    monkeypatch.setattr(
        performance, "_aplicar_ajustes_registro",
        lambda ajustes: (llamadas.append(("politicas", ajustes)), len(ajustes))[1])

    performance.aplicar_telemetria(automatico=True)

    assert [c[0] for c in llamadas] == ["tareas", "politicas"]


# --------------------------------------------------------------- rollback
def test_una_tarea_ya_desactivada_no_se_toca_ni_se_registra(monkeypatch):
    """Si ya estaba apagada, 'Deshacer' no debe encenderla."""
    from modules import rollback

    monkeypatch.setattr(performance, "TAREAS_TELEMETRIA", [(r"\X", "Y")])
    comandos = []
    monkeypatch.setattr(
        performance, "ejecutar_powershell",
        lambda cmd: (comandos.append(cmd), (0, "Disabled"))[1])
    registros = []
    monkeypatch.setattr(rollback, "registrar_tarea",
                        lambda *a: registros.append(a))

    performance.deshabilitar_tareas_telemetria(automatico=True)

    assert not any("Disable-ScheduledTask" in c for c in comandos)
    assert registros == []


def test_una_tarea_activa_se_desactiva_y_se_registra(monkeypatch):
    from modules import rollback

    monkeypatch.setattr(performance, "TAREAS_TELEMETRIA", [(r"\X", "Y")])
    comandos = []

    def falso(cmd):
        comandos.append(cmd)
        return (0, "Ready") if "Get-ScheduledTask" in cmd else (0, "")

    monkeypatch.setattr(performance, "ejecutar_powershell", falso)
    registros = []
    monkeypatch.setattr(rollback, "registrar_tarea",
                        lambda *a: registros.append(a))

    performance.deshabilitar_tareas_telemetria(automatico=True)

    assert any("Disable-ScheduledTask" in c for c in comandos)
    assert registros == [(r"\X", "Y")]
