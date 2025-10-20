#!/bin/bash

# Swiss Asset Manager - Startup Script mit verbesserter Thread-Behandlung
# Dieses Skript aktualisiert alle Pakete und startet die Anwendung
# Es stellt sicher, dass alle Threads sauber beendet werden

echo "==============================================="
echo "Swiss Asset Manager - 🔴 LIVE-Daten Version"
echo "==============================================="

# Prüfe, ob Python installiert ist
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 ist nicht installiert. Bitte installieren Sie Python 3."
    exit 1
fi

# Erstelle virtuelle Umgebung, falls nicht vorhanden
if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

# Aktiviere virtuelle Umgebung
echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate || source venv/Scripts/activate

# Aktualisiere Pakete
echo "Installiere/aktualisiere Pakete..."
pip install --upgrade pip
pip install -r requirements.txt

# Stoppe eventuell laufende Instanzen
echo "Prüfe auf laufende Instanzen..."
if pgrep -f "python.*app.py" > /dev/null; then
    echo "Beende laufende Instanzen..."
    pkill -f "python.*app.py"
    sleep 2
fi

# Starte die Anwendung
echo "==============================================="
echo "🚀 Starte Swiss Asset Manager mit Live-Daten"
echo "==============================================="

# Trap für sauberes Beenden bei CTRL+C
trap cleanup INT TERM
cleanup() {
    echo -e "\n💤 Anwendung wird beendet..."
    if pgrep -f "python.*app.py" > /dev/null; then
        pkill -f "python.*app.py"
    fi
    deactivate
    exit 0
}

# Anwendung im Vordergrund starten, um CTRL+C zu ermöglichen
python app.py

# Falls wir hier ankommen, wurde die App regulär beendet
cleanup