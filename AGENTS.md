# PRIORIDAD EXTREMA (se cumple siempre, sobre cualquier otra regla)
1. IDIOMA DE TRABAJO: SIEMPRE en español, sin excepciones ni alternativas.
   Aplica a: respuestas del agente, comentarios de código, documentación y archivos .md.
   No cambia aunque el usuario escriba en otro idioma. Única salvedad: el código,
   los identificadores y los mensajes de commit se mantienen en inglés técnico.
2. Las APLICACIONES pueden ser bilingües (español e inglés): interfaz, textos de
   usuario y archivos de idioma/i18n. La regla 1 rige al agente, no al producto.
3. NUNCA dejar en los archivos del proyecto datos propios de la PC: hardware,
   números de serie, nombre de usuario, rutas personales ni exportaciones (.reg).
   Si hace falta mencionar algo, usar valores genéricos (ej: "GPU NVIDIA", "C:\Users\<usuario>").
4. PUBLICACIÓN EN GITHUB: todo proyecto se prueba PRIMERO en local, con sus
   respectivas actualizaciones (compilación correcta, pruebas reales y
   verificación funcional). NADA se sube a GitHub hasta que el usuario da el
   visto bueno explícito ("ok, súbelo" o equivalente). En GitHub se publica un
   único release final, no versiones intermedias.

---

# Optimizacion-de-windows - Guía para Agentes

## 📋 Descripción del Proyecto
Herramienta en **Python 3.10+** para optimizar Windows 10/11 (x64). Incluye limpieza de disco, gestión de inicio, rendimiento y mantenimiento. Se ejecuta en dos modos: consola (`main.py`) y GUI (`gui.py`).

## 🏗️ Estructura del Proyecto
- `main.py` — Menú de consola. Verifica admin, muestra opciones (1-8, 0).
- `gui.py` — **Centro de mando** (Tkinter): orquesta los widgets de `modules/hud/`, los hilos y la cola; no contiene lógica de sistema. Ventana de 1000×660 (mínimo 900×620) con barra superior (título + `ES | EN` + marca "Auto"), barra lateral de navegación, medidor circular de salud 0-100, cuatro tarjetas clicables (disco, inicio, RAM/CPU, mantenimiento), botón principal **"Optimizar ahora"** y **"Deshacer último cambio"**, registro en vivo, barra de progreso y barra de estado. Acciones de la barra lateral: Optimizar todo (modo automático con confirmación DESPUÉS del dry-run), Limpieza, Inicio, Rendimiento, Mantenimiento, **Perfiles (diálogo E/G/P: `_accion_perfiles`)**, Vista previa, Análisis, Exportar informe, Punto de restauración, **Tareas de telemetría (`_accion_telemetria`)**, Información, Abrir registro y **Deshacer (`_accion_deshacer` → rollback)**. Los datos lentos (disco, inicio) se miden en un hilo; RAM/CPU cada 1,5 s con `Sondeo`. Log coloreado automático (✅ verde / ⚠️ amarillo / ❌ rojo).
- `modules/hud/` — Componentes de la interfaz, uno por archivo: `tema.py` (paleta y fuentes, **único sitio con colores**), `datos.py` (datos reales + fórmula de salud + `Sondeo`), `medidor.py` (`MedidorSalud`), `tarjeta.py` (`Tarjeta`), `boton.py` (`BotonHUD`), `lateral.py` (`BarraLateral`), `superior.py` (`BarraSuperior`).
- `config_gui.py` — Configuración persistente de la GUI (JSON junto al exe). Con `"recordar_pos": true` restaura tamaño/posición de la ventana (la geometría se guarda al cerrar).
- `modules/core.py` — **Lógica central compartida** (verificar_permisos, reiniciar_como_admin, ejecutar_vista_previa, ejecutar_auto_completo). `main.py` y `gui.py` la consumen sin duplicar código.
- `modules/analisis.py` — Análisis de espacio y vista previa (dry-run) con indicadores de progreso.
- `modules/disk_cleanup.py` — Limpieza de temporales, prefetch, papelera, caché de Windows Update/entrega, DISM, caché de navegadores (Chrome/Edge/Firefox), miniaturas y logs/volcados. Eliminación iterativa (sin recursión).
- `modules/startup.py` — Gestión de entradas de inicio del registro.
- `modules/performance.py` — Planes de energía, efectos visuales, servicios (opcionales + avanzados con detección), tareas de telemetría, perfiles (equilibrado/gaming/privacidad).
- `modules/rollback.py` — Registro JSON (`logs/rollback.json`) de cambios reversibles (servicios/tareas/registro) y `deshacer()`. Registrar SIEMPRE el estado previo antes de tocar.
- `modules/maintenance.py` — SFC, DISM, optimización de discos, diagnóstico RAM.
- `utils.py` — Ejecución de comandos, logger **`logs/optimizador-AAAA-MM-DD.log`** (v1.7.0: ya no el único archivo gigante), helpers, **`ejecutar_con_barra()`** (barra por %), **`etapa()`** (barra por pasos), **`tipo_unidad()`** (SSD/HDD).
- `ui.py` — Colores (`Color`), banner, splash, versión. Helpers de menú:
  **`titulo_menu(texto, color)`** (encabezado con color de categoría) y
  **`separador(texto)`** (secciones dentro de menús).
