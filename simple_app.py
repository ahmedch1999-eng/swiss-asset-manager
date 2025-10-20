#!/usr/bin/env python3

"""
Swiss Asset Manager - Einfache, standalone Version
Diese Version behebt den schwarzen Bildschirm und lädt schneller
"""

from flask import Flask, render_template_string, send_from_directory, request, jsonify
import os
import time
import logging
import random
import json

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("swiss_asset_standalone")

app = Flask(__name__)

# Sehr einfaches HTML-Template für den Start
SIMPLE_HTML = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swiss Asset Manager</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #0A0A0A;
            color: #FFFFFF;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 1px solid #333;
            padding-bottom: 20px;
        }
        
        h1 {
            color: #FFFFFF;
        }
        
        .card {
            background-color: #1A1A1A;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            cursor: pointer;
            transition: transform 0.2s, background-color 0.2s;
        }
        
        .card:hover {
            background-color: #222;
            transform: translateY(-5px);
        }
        
        .card h2 {
            margin-top: 0;
            color: #FFFFFF;
        }
        
        .login-container {
            background-color: #1A1A1A;
            border-radius: 8px;
            padding: 30px;
            max-width: 400px;
            margin: 100px auto;
            text-align: center;
        }
        
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #333;
            background-color: #222;
            color: white;
            border-radius: 4px;
            font-size: 16px;
        }
        
        .btn {
            background-color: #003366;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        
        .btn:hover {
            background-color: #004b8f;
        }
        
        #errorMsg {
            color: #ff5555;
            margin-top: 10px;
            display: none;
        }
        
        #content {
            display: none;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .tile {
            background-color: #1A1A1A;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, background-color 0.2s;
        }
        
        .tile:hover {
            background-color: #222;
            transform: translateY(-5px);
        }
        
        .tile img {
            width: 64px;
            height: 64px;
            margin-bottom: 10px;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
            margin-left: 10px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <!-- Login Screen -->
    <div id="loginContainer" class="login-container">
        <h1>Swiss Asset Manager</h1>
        <p>Bitte geben Sie Ihr Passwort ein, um fortzufahren.</p>
        <input type="password" id="passwordInput" placeholder="Passwort eingeben">
        <p id="errorMsg">Ungültiges Passwort</p>
        <button id="loginBtn" class="btn">Anmelden</button>
    </div>
    
    <!-- Main Content (initially hidden) -->
    <div id="content">
        <div class="container">
            <header>
                <h1>Swiss Asset Manager</h1>
                <p>Ihr persönliches Finanzmanagement-Tool</p>
            </header>
            
            <h2>Startseite</h2>
            <div class="grid">
                <div class="tile" onclick="navigateTo('portfolio')">
                    <h3>Portfolio</h3>
                    <p>Erstellen und verwalten Sie Ihr Portfolio</p>
                </div>
                <div class="tile" onclick="navigateTo('markte')">
                    <h3>Märkte</h3>
                    <p>Marktübersicht und Kurse</p>
                </div>
                <div class="tile" onclick="navigateTo('nachrichten')">
                    <h3>Nachrichten</h3>
                    <p>Aktuelle Finanznachrichten</p>
                </div>
                <div class="tile" onclick="navigateTo('performance')">
                    <h3>Performance</h3>
                    <p>Performance-Analyse und Benchmarks</p>
                </div>
                <div class="tile" onclick="navigateTo('einstellungen')">
                    <h3>Einstellungen</h3>
                    <p>App-Einstellungen anpassen</p>
                </div>
                <div class="tile" onclick="navigateTo('monte-carlo')">
                    <h3>Monte Carlo</h3>
                    <p>Monte Carlo Simulation starten</p>
                </div>
            </div>
            
            <!-- Dynamischer Inhaltsbereich -->
            <div id="dynamicContent" style="margin-top: 40px;">
                <div id="portfolioContent" style="display:none;">
                    <h2>Portfolio</h2>
                    <p>Hier können Sie Ihr Portfolio erstellen und verwalten.</p>
                    <button class="btn" onclick="createPortfolio()">Portfolio erstellen</button>
                </div>
                
                <div id="markteContent" style="display:none;">
                    <h2>Märkte</h2>
                    <p>Daten werden geladen, sobald Sie Ihr Portfolio erstellt haben.</p>
                </div>
                
                <div id="nachrichtenContent" style="display:none;">
                    <h2>Nachrichten</h2>
                    <p>Aktuelle Finanznachrichten werden hier angezeigt.</p>
                </div>
                
                <div id="performanceContent" style="display:none;">
                    <h2>Performance</h2>
                    <p>Ihre Performance-Analyse wird hier angezeigt.</p>
                </div>
                
                <div id="einstellungenContent" style="display:none;">
                    <h2>Einstellungen</h2>
                    <p>Hier können Sie Ihre App-Einstellungen anpassen.</p>
                </div>
                
                <div id="monteCarloContent" style="display:none;">
                    <h2>Monte Carlo Simulation</h2>
                    <p>Erstellen Sie eine Monte Carlo Simulation für Ihr Portfolio.</p>
                    <button class="btn" style="background-color: #4CAF50;">Simulation starten</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Passwort-Prüfung
        document.getElementById('loginBtn').addEventListener('click', function() {
            const password = document.getElementById('passwordInput').value;
            if (password === 'swissassetmanagerAC') {
                document.getElementById('loginContainer').style.display = 'none';
                document.getElementById('content').style.display = 'block';
            } else {
                document.getElementById('errorMsg').style.display = 'block';
            }
        });
        
        // Enter-Taste für Login
        document.getElementById('passwordInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                document.getElementById('loginBtn').click();
            }
        });
        
        // Navigation
        function navigateTo(page) {
            // Hide all content
            const contents = document.querySelectorAll('#dynamicContent > div');
            contents.forEach(content => content.style.display = 'none');
            
            // Show selected content
            document.getElementById(page + 'Content').style.display = 'block';
        }
        
        // Portfolio erstellen
        function createPortfolio() {
            const portfolioContent = document.getElementById('portfolioContent');
            portfolioContent.innerHTML = '<h2>Portfolio</h2><p>Ihr Portfolio wird erstellt...</p><span class="loading"></span>';
            
            // Simulate portfolio creation
            setTimeout(() => {
                portfolioContent.innerHTML = `
                    <h2>Mein Portfolio</h2>
                    <p>Ihr Portfolio wurde erstellt. Jetzt können Sie Assets hinzufügen.</p>
                    <div style="background-color: #222; padding: 20px; border-radius: 8px; margin-top: 20px;">
                        <h3>Assets hinzufügen</h3>
                        <p>Wählen Sie aus den folgenden Kategorien:</p>
                        <button class="btn" onclick="showAssets('aktien')">Aktien</button>
                        <button class="btn" onclick="showAssets('indizes')">Indizes</button>
                        <button class="btn" onclick="showAssets('rohstoffe')">Rohstoffe</button>
                        <button class="btn" onclick="showAssets('krypto')">Kryptowährungen</button>
                    </div>
                    <div id="assetsList" style="margin-top: 20px;"></div>
                `;
                
                // Now we can start loading market data in the background
                fetch('/api/load_market_data');
            }, 1500);
        }
        
        // Zeige Assets
        function showAssets(category) {
            const assetsList = document.getElementById('assetsList');
            assetsList.innerHTML = `<h3>${category.charAt(0).toUpperCase() + category.slice(1)}</h3><p>Lade Assets...</p><span class="loading"></span>`;
            
            // Simulate loading assets
            setTimeout(() => {
                let assets;
                switch(category) {
                    case 'aktien':
                        assets = ['Nestlé', 'Novartis', 'Roche', 'UBS', 'Credit Suisse', 'ABB', 'Swatch', 'Richemont'];
                        break;
                    case 'indizes':
                        assets = ['SMI', 'SPI', 'DAX', 'S&P 500', 'NASDAQ', 'Dow Jones'];
                        break;
                    case 'rohstoffe':
                        assets = ['Gold', 'Silber', 'Öl', 'Kupfer', 'Erdgas'];
                        break;
                    case 'krypto':
                        assets = ['Bitcoin', 'Ethereum', 'Solana', 'Cardano', 'XRP'];
                        break;
                }
                
                let html = `<h3>${category.charAt(0).toUpperCase() + category.slice(1)}</h3>`;
                html += '<div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));">';
                
                assets.forEach(asset => {
                    html += `
                        <div class="tile" onclick="addAsset('${asset}')">
                            <h4>${asset}</h4>
                            <p>Zum Portfolio hinzufügen</p>
                        </div>
                    `;
                });
                
                html += '</div>';
                assetsList.innerHTML = html;
            }, 1000);
        }
        
        // Asset zum Portfolio hinzufügen
        function addAsset(asset) {
            // Hier würden wir das Asset zum Portfolio hinzufügen
            alert(`${asset} wurde zum Portfolio hinzugefügt!`);
            
            // Jetzt können wir Daten für dieses spezifische Asset laden
            fetch(`/api/load_asset_data?asset=${encodeURIComponent(asset)}`);
        }
    </script>
