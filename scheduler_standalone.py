"""
Scheduler Standalone Module
Ermöglicht das Ausführen des Schedulers als separater eigenständiger Prozess
"""
import os
import sys
import signal
import time
import logging
import atexit
import json
from datetime import datetime
from scheduler_config import SchedulerConfig

# Konfiguriere logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, SchedulerConfig.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scheduler_standalone.log')
    ]
)
logger = logging.getLogger("scheduler_standalone")

# Globale Flags für sauberes Herunterfahren
shutdown_requested = False
scheduler_instance = None

def handle_signal(sig, frame):
    """Signal-Handler für sauberes Beenden"""
    global shutdown_requested
    logger.info(f"Signal {sig} empfangen, beginne mit Graceful Shutdown...")
    shutdown_requested = True
    
    # Scheduler stoppen, falls er läuft
    if scheduler_instance:
        try:
            logger.info("Stoppe Scheduler-Instanz...")
            scheduler_instance.stop()
            logger.info("Scheduler-Instanz erfolgreich gestoppt.")
        except Exception as e:
            logger.error(f"Fehler beim Stoppen des Schedulers: {e}")
    
    # Status schreiben
    update_status("stopping")

def update_status(state, error=None):
    """Aktualisiert die Status-Datei für den Standalone-Prozess"""
    try:
        status = {
            "state": state,
            "pid": os.getpid(),
            "timestamp": datetime.now().isoformat(),
            "last_error": error
        }
        
        with open("scheduler_standalone_status.json", "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Status: {e}")

def write_pid():
    """Schreibt die PID in eine Datei"""
    try:
        with open("scheduler_standalone.pid", "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Fehler beim Schreiben der PID-Datei: {e}")

def cleanup():
    """Aufräumarbeiten bei Beendigung"""
    logger.info("Führe Aufräumarbeiten durch...")
    
    # PID-Datei entfernen
    try:
        if os.path.exists("scheduler_standalone.pid"):
            os.remove("scheduler_standalone.pid")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen der PID-Datei: {e}")
    
    # Status aktualisieren
    update_status("stopped")

def main():
    """Hauptfunktion für den Standalone-Modus"""
    global scheduler_instance
    
    logger.info(f"Starte Scheduler im Standalone-Modus mit PID {os.getpid()}")
    
    # Signal-Handler registrieren
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    # Aufräumen bei Exit
    atexit.register(cleanup)
    
    # PID schreiben
    write_pid()
    
    # Status aktualisieren
    update_status("starting")
    
    try:
        # Scheduler importieren und starten
        from data_refresh_scheduler import SafeScheduler, run_scheduled_updates, start_scheduler
        logger.info("Initialisiere Scheduler...")
        
        # Verwende die verbesserte start_scheduler-Funktion mit Process-Manager-Unterstützung
        scheduler = start_scheduler(
            managed_mode=True,  # Process-Manager-Modus aktivieren
            run_immediate_update=True  # Sofortiges Update beim Start
        )
        
        # Scheduler speichern für sauberes Herunterfahren
        scheduler_instance = scheduler
        
        # Status aktualisieren
        update_status("running")
        
        logger.info("Scheduler erfolgreich gestartet, beginne mit Ausführung...")
        
        # Scheduler-Loop
        while not shutdown_requested:
            scheduler.run_pending()
            time.sleep(1)
        
    except Exception as e:
        logger.critical(f"Schwerwiegender Fehler im Standalone-Modus: {e}", exc_info=True)
        update_status("error", str(e))
        return 1
    
    logger.info("Scheduler wurde sauber beendet")
    return 0

if __name__ == "__main__":
    sys.exit(main())