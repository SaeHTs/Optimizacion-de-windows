"""🖥️ Interfaz gráfica (GUI) del Optimizador.

Ejecutar: python gui.py
Tema cyberpunk / dark, registro en vivo y operaciones en hilos
para que la ventana no se congele.
"""
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

import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import ui
from i18n import get_idioma, set_idioma, tr
from ui import ruta_recurso, mostrar_splash

# ---------- Paleta cyberpunk / dark ----------
FONDO = "#0a0a0f"        # fondo principal (casi negro azulado)
PANEL = "#14141f"        # paneles y botones base
BORDE = "#2a2a40"        # borde sutil de paneles
TEXTO = "#e0e0ff"        # texto principal
TEXTO_SEC = "#8b8cf0"    # texto secundario / etiquetas
CIAN = "#00f3ff"         # neón cian (principal / acciones rápidas / información)
VERDE = "#00ff9d"        # neón verde (limpieza / éxito)
ROJO = "#ff0055"         # neón rojo (deshacer / errores)
AMARILLO = "#ffcc00"     # neón amarillo (rendimiento / avisos)
MAGENTA = "#ff00ff"      # neón magenta (mantenimiento / avanzado)
NARANJA = "#ff8c42"      # neón naranja (telemetría)
GRIS = "#8b8cf0"         # gris azulado secundario

from modules.config_gui import ConfigGUI  # noqa: E402


# ---------------------------------------------------------------- utilidades
# Permisos de Administrador: fuente única en modules/core.py
from modules.core import reiniciar_como_admin, verificar_permisos


_PATRON_PROGRESO = re.compile(r"Progreso:\s*(\d+)\s*%")


class _Redireccion:
    """Envía lo que imprimen los módulos al widget de log.

    Las líneas "Progreso: N%" (emitidas por ejecutar_con_barra en modo
    no interactivo) se convierten en mensajes de progreso para la barra
    visual en lugar de llenar el registro de texto.
    """

    def __init__(self, cola: queue.Queue) -> None:
        self.cola = cola

    def write(self, texto: str) -> None:
        if not texto.strip():
            return
        try:
            # block=False: si la cola está llena, se descarta el
            # mensaje en lugar de congelar el hilo de trabajo.
            coincidencia = _PATRON_PROGRESO.search(texto)
            if coincidencia:
                self.cola.put(("progreso", int(coincidencia.group(1))),
                              block=False)
            else:
                self.cola.put(("salida", texto), block=False)
        except queue.Full:
            pass

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        """Indica que NO es una consola interactiva (es la GUI)."""
        return False


