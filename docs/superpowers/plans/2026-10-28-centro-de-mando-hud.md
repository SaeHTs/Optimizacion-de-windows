# Centro de mando HUD — Plan de implementación

> **Para trabajadores agentes:** SUB-SKILL REQUERIDA: usa `executing-plans` para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Meta:** rediseñar la pantalla principal del Optimizador como un centro de mando HUD oscuro con medidor circular de salud, tarjetas de estado en vivo y botón principal de optimización, sin romper ninguna función existente.

**Arquitectura:** Tkinter sigue siendo la librería (no se cambia). La interfaz se parte en componentes reutilizables dentro del paquete nuevo `modules/hud/`; `gui.py` queda como orquestador. La paleta vive solo en `modules/hud/tema.py`. Los datos son reales: reutiliza `modules/analisis.py`, `modules/startup.py` y `modules/rollback.py`, más `psutil` (ya declarado en `requirements.txt`).

**Stack:** Python 3.10+, Tkinter/ttk, psutil (opcional, ya en requirements).

**Especificación:** la del autor (mensaje del 28/10/2026), resumida en la conversación de la sesión `20261028-1008`.

## Restricciones Globales

- Idioma de trabajo: español. Código, identificadores y commits en inglés técnico.
- Bilingüe ES/EN obligatorio: todo texto nuevo pasa por `tr()` y se añade a `locales/en*.json`.
- No cambiar de librería gráfica. No añadir dependencias nuevas.
- No modificar la lógica de limpieza, inicio, rendimiento, mantenimiento, perfiles ni deshacer: solo conectarla.
- Sin datos de la máquina en el repositorio (rutas genéricas, sin nombres de usuario).
- Nada se publica en GitHub sin visto bueno explícito del autor.
- Paleta: `#0A0A12` fondo, `#0F0F1C`/`#0D0D19` barras, `#12121F` paneles, `#24243A` bordes, `#00F0FF` cian, `#FF2BD6` magenta, `#FFE600` amarillo, `#E6E8F5` texto, `#8A8FA8` texto secundario.
- Fuente monoespaciada: Consolas (JetBrains Mono y Share Tech Mono no están instaladas en el equipo).

## Enfoque de revisión

Modos de fallo que la especificación implica y que ninguna prueba de tarea cubre por sí sola:

1. **Ventana redimensionada a lo mínimo** (900×620): la rejilla de tarjetas y el log deben seguir legibles, sin widgets cortados.
2. **Cambio de idioma con una operación en curso**: la UI se reconstruye y el log no puede perderse ni duplicarse.
3. **Deshacer sin cambios registrados**: debe informar con un mensaje claro, nunca fallar ni cerrar la app.
4. **`psutil` ausente** (dependencia opcional): las tarjetas de RAM/CPU muestran "No disponible" y el resto del HUD funciona.
5. **Ejecución sin Administrador**: el HUD abre, avisa en la barra superior y las acciones que necesitan UAC piden elevación en vez de fallar en silencio.

Cada una se fija con una prueba en la tarea que posee el código (Tareas 5 y 7).

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `modules/hud/__init__.py` | Paquete; exporta los nombres públicos |
| `modules/hud/tema.py` | Paleta, fuentes, `color_salud()` |
| `modules/hud/datos.py` | Instantánea real del sistema + fórmula de salud + sondeo RAM/CPU |
| `modules/hud/medidor.py` | `MedidorSalud` (Canvas, anillo animado) |
| `modules/hud/tarjeta.py` | `Tarjeta` (valor, estado "Analizando…", clic) |
| `modules/hud/boton.py` | `BotonHUD` (principal / secundario) |
| `modules/hud/lateral.py` | `BarraLateral` (entradas + selección activa) |
| `modules/hud/superior.py` | `BarraSuperior` (título, ES\|EN, "Auto") |
| `gui.py` | `CentroDeMando`: orquesta widgets, hilos, acciones |
| `locales/en.hud.json` | Traducciones nuevas |
| `test_hud.py` | Pruebas de la fórmula, el tema y el escaneo de último mantenimiento |
| `test_i18n.py` | Extender el escaneo a `modules/**` |

