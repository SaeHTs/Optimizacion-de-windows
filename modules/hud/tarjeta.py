"""Tarjeta de estado del centro de mando.

Cada tarjeta muestra un título, un valor grande y una línea de detalle.
Mientras el análisis lento está en marcha muestra "Analizando…".
Toda la tarjeta es clicable (incluidos sus hijos).
"""
import tkinter as tk

from i18n import tr
from modules.hud.tema import BORDE, PANEL, TEXTO, TEXTO_SEC, fuente

_FILO = 3  # alto del borde superior de color, en píxeles


class Tarjeta(tk.Frame):
    """Panel rectangular con borde superior de color por categoría."""

    def __init__(self, parent, titulo: str, color: str,
                 al_clic=None) -> None:
        super().__init__(
            parent, bg=PANEL, highlightthickness=1,
            highlightbackground=BORDE, bd=0,
        )
        self.color = color
        self._al_clic = al_clic

        tk.Frame(self, bg=color, height=_FILO).pack(fill="x")

        self.etiqueta_titulo = tk.Label(
            self, text=titulo, font=fuente(9), fg=TEXTO_SEC, bg=PANEL,
            anchor="w",
        )
        self.etiqueta_titulo.pack(fill="x", padx=10, pady=(8, 0))

        self.etiqueta_valor = tk.Label(
            self, text="—", font=fuente(20, True), fg=TEXTO, bg=PANEL,
            anchor="w",
        )
        self.etiqueta_valor.pack(fill="x", padx=10)

        self.etiqueta_detalle = tk.Label(
            self, text="", font=fuente(9), fg=TEXTO_SEC, bg=PANEL,
            anchor="w",
        )
        self.etiqueta_detalle.pack(fill="x", padx=10, pady=(0, 8))

        self._enlazar_clic()

    # -------------------------------------------------- contenido
    def set_valor(self, texto: str) -> None:
        """Valor principal de la tarjeta (ya formateado).

        Tkinter no encoge el texto solo: con "Sin registros" el tamaño
        grande se sale del panel, así que las cadenas largas bajan de
        tamaño en vez de recortarse.
        """
        tamano = 20 if len(texto) <= 10 else 15
        self.etiqueta_valor.config(text=texto, fg=TEXTO, font=fuente(tamano, True))

    def set_detalle(self, texto: str) -> None:
        """Línea pequeña bajo el valor."""
        self.etiqueta_detalle.config(text=texto)

    def set_analizando(self, analizando: bool = True) -> None:
        """Muestra el estado de espera mientras corre el análisis."""
        if analizando:
            self.etiqueta_valor.config(text=tr("Analizando…"), fg=TEXTO_SEC)
            self.etiqueta_detalle.config(text="")
        else:
            self.etiqueta_valor.config(fg=TEXTO)

    # -------------------------------------------------- clic
    def al_clic(self, callback) -> None:
        """Asigna (o reasigna) la acción de toda la tarjeta."""
        self._al_clic = callback
        self._enlazar_clic()

    def _enlazar_clic(self) -> None:
        """El clic funciona en el marco y en cualquier etiqueta hija."""
        self.configure(cursor="hand2")
        for widget in (self, self.etiqueta_titulo, self.etiqueta_valor,
                       self.etiqueta_detalle):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", self._pulsar)

    def _pulsar(self, _evento=None) -> None:
        if callable(self._al_clic):
            self._al_clic()
