"""
Swiss Asset Manager - Data Services Module
Diese Datei enthält alle Datenverarbeitungsfunktionen getrennt von den Flask-Routen.
Dadurch können diese Funktionen direkt vom Scheduler oder über API-Endpunkte aufgerufen werden.

Diese verbesserte Version enthält:
1. Thread-sichere Datenabrufe mit RLock
2. Optimierte Caching-Mechanismen mit Zeitstempeln
3. Fehlerbehandlung und Retry-Logik
4. Detailliertes Logging für Monitoring
5. Erweitertes Health-Checking
"""

import yfinance as yf
import numpy as np
import pandas as pd
import feedparser
import requests
import time
import re
import os
import logging
import random
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
import threading
import json
from typing import Dict, List, Any, Tuple, Optional

# Konfiguration für erweiteres Logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Hauptlogger für allgemeine Meldungen
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("data_services")

# Spezieller Logger für API-Zugriffe
api_logger = logging.getLogger("api_access")
api_handler = logging.FileHandler(f'{log_dir}/api_access.log')
api_handler.setFormatter(logging.Formatter('%(asctime)s [API] %(message)s'))
api_logger.addHandler(api_handler)
api_logger.setLevel(logging.INFO)
api_logger.propagate = False

# Thread-Locks für sichere Zugriffe auf gemeinsame Daten (reentrant für verschachtelte Aufrufe)
data_lock = threading.RLock()
market_data_lock = threading.RLock()
portfolio_data_lock = threading.RLock()
news_data_lock = threading.RLock()
market_cycle_lock = threading.RLock()

# AlphaVantage API-Key (sollte in Produktionsumgebung als Umgebungsvariable gespeichert sein)
AV_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")  # Fallback auf Demo-Key für Test

# Gemeinsamer Cache für Web-App und Scheduler mit erweitertem Status-Tracking
cache = {
    'live_market_data': {},
    'news_data': [],
    'historical_data': {},
    'benchmark_data': {},
    'last_market_update': None,
    'last_news_update': None,
    'last_benchmark_update': None,
    'update_in_progress': {
        'markets': False,
        'portfolios': False,
        'cycles': False,
        'news': False,
        'benchmarks': False
    },
    'update_success_count': {
        'markets': 0,
        'portfolios': 0,
        'cycles': 0,
        'news': 0,
        'benchmarks': 0
    },
    'update_error_count': {
        'markets': 0,
        'portfolios': 0,
        'cycles': 0,
        'news': 0,
        'benchmarks': 0
    }
}

# Maximales Alter der Daten (in Sekunden) - steuert Caching-Strategie
MAX_DATA_AGE = {
    "market_data": 900,     # 15 Minuten
    "portfolios": 3600,     # 1 Stunde  
    "news": 1800,           # 30 Minuten
    "market_cycles": 86400, # 24 Stunden
    "benchmarks": 7200      # 2 Stunden
}

# Retry-Konfiguration
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 10]  # Zunehmende Wartezeit bei Wiederholungen

# Externe Daten werden in diesen Modulvariablen gespeichert und sind für alle Funktionen verfügbar
SWISS_BANK_PORTFOLIOS = {}
MARKET_CYCLES = {}
SCENARIOS = {}

def initialize_data(initial_portfolios, initial_cycles, initial_scenarios):
    """Initialisiert die globalen Datenstrukturen mit den Werten aus app.py"""
    global SWISS_BANK_PORTFOLIOS, MARKET_CYCLES, SCENARIOS
    
    with data_lock:
        SWISS_BANK_PORTFOLIOS = initial_portfolios
        MARKET_CYCLES = initial_cycles
        SCENARIOS = initial_scenarios


