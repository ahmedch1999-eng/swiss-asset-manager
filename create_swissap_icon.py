#!/usr/bin/env python3
"""
Erstellt Swiss Asset Pro Icons mit weißem Hintergrund und schwarzer Schrift "SwissAP"
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Erstellt ein Icon in der angegebenen Größe"""
    # Dunkelbrauner Hintergrund (#5d4037)
    img = Image.new('RGB', (size, size), color='#5d4037')
    draw = ImageDraw.Draw(img)
    
    # Kein Rand mehr (sieht cleaner aus)
    
    # Text "SwissAP"
    # Font-Größe basierend auf Icon-Größe (KLEINER)
    font_size = size // 5  # Kleiner: von 4 auf 5
    
    try:
        # Versuche Helvetica Bold zu laden (macOS)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        try:
            # Fallback: Arial Bold
            font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
        except:
            # Fallback: Default
            font = ImageFont.load_default()
    
    # Text zentrieren
    text = "SwissAP"
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position berechnen (zentriert)
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - (font_size // 8)  # Leicht nach oben
    
    # Text zeichnen (WEISS)
    draw.text((x, y), text, fill='white', font=font)
    
    # Speichern
    output_path = os.path.join('static', filename)
    img.save(output_path, 'PNG', quality=95)
    print(f"✅ {filename} erstellt ({size}x{size})")

def main():
    """Erstellt alle benötigten Icon-Größen"""
    
    # Sicherstellen dass static/ existiert
    os.makedirs('static', exist_ok=True)
    
    # Alle benötigten Größen
    sizes = [
        (72, 'icon-72x72.png'),
        (96, 'icon-96x96.png'),
        (128, 'icon-128x128.png'),
        (144, 'icon-144x144.png'),
        (152, 'icon-152x152.png'),
        (180, 'apple-touch-icon.png'),  # iOS Standard
        (192, 'icon-192x192.png'),
        (384, 'icon-384x384.png'),
        (512, 'icon-512x512.png')
    ]
    
    print("🎨 Erstelle Swiss Asset Pro Icons...")
    print("=" * 50)
    
    for size, filename in sizes:
        create_icon(size, filename)
    
    print("=" * 50)
    print("✅ ALLE Icons erfolgreich erstellt!")
    print("\nIcons befinden sich in: ./static/")
    print("\nDesign:")
    print("  - Hintergrund: Dunkelbraun (#5d4037)")
    print("  - Text: Weiß")
    print("  - Schrift: SwissAP (kleiner)")
    print("  - Kein Rand (clean)")

if __name__ == '__main__':
    main()

