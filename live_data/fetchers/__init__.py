"""
Data Fetchers Module

This module contains fetchers for different data sources:
- Yahoo Finance: Stocks, ETFs, indices
- SNB (Swiss National Bank): Swiss Franc exchange rates
- CoinGecko: Cryptocurrency data
- IEX Cloud: Professional market data
- SIX Swiss Exchange: Swiss market data
"""

from .base_fetcher import BaseFetcher
from .yahoo_fetcher import YahooFetcher
from .snb_fetcher import SNBFetcher
from .coingecko_fetcher import CoinGeckoFetcher

__all__ = ['BaseFetcher', 'YahooFetcher', 'SNBFetcher', 'CoinGeckoFetcher']
