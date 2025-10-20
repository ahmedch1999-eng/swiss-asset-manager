"""
Daten-Aktualisierungs-Scheduler
Optimiert mit verbessertem Error-Handling und adaptiver Parallelisierung
Angepasst für den neuen Scheduler-Process-Manager

Diese Version ist kompatibel mit dem separaten Prozess-Management-System.
"""

import threading
import time
import schedule
import random
import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging
import functools
import signal
import json
import os
import requests
import yfinance as yf
import gc
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed, ProcessPoolExecutor
from collections import deque

# Setup logging
logger = logging.getLogger("data_refresh_scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Import der direkten Datenfunktionen (cached version)
try:
    from data_services_cached import DataServices
    
    # For backward compatibility with existing code
    def refresh_all_markets(*args, **kwargs):
        symbols_dict = args[0] if args else kwargs.get('symbols_to_fetch', {})
        symbols = list(symbols_dict.keys()) if isinstance(symbols_dict, dict) else symbols_dict
        return DataServices.refresh_all_market_data(symbols)
    
    def update_bank_portfolios(*args, **kwargs):
        return DataServices.update_bank_portfolios()
    
    def update_market_cycles(*args, **kwargs):
        return DataServices.update_market_cycles()
    
    def get_news(*args, **kwargs):
        return DataServices.get_news()
    
    # Log that we're using the cached version
    logger.info("Using cached data services for better performance")
    
except ImportError:
    # Fallback to original data services if cached version isn't available
    from data_services import (
        refresh_all_markets,
        update_bank_portfolios,
        update_market_cycles,
        get_news
    )
    logger.warning("Falling back to standard data services (no caching)")

# Import cache integration
from scheduler_cache_integration import get_cache_manager, get_cache_stats

# Import der Konfiguration
from scheduler_config import SchedulerConfig

# Konfiguration für erweitertes Logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Hauptlogger für allgemeine Meldungen
logging.basicConfig(
    level=getattr(logging, SchedulerConfig.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'{log_dir}/data_refresh.log')
    ]
)
logger = logging.getLogger("data_refresh")

# Spezieller Logger für Metriken und Performance-Tracking
metrics_logger = logging.getLogger("metrics")
metrics_handler = logging.FileHandler(f'{log_dir}/metrics.log')
metrics_handler.setFormatter(logging.Formatter('%(asctime)s [METRIC] %(message)s'))
metrics_logger.addHandler(metrics_handler)
metrics_logger.setLevel(logging.INFO)
metrics_logger.propagate = False  # Verhindert Duplizierung im Haupt-Logger

