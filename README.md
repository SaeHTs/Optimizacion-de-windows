# 🖥️ Optimizador de Windows

Herramienta interactiva en **Python** para optimizar Windows: limpieza de disco,
programas de inicio, rendimiento y mantenimiento, todo desde un menú en terminal.

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
cd "C:\Users\Sae\Documents\Default Project\windows-optimizer"
pip install -r requirements.txt   # opcional: psutil para info del sistema
python main.py
```

## 📂 Estructura

```
windows-optimizer/
├── main.py                 # Punto de entrada + menú principal
├── utils.py                # Ejecución de comandos, logs, seguridad
├── config.py               # Rutas, servicios seguros, planes de energía
├── requirements.txt        # Dependencias opcionales
└── modules/
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

## 📦 Distribución (para otros usuarios)

El ejecutable standalone está en `dist/OptimizadorWindows.exe` (7 MB aprox).
No requiere Python instalado y **solicita permisos de Administrador
automáticamente** al abrirlo.

**Para compartirlo:**

1. Sube el `.exe` a una **GitHub Release**, Google Drive, Dropbox, etc.
2. En la primera ejecución, Windows mostrará un aviso de SmartScreen
   (el exe no está firmado digitalmente): click en *"Más información"*
   → *"Ejecutar de todos modos"*.

**Para reconstruir el exe:**

```powershell
pip install pyinstaller
pyinstaller --onefile --uac-admin --name OptimizadorWindows main.py
```

## 📝 Logs

Todas las acciones quedan registradas en `optimizador.log`.

## ➕ Ideas para ampliar

- Gestión de tareas programadas en inicio (Task Scheduler)
- Limpieza de navegadores (caché, cookies) con confirmación
- Panel de control con interfaz gráfica (Tkinter/PyQt)
- Exportar/importar configuración de optimizaciones aplicadas
