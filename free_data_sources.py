"""
Free Data Sources - Öffentliche Endpunkte ohne API-Keys
=========================================================

Diese Datenquellen sind kostenlos und benötigen keine API-Keys.
Perfekt für Development und ungefähre Daten.

Für Production mit präzisen Daten: API-Keys in .env setzen
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('free_data_sources')

class FreeDataSources:
    """Kostenlose Datenquellen ohne API-Keys"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    # =========================================================================
    # AKTIEN - Yahoo Finance Query API (Öffentlich)
    # =========================================================================
    
    def get_stock_data_yahoo_query(self, symbol):
        """
        Yahoo Finance Query API - Öffentlicher Endpunkt
        Beispiel: https://query1.finance.yahoo.com/v8/finance/chart/MSFT?interval=1d&range=1mo
        """
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'interval': '1d',
                'range': '1mo'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse Yahoo Finance Response
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                timestamps = result.get('timestamp', [])
                quote = result.get('indicators', {}).get('quote', [{}])[0]
                
                if timestamps and quote.get('close'):
                    current_price = quote['close'][-1]
                    prev_price = quote['close'][-2] if len(quote['close']) > 1 else current_price
                    
                    return {
                        'symbol': symbol,
                        'price': round(float(current_price), 2),
                        'change': round(((current_price - prev_price) / prev_price * 100), 2) if prev_price else 0,
                        'currency': meta.get('currency', 'USD'),
                        'volume': int(quote.get('volume', [0])[-1]) if quote.get('volume') else 0,
                        'timestamp': timestamps[-1],
                        'source': 'Yahoo Finance Query API (Free)',
                        'data_quality': 'approximate'
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Yahoo Query API failed for {symbol}: {e}")
            return None
    
    def get_stock_data_stooq(self, symbol):
        """
        Stooq.pl - Kostenlose Börsendaten
        Beispiel: https://stooq.pl/q/d/l/?s=nvda.us&i=d
        """
        try:
            # Stooq Symbol Format: nvda.us für US-Aktien
            stooq_symbol = symbol.lower().replace('.', '_')
            if not '.' in symbol:
                stooq_symbol = f"{symbol.lower()}.us"
            
            url = "https://stooq.pl/q/d/l/"
            params = {
                's': stooq_symbol,
                'i': 'd'  # daily data
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse CSV Response
            lines = response.text.strip().split('\n')
            if len(lines) > 2:  # Header + at least 2 data rows
                # Last two lines for current and previous price
                last_line = lines[-1].split(',')
                prev_line = lines[-2].split(',') if len(lines) > 2 else last_line
                
                if len(last_line) >= 5:
                    current_price = float(last_line[4])  # Close price
                    prev_price = float(prev_line[4]) if len(prev_line) >= 5 else current_price
                    
                    return {
                        'symbol': symbol,
                        'price': round(current_price, 2),
                        'change': round(((current_price - prev_price) / prev_price * 100), 2),
                        'volume': int(float(last_line[5])) if len(last_line) > 5 else 0,
                        'source': 'Stooq.pl (Free)',
                        'data_quality': 'approximate'
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Stooq failed for {symbol}: {e}")
            return None
    
    # =========================================================================
    # FOREX (FX) - Europäische Zentralbank
    # =========================================================================
    
    def get_fx_data_ecb(self, currency_pair='EURUSD'):
        """
        ECB Daily Exchange Rates - Öffentlich
        Beispiel: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml
        """
        try:
            url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # ECB namespace
            ns = {'gesmes': 'http://www.gesmes.org/xml/2002-09-01',
                  'ecb': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            
            # Extract currency (z.B. USD aus EURUSD)
            target_currency = currency_pair.replace('EUR', '')
            
            for cube in root.findall('.//ecb:Cube[@currency]', ns):
                currency = cube.get('currency')
                rate = cube.get('rate')
                
                if currency == target_currency:
                    return {
                        'symbol': currency_pair,
                        'price': round(float(rate), 4),
                        'change': 0,  # ECB liefert nur aktuellen Wert
                        'source': 'European Central Bank (Free)',
                        'data_quality': 'official'
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"ECB failed for {currency_pair}: {e}")
            return None
    
    # =========================================================================
    # KRYPTO - CoinGecko & Binance
    # =========================================================================
    
    def get_crypto_data_coingecko(self, crypto_symbol='bitcoin'):
        """
        CoinGecko Public API - Kostenlos ohne Key
        Beispiel: https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd
        """
        try:
            # Mapping: BTC -> bitcoin, ETH -> ethereum
            crypto_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'BTC-USD': 'bitcoin',
                'ETH-USD': 'ethereum'
            }
            
            crypto_id = crypto_map.get(crypto_symbol.upper(), crypto_symbol.lower())
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if crypto_id in data:
                price_data = data[crypto_id]
                return {
                    'symbol': crypto_symbol,
                    'price': round(float(price_data['usd']), 2),
                    'change': round(float(price_data.get('usd_24h_change', 0)), 2),
                    'source': 'CoinGecko (Free)',
                    'data_quality': 'approximate'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"CoinGecko failed for {crypto_symbol}: {e}")
            return None
    
    def get_crypto_data_binance(self, symbol='BTCUSDT'):
        """
        Binance Public API - Kostenlos
        Beispiel: https://api.binance.com/api/v3/ticker/price
        """
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': symbol.upper().replace('-', '')}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'lastPrice' in data:
                return {
                    'symbol': symbol,
                    'price': round(float(data['lastPrice']), 2),
                    'change': round(float(data.get('priceChangePercent', 0)), 2),
                    'volume': float(data.get('volume', 0)),
                    'source': 'Binance Public API (Free)',
                    'data_quality': 'real-time'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Binance failed for {symbol}: {e}")
            return None
    
    # =========================================================================
    # MAKRO-DATEN - World Bank & Eurostat
    # =========================================================================
    
    def get_gdp_data_worldbank(self, country_code='DEU'):
        """
        World Bank Open Data API - Kostenlos
        Beispiel: https://api.worldbank.org/v2/country/deu/indicator/NY.GDP.MKTP.CD?format=json
        """
        try:
            url = f"https://api.worldbank.org/v2/country/{country_code.lower()}/indicator/NY.GDP.MKTP.CD"
            params = {
                'format': 'json',
                'per_page': 5,
                'date': f"{datetime.now().year-2}:{datetime.now().year}"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if len(data) > 1 and data[1]:
                latest = data[1][0]
                return {
                    'country': country_code,
                    'indicator': 'GDP',
                    'value': latest.get('value'),
                    'year': latest.get('date'),
                    'unit': 'USD',
                    'source': 'World Bank (Free)',
                    'data_quality': 'official'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"World Bank failed for {country_code}: {e}")
            return None
    
    def get_eurostat_data(self, indicator='tec00115'):
        """
        Eurostat Open Data API - Kostenlos
        Beispiel: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tec00115
        """
        try:
            url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{indicator}"
            params = {'format': 'JSON', 'lang': 'EN'}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Eurostat JSON ist komplex - vereinfachte Extraktion
            return {
                'indicator': indicator,
                'source': 'Eurostat (Free)',
                'data_quality': 'official',
                'raw_data': data  # Für weitere Verarbeitung
            }
            
        except Exception as e:
            logger.warning(f"Eurostat failed for {indicator}: {e}")
            return None
    
    # =========================================================================
    # INTELLIGENTE MULTI-SOURCE METHODE
    # =========================================================================
    
    def get_market_data(self, symbol):
        """
        Intelligente Datenabfrage - versucht verschiedene Quellen
        
        Args:
            symbol: Ticker-Symbol (AAPL, BTC-USD, EURUSD, etc.)
        
        Returns:
            dict mit Marktdaten oder None
        """
        # Erkenne Asset-Typ
        symbol_upper = symbol.upper()
        
        # 1. KRYPTO
        if any(x in symbol_upper for x in ['BTC', 'ETH', 'USDT']):
            # Versuche Binance
            data = self.get_crypto_data_binance(symbol)
            if data:
                return data
            
            # Fallback zu CoinGecko
            return self.get_crypto_data_coingecko(symbol)
        
        # 2. FOREX
        elif 'EUR' in symbol_upper or 'USD' in symbol_upper and len(symbol) == 6:
            return self.get_fx_data_ecb(symbol)
        
        # 3. AKTIEN
        else:
            # Versuche Yahoo Query API
            data = self.get_stock_data_yahoo_query(symbol)
            if data:
                return data
            
            # Fallback zu Stooq
            return self.get_stock_data_stooq(symbol)
        
        return None


# Initialisiere globale Instanz
free_sources = FreeDataSources()
logger.info("✅ Free Data Sources initialisiert (Yahoo, Stooq, ECB, CoinGecko, Binance)")