def get_yahoo_finance_data(symbol, swiss_stocks, indices):
    """Holt Daten von Yahoo Finance"""
    try:
        # Symbol-Korrektur für Yahoo Finance
        yahoo_symbol = symbol
        
        # Für Schweizer Aktien .SW Endung sicherstellen
        if symbol in swiss_stocks and not symbol.endswith('.SW'):
            yahoo_symbol = f"{symbol}.SW"
        
        # Für Indizes ^ voranstellen wenn nicht vorhanden
        elif symbol in indices and not symbol.startswith('^'):
            # Spezielle Behandlung für bekannte Indizes
            index_mapping = {
                "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", 
                "RUT": "^RUT", "VIX": "^VIX", "COMP": "^IXIC",
                "DAX": "^GDAXI", "CAC": "^FCHI", "FTSE": "^FTSE",
                "SMI": "^SSMI", "NIKKEI": "^N225", "HSI": "^HSI"
            }
            yahoo_symbol = index_mapping.get(symbol, f"^{symbol}")
        
        # Für Rohstoffe/Futures
        elif "=F" in symbol:
            yahoo_symbol = symbol  # Bereits korrekt
        
        # Für Forex
        elif "=X" in symbol:
            yahoo_symbol = symbol  # Bereits korrekt
        
        print(f"Yahoo fetching: {yahoo_symbol} (original: {symbol})")
        
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info
        hist = ticker.history(period="2d", interval="1d")
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        
        # Previous Close berechnen
        if len(hist) > 1:
            previous_close = hist['Close'].iloc[-2]
        else:
            previous_close = info.get('previousClose', current_price * 0.99)
        
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        return {
            "symbol": symbol,
            "yahoo_symbol": yahoo_symbol,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "currency": info.get('currency', 'USD'),
            "name": info.get('longName', info.get('shortName', symbol))
        }
    except Exception as e:
        print(f"Yahoo error for {symbol}: {e}")
        return None


def get_alpha_vantage_data(symbol):
    """Holt Daten von Alpha Vantage als Backup"""
    try:
        # WICHTIG: Hier einen echten Alpha Vantage API-Key einfügen
        # Kostenlos registrieren: https://www.alphavantage.co/support/#api-key
        # Die kostenlose Version erlaubt 5 API-Aufrufe pro Minute und 500 pro Tag
        API_KEY = "demo"  # Bitte ersetzen Sie "demo" durch Ihren eigenen API-Key
        
        # Symbol anpassen für Alpha Vantage
        av_symbol = symbol
        if symbol.endswith('.SW'):
            av_symbol = symbol[:-3] + '.ZRH'  # Alpha Vantage verwendet .ZRH für Schweizer Aktien
        
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={av_symbol}&apikey={API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "Global Quote" in data and data["Global Quote"]:
            quote = data["Global Quote"]
            price = float(quote.get("05. price", 0))
            previous_close = float(quote.get("08. previous close", price * 0.99))
            change = float(quote.get("09. change", 0))
            change_percent = float(quote.get("10. change percent", "0").replace('%', ''))
            
            # Weitere Informationen über eine zweite API-Abfrage holen
            symbol_info = {}
            time.sleep(0.5)  # API-Limit respektieren
            
            info_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={av_symbol}&apikey={API_KEY}"
            info_response = requests.get(info_url)
            info_data = info_response.json()
            
            currency = info_data.get("Currency", "USD")
            name = info_data.get("Name", symbol)
            
            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "currency": currency,
                "name": name
            }
        return None
    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
        return None


