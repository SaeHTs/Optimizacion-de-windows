"""Pruebas del centro de mando HUD.

Se ejecutan con:  python -m pytest test_hud.py -v
o directamente:  python test_hud.py

Cubren la lógica que se puede probar sin mirar la pantalla: la paleta,
la fórmula de salud, la antigüedad del último mantenimiento y la
construcción de los widgets (Tk real, ventana oculta).
"""
import os
import sys
import tkinter as tk
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)


# --------------------------------------------------------------- tema
def test_color_salud_por_tramos():
    """El anillo cambia de color en los umbrales 40 y 70."""
    from modules.hud.tema import AMARILLO, CIAN, MAGENTA, color_salud

    assert color_salud(0) == MAGENTA
    assert color_salud(39) == MAGENTA
    assert color_salud(40) == AMARILLO
    assert color_salud(70) == AMARILLO
    assert color_salud(71) == CIAN
    assert color_salud(100) == CIAN


def test_la_paleta_es_la_de_la_especificacion():
    """Los colores viven en un solo sitio y son los pedidos."""
    from modules.hud import tema

    assert tema.FONDO == "#0A0A12"
    assert tema.BARRA == "#0F0F1C"
    assert tema.LATERAL == "#0D0D19"
    assert tema.PANEL == "#12121F"
    assert tema.BORDE == "#24243A"
    assert tema.CIAN == "#00F0FF"
    assert tema.MAGENTA == "#FF2BD6"
    assert tema.AMARILLO == "#FFE600"
    assert tema.TEXTO == "#E6E8F5"
    assert tema.TEXTO_SEC == "#8A8FA8"


def test_las_fuentes_son_monoespaciadas():
    """Números y etiquetas usan la monoespaciada con su tamaño."""
    from modules.hud.tema import FUENTE_MONO, fuente

    assert fuente(20, True) == (FUENTE_MONO, 20, "bold")
    assert fuente(9) == (FUENTE_MONO, 9)


# --------------------------------------------------------------- salud
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

    assert penalizacion_ram(30) == 0
    assert penalizacion_ram(50) == 0
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
    # Un dato que no se pudo medir no penaliza: no se inventan valores.
    assert calcular_salud(None, None, None, None) == 100


def test_calcular_salud_nunca_sale_del_rango():
    from modules.hud.datos import calcular_salud

    for gb in (0, 1, 5, 99):
        for inicio in (0, 3, 50):
            for ram in (0, 55, 99):
                for dias in (None, 0, 30, 900):
                    valor = calcular_salud(gb, inicio, ram, dias)
                    assert 0 <= valor <= 100


# --------------------------------------------------------------- mantenimiento
def test_dias_desde_ultimo_log(tmp_path):
    """La antigüedad del mantenimiento sale del log más reciente."""
    from modules.hud.datos import dias_desde_ultimo_log

    assert dias_desde_ultimo_log(str(tmp_path)) is None

    hace = datetime.now() - timedelta(days=7)
    (tmp_path / f"optimizador-{hace:%Y-%m-%d}.log").write_text("x", encoding="utf-8")
    assert dias_desde_ultimo_log(str(tmp_path)) == 7

    hoy = tmp_path / f"optimizador-{datetime.now():%Y-%m-%d}.log"
    hoy.write_text("x", encoding="utf-8")
    assert dias_desde_ultimo_log(str(tmp_path)) == 0


def test_un_log_vacio_no_cuenta_como_mantenimiento(tmp_path):
    """Un log de 0 bytes se crea al abrir el registro, no al optimizar.

    Si contara, la tarjeta diría "Hoy" tras una operación cancelada.
    """
    from modules.hud.datos import dias_desde_ultimo_log

    vacio = tmp_path / f"optimizador-{datetime.now():%Y-%m-%d}.log"
    vacio.write_text("", encoding="utf-8")
    assert dias_desde_ultimo_log(str(tmp_path)) is None

    vacio.write_text("contenido real", encoding="utf-8")
    assert dias_desde_ultimo_log(str(tmp_path)) == 0


def test_un_nombre_de_log_raro_no_rompe():
    """Ficheros que no siguen el patrón se ignoran sin excepción."""
    from modules.hud.datos import dias_desde_ultimo_log

    assert dias_desde_ultimo_log(os.path.join(RAIZ, "no_existe_esta_carpeta")) is None


