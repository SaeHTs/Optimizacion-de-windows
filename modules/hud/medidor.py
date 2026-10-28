"""Medidor circular de salud del PC (anillo animado).

Tkinter no tiene desenfoque: el efecto neón se aproxima con dos arcos
concéntricos, uno tenue detrás y otro brillante delante.
"""
import tkinter as tk

from modules.hud.tema import (
    BORDE,
    PANEL,
    TEXTO_SEC,
    atenuar,
    color_salud,
    fuente,
)

_MARGEN = 14
_GROSOR_HALO = 11
_GROSOR_ANILLO = 6
_ANGULO_MAXIMO = -359.9  # casi una vuelta completa (0 y 360 coinciden)


class MedidorSalud(tk.Canvas):
    """Anillo de 0 a 100 con el puntaje de salud en el centro."""

    def __init__(self, parent, diametro: int = 170,
                 etiqueta: str = "Salud del PC") -> None:
        super().__init__(
            parent, width=diametro, height=diametro,
            bg=PANEL, highlightthickness=0, bd=0,
        )
        self.diametro = diametro
        self.etiqueta = etiqueta
        self.valor = 0
        self._animacion = None
        self._crear()

    # -------------------------------------------------- dibujo
    def _crear(self) -> None:
        caja = (_MARGEN, _MARGEN,
                self.diametro - _MARGEN, self.diametro - _MARGEN)
        self.create_oval(*caja, outline=BORDE, width=_GROSOR_ANILLO)
        # Halo tenue detrás del arco de color
        self._halo = self.create_arc(
            *caja, start=90, extent=0, style="arc",
            outline=BORDE, width=_GROSOR_HALO,
        )
        # Arco principal
        self._anillo = self.create_arc(
            *caja, start=90, extent=0, style="arc",
            outline=color_salud(0), width=_GROSOR_ANILLO,
        )
        centro = self.diametro / 2
        self._numero = self.create_text(
            centro, centro - 6, text="0",
            fill=color_salud(0), font=fuente(34, True),
        )
        self.create_text(
            centro, centro + 26, text=self.etiqueta,
            fill=TEXTO_SEC, font=fuente(9),
        )

    def _pintar(self, valor: int) -> None:
        """Repinta el anillo y el número para el valor indicado."""
        color = color_salud(valor)
        self.itemconfig(self._anillo, outline=color,
                        extent=_ANGULO_MAXIMO * valor / 100)
        self.itemconfig(self._halo, outline=atenuar(color, 0.35),
                        extent=_ANGULO_MAXIMO * valor / 100)
        self.itemconfig(self._numero, text=str(valor), fill=color)

    # -------------------------------------------------- API
    def set_valor(self, valor: int, animar: bool = True) -> None:
        """Fija el puntaje; con `animar` interpola hasta él suavemente."""
        objetivo = max(0, min(100, int(valor)))
        if self._animacion is not None:
            try:
                self.after_cancel(self._animacion)
            except Exception:  # pragma: no cover - ventana ya destruida
                pass
            self._animacion = None

        if not animar or objetivo == self.valor:
            self.valor = objetivo
            self._pintar(self.valor)
            return

        self._paso(objetivo, self.valor)

    def _paso(self, objetivo: int, actual: int) -> None:
        """Avanza un escalón de la animación (unos 12 tramos de 16 ms)."""
        diferencia = objetivo - actual
        if diferencia == 0:
            self.valor = objetivo
            self._pintar(self.valor)
            self._animacion = None
            return
        salto = int(round(diferencia / 12)) or (1 if diferencia > 0 else -1)
        siguiente = actual + int(round(salto))
        if (diferencia > 0 and siguiente >= objetivo) or \
                (diferencia < 0 and siguiente <= objetivo):
            siguiente = objetivo
        self.valor = siguiente
        self._pintar(self.valor)
        self._animacion = self.after(16, self._paso, objetivo, siguiente)
