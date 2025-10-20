#!/usr/bin/env python3

"""
Einfacher direkter Starter für Swiss Asset Manager
- Keine komplexen Skripte
- Direkte Ausführung
- Fehlerbehandlung
"""

import os
import sys
import time
import subprocess
import webbrowser
from datetime import datetime

# Farben für Terminal-Ausgabe
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

print(f"{BLUE}========================================================{RESET}")
print(f"{BLUE}Swiss Asset Manager - Einfacher Starter{RESET}")
print(f"{BLUE}========================================================{RESET}")

# Definiere den Pfad zur App
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

if not os.path.exists(app_path):
    print(f"{RED}Fehler: app.py nicht gefunden!{RESET}")
    sys.exit(1)

# Füge Login-Screen zur App hinzu, falls er fehlt
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

modified = False

# Prüfe und korrigiere Login-Screen
if 'id="loginScreen"' not in content:
    print(f"{YELLOW}Füge Login-Screen zur App hinzu...{RESET}")
    
    login_html = """
    <div id="loginScreen" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
         background-color: #0A1429; z-index: 9999; justify-content: center; align-items: center; flex-direction: column;">
        <h2 style="color: white; margin-bottom: 20px;">Swiss Asset Manager</h2>
        <div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); width: 300px;">
            <h3 style="margin-top: 0; color: #0A1429;">Anmeldung</h3>
            <p>Bitte geben Sie Ihr Passwort ein, um fortzufahren.</p>
            <input type="password" id="passwordInput" placeholder="Passwort" style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px;">
            <button onclick="checkPassword()" style="background: #0A1429; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; width: 100%;">Anmelden</button>
            <p id="loginError" style="color: red; margin-top: 10px; display: none;">Falsches Passwort. Bitte versuchen Sie es erneut.</p>
        </div>
    </div>

    <script>
    // Login-Funktion
    function checkPassword() {
        const password = document.getElementById('passwordInput').value;
        if (password === "swissassetmanagerAC") {
            document.getElementById('loginScreen').style.display = 'none';
            document.body.style.overflow = 'auto';
        } else {
            document.getElementById('loginError').style.display = 'block';
        }
    }
    
    // Event-Listener für Enter-Taste
    document.addEventListener('DOMContentLoaded', function() {
        const passwordInput = document.getElementById('passwordInput');
        if (passwordInput) {
            passwordInput.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    checkPassword();
                }
            });
            setTimeout(function() {
                passwordInput.focus();
            }, 300);
        }
    });
    </script>
    """
    
    if '</body>' in content:
        content = content.replace('</body>', f"{login_html}\n</body>")
        modified = True
        print(f"{GREEN}✓ Login-Screen hinzugefügt{RESET}")

if modified:
    # Backup erstellen
    backup_path = f"{app_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.backup"
    print(f"{YELLOW}Erstelle Backup: {backup_path}{RESET}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Aktualisierte Datei speichern
    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)

# Beende laufende Instanzen
print(f"{YELLOW}Beende laufende Instanzen...{RESET}")
subprocess.run(["pkill", "-f", "python.*app.py"], stderr=subprocess.DEVNULL)
time.sleep(1)  # Kurz warten

# Überprüfe, ob Port 8000 verfügbar ist
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port_available = True
try:
    s.bind(('127.0.0.1', 8000))
except socket.error:
    port_available = False
finally:
    s.close()

port = 8000 if port_available else 8080

# Starte die App
print(f"{YELLOW}Starte Swiss Asset Manager auf Port {port}...{RESET}")
os.environ["FLASK_APP"] = "app.py"
os.environ["FLASK_ENV"] = "production"
os.environ["FLASK_DEBUG"] = "0"

# Prozess im Hintergrund starten
with open(os.devnull, 'w') as devnull:
    cmd = [sys.executable, "-c", f"""
import os
import app
if __name__ == '__main__':
    app.app.run(host='0.0.0.0', port={port}, debug=False)
"""]
    
    process = subprocess.Popen(cmd, 
                             stdout=devnull,
                             stderr=devnull,
                             cwd=os.path.dirname(os.path.abspath(__file__)))

# Warte kurz und prüfe, ob der Server läuft
time.sleep(2)

# Versuche, eine Verbindung herzustellen
connection_successful = False
for _ in range(3):  # 3 Versuche
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(('127.0.0.1', port))
        s.close()
        connection_successful = True
        break
    except:
        time.sleep(1)

if connection_successful:
    print(f"{GREEN}✅ Server erfolgreich gestartet!{RESET}")
    url = f"http://localhost:{port}"
    print(f"{BLUE}Öffne Browser unter: {url}{RESET}")
    print(f"{BLUE}Passwort: swissassetmanagerAC{RESET}")
    webbrowser.open(url)
else:
    print(f"{RED}❌ Server konnte nicht gestartet werden!{RESET}")
    print(f"{YELLOW}Bitte starten Sie die App manuell mit:{RESET}")
    print(f"python3 app.py")

print(f"{BLUE}========================================================{RESET}")