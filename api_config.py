"""
Multi-Source API Configuration für Swiss Asset Pro
Unterstützt mehrere Finanzmarkt-Daten-Provider mit automatischem Fallback
"""

import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class APIConfig:
    """Konfiguration für einen API-Provider"""
    name: str
    enabled: bool
    api_key: str = ""
    daily_limit: int = 0
    priority: int = 0  # Niedrigere Nummer = höhere Priorität
    base_url: str = ""
    
# ================================================================================================
# API-KEYS (Environment Variables oder hier direkt)
# ================================================================================================

# Alpha Vantage - 500 requests/day kostenlos
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_KEY', 'demo')  # Ersetze 'demo' mit echtem Key

# Twelve Data - 800 requests/day kostenlos  
TWELVE_DATA_API_KEY = os.environ.get('TWELVE_DATA_KEY', 'demo')  # Ersetze 'demo' mit echtem Key

# Finnhub - 60 requests/minute kostenlos
FINNHUB_API_KEY = os.environ.get('FINNHUB_KEY', 'demo')  # Ersetze 'demo' mit echtem Key

# IEX Cloud - Verschiedene Pläne verfügbar
IEX_CLOUD_API_KEY = os.environ.get('IEX_CLOUD_KEY', 'demo')  # Ersetze 'demo' mit echtem Key

# Polygon.io - 5 requests/minute kostenlos
POLYGON_API_KEY = os.environ.get('POLYGON_KEY', 'demo')  # Ersetze 'demo' mit echtem Key

# ================================================================================================
# PROVIDER-KONFIGURATION
# ================================================================================================

API_PROVIDERS: Dict[str, APIConfig] = {
    'yfinance': APIConfig(
        name='Yahoo Finance',
        enabled=True,
        priority=1,  # Erste Wahl (kostenlos, keine Limits)
        daily_limit=999999,
        base_url='https://query1.finance.yahoo.com'
    ),
    
    'alpha_vantage': APIConfig(
        name='Alpha Vantage',
        enabled=True,
        api_key=ALPHA_VANTAGE_API_KEY,
        priority=2,
        daily_limit=500,
        base_url='https://www.alphavantage.co/query'
    ),
    
    'twelve_data': APIConfig(
        name='Twelve Data',
        enabled=True,
        api_key=TWELVE_DATA_API_KEY,
        priority=3,
        daily_limit=800,
        base_url='https://api.twelvedata.com'
    ),
    
    'finnhub': APIConfig(
        name='Finnhub',
        enabled=True,
        api_key=FINNHUB_API_KEY,
        priority=4,
        daily_limit=3600,  # 60/min * 60 min
        base_url='https://finnhub.io/api/v1'
    ),
    
    'iex_cloud': APIConfig(
        name='IEX Cloud',
        enabled=False,  # Nur aktivieren mit echtem Key
        api_key=IEX_CLOUD_API_KEY,
        priority=5,
        daily_limit=100,
        base_url='https://cloud.iexapis.com/stable'
    ),
    
    'polygon': APIConfig(
        name='Polygon.io',
        enabled=False,  # Nur aktivieren mit echtem Key
        api_key=POLYGON_API_KEY,
        priority=6,
        daily_limit=300,  # 5/min * 60 min
        base_url='https://api.polygon.io'
    )
}

# ================================================================================================
# SYMBOL-MAPPING (Jede API nutzt andere Symbol-Formate)
# ================================================================================================

def normalize_symbol(symbol: str, provider: str) -> str:
    """
    Konvertiert Symbole für verschiedene Provider
    
    Beispiele:
    - Yahoo Finance: NESN.SW
    - Alpha Vantage: NESN.SWX oder NESN
    - Twelve Data: NESN:SWX
    """
    
    # Schweizer Aktien
    if symbol.endswith('.SW'):
        base = symbol[:-3]
        if provider == 'alpha_vantage':
            return f"{base}.SWX"
        elif provider == 'twelve_data':
            return f"{base}:SWX"
        elif provider == 'finnhub':
            return f"{base}.SW"
        else:
            return symbol
    
    # US-Indizes
    if symbol.startswith('^'):
        base = symbol[1:]
        if provider in ['alpha_vantage', 'twelve_data']:
            return base
        else:
            return symbol
    
    # Standard (meist US-Aktien)
    return symbol

