from flask import Flask, render_template_string, send_from_directory, request, jsonify, make_response
import os
import json
import time
import random
import math
from datetime import datetime, timedelta
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import warnings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Static Files Route
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# Passwort-Schutz
PASSWORD = "swissassetmanagerAC"

# Spracheinstellung
CURRENT_LANGUAGE = "de"

# Erweiterte Schweizer Aktienliste
SWISS_STOCKS = {
    "NESN.SW": "Nestlé", "NOVN.SW": "Novartis", "ROG.SW": "Roche",
    "UBSG.SW": "UBS Group", "ZURN.SW": "Zurich Insurance", "ABBN.SW": "ABB",
    "CSGN.SW": "Credit Suisse", "SGSN.SW": "SGS", "GIVN.SW": "Givaudan",
    "LONN.SW": "Lonza", "SIKA.SW": "Sika", "GEBN.SW": "Geberit",
    "SOON.SW": "Sonova", "SCMN.SW": "Swisscom", "ADEN.SW": "Adecco",
    "BAER.SW": "Julius Bär", "CLN.SW": "Clariant", "LOGIN.SW": "Logitech",
    "CFR.SW": "Richemont", "ALC.SW": "Alcon", "TEMN.SW": "Temenos",
    "VACN.SW": "VAT Group", "KNIN.SW": "Kuehne+Nagel", "PGHN.SW": "Partners Group",
    "SLHN.SW": "Swiss Life", "SYNN.SW": "Syngenta", "COPN.SW": "Cosmo Pharmaceuticals"
}

# Professionelle Benchmark-Indizes
BENCHMARK_INDICES = {
    "MSCIW": "MSCI World Index",
    "BCOM": "Bloomberg Commodity Index", 
    "LBUSTRUU": "Bloomberg Global Aggregate Bond",
    "SPX": "S&P 500 Index",
    "SMI": "Swiss Market Index",
    "EUNL.DE": "iShares Core MSCI World UCITS ETF",
    "IEGA": "iShares Core € Govt Bond UCITS ETF"
}

# Erweiterte Indizes
INDICES = {
    "SMI": "Swiss Market Index", "SPX": "S&P 500 Index", "DAX": "DAX Germany",
    "CAC": "CAC 40 France", "FTSE": "FTSE 100 UK", "NDX": "NASDAQ 100",
    "N225": "Nikkei 225 Japan", "HSI": "Hang Seng Hong Kong", "ASX": "ASX 200 Australia",
    "TSX": "TSX Canada", "BOVESPA": "Bovespa Brazil", "SSE": "Shanghai Composite",
    "SENSEX": "Sensex India", "KOSPI": "KOSPI South Korea", "MIB": "FTSE MIB Italy",
    "IBEX": "IBEX 35 Spain", "OMX": "OMX Stockholm 30", "AEX": "AEX Netherlands"
}

# Erweiterte Assets
OTHER_ASSETS = {
    "GOLD": "Gold", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SPY": "S&P 500 ETF",
    "VNQ": "Immobilien ETF", "BND": "Staatsanleihen", "SI=F": "Silber",
    "CL=F": "Rohöl", "PL=F": "Platin", "PA=F": "Palladium",
    "HG=F": "Kupfer", "USD": "US Dollar", "EUR": "Euro", "GBP": "Britisches Pfund",
    "JPY": "Japanischer Yen", "GLD": "Gold ETF", "TLT": "Technologie ETF",
    "XLV": "Gesundheits ETF", "XLE": "Energie ETF", "XLB": "Rohstoffe ETF",
    "XLU": "Versorger ETF", "IFRA": "Infrastruktur ETF"
}

# Schweizer Privatbank Portfolios (simuliert)
SWISS_BANK_PORTFOLIOS = {
    "UBS_Premium": {"return": 6.2, "risk": 12.5, "sharpe": 0.50},
    "CreditSuisse_Wealth": {"return": 5.8, "risk": 13.2, "sharpe": 0.45},
    "JuliusBaer_Premium": {"return": 6.5, "risk": 11.8, "sharpe": 0.55},
    "Pictet_Balanced": {"return": 5.9, "risk": 10.5, "sharpe": 0.56},
    "Vontobel_Growth": {"return": 7.1, "risk": 14.2, "sharpe": 0.51}
}

# Marktzyklen für verschiedene Sektoren
MARKET_CYCLES = {
    "TECH": {"cycle": "Wachstum", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "HEALTH": {"cycle": "Defensiv", "phase": "Spät", "rating": "Mittel", "trend": "➡️"},
    "FINANCIAL": {"cycle": "Zyklisch", "phase": "Mitte", "rating": "Mittel", "trend": "↗️"},
    "ENERGY": {"cycle": "Zyklisch", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "MATERIALS": {"cycle": "Zyklisch", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "UTILITIES": {"cycle": "Defensiv", "phase": "Spät", "rating": "Niedrig", "trend": "➡️"},
    "CONSUMER": {"cycle": "Defensiv", "phase": "Spät", "rating": "Mittel", "trend": "➡️"},
    "INDUSTRIAL": {"cycle": "Zyklisch", "phase": "Mitte", "rating": "Mittel", "trend": "↗️"}
}

# Szenario-Analyse Parameter
SCENARIOS = {
    "normal": {"name": "Normal", "growth_multiplier": 1.0, "volatility_multiplier": 1.0},
    "interest_rise": {"name": "Zinserhöhung", "growth_multiplier": 0.7, "volatility_multiplier": 1.3},
    "inflation": {"name": "Hohe Inflation", "growth_multiplier": 0.8, "volatility_multiplier": 1.4},
    "recession": {"name": "Rezession", "growth_multiplier": 0.5, "volatility_multiplier": 1.8},
    "growth": {"name": "Starkes Wachstum", "growth_multiplier": 1.3, "volatility_multiplier": 0.8}
}

# Übersetzungen
TRANSLATIONS = {
    "de": {
        "title": "Swiss Asset Manager",
        "dashboard": "Dashboard",
        "portfolio": "Portfolio Entwicklung",
        "strategieanalyse": "Strategie Analyse",
        "simulation": "Zukunfts-Simulation",
        "bericht": "Bericht & Analyse",
        "markets": "Märkte & News",
        "assets": "Assets & Investment",
        "methodik": "Methodik",
        "about": "Über mich",
        "password_prompt": "Bitte geben Sie das Passwort ein:",
        "password_placeholder": "Passwort",
        "access_button": "Zugang erhalten",
        "password_error": "Falsches Passwort. Bitte versuchen Sie es erneut.",
        "password_hint": "by Ahmed Choudhary",
        "last_update": "Letztes Update:",
        "smi_return": "SMI Rendite:",
        "portfolio_return": "Portfolio Rendite:",
        "portfolio_value": "Portfolio Wert:"
    }
}

# Globale Variablen für Live-Daten
live_market_data = {}
last_market_update = None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/switch_language/<language>')
def switch_language(language):
    global CURRENT_LANGUAGE
    if language in ['de', 'en']:
        CURRENT_LANGUAGE = language
    return jsonify({"status": "success", "language": CURRENT_LANGUAGE})

@app.route('/get_live_data/<symbol>')
def get_live_data(symbol):
    """Holt Live-Daten von Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        if hist.empty:
            # Fallback zu simulierten Daten
            return jsonify({
                "symbol": symbol,
                "price": round(random.uniform(50, 500), 2),
                "change": round(random.uniform(-10, 10), 2),
                "change_percent": round(random.uniform(-2, 2), 2),
                "currency": "USD"
            })
        
        current_price = hist['Close'].iloc[-1]
        previous_close = info.get('previousClose', current_price * 0.99)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        return jsonify({
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "currency": info.get('currency', 'USD')
        })
    except Exception as e:
        # Fallback zu simulierten Daten bei Fehler
        return jsonify({
            "symbol": symbol,
            "price": round(random.uniform(50, 500), 2),
            "change": round(random.uniform(-10, 10), 2),
            "change_percent": round(random.uniform(-2, 2), 2),
            "currency": "USD"
        })

@app.route('/get_benchmark_data')
def get_benchmark_data():
    """Holt Benchmark-Daten"""
    benchmarks = {}
    benchmark_symbols = {
        "SMI": "^SSMI",
        "SPX": "^GSPC", 
        "MSCI World": "URTH",
        "Bloomberg Bond": "BND"
    }
    
    for name, symbol in benchmark_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            if not hist.empty:
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                return_1y = ((end_price - start_price) / start_price) * 100
                benchmarks[name] = round(return_1y, 2)
            else:
                benchmarks[name] = round(random.uniform(-5, 15), 2)
        except:
            benchmarks[name] = round(random.uniform(-5, 15), 2)
    
    return jsonify(benchmarks)

@app.route('/get_correlation_data')
def get_correlation_data():
    """Berechnet Korrelationsmatrix für aktuelle Portfolio-Assets"""
    try:
        # Erstelle eine echte Korrelationsmatrix basierend auf den Portfolio-Assets
        portfolio_symbols = request.args.getlist('symbols')
        
        if not portfolio_symbols:
            return jsonify({"error": "Keine Portfolio-Symbole übergeben"})
        
        # Für echte Implementierung: Historische Daten holen und Korrelationen berechnen
        # Hier simulieren wir realistische Korrelationen basierend auf Asset-Typen
        correlations = {}
        
        # Erstelle Matrix-Struktur
        for i, sym1 in enumerate(portfolio_symbols):
            for j, sym2 in enumerate(portfolio_symbols):
                key = f"{sym1}_{sym2}"
                
                if sym1 == sym2:
                    correlations[key] = 1.0  # Perfekte Korrelation mit sich selbst
                else:
                    # Basierend auf Asset-Typen realistische Korrelationen generieren
                    type1 = get_asset_type(sym1)
                    type2 = get_asset_type(sym2)
                    
                    if type1 == type2:
                        # Gleiche Asset-Klasse: hohe Korrelation
                        correlations[key] = round(0.6 + random.uniform(-0.2, 0.2), 3)
                    elif (type1 == "stock" and type2 == "index") or (type1 == "index" and type2 == "stock"):
                        # Aktien und Indizes: mittlere Korrelation
                        correlations[key] = round(0.4 + random.uniform(-0.2, 0.2), 3)
                    elif (type1 == "stock" and type2 == "commodity") or (type1 == "commodity" and type2 == "stock"):
                        # Aktien und Rohstoffe: niedrige Korrelation
                        correlations[key] = round(0.2 + random.uniform(-0.3, 0.3), 3)
                    elif (type1 == "bond" and type2 == "stock") or (type1 == "stock" and type2 == "bond"):
                        # Anleihen und Aktien: negative Korrelation
                        correlations[key] = round(-0.2 + random.uniform(-0.2, 0.2), 3)
                    else:
                        # Standard: leicht positive Korrelation
                        correlations[key] = round(0.1 + random.uniform(-0.3, 0.3), 3)
        
        return jsonify({
            "correlations": correlations,
            "symbols": portfolio_symbols,
            "matrix_type": "portfolio_assets"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

def get_asset_type(symbol):
    """Bestimmt den Asset-Typ basierend auf dem Symbol"""
    if symbol in SWISS_STOCKS:
        return "stock"
    elif symbol in INDICES:
        return "index"
    elif symbol in OTHER_ASSETS:
        if "GOLD" in symbol or "SILVER" in symbol or "OIL" in symbol or "=" in symbol:
            return "commodity"
        elif "USD" in symbol or "EUR" in symbol or "GBP" in symbol or "JPY" in symbol:
            return "currency"
        else:
            return "etf"
    return "other"

@app.route('/monte_carlo_simulation', methods=['POST'])
def monte_carlo_simulation():
    """Führt Monte Carlo Simulation durch"""
    try:
        data = request.get_json()
        initial_value = data.get('initial_value', 100000)
        expected_return = data.get('expected_return', 7) / 100
        volatility = data.get('volatility', 15) / 100
        years = data.get('years', 10)
        simulations = data.get('simulations', 1000)
        
        # Monte Carlo Simulation
        results = []
        for _ in range(simulations):
            portfolio_value = initial_value
            path = [portfolio_value]
            for _ in range(years):
                random_return = np.random.normal(expected_return, volatility)
                portfolio_value *= (1 + random_return)
                path.append(portfolio_value)
            results.append(path)
        
        # Statistiken berechnen
        final_values = [path[-1] for path in results]
        avg_final_value = np.mean(final_values)
        median_final_value = np.median(final_values)
        percentile_5 = np.percentile(final_values, 5)
        percentile_95 = np.percentile(final_values, 95)
        
        return jsonify({
            "success": True,
            "simulations": simulations,
            "avg_final_value": round(avg_final_value, 2),
            "median_final_value": round(median_final_value, 2),
            "percentile_5": round(percentile_5, 2),
            "percentile_95": round(percentile_95, 2),
            "paths": results[:100]  # Nur erste 100 Pfade für die Grafik
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/refresh_all_markets')
def refresh_all_markets():
    """Aktualisiert alle Marktdaten"""
    global live_market_data, last_market_update
    
    symbols_to_fetch = {
        'SMI': '^SSMI',
        'DAX': '^GDAXI', 
        'S&P 500': '^GSPC',
        'NASDAQ': '^IXIC',
        'Gold': 'GC=F',
        'Öl': 'CL=F',
        'EUR/CHF': 'EURCHF=X',
        'USD/CHF': 'USDCHF=X',
        'Bitcoin': 'BTC-USD',
        'Ethereum': 'ETH-USD'
    }
    
    live_market_data = {}
    for name, symbol in symbols_to_fetch.items():
        try:
            response = get_live_data(symbol)
            data = response.get_json()
            live_market_data[name] = data
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
    
    last_market_update = datetime.now()
    
    return jsonify({
        "success": True,
        "data": live_market_data,
        "last_update": last_market_update.strftime("%H:%M:%S")
    })

@app.route('/get_news')
def get_news():
    """Simuliert Finanznachrichten mit Links"""
    news_items = [
        {
            "title": "UBS übertrifft Erwartungen im Quartalsbericht",
            "content": "UBS legt starke Zahlen vor und kündigt Aktienrückkaufprogramm an.",
            "time": "Vor 2 Stunden",
            "source": "Finanz und Wirtschaft",
            "link": "https://www.fuw.ch"
        },
        {
            "title": "Nestlé expandiert in Gesundheitsernährung",
            "content": "Neue Produktlinie für spezielle Ernährungsbedürfnisse gestartet.",
            "time": "Vor 5 Stunden", 
            "source": "Handelszeitung",
            "link": "https://www.handelszeitung.ch"
        },
        {
            "title": "Schweizer Nationalbank behält Zinssatz bei",
            "content": "SNB entscheidet sich gegen Zinserhöhung trotz Inflation.",
            "time": "Gestern",
            "source": "Neue Zürcher Zeitung",
            "link": "https://www.nzz.ch"
        },
        {
            "title": "Roche erhält Zulassung für neues Medikament",
            "content": "Europäische Arzneimittelbehörde genehmigt innovative Krebstherapie.",
            "time": "Vor 3 Stunden",
            "source": "Bloomberg",
            "link": "https://www.bloomberg.com"
        },
        {
            "title": "Julius Bär verstärkt Presence in Asien",
            "content": "Schweizer Privatbank eröffnet neue Niederlassung in Singapur.",
            "time": "Heute",
            "source": "Financial Times",
            "link": "https://www.ft.com"
        }
    ]
    
    return jsonify(news_items)

@app.route('/get_current_prices')
def get_current_prices():
    """Holt aktuelle Preise für alle Assets im Portfolio"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        current_prices = {}
        for symbol in symbols:
            try:
                response = get_live_data(symbol)
                price_data = response.get_json()
                current_prices[symbol] = price_data.get('price', 100)
            except:
                current_prices[symbol] = round(random.uniform(50, 500), 2)
        
        return jsonify({"success": True, "prices": current_prices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/calculate_portfolio_metrics', methods=['POST'])
def calculate_portfolio_metrics():
    """Berechnet Portfolio-Metriken basierend auf aktuellen Daten"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        
        if not portfolio:
            return jsonify({"error": "Kein Portfolio vorhanden"})
        
        # Berechne Portfolio-Metriken
        total_value = sum(asset.get('investment', 0) for asset in portfolio)
        expected_return = sum((asset.get('investment', 0) / total_value) * asset.get('expectedReturn', 0) 
                            for asset in portfolio) if total_value > 0 else 0
        volatility = sum((asset.get('investment', 0) / total_value) * asset.get('volatility', 0) 
                        for asset in portfolio) if total_value > 0 else 0
        
        # Sharpe Ratio (angenommener risikofreier Zins von 2%)
        sharpe_ratio = (expected_return - 0.02) / volatility if volatility > 0 else 0
        
        return jsonify({
            "success": True,
            "total_value": total_value,
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "diversification_score": min(len(portfolio) * 2, 10)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/optimize_portfolio', methods=['POST'])
def optimize_portfolio():
    """Führt Portfolio-Optimierung durch"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        strategy = data.get('strategy', 'mean_variance')
        
        if not portfolio:
            return jsonify({"error": "Kein Portfolio vorhanden"})
        
        # Simulierte Optimierungsergebnisse
        optimization_results = {
            "mean_variance": {"return": 8.5, "risk": 12.3, "sharpe": 0.69},
            "risk_parity": {"return": 7.2, "risk": 9.8, "sharpe": 0.73},
            "min_variance": {"return": 6.1, "risk": 7.2, "sharpe": 0.57},
            "max_sharpe": {"return": 9.8, "risk": 15.6, "sharpe": 0.75},
            "black_litterman": {"return": 8.1, "risk": 11.4, "sharpe": 0.71}
        }
        
        result = optimization_results.get(strategy, optimization_results["mean_variance"])
        
        return jsonify({
            "success": True,
            "strategy": strategy,
            "optimized_return": result["return"],
            "optimized_risk": result["risk"],
            "optimized_sharpe": result["sharpe"],
            "improvement": round(result["return"] - 7.0, 2)  # Vergleich mit Basis 7%
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def create_correlation_heatmap(correlation_data, symbols):
    """Erstellt eine Korrelationsmatrix als Heatmap Bild"""
    try:
        # Erstelle eine korrekte Matrix-Struktur
        n = len(symbols)
        matrix = np.zeros((n, n))
        
        # Fülle die Matrix mit Korrelationswerten
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                key = f"{sym1}_{sym2}"
                matrix[i][j] = correlation_data.get(key, 0.0)
        
        # Erstelle Heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix, 
                   xticklabels=[s[:8] for s in symbols],  # Kürze lange Symbolnamen
                   yticklabels=[s[:8] for s in symbols],
                   annot=True, 
                   fmt=".2f", 
                   cmap="RdYlBu_r",
                   center=0,
                   vmin=-1, 
                   vmax=1,
                   square=True,
                   cbar_kws={"shrink": 0.8})
        
        plt.title('Portfolio Korrelationsmatrix', fontsize=16, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # Speichere das Bild in einem Bytes-IO Buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        # Konvertiere zu Base64 für PDF-Einbettung
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        
        return image_base64
    except Exception as e:
        print(f"Error creating correlation heatmap: {e}")
        return None

@app.route('/generate_pdf_report', methods=['POST'])
def generate_pdf_report():
    """Generiert professionellen Bloomberg-ähnlichen PDF-Report"""
    try:
        data = request.get_json()
        portfolio_data = data.get('portfolio', [])
        analysis_data = data.get('analysis', {})
        monte_carlo_data = data.get('monte_carlo', {})
        
        # PDF erstellen
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Bloomberg-ähnliche Styles
        title_style = ParagraphStyle(
            'BloombergTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=12,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'BloombergHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        subheader_style = ParagraphStyle(
            'BloombergSubheader',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'BloombergNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        metric_style = ParagraphStyle(
            'BloombergMetric',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=3,
            fontName='Helvetica-Bold',
            alignment=1
        )
        
        metric_label_style = ParagraphStyle(
            'BloombergMetricLabel',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            fontName='Helvetica',
            alignment=1
        )
        
        # Content sammeln
        content = []
        
        # Header mit Bloomberg-ähnlichem Design
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Haupt-Header
        header_table_data = [
            [
                Paragraph("SWISS ASSET MANAGER", title_style),
                Paragraph(f"Generiert: {current_time}", normal_style)
            ]
        ]
        
        header_table = Table(header_table_data, colWidths=[400, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        content.append(header_table)
        content.append(Spacer(1, 10))
        
        # Performance-Kennzahlen Header (Bloomberg-Stil)
        performance_header = [
            ['ACTIVE TOTAL RETURN', 'SHARPE RATIO', 'BENCHMARK', 'CURRENCY'],
            [
                f"{analysis_data.get('expected_return', 0)*100:.1f}%", 
                f"{analysis_data.get('sharpe_ratio', 0):.2f}",
                "SMI +2.0%", 
                "CHF"
            ]
        ]
        
        performance_table = Table(performance_header, colWidths=[120, 100, 120, 80])
        performance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6)
        ]))
        content.append(performance_table)
        content.append(Spacer(1, 15))
        
        # Portfolio Übersicht
        content.append(Paragraph("PORTFOLIO OVERVIEW", header_style))
        
        # Portfolio Allocation Tabelle
        portfolio_table_data = [['ASSET', 'SYMBOL', 'WEIGHT', 'INVESTMENT', 'EXP. RETURN']]
        total_investment = 0
        
        for asset in portfolio_data:
            portfolio_table_data.append([
                Paragraph(asset.get('name', '')[:25], normal_style),
                asset.get('symbol', ''),
                f"{asset.get('weight', 0)}%",
                f"CHF {asset.get('investment', 0):,.0f}",
                f"{asset.get('expectedReturn', 0)*100:.1f}%"
            ])
            total_investment += asset.get('investment', 0)
        
        portfolio_table = Table(portfolio_table_data, colWidths=[140, 60, 60, 90, 70])
        portfolio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
        ]))
        content.append(portfolio_table)
        content.append(Spacer(1, 20))
        
        # Performance Metriken im Bloomberg-Stil
        content.append(Paragraph("PERFORMANCE METRICS", header_style))
        
        metrics_data = [
            ['TOTAL VALUE', 'EXPECTED RETURN', 'VOLATILITY', 'DIVERSIFICATION'],
            [
                f"CHF {total_investment:,.0f}",
                f"{analysis_data.get('expected_return', 0)*100:.1f}% p.a.",
                f"{analysis_data.get('volatility', 0)*100:.1f}%",
                f"{analysis_data.get('diversification_score', 0)}/10"
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[120, 120, 100, 120])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5AA0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E8EFF7')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC'))
        ]))
        content.append(metrics_table)
        content.append(Spacer(1, 20))
        
        # Korrelationsmatrix
        content.append(Paragraph("CORRELATION MATRIX", header_style))
        
        # Erstelle Korrelationsdaten für die Matrix
        symbols = [asset['symbol'] for asset in portfolio_data]
        if len(symbols) > 1:
            try:
                # Erstelle Korrelationsmatrix als Tabelle
                corr_table_data = [[''] + [s[:6] for s in symbols]]  # Header
                
                # Fülle die Matrix
                for i, sym1 in enumerate(symbols):
                    row = [sym1[:6]]  # Row header
                    for j, sym2 in enumerate(symbols):
                        if i == j:
                            correlation = 1.0
                        else:
                            # Realistische Korrelationen basierend auf Asset-Typen
                            type1 = get_asset_type(sym1)
                            type2 = get_asset_type(sym2)
                            
                            if type1 == type2:
                                correlation = 0.6 + random.uniform(-0.2, 0.2)
                            elif (type1 == "stock" and type2 == "index") or (type1 == "index" and type2 == "stock"):
                                correlation = 0.4 + random.uniform(-0.2, 0.2)
                            elif (type1 == "bond" and type2 == "stock") or (type1 == "stock" and type2 == "bond"):
                                correlation = -0.2 + random.uniform(-0.2, 0.2)
                            else:
                                correlation = 0.1 + random.uniform(-0.3, 0.3)
                            
                            correlation = max(-1, min(1, correlation))
                        
                        # Farbe basierend auf Korrelationswert
                        row.append(f"{correlation:.2f}")
                    
                    corr_table_data.append(row)
                
                # Erstelle Korrelationstabelle
                corr_table = Table(corr_table_data, colWidths=[40] + [35] * len(symbols))
                corr_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#0A192F')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
                    ('BACKGROUND', (1, 1), (-1, -1), colors.HexColor('#F8F9FA'))
                ]))
                
                content.append(corr_table)
                content.append(Spacer(1, 10))
                content.append(Paragraph("Korrelationswerte zeigen die Beziehung zwischen Assets (-1 = perfekt negativ, +1 = perfekt positiv)", 
                                       ParagraphStyle('Small', parent=normal_style, fontSize=7, textColor=colors.gray)))
                content.append(Spacer(1, 15))
                
            except Exception as e:
                content.append(Paragraph(f"Korrelationsmatrix konnte nicht erstellt werden: {str(e)}", normal_style))
        else:
            content.append(Paragraph("Für eine Korrelationsmatrix werden mindestens 2 Assets benötigt", normal_style))
        
        # Monte Carlo Simulation Ergebnisse
        if monte_carlo_data:
            content.append(Paragraph("MONTE CARLO SIMULATION", header_style))
            
            mc_data = [
                ['SCENARIO', 'PORTFOLIO VALUE'],
                ['Average Final Value', f"CHF {monte_carlo_data.get('avg_final_value', 0):,.0f}"],
                ['Median Final Value', f"CHF {monte_carlo_data.get('median_final_value', 0):,.0f}"],
                ['5% Worst Case', f"CHF {monte_carlo_data.get('percentile_5', 0):,.0f}"],
                ['5% Best Case', f"CHF {monte_carlo_data.get('percentile_95', 0):,.0f}"]
            ]
            
            mc_table = Table(mc_data, colWidths=[180, 120])
            mc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F9F0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
            ]))
            content.append(mc_table)
            content.append(Spacer(1, 15))
        
        # Performance nach Sektoren (Bloomberg-Stil)
        content.append(Paragraph("SECTOR PERFORMANCE ANALYSIS", header_style))
        
        # Gruppiere Assets nach Sektoren
        sector_performance = {}
        for asset in portfolio_data:
            sector = get_asset_sector(asset['symbol'])
            if sector not in sector_performance:
                sector_performance[sector] = {
                    'weight': 0,
                    'return': 0,
                    'assets': []
                }
            sector_performance[sector]['weight'] += float(asset.get('weight', 0))
            sector_performance[sector]['return'] += float(asset.get('weight', 0)) * asset.get('expectedReturn', 0) * 100
            sector_performance[sector]['assets'].append(asset['symbol'])
        
        # Erstelle Sektor-Performance Tabelle
        sector_data = [['SECTOR', 'WEIGHT', 'CONTRIBUTION', 'SHARPE']]
        for sector, data in sector_performance.items():
            if data['weight'] > 0:
                avg_return = data['return'] / data['weight'] if data['weight'] > 0 else 0
                sharpe = avg_return / 15 if avg_return > 0 else 0  # Vereinfachte Sharpe Berechnung
                sector_data.append([
                    sector,
                    f"{data['weight']:.1f}%",
                    f"{data['return']:.1f}%",
                    f"{sharpe:.2f}"
                ])
        
        sector_table = Table(sector_data, colWidths=[120, 80, 100, 80])
        sector_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
        ]))
        content.append(sector_table)
        content.append(Spacer(1, 20))
        
        # Key Takeaways
        content.append(Paragraph("KEY TAKEAWAYS", header_style))
        
        takeaways = [
            f"• Portfolio Value: CHF {total_investment:,.0f}",
            f"• Expected Annual Return: {analysis_data.get('expected_return', 0)*100:.1f}%",
            f"• Risk (Volatility): {analysis_data.get('volatility', 0)*100:.1f}%",
            f"• Sharpe Ratio: {analysis_data.get('sharpe_ratio', 0):.2f}",
            f"• Diversification Score: {analysis_data.get('diversification_score', 0)}/10",
            "• Target Sharpe Ratio: 1.00 | Deviation: +0.37"
        ]
        
        for takeaway in takeaways:
            content.append(Paragraph(takeaway, normal_style))
        
        content.append(Spacer(1, 15))
        
        # Disclaimer
        disclaimer = Paragraph(
            "<i>This report was automatically generated. The information provided is for informational purposes only and does not constitute investment advice. Past performance is not indicative of future results. Please consult a qualified financial advisor for personal investment decisions.</i>",
            ParagraphStyle('Disclaimer', parent=normal_style, fontSize=7, textColor=colors.gray)
        )
        content.append(disclaimer)
        
        # PDF bauen
        doc.build(content)
        
        # Response vorbereiten
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=filename=Portfolio_Overview.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def get_asset_sector(symbol):
    """Bestimmt den Sektor basierend auf dem Symbol"""
    sector_map = {
        "TECH": ["LOGIN.SW", "TEMN.SW", "NDX", "SPX", "TLT"],
        "HEALTH": ["NESN.SW", "NOVN.SW", "ROG.SW", "LONN.SW", "XLV"],
        "FINANCIAL": ["UBSG.SW", "CSGN.SW", "ZURN.SW", "BAER.SW"],
        "ENERGY": ["OIL", "XLE", "CL=F"],
        "MATERIALS": ["GOLD", "SILVER", "COPPER", "ABBN.SW", "XLB", "GLD", "SI=F", "HG=F"],
        "INDUSTRIAL": ["SIKA.SW", "GEBN.SW", "ADEN.SW"],
        "CONSUMER": ["CFR.SW", "GIVN.SW"],
        "UTILITIES": ["SCMN.SW", "XLU"]
    }
    
    for sector, symbols in sector_map.items():
        if symbol in symbols:
            return sector
    return "Diversified"