def get_live_data(symbol, swiss_stocks, indices):
    """Holt Live-Daten von mehreren Quellen mit Fehlerbehandlung"""
    try:
        # VERSUCH 1: Yahoo Finance (Primary Source)
        yahoo_data = get_yahoo_finance_data(symbol, swiss_stocks, indices)
        if yahoo_data and yahoo_data.get('price', 0) > 0:
            yahoo_data['source'] = 'Yahoo Finance'
            yahoo_data['is_live'] = True  # 🔴 LIVE DATEN Marker
            return yahoo_data

        # VERSUCH 2: Alpha Vantage (Backup)
        alpha_data = get_alpha_vantage_data(symbol)
        if alpha_data and alpha_data.get('price', 0) > 0:
            alpha_data['source'] = 'Alpha Vantage'
            alpha_data['is_live'] = True  # 🔴 LIVE DATEN Marker
            return alpha_data

        # Wenn keine Live-Daten verfügbar sind, klare Fehlermeldung zurückgeben
        return {
            "error": "Keine Live-Daten verfügbar", 
            "source": "API Fehler",
            "symbol": symbol,
            "price": 0,
            "change": 0,
            "change_percent": 0,
            "is_live": False
        }
    except Exception as e:
        print(f"Multi-source error for {symbol}: {e}")
        # Klare Fehlermeldung statt simulierter Daten
        return {
            "error": str(e), 
            "source": "API Fehler",
            "symbol": symbol,
            "price": 0,
            "change": 0,
            "change_percent": 0,
            "is_live": False
        }


def refresh_all_markets(symbols_to_fetch, swiss_stocks, indices):
    """Aktualisiert alle Marktdaten mit erweiterten Symbolen"""
    # Wenn keine Symbole übergeben wurden, nichts tun
    if not symbols_to_fetch or len(symbols_to_fetch) == 0:
        logger.info("Keine Symbole zum Aktualisieren übergeben - überspringe Update")
        return {
            "success": True,
            "message": "No symbols provided, skipping update",
            "data": [],
            "last_update": datetime.now().strftime("%H:%M:%S")
        }
    
    # Beschränke die Anzahl der zu ladenden Symbole
    if len(symbols_to_fetch) > 10:
        logger.warning(f"Zu viele Symbole angefragt: {len(symbols_to_fetch)}. Limitiere auf 10.")
        # Erstelle eine Kopie der ersten 10 Elemente
        symbols_limited = {}
        for i, (name, symbol) in enumerate(symbols_to_fetch.items()):
            if i < 10:
                symbols_limited[name] = symbol
            else:
                break
        symbols_to_fetch = symbols_limited
    
    with data_lock:
        # Verhindern, dass mehrere Updates gleichzeitig laufen
        if cache['update_in_progress']['markets']:
            return {
                "success": False,
                "message": "Update already in progress",
                "data": cache['live_market_data'].get('data', []),
                "last_update": cache['last_market_update'].strftime("%H:%M:%S") if cache['last_market_update'] else "N/A",
            }
        
        cache['update_in_progress']['markets'] = True
    
    try:
        result = []
        
        # Logge, welche Symbole aktualisiert werden
        logger.info(f"Aktualisiere folgende Symbole: {', '.join(symbols_to_fetch.keys())}")
        
        for name, symbol in symbols_to_fetch.items():
            try:
                # Die bestehende get_live_data Funktion verwenden
                response = get_live_data(symbol, swiss_stocks, indices)
                response['display_name'] = name
                result.append(response)
                # Kurze Pause, um API-Limits zu respektieren
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren von {name}: {e}")
                result.append({
                    "symbol": symbol,
                    "display_name": name,
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "error": str(e),
                    "source": "⚠️ Fehler",
                    "is_live": False
                })
        
        with data_lock:
            cache['live_market_data'] = {
                "data": result,
                "success": True
            }
            cache['last_market_update'] = datetime.now()
            cache['update_in_progress']['markets'] = False
            
            return {
                "success": True,
                "data": result,
                "last_update": cache['last_market_update'].strftime("%H:%M:%S"),
            }
    except Exception as e:
        with data_lock:
            cache['update_in_progress']['markets'] = False
        return {
            "success": False,
            "error": str(e),
            "last_update": cache['last_market_update'].strftime("%H:%M:%S") if cache['last_market_update'] else "N/A",
        }


