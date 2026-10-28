"""Barra lateral de navegación del centro de mando.

Cada entrada es una fila clicable con una marca de 3 px a la izquierda
que se ilumina en cian cuando la entrada está activa. Las claves que
empiezan por `SECCION:` crean un separador con título.
"""
import tkinter as tk

from modules.hud.tema import (
    CIAN,
    LATERAL,
    TEXTO,
    TEXTO_SEC,
    fuente,
)

_ANCHO = 166
_MARCA = 3


class BarraLateral(tk.Frame):
    """Menú vertical con icono, texto y estado activo."""

    def __init__(self, parent, entradas: list) -> None:
        # Cada entrada: (clave, texto, comando, color)
        super().__init__(parent, bg=LATERAL, width=_ANCHO)
        self.pack_propagate(False)
        self.activo: str | None = None
        self._filas: dict[str, tuple[tk.Frame, tk.Label, str]] = {}

        for clave, texto, comando, color in entradas:
            if clave.startswith("SECCION:"):
                tk.Label(
                    self, text=clave.split(":", 1)[1].upper(),
                    font=fuente(8, True), fg=TEXTO_SEC, bg=LATERAL,
                    anchor="w",
                ).pack(fill="x", padx=14, pady=(9, 2))
                continue
            self._crear_fila(clave, texto, comando, color)

    def _crear_fila(self, clave: str, texto: str, comando, color: str) -> None:
        fila = tk.Frame(self, bg=LATERAL, cursor="hand2")
        fila.pack(fill="x")

        marca = tk.Frame(fila, bg=LATERAL, width=_MARCA)
        marca.pack(side="left", fill="y")

        etiqueta = tk.Label(
            fila, text=texto, font=fuente(10), fg=color, bg=LATERAL,
            anchor="w", padx=10, pady=5, cursor="hand2",
        )
        etiqueta.pack(side="left", fill="x", expand=True)

        for widget in (fila, etiqueta):
            widget.bind(
                "<Button-1>",
                lambda _e, c=clave, f=comando: self._pulsar(c, f),
            )
        self._filas[clave] = (marca, etiqueta, color)

    def _pulsar(self, clave: str, comando) -> None:
        """Marca la entrada como activa y ejecuta su acción."""
        self.seleccionar(clave)
        if callable(comando):
            comando()

    # -------------------------------------------------- API
    def seleccionar(self, clave: str) -> None:
        """Ilumina la entrada indicada y apaga la anterior."""
        for otra, (marca, etiqueta, color) in self._filas.items():
            activa = otra == clave
            marca.config(bg=CIAN if activa else LATERAL)
            etiqueta.config(fg=TEXTO if activa else color)
        if clave in self._filas:
            self.activo = clave

    def colorear(self, clave: str, color: str) -> None:
        """Cambia el color base de una entrada (p. ej. deshacer habilitado)."""
        if clave not in self._filas:
            return
        marca, etiqueta, _anterior = self._filas[clave]
        self._filas[clave] = (marca, etiqueta, color)
        if self.activo != clave:
            etiqueta.config(fg=color)
