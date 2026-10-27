"""⏪ Módulo de rollback: registra los cambios y permite deshacerlos.

Cada cambio reversible (servicio deshabilitado, tarea desactivada,
valor de registro modificado) se apunta en ``logs/rollback.json``
ANTES de aplicarse. ``deshacer()`` recorre el registro y restaura
cada valor a su estado previo.
"""
import json
import os
import winreg

from i18n import tr

from utils import BASE_DIR, ejecutar_powershell

RUTA = os.path.join(BASE_DIR, "logs", "rollback.json")

_RAIICES = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}


def _cargar() -> dict:
    try:
        with open(RUTA, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        datos = {}
    datos.setdefault("servicios", {})
    datos.setdefault("tareas", [])
    datos.setdefault("registro", [])
    return datos


def _guardar(datos: dict) -> None:
    try:
        os.makedirs(os.path.dirname(RUTA), exist_ok=True)
        tmp = RUTA + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, RUTA)
    except OSError as e:
        # El cambio se aplicará igual, pero SIN registro de deshacer:
        # avisar es la única forma honesta de decirlo (no cortar
        # la optimización a mitad por esto).
        print(tr("⚠️  No se pudo guardar el registro de deshacer: {e}").format(e=e))
        print(tr("    Los cambios se aplican, pero 'Deshacer' no los verá."))


def registrar_servicio(nombre: str, inicio_previo: str) -> None:
    """Apunta el StartupType previo (no se pisa si ya estaba apuntado)."""
    datos = _cargar()
    datos["servicios"].setdefault(nombre, inicio_previo or "Manual")
    _guardar(datos)


def registrar_tarea(ruta: str, nombre: str) -> None:
    datos = _cargar()
    entrada = {"path": ruta, "name": nombre}
    if entrada not in datos["tareas"]:
        datos["tareas"].append(entrada)
        _guardar(datos)


def registrar_registro(raiz: str, subclave: str, valor: str, previo) -> None:
    """Apunta el valor previo de una clave (None = no existía)."""
    datos = _cargar()
    entrada = {"raiz": raiz, "subclave": subclave, "valor": valor, "previo": previo}
    for vieja in datos["registro"]:
        if (vieja["raiz"], vieja["subclave"], vieja["valor"]) == (raiz, subclave, valor):
            return  # ya registrada: el valor previo correcto es el primero
    datos["registro"].append(entrada)
    _guardar(datos)


def hay_cambios() -> bool:
    datos = _cargar()
    return bool(datos["servicios"] or datos["tareas"] or datos["registro"])


def deshacer() -> tuple[int, int]:
    """Restaura todos los cambios registrados. Devuelve (ok, errores)."""
    datos = _cargar()
    ok = 0
    errores = 0

    for nombre, inicio_previo in datos["servicios"].items():
        # -ErrorAction Stop: el código de salida refleja el fallo real
        # (con SilentlyContinue un error contaba como "restaurado" y
        # se borraba el registro de deshacer sin haber restaurado nada).
        codigo, _salida = ejecutar_powershell(
            f"Set-Service -Name '{nombre}' -StartupType {inicio_previo} "
            "-ErrorAction Stop"
        )
        if codigo == 0:
            print(tr("  ↩️  Servicio {nombre}: vuelve a {inicio_previo}").format(
                nombre=nombre, inicio_previo=inicio_previo))
            ok += 1
        else:
            print(tr("  ⚠️  No se pudo restaurar el servicio {nombre}").format(nombre=nombre))
            errores += 1

    for tarea in datos["tareas"]:
        codigo, _salida = ejecutar_powershell(
            f"Enable-ScheduledTask -TaskName '{tarea['name']}' "
            f"-TaskPath '{tarea['path']}' -ErrorAction Stop"
        )
        if codigo == 0:
            print(tr("  ↩️  Tarea {nombre}: habilitada de nuevo").format(
                nombre=tarea["name"]))
            ok += 1
        else:
            print(tr("  ⚠️  No se pudo restaurar la tarea {nombre}").format(
                nombre=tarea["name"]))
            errores += 1

    for entrada in datos["registro"]:
        try:
            raiz = _RAIICES[entrada["raiz"]]
            with winreg.CreateKey(raiz, entrada["subclave"]) as k:
                if entrada["previo"] is None:
                    winreg.DeleteValue(k, entrada["valor"])
                else:
                    winreg.SetValueEx(k, entrada["valor"], 0,
                                      winreg.REG_DWORD, entrada["previo"])
            print(tr("  ↩️  Registro {nombre}: restaurado").format(
                nombre=entrada["valor"]))
            ok += 1
        except OSError:
            print(tr("  ⚠️  No se pudo restaurar {nombre}").format(
                nombre=entrada["valor"]))
            errores += 1

    if errores == 0:
        try:
            os.remove(RUTA)
        except OSError:
            pass
    return ok, errores
