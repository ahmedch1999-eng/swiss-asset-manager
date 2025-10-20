# BVAR Module - Swiss Asset Pro Integration

## 🎯 Was ist BVAR?

**BVAR (Bayesian Vector Autoregression)** ist ein fortgeschrittenes ökonometrisches Modell, das:
- **Interdependenzen** zwischen mehreren Zeitreihen (Assets) modelliert
- **Zukunftsprognosen** für erwartete Renditen erstellt
- **Robuster** ist als einfache historische Durchschnitte
- Für **Black-Litterman** präzisere π (Prior Returns) liefert

## 📁 Dateistruktur

```
SAP3/
├── bvar_module/
│   ├── __init__.py
│   ├── bvar_service.py       # Core BVAR logic
│   ├── cache/                # Cached results
│   ├── plots/                # IRF plots
│   └── README_BVAR.md        # This file
├── tests/
│   └── test_bvar_service.py  # Unit tests
└── app.py                    # Flask app with BVAR API routes
```

## 🔧 Installation

### Requirements
```bash
pip install statsmodels>=0.13.0
pip install fredapi>=0.4.0

# Optional (for Bayesian mode):
pip install pymc3>=3.11
pip install arviz>=0.12
```

### Environment Variables
```bash
# Optional: FRED API for macro data (10-Year Treasury, etc.)
export FRED_API_KEY="your_fred_api_key_here"

# Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html
```

## 🚀 Wie es funktioniert

### **Workflow:**

```
1. User erstellt Portfolio im Dashboard
   └─> [NESN.SW, NOVN.SW, ROG.SW]

2. User geht auf Black-Litterman Seite
   └─> Klickt "BVAR starten"

3. Backend fetcht historische Daten (2015-heute)
   └─> Yahoo Finance: Monatliche Renditen für alle Assets

4. VAR-Modell Schätzung
   └─> Statsmodels VAR mit nlags=2
   └─> Berechnet Koeffizienten-Matrix A

5. Forecast generieren
   └─> 12 Monate Vorhersage
   └─> Erwartete Renditen pro Asset

6. π (Pi) berechnen
   └─> Durchschnitt der Forecast-Renditen
   └─> Annualisiert (×12 für monatliche Daten)

7. Σ (Sigma) schätzen
   └─> Kovarianz-Matrix aus historischen Daten
   └─> Annualisiert (×12)

8. Black-Litterman mit BVAR π & Σ
   └─> μ_BL = [(τΣ)⁻¹ + P'Ω⁻¹P]⁻¹ × [(τΣ)⁻¹π + P'Ω⁻¹Q]
   └─> w_optimal = (λΣ)⁻¹ μ_BL

9. Frontend zeigt:
   └─> Optimale Gewichte (Bar Chart)
   └─> Erwartete Rendite, Volatilität, Sharpe
```

## 📊 Mathematische Formeln

### **VAR(p) Modell:**
```
y_t = A₁y_{t-1} + A₂y_{t-2} + ... + Aₚy_{t-p} + ε_t

wobei:
y_t = [r_NESN, r_NOVN, r_ROG]' (Returns zum Zeitpunkt t)
A_i = 3×3 Koeffizienten-Matrix für Lag i
ε_t = Innovations (Fehlerterm)
```

### **Forecast (h Schritte voraus):**
```
ŷ_{T+h} = A₁ŷ_{T+h-1} + A₂ŷ_{T+h-2} + ... + Aₚŷ_{T+h-p}
```

### **Expected Returns (π) für Black-Litterman:**
```
π = E[ŷ_{T+1}, ŷ_{T+2}, ..., ŷ_{T+12}]  # Durchschnitt über Forecast

Annualisierung:
π_annual = π_monthly × 12
```

### **Covariance (Σ) für Black-Litterman:**
```
Σ = Cov(y_t)  # Sample covariance

Annualisierung:
Σ_annual = Σ_monthly × 12
```

## 🎓 Vorteile gegenüber historischen Durchschnitten

| Methode | Historisch | BVAR |
|---------|-----------|------|
| **Berücksichtigt Trends** | ❌ Nein | ✅ Ja |
| **Interdependenzen** | ❌ Nein | ✅ Ja (VAR-Koeffizienten) |
| **Forecast** | ❌ Statisch | ✅ Dynamisch |
| **Robustheit** | ❌ Anfällig für Ausreißer | ✅ Glättet Noise |
| **Rechenzeit** | ✅ Schnell | ⚠️  Langsamer (10-30s) |

### **Beispiel:**
```
Historischer Durchschnitt NESN:
μ = average(returns_2015_2025) = 7.5%

BVAR-Forecast NESN:
- Berücksichtigt: NOVN & ROG performen schlecht → NESN wahrscheinlich auch
- Berücksichtigt: Trend der letzten 6 Monate negativ
- π_BVAR = 5.8% (realistischer!)
```

## 🔍 API-Endpunkte

### **1. `/api/bvar_analysis` (POST)**

**Request:**
```json
{
  "portfolio": [
    {"symbol": "NESN.SW", "weight": 0.33},
    {"symbol": "NOVN.SW", "weight": 0.50},
    {"symbol": "ROG.SW", "weight": 0.17}
  ],
  "nlags": 2,
  "forecastSteps": 12,
  "bayesian": false
}
```

**Response:**
```json
{
  "success": true,
  "forecast": [...],
  "pi": [0.058, 0.052, 0.061],
  "sigma": [[0.04, 0.01, 0.015], ...],
  "tickers": ["NESN.SW", "NOVN.SW", "ROG.SW"],
  "metadata": {
    "nlags": 2,
    "generated_at": "2025-10-16T04:30:00Z"
  }
}
```

