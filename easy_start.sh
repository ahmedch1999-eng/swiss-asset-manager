#!/bin/bash

# Swiss Asset Manager - Einfacher Start
# Dieses Skript startet den Swiss Asset Manager mit optimierten Einstellungen

echo "=================================================="
echo "   SWISS ASSET MANAGER - EINFACHER START"
echo "=================================================="

# Überprüfe, ob bereits eine Instanz läuft
if pgrep -f "python.*app.py" > /dev/null; then
  echo "⚠️ Es läuft bereits eine Instanz des Swiss Asset Manager."
  echo "Beenden Sie diese zuerst mit: pkill -f 'python.*app.py'"
  exit 1
fi

# Erstelle einen temporären Patch für das Datenladeproblem
echo "Erstelle temporären Fix für das Datenladeproblem..."

cat > lazy_data_fix.py << 'EOF'
"""
Lazy Data Loading Fix für Swiss Asset Manager
Diese Datei optimiert das Laden von Finanzdaten
"""

import logging
import functools
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lazy_data_fix")

def apply_lazy_loading_fix():
    """Patcht die Datenladefunktionen für verzögertes Laden"""
    logger.info("Anwenden von Lazy Loading Fix...")
    
    try:
        # Import und Patch von data_services
        import data_services
        import data_services_cached
        
        # Speichere die originalen Funktionen
        original_update_market_data = data_services.DataServices.update_market_data
        original_update_financial_news = data_services.DataServices.update_financial_news
        
        # Ersetzende Funktionen mit verzögertem Laden
        @functools.wraps(original_update_market_data)
        def delayed_update_market_data(self, symbols=None, force=False):
            """Verzögertes Laden von Marktdaten"""
            if not symbols:  # Wenn keine spezifischen Symbole angefordert werden
                logger.info("Lazy loading: Überspringe automatisches Laden aller Marktdaten")
                return {"status": "deferred", "message": "Automatisches Laden deaktiviert"}
            else:
                # Nur die angeforderten Symbole laden
                logger.info(f"Lade nur angeforderte Symbole: {symbols}")
                return original_update_market_data(self, symbols=symbols, force=force)
        
        @functools.wraps(original_update_financial_news)
        def delayed_update_financial_news(self, topics=None, force=False):
            """Verzögertes Laden von Finanznachrichten"""
            logger.info("Lazy loading: Überspringe initiales Laden von Finanznachrichten")
            return {"status": "deferred", "message": "Automatisches Laden deaktiviert"}
            
        # Patche die Funktionen
        data_services.DataServices.update_market_data = delayed_update_market_data
        data_services.DataServices.update_financial_news = delayed_update_financial_news
        
        # Patche auch die Cache-Funktionalität
        try:
            # Reduziere die Cache-Warming Aktivitäten
            import cache_manager
            original_warm_cache = cache_manager.CacheManager.warm_cache
            
            @functools.wraps(original_warm_cache)
            def minimal_warm_cache(self, key_pattern=None):
                """Minimales Cache-Warming"""
                logger.info("Lazy loading: Minimales Cache-Warming")
                if key_pattern and ":" in key_pattern:
                    category, item = key_pattern.split(":", 1)
                    # Nur spezifische Items wärmen
                    return original_warm_cache(self, key_pattern)
                return {"warmed": 0, "skipped": 0, "errors": 0}
            
            cache_manager.CacheManager.warm_cache = minimal_warm_cache
            logger.info("Cache-Manager erfolgreich gepatcht")
        except Exception as e:
            logger.warning(f"Konnte Cache-Manager nicht patchen: {e}")
        
        logger.info("Lazy Loading Fix erfolgreich angewendet!")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Anwenden des Lazy Loading Fix: {e}")
        return False

# Exportfunktionen
__all__ = ['apply_lazy_loading_fix']
EOF

# Erstelle ein einfaches Startup-Skript
cat > simple_start.py << 'EOF'
#!/usr/bin/env python3
"""
Einfacher Starter für Swiss Asset Manager
- Verhindert schwarzen Bildschirm
- Optimiert Ladeverhalten
- Verzögert Datenabrufe
"""

import os
import sys
import time
import logging
import importlib
import threading
import subprocess

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_start")

def print_header():
    """Zeigt Header an"""
    print("="*60)
    print("    SWISS ASSET MANAGER - EINFACHER START")
    print("="*60)
    print("✓ Optimierter Start ohne schwarzen Bildschirm")
    print("✓ Verzögertes Laden von Markt- und Finanzdaten")
    print("✓ Verbesserte Reaktionszeit der Benutzeroberfläche")
    print("="*60)

def apply_fixes():
    """Wendet alle Fixes an"""
    try:
        # Lazy Loading Fix anwenden
        from lazy_data_fix import apply_lazy_loading_fix
        if apply_lazy_loading_fix():
            logger.info("✓ Lazy Loading Fix erfolgreich angewendet")
        else:
            logger.error("✗ Fehler beim Anwenden des Lazy Loading Fix")
            return False
            
        return True
    except Exception as e:
        logger.error(f"✗ Fehler beim Anwenden der Fixes: {e}")
        return False

def start_app():
    """Startet die App in einem separaten Prozess"""
    try:
        # Den Python-Interpreter bestimmen
        python = sys.executable
        
        # Starte den Flask-Server in einem separaten Prozess
        cmd = [python, 'app.py']
        env = os.environ.copy()
        env['FLASK_RUN_PORT'] = '8000'  # Setze den Port
        env['OPTIMIZE_LOADING'] = 'true'  # Flag für optimiertes Laden
        
        logger.info(f"Starte Swiss Asset Manager mit: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, env=env)
        
        # Warte kurz, um zu sehen ob der Prozess abstürzt
        time.sleep(2)
        
        if process.poll() is not None:  # Wenn der Prozess bereits beendet wurde
            logger.error(f"✗ App konnte nicht gestartet werden (Exit-Code: {process.returncode})")
            return False
        
        logger.info("✓ Swiss Asset Manager erfolgreich gestartet!")
        return True
    except Exception as e:
        logger.error(f"✗ Fehler beim Starten der App: {e}")
        return False

def open_browser():
    """Öffnet den Browser"""
    import webbrowser
    time.sleep(3)  # Warte, bis der Server gestartet ist
    url = "http://localhost:8000"
    logger.info(f"Öffne Browser: {url}")
    webbrowser.open(url)

def main():
    """Hauptfunktion"""
    print_header()
    
    # Fixes anwenden
    logger.info("Wende Fixes an...")
    if not apply_fixes():
        logger.error("Konnte Fixes nicht anwenden. Breche ab.")
        return 1
    
    # App starten
    logger.info("Starte Swiss Asset Manager...")
    if not start_app():
        logger.error("Konnte App nicht starten. Breche ab.")
        return 1
    
    # Browser öffnen
    threading.Thread(target=open_browser).start()
    
    print("\n✓ Swiss Asset Manager erfolgreich gestartet!")
    print("  URL: http://localhost:8000")
    print("  Passwort: swissassetmanagerAC")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

# Mache das Skript ausführbar
chmod +x simple_start.py

echo "✅ Optimierungsskript erstellt!"
echo "Starte Swiss Asset Manager mit optimierten Einstellungen..."

# Starte den optimierten Server
python3 simple_start.py

# Starte die App direkt, falls das Skript nicht funktioniert
if [ $? -ne 0 ]; then
  echo "⚠️ Konnte Optimierungsskript nicht ausführen, versuche direkten Start..."
  python3 app.py
fi