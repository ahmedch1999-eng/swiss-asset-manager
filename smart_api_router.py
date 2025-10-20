"""
Smart API Router - Intelligente API-Verteilung für optimale Nutzung

Dieses Modul implementiert ein intelligentes Routing-System, das alle verfügbaren
kostenlosen APIs optimal nutzt und Calls aufteilt, um Limits zu vermeiden.
"""

import os
import time
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API-Konfiguration mit Limits und Prioritäten"""
    name: str
    api_key: str
    base_url: str
    calls_per_minute: int
    calls_per_day: int
    priority: int
    last_call: float = 0
    calls_today: int = 0
    calls_this_minute: int = 0
    available: bool = True

class SmartAPIRouter:
    """
    Intelligenter API-Router für optimale Nutzung aller verfügbaren APIs
    
    Features:
    - Automatische API-Auswahl basierend auf Symbol-Typ
    - Rate-Limiting für alle APIs
    - Fallback-System bei API-Ausfällen
    - Call-Tracking und Optimierung
    """
    
    def __init__(self):
        self.apis = self._initialize_apis()
        self.cache = {}
        self.cache_duration = {
            'real_time': 5 * 60,      # 5 Minuten
            'historical': 24 * 60 * 60, # 24 Stunden
            'financial': 7 * 24 * 60 * 60, # 7 Tage
        }
    
    def _initialize_apis(self) -> Dict[str, APIConfig]:
        """Initialisiere alle verfügbaren APIs"""
        return {
            'alpha_vantage': APIConfig(
                name='Alpha Vantage',
                api_key=os.getenv('ALPHA_VANTAGE_API_KEY', ''),
                base_url='https://www.alphavantage.co/query',
                calls_per_minute=5,
                calls_per_day=500,
                priority=3
            ),
            'finnhub': APIConfig(
                name='Finnhub',
                api_key=os.getenv('FINNHUB_API_KEY', ''),
                base_url='https://finnhub.io/api/v1',
                calls_per_minute=60,
                calls_per_day=1000,
                priority=2
            ),
            'twelve_data': APIConfig(
                name='Twelve Data',
                api_key=os.getenv('TWELVE_DATA_API_KEY', ''),
                base_url='https://api.twelvedata.com',
                calls_per_minute=8,  # 800 calls/day = ~8/min
                calls_per_day=800,
                priority=2
            ),
            'eodhd': APIConfig(
                name='EODHD',
                api_key=os.getenv('EODHD_API_KEY', ''),
                base_url='https://eodhd.com/api',
                calls_per_minute=1,  # 20 calls/day = ~1/min
                calls_per_day=20,
                priority=4
            ),
            'fmp': APIConfig(
                name='Financial Modeling Prep',
                api_key=os.getenv('FMP_API_KEY', ''),
                base_url='https://financialmodelingprep.com/api/v3',
                calls_per_minute=2,  # 250 calls/day = ~2/min
                calls_per_day=250,
                priority=3
            )
        }
    
    def get_market_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Hole Marktdaten mit intelligenter API-Auswahl
        
        Args:
            symbol: Marktsymbol (z.B. 'AAPL', 'NESN.SW', 'BTC-USD')
            data_type: Art der Daten ('price', 'historical', 'financial')
            
        Returns:
            Marktdaten oder None bei Fehlern
        """
        try:
            # Bestimme beste API für diesen Symbol-Typ
            best_api = self._select_best_api(symbol, data_type)
            if not best_api:
                logger.warning(f"No API available for {symbol}")
                return None
            
            # Prüfe Rate Limits
            if not self._check_rate_limits(best_api):
                logger.warning(f"Rate limit exceeded for {best_api.name}")
                return None
            
            # Hole Daten
            data = self._fetch_data(best_api, symbol, data_type)
            if data:
                # Update API-Statistiken
                self._update_api_stats(best_api)
                logger.info(f"Successfully fetched {symbol} from {best_api.name}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Hole historische Daten für Korrelationsanalyse"""
        try:
            # Wähle beste API für historische Daten
            api = self._select_best_api(symbol, 'historical')
            
            if not api:
                logger.warning(f"No available API for historical data of {symbol}")
                return None
            
            # Hole historische Daten
            historical_data = self._fetch_historical_data(api, symbol, days)
            
            if historical_data:
                logger.info(f"Successfully fetched {days} days of historical data for {symbol} from {api.name}")
                return historical_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def _select_best_api(self, symbol: str, data_type: str) -> Optional[APIConfig]:
        """Wähle beste API basierend auf Symbol-Typ und Verfügbarkeit"""
        symbol_upper = symbol.upper()
        
        # Schweizer Aktien - verwende Alpha Vantage (bessere Unterstützung)
        if symbol_upper.endswith('.SW') or symbol_upper in ['NESN', 'NOVN', 'ROG', 'UBSG']:
            # Für Schweizer Aktien: Versuche alle APIs, aber erwarte möglicherweise keine Daten
            return self._get_available_api(['alpha_vantage', 'twelve_data', 'finnhub'])
        
        # Kryptowährungen - verwende Twelve Data für historische Daten (bessere Unterstützung)
        elif symbol_upper in ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD']:
            if data_type == 'historical':
                return self._get_available_api(['twelve_data', 'alpha_vantage', 'finnhub'])
            else:
                # Für Live-Daten verwende Finnhub
                return self._get_available_api(['finnhub', 'twelve_data', 'alpha_vantage'])
        
        # US-Aktien
        elif symbol_upper in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']:
            if data_type == 'historical':
                return self._get_available_api(['twelve_data', 'alpha_vantage', 'finnhub'])
            else:
                return self._get_available_api(['twelve_data', 'finnhub', 'alpha_vantage', 'fmp'])
        
        # Indizes - verwende Alpha Vantage (bessere Index-Unterstützung)
        elif symbol_upper.startswith('^') or symbol_upper in ['SPX', 'NDX', 'DJI']:
            return self._get_available_api(['alpha_vantage', 'twelve_data'])
        
        # Finanzdaten
        elif data_type == 'financial':
            return self._get_available_api(['fmp', 'eodhd', 'alpha_vantage'])
        
        # Standard: Versuche alle APIs
        else:
            return self._get_available_api(['twelve_data', 'finnhub', 'alpha_vantage'])
    
    def _get_available_api(self, api_names: List[str]) -> Optional[APIConfig]:
        """Hole erste verfügbare API aus der Liste"""
        for api_name in api_names:
            if api_name in self.apis:
                api = self.apis[api_name]
                if api.api_key and self._check_rate_limits(api):
                    return api
        return None
    
    def _check_rate_limits(self, api: APIConfig) -> bool:
        """Prüfe ob API innerhalb der Rate Limits ist"""
        current_time = time.time()
        
        # Reset tägliche Calls um Mitternacht
        if current_time - api.last_call > 24 * 60 * 60:
            api.calls_today = 0
        
        # Reset minütliche Calls
        if current_time - api.last_call > 60:
            api.calls_this_minute = 0
        
        # Prüfe Limits
        if api.calls_today >= api.calls_per_day:
            return False
        if api.calls_this_minute >= api.calls_per_minute:
            return False
        
        return True
    
    def _fetch_data(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von spezifischer API"""
        try:
            # Symbol-Konvertierung für verschiedene APIs
            api_symbol = self._convert_symbol_for_api(api, symbol)
            
            if api.name == 'Alpha Vantage':
                return self._fetch_alpha_vantage(api, api_symbol, data_type)
            elif api.name == 'Finnhub':
                return self._fetch_finnhub(api, api_symbol, data_type)
            elif api.name == 'Twelve Data':
                return self._fetch_twelve_data(api, api_symbol, data_type)
            elif api.name == 'EODHD':
                return self._fetch_eodhd(api, api_symbol, data_type)
            elif api.name == 'Financial Modeling Prep':
                return self._fetch_fmp(api, api_symbol, data_type)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching from {api.name}: {str(e)}")
            return None
    
    def _convert_symbol_for_api(self, api: APIConfig, symbol: str) -> str:
        """Konvertiere Symbol für spezifische API"""
        symbol_upper = symbol.upper()
        
        if api.name == 'Finnhub':
            # Finnhub verwendet andere Symbol-Formate
            if symbol_upper == 'BTC-USD':
                return 'BTC'  # Für historische Daten verwende BTC statt BINANCE:BTCUSDT
            elif symbol_upper == 'ETH-USD':
                return 'ETH'  # Für historische Daten verwende ETH
            elif symbol_upper.endswith('.SW'):
                return symbol_upper  # Schweizer Aktien bleiben gleich
            else:
                return symbol_upper
        
        elif api.name == 'Alpha Vantage':
            # Alpha Vantage verwendet Standard-Formate
            if symbol_upper == '^GSPC':
                return 'SPY'  # S&P 500 ETF als Alternative
            elif symbol_upper == '^IXIC':
                return 'QQQ'  # NASDAQ ETF als Alternative
            else:
                return symbol_upper
        
        elif api.name == 'Twelve Data':
            # Twelve Data verwendet Standard-Formate
            if symbol_upper == 'BTC-USD':
                return 'BTC/USD'  # Twelve Data Format für Krypto
            elif symbol_upper == 'ETH-USD':
                return 'ETH/USD'  # Twelve Data Format für Krypto
            else:
                return symbol_upper
        
        else:
            return symbol_upper
    
    def _fetch_historical_data(self, api: APIConfig, symbol: str, days: int) -> Optional[List[Dict[str, Any]]]:
        """Hole historische Daten von spezifischer API"""
        try:
            api_symbol = self._convert_symbol_for_api(api, symbol)
            
            if api.name == 'Alpha Vantage':
                return self._fetch_alpha_vantage_historical(api, api_symbol, days)
            elif api.name == 'Twelve Data':
                return self._fetch_twelve_data_historical(api, api_symbol, days)
            elif api.name == 'Finnhub':
                return self._fetch_finnhub_historical(api, api_symbol, days)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data from {api.name}: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_historical(self, api: APIConfig, symbol: str, days: int) -> Optional[List[Dict[str, Any]]]:
        """Hole historische Daten von Alpha Vantage"""
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': api.api_key,
                'outputsize': 'compact'
            }
            
            response = requests.get(api.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'Time Series (Daily)' in data:
                time_series = data['Time Series (Daily)']
                historical_data = []
                
                # Konvertiere zu einheitlichem Format
                for date, values in list(time_series.items())[:days]:
                    historical_data.append({
                        'date': date,
                        'open': float(values['1. open']),
                        'high': float(values['2. high']),
                        'low': float(values['3. low']),
                        'close': float(values['4. close']),
                        'volume': int(values['5. volume']),
                        'symbol': symbol,
                        'source': 'Alpha Vantage'
                    })
                
                # Sortiere nach Datum (älteste zuerst)
                historical_data.sort(key=lambda x: x['date'])
                return historical_data
            
            return None
            
        except Exception as e:
            logger.error(f"Alpha Vantage historical error: {str(e)}")
            return None
    
    def _fetch_twelve_data_historical(self, api: APIConfig, symbol: str, days: int) -> Optional[List[Dict[str, Any]]]:
        """Hole historische Daten von Twelve Data"""
        try:
            params = {
                'symbol': symbol,
                'apikey': api.api_key,
                'interval': '1day',
                'outputsize': min(days, 100)  # Twelve Data Limit
            }
            
            response = requests.get(f"{api.base_url}/time_series", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'values' in data:
                historical_data = []
                
                for item in data['values'][:days]:
                    historical_data.append({
                        'date': item['datetime'],
                        'open': float(item['open']),
                        'high': float(item['high']),
                        'low': float(item['low']),
                        'close': float(item['close']),
                        'volume': int(item.get('volume', 0)),  # Volume kann fehlen bei Krypto
                        'symbol': symbol,
                        'source': 'Twelve Data'
                    })
                
                # Sortiere nach Datum (älteste zuerst)
                historical_data.sort(key=lambda x: x['date'])
                return historical_data
            
            return None
            
        except Exception as e:
            logger.error(f"Twelve Data historical error: {str(e)}")
            return None
    
    def _fetch_finnhub_historical(self, api: APIConfig, symbol: str, days: int) -> Optional[List[Dict[str, Any]]]:
        """Hole historische Daten von Finnhub"""
        try:
            # Finnhub verwendet Unix Timestamps
            end_time = int(time.time())
            start_time = end_time - (days * 24 * 60 * 60)
            
            params = {
                'symbol': symbol,
                'resolution': 'D',  # Daily
                'from': start_time,
                'to': end_time,
                'token': api.api_key
            }
            
            response = requests.get(f"{api.base_url}/stock/candle", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('s') == 'ok' and data.get('c'):
                historical_data = []
                
                for i in range(len(data['c'])):
                    historical_data.append({
                        'date': datetime.fromtimestamp(data['t'][i]).strftime('%Y-%m-%d'),
                        'open': float(data['o'][i]),
                        'high': float(data['h'][i]),
                        'low': float(data['l'][i]),
                        'close': float(data['c'][i]),
                        'volume': int(data['v'][i]),
                        'symbol': symbol,
                        'source': 'Finnhub'
                    })
                
                return historical_data
            
            return None
            
        except Exception as e:
            logger.error(f"Finnhub historical error: {str(e)}")
            return None
    
    def _fetch_alpha_vantage(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von Alpha Vantage"""
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api.api_key
            }
            
            response = requests.get(api.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'symbol': symbol,
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('09. change', 0)),
                    'change_percent': float(str(quote.get('10. change percent', 0)).replace('%', '')),
                    'volume': int(quote.get('06. volume', 0)),
                    'source': 'Alpha Vantage',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Alpha Vantage error: {str(e)}")
            return None
    
    def _fetch_finnhub(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von Finnhub"""
        try:
            params = {
                'symbol': symbol,
                'token': api.api_key
            }
            
            response = requests.get(f"{api.base_url}/quote", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'c' in data:  # current price
                return {
                    'symbol': symbol,
                    'price': float(data.get('c', 0)),
                    'change': float(data.get('d', 0)),
                    'change_percent': float(data.get('dp', 0)),
                    'volume': int(data.get('v', 0)),
                    'source': 'Finnhub',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Finnhub error: {str(e)}")
            return None
    
    def _fetch_twelve_data(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von Twelve Data"""
        try:
            params = {
                'symbol': symbol,
                'apikey': api.api_key,
                'interval': '1day',
                'outputsize': 1
            }
            
            response = requests.get(f"{api.base_url}/time_series", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'values' in data and data['values']:
                value = data['values'][0]
                return {
                    'symbol': symbol,
                    'price': float(value.get('close', 0)),
                    'change': float(value.get('close', 0)) - float(value.get('open', 0)),
                    'change_percent': ((float(value.get('close', 0)) - float(value.get('open', 0))) / float(value.get('open', 1))) * 100,
                    'volume': int(value.get('volume', 0)),
                    'source': 'Twelve Data',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Twelve Data error: {str(e)}")
            return None
    
    def _fetch_eodhd(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von EODHD"""
        try:
            params = {
                's': symbol,
                'api_token': api.api_key,
                'fmt': 'json'
            }
            
            response = requests.get(f"{api.base_url}/real-time/{symbol}", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'code' in data and data['code'] == symbol:
                return {
                    'symbol': symbol,
                    'price': float(data.get('close', 0)),
                    'change': float(data.get('change', 0)),
                    'change_percent': float(data.get('change_p', 0)),
                    'volume': int(data.get('volume', 0)),
                    'source': 'EODHD',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"EODHD error: {str(e)}")
            return None
    
    def _fetch_fmp(self, api: APIConfig, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Hole Daten von Financial Modeling Prep"""
        try:
            if not api.api_key or api.api_key == 'coming_soon':
                return None
            
            params = {
                'apikey': api.api_key
            }
            
            response = requests.get(f"{api.base_url}/quote/{symbol}", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                quote = data[0]
                return {
                    'symbol': symbol,
                    'price': float(quote.get('price', 0)),
                    'change': float(quote.get('change', 0)),
                    'change_percent': float(quote.get('changesPercentage', 0)),
                    'volume': int(quote.get('volume', 0)),
                    'market_cap': float(quote.get('marketCap', 0)),
                    'source': 'Financial Modeling Prep',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"FMP error: {str(e)}")
            return None
    
    def _update_api_stats(self, api: APIConfig):
        """Update API-Statistiken nach erfolgreichem Call"""
        current_time = time.time()
        api.last_call = current_time
        api.calls_today += 1
        api.calls_this_minute += 1
    
    def get_api_status(self) -> Dict[str, Any]:
        """Hole Status aller APIs"""
        status = {}
        for name, api in self.apis.items():
            status[name] = {
                'name': api.name,
                'calls_today': api.calls_today,
                'calls_per_day': api.calls_per_day,
                'calls_this_minute': api.calls_this_minute,
                'calls_per_minute': api.calls_per_minute,
                'last_call': datetime.fromtimestamp(api.last_call).isoformat() if api.last_call > 0 else None,
                'available': api.api_key and api.api_key != 'coming_soon',
                'rate_limit_ok': self._check_rate_limits(api)
            }
        return status
    
    def test_all_apis(self) -> Dict[str, bool]:
        """Teste alle APIs mit einem einfachen Call"""
        results = {}
        test_symbol = 'AAPL'
        
        for name, api in self.apis.items():
            if api.api_key and api.api_key != 'coming_soon':
                try:
                    data = self._fetch_data(api, test_symbol, 'price')
                    results[name] = data is not None
                except:
                    results[name] = False
            else:
                results[name] = False
        
        return results
