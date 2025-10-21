# 🏦 Swiss Asset Pro

**Professionelle Portfolio-Management-Plattform mit Echtzeit-Datenanalyse**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

---

## 🌟 Features

### 📊 **Portfolio-Management**
- ✅ Echtzeit-Kursdaten (Yahoo Finance)
- ✅ Schweizer Aktien (SMI, Mid Caps, Small Caps)
- ✅ Internationale Indizes (S&P 500, Nasdaq, etc.)
- ✅ Rohstoffe & Währungen

### 🎯 **Analysen & Optimierung**
- ✅ Portfolio-Optimierung (Markowitz, Black-Litterman)
- ✅ Monte Carlo Simulation (1000+ Simulationen)
- ✅ Strategieanalyse (Max Sharpe, Min Variance, Risk Parity)
- ✅ Backtesting & Performance-Tracking
- ✅ Stress-Testing (Crash-Szenarien)

### 📄 **Reporting**
- ✅ PDF Export mit allen Berechnungen
- ✅ Live Dashboard mit Kennzahlen
- ✅ Transparenz-Seite (System-Diagnose)

### 📱 **Progressive Web App (PWA)**
- ✅ Installierbar auf iOS/Android
- ✅ Offline-Fähigkeit
- ✅ App-ähnliches Feeling (kein Browser-UI)
- ✅ Responsive Design (Mobile, Tablet, Desktop)

---

## 🚀 Installation

### **1. Repository klonen**
```bash
git clone https://github.com/DEIN_USERNAME/swiss-asset-pro.git
cd swiss-asset-pro
```

### **2. Virtual Environment erstellen**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# oder
venv\Scripts\activate  # Windows
```

### **3. Dependencies installieren**
```bash
pip install -r requirements.txt
```

### **4. Environment Variables konfigurieren**
```bash
cp env.example .env
```

**Dann `.env` bearbeiten und eigene Werte eintragen:**
```bash
APP_PASSWORD=dein_sicheres_passwort
FLASK_SECRET_KEY=ein_langer_zufälliger_schlüssel_mindestens_32_zeichen
PORT=5077
```

### **5. Icons generieren (optional)**
```bash
python create_swissap_icon.py
```

### **6. App starten**
```bash
python app.py
```

App läuft auf: **http://127.0.0.1:5077**

---

## 📋 Requirements

- **Python:** 3.11+
- **Flask:** 3.0+
- **yfinance:** Für Echtzeit-Marktdaten
- **pandas, numpy, scipy:** Für Berechnungen
- **reportlab:** Für PDF-Export
- **PIL/Pillow:** Für Icon-Generierung

Siehe `requirements.txt` für vollständige Liste.

---

## 🎨 Screenshots

*Screenshots werden hier eingefügt*

---

## 📱 Mobile Installation (iOS)

1. Öffne die App in Safari
2. Tippe auf **Teilen-Button** (□↑)
3. Wähle **"Zum Home-Bildschirm"**
4. App wird installiert als **"SwissAP"**
5. ✅ Kein Safari-Balken, App-ähnliches Feeling!

---

## 🔐 Sicherheit

- ✅ Environment Variables für Secrets
- ✅ `.env` wird NICHT auf GitHub hochgeladen
- ✅ `env.example` als Template verfügbar
- ✅ Session-basierte Authentifizierung
- ✅ CORS-Schutz
- ✅ Input-Validierung mit Pydantic

---

## 🏗️ Architektur

```
swiss-asset-pro/
├── app.py                    # Haupt-Flask-App
├── requirements.txt          # Python Dependencies
├── manifest.json            # PWA Manifest
├── .env                     # Secrets (NICHT in Git!)
├── env.example              # Template für .env
├── create_swissap_icon.py   # Icon Generator
├── static/                  # Static Files
│   ├── profile.png          # Profilbild
│   ├── icon-*.png          # PWA Icons
│   ├── monitoring.js        # Frontend JS
│   └── Bilder-SAP/         # UI Bilder
├── cache/                   # Cache (ignoriert)
├── logs/                    # Logs (ignoriert)
└── docs/                    # Dokumentation
```

---

## 📚 Dokumentation

- `README.md` - Diese Datei
- `ARCHITECTURE.md` - System-Architektur
- `DEPLOYMENT_GUIDE.md` - Deployment-Anleitung
- `GITHUB_CHECKLIST.md` - GitHub Push Checkliste

---

## 🤝 Contribution

Contributions sind willkommen! Bitte erstelle ein Issue oder Pull Request.

---

## 📄 License

MIT License - siehe LICENSE Datei

---

## 👤 Autor

**Ahmed Choudhary**  
Portfolio- & Finanzanalyst  
📧 ahmedch1999@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/ahmed-choudhary-3a61371b6)

---

## ⚠️ Disclaimer

Diese Plattform ist **keine FINMA-lizenzierte Finanzdienstleistung**. Alle Analysen und Berechnungen dienen ausschließlich **Bildungs- und Informationszwecken**. Keine Anlageberatung. Konsultieren Sie vor Anlageentscheidungen einen qualifizierten Finanzberater.

---

**Viel Erfolg mit Swiss Asset Pro!** 🚀


