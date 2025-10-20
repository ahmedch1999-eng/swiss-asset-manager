"""
Scheduler Process Manager
Bietet die Möglichkeit, den Scheduler als separaten Prozess zu starten
und verwaltet dessen Lebenszyklus, Logging und Status
"""

import os
import sys
import time
import logging
import signal
import multiprocessing
import atexit
import json
from datetime import datetime
import psutil
import requests
from scheduler_config import SchedulerConfig

# Logger konfigurieren
logging.basicConfig(
    level=getattr(logging, SchedulerConfig.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scheduler_manager.log')
    ]
)
logger = logging.getLogger("scheduler_manager")

class SchedulerProcessManager:
    """
    Verwaltet den Scheduler-Prozess für die Produktion
    """
    def __init__(self, standalone=False):
        """
        Initialisiert den Scheduler-Manager.
        
        :param standalone: Wenn True, wird der Scheduler als eigenständiger Prozess gestartet,
                         nicht als Fork des Flask-Prozesses.
        """
        self.standalone = standalone or SchedulerConfig.SCHEDULER_STANDALONE
        self.process = None
        self.pid_file = "scheduler.pid"
        self.status_file = "scheduler_status.json"
        self.is_running = False
        self.start_time = None
        self.status = {
            "state": "stopped",
            "pid": None,
            "uptime": 0,
            "last_update": None,
            "memory_usage_mb": 0,
            "cpu_percent": 0,
            "updates_completed": 0,
            "updates_failed": 0,
            "last_error": None,
            "config": SchedulerConfig.get_config_dict()
        }
        
        # Verzeichnisse vorbereiten
        os.makedirs("logs", exist_ok=True)
        
        # Aufräumen bei Exit
        atexit.register(self.cleanup)
        
        # Signal-Handler registrieren
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        
        logger.info(f"Scheduler Process Manager initialisiert (Standalone-Modus: {self.standalone})")
    
    def _handle_signal(self, sig, frame):
        """Signal-Handler für sauberes Beenden"""
        logger.info(f"Signal {sig} empfangen, beende Scheduler-Prozess...")
        self.stop()
        
        # Exit nur im Standalone-Modus
        if self.standalone:
            sys.exit(0)
    
    def start(self):
        """Startet den Scheduler-Prozess"""
        if self.is_running:
            logger.warning("Scheduler läuft bereits")
            return False
        
        try:
            if self.standalone:
                # Starten als vollständig separater Prozess
                logger.info("Starte Scheduler als eigenständigen Prozess")
                import subprocess
                cmd = [sys.executable, "-m", "scheduler_standalone"]
                self.process = subprocess.Popen(
                    cmd,
                    stdout=open(os.path.join("logs", "scheduler_stdout.log"), "a"),
                    stderr=open(os.path.join("logs", "scheduler_stderr.log"), "a")
                )
                self.is_running = True
                
                # PID speichern
                with open(self.pid_file, "w") as f:
                    f.write(str(self.process.pid))
            else:
                # Starten als Kindprozess des Flask-Servers
                logger.info("Starte Scheduler als Kindprozess")
                # Multiprocessing-Context für Fork/Spawn basierend auf Betriebssystem
                ctx = multiprocessing.get_context('spawn')
                self.process = ctx.Process(
                    target=self._run_scheduler_process,
                    name="SwissAssetScheduler"
                )
                self.process.daemon = False  # Nicht als Daemon-Prozess, für sauberes Herunterfahren
                self.process.start()
                
                # PID speichern
                with open(self.pid_file, "w") as f:
                    f.write(str(self.process.pid))
                
                self.is_running = True
            
            self.start_time = datetime.now()
            
            # Status aktualisieren
            self._update_status({
                "state": "running",
                "pid": self.process.pid,
                "last_update": datetime.now().isoformat()
            })
            
            logger.info(f"Scheduler-Prozess gestartet mit PID {self.process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Starten des Scheduler-Prozesses: {e}", exc_info=True)
            self._update_status({
                "state": "error",
                "last_error": str(e),
                "last_update": datetime.now().isoformat()
            })
            return False
    
    def stop(self):
        """Stoppt den Scheduler-Prozess mit Graceful Shutdown"""
        if not self.is_running:
            logger.warning("Scheduler läuft nicht")
            return True
        
        try:
            logger.info("Stoppe Scheduler-Prozess mit Graceful Shutdown...")
            
            # PID laden
            pid = None
            if os.path.exists(self.pid_file):
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
            
            # Prozess stoppen
            if pid:
                try:
                    # SIGTERM senden für Graceful Shutdown
                    os.kill(pid, signal.SIGTERM)
                    
                    # Warten bis zum definierten Timeout
                    timeout = SchedulerConfig.SHUTDOWN_TIMEOUT
                    for _ in range(timeout):
                        time.sleep(1)
                        try:
                            # Prüfen, ob Prozess noch läuft
                            os.kill(pid, 0)
                        except OSError:
                            # Prozess existiert nicht mehr
                            logger.info(f"Scheduler-Prozess (PID {pid}) erfolgreich beendet")
                            break
                    else:
                        # Timeout erreicht, SIGKILL senden
                        logger.warning(f"Timeout erreicht, sende SIGKILL an Scheduler-Prozess (PID {pid})")
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    logger.info(f"Scheduler-Prozess (PID {pid}) existiert nicht mehr")
            
            # Status aktualisieren
            self._update_status({
                "state": "stopped",
                "pid": None,
                "last_update": datetime.now().isoformat()
            })
            
            self.is_running = False
            self.process = None
            
            # PID-Datei löschen
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Stoppen des Scheduler-Prozesses: {e}", exc_info=True)
            self._update_status({
                "state": "error",
                "last_error": str(e),
                "last_update": datetime.now().isoformat()
            })
            return False
    
    def restart(self):
        """Startet den Scheduler-Prozess neu"""
        self.stop()
        time.sleep(2)  # Kurze Pause zum Aufräumen
        return self.start()
    
    def _run_scheduler_process(self):
        """
        Diese Funktion wird im separaten Prozess ausgeführt und startet den eigentlichen Scheduler
        """
        try:
            # Separates Logging für den Scheduler-Prozess
            process_logger = logging.getLogger("scheduler_process")
            handler = logging.FileHandler('logs/scheduler_process.log')
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
            process_logger.addHandler(handler)
            process_logger.setLevel(getattr(logging, SchedulerConfig.LOG_LEVEL))
            
            process_logger.info(f"Scheduler-Prozess gestartet mit PID {os.getpid()}")
            
            # Eigene Signal-Handler für den Scheduler-Prozess
            def handle_signal(sig, frame):
                process_logger.info(f"Scheduler-Prozess: Signal {sig} empfangen, beende Prozess...")
                self._scheduler_cleanup()
                sys.exit(0)
            
            signal.signal(signal.SIGTERM, handle_signal)
            signal.signal(signal.SIGINT, handle_signal)
            
            # Daten-Aktualisierungs-Scheduler importieren und starten
            from data_refresh_scheduler import start_scheduler
            scheduler = start_scheduler()
            
            # Endlos-Loop für den Prozess
            process_logger.info("Scheduler-Hauptprozess gestartet, warte auf Beendigung...")
            while True:
                time.sleep(1)
                
        except Exception as e:
            logger.critical(f"Schwerwiegender Fehler im Scheduler-Prozess: {e}", exc_info=True)
            self._update_status({
                "state": "crashed",
                "last_error": str(e),
                "last_update": datetime.now().isoformat()
            })
            sys.exit(1)
    
    def _scheduler_cleanup(self):
        """Aufräumen, wenn der Scheduler-Prozess beendet wird"""
        try:
            logger.info("Führe Scheduler-Prozess-Cleanup durch...")
            # Hier kann zusätzlicher Cleanup-Code eingefügt werden
        except Exception as e:
            logger.error(f"Fehler beim Scheduler-Prozess-Cleanup: {e}")
    
    def _update_status(self, updates):
        """Aktualisiert den Status und speichert ihn in die Datei"""
        try:
            # Status aktualisieren
            self.status.update(updates)
            
            # Ressourcennutzung aktualisieren, falls Prozess läuft
            if self.status["pid"] is not None:
                try:
                    process = psutil.Process(self.status["pid"])
                    self.status["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
                    self.status["cpu_percent"] = process.cpu_percent(interval=0.1)
                    
                    # Uptime berechnen
                    if self.start_time:
                        uptime = (datetime.now() - self.start_time).total_seconds()
                        self.status["uptime"] = int(uptime)
                except (psutil.NoSuchProcess, ProcessLookupError):
                    # Prozess existiert nicht mehr
                    self.status["state"] = "unknown"
                    self.status["pid"] = None
            
            # Status in Datei speichern
            with open(self.status_file, "w") as f:
                json.dump(self.status, f, indent=2)
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Scheduler-Status: {e}")
    
    def get_status(self):
        """Gibt den aktuellen Status des Schedulers zurück"""
        self._update_status({})  # Status ohne Änderungen aktualisieren (für aktuelle Ressourcennutzung)
        return self.status
    
    def check_health(self):
        """Prüft die Gesundheit des Scheduler-Prozesses"""
        if not self.is_running:
            return {
                "status": "stopped",
                "healthy": False,
                "message": "Scheduler ist nicht gestartet"
            }
        
        # Status aktualisieren
        status = self.get_status()
        
        # Prüfen, ob Prozess noch läuft
        process_running = False
        if status["pid"]:
            try:
                process = psutil.Process(status["pid"])
                process_running = process.is_running() and process.status() != psutil.STATUS_ZOMBIE
            except (psutil.NoSuchProcess, ProcessLookupError):
                process_running = False
        
        # Memorynutzung prüfen
        memory_ok = status["memory_usage_mb"] < SchedulerConfig.MEMORY_LIMIT_MB
        
        # Gesundheitsstatus ermitteln
        healthy = process_running and memory_ok and status["state"] == "running"
        
        health_result = {
            "status": status["state"],
            "healthy": healthy,
            "pid": status["pid"],
            "process_running": process_running,
            "memory_usage_mb": status["memory_usage_mb"],
            "memory_ok": memory_ok,
            "cpu_percent": status["cpu_percent"],
            "uptime": status["uptime"],
            "updates_completed": status["updates_completed"],
            "updates_failed": status["updates_failed"],
            "last_error": status["last_error"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Alert bei ungesundem Zustand
        if not healthy and SchedulerConfig.ALERT_ON_FAILURE:
            self._send_alert(health_result)
        
        return health_result
    
    def _send_alert(self, health_data):
        """Sendet einen Alert bei kritischen Problemen"""
        if not SchedulerConfig.ALERT_EMAIL:
            logger.warning("Kein Alert-Email konfiguriert, Alert wird nicht gesendet")
            return
        
        # In der Praxis würde hier ein E-Mail oder ein API-Call an einen Alert-Service erfolgen
        logger.critical(f"ALERT: Scheduler-Problem erkannt: {json.dumps(health_data)}")
    
    def cleanup(self):
        """Aufräumen bei Beendigung des Managers"""
        logger.info("Scheduler Process Manager wird beendet, räume auf...")
        self.stop()
    
    def update_metrics(self, metrics):
        """Aktualisiert die Metriken im Status"""
        if metrics.get("success", False):
            self._update_status({
                "updates_completed": self.status["updates_completed"] + 1,
                "last_update": datetime.now().isoformat()
            })
        else:
            self._update_status({
                "updates_failed": self.status["updates_failed"] + 1,
                "last_error": metrics.get("error", "Unbekannter Fehler"),
                "last_update": datetime.now().isoformat()
            })

# Globale Singleton-Instanz
_scheduler_manager = None

def get_scheduler_manager():
    """Gibt eine Singleton-Instanz des SchedulerProcessManager zurück"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerProcessManager()
    return _scheduler_manager

if __name__ == "__main__":
    # Test des Managers
    manager = SchedulerProcessManager(standalone=True)
    manager.start()
    try:
        while True:
            time.sleep(60)
            status = manager.check_health()
            print(f"Scheduler Status: {status}")
    except KeyboardInterrupt:
        print("Manager wird beendet...")
        manager.stop()