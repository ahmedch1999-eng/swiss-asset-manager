# ✏️ QUICK EDIT GUIDE - Swiss Asset Pro

## 🎯 Was darf ich editieren?

### ✅ EDITIERBAR: Hauptseiten Content (Zeilen 4067-4071)

```html
<!-- Zwischen diesen Markierungen: -->
<!-- ✏️ EDITABLE SECTION START -->

<div class="gs-content-placeholder" id="gsPageContent" style="...">
    <!-- HIER DARF ALLES GEÄNDERT WERDEN -->
    <i class="fas fa-rocket" style="..."></i>
    <h2>Dein Titel</h2>
    <p>Dein Text</p>
    <!-- Füge Listen, Bilder, etc. hinzu -->
</div>

<!-- ✏️ EDITABLE SECTION END -->
```

### ❌ NICHT EDITIERBAR (ohne explizite Erlaubnis):

- ❌ **Login Screen** (Zeilen 3315-3336) - Password Protection
- ❌ **Welcome Screen & Animation** (Zeilen 3338-3360) - Stock Line Animation
- ❌ **Landing Page** (Zeilen 3554-3738) - Alle 13 Tiles, Hero Section
- ❌ **CSS Styles** (Zeilen 600-4018) - Komplettes Styling
- ❌ **Header & Navigation** (Zeilen 4020-4055) - Logo, Links, Client Access
- ❌ **Footer** (Zeilen 4090-4149) - Footer Content, Links
- ❌ **JavaScript** (Zeilen 4152+) - Alle Funktionen, Transitions
- ❌ **Main Container Wrapper** - `<main>`, `<div class="gs-main-container">`
- ❌ **Page Title** - `<h1 class="gs-page-title">`
- ❌ **Grey Box Container** - `<div class="gs-page-content">`

---

## 📍 Wo finde ich den editierbaren Bereich?

**Im Code suchen nach:**
```
<!-- ✏️ EDITABLE SECTION START -->
```

**Endet bei:**
```
<!-- ✏️ EDITABLE SECTION END -->
```

---

## 💡 Beispiel Content-Änderung:

### Vorher:
```html
<div class="gs-content-placeholder" id="gsPageContent" style="...">
    <i class="fas fa-rocket" style="..."></i>
    <h2>Erste Schritte</h2>
    <p>Alles, was Sie wissen müssen...</p>
</div>
```

### Nachher (z.B. mit Liste):
```html
<div class="gs-content-placeholder" id="gsPageContent" style="...">
    <i class="fas fa-chart-line" style="font-size: 48px; color: #8b7355;"></i>
    <h2>Portfolio Dashboard</h2>
    <p>Übersicht Ihrer Investments</p>
    
    <ul style="text-align: left; max-width: 600px; margin: 30px auto;">
        <li>Gesamtwert: CHF 1.2M</li>
        <li>Performance: +12.5%</li>
        <li>Assets: 25</li>
    </ul>
    
    <button onclick="alert('Demo')">Details anzeigen</button>
</div>
```

---

## 🎨 Verfügbare Icons (Font Awesome):

- `fa-rocket` - Rakete
- `fa-chart-line` - Chart
- `fa-briefcase` - Koffer (Portfolio)
- `fa-cogs` - Einstellungen
- `fa-flask` - Labor (Simulation)
- `fa-chart-bar` - Balkendiagramm
- `fa-coins` - Münzen
- `fa-newspaper` - News
- `fa-university` - Bank
- `fa-book` - Buch

**Verwendung:**
```html
<i class="fas fa-ICONNAME" style="font-size: 48px; color: #8b7355;"></i>
```

---

## 🚀 Alle 13 Hauptseiten:

1. **Getting Started** - `loadGSPage('getting-started')`
2. **Dashboard** - `loadGSPage('dashboard')`
3. **Portfolio** - `loadGSPage('portfolio')`
4. **Strategie** - `loadGSPage('strategie')`
5. **Simulation** - `loadGSPage('simulation')`
6. **Backtesting** - `loadGSPage('backtesting')`
7. **Investing** - `loadGSPage('investing')`
8. **Bericht** - `loadGSPage('bericht')`
9. **Märkte & News** - `loadGSPage('maerkte-news')`
10. **Asset-Klassen** - `loadGSPage('assetsklassen')`
11. **Methodik** - `loadGSPage('methodik')`
12. **Black-Litterman** - `loadGSPage('black-litterman')`
13. **Über Mich** - `loadGSPage('ueber-mich')`

**Jede Seite hat den gleichen editierbaren Bereich!**

---

## ⚠️ WICHTIG:

Wenn du sagst **"Ändere die Getting Started Seite"**, ändere ich **NUR** den Content zwischen den `✏️ EDITABLE SECTION` Markierungen!

Wenn du **CSS, Header, Footer, JavaScript** ändern willst, sage **explizit**:
- "Ändere das CSS für..."
- "Modifiziere den Header..."
- "Unlock protected sections"

---

**Erstellt**: 14. Oktober 2025  
**Code Version**: ALPEN Backup ✅

