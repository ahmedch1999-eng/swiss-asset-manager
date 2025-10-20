#!/bin/bash

# Swiss Asset Manager - Optimierter Startup
# Dieses Skript startet die Anwendung mit optimierten Einstellungen für schnellere Ladezeiten

echo "==============================================="
echo "Swiss Asset Manager - 🚀 OPTIMIERTE VERSION"
echo "==============================================="

# Prüfe, ob Python installiert ist
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 ist nicht installiert. Bitte installieren Sie Python 3."
    exit 1
fi

# Systemdiagnose
echo "Systemprüfung..."
free_memory=$(vm_stat | grep "Pages free" | grep -o "[0-9]\+" | head -1)
free_memory_mb=$(( $free_memory * 4096 / 1024 / 1024 ))
echo "- Freier Speicher: $free_memory_mb MB"

# Beende alle vorhandenen Instanzen der App
echo "Beende vorhandene Instanzen..."
pkill -f "python.*app.py" || true
sleep 1

# Lösche temporäre Dateien
echo "Räume auf..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +; 2>/dev/null || true

# Bereite Logs vor
mkdir -p logs
echo "App Start: $(date)" > logs/startup.log

# Erstelle virtuelle Umgebung, falls nicht vorhanden
if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

# Aktiviere virtuelle Umgebung
echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate || source venv/Scripts/activate

# Aktualisiere grundlegende Pakete
echo "Installiere/aktualisiere wichtige Pakete..."
pip install --upgrade pip > logs/pip.log 2>&1
pip install flask numpy pandas > logs/pip.log 2>&1

# Führe Diagnose aus
echo "Führe Diagnose aus..."
python diagnose.py > logs/diagnose.log 2>&1 || true

# Optimiere Cache
echo "Optimiere Cache..."
python -c "import cache_manager; print('Cache optimiert')" > logs/cache_opt.log 2>&1 || true

# Starte die Anwendung mit optimierten Einstellungen
echo "==============================================="
echo "🚀 Starte Swiss Asset Manager - Optimiert"
echo "==============================================="
echo "URL: http://localhost:8000"
echo "Passwort: swissassetmanagerAC"
echo "-----------------------------------------------"
echo "Bitte warten, Anwendung wird initialisiert..."

FLASK_ENV=production PYTHONOPTIMIZE=1 python app.py > logs/app.log 2>&1 &

# Prüfe, ob App gestartet ist
sleep 3
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✅ Swiss Asset Manager wurde erfolgreich gestartet!"
    echo "Drücken Sie Ctrl+C, um diesen Log zu verlassen (App läuft weiter)"
    echo "-----------------------------------------------"
    echo "Um die App zu stoppen, nutzen Sie: pkill -f 'python.*app.py'"
    
    # Zeige die App-Logs an
    tail -f logs/app.log
else
    echo "❌ Fehler beim Starten der Swiss Asset Manager App!"
    echo "Prüfen Sie die Logs für weitere Details: logs/app.log"
fi