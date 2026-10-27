"""Motor de internacionalización (i18n) del optimizador.

Sin dependencias externas. El texto origen está en español; el inglés
se resuelve con tablas de traducción en `locales/en*.json`.

Uso:
    from i18n import tr
    print(tr("Limpiando temporales..."))
    print(tr("Se eliminaron {n} archivos").format(n=3))

Las claves de las tablas son el propio texto en español (con marcadores
`{nombre}` si el texto es dinámico). Si falta una traducción, se devuelve
el texto original: la app nunca falla por una cadena sin traducir.
"""
import ctypes
import json
import os
import sys

_IDIOMA = "es"
_EN: dict[str, str] = {}
_CARGADO = False
# Funciones que recalculan textos ya construidos cuando cambia el idioma
# (tablas de config.py y analisis.py, que se construyen al importarse).
_RELOADERS: list = []


def registrar_recarga(funcion) -> None:
    """Registra una función que rehaga los textos ya construidos.

    Se usa para las tablas de `config.py` / `analisis.py`, que se crean al
    importarse y quedarían congeladas en el idioma de ese momento.
    """
    _RELOADERS.append(funcion)


def _dir_locales() -> str:
    """Carpeta de tablas de idioma (script o exe empaquetado)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "locales")


def _cargar() -> None:
    """Carga (una sola vez) todas las tablas en*.json de `locales/`."""
    global _CARGADO
    if _CARGADO:
        return
    carpeta = _dir_locales()
    try:
        for nombre in sorted(os.listdir(carpeta)):
            if nombre.startswith("en") and nombre.endswith(".json"):
                with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                    datos = json.load(f)
                if isinstance(datos, dict):
                    _EN.update({str(k): str(v) for k, v in datos.items()})
    except OSError:
        pass
    _CARGADO = True


def idioma_sistema() -> str:
    """Devuelve 'es' si Windows está en español; 'en' en cualquier otro caso."""
    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (langid & 0x3FF) == 0x0A:  # 0x0A = español
            return "es"
    except Exception:  # pragma: no cover
        pass
    return "en"


def set_idioma(idioma: str) -> None:
    """Fija el idioma activo. Acepta 'es', 'en' o 'auto' (detectar)."""
    global _IDIOMA
    if idioma == "auto":
        idioma = idioma_sistema()
    elif idioma not in ("es", "en"):
        # valor invalido (config corrupta): se detecta el idioma del sistema
        idioma = idioma_sistema()
    _IDIOMA = "en" if idioma == "en" else "es"
    _cargar()
    # las tablas ya construidas se rehacen con el idioma nuevo
    for recargar in _RELOADERS:
        try:
            recargar()
        except Exception:  # pragma: no cover - un texto fallido no rompe la app
            pass


def get_idioma() -> str:
    """Idioma activo actual ('es' o 'en')."""
    return _IDIOMA


def tr(texto: str) -> str:
    """Traduce un texto al idioma activo (español = identidad)."""
    if _IDIOMA == "es":
        return texto
    _cargar()
    return _EN.get(texto, texto)
