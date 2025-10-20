# Thread-Sicherheit in Swiss Asset Manager

## Übersicht

Die Swiss Asset Manager Anwendung verwendet mehrere Threads für verschiedene Aufgaben. Diese Dokumentation beschreibt, wie die Thread-Sicherheit in der Anwendung gewährleistet wird.

## Thread-Architektur

Die Anwendung hat drei Hauptthreads:

1. **Haupt-Thread (Flask)**: Verarbeitet HTTP-Anfragen und rendert die Benutzeroberfläche
2. **Scheduler-Thread**: Führt geplante Datenaktualisierungen durch
3. **Update-Threads**: Temporäre Threads für die eigentliche Datenaktualisierung

## Sicherheitsmechanismen

### 1. Thread-Lock für gemeinsame Datenstrukturen

```python
# Thread-Lock für sichere Datenzugriffe
data_lock = threading.RLock()

# Beispiel für die Verwendung:
with data_lock:
    # Kritischer Abschnitt - Thread-sichere Operationen
    cache['live_market_data'] = result
```

### 2. SafeScheduler-Klasse

Die `SafeScheduler`-Klasse ist eine spezielle Thread-Implementierung, die:

- Als Daemon-Thread läuft (beendet sich automatisch, wenn die Hauptanwendung stoppt)
- Einen sauberen Stopp-Mechanismus hat
- Keine blockierenden Operationen im Haupt-Thread ausführt
- Geplante Aktualisierungen in separaten Threads ausführt

### 3. Update-Status-Tracking

```python
cache['update_in_progress'] = {
    'markets': False,
    'portfolios': False,
    'cycles': False,
    'news': False
}
```

Dieses System verhindert, dass mehrere Updates gleichzeitig die gleichen Daten aktualisieren.

### 4. Fehlerbehandlung

Alle Thread-Operationen sind in `try-except`-Blöcke eingeschlossen, um zu verhindern, dass ein fehlerhafter Thread die gesamte Anwendung zum Absturz bringt.

## Sicheres Beenden

Die Anwendung implementiert einen sauberen Shutdown-Prozess:

1. **Abfangen von KeyboardInterrupt**: Erkennt, wenn der Benutzer CTRL+C drückt
2. **Thread-Stopp**: Ruft die `stop()`-Methode des Schedulers auf
3. **Ressourcen-Freigabe**: Gibt alle gehaltenen Ressourcen frei

## Potenzielle Probleme und Lösungen

### Problem: API-Rate-Limits

**Lösung:** Die Anwendung verwendet Verzögerungen (`time.sleep()`) zwischen API-Aufrufen und cacht Ergebnisse.

### Problem: Flask-Blockierung

**Lösung:** 
- Alle potenziell blockierenden Operationen laufen in eigenen Threads
- Scheduler verwendet `_stop_event.wait(timeout=30)` statt `time.sleep(60)`

### Problem: Race Conditions

**Lösung:**
- Verwendung von `threading.RLock()` für alle geteilten Ressourcen
- Status-Tracking für Updates verhindert doppelte Updates

## Best Practices

1. **Immer `with data_lock:` verwenden**, wenn auf geteilte Ressourcen zugegriffen wird
2. **Keine blockierenden Operationen im Haupt-Thread**
3. **Daemon-Threads für alle Hintergrundaufgaben** verwenden
4. **Klare Fehlerbehandlung** in allen Thread-Funktionen implementieren

## Testen der Thread-Sicherheit

Die Thread-Sicherheit kann getestet werden durch:

1. Gleichzeitiges Aufrufen mehrerer API-Endpunkte
2. Manuelles Aktualisieren während der Scheduler läuft
3. Beenden der Anwendung während Aktualisierungen laufen