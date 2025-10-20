"""
Smart Data Fetcher - Intelligentes Load-Balancing & Performance-Optimierung
============================================================================

Features:
- Round-Robin Load Balancing über alle Quellen
- Rate-Limiting pro API
- Parallele Requests für mehrere Symbole
- Intelligent Caching mit unterschiedlichen TTLs
- Automatische Fehler-Erkennung und Blacklisting
- Connection Pooling für bessere Performance
"""

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('smart_data_fetcher')

class RateLimiter:
    """Rate Limiter mit Sliding Window"""
    
    def __init__(self, max_calls_per_minute=60):
        self.max_calls = max_calls_per_minute
        self.calls = deque()
        self.lock = threading.Lock()
    
    def can_call(self):
        """Prüfe ob API-Call erlaubt ist"""
        with self.lock:
            now = time.time()
            # Entferne Calls älter als 1 Minute
            while self.calls and self.calls[0] < now - 60:
                self.calls.popleft()
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            return False
    
    def wait_if_needed(self):
        """Warte wenn Rate-Limit erreicht"""
        while not self.can_call():
            time.sleep(0.5)

class DataSourceManager:
    """Verwaltet alle Datenquellen mit Load-Balancing"""
    
    def __init__(self):
        self.sources = {}
        self.rate_limiters = {}
        self.success_count = defaultdict(int)
        self.failure_count = defaultdict(int)
        self.last_success = {}
        self.blacklist_until = {}
        self.lock = threading.Lock()
        
        # Thread Pool für parallele Requests
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Session mit Connection Pooling
        self.session = self._create_session()
        
        self._initialize_sources()
    
    def _create_session(self):
        """Erstelle optimierte Session mit Connection Pooling"""
        session = requests.Session()
        
        # Connection Pooling - hält Verbindungen offen
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Standard Headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def _initialize_sources(self):
        """Initialisiere alle Datenquellen"""
        
        # AKTIEN-QUELLEN
        self.sources['yahoo_query'] = {
            'name': 'Yahoo Finance Query API',
            'type': 'stock',
            'priority': 1,
            'rate_limit': 100,  # Großzügig
            'fetch_func': self._fetch_yahoo_query
        }
        
        self.sources['stooq'] = {
            'name': 'Stooq.pl',
            'type': 'stock',
            'priority': 2,
            'rate_limit': 50,
            'fetch_func': self._fetch_stooq
        }
        
        self.sources['yahoo_csv'] = {
            'name': 'Yahoo Finance CSV',
            'type': 'stock',
            'priority': 3,
            'rate_limit': 80,
            'fetch_func': self._fetch_yahoo_csv
        }
        
        # KRYPTO-QUELLEN
        self.sources['binance'] = {
            'name': 'Binance Public API',
            'type': 'crypto',
            'priority': 1,
            'rate_limit': 200,  # Sehr hoch!
            'fetch_func': self._fetch_binance
        }
        
        self.sources['coingecko'] = {
            'name': 'CoinGecko',
            'type': 'crypto',
            'priority': 2,
            'rate_limit': 50,
            'fetch_func': self._fetch_coingecko
        }
        
        self.sources['coinbase'] = {
            'name': 'Coinbase Public API',
            'type': 'crypto',
            'priority': 3,
            'rate_limit': 100,
            'fetch_func': self._fetch_coinbase
        }
        
        # FOREX-QUELLEN
        self.sources['ecb'] = {
            'name': 'European Central Bank',
            'type': 'forex',
            'priority': 1,
            'rate_limit': 30,
            'fetch_func': self._fetch_ecb
        }
        
        self.sources['exchangerate_api'] = {
            'name': 'ExchangeRate-API',
            'type': 'forex',
            'priority': 2,
            'rate_limit': 50,
            'fetch_func': self._fetch_exchangerate
        }
        
        # Rate Limiters erstellen
        for source_id, source_info in self.sources.items():
            self.rate_limiters[source_id] = RateLimiter(source_info['rate_limit'])
        
        logger.info(f"✅ {len(self.sources)} Datenquellen initialisiert")
    
    def is_source_available(self, source_id):
        """Prüfe ob Quelle verfügbar (nicht blacklisted)"""
        if source_id in self.blacklist_until:
            if time.time() < self.blacklist_until[source_id]:
                return False
            else:
                del self.blacklist_until[source_id]
        return True
    
    def get_best_sources(self, asset_type, count=3):
        """Hole beste verfügbare Quellen für Asset-Typ"""
        available = []
        
        for source_id, source_info in self.sources.items():
            if source_info['type'] == asset_type and self.is_source_available(source_id):
                # Score basierend auf Erfolgsrate
                success = self.success_count[source_id]
                failure = self.failure_count[source_id]
                total = success + failure
                
                if total > 0:
                    success_rate = success / total
                else:
                    success_rate = 1.0  # Neue Quelle - gebe Chance
                
                available.append((source_id, source_info, success_rate))
        
        # Sortiere nach Priority und Success Rate
        available.sort(key=lambda x: (x[1]['priority'], -x[2]))
        
        return [s[0] for s in available[:count]]
    
    def record_success(self, source_id):
        """Registriere erfolgreichen API-Call"""
        with self.lock:
            self.success_count[source_id] += 1
            self.last_success[source_id] = time.time()
    
    def record_failure(self, source_id):
        """Registriere fehlgeschlagenen API-Call"""
        with self.lock:
            self.failure_count[source_id] += 1
            
            # Blacklist bei vielen Fehlern
            total = self.success_count[source_id] + self.failure_count[source_id]
            if total > 5:
                failure_rate = self.failure_count[source_id] / total
                if failure_rate > 0.5:  # >50% Fehlerrate
                    # Blacklist für 5 Minuten
                    self.blacklist_until[source_id] = time.time() + 300
                    logger.warning(f"⚠️ {source_id} blacklisted für 5 Minuten (Fehlerrate: {failure_rate:.1%})")
    
    # =========================================================================
    # FETCH FUNKTIONEN FÜR JEDE QUELLE
    # =========================================================================
    
    def _fetch_yahoo_query(self, symbol):
        """Yahoo Finance Query API"""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {'interval': '1d', 'range': '1mo'}
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                quote = result.get('indicators', {}).get('quote', [{}])[0]
                
                if quote.get('close'):
                    current = quote['close'][-1]
                    prev = quote['close'][-2] if len(quote['close']) > 1 else current
                    
                    return {
                        'symbol': symbol,
                        'price': round(float(current), 2),
                        'change': round(((current - prev) / prev * 100), 2) if prev else 0,
                        'currency': meta.get('currency', 'USD'),
                        'volume': int(quote.get('volume', [0])[-1]) if quote.get('volume') else 0,
                        'source': 'yahoo_query'
                    }
        except Exception as e:
            logger.debug(f"Yahoo Query failed for {symbol}: {e}")
            return None
    
    def _fetch_stooq(self, symbol):
        """Stooq.pl"""
        try:
            stooq_symbol = f"{symbol.lower()}.us" if '.' not in symbol else symbol
            url = "https://stooq.pl/q/d/l/"
            params = {'s': stooq_symbol, 'i': 'd'}
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            if len(lines) > 2:
                last = lines[-1].split(',')
                prev = lines[-2].split(',') if len(lines) > 2 else last
                
                if len(last) >= 5:
                    current = float(last[4])
                    prev_price = float(prev[4]) if len(prev) >= 5 else current
                    
                    return {
                        'symbol': symbol,
                        'price': round(current, 2),
                        'change': round(((current - prev_price) / prev_price * 100), 2),
                        'volume': int(float(last[5])) if len(last) > 5 else 0,
                        'source': 'stooq'
                    }
        except Exception as e:
            logger.debug(f"Stooq failed for {symbol}: {e}")
            return None
    
    def _fetch_yahoo_csv(self, symbol):
        """Yahoo Finance CSV Download"""
        try:
            # Alternativer Yahoo Endpunkt
            end_time = int(time.time())
            start_time = end_time - (30 * 24 * 3600)  # 30 Tage
            
            url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
            params = {
                'period1': start_time,
                'period2': end_time,
                'interval': '1d',
                'events': 'history'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            if len(lines) > 2:
                last = lines[-1].split(',')
                prev = lines[-2].split(',') if len(lines) > 2 else last
                
                if len(last) >= 5:
                    current = float(last[4])  # Close
                    prev_price = float(prev[4]) if len(prev) >= 5 else current
                    
                    return {
                        'symbol': symbol,
                        'price': round(current, 2),
                        'change': round(((current - prev_price) / prev_price * 100), 2),
                        'volume': int(float(last[5])) if len(last) > 5 else 0,
                        'source': 'yahoo_csv'
                    }
        except Exception as e:
            logger.debug(f"Yahoo CSV failed for {symbol}: {e}")
            return None
    
    def _fetch_binance(self, symbol):
        """Binance Public API - SEHR SCHNELL"""
        try:
            # BTC-USD -> BTCUSDT
            binance_symbol = symbol.upper().replace('-', '').replace('USD', 'USDT')
            
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': binance_symbol}
            
            response = self.session.get(url, params=params, timeout=3)
            response.raise_for_status()
            data = response.json()
            
            if 'lastPrice' in data:
                return {
                    'symbol': symbol,
                    'price': round(float(data['lastPrice']), 2),
                    'change': round(float(data.get('priceChangePercent', 0)), 2),
                    'volume': float(data.get('volume', 0)),
                    'source': 'binance'
                }
        except Exception as e:
            logger.debug(f"Binance failed for {symbol}: {e}")
            return None
    
    def _fetch_coingecko(self, symbol):
        """CoinGecko"""
        try:
            crypto_map = {
                'BTC': 'bitcoin', 'BTC-USD': 'bitcoin',
                'ETH': 'ethereum', 'ETH-USD': 'ethereum',
                'ADA': 'cardano', 'ADA-USD': 'cardano',
                'SOL': 'solana', 'SOL-USD': 'solana'
            }
            
            crypto_id = crypto_map.get(symbol.upper(), symbol.lower().replace('-usd', ''))
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if crypto_id in data:
                return {
                    'symbol': symbol,
                    'price': round(float(data[crypto_id]['usd']), 2),
                    'change': round(float(data[crypto_id].get('usd_24h_change', 0)), 2),
                    'source': 'coingecko'
                }
        except Exception as e:
            logger.debug(f"CoinGecko failed for {symbol}: {e}")
            return None
    
    def _fetch_coinbase(self, symbol):
        """Coinbase Public API"""
        try:
            # BTC-USD format passt
            url = f"https://api.coinbase.com/v2/exchange-rates"
            params = {'currency': symbol.split('-')[0] if '-' in symbol else symbol}
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'rates' in data['data']:
                usd_rate = data['data']['rates'].get('USD')
                if usd_rate:
                    return {
                        'symbol': symbol,
                        'price': round(float(usd_rate), 2),
                        'change': 0,  # Coinbase liefert keine Change
                        'source': 'coinbase'
                    }
        except Exception as e:
            logger.debug(f"Coinbase failed for {symbol}: {e}")
            return None
    
    def _fetch_ecb(self, currency_pair):
        """Europäische Zentralbank"""
        try:
            import xml.etree.ElementTree as ET
            
            url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            ns = {'ecb': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            
            target = currency_pair.replace('EUR', '')
            
            for cube in root.findall('.//ecb:Cube[@currency]', ns):
                if cube.get('currency') == target:
                    return {
                        'symbol': currency_pair,
                        'price': round(float(cube.get('rate')), 4),
                        'change': 0,
                        'source': 'ecb'
                    }
        except Exception as e:
            logger.debug(f"ECB failed for {currency_pair}: {e}")
            return None
    
    def _fetch_exchangerate(self, currency_pair):
        """ExchangeRate-API (kostenlos)"""
        try:
            base = currency_pair[:3]
            target = currency_pair[3:]
            
            url = f"https://api.exchangerate-api.com/v4/latest/{base}"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and target in data['rates']:
                return {
                    'symbol': currency_pair,
                    'price': round(float(data['rates'][target]), 4),
                    'change': 0,
                    'source': 'exchangerate_api'
                }
        except Exception as e:
            logger.debug(f"ExchangeRate-API failed for {currency_pair}: {e}")
            return None
    
    # =========================================================================
    # INTELLIGENTE FETCH-METHODE
    # =========================================================================
    
    def fetch_data(self, symbol, asset_type='stock'):
        """
        Hole Daten mit intelligentem Load-Balancing
        
        Versucht mehrere Quellen parallel für maximale Geschwindigkeit
        """
        # Hole beste Quellen für diesen Asset-Typ
        best_sources = self.get_best_sources(asset_type, count=3)
        
        if not best_sources:
            logger.warning(f"Keine verfügbaren Quellen für {asset_type}")
            return None
        
        # Versuche Quellen parallel für maximale Geschwindigkeit
        futures = {}
        
        for source_id in best_sources:
            # Prüfe Rate Limit
            if not self.rate_limiters[source_id].can_call():
                continue
            
            # Starte parallelen Request
            future = self.executor.submit(
                self._try_source,
                source_id,
                symbol
            )
            futures[future] = source_id
        
        # Warte auf erste erfolgreiche Response
        for future in as_completed(futures, timeout=10):
            source_id = futures[future]
            try:
                result = future.result()
                if result:
                    self.record_success(source_id)
                    logger.info(f"✅ {symbol} from {self.sources[source_id]['name']}")
                    return result
                else:
                    self.record_failure(source_id)
            except Exception as e:
                self.record_failure(source_id)
                logger.debug(f"Source {source_id} failed: {e}")
        
        logger.warning(f"❌ Alle Quellen fehlgeschlagen für {symbol}")
        return None
    
    def _try_source(self, source_id, symbol):
        """Versuche Daten von einer Quelle zu holen"""
        try:
            fetch_func = self.sources[source_id]['fetch_func']
            return fetch_func(symbol)
        except Exception as e:
            logger.debug(f"Error in {source_id} for {symbol}: {e}")
            return None
    
    def fetch_multiple(self, symbols, asset_types=None):
        """
        Hole Daten für mehrere Symbole PARALLEL
        
        Massiv Performance-Boost für Portfolio-Abfragen!
        """
        if asset_types is None:
            asset_types = ['stock'] * len(symbols)
        
        results = {}
        futures = {}
        
        for symbol, asset_type in zip(symbols, asset_types):
            future = self.executor.submit(self.fetch_data, symbol, asset_type)
            futures[future] = symbol
        
        # Sammle Resultate
        for future in as_completed(futures, timeout=30):
            symbol = futures[future]
            try:
                result = future.result()
                if result:
                    results[symbol] = result
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
        
        logger.info(f"✅ Fetched {len(results)}/{len(symbols)} symbols in parallel")
        return results
    
    def get_stats(self):
        """Hole Statistiken über alle Quellen"""
        stats = {}
        for source_id, source_info in self.sources.items():
            success = self.success_count[source_id]
            failure = self.failure_count[source_id]
            total = success + failure
            
            stats[source_id] = {
                'name': source_info['name'],
                'type': source_info['type'],
                'success': success,
                'failure': failure,
                'success_rate': (success / total * 100) if total > 0 else 0,
                'blacklisted': source_id in self.blacklist_until
            }
        
        return stats


# Globale Instanz
smart_fetcher = DataSourceManager()
logger.info("✅ Smart Data Fetcher mit Load-Balancing initialisiert")