### **2. `/api/bvar_black_litterman` (POST)**

**Request:**
```json
{
  "portfolio": [...],
  "views": [
    {"asset1": "NESN.SW", "asset2": "NOVN.SW", "expectedOutperformance": 0.02}
  ],
  "nlags": 2,
  "riskAversion": 2.5
}
```

**Response:**
```json
{
  "success": true,
  "method": "BVAR-Enhanced Black-Litterman",
  "optimalWeights": {
    "NESN.SW": 0.38,
    "NOVN.SW": 0.45,
    "ROG.SW": 0.17
  },
  "expectedReturn": 6.8,
  "expectedVolatility": 14.2,
  "sharpeRatio": 0.34
}
```

## ⚙️ Configuration Options

### **nlags** (Lag-Ordnung)
- **1**: Nur vorheriger Monat (simple)
- **2**: Empfohlen für monatliche Daten
- **3-6**: Mehr Lags → mehr Parameter → braucht mehr Daten

### **forecastSteps** (Forecast-Horizon)
- **6**: Kurzfristig (6 Monate)
- **12**: Mittelfristig (1 Jahr) - Empfohlen
- **24**: Langfristig (2 Jahre) - Weniger genau

### **bayesian** (PyMC3 Mode)
- **False**: Klassische VAR (schnell, ~5-10s)
- **True**: Bayesian VAR (langsam, ~2-5 Minuten, braucht pymc3)

## 🧪 Testing

```bash
cd /Users/achi/Desktop/SAP3
python tests/test_bvar_service.py
```

Oder mit pytest:
```bash
pytest tests/test_bvar_service.py -v
```

## 📈 Performance

**Benchmark (MacBook Pro M1, 3 Assets, 2015-2025):**
- Data fetch: ~3s
- VAR estimation: ~2s
- Forecast generation: ~1s
- **Total: ~6-8 Sekunden**

**Mit 10 Assets:**
- Total: ~15-20 Sekunden

## ⚠️ Limitationen

1. **Monatliche Frequenz:** Aktuell nur FREQ='M', könnte auf 'W' (weekly) oder 'D' (daily) erweitert werden
2. **Stationarität:** VAR benötigt stationäre Daten; Returns sind meist stationär, aber nicht immer
3. **Sample Size:** Braucht min. 50-100 Beobachtungen für robuste Schätzung
4. **Computational Cost:** Bayesian mode ist sehr langsam (für Produktion in Background-Job)

## 🔮 Zukünftige Erweiterungen

### **Geplant:**
- [ ] **VECM** (Vector Error Correction Model) für kointegrierte Assets
- [ ] **Strukturelle VAR** (SVAR) mit ökonomischen Restriktionen
- [ ] **Rolling Window** BVAR für adaptive Forecasts
- [ ] **Exogene Variablen** (Interest Rates, VIX, etc.)
- [ ] **Automatic Lag Selection** (AIC/BIC Kriterien)

### **Nice-to-Have:**
- [ ] **Live BVAR Dashboard** (eigene Seite mit IRF-Plots)
- [ ] **BVAR vs. Historical** Vergleichstabelle
- [ ] **Granger Causality Tests** (Welches Asset treibt andere?)
- [ ] **Variance Decomposition** Visualisierung

## 📚 Referenzen

1. **Black, F., & Litterman, R. (1992):** "Global Portfolio Optimization", Financial Analysts Journal
2. **Litterman, R. (2003):** "Modern Investment Management: An Equilibrium Approach"
3. **Lütkepohl, H. (2005):** "New Introduction to Multiple Time Series Analysis"
4. **Sims, C. A. (1980):** "Macroeconomics and Reality", Econometrica

## 💡 Best Practices

1. **Datenqualität:** Min. 5 Jahre Historie für robuste Schätzung
2. **Lag-Wahl:** Start mit nlags=2, teste AIC/BIC für optimale Wahl
3. **Stationarität-Check:** Verwende Augmented Dickey-Fuller Test bei Unsicherheit
4. **Backtesting:** Validiere BVAR-Forecasts mit Out-of-Sample Tests
5. **Monitoring:** Logge Forecast-Errors und re-estimate regelmäßig

## 🛡️ Error Handling

```python
# Die API hat eingebautes Error Handling:
try:
    result = run_bvar_pipeline(config)
except ValueError as e:
    # Nicht genug Daten
    return fallback_to_historical_means()
except RuntimeError as e:
    # API fetch failed
    return use_cached_results()
except Exception as e:
    # Unbekannter Fehler
    log_error(e)
    return graceful_degradation()
```

## 🎯 Integration Checklist

- [x] BVAR Service erstellt
- [x] API-Endpunkte in app.py
- [x] Frontend auf Black-Litterman Seite
- [x] Tests geschrieben
- [x] README dokumentiert
- [ ] FRED API-Key konfiguriert (optional)
- [ ] pytest in CI/CD Pipeline
- [ ] Production: Background Worker für BVAR

## 📞 Support

Bei Fragen oder Problemen:
- Check logs in `bvar_module/cache/`
- Teste mit `tests/test_bvar_service.py`
- Debug-Mode: Set `logging.DEBUG` in bvar_service.py

---

**Version:** 1.0.0  
**Erstellt:** 2025-10-16  
**Author:** Ahmed Choudhary  
**Lizenz:** Proprietär (Swiss Asset Pro)






