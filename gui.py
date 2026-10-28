"""🖥️ Centro de mando del Optimizador (GUI HUD).

Ejecutar: python gui.py

La ventana es un panel HUD oscuro con:
  · barra superior (título + selector ES | EN + marca "Auto")
  · barra lateral de navegación
  · medidor circular de salud del PC (0-100)
  · cuatro tarjetas de estado en vivo y clicables
  · botón principal "Optimizar ahora" y "Deshacer último cambio"
  · registro en vivo, barra de progreso y barra de estado

Toda la lógica de sistema (limpieza, inicio, rendimiento, mantenimiento,
perfiles, deshacer) vive en `modules/`; aquí solo se conecta. Los colores
viven en `modules/hud/tema.py`.
"""
import os
import queue
import re
import sys
import threading

# Forzar UTF-8 con respaldo seguro
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import ui
from i18n import get_idioma, set_idioma, tr
from modules.config_gui import ConfigGUI
from modules.core import reiniciar_como_admin, verificar_permisos
from modules.hud import datos as hud_datos
from modules.hud.boton import BotonHUD
from modules.hud.lateral import BarraLateral
from modules.hud.medidor import MedidorSalud
from modules.hud.superior import BarraSuperior
from modules.hud.tarjeta import Tarjeta
from modules.hud.tema import (
    AMARILLO,
    BORDE,
    CIAN,
    FONDO,
    MAGENTA,
    PANEL,
    TEXTO,
    fuente,
)
from ui import ruta_recurso, mostrar_splash

_PATRON_PROGRESO = re.compile(r"Progreso:\s*(\d+)\s*%")

# Tamaño de la ventana del centro de mando (el mínimo deja sitio a las
# cuatro tarjetas sin recortar el medidor).
_ANCHO_INICIAL = "1000x660"
_MINIMO = (900, 620)

