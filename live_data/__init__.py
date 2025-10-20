"""
Swiss Asset Pro - Live Data Integration Module

This module provides real-time market data integration with fallback to simulation.
It implements a comprehensive data pipeline that fetches live data from multiple
trusted sources and falls back to simulated data when live sources are unavailable.

Architecture:
- DataIngestService: Fetches real data from various sources
- DataValidator: Validates data quality and plausibility
- DataStore: Stores data in PostgreSQL/TimescaleDB
- DataProvider: Decides between live and simulated data
- FallbackProvider: Provides simulated data as backup

Data Sources:
- Stocks/ETFs: Yahoo Finance, IEX Cloud, SIX Swiss Exchange
- FX Rates: SNB (Swiss National Bank), ECB, FED
- Crypto: CoinGecko, CoinMarketCap
- Company Data: EDGAR, Company IR websites
"""

from .providers.data_provider import DataProvider
from .providers.fallback_provider import FallbackProvider
from .storage.data_store import DataStore
from .validators.data_validator import DataValidator
from .fetchers.yahoo_fetcher import YahooFetcher
from .fetchers.snb_fetcher import SNBFetcher
from .fetchers.coingecko_fetcher import CoinGeckoFetcher

__version__ = "1.0.0"
__author__ = "Swiss Asset Pro Team"

__all__ = [
    'DataProvider',
    'FallbackProvider', 
    'DataStore',
    'DataValidator',
    'YahooFetcher',
    'SNBFetcher',
    'CoinGeckoFetcher'
]
