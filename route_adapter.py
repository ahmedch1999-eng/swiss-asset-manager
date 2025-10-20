"""
Adapter für die Flask-App, um die direkten Datenfunktionen aus data_services.py
mit den Flask-Routen zu verbinden.

Diese verbesserte Version enthält:
1. Umfassende Fehlerbehandlung für alle Route-Aufrufe
2. Konsistente Rückgabeformate mit Statuscodes
3. Detailliertes Logging für Debugging
4. Trennung von Daten- und Präsentationsschicht
"""

from flask import jsonify
import logging
import data_services
from datetime import datetime
import traceback

# Logger konfigurieren
logger = logging.getLogger("route_adapter")

def init_data_services(swiss_bank_portfolios, market_cycles, scenarios, swiss_stocks, indices):
    """
    Initialisiert den Data Service mit den Anfangsdaten aus app.py
    
    :param swiss_bank_portfolios: Dict mit Bank-Portfolio-Daten
    :param market_cycles: Dict mit Marktzyklus-Daten
    :param scenarios: Dict mit Szenario-Daten
    :param swiss_stocks: Dict mit Schweizer Aktien-Symbolen
    :param indices: Dict mit Index-Symbolen
    :return: True bei Erfolg, False bei Fehler
    """
    try:
        logger.info("Initialisiere Datenservices und Scheduler...")
        
        # Initialisiere die Datenstrukturen in data_services
        data_services.initialize_data(swiss_bank_portfolios, market_cycles, scenarios)
        
        # Initialisiere Referenzdaten im Scheduler
        from data_refresh_scheduler import initialize_reference_data
        initialize_reference_data(swiss_stocks, indices)
        
        logger.info("Datenservices und Scheduler erfolgreich initialisiert")
        return True
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Datenservices: {e}", exc_info=True)
        return False

def route_get_live_data(symbol, swiss_stocks, indices):
    """
    Flask-Route für get_live_data mit Fehlerbehandlung
    
    :param symbol: Aktien-/Index-Symbol
    :param swiss_stocks: Dict mit Schweizer Aktien-Symbolen
    :param indices: Dict mit Index-Symbolen
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.debug(f"Abfrage von Live-Daten für Symbol: {symbol}")
        start_time = datetime.now()
        
        result = data_services.get_live_data(symbol, swiss_stocks, indices)
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.debug(f"Live-Daten für {symbol} in {process_time:.1f}ms abgerufen")
        
        return jsonify({
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Fehler bei Live-Daten für {symbol}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def route_refresh_all_markets(symbols_to_fetch, swiss_stocks, indices):
    """
    Flask-Route für refresh_all_markets mit Fehlerbehandlung
    
    :param symbols_to_fetch: Dict mit Namen als Schlüssel und Symbolen als Werte
    :param swiss_stocks: Dict mit Schweizer Aktien-Symbolen
    :param indices: Dict mit Index-Symbolen
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.info(f"Aktualisiere alle Marktdaten für {len(symbols_to_fetch)} Symbole")
        start_time = datetime.now()
        
        result = data_services.refresh_all_markets(symbols_to_fetch, swiss_stocks, indices)
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Marktdaten in {process_time:.1f}ms aktualisiert")
        
        if result.get("success", False):
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Fehler bei Marktdaten-Update: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "exception_type": type(e).__name__,
            "stack_trace": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }), 500