def update_bank_portfolios():
    """Aktualisiert die Performance-Daten der Bank-Portfolios mit echten Daten"""
    global SWISS_BANK_PORTFOLIOS
    
    with data_lock:
        if cache['update_in_progress']['portfolios']:
            return {
                "success": False,
                "message": "Update already in progress",
                "portfolios": SWISS_BANK_PORTFOLIOS
            }
        
        cache['update_in_progress']['portfolios'] = True
    
    try:
        updated_portfolios = {}
        
        for name, portfolio in SWISS_BANK_PORTFOLIOS.items():
            try:
                ticker = portfolio.get('ticker')
                if ticker:
                    # Yahoo Finance API verwenden, um aktuelle Daten zu holen
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="3y")
                    
                    if not hist.empty and len(hist) > 252:  # Mindestens 1 Jahr Daten (252 Handelstage)
                        # Jahresrendite berechnen
                        returns = hist['Close'].pct_change().dropna()
                        annual_return = returns.mean() * 252 * 100  # Annualisierte Rendite in %
                        annual_risk = returns.std() * np.sqrt(252) * 100  # Annualisierte Volatilität in %
                        
                        if annual_risk > 0:
                            sharpe_ratio = round(annual_return / annual_risk, 2)
                        else:
                            sharpe_ratio = 0
                        
                        updated_portfolios[name] = {
                            "return": round(annual_return, 1),
                            "risk": round(annual_risk, 1),
                            "sharpe": sharpe_ratio,
                            "source": "🔴 LIVE (Yahoo Finance)",
                            "ticker": ticker
                        }
                        continue
            except Exception as e:
                print(f"Error updating portfolio {name}: {e}")
            
            # Bei Fehler die bestehenden Daten beibehalten
            updated_portfolios[name] = portfolio
        
        with data_lock:
            # Globale Variable aktualisieren
            SWISS_BANK_PORTFOLIOS = updated_portfolios
            cache['update_in_progress']['portfolios'] = False
            
            return {
                "success": True,
                "portfolios": SWISS_BANK_PORTFOLIOS
            }
    except Exception as e:
        with data_lock:
            cache['update_in_progress']['portfolios'] = False
        return {
            "success": False,
            "error": str(e)
        }


def update_market_cycles():
    """Aktualisiert die Marktzyklen mit echten ETF-Daten"""
    global MARKET_CYCLES
    
    with data_lock:
        if cache['update_in_progress']['cycles']:
            return {
                "success": False,
                "message": "Update already in progress",
                "cycles": MARKET_CYCLES
            }
        
        cache['update_in_progress']['cycles'] = True
    
    try:
        updated_cycles = {}
        
        for sector, data in MARKET_CYCLES.items():
            try:
                etf_symbol = data.get('etf')
                if etf_symbol:
                    # Yahoo Finance API verwenden, um aktuelle ETF-Daten zu holen
                    ticker = yf.Ticker(etf_symbol)
                    hist = ticker.history(period="1y")
                    
                    if not hist.empty:
                        # 1-Jahres-Performance berechnen
                        start_price = hist['Close'].iloc[0]
                        end_price = hist['Close'].iloc[-1]
                        return_1y = ((end_price - start_price) / start_price) * 100
                        
                        # Trend basierend auf Performance bestimmen
                        if return_1y > 15:
                            trend = "↗️↗️"  # Stark steigend
                        elif return_1y > 5:
                            trend = "↗️"  # Steigend
                        elif return_1y > -5:
                            trend = "➡️"  # Neutral
                        elif return_1y > -15:
                            trend = "↘️"  # Fallend
                        else:
                            trend = "↘️↘️"  # Stark fallend
                        
                        # Phasen und Rating basierend auf Performance bestimmen
                        if return_1y > 20:
                            phase = "Früh"
                            rating = "Hoch"
                        elif return_1y > 10:
                            phase = "Mitte"
                            rating = "Hoch"
                        elif return_1y > 0:
                            phase = "Mitte"
                            rating = "Mittel"
                        elif return_1y > -10:
                            phase = "Spät"
                            rating = "Niedrig"
                        else:
                            phase = "Ende"
                            rating = "Niedrig"
                        
                        updated_cycles[sector] = {
                            "cycle": data.get('cycle'),  # Sektortyp beibehalten
                            "phase": phase,
                            "rating": rating,
                            "trend": trend,
                            "etf": etf_symbol,
                            "return_1y": round(return_1y, 1),
                            "source": "🔴 LIVE (ETF Performance)"
                        }
                        continue
            except Exception as e:
                print(f"Error updating market cycle for {sector}: {e}")
            
            # Bei Fehler die bestehenden Daten beibehalten
            updated_cycles[sector] = data
        
        with data_lock:
            # Globale Variable aktualisieren
            MARKET_CYCLES = updated_cycles
            cache['update_in_progress']['cycles'] = False
            
            return {
                "success": True,
                "cycles": MARKET_CYCLES
            }
    except Exception as e:
        with data_lock:
            cache['update_in_progress']['cycles'] = False
        return {
            "success": False,
            "error": str(e)
        }


