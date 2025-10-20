"""
Data Providers Module

This module contains the core data provider classes that decide between
live and simulated data sources based on availability and quality.
"""

from .data_provider import DataProvider
from .fallback_provider import FallbackProvider

__all__ = ['DataProvider', 'FallbackProvider']
