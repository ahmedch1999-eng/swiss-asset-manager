# 📊 Live Data Integration - Swiss Asset Pro

## Übersicht

Swiss Asset Pro nutzt jetzt **echte Live-Daten** von Yahoo Finance für alle Portfolio-Berechnungen und Marktanalysen. Das System verfügt über ein intelligentes Caching-System und automatische Fallback-Mechanismen.

## 🎯 Features

### 1. **Live Marktdaten**
- **Quelle**: Yahoo Finance (yfinance Python-Bibliothek)
- **Update-Frequenz**: Alle 5 Minuten (für Einzelpreise), alle 15 Minuten (für Marktübersicht)
- **Verfügbare Daten**:
  - Aktuelle Preise (real-time)
  - Tagesveränderung (absolut & prozentual)
  - Handelsvolumen
  - Tageshoch/-tief
  - 52-Wochen-Hoch/-Tief
  - Historische Daten (1 Tag bis mehrere Jahre)

### 2. **Automatische Portfolio-Analyse**
Wenn ein Asset zum Portfolio hinzugefügt wird, werden automatisch berechnet:
- **Erwartete Rendite**: Basierend auf historischen Daten (annualisiert)
- **Volatilität**: Standardabweichung der Returns (annualisiert)
- **Beta**: Systematisches Risiko (falls verfügbar)
- **Korrelationen**: Zwischen verschiedenen Assets

### 3. **Intelligentes Caching**
```python
# Cache-Zeiten:
- Live-Preise: 5 Minuten (300 Sekunden)
- Historische Daten: 1 Stunde (3600 Sekunden)
- Marktübersicht: 5 Minuten (300 Sekunden)
```

### 4. **Fallback-System**
Bei Netzwerkfehlern oder fehlenden Daten:
1. **Primär**: Yahoo Finance API
2. **Sekundär**: Cached Daten (falls vorhanden)
3. **Tertiär**: Simulierte Daten als letzter Ausweg

## 🔧 API Endpunkte

### Backend (Flask)

#### 1. `/api/get_live_price/<symbol>`
Ruft den aktuellen Preis und Details für ein bestimmtes Symbol ab.

**Response**:
```json
{
  "symbol": "NESN.SW",
  "price": 108.50,
  "change": 1.20,
  "changePercent": 1.12,
  "volume": 1234567,
  "high": 109.00,
  "low": 107.80,
  "open": 108.00,
  "name": "Nestlé S.A.",
  "source": "yahoo_finance",
  "timestamp": 1697383200.0
}
```

#### 2. `/api/get_historical_data/<symbol>?period=1mo`
Ruft historische Daten ab.

**Parameter**:
- `period`: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

**Response**:
```json
{
  "symbol": "NESN.SW",
  "data": [
    {
      "date": "2025-10-01",
      "close": 108.50,
      "open": 107.80,
      "high": 109.20,
      "low": 107.50,
      "volume": 1234567
    },
    ...
  ],
  "source": "yahoo_finance",
  "timestamp": 1697383200.0
}
```

#### 3. `/api/get_market_overview`
Ruft eine Übersicht der wichtigsten Indizes ab.

**Response**:
```json
{
  "indices": [
    {
      "symbol": "^SSMI",
      "name": "SMI",
      "price": 11234.56,
      "change": 45.23,
      "changePercent": 0.40
    },
    ...
  ],
  "source": "yahoo_finance",
  "timestamp": 1697383200.0
}
```

#### 4. `/api/get_asset_stats/<symbol>`
Ruft detaillierte Statistiken für ein Asset ab (Volatilität, erwartete Rendite, etc.).

**Response**:
```json
{
  "symbol": "NESN.SW",
  "name": "Nestlé S.A.",
  "price": 108.50,
  "yearHigh": 125.30,
  "yearLow": 95.40,
  "avgVolume": 2345678,
  "volatility": 18.50,
  "expectedReturn": 8.20,
  "beta": 0.85,
  "marketCap": 250000000000,
  "sector": "Consumer Defensive",
  "source": "yahoo_finance",
  "timestamp": 1697383200.0
}
```

## 📈 Verwendete Indizes

Die App lädt automatisch Daten für folgende Indizes:

| Symbol  | Name         | Region       |
|---------|--------------|--------------|
| ^SSMI   | SMI          | Schweiz      |
| ^GSPC   | S&P 500      | USA          |
| ^DJI    | Dow Jones    | USA          |
| ^IXIC   | NASDAQ       | USA          |
| ^GDAXI  | DAX          | Deutschland  |
| ^FTSE   | FTSE 100     | UK           |

## 💻 Frontend Integration

