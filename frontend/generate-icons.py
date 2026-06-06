"""Generate PWA icons - run with Pillow"""
import os

SIZES = [48, 72, 96, 144, 180, 192, 512]
OUT_DIR = os.path.join(os.path.dirname(__file__), 'public', 'icons')
os.makedirs(OUT_DIR, exist_ok=True)

try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (512, 512), (25, 137, 250, 255))
    draw = ImageDraw.Draw(img)
    # Simple house icon
    draw.polygon([(100, 240), (256, 80), (412, 240)], fill=(255, 255, 255, 60))
    draw.rectangle([120, 240, 220, 380], fill=(255, 255, 255, 60))
    draw.rectangle([292, 240, 392, 380], fill=(255, 255, 255, 60))
    draw.rectangle([155, 310, 205, 380], fill=(25, 137, 250, 255))
    draw.rectangle([327, 310, 377, 380], fill=(25, 137, 250, 255))

    for size in SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        path = os.path.join(OUT_DIR, f'icon-{size}.png')
        resized.save(path, 'PNG')
        print(f'  OK icon-{size}.png')

    print(f'Done: {len(SIZES)} icons generated')
except ImportError:
    print('Pillow not installed. Install: pip install Pillow')
    print('Or manually place PNG icons in public/icons/')
