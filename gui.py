"""🖥️ Interfaz gráfica (GUI) del Optimizador.

Ejecutar: python gui.py
Tema oscuro, registro en vivo y operaciones en hilos
para que la ventana no se congele.
"""
import ctypes
import os
import queue
import sys
import threading

# Forzar UTF-8 con respaldo seguro
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

import tkinter as tk
from tkinter import messagebox, scrolledtext

import ui
from ui import ruta_recurso, mostrar_splash

# Colores del tema oscuro
FONDO = "#0d1117"
PANEL = "#161b22"
BORDE = "#30363d"
TEXTO = "#e6edf3"
GRIS = "#8b949e"
AZUL = "#58a6ff"
VERDE = "#3fb950"
ROJO = "#f85149"


# ---------------------------------------------------------------- utilidades
def es_administrador() -> bool:
    """Verifica permisos de Administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def reiniciar_como_admin() -> None:
    """Relanza la app con permisos de Administrador (UAC)."""
    if getattr(sys, "frozen", False):
        objetivo = sys.executable
        argumentos = ""
    else:
        objetivo = sys.executable
        argumentos = f'"{sys.argv[0]}"'
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", objetivo, argumentos, None, 1
    )


class _Redireccion:
    """Envía lo que imprimen los módulos al widget de log."""

    def __init__(self, cola: queue.Queue) -> None:
        self.cola = cola

    def write(self, texto: str) -> None:
        if texto.strip():
            self.cola.put(("salida", texto))

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------- aplicación
class OptimizadorGUI:
    """Ventana principal del optimizador."""

    def __init__(self) -> None:
        self.raiz = tk.Tk()
        self.raiz.title(f"{ui.PRODUCTO} — {ui.PROVEEDOR}")
        self.raiz.geometry("780x640")
        self.raiz.minsize(720, 560)
        self.raiz.configure(bg=FONDO)
        try:
            self.raiz.iconbitmap(ruta_recurso("icono.ico"))
        except Exception:  # pragma: no cover
            pass

        self.cola: queue.Queue = queue.Queue()
        self.ejecutando = False
        self.logger = None

        self._crear_widgets()
        self._redirigir_salida()
        self.raiz.after(100, self._procesar_cola)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)

    # -------------------------------------------------- widgets
    def _crear_widgets(self) -> None:
        # Encabezado
        encabezado = tk.Frame(self.raiz, bg=PANEL)
        encabezado.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(
            encabezado, text="🖥️  OPTIMIZACIÓN",
            font=("Segoe UI", 22, "bold"), fg=AZUL, bg=PANEL,
        ).pack(pady=(12, 2))
        tk.Label(
            encabezado, text=f"{ui.PROVEEDOR}  ·  v{ui.VERSION}",
            font=("Segoe UI", 10), fg=GRIS, bg=PANEL,
        ).pack(pady=(0, 12))

        # Botones
        marco_botones = tk.Frame(self.raiz, bg=FONDO)
        marco_botones.pack(fill="x", padx=12, pady=4)
        marco_botones.columnconfigure(0, weight=1)
        marco_botones.columnconfigure(1, weight=1)
        marco_botones.columnconfigure(2, weight=1)

        self.botones = []
        definiciones = [
            ("🧹 Limpieza\nde disco", self._accion_limpieza),
            ("🚀 Programas\nde inicio", self._accion_inicio),
            ("⚡ Rendimiento", self._accion_rendimiento),
            ("🔧 Mantenimiento", self._accion_mantenimiento),
            ("📊 Análisis\nde espacio", self._accion_analisis),
            ("🔍 Vista previa\n(dry-run)", self._accion_vista_previa),
            ("⚡ Modo\nautomático", self._accion_auto),
            ("🛡️ Punto de\nrestauración", self._accion_restore),
            ("ℹ️ Información\ndel sistema", self._accion_info),
        ]
        for indice, (texto, comando) in enumerate(definiciones):
            boton = tk.Button(
                marco_botones, text=texto, command=comando,
                font=("Segoe UI", 10, "bold"),
                bg=PANEL, fg=TEXTO, activebackground=BORDE,
                activeforeground=TEXTO, relief="flat",
                bd=1, highlightthickness=1, highlightbackground=BORDE,
                height=2, width=18,
            )
            boton.grid(
                row=indice // 3, column=indice % 3,
                padx=5, pady=5, sticky="nsew",
            )
            self.botones.append(boton)

        # Registro (log)
        marco_log = tk.Frame(self.raiz, bg=FONDO)
        marco_log.pack(fill="both", expand=True, padx=12, pady=6)
        self.log = scrolledtext.ScrolledText(
            marco_log, bg="#010409", fg=TEXTO,
            font=("Consolas", 9), insertbackground=TEXTO,
            relief="flat", bd=1, highlightthickness=1,
            highlightbackground=BORDE, wrap="word",
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("verde", foreground=VERDE)
        self.log.tag_configure("rojo", foreground=ROJO)
        self._log("✅ Listo. Elige una opción para optimizar.\n")

        # Barra de estado
        self.estado = tk.Label(
            self.raiz, text="  Listo  ·  Axiios_HTs",
            font=("Segoe UI", 9), fg=GRIS, bg=FONDO,
            anchor="w",
        )
        self.estado.pack(fill="x", padx=12, pady=(0, 10))

    def _redirigir_salida(self) -> None:
        sys.stdout = _Redireccion(self.cola)
        sys.stderr = _Redireccion(self.cola)

    def _log(self, texto: str) -> None:
        self.log.insert("end", texto)
        self.log.see("end")

    def _actualizar_botones(self) -> None:
        estado = "disabled" if self.ejecutando else "normal"
        for boton in self.botones:
            boton.config(state=estado)
        if self.ejecutando:
            self.estado.config(text="  ⏳ Ejecutando… no cierres la ventana  ")
        else:
            self.estado.config(text="  Listo  ·  Axiios_HTs")

    # -------------------------------------------------- cola de salida
    def _procesar_cola(self) -> None:
        while True:
            try:
                tipo, texto = self.cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "__FIN__":
                self.ejecutando = False
                self._actualizar_botones()
                self._log("\n✅ Operación completada.\n")
            else:
                self._log(texto)
        self.raiz.after(100, self._procesar_cola)

    # -------------------------------------------------- ejecución
    def _ejecutar(self, funcion, *args) -> None:
        """Ejecuta una operación en un hilo separado."""
        if self.ejecutando:
            return
        self.ejecutando = True
        self._actualizar_botones()
        self._log("\n" + "━" * 58 + "\n")

        def hilo() -> None:
            try:
                funcion(*args)
            except Exception as e:  # pragma: no cover
                print(f"❌ Error inesperado: {e}")
            finally:
                self.cola.put(("__FIN__", None))

        threading.Thread(target=hilo, daemon=True).start()

    # -------------------------------------------------- acciones
    def _accion_limpieza(self) -> None:
        from modules.disk_cleanup import modo_automatico
        self._ejecutar(modo_automatico, self._logger())

    def _accion_inicio(self) -> None:
        from modules.startup import modo_automatico
        self._ejecutar(modo_automatico, self._logger())

    def _accion_rendimiento(self) -> None:
        from modules.performance import modo_automatico
        self._ejecutar(modo_automatico, self._logger())

    def _accion_mantenimiento(self) -> None:
        from modules.maintenance import modo_automatico
        self._ejecutar(modo_automatico, self._logger())

    def _accion_analisis(self) -> None:
        from modules.analisis import analisis_espacio
        self._ejecutar(analisis_espacio)

    def _accion_vista_previa(self) -> None:
        from modules.analisis import vista_previa
        self._ejecutar(vista_previa, self._logger())

    def _accion_auto(self) -> None:
        from modules.disk_cleanup import modo_automatico as a1
        from modules.startup import modo_automatico as a2
        from modules.performance import modo_automatico as a3
        from modules.maintenance import modo_automatico as a4

        def todo() -> None:
            a1(self._logger())
            a2(self._logger())
            a3(self._logger())
            a4(self._logger())
            print("\n✅ Optimización COMPLETA finalizada.")
            print("   Reinicia el equipo para aplicar todos los cambios.")

        if messagebox.askyesno(
            "Modo automático",
            "Esto ejecuta TODAS las optimizaciones "
            "(puede tardar varios minutos).\n\n"
            "¿Crear un punto de restauración primero?",
        ):
            from utils import crear_punto_restauracion

            crear_punto_restauracion()
        self._ejecutar(todo)

    def _accion_restore(self) -> None:
        from utils import crear_punto_restauracion
        self._ejecutar(crear_punto_restauracion)

    def _accion_info(self) -> None:
        from utils import info_sistema
        self._ejecutar(info_sistema)

    def _logger(self):
        """Logger diferido (se crea al primer uso)."""
        if self.logger is None:
            from utils import setup_logger

            self.logger = setup_logger()
        return self.logger

    # -------------------------------------------------- cierre
    def _cerrar(self) -> None:
        if self.ejecutando:
            if not messagebox.askyesno(
                "Ejecutando…",
                "Hay una operación en curso. "
                "¿Seguro que quieres salir?",
            ):
                return
        self.raiz.destroy()


# ---------------------------------------------------------------- entrada
def main() -> None:
    if os.name != "nt":
        print("❌ Esta herramienta solo funciona en Windows.")
        sys.exit(1)

    if not es_administrador():
        raiz = tk.Tk()
        raiz.withdraw()
        if messagebox.askyesno(
            "Administrador requerido",
            "El optimizador necesita permisos de Administrador.\n\n"
            "¿Reiniciar como Administrador?",
        ):
            reiniciar_como_admin()
        raiz.destroy()
        sys.exit(0)

    mostrar_splash()
    app = OptimizadorGUI()
    app.raiz.mainloop()


if __name__ == "__main__":
    main()
