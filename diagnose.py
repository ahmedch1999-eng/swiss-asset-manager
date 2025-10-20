#!/usr/bin/env python3
"""
Swiss Asset Manager - Diagnose-Tool
-----------------------------------
Dieses Skript hilft bei der Identifizierung von Problemen mit dem Swiss Asset Manager,
insbesondere bei langsamen Ladezeiten und schwarzem Bildschirm.
"""

import os
import sys
import time
import importlib
import traceback
import logging
import platform
import psutil
import subprocess
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/diagnose.log', mode='w')
    ]
)
logger = logging.getLogger("diagnose")

def print_separator():
    logger.info("="*70)

def check_system_resources():
    """Überprüft System-Ressourcen"""
    logger.info("SYSTEM-RESSOURCEN:")
    
    # CPU Info
    logger.info(f"CPU-Kerne: {psutil.cpu_count(logical=False)} physisch, {psutil.cpu_count(logical=True)} logisch")
    logger.info(f"CPU-Auslastung: {psutil.cpu_percent(interval=1)}%")
    
    # Memory Info
    mem = psutil.virtual_memory()
    logger.info(f"Arbeitsspeicher: {mem.total/(1024*1024*1024):.2f} GB gesamt")
    logger.info(f"Speichernutzung: {mem.used/(1024*1024*1024):.2f} GB verwendet ({mem.percent}%)")
    
    # Disk Info
    disk = psutil.disk_usage('/')
    logger.info(f"Festplatte: {disk.total/(1024*1024*1024):.2f} GB gesamt")
    logger.info(f"Festplattennutzung: {disk.used/(1024*1024*1024):.2f} GB verwendet ({disk.percent}%)")
    
    # Python Info
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"Python Interpreter: {sys.executable}")

def check_required_files():
    """Überprüft, ob alle erforderlichen Dateien vorhanden sind"""
    logger.info("DATEIPRÜFUNG:")
    
    required_files = [
        "app.py", 
        "cache_enhancements_fix.py", 
        "quick_performance_fix.py",
        "scheduler_integration.py",
        "scheduler_dashboard.py",
        "metrics_collector.py",
        "cache_manager.py",
        "data_services.py",
        "data_services_cached.py",
        "route_adapter.py"
    ]
    
    all_ok = True
    for file in required_files:
        if os.path.exists(file):
            logger.info(f"✓ {file} gefunden")
        else:
            logger.error(f"✗ {file} FEHLT!")
            all_ok = False
    
    return all_ok

def check_module_imports():
    """Überprüft, ob alle erforderlichen Module importiert werden können"""
    logger.info("MODULE-IMPORTS:")
    
    modules_to_check = [
        # Core modules
        "flask", "numpy", "pandas", "matplotlib", "scipy",
        # Imported in app.py
        "cache_enhancements_fix", "quick_performance_fix", 
        "scheduler_integration", "scheduler_dashboard", "metrics_collector",
        # Custom modules
        "cache_manager", "data_services", "data_services_cached", 
        "route_adapter"
    ]
    
    success_count = 0
    for module in modules_to_check:
        try:
            start = time.time()
            if module in sys.modules:
                importlib.reload(sys.modules[module])
            else:
                importlib.import_module(module)
            end = time.time()
            logger.info(f"✓ {module} erfolgreich importiert ({(end-start)*1000:.2f} ms)")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ Fehler beim Import von {module}: {str(e)}")
            logger.debug(traceback.format_exc())
    
    return success_count, len(modules_to_check)

def check_database_files():
    """Überprüft Cache-Dateien"""
    logger.info("CACHE-DATEIEN:")
    
    cache_dir = "cache"
    if not os.path.exists(cache_dir):
        logger.error(f"✗ Cache-Verzeichnis '{cache_dir}' nicht gefunden!")
        return False
    
    cache_files = os.listdir(cache_dir)
    logger.info(f"Gefundene Cache-Dateien: {len(cache_files)}")
    
    for i, file in enumerate(cache_files[:5]):  # Nur die ersten 5 anzeigen
        full_path = os.path.join(cache_dir, file)
        size = os.path.getsize(full_path)
        logger.info(f"  - {file}: {size/1024:.2f} KB")
    
    if len(cache_files) > 5:
        logger.info(f"  ... und {len(cache_files) - 5} weitere Dateien")
    
    return True

