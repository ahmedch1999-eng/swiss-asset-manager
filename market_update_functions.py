@app.route('/update_market_cycles')
def update_market_cycles():
    """Aktualisiert die Marktzyklen mit echten ETF-Daten"""
    try:
        global MARKET_CYCLES
        updated_cycles = {}
        
        for sector, data in MARKET_CYCLES.items():
            try:
                etf_symbol = data.get('etf')
                if etf_symbol:
                    # Yahoo Finance API verwenden, um aktuelle ETF-Daten zu holen
                    ticker = yf.Ticker(etf_symbol)
                    hist = ticker.history(period="1y")
                    
                    if not hist.empty:
                        # 1-Jahres-Performance berechnen
                        start_price = hist['Close'].iloc[0]
                        end_price = hist['Close'].iloc[-1]
                        return_1y = ((end_price - start_price) / start_price) * 100
                        
                        # Volatilität berechnen
                        returns = hist['Close'].pct_change().dropna()
                        volatility = returns.std() * np.sqrt(252) * 100  # Annualisierte Volatilität
                        
                        # Bestimme Phase und Rating basierend auf Performance und Volatilität
                        if return_1y > 15:
                            phase = "Früh" if volatility < 20 else "Mitte"
                            rating = "Hoch"
                            trend = "↗️"
                        elif return_1y > 5:
                            phase = "Mitte"
                            rating = "Mittel"
                            trend = "↗️"
                        elif return_1y > -5:
                            phase = "Spät"
                            rating = "Niedrig"
                            trend = "➡️"
                        else:
                            phase = "Spät"
                            rating = "Niedrig"
                            trend = "↘️"
                        
                        # Bestimme Zyklustyp basierend auf Sektor
                        cycle_type = data.get('cycle')  # Behalte den ursprünglichen Zyklustyp
                        
                        updated_cycles[sector] = {
                            "cycle": cycle_type,
                            "phase": phase,
                            "rating": rating,
                            "trend": trend,
                            "etf": etf_symbol,
                            "return_1y": round(return_1y, 1),
                            "volatility": round(volatility, 1),
                            "source": "🔴 LIVE (Yahoo Finance ETF)",
                            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                    else:
                        updated_cycles[sector] = data
                else:
                    updated_cycles[sector] = data
            except Exception as e:
                print(f"Error updating market cycle for {sector}: {e}")
                updated_cycles[sector] = data
        
        # Nur aktualisieren, wenn wir Daten bekommen haben
        if updated_cycles:
            MARKET_CYCLES = updated_cycles
        
        return jsonify({
            "success": True,
            "message": "Marktzyklen aktualisiert",
            "cycles": MARKET_CYCLES
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })