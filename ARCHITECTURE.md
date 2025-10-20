# Swiss Asset Manager - Refaktorierte Daten-Architektur

## Überblick

Diese Architektur ermöglicht eine klare Trennung zwischen der Flask-Webanwendung und den Datendiensten. Dadurch können Datenaktualisierungen sowohl über die Web-API als auch direkt vom Scheduler ausgeführt werden, ohne zirkuläre Abhängigkeiten zu erzeugen.

## Hauptkomponenten

### 1. Daten-Services (`data_services.py`)
- Enthält alle Datenzugriffsfunktionen
- Verwaltet einen gemeinsamen Cache
- Thread-sicher durch Verwendung von RLock
- Führt die eigentlichen API-Aufrufe durch (Yahoo Finance, Alpha Vantage)
- Speichert die globalen Datenstrukturen (SWISS_BANK_PORTFOLIOS, MARKET_CYCLES, SCENARIOS)

### 2. Route-Adapter (`route_adapter.py`)
- Verbindet Flask-Routen mit Daten-Services
- Konvertiert API-Anfragen in Funktionsaufrufe
- Wandelt Funktionsergebnisse in JSON-Antworten um

### 3. Daten-Aktualisierungs-Scheduler (`data_refresh_scheduler.py`)
- Führt regelmäßige Datenaktualisierungen durch
- Ruft Funktionen direkt aus data_services auf
- Verwendet keine HTTP-Anfragen
- Läuft in einem eigenen Thread

### 4. Flask-App (`app.py`)
- Definiert die Web-API-Endpunkte
- Leitet Anfragen durch den Route-Adapter an die Daten-Services weiter
- Stellt die Benutzeroberfläche bereit

## Datenfluss

1. **Web-Anfrage**: 
   `HTTP-Anfrage → Flask-Route → Route-Adapter → data_services → Ergebnis → JSON-Antwort`

2. **Scheduler-Update**:
   `Scheduler → data_services → Cache-Update`

## Thread-Sicherheit

- Alle geteilten Datenstrukturen sind durch ein `threading.RLock` geschützt
- Updates werden atomisch ausgeführt
- Verhindert parallele Aktualisierungen der gleichen Ressource

## Vorteile der neuen Architektur

1. **Keine zirkulären Abhängigkeiten**: Der Scheduler ruft keine HTTP-Endpunkte mehr auf, sondern direkt die Datenfunktionen
2. **Ressourceneffizienz**: Keine redundanten HTTP-Anfragen, keine doppelte Datenverarbeitung
3. **Thread-Sicherheit**: Geschützte gemeinsame Datenstrukturen verhindern Race Conditions
4. **Bessere Testbarkeit**: Logik ist von der Web-Schicht getrennt und kann separat getestet werden
5. **Einfachere Wartung**: Klare Trennung der Zuständigkeiten

## Verwendung

Der Scheduler wird beim Starten der Anwendung automatisch initialisiert und führt die folgenden Aktualisierungen durch:
- Beim Start der App
- Täglich um 08:00, 12:00 und 16:00 Uhr (während der Handelszeiten)

Alle Daten werden im gemeinsamen Cache gespeichert und sind sowohl für die Web-API als auch für den Scheduler verfügbar.