def check_flask_app():
    """Überprüft, ob die Flask-App gestartet werden kann"""
    logger.info("FLASK-APP TEST:")
    
    try:
        start = time.time()
        # Importiere nur die Flask-App, starte sie nicht
        from app import app
        end = time.time()
        
        logger.info(f"✓ Flask-App erfolgreich importiert ({(end-start)*1000:.2f} ms)")
        
        # Zähle die Routen
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        logger.info(f"✓ {len(routes)} Routen gefunden")
        
        # Zeige die ersten 5 Routen
        for i, route in enumerate(routes[:5]):
            logger.info(f"  - {route}")
        
        if len(routes) > 5:
            logger.info(f"  ... und {len(routes) - 5} weitere Routen")
        
        return True
    except Exception as e:
        logger.error(f"✗ Fehler beim Import der Flask-App: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def check_html_template():
    """Überprüft die Größe des HTML-Templates"""
    logger.info("HTML-TEMPLATE PRÜFUNG:")
    
    try:
        # Import the HTML_TEMPLATE variable
        from app import HTML_TEMPLATE
        
        # Check size
        template_size = len(HTML_TEMPLATE)
        logger.info(f"HTML Template Größe: {template_size/1024:.2f} KB")
        
        # Check for common elements
        checks = [
            ("Passwortschutz", "passwordProtected" in HTML_TEMPLATE),
            ("Startseite", "landingPage" in HTML_TEMPLATE),
            ("Navigation", "navTab" in HTML_TEMPLATE),
            ("Dark Mode", "darkMode" in HTML_TEMPLATE),
            ("Monte Carlo", "monteCarloSimulation" in HTML_TEMPLATE),
            ("Charts", "chartContainer" in HTML_TEMPLATE)
        ]
        
        for name, result in checks:
            status = "✓" if result else "✗"
            logger.info(f"{status} {name}: {'gefunden' if result else 'NICHT GEFUNDEN'}")
        
        # Check if there's a lot of content (possible bloat)
        if template_size > 500 * 1024:  # More than 500KB
            logger.warning("⚠️ HTML Template ist sehr groß (>500KB), könnte Ladezeiten beeinträchtigen")
        
        return True
    except Exception as e:
        logger.error(f"✗ Fehler beim Prüfen des HTML-Templates: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def check_running_processes():
    """Überprüft, ob eine Instanz der App bereits läuft"""
    logger.info("LAUFENDE PROZESSE:")
    
    # Check if app is running using ps command
    try:
        ps_output = subprocess.check_output(["ps", "aux"]).decode('utf-8')
        app_processes = [line for line in ps_output.split('\n') if 'app.py' in line and 'python' in line]
        
        if app_processes:
            logger.info(f"✓ {len(app_processes)} laufende app.py Prozesse gefunden:")
            for process in app_processes:
                logger.info(f"  - {process.strip()}")
        else:
            logger.info("✗ Keine laufenden app.py Prozesse gefunden")
        
        # Check if port 8000 is in use
        port_in_use = False
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == 8000:
                    port_in_use = True
                    proc = psutil.Process(conn.pid)
                    logger.info(f"✓ Port 8000 wird von Prozess {conn.pid} ({proc.name()}) verwendet")
            
            if not port_in_use:
                logger.info("✗ Port 8000 ist nicht in Verwendung")
        except:
            logger.warning("⚠️ Konnte Portnutzung nicht überprüfen (erfordert root-Rechte)")
            
    except Exception as e:
        logger.error(f"✗ Fehler beim Prüfen laufender Prozesse: {str(e)}")

def run_quick_check():
    """Führt einen schnellen Funktionstest durch"""
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(datetime.now())}
    
    logger.info("Starte schnellen Flask-Test auf Port 9000...")
    try:
        process = subprocess.Popen([sys.executable, '-c', 
                                   'from flask import Flask; app = Flask(__name__); '
                                   '@app.route("/"); '
                                   'def index(): return "OK"; '
                                   'app.run(host="0.0.0.0", port=9000)'])
        time.sleep(1)  # Give it a moment to start
        
        # Check if it's running
        try:
            result = subprocess.check_output(['curl', '-s', 'http://localhost:9000/']).decode('utf-8')
            if "OK" in result:
                logger.info("✓ Test-Flask-Server funktioniert!")
            else:
                logger.error(f"✗ Unerwartete Antwort vom Test-Server: {result}")
        except:
            logger.error("✗ Konnte nicht mit Test-Server verbinden")
        
        # Kill process
        process.terminate()
        process.wait()
    except Exception as e:
        logger.error(f"✗ Fehler beim Test-Server: {str(e)}")

def main():
    """Hauptfunktion"""
    print_separator()
    logger.info("SWISS ASSET MANAGER - DIAGNOSE-TOOL")
    logger.info(f"Ausgeführt am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Prüfe System-Ressourcen
    check_system_resources()
    print_separator()
    
    # Prüfe erforderliche Dateien
    files_ok = check_required_files()
    print_separator()
    
    # Prüfe Module-Imports
    success_count, total_modules = check_module_imports()
    print_separator()
    
    # Prüfe Datenbank-Dateien
    cache_ok = check_database_files()
    print_separator()
    
    # Prüfe laufende Prozesse
    check_running_processes()
    print_separator()
    
    # Führe Flask-App-Test durch
    flask_ok = check_flask_app()
    print_separator()
    
    # Prüfe HTML-Template
    template_ok = check_html_template()
    print_separator()
    
    # Run quick check
    run_quick_check()
    print_separator()
    
    # Zusammenfassung
    logger.info("DIAGNOSE ZUSAMMENFASSUNG:")
    logger.info(f"Dateien: {'OK' if files_ok else 'PROBLEME GEFUNDEN'}")
    logger.info(f"Module: {success_count}/{total_modules} erfolgreich importiert")
    logger.info(f"Cache: {'OK' if cache_ok else 'PROBLEME GEFUNDEN'}")
    logger.info(f"Flask: {'OK' if flask_ok else 'PROBLEME GEFUNDEN'}")
    logger.info(f"Template: {'OK' if template_ok else 'PROBLEME GEFUNDEN'}")
    
    if files_ok and success_count == total_modules and cache_ok and flask_ok and template_ok:
        logger.info("✅ Alle Tests bestanden! Die App sollte funktionieren.")
        logger.info("Starten Sie die App mit: python app.py")
    else:
        logger.warning("⚠️ Einige Tests sind fehlgeschlagen. Bitte beheben Sie die oben genannten Probleme.")
    
    print_separator()

if __name__ == "__main__":
    main()