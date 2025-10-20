# bvar_module/bvar_service.py
"""
BVAR Service für Swiss Asset Pro
- Datenabruf (yfinance, FRED)
- Preprocessing
- Klassische VAR-Schätzung (statsmodels)
- Optional: Bayesian VAR via PyMC3 (Toggle)
- Forecast, IRF, FEVD
- Caching & Export
"""

import os
import logging
from datetime import datetime
import pickle
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from statsmodels.tsa.api import VAR
import yfinance as yf

try:
    from fredapi import Fred
except Exception:
    Fred = None

try:
    import pymc3 as pm
    import arviz as az
    PYMC3_AVAILABLE = True
except Exception:
    PYMC3_AVAILABLE = False

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

BASE = os.path.dirname(__file__)
CACHE_DIR = os.path.join(BASE, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
PLOTS_DIR = os.path.join(BASE, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Env vars
FRED_API_KEY = os.environ.get("FRED_API_KEY", None)
fred = Fred(api_key=FRED_API_KEY) if (FRED_API_KEY and Fred) else None

DEFAULT_TICKERS = ['^GSPC', '^IXIC', 'DGS10']
FREQ = 'M'  # Monthly frequency

def cache_save(obj, name):
    """Save object to cache"""
    path = os.path.join(CACHE_DIR, name)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    return path

def cache_load(name):
    """Load object from cache"""
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

def export_df_to_csv(df, name):
    """Export DataFrame to CSV"""
    path = os.path.join(CACHE_DIR, name)
    df.to_csv(path)
    return path

def save_plot(fig, name):
    """Save matplotlib figure"""
    path = os.path.join(PLOTS_DIR, name)
    fig.savefig(path, bbox_inches='tight', dpi=100)
    plt.close(fig)
    return path

def fetch_yfinance(tickers, start='2010-01-01', end=None):
    """Fetch data from Yahoo Finance"""
    end = end or datetime.today().strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start, end=end, progress=False)['Adj Close']
    if isinstance(df, pd.Series):
        df = df.to_frame()
    df.index = pd.to_datetime(df.index)
    df_m = df.resample(FREQ).last()
    returns = df_m.pct_change().dropna(how='all')
    return returns

def fetch_fred(series_id, start='2010-01-01'):
    """Fetch data from FRED"""
    if fred is None:
        raise RuntimeError("FRED API not configured. Set FRED_API_KEY in env.")
    s = fred.get_series(series_id, observation_start=start)
    s.index = pd.to_datetime(s.index)
    s_m = s.resample(FREQ).last()
    returns = s_m.pct_change().dropna()
    returns = returns.rename(series_id)
    return returns.to_frame()

def build_dataset(tickers=None, start='2010-01-01', end=None):
    """Build VAR dataset from multiple sources"""
    tickers = tickers or DEFAULT_TICKERS
    yf_list = []
    fred_list = []
    
    for t in tickers:
        # FRED series are usually uppercase without ^
        if (t.isupper() and not t.startswith('^')) and fred is not None:
            fred_list.append(t)
        else:
            yf_list.append(t)
    
    frames = []
    if yf_list:
        LOGGER.info("Fetching yfinance tickers: %s", yf_list)
        try:
            frames.append(fetch_yfinance(yf_list, start=start, end=end))
        except Exception as e:
            LOGGER.error("yfinance fetch error: %s", e)
    
    if fred_list:
        for f in fred_list:
            try:
                LOGGER.info("Fetching FRED series: %s", f)
                frames.append(fetch_fred(f, start=start))
            except Exception as e:
                LOGGER.error("FRED fetch error for %s: %s", f, e)
    
    if not frames:
        raise ValueError("Keine Datenquellen verfügbar (yfinance/fred).")
    
    data = pd.concat(frames, axis=1).dropna()
    data.columns = [str(c) for c in data.columns]
    return data

def estimate_var_classical(data, nlags=2):
    """Estimate VAR model using statsmodels"""
    model = VAR(data)
    res = model.fit(nlags)
    return res

def forecast_var_classical(var_res, steps=12):
    """Generate forecast from fitted VAR model"""
    endog = var_res.endog
    fc = var_res.forecast(endog, steps=steps)
    last_date = pd.to_datetime(var_res.data.dates[-1])
    idx = pd.date_range(start=last_date, periods=steps+1, freq=FREQ)[1:]
    df_fc = pd.DataFrame(fc, index=idx, columns=var_res.names)
    return df_fc

def irf_plot(var_res, orth=True, steps=12, save_as=None):
    """Generate and save Impulse Response Function plot"""
    irf = var_res.irf(steps)
    fig = irf.plot(orth=orth, figsize=(12, 8))
    if save_as:
        save_plot(fig, save_as)
    return irf

def fevd_table(var_res, steps=12):
    """Generate Forecast Error Variance Decomposition table"""
    try:
        fev = var_res.fevd(steps)
        data = fev.decomp
        last = data[-1]
        cols = var_res.names
        df = pd.DataFrame(last, index=cols, columns=cols)
        return df
    except Exception as e:
        LOGGER.error("FEVD error: %s", e)
        return None

def bvar_pymc3_simple(data, nlags=2, draws=1000, tune=1000, target_accept=0.9):
    """Bayesian VAR using PyMC3 (optional, computationally intensive)"""
    if not PYMC3_AVAILABLE:
        raise RuntimeError("PyMC3 not installed. Install pymc3 and arviz to use Bayesian mode.")
    
    df = data.copy()
    N = df.shape[1]
    T = df.shape[0]
    lags = nlags
    
    # Construct lagged design matrix
    Ys = df.values[lags:]
    Xs = []
    for i in range(1, lags+1):
        Xs.append(df.shift(i).values[lags:])
    X = np.hstack(Xs)
    X = np.hstack([np.ones((X.shape[0], 1)), X])  # Add intercept
    
    with pm.Model() as model:
        sigma = pm.Exponential("sigma", 1.0, shape=N)
        B = pm.Normal("B", mu=0, sigma=1, shape=(X.shape[1], N))
        mu = pm.math.dot(X, B)
        Yobs = pm.Normal("Yobs", mu=mu, sigma=sigma, observed=Ys)
        trace = pm.sample(draws=draws, tune=tune, target_accept=target_accept, return_inferencedata=True)
    
    return trace

def run_bvar_pipeline(config: dict):
    """
    Main pipeline for BVAR analysis
    
    config = {
        'tickers': list of symbols,
        'start': start date,
        'end': end date (optional),
        'nlags': number of lags,
        'bayesian': True/False,
        'forecast_steps': forecast horizon,
        'use_local_prices_df': optional DataFrame
    }
    """
    tickers = config.get("tickers", DEFAULT_TICKERS)
    start = config.get("start", "2010-01-01")
    end = config.get("end", None)
    nlags = int(config.get("nlags", 2))
    bayesian = bool(config.get("bayesian", False))
    steps = int(config.get("forecast_steps", 12))
    local = config.get("use_local_prices_df", None)
    
    # Load or fetch data
    if isinstance(local, pd.DataFrame):
        data = local.copy()
    else:
        data = build_dataset(tickers=tickers, start=start, end=end)
    
    if data.shape[0] < nlags + 10:
        raise ValueError("Nicht genug Beobachtungen für gegebene Lags. Benutze längeren Zeitraum oder weniger Lags.")
    
    # Classical VAR estimation
    LOGGER.info("Estimating VAR with %d lags...", nlags)
    var_res = estimate_var_classical(data, nlags=nlags)
    
    # Forecast
    LOGGER.info("Generating forecast for %d steps...", steps)
    forecast = forecast_var_classical(var_res, steps=steps)
    
    # IRF Plot
    irf_filename = f"irf_{'_'.join([str(t) for t in tickers])}_{nlags}.png".replace('/', '_').replace('^', '')
    irf_obj = irf_plot(var_res, orth=True, steps=steps, save_as=irf_filename)
    
    # FEVD
    fevd_df = fevd_table(var_res, steps=steps)
    fevd_path = None
    if fevd_df is not None:
        fevd_filename = f"fevd_{'_'.join([str(t) for t in tickers])}_{nlags}.csv".replace('/', '_').replace('^', '')
        fevd_path = export_df_to_csv(fevd_df, fevd_filename)
    
    # Bayesian VAR (optional)
    bvar_trace = None
    bayesian_meta = None
    if bayesian:
        if PYMC3_AVAILABLE:
            LOGGER.info("Starting PyMC3-BVAR (this may take a while)...")
            trace = bvar_pymc3_simple(data, nlags=nlags, draws=500, tune=500)
            bvar_trace = trace
            bayesian_meta = {"posterior_samples": len(trace.posterior.stack(sample=("chain", "draw")))}
            try:
                trace_filename = f"bvar_trace_{'_'.join([str(t) for t in tickers])}_{nlags}.nc".replace('/', '_').replace('^', '')
                az.to_netcdf(trace, os.path.join(CACHE_DIR, trace_filename))
            except Exception as e:
                LOGGER.error("Failed to save trace: %s", e)
        else:
            LOGGER.warning("PyMC3 not available; skipping Bayesian mode.")
    
    # Build result
    result = {
        "data": data,
        "var_res": var_res,
        "forecast": forecast,
        "irf_plot": os.path.join(PLOTS_DIR, irf_filename),
        "fevd_csv": fevd_path,
        "fevd_df": fevd_df,
        "bvar_trace": bvar_trace,
        "bayesian_meta": bayesian_meta,
        "metadata": {
            "tickers": tickers,
            "nlags": nlags,
            "bayesian": bayesian,
            "forecast_steps": steps,
            "generated_at": datetime.utcnow().isoformat()
        }
    }
    
    # Cache result
    cache_name = f"bvar_result_{'_'.join([str(t) for t in tickers])}_{nlags}.pkl".replace("/", "_").replace("^", "")
    cache_save(result, cache_name)
    LOGGER.info("BVAR pipeline complete. Cached as: %s", cache_name)
    
    return result

def bvar_forecast_to_pi(forecast_df, annualize=True):
    """Convert BVAR forecast to expected returns (pi) for Black-Litterman"""
    pi = forecast_df.mean(axis=0).values
    if annualize and FREQ == 'M':
        pi = pi * 12
    return pi

def estimate_sigma_from_data(data):
    """Estimate covariance matrix from data for Black-Litterman"""
    cov = data.cov().values
    if FREQ == 'M':
        cov = cov * 12  # Annualize
    return cov

if __name__ == "__main__":
    # Test run
    cfg = {
        "tickers": ['^GSPC', '^IXIC'],
        "start": "2015-01-01",
        "nlags": 2,
        "forecast_steps": 12,
        "bayesian": False
    }
    res = run_bvar_pipeline(cfg)
    print("Forecast:\n", res["forecast"].head())
    print("Cached files:", os.listdir(CACHE_DIR)[:5])






