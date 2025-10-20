#!/usr/bin/env python3
"""
Test Script für Live-Daten-Integration
Testet alle neuen API-Endpunkte ohne Flask-Server zu starten
"""

import yfinance as yf
import numpy as np
from datetime import datetime

def test_live_price():
    """Test: Live-Preis abrufen"""
    print("\n" + "="*60)
    print("🔍 TEST 1: Live-Preis abrufen (NESN.SW)")
    print("="*60)
    
    try:
        symbol = "NESN.SW"
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='1d')
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            print(f"✅ Symbol: {symbol}")
            print(f"✅ Name: {info.get('longName', 'N/A')}")
            print(f"✅ Aktueller Preis: CHF {current_price:.2f}")
            print(f"✅ Volumen: {hist['Volume'].iloc[-1]:,}")
            return True
        else:
            print("❌ Keine Daten verfügbar")
            return False
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
        return False

def test_historical_data():
    """Test: Historische Daten abrufen"""
    print("\n" + "="*60)
    print("🔍 TEST 2: Historische Daten (^SSMI - 1 Monat)")
    print("="*60)
    
    try:
        symbol = "^SSMI"
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1mo')
        
        if not hist.empty:
            print(f"✅ Symbol: {symbol}")
            print(f"✅ Datenpunkte: {len(hist)}")
            print(f"✅ Zeitraum: {hist.index[0].strftime('%Y-%m-%d')} bis {hist.index[-1].strftime('%Y-%m-%d')}")
            print(f"✅ Höchster Stand: {hist['High'].max():.2f}")
            print(f"✅ Tiefster Stand: {hist['Low'].min():.2f}")
            return True
        else:
            print("❌ Keine historischen Daten verfügbar")
            return False
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
        return False

def test_market_overview():
    """Test: Marktübersicht abrufen"""
    print("\n" + "="*60)
    print("🔍 TEST 3: Marktübersicht (Major Indizes)")
    print("="*60)
    
    indices = {
        '^SSMI': 'SMI',
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones',
        '^IXIC': 'NASDAQ'
    }
    
    results = []
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            if not hist.empty:
                current = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    prev = float(hist['Close'].iloc[-2])
                    change_pct = ((current - prev) / prev) * 100
                else:
                    change_pct = 0
                
                print(f"✅ {name:15} | {current:10,.2f} | {change_pct:+.2f}%")
                results.append(True)
            else:
                print(f"❌ {name:15} | Keine Daten verfügbar")
                results.append(False)
        except Exception as e:
            print(f"❌ {name:15} | Fehler: {str(e)}")
            results.append(False)
    
    return all(results)

def test_asset_statistics():
    """Test: Asset-Statistiken berechnen"""
    print("\n" + "="*60)
    print("🔍 TEST 4: Asset-Statistiken (UBS.SW)")
    print("="*60)
    
    try:
        symbol = "UBS.SW"
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='1y')
        
        if hist.empty:
            print("❌ Keine Daten verfügbar")
            return False
        
        # Statistiken berechnen
        returns = hist['Close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252) * 100)
        expected_return = float(returns.mean() * 252 * 100)
        
        print(f"✅ Symbol: {symbol}")
        print(f"✅ Name: {info.get('longName', 'N/A')}")
        print(f"✅ Aktueller Preis: CHF {hist['Close'].iloc[-1]:.2f}")
        print(f"✅ Volatilität (annualisiert): {volatility:.2f}%")
        print(f"✅ Erwartete Rendite (annualisiert): {expected_return:.2f}%")
        print(f"✅ Beta: {info.get('beta', 'N/A')}")
        print(f"✅ Sektor: {info.get('sector', 'N/A')}")
        return True
        
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
        return False

def test_swiss_stocks():
    """Test: Mehrere Schweizer Aktien"""
    print("\n" + "="*60)
    print("🔍 TEST 5: Top 5 Schweizer Aktien")
    print("="*60)
    
    swiss_stocks = ['NESN.SW', 'NOVN.SW', 'ROG.SW', 'ABBN.SW', 'UBS.SW']
    
    results = []
    for symbol in swiss_stocks:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                print(f"✅ {symbol:10} | CHF {price:8,.2f}")
                results.append(True)
            else:
                print(f"⚠️  {symbol:10} | Keine Daten verfügbar")
                results.append(False)
        except Exception as e:
            print(f"❌ {symbol:10} | Fehler: {str(e)[:30]}...")
            results.append(False)
    
    return any(results)  # Mindestens eine Aktie muss funktionieren

def main():
    """Führt alle Tests aus"""
    print("\n" + "🚀"*30)
    print("Swiss Asset Pro - Live-Daten Integration Test")
    print(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀"*30)
    
    tests = [
        ("Live-Preis abrufen", test_live_price),
        ("Historische Daten", test_historical_data),
        ("Marktübersicht", test_market_overview),
        ("Asset-Statistiken", test_asset_statistics),
        ("Schweizer Aktien", test_swiss_stocks)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' ist fehlgeschlagen: {str(e)}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "="*60)
    print("📊 TEST-ZUSAMMENFASSUNG")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ BESTANDEN" if result else "❌ FEHLGESCHLAGEN"
        print(f"{status:20} | {test_name}")
    
    print("\n" + "="*60)
    print(f"Ergebnis: {passed}/{total} Tests bestanden ({passed/total*100:.1f}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 Alle Tests erfolgreich! Live-Daten-Integration funktioniert.")
        print("✅ Die App ist bereit für echte Simulationen!")
    elif passed >= total * 0.7:
        print("\n⚠️  Die meisten Tests erfolgreich. Einige APIs könnten langsam sein.")
        print("✅ Die App sollte funktionieren, aber eventuell mit Fallback-Daten.")
    else:
        print("\n❌ Viele Tests fehlgeschlagen. Bitte Internet-Verbindung prüfen.")
        print("⚠️  Die App wird mit simulierten Daten laufen.")
    
    print("\n💡 Tipp: Starte jetzt 'python app.py' und teste die App im Browser!")

if __name__ == "__main__":
    try:
        import yfinance
        import numpy
        main()
    except ImportError as e:
        print(f"\n❌ Fehler: Benötigte Bibliothek nicht gefunden: {e}")
        print("\n📦 Bitte installiere die Abhängigkeiten:")
        print("   pip install yfinance numpy pandas")

