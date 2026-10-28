# Optimizador Windows

Herramienta para optimizar Windows 10/11: limpieza, inicio, rendimiento y mantenimiento. Interfaz gráfica y modo consola.

## Descarga

Descarga desde [Releases](https://github.com/SaeHTs/Optimizacion-de-windows/releases):
- **Optimizacion-Setup.exe** — Instalador (recomendado). Crea accesos directos.
- **Optimizacion.zip** — Portable. Ejecuta sin instalar.

## Características

- **Limpieza de disco** — Temporales, caché, papelera
- **Centro de mando** — Panel HUD con medidor de salud del PC (0-100) y tarjetas de estado en vivo
- **Gestión de inicio** — Controla programas al arrancar
- **Rendimiento** — Planes de energía, efectos visuales, servicios y telemetría
- **Mantenimiento** — SFC, DISM, optimización de discos
- **Modo automático** — Optimización completa con vista previa
- **Deshacer cambios** — Rollback de servicios, tareas y registro
- **Punto de restauración** — Recomendado antes de cambios importantes
- **Bilingüe** — Español/Inglés
- **Instalador por usuario** — Sin permisos de administrador

## Uso

Requiere **ejecutar como administrador** para aplicar optimizaciones.

La pantalla principal es un **centro de mando** con:
- Medidor circular de **salud del PC** (0-100). Fórmula documentada en
  `modules/hud/datos.py`: disco 30 + inicio 20 + RAM 25 + mantenimiento 25
  puntos de penalización; un dato que no se puede medir no penaliza.
- Cuatro tarjetas clicables (disco, inicio, RAM/CPU, mantenimiento) que
  llevan a su sección de la barra lateral.
- **Optimizar ahora**: crea punto de restauración y aplica el perfil activo
  (si el punto falla, no se cambia nada).
- **Deshacer último cambio**: usa el registro de `logs/rollback.json`.

## Licencia

MIT - ver [LICENSE.txt](LICENSE.txt).