---

### Tarea 1: Tema centralizado

**Archivos:**
- Crear: `modules/hud/__init__.py`, `modules/hud/tema.py`
- Prueba: `test_hud.py`

**Interfaces:**
- Produce: `FONDO, BARRA, LATERAL, PANEL, BORDE, CIAN, MAGENTA, AMARILLO, TEXTO, TEXTO_SEC` (str hex); `FUENTE_MONO: str`; `fuente(tamano: int, negrita: bool = False) -> tuple`; `color_salud(valor: int) -> str`.

- [x] **Paso 1: Escribe las pruebas que fallen**

```python
def test_color_salud_por_tramos():
    from modules.hud.tema import AMARILLO, CIAN, MAGENTA, color_salud
    assert color_salud(10) == MAGENTA
    assert color_salud(39) == MAGENTA
    assert color_salud(40) == AMARILLO
    assert color_salud(70) == AMARILLO
    assert color_salud(71) == CIAN
    assert color_salud(100) == CIAN


def test_la_paleta_no_tiene_colores_sueltos():
    from modules.hud import tema
    assert tema.FONDO == "#0A0A12"
    assert tema.CIAN == "#00F0FF"
    assert tema.MAGENTA == "#FF2BD6"
    assert tema.AMARILLO == "#FFE600"
    assert tema.TEXTO == "#E6E8F5"
    assert tema.TEXTO_SEC == "#8A8FA8"
```

- [x] **Paso 2: Ejecutar y ver que falla**

`python -m pytest test_hud.py -v` → FALLA con `ModuleNotFoundError: modules.hud`.

- [x] **Paso 3: Implementar `tema.py`**

Constantes con los valores exactos de la tabla de restricciones. `color_salud(valor)` devuelve `MAGENTA` si `valor < 40`, `AMARILLO` si `valor <= 70`, `CIAN` si es mayor. `FUENTE_MONO = "Consolas"` con detección previa por `tkinter.font.families()` y respaldo a `Courier New`. `fuente(tamano, negrita=False)` devuelve `(FUENTE_MONO, tamano, "bold")` o `(FUENTE_MONO, tamano)`.

- [x] **Paso 4: Ejecutar las pruebas → PASS**

- [x] **Paso 5: Commit** — `feat(hud): add centralized HUD theme`

---

### Tarea 2: Fórmula de salud

**Archivos:**
- Crear: `modules/hud/datos.py` (solo funciones puras en esta tarea)
- Prueba: `test_hud.py`

**Interfaces:**
- Produce: `penalizacion_disco(gb: float) -> int`; `penalizacion_inicio(entradas: int) -> int`; `penalizacion_ram(pct: float) -> int`; `penalizacion_mantenimiento(dias: int | None) -> int`; `calcular_salud(gb: float | None, entradas: int | None, ram_pct: float | None, dias: int | None) -> int`.

- [x] **Paso 1: Pruebas que fallen**

```python
def test_penalizacion_disco_tope_30():
    from modules.hud.datos import penalizacion_disco
    assert penalizacion_disco(0) == 0
    assert penalizacion_disco(2.5) == 5
    assert penalizacion_disco(40) == 30


def test_penalizacion_inicio_tope_20():
    from modules.hud.datos import penalizacion_inicio
    assert penalizacion_inicio(0) == 0
    assert penalizacion_inicio(2) == 10
    assert penalizacion_inicio(9) == 20


def test_penalizacion_ram_escala_50_a_90():
    from modules.hud.datos import penalizacion_ram
    assert penalizacion_ram(50) == 0
    assert penalizacion_ram(30) == 0
    assert penalizacion_ram(70) == 12
    assert penalizacion_ram(90) == 25
    assert penalizacion_ram(100) == 25


def test_penalizacion_mantenimiento():
    from modules.hud.datos import penalizacion_mantenimiento
    assert penalizacion_mantenimiento(None) == 0
    assert penalizacion_mantenimiento(0) == 0
    assert penalizacion_mantenimiento(15) == 12
    assert penalizacion_mantenimiento(60) == 25
    assert penalizacion_mantenimiento(400) == 25


def test_calcular_salud_resta_y_acota():
    from modules.hud.datos import calcular_salud
    assert calcular_salud(0, 0, 40, 0) == 100
    assert calcular_salud(40, 9, 100, 400) == 0
    assert calcular_salud(5, 2, 70, 15) == 100 - (10 + 10 + 12 + 12)
```

