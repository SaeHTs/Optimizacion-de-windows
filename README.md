# 🖥️ Optimización de windows

**Proveedor:** Axiios_HTs · **Versión:** 1.5.1

Herramienta interactiva en **Python** para optimizar Windows: limpieza de disco,
programas de inicio, rendimiento y mantenimiento, todo desde un menú en terminal.

## 💻 Compatibilidad

| Requisito | Detalle |
|-----------|---------|
| Sistema operativo | **Windows 10** y **Windows 11** |
| Arquitectura | 64 bits (x64) |
| Permisos | Administrador (UAC) |
| Dependencias | Ninguna (exe standalone) |
| Código fuente | Python 3.10+ |

> ⚠️ No compatible con Windows 7/8, macOS ni Linux.

## 🔗 Enlaces

- 📁 Repositorio: https://github.com/SaeHTs/Optimizacion-de-windows
- ⬇️ Descargas (releases): https://github.com/SaeHTs/Optimizacion-de-windows/releases

## ⚠️ Advertencias

- **Ejecuta siempre como Administrador** (el script se ofrece a reiniciarse solo).
- Los cambios en servicios y el registro pueden afectar el sistema. La herramienta
  **pidiende confirmación** y ofrece crear un **punto de restauración** antes de
  cambios importantes.
- La desactivación de entradas de inicio es **reversible** (se renombran con
  prefijo `DISABLED_`).
- La limpieza de registro **no** está incluida a propósito: los limpiadores de
  registro suelen causar más daño que beneficio.

## 🚀 Uso

```powershell
cd Optimizacion     # la carpeta donde clonaste o descargaste el repo
pip install -r requirements.txt   # opcional: psutil para info del sistema
python main.py
```

> 💡 La mayoría de usuarios prefieren descargar el `.exe`
> desde la sección **Releases** (no necesitan Python).

## 📂 Estructura

```
windows-optimizer/
├── main.py                 # Consola: punto de entrada + menú
├── gui.py                  # 🖥️ GUI: interfaz gráfica (Tkinter)
├── ui.py                   # Interfaz: colores, banner, splash
├── utils.py                # Ejecución de comandos, logs, seguridad
├── config.py               # Rutas, servicios seguros, planes de energía
├── setup.iss               # 📦 Script del instalador (Inno Setup)
├── LICENSE.txt             # Licencia MIT
├── requirements.txt        # Dependencias opcionales
└── modules/
    ├── analisis.py         # 🔍 Análisis de espacio + dry-run
    ├── disk_cleanup.py     # 🧹 Temporales, prefetch, papelera, DISM
    ├── startup.py          # 🚀 Programas de inicio (registro)
    ├── performance.py      # ⚡ Energía, efectos visuales, servicios
    └── maintenance.py      # 🔧 SFC, DISM, desfragmentación, RAM
```

## 🧩 Módulos

| Módulo | Operaciones |
|--------|-------------|
| Limpieza | `%TEMP%`, `Windows\Temp`, Prefetch, papelera, caché de Windows Update, DISM |
| Inicio | Listar/deshabilitar/habilitar entradas del registro (reversible) |
| Rendimiento | Planes de energía, efectos visuales, servicios opcionales |
| Mantenimiento | SFC, DISM RestoreHealth, optimización de discos (TRIM/HDD), diagnóstico de RAM |

## 📋 Descripción de las utilidades

### 🧹 Limpieza de disco
Libera espacio eliminando archivos innecesarios:
- **Archivos temporales:** vacía `%TEMP%` (usuario) y `C:\Windows\Temp`.
  Los archivos en uso se omiten automáticamente.
- **Prefetch:** elimina archivos de precarga; Windows los regenera solo.
- **Papelera de reciclaje:** vacía todas las unidades.
- **Caché de Windows Update:** detiene los servicios, borra
  `C:\Windows\SoftwareDistribution\Download` y los reinicia.
- **Componentes obsoletos (DISM):** elimina copias antiguas de componentes
  de Windows; puede liberar varios GB.

### 🚀 Optimizar programas de inicio
Acelera el arranque del equipo:
- **Listar:** muestra las entradas `Run` del registro (usuario, equipo y
  32-bit) y las carpetas de inicio.
- **Deshabilitar:** renombra la entrada con prefijo `DISABLED_` (reversible).
- **Habilitar:** revierte el cambio anterior.

### ⚡ Rendimiento general
Ajusta el sistema para mayor velocidad:
- **Planes de energía:** Alto rendimiento, Equilibrado o Ahorro de energía.
- **Efectos visuales:** prioriza el rendimiento (animaciones y transparencias
  reducidas) o restaura el modo automático.
- **Servicios opcionales:** deshabilita servicios no esenciales en un equipo
  doméstico (telemetría, fax, WAP push, registro remoto, etc.) y permite
  restaurarlos.

### 🔧 Mantenimiento del sistema
Mantiene Windows sano y estable:
- **SFC (`sfc /scannow`):** repara archivos del sistema protegidos.
- **DISM (`RestoreHealth`):** repara la imagen de Windows.
- **Optimizar unidades:** TRIM en SSD / desfragmentación en HDD.
- **Diagnóstico de memoria:** programa el análisis de RAM al reiniciar.

## ⚡ Rendimiento

- **Borrado de una sola pasada** con `scandir` (~15% más rápido
  en carpetas con muchos archivos).
- **Limpieza de temporales en paralelo** (`ThreadPoolExecutor`).
- **Salida en vivo** en SFC, DISM y desfragmentación
  (ves el progreso al instante).
