"""Barra superior de 36 px: título, selector ES|EN y marca de idioma automático."""
import tkinter as tk

from i18n import tr
from modules.hud.tema import (
    BARRA,
    CIAN,
    TEXTO,
    TEXTO_SEC,
    fuente,
)

_ALTO = 36


class BarraSuperior(tk.Frame):
    """Título a la izquierda y control de idioma a la derecha."""

    def __init__(self, parent, titulo: str, idioma: str, automatico: bool,
                 al_cambiar_idioma) -> None:
        super().__init__(parent, bg=BARRA, height=_ALTO)
        self.pack_propagate(False)
        self.al_cambiar_idioma = al_cambiar_idioma

        tk.Label(
            self, text=titulo, font=fuente(10, True), fg=TEXTO, bg=BARRA,
        ).pack(side="left", padx=14)

        derecha = tk.Frame(self, bg=BARRA)
        derecha.pack(side="right", padx=14)

        self._idiomas: dict[str, tk.Label] = {}
        for codigo, etiqueta in (("es", "ES"), ("en", "EN")):
            if self._idiomas:
                tk.Label(
                    derecha, text="|", font=fuente(9), fg=TEXTO_SEC, bg=BARRA,
                ).pack(side="left", padx=4)
            texto = tk.Label(
                derecha, text=etiqueta, font=fuente(9, True), fg=TEXTO_SEC,
                bg=BARRA, cursor="hand2", padx=2,
            )
            texto.pack(side="left")
            texto.bind("<Button-1>", lambda _e, c=codigo: self._elegir(c))
            self._idiomas[codigo] = texto

        # "Auto" solo aparece si el idioma se detectó del sistema.
        self.texto_auto = tk.Label(
            derecha, text="", font=fuente(8), fg=TEXTO_SEC, bg=BARRA,
        )
        self.texto_auto.pack(side="left", padx=(0, 10))

        self.actualizar(idioma, automatico)

    # -------------------------------------------------- API
    def _elegir(self, codigo: str) -> None:
        if callable(self.al_cambiar_idioma):
            self.al_cambiar_idioma(codigo)

    def actualizar(self, idioma: str, automatico: bool) -> None:
        """Repinta el idioma activo y la marca de detección automática."""
        for codigo, etiqueta in self._idiomas.items():
            etiqueta.config(fg=CIAN if codigo == idioma else TEXTO_SEC)
        self.texto_auto.config(text=f"· {tr('Auto')}" if automatico else "")
