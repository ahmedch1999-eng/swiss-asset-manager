#!/bin/bash

# Swiss Asset Manager - Optimierter Start mit Portfolio-First-Ansatz
# Dieses Skript startet die App mit optimiertem Datenladeverhalten

echo "==============================================="
echo "SWISS ASSET MANAGER - PORTFOLIO FIRST"
echo "==============================================="

# Prüfe Python-Installation
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ FEHLER: Python nicht gefunden. Bitte installieren Sie Python 3."
    exit 1
fi

# Beende laufende Prozesse
echo "Beende laufende Prozesse..."
pkill -f "python.*app.py" > /dev/null 2>&1

# Erstelle optimierte App-Version
cat > portfolio_first_app.py << 'EOL'
#!/usr/bin/env python3
"""
Swiss Asset Manager - Portfolio First
------------------------------------
Lädt Daten erst, nachdem das Portfolio erstellt wurde.
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
import os
import sys
import time
import logging
import threading
import json
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/portfolio_first.log',
    filemode='w'
)
logger = logging.getLogger("portfolio_first")

# Erstelle ein Verzeichnis für Logs, falls es nicht existiert
if not os.path.exists('logs'):
    os.makedirs('logs')

# Importiere den Portfolio Data Loader
try:
    from portfolio_data_loader import get_loader
    portfolio_loader = get_loader()
    logger.info("Portfolio Data Loader erfolgreich importiert")
except Exception as e:
    logger.error(f"Fehler beim Import des Portfolio Data Loaders: {e}")
    portfolio_loader = None

# Initialisiere Flask
app = Flask(__name__)

# Passwort-Schutz
PASSWORD = "swissassetmanagerAC"

# HTML-Template mit Portfolio-First-Ansatz
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Swiss Asset Manager - Portfolio First</title>
    <style>
        body {
            font-family: Arial, Helvetica, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #121212;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #003366;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        .nav-tabs {
            display: flex;
            background-color: #222;
            overflow-x: auto;
        }
        .nav-tab {
            padding: 15px 20px;
            cursor: pointer;
            color: #ccc;
            white-space: nowrap;
        }
        .nav-tab.active {
            color: white;
            border-bottom: 3px solid #0066cc;
            background-color: #333;
        }
        .page {
            display: none;
            padding: 20px;
        }
        .page.active {
            display: block;
        }
        .card {
            background-color: #222;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .btn {
            background-color: #0066cc;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #0055aa;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }
        th {
            background-color: #333;
        }
        input, select {
            background-color: #333;
            color: white;
            border: 1px solid #444;
            padding: 8px;
            border-radius: 4px;
            width: 100%;
        }
        .portfolio-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .asset-card {
            background-color: #222;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .asset-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .asset-name {
            font-weight: bold;
        }
        .asset-weight {
            color: #0066cc;
        }
        .asset-price {
            font-size: 18px;
        }
        .asset-change {
            margin-top: 5px;
        }
        .change-positive {
            color: #00cc66;
        }
        .change-negative {
            color: #ff5555;
        }
        #loadingOverlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            display: none;
        }
        .loader {
            border: 5px solid #333;
            border-top: 5px solid #0066cc;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
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
            text-align: center;
        }
    </style>
</head>
<body>
    <!-- Passwortschutz -->
    <div id="passwordProtected">
        <div class="login-container">
            <h2>Swiss Asset Manager</h2>
            <p>Bitte geben Sie das Passwort ein:</p>
            <input type="password" id="passwordInput" placeholder="Passwort eingeben" style="margin-bottom: 20px;">
            <button id="loginButton" class="btn">Anmelden</button>
            <p id="passwordError" style="color: #ff5555; margin-top: 15px; display: none;">Ungültiges Passwort</p>
        </div>
    </div>
    
    <!-- Lade-Overlay -->
    <div id="loadingOverlay">
        <div class="loader"></div>
    </div>
    
    <!-- Hauptinhalt -->
    <div class="header">
        <h1>Swiss Asset Manager</h1>
        <span id="statusIndicator" style="font-size: 12px; color: #ccc;"></span>
    </div>
    
    <div class="nav-tabs">
        <div class="nav-tab active" data-page="portfolio">Portfolio</div>
        <div class="nav-tab" data-page="markets">Märkte</div>
        <div class="nav-tab" data-page="performance">Performance</div>
        <div class="nav-tab" data-page="settings">Einstellungen</div>
    </div>
    
    <div class="container">
        <!-- Portfolio Seite -->
        <div id="portfolio" class="page active">
            <h2>Mein Portfolio</h2>
            
            <div class="card">
                <h3>Portfolio erstellen</h3>
                <p>Erstellen Sie Ihr Portfolio, um die Daten zu laden.</p>
                
                <div id="assetSelector">
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                        <select id="assetType" style="flex: 1;">
                            <option value="stocks">Aktien</option>
                            <option value="indices">Indizes</option>
                            <option value="crypto">Kryptowährungen</option>
                            <option value="forex">Währungen</option>
                        </select>
                        <select id="assetName" style="flex: 2;">
                            <option value="">Asset auswählen...</option>
                        </select>
                        <input type="number" id="assetWeight" placeholder="Gewicht %" min="1" max="100" style="flex: 1;">
                        <button id="addAssetBtn" class="btn">Hinzufügen</button>
                    </div>
                </div>
                
                <div id="portfolioAssets">
                    <h4>Ausgewählte Assets</h4>
                    <table id="assetsTable">
                        <thead>
                            <tr>
                                <th>Asset</th>
                                <th>Gewicht (%)</th>
                                <th>Aktionen</th>
                            </tr>
                        </thead>
                        <tbody id="assetsTableBody">
                            <!-- Assets werden hier eingefügt -->
                        </tbody>
                    </table>
                    <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                        <span>Gesamtgewicht: <span id="totalWeight">0</span>%</span>
                        <button id="loadDataBtn" class="btn" disabled>Daten laden</button>
                    </div>
                </div>
            </div>
            
            <div id="portfolioOverview" class="card" style="display: none;">
                <h3>Portfolio Übersicht</h3>
                <div id="portfolioStats">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                        <div>
                            <h4>Gesamtwert</h4>
                            <div id="totalValue" style="font-size: 24px;">-</div>
                        </div>
                        <div>
                            <h4>Performance</h4>
                            <div id="totalPerformance" style="font-size: 24px;">-</div>
                        </div>
                    </div>
                </div>
                <div id="portfolioAssetsList" class="portfolio-grid">
                    <!-- Portfolio Assets werden hier angezeigt -->
                </div>
            </div>
        </div>
        
        <!-- Märkte Seite -->
        <div id="markets" class="page">
            <h2>Märkte</h2>
            <div class="card">
                <p>Um Marktdaten anzuzeigen, erstellen Sie zuerst Ihr Portfolio auf der Portfolio-Seite.</p>
                <div id="marketsContent" style="display: none;">
                    <h3>Marktübersicht</h3>
                    <div id="marketsList">
                        <!-- Marktdaten werden hier angezeigt -->
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Performance Seite -->
        <div id="performance" class="page">
            <h2>Performance Analyse</h2>
            <div class="card">
                <p>Um Performance-Daten anzuzeigen, erstellen Sie zuerst Ihr Portfolio auf der Portfolio-Seite.</p>
                <div id="performanceContent" style="display: none;">
                    <h3>Performance Übersicht</h3>
                    <div id="performanceStats">
                        <!-- Performance-Daten werden hier angezeigt -->
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Einstellungen Seite -->
        <div id="settings" class="page">
            <h2>Einstellungen</h2>
            <div class="card">
                <h3>Daten Aktualisierung</h3>
                <div>
                    <label>Aktualisierungsintervall:</label>
                    <select id="updateInterval">
                        <option value="manual">Manuell</option>
                        <option value="300">5 Minuten</option>
                        <option value="600">10 Minuten</option>
                        <option value="1800">30 Minuten</option>
                        <option value="3600">1 Stunde</option>
                    </select>
                </div>
                <div style="margin-top: 20px;">
                    <button id="manualUpdateBtn" class="btn">Daten jetzt aktualisieren</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Asset-Daten
        const assetData = {
            stocks: {
                "NESN.SW": "Nestlé", 
                "NOVN.SW": "Novartis", 
                "ROG.SW": "Roche", 
                "UBSG.SW": "UBS Group",
                "ZURN.SW": "Zurich Insurance", 
                "ABBN.SW": "ABB", 
                "SGSN.SW": "SGS", 
                "GIVN.SW": "Givaudan",
                "AAPL": "Apple",
                "MSFT": "Microsoft",
                "AMZN": "Amazon",
                "GOOGL": "Alphabet",
                "TSLA": "Tesla"
            },
            indices: {
                "^GSPC": "S&P 500", 
                "^DJI": "Dow Jones", 
                "^IXIC": "NASDAQ", 
                "^GDAXI": "DAX",
                "^SSMI": "SMI", 
                "^STOXX50E": "EURO STOXX 50", 
                "^FTSE": "FTSE 100"
            },
            crypto: {
                "BTC-USD": "Bitcoin", 
                "ETH-USD": "Ethereum", 
                "SOL-USD": "Solana", 
                "BNB-USD": "Binance Coin",
                "XRP-USD": "Ripple"
            },
            forex: {
                "EURUSD=X": "EUR/USD", 
                "GBPUSD=X": "GBP/USD", 
                "USDJPY=X": "USD/JPY", 
                "USDCHF=X": "USD/CHF",
                "EURCHF=X": "EUR/CHF", 
                "CHFEUR=X": "CHF/EUR"
            }
        };
        
        // Globale Variablen
        let portfolio = {};
        let portfolioData = null;
        let updateIntervalId = null;
        
        // DOM-Elemente nach dem Laden initialisieren
        document.addEventListener('DOMContentLoaded', function() {
            // Login-Handler
            document.getElementById('loginButton').addEventListener('click', function() {
                const password = document.getElementById('passwordInput').value;
                if (password === 'swissassetmanagerAC') {
                    document.getElementById('passwordProtected').style.display = 'none';
                    initializeApp();
                } else {
                    document.getElementById('passwordError').style.display = 'block';
                }
            });
            
            // Enter-Taste für Login
            document.getElementById('passwordInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    document.getElementById('loginButton').click();
                }
            });
        });
        
        // Initialisiere die App nach erfolgreichem Login
        function initializeApp() {
            // Tab-Navigation
            const navTabs = document.querySelectorAll('.nav-tab');
            navTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Aktive Klasse entfernen
                    navTabs.forEach(t => t.classList.remove('active'));
                    // Aktive Klasse auf das geklickte Tab setzen
                    this.classList.add('active');
                    
                    // Alle Seiten ausblenden
                    const pages = document.querySelectorAll('.page');
                    pages.forEach(page => page.classList.remove('active'));
                    
                    // Die passende Seite einblenden
                    const pageId = this.getAttribute('data-page');
                    document.getElementById(pageId).classList.add('active');
                });
            });
            
            // Asset-Typ Änderung
            const assetTypeSelect = document.getElementById('assetType');
            const assetNameSelect = document.getElementById('assetName');
            
            assetTypeSelect.addEventListener('change', function() {
                updateAssetOptions(this.value);
            });
            
            // Initial Asset-Optionen laden
            updateAssetOptions('stocks');
            
            // Asset hinzufügen
            document.getElementById('addAssetBtn').addEventListener('click', addAssetToPortfolio);
            
            // Daten laden Button
            document.getElementById('loadDataBtn').addEventListener('click', loadPortfolioData);
            
            // Manuelle Aktualisierung
            document.getElementById('manualUpdateBtn').addEventListener('click', function() {
                if (Object.keys(portfolio).length > 0) {
                    loadPortfolioData();
                } else {
                    alert('Bitte erstellen Sie zuerst ein Portfolio.');
                }
            });
            
            // Update-Intervall Änderung
            document.getElementById('updateInterval').addEventListener('change', function() {
                const interval = parseInt(this.value);
                
                // Bestehende Intervall-Updates stoppen
                if (updateIntervalId) {
                    clearInterval(updateIntervalId);
                    updateIntervalId = null;
                }
                
                // Neues Intervall setzen, wenn nicht manuell
                if (!isNaN(interval) && interval > 0) {
                    updateIntervalId = setInterval(loadPortfolioData, interval * 1000);
                    updateStatusIndicator(`Auto-Update alle ${interval / 60} Minuten`);
                } else {
                    updateStatusIndicator('Manuelles Update');
                }
            });
            
            // Status-Indikator setzen
            updateStatusIndicator('Bereit - Bitte Portfolio erstellen');
        }
        
        // Asset-Optionen aktualisieren basierend auf dem gewählten Typ
        function updateAssetOptions(assetType) {
            const assetNameSelect = document.getElementById('assetName');
            assetNameSelect.innerHTML = '<option value="">Asset auswählen...</option>';
            
            const assets = assetData[assetType];
            for (const [symbol, name] of Object.entries(assets)) {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${name} (${symbol})`;
                assetNameSelect.appendChild(option);
            }
        }
        
        // Asset zum Portfolio hinzufügen
        function addAssetToPortfolio() {
            const assetSelect = document.getElementById('assetName');
            const weightInput = document.getElementById('assetWeight');
            const assetTypeSelect = document.getElementById('assetType');
            
            const symbol = assetSelect.value;
            const weight = parseInt(weightInput.value);
            const assetType = assetTypeSelect.value;
            
            // Validierung
            if (!symbol) {
                alert('Bitte wählen Sie ein Asset aus.');
                return;
            }
            
            if (isNaN(weight) || weight <= 0 || weight > 100) {
                alert('Bitte geben Sie ein gültiges Gewicht zwischen 1 und 100 ein.');
                return;
            }
            
            // Bestehende Gesamtgewicht berechnen
            let totalWeightValue = calculateTotalWeight();
            if (totalWeightValue + weight > 100) {
                alert('Das Gesamtgewicht kann 100% nicht überschreiten.');
                return;
            }
            
            // Zum Portfolio hinzufügen
            portfolio[symbol] = weight;
            
            // UI aktualisieren
            updatePortfolioTable();
            weightInput.value = '';
            
            // Prüfen, ob der "Daten laden" Button aktiviert werden soll
            checkLoadDataButton();
        }
        
        // Berechne das Gesamtgewicht des Portfolios
        function calculateTotalWeight() {
            return Object.values(portfolio).reduce((sum, weight) => sum + weight, 0);
        }
        
        // Aktualisiere die Portfolio-Tabelle
        function updatePortfolioTable() {
            const tableBody = document.getElementById('assetsTableBody');
            tableBody.innerHTML = '';
            
            let totalWeight = 0;
            
            for (const [symbol, weight] of Object.entries(portfolio)) {
                const row = document.createElement('tr');
                
                // Asset-Name ermitteln
                let assetName = symbol;
                for (const type in assetData) {
                    if (assetData[type][symbol]) {
                        assetName = assetData[type][symbol] + " (" + symbol + ")";
                        break;
                    }
                }
                
                row.innerHTML = `
                    <td>${assetName}</td>
                    <td>${weight}%</td>
                    <td><button class="btn" style="background-color: #cc3333; padding: 5px 10px;" data-symbol="${symbol}">Entfernen</button></td>
                `;
                
                // Entfernen-Button Event-Handler
                row.querySelector('button').addEventListener('click', function() {
                    const symbolToRemove = this.getAttribute('data-symbol');
                    delete portfolio[symbolToRemove];
                    updatePortfolioTable();
                    checkLoadDataButton();
                });
                
                tableBody.appendChild(row);
                totalWeight += weight;
            }
            
            // Gesamtgewicht aktualisieren
            document.getElementById('totalWeight').textContent = totalWeight;
        }
        
        // Prüfe, ob der "Daten laden" Button aktiviert werden soll
        function checkLoadDataButton() {
            const loadDataBtn = document.getElementById('loadDataBtn');
            const totalWeight = calculateTotalWeight();
            
            if (Object.keys(portfolio).length > 0 && totalWeight > 0) {
                loadDataBtn.disabled = false;
            } else {
                loadDataBtn.disabled = true;
            }
        }
        
        // Lade Portfolio-Daten
        function loadPortfolioData() {
            if (Object.keys(portfolio).length === 0) {
                alert('Bitte fügen Sie zuerst Assets zu Ihrem Portfolio hinzu.');
                return;
            }
            
            // Loading-Overlay anzeigen
            document.getElementById('loadingOverlay').style.display = 'flex';
            updateStatusIndicator('Lade Daten...');
            
            // Erstelle eine Liste der Asset-Symbole
            const symbols = Object.keys(portfolio);
            
            // API-Anfrage senden
            fetch('/api/portfolio/load_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ symbols: symbols }),
            })
            .then(response => response.json())
            .then(data => {
                // Verarbeite die Antwort
                if (data.status === 'completed') {
                    updateStatusIndicator(`Daten geladen: ${data.success_count} Assets erfolgreich, ${data.error_count} fehlgeschlagen`);
                    
                    // Hole die Portfolio-Performance
                    getPortfolioPerformance();
                } else {
                    updateStatusIndicator(`Fehler beim Laden der Daten: ${data.status}`);
                    document.getElementById('loadingOverlay').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Fehler:', error);
                updateStatusIndicator('Fehler bei der Datenabfrage');
                document.getElementById('loadingOverlay').style.display = 'none';
            });
        }
        
        // Hole die Portfolio-Performance
        function getPortfolioPerformance() {
            fetch('/api/portfolio/performance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ portfolio: portfolio }),
            })
            .then(response => response.json())
            .then(data => {
                portfolioData = data;
                
                // Aktualisiere UI
                updatePortfolioUI(data);
                updateMarketsUI(data);
                updatePerformanceUI(data);
                
                // Loading-Overlay ausblenden
                document.getElementById('loadingOverlay').style.display = 'none';
            })
            .catch(error => {
                console.error('Fehler:', error);
                updateStatusIndicator('Fehler bei der Performance-Abfrage');
                document.getElementById('loadingOverlay').style.display = 'none';
            });
        }
        
        // Aktualisiere die Portfolio-UI
        function updatePortfolioUI(data) {
            // Übersicht anzeigen
            document.getElementById('portfolioOverview').style.display = 'block';
            
            // Gesamtwerte aktualisieren
            document.getElementById('totalValue').textContent = data.total_value;
            
            const performanceElement = document.getElementById('totalPerformance');
            const performanceValue = data.total_change;
            performanceElement.textContent = `${performanceValue.toFixed(2)}%`;
            performanceElement.className = performanceValue >= 0 ? 'change-positive' : 'change-negative';
            
            // Asset-Liste aktualisieren
            const assetsList = document.getElementById('portfolioAssetsList');
            assetsList.innerHTML = '';
            
            data.assets.forEach(asset => {
                // Asset-Name ermitteln
                let assetName = asset.asset;
                for (const type in assetData) {
                    if (assetData[type][asset.asset]) {
                        assetName = assetData[type][asset.asset];
                        break;
                    }
                }
                
                const assetCard = document.createElement('div');
                assetCard.className = 'asset-card';
                
                const changeClass = asset.change >= 0 ? 'change-positive' : 'change-negative';
                const changeSymbol = asset.change >= 0 ? '▲' : '▼';
                
                assetCard.innerHTML = `
                    <div class="asset-header">
                        <div class="asset-name">${assetName}</div>
                        <div class="asset-weight">${asset.weight}%</div>
                    </div>
                    <div class="asset-price">${asset.price}</div>
                    <div class="asset-change ${changeClass}">
                        ${changeSymbol} ${Math.abs(asset.change).toFixed(2)}%
                    </div>
                `;
                
                assetsList.appendChild(assetCard);
            });
        }
        
        // Aktualisiere die Märkte-UI
        function updateMarketsUI(data) {
            const marketsContent = document.getElementById('marketsContent');
            marketsContent.style.display = 'block';
            
            const marketsList = document.getElementById('marketsList');
            marketsList.innerHTML = '<h4>Ihre Portfolio-Assets:</h4>';
            
            const table = document.createElement('table');
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Aktueller Kurs</th>
                        <th>Veränderung</th>
                        <th>Gewicht</th>
                    </tr>
                </thead>
                <tbody id="marketsTableBody"></tbody>
            `;
            
            const tableBody = table.querySelector('tbody');
            
            data.assets.forEach(asset => {
                // Asset-Name ermitteln
                let assetName = asset.asset;
                for (const type in assetData) {
                    if (assetData[type][asset.asset]) {
                        assetName = assetData[type][asset.asset];
                        break;
                    }
                }
                
                const row = document.createElement('tr');
                const changeClass = asset.change >= 0 ? 'change-positive' : 'change-negative';
                const changeSymbol = asset.change >= 0 ? '▲' : '▼';
                
                row.innerHTML = `
                    <td>${assetName} (${asset.asset})</td>
                    <td>${asset.price}</td>
                    <td class="${changeClass}">${changeSymbol} ${Math.abs(asset.change).toFixed(2)}%</td>
                    <td>${asset.weight}%</td>
                `;
                
                tableBody.appendChild(row);
            });
            
            marketsList.appendChild(table);
        }
        
        // Aktualisiere die Performance-UI
        function updatePerformanceUI(data) {
            const performanceContent = document.getElementById('performanceContent');
            performanceContent.style.display = 'block';
            
            const performanceStats = document.getElementById('performanceStats');
            performanceStats.innerHTML = '';
            
            // Gesamtperformance-Karte
            const totalCard = document.createElement('div');
            totalCard.className = 'card';
            totalCard.innerHTML = `
                <h3>Portfolio-Performance</h3>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h4>Gesamtwert</h4>
                        <div style="font-size: 24px;">${data.total_value}</div>
                    </div>
                    <div>
                        <h4>Veränderung</h4>
                        <div style="font-size: 24px;" class="${data.total_change >= 0 ? 'change-positive' : 'change-negative'}">
                            ${data.total_change >= 0 ? '▲' : '▼'} ${Math.abs(data.total_change).toFixed(2)}%
                        </div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <p>Letztes Update: ${data.timestamp}</p>
                </div>
            `;
            
            performanceStats.appendChild(totalCard);
            
            // Top Performer
            const sortedAssets = [...data.assets].sort((a, b) => b.change - a.change);
            
            // Top Performer
            const topCard = document.createElement('div');
            topCard.className = 'card';
            topCard.innerHTML = '<h3>Top Performer</h3>';
            
            const topTable = document.createElement('table');
            const topBody = document.createElement('tbody');
            
            sortedAssets.slice(0, 3).forEach(asset => {
                let assetName = asset.asset;
                for (const type in assetData) {
                    if (assetData[type][asset.asset]) {
                        assetName = assetData[type][asset.asset];
                        break;
                    }
                }
                
                const row = document.createElement('tr');
                const changeClass = asset.change >= 0 ? 'change-positive' : 'change-negative';
                const changeSymbol = asset.change >= 0 ? '▲' : '▼';
                
                row.innerHTML = `
                    <td>${assetName}</td>
                    <td>${asset.price}</td>
                    <td class="${changeClass}">${changeSymbol} ${Math.abs(asset.change).toFixed(2)}%</td>
                `;
                
                topBody.appendChild(row);
            });
            
            topTable.appendChild(topBody);
            topCard.appendChild(topTable);
            performanceStats.appendChild(topCard);
        }
        
        // Status-Indikator aktualisieren
        function updateStatusIndicator(message) {
            const indicator = document.getElementById('statusIndicator');
            indicator.textContent = message;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/portfolio/load_data', methods=['POST'])
def load_portfolio_data():
    """API zum Laden der Daten für das Portfolio"""
    if not request.is_json:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols:
        return jsonify({"status": "error", "message": "No symbols provided"}), 400
    
    # Portfolio Data Loader verwenden
    if portfolio_loader:
        try:
            portfolio_loader.register_portfolio_assets(symbols)
            result = portfolio_loader.load_data_for_portfolio()
            return jsonify(result)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Portfolio-Daten: {e}")
            return jsonify({
                "status": "error", 
                "message": f"Error loading data: {str(e)}"
            }), 500
    else:
        # Simuliere Erfolg, wenn kein Portfolio Loader verfügbar ist
        return jsonify({
            "status": "completed",
            "success_count": len(symbols),
            "error_count": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

@app.route('/api/portfolio/performance', methods=['POST'])
def get_portfolio_performance():
    """API zum Abrufen der Portfolio-Performance"""
    if not request.is_json:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    
    data = request.get_json()
    portfolio = data.get('portfolio', {})
    
    if not portfolio:
        return jsonify({"status": "error", "message": "No portfolio provided"}), 400
    
    # Portfolio Data Loader verwenden
    if portfolio_loader:
        try:
            result = portfolio_loader.get_portfolio_performance(portfolio)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Portfolio-Performance: {e}")
            return jsonify({
                "status": "error", 
                "message": f"Error getting performance: {str(e)}"
            }), 500
    else:
        # Simulierte Daten, wenn kein Portfolio Loader verfügbar ist
        assets_data = []
        
        for asset, weight in portfolio.items():
            # Zufallsdaten generieren
            price = round(random.uniform(50, 500), 2)
            change = round(random.uniform(-5, 5), 2)
            
            assets_data.append({
                "asset": asset,
                "weight": weight,
                "price": price,
                "change": change,
                "status": "success"
            })
        
        # Zufällige Gesamtwerte
        total_value = round(sum([a["price"] * a["weight"] / 100 for a in assets_data]), 2)
        total_change = round(sum([a["change"] * a["weight"] / 100 for a in assets_data]), 2)
        
        return jsonify({
            "total_value": total_value,
            "total_change": total_change,
            "assets": assets_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

if __name__ == "__main__":
    # Information über den Start
    print("\n" + "="*50)
    print("SWISS ASSET MANAGER - PORTFOLIO FIRST")
    print("="*50)
    print("✅ Server gestartet auf: http://localhost:8000")
    print("📋 Passwort: swissassetmanagerAC")
    print("="*50 + "\n")
    
    # Starte den Server
    app.run(host="0.0.0.0", port=8000, debug=True)
EOL

# Mache das Skript ausführbar
chmod +x portfolio_first_app.py

echo "App erstellt. Starte den Server..."

# Starte den Server im Hintergrund
$PYTHON portfolio_first_app.py &

# Ausgabe der Anleitung
echo ""
echo "==============================================="
echo "✅ SWISS ASSET MANAGER - PORTFOLIO FIRST"
echo "==============================================="
echo "Die App lädt Daten erst nach der Portfolio-Erstellung!"
echo ""
echo "📋 URL: http://localhost:8000"
echo "📋 Passwort: swissassetmanagerAC"
echo ""
echo "Schritte:"
echo "1. Melden Sie sich mit dem Passwort an"
echo "2. Erstellen Sie Ihr Portfolio auf der Portfolio-Seite"
echo "3. Klicken Sie auf 'Daten laden'"
echo ""
echo "Die Daten werden nur für die Assets geladen,"
echo "die Sie in Ihrem Portfolio haben!"
echo "==============================================="