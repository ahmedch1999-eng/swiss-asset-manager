"""
Scheduler Integration Module
Integriert den Process-Manager und Scheduler-API in die Hauptanwendung
mit verbesserter Fehlerbehandlung und Umgebungserkennung
"""

import os
import logging
import traceback
from flask import Flask, current_app
from scheduler_config import SchedulerConfig

# Logging-Konfiguration
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger = logging.getLogger("scheduler_integration")
logger.setLevel(getattr(logging, SchedulerConfig.LOG_LEVEL))

# Handler für Integration-spezifische Logs
file_handler = logging.FileHandler(os.path.join(log_dir, 'scheduler_integration.log'))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
))
logger.addHandler(file_handler)

# Import for cache system initialization
from scheduler_cache_integration import init_cache_system

# Signal-Handler für graceful Shutdown
import signal
import sys

def signal_handler(sig, frame):
    """Behandelt Shutdown-Signale für sauberes Beenden"""
    logger.info(f"Signal {sig} empfangen, führe sauberes Herunterfahren durch...")
    
    try:
        if hasattr(current_app, '_scheduler_instance'):
            logger.info("Stoppe Scheduler über Signal-Handler...")
            current_app._scheduler_instance.stop()
            
        if hasattr(current_app, '_scheduler_manager'):
            logger.info("Stoppe Scheduler-Manager über Signal-Handler...")
            current_app._scheduler_manager.stop()
    except Exception as e:
        logger.error(f"Fehler beim Herunterfahren des Schedulers: {e}")
    
    # Das Standardverhalten des Signals wiederherstellen und es erneut auslösen
    signal.signal(sig, signal.SIG_DFL)
    sys.exit(0)

# Registriere Signal-Handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def init_scheduler(app):
    """
    Initialisiert den Scheduler und die Scheduler-API in der Flask-Anwendung
    mit verbesserter Fehlerbehandlung und Umgebungserkennung.
    
    :param app: Flask-Anwendung
    :return: True bei Erfolg, False bei Fehler
    """
    logger.info("Initialisiere Scheduler-System...")
    
    # Validiere Konfiguration und protokolliere Einstellungen
    try:
        SchedulerConfig.validate_and_log()
    except Exception as e:
        logger.error(f"Fehler bei Validierung der Scheduler-Konfiguration: {e}")
    
    # Initialize the cache system
    try:
        logger.info("Initialisiere Cache-System")
        cache_manager = init_cache_system()
        # Store cache manager in the app for access
        app._cache_manager = cache_manager
        logger.info("Cache-System erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler beim Initialisieren des Cache-Systems: {e}")
        logger.error(traceback.format_exc())
    
    try:
        # Scheduler-API initialisieren, wenn aktiviert
        if SchedulerConfig.API_ENABLED:
            try:
                logger.info("Registriere Scheduler-API Endpoints")
                from scheduler_api import init_app as init_scheduler_api
                init_scheduler_api(app)
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren der Scheduler-API: {e}")
                logger.error(traceback.format_exc())
        
        # Scheduler nur starten, wenn aktiviert
        if not SchedulerConfig.SCHEDULER_ENABLED:
            logger.info("Scheduler ist deaktiviert")
            return False
        
        # Entscheiden, ob wir Process-Manager verwenden oder integrierten Scheduler
        if SchedulerConfig.USE_PROCESS_MANAGER:
            logger.info("Scheduler wird im Process-Manager-Modus initialisiert")
            
            try:
                from scheduler_manager import get_scheduler_manager
                
                # Scheduler-Manager holen
                manager = get_scheduler_manager()
                
                # Manager in der App speichern für späteren Zugriff
                app._scheduler_manager = manager
                
                # Registriere Shutdown-Handler für sauberes Beenden
                @app.teardown_appcontext
                def shutdown_scheduler_on_exit(exception=None):
                    if exception:
                        logger.warning(f"App wird wegen Exception beendet: {exception}")
                    else:
                        logger.info("App wird regulär beendet")
                    
                    logger.info("Stoppe Scheduler-Manager...")
                    try:
                        manager.stop()
                    except Exception as e:
                        logger.error(f"Fehler beim Stoppen des Scheduler-Managers: {e}")
                
                # Starte den Scheduler-Prozess beim App-Start, wenn konfiguriert
                if not SchedulerConfig.MANUAL_START:
                    logger.info("Starte Scheduler-Prozess")
                    success = manager.start()
                    if success:
                        logger.info("Scheduler-Prozess erfolgreich gestartet")
                    else:
                        logger.error("Konnte Scheduler-Prozess nicht starten")
                        
                logger.info("Process-Manager erfolgreich initialisiert")
                return True
                
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren des Process-Managers: {e}")
                logger.error(traceback.format_exc())
                return False
        else:
            # Integrierter Scheduler (im selben Prozess wie die Flask-App)
            logger.info("Scheduler wird im integrierten Modus initialisiert")
            
            try:
                from data_refresh_scheduler import start_scheduler
                
                # Starte den Scheduler im gleichen Prozess
                if not SchedulerConfig.MANUAL_START:
                    scheduler = start_scheduler(managed_mode=False)
                    
                    # Scheduler in der App speichern für späteren Zugriff
                    app._scheduler_instance = scheduler
                    
                    # Registriere Shutdown-Handler
                    @app.teardown_appcontext
                    def shutdown_inprocess_scheduler(exception=None):
                        if exception:
                            logger.warning(f"App wird wegen Exception beendet: {exception}")
                        else:
                            logger.info("App wird regulär beendet")
                        
                        logger.info("Stoppe integrierten Scheduler...")
                        try:
                            scheduler.stop()
                        except Exception as e:
                            logger.error(f"Fehler beim Stoppen des Schedulers: {e}")
                    
                    logger.info("Integrierter Scheduler erfolgreich gestartet")
                else:
                    logger.info("Scheduler im manuellen Modus, wird nicht automatisch gestartet")
                
                return True
                
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren des integrierten Schedulers: {e}")
                logger.error(traceback.format_exc())
                return False
    
    except Exception as e:
        logger.error(f"Unbehandelter Fehler beim Initialisieren des Scheduler-Systems: {e}")
        logger.error(traceback.format_exc())
        return False