# Metriken für das Performance-Tracking
class Metrics:
    """Klasse für das Sammeln und Loggen von Metriken"""
    
    def __init__(self):
        self.data = {
            'api_calls': 0,
            'api_errors': 0,
            'api_timeouts': 0,
            'api_retries': 0,
            'update_success': 0,
            'update_failure': 0,
            'components': {
                'markets': {'success': 0, 'failure': 0, 'last_success': None, 'avg_duration': 0, 'count': 0},
                'portfolios': {'success': 0, 'failure': 0, 'last_success': None, 'avg_duration': 0, 'count': 0},
                'cycles': {'success': 0, 'failure': 0, 'last_success': None, 'avg_duration': 0, 'count': 0},
                'news': {'success': 0, 'failure': 0, 'last_success': None, 'avg_duration': 0, 'count': 0},
            },
            'last_full_update': None,
            'health': 'unknown',
            'uptime_start': datetime.now(),
            'memory_usage': {},
            'parallel_efficiency': 0,
            'rate_limits': {
                'yahoo': {'calls_per_minute': 60, 'remaining': 60, 'reset_time': datetime.now()},
                'alphavantage': {'calls_per_minute': 5, 'remaining': 5, 'reset_time': datetime.now()}
            }
        }
        
        # Historie für adaptive Optimierung
        self.api_call_history = deque(maxlen=1000)  # Begrenzte Historie für Memory-Management
        
        # Periodisches Speichern der Metriken
        self.dump_timer = threading.Timer(60 * 15, self.periodic_dump)  # Alle 15 Minuten
        self.dump_timer.daemon = True
        self.dump_timer.start()
    
    def record_api_call(self, api_type="yahoo", success=True, timeout=False, retried=False, duration=0):
        """Zeichnet einen API-Aufruf auf mit erweitertem Rate-Limit-Tracking"""
        self.data['api_calls'] += 1
        if not success:
            self.data['api_errors'] += 1
        if timeout:
            self.data['api_timeouts'] += 1
        if retried:
            self.data['api_retries'] += 1
            
        # API-Call Historie für adaptive Rate Limiting
        now = datetime.now()
        self.api_call_history.append({
            'timestamp': now,
            'api_type': api_type,
            'success': success,
            'duration': duration
        })
        
        # Rate Limit aktualisieren
        if api_type in self.data['rate_limits']:
            rate_info = self.data['rate_limits'][api_type]
            
            # Rate Limit zurücksetzen, wenn Zeit abgelaufen
            if now > rate_info['reset_time']:
                if api_type == 'yahoo':
                    rate_info['remaining'] = rate_info['calls_per_minute']
                elif api_type == 'alphavantage':
                    rate_info['remaining'] = rate_info['calls_per_minute']
                rate_info['reset_time'] = now + timedelta(minutes=1)
            
            # Verbleibende Calls reduzieren
            rate_info['remaining'] = max(0, rate_info['remaining'] - 1)
    
    def record_update(self, component, success=True, duration=0):
        """Zeichnet ein Update für eine Komponente auf mit Performance-Metriken"""
        if success:
            self.data['update_success'] += 1
            self.data['components'][component]['success'] += 1
            self.data['components'][component]['last_success'] = datetime.now()
        else:
            self.data['update_failure'] += 1
            self.data['components'][component]['failure'] += 1
        
        # Performance-Tracking für adaptive Optimierung
        if duration > 0:
            comp_data = self.data['components'][component]
            # Gleitender Durchschnitt für Dauer
            if comp_data['count'] == 0:
                comp_data['avg_duration'] = duration
            else:
                # Gewichteter gleitender Durchschnitt (70% alt, 30% neu)
                comp_data['avg_duration'] = (comp_data['avg_duration'] * 0.7) + (duration * 0.3)
            comp_data['count'] += 1
            
        # Memory-Nutzung erfassen
        self.record_memory_usage()
        
        # Benachrichtige den Scheduler-Process-Manager
        try:
            if os.path.exists("scheduler_status.json"):
                with open("scheduler_status.json", "r") as f:
                    status = json.load(f)
                
                # Update Metriken basierend auf Erfolg
                metrics = {
                    "success": success,
                    "component": component,
                    "timestamp": datetime.now().isoformat(),
                    "duration": duration,
                    "error": None if success else "Update fehlgeschlagen"
                }
                
                # Import nur hier, um zirkuläre Imports zu vermeiden
                try:
                    from scheduler_manager import get_scheduler_manager
                    manager = get_scheduler_manager()
                    manager.update_metrics(metrics)
                except ImportError:
                    # Falls der Scheduler eigenständig läuft
                    pass
        except Exception as e:
            logger.warning(f"Konnte Process-Manager nicht über Update informieren: {e}")
    
    def record_full_update(self, success=True):
        """Zeichnet ein vollständiges Update auf"""
        self.data['last_full_update'] = datetime.now()
        self.data['health'] = 'healthy' if success else 'degraded'
    
    def record_memory_usage(self):
        """Erfasst die aktuelle Memory-Nutzung"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            self.data['memory_usage'] = {
                'rss': memory_info.rss / (1024 * 1024),  # MB
                'vms': memory_info.vms / (1024 * 1024),  # MB
                'timestamp': datetime.now()
            }
        except ImportError:
            # psutil nicht installiert, verwenden wir alternativen Ansatz
            gc.collect()  # Expliziter Garbage Collection vor Messung
            import sys
            self.data['memory_usage'] = {
                'python_objects': sum(sys.getsizeof(obj) for obj in gc.get_objects()) / (1024 * 1024),  # MB
                'timestamp': datetime.now()
            }
    
    def calculate_optimal_parallelism(self):
        """Berechnet den optimalen Parallelisierungsgrad basierend auf historischen Daten"""
        # Standard ist 4 Worker (1 pro Komponente)
        default_workers = 4
        
        # Wenn nicht genug Daten, Standard zurückgeben
        if len(self.api_call_history) < 50:
            return default_workers
        
        # Analyse der letzten API-Calls
        recent_calls = list(self.api_call_history)[-50:]
        avg_duration = sum(call['duration'] for call in recent_calls if call['duration'] > 0) / max(1, len(recent_calls))
        error_rate = sum(1 for call in recent_calls if not call['success']) / max(1, len(recent_calls))
        
        # Bei hoher Fehlerrate reduzieren wir den Parallelismus
        if error_rate > 0.2:  # Mehr als 20% Fehler
            return max(1, default_workers - 2)
        elif error_rate > 0.1:  # Mehr als 10% Fehler
            return max(2, default_workers - 1)
        
        # Bei schnellen Antworten erhöhen wir den Parallelismus
        if avg_duration < 1.0:  # Unter 1 Sekunde
            return min(8, default_workers + 2)
        elif avg_duration < 2.0:  # Unter 2 Sekunden
            return min(6, default_workers + 1)
        
        return default_workers
    
    def get_optimal_rate_limits(self):
        """Berechnet optimale API-Rate-Limits basierend auf API-Antworten"""
        limits = {}
        for api_type, rate_info in self.data['rate_limits'].items():
            # Übertragen der konfigurierten Werte
            limits[api_type] = {
                'calls_per_minute': rate_info['calls_per_minute'],
                'wait_time': 60.0 / max(1, rate_info['calls_per_minute']),  # Sekunden zwischen Calls
                'remaining': rate_info['remaining'],
                'reset_in_seconds': max(0, (rate_info['reset_time'] - datetime.now()).total_seconds())
            }
        return limits
    
    def record_parallel_efficiency(self, sequential_time, parallel_time):
        """Zeichnet die Effizienz der Parallelisierung auf"""
        if sequential_time > 0 and parallel_time > 0:
            # Theoretische Verbesserung vs. tatsächliche Verbesserung
            efficiency = (sequential_time / parallel_time) / 4  # 4 Komponenten
            self.data['parallel_efficiency'] = round(min(efficiency, 1.0) * 100, 2)  # In Prozent
    
    def get_stats(self):
        """Gibt erweiterte Statistiken zurück"""
        uptime = datetime.now() - self.data['uptime_start']
        uptime_hours = round(uptime.total_seconds() / 3600, 1)
        
        stats = {
            'uptime_hours': uptime_hours,
            'api_calls': self.data['api_calls'],
            'api_errors': self.data['api_errors'],
            'api_timeouts': self.data['api_timeouts'],
            'api_error_rate': round((self.data['api_errors'] / max(1, self.data['api_calls'])) * 100, 2),
            'update_success_rate': round((self.data['update_success'] / max(1, (self.data['update_success'] + self.data['update_failure']))) * 100, 2),
            'health': self.data['health'],
            'parallel_efficiency': self.data['parallel_efficiency'],
            'memory': self.data['memory_usage'],
            'components': {},
            'rate_limits': {k: {'calls_per_min': v['calls_per_minute'], 'remaining': v['remaining']} 
                           for k, v in self.data['rate_limits'].items()}
        }
        
        # Komponentenstatus berechnen
        for comp, data in self.data['components'].items():
            total = data['success'] + data['failure']
            success_rate = round((data['success'] / max(1, total)) * 100, 2)
            last_success_ago = 'never'
            if data['last_success']:
                delta = datetime.now() - data['last_success']
                last_success_ago = f"{delta.total_seconds() // 60:.0f} minutes ago"
            
            stats['components'][comp] = {
                'success_rate': success_rate,
                'last_success': last_success_ago,
                'avg_duration': round(data['avg_duration'], 2) if data['avg_duration'] > 0 else 0
            }
        
        return stats
    
    def log_stats(self):
        """Protokolliert aktuelle Statistiken"""
        stats = self.get_stats()
        metrics_logger.info(f"STATS: {json.dumps(stats)}")
        
        # Detaillierte Komponentenstatistiken
        for comp, data in stats['components'].items():
            metrics_logger.info(f"COMPONENT {comp}: Success rate {data['success_rate']}%, Last success {data['last_success']}")
    
    def periodic_dump(self):
        """Regelmäßiges Speichern der Metriken"""
        try:
            self.log_stats()
        finally:
            # Neuen Timer starten (selbst-erhaltend)
            self.dump_timer = threading.Timer(60 * 15, self.periodic_dump)  # Alle 15 Minuten
            self.dump_timer.daemon = True
            self.dump_timer.start()

# Globale Metrik-Instanz erstellen
metrics = Metrics()

# Decorator für API-Aufrufe mit Exponential Backoff und Timeout
def with_retry_and_timeout(max_retries=3, base_delay=1, max_delay=30, timeout=10, api_type="yahoo"):
    """
    Decorator für Funktionen, die Netzwerkanfragen ausführen.
    Implementiert exponential backoff, Timeouts und Rate Limiting.
    
    :param max_retries: Maximale Anzahl von Wiederholungsversuchen
    :param base_delay: Basisverzögerung in Sekunden
    :param max_delay: Maximale Verzögerung in Sekunden
    :param timeout: Timeout für jeden Versuch in Sekunden
    :param api_type: API-Typ für Rate-Limiting ('yahoo' oder 'alphavantage')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Rate Limit prüfen und warten wenn nötig
            rate_limits = metrics.get_optimal_rate_limits()
            if api_type in rate_limits:
                rate_info = rate_limits[api_type]
                if rate_info['remaining'] <= 0:
                    # Warten bis zum Reset des Rate Limits
                    wait_time = rate_info['reset_in_seconds']
                    if wait_time > 0:
                        logger.info(f"Rate-Limit für {api_type} erreicht, warte {wait_time:.1f}s")
                        time.sleep(wait_time)
            
            retries = 0
            start_time = time.time()
            
            while True:
                try:
                    # Funktion mit Timeout ausführen
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(func, *args, **kwargs)
                        try:
                            result = future.result(timeout=timeout)
                            call_duration = time.time() - start_time
                            metrics.record_api_call(api_type=api_type, success=True, 
                                                 retried=(retries > 0), duration=call_duration)
                            return result
                        except TimeoutError:
                            future.cancel()
                            call_duration = time.time() - start_time
                            metrics.record_api_call(api_type=api_type, success=False, 
                                                 timeout=True, retried=(retries > 0), 
                                                 duration=call_duration)
                            logger.warning(f"Timeout bei {func.__name__} nach {timeout} Sekunden")
                            raise TimeoutError(f"Funktion {func.__name__} hat das Timeout von {timeout}s überschritten")
                except (TimeoutError, Exception) as e:
                    call_duration = time.time() - start_time
                    metrics.record_api_call(api_type=api_type, success=False, 
                                         timeout=isinstance(e, TimeoutError), 
                                         retried=(retries > 0), 
                                         duration=call_duration)
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Maximale Anzahl von Wiederholungsversuchen ({max_retries}) für {func.__name__} erreicht: {str(e)}")
                        raise
                    
                    # Exponential Backoff mit Jitter
                    delay = min(base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), max_delay)
                    logger.warning(f"Wiederhole {func.__name__} in {delay:.2f}s (Versuch {retries}/{max_retries}) nach Fehler: {str(e)}")
                    time.sleep(delay)
        return wrapper
    return decorator

