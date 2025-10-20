# 🔒 CODE PROTECTION RULES - Swiss Asset Pro

## ⚠️ WICHTIGE REGEL FÜR AI-ASSISTENTEN
**Diese Bereiche dürfen NUR auf EXPLIZITE Anweisung des Benutzers geändert werden!**

---

## 🔒 GESCHÜTZTE BEREICHE (NICHT OHNE ERLAUBNIS ÄNDERN)

### 1. **Flask Backend & Konfiguration**
- **Zeilen**: 1-600
- **Inhalt**: 
  - Imports
  - Flask App Setup
  - Socket.IO Konfiguration
  - Datenbank Funktionen
  - Cache System
  - API Routes
  - Business Logic
  
❌ **NICHT ÄNDERN** ohne explizite Anweisung

---

### 2. **Login Screen**
- **Zeilen**: ca. 3315-3336
- **Inhalt**:
  - Password Protection
  - Login Form
  - Authentication Logic
  - Swiss Asset Pro Logo
  - Input Fields & Button
  
❌ **NICHT ÄNDERN** - Login funktioniert perfekt

---

### 3. **Welcome Screen & Animation**
- **Zeilen**: ca. 3338-3360
- **Inhalt**:
  - Welcome Screen mit Logo
  - Stock Line Animation (verschwindende Linie)
  - Loading Bar
  - Fade-Out Effekte
  - Timing Logic
  
❌ **NICHT ÄNDERN** - Animation ist perfekt optimiert

---

### 4. **Landing Page (Komplett)**
- **Zeilen**: ca. 3554-3738
- **Inhalt**:
  - Hero Section mit Logo
  - Welcome Text
  - Alle 13 Tiles mit Bildern:
    1. Getting Started
    2. Dashboard
    3. Portfolio
    4. Strategie
    5. Simulation
    6. Backtesting
    7. Investing
    8. Bericht
    9. Märkte & News
    10. Asset-Klassen
    11. Methodik
    12. Black-Litterman
    13. Über Mich
  - Footer auf Landing Page
  
❌ **NICHT ÄNDERN** - Layout und Design sind final

---

### 5. **CSS Styling (Komplett)**
- **Zeilen**: ca. 600-3800
- **Inhalt**:
  - Alle `<style>` Tags
  - Animation CSS
  - Landing Page Styles
  - Header/Navigation Styles
  - Footer Styles
  - Main Content Container Styles
  - Mobile Responsive Styles
  
❌ **NICHT ÄNDERN** - CSS ist perfekt formatiert und optimiert

---

### 6. **HTML Struktur - Header**
- **Zeilen**: ca. 4020-4055
- **Inhalt**:
  - Logo
  - Navigation (alle Links)
  - "Client Access" Button
  - Header Container
  
❌ **NICHT ÄNDERN** - Layout und Navigation sind final

---

### 7. **HTML Struktur - Footer**
- **Zeilen**: ca. 4090-4149
- **Inhalt**:
  - Footer Logo
  - Service Links
  - Resources Links
  - Company Links
  - Copyright
  
❌ **NICHT ÄNDERN** - Footer ist final gestaltet

---

### 8. **JavaScript Funktionen**
- **Zeilen**: ca. 4152-4380
- **Inhalt**:
  - Animation Logik
  - Page Navigation (`showGettingStartedPage`, `backToLandingPage`)
  - Content Loading (`loadGSPage`)
  - Password Verification
  - Cache Buster
  
❌ **NICHT ÄNDERN** - Alle Transitions sind optimiert

---

### 9. **Main Content Container Wrapper**
- **Zeilen**: 4057-4062, 4078-4088
- **Code**:
```html
<main class="gs-main">
    <div class="gs-main-container" style="...">
        <h1 class="gs-page-title" id="gsPageTitle" style="...">
        <div class="gs-page-content" style="...">
            <!-- NUR DIESER INNERE TEIL IST EDITIERBAR -->
        </div>
    </div>
</main>
```

❌ **Container, Title, und Wrapper NICHT ÄNDERN**

---

## ✏️ EDITIERBARER BEREICH (Darf geändert werden)

### **Main Content Bereich - Innerer Content**
- **Zeilen**: ca. 4050-4054
- **Bereich**: Innerhalb von `<div class="gs-content-placeholder" id="gsPageContent">`

```html
<!-- ✏️ EDITIERBAR START -->
<div class="gs-content-placeholder" id="gsPageContent" style="...">
    <i class="fas fa-rocket" style="..."></i>
    <h2 style="...">Erste Schritte</h2>
    <p style="...">Alles, was Sie wissen müssen...</p>
</div>
<!-- ✏️ EDITIERBAR END -->
```

✅ **HIER DARF GEÄNDERT WERDEN**:
- Icon und Farbe
- Überschrift Text
- Paragraph Text
- Zusätzliche Inhalte hinzufügen

**Gilt für alle Hauptseiten**:
- Getting Started
- Dashboard
- Portfolio
- Strategie
- Simulation
- Backtesting
- Investing
- Bericht
- Märkte & News
- Asset-Klassen
- Methodik
- Black-Litterman
- Über Mich

---

## 📋 WORKFLOW FÜR CONTENT-ÄNDERUNGEN

### Wenn Benutzer sagt: "Ändere den Content auf Getting Started"

1. ✅ **ERLAUBT**: 
   - Text im `<div id="gsPageContent">` ändern
   - Icon ändern
   - Neue Paragraphen/Listen hinzufügen

2. ❌ **NICHT ERLAUBT**:
   - CSS ändern
   - Container Padding ändern
   - Header/Footer ändern
   - JavaScript ändern
   - Page Title Format ändern

### Wenn Benutzer sagt: "Ändere das Layout"

❓ **NACHFRAGEN**:
"Möchtest du:
- A) Nur den Content-Bereich Layout ändern? (erlaubt)
- B) Das gesamte Seiten-Layout ändern? (benötigt Erlaubnis für geschützte Bereiche)"

---

## 🚨 AUSNAHMEN - Nur wenn explizit erlaubt

Der Benutzer kann geschützte Bereiche freigeben mit:
- "Ändere das CSS für..."
- "Passe die Navigation an..."
- "Modifiziere die Animation..."
- "Ändere den Header/Footer..."
- "Unlock protected sections"

Dann erst dürfen diese Bereiche geändert werden!

---

## 🔧 KONFIGURATION (Erlaubt zu ändern)

- **Port Nummer**: Zeile 4440
- **Cache Buster**: Zeile 607
- **Password**: Zeile ~550

Diese dürfen bei Bedarf angepasst werden.

---

## 📝 ZUSAMMENFASSUNG

### 🔒 GESCHÜTZT (95% des Codes):
- Flask Backend
- Alle CSS
- Header & Navigation
- Footer
- JavaScript
- Landing Page & Animation
- HTML Container Struktur

### ✏️ EDITIERBAR (5% des Codes):
- Main Content Bereich (innerhalb `#gsPageContent`)
- Für alle 13 Hauptseiten

---

**Erstellt**: 14. Oktober 2025
**Letztes Update**: Nach ALPEN Backup
**Status**: Alle Optimierungen abgeschlossen ✅

