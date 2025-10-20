#!/usr/bin/env python3

"""
Login-Screen-Fixer für Swiss Asset Manager
Dieses Skript repariert spezifisch das Login-Screen-Problem
"""

import os
import sys
import re
import shutil
from datetime import datetime

# Farben für die Ausgabe
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

print(f"{BLUE}========================================================{RESET}")
print(f"{BLUE}Swiss Asset Manager - Login Screen Fix{RESET}")
print(f"{BLUE}========================================================{RESET}")

# Pfad zur app.py
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

# Prüfen, ob die Datei existiert
if not os.path.exists(app_path):
    print(f"{RED}Error: app.py nicht gefunden!{RESET}")
    sys.exit(1)

# Backup erstellen
backup_path = f"{app_path}.login_fix_backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
print(f"{YELLOW}Erstelle Backup: {backup_path}{RESET}")
shutil.copy2(app_path, backup_path)

# Datei lesen
print(f"{YELLOW}Analysiere app.py...{RESET}")
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Spezifische Probleme suchen und beheben
fixes = 0

# Fix 1: Login-Screen HTML einfügen, wenn er fehlt
if 'id="loginScreen"' not in content:
    print(f"{YELLOW}Problem gefunden: Login-Screen HTML fehlt{RESET}")
    
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
    """
    
    if '</body>' in content:
        content = content.replace('</body>', f"{login_html}\n</body>")
        print(f"{GREEN}✓ Login-Screen HTML eingefügt{RESET}")
        fixes += 1
    else:
        print(f"{RED}Error: Konnte </body> Tag nicht finden{RESET}")

# Fix 2: Login JavaScript-Funktion einfügen oder korrigieren
if 'function checkPassword()' not in content:
    print(f"{YELLOW}Problem gefunden: Login-Funktion fehlt{RESET}")
    
    login_js = """
    <script>
    // Login-Funktion
    function checkPassword() {
        const password = document.getElementById('passwordInput').value;
        if (password === "swissassetmanagerAC") {
            document.getElementById('loginScreen').style.display = 'none';
            document.body.style.overflow = 'auto';
            // Erfolgreiche Anmeldung
            console.log('Anmeldung erfolgreich');
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
            // Fokus auf das Passwort-Feld setzen
            setTimeout(function() {
                passwordInput.focus();
            }, 500);
        }
    });
    </script>
    """
    
    if '</body>' in content:
        content = content.replace('</body>', f"{login_js}\n</body>")
        print(f"{GREEN}✓ Login-Funktion eingefügt{RESET}")
        fixes += 1
    else:
        print(f"{RED}Error: Konnte </body> Tag nicht finden{RESET}")

# Fix 3: Stelle sicher, dass das Passwort korrekt definiert ist
password_pattern = r'PASSWORD\s*=\s*["\']swissassetmanagerAC["\']'
if not re.search(password_pattern, content):
    print(f"{YELLOW}Problem gefunden: Passwort nicht korrekt definiert{RESET}")
    
    # Suche nach einer PASSWORD Variable
    old_password_match = re.search(r'PASSWORD\s*=\s*["\'](.*?)["\']', content)
    
    if old_password_match:
        old_password_line = old_password_match.group(0)
        new_password_line = 'PASSWORD = "swissassetmanagerAC"'
        content = content.replace(old_password_line, new_password_line)
        print(f"{GREEN}✓ Passwort korrigiert{RESET}")
        fixes += 1
    else:
        # Passwort-Variable hinzufügen, falls nicht vorhanden
        password_line = '# Passwort-Schutz\nPASSWORD = "swissassetmanagerAC"\n'
        if '# Spracheinstellung' in content:
            content = content.replace('# Spracheinstellung', f'{password_line}\n# Spracheinstellung')
        elif '# VOLLSTÄNDIGE Schweizer Aktienliste' in content:
            content = content.replace('# VOLLSTÄNDIGE Schweizer Aktienliste', f'{password_line}\n\n# VOLLSTÄNDIGE Schweizer Aktienliste')
        else:
            # Am Anfang der Datei nach den Imports einfügen
            import_end = content.find('\n\n', content.find('import'))
            if import_end != -1:
                content = content[:import_end + 2] + password_line + content[import_end + 2:]
        print(f"{GREEN}✓ Passwort-Variable hinzugefügt{RESET}")
        fixes += 1

# Änderungen speichern
print(f"{YELLOW}Speichere Änderungen...{RESET}")
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Erstelle ein sehr einfaches direktes Startskript
direct_start_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "direct_start.sh")
with open(direct_start_path, 'w') as f:
    f.write("""#!/bin/bash
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
""")
os.chmod(direct_start_path, 0o755)
print(f"{GREEN}✓ Neues Direktstart-Skript erstellt: direct_start.sh{RESET}")

if fixes > 0:
    print(f"{GREEN}✅ {fixes} Probleme wurden behoben!{RESET}")
    print(f"{YELLOW}App neu starten...{RESET}")
    
    # Beende eventuell laufende Instanz
    os.system("pkill -f 'python3 app.py' || true")
    
    # Starte die App im Hintergrund
    os.system("cd {} && python3 app.py &".format(os.path.dirname(os.path.abspath(__file__))))
    
    print(f"\n{GREEN}✅ App wurde neu gestartet!{RESET}")
    print(f"{BLUE}Öffnen Sie im Browser:{RESET} http://localhost:8000")
    print(f"{BLUE}Passwort:{RESET} swissassetmanagerAC")
    
    print(f"\n{YELLOW}Falls das Problem weiterhin besteht, verwenden Sie:{RESET}")
    print(f"./direct_start.sh")
else:
    print(f"{YELLOW}Es wurden keine spezifischen Probleme gefunden.{RESET}")
    print(f"{YELLOW}Bitte verwenden Sie das neue Direktstart-Skript:{RESET}")
    print(f"./direct_start.sh")

print(f"\n{BLUE}========================================================{RESET}")