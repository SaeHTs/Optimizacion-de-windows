"""Genera icono.ico y splash.png desde una imagen suministrada."""
import os

from PIL import Image, ImageFilter

# Ruta a tu imagen de logo (obligatoria, debe existir)
# En la carpeta donde queremos generar el icono
RUTA_IMAGEN = ""  # <=== AJUSTA esto a tu archivo PNG/JPG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONDO_OSCURO = (13, 17, 23, 255)  # #0d1117

# 1) icono.ico — fondo oscuro, tamaños estándar de Windows
img = Image.open(RUTA_IMAGEN).convert("RGBA")
dimension_original = min(img.size)  # más pequeño para mantener nitidez
# Engrandecer solo si la imagen es pequeña (a 256 ya es suficiente para el ícono)
if dimension_original < 256:
    img_grande = img.resize((256, 256), Image.LANCZOS)
else:
    img_grande = img

# Filtro de nitidez para compensar el escalado
def nitidez(imagen, fuerza=100, radio=0.8):
    """UnsharpMask: aplica enfoque leve para bordes más definidos."""
    return imagen.filter(ImageFilter.UnsharpMask(radius=radio, percent=fuerza, threshold=1))

icono_base = Image.new("RGBA", (512, 512), FONDO_OSCURO)
logo_centrado = nitidez(img_grande.resize((256, 256), Image.LANCZOS))
icono_base.paste(logo_centrado, (128, 128), logo_centrado)
icono_base.save(os.path.join(BASE_DIR, "icono.ico"), format="ICO",
                sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
print("✅ icono.ico generado (nitidez aplicada)")

# 2) splash.png — AGRANDADO: 560x420 con más espacio para el logo
ancho, alto = 560, 420
s = Image.new("RGBA", (ancho, alto), FONDO_OSCURO)
logo_splash = nitidez(img_grande.resize((210, 210), Image.LANCZOS))
s.paste(logo_splash, ((ancho - 210) // 2, 50), logo_splash)
s.save(os.path.join(BASE_DIR, "splash.png"))
print(f"✅ splash.png generada ({ancho}x{alto}, nítida)")
