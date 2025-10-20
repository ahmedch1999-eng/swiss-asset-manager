#!/bin/bash

# Sehr einfaches Startskript für Swiss Asset Manager
echo "=========================================="
echo "Swiss Asset Manager - Direktstart"
echo "=========================================="

# Beende laufende Prozesse
pkill -f "python.*app.py" || true
sleep 1

# Starte die App direkt im Vordergrund
cd "$(dirname "$0")"
echo "App wird gestartet... Bitte warten"
python3 app.py &

# Warte, bis der Server bereit ist
echo "Warte auf Server..."
sleep 3

# Öffne den Browser
echo "Öffne Browser..."
open http://localhost:8000

echo ""
echo "Passwort: swissassetmanagerAC"
echo "=========================================="