- **Consultas de servicios en paralelo** (`ThreadPoolExecutor`).

## 🤖 Modo automático

Opción **7** del menú principal (y en cada submenú): ejecuta
todas las optimizaciones de la sección sin preguntas intermedias.

- **Limpieza:** temporales + prefetch + papelera + caché + DISM
- **Inicio:** deshabilita solo entradas seguras
  (auto-lanzador de Edge, programador de Java) — reversible
- **Rendimiento:** plan alto rendimiento + visuales + servicios
- **Mantenimiento:** SFC + DISM + optimización de discos

### 🔧 Mantenimiento inteligente (v1.3)

El modo automático de mantenimiento **verifica primero**:

1. `sfc /verifyonly` y `DISM /CheckHealth` **en paralelo**
   (ambas son de solo lectura)
2. Solo repara lo que está dañado — si el sistema está
   íntegro, **no ejecuta** los SFC/DISM completos
   (de 5–15 min a ~2 min en PCs sanos)
3. Repara **DISM antes que SFC**: un almacén de
   componentes sano hace que SFC acierte a la primera
4. Al final, optimiza discos (TRIM/defrag)

El modo automático global ofrece crear un **punto de restauración**
antes de empezar. El diagnóstico de RAM queda fuera (reinicia el PC).

## 🖼️ Interfaz

- Pantalla de inicio (splash) con la imagen del producto
- Colores ANSI en el menú (Windows 10+)
- Banner con producto, proveedor y versión

## 🔍 Análisis del sistema (dry-run)

Opción **8** del menú principal — **no cambia nada**:

- **Análisis de espacio:** carpetas que más ocupan
  (en paralelo), espacio recuperable conocido
  (temporales, cachés de navegadores, papelera,
  Windows.old) y archivos del sistema
- **Vista previa:** qué se limpiaría, qué entradas de
  inicio se deshabilitarían, qué cambios de rendimiento
  se aplicarían y si SFC/DISM necesitarían reparación

## 🐞 Correcciones (v1.4.1)

- Caché de Firefox ahora mide solo `cache2` (antes medía
  todo el perfil)
- `ThreadPoolExecutor` con lista vacía ya no crashea
- La **optimización de entrega** de Windows Update ahora
  se limpia (antes solo aparecía en el análisis)

## 🖥️ Interfaz gráfica (GUI)

Versión con ventana (tema oscuro, log en vivo, sin congelarse):

```powershell
python gui.py
```

**Ejecutables resultantes:**
- `dist\Optimizacion.exe` — versión consola (menú en terminal)
- `dist\Optimizacion-GUI.exe` — versión gráfica (sin ventana de consola)

## 📦 Instalador (Inno Setup)

Genera `installer\Optimizacion-Setup.exe` con:
- Ambos ejecutables en `%LOCALAPPDATA%\Programs\Optimizacion`
  (**instalación por usuario: no pide Administrador** —
  soluciona el error 740; los exe se elevan solos con UAC)
- Accesos directos (escritorio y menú Inicio)
- Desinstalador
- Licencia MIT y ejecutar al finalizar

**Para compilar el instalador:**

```powershell
winget install JRSoftware.InnoSetup   # si no lo tienes
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

## 🛠️ Solución de problemas

| Problema | Solución |
|----------|----------|
| **Error 740** al instalar | Usar la **v1.5.1+**: el instalador es **por usuario** y no pide Administrador (los exe se elevan solos con UAC al ejecutarse) |
| SmartScreen bloquea el exe | *"Más información"* → *"Ejecutar de todos modos"* (exe sin firmar) |
| No puede optimizar | Los exe piden permisos de Administrador (UAC) solos; aceptar el aviso |
| No aparecen cambios | Reiniciar el equipo después de optimizar |

## 📦 Distribución (para otros usuarios)

El ejecutable standalone está en `dist/Optimizacion.exe` (7 MB aprox).
No requiere Python instalado y **solicita permisos de Administrador
automáticamente** al abrirlo.

**Datos del programa (Propiedades → Detalles):**

| Campo | Valor |
|-------|-------|
| Compañía | Axiios_HTs |
| Producto | Optimización |
| Versión | 1.5.1 |
| Ícono | Imagen + texto "optimización" |

**Para compartirlo:**

1. Sube el `.exe` a una **GitHub Release**, Google Drive, Dropbox, etc.
2. En la primera ejecución, Windows mostrará un aviso de SmartScreen
   (el exe no está firmado digitalmente): click en *"Más información"*
   → *"Ejecutar de todos modos"*.

**Para reconstruir los exe:**

```powershell
pip install pyinstaller pillow
python crear_icono.py "ruta\a\tu\imagen.bmp"   # genera icono.ico + splash.png
pyinstaller --onefile --uac-admin --icon icono.ico --version-file version_info.txt --add-data "splash.png;." --name Optimizacion main.py
pyinstaller --onefile --noconsole --uac-admin --icon icono.ico --version-file version_info.txt --add-data "splash.png;." --name Optimizacion-GUI gui.py
```

## 📝 Logs

Todas las acciones quedan registradas en `optimizador.log`.

## ➕ Ideas para ampliar

- Gestión de tareas programadas en inicio (Task Scheduler)
- Limpieza de navegadores (caché, cookies) con confirmación
- Panel de control con interfaz gráfica (Tkinter/PyQt)
- Exportar/importar configuración de optimizaciones aplicadas