- `i18n.py` — Motor bilingüe ES/EN. **`tr(texto)`** traduce al idioma activo;
  **`set_idioma("es"|"en"|"auto")`** debe llamarse ANTES de importar módulos
  que muestran texto. Detección por `GetUserDefaultUILanguage`.
  **`registrar_recarga(fn)`** permite que las tablas ya construidas
  (`config.py`, `modules/analisis.py`) se recalculen al cambiar de idioma:
  si no, quedarían congeladas en el idioma del import.
- `locales/` — Tablas `en*.json` (`"texto en español": "English text"`);
  se cargan todas al arrancar en inglés. Faltante → texto original.
  Una misma clave no puede estar en dos ficheros con textos distintos.
- `instalador/` — Mensajes propios del instalador por idioma
  (`mensajes_es.isl` / `mensajes_en.isl`), los usa `setup.iss` con
  `compiler:Languages\Spanish.isl` y `compiler:Default.isl`.
- `test_i18n.py` — Pruebas del soporte bilingüe: cobertura de traducciones,
  claves duplicadas, tablas que siguen al idioma, nombres de perfil.
  Recorre `modules/` **de forma recursiva** (subcarpetas incluidas), así que
  los textos de `modules/hud/` también quedan vigilados.
  Se ejecuta con `python test_i18n.py` (no necesita pytest).
- `test_hud.py` — Pruebas del centro de mando: paleta y umbrales de color,
  fórmula de salud, antigüedad del último mantenimiento y construcción de los
  widgets con una raíz Tk real y oculta. `python -m pytest test_hud.py -q`.
- `config.py` — Rutas, servicios seguros, planes de energía.

## ⚠️ Notas Críticas
- **Administrador obligatorio**: Toda operación de sistema requiere UAC (`ctypes.windll.shell32.IsUserAnAdmin`).
- **Modo Automático**: Ahora muestra una **vista previa (dry-run)** antes de ejecutar. Requiere confirmación explícita.
- **Logger**: `utils.setup_logger()` escribe en `logs/optimizador-YYYY-MM-DD.log` (uno por día; la carpeta se crea automáticamente y los antiguos `optimizador.log` siguen siendo válidos).
- **Cola GUI**: `gui.py` usa `queue.Queue(maxsize=100)` para evitar consumo excesivo de memoria; los mensajes se descartan si está llena.
- **Confirmaciones GUI**: el modo automático pregunta "¿Proceder?" DESPUÉS de la vista previa (paridad con consola, vía `__CONFIRMA_AUTO__` en la cola). El rollback es accesible desde la GUI (⏪ Deshacer / Ctrl+D); las funciones de `performance.py` aceptan `automatico=True` para uso desde GUI (saltan los `input()` de consola).
- **Consola**: menú principal con opciones 9) 🎯 Perfiles y 10) ⏪ Deshacer cambios.

