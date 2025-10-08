#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import io

# Farben aus der Anwendung
BACKGROUND_COLOR = (10, 10, 10)  # --base-black: #0A0A0A
ACCENT_COLOR = (138, 43, 226)    # --accent-violet: #8A2BE2

def create_icon(size, output_path):
    """Erstellt ein einfaches Icon mit 'S' in der Mitte."""
    # Icon erstellen
    icon = Image.new('RGB', (size, size), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(icon)
    
    # Hintergrund-Kreis
    circle_radius = int(size * 0.45)
    center = (size // 2, size // 2)
    draw.ellipse(
        (center[0] - circle_radius, center[1] - circle_radius, 
         center[0] + circle_radius, center[1] + circle_radius), 
        fill=ACCENT_COLOR
    )
    
    # Text hinzufügen
    try:
        # Versuche, eine Schriftart zu laden
        font_size = int(size * 0.5)
        try:
            font = ImageFont.truetype("Arial", font_size)
        except:
            font = ImageFont.load_default()
            
        text = "S"
        # Textbreite und -höhe berechnen
        text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else (font_size, font_size)
        
        # Text zentrieren
        draw.text(
            (center[0] - text_width // 2, center[1] - text_height // 2),
            text,
            fill="white",
            font=font
        )
    except Exception as e:
        # Falls Schriftart nicht funktioniert, füge einen weißen Kreis ein
        inner_circle_radius = int(size * 0.2)
        draw.ellipse(
            (center[0] - inner_circle_radius, center[1] - inner_circle_radius, 
             center[0] + inner_circle_radius, center[1] + inner_circle_radius), 
            fill="white"
        )
    
    # Icon speichern
    icon.save(output_path, 'PNG')
    print(f"Icon erstellt: {output_path}")

# Icons erstellen
if not os.path.exists("static"):
    os.makedirs("static")

create_icon(192, "static/icon-192x192.png")
create_icon(512, "static/icon-512x512.png")