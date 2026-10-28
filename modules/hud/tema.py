"""Paleta, fuentes y helpers visuales del centro de mando HUD.

Es el ÚNICO sitio donde viven los colores de la GUI. Ningún otro módulo
de `modules/hud/` debe escribir un color literal: si hace falta un tono
nuevo, se declara aquí.
"""
import os

# ---------- Paleta (valores exactos de la especificación) ----------
FONDO = "#0A0A12"        # fondo de la ventana
BARRA = "#0F0F1C"        # barra superior de 36 px
LATERAL = "#0D0D19"      # barra lateral
PANEL = "#12121F"        # tarjetas, botones base y medidor
BORDE = "#24243A"        # borde de 1 px de paneles y tarjetas
CIAN = "#00F0FF"         # activo / valores buenos
MAGENTA = "#FF2BD6"      # acciones y deshacer
AMARILLO = "#FFE600"     # advertencias
TEXTO = "#E6E8F5"        # texto principal
TEXTO_SEC = "#8A8FA8"    # texto secundario

# Tonos derivados (no son colores nuevos: son el mismo color atenuado).
CIAN_TENUE = "#0F3A44"    # anillo exterior del medidor
CIAN_CLARO = "#5CF8FF"    # hover del botón principal
MAGENTA_CLARO = "#FF6BE4"  # hover del botón secundario


def _detectar_mono() -> str:
    """Monoespaciada preferida, si está instalada en el equipo.

    JetBrains Mono y Share Tech Mono no vienen con Windows; si sus
    ficheros están en la carpeta de fuentes se usan, y si no, Consolas,
    que sí está en cualquier Windows 10/11.
    """
    carpeta = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    try:
        instaladas = {n.lower() for n in os.listdir(carpeta)}
    except OSError:  # pragma: no cover - sin acceso a la carpeta de fuentes
        return "Consolas"
    for prefijo, familia in (
        ("jetbrainsmono", "JetBrains Mono"),
        ("sharetechmono", "Share Tech Mono"),
    ):
        if any(n.startswith(prefijo) for n in instaladas):
            return familia
    return "Consolas"


FUENTE_MONO = _detectar_mono()


def fuente(tamano: int, negrita: bool = False) -> tuple:
    """Tupla de fuente para Tkinter con la monoespaciada del tema."""
    if negrita:
        return (FUENTE_MONO, tamano, "bold")
    return (FUENTE_MONO, tamano)


def atenuar(color: str, factor: float) -> str:
    """Mezcla un color con el fondo para simular un brillo tenue.

    Tkinter no tiene desenfoque (glow), así que el halo del medidor se
    aproxima dibujando el mismo arco en un tono apagado detrás.
    """
    factor = max(0.0, min(1.0, factor))
    origen = color.lstrip("#")
    destino = FONDO.lstrip("#")
    canales = []
    for i in (0, 2, 4):
        a = int(origen[i:i + 2], 16)
        b = int(destino[i:i + 2], 16)
        canales.append(int(round(a * factor + b * (1 - factor))))
    return "#%02X%02X%02X" % tuple(canales)


def color_salud(valor: int) -> str:
    """Color del anillo según el puntaje de salud.

    Menos de 40 → magenta (mal); 40 a 70 → amarillo (mejorable);
    por encima de 70 → cian (bien). Los umbrales son los de la
    especificación y están aquí para poder ajustarlos en un sitio.
    """
    if valor < 40:
        return MAGENTA
    if valor <= 70:
        return AMARILLO
    return CIAN
