"""
Fallback Provider - Provides simulated data when live sources fail

This module contains the existing simulation logic, now organized as a fallback provider.
It maintains all the original simulation capabilities while being integrated into the
new live data architecture.
"""

import time
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import logging
logger = logging.getLogger(__name__)

class FallbackProvider:
    """
    Fallback data provider that generates realistic simulated market data.
    
    This class encapsulates all the existing simulation logic and provides
    it as a fallback when live data sources are unavailable.
    """
    
    def __init__(self):
        # Asset class configurations for realistic simulation
        self.asset_classes = {
            'stocks': {'base': 100, 'volatility': 0.02, 'trend': 0.0001},
            'crypto': {'base': 50, 'volatility': 0.05, 'trend': 0.0002},
            'commodities': {'base': 150, 'volatility': 0.03, 'trend': 0.0001},
            'bonds': {'base': 100, 'volatility': 0.01, 'trend': 0.00005},
            'indices': {'base': 3000, 'volatility': 0.015, 'trend': 0.0001},
            'fx': {'base': 1.0, 'volatility': 0.01, 'trend': 0.00005}
        }
        
        # Symbol classifications
        self.crypto_symbols = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD', 'UNI-USD']
        self.commodity_symbols = ['GC=F', 'SI=F', 'CL=F', 'PL=F', 'HG=F', 'NG=F']
        self.bond_symbols = ['BND', 'AGG', 'LQD', 'HYG', 'TLT', 'IEF']
        self.fx_symbols = ['EURCHF=X', 'USDCHF=X', 'EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
        
        # Swiss-specific symbols
        self.swiss_stocks = ['NESN.SW', 'NOVN.SW', 'ROG.SW', 'UBSG.SW', 'ZURN.SW']
        self.swiss_indices = ['^SSMI', '^SLI', '^SPI']
    
    def get_simulated_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Generate simulated market data for a symbol.
        
        Args:
            symbol: Market symbol
            data_type: Type of data to generate ('price', 'volume', 'financials')
            
        Returns:
            Dict containing simulated data
        """
        try:
            if data_type == 'price':
                return self._generate_price_data(symbol)
            elif data_type == 'volume':
                return self._generate_volume_data(symbol)
            elif data_type == 'financials':
                return self._generate_financial_data(symbol)
            else:
                return self._generate_price_data(symbol)  # Default to price data
                
        except Exception as e:
            logger.error(f"Error generating simulated data for {symbol}: {str(e)}")
            return None
    
    def _generate_price_data(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic price data for a symbol."""
        # Determine asset class
        asset_class = self._classify_symbol(symbol)
        config = self.asset_classes[asset_class]
        
        # Generate realistic price movement
        base_price = config['base']
        volatility = config['volatility']
        trend = config['trend']
        
        # Add some randomness based on symbol
        symbol_hash = hash(symbol) % 1000
        base_price += (symbol_hash - 500) * 0.1
        
        # Generate price with trend and volatility
        current_time = time.time()
        time_factor = (current_time % 86400) / 86400  # Daily cycle
        
        # Market hours simulation (higher volatility during trading hours)
        if 9 <= (current_time % 86400) / 3600 <= 16:
            volatility *= 1.5
        
        # Generate price using geometric Brownian motion
        dt = 1.0 / 365  # Daily time step
        drift = trend * dt
        shock = volatility * np.sqrt(dt) * np.random.normal()
        
        # Apply some mean reversion
        mean_reversion = 0.1 * (base_price - base_price) * dt
        
        price_change = drift + shock - mean_reversion
        current_price = base_price * (1 + price_change)
        
        # Ensure positive price
        current_price = max(current_price, base_price * 0.1)
        
        # Calculate change from previous close
        previous_close = current_price / (1 + price_change)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        # Generate additional market data
        volume = self._generate_volume(symbol, current_price)
        market_cap = self._generate_market_cap(symbol, current_price)
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'previous_close': round(previous_close, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': volume,
            'market_cap': market_cap,
            'currency': self._get_currency(symbol),
            'timestamp': datetime.now().isoformat(),
            'source': 'simulation',
            'confidence_score': 30,
            'data_quality': 'simulated'
        }
    
    def _generate_volume_data(self, symbol: str) -> Dict[str, Any]:
        """Generate volume data for a symbol."""
        price_data = self._generate_price_data(symbol)
        volume = self._generate_volume(symbol, price_data['price'])
        
        return {
            'symbol': symbol,
            'volume': volume,
            'avg_volume': volume * random.uniform(0.8, 1.2),
            'timestamp': datetime.now().isoformat(),
            'source': 'simulation'
        }
    
    def _generate_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Generate financial statement data for a symbol."""
        # This would generate realistic financial metrics
        # For now, return basic structure
        return {
            'symbol': symbol,
            'revenue': random.uniform(1000000, 100000000),
            'net_income': random.uniform(100000, 10000000),
            'total_assets': random.uniform(5000000, 500000000),
            'debt': random.uniform(1000000, 100000000),
            'cash': random.uniform(500000, 50000000),
            'timestamp': datetime.now().isoformat(),
            'source': 'simulation'
        }
    
    def _classify_symbol(self, symbol: str) -> str:
        """Classify a symbol into an asset class."""
        symbol_upper = symbol.upper()
        
        if symbol_upper in self.crypto_symbols:
            return 'crypto'
        elif symbol_upper in self.commodity_symbols:
            return 'commodities'
        elif symbol_upper in self.bond_symbols:
            return 'bonds'
        elif symbol_upper in self.fx_symbols:
            return 'fx'
        elif symbol_upper.startswith('^'):
            return 'indices'
        elif symbol_upper.endswith('.SW') or symbol_upper in self.swiss_stocks:
            return 'stocks'
        else:
            return 'stocks'  # Default classification
    
    def _generate_volume(self, symbol: str, price: float) -> int:
        """Generate realistic trading volume."""
        # Base volume depends on asset class
        asset_class = self._classify_symbol(symbol)
        
        if asset_class == 'crypto':
            base_volume = random.uniform(1000000, 10000000)
        elif asset_class == 'stocks':
            base_volume = random.uniform(100000, 5000000)
        elif asset_class == 'indices':
            base_volume = random.uniform(1000000, 10000000)
        else:
            base_volume = random.uniform(10000, 1000000)
        
        # Add some randomness
        volume = int(base_volume * random.uniform(0.5, 2.0))
        return max(volume, 1000)  # Minimum volume
    
    def _generate_market_cap(self, symbol: str, price: float) -> int:
        """Generate realistic market capitalization."""
        # Estimate shares outstanding based on symbol
        if symbol.upper() in ['AAPL', 'MSFT', 'GOOGL']:
            shares = random.uniform(10000000000, 20000000000)
        elif symbol.upper() in self.swiss_stocks:
            shares = random.uniform(100000000, 1000000000)
        else:
            shares = random.uniform(1000000000, 5000000000)
        
        market_cap = int(price * shares)
        return market_cap
    
    def _get_currency(self, symbol: str) -> str:
        """Determine the currency for a symbol."""
        symbol_upper = symbol.upper()
        
        if symbol_upper.endswith('.SW'):
            return 'CHF'
        elif 'CHF' in symbol_upper:
            return 'CHF'
        elif symbol_upper in self.fx_symbols:
            return 'CHF'  # For FX pairs, use base currency
        else:
            return 'USD'  # Default to USD
    
    def get_available_symbols(self) -> Dict[str, list]:
        """Get list of symbols that can be simulated."""
        return {
            'crypto': self.crypto_symbols,
            'commodities': self.commodity_symbols,
            'bonds': self.bond_symbols,
            'fx': self.fx_symbols,
            'swiss_stocks': self.swiss_stocks,
            'swiss_indices': self.swiss_indices
        }
    
    def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol can be simulated."""
        all_symbols = []
        for symbol_list in self.get_available_symbols().values():
            all_symbols.extend(symbol_list)
        
        return symbol.upper() in all_symbols or symbol.upper().startswith('^')
