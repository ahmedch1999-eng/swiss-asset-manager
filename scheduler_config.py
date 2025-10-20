"""
Konfigurationsdatei für den Scheduler mit produktionsfähigen Einstellungen
und Umgebungsvariablen-Unterstützung.

Unterstützt den Scheduler-Process-Manager und separate Prozesse für robustere
Produktionsumgebungen mit verbesserter Fehlerbehandlung und Monitoring.
"""

import os
import logging
from pathlib import Path

# Verzeichnis für Logs erstellen
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Logger für Konfigurationen
logger = logging.getLogger("scheduler_config")

# Umgebungsbasierte Konfiguration mit sinnvollen Standardwerten
class SchedulerConfig:
    # Scheduler-Prozess - Grundeinstellungen
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'true').lower() == 'true'
    SCHEDULER_STANDALONE = os.environ.get('SCHEDULER_STANDALONE', 'false').lower() == 'true'
    
    # Process-Management-Konfiguration
    USE_PROCESS_MANAGER = os.environ.get('SCHEDULER_USE_PROCESS_MANAGER', 'true').lower() == 'true'
    PROCESS_MANAGED = os.environ.get('SCHEDULER_PROCESS_MANAGED', 'true').lower() == 'true'
    STATUS_CHECK_INTERVAL = int(os.environ.get('SCHEDULER_STATUS_CHECK_INTERVAL', '30'))
    RESTART_ON_FAILURE = os.environ.get('SCHEDULER_RESTART_ON_FAILURE', 'True').lower() == 'true'
    MAX_RESTART_ATTEMPTS = int(os.environ.get('SCHEDULER_MAX_RESTART_ATTEMPTS', '3'))
    PROCESS_MONITOR_ENABLED = os.environ.get('SCHEDULER_MONITOR_ENABLED', 'True').lower() == 'true'
    
    # API-Endpunkte für Process-Management
    API_ENABLED = os.environ.get('SCHEDULER_API_ENABLED', 'True').lower() == 'true'
    API_PORT = int(os.environ.get('SCHEDULER_API_PORT', '5001'))
    API_HOST = os.environ.get('SCHEDULER_API_HOST', '127.0.0.1')
    
    # Prozess- und Ausführungsoptionen
    CATCH_EXCEPTIONS = os.environ.get('SCHEDULER_CATCH_EXCEPTIONS', 'True').lower() == 'true'
    MANUAL_START = os.environ.get('SCHEDULER_MANUAL_START', 'False').lower() == 'true'
    UPDATE_INTERVAL_MINUTES = int(os.environ.get('SCHEDULER_UPDATE_INTERVAL', '60'))
    ENABLE_PARALLEL_UPDATES = os.environ.get('SCHEDULER_PARALLEL_UPDATES', 'true').lower() == 'true'
    MAX_WORKERS = int(os.environ.get('SCHEDULER_MAX_WORKERS', '4'))
    
    # Daten-Aktualisierungsintervalle (in Minuten)
    MARKET_UPDATE_INTERVAL = int(os.environ.get('MARKET_UPDATE_INTERVAL', '60'))
    PORTFOLIO_UPDATE_INTERVAL = int(os.environ.get('PORTFOLIO_UPDATE_INTERVAL', '120'))
    CYCLES_UPDATE_INTERVAL = int(os.environ.get('CYCLES_UPDATE_INTERVAL', '240'))
    NEWS_UPDATE_INTERVAL = int(os.environ.get('NEWS_UPDATE_INTERVAL', '30'))
    
    # API-Rate Limits
    YAHOO_API_RATE_LIMIT = int(os.environ.get('YAHOO_API_RATE_LIMIT', '60'))
    ALPHAVANTAGE_API_RATE_LIMIT = int(os.environ.get('ALPHAVANTAGE_API_RATE_LIMIT', '5'))
    
    # Performance-Optimierungen
    MAX_PARALLELISM = int(os.environ.get('MAX_PARALLELISM', '4'))
    MEMORY_LIMIT_MB = int(os.environ.get('MEMORY_LIMIT_MB', '500'))
    USE_PROCESS_POOL = os.environ.get('USE_PROCESS_POOL', 'false').lower() == 'true'
    
    # Health-Monitoring und Alerts
    HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', '5'))
    ALERT_ON_FAILURE = os.environ.get('ALERT_ON_FAILURE', 'false').lower() == 'true'
    ALERT_EMAIL = os.environ.get('ALERT_EMAIL', '')
    
    # Log-Level und Logging-Konfiguration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', '7'))
    LOG_MAX_SIZE_MB = int(os.environ.get('LOG_MAX_SIZE_MB', '10'))
    
    # Graceful Shutdown Timeout in Sekunden
    SHUTDOWN_TIMEOUT = int(os.environ.get('SHUTDOWN_TIMEOUT', '30'))
    
    # Fehlerbehandlung und Resilienz
    ERROR_THRESHOLD = int(os.environ.get('SCHEDULER_ERROR_THRESHOLD', '5'))
    ERROR_RESET_MINUTES = int(os.environ.get('SCHEDULER_ERROR_RESET_MINUTES', '60'))
    BACKOFF_FACTOR = float(os.environ.get('SCHEDULER_BACKOFF_FACTOR', '1.5'))
    
    # Dateiablageorte für Status und PID
    PID_FILE = os.environ.get('SCHEDULER_PID_FILE', 'scheduler.pid')
    STATUS_FILE = os.environ.get('SCHEDULER_STATUS_FILE', 'scheduler_status.json')
    METRICS_FILE = os.environ.get('SCHEDULER_METRICS_FILE', 'scheduler_metrics.json')
    
    # Spezielle Konfiguration für Entwicklungsumgebung
    @classmethod
    def is_development(cls) -> bool:
        """Prüft, ob die Anwendung in Entwicklungsumgebung läuft"""
        return os.environ.get('FLASK_ENV', 'production') == 'development'
    
    @classmethod
    def is_production(cls) -> bool:
        """Prüft, ob die Anwendung in Produktionsumgebung läuft"""
        return os.environ.get('FLASK_ENV', 'production') == 'production'
    
    @classmethod
    def is_testing(cls) -> bool:
        """Prüft, ob die Anwendung in Testumgebung läuft"""
        return os.environ.get('FLASK_ENV', '') == 'testing'
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Gibt die Konfiguration als Dictionary zurück"""
        return {
            # Grundeinstellungen
            'scheduler_enabled': cls.SCHEDULER_ENABLED,
            'scheduler_standalone': cls.SCHEDULER_STANDALONE,
            
            # Update-Intervalle
            'market_update_interval': cls.MARKET_UPDATE_INTERVAL,
            'portfolio_update_interval': cls.PORTFOLIO_UPDATE_INTERVAL,
            'cycles_update_interval': cls.CYCLES_UPDATE_INTERVAL,
            'news_update_interval': cls.NEWS_UPDATE_INTERVAL,
            'update_interval_minutes': cls.UPDATE_INTERVAL_MINUTES,
            
            # Performance-Einstellungen
            'max_parallelism': cls.MAX_PARALLELISM,
            'memory_limit_mb': cls.MEMORY_LIMIT_MB,
            'use_process_pool': cls.USE_PROCESS_POOL,
            'enable_parallel_updates': cls.ENABLE_PARALLEL_UPDATES,
            'max_workers': cls.MAX_WORKERS,
            
            # Monitoring und Logging
            'log_level': cls.LOG_LEVEL,
            'log_retention_days': cls.LOG_RETENTION_DAYS,
            'log_max_size_mb': cls.LOG_MAX_SIZE_MB,
            'health_check_interval': cls.HEALTH_CHECK_INTERVAL,
            'alert_on_failure': cls.ALERT_ON_FAILURE,
            'alert_email': cls.ALERT_EMAIL,
            
            # Prozess-Management
            'use_process_manager': cls.USE_PROCESS_MANAGER,
            'process_managed': cls.PROCESS_MANAGED,
            'status_check_interval': cls.STATUS_CHECK_INTERVAL,
            'restart_on_failure': cls.RESTART_ON_FAILURE,
            'max_restart_attempts': cls.MAX_RESTART_ATTEMPTS,
            'process_monitor_enabled': cls.PROCESS_MONITOR_ENABLED,
            
            # API-Konfiguration
            'api_enabled': cls.API_ENABLED,
            'api_port': cls.API_PORT,
            'api_host': cls.API_HOST,
            
            # Fehlerbehandlung und Shutdown
            'catch_exceptions': cls.CATCH_EXCEPTIONS,
            'manual_start': cls.MANUAL_START,
            'shutdown_timeout': cls.SHUTDOWN_TIMEOUT,
            'error_threshold': cls.ERROR_THRESHOLD,
            'error_reset_minutes': cls.ERROR_RESET_MINUTES,
            'backoff_factor': cls.BACKOFF_FACTOR,
            
            # Umgebung
            'environment': 'development' if cls.is_development() else 'production'
        }
        
    @classmethod
    def validate_and_log(cls) -> None:
        """Validiert die Konfiguration und protokolliert wichtige Einstellungen"""
        logger.info("============ Scheduler-Konfiguration ============")
        logger.info(f"Umgebung: {'Entwicklung' if cls.is_development() else 'Produktion'}")
        logger.info(f"Scheduler aktiviert: {cls.SCHEDULER_ENABLED}")
        logger.info(f"Process-Manager: {cls.USE_PROCESS_MANAGER}")
        logger.info(f"Update-Intervall: {cls.UPDATE_INTERVAL_MINUTES} Minuten")
        logger.info(f"Parallele Updates: {cls.ENABLE_PARALLEL_UPDATES} (max. {cls.MAX_WORKERS} Worker)")
        logger.info(f"API aktiviert: {cls.API_ENABLED} (Host: {cls.API_HOST}, Port: {cls.API_PORT})")
        logger.info(f"Log-Level: {cls.LOG_LEVEL}")
        logger.info("===============================================")
        
        # Warnungen bei potenziell problematischen Konfigurationen
        if cls.is_production() and cls.LOG_LEVEL == "DEBUG":
            logger.warning("DEBUG-Log-Level in Produktionsumgebung könnte Performance beeinträchtigen")
            
        if cls.is_production() and not cls.USE_PROCESS_MANAGER:
            logger.warning("Process-Manager ist in Produktionsumgebung deaktiviert")
            
        if cls.MEMORY_LIMIT_MB < 200:
            logger.warning(f"Niedrige Memory-Limit-Einstellung: {cls.MEMORY_LIMIT_MB} MB")