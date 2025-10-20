# Swiss Asset Manager - Umstellung auf Echtzeitdaten

## Übersicht der Änderungen

Diese Zusammenfassung beschreibt die vollständige Umstellung des Swiss Asset Managers von simulierten Daten auf Echtzeitdaten. Alle simulierten Daten wurden durch echte Datenquellen ersetzt.

### 1. Primäre Datenquellen

- **Yahoo Finance API** (primär): Für Aktien-, Index- und ETF-Daten
- **Alpha Vantage API** (Backup): Alternative Quelle, falls Yahoo Finance nicht verfügbar ist
- **RSS Feeds**: Für Finanznachrichten (FUW, Handelszeitung, NZZ, Cash, etc.)
- **Historische Daten**: Für Korrelationen und Volatilitätsberechnungen

### 2. Hauptänderungen

#### Datenabfrage-Funktionen
- `get_live_data()`: Ruft Live-Daten von Yahoo Finance und Alpha Vantage ab
- `get_yahoo_finance_data()`: Implementiert Yahoo Finance API-Abfragen
- `get_alpha_vantage_data()`: Implementiert Alpha Vantage API-Abfragen als Backup
- `get_benchmark_data()`: Holt Benchmark-Daten aus echten Quellen
- `get_correlation_data()`: Berechnet echte Korrelationen aus historischen Daten
- `monte_carlo_simulation()`: Verwendet echte historische Volatilitätsdaten
- `get_news()`: Ruft aktuelle Finanznachrichten von RSS-Feeds ab

#### Datenspeicher
- `SWISS_BANK_PORTFOLIOS`: Aktualisiert mit echten Fonds-Daten
- `MARKET_CYCLES`: Basiert auf echten Sektor-ETF-Daten
- `SCENARIOS`: Verwendet reale historische Marktdaten

#### Neue Funktionen
- `update_bank_portfolios()`: Aktualisiert Portfolio-Daten mit Echtzeitdaten
- `update_market_cycles()`: Aktualisiert Marktzyklen mit Echtzeitdaten
- `data_refresh_scheduler.py`: Automatische regelmäßige Aktualisierung aller Datenquellen

#### UI-Verbesserungen
- 🔴 **LIVE-Daten Markierung**: Klare visuelle Unterscheidung zwischen Echtdaten und Fehlermeldungen
- **Datenquellenanzeige**: Jeder Datenpunkt zeigt seine Herkunft an
- **Fehlerbehandlung**: Klare Fehlermeldungen statt Rückfall auf simulierte Daten

### 3. Technische Details

#### API-Nutzung
- Yahoo Finance: Kostenlos mit Nutzungsbeschränkungen
- Alpha Vantage: Kostenlos mit API-Key (5 Aufrufe/Minute, 500/Tag)
- **WICHTIG**: Alpha Vantage API-Key muss eingerichtet werden (siehe Kommentar in app.py)

#### Datenaktualisierung
- Automatischer Scheduler aktualisiert Daten mehrmals täglich
- Manuelle Aktualisierung über UI-Schaltflächen möglich
- Cache-System respektiert API-Limits

#### Fehlerbehandlung
- Mehrschichtige Backup-Strategie: Yahoo → Alpha Vantage → Fehlermeldung
- Klare Fehlermeldungen mit 0-Werten statt falscher Daten
- Keine Rückfalloptionen auf simulierte Daten mehr

### 4. Verwendung

1. **Installation/Update der Pakete**:
   ```
   pip install -r requirements.txt
   ```

2. **Automatischer Start**:
   ```
   ./start_app.sh
   ```

3. **Alpha Vantage API-Key einrichten**:
   - Registrieren Sie sich kostenlos unter: https://www.alphavantage.co/support/#api-key
   - Fügen Sie Ihren API-Key in app.py ein (suchen Sie nach "API_KEY = "demo"")

### 5. Bekannte Einschränkungen

- Kostenlose APIs haben Nutzungsbeschränkungen
- Manche Daten könnten verzögert sein (15-20 Minuten)
- Bei API-Ausfällen werden klare Fehlermeldungen angezeigt
- Bei sehr spezifischen oder exotischen Assets könnten keine Daten verfügbar sein

---

Implementiert von GitHub Copilot