- [x] **Paso 2: Ejecutar y ver que falla** (`ImportError: penalizacion_disco`).

- [x] **Paso 3: Implementar las cinco funciones**

`penalizacion_disco = min(30, int(gb * 2))` con `gb <= 0 → 0`.
`penalizacion_inicio = min(20, entradas * 5)`.
`penalizacion_ram`: `0` por debajo de 50 %; interpolación lineal 50→0, 90→25; tope 25.
`penalizacion_mantenimiento`: `None → 0`; `dias * 25 / 45` redondeado, con tope 25.
`calcular_salud` suma las cuatro y devuelve `max(0, min(100, 100 - total))`. Un `None` en `gb` o `entradas` cuenta como 0.

- [x] **Paso 4: Ejecutar → PASS**

- [x] **Paso 5: Commit** — `feat(hud): add documented health score formula`

---

### Tarea 3: Recolección de datos reales

**Archivos:**
- Modificar: `modules/hud/datos.py`
- Prueba: `test_hud.py`

**Interfaces:**
- Produce: `dias_desde_ultimo_log(base_logs: str | None = None) -> int | None`; `escanear_disco() -> float` (GB); `contar_inicio() -> int`; `leer_ram_cpu() -> tuple[float, float] | None`; clase `Sondeo(intervalo: float = 1.5)` con `iniciar()`, `detener()`, atributo `ultimo: tuple[float, float] | None`; dataclass `Instantanea` con `gb`, `inicio`, `ram`, `cpu`, `dias`, `salud` y `completa: bool`.

- [x] **Paso 1: Prueba que falle (último mantenimiento)**

```python
def test_dias_desde_ultimo_log(tmp_path):
    from datetime import datetime, timedelta
    from modules.hud.datos import dias_desde_ultimo_log
    assert dias_desde_ultimo_log(str(tmp_path)) is None
    hace = datetime.now() - timedelta(days=7)
    (tmp_path / f"optimizador-{hace:%Y-%m-%d}.log").write_text("x", encoding="utf-8")
    assert dias_desde_ultimo_log(str(tmp_path)) == 7
```

- [x] **Paso 2: Ejecutar → FALLA**

- [x] **Paso 3: Implementar**

- `dias_desde_ultimo_log`: lee `logs/optimizador-AAAA-MM-DD.log` (por defecto `utils.LOG_DIR`), toma la fecha más reciente y devuelve la diferencia en días (`0` si es hoy). Sin ficheros → `None`.
- `escanear_disco`: reutiliza `analisis.tamano_recursivo`, `tamano_papelera`, `tamano_cache_firefox` sobre `config.RUTAS_TEMPORALES` + prefetch + caché de Update/entrega + navegadores; devuelve GB.
- `contar_inicio`: reutiliza el mismo recorrido de `test_efectividad._entradas_deshabilitables` (prefijos de `config.ENTRADAS_INICIO_AUTO`, claves de `modules.startup.CLAVES_INICIO`). Se mueve esa lógica a `datos.py` y `test_efectividad.py` la importa desde ahí para no duplicar.
- `leer_ram_cpu`: `psutil.virtual_memory().percent` y `psutil.cpu_percent(interval=None)`. Sin psutil → `None`.
- `Sondeo`: hilo `daemon` que cada `intervalo` segundos actualiza `ultimo`; `detener()` usa un `threading.Event`.

- [x] **Paso 4: Ejecutar las pruebas → PASS**

- [x] **Paso 5: Commit** — `feat(hud): collect real system data for the dashboard`

---

### Tarea 4: Widgets base (medidor, tarjeta, botón)

**Archivos:**
- Crear: `modules/hud/medidor.py`, `modules/hud/tarjeta.py`, `modules/hud/boton.py`
- Prueba: `test_hud.py` (prueba de construcción con Tk real)