def route_update_bank_portfolios():
    """
    Flask-Route für update_bank_portfolios mit Fehlerbehandlung
    
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.info("Aktualisiere Bank-Portfolios")
        start_time = datetime.now()
        
        result = data_services.update_bank_portfolios()
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Bank-Portfolios in {process_time:.1f}ms aktualisiert")
        
        if result.get("success", False):
            return jsonify({
                "success": True,
                "portfolios": data_services.SWISS_BANK_PORTFOLIOS,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Unbekannter Fehler"),
                "portfolios": data_services.SWISS_BANK_PORTFOLIOS,
                "timestamp": datetime.now().isoformat()
            }), 500
    except Exception as e:
        logger.error(f"Fehler bei Portfolio-Update: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "exception_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }), 500

def route_update_market_cycles():
    """
    Flask-Route für update_market_cycles mit Fehlerbehandlung
    
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.info("Aktualisiere Marktzyklen")
        start_time = datetime.now()
        
        result = data_services.update_market_cycles()
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Marktzyklen in {process_time:.1f}ms aktualisiert")
        
        if result.get("success", False):
            return jsonify({
                "success": True,
                "cycles": data_services.MARKET_CYCLES,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Unbekannter Fehler"),
                "cycles": data_services.MARKET_CYCLES,
                "timestamp": datetime.now().isoformat()
            }), 500
    except Exception as e:
        logger.error(f"Fehler bei Marktzyklus-Update: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def route_get_news():
    """
    Flask-Route für get_news mit Fehlerbehandlung
    
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.debug("Hole Nachrichtendaten")
        start_time = datetime.now()
        
        news_items = data_services.get_news()
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.debug(f"{len(news_items)} Nachrichtenartikel in {process_time:.1f}ms abgerufen")
        
        return jsonify({
            "success": True,
            "news": news_items,
            "count": len(news_items),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Fehler beim Nachrichten-Abruf: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "news": [],
            "timestamp": datetime.now().isoformat()
        }), 500

def route_get_benchmark_data():
    """
    Flask-Route für get_benchmark_data mit Fehlerbehandlung
    
    :return: Flask-Response mit JSON-Daten
    """
    try:
        logger.debug("Hole Benchmark-Daten")
        start_time = datetime.now()
        
        result = data_services.get_benchmark_data()
        
        # Verarbeitungszeit messen
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.debug(f"Benchmark-Daten in {process_time:.1f}ms abgerufen")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Fehler beim Benchmark-Daten-Abruf: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": {},
            "sources": {},
            "is_live": False,
            "timestamp": datetime.now().isoformat()
        }), 500

def get_swiss_bank_portfolios():
    """
    Gibt die aktuellen Bank-Portfolios zurück
    
    :return: Dict mit Bank-Portfolio-Daten
    """
    try:
        return {
            "success": True,
            "data": data_services.SWISS_BANK_PORTFOLIOS,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Fehler beim Abruf der Bank-Portfolios: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "timestamp": datetime.now().isoformat()
        }

def get_market_cycles():
    """
    Gibt die aktuellen Marktzyklen zurück
    
    :return: Dict mit Marktzyklus-Daten
    """
    try:
        return {
            "success": True,
            "data": data_services.MARKET_CYCLES,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Fehler beim Abruf der Marktzyklen: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "timestamp": datetime.now().isoformat()
        }

def get_scenarios():
    """
    Gibt die aktuellen Szenarien zurück
    
    :return: Dict mit Szenario-Daten
    """
    try:
        return {
            "success": True,
            "data": data_services.SCENARIOS,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Fehler beim Abruf der Szenarien: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {},
            "timestamp": datetime.now().isoformat()
        }

def get_system_status():
    """
    Gibt Statusinformationen über die Datenservices zurück
    
    :return: Dict mit Statusinformationen
    """
    try:
        # Cache-Status aus data_services abrufen
        cache = data_services.cache
        
        # Updates formatieren
        last_updates = {}
        for key in cache:
            if key.startswith("last_") and key.endswith("_update") and cache[key]:
                component = key.replace("last_", "").replace("_update", "")
                last_updates[component] = cache[key].strftime("%Y-%m-%d %H:%M:%S")
        
        # Update-Status sammeln
        update_status = {}
        for component, status in cache["update_in_progress"].items():
            update_status[component] = "running" if status else "idle"
        
        # Erfolgs- und Fehlerstatistiken
        success_stats = cache["update_success_count"]
        error_stats = cache["update_error_count"]
        
        # Status zusammenstellen
        return {
            "success": True,
            "status": {
                "last_updates": last_updates,
                "update_status": update_status,
                "success_counts": success_stats,
                "error_counts": error_stats,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except Exception as e:
        logger.error(f"Fehler beim Abruf des Systemstatus: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "status": {
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }