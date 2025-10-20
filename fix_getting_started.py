#!/usr/bin/env python3
# Script um den Getting Started Content aus dem Static HTML zu entfernen

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Finde den Start des Contents
start_marker = '                    <div class="gs-content-placeholder" id="gsPageContent" style="text-align: left; color: #333333; font-size: 16px; padding: 0; width: calc(100% + 60px); margin: -30px -30px 0 -30px;">\n                        <!-- Content wird durch JavaScript geladen -->'

# Finde das Ende (vor dem EDITABLE SECTION END Kommentar)
end_marker = '\n                    </div>\n                    \n                    <!-- ============================================================================ -->\n                    <!-- ✏️ EDITABLE SECTION END -->'

if start_marker in content and end_marker in content:
    # Finde die Positionen
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos < end_pos:
        # Entferne alles zwischen start und end, behalte nur den Platzhalter
        new_content = (
            content[:start_pos + len(start_marker)] +
            content[end_pos:]
        )
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Getting Started Content erfolgreich entfernt!")
        print(f"Entfernte Zeichen: {end_pos - (start_pos + len(start_marker))}")
    else:
        print("❌ Fehler: End-Marker vor Start-Marker gefunden")
else:
    print("❌ Fehler: Marker nicht gefunden")
    print(f"Start-Marker gefunden: {start_marker in content}")
    print(f"End-Marker gefunden: {end_marker in content}")


