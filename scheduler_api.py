"""
Scheduler Health API
Bietet Endpoints zum Überwachen und Steuern des Schedulers
"""

from flask import Blueprint, jsonify, request, current_app
import logging
from scheduler_manager import get_scheduler_manager
from scheduler_config import SchedulerConfig

logger = logging.getLogger(__name__)

# Blueprint für die Scheduler-API
scheduler_api = Blueprint("scheduler_api", __name__, url_prefix="/scheduler")

@scheduler_api.route("/status", methods=["GET"])
def get_status():
    """
    Gibt den Status des Schedulers zurück
    ---
    responses:
      200:
        description: Scheduler status information
    """
    try:
        manager = get_scheduler_manager()
        status = manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Scheduler-Status: {e}", exc_info=True)
        return jsonify({
            "error": "Konnte Status nicht abrufen",
            "details": str(e)
        }), 500

@scheduler_api.route("/health", methods=["GET"])
def health_check():
    """
    Führt einen Gesundheitscheck des Schedulers durch
    ---
    responses:
      200:
        description: Scheduler health information
      500:
        description: Scheduler is unhealthy
    """
    try:
        manager = get_scheduler_manager()
        health = manager.check_health()
        
        if health["healthy"]:
            return jsonify(health), 200
        else:
            # HTTP 500, wenn der Scheduler nicht gesund ist
            return jsonify(health), 500
    except Exception as e:
        logger.error(f"Fehler beim Health-Check: {e}", exc_info=True)
        return jsonify({
            "healthy": False,
            "error": "Konnte Health-Check nicht durchführen",
            "details": str(e)
        }), 500

@scheduler_api.route("/start", methods=["POST"])
def start_scheduler():
    """
    Startet den Scheduler
    ---
    responses:
      200:
        description: Scheduler started successfully
      400:
        description: Scheduler is already running
      500:
        description: Failed to start scheduler
    """
    try:
        manager = get_scheduler_manager()
        
        if manager.is_running:
            return jsonify({
                "success": False,
                "message": "Scheduler läuft bereits"
            }), 400
        
        success = manager.start()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Scheduler erfolgreich gestartet"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Konnte Scheduler nicht starten"
            }), 500
    except Exception as e:
        logger.error(f"Fehler beim Starten des Schedulers: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Fehler beim Starten: {str(e)}"
        }), 500

@scheduler_api.route("/stop", methods=["POST"])
def stop_scheduler():
    """
    Stoppt den Scheduler
    ---
    responses:
      200:
        description: Scheduler stopped successfully
      400:
        description: Scheduler is not running
      500:
        description: Failed to stop scheduler
    """
    try:
        manager = get_scheduler_manager()
        
        if not manager.is_running:
            return jsonify({
                "success": False,
                "message": "Scheduler läuft nicht"
            }), 400
        
        success = manager.stop()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Scheduler erfolgreich gestoppt"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Konnte Scheduler nicht stoppen"
            }), 500
    except Exception as e:
        logger.error(f"Fehler beim Stoppen des Schedulers: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Fehler beim Stoppen: {str(e)}"
        }), 500

@scheduler_api.route("/restart", methods=["POST"])
def restart_scheduler():
    """
    Startet den Scheduler neu
    ---
    responses:
      200:
        description: Scheduler restarted successfully
      500:
        description: Failed to restart scheduler
    """
    try:
        manager = get_scheduler_manager()
        success = manager.restart()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Scheduler erfolgreich neugestartet"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Konnte Scheduler nicht neustarten"
            }), 500
    except Exception as e:
        logger.error(f"Fehler beim Neustarten des Schedulers: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Fehler beim Neustarten: {str(e)}"
        }), 500

@scheduler_api.route("/config", methods=["GET"])
def get_config():
    """
    Gibt die aktuelle Konfiguration des Schedulers zurück
    ---
    responses:
      200:
        description: Current scheduler configuration
    """
    try:
        config = SchedulerConfig.get_config_dict()
        return jsonify(config), 200
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Scheduler-Konfiguration: {e}", exc_info=True)
        return jsonify({
            "error": "Konnte Konfiguration nicht abrufen",
            "details": str(e)
        }), 500

def init_app(app):
    """Initialisiert die Scheduler-API mit der Flask-App"""
    app.register_blueprint(scheduler_api)
    
    # Starte Scheduler automatisch, wenn in Konfiguration aktiviert
    if not hasattr(SchedulerConfig, 'AUTO_START') or SchedulerConfig.SCHEDULER_ENABLED:
        with app.app_context():
            try:
                logger.info("Starte Scheduler automatisch beim App-Start")
                manager = get_scheduler_manager()
                manager.start()
            except Exception as e:
                logger.error(f"Fehler beim automatischen Starten des Schedulers: {e}", exc_info=True)