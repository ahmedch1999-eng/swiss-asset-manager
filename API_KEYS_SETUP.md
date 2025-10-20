# 🔑 API KEYS SETUP GUIDE

## ⚡ QUICK START (2 Minuten)

**WICHTIG:** Yahoo Finance funktioniert OHNE API-Key! Du kannst die App sofort nutzen.

Für zusätzliche Redundanz und höhere Limits kannst du optionale API-Keys hinzufügen.

---

## 🎯 SOFORT NUTZBAR - Keine Keys erforderlich!

Die App funktioniert out-of-the-box mit **Yahoo Finance** (kostenlos, kein Key nötig):

```bash
# Starte die App - funktioniert sofort!
python app.py
```

✅ **Yahoo Finance bietet:**
- Echtzeitdaten für Aktien, ETFs, Indizes
- Historische Daten
- Volumen & Market Cap
- KOSTENLOS & UNBEGRENZT

---

## 🚀 OPTIONAL: Zusätzliche Datenquellen

Für professionelle Nutzung mit Redundanz und erweiterten Daten:

### Schritt 1: Kostenlose API-Keys erhalten

| Service | Limits (FREE) | Registrierung | Empfehlung |
|---------|---------------|---------------|------------|
| **Alpha Vantage** | 5/min, 500/day | [Hier registrieren](https://www.alphavantage.co/support/#api-key) | ⭐⭐⭐ Gut für US-Aktien |
| **Finnhub** | 60/min, 1000/day | [Hier registrieren](https://finnhub.io/register) | ⭐⭐⭐⭐⭐ BESTE Option! |
| **Twelve Data** | 8/min, 800/day | [Hier registrieren](https://twelvedata.com/pricing) | ⭐⭐⭐⭐ Gut für Forex |
| **EODHD** | 1/min, 20/day | [Hier registrieren](https://eodhd.com/pricing) | ⭐⭐ Backup nur |
| **FMP** | 2/min, 250/day | [Hier registrieren](https://site.financialmodelingprep.com/developer/docs/pricing) | ⭐⭐⭐ Gut für Fundamentals |

### Schritt 2: .env Datei erstellen

```bash
# Kopiere die Vorlage
cp .env.example .env

# Bearbeite die Datei
nano .env
```

### Schritt 3: Keys eintragen

```bash
# .env Datei
ALPHA_VANTAGE_API_KEY=DEIN_KEY_HIER
FINNHUB_API_KEY=DEIN_KEY_HIER
TWELVE_DATA_API_KEY=DEIN_KEY_HIER
EODHD_API_KEY=DEIN_KEY_HIER
FMP_API_KEY=DEIN_KEY_HIER
```

### Schritt 4: App neu starten

```bash
python app.py
```

Die App erkennt automatisch verfügbare API-Keys und nutzt sie als Backup/Redundanz zu Yahoo Finance.

---

## 📊 DATENQUELLEN-STRATEGIE

Die App verwendet intelligentes Multi-Source Routing:

```
1. CACHE CHECK (5 Min TTL)
   ↓
2. YAHOO FINANCE (Primary - kostenlos)
   ↓ (bei Fehler)
3. FINNHUB (wenn Key vorhanden)
   ↓ (bei Fehler)
4. ALPHA VANTAGE (wenn Key vorhanden)
   ↓ (bei Fehler)
5. TWELVE DATA (wenn Key vorhanden)
   ↓ (bei Fehler)
6. ERROR RESPONSE (KEINE Simulation!)
```

---

## ✅ EMPFOHLENE KONFIGURATION

### Für Entwicklung/Testing:
```bash
# Nur Yahoo Finance - KEINE KEYS NÖTIG
# Funktioniert perfekt!
```

### Für Produktion:
```bash
# Yahoo Finance + Finnhub
FINNHUB_API_KEY=dein_key_hier
```

### Für High-Availability:
```bash
# Alle Keys für maximale Redundanz
FINNHUB_API_KEY=key1
ALPHA_VANTAGE_API_KEY=key2
TWELVE_DATA_API_KEY=key3
FMP_API_KEY=key4
```

---

## 🔒 SICHERHEIT

**WICHTIG:**

1. ✅ `.env` ist bereits in `.gitignore`
2. ✅ NIEMALS `.env` committen!
3. ✅ Keys regelmäßig rotieren
4. ✅ Produktions-Keys separat von Test-Keys

---

## 🧪 TESTEN DER KONFIGURATION

### Test 1: Yahoo Finance (immer verfügbar)
```bash
curl "http://localhost:5000/get_live_data/AAPL" | jq
```

Erwartete Response:
```json
{
  "symbol": "AAPL",
  "price": 234.52,
  "change": 1.25,
  "source": "Yahoo Finance (Real)",
  "data_quality": "verified"
}
```

### Test 2: API-Keys überprüfen
```bash
# In Python Console
from dotenv import load_dotenv
import os
load_dotenv()

print("Alpha Vantage:", "✅" if os.getenv('ALPHA_VANTAGE_API_KEY') else "❌")
print("Finnhub:", "✅" if os.getenv('FINNHUB_API_KEY') else "❌")
```

---

## ❓ TROUBLESHOOTING

### Problem: "No data available"
**Lösung:**
- Yahoo Finance ist down (selten)
- Symbol ist falsch (z.B. `APPL` statt `AAPL`)
- Netzwerkproblem
- Teste mit bekanntem Symbol: `AAPL`, `GOOGL`, `MSFT`

### Problem: Rate Limits erreicht
**Lösung:**
- Cache wird automatisch verwendet (5 Min TTL)
- Füge zusätzliche API-Keys hinzu
- Erhöhe Cache-TTL in `.env`: `CACHE_TTL=600` (10 Min)

### Problem: Ungültige API-Keys
**Lösung:**
- Keys neu generieren
- Whitespace/Newlines entfernen
- Keys in Quotes setzen wenn Sonderzeichen: `KEY="abc123!@#"`

---

## 📚 WEITERE RESSOURCEN

- [Yahoo Finance API Docs](https://github.com/ranaroussi/yfinance)
- [Alpha Vantage Docs](https://www.alphavantage.co/documentation/)
- [Finnhub Docs](https://finnhub.io/docs/api)
- [Twelve Data Docs](https://twelvedata.com/docs)

---

## 💡 PRO TIPPS

1. **Starte mit Yahoo Finance** - Funktioniert sofort, keine Keys nötig
2. **Füge Finnhub hinzu** - Beste kostenlose Alternative (60 calls/min!)
3. **Monitor deine Limits** - Logs zeigen welche API verwendet wurde
4. **Cache nutzen** - 5 Min TTL spart API-Calls
5. **Produktions-Keys** - Kaufe Premium wenn du >1000 calls/day brauchst

---

**FERTIG! 🎉**

Die App ist jetzt für echte Marktdaten konfiguriert!
