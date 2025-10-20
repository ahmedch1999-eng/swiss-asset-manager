"""
Swiss Asset Manager - Optimierte Datenabfrage
---------------------------------------------
Lädt nur die Daten, die für das aktuelle Portfolio benötigt werden.
"""

import logging
import os
import time
import json
import threading
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio_data")

# Sicherstellen, dass das Cache-Verzeichnis existiert
if not os.path.exists('cache'):
    os.makedirs('cache')

class PortfolioDataLoader:
    """Lädt nur die Daten, die für das aktuelle Portfolio benötigt werden"""
    
    def __init__(self):
        self.cache_dir = "cache"
        self.cache_duration = 3600  # 1 Stunde Cache-Dauer
        self.lock = threading.Lock()
        self.portfolio_assets = set()
        self.loading_status = "idle"
        self.last_update = None
    
    def register_portfolio_assets(self, assets):
        """Registriert Assets aus dem Portfolio für das Laden"""
        with self.lock:
            self.portfolio_assets.update(assets)
            logger.info(f"Portfolio Assets aktualisiert: {len(self.portfolio_assets)} Assets")
    
    def clear_portfolio_assets(self):
        """Löscht alle registrierten Portfolio Assets"""
        with self.lock:
            self.portfolio_assets.clear()
            logger.info("Portfolio Assets zurückgesetzt")
    
    def get_loading_status(self):
        """Gibt den aktuellen Ladestatus zurück"""
        return {
            "status": self.loading_status,
            "assets_count": len(self.portfolio_assets),
            "last_update": self.last_update
        }
    
    def load_data_for_portfolio(self):
        """Lädt nur die Daten für die registrierten Portfolio Assets"""
        if not self.portfolio_assets:
            logger.info("Kein Portfolio vorhanden - überspringe Datenladung")
            return {"status": "no_portfolio", "message": "Kein Portfolio vorhanden"}
        
        with self.lock:
            self.loading_status = "loading"
            assets_to_load = list(self.portfolio_assets)
        
        logger.info(f"Starte Laden von {len(assets_to_load)} Portfolio Assets...")
        results = {"success": [], "error": []}
        
        for asset in assets_to_load:
            try:
                # Prüfe Cache zuerst
                cache_file = os.path.join(self.cache_dir, f"market_data_{asset}.cache")
                if os.path.exists(cache_file):
                    cache_time = os.path.getmtime(cache_file)
                    if time.time() - cache_time < self.cache_duration:
                        logger.info(f"Verwende Cache für {asset}")
                        results["success"].append(asset)
                        continue
                
                # Lade Daten von Yahoo Finance
                logger.info(f"Lade Daten für {asset}...")
                ticker = yf.Ticker(asset)
                hist = ticker.history(period="1mo")
                if hist.empty:
                    logger.warning(f"Keine Daten für {asset} gefunden")
                    results["error"].append(asset)
                    continue
                
                # Speichere in Cache
                with open(cache_file, 'w') as f:
                    hist.to_json(f)
                
                logger.info(f"Daten für {asset} erfolgreich geladen")
                results["success"].append(asset)
                
            except Exception as e:
                logger.error(f"Fehler beim Laden von {asset}: {e}")
                results["error"].append(asset)
        
        with self.lock:
            self.loading_status = "completed"
            self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Datenladung abgeschlossen: {len(results['success'])} erfolgreich, {len(results['error'])} fehlgeschlagen")
        return {
            "status": "completed",
            "success_count": len(results["success"]),
            "error_count": len(results["error"]),
            "timestamp": self.last_update
        }
    
    def get_asset_data(self, asset):
        """Holt Daten für ein bestimmtes Asset"""
        cache_file = os.path.join(self.cache_dir, f"market_data_{asset}.cache")
        
        # Wenn nicht im Cache oder Cache abgelaufen, lade neu
        if not os.path.exists(cache_file) or time.time() - os.path.getmtime(cache_file) > self.cache_duration:
            try:
                logger.info(f"Lade aktuelle Daten für {asset}...")
                ticker = yf.Ticker(asset)
                hist = ticker.history(period="1mo")
                if hist.empty:
                    logger.warning(f"Keine Daten für {asset} gefunden")
                    return None
                
                # Speichere in Cache
                with open(cache_file, 'w') as f:
                    hist.to_json(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden von {asset}: {e}")
                if os.path.exists(cache_file):
                    # Verwende alten Cache im Notfall
                    pass
                else:
                    return None
        
        # Lese aus Cache
        try:
            with open(cache_file, 'r') as f:
                data = pd.read_json(f)
            return data
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Cache für {asset}: {e}")
            return None
    
    def get_portfolio_performance(self, portfolio):
        """Berechnet die Performance für ein Portfolio"""
        if not portfolio or not isinstance(portfolio, dict):
            return {"error": "Kein gültiges Portfolio"}
        
        total_value = 0
        total_change = 0
        assets_data = []
        
        for asset, weight in portfolio.items():
            data = self.get_asset_data(asset)
            if data is None or data.empty:
                assets_data.append({
                    "asset": asset,
                    "weight": weight,
                    "price": 0,
                    "change": 0,
                    "status": "error"
                })
                continue
            
            # Berechne aktuelle Werte
            current_price = data['Close'].iloc[-1]
            previous_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
            change_pct = ((current_price - previous_price) / previous_price) * 100 if previous_price > 0 else 0
            
            weighted_value = weight * current_price
            weighted_change = weight * change_pct
            
            total_value += weighted_value
            total_change += weighted_change
            
            assets_data.append({
                "asset": asset,
                "weight": weight,
                "price": round(current_price, 2),
                "change": round(change_pct, 2),
                "status": "success"
            })
        
        return {
            "total_value": round(total_value, 2),
            "total_change": round(total_change, 2),
            "assets": assets_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Singleton-Instanz
portfolio_loader = PortfolioDataLoader()

def get_loader():
    """Gibt die Singleton-Instanz zurück"""
    return portfolio_loader

# Exportiere die Hauptfunktion für die Integration
def load_portfolio_data(assets):
    """Lädt Daten für die angegebenen Assets"""
    loader = get_loader()
    loader.register_portfolio_assets(assets)
    return loader.load_data_for_portfolio()