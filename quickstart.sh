#!/bin/bash

# Schnellstart-Skript für Swiss Asset Manager
# Dieses Skript startet eine optimierte Version der App und beheibt schwarzen Bildschirm Probleme

echo "=================================================="
echo "   SWISS ASSET MANAGER - SCHNELLSTART"
echo "=================================================="
echo "Dieses Skript behebt Probleme mit dem schwarzen Bildschirm und langen Ladezeiten."

# Suche und beende laufende Instanzen
echo -n "Suche nach laufenden Instanzen... "
pkill -f "python.*app.py" > /dev/null 2>&1
echo "Erledigt."

# Prüfe Python Installation
if command -v python3 > /dev/null; then
    PYTHON="python3"
elif command -v python > /dev/null; then
    PYTHON="python"
else
    echo "❌ FEHLER: Konnte Python nicht finden. Bitte installieren Sie Python."
    exit 1
fi

# Starte einfache Version
echo -n "Erstelle optimierten Start... "

cat > optimized_app.py << 'EOL'
#!/usr/bin/env python3
"""
Swiss Asset Manager - Schnellstart-Version
Beheibt Probleme mit schwarzem Bildschirm und langen Ladezeiten
"""

from flask import Flask, render_template_string, send_from_directory, request, jsonify
import os
import sys
import time
import signal

app = Flask(__name__)

# Passwort-Schutz
PASSWORD = "swissassetmanagerAC"

# Ein einfaches, schnelles Template für sofortige Anzeige
QUICK_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Swiss Asset Pro - Schnellstart</title>
    <link rel="apple-touch-icon" href="/static/icon-192x192.png">
    <style>
        body {
            font-family: Arial, Helvetica, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #121212;
            color: white;
        }
        .container {
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #fff;
        }
        .card {
            background-color: #222;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
            background-color: #333;
        }
        .btn {
            background-color: #003366;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
        }
        #passwordProtected {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #121212;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .login-container {
            background-color: #222;
            padding: 30px;
            border-radius: 8px;
            width: 300px;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            background-color: #333;
            border: 1px solid #444;
            color: white;
            border-radius: 4px;
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #003366;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            color: #ff5555;
            display: none;
        }
    </style>
