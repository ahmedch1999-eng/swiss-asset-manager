#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Erstelle virtuelle Umgebung..."
  python3 -m venv venv
fi

echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate || source venv/Scripts/activate

PORT=${PORT:-8000}
if lsof -iTCP:${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port ${PORT} belegt. Wechsle auf 8001."
  PORT=8001
fi
export PORT

if [ -f requirements.txt ]; then
  python -m pip install -U pip setuptools wheel >/dev/null 2>&1 || true
  python -m pip install -r requirements.txt || true
fi

echo "Starte Backup-App auf Port ${PORT}..."
python3 app.py.backup