## 🛠️ Comandos Útiles (desde la raíz del proyecto)
```powershell
# Modo consola
python main.py

# Modo GUI
python gui.py

# Test de efectividad (solo lectura, puntúa el PC 0-100)
python test_efectividad.py

# Pruebas del centro de mando y del bilingüe
python -m pytest test_hud.py test_i18n.py -q

# Verificar sintaxis (python NO expande comodines en PowerShell: hay que
# construir la lista de ficheros, si no falla con "Invalid argument")
$f = @("main.py") + @(Get-ChildItem modules\*.py, modules\hud\*.py | ForEach-Object { $_.FullName })
python -m py_compile @f

# Construir ejecutables (requiere pyinstaller e inno setup)
pyinstaller --onefile --uac-admin --icon icono.ico --version-file version_info.txt --add-data "splash.png;." --add-data "locales;locales" --name Optimizacion main.py
pyinstaller --onefile --noconsole --uac-admin --icon icono.ico --version-file version_info.txt --add-data "splash.png;." --add-data "locales;locales" --name Optimizacion-GUI gui.py
# Instalador: ISCC.exe cambia de ruta segun se instale Inno Setup
# (para todos: Program Files / por usuario: %LOCALAPPDATA%\Programs)
$iscc = @("C:\Program Files (x86)\Inno Setup 6\ISCC.exe", "C:\Program Files\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
& $iscc setup.iss
```

## 🚨 Gotchas
1. Ejecutar sin admin → fallos de acceso denegado.
2. El modo automático modifica registro/servicios → usar punto de restauración.
3. `vista_previa` puede tardar (calcula tamaños + verifica SFC/DISM); muestra indicadores "⏳".
4. No romper la estructura de importaciones diferidas en `main.py` (evita costos de arranque).
5. **Una sola raíz de Tk por proceso de prueba**: crear y destruir varias
   `tk.Tk()` seguidas deja Tcl inservible ("Can't find a usable init.tcl").
   `test_hud.py` comparte una raíz oculta fuera de pantalla (`+4000+4000`).
6. `scrolledtext.ScrolledText` trae una **Scrollbar clásica** (`tk.Scrollbar`),
   no ttk: los estilos `ttk.Style` no le llegan, hay que configurar
   `log.vbar` directamente.
7. La salud del HUD no penaliza los datos no medidos (`None`): sin registros
   de mantenimiento la tarjeta dice "Sin registros" y ese tramo no resta.
   Los logs de **0 bytes** no cuentan como mantenimiento: `setup_logger()` crea
   el fichero del día aunque la operación se cancele sin escribir nada.

## 📚 Fuentes de Verdad
- `README.md` — Uso y compilación.
- `config.py` — Configuración global.
- `modules/` — Lógica por dominio.
- `utils.py` — Logger y ejecución de comandos.

---
*Guía actualizada a v1.9.0 (bilingüe ES/EN: motor i18n propio sin dependencias, detección automática del idioma de Windows, botón 🌐 en la GUI que cambia el idioma al instante, opción 11 en consola, preferencia `idioma` en `config_gui.json`; hereda v1.8.4: interfaz cyberpunk/dark en la GUI, logo de inicio intacto; validación de Python 64 bits; timeout default de comandos a 60 s; plan de energía inteligente laptop/desktop; deshabilitación de servicios en paralelo; hereda v1.8.3: robustez — logger con fallback a %TEMP% si la carpeta es de solo lectura, rollback avisa si no puede guardar, GUI valida que la geometría recordada sea visible, test redirige UTF-8 sin crash; hereda v1.8.2: extracción de versión reparada en los .bat de release vía línea `FileVersion`, `version_info.txt` en UTF-8 limpio sin BOM, rollback también para modo automático y menú de servicios, deshacer con errores reales vía `-ErrorAction Stop`, test de efectividad con detección de plan por GUID): logs por fecha (`logs/`), detección SSD/HDD en optimización de discos (`tipo_unidad()`), atajos de teclado en GUI (Ctrl+L/I/R/M/A/V/O/P/D/T y F5), config persistente del GUI (`config_gui.json`, `recordar_pos` funciona), interfaz GUI reorganizada por secciones con perfiles/telemetría/deshacer. Demos locales (`demo_barra.py`, `demo_emisor.py`, `DEMO_BARRA.bat`) NO suben al repo (ver `.gitignore`).*

