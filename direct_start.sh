#!/bin/bash
echo "========================================"
echo "Swiss Asset Manager - Direktstart"
echo "========================================"

# Beende eventuell laufende Instanzen
pkill -f "python3 app.py" || true

# Starte die App mit optimierten Einstellungen
export FLASK_APP=app.py
export FLASK_ENV=production
export FLASK_DEBUG=0
export OPTIMIZE_STARTUP=1
export SKIP_PRELOAD=1

# Starte den Server
echo "Server wird gestartet..."
python3 app.py &

# Warte kurz und öffne dann den Browser
sleep 2
echo "Öffne Browser..."
open http://localhost:8000

echo ""
echo "Server läuft im Hintergrund."
echo "Passwort: swissassetmanagerAC"
echo "========================================"