**Interfaces:**
- Produce: `MedidorSalud(parent, diametro: int = 170)` con `.set_valor(valor: int, animar: bool = True)`; `Tarjeta(parent, titulo: str, color: str)` con `.set_valor(texto: str)`, `.set_detalle(texto: str)`, `.set_analizando(bool)`, `.al_clic(callback)`; `BotonHUD(parent, texto: str, comando, variante: str = "principal")` con `.configurar_texto(texto: str)`.

- [x] **Paso 1: Prueba de humo**

```python
def test_los_widgets_se_construyen():
    import tkinter as tk
    from modules.hud.boton import BotonHUD
    from modules.hud.medidor import MedidorSalud
    from modules.hud.tarjeta import Tarjeta
    raiz = tk.Tk()
    raiz.withdraw()
    try:
        medidor = MedidorSalud(raiz)
        medidor.set_valor(72, animar=False)
        assert medidor.valor == 72
        tarjeta = Tarjeta(raiz, "Disco", "#00F0FF")
        tarjeta.set_analizando(True)
        tarjeta.set_valor("12,4 GB")
        boton = BotonHUD(raiz, "Optimizar ahora", lambda: None)
        assert boton.cget("text") == "Optimizar ahora"
    finally:
        raiz.destroy()
```

- [x] **Paso 2: Ejecutar → FALLA** (`ModuleNotFoundError`).

- [x] **Paso 3: Implementar**

- `MedidorSalud` es un `tk.Canvas` sin borde, fondo `PANEL`. Anillo con dos `create_arc` concéntricos: exterior atenuado (`#0f3a44`) y principal del color de `color_salud`. Arranca en `start=90, extent=-359.9`. Texto central con `fuente(34, True)` para el número y `fuente(9)` para "Salud del PC". `set_valor` anima con `after(16, ...)` en ~20 pasos hasta el objetivo; `animar=False` lo fija de golpe.
- `Tarjeta` es un `tk.Frame` con `highlightthickness=1`, `highlightbackground=BORDE`, y un `tk.Frame` superior de 3 px con el color de categoría. Título en `fuente(9)` color `TEXTO_SEC`; valor en `fuente(20, True)`; detalle en `fuente(9)`. `set_analizando(True)` muestra "Analizando…" en `TEXTO_SEC`. El clic se enlaza en el frame y en todos los hijos (`bind` recursivo).
- `BotonHUD` deriva de `tk.Button`: variante `"principal"` (fondo `CIAN`, texto `#0A0A12`), `"secundario"` (fondo `PANEL`, texto `MAGENTA`, borde `MAGENTA`). Efecto hover cambiando `bg` a un tono más claro.

- [x] **Paso 4: Ejecutar → PASS**

- [x] **Paso 5: Commit** — `feat(hud): add gauge, card and button widgets`

---

### Tarea 5: Barra lateral y barra superior

**Archivos:**
- Crear: `modules/hud/lateral.py`, `modules/hud/superior.py`
- Prueba: `test_hud.py`

**Interfaces:**
- Produce: `BarraLateral(parent, entradas: list[tuple[str, str, object, str]])` donde cada entrada es `(clave, texto, comando, color)`, y `"SECCION:Texto"` como clave especial para un separador de sección; métodos `.seleccionar(clave: str)`, `.marcar_deshacer(habilitado: bool)`. `BarraSuperior(parent, titulo: str, idioma: str, automatico: bool, al_cambiar_idioma)` con `.actualizar(idioma: str, automatico: bool)`.

- [x] **Paso 1: Pruebas que fallen**