# ================================================================================================
# RATE LIMITING
# ================================================================================================

class RateLimiter:
    """Verwaltet Rate Limits für jeden Provider"""
    
    def __init__(self):
        self.request_counts: Dict[str, int] = {
            provider: 0 for provider in API_PROVIDERS.keys()
        }
        self.last_reset: Dict[str, float] = {}
    
    def can_make_request(self, provider: str) -> bool:
        """Prüft ob Request erlaubt ist"""
        import time
        
        config = API_PROVIDERS.get(provider)
        if not config:
            return False
        
        # Reset counter nach 24h
        current_time = time.time()
        if provider not in self.last_reset:
            self.last_reset[provider] = current_time
        elif current_time - self.last_reset[provider] > 86400:  # 24 Stunden
            self.request_counts[provider] = 0
            self.last_reset[provider] = current_time
        
        return self.request_counts[provider] < config.daily_limit
    
    def increment(self, provider: str):
        """Erhöht Request-Counter"""
        self.request_counts[provider] += 1
    
    def get_stats(self) -> Dict[str, Dict]:
        """Gibt Statistiken zurück"""
        return {
            provider: {
                'requests_made': count,
                'limit': API_PROVIDERS[provider].daily_limit,
                'remaining': API_PROVIDERS[provider].daily_limit - count,
                'percentage_used': (count / API_PROVIDERS[provider].daily_limit * 100)
            }
            for provider, count in self.request_counts.items()
        }

# ================================================================================================
# PROVIDER-AUSWAHL
# ================================================================================================

def get_available_providers() -> List[str]:
    """Gibt Liste der verfügbaren Provider zurück (sortiert nach Priorität)"""
    available = [
        (provider, config.priority)
        for provider, config in API_PROVIDERS.items()
        if config.enabled
    ]
    available.sort(key=lambda x: x[1])  # Nach Priorität sortieren
    return [provider for provider, _ in available]

def get_best_provider(rate_limiter: RateLimiter) -> str:
    """Gibt den besten verfügbaren Provider zurück"""
    for provider in get_available_providers():
        if rate_limiter.can_make_request(provider):
            return provider
    return 'yfinance'  # Fallback zu Yahoo Finance (keine Limits)

# ================================================================================================
# KOSTENLOSE API-KEYS BEANTRAGEN
# ================================================================================================

API_KEY_URLS = {
    'alpha_vantage': 'https://www.alphavantage.co/support/#api-key',
    'twelve_data': 'https://twelvedata.com/pricing',
    'finnhub': 'https://finnhub.io/register',
    'iex_cloud': 'https://iexcloud.io/cloud-login#/register',
    'polygon': 'https://polygon.io/dashboard/signup'
}

def print_api_key_info():
    """Gibt Informationen zu API-Keys aus"""
    print("\n" + "="*70)
    print("📊 KOSTENLOSE FINANZMARKT-API KEYS")
    print("="*70)
    
    for provider, url in API_KEY_URLS.items():
        config = API_PROVIDERS.get(provider)
        if config:
            status = "✅ Aktiviert" if config.enabled else "⚠️  Deaktiviert"
            has_key = "🔑 Key vorhanden" if config.api_key != 'demo' else "❌ Demo-Key"
            print(f"\n{config.name:20} {status:15} {has_key}")
            print(f"  └─ Limit: {config.daily_limit:,} requests/day")
            print(f"  └─ URL: {url}")
    
    print("\n" + "="*70)
    print("💡 Tipp: Setze echte API-Keys als Environment Variables:")
    print("   export ALPHA_VANTAGE_KEY='dein_key_hier'")
    print("   export TWELVE_DATA_KEY='dein_key_hier'")
    print("="*70 + "\n")

# ================================================================================================
# INITIALISIERUNG
# ================================================================================================

# Globaler Rate Limiter
rate_limiter = RateLimiter()

if __name__ == "__main__":
    print_api_key_info()
    print("\n📈 Verfügbare Provider (nach Priorität):")
    for i, provider in enumerate(get_available_providers(), 1):
        config = API_PROVIDERS[provider]
        print(f"  {i}. {config.name} (Limit: {config.daily_limit:,}/day)")
    
    print(f"\n🎯 Bester Provider: {API_PROVIDERS[get_best_provider(rate_limiter)].name}")

