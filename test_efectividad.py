"""Test de efectividad del Optimizador.

Puntúa un PC de 0 a 100 según cuánto se beneficiaría una optimización.
Solo lectura: NO modifica nada del sistema.
Cada categoría tiene:
  1. Qué se mide (disco, inicio, rendimiento, servicios)
  2. Cómo se calculan los puntos
  3. Recomendación de cómo mejorarlo si está bajo

Uso:  python test_efectividad.py
"""
import os
import re
import sys
import winreg
from datetime import datetime

# Forzar UTF-8 con respaldo seguro (igual que main.py/gui.py): sin
# esto, redirigir la salida ("> informe.txt", pipe) en Python < 3.15
# crashea con UnicodeEncodeError por los emojis.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from i18n import set_idioma, tr
from modules.config_gui import ConfigGUI

# Idioma: preferencia guardada o detección automática de Windows.
# Debe fijarse ANTES de importar config (traduce descripciones al importar).
set_idioma(ConfigGUI().datos.get("idioma", "auto"))

from config import ENTRADAS_INICIO_AUTO, PLANES_ENERGIA, SERVICIOS_OPCIONALES
from modules.performance import estados_servicios, CLAVE_EFECTOS
from modules.startup import CLAVES_INICIO, PREFIJO_DESHABILITADO
from modules.analisis import (
    tamano_cache_firefox,
    tamano_papelera,
    tamano_recursivo,
)
from ui import VERSION
from utils import ejecutar_comando, fmt_bytes

# Umbrales (coinciden con los mensajes del final):
#   70-100 → mucho por mejorar (beneficio grande)
#   35-69  → puede mejorar decentemente
#   0-34   → ya está muy optimizado


# ---------------------------------------------------------------- helpers

def _entradas_deshabilitables() -> int:
    """Cuenta entradas de inicio seguras aún activas."""
    total = 0
    for ambito, prefijo in ENTRADAS_INICIO_AUTO:
        for etiqueta, raiz, clave in CLAVES_INICIO:
            if etiqueta != ambito:
                continue
            try:
                with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                    indice = 0
                    while True:
                        try:
                            nombre, _, _ = winreg.EnumValue(k, indice)
                            indice += 1
                        except OSError:
                            break
                        if (nombre.startswith(prefijo)
                                and not nombre.startswith(PREFIJO_DESHABILITADO)):
                            total += 1
            except FileNotFoundError:
                continue
    return total


def _plan_actual() -> str:
    codigo, salida = ejecutar_comando("powercfg /getactivescheme")
    return salida.strip().splitlines()[-1] if salida.strip() else "?"


# GUID del plan "Alto rendimiento" (SCHEME_MIN): es estable en cualquier
# idioma de Windows, a diferencia del nombre localizado ("Alto rendimiento").
GUID_ALTO_RENDIMIENTO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

# GUID de los planes conocidos -> alias de config.PLANES_ENERGIA (traducido).
# El nombre que devuelve Windows va en su idioma: asi el informe no mezcla.
_GUIDS_PLANES = {
    "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "SCHEME_MIN",
    "381b4222-f694-41f0-9685-ff5bb260df2e": "SCHEME_BALANCED",
    "a1841308-3541-4fab-bc81-f71556f20b2a": "SCHEME_MAX",
}


def _nombre_plan(plan: str) -> str:
    """Nombre del plan en el idioma activo, si se reconoce su GUID."""
    m = re.search(
        r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})", plan or ""
    )
    if m:
        alias = _GUIDS_PLANES.get(m.group(1).lower())
        if alias:
            return PLANES_ENERGIA[alias]
    # plan desconocido: se muestra el nombre tal cual lo da Windows
    return (plan or "?").split("(")[-1].rstrip(")")


def _es_alto_rendimiento() -> bool:
    """True si el plan activo es Alto rendimiento (comparado por GUID)."""
    codigo, salida = ejecutar_comando("powercfg /getactivescheme")
    m = re.search(
        r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})", salida
    )
    return bool(m) and m.group(1).lower() == GUID_ALTO_RENDIMIENTO


def _efectos_actuales() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, CLAVE_EFECTOS, 0, winreg.KEY_READ
        ) as k:
            valor, _ = winreg.QueryValueEx(k, "VisualFXSetting")
        return {0: tr("Windows decide"), 1: tr("Mejor apariencia"),
                2: tr("Mejor rendimiento"), 3: tr("Personalizado")}.get(valor, str(valor))
    except OSError:
        return tr("Por defecto")


def _recomendar(genero: str, accion: str) -> str:
    """Genera la recomendación de acción según el estado."""
    return f"  → {tr(genero).upper()}: {accion}"


# ---------------------------------------------------------------- principal