</body>
</html>
'''

# Passwort-Schutz
PASSWORD = "swissassetmanagerAC"

@app.route('/')
def index():
    return render_template_string(SIMPLE_HTML)

@app.route('/api/load_market_data')
def load_market_data():
    """Endpoint zum Laden von Marktdaten im Hintergrund"""
    # In einer echten App würden wir hier Daten laden
    # Hier simulieren wir nur eine Verzögerung
    time.sleep(1)
    return jsonify({"status": "success", "message": "Marktdaten werden im Hintergrund geladen"})

@app.route('/api/load_asset_data')
def load_asset_data():
    """Endpoint zum Laden von spezifischen Asset-Daten"""
    asset = request.args.get('asset', '')
    if not asset:
        return jsonify({"status": "error", "message": "Kein Asset angegeben"})
    
    # In einer echten App würden wir hier Daten für das Asset laden
    # Hier simulieren wir nur eine Verzögerung
    time.sleep(0.5)
    return jsonify({
        "status": "success", 
        "message": f"Daten für {asset} werden geladen",
        "data": {
            "name": asset,
            "price": round(random.uniform(10, 1000), 2),
            "change": round(random.uniform(-5, 5), 2)
        }
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Endpoint zum Bereitstellen von statischen Dateien"""
    return send_from_directory('static', filename)

if __name__ == "__main__":
    # Starte den Server
    port = 8000
    
    print("="*70)
    print("SWISS ASSET MANAGER - EINFACHE VERSION")
    print("="*70)
    print(f"Server startet auf: http://localhost:{port}")
    print(f"Passwort: {PASSWORD}")
    print("="*70)
    
    app.run(host="0.0.0.0", port=port, debug=True)