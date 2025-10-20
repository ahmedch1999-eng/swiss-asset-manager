#!/bin/bash
# Helper to install Homebrew and pyenv on macOS and install Python 3.11

set -e

if [[ "$(uname)" != "Darwin" ]]; then
  echo "Dieses Skript ist für macOS (Darwin)." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew nicht gefunden. Installiere Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "Homebrew vorhanden. Aktualisiere..."
  brew update
fi

if ! command -v pyenv >/dev/null 2>&1; then
  echo "Installiere pyenv..."
  brew install pyenv
else
  echo "pyenv bereits installiert"
fi

echo 'Füge pyenv-Initialisierung zu ~/.zprofile und ~/.zshrc hinzu (wenn nicht bereits vorhanden)'
if ! grep -q "pyenv init" ~/.zprofile 2>/dev/null; then
  echo 'eval "$(pyenv init --path)"' >> ~/.zprofile
fi
if ! grep -q "pyenv init" ~/.zshrc 2>/dev/null; then
  echo 'eval "$(pyenv init -)"' >> ~/.zshrc
fi

echo "Starte Shell neu oder lade Profile: exec \$SHELL"
echo "Installiere Python 3.11.x via pyenv (falls nicht vorhanden)..."
# Install OS-level build dependencies that Python and SciPy need
echo "Stelle sicher, dass erforderliche Build-Tools vorhanden sind (xz, gcc)"
brew install xz || true
brew install gcc || true
brew install pkg-config || true

# Initialize pyenv in this script so we can immediately use it
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

PY311=$(pyenv install --list | grep -E "^\s*3\\.11\\.[0-9]+$" | tail -1 | tr -d ' ')
if [ -z "$PY311" ]; then
  echo "Konnte keine 3.11-Version finden via pyenv. Abbruch." >&2
  exit 1
fi

echo "Installiere Python $PY311 via pyenv (kann einige Minuten dauern)..."
pyenv install -s $PY311 || true
echo "Setze lokal Python $PY311 für dieses Verzeichnis"
pyenv local $PY311
echo "Fertig. Bitte führe nun: rm -rf venv && ./start_app.sh"
