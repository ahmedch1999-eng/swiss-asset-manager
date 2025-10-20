# Swiss Asset Pro - Deployment Guide

## 🚀 PWA-Optimierte Deployment-Anleitung

### Übersicht
Diese Anleitung beschreibt die vollständige Deployment-Strategie für Swiss Asset Pro als Progressive Web App (PWA) mit iOS App-ähnlicher Erfahrung.

## 📋 Voraussetzungen

### System-Anforderungen
- **Node.js**: 18.x oder höher
- **Python**: 3.8 oder höher
- **Docker**: 20.x oder höher
- **Docker Compose**: 2.x oder höher
- **Nginx**: 1.18 oder höher (optional)

### Entwicklungsumgebung
- **Git**: Für Versionskontrolle
- **VS Code**: Empfohlener Editor
- **Chrome DevTools**: Für PWA-Testing

## 🏗️ Lokale Entwicklung

### 1. Repository klonen
```bash
git clone https://github.com/your-username/swiss-asset-manager.git
cd swiss-asset-manager
```

### 2. Abhängigkeiten installieren
```bash
# Python-Abhängigkeiten
pip install -r requirements.txt

# Node.js-Abhängigkeiten (für Tests)
npm install
```

### 3. Anwendung starten
```bash
# Entwicklungsserver
python app.py

# Oder mit Docker
docker-compose up -d
```

### 4. PWA testen
```bash
# Lighthouse CI lokal ausführen
npx lhci autorun

# Performance-Tests
k6 run performance-tests.js
```

## 🐳 Docker Deployment

### 1. Produktions-Image erstellen
```bash
# Multi-stage Build
docker build -f Dockerfile.production -t swiss-asset-pro:latest .

# Image testen
docker run -p 3000:3000 swiss-asset-pro:latest
```

### 2. Docker Compose für Produktion
```bash
# Produktions-Stack starten
docker-compose -f docker-compose.prod.yml up -d

# Logs überwachen
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. Nginx als Reverse Proxy
```bash
# Nginx-Konfiguration kopieren
cp nginx.conf /etc/nginx/nginx.conf

# Nginx neu starten
sudo systemctl reload nginx
```

## ☁️ Cloud Deployment

### Heroku
```bash
# Heroku CLI installieren
npm install -g heroku

# App erstellen
heroku create swiss-asset-pro

# Environment Variables setzen
heroku config:set FLASK_ENV=production
heroku config:set PORT=3000

# Deployen
git push heroku main
```

### AWS ECS
```bash
# ECS CLI installieren
pip install awscli

# Task Definition erstellen
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Service erstellen
aws ecs create-service --cluster swiss-asset-pro --service-name swiss-asset-pro-service --task-definition swiss-asset-pro:1
```

### Google Cloud Run
```bash
# Google Cloud CLI installieren
curl https://sdk.cloud.google.com | bash

# App deployen
gcloud run deploy swiss-asset-pro --source . --platform managed --region europe-west1
```

## 📱 PWA-spezifische Konfiguration

### 1. Service Worker registrieren
```javascript
// Automatisch in app.py integriert
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js');
}
```

### 2. Manifest.json konfigurieren
```json
{
  "name": "Swiss Asset Pro",
  "short_name": "SwissAssetPro",
  "display": "standalone",
  "theme_color": "#8A2BE2",
  "background_color": "#0A0A0A"
}
```

### 3. iOS-spezifische Meta-Tags
```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

## 🔧 CI/CD Pipeline

### GitHub Actions
Die CI/CD-Pipeline ist in `.github/workflows/ci-cd.yml` konfiguriert und umfasst:

1. **Tests**: Unit, Integration, E2E
2. **Linting**: Flake8, Black
3. **Security**: Trivy vulnerability scanning
4. **Performance**: Lighthouse CI
5. **Deployment**: Staging → Production

### Pipeline ausführen
```bash
# Lokal testen
act -j test

# Mit GitHub Actions
git push origin main
```

## 📊 Monitoring & Observability

