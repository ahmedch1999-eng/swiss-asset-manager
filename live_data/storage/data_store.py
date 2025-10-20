"""
Data Store - Handles data persistence and retrieval

This module provides database operations for storing and retrieving
market data, financial statements, and source status information.
Uses SQLite for simplicity, but can be extended to PostgreSQL/TimescaleDB.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class DataStore:
    """
    Data store for market data persistence.
    
    Handles storage and retrieval of:
    - Market prices and volumes
    - Financial statements
    - Source status and reliability
    - Data quality metrics
    """
    
    def __init__(self, db_path: str = 'swiss_asset_manager_live.db'):
        """
        Initialize the data store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Market prices table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        source TEXT NOT NULL,
                        price REAL NOT NULL,
                        change REAL,
                        change_percent REAL,
                        volume INTEGER,
                        market_cap INTEGER,
                        currency TEXT,
                        data_type TEXT DEFAULT 'price',
                        quality_score REAL,
                        raw_data TEXT,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Financial statements table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS financial_statements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        source TEXT NOT NULL,
                        period TEXT NOT NULL,
                        report_type TEXT DEFAULT 'annual',
                        revenue REAL,
                        net_income REAL,
                        total_assets REAL,
                        total_debt REAL,
                        cash REAL,
                        free_cash_flow REAL,
                        quality_score REAL,
                        raw_data TEXT,
                        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Source status table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS source_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_name TEXT NOT NULL,
                        last_fetch TIMESTAMP,
                        success_rate REAL,
                        error_count INTEGER DEFAULT 0,
                        total_requests INTEGER DEFAULT 0,
                        fallback_active BOOLEAN DEFAULT FALSE,
                        trust_score REAL,
                        last_error TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Data quality metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS data_quality_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        source TEXT NOT NULL,
                        quality_score REAL NOT NULL,
                        validation_errors TEXT,
                        data_completeness REAL,
                        timestamp_accuracy BOOLEAN,
                        price_plausibility BOOLEAN,
                        volume_plausibility BOOLEAN,
                        measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_prices_symbol ON market_prices(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_prices_fetched_at ON market_prices(fetched_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_statements_symbol ON financial_statements(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_status_source ON source_status(source_name)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def store_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Store market data in the database.
        
        Args:
            symbol: Market symbol
            data: Market data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO market_prices 
                    (symbol, source, price, change, change_percent, volume, market_cap, 
                     currency, data_type, quality_score, raw_data, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    data.get('source', 'unknown'),
                    data.get('price', 0),
                    data.get('change', 0),
                    data.get('change_percent', 0),
                    data.get('volume', 0),
                    data.get('market_cap', 0),
                    data.get('currency', 'USD'),
                    data.get('data_type', 'price'),
                    data.get('quality_score', 0),
                    json.dumps(data),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.debug(f"Stored market data for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing market data for {symbol}: {str(e)}")
            return False
    
    def get_latest_market_data(self, symbol: str, data_type: str = 'price') -> Optional[Dict[str, Any]]:
        """
        Get the latest market data for a symbol.
        
        Args:
            symbol: Market symbol
            data_type: Type of data
            
        Returns:
            Latest market data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM market_prices 
                    WHERE symbol = ? AND data_type = ?
                    ORDER BY fetched_at DESC 
                    LIMIT 1
                ''', (symbol, data_type))
                
                row = cursor.fetchone()
                if row:
                    # Convert row to dictionary
                    columns = [description[0] for description in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Parse raw_data if present
                    if data.get('raw_data'):
                        try:
                            raw_data = json.loads(data['raw_data'])
                            data.update(raw_data)
                        except json.JSONDecodeError:
                            pass
                    
                    return data
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest market data for {symbol}: {str(e)}")
            return None
    
    def get_historical_market_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical market data for a symbol.
        
        Args:
            symbol: Market symbol
            days: Number of days of historical data
            
        Returns:
            List of historical market data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days)
                
                cursor.execute('''
                    SELECT * FROM market_prices 
                    WHERE symbol = ? AND fetched_at >= ?
                    ORDER BY fetched_at ASC
                ''', (symbol, cutoff_date.isoformat()))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                historical_data = []
                for row in rows:
                    data = dict(zip(columns, row))
                    
                    # Parse raw_data if present
                    if data.get('raw_data'):
                        try:
                            raw_data = json.loads(data['raw_data'])
                            data.update(raw_data)
                        except json.JSONDecodeError:
                            pass
                    
                    historical_data.append(data)
                
                return historical_data
                
        except Exception as e:
            logger.error(f"Error getting historical market data for {symbol}: {str(e)}")
            return []
    
    def store_financial_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Store financial statement data.
        
        Args:
            symbol: Market symbol
            data: Financial data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO financial_statements 
                    (symbol, source, period, report_type, revenue, net_income, 
                     total_assets, total_debt, cash, free_cash_flow, quality_score, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    data.get('source', 'unknown'),
                    data.get('period', ''),
                    data.get('report_type', 'annual'),
                    data.get('revenue', 0),
                    data.get('net_income', 0),
                    data.get('total_assets', 0),
                    data.get('total_debt', 0),
                    data.get('cash', 0),
                    data.get('free_cash_flow', 0),
                    data.get('quality_score', 0),
                    json.dumps(data)
                ))
                
                conn.commit()
                logger.debug(f"Stored financial data for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing financial data for {symbol}: {str(e)}")
            return False
    
    def update_source_status(self, source_name: str, success: bool, error_message: str = None):
        """
        Update source status information.
        
        Args:
            source_name: Name of the data source
            success: Whether the request was successful
            error_message: Error message if request failed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('''
                    SELECT * FROM source_status WHERE source_name = ?
                ''', (source_name,))
                
                row = cursor.fetchone()
                
                if row:
                    # Update existing record
                    columns = [description[0] for description in cursor.description]
                    current_data = dict(zip(columns, row))
                    
                    total_requests = current_data['total_requests'] + 1
                    error_count = current_data['error_count'] + (0 if success else 1)
                    success_rate = ((total_requests - error_count) / total_requests) * 100
                    
                    cursor.execute('''
                        UPDATE source_status 
                        SET last_fetch = ?, success_rate = ?, error_count = ?, 
                            total_requests = ?, last_error = ?, updated_at = ?
                        WHERE source_name = ?
                    ''', (
                        datetime.now().isoformat() if success else current_data['last_fetch'],
                        success_rate,
                        error_count,
                        total_requests,
                        error_message if not success else None,
                        datetime.now().isoformat(),
                        source_name
                    ))
                else:
                    # Insert new record
                    success_rate = 100.0 if success else 0.0
                    cursor.execute('''
                        INSERT INTO source_status 
                        (source_name, last_fetch, success_rate, error_count, total_requests, last_error)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        source_name,
                        datetime.now().isoformat() if success else None,
                        success_rate,
                        0 if success else 1,
                        1,
                        error_message if not success else None
                    ))
                
                conn.commit()
                logger.debug(f"Updated source status for {source_name}")
                
        except Exception as e:
            logger.error(f"Error updating source status for {source_name}: {str(e)}")
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all data sources."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM source_status ORDER BY source_name
                ''')
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                sources = {}
                for row in rows:
                    data = dict(zip(columns, row))
                    sources[data['source_name']] = data
                
                return sources
                
        except Exception as e:
            logger.error(f"Error getting source status: {str(e)}")
            return {}
    
    def store_quality_metrics(self, symbol: str, source: str, quality_data: Dict[str, Any]):
        """
        Store data quality metrics.
        
        Args:
            symbol: Market symbol
            source: Data source
            quality_data: Quality metrics data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO data_quality_metrics 
                    (symbol, source, quality_score, validation_errors, data_completeness,
                     timestamp_accuracy, price_plausibility, volume_plausibility)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    source,
                    quality_data.get('quality_score', 0),
                    json.dumps(quality_data.get('validation_errors', [])),
                    quality_data.get('data_completeness', 0),
                    quality_data.get('timestamp_accuracy', False),
                    quality_data.get('price_plausibility', False),
                    quality_data.get('volume_plausibility', False)
                ))
                
                conn.commit()
                logger.debug(f"Stored quality metrics for {symbol} from {source}")
                
        except Exception as e:
            logger.error(f"Error storing quality metrics for {symbol}: {str(e)}")
    
    def cleanup_old_data(self, days: int = 30):
        """
        Clean up old data to prevent database bloat.
        
        Args:
            days: Number of days of data to keep
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Clean up old market prices
                cursor.execute('''
                    DELETE FROM market_prices WHERE fetched_at < ?
                ''', (cutoff_date.isoformat(),))
                
                # Clean up old quality metrics
                cursor.execute('''
                    DELETE FROM data_quality_metrics WHERE measured_at < ?
                ''', (cutoff_date.isoformat(),))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count records in each table
                tables = ['market_prices', 'financial_statements', 'source_status', 'data_quality_metrics']
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Get database file size
                if os.path.exists(self.db_path):
                    stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}
