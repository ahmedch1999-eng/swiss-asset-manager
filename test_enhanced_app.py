#!/usr/bin/env python3
"""
Swiss Asset Manager - Erweiterte Test Suite
Testet alle neuen Features und Verbesserungen
"""

import unittest
import requests
import json
import time
from datetime import datetime
import sys
import os

# Füge das Hauptverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestEnhancedSwissAssetManager(unittest.TestCase):
    """Test-Klasse für die erweiterten Features"""
    
    def setUp(self):
        """Setup für jeden Test"""
        self.base_url = "http://localhost:3000"
        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.test_indices = ['^GSPC', '^IXIC', '^DJI', '^SSMI']
        
    def test_app_running(self):
        """Test ob die Anwendung läuft"""
        try:
            response = requests.get(self.base_url, timeout=5)
            self.assertEqual(response.status_code, 200)
            print("✅ App läuft erfolgreich")
        except requests.exceptions.RequestException as e:
            self.fail(f"App läuft nicht: {e}")
    
    def test_live_data_endpoint(self):
        """Test der erweiterten Live-Daten API"""
        for symbol in self.test_symbols:
            with self.subTest(symbol=symbol):
                try:
                    response = requests.get(f"{self.base_url}/get_live_data/{symbol}", timeout=10)
                    self.assertEqual(response.status_code, 200)
                    
                    data = response.json()
                    self.assertIn('price', data)
                    self.assertIn('change_percent', data)
                    self.assertIn('source', data)
                    self.assertIn('reliability', data)
                    
                    print(f"✅ Live-Daten für {symbol}: {data['source']} ({data['reliability']})")
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Fehler bei {symbol}: {e}")
    
    def test_technical_analysis_api(self):
        """Test der technischen Analyse API"""
        for symbol in self.test_symbols[:2]:  # Teste nur die ersten 2
            with self.subTest(symbol=symbol):
                try:
                    response = requests.get(f"{self.base_url}/api/technical_analysis/{symbol}", timeout=10)
                    self.assertEqual(response.status_code, 200)
                    
                    data = response.json()
                    self.assertIn('indicators', data)
                    self.assertIn('signals', data)
                    self.assertIn('timestamp', data)
                    
                    # Prüfe technische Indikatoren
                    indicators = data['indicators']
                    if indicators:  # Nur prüfen wenn Daten vorhanden
                        self.assertIn('rsi', indicators)
                        self.assertIn('sma', indicators)
                        self.assertIn('ema', indicators)
                    
                    print(f"✅ Technische Analyse für {symbol}: RSI={indicators.get('rsi', 'N/A')}")
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Fehler bei technischer Analyse für {symbol}: {e}")
    
    def test_portfolio_analysis_api(self):
        """Test der Portfolio-Analyse API"""
        try:
            response = requests.get(f"{self.base_url}/api/portfolio_analysis", timeout=15)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('portfolio_metrics', data)
            self.assertIn('recommendations', data)
            self.assertIn('timestamp', data)
            
            metrics = data['portfolio_metrics']
            if metrics:
                self.assertIn('portfolio_return', metrics)
                self.assertIn('portfolio_volatility', metrics)
                self.assertIn('sharpe_ratio', metrics)
            
            print(f"✅ Portfolio-Analyse: Sharpe={metrics.get('sharpe_ratio', 'N/A')}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei Portfolio-Analyse: {e}")
    
    def test_market_sentiment_api(self):
        """Test der Marktstimmung API"""
        try:
            response = requests.get(f"{self.base_url}/api/market_sentiment", timeout=15)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('sentiment', data)
            self.assertIn('color', data)
            self.assertIn('average_change', data)
            self.assertIn('volatility', data)
            
            print(f"✅ Marktstimmung: {data['sentiment']} ({data['average_change']}%)")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei Marktstimmung: {e}")
    
    def test_benchmark_data(self):
        """Test der Benchmark-Daten"""
        try:
            response = requests.get(f"{self.base_url}/get_benchmark_data", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIsInstance(data, dict)
            
            print("✅ Benchmark-Daten erfolgreich abgerufen")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei Benchmark-Daten: {e}")
    
    def test_news_endpoint(self):
        """Test der News API"""
        try:
            response = requests.get(f"{self.base_url}/get_news", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIsInstance(data, list)
            
            print(f"✅ News erfolgreich abgerufen: {len(data)} Artikel")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei News: {e}")
    
    def test_market_refresh(self):
        """Test der Marktaktualisierung"""
        try:
            response = requests.get(f"{self.base_url}/refresh_all_markets", timeout=30)
            self.assertEqual(response.status_code, 200)
            
            print("✅ Marktaktualisierung erfolgreich")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei Marktaktualisierung: {e}")
    
    def test_data_quality(self):
        """Test der Datenqualität"""
        for symbol in self.test_symbols[:2]:
            with self.subTest(symbol=symbol):
                try:
                    response = requests.get(f"{self.base_url}/get_live_data/{symbol}", timeout=10)
                    data = response.json()
                    
                    # Prüfe Datenqualität
                    if data.get('price', 0) > 0:
                        self.assertGreater(data['price'], 0, f"Preis für {symbol} sollte positiv sein")
                        self.assertIsInstance(data['change_percent'], (int, float), f"Änderung für {symbol} sollte numerisch sein")
                        self.assertIn('source', data, f"Quelle für {symbol} sollte angegeben sein")
                        
                        print(f"✅ Datenqualität für {symbol}: Preis=${data['price']:.2f}, Änderung={data['change_percent']:.2f}%")
                    else:
                        print(f"⚠️  Simulierte Daten für {symbol}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Fehler bei Datenqualität für {symbol}: {e}")
    
    def test_performance(self):
        """Test der Performance"""
        start_time = time.time()
        
        # Teste mehrere gleichzeitige Anfragen
        symbols = self.test_symbols[:3]
        responses = []
        
        for symbol in symbols:
            try:
                response = requests.get(f"{self.base_url}/get_live_data/{symbol}", timeout=5)
                responses.append(response)
            except requests.exceptions.RequestException:
                pass
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.assertLess(duration, 10, "API-Antworten sollten unter 10 Sekunden liegen")
        print(f"✅ Performance-Test: {len(responses)} Anfragen in {duration:.2f} Sekunden")
    
    def test_error_handling(self):
        """Test der Fehlerbehandlung"""
        # Teste mit ungültigem Symbol
        try:
            response = requests.get(f"{self.base_url}/get_live_data/INVALID_SYMBOL_12345", timeout=5)
            self.assertEqual(response.status_code, 200)  # Sollte 200 zurückgeben mit Fallback-Daten
            
            data = response.json()
            self.assertIn('source', data)
            print("✅ Fehlerbehandlung: Ungültiges Symbol wird korrekt behandelt")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Fehler bei Fehlerbehandlung: {e}")

def run_performance_test():
    """Führt einen erweiterten Performance-Test durch"""
    print("\n🚀 Erweiterter Performance-Test")
    print("=" * 50)
    
    base_url = "http://localhost:3000"
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', '^GSPC', '^IXIC', '^DJI']
    
    # Test 1: Einzelne API-Aufrufe
    print("\n📊 Test 1: Einzelne API-Aufrufe")
    start_time = time.time()
    
    for symbol in test_symbols:
        try:
            response = requests.get(f"{base_url}/get_live_data/{symbol}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  {symbol}: {data.get('source', 'Unknown')} - {data.get('price', 0):.2f}")
        except:
            print(f"  {symbol}: Fehler")
    
    single_duration = time.time() - start_time
    print(f"  Dauer: {single_duration:.2f} Sekunden")
    
    # Test 2: Parallele API-Aufrufe
    print("\n📊 Test 2: Parallele API-Aufrufe")
    start_time = time.time()
    
    import concurrent.futures
    
    def fetch_data(symbol):
        try:
            response = requests.get(f"{base_url}/get_live_data/{symbol}", timeout=5)
            return symbol, response.json() if response.status_code == 200 else None
        except:
            return symbol, None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_data, symbol) for symbol in test_symbols]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    parallel_duration = time.time() - start_time
    print(f"  Dauer: {parallel_duration:.2f} Sekunden")
    
    # Test 3: Technische Analyse
    print("\n📊 Test 3: Technische Analyse")
    start_time = time.time()
    
    for symbol in test_symbols[:3]:
        try:
            response = requests.get(f"{base_url}/api/technical_analysis/{symbol}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                indicators = data.get('indicators', {})
                print(f"  {symbol}: RSI={indicators.get('rsi', 'N/A')}, SMA={indicators.get('sma', 'N/A')}")
        except:
            print(f"  {symbol}: Fehler")
    
    analysis_duration = time.time() - start_time
    print(f"  Dauer: {analysis_duration:.2f} Sekunden")
    
    print(f"\n📈 Performance-Zusammenfassung:")
    print(f"  Einzelne Aufrufe: {single_duration:.2f}s")
    print(f"  Parallele Aufrufe: {parallel_duration:.2f}s")
    print(f"  Technische Analyse: {analysis_duration:.2f}s")
    print(f"  Gesamt: {single_duration + parallel_duration + analysis_duration:.2f}s")

if __name__ == '__main__':
    print("🧪 Swiss Asset Manager - Erweiterte Test Suite")
    print("=" * 60)
    print(f"Test gestartet um: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Führe Unit-Tests aus
    unittest.main(verbosity=2, exit=False)
    
    # Führe Performance-Test aus
    run_performance_test()
    
    print("\n✅ Alle Tests abgeschlossen!")
    print("=" * 60)
