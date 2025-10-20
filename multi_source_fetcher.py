"""
Multi-Source Data Fetcher für Swiss Asset Pro
Intelligentes System zum Abrufen von Finanzdaten aus mehreren Quellen
"""

import yfinance as yf
import requests
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import time

from api_config import (
    API_PROVIDERS, 
    rate_limiter, 
    normalize_symbol, 
    get_best_provider,
    get_available_providers
)

# ================================================================================================
# MULTI-SOURCE DATA FETCHER
# ================================================================================================

class MultiSourceFetcher:
    """
    Intelligenter Fetcher der mehrere Datenquellen nutzt
    """
    
    def __init__(self):
        self.providers = get_available_providers()
        self.success_count = {provider: 0 for provider in self.providers}
        self.error_count = {provider: 0 for provider in self.providers}
        self.last_errors = {provider: [] for provider in self.providers}
    
    def get_live_price(self, symbol: str) -> Dict:
        """
        Ruft Live-Preis von der besten verfügbaren Quelle ab
        Versucht alle Provider nacheinander bis Erfolg
        """
        
        for provider in self.providers:
            if not rate_limiter.can_make_request(provider):
                print(f"⚠️  {provider} rate limit erreicht, versuche nächsten Provider...")
                continue
            
            try:
                normalized_symbol = normalize_symbol(symbol, provider)
                
                if provider == 'yfinance':
                    result = self._fetch_yfinance(normalized_symbol)
                elif provider == 'alpha_vantage':
                    result = self._fetch_alpha_vantage(normalized_symbol)
                elif provider == 'twelve_data':
                    result = self._fetch_twelve_data(normalized_symbol)
                elif provider == 'finnhub':
                    result = self._fetch_finnhub(normalized_symbol)
                else:
                    continue
                
                if result and 'price' in result:
                    rate_limiter.increment(provider)
                    self.success_count[provider] += 1
                    result['source'] = API_PROVIDERS[provider].name
                    result['provider'] = provider
                    print(f"✅ {symbol}: Erfolgreich von {API_PROVIDERS[provider].name} geladen")
                    return result
                
            except Exception as e:
                self.error_count[provider] += 1
                self.last_errors[provider].append(str(e)[:100])
                if len(self.last_errors[provider]) > 5:
                    self.last_errors[provider] = self.last_errors[provider][-5:]
                print(f"⚠️  {provider} Fehler: {str(e)[:50]}...")
                continue
        
        # Fallback zu simulierten Daten
        print(f"⚠️  Alle Provider fehlgeschlagen für {symbol}, nutze simulierte Daten")
        return self._generate_simulated_data(symbol)
    
    def get_historical_data(self, symbol: str, period: str = '1mo') -> Dict:
        """
        Ruft historische Daten ab
        """
        
        for provider in self.providers:
            if not rate_limiter.can_make_request(provider):
                continue
            
            try:
                normalized_symbol = normalize_symbol(symbol, provider)
                
                if provider == 'yfinance':
                    result = self._fetch_yfinance_history(normalized_symbol, period)
                elif provider == 'alpha_vantage':
                    result = self._fetch_alpha_vantage_history(normalized_symbol)
                elif provider == 'twelve_data':
                    result = self._fetch_twelve_data_history(normalized_symbol, period)
                else:
                    continue
                
                if result and 'data' in result and result['data']:
                    rate_limiter.increment(provider)
                    self.success_count[provider] += 1
                    result['source'] = API_PROVIDERS[provider].name
                    result['provider'] = provider
                    print(f"✅ {symbol}: Historische Daten von {API_PROVIDERS[provider].name}")
                    return result
                
            except Exception as e:
                self.error_count[provider] += 1
                print(f"⚠️  {provider} History Fehler: {str(e)[:50]}...")
                continue
        
        return {'symbol': symbol, 'data': [], 'source': 'error'}
    
    def get_asset_stats(self, symbol: str) -> Dict:
        """
        Berechnet detaillierte Asset-Statistiken
        """
        
        # Versuche historische Daten zu laden
        hist_data = self.get_historical_data(symbol, period='1y')
        
        if not hist_data.get('data'):
            return self._generate_simulated_stats(symbol)
        
        try:
            # Konvertiere zu DataFrame
            df = pd.DataFrame(hist_data['data'])
            df['close'] = pd.to_numeric(df['close'])
            
            # Berechne Returns
            returns = df['close'].pct_change().dropna()
            
            # Statistiken berechnen
            stats = {
                'symbol': symbol,
                'name': symbol,  # Provider-spezifisch
                'price': float(df['close'].iloc[-1]),
                'yearHigh': float(df['close'].max()) if len(df) > 0 else 0,
                'yearLow': float(df['close'].min()) if len(df) > 0 else 0,
                'volatility': float(returns.std() * np.sqrt(252) * 100) if len(returns) > 0 else 20.0,
                'expectedReturn': float(returns.mean() * 252 * 100) if len(returns) > 0 else 8.0,
                'source': hist_data.get('source', 'calculated'),
                'timestamp': time.time()
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Fehler bei Statistik-Berechnung: {str(e)}")
            return self._generate_simulated_stats(symbol)
    
    # ============================================================================
    # PROVIDER-SPEZIFISCHE METHODEN
    # ============================================================================
    
    def _fetch_yfinance(self, symbol: str) -> Dict:
        """Yahoo Finance"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1d')
        
        if hist.empty:
            return {}
        
        current_price = float(hist['Close'].iloc[-1])
        
        if len(hist) > 1:
            prev_price = float(hist['Close'].iloc[-2])
            change = current_price - prev_price
            change_percent = (change / prev_price) * 100
        else:
            change = 0
            change_percent = 0
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'change': round(change, 2),
            'changePercent': round(change_percent, 2),
            'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
            'high': round(float(hist['High'].iloc[-1]), 2) if 'High' in hist else 0,
            'low': round(float(hist['Low'].iloc[-1]), 2) if 'Low' in hist else 0,
            'timestamp': time.time()
        }
    
    def _fetch_alpha_vantage(self, symbol: str) -> Dict:
        """Alpha Vantage API"""
        config = API_PROVIDERS['alpha_vantage']
        
        if config.api_key == 'demo':
            return {}
        
        url = f"{config.base_url}"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': config.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Global Quote' not in data:
            return {}
        
        quote = data['Global Quote']
        
        return {
            'symbol': symbol,
            'price': round(float(quote.get('05. price', 0)), 2),
            'change': round(float(quote.get('09. change', 0)), 2),
            'changePercent': round(float(quote.get('10. change percent', '0').replace('%', '')), 2),
            'volume': int(quote.get('06. volume', 0)),
            'high': round(float(quote.get('03. high', 0)), 2),
            'low': round(float(quote.get('04. low', 0)), 2),
            'timestamp': time.time()
        }
    
    def _fetch_twelve_data(self, symbol: str) -> Dict:
        """Twelve Data API"""
        config = API_PROVIDERS['twelve_data']
        
        if config.api_key == 'demo':
            return {}
        
        url = f"{config.base_url}/quote"
        params = {
            'symbol': symbol,
            'apikey': config.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'close' not in data:
            return {}
        
        return {
            'symbol': symbol,
            'price': round(float(data.get('close', 0)), 2),
            'change': round(float(data.get('change', 0)), 2),
            'changePercent': round(float(data.get('percent_change', 0)), 2),
            'volume': int(data.get('volume', 0)),
            'high': round(float(data.get('high', 0)), 2),
            'low': round(float(data.get('low', 0)), 2),
            'timestamp': time.time()
        }
    
    def _fetch_finnhub(self, symbol: str) -> Dict:
        """Finnhub API"""
        config = API_PROVIDERS['finnhub']
        
        if config.api_key == 'demo':
            return {}
        
        url = f"{config.base_url}/quote"
        params = {
            'symbol': symbol,
            'token': config.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'c' not in data:  # current price
            return {}
        
        current = float(data.get('c', 0))
        prev = float(data.get('pc', current))
        change = current - prev
        change_percent = (change / prev * 100) if prev > 0 else 0
        
        return {
            'symbol': symbol,
            'price': round(current, 2),
            'change': round(change, 2),
            'changePercent': round(change_percent, 2),
            'high': round(float(data.get('h', 0)), 2),
            'low': round(float(data.get('l', 0)), 2),
            'timestamp': time.time()
        }
    
    def _fetch_yfinance_history(self, symbol: str, period: str) -> Dict:
        """Yahoo Finance historische Daten"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return {}
        
        data_points = []
        for date, row in hist.iterrows():
            data_points.append({
                'date': date.strftime('%Y-%m-%d'),
                'close': round(float(row['Close']), 2),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'volume': int(row['Volume'])
            })
        
        return {
            'symbol': symbol,
            'data': data_points,
            'timestamp': time.time()
        }
    
    def _fetch_alpha_vantage_history(self, symbol: str) -> Dict:
        """Alpha Vantage historische Daten"""
        config = API_PROVIDERS['alpha_vantage']
        
        if config.api_key == 'demo':
            return {}
        
        url = f"{config.base_url}"
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': 'compact',  # 100 Tage
            'apikey': config.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Time Series (Daily)' not in data:
            return {}
        
        time_series = data['Time Series (Daily)']
        
        data_points = []
        for date_str, values in sorted(time_series.items()):
            data_points.append({
                'date': date_str,
                'close': round(float(values['4. close']), 2),
                'open': round(float(values['1. open']), 2),
                'high': round(float(values['2. high']), 2),
                'low': round(float(values['3. low']), 2),
                'volume': int(values['5. volume'])
            })
        
        return {
            'symbol': symbol,
            'data': data_points,
            'timestamp': time.time()
        }
    
    def _fetch_twelve_data_history(self, symbol: str, period: str) -> Dict:
        """Twelve Data historische Daten"""
        config = API_PROVIDERS['twelve_data']
        
        if config.api_key == 'demo':
            return {}
        
        # Konvertiere period zu outputsize
        outputsize_map = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
            '6mo': 180, '1y': 365, '2y': 730
        }
        outputsize = outputsize_map.get(period, 30)
        
        url = f"{config.base_url}/time_series"
        params = {
            'symbol': symbol,
            'interval': '1day',
            'outputsize': outputsize,
            'apikey': config.api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'values' not in data:
            return {}
        
        data_points = []
        for item in data['values']:
            data_points.append({
                'date': item.get('datetime', ''),
                'close': round(float(item.get('close', 0)), 2),
                'open': round(float(item.get('open', 0)), 2),
                'high': round(float(item.get('high', 0)), 2),
                'low': round(float(item.get('low', 0)), 2),
                'volume': int(item.get('volume', 0))
            })
        
        return {
            'symbol': symbol,
            'data': data_points,
            'timestamp': time.time()
        }
    
    # ============================================================================
    # FALLBACK & SIMULATION
    # ============================================================================
    
    def _generate_simulated_data(self, symbol: str) -> Dict:
        """Generiert simulierte Daten als Fallback"""
        import random
        
        base_price = 100 + random.random() * 50
        change_pct = (random.random() - 0.5) * 5
        change = base_price * change_pct / 100
        
        return {
            'symbol': symbol,
            'price': round(base_price, 2),
            'change': round(change, 2),
            'changePercent': round(change_pct, 2),
            'volume': int(random.random() * 1000000),
            'high': round(base_price * 1.02, 2),
            'low': round(base_price * 0.98, 2),
            'source': 'simulated',
            'timestamp': time.time()
        }
    
    def _generate_simulated_stats(self, symbol: str) -> Dict:
        """Generiert simulierte Statistiken"""
        import random
        
        return {
            'symbol': symbol,
            'name': symbol,
            'price': round(100 + random.random() * 50, 2),
            'yearHigh': round(150 + random.random() * 30, 2),
            'yearLow': round(80 + random.random() * 20, 2),
            'volatility': round(15 + random.random() * 15, 2),
            'expectedReturn': round(6 + random.random() * 6, 2),
            'source': 'simulated',
            'timestamp': time.time()
        }
    
    # ============================================================================
    # STATISTIKEN & MONITORING
    # ============================================================================
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken über alle Provider zurück"""
        stats = {
            'providers': {},
            'rate_limits': rate_limiter.get_stats(),
            'total_requests': sum(self.success_count.values()),
            'timestamp': time.time()
        }
        
        for provider in self.providers:
            total = self.success_count[provider] + self.error_count[provider]
            success_rate = (self.success_count[provider] / total * 100) if total > 0 else 0
            
            stats['providers'][provider] = {
                'name': API_PROVIDERS[provider].name,
                'success': self.success_count[provider],
                'errors': self.error_count[provider],
                'success_rate': round(success_rate, 1),
                'last_errors': self.last_errors[provider][-3:],  # Letzte 3 Fehler
                'enabled': API_PROVIDERS[provider].enabled
            }
        
        return stats
    
    def print_stats(self):
        """Gibt formatierte Statistiken aus"""
        stats = self.get_stats()
        
        print("\n" + "="*70)
        print("📊 MULTI-SOURCE FETCHER STATISTIKEN")
        print("="*70)
        print(f"Gesamt-Requests: {stats['total_requests']}")
        print("\nProvider-Performance:")
        
        for provider, data in stats['providers'].items():
            if not data['enabled']:
                continue
            
            status = "✅" if data['success_rate'] > 80 else "⚠️" if data['success_rate'] > 50 else "❌"
            print(f"\n{status} {data['name']:20}")
            print(f"   └─ Erfolg: {data['success']:4} | Fehler: {data['errors']:4} | Rate: {data['success_rate']:.1f}%")
            
            if data['last_errors']:
                print(f"   └─ Letzte Fehler: {len(data['last_errors'])}")
        
        print("\n" + "="*70 + "\n")

# ================================================================================================
# GLOBALE INSTANZ
# ================================================================================================

multi_fetcher = MultiSourceFetcher()

# ================================================================================================
# TEST
# ================================================================================================

if __name__ == "__main__":
    print("\n🚀 Multi-Source Fetcher Test\n")
    
    # Test verschiedene Symbole
    test_symbols = ['AAPL', 'MSFT', 'NESN.SW', '^SSMI']
    
    for symbol in test_symbols:
        print(f"\n📈 Teste {symbol}...")
        data = multi_fetcher.get_live_price(symbol)
        if data:
            print(f"   Preis: ${data.get('price', 'N/A')}")
            print(f"   Quelle: {data.get('source', 'N/A')}")
    
    # Statistiken anzeigen
    multi_fetcher.print_stats()