### 1. Prometheus + Grafana
```bash
# Monitoring-Stack starten
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

# Grafana Dashboard: http://localhost:3001
# Prometheus: http://localhost:9090
```

### 2. Application Performance Monitoring
- **Web Vitals**: LCP, FID, CLS
- **Error Tracking**: JavaScript-Fehler, API-Fehler
- **User Analytics**: Page Views, User Interactions
- **Performance Metrics**: Load Times, Resource Sizes

### 3. Logs
```bash
# Application Logs
docker-compose logs -f swiss-asset-pro

# Nginx Logs
docker-compose logs -f nginx

# System Logs
journalctl -u swiss-asset-pro -f
```

## 🔒 Sicherheit

### 1. HTTPS-Konfiguration
```nginx
# SSL-Zertifikat hinzufügen
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### 2. Security Headers
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

### 3. Rate Limiting
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

## 🚀 Performance-Optimierung

### 1. Caching-Strategie
- **Static Assets**: 1 Jahr Cache
- **API Responses**: 5 Minuten Cache
- **Service Worker**: No-Cache

### 2. Compression
```nginx
gzip on;
gzip_comp_level 6;
gzip_types text/plain text/css application/json;
```

### 3. CDN-Integration
```bash
# CloudFlare CDN
# AWS CloudFront
# Google Cloud CDN
```

## 📱 iOS App-ähnliche Erfahrung

### 1. Add to Home Screen
- Automatische Install-Prompts
- iOS-spezifische Anweisungen
- Splash Screens für alle Geräte

### 2. Offline-Funktionalität
- Service Worker mit Cache-Strategien
- Offline-Fallback-Seiten
- Background Sync

### 3. Touch-Optimierung
- 44px Mindest-Touch-Targets
- Passive Event Listeners
- 60fps-Animationen

## 🧪 Testing

### 1. Unit Tests
```bash
pytest tests/unit/
```

### 2. Integration Tests
```bash
pytest tests/integration/
```

### 3. E2E Tests
```bash
pytest tests/e2e/
```

### 4. Performance Tests
```bash
k6 run performance-tests.js
```

### 5. Lighthouse CI
```bash
npx lhci autorun
```

## 📈 Monitoring & Alerts

### 1. Health Checks
```bash
# Application Health
curl http://localhost:3000/health

# Database Health
curl http://localhost:3000/health/db

# Cache Health
curl http://localhost:3000/health/cache
```

### 2. Alerting Rules
```yaml
# Prometheus Alert Rules
groups:
  - name: swiss-asset-pro
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
```

## 🔄 Rollback-Strategie

### 1. Blue-Green Deployment
```bash
# Neue Version deployen
docker-compose -f docker-compose.prod.yml up -d --scale swiss-asset-pro=2

# Traffic umleiten
# Alte Version stoppen
```

### 2. Canary Releases
```bash
# 10% Traffic auf neue Version
# Monitoring für 30 Minuten
# Vollständige Umstellung
```

## 📚 Troubleshooting

### Häufige Probleme

#### 1. Service Worker nicht registriert
```bash
# Browser DevTools → Application → Service Workers
# Cache leeren und neu laden
```

#### 2. PWA nicht installierbar
```bash
# Manifest.json prüfen
# HTTPS erforderlich
# Service Worker aktiv
```

#### 3. Performance-Probleme
```bash
# Lighthouse CI ausführen
# Bundle-Größe analysieren
# Critical Path optimieren
```

### Debug-Commands
```bash
# Container-Logs
docker logs swiss-asset-pro

# Performance-Metriken
curl http://localhost:3000/metrics

# Health-Status
curl http://localhost:3000/health
```

## 📞 Support

### Kontakt
- **GitHub Issues**: [Repository Issues](https://github.com/your-username/swiss-asset-manager/issues)
- **Email**: support@swissassetpro.com
- **Documentation**: [Wiki](https://github.com/your-username/swiss-asset-manager/wiki)

### Nützliche Links
- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)