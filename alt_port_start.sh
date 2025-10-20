#!/bin/bash
echo "========================================"
echo "Swiss Asset Manager - Direktstart mit alternativem Port"
echo "========================================"

# Beende eventuell laufende Instanzen
pkill -f "python3 app.py" || true

# Starte die App mit optimierten Einstellungen
export FLASK_APP=app.py
export FLASK_ENV=production
export FLASK_DEBUG=0
export OPTIMIZE_STARTUP=1
export SKIP_PRELOAD=1
export PORT=8080  # Alternativer Port

# Starte den Server mit dem alternativen Port
echo "Server wird auf Port 8080 gestartet..."
cd "$(dirname "$0")"
python3 -c "
import app
import os
from flask import Flask
if __name__ == '__main__':
    app.app.run(host='0.0.0.0', port=8080, debug=False)
" &

# Warte kurz und öffne dann den Browser
sleep 2
echo "Öffne Browser..."
open http://localhost:8080

echo ""
echo "Server läuft im Hintergrund auf Port 8080."
echo "Passwort: swissassetmanagerAC"
echo "========================================"