```python
def test_la_barra_lateral_marca_el_activo():
    import tkinter as tk
    from modules.hud.lateral import BarraLateral
    raiz = tk.Tk()
    raiz.withdraw()
    try:
        barra = BarraLateral(raiz, [
            ("panel", "Panel", lambda: None, "#00F0FF"),
            ("SECCION:Informes", "", None, ""),
            ("limpieza", "Limpieza", lambda: None, "#E6E8F5"),
        ])
        barra.seleccionar("limpieza")
        assert barra.activo == "limpieza"
        barra.seleccionar("panel")
        assert barra.activo == "panel"
    finally:
        raiz.destroy()


def test_la_barra_superior_muestra_auto():
    import tkinter as tk
    from modules.hud.superior import BarraSuperior
    raiz = tk.Tk()
    raiz.withdraw()
    try:
        barra = BarraSuperior(raiz, "Optimizador // Windows 11", "es", True, lambda: None)
        assert "AUTO" in barra.texto_auto.upper()
        barra.actualizar("en", False)
        assert barra.texto_auto == ""
    finally:
        raiz.destroy()
```

- [x] **Paso 2: Ejecutar → FALLA**

- [x] **Paso 3: Implementar**

- `BarraLateral`: `tk.Frame` de ancho fijo 150 (`pack_propagate(False)`), fondo `LATERAL`, borde derecho de 1 px. Cada entrada es un `tk.Label` con `cursor="hand2"`, padding 8×6; el activo lleva un `tk.Frame` de 3 px a la izquierda en cian y el texto en `TEXTO`. Las claves `SECCION:…` crean una etiqueta pequeña en `TEXTO_SEC` con mayúsculas.
- `BarraSuperior`: `tk.Frame` de 36 px de alto, fondo `BARRA`. Título a la izquierda en `fuente(10, True)`. A la derecha dos `tk.Label` clicables "ES" y "EN" (el activo en `CIAN`, el otro en `TEXTO_SEC`, separados por "|"), más `texto_auto` que vale `tr("Auto")` cuando el idioma se detectó automáticamente o `""` si el usuario lo eligió.

- [x] **Paso 4: Ejecutar → PASS**

- [x] **Paso 5: Commit** — `feat(hud): add sidebar and top bar`

---

### Tarea 6: `gui.py` como centro de mando

**Archivos:**
- Modificar: `gui.py` (reemplazo completo de `OptimizadorGUI` por `CentroDeMando`; se conservan `_Redireccion`, `_geometria_visible`, `_logger`, `_cerrar` y la entrada `main()`)
- Modificar: `modules/config_gui.py` (`perfil_activo` en `_DEFAULTS`, por defecto `"equilibrado"`)

**Interfaces:**
- Consume: todo lo de las Tareas 1-5, `modules.core.verificar_permisos`, `modules.core.ejecutar_auto_completo`, `modules.performance.modo_perfil_auto`, `modules.performance.deshacer_cambios`, `modules.rollback.hay_cambios`, `utils.crear_punto_restauracion`.
- Produce: `CentroDeMando` con `raiz`, `botones`, `log`, `progreso`, `_ejecutar(funcion, *args)`.

- [x] **Paso 1: Montar la estructura**

Ventana 1000×660, mínimo 900×620. Orden vertical: `BarraSuperior` → `BarraLateral` (izquierda, `fill="y"`) + zona central (`fill="both", expand=True`). Zona central: fila superior con `MedidorSalud` (izquierda) y una rejilla 2×2 de `Tarjeta`; fila de botones (`BotonHUD` principal + secundario); barra de progreso `ttk`; etiqueta de estado; `ScrolledText` de log compacto con `fill="both", expand=True`.

- [x] **Paso 2: Conectar las acciones existentes**

Reutiliza exactamente las llamadas actuales: `disk_cleanup.modo_automatico`, `startup.modo_automatico`, `performance.modo_automatico`, `maintenance.modo_automatico`, `analisis.analisis_espacio`, `analisis.vista_previa`, `utils.info_sistema`, `analisis.exportar_informe`, `performance.deshacer_cambios`, `performance.modo_perfil_auto`, `performance.deshabilitar_tareas_telemetria`, `utils.crear_punto_restauracion`. El diálogo de perfiles (`_accion_perfiles`) se conserva tal cual, adaptado a la paleta nueva.

- [x] **Paso 3: "Optimizar ahora"**