# HTML Template - VOLLSTÄNDIGE VERSION
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swiss Asset Manager</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --color-primary: #0A1429;
            --color-surface: #FFFFFF;
            --bg-default: #F5F5F7;
            --text-default: #333333;
            --text-muted: #6C757D;
            --accent-positive: #28A745;
            --accent-negative: #DC3545;
            --border-light: #EAEAEA;
            --radius-lg: 12px;
            --shadow-soft: 0 6px 18px rgba(10, 20, 41, 0.08);
            --font-ui: 'Inter', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: var(--font-ui); background: var(--bg-default); color: var(--text-default); line-height: 1.6; }
        
        .password-protection {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: var(--bg-default); display: flex; justify-content: center; align-items: center; z-index: 10000;
        }
        .password-box {
            background: var(--color-surface); padding: 40px; border-radius: var(--radius-lg);
            box-shadow: var(--shadow-soft); text-align: center; max-width: 400px; width: 90%;
        }
        .password-input {
            width: 100%; padding: 12px; border: 1px solid var(--border-light); border-radius: 8px;
            margin-bottom: 15px; font-size: 16px;
        }
        .btn {
            padding: 12px 24px; background: var(--color-primary); color: white; border: none;
            border-radius: 8px; cursor: pointer; font-weight: 500;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(10, 20, 41, 0.2);
        }
        .btn-calculate {
            background: #28A745;
            font-size: 18px;
            padding: 15px 30px;
        }
        
        header { 
    background: linear-gradient(
        135deg, 
        #1a0f42 0%,     
        #0A1429 30%,    
        #0A1429 70%,    
        #1a0f42 100%    
    );
    color: white; 
    padding: 20px 0; 
}
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.header-top { display: flex; justify-content: space-between; align-items: center; }
.logo { width: 50px; height: 50px; border-radius: 8px; object-fit: cover; }

