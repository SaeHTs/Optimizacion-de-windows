# Tablas de idioma (i18n)

- El texto origen de la aplicación está en **español**.
- Cada archivo `en*.json` es un diccionario `"texto en español": "text in English"`.
- `i18n.py` carga todos los `en*.json` de esta carpeta al iniciar en inglés.
- Si falta una clave, se muestra el texto en español (nunca falla).

Convención de nombres por área:

| Archivo | Área |
|---|---|
| `en.console.json` | `main.py` y `ui.py` |
| `en.core.json` | `utils.py` y `modules/core.py` |
| `en.gui.json` | `gui.py` |
| `en.cleanup.json` | `modules/disk_cleanup.py` |
| `en.analysis.json` | `modules/analisis.py` |
| `en.performance.json` | `modules/performance.py` |
| `en.maintenance.json` | `modules/maintenance.py` |
| `en.startup.json` | `modules/startup.py` |
| `en.rollback.json` | `modules/rollback.py` |

No traducir: marcadores de protocolo (`Progreso: N%`, `__FIN__`,
`__CONFIRMA_AUTO__`), nombres de servicios, claves de registro, rutas y
comandos de sistema.