def main() -> None:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- Datos por categoría ----
    from config import (
        CACHE_NAVEGADORES, RUTA_CACHE_ENTREGA, RUTA_CACHE_UPDATE,
        RUTA_PREFETCH, RUTAS_TEMPORALES,
    )
    liberable = 0
    for plantilla in (RUTAS_TEMPORALES + [RUTA_PREFETCH, RUTA_CACHE_UPDATE, RUTA_CACHE_ENTREGA] + CACHE_NAVEGADORES):
        ruta = os.path.expandvars(plantilla)
        if os.path.isdir(ruta):
            liberable += tamano_recursivo(ruta)
    liberable += tamano_papelera() + tamano_cache_firefox()
    gb = liberable / (1024 ** 3)

    n_inicio = _entradas_deshabilitables()

    plan = _plan_actual()
    es_alto = _es_alto_rendimiento()
    efectos = _efectos_actuales()
    es_mejor_fx = efectos == tr("Mejor rendimiento")

    estados = estados_servicios(list(SERVICIOS_OPCIONALES))
    activos = sum(1 for e in estados.values() if e == "RUNNING")

    # ---- Puntuación ----
    puntos_d   = min(40, int(gb * 2))                      # 0-40 GB
    puntos_i   = min(10, n_inicio * 5)                     # 0-10 inicios
    puntos_e   = 0 if es_alto else 15                       # plan energía 15
    puntos_fx  = 0 if es_mejor_fx else 15                   # efectos 15
    puntos_s   = round((6 - activos) * 20 / 6)              # 0-20 servicios

    puntos_total = puntos_d + puntos_i + puntos_e + puntos_fx + puntos_s

    # ---- Imprimir ----
    print("\n" + "═" * 58)
    print(tr("  🧪 TEST DE EFECTIVIDAD  ({fecha})  v{version}").format(fecha=fecha, version=VERSION))
    print(tr("  Solo lectura — no cambia nada"))
    print("═" * 58)

    print(tr("\n  💾 DISCO ({puntos:>3}/40 pts × {gb} GB liberables)").format(puntos=min(40, int(gb*2)), gb=f"{gb:.1f}"))
    if gb > 15:
        print(_recomendar("alto", tr("liberas {gb} GB — ejecuta la limpieza completa").format(gb=f"{gb:.1f}")))
    elif gb > 5:
        print(_recomendar("medio", tr("liberas {gb} GB — ejecuta la limpieza").format(gb=f"{gb:.1f}")))
    else:
        print(_recomendar("bajo", tr("queda poco por liberar ({gb} GB)").format(gb=f"{gb:.1f}")))

    print(tr("\n  🚀 INICIO ({puntos:>3}/10 pts × {n} entradas deshabilitables)").format(puntos=puntos_i, n=n_inicio))
    if n_inicio >= 2:
        print(_recomendar("alto", tr("{n} programas se deshabilitan → más arranque rápido").format(n=n_inicio)))
    else:
        print(_recomendar("bajo", tr("listo (solo {n} entrada por deshabilitar)").format(n=n_inicio)))

    print(tr("\n  ⚡ RENDIMIENTO ({puntos:>3}/30 pts)").format(puntos=puntos_e + puntos_fx))
    print(tr("     Plan actual: {plan}").format(plan=_nombre_plan(plan)))
    print(tr("     Efectos visuales: {efectos}").format(efectos=efectos))
    if not es_alto and not es_mejor_fx:
        print(_recomendar("alto", tr("activar rendimiento + ajustar efectos aceleran el PC")))
    elif not es_alto or not es_mejor_fx:
        print(_recomendar("medio", tr("algunos ajustes ayudarían")))
    else:
        print(_recomendar("bajo", tr("ya está en modo óptimo")))

    print(tr("\n  🔌 SERVICIOS ({puntos:>3}/20 pts × {activos}/{total} activos)").format(puntos=puntos_s, activos=activos, total=len(SERVICIOS_OPCIONALES)))
    if activos >= 4:
        print(_recomendar("alto", tr("{activos} servicios se deshabilitan → menos consumo en reposo").format(activos=activos)))
    elif activos > 0:
        print(_recomendar("medio", tr("{activos} servicios en uso").format(activos=activos)))
    else:
        print(_recomendar("bajo", tr("ningún servicio opcional activo")))

    # ---- Tabla resumen con barras ----
    print()
    print("  " + "─" * 64)
    print(f"  {tr('Categoría'):<25} {tr('Estado'):<24} {tr('Progreso')}")
    print("  " + "─" * 64)
    print(f"  {tr('💾 Disco'):<25} {fmt_bytes(liberable):<24} {_barra_ascii(puntos_d, 40)}")
    print(f"  {tr('🚀 Inicio'):<25} {(str(n_inicio) + ' ' + tr('entradas')) if n_inicio else tr('listo'):<24} {_barra_ascii(puntos_i, 10)}")
    print(f"  {tr('⚡ Rendimiento'):<25} {_nombre_plan(plan):<24} {_barra_ascii(puntos_e + puntos_fx, 30)}")
    print(f"  {tr('🔌 Servicios'):<25} {str(activos)+'/'+str(len(SERVICIOS_OPCIONALES))+' '+tr('activos'):<24} {_barra_ascii(puntos_s, 20)}")
    print("  " + "─" * 64)
    print(f"  {tr('PUNTUACIÓN DE OPTIMIZACIÓN'):<25} {'':<24} {_barra_ascii(puntos_total, 100)}")
    print(f"  {tr('Optimización actual del PC'):<25} {'':<24} {100 - puntos_total}% {tr('optimizado')}")

    if puntos_total >= 70:
        print(tr("  🟢 ANIMA: tu PC tiene mucho por mejorar (beneficio grande)"))
    elif puntos_total >= 35:
        print(tr("  🟡 TU PC PUEDE MEJORAR DECENTEMENTE"))
    else:
        print(tr("  🔵 TU PC ESTÁ MUY OPTIMIZADO"))
    print("═" * 58)
    print(tr("  Ejecuta 'main.py' como Administrador para aplicar las mejoras."))


def _barra_ascii(activo: int, total: int, ancho: int = 20) -> str:
    """Dibuja una barra de progreso en texto."""
    activo = max(0, min(activo, total))
    lleno = int(ancho * activo / total) if total else 0
    vacio = ancho - lleno
    return f"[{'█' * lleno}{'░' * vacio}] ({activo}/{total})"


if __name__ == "__main__":
    main()
