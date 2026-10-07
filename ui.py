"""Interfaz de consola: colores ANSI, banner y pantalla de inicio (splash)."""
import ctypes
import os
import sys

VERSION = "1.5"
PRODUCTO = "Optimización"
PROVEEDOR = "Axiios_HTs"


class Color:
    """Códigos de color ANSI (Windows 10+ con VT habilitado)."""

    CIAN = "\033[96m"
    VERDE = "\033[92m"
    AMARILLO = "\033[93m"
    ROJO = "\033[91m"
    MAGENTA = "\033[95m"
    NEGRITA = "\033[1m"
    GRIS = "\033[90m"
    RESET = "\033[0m"


def activar_ansi() -> None:
    """Habilita colores ANSI en la consola de Windows."""
    try:
        kernel32 = ctypes.windll.kernel32
        manejador = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        modo = ctypes.c_ulong()
        if kernel32.GetConsoleMode(manejador, ctypes.byref(modo)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(manejador, modo.value | 0x0004)
    except Exception:  # pragma: no cover
        pass


def ruta_recurso(nombre: str) -> str:
    """Ruta de un recurso (funciona en script y en exe empaquetado)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, nombre)


def banner() -> None:
    """Muestra el encabezado del programa."""
    linea = "═" * 50
    print(f"{Color.CIAN}{Color.NEGRITA}{linea}")
    print(f"   🖥️   O P T I M I Z A C I Ó N")
    print(f"   {PROVEEDOR} · v{VERSION}")
    print(f"{linea}{Color.RESET}")


def mostrar_splash(duracion: float = 1.6) -> None:
    """Muestra la pantalla de inicio con la imagen del producto."""
    ruta = ruta_recurso("splash.png")
    if not os.path.exists(ruta):
        return
    try:
        import tkinter as tk

        fondo = "#0d1117"
        raiz = tk.Tk()
        raiz.title(f"{PRODUCTO} — {PROVEEDOR}")
        raiz.configure(bg=fondo)
        raiz.overrideredirect(True)  # ventana sin bordes

        imagen = tk.PhotoImage(file=ruta)
        tk.Label(raiz, image=imagen, bg=fondo).pack(
            padx=24, pady=(24, 6)
        )
        tk.Label(
            raiz, text=PRODUCTO.lower(), fg="#ffffff", bg=fondo,
            font=("Segoe UI", 24, "bold"),
        ).pack()
        tk.Label(
            raiz, text=f"{PROVEEDOR}  ·  v{VERSION}", fg="#8b949e",
            bg=fondo, font=("Segoe UI", 10),
        ).pack(pady=(2, 20))

        raiz.update_idletasks()
        x = (raiz.winfo_screenwidth() - raiz.winfo_width()) // 2
        y = (raiz.winfo_screenheight() - raiz.winfo_height()) // 2
        raiz.geometry(f"+{x}+{y}")
        raiz.attributes("-topmost", True)
        raiz.after(int(duracion * 1000), raiz.destroy)
        raiz.mainloop()
    except Exception:  # pragma: no cover
        pass