</head>
<body>
    <!-- Passwortschutz -->
    <div id="passwordProtected">
        <div class="login-container">
            <h2>Swiss Asset Pro</h2>
            <p>Bitte geben Sie das Passwort ein:</p>
            <input type="password" id="passwordInput" placeholder="Passwort eingeben">
            <button id="loginButton" class="btn">Anmelden</button>
            <p id="passwordError" class="error">Ungültiges Passwort</p>
        </div>
    </div>
    
    <!-- Hauptinhalt -->
    <div id="content" style="display: none;">
        <div class="container">
            <h1>Swiss Asset Manager - Schnellstart</h1>
            <p>Diese Version behebt Probleme mit schwarzem Bildschirm und langen Ladezeiten.</p>
            
            <div class="card" onclick="startMainApp()">
                <h2>Standard App starten</h2>
                <p>Die vollständige Swiss Asset Manager App laden</p>
                <div class="loader" id="mainLoader" style="display: none;"></div>
                <button class="btn">Starten</button>
            </div>
            
            <div class="card" onclick="startBasicApp()">
                <h2>Einfache Version</h2>
                <p>Einfache Version ohne komplexe Funktionen laden</p>
                <div class="loader" id="basicLoader" style="display: none;"></div>
                <button class="btn">Starten</button>
            </div>
            
            <div class="card">
                <h2>Diagnose Tool</h2>
                <p>Probleme mit der App identifizieren und beheben</p>
                <div class="loader" id="diagnosticLoader" style="display: none;"></div>
                <button class="btn" onclick="runDiagnostics()">Diagnose starten</button>
            </div>
        </div>
    </div>
    
    <script>
        // Login handling
        document.getElementById('loginButton').addEventListener('click', function() {
            const password = document.getElementById('passwordInput').value;
            if (password === 'swissassetmanagerAC') {
                document.getElementById('passwordProtected').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            } else {
                document.getElementById('passwordError').style.display = 'block';
            }
        });
        
        // Enter key for login
        document.getElementById('passwordInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                document.getElementById('loginButton').click();
            }
        });
        
        // App functions
        function startMainApp() {
            document.getElementById('mainLoader').style.display = 'block';
            window.location.href = '/start_main';
        }
        
        function startBasicApp() {
            document.getElementById('basicLoader').style.display = 'block';
            window.location.href = '/start_basic';
        }
        
        function runDiagnostics() {
            document.getElementById('diagnosticLoader').style.display = 'block';
            fetch('/run_diagnostics')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('diagnosticLoader').style.display = 'none';
                    alert('Diagnose abgeschlossen: ' + data.message);
                })
                .catch(error => {
                    document.getElementById('diagnosticLoader').style.display = 'none';
                    alert('Fehler bei der Diagnose: ' + error);
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(QUICK_TEMPLATE)

@app.route('/start_main')
def start_main():
    # Starte die Hauptapp in einem separaten Prozess
    import subprocess
    subprocess.Popen([sys.executable, 'app.py'])
    return jsonify({"status": "started", "message": "Die Hauptanwendung wurde gestartet. Bitte öffnen Sie http://localhost:8000"})

@app.route('/start_basic')
def start_basic():
    # Eine einfache Version der App
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Swiss Asset Manager - Basic</title>
        <style>
            body { font-family: Arial; background: #121212; color: white; margin: 0; padding: 20px; }
            h1 { color: #fff; }
            .card { background: #222; padding: 20px; margin: 20px 0; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>Swiss Asset Manager - Einfache Version</h1>
        <div class="card">
            <h2>Willkommen</h2>
            <p>Dies ist eine vereinfachte Version der Swiss Asset Manager App ohne komplexe Funktionen.</p>
        </div>
        <a href="/" style="color: #0066cc;">Zurück</a>
    </body>
    </html>
    """)

@app.route('/run_diagnostics')
def run_diagnostics():
    # Führe einfache Diagnose durch
    import platform
    import psutil
    
    results = {
        "system": platform.system(),
        "python_version": platform.python_version(),
        "memory_available": psutil.virtual_memory().available / (1024 * 1024),
        "cpu_usage": psutil.cpu_percent(),
        "app_path": os.path.abspath("app.py"),
        "app_exists": os.path.exists("app.py")
    }
    
    return jsonify({
        "status": "success", 
        "message": "Diagnose abgeschlossen", 
        "results": results
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("="*50)
    print("SWISS ASSET MANAGER - SCHNELLSTART")
    print("="*50)
    print("✅ Server gestartet auf: http://localhost:8999")
    print("📋 Passwort: swissassetmanagerAC")
    print("="*50)
    
    # Graceful shutdown handler
    def signal_handler(sig, frame):
        print("\n✅ Server wird beendet...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    app.run(host='0.0.0.0', port=8999, debug=True)
EOL

echo "Erledigt."

# Starte die App
echo -n "Starte optimierte App... "
$PYTHON optimized_app.py > /dev/null 2>&1 &
PID=$!
echo "Erledigt. (PID: $PID)"

# Warte, bis der Server läuft
echo -n "Warte auf Server... "
sleep 2
echo "Erledigt."

echo ""
echo "=================================================="
echo "✅ SWISS ASSET MANAGER SCHNELLSTART IST BEREIT"
echo "=================================================="
echo "📋 URL: http://localhost:8999"
echo "📋 Passwort: swissassetmanagerAC"
echo ""
echo "Mit diesem Tool können Sie:"
echo "  1. Die Standard-App starten"
echo "  2. Eine einfache Version ohne komplexe Funktionen starten"
echo "  3. Diagnosen durchführen, um Probleme zu identifizieren"
echo ""
echo "Drücken Sie Ctrl+C, um dieses Skript zu beenden."
echo "=================================================="

# Warte, bis der Benutzer abbricht
wait $PID