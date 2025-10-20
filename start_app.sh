#!/bin/bash

# Swiss Asset Manager - Startup Script mit Live-Daten
# Dieses Skript aktualisiert alle Pakete und startet die Anwendung

echo "==============================================="
echo "Swiss Asset Manager - 🔴 LIVE-Daten Version (Backup als Standard)"
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

# Lade Umgebungsvariablen aus .env, falls vorhanden (inkl. APP_PASSWORD)
if [ -f ".env" ]; then
    echo "Lade Umgebungsvariablen aus .env..."
    set -a
    source .env
    set +a
fi

# Prüfe Python Version der venv
PY_VER=$(python3 -c 'import sys; print("{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))')
echo "Virtuelle Umgebung verwendet Python ${PY_VER}"
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

# Wenn Python-Version nicht 3.11.x ist, versuche pyenv zu verwenden, um 3.11 zu installieren und venv neu zu erstellen
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -ne 11 ]; then
    echo "Die venv-Python-Version ist nicht 3.11 (empfohlen)."
    if command -v pyenv >/dev/null 2>&1; then
        echo "pyenv gefunden. Versuche, Python 3.11 zu installieren und venv neu zu erstellen..."
        PY311=$(pyenv install --list | grep -E "^\s*3\\.11\\.[0-9]+$" | tail -1 | tr -d ' ')
        if [ -z "$PY311" ]; then
            echo "Konnte keine 3.11-Version über pyenv finden. Bitte installiere pyenv oder setze Python manuell auf 3.11." >&2
        else
            echo "Installiere Python $PY311 via pyenv (kann einige Minuten dauern)..."
            pyenv install -s $PY311 || true
            # Nutze pyenv local für dieses Projekt
            pyenv local $PY311
            echo "Erstelle venv mit Python $PY311..."
            deactivate || true
            rm -rf venv
            python3 -m venv venv
            source venv/bin/activate || source venv/Scripts/activate
            python3 -V
        fi
    else
        echo "pyenv nicht gefunden. Um automatisch auf Python 3.11 zu wechseln, installiere pyenv (empfohlen)." >&2
        echo "Anleitung: https://github.com/pyenv/pyenv#installation" >&2
    fi
fi

# Aktualisiere Pakete (inkl. setuptools/wheel um Build-Probleme zu reduzieren)
echo "Installiere/aktualisiere Pakete..."
python3 -m pip install --upgrade pip setuptools wheel
if ! python3 -m pip install -r requirements.txt; then
    echo "\nFehler beim Installieren der Anforderungen. Wenn Fehlermeldungen beim Build von numpy/anderen Paketen auftreten, verwende Python 3.11 (empfohlen)." >&2
    echo "Siehe README oder frage mich, ich helfe beim Umstieg auf Python 3.11." >&2
    deactivate || true
    exit 1
fi

# Versuche, einen freien Port zu finden (8000, dann 8001)
PORT=8000
if lsof -iTCP:${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port ${PORT} in Benutzung, versuche ${PORT:-8001}..."
    PORT=8001
    if lsof -iTCP:${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Ports 8000 und 8001 sind belegt. Bitte beende den laufenden Dienst oder passe das Skript an." >&2
        deactivate || true
        exit 1
    fi
fi

export PORT

# Wähle Entry-Point (standardmäßig app.py, das die Backup-Version lädt)
APP_ENTRY=${APP_ENTRY:-app.py}
if [ ! -f "$APP_ENTRY" ]; then
    echo "Warnung: $APP_ENTRY nicht gefunden. Fallback auf app.py" >&2
    APP_ENTRY=app.py
fi
echo "==============================================="
echo "🚀 Starte Swiss Asset Manager (${APP_ENTRY}) auf Port ${PORT}"
echo "==============================================="
python3 "$APP_ENTRY"

# Deaktiviere virtuelle Umgebung beim Beenden
deactivate || true