# --------------------------------------------------------------- widgets
# Una sola raíz de Tk para todas las pruebas del módulo: crear y destruir
# varias raíces en el mismo proceso deja el intérprete de Tcl inservible
# ("Can't find a usable init.tcl"). Se coloca fuera de la pantalla para
# que los eventos de ratón se despachen sin que la ventana moleste.
_RAIZ = None


def _raiz():
    global _RAIZ
    if _RAIZ is None:
        _RAIZ = tk.Tk()
        _RAIZ.geometry("+4000+4000")
        _RAIZ.update()
    return _RAIZ


def test_el_medidor_fija_el_valor_sin_animar():
    from modules.hud.medidor import MedidorSalud

    medidor = MedidorSalud(_raiz())
    try:
        medidor.set_valor(72, animar=False)
        assert medidor.valor == 72
        medidor.set_valor(150, animar=False)
        assert medidor.valor == 100
        medidor.set_valor(-5, animar=False)
        assert medidor.valor == 0
    finally:
        medidor.destroy()


def test_la_tarjeta_muestra_analizando_y_valor():
    from modules.hud.tarjeta import Tarjeta

    tarjeta = Tarjeta(_raiz(), "Disco", "#00F0FF")
    try:
        tarjeta.set_analizando(True)
        assert tarjeta.etiqueta_valor.cget("text") != ""
        tarjeta.set_analizando(False)
        tarjeta.set_valor("12,4 GB")
        assert tarjeta.etiqueta_valor.cget("text") == "12,4 GB"
    finally:
        tarjeta.destroy()


def test_la_tarjeta_avisa_del_clic():
    from modules.hud.tarjeta import Tarjeta

    pulsada = []
    tarjeta = Tarjeta(_raiz(), "Inicio", "#FF2BD6")
    try:
        tarjeta.pack()
        _raiz().update()
        tarjeta.al_clic(lambda: pulsada.append(True))
        tarjeta.event_generate("<Button-1>", x=5, y=5)
        _raiz().update()
        assert pulsada == [True]
    finally:
        tarjeta.destroy()


def test_el_boton_principal_y_el_secundario():
    from modules.hud.boton import BotonHUD
    from modules.hud.tema import CIAN, MAGENTA, PANEL

    principal = BotonHUD(_raiz(), "Optimizar ahora", lambda: None)
    secundario = BotonHUD(_raiz(), "Deshacer", lambda: None, variante="secundario")
    try:
        assert principal.cget("bg") == CIAN
        assert secundario.cget("highlightbackground") == MAGENTA
        assert secundario.cget("bg") == PANEL
    finally:
        principal.destroy()
        secundario.destroy()


def test_la_barra_lateral_marca_el_activo():
    from modules.hud.lateral import BarraLateral

    barra = BarraLateral(_raiz(), [
        ("panel", "Panel", lambda: None, "#00F0FF"),
        ("SECCION:Informes", "", None, ""),
        ("limpieza", "Limpieza", lambda: None, "#E6E8F5"),
    ])
    try:
        barra.seleccionar("limpieza")
        assert barra.activo == "limpieza"
        barra.seleccionar("panel")
        assert barra.activo == "panel"
    finally:
        barra.destroy()


def test_la_barra_superior_muestra_auto_solo_si_es_automatico():
    from modules.hud.superior import BarraSuperior

    barra = BarraSuperior(
        _raiz(), "Optimizador // Windows 11", "es", True, lambda i: None,
    )
    try:
        assert barra.texto_auto.cget("text") != ""
        barra.actualizar("en", False)
        assert barra.texto_auto.cget("text") == ""
    finally:
        barra.destroy()


if __name__ == "__main__":
    fallos = 0
    for nombre, funcion in sorted(globals().items()):
        if nombre.startswith("test_") and callable(funcion):
            try:
                if funcion.__code__.co_argcount == 1:
                    import tempfile

                    with tempfile.TemporaryDirectory() as tmp:
                        funcion(type("P", (), {"__fspath__": lambda s: tmp,
                                               "__str__": lambda s: tmp})())
                else:
                    funcion()
                print("OK   %s" % nombre)
            except AssertionError as e:
                fallos += 1
                print("FALLA %s: %s" % (nombre, e))
    raise SystemExit(1 if fallos else 0)