def get_news():
    """Echte Schweizer Finanznachrichten von RSS Feeds"""
    with data_lock:
        if cache['update_in_progress']['news']:
            return cache['news_data'] if cache['news_data'] else []
        
        cache['update_in_progress']['news'] = True
    
    try:
        # Schweizer Finanznews RSS Feeds - erweitert mit internationalen Quellen
        feeds = [
            # Schweizer Quellen
            "https://www.fuw.ch/feed/",
            "https://www.handelszeitung.ch/feed",
            "https://www.nzz.ch/finanzen.rss",
            "https://www.cash.ch/rss/news/alle-news",
            # Internationale Quellen als Backup
            "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # Finance News
            "https://www.ft.com/markets?format=rss",                # Financial Times Markets
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^SSMI&region=US&lang=en-US"  # Yahoo Finance SMI News
        ]
        
        news_items = []
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed_url.split('/')[2].replace('www.', '').split('.')[0].capitalize()
                
                for entry in feed.entries[:3]:  # 3 News pro Feed
                    # Datum formatieren
                    try:
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                            now = datetime.now()
                            delta = now - dt
                            
                            if delta.days == 0:
                                if delta.seconds < 3600:
                                    time_str = f"Vor {delta.seconds // 60} Min."
                                else:
                                    time_str = f"Vor {delta.seconds // 3600} Std."
                            elif delta.days == 1:
                                time_str = "Gestern"
                            else:
                                time_str = f"Vor {delta.days} Tagen"
                        else:
                            time_str = "Kürzlich"
                    except:
                        time_str = "Kürzlich"
                    
                    # Content extrahieren und säubern
                    content = entry.summary if hasattr(entry, 'summary') else ""
                    # HTML-Tags entfernen
                    content = re.sub('<[^<]+?>', '', content)
                    # Auf 200 Zeichen kürzen
                    content = content[:200] + "..." if len(content) > 200 else content
                    
                    news_items.append({
                        "title": entry.title,
                        "content": content,
                        "time": time_str,
                        "source": source_name,
                        "link": entry.link,
                        "is_live": True
                    })
            except Exception as e:
                print(f"Error fetching feed {feed_url}: {e}")
                continue
        
        with data_lock:
            # Cache updaten
            cache['news_data'] = news_items[:8]  # Auf 8 News begrenzen
            cache['last_news_update'] = datetime.now()
            cache['update_in_progress']['news'] = False
            
            return cache['news_data']
    except Exception as e:
        with data_lock:
            cache['update_in_progress']['news'] = False
        print(f"News error: {e}")
        return []


