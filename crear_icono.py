"""Genera el ícono del ejecutable a partir de una imagen BMP/PNG.

Diseño: imagen en la parte superior y el texto 'optimización'
debajo, en un lienzo cuadrado con fondo transparente.

Uso: python crear_icono.py [ruta_imagen] [salida.ico]
Si no se indica una imagen, busca la primera imagen (.bmp/.png/.jpg)
en la carpeta del script.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

IMAGEN = None
SALIDA = None
if len(sys.argv) > 1:
    IMAGEN = sys.argv[1]
if len(sys.argv) > 2:
    SALIDA = sys.argv[2]
else:
    SALIDA = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "icono.ico"
    )

TEXTO = "optimización"
TAM = 256
FUENTES = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def cargar_fuente(tamano: int) -> ImageFont.FreeTypeFont:
    for ruta in FUENTES:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> None:
    global IMAGEN

    if not IMAGEN:
        # Busca una imagen junto al script como comodín
        aqui = os.path.dirname(os.path.abspath(__file__))
        for extension in ("bmp", "png", "jpg", "jpeg"):
            encontrados = sorted(
                f for f in os.listdir(aqui)
                if f.lower().endswith("." + extension)
            )
            if encontrados:
                IMAGEN = os.path.join(aqui, encontrados[0])
                break
    if not IMAGEN:
        print("Uso: python crear_icono.py [ruta_imagen] [salida.ico]")
        sys.exit(1)
    if not os.path.exists(IMAGEN):
        print(f"No se encontró la imagen: {IMAGEN}")
        sys.exit(1)

    # Imagen: escalada para ocupar la parte superior del ícono
    img = Image.open(IMAGEN).convert("RGBA")
    img.thumbnail((188, 188), Image.LANCZOS)

    canvas = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
    canvas.paste(img, ((TAM - img.width) // 2, 6), img)

    # Texto debajo del dibujo
    draw = ImageDraw.Draw(canvas)
    fuente = cargar_fuente(36)
    bbox = draw.textbbox((0, 0), TEXTO, font=fuente)
    ancho = bbox[2] - bbox[0]
    alto = bbox[3] - bbox[1]
    tx = (TAM - ancho) // 2 - bbox[0]
    ty = TAM - alto - 12 - bbox[1]

    # Contorno oscuro para legibilidad + texto blanca
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (1, 1), (-1, 1), (1, -1)):
        draw.text((tx + dx, ty + dy), TEXTO, font=fuente,
                  fill=(0, 0, 0, 220))
    draw.text((tx, ty), TEXTO, font=fuente, fill=(255, 255, 255, 255))

    canvas.save(
        SALIDA,
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Icono creado correctamente: {SALIDA}")


if __name__ == "__main__":
    main()
