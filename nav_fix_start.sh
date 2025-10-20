#!/bin/bash

# Swiss Asset Manager Navigation-Fix Starter
echo "=================================================="
echo "Swiss Asset Manager - Navigation-Fix Starter"
echo "=================================================="

# Beende laufende Prozesse
echo "Beende laufende Prozesse..."
pkill -f "python.*app.py" || true
sleep 1

# Stelle sicher, dass der Port frei ist
port=8000
is_port_free=$(lsof -i :$port | grep LISTEN)
if [ ! -z "$is_port_free" ]; then
    echo "Port $port ist bereits belegt, versuche ihn freizugeben..."
    kill -9 $(lsof -t -i:$port) 2>/dev/null || true
    sleep 1
fi

# Stelle sicher, dass das aktuelle Arbeitsverzeichnis korrekt ist
cd "$(dirname "$0")"

# Starte die App
echo "Starte Swiss Asset Manager..."
python3 app.py &

# Warte kurz, bis der Server bereit ist
echo "Warte auf Server-Start..."
sleep 2

# Öffne Browser
echo "Öffne Browser..."
open http://localhost:8000

echo ""
echo "Swiss Asset Manager läuft jetzt."
echo "Passwort: swissassetmanagerAC"
echo ""
echo "HINWEIS: Falls die Navigation nicht funktioniert, drücken Sie im"
echo "Browser F5, nachdem Sie sich angemeldet haben."
echo "=================================================="