def is_data_fresh(data_type: str) -> bool:
    """
    Prüft, ob die Daten noch frisch genug für die Verwendung sind
    
    :param data_type: Art der Daten ('market_data', 'portfolios', 'news', etc.)
    :return: True, wenn die Daten frisch sind, sonst False
    """
    last_update_key = f"last_{data_type}_update"
    if last_update_key not in cache or cache[last_update_key] is None:
        return False
        
    last_update = cache[last_update_key]
    max_age = MAX_DATA_AGE.get(data_type, 900)  # Standard: 15 Minuten
    
    # Aktuelle Zeit
    now = datetime.now()
    
    # Zeitunterschied in Sekunden
    age = (now - last_update).total_seconds()
    
    return age < max_age

def safe_get_with_retry(url: str, params: dict = None, headers: dict = None, 
                       max_retries: int = MAX_RETRIES) -> dict:
    """
    Führt eine GET-Anfrage mit Retry-Mechanismus durch
    
    :param url: URL für die Anfrage
    :param params: URL-Parameter (optional)
    :param headers: HTTP-Header (optional)
    :param max_retries: Maximale Anzahl von Wiederholungsversuchen
    :return: JSON-Antwort oder leeres Dict bei Fehler
    """
    attempt = 0
    
    while attempt <= max_retries:
        try:
            api_logger.info(f"API request: GET {url}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()  # Fehler bei HTTP-Statuscode >= 400
            return response.json()
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                api_logger.error(f"Failed API request after {max_retries} attempts: {url} - {str(e)}")
                return {}
                
            # Exponentielles Backoff mit Jitter
            retry_delay = RETRY_BACKOFF[min(attempt-1, len(RETRY_BACKOFF)-1)]
            jitter = random.uniform(0, 2)
            wait_time = retry_delay + jitter
            
            api_logger.warning(f"Retry {attempt}/{max_retries} in {wait_time:.2f}s: {url} - {str(e)}")
            time.sleep(wait_time)
    
    # Sollte nie erreicht werden, aber sicherheitshalber
    return {}

def get_benchmark_data():
    """
    Holt Benchmark-Daten aus mehreren Quellen mit Fehlerbehandlung und Timeout-Management
    
    :return: Dict mit Benchmark-Daten, Quellen und Status
    """
    # Thread-sicheres Prüfen und Setzen des Update-Status
    with data_lock:
        # Wenn bereits frische Daten im Cache sind, diese verwenden
        if 'benchmarks' in cache and is_data_fresh('benchmarks'):
            return cache['benchmark_data']
            
        if cache['update_in_progress']['benchmarks']:
            # Update läuft bereits - ältere Daten zurückgeben falls vorhanden
            if cache['benchmark_data']:
                return cache['benchmark_data']
            return {
                "success": False,
                "message": "Update in progress, no cached data available",
                "data": {},
                "sources": {},
                "is_live": False
            }
            
        # Update-Status setzen
        cache['update_in_progress']['benchmarks'] = True
    
    try:
        logger.info("Hole Benchmark-Daten...")
        benchmarks = {}
        benchmark_sources = {}
        
        # Erweiterte Benchmark-Symbole
        benchmark_symbols = {
            "SMI": "^SSMI",
            "S&P 500": "^GSPC", 
            "MSCI World": "URTH",
            "Bloomberg Bond": "BND",
            "Gold": "GC=F",
            "Silber": "SI=F",
            "Bitcoin": "BTC-USD",
            "Ethereum": "ETH-USD"
        }
        
        # Für Parallelverarbeitung
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for name, symbol in benchmark_symbols.items():
                futures[executor.submit(fetch_benchmark_for_symbol, name, symbol)] = name
                
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result(timeout=15)
                    if result and 'value' in result:
                        benchmarks[name] = result['value']
                        benchmark_sources[name] = result['source']
                    else:
                        benchmarks[name] = 0
                        benchmark_sources[name] = "⚠️ Daten nicht verfügbar"
                        # Fehler zählen
                        with data_lock:
                            cache['update_error_count']['benchmarks'] += 1
                except TimeoutError:
                    benchmarks[name] = 0
                    benchmark_sources[name] = "⚠️ Timeout bei Datenabfrage"
                    logger.warning(f"Timeout bei Benchmark-Daten für {name}")
                    with data_lock:
                        cache['update_error_count']['benchmarks'] += 1
                except Exception as e:
                    benchmarks[name] = 0
                    benchmark_sources[name] = f"⚠️ Fehler: {str(e)[:30]}"
                    logger.error(f"Fehler bei Benchmark-Daten für {name}: {e}")
                    with data_lock:
                        cache['update_error_count']['benchmarks'] += 1
        
        # Ergebnis vorbereiten
        result = {
            "success": len(benchmarks) > 0,
            "data": benchmarks,
            "sources": benchmark_sources,
            "is_live": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Thread-sicher Cache aktualisieren
        with data_lock:
            cache['benchmark_data'] = result
            cache['last_benchmark_update'] = datetime.now()
            cache['update_in_progress']['benchmarks'] = False
            cache['update_success_count']['benchmarks'] += 1
            
        logger.info(f"Benchmark-Daten erfolgreich aktualisiert: {len(benchmarks)} Werte")
        return result
        
    except Exception as e:
        logger.error(f"Globaler Fehler bei Benchmark-Update: {str(e)}", exc_info=True)
        with data_lock:
            cache['update_in_progress']['benchmarks'] = False
            cache['update_error_count']['benchmarks'] += 1
            
        # Fallback: Vorhandene Daten zurückgeben oder leeres Ergebnis
        if cache['benchmark_data']:
            cache['benchmark_data']['success'] = False
            cache['benchmark_data']['error'] = str(e)
            return cache['benchmark_data']
        
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "sources": {},
            "is_live": False
        }

def fetch_benchmark_for_symbol(name: str, symbol: str) -> Dict[str, Any]:
    """
    Holt Benchmark-Daten für ein einzelnes Symbol mit Fehlerbehandlung
    
    :param name: Name des Benchmarks
    :param symbol: Yahoo Finance Symbol
    :return: Dict mit Wert und Quelle oder leeres Dict bei Fehler
    """
    api_logger.info(f"Fetching benchmark data for {name} ({symbol})")
    try:
        # Versuch 1: Yahoo Finance
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: yf.Ticker(symbol).history(period="1y"))
            hist = future.result(timeout=10)
        
        if not hist.empty:
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return_1y = ((end_price - start_price) / start_price) * 100
            return {
                "value": round(return_1y, 2),
                "source": "Yahoo Finance"
            }
        
        # Versuch 2: Alpha Vantage als Backup
        try:
            api_logger.info(f"Yahoo Finance failed for {symbol}, trying Alpha Vantage")
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_MONTHLY", 
                "symbol": symbol, 
                "apikey": AV_API_KEY
            }
            
            data = safe_get_with_retry(url, params=params)
            
            if "Monthly Time Series" in data:
                time_series = data["Monthly Time Series"]
                dates = sorted(time_series.keys())
                if len(dates) >= 12:
                    start_date = dates[-12]  # Vor einem Jahr
                    end_date = dates[0]      # Neuester Datenpunkt
                    start_price = float(time_series[start_date]["4. close"])
                    end_price = float(time_series[end_date]["4. close"])
                    return_1y = ((end_price - start_price) / start_price) * 100
                    return {
                        "value": round(return_1y, 2),
                        "source": "Alpha Vantage"
                    }
        except Exception as e:
            api_logger.error(f"Alpha Vantage error for {symbol}: {str(e)}")
        
        # Wenn keine Daten verfügbar sind
        return {}
            
    except TimeoutError:
        api_logger.error(f"Timeout bei Benchmark-Daten für {symbol}")
        return {}
    except Exception as e:
        api_logger.error(f"Error fetching benchmark {symbol}: {str(e)}")
        return {}