# Decorator für Async/Await Pattern mit Retry und Timeout
def async_with_retry(max_retries=3, base_delay=1, max_delay=30, timeout=10, api_type="yahoo"):
    """
    Decorator für asynchrone Funktionen mit Retry-Logik und Timeout.
    Für nicht-blockierende API-Aufrufe.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Rate Limit prüfen und warten wenn nötig
            rate_limits = metrics.get_optimal_rate_limits()
            if api_type in rate_limits:
                rate_info = rate_limits[api_type]
                if rate_info['remaining'] <= 0:
                    # Warten bis zum Reset des Rate Limits
                    wait_time = rate_info['reset_in_seconds']
                    if wait_time > 0:
                        logger.info(f"Rate-Limit für {api_type} erreicht, warte {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
            
            retries = 0
            start_time = time.time()
            
            while True:
                try:
                    # Funktion mit Timeout ausführen
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    call_duration = time.time() - start_time
                    metrics.record_api_call(api_type=api_type, success=True, 
                                         retried=(retries > 0), duration=call_duration)
                    return result
                except asyncio.TimeoutError:
                    call_duration = time.time() - start_time
                    metrics.record_api_call(api_type=api_type, success=False, 
                                         timeout=True, retried=(retries > 0), 
                                         duration=call_duration)
                    logger.warning(f"Async-Timeout bei {func.__name__} nach {timeout} Sekunden")
                    if retries >= max_retries:
                        raise TimeoutError(f"Async-Funktion {func.__name__} hat das Timeout von {timeout}s überschritten")
                except Exception as e:
                    call_duration = time.time() - start_time
                    metrics.record_api_call(api_type=api_type, success=False, 
                                         retried=(retries > 0), duration=call_duration)
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Maximale Anzahl von Wiederholungsversuchen ({max_retries}) für async {func.__name__} erreicht: {str(e)}")
                        raise
                    
                    # Exponential Backoff mit Jitter
                    delay = min(base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), max_delay)
                    logger.warning(f"Wiederhole async {func.__name__} in {delay:.2f}s (Versuch {retries}/{max_retries}) nach Fehler: {str(e)}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

# Decorator für Component-Updates mit Fehlerbehandlung
def component_update(component_name):
    """
    Decorator für Komponenten-Update-Funktionen.
    Zeichnet Erfolg/Misserfolg auf und verhindert, dass Fehler andere Updates beeinträchtigen.
    
    :param component_name: Name der Komponente (markets, portfolios, etc.)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_update(component_name, success=True, duration=duration)
                metrics_logger.info(f"UPDATE {component_name}: SUCCESS in {duration:.2f}s")
                
                # Expliziter Garbage Collection nach großen Datenupdates
                if component_name in ['markets', 'portfolios']:
                    gc.collect()
                    
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_update(component_name, success=False, duration=duration)
                logger.error(f"Fehler bei Update von {component_name} nach {duration:.2f}s: {str(e)}", exc_info=True)
                metrics_logger.info(f"UPDATE {component_name}: FAILURE in {duration:.2f}s - {str(e)}")
                return {"success": False, "error": str(e), "component": component_name}
        return wrapper
    return decorator

# Decorator für asynchrone Component-Updates
def async_component_update(component_name):
    """
    Decorator für asynchrone Komponenten-Update-Funktionen.
    Ermöglicht nicht-blockierende parallele Updates.
    
    :param component_name: Name der Komponente (markets, portfolios, etc.)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_update(component_name, success=True, duration=duration)
                metrics_logger.info(f"ASYNC UPDATE {component_name}: SUCCESS in {duration:.2f}s")
                
                # Expliziter Garbage Collection nach großen Datenupdates
                if component_name in ['markets', 'portfolios']:
                    gc.collect()
                    
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_update(component_name, success=False, duration=duration)
                logger.error(f"Fehler bei async Update von {component_name} nach {duration:.2f}s: {str(e)}", exc_info=True)
                metrics_logger.info(f"ASYNC UPDATE {component_name}: FAILURE in {duration:.2f}s - {str(e)}")
                return {"success": False, "error": str(e), "component": component_name}
        return wrapper
    return decorator

# Symbole für die Marktdaten - gleich wie in app.py
symbols_to_fetch = {
    # Schweizer Indizes
    'SMI': '^SSMI', 'Swiss Leader': '^SLI', 'Swiss Performance': '^SPI',
    
    # Globale Hauptindizes
    'DAX': '^GDAXI', 'S&P 500': '^GSPC', 'NASDAQ': '^IXIC',
    'FTSE 100': '^FTSE', 'CAC 40': '^FCHI', 'Nikkei 225': '^N225',
    'Hang Seng': '^HSI', 'Shanghai': '000001.SS',
    
    # Rohstoffe
    'Gold': 'GC=F', 'Silber': 'SI=F', 'Öl': 'CL=F', 
    'Platin': 'PL=F', 'Kupfer': 'HG=F', 'Erdgas': 'NG=F',
    
    # Währungen
    'EUR/CHF': 'EURCHF=X', 'USD/CHF': 'USDCHF=X', 'GBP/CHF': 'GBPCHF=X',
    'JPY/CHF': 'JPYCHF=X', 'EUR/USD': 'EURUSD=X',
    
    # Kryptowährungen
    'Bitcoin': 'BTC-USD', 'Ethereum': 'ETH-USD', 'Solana': 'SOL-USD'
}

# Listen für Symbol-Korrektur
swiss_stocks = {}  # Diese werden in der initialize_data Funktion gefüllt
indices = {}       # Diese werden in der initialize_data Funktion gefüllt

def initialize_reference_data(swiss_stocks_data, indices_data):
    """Initialisiert die Referenzdaten für Symbol-Korrektur"""
    global swiss_stocks, indices
    
    swiss_stocks = swiss_stocks_data
    indices = indices_data
    
    logger.info("Referenzdaten für Symbol-Korrektur initialisiert")

def check_api_health():
    """Überprüft die Gesundheit der APIs vor Updates"""
    health = {
        'yahoo_finance': False,
        'alpha_vantage': False,
        'internet_connection': False
    }
    
    try:
        # Einfache Internetverbindung prüfen
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        health['internet_connection'] = True
    except Exception as e:
        logger.warning(f"Internetverbindung scheint unterbrochen: {e}")
        return health
    
    # Yahoo Finance API prüfen
    try:
        test_symbol = "^GSPC"  # S&P 500 als Test
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: yf.Ticker(test_symbol).info)
            result = future.result(timeout=10)
        if result:
            health['yahoo_finance'] = True
    except Exception as e:
        logger.warning(f"Yahoo Finance API nicht erreichbar: {e}")
    
    # Alpha Vantage API prüfen
    try:
        import requests
        API_KEY = "demo"
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={API_KEY}"
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: requests.get(url, timeout=10).json())
            result = future.result(timeout=10)
        if result and "Time Series" in str(result):
            health['alpha_vantage'] = True
    except Exception as e:
        logger.warning(f"Alpha Vantage API nicht erreichbar: {e}")
    
    return health

# Synchrone Update-Funktionen für Kompatibilität
@component_update('markets')
def update_markets():
    """Aktualisiert die Marktdaten"""
    return refresh_all_markets(symbols_to_fetch, swiss_stocks, indices)

@component_update('portfolios')
def update_portfolios():
    """Aktualisiert die Bank-Portfolios"""
    return update_bank_portfolios()

@component_update('cycles')
def update_market_cycles_wrapper():
    """Aktualisiert die Marktzyklen"""
    return update_market_cycles()

@component_update('news')
def update_news():
    """Aktualisiert die Nachrichten"""
    news_data = get_news()
    return {
        "success": bool(news_data),
        "count": len(news_data) if news_data else 0,
        "data": news_data
    }

# Asynchrone Versionen der Update-Funktionen für parallele Verarbeitung
@async_component_update('markets')
async def async_update_markets():
    """Aktualisiert die Marktdaten asynchron"""
    # Führt die Funktion im Thread-Pool aus, um blockierende Operationen zu umgehen
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: refresh_all_markets(symbols_to_fetch, swiss_stocks, indices)
    )

@async_component_update('portfolios')
async def async_update_portfolios():
    """Aktualisiert die Bank-Portfolios asynchron"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, update_bank_portfolios)