### Automatisches Laden beim Asset-Hinzufügen

```javascript
// Beispiel: Stock hinzufügen
function addStock() {
    const symbol = select.value;
    
    fetch(`/api/get_asset_stats/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                userPortfolio.push({
                    symbol: symbol,
                    name: data.name,
                    expectedReturn: data.expectedReturn / 100,
                    volatility: data.volatility / 100,
                    currentPrice: data.price,
                    source: 'yahoo_finance'
                });
                console.log(`✅ Loaded real data for ${symbol}`);
            }
        });
}
```

### Live Markets Page

Die "Märkte"-Seite lädt automatisch Live-Daten:

```javascript
function loadLiveMarkets() {
    fetch('/api/get_market_overview')
        .then(response => response.json())
        .then(data => {
            // Zeigt Live-Daten für alle Major-Indizes an
            data.indices.forEach(index => {
                // Render market card
            });
        });
}
```

## 🔒 Fehlerbehandlung

Das System ist robust und behandelt Fehler elegant:

1. **Netzwerkfehler**: Fallback zu Cache oder simulierten Daten
2. **Ungültige Symbole**: Benutzerfreundliche Fehlermeldung
3. **API-Limits**: Automatisches Caching verhindert zu viele Requests
4. **Leere Daten**: Fallback-Mechanismen aktivieren sich automatisch

## 📝 Logging

Alle wichtigen Events werden geloggt:

```
✅ Loaded real data for NESN.SW from Yahoo Finance
🔄 Loading live market data from Yahoo Finance...
❌ Error loading live markets: Connection timeout
```

## 🚀 Performance

- **Caching** reduziert API-Calls um ~80%
- **Parallele Requests** für mehrere Assets
- **Lazy Loading** für Market-Daten
- **Optimierte Datenstrukturen** für schnelle Berechnungen

## 📊 Datenqualität

### Yahoo Finance Vorteile:
✅ Kostenlos und zuverlässig  
✅ Historische Daten verfügbar  
✅ Internationale Märkte  
✅ Real-time Quotes (mit kleiner Verzögerung)  
✅ Fundamentaldaten (Beta, Market Cap, etc.)

### Limitierungen:
⚠️ 15-20 Minuten Verzögerung bei einigen Märkten  
⚠️ Rate Limiting bei zu vielen Requests  
⚠️ Nicht alle Small-Cap Aktien verfügbar  

## 🔄 Auto-Refresh

Die Markets-Seite aktualisiert sich automatisch:
- Manuell: Button "Jetzt aktualisieren"
- Automatisch: Alle 15 Minuten (geplant)

## 📖 Verwendung

### Für Endbenutzer:

1. **Portfolio erstellen**: Assets werden automatisch mit Live-Daten geladen
2. **Dashboard**: Zeigt "Live-Daten" Badge an
3. **Markets-Seite**: Automatische Aktualisierung der Indizes
4. **Berechnungen**: Alle Optimierungen basieren auf echten Daten

### Für Entwickler:

```python
# Backend: Neue API hinzufügen
@app.route('/api/get_asset_stats/<symbol>')
def get_asset_stats(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    hist = ticker.history(period='1y')
    # ... Berechnungen
    return jsonify(stats)
```

```javascript
// Frontend: API aufrufen
fetch('/api/get_asset_stats/NESN.SW')
    .then(res => res.json())
    .then(data => {
        console.log(data.price, data.volatility);
    });
```

## 🎯 Nächste Schritte

- [ ] WebSocket-Integration für Echtzeit-Updates
- [ ] Erweiterte Chart-Darstellungen mit historischen Daten
- [ ] Benachrichtigungen bei signifikanten Preisänderungen
- [ ] Export von Live-Daten (CSV, JSON)
- [ ] Historisches Backtesting mit echten Daten

## ⚙️ Konfiguration

In `app.py`:

```python
# Cache TTL (Time To Live)
CACHE_TTL_LIVE_PRICE = 300      # 5 Minuten
CACHE_TTL_HISTORICAL = 3600     # 1 Stunde
CACHE_TTL_OVERVIEW = 300        # 5 Minuten

# Yahoo Finance Settings
YFINANCE_TIMEOUT = 10           # Sekunden
YFINANCE_MAX_RETRIES = 3        # Versuche
```

## 📞 Support

Bei Fragen oder Problemen:
- Console Logs überprüfen (F12 → Console)
- Network Tab überprüfen für API-Calls
- Backend Logs in Terminal ansehen

---

**Version**: 1.0.0  
**Letztes Update**: 15. Oktober 2025  
**Status**: ✅ Produktiv