---

## Sistema Superpowers (skills en .opencode/skills/)

Metodología completa de desarrollo de software para agentes de código, con 17 skills organizadas en categorías. La skill using-superpowers es obligatoria al iniciar cualquier conversación: requiere invocar skills relevantes ANTES de cualquier respuesta.

### Flujo recomendado
1. Inicio → using-superpowers (obligatorio)
2. Trabajo creativo → rainstorming → (si es proyecto) writing-plans
3. Implementación → 	est-driven-development + erification-before-completion
4. Ejecución → subagent-driven-development o executing-plans
5. Revisión → 
equesting-code-review / 
eceiving-code-review
6. Integración → inishing-a-development-branch
7. Bugs → systematic-debugging

### Acoplamiento automático de skills por tipo de tarea

Al iniciar cualquier tarea, identifico el tipo de tarea y acoplo la skill correspondiente **antes** de responder o actuar:

| Tipo de tarea | Skill acoplada |
|---|---|
| Inicio de cualquier conversación | using-superpowers |
| Trabajo creativo, nuevo proyecto | rainstorming |
| Plan de implementación (varios pasos) | writing-plans |
| Bug, falla de prueba | systematic-debugging |
| Implementar característica | 	est-driven-development |
| Afirmar completación | erification-before-completion |

**Regla de acoplamiento:** La skill correspondiente debe invocarse ANTES de cualquier respuesta, acción o aclaración relacionada con ese tipo de tarea.

---

## Sistema ECC (skills en .opencode/skills/, plugin en .opencode/plugins/ecc.js)

Sistema de ingeniería de software para agentes de código de affaan-m/ecc, con plugin de OpenCode (hooks, herramientas personalizadas) y skills organizadas por dominio.

### Dominio Técnico (ECC)
- **coding-standards** — Convenciones base de nombrado, legibilidad, inmutabilidad.
- **backend-patterns** — Arquitectura backend, API, base de datos, caché, colas.
- **frontend-patterns** — React, Next.js, hooks, estado, rendimiento, accesibilidad.
- **api-design** — REST: nombrado, códigos de estado, paginación, versionado, formato.
- **e2e-testing** — Playwright, Page Object Model, pruebas flaky, CI/CD.
- **security-review** — Checklist de seguridad: secretos, validación, SQLi, XSS, CSRF, rate limiting.
- **security-scan** — Auditoría de configuración con AgentShield.

### Herramientas personalizadas del plugin ECC

un-tests, check-coverage, security-audit, ormat-code, lint-check, git-summary, changed-files, dependency-analyzer

---

## Formato AGENTS.md estándar (referencia abierta)

Este proyecto sigue el formato abierto de [AGENTS.md](https://agents.md/) — un archivo de instrucciones dedicado y predecible para guiar a los agentes de código en un proyecto.

**Regla:** Este AGENTS.md tiene prioridad sobre cualquier instrucción genérica de AGENTS.md estándar.

---

## System Prompts Públicos (referencia abierta)

Este proyecto referencia el repositorio [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) como colección pública de system prompts de proveedores de IA.

**No es una skill ni plugin:** Los system prompts filtrados son documentos de referencia, no skills cargables por OpenCode ni plugins ejecutables.

**Regla:** Este AGENTS.md tiene prioridad sobre cualquier instrucción de system prompt externo.