Pide confirmación (`messagebox.askyesno`), crea el punto de restauración en el hilo de trabajo con `crear_punto_restauracion()`, aplica `modo_perfil_auto(perfil_activo, logger)` y al terminar refresca la instantánea. Si falta Administrador, muestra el aviso y ofrece `reiniciar_como_admin()`.

- [x] **Paso 4: "Deshacer último cambio"**

Si `rollback.hay_cambios()` es falso, `messagebox.showinfo` con el texto existente y retorno inmediato. Si hay cambios, confirma y llama a `deshacer_cambios(True)`.

- [x] **Paso 5: Datos y sondeo**

Al arrancar, lanza un hilo que calcula la instantánea lenta (disco, inicio, último mantenimiento) y la deja en la cola como `("instantanea", datos)`. Un `Sondeo` actualiza RAM/CPU cada 1,5 s. `_procesar_cola` refresca las cuatro tarjetas y el medidor. Mientras llegan, las tarjetas muestran "Analizando…". Sin psutil, RAM/CPU muestran "No disponible".

- [x] **Paso 6: Idioma y redimensionado**

`_alternar_idioma` guarda `idioma`, llama a `set_idioma` y reconstruye la UI conservando el texto del log (misma estrategia que hoy). `BarraSuperior` marca "Auto" solo si `config_gui.json` tenía `"idioma": "auto"`.

- [x] **Paso 7: Verificar que abre**

`python -c "import gui; a=gui.CentroDeMando(); a.raiz.after(2500, a.raiz.destroy); a.raiz.mainloop()"` → sin trazas.

- [x] **Paso 8: Commit** — `feat(gui): rebuild main screen as HUD command center`

---

### Tarea 7: Traducciones y pruebas funcionales

**Archivos:**
- Crear: `locales/en.hud.json`
- Modificar: `test_i18n.py` (escaneo recursivo de `modules/`)
- Prueba: `test_i18n.py`, `test_hud.py`

**Interfaces:**
- Consume: todas las claves `tr("…")` nuevas de `modules/hud/*` y `gui.py`.

- [x] **Paso 1: Extender el escaneo y verlo fallar**

```python
    ficheros = ["main.py", "gui.py", "i18n.py", "ui.py", "utils.py", "config.py",
                "test_efectividad.py"]
    for base, _dirs, nombres in os.walk(os.path.join(RAIZ, "modules")):
        for f in sorted(nombres):
            if f.endswith(".py"):
                ficheros.append(os.path.relpath(os.path.join(base, f), RAIZ))
```

`python test_i18n.py` → FALLA listando los textos nuevos sin traducción.

- [x] **Paso 2: Añadir `locales/en.hud.json`**

Una clave por texto español nuevo, con su inglés. Sin duplicar claves ya existentes en otra tabla con texto distinto.

- [x] **Paso 3: Ejecutar `python test_i18n.py` → todo OK**

- [x] **Paso 4: Pruebas funcionales manuales**

1. ES: abrir, comprobar título, tarjetas y barra lateral.
2. EN: pulsar "EN", comprobar que todo cambia y que el log se conserva.
3. Sin cambios registrados: pulsar "Deshacer" → mensaje informativo, app viva.
4. Con cambios: aplicar perfil, luego deshacer → ambos terminan sin error.
5. Redimensionar a 900×620 y a 1400×900 → nada cortado.

- [x] **Paso 5: `python -m py_compile` de todo y `pyflakes`**

- [x] **Paso 6: Commit** — `feat(i18n): translate the HUD and cover modules recursively`

---

### Tarea 8: Documentación y registro

**Archivos:**
- Modificar: `AGENTS.md`, `README.md`
- Crear: `D:\iA\%temp%\registros\sesion-20261028-1008\REGISTRO.md` y `ERRORES.md`
- Modificar: `REGISTRO.md` y `ERRORES.md` de la raíz (solo la línea del índice)

- [x] **Paso 1: Actualizar la descripción de `gui.py` y del paquete `modules/hud/`**
- [x] **Paso 2: Anotar errores y soluciones de la sesión en su fichero propio**
- [x] **Paso 3: Añadir la línea del índice en los dos ficheros compartidos**
- [x] **Paso 4: Commit** — `docs: describe the HUD command center`