@async_component_update('cycles')
async def async_update_market_cycles():
    """Aktualisiert die Marktzyklen asynchron"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, update_market_cycles)

@async_component_update('news')
async def async_update_news():
    """Aktualisiert die Nachrichten asynchron"""
    loop = asyncio.get_running_loop()
    news_data = await loop.run_in_executor(None, get_news)
    return {
        "success": bool(news_data),
        "count": len(news_data) if news_data else 0,
        "data": news_data
    }

def update_all_real_data():
    """
    Aktualisiert alle Live-Datenquellen direkt ohne HTTP-Requests (sequenziell)
    Mit verbessertem Error-Handling und separaten Komponenten
    """
    start_time = time.time()
    logger.info("════════ STARTE SEQUENTIELLE DATENAKTUALISIERUNG ════════")
    
    # Gesundheitscheck vor der Aktualisierung
    api_health = check_api_health()
    
    if not api_health['internet_connection']:
        logger.error("❌ Keine Internetverbindung. Aktualisierung wird übersprungen.")
        metrics.record_full_update(success=False)
        metrics_logger.info(f"UPDATE ALL: ABORTED - No internet connection")
        return False
    
    if not (api_health['yahoo_finance'] or api_health['alpha_vantage']):
        logger.error("❌ Keine API erreichbar. Aktualisierung wird übersprungen.")
        metrics.record_full_update(success=False)
        metrics_logger.info(f"UPDATE ALL: ABORTED - No APIs available")
        return False
    
    # Warnungen ausgeben, wenn eine API nicht verfügbar ist
    if not api_health['yahoo_finance']:
        logger.warning("⚠️ Yahoo Finance API nicht erreichbar. Versuche Alpha Vantage.")
    if not api_health['alpha_vantage']:
        logger.warning("⚠️ Alpha Vantage API nicht erreichbar. Versuche Yahoo Finance.")
    
    # Array für Ergebnisse und Gesundheitszustand
    results = []
    overall_success = True
    
    # Komponenten aktualisieren - jede Komponente unabhängig von anderen
    # 1. Marktdaten aktualisieren
    result_markets = update_markets()
    results.append(result_markets)
    if not result_markets.get("success", False):
        overall_success = False
    
    # Adaptive Pause basierend auf API-Gesundheit
    pause_time = 8 if not api_health['yahoo_finance'] or not api_health['alpha_vantage'] else 3
    logger.debug(f"Pausiere für {pause_time}s, um API-Limits zu respektieren...")
    time.sleep(pause_time)
    
    # 2. Bankportfolios aktualisieren
    result_portfolios = update_portfolios()
    results.append(result_portfolios)
    if not result_portfolios.get("success", False):
        overall_success = False
    
    time.sleep(pause_time)
    
    # 3. Marktzyklen aktualisieren
    result_cycles = update_market_cycles_wrapper()
    results.append(result_cycles)
    if not result_cycles.get("success", False):
        overall_success = False
    
    time.sleep(pause_time)
    
    # 4. Nachrichten aktualisieren
    result_news = update_news()
    results.append(result_news)
    if not result_news.get("success", False):
        overall_success = False
    
    # Gesamtstatus protokollieren
    duration = time.time() - start_time
    metrics.record_full_update(success=overall_success)
    
    if overall_success:
        logger.info(f"✅ Alle Daten aktualisiert in {duration:.2f}s")
    else:
        successful_components = sum(1 for r in results if r.get("success", False))
        logger.warning(f"⚠️ Nur {successful_components}/4 Komponenten erfolgreich aktualisiert in {duration:.2f}s")
    
    # Metriken protokollieren
    metrics_logger.info(f"UPDATE ALL: {'SUCCESS' if overall_success else 'PARTIAL'} in {duration:.2f}s")
    metrics.log_stats()
    
    return overall_success, duration

# Event loop für asyncio
def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

async def update_all_real_data_parallel():
    """
    Aktualisiert alle Live-Datenquellen parallel mit asyncio
    Deutlich bessere Performance durch Parallelisierung unabhängiger Tasks
    """
    start_time = time.time()
    logger.info("════════ STARTE PARALLELE DATENAKTUALISIERUNG ════════")
    
    # Gesundheitscheck vor der Aktualisierung
    api_health = check_api_health()
    
    if not api_health['internet_connection']:
        logger.error("❌ Keine Internetverbindung. Aktualisierung wird übersprungen.")
        metrics.record_full_update(success=False)
        metrics_logger.info(f"UPDATE ALL PARALLEL: ABORTED - No internet connection")
        return False
    
    if not (api_health['yahoo_finance'] or api_health['alpha_vantage']):
        logger.error("❌ Keine API erreichbar. Aktualisierung wird übersprungen.")
        metrics.record_full_update(success=False)
        metrics_logger.info(f"UPDATE ALL PARALLEL: ABORTED - No APIs available")
        return False
    
    # Warnungen ausgeben, wenn eine API nicht verfügbar ist
    if not api_health['yahoo_finance']:
        logger.warning("⚠️ Yahoo Finance API nicht erreichbar. Versuche Alpha Vantage.")
    if not api_health['alpha_vantage']:
        logger.warning("⚠️ Alpha Vantage API nicht erreichbar. Versuche Yahoo Finance.")
    
    # Optimalen Parallelisierungsgrad berechnen
    max_workers = metrics.calculate_optimal_parallelism()
    logger.info(f"Verwende optimalen Parallelisierungsgrad: {max_workers} Worker")
    
    # Parallele Ausführung aller Updates
    try:
        # Alle Updates parallel starten
        tasks = [
            asyncio.create_task(async_update_markets()),
            asyncio.create_task(async_update_portfolios()),
            asyncio.create_task(async_update_market_cycles()),
            asyncio.create_task(async_update_news())
        ]
        
        # Warten bis alle abgeschlossen sind
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ergebnisse analysieren
        overall_success = True
        successful_components = 0
        
        for i, result in enumerate(results):
            component_name = ['markets', 'portfolios', 'cycles', 'news'][i]
            
            if isinstance(result, Exception):
                logger.error(f"Fehler bei parallelem Update von {component_name}: {str(result)}")
                overall_success = False
            elif isinstance(result, dict) and not result.get("success", False):
                logger.warning(f"Update von {component_name} nicht erfolgreich: {result.get('error', 'Unbekannter Fehler')}")
                overall_success = False
            else:
                successful_components += 1
        
        # Gesamtstatus protokollieren
        duration = time.time() - start_time
        metrics.record_full_update(success=overall_success)
        
        if overall_success:
            logger.info(f"✅ Alle Daten parallel aktualisiert in {duration:.2f}s")
        else:
            logger.warning(f"⚠️ Nur {successful_components}/4 Komponenten erfolgreich parallel aktualisiert in {duration:.2f}s")
        
        # Memory-Management
        gc.collect()
        
        # Metriken protokollieren
        metrics_logger.info(f"UPDATE ALL PARALLEL: {'SUCCESS' if overall_success else 'PARTIAL'} in {duration:.2f}s")
        metrics.log_stats()
        
        return overall_success, duration
        
    except Exception as e:
        logger.error(f"Kritischer Fehler bei paralleler Datenaktualisierung: {str(e)}", exc_info=True)
        metrics.record_full_update(success=False)
        return False, time.time() - start_time

def update_all_data_optimized():
    """
    Optimierter Wrapper für die Datenaktualisierung
    Wählt automatisch zwischen sequenzieller und paralleler Ausführung
    basierend auf historischer Performance und API-Verfügbarkeit
    """
    # Sequentielle Ausführung für Baseline-Messung (einmal alle 10 Updates)
    use_sequential = random.random() < 0.1
    
    if use_sequential:
        # Sequenzielle Ausführung für Benchmark-Messung
        success_seq, duration_seq = update_all_real_data()
        return success_seq, duration_seq, "sequential"
    else:
        try:
            # Event Loop für asyncio erstellen
            loop = get_or_create_eventloop()
            
            # Parallele Ausführung mit asyncio
            success_par, duration_par = loop.run_until_complete(update_all_real_data_parallel())
            
            # Gelegentliche sequenzielle Ausführung zum Performance-Vergleich
            if random.random() < 0.1:
                success_seq, duration_seq = update_all_real_data()
                # Performance-Vergleich für Metriken
                metrics.record_parallel_efficiency(duration_seq, duration_par)
                logger.info(f"Performance-Vergleich: Parallel {duration_par:.2f}s vs. Sequenziell {duration_seq:.2f}s")
                
            return success_par, duration_par, "parallel"
        except Exception as e:
            logger.error(f"Fehler bei paralleler Ausführung, fallback auf sequenziell: {str(e)}", exc_info=True)
            # Fallback auf sequenzielle Ausführung bei Problemen
            success_seq, duration_seq = update_all_real_data()
            return success_seq, duration_seq, "sequential_fallback"

class SafeScheduler:
    """
    Thread-sichere Scheduler-Implementierung mit verbessertem Error-Handling,
    Timeout-Management und Thread-Kontrolle
    
    Diese Version unterstützt die Integration mit dem Scheduler-Process-Manager
    und bietet erweiterte Graceful-Shutdown-Funktionen.
    """
    
    def __init__(self, catch_exceptions=True, managed_mode=False):
        """
        Initialisiert den SafeScheduler
        
        :param catch_exceptions: Ob Exceptions abgefangen werden sollen oder nicht
        :param managed_mode: Ob der Scheduler im Process-Manager-Modus läuft
        """
        self._scheduler = schedule.Scheduler()
        self._stop_event = threading.Event()
        self._thread = None
        self._initialized = False
        self._running_update = False
        self._last_update_time = None
        self._update_lock = threading.Lock()
        self._active_threads = []
        self._catch_exceptions = catch_exceptions
        self._managed_mode = managed_mode
        self._status_file = "scheduler_status.json"
        self._shutdown_callbacks = []
        
        # Signalhandler für sauberes Beenden
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialisiere Status-Datei im managed mode
        if self._managed_mode:
            self._update_status_file({
                "status": "initializing",
                "pid": os.getpid(),
                "start_time": datetime.now().isoformat(),
                "last_update": None,
                "metrics": {
                    "update_success": 0,
                    "update_failure": 0
                }
            })
    
    def _signal_handler(self, signum, frame):
        """Signal-Handler für sauberes Beenden mit Graceful-Shutdown-Unterstützung"""
        logger.info(f"Signal {signum} empfangen, führe Graceful Shutdown durch...")
        
        # Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "shutting_down",
                "shutdown_time": datetime.now().isoformat(),
                "shutdown_reason": f"Signal {signum}"
            })
        
        # Führe alle registrierten Shutdown-Callbacks aus
        for callback in self._shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Fehler beim Ausführen eines Shutdown-Callbacks: {e}")
        
        # Scheduler stoppen
        self.stop()
    
    def register_shutdown_callback(self, callback):
        """Registriert einen Callback, der beim Shutdown ausgeführt wird"""
        if callable(callback):
            self._shutdown_callbacks.append(callback)
            return True
        return False
    
    def _update_status_file(self, status_data):
        """Aktualisiert die Status-Datei mit den übergebenen Daten"""
        if not self._managed_mode:
            return
            
        try:
            # Lese aktuelle Daten, wenn vorhanden
            current_data = {}
            if os.path.exists(self._status_file):
                with open(self._status_file, "r") as f:
                    current_data = json.load(f)
            
            # Aktualisiere mit neuen Daten
            current_data.update(status_data)
            
            # Speichern
            with open(self._status_file, "w") as f:
                json.dump(current_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Fehler beim Aktualisieren der Status-Datei: {e}")
    
    def update_metrics(self, metrics_data):
        """Aktualisiert die Metriken in der Status-Datei"""
        if not self._managed_mode:
            return
            
        try:
            self._update_status_file({
                "last_update": datetime.now().isoformat(),
                "metrics": metrics_data
            })
        except Exception as e:
            logger.warning(f"Fehler beim Aktualisieren der Metriken: {e}")
    
    def get_status(self):
        """Gibt den aktuellen Status des Schedulers zurück"""
        status = {
            "running": self._thread is not None and self._thread.is_alive(),
            "update_in_progress": self._running_update,
            "last_update_time": self._last_update_time.isoformat() if self._last_update_time else None,
            "active_threads": len([t for t in self._active_threads if t.is_alive()]),
            "initialized": self._initialized,
            "pid": os.getpid(),
            "uptime": (datetime.now() - metrics.data["uptime_start"]).total_seconds() if "uptime_start" in metrics.data else None
        }
        
        # Erweiterte Metriken hinzufügen
        status["metrics"] = metrics.get_stats()
        
        # Cache-Metriken hinzufügen
        try:
            cache_stats = get_cache_stats()
            status["cache"] = {
                "enabled": True,
                "hit_ratio": f"{cache_stats.get('hit_ratio', 0) * 100:.1f}%",
                "size": cache_stats.get('size', 0),
                "memory_usage_mb": f"{cache_stats.get('memory_usage_mb', 0):.1f} MB",
                "disk_enabled": cache_stats.get('disk_enabled', False),
                "hits": cache_stats.get('hits', 0),
                "misses": cache_stats.get('misses', 0),
                "fallbacks": cache_stats.get('fallbacks', 0)
            }
        except Exception as e:
            logger.warning(f"Fehler beim Abrufen der Cache-Metriken: {e}")
            status["cache"] = {"enabled": False, "error": str(e)}
        
        return status
    
    def setup_schedule(self):
        """Konfiguriert die geplanten Aufgaben mit adaptiver Scheduling-Logik"""
        # Haupt-Schedule während der Handelszeiten
        schedule.every().day.at("08:00").do(self._safe_update, priority='high')
        schedule.every().day.at("12:00").do(self._safe_update, priority='high')
        schedule.every().day.at("16:00").do(self._safe_update, priority='high')
        
        # Zusätzlich einige Updates außerhalb der Hauptzeiten, aber mit niedrigerer Priorität
        schedule.every().day.at("20:00").do(self._safe_update, priority='medium')
        
        # Täglicher Gesundheitscheck und Metrik-Reset
        schedule.every().day.at("00:00").do(self._health_check)
        
        # Nur einmal ausführen beim ersten Setup mit verzögertem Start für bessere App-Initialisierung
        if not self._initialized:
            logger.info("Scheduler initialisiert, plane erste Aktualisierung...")
            # Verzögerte Initialisierung, um App-Startup nicht zu verlangsamen
            self._delayed_initial_update()
            self._initialized = True
    
    def _delayed_initial_update(self):
        """Verzögerte Erstinitialisierung für besseren App-Startup"""
        def delayed_start():
            try:
                # Kurz warten, damit die App vollständig starten kann
                time.sleep(10)
                logger.info("Erste Datenaktualisierung wird gestartet...")
                self._safe_update(priority='high')
            except Exception as e:
                logger.error(f"Fehler bei initialer Aktualisierung: {e}", exc_info=True)
        
        # Starten in separatem Thread
        init_thread = threading.Thread(target=delayed_start)
        init_thread.daemon = True
        init_thread.start()
    
    def _health_check(self):
        """Täglicher Gesundheitscheck und Reset relevanter Metriken"""
        logger.info("Führe täglichen Gesundheitscheck durch...")
        
        try:
            # API-Gesundheit prüfen
            api_health = check_api_health()
            
            # Cache-Gesundheit prüfen
            cache_stats = get_cache_stats()
            cache_health = {
                'hit_ratio': cache_stats.get('hit_ratio', 0) * 100,  # as percentage
                'size': cache_stats.get('size', 0),
                'memory_usage_mb': cache_stats.get('memory_usage_mb', 0),
                'disk_enabled': cache_stats.get('disk_enabled', False)
            }
            
            # Status protokollieren
            metrics_logger.info(f"HEALTH CHECK: Internet={api_health['internet_connection']}, " +
                               f"Yahoo={api_health['yahoo_finance']}, " +
                               f"AlphaVantage={api_health['alpha_vantage']}, " +
                               f"Cache Hit Ratio={cache_health['hit_ratio']:.1f}%, " +
                               f"Cache Size={cache_health['size']} items")
            
            # Bei ernsthaften Problemen kritisches Log erstellen
            if not api_health['internet_connection']:
                logger.critical("❌ KRITISCH: Keine Internetverbindung erkannt bei Gesundheitscheck")
            elif not (api_health['yahoo_finance'] or api_health['alpha_vantage']):
                logger.critical("❌ KRITISCH: Keine Daten-API erreichbar")
            
            # Ungenutzte, aber potenziell blockierende Threads aufräumen
            self._cleanup_threads()
            
            # Cache-Überwachung und Optimierung
            if cache_health['memory_usage_mb'] > 500:  # If cache exceeds 500MB
                logger.warning(f"Cache-Speichernutzung hoch: {cache_health['memory_usage_mb']:.1f}MB")
                # Trigger garbage collection
                gc.collect()
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Gesundheitscheck: {e}", exc_info=True)
            return True  # Trotzdem weiterlaufen lassen
    
    def _cleanup_threads(self):
        """Räumt nicht mehr laufende Threads auf"""
        if self._active_threads:
            active = [t for t in self._active_threads if t.is_alive()]
            inactive = len(self._active_threads) - len(active)
            if inactive > 0:
                logger.debug(f"{inactive} beendete Threads wurden aufgeräumt")
            self._active_threads = active
    
    def _safe_update(self, priority='medium'):
        """
        Thread-sichere Wrapper-Methode für Aktualisierungen mit Prioritätsmanagement,
        Timeout-Kontrolle und optimierter Performance durch Parallelisierung
        
        :param priority: Priorität des Updates ('high', 'medium', 'low')
        """
        # Verhindern mehrerer gleichzeitiger Updates
        if self._running_update:
            if priority == 'high':
                logger.warning("Hohes Prioritäts-Update angefordert, aber bereits Update aktiv. Warte auf Abschluss...")
                # Für hohe Priorität warten wir aktiv auf Abschluss des vorherigen Updates
                wait_start = time.time()
                while self._running_update and time.time() - wait_start < 300:  # Max 5 Minuten warten
                    time.sleep(1)
                if self._running_update:
                    logger.error("Vorheriges Update läuft immer noch nach 5 Minuten, breche ab.")
                    return True
            else:
                logger.info(f"Update mit Priorität '{priority}' übersprungen - bereits ein Update aktiv")
                return True
        
        # Prüfen, ob genügend Zeit seit letztem Update vergangen ist
        # Adaptives Zeitlimit basierend auf Priorität
        if self._last_update_time:
            time_since_last = datetime.now() - self._last_update_time
            min_interval = {
                'high': 300,     # 5 Minuten für hohe Priorität
                'medium': 1800,  # 30 Minuten für mittlere Priorität
                'low': 3600      # 60 Minuten für niedrige Priorität
            }.get(priority, 1800)
            
            if time_since_last.total_seconds() < min_interval:
                logger.info(f"Update mit Priorität '{priority}' übersprungen - letztes Update vor {time_since_last.total_seconds() / 60:.1f} Minuten")
                return True
        
        # Update als laufend markieren mit Thread-sicherer Kontrolle
        with self._update_lock:
            if self._running_update:
                return True  # Nochmalige Überprüfung innerhalb des Locks
            self._running_update = True
        
        # Eigentlichen Update-Prozess in separatem Thread starten
        try:
            def do_update_with_timeout():
                try:
                    # Optimierte Datenaktualisierung mit Parallelisierung
                    success, duration, method = update_all_data_optimized()
                    logger.info(f"Datenaktualisierung abgeschlossen (Methode: {method}) in {duration:.2f}s")
                    
                    # Memory-Management nach Update
                    gc.collect()
                    
                    with self._update_lock:
                        self._running_update = False
                        self._last_update_time = datetime.now()
                except Exception as e:
                    logger.error(f"Unbehandelter Fehler im Update-Thread: {e}", exc_info=True)
                    with self._update_lock:
                        self._running_update = False
            
            # Thread mit Timeout und Überwachung erstellen
            update_thread = threading.Thread(target=do_update_with_timeout)
            update_thread.daemon = True
            update_thread.start()
            self._active_threads.append(update_thread)
            
            # Thread-Verwaltung (ältere entfernen)
            self._cleanup_threads()
            
            # Erfolg melden
            return True
        except Exception as e:
            logger.error(f"Fehler beim Starten des Update-Threads: {e}", exc_info=True)
            with self._update_lock:
                self._running_update = False
            return True  # Schedule trotz Fehler beibehalten
    
    def stop(self, timeout=30):
        """
        Stoppt den Scheduler-Thread sauber und beendet alle aktiven Updates
        
        :param timeout: Timeout in Sekunden für das Beenden der Threads (pro Thread)
        """
        logger.info("Stoppe Scheduler und alle aktiven Updates...")
        
        # Im managed mode, Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "stopping",
                "stop_time": datetime.now().isoformat()
            })
        
        # Signal zum Stoppen setzen
        self._stop_event.set()
        
        # Warten bis Thread beendet ist, falls er läuft
        if self._thread and self._thread.is_alive():
            logger.info("Warte auf Beendigung des Scheduler-Threads...")
            self._thread.join(timeout=timeout)  # Mit konfiguriertem Timeout
            if self._thread.is_alive():
                logger.warning(f"Scheduler-Thread konnte nicht innerhalb von {timeout}s gestoppt werden")
        
        # Aktive Threads protokollieren und versuchen zu beenden
        active_threads = [t for t in self._active_threads if t.is_alive()]
        active_count = len(active_threads)
        
        if active_count > 0:
            logger.info(f"Warte auf Beendigung von {active_count} aktiven Update-Threads...")
            
            # Versuche, alle aktiven Updates zu beenden (mit Timeout)
            start_time = time.time()
            max_wait = timeout * active_count  # Maximal timeout Sekunden pro Thread
            
            while active_threads and time.time() - start_time < max_wait:
                for thread in list(active_threads):
                    if not thread.is_alive():
                        active_threads.remove(thread)
                time.sleep(0.5)
                
            # Überprüfe, ob alle Threads beendet wurden
            still_active = len(active_threads)
            if still_active > 0:
                logger.warning(f"{still_active} Threads konnten nicht sauber beendet werden")
        
        # Versuchen, Metriken zu speichern
        try:
            metrics.log_stats()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Metriken: {e}")
        
        # Im managed mode, Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "stopped",
                "stop_completed_time": datetime.now().isoformat()
            })
            
        logger.info("Scheduler wurde erfolgreich gestoppt")
    
    def every(self, interval=1):
        """
        Schedule a job to run every interval time units.
        :param interval: Integer Zeit-Einheiten
        :return: Job instance for method chaining
        """
        return self._scheduler.every(interval)
    
    def run_pending(self):
        """
        Führt alle anstehenden Jobs aus.
        """
        self._scheduler.run_pending()
    
    def _run(self):
        """Hauptmethode des Threads - läuft im Hintergrund mit verbessertem Error-Handling"""
        logger.info("Scheduler-Thread gestartet")
        self.setup_schedule()
        
        # Watchdog für hängende Updates
        last_activity = time.time()
        last_heartbeat = time.time()
        
        while not self._stop_event.is_set():
            try:
                # Führe anstehende Aufgaben aus
                self.run_pending()
                
                # Prüfen auf hängende Updates (mehr als 30 Minuten)
                if self._running_update:
                    time_since_start = time.time() - last_activity
                    if time_since_start > 1800:  # 30 Minuten
                        logger.warning(f"Update läuft seit {time_since_start/60:.1f} Minuten. Potenziell hängend.")
                        with self._update_lock:
                            self._running_update = False
                        logger.warning("Hängendes Update zurückgesetzt")
                else:
                    # Aktivitätszeitpunkt aktualisieren
                    last_activity = time.time()
                
                # Periodisches Heartbeat und Status-Update (alle 60 Sekunden)
                current_time = time.time()
                if current_time - last_heartbeat > 60 and self._managed_mode:
                    # Status aktualisieren mit Heartbeat
                    self._update_status_file({
                        "status": "running",
                        "heartbeat": datetime.now().isoformat(),
                        "memory_usage": metrics.data.get("memory_usage", {}),
                        "current_stats": {
                            "update_in_progress": self._running_update,
                            "active_threads": len([t for t in self._active_threads if t.is_alive()]),
                        }
                    })
                    last_heartbeat = current_time
                
                # Kurzer Sleep mit besserer Kontrolle
                for _ in range(6):  # 6 x 5 Sekunden = 30 Sekunden
                    if self._stop_event.is_set():
                        break
                    # Kurze Intervalle für bessere Reaktionsfähigkeit
                    self._stop_event.wait(timeout=5)
            except Exception as e:
                if self._catch_exceptions:
                    logger.error(f"Fehler im Scheduler-Loop: {e}", exc_info=True)
                    
                    # Status aktualisieren bei Fehlern
                    if self._managed_mode:
                        self._update_status_file({
                            "last_error": {
                                "time": datetime.now().isoformat(),
                                "message": str(e),
                                "type": e.__class__.__name__
                            }
                        })
                    
                    # Kurze Pause bei Fehlern, aber Thread weiter laufen lassen
                    self._stop_event.wait(timeout=5)
                else:
                    logger.critical(f"Unbehandelter Fehler im Scheduler-Loop: {e}", exc_info=True)
                    
                    # Status aktualisieren bei kritischem Fehler
                    if self._managed_mode:
                        self._update_status_file({
                            "status": "error",
                            "critical_error": {
                                "time": datetime.now().isoformat(),
                                "message": str(e),
                                "type": e.__class__.__name__
                            }
                        })
                    
                    raise
        
        logger.info("Scheduler-Thread wurde sauber beendet.")
        
    def start(self, run_immediate_update=False):
        """
        Startet den Scheduler in einem separaten Thread
        
        :param run_immediate_update: Ob sofort ein Update ausgeführt werden soll
        :return: self für Method Chaining
        """
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler läuft bereits, kein Neustart nötig")
            return self
        
        # Im managed mode, Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "starting",
                "start_time": datetime.now().isoformat()
            })
        
        # Neuen Thread erstellen und starten
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        # Im managed mode, Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "running",
                "thread_id": self._thread.ident,
                "running_since": datetime.now().isoformat()
            })
        
        # Sofortiges Update ausführen, wenn gewünscht
        if run_immediate_update:
            logger.info("Führe sofortiges Update aus...")
            # In separatem Thread, um nicht zu blockieren
            immediate_thread = threading.Thread(target=self._safe_update, kwargs={"priority": 'high'})
            immediate_thread.daemon = True
            immediate_thread.start()
            self._active_threads.append(immediate_thread)
        
        return self
    
    def restart(self, wait_for_shutdown=True, timeout=30):
        """
        Startet den Scheduler neu
        
        :param wait_for_shutdown: Ob auf das vollständige Herunterfahren gewartet werden soll
        :param timeout: Timeout in Sekunden für das Warten
        :return: self für Method Chaining
        """
        logger.info("Starte Scheduler neu...")
        
        # Status aktualisieren
        if self._managed_mode:
            self._update_status_file({
                "status": "restarting",
                "restart_time": datetime.now().isoformat()
            })
        
        # Scheduler stoppen
        self.stop(timeout=timeout)
        
        # Auf vollständiges Herunterfahren warten, wenn gewünscht
        if wait_for_shutdown and self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        
        # Scheduler neu starten
        return self.start(run_immediate_update=True)

def run_scheduled_updates(parallel=True, max_workers=None):
    """Führt Datenaktualisierungen direkt aus (für den Schedule-Job)"""
    try:
        logger.info(f"Geplante Datenaktualisierung wird ausgeführt (parallel={parallel})")
        
        # Konfiguriere Worker-Anzahl basierend auf Konfiguration oder Übergabeparameter
        if max_workers is None:
            max_workers = SchedulerConfig.MAX_WORKERS
        
        # Optimiere Parallelisierungsgrad
        if parallel:
            try:
                loop = get_or_create_eventloop()
                success, duration = loop.run_until_complete(update_all_real_data_parallel())
                logger.info(f"Parallele Datenaktualisierung abgeschlossen in {duration:.2f}s")
            except Exception as e:
                logger.error(f"Fehler bei paralleler Ausführung, fallback auf sequenziell: {e}")
                success, duration = update_all_real_data()
                logger.info(f"Sequentielle Datenaktualisierung (Fallback) abgeschlossen in {duration:.2f}s")
        else:
            # Sequentielle Ausführung
            success, duration = update_all_real_data()
            logger.info(f"Sequentielle Datenaktualisierung abgeschlossen in {duration:.2f}s")
        
        # Memory-Management
        gc.collect()
        
        return {
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unbehandelter Fehler bei Ausführung geplanter Updates: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Globale Scheduler-Instanz für Singleton-Zugriff
_scheduler_instance = None

def get_scheduler():
    """Gibt die globale Scheduler-Instanz zurück (Singleton)"""
    global _scheduler_instance
    return _scheduler_instance

def start_scheduler(managed_mode=False, run_immediate_update=False):
    """
    Startet den optimierten, hochperformanten Scheduler mit Parallelisierung
    
    :param managed_mode: Ob der Scheduler im Process-Manager-Modus läuft
    :param run_immediate_update: Ob sofort ein Update ausgeführt werden soll
    :return: Die Scheduler-Instanz
    """
    global _scheduler_instance
    
    logger.info(f"Starte optimierten Daten-Aktualisierungs-Scheduler (managed_mode={managed_mode})...")
    try:
        # Prüfen, ob Abhängigkeiten vorhanden sind
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp nicht gefunden, installiere es für beste Async-Performance...")
            import pip
            pip.main(['install', 'aiohttp'])
            logger.info("aiohttp erfolgreich installiert")
        
        try:
            import psutil
        except ImportError:
            logger.warning("psutil nicht gefunden, installiere es für Ressourcen-Monitoring...")
            import pip
            pip.main(['install', 'psutil'])
            logger.info("psutil erfolgreich installiert")
        
        # Memory-Management optimieren
        gc.collect()
        
        # Scheduler initialisieren
        scheduler = SafeScheduler(
            catch_exceptions=SchedulerConfig.CATCH_EXCEPTIONS,
            managed_mode=managed_mode
        )
        
        # Konfiguriere den Scheduler basierend auf der Umgebungskonfiguration
        scheduler.every(SchedulerConfig.UPDATE_INTERVAL_MINUTES).minutes.do(
            run_scheduled_updates, 
            parallel=SchedulerConfig.ENABLE_PARALLEL_UPDATES,
            max_workers=SchedulerConfig.MAX_WORKERS
        )
        
        # Shutdown-Callback für saubere Beendigung registrieren
        def cleanup_on_shutdown():
            logger.info("Führe Scheduler-Cleanup bei Shutdown durch...")
            try:
                # Metriken speichern
                metrics.log_stats()
                
                # Speicher freigeben
                gc.collect()
                
                # Status-Datei aktualisieren
                if managed_mode:
                    scheduler._update_status_file({
                        "status": "shutdown_complete",
                        "shutdown_completed_at": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Fehler beim Cleanup bei Shutdown: {e}")
        
        # Callback registrieren
        scheduler.register_shutdown_callback(cleanup_on_shutdown)
        
        # Scheduler starten
        if not SchedulerConfig.MANUAL_START:
            scheduler.start(run_immediate_update=run_immediate_update)
            logger.info("Optimierter Daten-Aktualisierungs-Scheduler erfolgreich gestartet!")
            logger.info(f"Parallelisierung: {'Aktiviert' if SchedulerConfig.ENABLE_PARALLEL_UPDATES else 'Deaktiviert'}")
            logger.info(f"Update-Intervall: {SchedulerConfig.UPDATE_INTERVAL_MINUTES} Minuten")
            logger.info(f"Process-Manager-Modus: {'Aktiviert' if managed_mode else 'Deaktiviert'}")
        else:
            logger.info("Scheduler im manuellen Modus initialisiert - verwende scheduler.start() zum Starten")
        
        # Globale Instanz speichern
        _scheduler_instance = scheduler
        
        return scheduler
    except Exception as e:
        logger.error(f"Fehler beim Starten des Schedulers: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    """
    Wenn das Skript direkt ausgeführt wird, kann es als Standalone-Scheduler laufen
    oder ein einmaliges Update ausführen
    
    Verwendung:
    - python data_refresh_scheduler.py            # Einmaliges Update
    - python data_refresh_scheduler.py --daemon   # Als Daemon (für Process-Manager)
    - python data_refresh_scheduler.py --status   # Status anzeigen
    """
    import argparse
    
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description="Daten-Aktualisierungs-Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Als Daemon-Prozess laufen (für Process-Manager)")
    parser.add_argument("--status", action="store_true", help="Aktuellen Status anzeigen")
    parser.add_argument("--update", action="store_true", help="Einmaliges Update ausführen")
    args = parser.parse_args()
    
    # Status anzeigen
    if args.status:
        if os.path.exists("scheduler_status.json"):
            try:
                with open("scheduler_status.json", "r") as f:
                    status = json.load(f)
                print(json.dumps(status, indent=2))
            except Exception as e:
                print(f"Fehler beim Lesen des Status: {e}")
        else:
            print("Keine Status-Datei gefunden. Scheduler läuft möglicherweise nicht.")
        exit(0)
    
    # Als Daemon laufen
    if args.daemon:
        logger.info("Starte Scheduler im Daemon-Modus (für Process-Manager)...")
        
        # PID in Datei schreiben für Process-Manager
        with open("scheduler.pid", "w") as f:
            f.write(str(os.getpid()))
        
        # Scheduler mit Process-Manager-Unterstützung starten
        scheduler = start_scheduler(managed_mode=True, run_immediate_update=True)
        
        try:
            # Endlosschleife mit Sleep, damit der Prozess läuft
            logger.info("Scheduler läuft im Daemon-Modus. Drücke Ctrl+C zum Beenden.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler wird durch Benutzer beendet...")
            scheduler.stop()
        finally:
            # PID-Datei entfernen
            if os.path.exists("scheduler.pid"):
                os.remove("scheduler.pid")
    
    # Einmaliges Update ausführen (Standardverhalten)
    else:
        logger.info("Führe einmaliges Daten-Update aus...")
        success, duration, method = update_all_data_optimized()
        logger.info(f"Daten-Update abgeschlossen mit Methode {method} in {duration:.2f}s (Erfolg: {success})")