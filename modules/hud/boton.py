"""Botones del centro de mando: principal (relleno) y secundario (contorno)."""
import tkinter as tk

from modules.hud.tema import (
    BORDE,
    CIAN,
    CIAN_CLARO,
    FONDO,
    MAGENTA,
    MAGENTA_CLARO,
    PANEL,
    fuente,
)


class BotonHUD(tk.Button):
    """Botón plano con dos variantes: `principal` y `secundario`."""

    def __init__(self, parent, texto: str, comando, variante: str = "principal",
                 ancho: int | None = None) -> None:
        self.variante = variante
        opciones = (
            self._estilo_principal() if variante == "principal"
            else self._estilo_secundario()
        )
        super().__init__(
            parent, text=texto, command=comando,
            font=fuente(11, True), cursor="hand2", relief="flat",
            bd=0, padx=22, pady=9, **opciones,
        )
        if ancho:
            self.configure(width=ancho)
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)

    # -------------------------------------------------- estilos
    @staticmethod
    def _estilo_principal() -> dict:
        return {
            "bg": CIAN, "fg": FONDO,
            "activebackground": CIAN_CLARO, "activeforeground": FONDO,
            "highlightthickness": 0,
        }

    @staticmethod
    def _estilo_secundario() -> dict:
        return {
            "bg": PANEL, "fg": MAGENTA,
            "activebackground": PANEL, "activeforeground": MAGENTA_CLARO,
            "highlightthickness": 1, "highlightbackground": MAGENTA,
            "highlightcolor": MAGENTA,
        }

    # -------------------------------------------------- interacción
    def _entrar(self, _evento=None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        if self.variante == "principal":
            self.config(bg=CIAN_CLARO)
        else:
            self.config(bg=BORDE, fg=MAGENTA_CLARO)

    def _salir(self, _evento=None) -> None:
        if self.variante == "principal":
            self.config(bg=CIAN)
        else:
            self.config(bg=PANEL, fg=MAGENTA)

    # -------------------------------------------------- API
    def configurar_texto(self, texto: str) -> None:
        """Cambia la etiqueta sin recrear el botón (cambio de idioma)."""
        self.config(text=texto)