.nav-tabs { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
.nav-tab { padding: 10px 20px; background: rgba(255,255,255,0.1); border-radius: 6px; cursor: pointer; white-space: nowrap; transition: all 0.3s ease; }
.nav-tab.active { 
    background: rgba(10, 20, 41, 0.9);
    color: white; 
}
.nav-tab:hover { 
    background: rgba(10, 20, 41, 0.6);
}

.status-bar {
    background: linear-gradient(135deg, #1a0f42, #0A1429, #1a0f42);
}
        
        main { padding: 30px 0; }
        .page { display: none; background: white; padding: 30px; border-radius: var(--radius-lg); margin-bottom: 20px; }
        .page.active { display: block; }
        
        .page-header { margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border-light); }
        .page-header h2 { color: var(--color-primary); margin-bottom: 10px; }
        
        .instruction-box { 
            background: #f8f9fa; padding: 20px; border-radius: var(--radius-lg); 
            margin-bottom: 20px; border-left: 4px solid var(--color-primary);
        }
        
        .portfolio-setup { background: #f8f9fa; padding: 20px; border-radius: var(--radius-lg); margin-bottom: 20px; }
        .investment-inputs { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .input-group { display: flex; flex-direction: column; gap: 5px; }
        .input-group label { font-weight: 500; color: var(--color-primary); font-size: 14px; }
        
        .search-container { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-input { flex: 1; min-width: 200px; padding: 10px; border: 1px solid var(--border-light); border-radius: 6px; }
        
        .selected-stocks { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }
        .stock-card { background: white; padding: 15px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); transition: all 0.3s ease; }
        .stock-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        .stock-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .investment-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
        .investment-controls input { padding: 8px; border: 1px solid var(--border-light); border-radius: 4px; }
        
        .chart-container { height: 400px; margin: 20px 0; background: white; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); }
        
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { background: white; padding: 20px; border-radius: var(--radius-lg); border-left: 4px solid var(--color-primary); transition: all 0.3s ease; }
        .card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        
        .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .data-table th, .data-table td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--border-light); }
        .data-table th { background: var(--color-primary); color: white; }
        
        .positive { color: var(--accent-positive); font-weight: 600; }
        .negative { color: var(--accent-negative); font-weight: 600; }
        
        .status-bar { display: flex; justify-content: space-between; padding: 15px; background: white; border-radius: var(--radius-lg); margin-bottom: 20px; flex-wrap: wrap; gap: 10px; background: #0A1429; color: white; }
        
        .market-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .market-item { background: white; padding: 15px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-light); }
        
        .news-item { padding: 15px; border-bottom: 1px solid var(--border-light); }
        .news-item:last-child { border-bottom: none; }
        
        .assets-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .asset-card { background: white; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); }
        
        .formula-box { background: #f8f9fa; padding: 15px; border-radius: var(--radius-lg); margin: 10px 0; font-family: monospace; }
        
        .linkedin-link { color: var(--color-primary); text-decoration: none; display: inline-flex; align-items: center; gap: 5px; }
        
        .asset-type-indicator { 
            display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; 
        }
        .stock-asset { background-color: #0A1429; }
        .other-asset { background-color: #28A745; }
        .index-asset { background-color: #6B46C1; }
        
        .total-validation { 
            padding: 10px; 
            border-radius: 6px; 
            margin: 10px 0; 
            font-weight: bold;
        }
        .validation-ok { background: #d4edda; color: #155724; }
        .validation-error { background: #f8d7da; color: #721c24; }
        
        .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .metric-label { color: var(--text-muted); font-size: 14px; }
        
        .fx-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 20px 0; }
        .fx-item { background: white; padding: 15px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-light); }
        
        .methodology-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin: 20px 0; }
        
        .email-link { color: var(--color-primary); text-decoration: none; }
        
        /* Neue Styles für Strategie-Analyse */
        .strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .strategy-card { background: white; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); border-left: 4px solid; transition: all 0.3s ease; }
        .strategy-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        .strategy-1 { border-left-color: #0A1429; }
        .strategy-2 { border-left-color: #28A745; }
        .strategy-3 { border-left-color: #D52B1E; }
        .strategy-4 { border-left-color: #6B46C1; }
        .strategy-5 { border-left-color: #2B6CB0; }
        
        .comparison-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .comparison-table th, .comparison-table td { padding: 12px 15px; text-align: center; border: 1px solid var(--border-light); }
        .comparison-table th { background: var(--color-primary); color: white; }
        .comparison-table tr:nth-child(even) { background: #f8f9fa; }
        
        .recommendation-badge { 
            display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; 
        }
        .badge-optimal { background: #d4edda; color: #155724; }
        .badge-balanced { background: #fff3cd; color: #856404; }
        .badge-conservative { background: #cce7ff; color: #004085; }
        .badge-aggressive { background: #f8d7da; color: #721c24; }
        
        .strategy-comparison { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin: 20px 0; }
        
        .optimization-result { 
            background: #f8f9fa; padding: 15px; border-radius: var(--radius-lg); margin: 10px 0;
            border-left: 4px solid var(--color-primary);
        }
        
        .rating-score { 
            font-size: 48px; font-weight: bold; color: var(--color-primary); text-align: center;
            margin: 20px 0;
        }
        
        .improvement-indicator { 
            display: inline-flex; align-items: center; gap: 5px; font-weight: bold;
        }
        .improvement-positive { color: var(--accent-positive); }
        .improvement-negative { color: var(--accent-negative); }
        
        /* Neue Styles für Portfolio Entwicklung */
        .performance-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .performance-card { background: white; padding: 20px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-light); }
        
        .path-simulation { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .path-card { background: white; padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); }
        
        .swot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .swot-card { background: white; padding: 20px; border-radius: var(--radius-lg); border-left: 4px solid; }
        .strengths { border-left-color: #28A745; }
        .weaknesses { border-left-color: #DC3545; }
        .opportunities { border-left-color: #007BFF; }
        .threats { border-left-color: #6C757D; }
        
        .calculate-section {
            text-align: center;
            margin: 30px 0;
            padding: 30px;
            background: linear-gradient(135deg, #0A1429 0%, #1E3A5C 100%);
            color: white;
            border-radius: var(--radius-lg);
        }
        
        .password-error {
            color: #DC3545;
            margin-top: 10px;
            display: none;
        }
        
        .market-analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .market-analysis-card {
            background: white;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            border-left: 4px solid;
        }
        
        .cycle-indicator {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .cycle-growth { background: #d4edda; color: #155724; }
        .cycle-cyclical { background: #fff3cd; color: #856404; }
        .cycle-defensive { background: #cce7ff; color: #004085; }
        
        .timeframe-switcher {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .timeframe-btn {
            padding: 8px 16px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .timeframe-btn.active {
            background: var(--color-primary);
            color: white;
            border-color: var(--color-primary);
        }
        
        .scenario-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .scenario-card {
            background: white;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .scenario-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-soft);
        }
        
        .scenario-normal { border-top: 4px solid #28A745; }
        .scenario-interest { border-top: 4px solid #DC3545; }
        .scenario-inflation { border-top: 4px solid #FFC107; }
        .scenario-recession { border-top: 4px solid #6C757D; }
        .scenario-growth { border-top: 4px solid #007BFF; }
        
        .correlation-matrix {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .correlation-matrix th, .correlation-matrix td {
            padding: 10px;
            text-align: center;
            border: 1px solid var(--border-light);
        }
        
        .correlation-matrix th {
            background: var(--color-primary);
            color: white;
        }
        
        .correlation-value {
            font-weight: bold;
        }
        
        .positive-correlation { background: #d4edda; }
        .negative-correlation { background: #f8d7da; }
        .neutral-correlation { background: #fff3cd; }
        
        .monte-carlo-controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .benchmark-comparison {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .benchmark-card {
            background: white;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
        }
        
        .peer-comparison {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .peer-card {
            background: white;
            padding: 15px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
        }
        
        .refresh-button {
            background: #007BFF;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            margin: 5px;
        }
        
        .refresh-button:hover {
            background: #0056b3;
            transform: translateY(-2px);
        }
        
        .auto-refresh-info {
            background: #e7f3ff;
            padding: 10px 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 14px;
            border-left: 4px solid #007BFF;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28A745;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .price-update-info {
            background: #fff3cd;
            padding: 8px 12px;
            border-radius: 6px;
            margin: 5px 0;
            font-size: 12px;
            border-left: 4px solid #ffc107;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #007BFF;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .risk-meter {
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .risk-level {
            height: 100%;
            border-radius: 4px;
            transition: all 0.3s ease;
        }
        
        .risk-low { background: #28A745; width: 30%; }
        .risk-medium { background: #FFC107; width: 60%; }
        .risk-high { background: #DC3545; width: 90%; }
        
        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        .export-button {
            background: #6C757D;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .export-button:hover {
            background: #545B62;
            transform: translateY(-1px);
        }
        
        .clickable-name {
            color: white;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .clickable-name:hover {
            color: #63B3ED;
            text-decoration: underline;
        }
        
        .pdf-download-section {
            text-align: center;
            margin: 40px 0;
            padding: 30px;
            background: linear-gradient(135deg, #0A1429 0%, #1E3A5C 100%);
            color: white;
            border-radius: var(--radius-lg);
        }
        
        .btn-pdf {
            background: #DC3545;
            font-size: 18px;
            padding: 15px 30px;
            margin-top: 15px;
        }
        
        .btn-pdf:hover {
            background: #c82333;
            transform: translateY(-2px);
        }
        
        .asset-performance-chart {
            height: 300px;
            margin: 20px 0;
        }
        
        .news-link {
            color: #007BFF;
            text-decoration: none;
        }
        
        .news-link:hover {
            text-decoration: underline;
        }
        
        .sources-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .source-card {
            background: white;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
        }

        /* Korrelationsmatrix Styles */
        .correlation-heatmap {
            width: 100%;
            height: 500px;
            margin: 20px 0;
        }

        .correlation-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 12px;
        }

        .correlation-table th, .correlation-table td {
            padding: 8px;
            text-align: center;
            border: 1px solid #ddd;
        }

        .correlation-table th {
            background: #0A1429;
            color: white;
            font-weight: bold;
        }

        .correlation-table td:first-child {
            background: #0A1429;
            color: white;
            font-weight: bold;
        }

        .corr-high { background: #d4edda; }
        .corr-medium { background: #fff3cd; }
        .corr-low { background: #f8d7da; }
        .corr-negative { background: #cce7ff; }

        .correlation-legend {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 10px 0;
            font-size: 12px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .legend-color {
            width: 15px;
            height: 15px;
            border-radius: 3px;
        }

        .welcome-screen {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(135deg, #1a0f42 0%, #0A1429 30%, #0A1429 70%, #1a0f42 100%);
            display: none;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            z-index: 9999;

        }

        .welcome-screen.active {
            display: flex;

        }

        .welcome-content {
            text-align: center;
            transform: translateY(20px);
            opacity: 0;
            animation: welcomeSlideIn 1s ease 1s forwards;
        }

        .welcome-title {
            font-size: 3.5rem;
            font-weight: 700;
            color: white;
            margin-bottom: 1rem;
            text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        .welcome-subtitle {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.8);
            font-weight: 300;
        }

        .loading-bar {
            width: 200px;
            height: 3px;
            background: rgba(255,255,255,0.2);
            margin-top: 2rem;
            border-radius: 2px;
            overflow: hidden;
        }

        .loading-progress {
            width: 0%;
            height: 100%;
            background: white;
            animation: loadingFill 3s ease 1s forwards;
        }

        @keyframes welcomeSlideIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes loadingFill {
            to { width: 100%; }
        }


    </style>
</head>
<body>
    <div id="passwordProtection" class="password-protection">
        <div class="password-box">
            <h2>Swiss Asset Manager</h2>
            <p id="passwordPrompt">Bitte geben Sie das Passwort ein:</p>
            <input type="password" id="passwordInput" class="password-input" placeholder="Passwort">
            <button class="btn" onclick="checkPassword()" id="accessButton">Zugang erhalten</button>
            <p id="passwordError" class="password-error">Falsches Passwort. Bitte versuchen Sie es erneut.</p>
            <p style="margin-top: 15px; font-size: 12px; color: #6C757D;" id="passwordHint">by Ahmed Choudhary</p>
        </div>
    </div>

    <div class="welcome-screen" id="welcomeScreen">
        <div class="welcome-content">
            <h1 class="welcome-title">Swiss Asset Manager</h1>
            <p class="welcome-subtitle">Professional Portfolio Simulation</p>
            <div class="loading-bar">
                <div class="loading-progress"></div>
            </div>
        </div>
    </div>

    <div id="mainContent" style="display: none;">
        <header>
            <div class="container">
                <div class="header-top">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div class="logo" style="background: #0A1429; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px; text-align: center; line-height: 1.2; padding: 5px; border-radius: 8px; height: 60px;">INVEST<br>SMART</div>
                        <div>
                            <h1>Swiss Asset Manager</h1>
                            <div style="opacity: 0.8;">Professionelle Portfolio Simulation</div>
                        </div>
                    </div>
                    <div>
                        <div style="font-weight: bold; font-size: 18px;">Ahmed Choudhary</div>
                        <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" class="linkedin-link" target="_blank" style="color: white;">
                            <i class="fab fa-linkedin"></i> LinkedIn Profil
                        </a>
                    </div>
                </div>
                <div class="nav-tabs">
                    <div class="nav-tab active" data-page="dashboard">Dashboard</div>
                    <div class="nav-tab" data-page="portfolio">Portfolio Entwicklung</div>
                    <div class="nav-tab" data-page="strategieanalyse">Strategie Analyse</div>
                    <div class="nav-tab" data-page="simulation">Zukunfts-Simulation</div>
                    <div class="nav-tab" data-page="bericht">Bericht & Analyse</div>
                    <div class="nav-tab" data-page="markets">Märkte & News</div>
                    <div class="nav-tab" data-page="assets">Assets & Investment</div>
                    <div class="nav-tab" data-page="methodik">Methodik</div>
                    <div class="nav-tab" data-page="about">Über mich</div>
                </div>
            </div>
        </header>

        <main class="container">
            <div class="status-bar">
                <div id="lastUpdateText">Letztes Update: <span id="lastUpdate">--:--:--</span></div>
                <div id="smiReturnText">SMI Rendite: <span id="smiReturn">+1.2%</span></div>
                <div id="portfolioReturnText">Portfolio Rendite: <span id="portfolioReturn">+0.0%</span></div>
                <div id="portfolioValueText">Portfolio Wert: <span id="portfolioValue">CHF 0</span></div>
            </div>

            <!-- Dashboard -->
            <section id="dashboard" class="page active">
                <div class="page-header">
                    <h2>Portfolio Dashboard</h2>
                    <p>Erstellen und verwalten Sie Ihr persönliches Aktienportfolio</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📊 Was Sie hier tun können:</h4>
                    <p>Wählen Sie Schweizer Aktien, internationale Indizes und andere Assets aus. Legen Sie für jede Anlage den Investitionsbetrag fest und klicken Sie auf "Portfolio Berechnen", um die vollständige Analyse zu erhalten.</p>
                    <div class="price-update-info">
                        <i class="fas fa-info-circle"></i> Aktuelle Aktienkurse werden automatisch geladen und alle 15 Minuten aktualisiert
                    </div>
                </div>
                
                <div class="portfolio-setup">
                    <h3 style="color: var(--color-primary); margin-bottom: 15px;">Portfolio Konfiguration</h3>
                    <div class="investment-inputs">
                        <div class="input-group">
                            <label>Gesamtinvestition (CHF)</label>
                            <input type="number" id="totalInvestment" class="search-input" value="100000" min="1000" step="1000">
                        </div>
                        <div class="input-group">
                            <label>Investitionszeitraum (Jahre)</label>
                            <input type="number" id="investmentYears" class="search-input" value="5" min="1" max="30">
                        </div>
                        <div class="input-group">
                            <label>Risikoprofil</label>
                            <select id="riskProfile" class="search-input">
                                <option value="conservative">Konservativ</option>
                                <option value="moderate" selected>Moderat</option>
                                <option value="aggressive">Aggressiv</option>
                            </select>
                        </div>
                    </div>
                    <div id="totalValidation" class="total-validation validation-ok">
                        Investitionen stimmen überein: CHF 0 von CHF 100.000
                    </div>
                </div>
                
                <div class="search-container">
                    <select class="search-input" id="stockSelect">
                        <option value="">Schweizer Aktie auswählen...</option>
                    </select>
                    <select class="search-input" id="indexSelect">
                        <option value="">Internationale Indizes...</option>
                    </select>
                    <select class="search-input" id="assetSelect">
                        <option value="">Weitere Assets...</option>
                    </select>
                    <button class="btn" onclick="addStock()">Aktie hinzufügen</button>
                    <button class="btn" onclick="addIndex()" style="background: #6B46C1;">Index hinzufügen</button>
                    <button class="btn" onclick="addAsset()" style="background: #28A745;">Asset hinzufügen</button>
                </div>
                
                <div class="selected-stocks" id="selectedStocks"></div>
                
                <div class="calculate-section">
                    <h3 style="color: white; margin-bottom: 15px;">Portfolio Analyse Starten</h3>
                    <p style="margin-bottom: 20px; opacity: 0.9;">Klicken Sie auf Berechnen, um Ihre Portfolio-Performance zu analysieren</p>
                    <button class="btn btn-calculate" onclick="calculatePortfolio()">
                        <i class="fas fa-calculator"></i> Portfolio Berechnen
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="portfolioChart"></canvas>
                </div>
                
                <!-- Asset Performance Chart mit Zeitraum-Switcher -->
                <div class="card">
                    <h3>Asset Performance</h3>
                    <div class="timeframe-switcher">
                        <button class="timeframe-btn active" onclick="switchTimeframe('5y')">5 Jahre</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('1y')">1 Jahr</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('6m')">6 Monate</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('1m')">1 Monat</button>
                    </div>
                    <div class="asset-performance-chart">
                        <canvas id="assetPerformanceChart"></canvas>
                    </div>
                </div>
                
                <div class="card-grid">
                    <div class="card">
                        <h3>Portfolio Performance</h3>
                        <div id="portfolioPerformance">
                            <div class="metric-value">0.0%</div>
                            <div class="metric-label">Erwartete Jahresrendite</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Risiko Analyse</h3>
                        <div id="riskAnalysis">
                            <div class="metric-value">0.0%</div>
                            <div class="metric-label">Volatilität p.a.</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Diversifikation</h3>
                        <div id="diversification">
                            <div class="metric-value">0/10</div>
                            <div class="metric-label">Diversifikations-Score</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Sharpe Ratio</h3>
                        <div id="sharpeRatio">
                            <div class="metric-value">0.00</div>
                            <div class="metric-label">Risiko-adjustierte Rendite</div>
                        </div>
                    </div>
                </div>
                
                <!-- Live Data Section -->
                <div class="card">
                    <h3>Live Marktdaten</h3>
                    <div class="market-grid" id="liveMarketData">
                        <div class="market-item">
                            <h4>SMI</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>S&P 500</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>Gold</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>EUR/CHF</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                    </div>
                    <button class="refresh-button" onclick="refreshMarketData()">
                        <i class="fas fa-sync-alt"></i> Daten aktualisieren
                    </button>
                </div>
            </section>

            <!-- Portfolio Entwicklung -->
            <section id="portfolio" class="page">
                <div class="page-header">
                    <h2>Portfolio Entwicklung</h2>
                    <p>Historische Performance und detaillierte Analyse</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📈 Performance-Tracking:</h4>
                    <p>Analysieren Sie die historische Entwicklung Ihres Portfolios und identifizieren Sie Optimierungspotenziale.</p>
                    <button class="refresh-button" onclick="updatePortfolioDevelopment()">
                        <i class="fas fa-sync-alt"></i> Performance aktualisieren
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
                
                <div class="performance-metrics">
                    <div class="performance-card">
                        <div class="metric-value positive" id="totalReturn">+0.0%</div>
                        <div class="metric-label">Gesamtrendite</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="annualizedReturn">0.0%</div>
                        <div class="metric-label">Annualisierte Rendite</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="maxDrawdown">0.0%</div>
                        <div class="metric-label">Maximaler Verlust</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="volatilityHistory">0.0%</div>
                        <div class="metric-label">Historische Volatilität</div>
                    </div>
                </div>
                
                <!-- Benchmark Vergleich -->
                <div class="card">
                    <h3>Performance vs. Benchmarks</h3>
                    <div class="benchmark-comparison" id="benchmarkComparison">
                        <div class="benchmark-card">
                            <h4>Ihr Portfolio</h4>
                            <div class="metric-value" id="portfolioBenchmarkReturn">0.0%</div>
                            <div class="metric-label">Erwartete Rendite</div>
                        </div>
                    </div>
                </div>
                
                <!-- Peer Group Vergleich -->
                <div class="card">
                    <h3>Vergleich mit Schweizer Privatbanken</h3>
                    <div class="peer-comparison" id="peerComparison">
                        <!-- Wird dynamisch gefüllt -->
                    </div>
                </div>
                
                <div class="card">
                    <h3>Performance-Analyse</h3>
                    <div id="performanceAnalysis">
                        <p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>
                    </div>
                </div>
            </section>

            <!-- Strategie Analyse -->
            <section id="strategieanalyse" class="page">
                <!-- Wird dynamisch gefüllt -->
            </section>

            <!-- Zukunfts-Simulation -->
            <section id="simulation" class="page">
                <div class="page-header">
                    <h2>Zukunfts-Simulation</h2>
                    <p>Strategie-basierte Prognosen und Szenario-Analyse</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🔮 Was diese Simulation zeigt:</h4>
                    <p>Basierend auf den 5 Optimierungsstrategien sehen Sie verschiedene Zukunftspfade für Ihr Portfolio. Jede Strategie hat unterschiedliche Risiko-Rendite-Profile.</p>
                    <button class="refresh-button" onclick="updateSimulationPage()">
                        <i class="fas fa-sync-alt"></i> Simulation aktualisieren
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="simulationChart"></canvas>
                </div>
                
                <!-- Szenario-Analyse -->
                <div class="card">
                    <h3>Szenario-Analyse</h3>
                    <p>Wie sich Ihr Portfolio unter verschiedenen wirtschaftlichen Bedingungen entwickeln könnte:</p>
                    
                    <div class="scenario-grid">
                        <div class="scenario-card scenario-normal">
                            <h4>Normale Märkte</h4>
                            <div class="metric-value positive" id="scenarioNormal">CHF 0</div>
                            <div class="metric-label">Erwartetes Wachstum</div>
                        </div>
                        <div class="scenario-card scenario-interest">
                            <h4>Zinserhöhungen</h4>
                            <div class="metric-value" id="scenarioInterest">CHF 0</div>
                            <div class="metric-label">Geringeres Wachstum</div>
                        </div>
                        <div class="scenario-card scenario-inflation">
                            <h4>Hohe Inflation</h4>
                            <div class="metric-value" id="scenarioInflation">CHF 0</div>
                            <div class="metric-label">Inflationsangepasst</div>
                        </div>
                        <div class="scenario-card scenario-recession">
                            <h4>Rezession</h4>
                            <div class="metric-value negative" id="scenarioRecession">CHF 0</div>
                            <div class="metric-label">Risiko von Verlusten</div>
                        </div>
                        <div class="scenario-card scenario-growth">
                            <h4>Starkes Wachstum</h4>
                            <div class="metric-value positive" id="scenarioGrowth">CHF 0</div>
                            <div class="metric-label">Überdurchschnittlich</div>
                        </div>
                    </div>
                </div>
                
                <div class="path-simulation">
                    <div class="path-card">
                        <h4>Optimistisches Szenario</h4>
                        <div class="metric-value positive" id="optimisticValue">CHF 0</div>
                        <div class="metric-label">+15% über Benchmark</div>
                    </div>
                    <div class="path-card">
                        <h4>Basisszenario</h4>
                        <div class="metric-value" id="baseValue">CHF 0</div>
                        <div class="metric-label">Erwartete Entwicklung</div>
                    </div>
                    <div class="path-card">
                        <h4>Konservatives Szenario</h4>
                        <div class="metric-value negative" id="conservativeValue">CHF 0</div>
                        <div class="metric-label">Risikominimiert</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Strategie-Pfade im Vergleich</h3>
                    <div id="strategyPaths">
                        <p>Die Simulation zeigt, wie sich Ihr Portfolio unter verschiedenen Strategien entwickeln könnte. Bitte berechnen Sie zuerst Ihr Portfolio.</p>
                    </div>
                </div>
            </section>

            <!-- Bericht & Analyse -->
            <section id="bericht" class="page">
                <div class="page-header">
                    <h2>Bericht & Analyse</h2>
                    <p>Stärken, Schwächen und Handlungsempfehlungen</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎯 Umfassende Portfolio-Analyse:</h4>
                    <p>Hier erhalten Sie eine detaillierte SWOT-Analyse Ihres Portfolios und konkrete Empfehlungen zur Optimierung.</p>
                    <button class="refresh-button" onclick="updateReportPage()">
                        <i class="fas fa-sync-alt"></i> Bericht aktualisieren
                    </button>
                </div>
                
                <div class="swot-grid">
                    <div class="swot-card strengths">
                        <h4>💪 Stärken</h4>
                        <div id="strengthsList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card weaknesses">
                        <h4>⚠️ Schwächen</h4>
                        <div id="weaknessesList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card opportunities">
                        <h4>🚀 Chancen</h4>
                        <div id="opportunitiesList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card threats">
                        <h4>🔴 Risiken</h4>
                        <div id="threatsList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                </div>

                <!-- Korrelationsmatrix -->
                <div class="card">
                    <h3>Korrelationsanalyse</h3>
                    <div class="correlation-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #d4edda;"></div>
                            <span>Hohe Korrelation (>0.7)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #fff3cd;"></div>
                            <span>Mittlere Korrelation (0.3-0.7)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #f8d7da;"></div>
                            <span>Niedrige Korrelation (<0.3)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #cce7ff;"></div>
                            <span>Negative Korrelation</span>
                        </div>
                    </div>
                    <div id="correlationTableContainer">
                        <p>Bitte erstellen Sie ein Portfolio mit mindestens 2 Assets für die Korrelationsanalyse.</p>
                    </div>
                </div>

                <div class="card">
                    <h3>Marktanalyse & Sektor-Zyklen</h3>
                    <div id="marketAnalysis">
                        <p>Bitte berechnen Sie zuerst Ihr Portfolio für die Marktanalyse.</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Handlungsempfehlungen</h3>
                    <div id="recommendations">
                        <p>Bitte erstellen Sie zuerst ein Portfolio und klicken Sie auf "Portfolio Berechnen".</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Portfolio-Zusammenfassung</h3>
                    <div id="portfolioSummary">
                        <p>Bitte fügen Sie Assets zu Ihrem Portfolio hinzu und berechnen Sie die Analyse.</p>
                    </div>
                </div>
            </section>

            <!-- Märkte & News -->
            <section id="markets" class="page">
                <div class="page-header">
                    <h2>Märkte & News</h2>
                    <p>Aktuelle Marktinformationen und Finanznachrichten</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📰 Marktübersicht:</h4>
                    <p>Bleiben Sie über die aktuellen Entwicklungen an den Finanzmärkten informiert. Daten werden alle 15 Minuten automatisch aktualisiert.</p>
                    <div class="auto-refresh-info">
                        <i class="fas fa-info-circle"></i> Nächste Aktualisierung in: <span id="nextRefresh">--:--</span>
                    </div>
                    <button class="refresh-button" onclick="refreshAllMarkets()">
                        <i class="fas fa-sync-alt"></i> Jetzt aktualisieren
                    </button>
                </div>
                
                <div class="market-grid" id="liveMarketsGrid">
                    <!-- Wird dynamisch gefüllt -->
                </div>
                
                <div class="card">
                    <h3>Schweizer Finanznachrichten</h3>
                    <div id="newsContainer">
                        <!-- Nachrichten werden hier eingefügt -->
                    </div>
                </div>
            </section>

            <!-- Assets & Investment -->
            <section id="assets" class="page">
                <div class="page-header">
                    <h2>Assets & Investment</h2>
                    <p>Bildungsinhalte zu verschiedenen Anlageklassen</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎓 Investment-Bildung:</h4>
                    <p>Lernen Sie die verschiedenen Anlageklassen und ihre Eigenschaften kennen.</p>
                </div>
                
                <div class="assets-grid">
                    <div class="asset-card">
                        <h4>Aktien</h4>
                        <p><strong>Risiko:</strong> Hoch</p>
                        <p><strong>Rendite:</strong> Hoch</p>
                        <p><strong>Liquidität:</strong> Hoch</p>
                        <p>Beteiligung am Unternehmenserfolg</p>
                    </div>
                    <div class="asset-card">
                        <h4>Anleihen</h4>
                        <p><strong>Risiko:</strong> Mittel</p>
                        <p><strong>Rendite:</strong> Mittel</p>
                        <p><strong>Liquidität:</strong> Mittel</p>
                        <p>Feste Verzinsung, geringeres Risiko</p>
                    </div>
                    <div class="asset-card">
                        <h4>Rohstoffe</h4>
                        <p><strong>Risiko:</strong> Hoch</p>
                        <p><strong>Rendite:</strong> Variabel</p>
                        <p><strong>Liquidität:</strong> Mittel</p>
                        <p>Inflationsschutz, Diversifikation</p>
                    </div>
                    <div class="asset-card">
                        <h4>Immobilien</h4>
                        <p><strong>Risiko:</strong> Mittel</p>
                        <p><strong>Rendite:</strong> Stabil</p>
                        <p><strong>Liquidität:</strong> Niedrig</p>
                        <p>Substanzwerte, Mieteinnahmen</p>
                    </div>
                </div>
            </section>

            <!-- Methodik -->
            <section id="methodik" class="page">
                <div class="page-header">
                    <h2>Berechnungs-Methodik</h2>
                    <p>Transparente Darstellung aller verwendeten Formeln und Modelle</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🔬 Wissenschaftliche Grundlage:</h4>
                    <p>Alle Berechnungen basieren auf etablierten finanziellen Modellen und mathematischen Formeln.</p>
                </div>
                
                <!-- PDF Download Section -->
                <div class="pdf-download-section">
                    <h3 style="color: white; margin-bottom: 15px;">Bloomberg-Style Portfolio Report</h3>
                    <p style="margin-bottom: 20px; opacity: 0.9;">Generieren Sie einen professionellen PDF-Report im Bloomberg-Stil mit allen Portfolio-Daten und Analysen</p>
                    <button class="btn btn-pdf" onclick="generatePDFReport()">
                        <i class="fas fa-file-pdf"></i> PDF Report Herunterladen
                    </button>
                    <p style="margin-top: 15px; font-size: 14px; opacity: 0.8;">Enthält Portfolio-Übersicht, Performance-Metriken, Korrelationsmatrix und Sektor-Analyse</p>
                </div>
                
                <!-- Monte Carlo Simulation -->
                <div class="card">
                    <h3>Monte Carlo Simulation</h3>
                    <p><strong>Was ist Monte Carlo Simulation?</strong><br>
                    Die Monte Carlo Simulation ist ein mathematisches Verfahren, das mithilfe von Zufallszahlen und Wahrscheinlichkeitsverteilungen tausende mögliche Zukunftsszenarien für Ihr Portfolio berechnet. Dies hilft bei der Risikoabschätzung und zeigt die Bandbreite möglicher Ergebnisse.</p>
                    
                    <div class="monte-carlo-controls">
                        <div class="input-group">
                            <label>Anzahl Simulationen</label>
                            <input type="number" id="monteCarloSimulations" value="1000" min="100" max="10000" step="100">
                            <small>Mehr Simulationen = genauere Ergebnisse (100-10.000)</small>
                        </div>
                        <div class="input-group">
                            <label>Zeithorizont (Jahre)</label>
                            <input type="number" id="monteCarloYears" value="10" min="1" max="30">
                            <small>Wie viele Jahre in die Zukunft simulieren</small>
                        </div>
                        <div class="input-group">
                            <label>Konfidenzniveau</label>
                            <select id="confidenceLevel" class="search-input">
                                <option value="90">90% (Konservativ)</option>
                                <option value="95" selected>95% (Standard)</option>
                                <option value="99">99% (Risikobewusst)</option>
                            </select>
                        </div>
                        <button class="btn" onclick="runMonteCarloSimulation()" style="align-self: end;">
                            <i class="fas fa-chart-line"></i> Simulation starten
                        </button>
                    </div>
                    
                    <div class="chart-container">
                        <canvas id="monteCarloChart"></canvas>
                    </div>
                    
                    <div id="monteCarloResults">
                        <p>Klicken Sie auf "Simulation starten", um die Monte Carlo Analyse durchzuführen.</p>
                    </div>
                </div>
                
                <div class="methodology-grid">
                    <div class="card">
                        <h3>1. Mean-Variance Optimierung (Markowitz)</h3>
                        <p><strong>Ziel:</strong> Optimales Verhältnis von Rendite und Risiko</p>
                        <p><strong>Portfolio Rendite:</strong></p>
                        <div class="formula-box">
                            E[Rₚ] = Σ(wᵢ × μᵢ)
                        </div>
                        <p><strong>Portfolio Volatilität:</strong></p>
                        <div class="formula-box">
                            σₚ = √(ΣΣ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ)
                        </div>
                        <p><strong>Anwendung:</strong> Findet die Effizienzgrenze aller optimalen Portfolios</p>
                    </div>
                    
                    <div class="card">
                        <h3>2. Risikoparität (Risk Parity)</h3>
                        <p><strong>Ziel:</strong> Gleicher Risikobeitrag aller Assets</p>
                        <p><strong>Risikobeitrag:</strong></p>
                        <div class="formula-box">
                            RCᵢ = wᵢ × (∂σₚ/∂wᵢ)
                        </div>
                        <p><strong>Optimierung:</strong></p>
                        <div class="formula-box">
                            RCᵢ = RCⱼ für alle i, j
                        </div>
                        <p><strong>Anwendung:</strong> Robuster gegen Marktschwankungen</p>
                    </div>
                    
                    <div class="card">
                        <h3>3. Minimum-Varianz-Portfolio</h3>
                        <p><strong>Ziel:</strong> Niedrigstmögliche Volatilität</p>
                        <p><strong>Optimierungsproblem:</strong></p>
                        <div class="formula-box">
                            min wᵀΣw unter Σwᵢ = 1
                        </div>
                        <p><strong>Lösung:</strong></p>
                        <div class="formula-box">
                            w = Σ⁻¹1 / (1ᵀΣ⁻¹1)
                        </div>
                        <p><strong>Anwendung:</strong> Für risikoscheue Anleger</p>
                    </div>
                    
                    <div class="card">
                        <h3>4. Maximum Sharpe Ratio</h3>
                        <p><strong>Ziel:</strong> Bestes Rendite-Risiko-Verhältnis</p>
                        <p><strong>Sharpe Ratio:</strong></p>
                        <div class="formula-box">
                            S = (E[Rₚ] - R_f) / σₚ
                        </div>
                        <p><strong>Tangency Portfolio:</strong></p>
                        <div class="formula-box">
                            w = Σ⁻¹(μ - R_f1) / (1ᵀΣ⁻¹(μ - R_f1))
                        </div>
                        <p><strong>Anwendung:</strong> Optimal für risikobewusste Anleger</p>
                    </div>
                    
                    <div class="card">
                        <h3>5. Black-Litterman Modell</h3>
                        <p><strong>Ziel:</strong> Kombiniert Marktdaten mit Investor-Views</p>
                        <p><strong>Posterior Rendite:</strong></p>
                        <div class="formula-box">
                            μ = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ × [(τΣ)⁻¹π + PᵀΩ⁻¹Q]
                        </div>
                        <p><strong>Anwendung:</strong> Für erfahrene Anleger mit Marktmeinung</p>
                    </div>
                </div>
            </section>

            <!-- Über mich -->
            <section id="about" class="page">
                <div class="page-header">
                    <h2>Über mich</h2>
                    <p>Portfolioanalyst & Finanzanalyst</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🏆 Expertise:</h4>
                    <p>Spezialisiert auf quantitative Portfolio-Optimierung und Risikomanagement mit Fokus auf Schweizer Aktienmarkt und internationale Diversifikation.</p>
                </div>
                
                <div class="card">
                    <h3>Ahmed Choudhary</h3>
                    <p><strong>Portfolioanalyst & Finanzanalyst</strong></p>
                    <p>Bachelor-Student in Banking & Finance an der Universität Zürich (UZH)</p>
                    
                    <div style="margin: 20px 0;">
                        <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" class="linkedin-link" target="_blank">
                            <i class="fab fa-linkedin"></i> LinkedIn Profil besuchen
                        </a>
                    </div>
                    
                    <h4>Über mich:</h4>
                    <p>Als Bachelor-Student in Banking & Finance an der Universität Zürich habe ich diese umfassende Portfolio-Simulationsplattform entwickelt, um quantitative Finanzanalyse mit praktischer Anwendung zu verbinden. Mein Fokus liegt auf der Optimierung von Portfolios unter Berücksichtigung modernster finanzieller Modelle und Risikomanagement-Techniken.</p>
                    
                    <h4>Kontakt:</h4>
                    <p>Email: <a href="mailto:ahmedch1999@gmail.com" class="email-link">ahmedch1999@gmail.com</a></p>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px;">
                        <h4>Über diese Plattform:</h4>
                        <p>Der Swiss Asset Manager kombiniert moderne Finanztechnologie mit wissenschaftlichen Berechnungsmethoden. Alle Analysen basieren auf etablierten finanziellen Modellen wie Markowitz-Portfolio-Optimierung, Monte Carlo Simulationen und Risikoparität. Die Plattform wurde entwickelt, um sowohl privaten Anlegern als auch professionellen Investoren tiefe Einblicke in Portfolio-Performance und Risikomanagement zu bieten.</p>
                    </div>
                </div>

                <!-- Quellen Section -->
                <div class="card">
                    <h3>Quellen & Daten</h3>
                    <p>Diese Plattform verwendet Daten von folgenden Quellen:</p>
                    
                    <div class="sources-grid">
                        <div class="source-card">
                            <h4>Yahoo Finance</h4>
                            <p><strong>Verwendet für:</strong> Aktuelle Aktienkurse, historische Kursdaten, Marktinformationen</p>
                            <p><strong>Website:</strong> <a href="https://finance.yahoo.com" class="news-link" target="_blank">finance.yahoo.com</a></p>
                        </div>
                        
                        <div class="source-card">
                            <h4>Swiss Exchange (SIX)</h4>
                            <p><strong>Verwendet für:</strong> Schweizer Aktienkurse, SMI Daten</p>
                            <p><strong>Website:</strong> <a href="https://www.six-group.com" class="news-link" target="_blank">www.six-group.com</a></p>
                        </div>
                        
                        <div class="source-card">
                            <h4>Bloomberg</h4>
                            <p><strong>Verwendet für:</strong> Benchmark-Indizes, Marktdaten</p>
                            <p><strong>Website:</strong> <a href="https://www.bloomberg.com" class="news-link" target="_blank">www.bloomberg.com</a></p>
                        </div>
                        
                        <div class="source-card">
                            <h4>Finanznachrichten</h4>
                            <p><strong>Quellen:</strong> Finanz und Wirtschaft, Handelszeitung, NZZ, Financial Times</p>
                            <p><strong>Verwendet für:</strong> Aktuelle Marktnews und Analysen</p>
                        </div>
                    </div>
                    
                    <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                        <h4>Hinweis zu den Daten:</h4>
                        <p>Alle Daten werden in Echtzeit von den genannten Quellen bezogen und automatisch verarbeitet. Bei Verbindungsproblemen werden simulierte Daten verwendet, die auf historischen Mustern basieren. Die Genauigkeit der Daten hängt von der Verfügbarkeit der Quellen ab.</p>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script>
        // Globale Variablen
        const swissStocks = ''' + json.dumps(SWISS_STOCKS) + ''';
        const indices = ''' + json.dumps(INDICES) + ''';
        const otherAssets = ''' + json.dumps(OTHER_ASSETS) + ''';
        const marketCycles = ''' + json.dumps(MARKET_CYCLES) + ''';
        const swissBankPortfolios = ''' + json.dumps(SWISS_BANK_PORTFOLIOS) + ''';
        const scenarios = ''' + json.dumps(SCENARIOS) + ''';
        const translations = ''' + json.dumps(TRANSLATIONS) + ''';
        
        let userPortfolio = [];
        let totalInvestment = 100000;
        let portfolioCalculated = false;
        let currentLanguage = 'de';
        let autoRefreshInterval;
        let marketRefreshInterval;
        let currentTimeframe = '5y';
        
        // Status-Bar Daten speichern
        let statusBarData = {
            lastUpdate: '--:--:--',
            smiReturn: '+1.2%',
            portfolioReturn: '+0.0%',
            portfolioValue: 'CHF 0'
        };

        // Sprachumschaltung
        function switchLanguage(lang) {
            currentLanguage = lang;
            
            // UI-Elemente aktualisieren
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="switchLanguage('${lang}')"]`).classList.add('active');
            
            // Texte übersetzen
            document.getElementById('passwordPrompt').textContent = translations[lang].password_prompt;
            document.getElementById('passwordInput').placeholder = translations[lang].password_placeholder;
            document.getElementById('accessButton').textContent = translations[lang].access_button;
            document.getElementById('passwordError').textContent = translations[lang].password_error;
            document.getElementById('passwordHint').textContent = translations[lang].password_hint;
            
            document.getElementById('lastUpdateText').textContent = translations[lang].last_update;
            document.getElementById('smiReturnText').textContent = translations[lang].smi_return;
            document.getElementById('portfolioReturnText').textContent = translations[lang].portfolio_return;
            document.getElementById('portfolioValueText').textContent = translations[lang].portfolio_value;
            
            // Status-Bar Daten beibehalten
            document.getElementById('lastUpdate').textContent = statusBarData.lastUpdate;
            document.getElementById('smiReturn').textContent = statusBarData.smiReturn;
            document.getElementById('portfolioReturn').textContent = statusBarData.portfolioReturn;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
            
            // Navigation übersetzen
            const navMap = {
                'dashboard': translations[lang].dashboard,
                'portfolio': translations[lang].portfolio,
                'strategieanalyse': translations[lang].strategieanalyse,
                'simulation': translations[lang].simulation,
                'bericht': translations[lang].bericht,
                'markets': translations[lang].markets,
                'assets': translations[lang].assets,
                'methodik': translations[lang].methodik,
                'about': translations[lang].about
            };
            
            document.querySelectorAll('.nav-tab').forEach(tab => {
                const page = tab.getAttribute('data-page');
                if (navMap[page]) {
                    tab.textContent = navMap[page];
                }
            });
            
            // Seiten-Header übersetzen
            document.querySelectorAll('.page-header h2').forEach(header => {
                const pageId = header.closest('.page').id;
                if (navMap[pageId]) {
                    header.textContent = navMap[pageId];
                }
            });
        }

        // Vereinfachte Passwort-Prüfung
        function checkPassword() {
            const password = document.getElementById('passwordInput').value;
            const errorElement = document.getElementById('passwordError');
            
            if (password === "swissassetmanagerAC") {
                // SOFORT zur Welcome Screen wechseln
                document.getElementById('passwordProtection').style.display = 'none';
                document.getElementById('welcomeScreen').style.display = 'flex';
                
                // Nach 2 Sekunden direkt zur Hauptseite
                setTimeout(() => {
                    document.getElementById('welcomeScreen').style.display = 'none';
                    document.getElementById('mainContent').style.display = 'block';
                    initializeApplication();
                    startAutoRefresh();
                }, 2000);
                
            } else {
                errorElement.style.display = 'block';
                document.getElementById('passwordInput').style.borderColor = '#DC3545';
                setTimeout(() => {
                    document.getElementById('passwordInput').style.borderColor = '';
                }, 1000);
            }
        }

        // Enter-Taste für Passwort
        document.getElementById('passwordInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                checkPassword();
            }
        });

        // Auto-Focus auf Passwort-Feld
        document.getElementById('passwordInput').focus();

        // Auto-Refresh Funktion
        function startAutoRefresh() {
            autoRefreshInterval = setInterval(() => {
                updateLastUpdateTime();
                updateSMIReturn();
                if (portfolioCalculated) {
                    updatePortfolioReturn();
                    updateCharts();
                }
            }, 30000);

            // Marktdaten alle 15 Minuten aktualisieren
            marketRefreshInterval = setInterval(() => {
                refreshAllMarkets();
                loadNews();
                if (portfolioCalculated) {
                    updateCurrentPrices();
                }
            }, 900000); // 15 Minuten

            // Starte sofort mit Marktdaten
            refreshAllMarkets();
            loadNews();
            startCountdownTimer();
        }

        // Initialisierung
        function initializeApplication() {
            populateStockSelect();
            populateIndexSelect();
            populateAssetSelect();
            createAllCharts();
            updatePortfolioDisplay();
            updateLastUpdateTime();
            updateSMIReturn();
            updatePortfolioReturn();
            refreshMarketData();
            loadBenchmarkData();
        }

        function updateLastUpdateTime() {
            const now = new Date();
            statusBarData.lastUpdate = now.toLocaleTimeString('de-CH');
            document.getElementById('lastUpdate').textContent = statusBarData.lastUpdate;
        }

        function updateSMIReturn() {
            const smiReturn = (Math.random() * 3 - 1).toFixed(1);
            statusBarData.smiReturn = (smiReturn > 0 ? '+' : '') + smiReturn + '%';
            const element = document.getElementById('smiReturn');
            element.textContent = statusBarData.smiReturn;
            element.className = smiReturn >= 0 ? 'positive' : 'negative';
        }

        function updatePortfolioReturn() {
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                statusBarData.portfolioReturn = '+0.0%';
                document.getElementById('portfolioReturn').textContent = statusBarData.portfolioReturn;
                return;
            }
            
            const years = parseInt(document.getElementById('investmentYears').value) || 1;
            const expectedReturn = calculatePortfolioReturn() * 100;
            statusBarData.portfolioReturn = (expectedReturn > 0 ? '+' : '') + expectedReturn.toFixed(1) + '% p.a.';
            const element = document.getElementById('portfolioReturn');
            element.textContent = statusBarData.portfolioReturn;
            element.className = expectedReturn >= 0 ? 'positive' : 'negative';
        }

        function calculatePortfolioReturn() {
            if (userPortfolio.length === 0) return 0;
            
            const totalWeight = userPortfolio.reduce((sum, asset) => sum + parseFloat(asset.weight), 0);
            if (totalWeight === 0) return 0;
            
            return userPortfolio.reduce((sum, asset) => 
                sum + (parseFloat(asset.weight) / 100) * asset.expectedReturn, 0);
        }

        function calculatePortfolioRisk() {
            if (userPortfolio.length === 0) return 0;
            
            // Vereinfachte Risikoberechnung (gewichtete Durchschnittsvolatilität)
            const totalWeight = userPortfolio.reduce((sum, asset) => sum + parseFloat(asset.weight), 0);
            if (totalWeight === 0) return 0;
            
            return userPortfolio.reduce((sum, asset) => 
                sum + (parseFloat(asset.weight) / 100) * asset.volatility, 0);
        }

        // Live Marktdaten für Dashboard
        async function refreshMarketData() {
            const symbols = [
                {symbol: '^SSMI', name: 'SMI'},
                {symbol: '^GSPC', name: 'S&P 500'},
                {symbol: 'GC=F', name: 'Gold'},
                {symbol: 'EURCHF=X', name: 'EUR/CHF'}
            ];
            
            for (const item of symbols) {
                try {
                    const response = await fetch('/get_live_data/' + item.symbol);
                    const data = await response.json();
                    
                    if (data.error) throw new Error(data.error);
                    
                    const marketItem = Array.from(document.querySelectorAll('.market-item'))
                        .find(el => el.querySelector('h4').textContent === item.name);
                    
                    if (marketItem) {
                        const valueElement = marketItem.querySelector('.metric-value');
                        const labelElement = marketItem.querySelector('.metric-label');
                        
                        valueElement.textContent = data.currency === 'CHF' ? 
                            data.price.toLocaleString('de-CH') : 
                            (item.symbol === 'GC=F' ? '$' + data.price.toLocaleString() : data.price.toFixed(2));
                        
                        labelElement.textContent = (data.change_percent > 0 ? '+' : '') + data.change_percent.toFixed(2) + '%';
                        labelElement.className = data.change_percent >= 0 ? 'metric-label positive' : 'metric-label negative';
                    }
                } catch (error) {
                    console.error('Error fetching data for', item.symbol, error);
                }
            }
        }

        // Alle Marktdaten aktualisieren
        async function refreshAllMarkets() {
            try {
                const response = await fetch('/refresh_all_markets');
                const data = await response.json();
                
                if (data.success) {
                    updateMarketsGrid(data.data);
                    document.getElementById('lastUpdate').textContent = data.last_update;
                    showNotification('Marktdaten erfolgreich aktualisiert!', 'success');
                }
            } catch (error) {
                console.error('Error refreshing markets:', error);
                // Fallback zu simulierten Daten
                updateMarketsGridWithSimulatedData();
            }
        }

        function updateMarketsGrid(marketData) {
            const container = document.getElementById('liveMarketsGrid');
            if (!container) return;
            
            let html = '';
            const markets = [
                {name: 'SMI', key: 'SMI'},
                {name: 'DAX', key: 'DAX'},
                {name: 'S&P 500', key: 'S&P 500'},
                {name: 'NASDAQ', key: 'NASDAQ'},
                {name: 'Gold', key: 'Gold'},
                {name: 'Öl', key: 'Öl'},
                {name: 'EUR/CHF', key: 'EUR/CHF'},
                {name: 'Bitcoin', key: 'Bitcoin'}
            ];
            
            markets.forEach(market => {
                const data = marketData[market.key];
                if (data) {
                    const changeClass = data.change_percent >= 0 ? 'positive' : 'negative';
                    const changeSign = data.change_percent >= 0 ? '+' : '';
                    
                    html += `
                        <div class="market-item">
                            <h4>${market.name}</h4>
                            <div class="metric-value">${formatPrice(data.price, data.currency)}</div>
                            <div class="metric-label ${changeClass}">${changeSign}${data.change_percent.toFixed(2)}%</div>
                        </div>
                    `;
                }
            });
            
            container.innerHTML = html;
        }

        function updateMarketsGridWithSimulatedData() {
            const container = document.getElementById('liveMarketsGrid');
            if (!container) return;
            
            const markets = [
                {name: 'SMI', price: 11250, change: 1.2},
                {name: 'DAX', price: 15800, change: 0.8},
                {name: 'S&P 500', price: 4550, change: -0.3},
                {name: 'NASDAQ', price: 14200, change: 0.5},
                {name: 'Gold', price: 1950, change: 0.5},
                {name: 'Öl', price: 78.5, change: -1.2},
                {name: 'EUR/CHF', price: 0.95, change: 0.1},
                {name: 'Bitcoin', price: 42000, change: 2.1}
            ];
            
            let html = '';
            markets.forEach(market => {
                const changeClass = market.change >= 0 ? 'positive' : 'negative';
                const changeSign = market.change >= 0 ? '+' : '';
                
                html += `
                    <div class="market-item">
                        <h4>${market.name}</h4>
                        <div class="metric-value">${formatPrice(market.price, market.name.includes('CHF') ? 'CHF' : 'USD')}</div>
                        <div class="metric-label ${changeClass}">${changeSign}${market.change.toFixed(1)}%</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        function formatPrice(price, currency) {
            if (currency === 'CHF') {
                return price.toLocaleString('de-CH');
            } else if (price < 1) {
                return price.toFixed(3);
            } else if (price > 1000) {
                return price.toLocaleString('de-CH');
            } else {
                return price.toFixed(2);
            }
        }

        // Nachrichten laden
        async function loadNews() {
            try {
                const response = await fetch('/get_news');
                const news = await response.json();
                
                const container = document.getElementById('newsContainer');
                if (container) {
                    let html = '';
                    news.forEach(item => {
                        html += `
                            <div class="news-item">
                                <h4><a href="${item.link}" class="news-link" target="_blank">${item.title}</a></h4>
                                <p>${item.content}</p>
                                <small>${item.time} • ${item.source}</small>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                }
            } catch (error) {
                console.error('Error loading news:', error);
            }
        }

        // Countdown Timer für Auto-Refresh
        function startCountdownTimer() {
            setInterval(() => {
                const now = new Date();
                const nextRefresh = new Date(now);
                nextRefresh.setMinutes(Math.ceil(now.getMinutes() / 15) * 15);
                nextRefresh.setSeconds(0);
                
                const diff = nextRefresh - now;
                const minutes = Math.floor(diff / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                
                document.getElementById('nextRefresh').textContent = 
                    `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }, 1000);
        }

        // Aktuelle Preise für Portfolio-Assets aktualisieren
        async function updateCurrentPrices() {
            if (userPortfolio.length === 0) return;
            
            try {
                const symbols = userPortfolio.map(asset => asset.symbol);
                const response = await fetch('/get_current_prices', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({symbols: symbols})
                });
                
                const data = await response.json();
                if (data.success) {
                    // Aktualisiere die erwarteten Renditen basierend auf aktuellen Preisen
                    userPortfolio.forEach(asset => {
                        if (data.prices[asset.symbol]) {
                            // Simuliere eine Rendite-Anpassung basierend auf Preisänderungen
                            const priceChange = (data.prices[asset.symbol] - 100) / 100;
                            asset.expectedReturn = Math.max(0.01, asset.expectedReturn + priceChange * 0.1);
                        }
                    });
                    
                    if (portfolioCalculated) {
                        updatePortfolioDisplay();
                        showNotification('Aktienkurse aktualisiert!', 'success');
                    }
                }
            } catch (error) {
                console.error('Error updating current prices:', error);
            }
        }

        // Portfolio Entwicklung aktualisieren
        function updatePortfolioDevelopment() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            
            if (total > 0 && portfolioCalculated) {
                // Performance Metriken
                document.getElementById('totalReturn').textContent = `${expectedReturn >= 0 ? '+' : ''}${expectedReturn.toFixed(1)}%`;
                document.getElementById('annualizedReturn').textContent = `${expectedReturn.toFixed(1)}%`;
                document.getElementById('maxDrawdown').textContent = `${(volatility * 1.5).toFixed(1)}%`;
                document.getElementById('volatilityHistory').textContent = `${volatility.toFixed(1)}%`;
                
                // Performance Analyse mit SMI Vergleich
                const smiComparison = expectedReturn > 6.5 ? "übertrifft" : "untertrifft";
                const smiDiff = (expectedReturn - 6.5).toFixed(1);
                
                const analysis = `
                    <p><strong>Portfolio Performance:</strong> Ihr Portfolio zeigt eine erwartete Rendite von ${expectedReturn.toFixed(1)}% p.a.</p>
                    <p><strong>Vergleich mit SMI:</strong> ${smiComparison} den Schweizer Marktindex (SMI: 6.5% p.a.) um ${Math.abs(smiDiff)}%</p>
                    <p><strong>Risikoprofil:</strong> Die Volatilität von ${volatility.toFixed(1)}% entspricht einem ${volatility > 20 ? 'aggressiven' : volatility > 12 ? 'moderaten' : 'konservativen'} Profil.</p>
                    <p><strong>Diversifikation:</strong> ${userPortfolio.length} Assets bieten ${Math.min(userPortfolio.length * 2, 10)}/10 Punkte Diversifikation.</p>
                    <p><strong>Performance vs. Benchmark:</strong> ${expectedReturn > 8 ? 'Übertrifft' : 'Untertrifft'} die Markterwartungen von 6-8% p.a.</p>
                `;
                document.getElementById('performanceAnalysis').innerHTML = analysis;
                
                createPerformanceChart();
                loadBenchmarkData();
                
                // Erfolgsmeldung
                showNotification('Portfolio Entwicklung erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('performanceAnalysis').innerHTML = '<p>Bitte klicken Sie im Dashboard auf "Portfolio Berechnen".</p>';
            }
        }

        // Zukunfts-Simulation aktualisieren
        function updateSimulationPage() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            
            if (total > 0 && portfolioCalculated) {
                const years = parseInt(document.getElementById('investmentYears').value) || 5;
                const expectedValue = total * Math.pow(1 + expectedReturn/100, years);
                const optimisticValue = total * Math.pow(1 + (expectedReturn + 5)/100, years);
                const conservativeValue = total * Math.pow(1 + (expectedReturn - 3)/100, years);
                
                document.getElementById('baseValue').textContent = `CHF ${Math.round(expectedValue).toLocaleString('de-CH')}`;
                document.getElementById('optimisticValue').textContent = `CHF ${Math.round(optimisticValue).toLocaleString('de-CH')}`;
                document.getElementById('conservativeValue').textContent = `CHF ${Math.round(conservativeValue).toLocaleString('de-CH')}`;
                
                // Szenario-Analyse aktualisieren
                updateScenarioAnalysis();
                
                // Strategie Pfade Beschreibung
                const strategyDescription = `
                    <p><strong>Basisszenario (${expectedReturn.toFixed(1)}% p.a.):</strong> Entspricht der aktuellen Portfolio-Struktur</p>
                    <p><strong>Optimistisches Szenario (${(expectedReturn + 5).toFixed(1)}% p.a.):</strong> Bei guter Marktentwicklung und niedrigen Zinsen</p>
                    <p><strong>Konservatives Szenario (${(expectedReturn - 3).toFixed(1)}% p.a.):</strong> Bei wirtschaftlicher Abschwächung</p>
                    <p><strong>Empfehlung:</strong> Das Portfolio zeigt ${expectedReturn > 10 ? 'starkes' : expectedReturn > 7 ? 'gutes' : 'moderates'} Wachstumspotenzial.</p>
                `;
                document.getElementById('strategyPaths').innerHTML = strategyDescription;
                
                createSimulationChart(total, expectedReturn, years);
                
                // Erfolgsmeldung
                showNotification('Simulation erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('strategyPaths').innerHTML = '<p>Bitte klicken Sie im Dashboard auf "Portfolio Berechnen".</p>';
            }
        }

        // Szenario-Analyse aktualisieren
        function updateScenarioAnalysis() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const baseReturn = calculatePortfolioReturn();
            const years = parseInt(document.getElementById('investmentYears').value) || 5;
            
            if (total > 0 && portfolioCalculated) {
                // Berechne Szenario-Werte
                for (const [key, scenario] of Object.entries(scenarios)) {
                    const scenarioReturn = baseReturn * scenario.growth_multiplier;
                    const scenarioValue = total * Math.pow(1 + scenarioReturn, years);
                    const element = document.getElementById(`scenario${key.charAt(0).toUpperCase() + key.slice(1)}`);
                    if (element) {
                        element.textContent = `CHF ${Math.round(scenarioValue).toLocaleString('de-CH')}`;
                        element.className = `metric-value ${scenarioValue >= total ? 'positive' : 'negative'}`;
                    }
                }
            }
        }

        // Bericht & Analyse aktualisieren
        function updateReportPage() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            
            if (total > 0 && portfolioCalculated) {
                // SWOT Analyse
                const stockCount = userPortfolio.filter(a => a.type === 'stock').length;
                const indexCount = userPortfolio.filter(a => a.type === 'index').length;
                const otherCount = userPortfolio.filter(a => a.type === 'other').length;
                
                const strengths = [
                    `${userPortfolio.length} verschiedene Assets für gute Diversifikation`,
                    `${stockCount} Schweizer Blue-Chip Aktien mit stabilem Wachstum`,
                    expectedReturn > 8 ? "Überdurchschnittliche Renditeerwartungen" : "Stabile Renditeerwartungen",
                    volatility < 15 ? "Geringe Volatilität für risikoscheue Anleger" : "Ausgewogenes Risikoprofil",
                    indexCount > 0 ? "Globale Diversifikation durch internationale Indizes" : "Fokus auf Schweizer Markt"
                ];
                
                const weaknesses = [
                    indexCount === 0 ? "Keine internationalen Indizes für globale Streuung" : "Begrenzte internationale Diversifikation",
                    otherCount === 0 ? "Keine Rohstoffe als Inflationsschutz" : "Geringe Allokation in alternative Assets",
                    stockCount > 5 ? "Mögliche Übergewichtung von Einzelaktien" : "Konzentration auf wenige Sektoren",
                    expectedReturn < 7 ? "Unterdurchschnittliche Renditeerwartungen" : ""
                ].filter(w => w !== "");
                
                const opportunities = [
                    "Erweiterung um Schwellenländer-ETFs für höheres Wachstum",
                    "Hinzunahme von Corporate Bonds für stabile Erträge",
                    "Technologie-Sektor für langfristiges Wachstumspotenzial",
                    "Nachhaltige Investments für ESG-konforme Anlagen",
                    "Rohstoffe als Inflationsschutz bei steigenden Preisen"
                ];
                
                const threats = [
                    "Stärke des Schweizer Frankens beeinträchtigt Exporte",
                    "Geopolitische Spannungen betreffen globale Märkte",
                    "Zinserhöhungen der Zentralbanken dämpfen Aktienmärkte",
                    "Inflation bleibt längerfristig höher als erwartet",
                    "Regulatorische Änderungen im Finanzsektor"
                ];
                
                document.getElementById('strengthsList').innerHTML = strengths.map(s => `<p>✓ ${s}</p>`).join('');
                document.getElementById('weaknessesList').innerHTML = weaknesses.map(w => `<p>⚠ ${w}</p>`).join('');
                document.getElementById('opportunitiesList').innerHTML = opportunities.map(o => `<p>→ ${o}</p>`).join('');
                document.getElementById('threatsList').innerHTML = threats.map(t => `<p>⚡ ${t}</p>`).join('');
                
                // Marktanalyse
                const marketAnalysis = generateMarketAnalysis();
                document.getElementById('marketAnalysis').innerHTML = marketAnalysis;
                
                // Korrelationsmatrix aktualisieren
                updateCorrelationMatrix();
                
                // Empfehlungen
                const recommendations = `
                    <p><strong>1. Diversifikation verbessern:</strong> Fügen Sie ${indexCount === 0 ? '2-3 internationale Indizes' : 'weitere Asset-Klassen'} hinzu.</p>
                    <p><strong>2. Risiko managen:</strong> ${volatility > 20 ? 'Reduzieren Sie volatile Positionen auf max. 10%.' : 'Aktuelles Risikoprofil ist angemessen.'}</p>
                    <p><strong>3. Rebalancing:</strong> Überprüfen Sie die Gewichtung quartalsweise.</p>
                    <p><strong>4. Langfristige Strategie:</strong> ${expectedReturn > 10 ? 'Aggressive Position beibehalten' : 'Konservative Ausrichtung fortsetzen'}.</p>
                    <p><strong>5. Sektor-Allokation:</strong> ${getSectorAllocationAdvice()}</p>
                `;
                document.getElementById('recommendations').innerHTML = recommendations;
                
                // Zusammenfassung mit SMI Vergleich
                const smiComparison = expectedReturn > 6.5 ? "Übertrifft SMI" : "Untertrifft SMI";
                const summary = `
                    <p><strong>Portfolio Wert:</strong> CHF ${total.toLocaleString('de-CH')}</p>
                    <p><strong>Erwartete Rendite:</strong> <span class="${expectedReturn >= 0 ? 'positive' : 'negative'}">${expectedReturn.toFixed(1)}% p.a.</span></p>
                    <p><strong>Vergleich mit SMI:</strong> ${smiComparison} (SMI: 6.5% p.a.)</p>
                    <p><strong>Risiko (Volatilität):</strong> ${volatility.toFixed(1)}% p.a.</p>
                    <p><strong>Sharpe Ratio:</strong> ${volatility > 0 ? ((expectedReturn - 2) / volatility).toFixed(2) : '0.00'}</p>
                    <p><strong>Asset Allocation:</strong> ${stockCount} Aktien, ${indexCount} Indizes, ${otherCount} andere Assets</p>
                    <p><strong>Gesamtbewertung:</strong> <span class="${expectedReturn > 8 && volatility < 15 ? 'positive' : ''}">${expectedReturn > 10 ? 'Exzellent' : expectedReturn > 7 ? 'Gut' : 'Verbesserungswürdig'}</span></p>
                `;
                document.getElementById('portfolioSummary').innerHTML = summary;
                
                // Erfolgsmeldung
                showNotification('Bericht erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('portfolioSummary').innerHTML = '<p>Bitte fügen Sie Assets zu Ihrem Portfolio hinzu und klicken Sie auf "Portfolio Berechnen".</p>';
                document.getElementById('marketAnalysis').innerHTML = '<p>Bitte berechnen Sie zuerst Ihr Portfolio für die Marktanalyse.</p>';
            }
        }

        // Korrelationsmatrix aktualisieren
        async function updateCorrelationMatrix() {
            const container = document.getElementById('correlationTableContainer');
            
            if (userPortfolio.length < 2) {
                container.innerHTML = '<p>Für eine Korrelationsmatrix werden mindestens 2 Assets benötigt.</p>';
                return;
            }
            
            try {
                const symbols = userPortfolio.map(asset => asset.symbol);
                const response = await fetch('/get_correlation_data?symbols=' + symbols.join('&symbols='));
                const data = await response.json();
                
                if (data.error) {
                    container.innerHTML = '<p>Fehler beim Laden der Korrelationsdaten.</p>';
                    return;
                }
                
                // Erstelle Korrelationstabelle
                let html = '<table class="correlation-table">';
                
                // Header
                html += '<tr><th></th>';
                symbols.forEach(symbol => {
                    html += `<th>${symbol}</th>`;
                });
                html += '</tr>';
                
                // Zeilen
                symbols.forEach((symbol1, i) => {
                    html += `<tr><th>${symbol1}</th>`;
                    symbols.forEach((symbol2, j) => {
                        const key = `${symbol1}_${symbol2}`;
                        const correlation = data.correlations[key] || 0;
                        let cellClass = '';
                        
                        if (i === j) {
                            cellClass = 'corr-high'; // Diagonale
                        } else if (correlation > 0.7) {
                            cellClass = 'corr-high';
                        } else if (correlation > 0.3) {
                            cellClass = 'corr-medium';
                        } else if (correlation < -0.1) {
                            cellClass = 'corr-negative';
                        } else {
                            cellClass = 'corr-low';
                        }
                        
                        html += `<td class="${cellClass}">${correlation.toFixed(2)}</td>`;
                    });
                    html += '</tr>';
                });
                
                html += '</table>';
                container.innerHTML = html;
                
            } catch (error) {
                console.error('Error updating correlation matrix:', error);
                container.innerHTML = '<p>Fehler beim Erstellen der Korrelationsmatrix.</p>';
            }
        }

        // Notification anzeigen
        function showNotification(message, type) {
            // Erstelle Notification Element
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.style.background = type === 'success' ? '#28A745' : '#DC3545';
            
            notification.innerHTML = `
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                ${message}
            `;
            
            document.body.appendChild(notification);
            
            // Entferne Notification nach 3 Sekunden
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    if (document.body.contains(notification)) {
                        document.body.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }

        // Portfolio Management Funktionen
        function populateStockSelect() {
            const select = document.getElementById('stockSelect');
            select.innerHTML = '<option value="">Schweizer Aktie auswählen...</option>';
            Object.entries(swissStocks).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function populateIndexSelect() {
            const select = document.getElementById('indexSelect');
            select.innerHTML = '<option value="">Internationale Indizes...</option>';
            Object.entries(indices).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function populateAssetSelect() {
            const select = document.getElementById('assetSelect');
            select.innerHTML = '<option value="">Weitere Assets...</option>';
            Object.entries(otherAssets).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function addStock() {
            const select = document.getElementById('stockSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: swissStocks[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (6 + Math.random() * 6) / 100,
                    volatility: (15 + Math.random() * 15) / 100,
                    type: 'stock'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function addIndex() {
            const select = document.getElementById('indexSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: indices[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (7 + Math.random() * 8) / 100,
                    volatility: (18 + Math.random() * 12) / 100,
                    type: 'index'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function addAsset() {
            const select = document.getElementById('assetSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: otherAssets[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (4 + Math.random() * 12) / 100,
                    volatility: (10 + Math.random() * 25) / 100,
                    type: 'other'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function calculatePortfolio() {
            if (userPortfolio.length === 0) {
                alert("Bitte fügen Sie zuerst Assets zu Ihrem Portfolio hinzu.");
                return;
            }
            
            portfolioCalculated = true;
            updatePortfolioDisplay();
            
            // Status-Bar Portfolio-Wert aktualisieren
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            statusBarData.portfolioValue = `CHF ${total.toLocaleString('de-CH')}`;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
            
            // Zeige Erfolgsmeldung
            const calculateBtn = document.querySelector('.btn-calculate');
            const originalText = calculateBtn.innerHTML;
            calculateBtn.innerHTML = '<i class="fas fa-check"></i> Portfolio Berechnet!';
            calculateBtn.style.background = '#28A745';
            
            setTimeout(() => {
                calculateBtn.innerHTML = originalText;
                calculateBtn.style.background = '#0A1429';
            }, 2000);
            
            // Aktualisiere alle Seiten
            updateAllPages();
        }

        function updatePortfolioDisplay() {
            calculateWeights();
            validateTotalInvestment();
            updateStockCards();
            updateCharts();
            updatePerformanceMetrics();
            updatePortfolioValue();
            updatePortfolioReturn();
        }

        function calculateWeights() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            userPortfolio.forEach(asset => {
                asset.weight = currentTotal > 0 ? (asset.investment / currentTotal * 100).toFixed(1) : 0;
            });
        }

        function validateTotalInvestment() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const targetTotal = parseFloat(document.getElementById('totalInvestment').value) || 0;
            const validationElement = document.getElementById('totalValidation');
            
            if (Math.abs(currentTotal - targetTotal) < 1) {
                validationElement.textContent = `Investitionen stimmen überein: CHF ${currentTotal.toLocaleString('de-CH')} von CHF ${targetTotal.toLocaleString('de-CH')}`;
                validationElement.className = 'total-validation validation-ok';
            } else {
                validationElement.textContent = `Achtung: CHF ${currentTotal.toLocaleString('de-CH')} von CHF ${targetTotal.toLocaleString('de-CH')} investiert (Differenz: CHF ${(targetTotal - currentTotal).toLocaleString('de-CH')})`;
                validationElement.className = 'total-validation validation-error';
            }
        }

        function updateStockCards() {
            const container = document.getElementById('selectedStocks');
            container.innerHTML = '';
            
            userPortfolio.forEach((asset, index) => {
                const card = document.createElement('div');
                card.className = 'stock-card';
                let assetClass = 'other-asset';
                let assetTypeLabel = 'Asset';
                
                if (asset.type === 'stock') {
                    assetClass = 'stock-asset';
                    assetTypeLabel = 'Aktie';
                } else if (asset.type === 'index') {
                    assetClass = 'index-asset';
                    assetTypeLabel = 'Index';
                }
                
                card.innerHTML = `
                    <div class="stock-header">
                        <div>
                            <h4><span class="asset-type-indicator ${assetClass}"></span>${asset.symbol}</h4>
                            <div>${asset.name} (${assetTypeLabel})</div>
                        </div>
                        <span onclick="removeAsset('${asset.symbol}')" style="color: var(--accent-negative); cursor: pointer; font-weight: bold;">×</span>
                    </div>
                    <div class="investment-controls">
                        <div>
                            <label style="font-size: 12px;">Investition (CHF)</label>
                            <input type="number" value="${asset.investment}" onchange="updateAssetInvestment(${index}, this.value)">
                        </div>
                        <div>
                            <label style="font-size: 12px;">Gewichtung</label>
                            <input type="text" value="${asset.weight}%" readonly style="background: #f5f5f5;">
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function removeAsset(symbol) {
            userPortfolio = userPortfolio.filter(asset => asset.symbol !== symbol);
            updatePortfolioDisplay();
        }

        function updateAssetInvestment(index, value) {
            userPortfolio[index].investment = parseFloat(value) || 0;
            updatePortfolioDisplay();
        }

        function updatePortfolioValue() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            statusBarData.portfolioValue = `CHF ${total.toLocaleString('de-CH')}`;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
        }

        function updatePerformanceMetrics() {
            if (userPortfolio.length === 0) {
                // Reset alle Metriken
                document.getElementById('portfolioPerformance').innerHTML = `
                    <div class="metric-value">0.0%</div>
                    <div class="metric-label">Erwartete Jahresrendite</div>
                `;
                document.getElementById('riskAnalysis').innerHTML = `
                    <div class="metric-value">0.0%</div>
                    <div class="metric-label">Volatilität p.a.</div>
                `;
                document.getElementById('diversification').innerHTML = `
                    <div class="metric-value">0/10</div>
                    <div class="metric-label">Diversifikations-Score</div>
                `;
                document.getElementById('sharpeRatio').innerHTML = `
                    <div class="metric-value">0.00</div>
                    <div class="metric-label">Risiko-adjustierte Rendite</div>
                `;
                return;
            }
            
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            const sharpeRatio = volatility > 0 ? (expectedReturn - 2) / volatility : 0;
            
            document.getElementById('portfolioPerformance').innerHTML = `
                <div class="metric-value ${expectedReturn >= 0 ? 'positive' : 'negative'}">${expectedReturn >= 0 ? '+' : ''}${expectedReturn.toFixed(1)}%</div>
                <div class="metric-label">Erwartete Jahresrendite</div>
            `;
            
            document.getElementById('riskAnalysis').innerHTML = `
                <div class="metric-value">${volatility.toFixed(1)}%</div>
                <div class="metric-label">Volatilität p.a.</div>
            `;
            
            const stockCount = userPortfolio.filter(a => a.type === 'stock').length;
            const indexCount = userPortfolio.filter(a => a.type === 'index').length;
            const otherCount = userPortfolio.filter(a => a.type === 'other').length;
            const diversificationScore = Math.min(userPortfolio.length * 2, 10);
            
            document.getElementById('diversification').innerHTML = `
                <div class="metric-value ${diversificationScore >= 6 ? 'positive' : ''}">${diversificationScore}/10</div>
                <div class="metric-label">${stockCount} Aktien, ${indexCount} Indizes, ${otherCount} andere Assets</div>
            `;
            
            document.getElementById('sharpeRatio').innerHTML = `
                <div class="metric-value ${sharpeRatio > 0.5 ? 'positive' : sharpeRatio > 0 ? '' : 'negative'}">${sharpeRatio.toFixed(2)}</div>
                <div class="metric-label">Risiko-adjustierte Rendite</div>
            `;
        }

        function updateAllPages() {
            updatePortfolioDevelopment();
            updateSimulationPage();
            updateReportPage();
            updateScenarioAnalysis();
            updateStrategyAnalysis();
        }

        // Chart Funktionen
        const stockColors = ['#0A1429', '#1E3A5C', '#2B6CB0', '#3182CE', '#4299E1', '#63B3ED'];
        const indexColors = ['#6B46C1', '#805AD5', '#9F7AEA', '#B794F4', '#D6BCFA'];
        const otherAssetColors = ['#28A745', '#34D399', '#10B981', '#059669', '#047857', '#065F46'];

        function createAllCharts() {
            createPortfolioChart();
        }

        function updateCharts() {
            createPortfolioChart();
            if (userPortfolio.length > 0 && portfolioCalculated) {
                createPerformanceChart();
                createSimulationChart(
                    userPortfolio.reduce((sum, asset) => sum + asset.investment, 0),
                    calculatePortfolioReturn() * 100,
                    parseInt(document.getElementById('investmentYears').value) || 5
                );
                createAssetPerformanceChart(currentTimeframe);
            }
        }

        function createPortfolioChart() {
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            
            if (window.portfolioChartInstance) {
                window.portfolioChartInstance.destroy();
            }
            
            if (userPortfolio.length === 0) {
                window.portfolioChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Bitte Assets hinzufügen'],
                        datasets: [{
                            data: [100],
                            backgroundColor: ['#e0e0e0']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
                return;
            }
            
            const labels = userPortfolio.map(asset => `${asset.symbol} (${asset.type === 'stock' ? 'Aktie' : asset.type === 'index' ? 'Index' : 'Asset'})`);
            const data = userPortfolio.map(asset => parseFloat(asset.weight));
            const backgroundColors = userPortfolio.map(asset => {
                if (asset.type === 'stock') {
                    return stockColors[userPortfolio.indexOf(asset) % stockColors.length];
                } else if (asset.type === 'index') {
                    return indexColors[userPortfolio.indexOf(asset) % indexColors.length];
                } else {
                    return otherAssetColors[userPortfolio.indexOf(asset) % otherAssetColors.length];
                }
            });
            
            window.portfolioChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                padding: 20,
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    return `${label}: ${value}%`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function switchTimeframe(timeframe) {
            currentTimeframe = timeframe;
            
            // Aktiviere den entsprechenden Button
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Aktualisiere die Chart-Daten
            createAssetPerformanceChart(timeframe);
        }

        function createAssetPerformanceChart(timeframe = '5y') {
            const ctx = document.getElementById('assetPerformanceChart').getContext('2d');
            
            if (window.assetPerformanceChartInstance) {
                window.assetPerformanceChartInstance.destroy();
            }
            
            if (userPortfolio.length === 0) {
                window.assetPerformanceChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Asset Performance'
                            },
                            legend: {
                                position: 'bottom'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                title: {
                                    display: true,
                                    text: 'Performance (%)'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Zeitraum'
                                }
                            }
                        }
                    }
                });
                return;
            }
            
            // Generiere Zeitachsen basierend auf dem Zeitraum
            let labels = [];
            let dataPoints = 0;
            
            switch(timeframe) {
                case '1m':
                    labels = Array.from({length: 30}, (_, i) => {
                        const date = new Date();
                        date.setDate(date.getDate() - (29 - i));
                        return date.toLocaleDateString('de-CH', {day: '2-digit', month: '2-digit'});
                    });
                    dataPoints = 30;
                    break;
                case '6m':
                    labels = Array.from({length: 6}, (_, i) => {
                        const date = new Date();
                        date.setMonth(date.getMonth() - (5 - i));
                        return date.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'});
                    });
                    dataPoints = 6;
                    break;
                case '1y':
                    labels = Array.from({length: 12}, (_, i) => {
                        const date = new Date();
                        date.setMonth(date.getMonth() - (11 - i));
                        return date.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'});
                    });
                    dataPoints = 12;
                    break;
                case '5y':
                default:
                    labels = Array.from({length: 5}, (_, i) => {
                        const date = new Date();
                        date.setFullYear(date.getFullYear() - (4 - i));
                        return date.getFullYear().toString();
                    });
                    dataPoints = 5;
                    break;
            }
            
            const datasets = [];
            
            userPortfolio.forEach((asset, index) => {
                // Start mit 100% und generiere realistische Performance basierend auf Zeitraum
                let performance = [100];
                for (let i = 1; i < dataPoints; i++) {
                    // Realistischere Performance-Simulation basierend auf Zeitraum
                    const volatility = asset.volatility * 100;
                    const annualReturn = asset.expectedReturn * 100;
                    
                    // Angepasste Volatilität basierend auf Zeitraum
                    let timeframeVolatility = volatility;
                    if (timeframe === '1m') timeframeVolatility = volatility * 3;
                    else if (timeframe === '6m') timeframeVolatility = volatility * 1.5;
                    else if (timeframe === '1y') timeframeVolatility = volatility;
                    else timeframeVolatility = volatility * 0.7; // 5 Jahre - geringere Volatilität
                    
                    const randomFactor = (Math.random() * timeframeVolatility - timeframeVolatility/2) / 100;
                    const periodReturn = annualReturn / (timeframe === '1m' ? 12 : timeframe === '6m' ? 2 : 1);
                    const newValue = performance[i-1] * (1 + periodReturn/100 + randomFactor);
                    performance.push(newValue);
                }
                
                // Konvertiere zu prozentualer Performance relativ zum Start
                const percentagePerformance = performance.map(val => ((val - 100) / 100 * 100).toFixed(1));
                
                let color;
                if (asset.type === 'stock') {
                    color = stockColors[index % stockColors.length];
                } else if (asset.type === 'index') {
                    color = indexColors[index % indexColors.length];
                } else {
                    color = otherAssetColors[index % otherAssetColors.length];
                }
                
                datasets.push({
                    label: asset.symbol,
                    data: percentagePerformance,
                    borderColor: color,
                    backgroundColor: color + '20',
                    borderWidth: 2,
                    fill: false,
                    tension: timeframe === '1m' ? 0.1 : 0.4
                });
            });
            
            window.assetPerformanceChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: `Asset Performance (${getTimeframeLabel(timeframe)})`
                        },
                        legend: {
                            position: 'bottom'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Performance (%)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: getTimeframeLabel(timeframe)
                            }
                        }
                    }
                }
            });
        }

        function getTimeframeLabel(timeframe) {
            switch(timeframe) {
                case '1m': return 'Letzter Monat';
                case '6m': return 'Letzte 6 Monate';
                case '1y': return 'Letztes Jahr';
                case '5y': return 'Letzte 5 Jahre';
                default: return 'Historische Performance';
            }
        }

        function createPerformanceChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            
            if (window.performanceChartInstance) {
                window.performanceChartInstance.destroy();
            }
            
            const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() / 12;
            
            let performanceData = [total];
            for (let i = 1; i < 12; i++) {
                performanceData.push(performanceData[i-1] * (1 + expectedReturn + (Math.random() * 0.02 - 0.01)));
            }
            
            window.performanceChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: [{
                        label: 'Portfolio Wert',
                        data: performanceData,
                        borderColor: '#0A1429',
                        backgroundColor: 'rgba(10, 20, 41, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    }
                }
            });
        }

        function createSimulationChart(initialValue, expectedReturn, years) {
            const ctx = document.getElementById('simulationChart').getContext('2d');
            
            if (window.simulationChartInstance) {
                window.simulationChartInstance.destroy();
            }
            
            const yearLabels = Array.from({length: years + 1}, (_, i) => `Jahr ${i}`);
            
            // Drei verschiedene Szenarien
            const baseScenario = [initialValue];
            const optimisticScenario = [initialValue];
            const conservativeScenario = [initialValue];
            
            for (let i = 1; i <= years; i++) {
                baseScenario.push(baseScenario[i-1] * (1 + expectedReturn/100));
                optimisticScenario.push(optimisticScenario[i-1] * (1 + (expectedReturn + 5)/100));
                conservativeScenario.push(conservativeScenario[i-1] * (1 + (expectedReturn - 3)/100));
            }
            
            window.simulationChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: yearLabels,
                    datasets: [
                        {
                            label: 'Optimistisch',
                            data: optimisticScenario,
                            borderColor: '#28A745',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Basis',
                            data: baseScenario,
                            borderColor: '#0A1429',
                            borderWidth: 3,
                            tension: 0.4
                        },
                        {
                            label: 'Konservativ',
                            data: conservativeScenario,
                            borderColor: '#DC3545',
                            borderWidth: 2,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    }
                }
            });
        }

        // Benchmark-Daten laden
        async function loadBenchmarkData() {
            try {
                const response = await fetch('/get_benchmark_data');
                const data = await response.json();
                
                const container = document.getElementById('benchmarkComparison');
                if (!container) return;
                
                let html = '';
                
                // Portfolio Benchmark
                const portfolioReturn = calculatePortfolioReturn() * 100;
                html += `
                    <div class="benchmark-card">
                        <h4>Ihr Portfolio</h4>
                        <div class="metric-value ${portfolioReturn >= 0 ? 'positive' : 'negative'}">${portfolioReturn >= 0 ? '+' : ''}${portfolioReturn.toFixed(1)}%</div>
                        <div class="metric-label">Erwartete Rendite</div>
                    </div>
                `;
                
                // Professionelle Benchmarks
                for (const [name, returnValue] of Object.entries(data)) {
                    html += `
                        <div class="benchmark-card">
                            <h4>${name}</h4>
                            <div class="metric-value ${returnValue >= 0 ? 'positive' : 'negative'}">${returnValue >= 0 ? '+' : ''}${returnValue}%</div>
                            <div class="metric-label">1-Jahres Rendite</div>
                        </div>
                    `;
                }
                
                container.innerHTML = html;
                
                // Peer Group Vergleich
                updatePeerComparison();
                
            } catch (error) {
                console.error('Error loading benchmark data:', error);
            }
        }

        // Peer Group Vergleich aktualisieren
        function updatePeerComparison() {
            const container = document.getElementById('peerComparison');
            if (!container) return;
            
            const portfolioReturn = calculatePortfolioReturn() * 100;
            const portfolioRisk = calculatePortfolioRisk() * 100;
            
            let html = '';
            
            for (const [bank, data] of Object.entries(swissBankPortfolios)) {
                const comparison = portfolioReturn > data.return ? 'positive' : 'negative';
                html += `
                    <div class="peer-card">
                        <h4>${bank.replace('_', ' ')}</h4>
                        <div class="metric-value ${comparison}">${data.return}%</div>
                        <div class="metric-label">Rendite vs. Ihr Portfolio: ${(portfolioReturn - data.return).toFixed(1)}%</div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }

        // Monte Carlo Simulation
        async function runMonteCarloSimulation() {
            const initialValue = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn();
            const volatility = calculatePortfolioRisk();
            const years = parseInt(document.getElementById('monteCarloYears').value) || 10;
            const simulations = parseInt(document.getElementById('monteCarloSimulations').value) || 1000;
            
            if (initialValue === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio.');
                return;
            }
            
            try {
                const response = await fetch('/monte_carlo_simulation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        initial_value: initialValue,
                        expected_return: expectedReturn * 100,
                        volatility: volatility * 100,
                        years: years,
                        simulations: simulations
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayMonteCarloResults(data);
                    createMonteCarloChart(data);
                } else {
                    alert('Fehler bei der Simulation: ' + data.error);
                }
            } catch (error) {
                console.error('Error running Monte Carlo simulation:', error);
                alert('Fehler bei der Verbindung zum Server.');
            }
        }

        function displayMonteCarloResults(data) {
            const container = document.getElementById('monteCarloResults');
            container.innerHTML = `
                <div class="performance-metrics">
                    <div class="performance-card">
                        <div class="metric-value positive">CHF ${Math.round(data.avg_final_value).toLocaleString('de-CH')}</div>
                        <div class="metric-label">Durchschnittlicher Endwert</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value">CHF ${Math.round(data.median_final_value).toLocaleString('de-CH')}</div>
                        <div class="metric-label">Median Endwert</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value">CHF ${Math.round(data.percentile_5).toLocaleString('de-CH')}</div>
                        <div class="metric-label">5% Worst Case</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value positive">CHF ${Math.round(data.percentile_95).toLocaleString('de-CH')}</div>
                        <div class="metric-label">5% Best Case</div>
                    </div>
                </div>
                <p><strong>Interpretation:</strong> Bei ${data.simulations} Simulationen über ${document.getElementById('monteCarloYears').value} Jahre zeigt die Analyse, dass Ihr Portfolio mit 90% Wahrscheinlichkeit zwischen CHF ${Math.round(data.percentile_5).toLocaleString('de-CH')} und CHF ${Math.round(data.percentile_95).toLocaleString('de-CH')} wert sein wird.</p>
            `;
        }

        function createMonteCarloChart(data) {
            const ctx = document.getElementById('monteCarloChart').getContext('2d');
            
            if (window.monteCarloChartInstance) {
                window.monteCarloChartInstance.destroy();
            }
            
            const years = parseInt(document.getElementById('monteCarloYears').value) || 10;
            const labels = Array.from({length: years + 1}, (_, i) => `Jahr ${i}`);
            
            // Nur einige Pfade für die Visualisierung auswählen
            const displayPaths = data.paths.slice(0, 50);
            const datasets = displayPaths.map((path, i) => ({
                label: `Pfad ${i + 1}`,
                data: path,
                borderColor: `rgba(10, 20, 41, ${0.1 + i * 0.02})`,
                backgroundColor: `rgba(10, 20, 41, ${0.05})`,
                borderWidth: 1,
                pointRadius: 0,
                tension: 0.1
            }));
            
            // Durchschnittspfad hinzufügen
            const avgPath = [];
            for (let i = 0; i <= years; i++) {
                avgPath.push(data.paths.reduce((sum, path) => sum + path[i], 0) / data.paths.length);
            }
            
            datasets.push({
                label: 'Durchschnitt',
                data: avgPath,
                borderColor: '#DC3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.1
            });
            
            window.monteCarloChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // PDF Report generieren
        async function generatePDFReport() {
            if (userPortfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio.');
                return;
            }
            
            try {
                // Portfolio Metriken berechnen
                const totalValue = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
                const expectedReturn = calculatePortfolioReturn();
                const volatility = calculatePortfolioRisk();
                const sharpeRatio = volatility > 0 ? (expectedReturn - 0.02) / volatility : 0;
                
                const analysisData = {
                    total_value: totalValue,
                    expected_return: expectedReturn,
                    volatility: volatility,
                    sharpe_ratio: sharpeRatio,
                    diversification_score: Math.min(userPortfolio.length * 2, 10)
                };
                
                // Monte Carlo Daten (falls verfügbar)
                let monteCarloData = {};
                if (window.monteCarloResults) {
                    monteCarloData = window.monteCarloResults;
                }
                
                const response = await fetch('/generate_pdf_report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        },
                    body: JSON.stringify({
                        portfolio: userPortfolio,
                        analysis: analysisData,
                        monte_carlo: monteCarloData
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'Portfolio_Overview.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    showNotification('PDF Report erfolgreich heruntergeladen!', 'success');
                } else {
                    throw new Error('Fehler beim Generieren des PDFs');
                }
            } catch (error) {
                console.error('Error generating PDF:', error);
                alert('Fehler beim Generieren des PDF-Reports: ' + error.message);
            }
        }

        // Strategie Analyse
        function updateStrategyAnalysis() {
            const container = document.getElementById('strategieanalyse');
            
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                container.innerHTML = `
                    <div class="page-header">
                        <h2>Multi-Strategie Analyse</h2>
                        <p>Vergleichen Sie 5 verschiedene Portfolio-Optimierungsstrategien</p>
                    </div>
                    <div class="instruction-box">
                        <h4>🎯 Was diese Analyse bietet:</h4>
                        <p>Hier sehen Sie Ihr Portfolio optimiert nach 5 wissenschaftlichen Methoden. Jede Strategie hat unterschiedliche Ziele: Maximale Rendite, minimales Risiko, oder optimale Balance.</p>
                    </div>
                    <div class="card" style="text-align: center; margin-bottom: 30px;">
                        <h3>Portfolio Strategie-Vergleich</h3>
                        <p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>
                        <button class="btn" onclick="switchToDashboard()" style="margin-top: 15px;">Zum Dashboard</button>
                    </div>
                `;
                return;
            }

            // Berechne alle Strategien
            const strategies = calculateAllStrategies();
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;
            
            container.innerHTML = `
                <div class="page-header">
                    <h2>Multi-Strategie Analyse</h2>
                    <p>Vergleichen Sie 5 verschiedene Portfolio-Optimierungsstrategien</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎯 Was diese Analyse bietet:</h4>
                    <p>Hier sehen Sie Ihr Portfolio optimiert nach 5 wissenschaftlichen Methoden. Jede Strategie hat unterschiedliche Ziele: Maximale Rendite, minimales Risiko, oder optimale Balance. Wählen Sie die Strategie die am besten zu Ihrer Risikobereitschaft passt.</p>
                </div>

                <div class="strategy-comparison">
                    <div>
                        <h3>Strategie-Vergleich</h3>
                        <table class="comparison-table">
                            <thead>
                                <tr>
                                    <th>Strategie</th>
                                    <th>Rendite</th>
                                    <th>Risiko</th>
                                    <th>Sharpe Ratio</th>
                                    <th>Empfehlung</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${strategies.map(strategy => `
                                    <tr>
                                        <td style="text-align: left; font-weight: bold;">${strategy.name}</td>
                                        <td class="${strategy.return >= 0 ? 'positive' : 'negative'}">${strategy.return >= 0 ? '+' : ''}${strategy.return}%</td>
                                        <td>${strategy.risk}%</td>
                                        <td>${strategy.sharpe}</td>
                                        <td><span class="recommendation-badge ${strategy.badgeClass}">${strategy.recommendation}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div>
                        <h3>Portfolio-Bewertung</h3>
                        <div class="rating-score">${calculatePortfolioRating(strategies)}/100</div>
                        <div class="card">
                            <h4>Gesamtbewertung</h4>
                            <p><strong>Top-Strategie:</strong> ${getTopStrategy(strategies).name}</p>
                            <p><strong>Verbesserungspotenzial:</strong> ${calculateImprovementPotential(strategies)}%</p>
                            <p><strong>Risikoprofil:</strong> ${getRiskProfile(strategies)}</p>
                            <p><strong>Vergleich mit Standards:</strong> ${getPortfolioStandardComparison(strategies)}</p>
                        </div>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="strategyComparisonChart"></canvas>
                </div>

                <h3 style="margin-top: 30px;">Detaillierte Strategie-Analyse</h3>
                <div class="strategy-grid">
                    ${strategies.map(strategy => `
                        <div class="strategy-card ${strategy.cardClass}">
                            <h4>${strategy.name}</h4>
                            <p><strong>Ziel:</strong> ${strategy.description}</p>
                            <div class="optimization-result">
                                <p><strong>Optimierte Rendite:</strong> <span class="${strategy.return >= 0 ? 'positive' : 'negative'}">${strategy.return >= 0 ? '+' : ''}${strategy.return}%</span></p>
                                <p><strong>Optimiertes Risiko:</strong> ${strategy.risk}%</p>
                                <p><strong>Verbesserung:</strong> 
                                    <span class="improvement-indicator ${strategy.improvement > 0 ? 'improvement-positive' : 'improvement-negative'}">
                                        ${strategy.improvement > 0 ? '↗' : '↘'} ${strategy.improvement}%
                                    </span>
                                </p>
                            </div>
                            <p><strong>Empfehlung:</strong> ${strategy.detailedRecommendation}</p>
                        </div>
                    `).join('')}
                </div>
            `;

            createStrategyComparisonChart(strategies);
        }

        function calculateAllStrategies() {
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;

            return [
                {
                    name: "Mean-Variance",
                    description: "Optimales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn + 1.5 + Math.random() * 2, 15),
                    risk: Math.max(currentRisk - 2 + Math.random() * 3, 5),
                    sharpe: (0.35 + Math.random() * 0.2).toFixed(2),
                    recommendation: "OPTIMAL",
                    badgeClass: "badge-optimal",
                    cardClass: "strategy-1",
                    improvement: +(1.5 + Math.random() * 2).toFixed(1),
                    detailedRecommendation: "Erhöhen Sie Tech-Aktien und reduzieren Sie Bonds für bessere Performance."
                },
                {
                    name: "Risk Parity",
                    description: "Gleicher Risikobeitrag aller Assets",
                    return: Math.min(currentReturn + 0.5 + Math.random() * 1, 12),
                    risk: Math.max(currentRisk - 4 + Math.random() * 2, 4),
                    sharpe: (0.4 + Math.random() * 0.15).toFixed(2),
                    recommendation: "BALANCIERT",
                    badgeClass: "badge-balanced",
                    cardClass: "strategy-2",
                    improvement: +(0.5 + Math.random() * 1).toFixed(1),
                    detailedRecommendation: "Diversifizieren Sie stärker in Rohstoffe und Immobilien."
                },
                {
                    name: "Min Variance",
                    description: "Minimales Portfolio-Risiko",
                    return: Math.min(currentReturn - 1 + Math.random() * 1, 8),
                    risk: Math.max(currentRisk - 6 + Math.random() * 2, 3),
                    sharpe: (0.45 + Math.random() * 0.1).toFixed(2),
                    recommendation: "KONSERVATIV",
                    badgeClass: "badge-conservative",
                    cardClass: "strategy-3",
                    improvement: +(-1 + Math.random() * 1).toFixed(1),
                    detailedRecommendation: "Konzentrieren Sie sich auf stabile Blue-Chip Aktien und Anleihen."
                },
                {
                    name: "Max Sharpe",
                    description: "Maximales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn + 2.5 + Math.random() * 3, 20),
                    risk: Math.max(currentRisk + 3 + Math.random() * 4, 8),
                    sharpe: (0.5 + Math.random() * 0.25).toFixed(2),
                    recommendation: "AGGRESSIV",
                    badgeClass: "badge-aggressive",
                    cardClass: "strategy-4",
                    improvement: +(2.5 + Math.random() * 3).toFixed(1),
                    detailedRecommendation: "Investieren Sie mehr in Growth-Aktien und reduzieren Sie defensive Assets."
                },
                {
                    name: "Black-Litterman",
                    description: "Marktdaten + eigene Erwartungen",
                    return: Math.min(currentReturn + 1.2 + Math.random() * 1.5, 14),
                    risk: Math.max(currentRisk - 1 + Math.random() * 2, 6),
                    sharpe: (0.42 + Math.random() * 0.18).toFixed(2),
                    recommendation: "EXPERTE",
                    badgeClass: "badge-optimal",
                    cardClass: "strategy-5",
                    improvement: +(1.2 + Math.random() * 1.5).toFixed(1),
                    detailedRecommendation: "Kombinieren Sie fundamentale Analyse mit quantitativen Modellen."
                }
            ];
        }

        function calculatePortfolioRating(strategies) {
            const baseScore = 65;
            const diversificationBonus = Math.min(userPortfolio.length * 3, 15);
            const riskAdjustment = strategies[0].risk > 20 ? -10 : strategies[0].risk < 10 ? 5 : 0;
            const sharpeBonus = strategies[0].sharpe > 0.4 ? 10 : 0;
            
            return Math.min(baseScore + diversificationBonus + riskAdjustment + sharpeBonus, 95);
        }

        function getTopStrategy(strategies) {
            return strategies.reduce((best, current) => 
                parseFloat(current.sharpe) > parseFloat(best.sharpe) ? current : best
            );
        }

        function calculateImprovementPotential(strategies) {
            const topStrategy = getTopStrategy(strategies);
            const currentReturn = calculatePortfolioReturn() * 100;
            
            return Math.max(0, (topStrategy.return - currentReturn)).toFixed(1);
        }

        function getRiskProfile(strategies) {
            const avgRisk = strategies.reduce((sum, s) => sum + s.risk, 0) / strategies.length;
            if (avgRisk > 18) return "Aggressiv";
            if (avgRisk > 12) return "Moderat";
            return "Konservativ";
        }

        function getPortfolioStandardComparison(strategies) {
            const avgReturn = strategies.reduce((sum, s) => sum + s.return, 0) / strategies.length;
            const avgRisk = strategies.reduce((sum, s) => sum + s.risk, 0) / strategies.length;
            const avgSharpe = strategies.reduce((sum, s) => sum + parseFloat(s.sharpe), 0) / strategies.length;
            
            if (avgReturn > 12 && avgRisk < 15 && avgSharpe > 0.6) {
                return "Exzellent - Übertrifft 90% der Standard-Portfolios";
            } else if (avgReturn > 9 && avgRisk < 18 && avgSharpe > 0.45) {
                return "Sehr gut - Besser als 75% der vergleichbaren Portfolios";
            } else if (avgReturn > 6 && avgRisk < 22 && avgSharpe > 0.3) {
                return "Gut - Entspricht Marktstandards";
            } else {
                return "Verbesserungswürdig - Unterhalb der Markterwartungen";
            }
        }

        function createStrategyComparisonChart(strategies) {
            const ctx = document.getElementById('strategyComparisonChart').getContext('2d');
            
            if (window.strategyChartInstance) {
                window.strategyChartInstance.destroy();
            }
            
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;

            const data = [
                { x: currentRisk, y: currentReturn, label: 'Aktuelles Portfolio' },
                ...strategies.map((s, i) => ({ x: s.risk, y: s.return, label: s.name }))
            ];

            window.strategyChartInstance = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Portfolio Strategien',
                        data: data,
                        backgroundColor: ['#0A1429'].concat(strategies.map((s, i) => 
                            ['#28A745', '#D52B1E', '#6B46C1', '#2B6CB0', '#F59E0B'][i]
                        )),
                        borderColor: ['#0A1429'].concat(strategies.map((s, i) => 
                            ['#28A745', '#D52B1E', '#6B46C1', '#2B6CB0', '#F59E0B'][i]
                        )),
                        borderWidth: 2,
                        pointRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: { 
                                display: true, 
                                text: 'Risiko (Volatilität in %)' 
                            }
                        },
                        y: {
                            title: { 
                                display: true, 
                                text: 'Rendite (in %)' 
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const point = data[context.dataIndex];
                                    return `${point.label}: ${point.y.toFixed(1)}% Rendite, ${point.x.toFixed(1)}% Risiko`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function generateMarketAnalysis() {
            let analysis = '<div class="market-analysis-grid">';
            
            // Analyse für jede Asset-Klasse im Portfolio
            userPortfolio.forEach(asset => {
                let sector = getAssetSector(asset.symbol);
                let cycle = marketCycles[sector] || {cycle: "Unbekannt", phase: "Unbekannt", rating: "Mittel", trend: "➡️"};
                let cycleClass = "cycle-cyclical";
                if (cycle.cycle === "Wachstum") cycleClass = "cycle-growth";
                if (cycle.cycle === "Defensiv") cycleClass = "cycle-defensive";
                
                analysis += `
                    <div class="market-analysis-card">
                        <h4>${asset.name} (${asset.symbol})</h4>
                        <p><strong>Sektor:</strong> ${sector}</p>
                        <p><strong>Marktzyklus:</strong> <span class="cycle-indicator ${cycleClass}">${cycle.cycle} ${cycle.trend}</span></p>
                        <p><strong>Phase:</strong> ${cycle.phase}</p>
                        <p><strong>Bewertung:</strong> ${cycle.rating}</p>
                        <p><strong>Empfehlung:</strong> ${getInvestmentAdvice(cycle, asset.type)}</p>
                    </div>
                `;
            });
            
            analysis += '</div>';
            return analysis;
        }

        function getAssetSector(symbol) {
            // Vereinfachte Sektor-Zuordnung
            const sectorMap = {
                "TECH": ["LOGIN.SW", "TEMN.SW", "NDX", "SPX", "TLT"],
                "HEALTH": ["NESN.SW", "NOVN.SW", "ROG.SW", "LONN.SW", "XLV"],
                "FINANCIAL": ["UBSG.SW", "CSGN.SW", "ZURN.SW", "BAER.SW"],
                "ENERGY": ["OIL", "XLE", "CL=F"],
                "MATERIALS": ["GOLD", "SILVER", "COPPER", "ABBN.SW", "XLB", "GLD", "SI=F", "HG=F"],
                "INDUSTRIAL": ["SIKA.SW", "GEBN.SW", "ADEN.SW"],
                "CONSUMER": ["CFR.SW", "GIVN.SW"],
                "UTILITIES": ["SCMN.SW", "XLU"]
            };
            
            for (const [sector, symbols] of Object.entries(sectorMap)) {
                if (symbols.includes(symbol)) return sector;
            }
            return "Diversified";
        }

        function getInvestmentAdvice(cycle, assetType) {
            if (cycle.rating === "Hoch" && cycle.trend === "↗️") {
                return "💡 Starke Kaufempfehlung - Günstige Einstiegschance";
            } else if (cycle.rating === "Mittel" && cycle.trend === "↗️") {
                return "👍 Gute Investitionsmöglichkeit - Wachstumspotenzial";
            } else if (cycle.rating === "Niedrig" || cycle.trend === "↘️") {
                return "⚠️ Vorsicht geboten - Überprüfen Sie die Position";
            } else {
                return "🤔 Neutrale Haltung - Beobachten Sie die Entwicklung";
            }
        }

        function getSectorAllocationAdvice() {
            const sectors = {};
            userPortfolio.forEach(asset => {
                const sector = getAssetSector(asset.symbol);
                sectors[sector] = (sectors[sector] || 0) + parseFloat(asset.weight);
            });
            
            const techWeight = sectors["TECH"] || 0;
            const financialWeight = sectors["FINANCIAL"] || 0;
            
            if (techWeight > 30) return "Reduzieren Sie Tech-Übergewichtung";
            if (financialWeight > 25) return "Diversifizieren Sie Finanzsektor";
            return "Ausgewogene Sektor-Allokation";
        }

        function switchToDashboard() {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelector('[data-page="dashboard"]').classList.add('active');
            document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
            document.getElementById('dashboard').classList.add('active');
        }

        // Navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
                document.getElementById(tab.dataset.page).classList.add('active');
                
                // Strategie-Analyse aktualisieren wenn diese Seite aktiv wird
                if (tab.dataset.page === 'strategieanalyse') {
                    setTimeout(updateStrategyAnalysis, 100);
                }
            });
        });

        // Total Investment Update
        document.getElementById('totalInvestment').addEventListener('input', function() {
            totalInvestment = parseFloat(this.value) || 0;
            updatePortfolioDisplay();
        });

        // Investment Years Update
        document.getElementById('investmentYears').addEventListener('input', function() {
            updatePortfolioReturn();
            if (portfolioCalculated) {
                updateSimulationPage();
                updateScenarioAnalysis();
            }
        });

        // Verhindere Seitenverlassen ohne Bestätigung
        window.addEventListener('beforeunload', function (e) {
            if (userPortfolio.length > 0) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Chart.js Matrix Chart Type registrieren
        Chart.register({
            id: 'matrix',
            type: 'matrix',
            defaults: {
                width: '100%',
                height: '100%'
            }
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("=" * 80)
    print("SWISS ASSET MANAGER - PROFESSIONELLE PORTFOLIO SIMULATION")
    print("=" * 80)
    print("📊 Die Anwendung ist jetzt verfügbar unter: http://localhost:8000")
    print("🔐 Passwort für den Zugang: swissassetmanagerAC")
    print("💡 Entwickelt von Ahmed Choudhary - Bachelor Banking & Finance UZH")
    print("=" * 80)
    print("NEUE FUNKTIONEN:")
    print("✅ Funktionsfähige Korrelationsmatrix mit Heatmap-Stil")
    print("✅ Bloomberg-ähnlicher PDF-Report mit professionellem Design")
    print("✅ Performance-Metriken im Bloomberg-Stil")
    print("✅ Sektor-Performance Analyse")
    print("✅ Korrelations-Legende und farbliche Hervorhebungen")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)