"""🚀 Módulo 2: Optimización de programas de inicio."""
import os
import winreg

from config import ENTRADAS_INICIO_AUTO
from utils import confirmar, pausa

# Claves del registro que definen programas de inicio
CLAVES_INICIO = [
    ("Usuario", winreg.HKEY_CURRENT_USER,
     r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("Equipo", winreg.HKEY_LOCAL_MACHINE,
     r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("Equipo 32-bit", winreg.HKEY_LOCAL_MACHINE,
     r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
]

# Carpetas de inicio (accesos directos .lnk)
CARPETAS_INICIO = [
    os.path.join(os.environ.get("APPDATA", ""),
                 r"Microsoft\Windows\Start Menu\Programs\Startup"),
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp",
]

PREFIJO_DESHABILITADO = "DISABLED_"


# ---------------------------------------------------------------- listar
def listar() -> None:
    """Muestra todos los programas de inicio registrados."""
    print("\n📋 Programas de inicio (registro):")
    for etiqueta, raiz, clave in CLAVES_INICIO:
        try:
            with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                indice = 0
                while True:
                    try:
                        nombre, valor, _ = winreg.EnumValue(k, indice)
                        marca = "  ⏸️ " if nombre.startswith(
                            PREFIJO_DESHABILITADO) else "  • "
                        print(f"{marca}[{etiqueta}] {nombre}")
                        print(f"      → {valor}")
                        indice += 1
                    except OSError:
                        break
        except FileNotFoundError:
            pass

    print("\n📁 Carpetas de inicio (accesos directos):")
    for carpeta in CARPETAS_INICIO:
        if os.path.isdir(carpeta):
            archivos = sorted(os.listdir(carpeta))
            if archivos:
                print(f"  • {carpeta}")
                for archivo in archivos:
                    print(f"      → {archivo}")


# ---------------------------------------------------------------- operaciones
def _buscar_clave(nombre: str):
    """Busca en qué clave de inicio existe un valor. Devuelve (raiz, clave)."""
    for _, raiz, clave in CLAVES_INICIO:
        try:
            with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                winreg.QueryValueEx(k, nombre)
                return raiz, clave
        except (FileNotFoundError, OSError):
            continue
    return None


def deshabilitar() -> None:
    """Deshabilita una entrada de inicio (reversible: la renombra)."""
    listar()
    nombre = input("\nNombre exacto de la entrada a deshabilitar: ").strip()
    if not nombre:
        print("❌ Nombre vacío.")
        return

    ubicacion = _buscar_clave(nombre)
    if not ubicacion:
        print(f"❌ No se encontró la entrada '{nombre}'.")
        return

    raiz, clave = ubicacion
    try:
        with winreg.OpenKey(raiz, clave, 0,
                            winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            valor, tipo = winreg.QueryValueEx(k, nombre)
            nuevo_nombre = PREFIJO_DESHABILITADO + nombre
            winreg.SetValueEx(k, nuevo_nombre, 0, tipo, valor)
            winreg.DeleteValue(k, nombre)
        print(f"✅ '{nombre}' deshabilitado (se conserva como '{nuevo_nombre}').")
        print("   Para revertirlo, use la opción 'Habilitar entrada'.")
    except OSError as e:
        print(f"❌ Error: {e}")


def habilitar() -> None:
    """Revierte una entrada previamente deshabilitada."""
    listar()
    nombre = input("\nNombre de la entrada deshabilitada"
                   " (con prefijo DISABLED_): ").strip()
    if not nombre:
        print("❌ Nombre vacío.")
        return

    ubicacion = _buscar_clave(nombre)
    if not ubicacion:
        print(f"❌ No se encontró la entrada '{nombre}'.")
        return

    if not nombre.startswith(PREFIJO_DESHABILITADO):
        print("⚠️  Esa entrada no parece estar deshabilitada por esta herramienta.")
        if not confirmar("¿Habilitarla de todos modos?"):
            return
        nombre_original = nombre
    else:
        nombre_original = nombre[len(PREFIJO_DESHABILITADO):]

    raiz, clave = ubicacion
    try:
        with winreg.OpenKey(raiz, clave, 0,
                            winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            valor, tipo = winreg.QueryValueEx(k, nombre)
            winreg.SetValueEx(k, nombre_original, 0, tipo, valor)
            winreg.DeleteValue(k, nombre)
        print(f"✅ '{nombre_original}' habilitado de nuevo.")
    except OSError as e:
        print(f"❌ Error: {e}")


def deshabilitar_automatico() -> int:
    """Deshabilita las entradas de inicio seguras (por prefijo).

    Solo toca actualizadores y helpers del sistema listados en
    ENTRADAS_INICIO_AUTO. Revertible con 'Habilitar entrada'.
    """
    deshabilitadas = 0
    print("\n⚡ Modo automático: entradas de inicio seguras")
    for ambito, prefijo in ENTRADAS_INICIO_AUTO:
        for etiqueta, raiz, clave in CLAVES_INICIO:
            if etiqueta != ambito:
                continue
            try:
                with winreg.OpenKey(raiz, clave, 0, winreg.KEY_READ) as k:
                    entradas = []
                    indice = 0
                    while True:
                        try:
                            entradas.append(winreg.EnumValue(k, indice))
                            indice += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue

            for nombre, valor, tipo in entradas:
                if (nombre.startswith(prefijo)
                        and not nombre.startswith(PREFIJO_DESHABILITADO)):
                    try:
                        with winreg.OpenKey(
                            raiz, clave, 0, winreg.KEY_SET_VALUE
                        ) as k:
                            winreg.SetValueEx(
                                k, PREFIJO_DESHABILITADO + nombre,
                                0, tipo, valor,
                            )
                            winreg.DeleteValue(k, nombre)
                        print(f"  ⏸️  {nombre} → deshabilitado")
                        deshabilitadas += 1
                    except OSError:
                        pass
    if deshabilitadas == 0:
        print("  No se encontraron entradas seguras que deshabilitar.")
    else:
        print(f"✅ {deshabilitadas} entrada(s) deshabilitadas (reversible).")
    return deshabilitadas


# ---------------------------------------------------------------- automático
def modo_automatico(logger) -> None:
    """Optimiza el inicio deshabilitando entradas seguras."""
    print("\n" + "═" * 44)
    print("  ⚡ MODO AUTOMÁTICO — INICIO")
    print("═" * 44)
    deshabilitar_automatico()
    logger.info("Optimización automática de inicio completada")


# ---------------------------------------------------------------- menú
def menu_inicio(logger) -> None:
    while True:
        print("\n" + "═" * 44)
        print("  🚀 OPTIMIZAR PROGRAMAS DE INICIO")
        print("═" * 44)
        print("  1) 📋 Listar programas de inicio")
        print("  2) ⏸️  Deshabilitar una entrada")
        print("  3) ▶️  Habilitar una entrada")
        print("  4) ⚡ MODO AUTOMÁTICO (entradas seguras)")
        print("  0) ⬅️  Volver")
        print("═" * 44)

        opcion = input("Seleccione una opción: ").strip()
        if opcion == "1":
            listar()
        elif opcion == "2":
            deshabilitar()
        elif opcion == "3":
            habilitar()
        elif opcion == "4":
            modo_automatico(logger)
        elif opcion == "0":
            break
        else:
            print("❌ Opción no válida.")
        logger.info("Módulo de inicio ejecutado: opción %s", opcion)
        pausa()
