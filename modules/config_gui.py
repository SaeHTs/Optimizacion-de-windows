"""Configuración persistente para la GUI (JSON en el directorio del exe).

Guarda preferencias del usuario que sobreviven a reinicios:
- tema oscuro siempre activo
- tamaño de la ventana
- etc.
"""
import json
import os
import sys


def _ruta_config() -> str:
    """Ruta del archivo de configuración en el directorio del programa."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config_gui.json")


class ConfigGUI:
    """Configuración persistente leída/guardada en JSON."""

    _DEFAULTS = {
        "tema_oscuro": True,
        "recordar_pos": False,
        "mostrar_confirmaciones": True,
        "idioma": "auto",  # "auto" (detectar Windows) | "es" | "en"
    }

    def __init__(self) -> None:
        self.ruta = _ruta_config()
        self.datos = dict(self._DEFAULTS)
        self._cargar()

    def _cargar(self) -> None:
        """Carga la configuración si existe."""
        try:
            if os.path.exists(self.ruta):
                # utf-8-sig tolera el BOM que añaden PowerShell y algunos
                # editores: sin él, json.load fallaría y la config se
                # ignoraría en silencio.
                with open(self.ruta, encoding="utf-8-sig") as f:
                    self.datos.update(json.load(f))
        except Exception:  # pragma: no cover
            pass

    def guardar(self) -> None:
        """Guarda la configuración actual."""
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(self.datos, f, ensure_ascii=False, indent=2)
        except Exception:  # pragma: no cover
            pass
