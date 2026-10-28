"""Pruebas del soporte bilingue del optimizador.

Se ejecutan con:  python -m pytest test_i18n.py -v
(o con el script `test_efectividad.py`, que es de solo lectura).
"""
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

import i18n  # noqa: E402


# --------------------------------------------------------------- traducciones
def _tablas():
    """Devuelve {fichero: {clave: traducción}} de locales/en*.json."""
    salida = {}
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "locales", "en*.json"))):
        with open(ruta, encoding="utf-8-sig") as f:
            salida[os.path.basename(ruta)] = json.load(f)
    return salida


def test_no_hay_claves_duplicadas_con_valores_distintos():
    """La misma clave en dos ficheros con textos distintos es una trampa.

    Gana el último fichero cargado, asi que una traduccion puede morir sin
    que nadie se entere. Aqui se delata.
    """
    vistas = {}
    conflictos = []
    for nombre, tabla in _tablas().items():
        for clave, valor in tabla.items():
            if clave in vistas and vistas[clave][1] != valor:
                conflictos.append("%s: %r -> %r / %r -> %r"
                                  % (clave, vistas[clave][0], vistas[clave][1],
                                     nombre, valor))
            vistas[clave] = (nombre, valor)
    assert not conflictos, "claves duplicadas con traducciones distintas:\n" + \
        "\n".join(sorted(conflictos))


def test_todos_los_textos_traducidos_existen_en_las_tablas():
    """Todo lo que se muestra al usuario debe estar en las tablas inglesas."""
    import ast

    claves = set()
    for tabla in _tablas().values():
        claves.update(tabla)

    ficheros = ["main.py", "gui.py", "i18n.py", "ui.py", "utils.py", "config.py",
                "test_efectividad.py"]
    # Recorre modules/ ENTERO, subcarpetas incluidas: al partir la interfaz
    # en componentes (modules/hud/) una lista fija dejaba sus textos sin
    # vigilar y una cadena sin traducir pasaba desapercibida.
    for base, _dirs, nombres in os.walk(os.path.join(RAIZ, "modules")):
        for fichero in sorted(nombres):
            if fichero.endswith(".py"):
                ficheros.append(
                    os.path.relpath(os.path.join(base, fichero), RAIZ))

    faltan = []
    for nombre in ficheros:
        ruta = os.path.join(RAIZ, nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read(), filename=ruta)
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                    and nodo.func.id == "tr"
                    and nodo.args and isinstance(nodo.args[0], ast.Constant)
                    and isinstance(nodo.args[0].value, str)):
                if nodo.args[0].value not in claves:
                    faltan.append("%s:%d %r" % (nombre, nodo.lineno, nodo.args[0].value))
    assert not faltan, "textos sin traduccion:\n" + "\n".join(faltan)


def test_los_marcadores_coinciden_entre_idiomas():
    """Cada clave debe usar los mismos marcadores {..} en los dos idiomas."""
    tablas = _tablas()
    for nombre, tabla in tablas.items():
        for clave, valor in tabla.items():
            marcadores = set(re.findall(r"\{(\w+)\}", valor))
            if clave in _ORIGINALES and _ORIGINALES[clave] is not None:
                esperados = set(re.findall(r"\{(\w+)\}", _ORIGINALES[clave]))
                assert marcadores == esperados, "%s: %r" % (nombre, clave)


_ORIGINALES = {}


def _cargar_originales():
    """Los textos originales en espanol estan en las claves de las tablas."""
    for tabla in _tablas().values():
        for clave in tabla:
            _ORIGINALES[clave] = clave


_cargar_originales()


# --------------------------------------------------------------- idioma activo
def test_el_idioma_invalido_cae_en_el_del_sistema():
    """Una config corrupta ('idioma': null) no debe dejar la app en espanol a saco."""
    original = i18n.idioma_sistema
    try:
        i18n.idioma_sistema = lambda: "en"
        i18n.set_idioma(None)
        assert i18n.get_idioma() == "en"
        i18n.set_idioma("auto")
        assert i18n.get_idioma() == "en"
    finally:
        i18n.idioma_sistema = original
        i18n.set_idioma("es")


def test_las_tablas_de_config_siguen_al_idioma():
    """I-1: config/analisis construyen tablas al importarse: deben recalcularse."""
    i18n.set_idioma("es")
    import config
    from modules import analisis

    assert config.PLANES_ENERGIA["SCHEME_MIN"] == "Alto rendimiento"
    assert analisis.NOMBRES_EFECTOS[2] == "Mejor rendimiento"

    i18n.set_idioma("en")
    assert config.PLANES_ENERGIA["SCHEME_MIN"] == "High performance"
    assert config.SERVICIOS_OPCIONALES["DiagTrack"].startswith("Telemetry")
    assert analisis.NOMBRES_EFECTOS[2] == "Best performance"
    assert config.AJUSTES_PRIVACIDAD[0][0] == "Advertising ID"
    assert analisis.RUTAS_LIMPIABLES[0][0] == "User temporary files"
    i18n.set_idioma("es")


def test_el_nombre_del_perfil_se_traduce():
    """I-3: la clave interna del perfil no puede salir en pantalla."""
    from modules.performance import nombre_perfil
    i18n.set_idioma("en")
    assert nombre_perfil("equilibrado") == "Balanced"
    assert nombre_perfil("privacidad") == "Privacy"
    i18n.set_idioma("es")
    assert nombre_perfil("equilibrado") == "Equilibrado"


if __name__ == "__main__":
    fallos = 0
    for nombre, funcion in sorted(globals().items()):
        if nombre.startswith("test_") and callable(funcion):
            try:
                funcion()
                print("OK   %s" % nombre)
            except AssertionError as e:
                fallos += 1
                print("FALLA %s: %s" % (nombre, e))
    raise SystemExit(1 if fallos else 0)