# ---------------------------------------------------------------- aplicación
class OptimizadorGUI:
    """Ventana principal del optimizador."""

    def __init__(self) -> None:
        self.raiz = tk.Tk()
        self.raiz.title(f"{ui.PRODUCTO} — {ui.PROVEEDOR}")
        self.raiz.geometry("780x680")
        self.raiz.minsize(720, 600)
        self.raiz.configure(bg=FONDO)
        try:
            self.raiz.iconbitmap(ruta_recurso("icono.ico"))
        except Exception:  # pragma: no cover
            pass

        # Configuración persistente (config_gui.json junto al exe/script):
        # con "recordar_pos": true se restaura el tamaño/posición guardados.
        self.cfg = ConfigGUI()
        if (self.cfg.datos.get("recordar_pos")
                and self.cfg.datos.get("ultima_geometria")):
            geo = self._geometria_visible(self.cfg.datos["ultima_geometria"])
            if geo:
                try:
                    self.raiz.geometry(geo)
                except Exception:  # pragma: no cover
                    pass

        # Cola con tamaño máximo para prevenir bloqueos o consumo excesivo
        # de memoria si la UI va más lenta que el hilo de trabajo.
        self.cola: queue.Queue = queue.Queue(maxsize=100)
        self.ejecutando = False
        self.logger = None
        self._pendiente_auto = None  # confirmación post-vista-previa (modo automático)

        self._crear_widgets()
        self._redirigir_salida()
        self._configurar_atajos()
        self.raiz.after(100, self._procesar_cola)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _geometria_visible(self, geo: str) -> str | None:
        """Devuelve la geometría solo si cruza la pantalla principal.

        Evita la ventana invisible tras desconectar un monitor: la
        posición guardada puede apuntar a una pantalla que ya no
        existe. Los monitores a la izquierda (coordenadas negativas)
        se sacrifican a cambio de que la ventana SIEMPRE sea visible.
        """
        m = re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", geo.strip())
        if not m:
            return None
        ancho, alto, x, y = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        if ancho < 100 or alto < 100 or ancho > 5000 or alto > 5000:
            return None
        pantalla_w = self.raiz.winfo_screenwidth()
        pantalla_h = self.raiz.winfo_screenheight()
        # Debe solapar al menos 50 px con la pantalla principal
        if x + ancho <= 0 or y + alto <= 0 or x >= pantalla_w or y >= pantalla_h:
            return None
        return f"{ancho}x{alto}{x:+d}{y:+d}"

    # -------------------------------------------------- widgets
    def _crear_widgets(self) -> None:
        # Encabezado con estilo cyberpunk
        encabezado = tk.Frame(self.raiz, bg=PANEL, highlightthickness=1,
                              highlightbackground=BORDE)
        encabezado.pack(fill="x", padx=12, pady=(12, 8))
        tk.Button(
            encabezado, text=f"🌐 {get_idioma().upper()}",
            command=self._alternar_idioma,
            font=("Segoe UI", 9, "bold"), fg=CIAN, bg=PANEL,
            activebackground=BORDE, activeforeground=CIAN,
            relief="flat", bd=1, highlightthickness=1,
            highlightbackground=BORDE, cursor="hand2",
        ).place(relx=1.0, x=-12, y=10, anchor="ne")
        tk.Label(
            encabezado, text=tr("⚡  HTs OPTIMIZACIÓN"),
            font=("Segoe UI", 20, "bold"), fg=CIAN, bg=PANEL,
        ).pack(pady=(14, 2))
        admin = (tr("🔰 Administrador") if verificar_permisos()
                 else tr("⚠️ Sin admin (UAC al operar)"))
        tk.Label(
            encabezado, text=f"{ui.PROVEEDOR}  ·  v{ui.VERSION}  ·  {admin}",
            font=("Segoe UI", 10), fg=TEXTO_SEC, bg=PANEL,
        ).pack(pady=(0, 14))

        # Botones agrupados por secciones, con color neón por categoría
        marco_botones = tk.Frame(self.raiz, bg=FONDO)
        marco_botones.pack(fill="x", padx=12, pady=4)
        marco_botones.columnconfigure(0, weight=1)
        marco_botones.columnconfigure(1, weight=1)
        marco_botones.columnconfigure(2, weight=1)

        self.botones = []
        secciones = [
            (tr("⚡ ACCIONES RÁPIDAS"), [
                (tr("⚡ Modo\nautomático"), self._accion_auto, AMARILLO),
                (tr("🔍 Vista previa\n(dry-run)"), self._accion_vista_previa, CIAN),
                (tr("🎯 Perfiles\n(E/G/P)"), self._accion_perfiles, VERDE),
            ]),
            (tr("🧹 SISTEMA"), [
                (tr("🧹 Limpieza\nde disco"), self._accion_limpieza, VERDE),
                (tr("🚀 Programas\nde inicio"), self._accion_inicio, CIAN),
                (tr("🔧 Mantenimiento"), self._accion_mantenimiento, MAGENTA),
            ]),
            (tr("⚡ RENDIMIENTO Y AVANZADO (reversible)"), [
                (tr("⚡ Rendimiento"), self._accion_rendimiento, AMARILLO),
                (tr("📡 Tareas de\ntelemetría"), self._accion_telemetria, NARANJA),
                (tr("⏪ Deshacer\ncambios"), self._accion_deshacer, ROJO),
            ]),
            (tr("📊 INFORMES"), [
                (tr("📊 Análisis\nde espacio"), self._accion_analisis, CIAN),
                (tr("🛡️ Punto de\nrestauración"), self._accion_restore, CIAN),
                (tr("📋 Exportar\ninforme"), self._accion_exportar, CIAN),
            ]),
            (tr("ℹ️ EXTRAS"), [
                (tr("ℹ️ Información\ndel sistema"), self._accion_info, GRIS),
                (tr("📄 Abrir\nregistro"), self._accion_log, GRIS),
            ]),
        ]
        fila_actual = 0
        for titulo_seccion, definiciones in secciones:
            etiqueta = tk.Label(
                marco_botones, text=titulo_seccion,
                font=("Segoe UI", 9, "bold"), fg=TEXTO_SEC, bg=FONDO,
                anchor="w",
            )
            etiqueta.grid(row=fila_actual, column=0, columnspan=3,
                          sticky="w", padx=5, pady=(8, 0))
            fila_actual += 1
            for indice, (texto, comando, color) in enumerate(definiciones):
                fila, columna = divmod(indice, 3)
                boton = tk.Button(
                    marco_botones, text=texto, command=comando,
                    font=("Segoe UI", 10, "bold"),
                    bg=PANEL, fg=color, activebackground=BORDE,
                    activeforeground=color, relief="flat",
                    bd=1, highlightthickness=1, highlightbackground=BORDE,
                    height=2, width=18,
                    cursor="hand2",
                )
                # Efecto neón al pasar el mouse: borde y texto brillan.
                boton.bind(
                    "<Enter>",
                    lambda e, b=boton, c=color: self._entrar_boton(b, c),
                )
                boton.bind(
                    "<Leave>",
                    lambda e, b=boton, c=color: self._salir_boton(b, c),
                )
                boton.grid(
                    row=fila_actual + fila, column=columna,
                    padx=5, pady=5, sticky="nsew",
                )
                self.botones.append(boton)
            fila_actual += (len(definiciones) + 2) // 3

        # Registro (log)
        marco_log = tk.Frame(self.raiz, bg=FONDO)
        marco_log.pack(fill="both", expand=True, padx=12, pady=6)
        self.log = scrolledtext.ScrolledText(
            marco_log, bg="#050508", fg=TEXTO,
            font=("Consolas", 9), insertbackground=TEXTO,
            relief="flat", bd=1, highlightthickness=1,
            highlightbackground=BORDE, wrap="word",
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("verde", foreground=VERDE)
        self.log.tag_configure("rojo", foreground=ROJO)
        self.log.tag_configure("amarillo", foreground=AMARILLO)
        self.log.tag_configure("cian", foreground=CIAN)
        self._log(tr("✅ Listo. Elige una opción para optimizar.\n"), "cian")

        # Barra de progreso (determinada cuando el comando reporta %;
        # indeterminada (marquee) mientras la operación corre sin %)
        estilo = ttk.Style(self.raiz)
        estilo.theme_use("clam")
        estilo.configure(
            "Ciber.Horizontal.TProgressbar",
            troughcolor="#050508", background=CIAN,
            bordercolor=BORDE, lightcolor=CIAN, darkcolor=CIAN,
        )
        self.progreso = ttk.Progressbar(
            self.raiz, style="Ciber.Horizontal.TProgressbar",
            mode="determinate", maximum=100, value=0,
        )
        self.progreso.pack(fill="x", padx=12, pady=(0, 2))

        # Texto informativo encima de la barra de estado
        self.texto_progreso = tk.Label(
            self.raiz, text="",
            font=("Segoe UI", 9), fg=VERDE, bg=FONDO,
            anchor="w",
        )
        self.texto_progreso.pack(fill="x", padx=12, pady=(0, 4))

        # Barra de estado
        self.estado = tk.Label(
            self.raiz, text=tr("  Listo  ·  Axiios_HTs"),
            font=("Segoe UI", 9), fg=TEXTO_SEC, bg=FONDO,
            anchor="w",
        )
        self.estado.pack(fill="x", padx=12, pady=(0, 10))

    def _entrar_boton(self, boton: tk.Button, color: str) -> None:
        """Efecto neón al entrar al botón: borde y texto brillan."""
        boton.config(highlightbackground=color, fg="#ffffff")

    def _salir_boton(self, boton: tk.Button, color: str) -> None:
        """Vuelve al estilo base al salir del botón."""
        boton.config(highlightbackground=BORDE, fg=color)

    def _redirigir_salida(self) -> None:
        sys.stdout = _Redireccion(self.cola)
        sys.stderr = _Redireccion(self.cola)

    def _log(self, texto: str, tag: str | None = None) -> None:
        # Colorea por contenido: ✅ verde neón, ⚠️ amarillo neón, ❌ rojo neón.
        if tag is None:
            if "✅" in texto:
                tag = "verde"
            elif "❌" in texto:
                tag = "rojo"
            elif "⚠️" in texto:
                tag = "amarillo"
            else:
                tag = "cian"
        self.log.insert("end", texto, tag)
        self.log.see("end")

    def _actualizar_botones(self) -> None:
        estado = "disabled" if self.ejecutando else "normal"
        for boton in self.botones:
            boton.config(state=estado)
        if self.ejecutando:
            self.estado.config(text=tr("  ⏳ Ejecutando… no cierres la ventana  "))
        else:
            self.estado.config(text=tr("  Listo  ·  Axiios_HTs"))

    def _configurar_atajos(self) -> None:
        """Atajos de teclado para las acciones comunes."""
        self.raiz.bind("<Control-l>", lambda e: self._accion_limpieza())
        self.raiz.bind("<Control-i>", lambda e: self._accion_inicio())
        self.raiz.bind("<Control-r>", lambda e: self._accion_rendimiento())
        self.raiz.bind("<Control-m>", lambda e: self._accion_mantenimiento())
        self.raiz.bind("<Control-a>", lambda e: self._accion_analisis())
        self.raiz.bind("<Control-v>", lambda e: self._accion_vista_previa())
        self.raiz.bind("<Control-o>", lambda e: self._accion_auto())
        self.raiz.bind("<Control-p>", lambda e: self._accion_restore())
        self.raiz.bind("<Control-d>", lambda e: self._accion_deshacer())
        self.raiz.bind("<Control-t>", lambda e: self._accion_telemetria())
        self.raiz.bind("<F5>", lambda e: self._accion_info())
        self.raiz.bind("<Escape>", lambda e: self._cerrar() if not self.ejecutando else None)

    # -------------------------------------------------- cola de salida
    def _procesar_cola(self) -> None:
        while True:
            try:
                tipo, texto = self.cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "__CONFIRMA_AUTO__":
                # La vista previa terminó: guardar para preguntar
                # cuando el hilo marque su fin (__FIN__).
                self._pendiente_auto = True
            elif tipo == "__FIN__":
                self.ejecutando = False
                self._actualizar_botones()
                self.progreso.stop()
                self.progreso.config(mode="determinate")
                self.progreso["value"] = 100
                self.texto_progreso.config(text=tr("  ✅ 100% — Completado"))
                self._log(tr("\n✅ Operación completada.\n"), "verde")
                if self._pendiente_auto:
                    self._pendiente_auto = None
                    self._preguntar_auto()
            elif tipo == "progreso":
                # Primer porcentaje real: sale del modo indeterminado
                self.progreso.stop()
                self.progreso.config(mode="determinate")
                self.progreso["value"] = texto
                self.texto_progreso.config(text=f"  ⏳ {tr('Progreso')}: {texto}%")
            elif (tipo == "salida"
                  and (texto.startswith("   Etapa ")
                       or texto.startswith("   Stage "))):
                # Muestra la etapa actual junto al porcentaje
                self.texto_progreso.config(text=f"  {texto.strip()}")
                self._log(texto, "cian")
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
        # Reinicia la barra: indeterminada hasta que llegue el primer %
        self.progreso.config(mode="indeterminate")
        self.progreso["value"] = 0
        self.progreso.start(60)
        self.texto_progreso.config(text=tr("  ⏳ Ejecutando…"))
        self._log("\n" + "━" * 58 + "\n", "cian")

        def hilo() -> None:
            try:
                funcion(*args)
            except Exception as e:  # pragma: no cover
                print(tr("❌ Error inesperado: {e}").format(e=e))
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

    def _accion_info(self) -> None:
        """Muestra la información del sistema (opción 6 del menú)."""
        from utils import info_sistema
        self._ejecutar(info_sistema)

    def _accion_perfiles(self) -> None:
        """Diálogo con los 3 perfiles: Equilibrado / Gaming / Privacidad."""
        eleccion = {"perfil": None}

        dlg = tk.Toplevel(self.raiz)
        dlg.title(tr("Perfiles de optimización"))
        dlg.configure(bg=FONDO)
        dlg.transient(self.raiz)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(
            dlg, text=tr("🎯 Elige un perfil"), font=("Segoe UI", 14, "bold"),
            fg=VERDE, bg=FONDO,
        ).pack(padx=24, pady=(16, 4))
        tk.Label(
            dlg, text=tr("Todo es reversible (Historial → 'Deshacer cambios')."),
            font=("Segoe UI", 9), fg=TEXTO_SEC, bg=FONDO,
        ).pack(padx=24, pady=(0, 10))

        def elegir(nombre: str) -> None:
            eleccion["perfil"] = nombre
            dlg.destroy()

        opciones = [
            (tr("⚖️ Equilibrado"), "equilibrado",
             tr("Telemetría y servicios obsoletos"), VERDE),
            (tr("🎮 Gaming"), "gaming",
             tr("Equilibrado + Xbox + Game DVR + Superfetch si es SSD"), AMARILLO),
            (tr("🕵️ Privacidad"), "privacidad",
             tr("Equilibrado + publicidad/historial/Widgets/Copilot"), CIAN),
        ]
        for texto, clave, descripcion, color in opciones:
            marco = tk.Frame(dlg, bg=PANEL, highlightthickness=1,
                             highlightbackground=BORDE)
            marco.pack(fill="x", padx=16, pady=4)
            btn = tk.Button(
                marco, text=texto, command=lambda c=clave: elegir(c),
                font=("Segoe UI", 11, "bold"), fg=color, bg=PANEL,
                activebackground=BORDE, activeforeground=color,
                relief="flat", bd=1, highlightthickness=0,
                width=16, height=2, cursor="hand2",
            )
            btn.bind(
                "<Enter>",
                lambda e, b=btn, c=color: self._entrar_boton(b, c),
            )
            btn.bind(
                "<Leave>",
                lambda e, b=btn, c=color: self._salir_boton(b, c),
            )
            btn.pack(side="left", padx=(8, 12), pady=8)
            tk.Label(
                marco, text=descripcion, font=("Segoe UI", 9),
                fg=TEXTO_SEC, bg=PANEL, anchor="w", justify="left", wraplength=320,
            ).pack(side="left", fill="x", expand=True, pady=8)
        tk.Button(
            dlg, text=tr("Cancelar"), command=dlg.destroy,
            font=("Segoe UI", 9), fg=GRIS, bg=FONDO,
            relief="flat", cursor="hand2",
        ).pack(pady=(6, 14))

        self.raiz.wait_window(dlg)
        perfil = eleccion["perfil"]
        if not perfil:
            return

        from modules.performance import modo_perfil_auto, nombre_perfil

        if not messagebox.askyesno(
            tr("Perfil {perfil}").format(perfil=nombre_perfil(perfil)),
            tr("¿Aplicar el perfil '{perfil}'?\n\n"
               "Se deshabilitarán servicios y tareas de telemetría.\n"
               "Todo queda registrado y se puede deshacer.").format(
                   perfil=nombre_perfil(perfil)),
        ):
            return

        crear_rp = messagebox.askyesno(
            tr("Punto de restauración"),
            tr("¿Crear un punto de restauración antes de aplicar?"),
        )

        def trabajo() -> None:
            if crear_rp:
                from utils import crear_punto_restauracion
                crear_punto_restauracion()
            modo_perfil_auto(perfil, self._logger())

        self._ejecutar(trabajo)

    def _accion_deshacer(self) -> None:
        """Restaura servicios/tareas/registro registrados en rollback.json."""
        from modules import rollback
        if not rollback.hay_cambios():
            messagebox.showinfo(
                tr("Deshacer cambios"),
                tr("No hay cambios registrados que deshacer."),
            )
            return
        if not messagebox.askyesno(
            tr("Deshacer cambios"),
            tr("Se restaurarán TODOS los cambios registrados por los\n"
               "perfiles y el selector de servicios (servicios, tareas de\n"
               "telemetría y ajustes de registro).\n\n"
               "¿Deshacer ahora?"),
        ):
            return
        from modules.performance import deshacer_cambios
        self._ejecutar(deshacer_cambios, True)  # automatico=True: ya confirmado aquí

    def _accion_telemetria(self) -> None:
        """Desactiva las tareas programadas de telemetría (reversible)."""
        if not messagebox.askyesno(
            tr("Tareas de telemetría"),
            tr("Se desactivarán las tareas programadas de telemetría\n"
               "(CEIP / Application Experience / Autochk Proxy).\n\n"
               "Es reversible con 'Deshacer cambios'.\n\n"
               "¿Continuar?"),
        ):
            return
        from modules.performance import deshabilitar_tareas_telemetria
        self._ejecutar(deshabilitar_tareas_telemetria, True)  # automatico=True

    def _accion_auto(self) -> None:
        from modules.core import verificar_permisos
        from modules.analisis import vista_previa

        if not verificar_permisos():
            messagebox.showerror(
                tr("Permisos requeridos"),
                tr("El optimizador necesita permisos de Administrador.")
            )
            return

        crear_rp = messagebox.askyesno(
            tr("Modo automático"),
            tr("Esto ejecutará TODAS las optimizaciones.\n\n"
               "Primero se mostrará una VISTA PREVIA (dry-run) en el registro.\n\n"
               "¿Crear un punto de restauración primero?"),
        )

        def etapa_vista_previa() -> None:
            # En el hilo de trabajo: el punto de restauración puede
            # tardar ~1 minuto y no debe congelar la ventana.
            if crear_rp:
                from utils import crear_punto_restauracion
                crear_punto_restauracion()
            print(tr("\n🔍 VISTA PREVIA (DRY-RUN) ANTES DE LA OPTIMIZACIÓN"))
            vista_previa(self._logger())
            # Pide confirmación en el hilo principal (ver _preguntar_auto).
            self.cola.put(("__CONFIRMA_AUTO__", None))

        self._ejecutar(etapa_vista_previa)

    def _preguntar_auto(self) -> None:
        """Tras la vista previa: confirmación explícita para ejecutar todo."""
        if not messagebox.askyesno(
            tr("Modo automático"),
            tr("La vista previa terminó (mira el registro).\n\n"
               "¿Proceder con la OPTIMIZACIÓN COMPLETA ahora?"),
        ):
            self._log(tr("⏸️ Optimización completa cancelada por el usuario.\n"), "amarillo")
            return
        from modules.core import ejecutar_auto_completo

        def etapa_completa() -> None:
            print("\n" + "━" * 58)
            print(tr("🚀 Iniciando optimización completa..."))
            ejecutar_auto_completo(self._logger())

        self._ejecutar(etapa_completa)

    def _accion_restore(self) -> None:
        if not verificar_permisos():
            messagebox.showwarning(
                tr("Permisos requeridos"),
                tr("Crear un punto de restauración necesita Administrador.\n"
                   "Reinicia el programa como Administrador."),
            )
            return
        if not messagebox.askyesno(
            tr("Crear punto de restauración"),
            tr("¿Crear un punto de restauración de Windows?\n\n"
               "Este punto te devuelve a esta configuración si algo sale mal."),
        ):
            return

        from utils import crear_punto_restauracion

        def accion() -> bool:
            return crear_punto_restauracion()

        def hilo():
            exito = False
            error = ""
            try:
                exito = accion()
            except Exception as e:
                # Precomputar el mensaje: 'e' no sobrevive al bloque
                # except y el lambda se ejecuta después (daría NameError).
                error = str(e)
            # Volver al hilo principal por seguridad del GUI
            self.raiz.after(0, lambda: self._completar_restore(exito, error))

        self.ejecutando = True
        self._actualizar_botones()
        self.progreso.config(mode="indeterminate")
        self.progreso.start(60)
        threading.Thread(target=hilo, daemon=True).start()

    def _completar_restore(self, exito: bool, error: str = "") -> None:
        self.ejecutando = False
        self._actualizar_botones()
        self.progreso.stop()
        self.progreso.config(mode="determinate")
        self.progreso["value"] = 100
        self.texto_progreso.config(
            text=tr("  ✅ Punto de restauración completado.")
            if exito else tr("  ❌ No se pudo crear el punto.")
        )
        if exito:
            messagebox.showinfo(
                tr("Punto de restauración"),
                tr("✅ Punto de restauración creado correctamente."),
            )
        else:
            detalle = tr("\n\nDetalle: {detalle}").format(detalle=error) if error else ""
            messagebox.showerror(
                tr("Punto de restauración"),
                tr("⚠️ No se pudo crear el punto de restauración.") + detalle,
            )

    def _accion_exportar(self) -> None:
        """Ejecuta el análisis de espacio y exporta el informe."""
        from modules.analisis import exportar_informe

        def accion() -> str:
            return exportar_informe()

        def hilo():
            ruta = ""
            error = ""
            try:
                ruta = accion()
            except Exception as e:
                # Precomputar el mensaje: 'e' no sobrevive al bloque
                # except y el lambda se ejecuta después (daría NameError).
                error = str(e)
            self.raiz.after(0, lambda: self._completar_exportacion(ruta, error))

        self.ejecutando = True
        self._actualizar_botones()
        self.progreso.config(mode="indeterminate")
        self.progreso.start(60)
        self.texto_progreso.config(text=tr("  ⏳ Generando informe…"))
        threading.Thread(target=hilo, daemon=True).start()

    def _completar_exportacion(self, ruta: str, error: str = "") -> None:
        self.ejecutando = False
        self._actualizar_botones()
        self.progreso.stop()
        self.progreso.config(mode="determinate")
        self.progreso["value"] = 100
        if ruta:
            self.texto_progreso.config(text=tr("  ✅ Informe generado"))
            messagebox.showinfo(
                tr("Informe exportado"),
                tr("✅ Informe guardado correctamente en:\n\n{ruta}\n\n"
                   "Puedes abrirlo con el Bloc de notas.").format(ruta=ruta),
            )
        else:
            self.texto_progreso.config(text=tr("  ❌ Error al exportar"))
            messagebox.showerror(
                tr("Error al exportar"),
                tr("⚠️ No se pudo generar el informe.\n\nDetalle: {detalle}").format(detalle=error),
            )

    def _accion_log(self) -> None:
        """Abre la carpeta de logs del día (o el archivo de hoy)."""
        from utils import BASE_DIR
        import os
        log_path = os.path.join(BASE_DIR, "logs")
        if os.path.isdir(log_path):
            os.startfile(log_path)  # pragma: no cover
            return
        # Compatibilidad con la versión anterior (un solo archivo)
        log_path = os.path.join(BASE_DIR, "optimizador.log")
        if os.path.exists(log_path):
            os.startfile(log_path)  # pragma: no cover
            return
        messagebox.showinfo(
            tr("Registro no encontrado"),
            tr("Aún no se ha creado la carpeta de logs.\n"
               "Se genera al usar cualquier acción del optimizador."),
        )

    def _logger(self):
        """Logger diferido (se crea al primer uso)."""
        if self.logger is None:
            from utils import setup_logger

            self.logger = setup_logger()
        return self.logger

    # -------------------------------------------------- idioma
    def _alternar_idioma(self) -> None:
        """Cambia español/inglés, guarda la preferencia y reconstruye la UI."""
        nuevo = "es" if get_idioma() == "en" else "en"
        try:
            self.cfg.datos["idioma"] = nuevo
            self.cfg.guardar()
        except Exception:  # pragma: no cover
            pass
        set_idioma(nuevo)
        self._reiniciar_ui()

    def _reiniciar_ui(self) -> None:
        """Destruye y recrea todos los widgets con el idioma activo.

        Se conserva el texto del log: si no, al cambiar de idioma se perdería
        la evidencia de lo que la optimización ya había hecho.
        """
        historial = ""
        if getattr(self, "log", None) is not None:
            try:
                historial = self.log.get("1.0", "end-1c")
            except Exception:  # pragma: no cover
                historial = ""
        for hijo in self.raiz.winfo_children():
            hijo.destroy()
        self._crear_widgets()
        if historial:
            try:
                self.log.insert("end", historial)
                self.log.see("end")
            except Exception:  # pragma: no cover
                pass
        if self.ejecutando:
            self.progreso.config(mode="indeterminate")
            self.progreso.start(60)
        self._actualizar_botones()

    # -------------------------------------------------- cierre
    def _cerrar(self) -> None:
        if self.ejecutando:
            if not messagebox.askyesno(
                tr("Ejecutando…"),
                tr("Hay una operación en curso. "
                   "¿Seguro que quieres salir?"),
            ):
                return
        # Guarda la geometría para "recordar_pos": true (config_gui.json)
        try:
            self.cfg.datos["ultima_geometria"] = self.raiz.geometry()
            self.cfg.guardar()
        except Exception:  # pragma: no cover
            pass
        self.raiz.destroy()


# ---------------------------------------------------------------- entrada
def main() -> None:
    # Idioma: preferencia guardada o detección automática de Windows.
    # Debe fijarse ANTES de crear la ventana (y antes de importar módulos).
    set_idioma(ConfigGUI().datos.get("idioma", "auto"))

    if os.name != "nt":
        print(tr("❌ Esta herramienta solo funciona en Windows."))
        sys.exit(1)

    # Requisito: Python de 64 bits (amd64)
    if sys.maxsize <= 2**32:
        print(tr("❌ Esta herramienta requiere Python de 64 bits."))
        print(tr("   Instala Python de 64 bits (amd64) y vuelve a intentarlo."))
        sys.exit(1)

    if not verificar_permisos():
        raiz = tk.Tk()
        raiz.withdraw()
        if messagebox.askyesno(
            tr("Administrador requerido"),
            tr("El optimizador necesita permisos de Administrador.\n\n"
               "¿Reiniciar como Administrador?"),
        ):
            reiniciar_como_admin()
        raiz.destroy()
        sys.exit(0)

    mostrar_splash()
    app = OptimizadorGUI()
    app.raiz.mainloop()


if __name__ == "__main__":
    main()