# Refresco de las tarjetas de RAM/CPU, en milisegundos.
_REFRESCO_MS = 1500


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
class CentroDeMando:
    """Ventana principal: panel HUD con datos reales del equipo."""

    def __init__(self) -> None:
        self.raiz = tk.Tk()
        self.raiz.title(f"{ui.PRODUCTO} — {ui.PROVEEDOR}")
        self.raiz.geometry(_ANCHO_INICIAL)
        self.raiz.minsize(*_MINIMO)
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
        self.instantanea = hud_datos.Instantanea()
        self.sondeo = hud_datos.Sondeo()
        self._pendiente_auto = None  # confirmación tras la vista previa

        self._crear_widgets()
        self._redirigir_salida()
        self._configurar_atajos()
        self.raiz.after(100, self._procesar_cola)
        self.raiz.after(_REFRESCO_MS, self._refrescar)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cerrar)

        self.sondeo.iniciar()
        self._analizar_sistema()

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
        self.barra_superior = BarraSuperior(
            self.raiz,
            tr("Optimizador // Windows 11"),
            get_idioma(),
            self._idioma_automatico(),
            self._cambiar_idioma,
        )
        self.barra_superior.pack(fill="x")

        cuerpo = tk.Frame(self.raiz, bg=FONDO)
        cuerpo.pack(fill="both", expand=True)

        self.barra_lateral = BarraLateral(cuerpo, self._entradas_laterales())
        self.barra_lateral.pack(side="left", fill="y")
        self.barra_lateral.seleccionar("panel")

        centro = tk.Frame(cuerpo, bg=FONDO)
        centro.pack(side="left", fill="both", expand=True, padx=14, pady=12)

        self._crear_panel_central(centro)
        self._crear_botones(centro)
        self._crear_progreso(centro)
        self._crear_registro(centro)

        self._pintar()

    def _entradas_laterales(self) -> list:
        """Entradas de la barra lateral: secciones y acciones."""
        return [
            ("panel", f"◈  {tr('Panel')}", self._ir_panel, TEXTO),
            (f"SECCION:{tr('Optimizar')}", "", None, ""),
            ("completa", f"🚀  {tr('Optimizar todo')}",
             self._accion_auto, TEXTO),
            ("limpieza", f"🧹  {tr('Limpieza')}", self._accion_limpieza, TEXTO),
            ("inicio", f"🚀  {tr('Inicio')}", self._accion_inicio, TEXTO),
            ("rendimiento", f"⚡  {tr('Rendimiento')}",
             self._accion_rendimiento, TEXTO),
            ("mantenimiento", f"🔧  {tr('Mantenimiento')}",
             self._accion_mantenimiento, TEXTO),
            ("perfiles", f"🎯  {tr('Perfiles')}", self._accion_perfiles, TEXTO),
            (f"SECCION:{tr('Informes')}", "", None, ""),
            ("vista_previa", f"🔍  {tr('Vista previa')}",
             self._accion_vista_previa, TEXTO),
            ("analisis", f"📊  {tr('Análisis')}", self._accion_analisis, TEXTO),
            ("exportar", f"📋  {tr('Exportar informe')}",
             self._accion_exportar, TEXTO),
            (f"SECCION:{tr('Sistema')}", "", None, ""),
            ("restauracion", f"🛡️  {tr('Restauración')}",
             self._accion_restore, TEXTO),
            ("telemetria", f"📡  {tr('Telemetría')}",
             self._accion_telemetria, TEXTO),
            ("informacion", f"ℹ️  {tr('Información')}", self._accion_info, TEXTO),
            ("registro", f"📄  {tr('Registro')}", self._accion_log, TEXTO),
            ("deshacer", f"⏪  {tr('Deshacer')}", self._accion_deshacer, MAGENTA),
        ]

    def _crear_panel_central(self, centro: tk.Misc) -> None:
        """Medidor circular a la izquierda y rejilla 2x2 de tarjetas."""
        fila = tk.Frame(centro, bg=FONDO)
        fila.pack(fill="x")

        self.medidor = MedidorSalud(fila, 170, tr("Salud del PC"))
        self.medidor.pack(side="left", padx=(0, 14))

        rejilla = tk.Frame(fila, bg=FONDO)
        rejilla.pack(side="left", fill="both", expand=True)
        for columna in (0, 1):
            rejilla.columnconfigure(columna, weight=1, uniform="tarjetas")
        for indice_fila in (0, 1):
            rejilla.rowconfigure(indice_fila, weight=1, uniform="tarjetas")

        self.tarjeta_disco = Tarjeta(
            rejilla, tr("Disco"), CIAN, self._accion_limpieza)
        self.tarjeta_inicio = Tarjeta(
            rejilla, tr("Programas de inicio"), MAGENTA, self._accion_inicio)
        self.tarjeta_recursos = Tarjeta(
            rejilla, tr("RAM / CPU"), CIAN, self._accion_rendimiento)
        self.tarjeta_mantenimiento = Tarjeta(
            rejilla, tr("Mantenimiento"), AMARILLO, self._accion_mantenimiento)

        for indice, tarjeta in enumerate((
            self.tarjeta_disco, self.tarjeta_inicio,
            self.tarjeta_recursos, self.tarjeta_mantenimiento,
        )):
            fila_t, columna_t = divmod(indice, 2)
            tarjeta.grid(row=fila_t, column=columna_t, sticky="nsew",
                         padx=5, pady=5)

    def _crear_botones(self, centro: tk.Misc) -> None:
        fila = tk.Frame(centro, bg=FONDO)
        fila.pack(fill="x", pady=(10, 6))

        self.boton_principal = BotonHUD(
            fila, f"⚡ {tr('Optimizar ahora')}", self._accion_optimizar)
        self.boton_principal.pack(side="left")

        self.boton_deshacer = BotonHUD(
            fila, f"⏪ {tr('Deshacer último cambio')}",
            self._accion_deshacer, variante="secundario")
        self.boton_deshacer.pack(side="left", padx=(10, 0))

        self.botones = [self.boton_principal, self.boton_deshacer]

    def _crear_progreso(self, centro: tk.Misc) -> None:
        estilo = ttk.Style(self.raiz)
        estilo.theme_use("clam")
        estilo.configure(
            "Ciber.Horizontal.TProgressbar",
            troughcolor="#050508", background=CIAN,
            bordercolor=BORDE, lightcolor=CIAN, darkcolor=CIAN,
        )
        self.progreso = ttk.Progressbar(
            centro, style="Ciber.Horizontal.TProgressbar",
            mode="determinate", maximum=100, value=0,
        )
        self.progreso.pack(fill="x", pady=(0, 2))

        self.texto_progreso = tk.Label(
            centro, text="", font=fuente(9), fg=CIAN, bg=FONDO, anchor="w",
        )
        self.texto_progreso.pack(fill="x", pady=(0, 2))

        self.estado = tk.Label(
            centro, text=tr("  Listo  ·  Axiios_HTs"),
            font=fuente(9), fg=TEXTO, bg=FONDO, anchor="w",
        )
        self.estado.pack(fill="x")

    def _crear_registro(self, centro: tk.Misc) -> None:
        marco = tk.Frame(centro, bg=FONDO)
        marco.pack(fill="both", expand=True, pady=(8, 0))

        self.log = scrolledtext.ScrolledText(
            marco, bg="#050508", fg=TEXTO, height=8,
            font=fuente(9), insertbackground=TEXTO,
            relief="flat", bd=1, highlightthickness=1,
            highlightbackground=BORDE, wrap="word",
        )
        self.log.pack(fill="both", expand=True)
        # ScrolledText usa un Scrollbar CLÁSICO (no ttk): el estilo ttk no
        # le llega y por defecto sale gris claro, rompiendo el HUD.
        try:
            self.log.vbar.configure(
                bg=BORDE, troughcolor=FONDO, activebackground=CIAN,
                highlightthickness=0, relief="flat", width=10,
            )
        except Exception:  # pragma: no cover - variante sin barra propia
            pass
        self.log.tag_configure("verde", foreground="#00FF9D")
        self.log.tag_configure("rojo", foreground=MAGENTA)
        self.log.tag_configure("amarillo", foreground=AMARILLO)
        self.log.tag_configure("cian", foreground=CIAN)
        # Al reconstruir la UI (cambio de idioma) no se repite el saludo:
        # se restaura el historial y cada cambio añadiría una línea más.
        if not getattr(self, "_reiniciando", False):
            self._log(tr("✅ Listo. Elige una opción para optimizar.\n"), "cian")

    # -------------------------------------------------- datos
    def _idioma_automatico(self) -> bool:
        """True si el idioma guardado es 'auto' (detección de Windows)."""
        return self.cfg.datos.get("idioma", "auto") == "auto"

    def _analizar_sistema(self) -> None:
        """Mide disco, inicio y mantenimiento en un hilo aparte."""
        def trabajo() -> None:
            try:
                instantanea = hud_datos.recolectar()
            except Exception as e:  # pragma: no cover - equipo atípico
                self.cola.put(("salida", tr(
                    "❌ No se pudo analizar el sistema: {e}").format(e=e)))
                return
            self.cola.put(("instantanea", instantanea))

        threading.Thread(target=trabajo, daemon=True).start()

    def _refrescar(self) -> None:
        """Refresco periódico de RAM/CPU y del medidor de salud."""
        self._pintar()
        self.raiz.after(_REFRESCO_MS, self._refrescar)

    def _pintar(self) -> None:
        """Vuelca la instantánea y el sondeo en tarjetas y medidor."""
        instantanea = self.instantanea
        ram_cpu = self.sondeo.ultimo
        ram = ram_cpu[0] if ram_cpu else None
        cpu = ram_cpu[1] if ram_cpu else None

        # --- Disco ---
        if instantanea.gb is None:
            self.tarjeta_disco.set_analizando(True)
        else:
            self.tarjeta_disco.set_analizando(False)
            self.tarjeta_disco.set_valor(f"{instantanea.gb:.1f} GB")
            self.tarjeta_disco.set_detalle(tr("recuperables"))

        # --- Inicio ---
        if instantanea.inicio is None:
            self.tarjeta_inicio.set_analizando(True)
        else:
            self.tarjeta_inicio.set_analizando(False)
            self.tarjeta_inicio.set_valor(str(instantanea.inicio))
            self.tarjeta_inicio.set_detalle(tr("arrancan con Windows"))

        # --- RAM / CPU ---
        if ram is None or cpu is None:
            if hud_datos.hay_psutil():
                # psutil está, pero aún no hay primera medida.
                self.tarjeta_recursos.set_analizando(True)
            else:
                self.tarjeta_recursos.set_analizando(False)
                self.tarjeta_recursos.set_valor(tr("No disponible"))
                self.tarjeta_recursos.set_detalle(tr("psutil no instalado"))
        else:
            self.tarjeta_recursos.set_analizando(False)
            self.tarjeta_recursos.set_valor(f"{ram:.0f}%  ·  {cpu:.0f}%")
            self.tarjeta_recursos.set_detalle(tr("uso en tiempo real"))

        # --- Mantenimiento ---
        dias = instantanea.dias
        if not instantanea.completa:
            self.tarjeta_mantenimiento.set_analizando(True)
        elif dias is None:
            self.tarjeta_mantenimiento.set_analizando(False)
            self.tarjeta_mantenimiento.set_valor(tr("Sin registros"))
            self.tarjeta_mantenimiento.set_detalle(tr("último análisis"))
        elif dias == 0:
            self.tarjeta_mantenimiento.set_analizando(False)
            self.tarjeta_mantenimiento.set_valor(tr("Hoy"))
            self.tarjeta_mantenimiento.set_detalle(tr("último análisis"))
        else:
            self.tarjeta_mantenimiento.set_analizando(False)
            self.tarjeta_mantenimiento.set_valor(f"{dias} {tr('días')}")
            self.tarjeta_mantenimiento.set_detalle(tr("último análisis"))

        # --- Medidor ---
        salud = hud_datos.calcular_salud(
            instantanea.gb, instantanea.inicio, ram, dias)
        self.medidor.set_valor(salud)

    # -------------------------------------------------- utilidades
    def _redirigir_salida(self) -> None:
        sys.stdout = _Redireccion(self.cola)
        sys.stderr = _Redireccion(self.cola)

    def _log(self, texto: str, tag: str | None = None) -> None:
        # Colorea por contenido: ✅ verde, ⚠️ amarillo, ❌ magenta.
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
        self.raiz.bind("<Control-o>", lambda e: self._accion_optimizar())
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
                # Los datos han podido cambiar: se vuelve a medir.
                self._analizar_sistema()
                if self._pendiente_auto:
                    self._pendiente_auto = None
                    self._preguntar_auto()
            elif tipo == "instantanea":
                self.instantanea = texto
                self._pintar()
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
    def _ir_panel(self) -> None:
        """Vuelve al panel: vuelve a medir el equipo."""
        self._analizar_sistema()

    def _accion_auto(self) -> None:
        """Optimización completa: vista previa (dry-run) y confirmación.

        Se conserva el flujo de la versión anterior: primero se enseña
        qué se haría y solo después se pregunta si se procede.
        """
        from modules.analisis import vista_previa

        if not verificar_permisos():
            if messagebox.askyesno(
                tr("Permisos requeridos"),
                tr("El optimizador necesita permisos de Administrador.\n\n"
                   "¿Reiniciar como Administrador?"),
            ):
                reiniciar_como_admin()
                self.raiz.destroy()
                sys.exit(0)
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
            self._log(tr("⏸️ Optimización completa cancelada por el usuario.\n"),
                      "amarillo")
            return
        from modules.core import ejecutar_auto_completo

        def etapa_completa() -> None:
            print("\n" + "━" * 58)
            print(tr("🚀 Iniciando optimización completa..."))
            ejecutar_auto_completo(self._logger())

        self._ejecutar(etapa_completa)

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
        """Muestra la información del sistema."""
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
            dlg, text=f"🎯 {tr('Elige un perfil')}", font=fuente(13, True),
            fg=CIAN, bg=FONDO,
        ).pack(padx=24, pady=(16, 4))
        tk.Label(
            dlg, text=tr("Todo es reversible (Historial → 'Deshacer cambios')."),
            font=fuente(9), fg=TEXTO, bg=FONDO,
        ).pack(padx=24, pady=(0, 10))

        def elegir(nombre: str) -> None:
            eleccion["perfil"] = nombre
            dlg.destroy()

        opciones = [
            (f"⚖️ {tr('Equilibrado')}", "equilibrado",
             tr("Telemetría y servicios obsoletos"), CIAN),
            (f"🎮 {tr('Gaming')}", "gaming",
             tr("Equilibrado + Xbox + Game DVR + Superfetch si es SSD"), AMARILLO),
            (f"🕵️ {tr('Privacidad')}", "privacidad",
             tr("Equilibrado + publicidad/historial/Widgets/Copilot"), MAGENTA),
        ]
        for texto, clave, descripcion, color in opciones:
            marco = tk.Frame(dlg, bg=PANEL, highlightthickness=1,
                             highlightbackground=BORDE)
            marco.pack(fill="x", padx=16, pady=4)
            boton = tk.Button(
                marco, text=texto, command=lambda c=clave: elegir(c),
                font=fuente(10, True), fg=color, bg=PANEL,
                activebackground=BORDE, activeforeground=color,
                relief="flat", bd=1, highlightthickness=0,
                width=16, height=2, cursor="hand2",
            )
            boton.pack(side="left", padx=(8, 12), pady=8)
            tk.Label(
                marco, text=descripcion, font=fuente(9),
                fg=TEXTO, bg=PANEL, anchor="w", justify="left", wraplength=320,
            ).pack(side="left", fill="x", expand=True, pady=8)
        tk.Button(
            dlg, text=tr("Cancelar"), command=dlg.destroy,
            font=fuente(9), fg=TEXTO, bg=FONDO,
            relief="flat", cursor="hand2",
        ).pack(pady=(6, 14))

        self.raiz.wait_window(dlg)
        perfil = eleccion["perfil"]
        if not perfil:
            return
        self._aplicar_perfil(perfil)

    def _aplicar_perfil(self, perfil: str) -> None:
        """Aplica un perfil dejando el punto de restauración hecho."""
        from modules.performance import modo_perfil_auto, nombre_perfil

        if not messagebox.askyesno(
            tr("Perfil {perfil}").format(perfil=nombre_perfil(perfil)),
            tr("¿Aplicar el perfil '{perfil}'?\n\n"
               "Se deshabilitarán servicios y tareas de telemetría.\n"
               "Todo queda registrado y se puede deshacer.").format(
                   perfil=nombre_perfil(perfil)),
        ):
            return

        try:
            self.cfg.datos["perfil_activo"] = perfil
            self.cfg.guardar()
        except Exception:  # pragma: no cover
            pass

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

    def _accion_optimizar(self) -> None:
        """Botón principal: punto de reversión + perfil activo."""
        if not verificar_permisos():
            if messagebox.askyesno(
                tr("Permisos requeridos"),
                tr("El optimizador necesita permisos de Administrador.\n\n"
                   "¿Reiniciar como Administrador?"),
            ):
                reiniciar_como_admin()
                self.raiz.destroy()
                sys.exit(0)
            return

        from modules.performance import modo_perfil_auto, nombre_perfil

        perfil = self.cfg.datos.get("perfil_activo", "equilibrado")
        if perfil not in ("equilibrado", "gaming", "privacidad"):
            perfil = "equilibrado"

        if not messagebox.askyesno(
            f"⚡ {tr('Optimizar ahora')}",
            tr("Se aplicará el perfil '{perfil}'.\n"
               "Antes de cambiar nada se crea un punto de restauración.\n\n"
               "¿Continuar?").format(perfil=nombre_perfil(perfil)),
        ):
            return

        self._log(tr("\n⚡ Optimización con el perfil '{perfil}'…\n").format(
            perfil=nombre_perfil(perfil)), "cian")

        def trabajo() -> None:
            from utils import crear_punto_restauracion

            if not crear_punto_restauracion():
                # Sin punto de reversión NO se toca nada (regla de la spec).
                print(tr("\n⚠️ No se pudo crear el punto de restauración."))
                print(tr("   No se aplicó ningún cambio."))
                return
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
        """Tareas de telemetría y políticas de privacidad (reversible)."""
        if not messagebox.askyesno(
            tr("Telemetría"),
            tr("Se desactivarán las tareas programadas de telemetría\n"
               "(CEIP / Feedback / WER / SQM / diagnóstico de disco)\n"
               "y se aplicarán las políticas de privacidad: diagnóstico\n"
               "mínimo, sin seguimiento de apps ni apps sugeridas.\n\n"
               "No rompe notificaciones, ubicación, portapapeles ni impresión.\n"
               "Es reversible con 'Deshacer cambios'.\n\n"
               "¿Continuar?"),
        ):
            return
        from modules.performance import aplicar_telemetria
        self._ejecutar(aplicar_telemetria, True)  # automatico=True

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

        def hilo():
            exito = False
            error = ""
            try:
                exito = crear_punto_restauracion()
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

        def hilo():
            ruta = ""
            error = ""
            try:
                ruta = exportar_informe()
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
    def _cambiar_idioma(self, idioma: str) -> None:
        """Fija el idioma elegido a mano, lo guarda y reconstruye la UI."""
        try:
            self.cfg.datos["idioma"] = idioma
            self.cfg.guardar()
        except Exception:  # pragma: no cover
            pass
        set_idioma(idioma)
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
        self._reiniciando = True
        try:
            self._crear_widgets()
        finally:
            self._reiniciando = False
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
        self.sondeo.detener()
        self.raiz.destroy()


# Nombre anterior: se conserva por compatibilidad con scripts externos.
OptimizadorGUI = CentroDeMando


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
    app = CentroDeMando()
    app.raiz.mainloop()


if __name__ == "__main__":
    main()
