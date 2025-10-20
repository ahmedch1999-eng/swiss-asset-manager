# ✅ GitHub Push Checklist

## ⚠️ VOR DEM PUSH - KRITISCH!

### 🔐 **Sicherheit (MUSS!)**

- [ ] **1. Passwort aus Code entfernen**
  - Zeile 337: `PASSWORD = "y4YpFgdLJD1tK19"` → In .env verschieben
  - Code ändern zu: `PASSWORD = os.environ.get('APP_PASSWORD', 'CHANGE_ME')`

- [ ] **2. Secret Key aus Code entfernen**
  - Zeile 161: `app.config['SECRET_KEY'] = '...'` → In .env verschieben
  - Code ändern zu: `app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'CHANGE_ME')`

- [ ] **3. .env Datei erstellen**
  ```bash
  cp env.example .env
  # Dann .env mit echten Werten füllen
  ```

- [ ] **4. Prüfen dass .env in .gitignore ist**
  - ✅ Bereits vorhanden!

---

## 📁 **Ordner-Struktur**

### ✅ **Bereits gut:**
- ✅ `static/` - Alle Bilder, Icons, JS, CSS
- ✅ `templates/` - (nicht verwendet, alles in app.py)
- ✅ `requirements.txt` - Python Dependencies
- ✅ `manifest.json` - PWA Manifest
- ✅ `.gitignore` - Erweitert und komplett

### ⚠️ **Sollten NICHT auf GitHub:**
- ❌ `cache/` - wird ignoriert ✅
- ❌ `logs/` - wird ignoriert ✅
- ❌ `*.db` - wird ignoriert ✅
- ❌ `*_backup*.py` - wird ignoriert ✅
- ❌ `venv/` - wird ignoriert ✅
- ❌ `.env` - wird ignoriert ✅

---

## 📝 **Dokumentation**

### ✅ **Bereits vorhanden:**
- ✅ `README.md` - Hauptdokumentation
- ✅ `QUICK_START.md` - Schnellstart-Anleitung
- ✅ `DEPLOYMENT_GUIDE.md` - Deployment-Infos
- ✅ `ARCHITECTURE.md` - System-Architektur

### 📄 **Für GitHub erstellen:**
- [ ] `GITHUB_README.md` - Spezielle README für GitHub
  - Installation
  - Setup .env
  - Start-Befehle
  - Screenshots
  - Features

---

## 🧪 **Testing**

- [ ] **App startet ohne Fehler**
  ```bash
  python app.py
  ```

- [ ] **Alle Features funktionieren:**
  - [ ] Login
  - [ ] Dashboard
  - [ ] Portfolio-Berechnung
  - [ ] PDF Export
  - [ ] Alle Seiten laden

- [ ] **Icons generiert:**
  ```bash
  python create_swissap_icon.py
  ```

---

## 🚀 **GitHub Push Befehle**

**ERST nach allen Checks oben!**

```bash
# 1. Repository initialisieren (falls noch nicht)
git init

# 2. Alle Dateien hinzufügen
git add .

# 3. Ersten Commit
git commit -m "Initial commit - Swiss Asset Pro v1.0"

# 4. Remote Repository hinzufügen
git remote add origin https://github.com/DEIN_USERNAME/swiss-asset-pro.git

# 5. Push
git push -u origin main
```

---

## 📊 **Was auf GitHub KOMMT:**

✅ **Hauptdateien:**
- `app.py` (OHNE Secrets!)
- `requirements.txt`
- `manifest.json`
- `create_swissap_icon.py`

✅ **Dokumentation:**
- `README.md`
- `env.example` (Template!)
- Alle Markdown-Dateien

✅ **Static Files:**
- `static/` Ordner (Bilder, JS, CSS)
- Icons (nach Generierung)

❌ **NICHT auf GitHub:**
- `.env` (echte Secrets!)
- `*.db` (Datenbanken)
- `cache/` (Cache-Daten)
- `logs/` (Log-Dateien)
- `*_backup*.py` (Backups)
- `venv/` (Dependencies)

---

## 🎯 **NÄCHSTE SCHRITTE:**

1. ✅ Sichere dein aktuelles Passwort (notiere es!)
2. ⚠️ Ich fixe die hardcoded Secrets
3. ✅ Icons generieren
4. ✅ Finaler Test
5. ✅ GitHub Push

**Soll ich die Secrets jetzt fixen?** 🔐

