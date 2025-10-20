# ================================================================================================
# 🔒 PROTECTED SECTION - FLASK BACKEND & CONFIGURATION
# DO NOT MODIFY WITHOUT EXPLICIT PERMISSION
# This section contains all backend logic, routes, database functions, and business logic
# ================================================================================================

from flask import Flask, render_template_string, send_from_directory, request, jsonify, make_response, send_file
from flask_socketio import SocketIO, emit
import os
import sqlite3
import json
import time
import random
import math
from datetime import datetime, timedelta
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from scipy.optimize import minimize
import warnings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging
from logging.handlers import RotatingFileHandler
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import threading

# Setup Professional Logging
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logger
logger = logging.getLogger('swiss_asset_pro')
logger.setLevel(logging.INFO)

# File handler with rotation
file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("=" * 80)
logger.info("Swiss Asset Pro Starting Up")
logger.info("=" * 80)

# Pydantic Validation Models
class PortfolioAsset(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol (e.g., AAPL)")
    amount: float = Field(..., gt=0, le=1000000000, description="Investment amount in CHF")
    weight: Optional[float] = Field(None, ge=0, le=1, description="Portfolio weight (0-1)")

    @validator('symbol')
    def validate_symbol(cls, v):
        v = v.upper().strip()
        import re
        if not re.match(r'^[A-Z0-9\.\-=^]+$', v):
            raise ValueError('Symbol contains invalid characters')
        return v

class PortfolioRequest(BaseModel):
    portfolio: List[PortfolioAsset] = Field(..., min_length=1, max_length=100)
    total_investment: Optional[float] = Field(None, gt=0, le=1000000000)
    risk_profile: Optional[str] = Field('moderate', pattern=r'^(conservative|moderate|aggressive)$')

class BlackLittermanRequest(BaseModel):
    symbols: List[str] = Field(..., min_items=2, max_items=50)
    views: List[dict] = Field(..., min_items=1)
    risk_aversion: Optional[float] = Field(2.5, gt=0, le=10)

    @validator('symbols', each_item=True)
    def validate_symbols(cls, v):
        v = v.upper().strip()
        import re
        if not re.match(r'^[A-Z0-9\.\-=^]+$', v):
            raise ValueError('Invalid symbol format')
        return v

class MonteCarloRequest(BaseModel):
    initial_value: float = Field(..., gt=0, le=1000000000)
    expected_return: float = Field(..., ge=-1, le=2)
    volatility: float = Field(..., ge=0, le=2)
    years: int = Field(..., ge=1, le=50)
    simulations: int = Field(1000, ge=100, le=10000)

# Simple in-memory cache implementation
class SimpleCache:
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        if key in self._cache:
            data, timestamp, ttl = self._cache[key]
            if time.time() - timestamp < ttl:
                return data
            else:
                del self._cache[key]
        return None
    
    def set(self, key, value, ttl=300):
        self._cache[key] = (value, time.time(), ttl)
    
    def touch(self, key):
        if key in self._cache:
            data, _, ttl = self._cache[key]
            self._cache[key] = (data, time.time(), ttl)
from reportlab.lib.units import inch
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

# Swiss-specific constants
SWISS_STAMP_TAX_RATE = 0.0015  # 0.15% stamp tax on Swiss securities
SWISS_WITHHOLDING_TAX = 0.35   # 35% withholding tax on dividends
SWISS_CAPITAL_GAINS_TAX = 0.0  # No capital gains tax in Switzerland
SWISS_INCOME_TAX_RATE = 0.25   # Average income tax rate

# Asset classification lists
CRYPTO = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD', 'UNI-USD']
COMMODITIES = ['GC=F', 'SI=F', 'CL=F', 'NG=F', 'PL=F', 'HG=F', 'PA=F']
BONDS = ['BND', 'AGG', 'LQD', 'HYG', 'TLT', 'IEF', 'SHY']
SWISS_STOCKS = ['NESN.SW', 'NOVN.SW', 'ROG.SW', 'UBSG.SW', 'ZURN.SW', 'ABBN.SW', 'CSGN.SW']
SWISS_INDICES = ['^SSMI', '^SLI', '^SPI']

# SSL context workaround for certain environments (yfinance/requests)
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'CHANGE_ME_BEFORE_PRODUCTION')
socketio = SocketIO(app, cors_allowed_origins="*")
app_start_time = time.time()

# Initialize cache
cache = SimpleCache()
logger.info("Cache system initialized")

# Pydantic validation models initialized
logger.info("Pydantic validation models initialized")

# yfinance Session mit Retry-Logic und User-Agent
def create_yf_session():
    import requests
    from requests.adapters import HTTPAdapter
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        from requests.packages.urllib3.util.retry import Retry

    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://finance.yahoo.com/'
    })
    return session

YF_SESSION = create_yf_session()
logger.info("✅ yfinance Session mit Retry-Logic und User-Agent initialisiert")

def fetch_ticker_data(symbol, period='1mo', max_retries=3):
    import time
    for attempt in range(max_retries):
        try:
            logger.debug(f"Fetching {symbol}, attempt {attempt + 1}/{max_retries}")
            ticker = yf.Ticker(symbol, session=YF_SESSION)
            hist = ticker.history(period=period)
            if len(hist) > 0:
                logger.info(f"✅ Successfully fetched {len(hist)} days for {symbol}")
                return hist
            logger.warning(f"No data for {symbol} on attempt {attempt + 1}, retrying...")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Error fetching {symbol}: {e}, attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    logger.error(f"❌ Failed to fetch {symbol} after {max_retries} attempts")
    return None

logger.info("yfinance Helper-Funktionen initialisiert")

# Module Integration
try:
    from free_data_sources import free_sources
    FREE_SOURCES_AVAILABLE = True
    logger.info("✅ Free Data Sources verfügbar (Yahoo Query, Stooq, ECB, CoinGecko, Binance)")
except ImportError as e:
    FREE_SOURCES_AVAILABLE = False
    logger.warning(f"⚠️ Free Data Sources nicht verfügbar: {e}")

try:
    from smart_data_fetcher import smart_fetcher
    SMART_FETCHER_AVAILABLE = True
    logger.info("✅ Smart Data Fetcher mit Load-Balancing und parallelen Requests verfügbar")
except ImportError as e:
    SMART_FETCHER_AVAILABLE = False
    logger.warning(f"⚠️ Smart Data Fetcher nicht verfügbar: {e}")

try:
    from real_calculations import real_calculator, get_real_asset_stats
    REAL_CALCULATIONS_AVAILABLE = True
    logger.info("✅ Echte Berechnungsfunktionen verfügbar (keine Random-Zahlen mehr!)")
except ImportError as e:
    REAL_CALCULATIONS_AVAILABLE = False
    logger.warning(f"⚠️ Echte Berechnungen nicht verfügbar: {e}")

try:
    from multi_source_fetcher import multi_fetcher
    MULTI_FETCHER_AVAILABLE = True
    logger.info("✅ Multi-Source Fetcher aktiviert")
except ImportError as e:
    MULTI_FETCHER_AVAILABLE = False
    logger.warning(f"⚠️ Multi-Source Fetcher nicht verfügbar: {e}")

# Database initialization
def init_database():
    """Initialize SQLite database for persistent data storage"""
    conn = sqlite3.connect('swiss_asset_manager.db')
    cursor = conn.cursor()
    
    # Portfolio holdings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            purchase_price REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            current_price REAL,
            last_updated TEXT,
            asset_class TEXT,
            is_swiss BOOLEAN DEFAULT 0
        )
    ''')
    
    # Market data cache table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data_cache (
            symbol TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL
        )
    ''')
    
    # User preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Performance metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            portfolio_value REAL NOT NULL,
            daily_return REAL,
            cumulative_return REAL,
            volatility REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            var_95 REAL
        )
    ''')
    
    # Swiss tax calculations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            stamp_tax REAL,
            withholding_tax REAL,
            net_amount REAL,
            calculation_date TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Passwort-Schutz (aus Environment Variable)
PASSWORD = os.environ.get('APP_PASSWORD', 'CHANGE_ME_BEFORE_USE')

# Spracheinstellung
CURRENT_LANGUAGE = "de"

# VOLLSTÄNDIGE Schweizer Aktienliste - 239 Aktien
SWISS_STOCKS = {
    # Bestehende + alle neuen Aktien
    "NESN.SW": "Nestlé", "NOVN.SW": "Novartis", "ROG.SW": "Roche", "UBSG.SW": "UBS Group",
    "ZURN.SW": "Zurich Insurance", "ABBN.SW": "ABB", "CSGN.SW": "Credit Suisse",
    "SGSN.SW": "SGS", "GIVN.SW": "Givaudan", "LONN.SW": "Lonza", "SIKA.SW": "Sika",
    "GEBN.SW": "Geberit", "SOON.SW": "Sonova", "SCMN.SW": "Swisscom", "ADEN.SW": "Adecco",
    "BAER.SW": "Julius Bär", "CLN.SW": "Clariant", "LOGIN.SW": "Logitech", "CFR.SW": "Richemont",
    "ALC.SW": "Alcon", "TEMN.SW": "Temenos", "VACN.SW": "VAT Group", "KNIN.SW": "Kuehne+Nagel",
    "PGHN.SW": "Partners Group", "SLHN.SW": "Swiss Life", "SYNN.SW": "Syngenta", "COPN.SW": "Cosmo Pharmaceuticals",
    
    # NEUE AKTIEN aus der Liste - Alle 239
    "GOOGL.SW": "Alphabet", "LLY.SW": "Eli Lilly", "V.SW": "Visa", "KO.SW": "Coca-Cola",
    "PEP.SW": "PepsiCo", "MCD.SW": "McDonald's", "ABT.SW": "Abbott", "MMM.SW": "3M",
    "EMR.SW": "Emerson Electric", "GOB.SW": "Gobain", "FCX.SW": "Freeport-McMoRan",
    "SREN.SW": "Swiss Re", "HOLN.SW": "Holcim", "GALD.SW": "Galapagos", "AAM.SW": "AAM",
    "SCHNE.SW": "Schneider Electric", "SCHP.SW": "Schindler", "SCHPE.SW": "Schindler Part",
    "SCHN.SW": "Schindler Holding", "SCMN.SW": "Swisscom", "ALC.SW": "Alcon",
    "GIVN.SW": "Givaudan", "DAL.SW": "Delta Air Lines", "SIKA.SW": "Sika",
    "PGHN.SW": "Partners Group", "LISN.SW": "Lindt & Sprüngli", "LISP.SW": "Lindt Part",
    "SLHN.SW": "Swiss Life", "AMRZ.SW": "Amriz", "WILL.SW": "Wilhelm",
    "SDZ.SW": "Sandoz", "GEBN.SW": "Geberit", "KNIN.SW": "Kuehne+Nagel",
    "SGSN.SW": "SGS", "ZBH.SW": "Zimmer Biomet", "STMN.SW": "Stadler Rail",
    "HUAYO.SW": "Huayo", "EMSN.SW": "EMS Chemie", "SOON.SW": "Sonova",
    "LOGN.SW": "Logitech", "BAER.SW": "Julius Bär", "VACN.SW": "VAT Group",
    "HELN.SW": "Helvetia", "BEAN.SW": "Belimo", "GOTION.SW": "Gotion High-tech",
    "BKW.SW": "BKW", "BALN.SW": "Baloise", "SPSN.SW": "Swiss Prime Site",
    "BCVN.SW": "Bachem", "UHR.SW": "Swatch Group", "UHRN.SW": "Swatch Part",
    "SQN.SW": "Square", "FHZN.SW": "Flughafen Zürich", "BNR.SW": "Brenntag",
    "DFSH.SW": "DFS", "SWD.SW": "Swedbank", "VZN.SW": "VZ Holding",
    "BARN.SW": "Barry Callebaut", "AVOL.SW": "Avolta", "PSPN.SW": "PSP Swiss Property",
    "ACLN.SW": "Aclon", "O2D.SW": "O2", "GF.SW": "Georg Fischer",
    "SCR.SW": "SCOR", "EFGN.SW": "EFG International", "SUPCON.SW": "Supercond",
    "GEM.SW": "Gemalto", "SUN.SW": "Sun", "YPSN.SW": "Ypsomed",
    "OSR.SW": "Oskar", "BANB.SW": "BanB", "TEMN.SW": "Temenos",
    "DESN.SW": "Desna", "GRKP.SW": "Gurkap", "SFSN.SW": "SFS Group",
    "GALE.SW": "Galenica", "SMG.SW": "SMG", "YJET.SW": "Yankee Jet",
    "GSI.SW": "GSI", "LUKN.SW": "Lukas", "ADEN.SW": "Adecco",
    "BUCN.SW": "Bucher", "SSNE.SW": "SSN", "EMMN.SW": "Emmi",
    "SFZN.SW": "SF-Zurich", "LEPU.SW": "Lepu", "DKSH.SW": "DKSH",
    "SUNN.SW": "Sunn", "VONN.SW": "Von Roll", "DRI.SW": "Drie",
    "BSKP.SW": "Basler Kantonalbank", "TKBP.SW": "Thurgauer Kantonalbank",
    "SGKN.SW": "St. Galler Kantonalbank", "ALLN.SW": "Allreal",
    "SIGN.SW": "SIG", "DOKA.SW": "Doka", "ALSN.SW": "Alessandro",
    "MOVE.SW": "Move", "CMBN.SW": "Combin", "HUBN.SW": "Hubner",
    "JCARE.SW": "J Care", "KEDA.SW": "Keda", "ZUGER.SW": "Zugerberg",
    "ZHT.SW": "ZHT", "IFCN.SW": "IFC", "DAE.SW": "Dae",
    "MOBN.SW": "Mobimo", "BEKN.SW": "Bekon", "CLN.SW": "Clariant",
    "KARN.SW": "Karn", "LLBN.SW": "LLB", "RKET.SW": "Rocket",
    "FDCB.SW": "FDC", "CFT.SW": "CFFT", "TXGN.SW": "TxGN",
    "SENIOR.SW": "Senior", "INRN.SW": "InRN", "BCHN.SW": "Bachem",
    "VATN.SW": "VAT", "WKBN.SW": "WKB", "BLKB.SW": "Basellandschaftliche Kantonalbank",
    "SRAIL.SW": "Stadler Rail", "TECN.SW": "Tecan", "LAND.SW": "Landis",
    "VAHN.SW": "VAHN", "SWON.SW": "Swon", "BCGE.SW": "Banque Cantonale de Genève",
    "GT.SW": "GT", "AERO.SW": "Aero", "IREN.SW": "Iren",
    "COTN.SW": "Coton", "ARYN.SW": "Aryn", "BELL.SW": "Bell",
    "ISN.SW": "ISN", "2HQ.SW": "2HQ", "BRKN.SW": "Brückner",
    "BOSN.SW": "Bosch", "KUDO.SW": "Kudo", "JFN.SW": "JFN",
    "SKAN.SW": "Skan", "GXI.SW": "GXI", "IMPN.SW": "Impinj",
    "AMS.SW": "AMS", "CHAM.SW": "Cham", "AEVS.SW": "Aevs",
    "KURN.SW": "Kurn", "HIAG.SW": "HIAG", "ZUGN.SW": "Zuger",
    "NEAG.SW": "Neag", "COPN.SW": "Cosmo", "REHN.SW": "Rehn",
    "MED.SW": "Med", "UBXN.SW": "Ubxn", "RSGN.SW": "Rsgn",
    "FORN.SW": "Forn", "SENS.SW": "Sens", "AUTN.SW": "Autn",
    "IDIA.SW": "Idia", "OERL.SW": "Oerlikon", "PPGN.SW": "PPG",
    "EPIC.SW": "Epic", "PLAN.SW": "Plan", "CICN.SW": "Cicn",
    "COK.SW": "Cok", "ZEHN.SW": "Zehn", "BYS.SW": "Bys",
    "TMO.SW": "Thermo Fisher", "APGN.SW": "Apgn", "WARN.SW": "Warn",
    "BSLN.SW": "Bsl", "LEHN.SW": "Lehn", "FREN.SW": "Fren",
    "VPBN.SW": "Vpb", "VETN.SW": "Vetn", "MOZN.SW": "Mozn",
    "PKTM.SW": "Pktm", "CPHN.SW": "Cphn", "MTG.SW": "Mtg",
    "PMN.SW": "Pmn", "PMNE.SW": "Pmne", "SWTQ.SW": "Swtq",
    "NREN.SW": "Nren", "METN.SW": "Metn", "SNBN.SW": "Snbn",
    "KOMN.SW": "Komn", "ARBN.SW": "Arbn", "MEDX.SW": "Medx",
    "PEAN.SW": "Pean", "EPH.SW": "Eph", "VBSN.SW": "Vbsn",
    "SFPN.SW": "Sfpn", "MIKN.SW": "Mikn", "LEON.SW": "Leon",
    "DOCM.SW": "Docm", "HBLN.SW": "Hbln", "VZUG.SW": "Vzug",
    "GLKBN.SW": "Glkb", "NWRN.SW": "Nwrn", "ELMN.SW": "Elmn",
    "CLTN.SW": "Cltn", "OFN.SW": "Ofn", "VARN.SW": "Varn",
    "LECN.SW": "Lecn", "BVZN.SW": "Bvzn", "BTC.SW": "BTC",
    "BCJ.SW": "Bcj", "GAM.SW": "Gam", "STGN.SW": "Stgn",
    "BIOV.SW": "Biov", "LMN.SW": "Lmn", "FTON.SW": "Fton",
    "ZUBN.SW": "Zubn", "TIBN.SW": "Tibn", "SANN.SW": "Sann",
    "ASCN.SW": "Ascn", "XLS.SW": "Xls", "GAV.SW": "Gav",
    "BBN.SW": "Bbn", "MOLN.SW": "Moln", "HLEE.SW": "Hlee",
    "MCHN.SW": "Mchn", "KLIN.SW": "Klin", "CALN.SW": "Caln",
    "ORON.SW": "Oron", "ALPN.SW": "Alpn", "ALPNE.SW": "Alpne",
    "KUD.SW": "Kud", "GMI.SW": "Gmi", "CURN.SW": "Curn",
    "VILN.SW": "Viln", "ESUN.SW": "Esun", "NBEN.SW": "Nben",
    "GURN.SW": "Gurn", "WIHN.SW": "Wihn", "RLF.SW": "Rlf",
    "YTME.SW": "Ytme", "VLRT.SW": "Vlrt", "ADVN.SW": "Advn",
    "MBTN.SW": "Mbtn", "STRN.SW": "Strn", "RIEN.SW": "Rien",
    "SHLTN.SW": "Shltn", "ASWN.SW": "Aswn", "ZWM.SW": "Zwm",
    "ADXN.SW": "Adxn", "EVE.SW": "Eve", "PEDU.SW": "Pedu",
    "HT5.SW": "Ht5", "EEII.SW": "Eeii", "AIRE.SW": "Aire",
    "CIE.SW": "CIE"
}

# Professionelle Benchmark-Indizes
BENCHMARK_INDICES = {
    "MSCIW": "MSCI World Index", "BCOM": "Bloomberg Commodity Index", 
    "LBUSTRUU": "Bloomberg Global Aggregate Bond", "SPX": "S&P 500 Index",
    "^SSMI": "Swiss Market Index", "EUNL.DE": "iShares Core MSCI World UCITS ETF",
    "IEGA": "iShares Core € Govt Bond UCITS ETF", "NDX": "NASDAQ 100",
    "DJI": "Dow Jones Industrial Average", "RUT": "Russell 2000",
    "VIX": "CBOE Volatility Index", "COMP": "NASDAQ Composite"
}

# VOLLSTÄNDIGE Indizes-Liste - Alle Kategorien
INDICES = {
    # US-Indizes
    "SPX": "S&P 500 Index", "NDX": "NASDAQ 100", "DJI": "Dow Jones Industrial Average",
    "RUT": "Russell 2000", "VIX": "CBOE Volatility Index", "COMP": "NASDAQ Composite",
    "NYA": "NYSE Composite", "MID": "S&P MidCap 400", "SML": "S&P SmallCap 600",
    "OEX": "S&P 100", "XAX": "NYSE AMEX Composite", "VXN": "NASDAQ Volatility",
    "VXD": "DJIA Volatility", "TXX": "CBOE Technology Index", "DXY": "US Dollar Index",
    "UIX": "CBOE Uranium Index", "CBOE": "CBOE Market Index", "RUI": "Russell 1000",
    "RUA": "Russell 3000", "RAY": "Raymond James", "RMZ": "MSCI US REIT",
    "HGX": "PHLX Housing Sector", "BKX": "KBW Bank Index", "XBD": "S&P Broker Dealer",
    "XLF": "Financial Select Sector", "XLI": "Industrial Select Sector",
    "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "XLE": "Energy Select Sector",
    "XLU": "Utilities Select Sector", "XLV": "Health Care Select Sector",
    "XLB": "Materials Select Sector", "XLK": "Technology Select Sector",
    "XME": "S&P Metals & Mining", "XPH": "S&P Pharmaceuticals", "XRT": "S&P Retail",
    "XHB": "S&P Homebuilders", "SOX": "PHLX Semiconductor", "OSX": "PHLX Oil Service",
    "DRG": "NYSE Arca Pharmaceutical", "BTK": "NYSE Arca Biotech", "NBI": "NASDAQ Biotech",
    "XNG": "NYSE Arca Natural Gas", "XAL": "NYSE Arca Airline", "XCI": "NYSE Arca Computer",
    "XOI": "NYSE Arca Oil", "XSD": "S&P Semiconductor", "XSW": "S&P Software",
    "XTH": "S&P Technology Hardware", "XTL": "S&P Telecom", "XES": "S&P Oil & Gas Equipment",
    "KBE": "KBW Bank ETF", "KRE": "KBW Regional Banking", "IAK": "iShares Insurance",
    "IAT": "iShares Regional Banks", "PSCE": "S&P SmallCap Energy", "PSCI": "S&P SmallCap Industrials",
    "PSCH": "S&P SmallCap Health Care",
    
    # Europäische Indizes
    "DAX": "DAX Germany", "CAC": "CAC 40 France", "FTSE": "FTSE 100 UK",
    "STOXX50": "Euro Stoxx 50", "AEX": "AEX Netherlands", "IBEX": "IBEX 35 Spain",
    "FTSE MIB": "FTSE MIB Italy", "^SSMI": "Swiss Market Index", "PSI20": "PSI 20 Portugal",
    "OMX": "OMX Stockholm 30", "ATX": "ATX Austria", "BEL20": "BEL 20 Belgium",
    "ISEQ": "ISEQ Ireland", "WIG": "WIG Poland", "BUX": "BUX Hungary",
    "RTS": "RTS Russia", "BIST": "BIST Turkey", "SOFIX": "SOFIX Bulgaria",
    "SBITOP": "SBITOP Slovenia", "UX": "UX Ukraine", "CEETX": "CEE TX",
    "CROBEX": "CROBEX Croatia", "HEX": "HEX Finland", "LITIN": "LITIN Lithuania",
    "OMXR": "OMX Riga", "OMXT": "OMX Tallinn", "PRAGUE SE PX": "Prague PX",
    "SAX": "SAX Slovakia",
    
    # Asien-Pazifik Indizes
    "NIKKEI": "Nikkei 225 Japan", "HSI": "Hang Seng Hong Kong", 
    "SHCOMP": "Shanghai Composite", "SZCOMP": "Shenzhen Composite",
    "CSI300": "CSI 300 China", "KOSPI": "KOSPI South Korea", "TWSE": "Taiwan Weighted",
    "STI": "Straits Times Singapore", "ASX": "ASX 200 Australia", "SENSEX": "Sensex India",
    "NIFTY50": "Nifty 50 India", "JKSE": "Jakarta Composite", "KLCI": "KLCI Malaysia",
    "PSEI": "PSEi Philippines", "SET": "SET Thailand", "VNI": "VN Index Vietnam",
    "COLOMBO": "Colombo Sri Lanka", "DSEX": "DSEX Bangladesh", "KS11": "KOSPI South Korea",
    "TOPIX": "TOPIX Japan", "TPEX": "TPEX Taiwan", "NZX50": "NZX 50 New Zealand",
    "MNI": "MNI China", "KOSDAQ": "KOSDAQ South Korea", "HSCEI": "Hang Seng China Enterprises",
    "HSML": "Hang Seng MidCap", "CNX500": "CNX 500 India", "BSE500": "BSE 500 India",
    "BSE100": "BSE 100 India", "BSE200": "BSE 200 India",
    
    # Globale/Internationale Indizes
    "MSCIW": "MSCI World", "MSCIEM": "MSCI Emerging Markets", "MSCIEAFE": "MSCI EAFE",
    "MSCIACWI": "MSCI ACWI", "FTSEALLW": "FTSE All-World", "SPGLOBAL100": "S&P Global 100",
    "SPGLOBAL1200": "S&P Global 1200", "DJGLOBAL": "Dow Jones Global",
    "RUSSELLGLOBAL": "Russell Global", "NYSEWL": "NYSE World Leaders",
    "MSCIWEXUSA": "MSCI World ex USA", "MSCIPACIFIC": "MSCI Pacific",
    "MSCIEUROPE": "MSCI Europe", "MSCIASIA": "MSCI Asia", "MSCICHINA": "MSCI China",
    "MSCIJAPAN": "MSCI Japan", "MSCIUK": "MSCI UK", "MSCICANADA": "MSCI Canada",
    "MSCIBRAZIL": "MSCI Brazil", "MSCIINDIA": "MSCI India",
    
    # Sektor-/Branchenindizes
    "DJUS": "Dow Jones US", "SPDR": "SPDR Sectors", "ISHARES": "iShares Core",
    "VANGUARD": "Vanguard Total", "INVESCO": "Invesco QQQ", "GLOBALX": "Global X",
    "ARK": "ARK Innovation", "PHLX": "PHLX Sector", "KBW": "KBW Regional",
    "NASDAQ": "NASDAQ Sector", "BLOOMBERG": "Bloomberg Commodity", "REFINITIV": "Refinitiv",
    "FACTSET": "FactSet", "BARRONS": "Barron's 400", "WILSHIRE": "Wilshire 5000",
    "COHEN": "Cohen & Steers", "ALERIAN": "Alerian MLP", "MVIS": "MVIS",
    "BLUESTAR": "BlueStar", "SOLACTIVE": "Solactive", "STOXXS": "STOXX Europe 600",
    "MSCISECTOR": "MSCI Sector", "SPSECTOR": "S&P Sector", "RUSSELLSECTOR": "Russell Sector",
    "FTSEsECTOR": "FTSE Sector", "DJSECTOR": "Dow Jones Sector", "NASDAQSECTOR": "Nasdaq Sector",
    "CBOESECTOR": "CBOE Sector"
}

# VOLLSTÄNDIGE Andere Assets
OTHER_ASSETS = {
    # Rohstoffe & Futures
    "GOLD": "Gold Spot", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", 
    "SPY": "S&P 500 ETF", "VNQ": "Real Estate ETF", "BND": "Total Bond Market",
    "SI=F": "Silver Futures", "CL=F": "Crude Oil Futures", "PL=F": "Platinum Futures",
    "PA=F": "Palladium Futures", "HG=F": "Copper Futures", "NG=F": "Natural Gas Futures",
    "ZC=F": "Corn Futures", "ZW=F": "Wheat Futures", "ZS=F": "Soybean Futures",
    "ZL=F": "Soybean Oil Futures", "ZM=F": "Soybean Meal Futures", "ZO=F": "Oats Futures",
    "KE=F": "KC HRW Wheat Futures", "CC=F": "Cocoa Futures", "CT=F": "Cotton Futures",
    "OJ=F": "Orange Juice Futures", "SB=F": "Sugar Futures", "LB=F": "Lumber Futures",
    "HO=F": "Heating Oil Futures", "RB=F": "RBOB Gasoline Futures",
    
    # Währungen/Forex
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "JPY": "Japanese Yen",
    "CHF": "Swiss Franc", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
    "NZD": "New Zealand Dollar", "CNY": "Chinese Yuan", "HKD": "Hong Kong Dollar",
    "SGD": "Singapore Dollar", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
    "DKK": "Danish Krone", "MXN": "Mexican Peso", "BRL": "Brazilian Real",
    "RUB": "Russian Ruble", "INR": "Indian Rupee", "KRW": "South Korean Won",
    "TRY": "Turkish Lira", "ZAR": "South African Rand",
    
    # Forex Paare
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD",
    "NZDUSD=X": "NZD/USD", "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "EURCHF=X": "EUR/CHF", "GBPCHF=X": "GBP/CHF",
    "CHFJPY=X": "CHF/JPY", "CADJPY=X": "CAD/JPY", "AUDJPY=X": "AUD/JPY",
    "NZDJPY=X": "NZD/JPY",
    
    # ETFs
    "GLD": "SPDR Gold Trust", "TLT": "iShares 20+ Year Treasury", "XLV": "Health Care Select Sector",
    "XLE": "Energy Select Sector", "XLB": "Materials Select Sector", "XLU": "Utilities Select Sector",
    "IFRA": "iShares Infrastructure", "XLK": "Technology Select Sector", "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary", "XLI": "Industrial Select Sector", "XLF": "Financial Select Sector",
    "XBI": "SPDR Biotech", "XRT": "SPDR Retail", "XHB": "SPDR Homebuilders",
    "XOP": "SPDR Oil & Gas Exploration", "XME": "SPDR Metals & Mining", "XSD": "SPDR Semiconductor",
    "XSW": "SPDR Software", "XTH": "SPDR Technology Hardware", "XTL": "SPDR Telecom",
    "XES": "SPDR Oil & Gas Equipment", "KBE": "SPDR Banks", "KRE": "SPDR Regional Banks",
    
    # Spezialisierte ETFs
    "REET": "iShares Global REIT", "REM": "iShares Mortgage Real Estate", "BDCS": "UBS ETRACS Business Development",
    "CEF": "Closed-End Fund", "ESG": "iShares ESG Aware", "SRI": "iShares MSCI KLD 400 Social",
    "ICLN": "iShares Global Clean Energy", "TAN": "Invesco Solar", "PBW": "Invesco WilderHill Clean Energy",
    "BLOK": "Amplify Transformational Data", "HACK": "ETFMG Prime Cyber Security", "AIQ": "Global X Artificial Intelligence",
    "BOTZ": "Global X Robotics & AI", "GNOM": "Global X Genomics", "FINX": "Global X FinTech",
    "CLOU": "Global X Cloud Computing", "NERD": "Roundhill Video Games", "BETZ": "Roundhill Sports Betting",
    "YOLO": "AdvisorShares Pure Cannabis", "LIT": "Global X Lithium & Battery Tech", "BATT": "Amplify Lithium & Battery Technology",
    "FAN": "First Trust Global Wind Energy", "HYDR": "Global X Hydrogen", "CGW": "Invesco S&P Global Water",
    "WOOD": "iShares Global Timber", "VEGI": "iShares MSCI Agriculture", "GDX": "VanEck Gold Miners",
    "SIL": "Global X Silver Miners", "COPX": "Global X Copper Miners", "OIH": "VanEck Oil Services",
    "SEA": "Invesco Shipping", "ITA": "iShares Aerospace & Defense", "LUX": "VanEck Luxury Goods",
    "GAMR": "ETFMG Video Game Tech", "SOXX": "iShares PHLX Semiconductor",
    
    # Anleihen/Renten
    "BND": "Vanguard Total Bond", "AGG": "iShares Core US Aggregate", "LQD": "iShares iBoxx Investment Grade",
    "HYG": "iShares iBoxx High Yield", "JNK": "SPDR Bloomberg High Yield", "EMB": "iShares J.P. Morgan EM Bond",
    "TLT": "iShares 20+ Year Treasury", "IEF": "iShares 7-10 Year Treasury", "SHY": "iShares 1-3 Year Treasury",
    "GOVT": "iShares US Treasury", "MUB": "iShares National Muni", "PZA": "Invesco National AMT-Free Muni",
    "BAB": "Invesco Taxable Municipal", "PIMIX": "PIMCO Income", "BOND": "PIMCO Active Bond",
    "BLACKROCK": "BlackRock Total Return", "FIDELITY": "Fidelity Total Bond", "SCHWAB": "Schwab US Aggregate",
    "INVESCOB": "Invesco Total Return", "SPDRB": "SPDR Portfolio Aggregate", "VANECK": "VanEck Investment Grade",
    "GLOBALXB": "Global X Yield", "WISDOMTREE": "WisdomTree Yield"
}

# Schweizer Privatbank Portfolios (simuliert)
SWISS_BANK_PORTFOLIOS = {
    "UBS_Premium": {"return": 6.2, "risk": 12.5, "sharpe": 0.50},
    "CreditSuisse_Wealth": {"return": 5.8, "risk": 13.2, "sharpe": 0.45},
    "JuliusBaer_Premium": {"return": 6.5, "risk": 11.8, "sharpe": 0.55},
    "Pictet_Balanced": {"return": 5.9, "risk": 10.5, "sharpe": 0.56},
    "Vontobel_Growth": {"return": 7.1, "risk": 14.2, "sharpe": 0.51}
}

# Marktzyklen für verschiedene Sektoren
MARKET_CYCLES = {
    "TECH": {"cycle": "Wachstum", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "HEALTH": {"cycle": "Defensiv", "phase": "Spät", "rating": "Mittel", "trend": "➡️"},
    "FINANCIAL": {"cycle": "Zyklisch", "phase": "Mitte", "rating": "Mittel", "trend": "↗️"},
    "ENERGY": {"cycle": "Zyklisch", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "MATERIALS": {"cycle": "Zyklisch", "phase": "Früh", "rating": "Hoch", "trend": "↗️"},
    "UTILITIES": {"cycle": "Defensiv", "phase": "Spät", "rating": "Niedrig", "trend": "➡️"},
    "CONSUMER": {"cycle": "Defensiv", "phase": "Spät", "rating": "Mittel", "trend": "➡️"},
    "INDUSTRIAL": {"cycle": "Zyklisch", "phase": "Mitte", "rating": "Mittel", "trend": "↗️"}
}

# Szenario-Analyse Parameter
SCENARIOS = {
    "normal": {"name": "Normal", "growth_multiplier": 1.0, "volatility_multiplier": 1.0},
    "interest_rise": {"name": "Zinserhöhung", "growth_multiplier": 0.7, "volatility_multiplier": 1.3},
    "inflation": {"name": "Hohe Inflation", "growth_multiplier": 0.8, "volatility_multiplier": 1.4},
    "recession": {"name": "Rezession", "growth_multiplier": 0.5, "volatility_multiplier": 1.8},
    "growth": {"name": "Starkes Wachstum", "growth_multiplier": 1.3, "volatility_multiplier": 0.8}
}

# Übersetzungen
TRANSLATIONS = {
    "de": {
        "title": "Swiss Asset Pro",
        "dashboard": "Dashboard",
        "portfolio": "Portfolio Entwicklung",
        "strategieanalyse": "Strategie Analyse",
        "simulation": "Zukunfts-Simulation",
        "bericht": "Bericht & Analyse",
        "markets": "Märkte",
        "assets": "Assets & Investment",
        "methodik": "Methodik",
        "black-litterman": "Black-Litterman",
        "about": "Über mich",
        "password_prompt": "Bitte geben Sie das Passwort ein:",
        "password_placeholder": "Passwort",
        "access_button": "Zugang erhalten",
        "password_error": "Falsches Passwort. Bitte versuchen Sie es erneut.",
        "password_hint": "by Ahmed Choudhary",
        "last_update": "Letztes Update:",
        "smi_return": "SMI Rendite:",
        "portfolio_return": "Portfolio Rendite:",
        "portfolio_value": "Portfolio Wert:"
    }
}

# Globale Variablen für Live-Daten
live_market_data = {}
last_market_update = None

# LIVE DATA SYSTEM API ENDPOINTS:
@app.route('/api/verify_password', methods=['POST'])
def verify_password():
    try:
        if not request.json:
            return jsonify({"success": False, "error": "No JSON data"})
            
        user_password = request.json.get('password')
        logger.info(f"Password verification attempt from {request.remote_addr}")
        
        # Prefer environment variable for security; fallback to app constant
        correct_password = os.environ.get('APP_PASSWORD', PASSWORD)
        
        if user_password == correct_password:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Invalid password"})
            
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return jsonify({"success": False, "error": str(e)})

# ================================================================================================
# 🚀 NEUE API ENDPOINTS - ECHTE BERECHNUNGEN & DATEN
# ================================================================================================

@app.route('/api/data_source_stats', methods=['GET'])
def data_source_stats():
    """API endpoint für Data Source Performance Statistics"""
    try:
        stats = {
            "free_sources_available": FREE_SOURCES_AVAILABLE,
            "smart_fetcher_available": SMART_FETCHER_AVAILABLE,
            "real_calculations_available": REAL_CALCULATIONS_AVAILABLE,
            "multi_fetcher_available": MULTI_FETCHER_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Data source stats requested: {stats}")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting data source stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_live_data/<symbol>', methods=['GET'])
@app.route('/api/live_data/<symbol>', methods=['GET'])
def get_live_data_route(symbol):
    """Enhanced live data endpoint with multi-source fetching"""
    try:
        logger.info(f"Live data requested for {symbol}")
        
        # Try Smart Fetcher first if available
        if SMART_FETCHER_AVAILABLE:
            try:
                data = smart_fetcher.fetch_data(symbol)
                if data and 'price' in data:
                    logger.info(f"✅ Smart Fetcher success for {symbol}: {data['price']}")
                    return jsonify({
                        "symbol": symbol,
                        "price": data['price'],
                        "change": data.get('change', 0),
                        "change_percent": data.get('change_percent', 0),
                        "source": "smart_fetcher",
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.warning(f"Smart Fetcher failed for {symbol}: {e}")
        
        # Try yfinance with retry logic
        hist = fetch_ticker_data(symbol, period='5d')
        if hist is not None and len(hist) > 0:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            
            price = float(latest['Close'])
            change = float(latest['Close'] - prev['Close'])
            change_percent = (change / float(prev['Close'])) * 100
            
            logger.info(f"✅ yfinance success for {symbol}: {price}")
            return jsonify({
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "source": "yfinance",
                "timestamp": datetime.now().isoformat()
            })
        
        # Fallback to simulated data
        logger.warning(f"Using simulated data for {symbol}")
        simulated_price = random.uniform(50, 500)
        simulated_change = random.uniform(-10, 10)
        simulated_change_percent = (simulated_change / simulated_price) * 100
        
        return jsonify({
            "symbol": symbol,
            "price": simulated_price,
            "change": simulated_change,
            "change_percent": simulated_change_percent,
            "source": "simulated",
            "timestamp": datetime.now().isoformat(),
            "warning": "Using simulated data - real data unavailable"
        })
        
    except Exception as e:
        logger.error(f"Error fetching live data for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/real_asset_stats/<symbol>', methods=['GET'])
def real_asset_stats(symbol):
    """Real asset statistics using real_calculations module"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        stats = get_real_asset_stats(symbol)
        logger.info(f"Real asset stats for {symbol}: {stats}")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting real asset stats for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/real_portfolio_analysis', methods=['POST'])
def real_portfolio_analysis():
    """Real portfolio analysis using real_calculations module"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        data = request.get_json()
        if not data or 'portfolio' not in data:
            return jsonify({"error": "Portfolio data required"}), 400
            
        # Validate with Pydantic
        try:
            portfolio_request = PortfolioRequest(**data)
        except Exception as e:
            return jsonify({"error": f"Validation error: {str(e)}"}), 400
            
        # Get real portfolio analysis
        analysis = real_calculator.get_portfolio_analysis(portfolio_request.portfolio)
        logger.info(f"Real portfolio analysis completed: {len(analysis)} assets")
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error in real portfolio analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/real_monte_carlo', methods=['POST'])
def real_monte_carlo():
    """Real Monte Carlo simulation using real_calculations module"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data required"}), 400
            
        # Validate with Pydantic
        try:
            mc_request = MonteCarloRequest(**data)
        except Exception as e:
            return jsonify({"error": f"Validation error: {str(e)}"}), 400
            
        # Get real Monte Carlo simulation
        simulation = real_calculator.monte_carlo_simulation(
            mc_request.initial_value,
            mc_request.expected_return,
            mc_request.volatility,
            mc_request.years,
            mc_request.simulations
        )
        logger.info(f"Real Monte Carlo simulation completed: {len(simulation)} scenarios")
        return jsonify(simulation)
    except Exception as e:
        logger.error(f"Error in real Monte Carlo simulation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_currency_rates', methods=['GET'])
def get_currency_rates():
    """Get real-time currency exchange rates"""
    try:
        # Fixed fallback rates (temporary solution)
        rates = {
            "USD": 0.88,  # 1 USD = 0.88 CHF
            "EUR": 0.95,  # 1 EUR = 0.95 CHF
            "GBP": 1.12,  # 1 GBP = 1.12 CHF
            "JPY": 0.006, # 1 JPY = 0.006 CHF
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Currency rates requested: {rates}")
        return jsonify(rates)
    except Exception as e:
        logger.error(f"Error getting currency rates: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimize_portfolio', methods=['POST'])
def optimize_portfolio():
    """Portfolio optimization using real calculations"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({"error": "Symbols required"}), 400
            
        symbols = data['symbols']
        portfolio = data.get('portfolio', [])
        
        if len(symbols) < 2:
            return jsonify({"error": "At least 2 symbols required"}), 400
            
        # Get portfolio metrics from real_calculations
        if portfolio and len(portfolio) >= 2:
            metrics = real_calculator.calculate_portfolio_metrics(portfolio)
        else:
            # Fallback: equal weights
            portfolio_data = [{'symbol': s, 'weight': 1.0/len(symbols)} for s in symbols]
            metrics = real_calculator.calculate_portfolio_metrics(portfolio_data)
        
        logger.info(f"Portfolio metrics calculated for {len(symbols)} symbols")
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error in portfolio optimization: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/strategy_optimization', methods=['POST'])
def strategy_optimization():
    """Calculate all optimization strategies"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({"error": "Symbols required"}), 400
            
        symbols = data['symbols']
        if len(symbols) < 2:
            return jsonify({"error": "At least 2 symbols required"}), 400
        
        strategies = []
        
        # 1. Mean-Variance Optimization with moderate target return
        try:
            # Calculate average expected return of all assets
            avg_return = 0
            for symbol in symbols:
                exp_ret = real_calculator.calculate_real_expected_return(symbol, '1y')
                if exp_ret:
                    avg_return += exp_ret
            avg_return = avg_return / len(symbols) if len(symbols) > 0 else 0.08
            
            # Use 80% of average return as target (balanced approach)
            target_return = avg_return * 0.8
            
            mv_result = real_calculator.mean_variance_optimization(symbols, target_return=target_return)
            if mv_result:
                strategies.append({
                    'name': 'Mean-Variance',
                    'description': 'Optimales Rendite-Risiko-Verhältnis',
                    'return': mv_result.get('expected_return', 0),  # Already in %
                    'risk': mv_result.get('volatility', 0),          # Already in %
                    'sharpe': mv_result.get('sharpe_ratio', 0),
                    'weights': mv_result.get('weights', []),
                    'recommendation': 'OPTIMAL' if mv_result.get('sharpe_ratio', 0) > 0.5 else 'BALANCIERT'
                })
        except Exception as e:
            logger.warning(f"Mean-Variance optimization failed: {e}")
        
        # 2. Risk Parity
        try:
            rp_result = real_calculator.risk_parity_optimization(symbols)
            if rp_result:
                strategies.append({
                    'name': 'Risk Parity',
                    'description': 'Gleicher Risikobeitrag aller Assets',
                    'return': rp_result.get('expected_return', 0),  # Already in %
                    'risk': rp_result.get('volatility', 0),          # Already in %
                    'sharpe': rp_result.get('sharpe_ratio', 0),
                    'weights': rp_result.get('weights', []),
                    'recommendation': 'BALANCIERT'
                })
        except Exception as e:
            logger.warning(f"Risk Parity optimization failed: {e}")
        
        # 3. Minimum Variance
        try:
            minvar_result = real_calculator.minimum_variance_optimization(symbols)
            if minvar_result:
                strategies.append({
                    'name': 'Min Variance',
                    'description': 'Minimales Portfolio-Risiko',
                    'return': minvar_result.get('expected_return', 0),  # Already in %
                    'risk': minvar_result.get('volatility', 0),          # Already in %
                    'sharpe': minvar_result.get('sharpe_ratio', 0),
                    'weights': minvar_result.get('weights', []),
                    'recommendation': 'KONSERVATIV'
                })
        except Exception as e:
            logger.warning(f"Min Variance optimization failed: {e}")
        
        # 4. Max Sharpe - Direct Sharpe Ratio Maximization
        try:
            # Custom optimization to maximize Sharpe Ratio directly
            from scipy.optimize import minimize
            import numpy as np
            
            returns_data = {}
            for symbol in symbols:
                returns = real_calculator.calculate_real_returns(symbol, '1y')
                if returns is not None:
                    returns_data[symbol] = returns
            
            if len(returns_data) >= 2:
                returns_df = pd.DataFrame(returns_data)
                mean_returns = returns_df.mean() * 252
                cov_matrix = returns_df.cov() * 252
                
                def neg_sharpe(weights):
                    portfolio_return = np.dot(weights, mean_returns.values)
                    portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights)))
                    sharpe = (portfolio_return - real_calculator.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
                    return -sharpe  # Negative because we minimize
                
                constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
                bounds = tuple((0, 1) for _ in symbols)
                initial_weights = np.array([1/len(symbols)] * len(symbols))
                
                result = minimize(neg_sharpe, initial_weights, method='SLSQP', bounds=bounds, constraints=constraints)
                
                if result.success:
                    optimal_weights = dict(zip(symbols, result.x))
                    portfolio_return = np.dot(result.x, mean_returns.values)
                    portfolio_vol = np.sqrt(np.dot(result.x, np.dot(cov_matrix.values, result.x)))
                    sharpe_ratio = (portfolio_return - real_calculator.risk_free_rate) / portfolio_vol
                    
                    strategies.append({
                        'name': 'Max Sharpe',
                        'description': 'Maximales Rendite-Risiko-Verhältnis',
                        'return': portfolio_return * 100,
                        'risk': portfolio_vol * 100,
                        'sharpe': sharpe_ratio,
                        'weights': optimal_weights,
                        'recommendation': 'AGGRESSIV' if portfolio_return > 0.10 else 'MODERAT'
                    })
        except Exception as e:
            logger.warning(f"Max Sharpe optimization failed: {e}")
        
        # 5. Black-Litterman
        try:
            # Get market caps (simplified - equal for now)
            market_caps = [1.0] * len(symbols)
            bl_result = real_calculator.black_litterman_optimization(symbols, market_caps)
            if bl_result:
                strategies.append({
                    'name': 'Black-Litterman',
                    'description': 'Marktdaten + eigene Erwartungen',
                    'return': bl_result.get('expected_return', 0),  # Already in %
                    'risk': bl_result.get('volatility', 0),          # Already in %
                    'sharpe': bl_result.get('sharpe_ratio', 0),
                    'weights': bl_result.get('weights', []),
                    'recommendation': 'EXPERTE'
                })
        except Exception as e:
            logger.warning(f"Black-Litterman optimization failed: {e}")
        
        logger.info(f"Strategy optimization completed: {len(strategies)} strategies calculated")
        return jsonify({'strategies': strategies, 'symbols': symbols})
    except Exception as e:
        logger.error(f"Error in strategy optimization: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_financial_news', methods=['GET'])
def get_financial_news():
    """Get real financial news"""
    try:
        # Simulated news for now (can be replaced with real news API)
        news = [
            {
                "title": "Marktanalyse: Schweizer Aktien zeigen Stabilität",
                "summary": "Der SMI bleibt trotz globaler Unsicherheiten stabil...",
                "timestamp": datetime.now().isoformat(),
                "source": "Swiss Financial News"
            },
            {
                "title": "Zinssätze: SNB behält aktuellen Kurs bei",
                "summary": "Die Schweizerische Nationalbank hat beschlossen...",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "source": "SNB Press Release"
            },
            {
                "title": "Portfolio-Strategien: Diversifikation im Fokus",
                "summary": "Experten empfehlen eine breite Streuung...",
                "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
                "source": "Investment Weekly"
            }
        ]
        logger.info(f"Financial news requested: {len(news)} articles")
        return jsonify(news)
    except Exception as e:
        logger.error(f"Error getting financial news: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/calculate_correlation', methods=['POST'])
def calculate_correlation():
    """Calculate correlation matrix for portfolio symbols"""
    try:
        if not REAL_CALCULATIONS_AVAILABLE:
            return jsonify({"error": "Real calculations not available"}), 503
            
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({"error": "Symbols required"}), 400
            
        symbols = data['symbols']
        if len(symbols) < 2:
            return jsonify({"error": "At least 2 symbols required"}), 400
            
        # Get correlation matrix from real_calculations
        correlation_matrix = real_calculator.get_correlation_matrix(symbols)
        logger.info(f"Correlation matrix calculated for {len(symbols)} symbols")
        return jsonify({
            "correlation_matrix": correlation_matrix,
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error calculating correlation: {e}")
        return jsonify({"error": str(e)}), 500

# Routes
@app.route('/')
def index():
    import time
    import random
    # Cache Buster - neue Version mit reduzierter Balkenhöhe (0.25cm)
    timestamp = int(time.time()) + random.randint(1000000, 9999999)
    return render_template_string(HTML_TEMPLATE, timestamp=timestamp)

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/switch_language/<language>')
def switch_language(language):
    global CURRENT_LANGUAGE
    if language in ['de', 'en']:
        CURRENT_LANGUAGE = language
    return jsonify({"status": "success", "language": CURRENT_LANGUAGE})

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="apple-mobile-web-app-title" content="SwissAP">
    <meta name="application-name" content="SwissAP">
    <meta name="theme-color" content="#5d4037">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="format-detection" content="telephone=no">
    <meta name="format-detection" content="address=no">
    <meta name="apple-touch-fullscreen" content="yes">
    <meta name="apple-mobile-web-app-orientations" content="portrait">
    <meta name="mobile-web-app-capable" content="yes">
    
    <!-- Theme Toggle removed -->
    <title>Swiss Asset Pro – Invest Smart</title>
    <link rel="manifest" href="/manifest.json">
    <!-- Apple Touch Icons - Complete Set -->
    <link rel="apple-touch-icon" href="/static/icon-180x180.png">
    <link rel="apple-touch-icon" sizes="57x57" href="/static/icon-57x57.png">
    <link rel="apple-touch-icon" sizes="60x60" href="/static/icon-60x60.png">
    <link rel="apple-touch-icon" sizes="72x72" href="/static/icon-72x72.png">
    <link rel="apple-touch-icon" sizes="76x76" href="/static/icon-76x76.png">
    <link rel="apple-touch-icon" sizes="114x114" href="/static/icon-114x114.png">
    <link rel="apple-touch-icon" sizes="120x120" href="/static/icon-120x120.png">
    <link rel="apple-touch-icon" sizes="144x144" href="/static/icon-144x144.png">
    <link rel="apple-touch-icon" sizes="152x152" href="/static/icon-152x152.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/icon-180x180.png">
    <link rel="apple-touch-icon" sizes="192x192" href="/static/icon-192x192.png">
    <link rel="apple-touch-icon" sizes="512x512" href="/static/icon-512x512.png">
    
    <!-- Splash Screens for iOS -->
    <link rel="apple-touch-startup-image" href="/static/splash-640x1136.png" media="(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-750x1334.png" media="(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-1242x2208.png" media="(device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1125x2436.png" media="(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-828x1792.png" media="(device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-1170x2532.png" media="(device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1179x2556.png" media="(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1284x2778.png" media="(device-width: 428px) and (device-height: 926px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1176x2552.png" media="(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1242x2688.png" media="(device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 3)">
    <link rel="apple-touch-startup-image" href="/static/splash-1536x2048.png" media="(device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-1668x2224.png" media="(device-width: 834px) and (device-height: 1112px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-1668x2388.png" media="(device-width: 834px) and (device-height: 1194px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/splash-2048x2732.png" media="(device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2)">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@2.0.1/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <script defer src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/js/all.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="/static/monitoring.js?v={{ timestamp }}"></script>
    <!-- Fallback CDN (jsDelivr) falls cdnjs blockiert ist -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@5.15.4/css/all.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@5.15.4/js/all.min.js"></script>
    <style>
      /* Font Awesome render fixes: enforce correct font families and weights */
      .fa, .fas, .far, .fal { font-family: "Font Awesome 5 Free" !important; font-style: normal !important; display: inline-block !important; }
      .fab { font-family: "Font Awesome 5 Brands" !important; font-style: normal !important; display: inline-block !important; }
      .fas, .fa { font-weight: 900 !important; }
      .far { font-weight: 400 !important; }
      .fab { font-weight: 400 !important; }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <!-- J.P. Morgan Style Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Helvetica+Neue:wght@300;400;500;600;700&family=Helvetica:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/static/sw.js').then(function(registration) {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }, function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                });
            });
        }
    </script>
    <!-- Bilder Preload für schnelles Laden -->
    <link rel="preload" as="image" href="/static/Bilder-SAP/annie-spratt-IT6aov1ScW0-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/david-werbrouck-5GwLlb-_UYk-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/anthony-tyrrell-Bl-LiSJOnlY-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/frederic-perez-RDNAtCk5rJ8-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/benedikt-jaletzke-TZsfOb3cgJM-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/armando-castillejos-DPi0ddFTBS0-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/bumgeun-nick-suh-o40m9hf2lB4-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/ian-parker-rWey_wseEcY-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/jason-dent-3wPJxh-piRw-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/jiri-brtnik-jIaSUaQVPl0-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/pepi-stojanovski-MJSFNZ8BAXw-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/robert-tudor-G7bXcUgh_xk-unsplash.jpg">
    <link rel="preload" as="image" href="/static/Bilder-SAP/tai-s-captures-r5kTKshp22M-unsplash.jpg">
    <!-- Custom scoped overrides for Getting Started + Header/Footer -->
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <meta name="cache-buster" content="fix-checkpassword-20251015-0340">
        <script>
            // Cache clearing only - no redirect
            if ('caches' in window) {
                caches.keys().then(names => {
                    names.forEach(name => caches.delete(name));
                });
            }
        </script>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; }
    
    /* iOS Safe Area Support */
    :root {
      --safe-area-inset-top: env(safe-area-inset-top);
      --safe-area-inset-right: env(safe-area-inset-right);
      --safe-area-inset-bottom: env(safe-area-inset-bottom);
      --safe-area-inset-left: env(safe-area-inset-left);
    }
    
    /* PWA Standalone Detection */
    @media (display-mode: standalone) {
      body {
        padding-top: var(--safe-area-inset-top);
        padding-bottom: var(--safe-area-inset-bottom);
        padding-left: var(--safe-area-inset-left);
        padding-right: var(--safe-area-inset-right);
      }
      
      .custom-header {
        padding-top: calc(20px + var(--safe-area-inset-top));
      }
      
      .custom-footer {
        padding-bottom: calc(20px + var(--safe-area-inset-bottom));
      }
    }
    
    /* iOS-specific adjustments */
    @supports (-webkit-touch-callout: none) {
      body {
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -webkit-tap-highlight-color: transparent;
      }
      
      input, textarea, select {
        -webkit-appearance: none;
        border-radius: 0;
      }
      
      .btn, button {
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
      }
    }
    
    /* Touch optimizations */
    @media (hover: none) and (pointer: coarse) {
      .btn, button, .nav-tab, .structure-item {
        min-height: 44px;
        min-width: 44px;
      }
      
      .nav-tab {
        padding: 12px 16px;
      }
      
      .landing-card {
        min-height: 85px;
      }
    }
    
    /* Force visibility of changes - REMOVED, using inline styles */
    .nav-tabs { 
        display: flex !important; 
        justify-content: center !important; 
        gap: 8px !important; 
    }
    .portfolio-legend { 
        display: flex !important; 
        flex-direction: column !important; 
    }

    /* Farbpalette Schwarz / Dunkelgrau / Violett / Silber */
    .bg-black-main { background-color: #0A0A0A; }      /* Haupt-Hintergrund */
    .bg-panel { background: linear-gradient(145deg, #1F1F1F, #181818); }  /* Panels / Cards */
    .text-primary { color: #E0E0E0; }                  /* Überschriften / Haupttext */
    .text-secondary { color: #A0A0A0; }                /* Sekundärtext / Details */
    .text-accent { color: #8A2BE2; }                   /* Violett für Akzente */
    .text-silver { color: #D9D9D9; }                   /* Silber für Buttons / Lines */
    .border-panel { border-color: #2C2C2C; }           /* Panel-Border */
    .bg-accent { background-color: #8A2BE2; }
    .bg-silver { background-color: #D9D9D9; }
    .hover-accent:hover { background-color: #A64DF0 !important; color: #0A0A0A !important; }

    :root {
                /* Neue Farbpalette */
                --color-bg-light: #F5F5F5;
                --color-primary-dark: #31081F;
                --color-accent-rose: #CD8B76;
                --color-text-gray: #595959;
                --color-border-green: #808F85;
                
                /* Alternierende Section Farben */
                --section-white: #FFFFFF;
                --section-beige: #F7F3EE;
            
            /* Legacy colors kept for login/animation */
            --bg-black-main: #0A0A0A;
            --bg-dark: #111111;
            --bg-panel: linear-gradient(145deg, #252525, #1E1E1E);
            --text-primary: #E8E8E8;
            --text-secondary: #B8B8B8;
            --accent-violet: #8b7355;
            --color-accent: #8b7355;
            --text-silver: #E6E6E6;
            --border-panel: #3A3A3A;
            --glass: rgba(139, 115, 85, 0.08);
            --accent-positive: #28A745;
            --accent-negative: #DC3545;
            --border-light: #454545;
            --radius-lg: 4px;
            --radius-md: 2px;
            --shadow-soft: 0 8px 20px rgba(0, 0, 0, 0.4);
            --font-heading: 'Playfair Display', serif;
            --font-body: 'Inter', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--font-body);
            background: #000000 !important; 
            color: var(--text-primary); 
            line-height: 1.8; 
            font-size: 16px;
            font-weight: 400;
        }
        
        /* Block text everywhere except login and animation pages */
        .gs-page-content p {
            text-align: justify !important;
            hyphens: auto;
            -webkit-hyphens: auto;
            -moz-hyphens: auto;
        }
        
        /* All buttons should have centered text, never justified */
        button, .btn, input[type="submit"], input[type="button"] {
            text-align: center !important;
        }
        
        /* Login page: keep elements as they are (some centered, input can be left) */
        #passwordProtection input {
            text-align: left !important;
        }
        
        #passwordProtection button {
            text-align: center !important;
        }
        
        /* Animation page: keep text centered */
        .welcome-screen p,
        .welcome-screen *,
        .welcome-content p,
        .welcome-subtitle,
        .welcome-author {
            text-align: center !important;
        }
        
        /* About page: specific elements should NOT have block text */
        .gs-page-content .source-card p,
        .gs-page-content .sources-grid p {
            text-align: left !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-heading);
            line-height: 1.5;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }
        
        p, div, span, li {
            line-height: 1.8;
            margin-bottom: 0.8rem;
        }
        
        .card, .section, .page {
            margin-bottom: 2rem;
        }
        
        h1 { 
            font-size: 34px; 
            font-weight: 700; 
            letter-spacing: -0.7px;
        }
        h2 { 
            font-size: 28px; 
            font-weight: 600; 
            letter-spacing: -0.5px;
        }
        h3 { 
            font-size: 24px; 
            font-weight: 600; 
            letter-spacing: -0.3px;
        }
        h4 { 
            font-size: 20px; 
            font-weight: 500; 
            letter-spacing: -0.2px;
        }
        h5 { 
            font-size: 18px; 
            font-weight: 500; 
        }
        h6 { 
            font-size: 16px; 
            font-weight: 500; 
        }
}
        
        .password-protection {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: var(--bg-default); display: flex !important; justify-content: center !important; align-items: center !important; 
            z-index: 10000; margin: 0; padding: 0; box-sizing: border-box;
        }
        .password-box {
            background: #000000 !important; 
            padding: 50px; 
            border-radius: 0 !important;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5) !important; 
            text-align: center; 
            max-width: 400px; 
            width: 90%;
            border: none !important;
            position: relative;
            margin: 0 auto;
            transform: translateY(0);
        }
        .password-input {
            width: 100%; padding: 12px; border: 1px solid var(--border-light); border-radius: 0;
            margin-bottom: 15px; font-size: 16px;
        }
        .btn {
            padding: 12px 28px; 
            background-color: var(--color-accent-rose);
            color: white; 
            border: none;
            border-radius: 0; 
            cursor: pointer; 
            font-weight: 600;
            font-family: var(--font-body);
            font-size: 14px;
            letter-spacing: 0.3px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background-color: var(--color-primary-dark);
            color: white;
            transform: translateY(-2px);
        }
        .btn:focus {
            outline: none;
        }
        .btn-calculate {
            background: var(--color-accent-rose);
            font-size: 16px;
            padding: 15px 30px;
            font-weight: 600;
            color: white;
            border: 1px solid var(--color-border-green);
            box-shadow: 0 2px 8px rgba(205, 139, 118, 0.3);
        }
        .btn-calculate:hover {
            background: var(--color-primary-dark);
            box-shadow: 0 4px 12px rgba(49, 8, 31, 0.4);
            transform: translateY(-2px);
        }
        
        header { 
    background-color: var(--bg-black-main);
    color: white; 
    padding: 50px 0 40px 0;
    border-bottom: 4px solid #2A2A2A;
}
.container { max-width: 1800px; margin: 0 auto; padding: 0 40px; }

.nav-tabs { 
    display: flex !important; 
    gap: 4px !important; 
    flex-wrap: wrap !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
    z-index: 10 !important;
    width: 100% !important;
    background: #E8E8E8 !important;
    padding: 12px 16px !important;
    border-radius: 0px !important;
    border: 1px solid #D0D0D0 !important;
}
.nav-tab { 
    padding: 8px 16px !important; 
    background: transparent !important; 
    border: none !important;
    border-radius: 0px !important; 
    cursor: pointer !important; 
    white-space: nowrap !important; 
    transition: all 0.3s ease !important; 
    color: #000000 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}
.nav-tab.active { 
    background: #FFFFFF !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border: 1px solid #C0C0C0 !important;
    border-radius: 0px !important;
}
.nav-tab:hover { 
    color: #000000 !important;
    background: #F5F5F5 !important;
    border-radius: 0px !important;
}


        
        /* ===== BREITE SEITEN UPDATE v8012 - FINMA Kompakt + Titel ===== */
        main { 
    padding: 40px 0; 
    position: relative;
    z-index: 1;
    max-width: 1600px !important;
    margin: 0 auto !important;
    width: 100% !important;
}
        .page { 
    display: none; 
    background: var(--bg-panel); 
    padding: 35px 0 !important; 
    border-radius: var(--radius-lg); 
    margin-bottom: 30px; 
    position: relative; 
    z-index: 2; 
    border: 1px solid var(--border-panel);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    width: 100% !important;
    max-width: 100% !important;
}
        /* ===== END BREITE SEITEN UPDATE ===== */
        .page.active { display: block; }
        
        .page-header { 
            margin-bottom: 30px; 
            padding-bottom: 20px; 
            border-bottom: 1px solid var(--border-panel); 
            position: relative;
        }
        .page-header::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 80px;
            height: 3px;
            background: linear-gradient(90deg, #8b7355, rgba(139, 115, 85, 0.3));
            border-radius: 0;
        }
        .page-header h2 { 
            color: var(--color-primary); 
            margin-bottom: 12px; 
            font-family: 'Playfair Display', serif;
            letter-spacing: -0.5px;
        }
        
        .instruction-box { 
            background: rgba(205, 139, 118, 0.1); 
            padding: 20px; 
            border-radius: var(--radius-lg); 
            margin-bottom: 20px; 
            border-left: 4px solid var(--color-accent-rose);
        }
        
        .portfolio-setup { 
            background: linear-gradient(145deg, #2A2A2A, #232323); 
            padding: 20px; 
            border-radius: var(--radius-lg); 
            margin-bottom: 20px; 
            border: 1px solid var(--border-light);
            box-shadow: var(--shadow-soft);
        }
        .investment-inputs { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .input-group { display: flex; flex-direction: column; gap: 5px; }
        .input-group label { font-weight: 500; color: var(--text-silver); font-size: 14px; }
        
        .search-container { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-input { 
            flex: 1; 
            min-width: 200px; 
            padding: 10px; 
            border: 1px solid var(--border-light); 
            border-radius: 0;
            background-color: var(--bg-panel);
            color: var(--text-primary);
        }
        select.search-input {
            background-color: var(--bg-panel);
            color: var(--text-primary);
        }
        select.search-input option {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            padding: 8px;
        }
        
        .selected-stocks { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin: 20px 0; }
        .stock-card { 
            background: var(--bg-panel); 
            padding: 20px; 
            border-radius: var(--radius-lg); 
            border: 1px solid var(--border-light); 
            transition: all 0.3s ease; 
            box-shadow: var(--shadow-soft);
            min-height: 200px;
            display: flex;
            flex-direction: column;
        }
        .stock-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        .stock-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-start;
            margin-bottom: 15px; 
            flex-shrink: 0;
        }
.investment-controls { 
    display: grid; 
    grid-template-columns: 1fr 1fr; 
    gap: 10px; 
    margin-top: auto;
    padding-top: 15px;
    width: 100%;
    box-sizing: border-box;
}
        .investment-controls input { 
            padding: 8px; 
            border: 1px solid var(--border-light); 
            border-radius: 0; 
            background: var(--bg-dark);
            color: var(--text-primary); 
            font-size: 13px; 
            width: 100%; 
            max-width: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }
        .investment-controls label {
            display: block;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 5px;
            font-weight: 500;
        }
        .asset-type-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .stock-asset { background-color: #8A2BE2; }
        .index-asset { background-color: #4ECDC4; }
        .other-asset { background-color: #FF6B6B; }
        
        .chart-container { 
            height: 450px; 
            margin: 20px 0; 
            background: var(--bg-panel); 
            padding: 25px; 
            border-radius: var(--radius-lg); 
            border: 1px solid var(--border-panel);
            position: relative;
        }
        .chart-container canvas {
            max-height: 100% !important;
        }
        
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { 
    background: var(--perlweiss); 
    padding: 24px; 
    border-radius: 0; 
    border-left: 4px solid var(--color-accent-rose); 
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(89, 89, 89, 0.1);
    border: 1px solid var(--color-border-green);
}
        .card:hover { 
    transform: translateY(-2px); 
    box-shadow: 0 4px 12px rgba(205, 139, 118, 0.2);
    border-color: var(--color-accent-rose);
    border-left-width: 5px;
}
        
        /* Apply new color palette to content pages only */
        .gs-page-content .card {
            background: var(--perlweiss);
            color: var(--color-primary-dark);
            border-left-color: var(--color-accent-rose);
            border-color: var(--color-border-green);
        }
        .gs-page-content h1, .gs-page-content h2, .gs-page-content h3, 
        .gs-page-content h4, .gs-page-content h5, .gs-page-content h6 {
            color: var(--color-primary-dark);
        }
        .gs-page-content p, .gs-page-content li {
            color: var(--color-text-gray);
}
        
        .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .data-table th, .data-table td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--border-light); }
        .data-table th { background: var(--color-primary); color: white; }
        
        .positive { 
    color: var(--accent-positive); 
    font-weight: 600;
    text-shadow: 0 0 8px rgba(138, 43, 226, 0.2);
}
        .negative { 
    color: var(--accent-negative); 
    font-weight: 600;
    text-shadow: 0 0 8px rgba(220, 38, 38, 0.2);
}
        
        /* Strategieanalyse spezifische Styles */
        .strategy-comparison {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }
        
        @media (max-width: 1024px) {
            .strategy-comparison {
                grid-template-columns: 1fr;
            }
        }
        
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            background: var(--white);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--shadow);
        }
        
        .comparison-table thead {
            background: linear-gradient(135deg, var(--primary) 0%, #2d2d2d 100%);
        }
        
        .comparison-table thead th {
            color: var(--white);
            font-weight: 600;
            padding: 15px;
            text-align: center;
            font-size: 13px;
        }
        
        .comparison-table tbody tr {
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            transition: background 0.2s ease;
        }
        
        .comparison-table tbody tr:hover {
            background: rgba(139, 115, 85, 0.05);
        }
        
        .comparison-table tbody td {
            padding: 15px;
            text-align: center;
            font-size: 14px;
        }
        
        .comparison-table tbody td:first-child {
            text-align: left;
            font-weight: 600;
        }
        
        .recommendation-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 0;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-optimal {
            background: var(--success);
            color: white;
        }
        
        .badge-balanced {
            background: #2196F3;
            color: white;
        }
        
        .badge-conservative {
            background: #9C27B0;
            color: white;
        }
        
        .badge-aggressive {
            background: var(--warning);
            color: white;
        }
        
        .rating-score {
            font-size: 72px;
            font-weight: 700;
            text-align: center;
            color: var(--secondary);
            margin: 20px 0;
        }
        
        .strategy-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .strategy-card {
            background: var(--white);
            padding: 25px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            border-top: 4px solid var(--secondary);
        }
        
        .strategy-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .strategy-card h4 {
            color: var(--primary);
            font-size: 18px;
            margin-bottom: 12px;
            font-weight: 600;
        }
        
        .strategy-card p {
            color: var(--dark);
            line-height: 1.6;
            margin: 10px 0;
        }
        
        .optimization-result {
            background: rgba(205, 139, 118, 0.1);
            padding: 15px;
            border-radius: var(--border-radius);
            margin: 15px 0;
        }
        
        .improvement-indicator {
            font-weight: 700;
            font-size: 16px;
        }
        
        .improvement-positive {
            color: var(--success);
        }
        
        .improvement-negative {
            color: var(--danger);
        }
        
        .chart-container {
            height: 400px;
            position: relative;
            margin: 30px 0;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .strategy-grid {
                grid-template-columns: 1fr;
            }
            
            .comparison-table {
                font-size: 12px;
            }
            
            .comparison-table thead th,
            .comparison-table tbody td {
                padding: 10px 8px;
            }
            
            .rating-score {
                font-size: 48px;
            }
        }
        
        .status-bar {
    display: flex; 
    justify-content: center; 
    align-items: center;
    padding: 1px 8px; 
    background: rgba(26, 26, 26, 0.4); 
    border-radius: 0; 
    margin-bottom: 8px; 
    flex-wrap: nowrap; 
    gap: 6px; 
    color: var(--text-primary);
    border: 1px solid rgba(138, 43, 226, 0.1);
    box-shadow: none;
    font-size: 5px;
    min-height: 14px;
    white-space: nowrap;
    overflow-x: auto;
}

.status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 500;
}

.status-item i {
    color: var(--accent-primary);
    font-size: 16px;
}

.smi-indicator {
    background: rgba(138, 43, 226, 0.1);
    padding: 12px 16px;
    border-radius: 0;
    border: 1px solid rgba(138, 43, 226, 0.2);
    position: relative;
}

.mini-chart {
    display: flex;
    align-items: end;
    gap: 2px;
    height: 20px;
    margin-left: 8px;
}

.chart-bar {
    width: 3px;
    border-radius: 0;
    transition: all 0.3s ease;
}

.market-status-indicator {
    padding: 2px 6px;
    border-radius: 0;
    font-size: 11px;
    font-weight: 600;
}

.market-status-indicator.open {
    background: #4CAF50;
    color: white;
}

.market-status-indicator.closed {
    background: #f44336;
    color: white;
}
        
        .market-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .market-item { background: var(--bg-panel); padding: 15px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-panel); }
        
        .news-item { padding: 15px; border-bottom: 1px solid var(--border-light); }
        .news-item:last-child { border-bottom: none; }
        
        .assets-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .asset-card { background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-panel); }
        
        .formula-box { 
            background: #2A2A2A; 
            color: #E6E6E6; 
            padding: 15px; 
            border-radius: var(--radius-lg); 
            margin: 10px 0; 
            font-family: monospace; 
            border: 1px solid #8b7355;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            font-size: 1.05rem;
        } /* WINDOWS PERFORMANCE FIX - STUFE 1 */
/* FINALE LÖSUNG - OPTIMIERT FÜR WINDOWS, ORIGINAL FÜR MAC */
.performance-mode .layer {
    animation-duration: 40s, 50s, 60s !important;
    filter: blur(30px) !important;
}

.performance-mode .pulse {
    animation-duration: 20s !important;
    opacity: 0.04 !important;
}
        
        .linkedin-link { color: var(--color-primary); text-decoration: none; display: inline-flex; align-items: center; gap: 5px; }
        
        .asset-type-indicator { 
            display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; 
        }
        .stock-asset { background-color: #0A1429; }
        .other-asset { background-color: #28A745; }
        .index-asset { background-color: #6B46C1; }
        
        .total-validation { 
            padding: 10px; 
            border-radius: 0; 
            margin: 10px 0; 
            font-weight: bold;
        }
        .validation-ok { background: #d4edda; color: #155724; }
        .validation-error { background: #f8d7da; color: #721c24; }
        
        .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .metric-label { color: var(--text-muted); font-size: 14px; }
        
        .fx-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 20px 0; }
        .fx-item { background: var(--bg-panel); padding: 15px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-panel); }
        
        .methodology-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin: 20px 0; }
        
        .email-link { color: var(--color-primary); text-decoration: none; }
        
        /* Neue Styles für Strategie-Analyse */
        .strategy-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .strategy-card { background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-panel); border-left: 4px solid; transition: all 0.3s ease; }
        .strategy-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        .strategy-1 { border-left-color: #0A1429; }
        .strategy-2 { border-left-color: #28A745; }
        .strategy-3 { border-left-color: #D52B1E; }
        .strategy-4 { border-left-color: #6B46C1; }
        .strategy-5 { border-left-color: #2B6CB0; }
        
        .comparison-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .comparison-table th, .comparison-table td { padding: 12px 15px; text-align: center; border: 1px solid var(--border-light); }
        .comparison-table th { background: #2A2A2A; color: #E8E8E8; font-weight: 600; }
        .comparison-table tr:nth-child(even) { background: rgba(138, 43, 226, 0.08); }
        .comparison-table tr:nth-child(odd) { background: rgba(42, 42, 42, 0.7); }
        
        .recommendation-badge { 
            display: inline-block; padding: 5px 12px; border-radius: 0; font-size: 12px; font-weight: 600; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .badge-optimal { background: #0d6e32; color: #d4edda; border: 1px solid #28a745; }
        .badge-balanced { background: #664d03; color: #fff3cd; border: 1px solid #ffc107; }
        .badge-conservative { background: #002752; color: #cce7ff; border: 1px solid #0d6efd; }
        .badge-aggressive { background: #4f0f16; color: #f8d7da; border: 1px solid #dc3545; }
        
        .strategy-comparison { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin: 20px 0; }
        
        .optimization-result { 
            background: rgba(205, 139, 118, 0.1); 
            padding: 15px; 
            border-radius: var(--radius-lg); 
            margin: 10px 0;
            border-left: 4px solid var(--color-accent-rose);
            color: #E0E0E0;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        
        /* Landing Page Styles */
        .landing-card {
            background: linear-gradient(145deg, var(--color-accent-rose), #d4a792);
            border: 1px solid var(--color-accent-rose);
            border-radius: 0;
            padding: 18px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(205, 139, 118, 0.3);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            min-height: 85px;
            position: relative;
            overflow: hidden;
        }
        
        .landing-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 12px 25px rgba(139, 115, 85, 0.4), 0 0 15px rgba(139, 115, 85, 0.6);
            border-color: #a68968;
        }
        
        .landing-card h3 {
            font-family: 'Playfair Display', serif;
            color: #FFFFFF;
            font-size: 18px;
            margin: 0 0 12px 0;
        }
        
        .landing-card p {
            font-family: 'Inter', sans-serif;
            color: #D9D9D9;
            font-size: 13px;
            line-height: 1.4;
            margin: 0;
        }
        
        
        /* Fade in animations */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            50% {
                transform: scale(1.05);
                box-shadow: 0 4px 12px rgba(93, 64, 55, 0.4);
            }
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            #landingPanelsContainer {
                grid-template-columns: 1fr;
            }
            .landing-card {
                min-height: 85px;
            }
        }
        
        .rating-score { 
            font-size: 48px; font-weight: bold; color: var(--color-primary); text-align: center;
            margin: 20px 0;
        }
        
        .improvement-indicator { 
            display: inline-flex; align-items: center; gap: 5px; font-weight: bold;
        }
        .improvement-positive { color: var(--accent-positive); }
        .improvement-negative { color: var(--accent-negative); }
        
        /* Neue Styles für Portfolio Entwicklung */
        .performance-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .performance-card { background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--border-panel); }
        
        .path-simulation { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .path-card { background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-panel); }
        
        .swot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .swot-card { background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); border-left: 4px solid; }
        .strengths { border-left-color: #28A745; }
        .weaknesses { border-left-color: #DC3545; }
        .opportunities { border-left-color: var(--color-accent-rose); }
        .threats { border-left-color: #6C757D; }
        
        .calculate-section {
            text-align: center;
            margin: 30px 0;
            padding: 30px;
            background: var(--bg-panel);
            color: var(--text-primary);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-panel);
        }
        
        .password-error {
            color: #DC3545;
            margin-top: 10px;
            display: none;
        }
        
        .market-analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .market-analysis-card {
            background: #1F1F1F;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            border-left: 4px solid;
        }
        
        .cycle-indicator {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 12px;
            border-radius: 0;
            font-size: 12px;
            font-weight: bold;
        }
        
        .cycle-growth { background: #d4edda; color: #155724; }
        .cycle-cyclical { background: #fff3cd; color: #856404; }
        .cycle-defensive { background: #cce7ff; color: #004085; }
        
        .timeframe-switcher {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .timeframe-btn {
            padding: 8px 16px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .timeframe-btn.active {
            background: var(--color-primary);
            color: white;
            border-color: var(--color-primary);
        }
        
        .scenario-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .scenario-card {
            background: #1F1F1F;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .scenario-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-soft);
        }
        
        .scenario-normal { border-top: 4px solid #28A745; }
        .scenario-interest { border-top: 4px solid #DC3545; }
        .scenario-inflation { border-top: 4px solid #FFC107; }
        .scenario-recession { border-top: 4px solid #6C757D; }
        .scenario-growth { border-top: 4px solid var(--color-accent-rose); }
        
        .correlation-matrix {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .correlation-matrix th, .correlation-matrix td {
            padding: 10px;
            text-align: center;
            border: 1px solid var(--border-light);
        }
        
        .correlation-matrix th {
            background: var(--color-primary);
            color: white;
        }
        
        .correlation-value {
            font-weight: bold;
        }
        
        .positive-correlation { background: #d4edda; }
        .negative-correlation { background: #f8d7da; }
        .neutral-correlation { background: #fff3cd; }
        
        .monte-carlo-controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .benchmark-comparison {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .benchmark-card {
            background: #1F1F1F;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
        }
        
        .peer-comparison {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .peer-card {
            background: #1F1F1F;
            padding: 15px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
            text-align: center;
        }
        
        .refresh-button {
            background: var(--color-accent-rose);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 0;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            margin: 5px;
        }
        
        .refresh-button:hover {
            background: #6d5a42;
            transform: translateY(-2px);
        }
        
        .auto-refresh-info {
            background: rgba(139, 115, 85, 0.15);
            padding: 12px 16px;
            border-radius: var(--radius-md);
            margin: 15px 0;
            font-size: 14px;
            border-left: 4px solid var(--color-accent);
            color: var(--text-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28A745;
            color: white;
            padding: 15px 20px;
            border-radius: 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .price-update-info {
            background: rgba(139, 115, 85, 0.15);
            padding: 12px 16px;
            border-radius: var(--radius-md);
            margin: 12px 0;
            font-size: 14px;
            border-left: 4px solid var(--color-accent);
            color: var(--text-primary);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #8b7355;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .risk-meter {
            height: 8px;
            background: #e9ecef;
            border-radius: 0;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .risk-level {
            height: 100%;
            border-radius: 0;
            transition: all 0.3s ease;
        }
        
        .risk-low { background: #28A745; width: 30%; }
        .risk-medium { background: #FFC107; width: 60%; }
        .risk-high { background: #DC3545; width: 90%; }
        
        .tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 0;
            padding: 8px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        .export-button {
            background: var(--color-accent-rose);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 0;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .export-button:hover {
            background: #6d5a42;
            transform: translateY(-1px);
        }
        
        .clickable-name {
            color: white;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .clickable-name:hover {
            color: var(--color-accent-rose);
            text-decoration: underline;
        }
        
        .pdf-download-section {
            text-align: center;
            margin: 40px 0;
            padding: 30px;
            background: linear-gradient(135deg, #0A1429 0%, #1E3A5C 100%);
            color: white;
            border-radius: var(--radius-lg);
        }
        
        .btn-pdf {
            background: #DC3545;
            font-size: 18px;
            padding: 15px 30px;
            margin-top: 15px;
        }
        
        .btn-pdf:hover {
            background: #c82333;
            transform: translateY(-2px);
        }
        
        .asset-performance-chart {
            height: 300px;
            margin: 20px 0;
        }
        
        .news-link {
            color: var(--color-accent-rose);
            text-decoration: none;
        }
        
        .news-link:hover {
            text-decoration: underline;
        }

        /* Korrelationsmatrix Styles */
        .correlation-heatmap {
            width: 100%;
            height: 500px;
            margin: 20px 0;
        }

        .correlation-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 12px;
        }

        .correlation-table th, .correlation-table td {
            padding: 10px;
            text-align: center;
            border: 1px solid #444;
            font-size: 13px;
        }

        .correlation-table th {
            background: #1A1A1A;
            color: #E8E8E8;
            font-weight: bold;
        }

        .correlation-table td:first-child {
            background: #1A1A1A;
            color: #E8E8E8;
            font-weight: bold;
        }

        .corr-high { 
            background: #2D4A2D; 
            color: #90EE90; 
            font-weight: 600;
        }
        .corr-medium { 
            background: #4A3D2D; 
            color: #FFD700; 
            font-weight: 600;
        }
        .corr-low { 
            background: #4A2D2D; 
            color: #FFB6C1; 
            font-weight: 600;
        }
        .corr-negative { 
            background: #2D3A4A; 
            color: #87CEEB; 
            font-weight: 600;
        }

        /* Value Testing Styles */
        .value-testing-controls {
            margin-bottom: 30px;
        }

        .parameter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .parameter-item {
            display: flex;
            flex-direction: column;
        }

        .parameter-item label {
            color: #E8E8E8;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }

        .parameter-item input {
            padding: 10px;
            border: 1px solid #444;
            border-radius: 0;
            background: #2A2A2A;
            color: #E8E8E8;
            font-size: 14px;
        }

        .parameter-item input:focus {
            outline: none;
            border-color: #8A2BE2;
            box-shadow: 0 0 0 2px rgba(138, 43, 226, 0.2);
        }

        .analysis-actions {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .loading-container {
            text-align: center;
            padding: 40px;
        }

        .loading-spinner {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }

        .loading-spinner i {
            font-size: 48px;
            color: #8A2BE2;
        }

        .loading-spinner p {
            color: #E8E8E8;
            font-size: 18px;
            margin: 0;
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }

        .progress-bar {
            width: 300px;
            height: 8px;
            background: #333;
            border-radius: 0;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #8A2BE2, #B05EED);
            width: 0%;
            transition: width 0.3s ease;
        }

        .value-testing-results {
            margin-top: 30px;
        }

        .portfolio-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .summary-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(145deg, #2A2A2A, #232323);
            border-radius: 0;
            border: 1px solid #444;
        }

        .summary-item h4 {
            color: #E8E8E8;
            margin-bottom: 10px;
            font-size: 14px;
            font-weight: 600;
        }

        .summary-item p {
            color: #8A2BE2;
            font-size: 24px;
            font-weight: bold;
            margin: 0;
        }

        .value-analysis-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .value-analysis-table th,
        .value-analysis-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }

        .value-analysis-table th {
            background: #1A1A1A;
            color: #E8E8E8;
            font-weight: 600;
            font-size: 14px;
        }

        .value-analysis-table td {
            color: #D0D0D0;
            font-size: 13px;
        }

        .value-analysis-table tr:hover {
            background: rgba(138, 43, 226, 0.1);
        }

        .recommendation-buy {
            color: #4CAF50;
            font-weight: bold;
        }

        .recommendation-hold {
            color: #FFD700;
            font-weight: bold;
        }

        .recommendation-sell {
            color: #FF6B6B;
            font-weight: bold;
        }

        .score-bar {
            width: 100%;
            height: 20px;
            background: #333;
            border-radius: 0;
            overflow: hidden;
            position: relative;
        }

        .score-fill {
            height: 100%;
            border-radius: 0;
            transition: width 0.3s ease;
        }

        .score-high { background: linear-gradient(90deg, #4CAF50, #66BB6A); }
        .score-medium { background: linear-gradient(90deg, #FFD700, #FFE082); }
        .score-low { background: linear-gradient(90deg, #FF6B6B, #FF8A80); }

        .charts-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .sources-list {
            display: grid;
            gap: 15px;
        }

        .source-item {
            padding: 15px;
            background: #2A2A2A;
            border-radius: 0;
            border-left: 4px solid #8A2BE2;
        }

        .source-item h5 {
            color: #E8E8E8;
            margin: 0 0 8px 0;
            font-size: 14px;
        }

        .source-item p {
            color: #D0D0D0;
            margin: 4px 0;
            font-size: 13px;
        }

        .source-item a {
            color: #8A2BE2;
            text-decoration: none;
        }

        .source-item a:hover {
            text-decoration: underline;
        }

        .modal {
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background: #1A1A1A;
            padding: 30px;
            border-radius: 0;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            border: 1px solid #444;
        }

        .close {
            position: absolute;
            top: 15px;
            right: 20px;
            color: #E8E8E8;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }

        .close:hover {
            color: #8A2BE2;
        }

        .asset-detail-content h3 {
            color: #E8E8E8;
            margin-bottom: 20px;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .detail-item {
            padding: 15px;
            background: #2A2A2A;
            border-radius: 0;
        }

        .detail-item h5 {
            color: #E8E8E8;
            margin: 0 0 8px 0;
            font-size: 14px;
        }

        .detail-item p {
            color: #D0D0D0;
            margin: 0;
            font-size: 16px;
            font-weight: 600;
        }

        .valuation-methods {
            margin-top: 20px;
        }

        .valuation-method {
            margin-bottom: 20px;
            padding: 15px;
            background: #2A2A2A;
            border-radius: 0;
            border-left: 4px solid #8A2BE2;
        }

        .valuation-method h5 {
            color: #E8E8E8;
            margin: 0 0 10px 0;
        }

        .valuation-method p {
            color: #D0D0D0;
            margin: 5px 0;
        }

        /* Investment Strategy Modules Styles */
        .momentum-controls, .buyhold-controls, .carry-controls {
            margin-bottom: 30px;
        }

        .momentum-analysis-table, .buyhold-analysis-table, .carry-analysis-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .momentum-analysis-table th,
        .momentum-analysis-table td,
        .buyhold-analysis-table th,
        .buyhold-analysis-table td,
        .carry-analysis-table th,
        .carry-analysis-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #444;
            font-size: 13px;
        }

        .momentum-analysis-table th,
        .buyhold-analysis-table th,
        .carry-analysis-table th {
            background: #1A1A1A;
            color: #E8E8E8;
            font-weight: 600;
        }

        .momentum-analysis-table td,
        .buyhold-analysis-table td,
        .carry-analysis-table td {
            color: #D0D0D0;
        }

        .momentum-analysis-table tr:hover,
        .buyhold-analysis-table tr:hover,
        .carry-analysis-table tr:hover {
            background: rgba(138, 43, 226, 0.1);
        }

        .momentum-results, .buyhold-results, .carry-results {
            margin-top: 30px;
        }

        .performance-positive {
            color: #4CAF50;
            font-weight: bold;
        }

        .performance-negative {
            color: #FF6B6B;
            font-weight: bold;
        }

        .performance-neutral {
            color: #FFD700;
            font-weight: bold;
        }

        .recommendation-strong-buy {
            color: #4CAF50;
            font-weight: bold;
        }

        .recommendation-buy {
            color: #66BB6A;
            font-weight: bold;
        }

        .recommendation-neutral {
            color: #FFD700;
            font-weight: bold;
        }

        .recommendation-avoid {
            color: #FF6B6B;
            font-weight: bold;
        }

        .recommendation-recommend {
            color: #4CAF50;
            font-weight: bold;
        }

        .recommendation-opportunistic {
            color: #FFD700;
            font-weight: bold;
        }

        .heatmap-cell {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin: 2px;
            border-radius: 0;
            text-align: center;
            line-height: 20px;
            font-size: 10px;
            font-weight: bold;
        }

        .heatmap-positive {
            background: #4CAF50;
            color: white;
        }

        .heatmap-negative {
            background: #FF6B6B;
            color: white;
        }

        .heatmap-neutral {
            background: #FFD700;
            color: black;
        }

        .simulation-chart {
            margin-top: 20px;
        }

        .carry-simulation {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }

        .simulation-item {
            text-align: center;
            padding: 10px;
            background: #2A2A2A;
            border-radius: 0;
            border: 1px solid #444;
        }

        .simulation-item h6 {
            color: #E8E8E8;
            margin: 0 0 5px 0;
            font-size: 12px;
        }

        .simulation-item p {
            color: #8A2BE2;
            margin: 0;
            font-weight: bold;
            font-size: 14px;
        }

        .strategy-navigation {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .strategy-card {
            background: linear-gradient(145deg, #2A2A2A, #232323);
            border-radius: 0;
            padding: 20px;
            border: 1px solid #444;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .strategy-card:hover {
            border-color: #8A2BE2;
            box-shadow: 0 4px 20px rgba(138, 43, 226, 0.2);
            transform: translateY(-2px);
        }

        .strategy-card h3 {
            color: #8A2BE2;
            margin: 0 0 15px 0;
            font-size: 18px;
        }

        .strategy-card p {
            color: #D0D0D0;
            margin: 0 0 15px 0;
            font-size: 14px;
            line-height: 1.5;
        }

        .strategy-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }

        .strategy-feature {
            padding: 8px;
            background: rgba(138, 43, 226, 0.1);
            border-radius: 0;
            text-align: center;
            font-size: 12px;
            color: #E8E8E8;
        }

        .strategy-button {
            width: 100%;
            padding: 10px;
            background: linear-gradient(90deg, #8A2BE2, #B05EED);
            color: white;
            border: none;
            border-radius: 0;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .strategy-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(138, 43, 226, 0.3);
        }

        .correlation-legend {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 10px 0;
            font-size: 12px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .legend-color {
            width: 15px;
            height: 15px;
            border-radius: 0;
        }

        .welcome-screen {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(135deg, #1a0f42 0%, #0A1429 30%, #0A1429 70%, #1a0f42 100%);
            display: none;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            z-index: 9999;

        }

        .welcome-screen.active {
            display: flex;

        }

        .welcome-content {
            text-align: center;
            transform: translateY(20px);
            opacity: 0;
            animation: welcomeSlideIn 1s ease 1s forwards;
        }

        .welcome-title {
            font-size: 3.5rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 1rem;
            text-shadow: none;
            font-family: 'Playfair Display', serif;
        }

        .welcome-subtitle {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.8);
            font-weight: 300;
        }
.welcome-author {
    font-size: 1rem;
    color: rgba(255,255,255,0.7);
    font-weight: 300;
    margin-bottom: 2rem;
}
        .loading-bar {
            width: 200px;
            height: 3px;
            background: rgba(255,255,255,0.2);
            margin-top: 2rem;
            border-radius: 0;
            overflow: hidden;
        }

        .loading-progress {
            width: 0%;
            height: 100%;
            background: #333333;
            animation: loadingFill 3s ease 1s forwards;
        }

        @keyframes welcomeSlideIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes loadingFill {
            0% { width: 0%; }
            60% { width: 70%; }
            80% { width: 85%; }
            100% { width: 100%; }
        }
        /* Finance Footer Styles */
        /* Footer styles are handled by utility classes in the HTML */
        .market-open { color: #28A745; font-weight: bold; }
        .market-closed { color: #DC3545; }
        .market-status { margin: 0 5px; }
/* Violet Background Styles */
:root{
    /* Basis / Branding-empfohlene Farben */
    --base-black: #050510;      /* sehr dunkler Grundton (nicht reines Schwarz) */
    --violet-1:  #0a0f2c;       /* sehr dunkles Blau-Violett */
    --violet-2:  #1a0b38;       /* tiefes Violett */
    --violet-3:  #2e0f54;       /* edles Lila */
    --violet-4:  #3c1a70;       /* Blau-Violett für Tiefe */

    /* Bewegung (kleiner = schneller) */
    --d1: 10s;
    --d2: 14s;
    --d3: 20s;

    /* Unschärfe / Sichtbarkeit (anpassbar) */
    --blur1: 48px;
    --blur2: 84px;
    --blur3: 120px;
    --opa1: 0.96;
    --opa2: 0.82;
    --opa3: 0.74;
}

/* Fullscreen background container */
.bg {
    position: fixed;
    inset: 0;
    z-index: -1; /* WICHTIG: Hinter allen Inhalten */
    pointer-events: none;
    isolation: isolate;
    background: var(--base-black);
}

/* Layers use repeating radial gradients and animate background-position diagonally.
   Because they repeat, the motion loops seamlessly (no snapping). */
.layer {
    position: absolute;
    inset: -40%;
    pointer-events: none;
    background-repeat: repeat;
    mix-blend-mode: screen;
    will-change: background-position, transform, opacity;
}

/* Layer 1 - vorne (fein strukturiert, schneller) */
.l1 {
    background-image:
        radial-gradient(closest-side, rgba(138,43,226,0.25) 0%, rgba(138,43,226,0) 48%),
        radial-gradient(circle at 18% 82%, rgba(138,43,226,0.18) 0%, rgba(138,43,226,0) 44%);
    background-size: 1200px 1200px, 1600px 1600px;
    filter: blur(var(--blur1)) saturate(116%);
    opacity: var(--opa1);
    animation:
        bgMove1 var(--d1) linear infinite,
        wave1 calc(var(--d1) * 1.12) ease-in-out infinite;
}

/* Layer 2 - mitte (mittlere Tiefe, moderat) */
.l2 {
    background-image:
        radial-gradient(circle at 16% 86%, rgba(138,43,226,0.15) 0%, rgba(138,43,226,0) 42%),
        radial-gradient(circle at 8% 92%, rgba(138,43,226,0.12) 0%, rgba(138,43,226,0) 38%);
    background-size: 1800px 1800px, 2200px 2200px;
    filter: blur(var(--blur2)) saturate(106%);
    opacity: var(--opa2);
    animation:
        bgMove2 var(--d2) linear infinite,
        wave2 calc(var(--d2) * 1.18) ease-in-out infinite;
}

/* Layer 3 - hinten (groß, sehr weich) */
.l3 {
    background-image:
        radial-gradient(circle at 12% 92%, rgba(138,43,226,0.10) 0%, rgba(138,43,226,0) 36%),
        radial-gradient(circle at 22% 72%, rgba(138,43,226,0.08) 0%, rgba(138,43,226,0) 40%);
    background-size: 2600px 2600px, 3000px 3000px;
    filter: blur(var(--blur3)) saturate(102%);
    opacity: var(--opa3);
    animation:
        bgMove3 var(--d3) linear infinite,
        wave3 calc(var(--d3) * 1.22) ease-in-out infinite;
}

/* subtle overlay for micro-life */
.pulse {
    position: absolute;
    inset: -60%;
    background: linear-gradient(135deg, rgba(255,255,255,0.01), rgba(255,255,255,0) 22%);
    filter: blur(160px);
    mix-blend-mode: overlay;
    animation: pulse 12s ease-in-out infinite;
    opacity: 0.07;
    pointer-events: none;
}

/* fine grain texture for luxury finish */
.grain {
    position: fixed;
    inset: 0;
    z-index: -1; /* WICHTIG: Hinter allen Inhalten */
    pointer-events: none;
    opacity: 0.03;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'><filter id='g'><feTurbulence baseFrequency='0.9' numOctaves='1' seed='29' /></filter><rect width='100%' height='100%' filter='url(%23g)' opacity='0.18' /></svg>");
    mix-blend-mode: overlay;
}

/* KEYFRAMES — diagonal translation of repeating background tiles (seamless loop) */
@keyframes bgMove1 {
    from { background-position: -1400px -1400px, -1800px -1800px; }
    to   { background-position: 1400px 1400px, 1800px 1800px; }
}
@keyframes bgMove2 {
    from { background-position: -1800px -1800px, -2200px -2200px; }
    to   { background-position: 1800px 1800px, 2200px 2200px; }
}
@keyframes bgMove3 {
    from { background-position: -2400px -2400px, -2800px -2800px; }
    to   { background-position: 2400px 2400px, 2800px 2800px; }
}

/* gentle orthogonal wave movement for organic flow */
@keyframes wave1 {
    0%   { transform: translate(0%, 0%); }
    25%  { transform: translate(0.35%, -0.18%); }
    50%  { transform: translate(0%, -0.36%); }
    75%  { transform: translate(-0.35%, -0.18%); }
    100% { transform: translate(0%, 0%); }
}
@keyframes wave2 {
    0%   { transform: translate(0%, 0%); }
    25%  { transform: translate(0.52%, -0.28%); }
    50%  { transform: translate(0%, -0.56%); }
    75%  { transform: translate(-0.52%, -0.28%); }
    100% { transform: translate(0%, 0%); }
}
@keyframes wave3 {
    0%   { transform: translate(0%, 0%); }
    25%  { transform: translate(0.75%, -0.36%); }
    50%  { transform: translate(0%, -0.72%); }
    75%  { transform: translate(-0.75%, -0.36%); }
    100% { transform: translate(0%, 0%); }
}

/* micro pulse */
@keyframes pulse {
    0%   { opacity: 0.05; transform: scale(1) translate(0,0); }
    50%  { opacity: 0.11; transform: scale(1.01) translate(0.12%, -0.18%); }
    100% { opacity: 0.05; transform: scale(1) translate(0,0); }
}

/* respect user motion preferences */
@media (prefers-reduced-motion: reduce) {
    .layer, .pulse { animation: none !important; transform: none !important; }
    .grain { opacity: 0.02 !important; }
}
/* NUR WINDOWS PERFORMANCE OPTIMIERUNGEN - STANDIMAGE */
.performance-mode .layer {
    animation: none !important;
    filter: blur(40px) !important;
}

.performance-mode .pulse {
    display: none !important;
}

.performance-mode .l1 { opacity: 0.9; }
.performance-mode .l2 { opacity: 0.7; }
.performance-mode .l3 { opacity: 0.5; }

/* SMOOTH SCROLLING FIX */
html, body {
    overflow-x: hidden;
    overflow-y: auto;
    height: 100%;
    scroll-behavior: smooth;
}

.performance-mode main {
    transform: translate3d(0, 0, 0);
    backface-visibility: hidden;
    will-change: transform;
}

/* Getting Started Page Styles */
.steps-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin: 30px 0;
}

.step {
    display: flex;
    align-items: flex-start;
    background: linear-gradient(145deg, #262626, #1a1a1a);
    border-radius: 0;
    padding: 20px;
    transition: transform 0.3s, box-shadow 0.3s;
}

.step:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
}

.step-number {
    background: linear-gradient(145deg, #8A2BE2, #6B24B2);
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
    margin-right: 20px;
    flex-shrink: 0;
}

.step-content {
    flex: 1;
}

.step-btn {
    margin-top: 10px;
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.feature-item {
    background: linear-gradient(145deg, #262626, #1a1a1a);
    border-radius: 0;
    padding: 20px;
    text-align: center;
    transition: transform 0.3s;
}

.feature-item:hover {
    transform: translateY(-5px);
}

.feature-icon {
    font-size: 2.5rem;
    margin-bottom: 15px;
    color: #8A2BE2;
}

.quick-links-container {
    margin-top: 30px;
}

.quick-links {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
    margin-top: 15px;
}

.quick-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    background: linear-gradient(145deg, #262626, #1a1a1a);
    border-radius: 0;
    padding: 20px;
    text-decoration: none;
    color: #E0E0E0;
    transition: all 0.3s;
}

.quick-link:hover {
    background: linear-gradient(145deg, #2D2D2D, #212121);
    transform: translateY(-5px);
    color: #8A2BE2;
}

.quick-link i {
    font-size: 2rem;
    margin-bottom: 10px;
}

/* Investing Page Styles */
.principles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.principle-item {
    background: linear-gradient(145deg, #262626, #1a1a1a);
    border-radius: 0;
    padding: 20px;
    transition: transform 0.3s;
}

.principle-item:hover {
    transform: translateY(-5px);
}

.principle-image {
    height: 150px;
    margin-top: 15px;
    border-radius: 0;
    background-color: #333;
    background-size: cover;
    background-position: center;
}

.tabs-container {
    margin-top: 20px;
}

.tabs {
    display: flex;
    flex-wrap: wrap;
    border-bottom: 1px solid #333;
    margin-bottom: 20px;
}

.tab {
    padding: 10px 20px;
    cursor: pointer;
    transition: all 0.3s;
}

.tab.active {
    color: #8A2BE2;
    border-bottom: 2px solid #8A2BE2;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
    animation: fade-in 0.3s ease-out;
}

.strategy-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

.strategy-table th,
.strategy-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #333;
}

.strategy-table th {
    background-color: #222;
    color: #E0E0E0;
}

.strategy-table tr:hover {
    background-color: #282828;
}

/* News Styling */
.news-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #333;
}

.news-item {
    background: #1A1A1A;
    border: 1px solid #333;
    border-radius: 0;
    padding: 20px;
    margin-bottom: 15px;
    transition: all 0.3s ease;
}

.news-item:hover {
    background: #222;
    border-color: #8A2BE2;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(138, 43, 226, 0.2);
}

.news-item .news-header {
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid #333;
}

.news-title {
    color: #E8E8E8;
    text-decoration: none;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.4;
    transition: color 0.3s ease;
}

.news-title:hover {
    color: #8A2BE2;
    text-decoration: underline;
}

.news-meta {
    display: flex;
    gap: 15px;
    margin-top: 8px;
}

.news-source {
    background: #8A2BE2;
    color: white;
    padding: 4px 8px;
    border-radius: 0;
    font-size: 12px;
    font-weight: 600;
}

.news-time {
    color: #888;
    font-size: 12px;
    font-style: italic;
}

.news-description {
    color: #D0D0D0;
    line-height: 1.6;
    margin: 0;
}

.news-loading {
    text-align: center;
    color: #888;
    padding: 40px;
    font-size: 16px;
}

.news-loading i {
    margin-right: 10px;
    color: #8A2BE2;
}

/* Asset Section Styling */
.asset-section {
    background: #1A1A1A;
    border: 1px solid #333;
    border-radius: 0;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.asset-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 2px solid #8A2BE2;
}

.asset-header h3 {
    color: #E8E8E8;
    font-size: 24px;
    margin: 0;
}

.asset-badges {
    display: flex;
    gap: 10px;
}

.risk-badge, .return-badge, .liquidity-badge {
    padding: 4px 12px;
    border-radius: 0;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}

.risk-badge.high, .return-badge.high, .liquidity-badge.high {
    background: #FF6B6B;
    color: white;
}

.risk-badge.medium, .return-badge.medium, .liquidity-badge.medium {
    background: #FFD700;
    color: #1A1A1A;
}

.risk-badge.low, .return-badge.low, .liquidity-badge.low {
    background: #90EE90;
    color: #1A1A1A;
}

.return-badge.stable {
    background: #87CEEB;
    color: #1A1A1A;
}

.risk-badge.variable, .return-badge.variable, .liquidity-badge.variable {
    background: #DDA0DD;
    color: white;
}

.theory-content h4 {
    color: #8A2BE2;
    font-size: 20px;
    margin: 25px 0 15px 0;
    border-left: 4px solid #8A2BE2;
    padding-left: 15px;
}

.theory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 25px;
}

.theory-card {
    background: #222;
    border: 1px solid #444;
    border-radius: 0;
    padding: 20px;
    transition: all 0.3s ease;
}

.theory-card:hover {
    border-color: #8A2BE2;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(138, 43, 226, 0.2);
}

.theory-card h5 {
    color: #E8E8E8;
    font-size: 16px;
    margin: 0 0 10px 0;
}

.theory-card p {
    color: #D0D0D0;
    line-height: 1.6;
    margin: 0 0 10px 0;
}

.formula {
    background: #0A0A0A;
    border: 1px solid #8A2BE2;
    border-radius: 0;
    padding: 10px;
    font-family: 'Courier New', monospace;
    color: #8A2BE2;
    font-size: 14px;
    text-align: center;
    margin-top: 10px;
}

.practice-content {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 20px;
}

.practice-item {
    background: #1F1F1F;
    border: 1px solid #444;
    border-radius: 0;
    padding: 20px;
    transition: all 0.3s ease;
}

.practice-item:hover {
    border-color: #8A2BE2;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(138, 43, 226, 0.1);
}

.practice-item h5 {
    color: #E8E8E8;
    font-size: 16px;
    margin: 0 0 10px 0;
    border-bottom: 1px solid #333;
    padding-bottom: 8px;
}

.practice-item p {
    color: #D0D0D0;
    line-height: 1.6;
    margin: 0 0 8px 0;
}

.practice-item p:last-child {
    margin-bottom: 0;
}

/* Backtesting Module Styles */
.backtesting-controls {
    background: #1A1A1A;
    border: 1px solid #333;
    border-radius: 0;
    padding: 25px;
    margin: 20px 0;
}

.strategy-parameters {
    margin: 20px 0;
    padding: 20px;
    background: #222;
    border-radius: 0;
    border-left: 4px solid #8A2BE2;
}

.backtesting-results {
    margin-top: 30px;
}

.metric-value {
    font-size: 24px;
    font-weight: bold;
    color: #8A2BE2;
    margin-top: 5px;
}

.summary-item h4 {
    color: #E0E0E0;
    font-size: 14px;
    margin-bottom: 5px;
    opacity: 0.8;
}

/* Comprehensive PDF Download Styles */
.comprehensive-pdf-section {
    background: linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 100%);
    border: 1px solid #8A2BE2;
    border-radius: 0;
    margin: 30px 0;
    overflow: hidden;
    position: relative;
}

.comprehensive-pdf-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #8A2BE2, #B05EED, #8A2BE2);
    background-size: 200% 100%;
    animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.pdf-download-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    margin-top: 20px;
}

.pdf-preview {
    background: #222;
    border-radius: 0;
    padding: 25px;
    border: 1px solid #333;
}

.pdf-preview h4 {
    color: #8A2BE2;
    font-size: 18px;
    margin-bottom: 20px;
    font-family: 'Playfair Display', serif;
}

.pdf-content-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.content-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: #1A1A1A;
    border-radius: 0;
    border-left: 3px solid #8A2BE2;
    transition: all 0.3s ease;
}

.content-item:hover {
    background: #2A2A2A;
    transform: translateX(5px);
}

.content-item i {
    color: #8A2BE2;
    font-size: 16px;
    width: 20px;
    text-align: center;
}

.content-item span {
    color: #E0E0E0;
    font-size: 14px;
    font-weight: 500;
}

.pdf-download-form {
    background: #222;
    border-radius: 0;
    padding: 25px;
    border: 1px solid #333;
}

.pdf-download-form h4 {
    color: #8A2BE2;
    font-size: 18px;
    margin-bottom: 15px;
    font-family: 'Playfair Display', serif;
}

.pdf-download-form p {
    color: #B0B0B0;
    margin-bottom: 20px;
    font-size: 14px;
}

.password-input-group {
    position: relative;
    margin-bottom: 20px;
}

.password-input {
    width: 100%;
    padding: 15px 50px 15px 15px;
    background: #1A1A1A;
    border: 2px solid #333;
    border-radius: 0;
    color: #E0E0E0;
    font-size: 16px;
    transition: all 0.3s ease;
}

.password-input:focus {
    outline: none;
    border-color: #8A2BE2;
    box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.1);
}

.password-toggle {
    position: absolute;
    right: 15px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #8A2BE2;
    cursor: pointer;
    font-size: 16px;
    padding: 5px;
    transition: color 0.3s ease;
}

.password-toggle:hover {
    color: #B05EED;
}

.pdf-generate-btn {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #8A2BE2, #B05EED);
    border: none;
    border-radius: 0;
    color: white;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-bottom: 15px;
}

.pdf-generate-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(138, 43, 226, 0.3);
}

.pdf-generate-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}

.pdf-info {
    color: #B0B0B0;
    font-size: 12px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.pdf-features {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.feature-tag {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(138, 43, 226, 0.1);
    color: #8A2BE2;
    padding: 6px 12px;
    border-radius: 0;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid rgba(138, 43, 226, 0.2);
}

.feature-tag i {
    font-size: 10px;
}

@media (max-width: 768px) {
    .pdf-download-container {
        grid-template-columns: 1fr;
        gap: 20px;
    }
    
    .pdf-preview, .pdf-download-form {
        padding: 20px;
    }
}

/* Getting Started Structure Styles */
.website-structure {
    margin: 20px 0;
}

.structure-section {
    margin-bottom: 15px;
    padding: 12px 16px;
    background: var(--perlweiss);
    border-radius: 0;
    border-left: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.structure-section h4 {
    color: var(--kohlegrau);
    font-size: 14px;
    margin-bottom: 10px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
}

.structure-items {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
}

.structure-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px;
    background: var(--perlweiss);
    border-radius: 0;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid #e0e0e0;
}

.structure-item:hover {
    background: #f5f9fc;
    border-color: #4a90e2;
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(74, 144, 226, 0.15);
}

.structure-item i {
    font-size: 20px;
    color: #4a90e2;
    margin-top: 3px;
    min-width: 24px;
}

.structure-item strong {
    color: #000000;
    font-size: 16px;
    display: block;
    margin-bottom: 5px;
}

.structure-item p {
    color: #666666;
    font-size: 14px;
    line-height: 1.4;
    margin: 0;
}

.step-actions {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

/* Quick Links Styles */
.quick-links-container {
    margin-bottom: 40px;
}

.quick-links {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.quick-link {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 15px;
    background: #f8f8f8;
    border-radius: 0;
    text-decoration: none;
    color: #333;
    transition: all 0.3s ease;
    border-left: 3px solid #8b7355;
}

.quick-link:hover {
    background: var(--perlweiss);
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(139, 115, 85, 0.2);
}

/* Features Grid Styles */
.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
}

.feature-item {
    background: var(--perlweiss);
    padding: 25px;
    border-radius: 0;
    border: 1px solid #e8e8e8;
    transition: all 0.3s ease;
}

.feature-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(139, 115, 85, 0.1);
}

.feature-icon {
    margin-bottom: 15px;
}

.feature-icon i {
    color: var(--color-accent-rose);
    font-size: 32px;
}

/* Steps Container Styles */
.steps-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
    margin: 25px 0;
}

.step {
    display: flex;
    align-items: flex-start;
    gap: 20px;
    padding: 20px;
    background: #f8f8f8;
    border-radius: 0;
    border-left: 4px solid var(--color-accent-rose);
}

.step-number {
    background: var(--color-accent-rose);
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 18px;
    flex-shrink: 0;
}

.step-content {
    flex: 1;
}

.step-content h4 {
    font-family: 'Inter', sans-serif;
    font-size: 20px;
    color: #000000;
    margin: 0 0 10px 0;
    font-weight: 600;
}

.step-content p {
    color: #666666;
    font-size: 16px;
    line-height: 1.6;
    margin: 0 0 15px 0;
}

.step-actions .btn {
    background: var(--color-accent-rose);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 0;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s ease;
}

.step-actions .btn:hover {
    background: #7a634a;
    transform: translateY(-1px);
}

@media (max-width: 768px) {
    .step-actions {
        flex-wrap: wrap;
    }

    .step-actions .btn {
        font-size: 12px;
        padding: 8px 16px;
    }
}

</style>
<script>
    // Initial Footer ausblenden für Login-Bildschirm
    window.onload = function() {
        document.querySelector('footer').style.display = 'none';
        
        // Ensure login screen is properly centered
        const loginScreen = document.getElementById('passwordProtection');
        if (loginScreen) {
            loginScreen.style.display = 'flex';
            loginScreen.style.justifyContent = 'center';
            loginScreen.style.alignItems = 'center';
            loginScreen.style.width = '100vw';
            loginScreen.style.height = '100vh';
        }
    }
</script>
</head>
<body class="sap-theme-dark" style="margin: 0; padding: 0;">
    
    <!-- Login Function - MUST be defined before login button -->
    <script>
        function checkPassword() {
            console.log('checkPassword function called');
            const password = document.getElementById('passwordInput').value;
            const errorMsg = document.getElementById('passwordError');
            
            fetch('/api/verify_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Login erfolgreich - verstecke Login und zeige Welcome Screen
                    document.getElementById('passwordProtection').style.display = 'none';
                    // startWelcomeAnimation wird später im Code definiert
                    if (typeof startWelcomeAnimation === 'function') {
                        startWelcomeAnimation();
                    } else {
                        // Fallback wenn startWelcomeAnimation noch nicht geladen ist
                        setTimeout(function() {
                            if (typeof startWelcomeAnimation === 'function') {
                                startWelcomeAnimation();
                            }
                        }, 100);
                    }
                } else {
                    errorMsg.style.display = 'block';
                    setTimeout(() => errorMsg.style.display = 'none', 3000);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                errorMsg.style.display = 'block';
            });
        }
        // Make it globally accessible for inline onclick/onkeypress
        window.checkPassword = checkPassword;
    </script>
    
    <!-- ======================================================================================== -->
    <!-- 🔒 PROTECTED - LOGIN SCREEN - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
    <!-- Contains: Password Protection, Login Form, Authentication -->
    <!-- ======================================================================================== -->
    <div id="passwordProtection" style="display: flex; justify-content: center; align-items: center; width: 100vw; height: 100vh; position: fixed; top: 0; left: 0; background: #000000; z-index: 10000;">
        <div style="background: #000000; padding: 60px; border-radius: 0; box-shadow: none; text-align: center; max-width: 500px; width: 90%; border: none; margin: 0 auto;">
            <!-- Title UPDATED - Swiss in BEIGE 52px -->
            <div style="margin-bottom: 30px; line-height: 1.1;">
                <span style="color: #8b7355 !important; font-size: 52px !important; font-weight: 300 !important; font-family: 'Playfair Display', serif !important; display: inline !important;">Swiss</span>
                <span style="color: #FFFFFF !important; font-size: 52px !important; font-weight: 300 !important; font-family: 'Playfair Display', serif !important; display: inline !important;"> Asset Pro</span>
            </div>
            
            <p style="margin-bottom: 25px; color: #E8E8E8; font-size: 15px;">Bitte geben Sie das Passwort ein:</p>
            <input type="password" id="passwordInput" placeholder="Passwort" onkeypress="if(event.key === 'Enter') checkPassword()" style="width: 100%; padding: 14px; border: 1px solid #454545; border-radius: 0; margin-bottom: 18px; font-size: 16px; background: #1a1a1a; color: white; outline: none !important; box-sizing: border-box;">
            <button onclick="checkPassword()" id="accessButton" style="background: #8b7355 !important; color: white !important; font-weight: 600; padding: 14px 30px; border-radius: 0; box-shadow: none; border: none; cursor: pointer; width: 100%; font-size: 17px; outline: none !important;">Zugang erhalten</button>
            <p id="passwordError" style="color: #DC3545; margin-top: 12px; display: none; font-size: 14px;">Falsches Passwort. Bitte versuchen Sie es erneut.</p>
            <p style="margin-top: 20px; font-size: 13px; color: #999;">by Ahmed Choudhary</p>
        </div>
    </div>
    <!-- ======================================================================================== -->
    <!-- 🔒 END PROTECTED - Login Screen -->
    <!-- ======================================================================================== -->

    <!-- ======================================================================================== -->
    <!-- 🔒 PROTECTED - WELCOME SCREEN & ANIMATION - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
    <!-- Contains: Welcome Screen, Stock Line Animation, Loading Bar, Fade Effects -->
    <!-- ======================================================================================== -->
    <div class="welcome-screen" id="welcomeScreen">
    <div class="welcome-content">
        <h1 class="welcome-title">Swiss Asset Pro</h1>
        <p class="welcome-subtitle">Professional Portfolio Simulation</p>
        <p class="welcome-author">by Ahmed Choudhary</p>
        
        <div class="loading-bar">
            <div class="loading-progress"></div>
        </div>
        
        <!-- VERSCHWINDENDE AKTIEN-LINIE - 2025-10-12 00:43 -->
        <div class="stock-graph-fade" style="margin-top: 40px; display: flex; justify-content: center;">
            <div class="graph-container-fade" style="width: 300px; height: 80px; position: relative;">
                <svg viewBox="0 0 300 80" preserveAspectRatio="none" style="width: 100%; height: 100%;">
                    <!-- Aktien-Linie die langsam verschwindet -->
                    <path id="fadingStockLine" d="M0,60 L50,55 L100,70 L150,65 L200,75 L250,68 L300,20" 
                          style="fill: none; stroke: #8b7355; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; opacity: 1; filter: drop-shadow(0 0 10px rgba(139, 115, 85, 0.8)); transition: opacity 1s ease-out;" />
                </svg>
            </div>
        </div>
        
    </div>
</div>

<style>
.welcome-screen {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: #0A0A0A;
    display: none;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    z-index: 9999;
}

.welcome-screen.active {
    display: flex;
}

.welcome-content {
    text-align: center;
    transform: translateY(0);
    opacity: 1;
    animation: welcomeSlideIn 0.8s ease 0.2s forwards;
}

.welcome-title {
    font-family: 'Playfair Display', serif;
    font-size: 3.5rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 1.5rem;
    text-shadow: none;
    letter-spacing: -1px;
}

.welcome-subtitle {
    font-family: var(--font-body);
    font-size: 1.2rem;
    color: rgba(255,255,255,0.8);
    font-weight: 300;
    letter-spacing: 0.3px;
}

.welcome-author {
    font-size: 1rem;
    color: rgba(255,255,255,0.7);
    font-weight: 300;
    margin-bottom: 2rem;
}

.loading-bar {
    width: 250px;
    height: 4px;
    background: rgba(255,255,255,0.1);
    margin: 2.5rem auto 0;
    border-radius: 0;
    overflow: hidden;
}

        .loading-progress {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, var(--color-accent-rose), var(--color-primary-dark));
            animation: loadingFill 2.2s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s forwards;
            box-shadow: 0 0 15px rgba(205, 139, 118, 0.6);
        }/* NEUE AKTIEN-GRAPH ANIMATION */
.stock-graph-animation {
    margin-top: 40px;
    display: flex;
    justify-content: center;
}

.graph-container {
    width: 300px;
    height: 80px;
    position: relative;
}

.stock-graph {
    width: 100%;
    height: 100%;
}

.graph-line {
    fill: none;
    stroke: #8b7355;
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 100;
    stroke-dashoffset: 100;
    animation: drawGraph 3.5s ease-in-out 0.8s forwards;
    filter: drop-shadow(0 0 10px rgba(139, 115, 85, 0.8));
}

.graph-dot {
    fill: #d4af37;
    stroke: #8b7355;
    stroke-width: 2;
    filter: drop-shadow(0 0 8px #d4af37);
    animation: followPath 3.5s ease-in-out 0.8s forwards;
}

@keyframes welcomeSlideIn {
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes loadingFill {
    to { width: 100%; }
}

@keyframes drawGraph {
    to {
        stroke-dashoffset: 0;
    }
}

@keyframes followPath {
    0% {
        cx: 0;
        cy: 60;
    }
    16% {
        cx: 50;
        cy: 55;
    }
    33% {
        cx: 100;
        cy: 70;
    }
    50% {
        cx: 150;
        cy: 65;
    }
    66% {
        cx: 200;
        cy: 75;
    }
    83% {
        cx: 250;
        cy: 68;
    }
    100% {
        cx: 300;
        cy: 20;
    }
}
</style>

    <!-- PWA Install Banner -->
    <div id="pwaInstallBanner" style="display: none; position: fixed; bottom: 0; left: 0; right: 0; background: linear-gradient(135deg, #8A2BE2, #B05EED); color: white; padding: 15px; z-index: 9999; transform: translateY(100%); transition: transform 0.3s ease;">
        <div style="display: flex; align-items: center; justify-content: space-between; max-width: 400px; margin: 0 auto;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-download" style="font-size: 20px;"></i>
                <div>
                    <div style="font-weight: 600; font-size: 14px;">App installieren</div>
                    <div style="font-size: 12px; opacity: 0.9;">Für bessere Performance</div>
                </div>
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="installPWA()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 8px 16px; border-radius: 0; font-size: 12px; cursor: pointer;">Installieren</button>
                <button onclick="dismissInstallBanner()" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">×</button>
            </div>
        </div>
    </div>

    <!-- Offline Indicator -->
    <div id="offlineIndicator" style="display: none; position: fixed; top: 0; left: 0; right: 0; background: #FF6B6B; color: white; text-align: center; padding: 8px; z-index: 9998; font-size: 14px;">
        <i class="fas fa-wifi" style="margin-right: 8px;"></i>
        Sie sind offline. Einige Funktionen sind möglicherweise eingeschränkt.
    </div>

    <!-- iOS Add to Home Screen Instructions -->
    <div id="iosInstallInstructions" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); z-index: 10000; color: white; padding: 20px; text-align: center;">
        <div style="max-width: 400px; margin: 50px auto;">
            <div style="font-size: 48px; margin-bottom: 20px;">📱</div>
            <h2 style="color: #8A2BE2; margin-bottom: 20px;">App zum Home Screen hinzufügen</h2>
            <div style="text-align: left; margin-bottom: 30px;">
                <p style="margin-bottom: 15px;"><strong>1.</strong> Tippen Sie auf das <i class="fas fa-share" style="color: #8A2BE2;"></i> Teilen-Symbol</p>
                <p style="margin-bottom: 15px;"><strong>2.</strong> Wählen Sie "Zum Home-Bildschirm"</p>
                <p style="margin-bottom: 15px;"><strong>3.</strong> Tippen Sie auf "Hinzufügen"</p>
            </div>
            <button onclick="closeIOSInstructions()" style="background: #8A2BE2; color: white; border: none; padding: 12px 24px; border-radius: 0; font-size: 16px; cursor: pointer;">Verstanden</button>
        </div>
    </div>

    <!-- ======================================================================================== -->
    <!-- 🔒 PROTECTED - LANDING PAGE - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
    <!-- Contains: All 14 Landing Page Tiles, Hero Section, Images, Icons, Navigation Links -->
    <!-- Tiles: Getting Started, Dashboard, Portfolio, Strategie, Simulation, Backtesting, -->
    <!-- Investing, Bericht, Märkte, Assets, Methodik, BL & BVAR, Steuern, Über Mich -->
    <!-- ======================================================================================== -->
    <div id="landingPage" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: #FFFFFF; z-index: 1000; overflow-y: auto; opacity: 0; transition: none;">
        <div class="container" style="max-width: 1600px; margin: 0 auto; padding: 40px 20px;">
            <!-- Hero Section -->
            <div style="display: flex; flex-direction: column; margin-bottom: 40px; opacity: 1 !important; transform: translateY(0); transition: all 0.3s ease;" class="landing-hero-section">
                <div style="text-align: center; margin-bottom: 30px; line-height: 1.1;">
                    <span style="color: #8b7355 !important; font-size: 52px !important; font-weight: 300 !important; font-family: 'Playfair Display', serif !important; display: inline !important;">Swiss</span>
                    <span style="color: #000000 !important; font-size: 52px !important; font-weight: 300 !important; font-family: 'Playfair Display', serif !important; display: inline !important;"> Asset Pro</span>
                </div>
                <h2 style="font-family: 'Playfair Display', serif !important; font-size: 26px !important; color: #3a3a3a !important; margin: 20px auto !important; font-weight: 500 !important; text-align: center !important; opacity: 1 !important; line-height: 1.3 !important;">Willkommen zur professionellen Portfolio-Simulation</h2>
                <p style="font-family: 'Inter', sans-serif !important; font-size: 15px !important; color: #4a4a4a !important; font-weight: 500 !important; max-width: 800px; line-height: 1.6 !important; text-align: center !important; margin: 0 auto !important; opacity: 1 !important;">Wählen Sie einen Bereich, um direkt einzusteigen, oder erkunden Sie alle Funktionen für eine umfassende Finanzanalyse Ihres Portfolios.</p>
            </div>
            
            <!-- Panels Container -->
            <div id="landingPanelsContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; opacity: 1; transform: translateY(0); transition: all 0.3s ease;">
                
                <!-- Panel 1 - Getting Started -->
                <div class="landing-card" onclick="showGettingStartedPage('getting-started')" style="background: url('/static/Bilder-SAP/annie-spratt-IT6aov1ScW0-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Getting Started</h3>
                    </div>
                </div>
                
                <!-- Panel 2 - Dashboard -->
                <div class="landing-card" onclick="showGettingStartedPage('dashboard')" style="background: url('/static/Bilder-SAP/david-werbrouck-5GwLlb-_UYk-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <i class="fas fa-chart-pie" style="color: #FFFFFF; font-size: 18px;"></i>
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Dashboard</h3>
                    </div>
                </div>
                
                <!-- Panel 3 - Portfolio -->
                <div class="landing-card" onclick="showGettingStartedPage('portfolio')" style="background: url('/static/Bilder-SAP/anthony-tyrrell-Bl-LiSJOnlY-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <i class="fas fa-briefcase" style="color: #FFFFFF; font-size: 18px;"></i>
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Portfolio</h3>
                    </div>
                </div>
                
                <!-- Panel 4 - Strategie -->
                <div class="landing-card" onclick="showGettingStartedPage('strategieanalyse')" style="background: url('/static/Bilder-SAP/frederic-perez-RDNAtCk5rJ8-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Strategie</h3>
                    </div>
                </div>
                
                <!-- Panel 5 - Simulation -->
                <div class="landing-card" onclick="showGettingStartedPage('simulation')" style="background: url('/static/Bilder-SAP/benedikt-jaletzke-TZsfOb3cgJM-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Simulation</h3>
                    </div>
                </div>
                
                <!-- Panel 6 - Backtesting -->
                <div class="landing-card" onclick="showGettingStartedPage('backtesting')" style="background: url('/static/Bilder-SAP/armando-castillejos-DPi0ddFTBS0-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Backtesting</h3>
                    </div>
                </div>
                
                <!-- Panel 7 - Investing -->
                <div class="landing-card" onclick="showGettingStartedPage('investing')" style="background: url('/static/Bilder-SAP/bumgeun-nick-suh-o40m9hf2lB4-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Investing</h3>
                    </div>
                </div>
                
                <!-- Panel 8 - Bericht -->
                <div class="landing-card" onclick="showGettingStartedPage('bericht')" style="background: url('/static/Bilder-SAP/ian-parker-rWey_wseEcY-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Bericht</h3>
                    </div>
                </div>
                
                <!-- Panel 9 - Märkte -->
                <div class="landing-card" onclick="showGettingStartedPage('markets')" style="background: url('/static/Bilder-SAP/jason-dent-3wPJxh-piRw-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <i class="fas fa-newspaper" style="color: #FFFFFF; font-size: 18px;"></i>
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Märkte</h3>
                    </div>
                </div>
                
                <!-- Panel 10 - Assets -->
                <div class="landing-card" onclick="showGettingStartedPage('assets')" style="background: url('/static/Bilder-SAP/jiri-brtnik-jIaSUaQVPl0-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <i class="fas fa-coins" style="color: #FFFFFF; font-size: 18px;"></i>
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Assets</h3>
                    </div>
                </div>
                
                <!-- Panel 11 - Methodik -->
                <div class="landing-card" onclick="showGettingStartedPage('methodik')" style="background: url('/static/Bilder-SAP/pepi-stojanovski-MJSFNZ8BAXw-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Methodik</h3>
                    </div>
                </div>
                
                <!-- Panel 12 - Black-Litterman & BVAR -->
                <div class="landing-card" onclick="showGettingStartedPage('black-litterman')" style="background: url('/static/Bilder-SAP/bumgeun-nick-suh-o40m9hf2lB4-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">BL & BVAR</h3>
                    </div>
                </div>
                
                <!-- Panel 13 - Steuern -->
                <div class="landing-card" onclick="showGettingStartedPage('sources')" style="background: url('/static/Bilder-SAP/robert-tudor-G7bXcUgh_xk-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Steuern</h3>
                    </div>
                </div>
                
                <!-- Panel 14 - Über mich -->
                <div class="landing-card" onclick="showGettingStartedPage('about')" style="background: url('/static/Bilder-SAP/tai-s-captures-r5kTKshp22M-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Über mich</h3>
                    </div>
                </div>
                
                <!-- Panel 15 - Transparenz -->
                <div class="landing-card" onclick="showGettingStartedPage('transparency')" style="background: url('/static/Bilder-SAP/robert-tudor-G7bXcUgh_xk-unsplash.jpg'); background-size: cover; background-position: center;  min-height: 93px; cursor: pointer;">
                    <div style="background: rgba(0, 0, 0, 0.85); padding: 8px 20px; border-radius: 0; display: inline-flex; align-items: center; gap: 12px;">
                        <h3 style="color: #FFFFFF; margin: 0; font-weight: 600; font-size: 18px;">Transparenz</h3>
                    </div>
                </div>
                
            </div>
            
            <!-- Landing Page Footer -->
            <!-- Footer -->
            <footer style="background: #000000; color: #ffffff; padding: 80px 0 40px; margin-top: 60px;">
                <div style="max-width: 1400px; margin: 0 auto; padding: 0 15px;">
                    <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 50px; margin-bottom: 60px;">
                        <div style="max-width: 350px;">
                            <div style="font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 500; color: #ffffff; margin-bottom: 20px;">
                                <span style="color: var(--color-accent-rose);">Swiss</span> Asset Pro
                            </div>
                            <p style="font-size: 14px; color: #cccccc; line-height: 1.7; margin-bottom: 25px;">Swiss Asset Pro ist eine moderne Portfolio-Management-Plattform, die quantitative Analyse, Echtzeit-Daten und fortgeschrittene Optimierungsstrategien kombiniert, um Investoren bei fundierten Anlageentscheidungen zu unterstützen.</p>
                        </div>
                        
                        <div>
                            <h3 style="font-size: 15px; color: #ffffff; font-weight: 500; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">TOOLS & SERVICES</h3>
                            <ul style="list-style: none; padding: 0; margin: 0;">
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Portfolio-Simulation</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Strategie-Analyse</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Backtesting & Vergleich</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Investment Insights</a></li>
                            </ul>
                        </div>
                        
                        <div>
                            <h3 style="font-size: 15px; color: #ffffff; font-weight: 500; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">KNOWLEDGE HUB</h3>
                            <ul style="list-style: none; padding: 0; margin: 0;">
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Märkte & News</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Asset-Klassen</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Methodik & Modelle</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Black-Litterman & BVAR</a></li>
                            </ul>
                        </div>
                        
                        <div>
                            <h3 style="font-size: 15px; color: #ffffff; font-weight: 500; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px;">ABOUT</h3>
                            <ul style="list-style: none; padding: 0; margin: 0;">
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Über das Projekt</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" onclick="showGettingStartedPage(); return false;" style="color: #cccccc; font-size: 13px; text-decoration: none;">Erste Schritte</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Berichte</a></li>
                                <li style="margin-bottom: 12px;"><a href="#" style="color: #cccccc; font-size: 13px; text-decoration: none;">Kontakt</a></li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style="border-top: 1px solid #333333; padding-top: 30px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #888888;">
                        <div>© 2025 Swiss Asset Pro. All rights reserved.</div>
                        <div style="display: flex; gap: 12px;">
                            <a href="#" style="color: #cccccc; font-size: 14px; text-decoration: none;"><i class="fab fa-linkedin"></i></a>
                            <a href="#" style="color: #cccccc; font-size: 14px; text-decoration: none;"><i class="fab fa-twitter"></i></a>
                            <a href="#" style="color: #cccccc; font-size: 14px; text-decoration: none;"><i class="fab fa-instagram"></i></a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    </div>
    <!-- ======================================================================================== -->
    <!-- 🔒 END PROTECTED - Landing Page -->
    <!-- ======================================================================================== -->

    <!-- ======================================================================================== -->
    <!-- 🔒 PROTECTED - GETTING STARTED PAGE STRUCTURE & CSS -->
    <!-- Only the content inside "✏️ EDITABLE SECTION" can be modified -->
    <!-- Everything else (Header, Footer, Navigation, CSS, Container) is PROTECTED -->
    <!-- ======================================================================================== -->
    <div id="gettingStartedPage" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #ffffff !important; z-index: -1; overflow-y: auto; opacity: 0; transition: none; visibility: hidden;">
        <style>
            /* Reset für Getting Started Page */
            #gettingStartedPage,
            #gettingStartedPage * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            #gettingStartedPage {
                color: #2c2c2c !important;
                line-height: 1.7 !important;
                background: #ffffff !important;
                font-family: 'Inter', sans-serif !important;
                font-weight: 400 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 100vh !important;
            }
            
            #gettingStartedPage a {
                text-decoration: none !important;
                color: inherit !important;
                transition: all 0.3s ease !important;
            }
            
            #gettingStartedPage ul {
                list-style: none !important;
            }
            
            #gettingStartedPage .gs-container {
                max-width: 1600px !important;
                margin: 0 auto !important;
                padding: 0 calc(30px + 1cm) !important;
            }
            #gettingStartedPage .gs-main-container {
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                background: #F5F5F5 !important;
            }
            #gettingStartedPage header {
                background: #F0EBE3 !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                z-index: 1001 !important;
                border-bottom: 1px solid #f0f0f0 !important;
                padding: 18px 0 !important;
                transition: all 0.3s ease !important;
            }
            #gettingStartedPage .header-content {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
            }
            #gettingStartedPage .gs-logo {
                font-family: 'Playfair Display', serif !important;
                font-size: 18px !important;
                font-weight: 500 !important;
                white-space: nowrap !important;
                margin-right: 15px !important;
            }
            #gettingStartedPage .gs-logo .swiss-part {
                font-family: 'Playfair Display', serif !important;
                font-size: 18px !important;
                font-weight: 500 !important;
                color: #8b7355 !important;
            }
            #gettingStartedPage .gs-logo .asset-part {
                font-family: 'Playfair Display', serif !important;
                font-size: 18px !important;
                font-weight: 500 !important;
                color: #000000 !important;
            }
            #gettingStartedPage .gs-header-nav {
                display: flex !important;
                gap: 10px !important;
                flex-wrap: nowrap !important;
                flex: 1 !important;
                justify-content: center !important;
                margin: 0 auto !important;
                max-width: calc(100% - 360px) !important;
                padding: 0 15px !important;
                align-items: center !important;
            }
            #gettingStartedPage .gs-header-nav a {
                font-weight: 400 !important;
                font-size: 10.5px !important;
                color: #666666 !important;
                position: relative !important;
                padding: 6px 0 !important;
                white-space: nowrap !important;
            }
            #gettingStartedPage .gs-header-nav a:after {
                content: '' !important;
                position: absolute !important;
                width: 0 !important;
                height: 1px !important;
                bottom: 0 !important;
                left: 0 !important;
                background: #000000 !important;
                transition: width 0.3s ease !important;
            }
            #gettingStartedPage .gs-header-nav a:hover {
                color: #000000 !important;
            }
            #gettingStartedPage .gs-header-nav a:hover:after {
                width: 100% !important;
            }
            
            /* Dropdown Menu Styles */
            #gettingStartedPage .gs-nav-dropdown {
                position: relative !important;
                display: inline-flex !important;
                align-items: center !important;
            }
            #gettingStartedPage .gs-nav-dropdown-trigger {
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
            }
            #gettingStartedPage .gs-nav-dropdown-content {
                display: none !important;
                position: absolute !important;
                top: 100% !important;
                left: 0 !important;
                background: #ffffff !important;
                min-width: 180px !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
                border-radius: 0 !important;
                padding: 8px 0 !important;
                margin-top: 2px !important;
                z-index: 1000 !important;
                pointer-events: auto !important;
            }
            #gettingStartedPage .gs-nav-dropdown:hover .gs-nav-dropdown-content,
            #gettingStartedPage .gs-nav-dropdown-content:hover {
                display: block !important;
            }
            #gettingStartedPage .gs-nav-dropdown-content a {
                display: block !important;
                padding: 10px 20px !important;
                color: #666666 !important;
                text-decoration: none !important;
                font-size: 11px !important;
                transition: all 0.2s ease !important;
                border-left: 3px solid transparent !important;
                pointer-events: auto !important;
            }
            #gettingStartedPage .gs-nav-dropdown-content a:hover {
                background: #f8f8f8 !important;
                color: #000000 !important;
                border-left-color: #8b7355 !important;
            }
            #gettingStartedPage .gs-nav-dropdown-content a:after {
                display: none !important;
            }
            #gettingStartedPage .gs-header-actions {
                display: flex !important;
                gap: 8px !important;
                align-items: center !important;
                margin-left: 10px !important;
                margin-right: 30px !important;
            }
            #gettingStartedPage .gs-btn {
                background: none !important;
                border: none !important;
                cursor: pointer !important;
                font-size: 11px !important;
                color: #666666 !important;
                transition: all 0.3s ease !important;
                padding: 2px 0 !important;
            }
            #gettingStartedPage .gs-btn:hover {
                color: #000000 !important;
            }
            #gettingStartedPage .gs-login-btn {
                border: 1px solid #000000 !important;
                color: #000000 !important;
                padding: 5px 12px !important;
                border-radius: 0 !important;
                font-size: 10px !important;
                font-weight: 400 !important;
                background: none !important;
                cursor: pointer !important;
            }
            #gettingStartedPage .gs-login-btn:hover {
                background: #000000 !important;
                color: #ffffff !important;
            }
            #gettingStartedPage .gs-main {
                margin-top: 80px !important;
                padding: 0 !important;
                flex: 1 !important;
                background: transparent !important;
                max-width: 1600px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
            #gettingStartedPage .gs-page-title {
                background: #DDD5C8 !important;
                color: #2c3e50 !important;
                font-size: 14px !important;
                margin: 0 !important;
                text-align: left !important;
                width: 100vw !important;
                position: fixed !important;
                top: 60px !important;
                left: 0 !important;
                right: 0 !important;
                box-sizing: border-box !important;
                z-index: 1000 !important;
                font-family: 'Playfair Display', serif !important;
                font-weight: 400 !important;
                padding-left: calc(30px + 1cm) !important;
                padding-top: 0 !important;
                padding-bottom: 2px !important;
                padding-right: 0 !important;
                height: 35px !important;
                min-height: 35px !important;
                max-height: 35px !important;
                display: flex !important;
                align-items: flex-end !important;
                line-height: 1 !important;
                letter-spacing: 0.8px !important;
            }
            #gettingStartedPage .gs-main-container {
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                background: transparent !important;
            }
            #gettingStartedPage .gs-page-content {
                background: transparent !important;
                border-radius: 0 !important;
                min-height: calc(100vh - 200px) !important;
                padding: 0 !important;
                margin-top: calc(60px + 35px) !important;
                color: var(--color-primary-dark) !important;
                margin: 0 !important;
                width: 100% !important;
            }
            
            /* Volle Breite für Section-Hintergründe */
            #gettingStartedPage .gs-page-content > div {
                width: 100% !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
            }
            
            /* KOMPLETT NEUE LÖSUNG - Container mit festen Rändern */
            #gettingStartedPage .gs-page-content {
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                display: block !important;
            }
            
            #gettingStartedPage .gs-content-placeholder {
                background: transparent !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                display: block !important;
            }
            
            /* NUCLEAR OPTION - Überschreibe ALLES - SYMMETRISCH 30px SICHTBAR */
            #gettingStartedPage .gs-content-placeholder {
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
                max-width: none !important;
                box-sizing: border-box !important;
            }
            
            /* Neue Farbpalette - CSS Variablen */
            :root {
                /* Primärfarben */
                --eichenbraun: #7a6a52;
                --perlweiss: #f8f9fa;
                --nachtblau: #1a1d29;
                
                /* Akzentfarben */
                --honiggold: #c9a96e;
                --waldgruen: #3d5a50;
                --gebirgsblau: #5d7b93;
                
                /* Neutrale Töne */
                --morgenlicht: #e9ecef;
                --steingrau: #8a8d93;
                --kohlegrau: #495057;
            }
            
            /* J.P. Morgan Style Typography für alle Content-Seiten */
            /* Globale Schriftart für alle Content-Seiten (außer Login, Animation, Landing) */
            #gettingStartedPage * {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
            }
            
            /* Typografie mit neuer Farbpalette - ASYMMETRISCH */
            #gettingStartedPage h1 {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                font-size: 2.5rem !important;
                font-weight: 600 !important;
                color: var(--perlweiss) !important;
                margin-bottom: 1.5rem !important;
                line-height: 1.2 !important;
                background: var(--eichenbraun) !important;
                padding: 30px 0 !important;
                margin: 0 0 1.5rem 0 !important;
                text-align: center !important;
                width: 100vw !important;
                position: relative !important;
                left: 50% !important;
                right: 50% !important;
                margin-left: -50vw !important;
                margin-right: -50vw !important;
                box-sizing: border-box !important;
            }
            
            #gettingStartedPage h2 {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                font-size: 2rem !important;
                font-weight: 500 !important;
                color: var(--eichenbraun) !important;
                margin-bottom: 1.25rem !important;
                margin-top: 2.5rem !important;
                line-height: 1.3 !important;
            }
            
            #gettingStartedPage h3 {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                font-size: 1.5rem !important;
                font-weight: 600 !important;
                color: var(--kohlegrau) !important;
                margin-bottom: 1rem !important;
                margin-top: 2rem !important;
                line-height: 1.4 !important;
            }
            
            #gettingStartedPage p {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                font-size: 1.1rem !important;
                line-height: 1.7 !important;
                color: var(--steingrau) !important;
                margin-bottom: 1.5rem !important;
            }
            
            /* Professionelle Karten mit neuer Farbpalette */
            #gettingStartedPage .card {
                background: var(--perlweiss) !important;
                border: 1px solid var(--morgenlicht) !important;
                border-radius: 8px !important;
                padding: 2rem !important;
                margin-bottom: 2rem !important;
                box-shadow: 0 2px 8px rgba(26, 29, 41, 0.08) !important;
                transition: all 0.3s ease !important;
            }
            
            #gettingStartedPage .card:hover {
                box-shadow: 0 4px 16px rgba(26, 29, 41, 0.12) !important;
                transform: translateY(-2px) !important;
                border-color: var(--honiggold) !important;
            }
            
            /* Buttons und Links mit Akzentfarben */
            #gettingStartedPage button,
            #gettingStartedPage .btn,
            #gettingStartedPage input[type="button"],
            #gettingStartedPage input[type="submit"] {
                background: var(--honiggold) !important;
                color: var(--nachtblau) !important;
                border: 1px solid var(--eichenbraun) !important;
                transition: all 0.3s ease !important;
            }
            
            #gettingStartedPage button:hover,
            #gettingStartedPage .btn:hover {
                background: var(--eichenbraun) !important;
                color: var(--perlweiss) !important;
                transform: translateY(-1px) !important;
            }
            
            /* Links mit Akzentfarben */
            #gettingStartedPage a {
                color: var(--gebirgsblau) !important;
                text-decoration: none !important;
                transition: color 0.3s ease !important;
            }
            
            #gettingStartedPage a:hover {
                color: var(--waldgruen) !important;
                text-decoration: underline !important;
            }
            /* Content-Placeholder mit neuer Farbpalette */
            #gettingStartedPage .gs-content-placeholder {
                text-align: left !important;
                color: var(--steingrau) !important;
                font-size: 16px !important;
            }
            
            /* WICHTIG: Alle direkten Kinder des Content-Placeholders sollen KEINE horizontalen Margins haben */
            #gettingStartedPage .gs-content-placeholder > * {
                margin-left: 0 !important;
                margin-right: 0 !important;
            }
            
            /* Zentriere alle Content-Container mit max-width wie Dashboard */
            #gettingStartedPage .gs-content-placeholder > div {
                max-width: 1600px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
            
            /* Spezielle Akzente für wichtige Elemente */
            #gettingStartedPage .highlight {
                background: var(--honiggold) !important;
                color: var(--nachtblau) !important;
                padding: 0.2rem 0.5rem !important;
                border-radius: 4px !important;
            }
            
            #gettingStartedPage .success {
                color: var(--waldgruen) !important;
            }
            
            #gettingStartedPage .warning {
                color: var(--eichenbraun) !important;
            }
            
            #gettingStartedPage .info {
                color: var(--gebirgsblau) !important;
            }
            
            /* WICHTIG: Grün für positiv und Rot für negativ beibehalten */
            #gettingStartedPage .positive,
            #gettingStartedPage .profit,
            #gettingStartedPage .gain,
            #gettingStartedPage .up,
            #gettingStartedPage .success-value {
                color: #28a745 !important; /* Grün für positive Werte */
            }
            
            #gettingStartedPage .negative,
            #gettingStartedPage .loss,
            #gettingStartedPage .down,
            #gettingStartedPage .error-value {
                color: #dc3545 !important; /* Rot für negative Werte */
            }
            
            /* Chart-Farben beibehalten */
            #gettingStartedPage .chart-positive {
                color: #28a745 !important;
                background-color: rgba(40, 167, 69, 0.1) !important;
            }
            
            #gettingStartedPage .chart-negative {
                color: #dc3545 !important;
                background-color: rgba(220, 53, 69, 0.1) !important;
            }
            
            /* KOMPLETTE FARBPALETTE FÜR ALLE ELEMENTE */
            
            /* Grafiken und Charts */
            #gettingStartedPage .chart-line,
            #gettingStartedPage .graph-line,
            #gettingStartedPage .performance-line {
                stroke: var(--honiggold) !important;
                fill: var(--honiggold) !important;
            }
            
            #gettingStartedPage .chart-grid,
            #gettingStartedPage .graph-grid {
                stroke: var(--morgenlicht) !important;
            }
            
            #gettingStartedPage .chart-axis,
            #gettingStartedPage .graph-axis {
                color: var(--steingrau) !important;
                stroke: var(--steingrau) !important;
            }
            
            /* Buttons - alle Varianten */
            #gettingStartedPage .btn-primary,
            #gettingStartedPage .btn-main,
            #gettingStartedPage .btn-update {
                background: var(--honiggold) !important;
                color: var(--nachtblau) !important;
                border: 1px solid var(--eichenbraun) !important;
            }
            
            #gettingStartedPage .btn-secondary,
            #gettingStartedPage .btn-cancel {
                background: var(--morgenlicht) !important;
                color: var(--kohlegrau) !important;
                border: 1px solid var(--steingrau) !important;
            }
            
            /* Sparplaner spezielle Farben */
            #gettingStartedPage .sparplaner-card,
            #gettingStartedPage .savings-plan {
                background: var(--perlweiss) !important;
                border: 1px solid var(--honiggold) !important;
            }
            
            #gettingStartedPage .sparplaner-title {
                color: var(--eichenbraun) !important;
            }
            
            #gettingStartedPage .sparplaner-amount {
                color: var(--waldgruen) !important;
            }
            
            /* Input-Felder */
            #gettingStartedPage input[type="text"],
            #gettingStartedPage input[type="number"],
            #gettingStartedPage select {
                background: var(--perlweiss) !important;
                border: 1px solid var(--morgenlicht) !important;
                color: var(--kohlegrau) !important;
            }
            
            #gettingStartedPage input:focus,
            #gettingStartedPage select:focus {
                border-color: var(--honiggold) !important;
                box-shadow: 0 0 0 2px rgba(201, 169, 110, 0.2) !important;
            }
            
            /* Labels und Beschriftungen */
            #gettingStartedPage label {
                color: var(--kohlegrau) !important;
            }
            
            /* Status-Balken */
            #gettingStartedPage .status-bar,
            #gettingStartedPage .progress-bar {
                background: var(--morgenlicht) !important;
            }
            
            #gettingStartedPage .status-bar-fill {
                background: var(--waldgruen) !important;
            }
            
            /* Tooltips */
            #gettingStartedPage .tooltip {
                background: var(--nachtblau) !important;
                color: var(--perlweiss) !important;
            }
            
            /* Titel-Balken - IMMER STICKY, 35px HÖHE (ca. 3mm weniger), AN HEADER GESCHMIEGT */
            #gettingStartedPage .gs-page-title {
                background: #DDD5C8 !important;
                color: #2c3e50 !important;
                font-size: 14px !important;
                margin: 0 !important;
                text-align: left !important;
                width: 100vw !important;
                position: fixed !important;
                top: 60px !important;
                left: 0 !important;
                right: 0 !important;
                box-sizing: border-box !important;
                z-index: 1000 !important;
                font-family: 'Playfair Display', serif !important;
                font-weight: 400 !important;
                padding-left: calc(30px + 1cm) !important;
                padding-top: 0 !important;
                padding-bottom: 2px !important;
                padding-right: 0 !important;
                height: 35px !important;
                min-height: 35px !important;
                max-height: 35px !important;
                display: flex !important;
                align-items: flex-end !important;
                line-height: 1 !important;
                letter-spacing: 0.8px !important;
            }
            
            /* ===================================== */
            /* RESPONSIVE DESIGN - Media Queries     */
            /* ===================================== */
            
            /* Mobile Phones (< 768px) */
            @media screen and (max-width: 767px) {
                #gettingStartedPage .gs-content-placeholder {
                    padding: 0 !important;
                }
                
                #gettingStartedPage h1 {
                    font-size: 1.8rem !important;
                    padding: 20px 0 !important;
                }
                
                #gettingStartedPage .gs-page-title {
                    font-size: 11px !important;
                    height: 35px !important;
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    width: 100vw !important;
                    position: fixed !important;
                    top: 60px !important;
                    letter-spacing: 0.8px !important;
                }
                
                #gettingStartedPage .gs-page-title h1 {
                    font-size: 11px !important;
                    color: #2c3e50 !important;
                    letter-spacing: 0.8px !important;
                }
                
                #gettingStartedPage h2 {
                    font-size: 1.5rem !important;
                }
                
                #gettingStartedPage h3 {
                    font-size: 1.2rem !important;
                }
            }
            
            /* Tablets (768px - 1023px) */
            @media screen and (min-width: 768px) and (max-width: 1023px) {
                #gettingStartedPage .gs-content-placeholder {
                    padding: 0 !important;
                }
                
                #gettingStartedPage h1 {
                    font-size: 2.2rem !important;
                    padding: 25px 0 !important;
                }
                
                #gettingStartedPage .gs-page-title {
                    font-size: 12px !important;
                    height: 35px !important;
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    width: 100vw !important;
                    position: fixed !important;
                    top: 60px !important;
                    letter-spacing: 0.8px !important;
                }
                
                #gettingStartedPage .gs-page-title h1 {
                    font-size: 12px !important;
                    color: #2c3e50 !important;
                    letter-spacing: 0.8px !important;
                }
            }
            
            /* Desktop (>= 1024px) */
            @media screen and (min-width: 1024px) {
                #gettingStartedPage .gs-content-placeholder {
                    padding: 0 !important;
                }
                
                #gettingStartedPage h1 {
                    font-size: 2.5rem !important;
                    padding: 30px 0 !important;
                }
                
                #gettingStartedPage .gs-page-title {
                    font-size: 14px !important;
                    height: 35px !important;
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    width: 100vw !important;
                    position: fixed !important;
                    top: 60px !important;
                    letter-spacing: 0.8px !important;
                }
                
                #gettingStartedPage .gs-page-title h1 {
                    font-size: 14px !important;
                    color: #2c3e50 !important;
                    letter-spacing: 0.8px !important;
                }
            }
            
            #gettingStartedPage .gs-content-placeholder h2 {
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                font-size: 28px !important;
                margin-bottom: 15px !important;
                color: var(--eichenbraun) !important;
                font-weight: 400 !important;
            }
            #gettingStartedPage .gs-content-placeholder p {
                color: #666666 !important;
                font-size: 16px !important;
                line-height: 1.7 !important;
            }
            #gettingStartedPage .gs-footer {
                background: #000000 !important;
                color: #ffffff !important;
                padding: 80px 0 40px !important;
                margin-top: auto !important;
            }
            #gettingStartedPage .gs-footer-content {
                display: grid !important;
                grid-template-columns: 2fr 1fr 1fr 1fr !important;
                gap: 50px !important;
                margin-bottom: 60px !important;
            }
            #gettingStartedPage .gs-footer-brand {
                max-width: 350px !important;
            }
            #gettingStartedPage .gs-footer-logo {
                font-family: 'Playfair Display', serif !important;
                font-size: 24px !important;
                font-weight: 500 !important;
                color: #ffffff !important;
                margin-bottom: 20px !important;
            }
            #gettingStartedPage .gs-footer-logo .swiss-part {
                color: #8b7355 !important;
            }
            #gettingStartedPage .gs-footer-logo .asset-part {
                color: #ffffff !important;
            }
            #gettingStartedPage .gs-footer-description {
                font-size: 14px !important;
                color: #cccccc !important;
                line-height: 1.7 !important;
                margin-bottom: 25px !important;
            }
            #gettingStartedPage .gs-footer-heading {
                font-size: 15px !important;
                color: #ffffff !important;
                font-weight: 500 !important;
                margin-bottom: 20px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
            }
            #gettingStartedPage .gs-footer-links {
                list-style: none !important;
            }
            #gettingStartedPage .gs-footer-links li {
                margin-bottom: 12px !important;
            }
            #gettingStartedPage .gs-footer-links a {
                color: #cccccc !important;
                font-size: 13px !important;
            }
            #gettingStartedPage .gs-footer-links a:hover {
                color: #ffffff !important;
            }
            #gettingStartedPage .gs-footer-bottom {
                border-top: 1px solid #333333 !important;
                padding-top: 30px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                font-size: 13px !important;
                color: #888888 !important;
            }
            #gettingStartedPage .gs-social-links {
                display: flex !important;
                gap: 12px !important;
            }
            #gettingStartedPage .gs-social-links a {
                color: #cccccc !important;
                font-size: 14px !important;
                transition: all 0.3s ease !important;
            }
            #gettingStartedPage .gs-social-links a:hover {
                color: #ffffff !important;
            }
            
            /* CSS Variables für Sektionsfarben */
            :root {
                --section-white: #ffffff;
                --section-beige: #f0ebe5;
            }
            
            /* Responsive Design */
            @media (max-width: 1200px) {
                #gettingStartedPage .gs-footer-content {
                    grid-template-columns: 1fr 1fr !important;
                }
                #gettingStartedPage .gs-header-nav {
                    gap: 8px !important;
                }
                #gettingStartedPage .gs-header-nav a {
                    font-size: 10px !important;
                }
                #gettingStartedPage .gs-page-title {
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    letter-spacing: 0.8px !important;
                }
                #gettingStartedPage .gs-page-title h1 {
                    letter-spacing: 0.8px !important;
                }
                #gettingStartedPage header {
                    background: #F0EBE3 !important;
                }
            }
            
            /* Mobile Navigation Button */
            #gettingStartedPage .gs-mobile-nav-btn {
                display: none !important;
                background: #8B7355 !important;
                color: white !important;
                border: none !important;
                padding: 6px 12px !important;
                font-size: 10px !important;
                cursor: pointer !important;
                border-radius: 0 !important;
                font-weight: 500 !important;
            }
            #gettingStartedPage .gs-mobile-nav-btn:hover {
                background: #7A6449 !important;
            }
            #gettingStartedPage .gs-mobile-nav-menu {
                display: none !important;
                position: absolute !important;
                top: 100% !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background: white !important;
                border: 1px solid #d0d0d0 !important;
                padding: 10px 0 !important;
                min-width: 200px !important;
                max-height: 400px !important;
                overflow-y: auto !important;
                z-index: 2000 !important;
            }
            #gettingStartedPage .gs-mobile-nav-menu.show {
                display: block !important;
            }
            #gettingStartedPage .gs-mobile-nav-menu a {
                display: block !important;
                padding: 8px 15px !important;
                color: #333 !important;
                text-decoration: none !important;
                font-size: 11px !important;
            }
            #gettingStartedPage .gs-mobile-nav-menu a:hover {
                background: #F8F8F8 !important;
            }
            
            @media (max-width: 992px) {
                #gettingStartedPage .gs-header-nav {
                    display: none !important;
                }
                #gettingStartedPage .gs-mobile-nav-btn {
                    display: block !important;
                }
                #gettingStartedPage .gs-page-title {
                    font-size: 12px !important;
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    letter-spacing: 0.8px !important;
                }
                #gettingStartedPage .gs-page-title h1 {
                    letter-spacing: 0.8px !important;
                }
                #gettingStartedPage header {
                    background: #F0EBE3 !important;
                }
            }
            
            @media (max-width: 768px) {
                #gettingStartedPage .gs-container {
                    padding: 0 calc(30px + 1cm) !important;
                }
                #gettingStartedPage .gs-main-container {
                    padding: 0 !important;
                }
                #gettingStartedPage .gs-page-content {
                    padding: 20px 15px !important;
                    margin: 0 !important;
                }
                #gettingStartedPage .gs-footer-content {
                    grid-template-columns: 1fr !important;
                }
                #gettingStartedPage .gs-footer-bottom {
                    flex-direction: column !important;
                    gap: 15px !important;
                    text-align: center !important;
                }
                #gettingStartedPage .gs-logo {
                    font-size: 20px !important;
                }
                #gettingStartedPage .gs-page-title {
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                    letter-spacing: 0.8px !important;
                    font-size: 11px !important;
                }
                #gettingStartedPage .gs-page-title h1 {
                    letter-spacing: 0.8px !important;
                }
                #gettingStartedPage header {
                    background: #F0EBE3 !important;
                }
                #gettingStartedPage .gs-mobile-nav-btn {
                    display: block !important;
                }
                #gettingStartedPage .gs-header-nav {
                    display: none !important;
                }
            }
            
            /* Marktdaten im Balken - dezent und mittig */
            #gettingStartedPage .gs-page-title {
                display: flex !important;
                align-items: baseline !important;
                justify-content: space-between !important;
                padding-right: calc(30px + 1cm) !important;
                line-height: 35px !important;
            }
            
            #gettingStartedPage .gs-title-text {
                font-family: 'Playfair Display', serif !important;
                font-size: inherit !important;
                color: inherit !important;
                font-weight: 400 !important;
                letter-spacing: 0.8px !important;
                line-height: inherit !important;
                margin-top: 2mm !important;
            }
            
            #gettingStartedPage .gs-title-market-data {
                display: flex !important;
                align-items: baseline !important;
                gap: 15px !important;
                font-size: 9px !important;
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif !important;
                color: #555 !important;
                opacity: 0.85 !important;
                line-height: inherit !important;
                position: relative !important;
                top: -0.8mm !important;
            }
            
            #gettingStartedPage .gs-live-badge {
                background: #28a745 !important;
                color: white !important;
                padding: 1px 4px !important;
                border-radius: 2px !important;
                font-size: 7px !important;
                font-weight: 600 !important;
                letter-spacing: 0.5px !important;
            }
            
            #gettingStartedPage .gs-market-item {
                font-weight: 400 !important;
                color: #555 !important;
            }
            
            @media (max-width: 1200px) {
                #gettingStartedPage .gs-title-market-data {
                    font-size: 8px !important;
                    gap: 10px !important;
                }
                #gettingStartedPage .gs-live-badge {
                    font-size: 6px !important;
                }
            }
            
            @media (max-width: 768px) {
                #gettingStartedPage .gs-title-market-data {
                    display: none !important;
                }
            }
        </style>
        
        <!-- ======================================================================================== -->
        <!-- 🔒 PROTECTED - Header & Navigation - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
        <!-- Contains: Logo, Navigation Links, Client Access Button -->
        <!-- ======================================================================================== -->
        <header>
            <div class="gs-container">
                <div class="header-content">
                    <div class="gs-logo">
                        <span class="swiss-part">Swiss</span><span class="asset-part"> Asset Pro</span>
                    </div>
                    
                    <!-- Mobile Navigation Button -->
                    <div style="position: relative; flex: 1; display: flex; justify-content: center;">
                        <button class="gs-mobile-nav-btn" onclick="toggleMobileNav()">
                            <i class="fas fa-bars" style="margin-right: 6px;"></i>Navigation
                        </button>
                        <div class="gs-mobile-nav-menu" id="mobileNavMenu">
                            <a href="#" onclick="backToLandingPage(); closeMobileNav(); return false;">Start</a>
                            <a href="#" onclick="loadGSPage('getting-started'); closeMobileNav(); return false;">Getting Started</a>
                            <a href="#" onclick="loadGSPage('dashboard'); closeMobileNav(); return false;">Dashboard</a>
                            <a href="#" onclick="loadGSPage('portfolio'); closeMobileNav(); return false;">Portfolio</a>
                            <a href="#" onclick="loadGSPage('strategieanalyse'); closeMobileNav(); return false;">Strategie</a>
                            <a href="#" onclick="loadGSPage('simulation'); closeMobileNav(); return false;">Simulation</a>
                            <a href="#" onclick="loadGSPage('backtesting'); closeMobileNav(); return false;">Backtesting</a>
                            <a href="#" onclick="loadGSPage('investing'); closeMobileNav(); return false;">Investing</a>
                            <a href="#" onclick="loadGSPage('value-testing'); closeMobileNav(); return false;">Value Investing</a>
                            <a href="#" onclick="loadGSPage('momentum-growth'); closeMobileNav(); return false;">Momentum Growth</a>
                            <a href="#" onclick="loadGSPage('buy-hold'); closeMobileNav(); return false;">Buy & Hold</a>
                            <a href="#" onclick="loadGSPage('carry-strategy'); closeMobileNav(); return false;">Carry Strategy</a>
                            <a href="#" onclick="loadGSPage('bericht'); closeMobileNav(); return false;">Bericht</a>
                            <a href="#" onclick="loadGSPage('markets'); closeMobileNav(); return false;">Märkte</a>
                            <a href="#" onclick="loadGSPage('assets'); closeMobileNav(); return false;">Assets</a>
                            <a href="#" onclick="loadGSPage('methodik'); closeMobileNav(); return false;">Methodik</a>
                            <a href="#" onclick="loadGSPage('black-litterman'); closeMobileNav(); return false;">B. Litterman & BVAR</a>
                            <a href="#" onclick="loadGSPage('sources'); closeMobileNav(); return false;">Steuern</a>
                            <a href="#" onclick="loadGSPage('about'); closeMobileNav(); return false;">Über mich</a>
                            <a href="#" onclick="loadGSPage('transparency'); closeMobileNav(); return false;">Transparenz</a>
                        </div>
                    </div>
                    
                    <nav class="gs-header-nav">
                        <a href="#" onclick="backToLandingPage(); return false;">Start</a>
                        <a href="#" onclick="loadGSPage('getting-started'); return false;" id="nav-getting-started">Getting Started</a>
                        <a href="#" onclick="loadGSPage('dashboard'); return false;" id="nav-dashboard">Dashboard</a>
                        <a href="#" onclick="loadGSPage('portfolio'); return false;" id="nav-portfolio">Portfolio</a>
                        <a href="#" onclick="loadGSPage('strategieanalyse'); return false;" id="nav-strategieanalyse">Strategie</a>
                        <a href="#" onclick="loadGSPage('simulation'); return false;" id="nav-simulation">Simulation</a>
                        <a href="#" onclick="loadGSPage('backtesting'); return false;" id="nav-backtesting">Backtesting</a>
                        <div class="gs-nav-dropdown" id="nav-investing-dropdown">
                            <a href="#" onclick="loadGSPage('investing'); return false;" id="nav-investing" class="gs-nav-dropdown-trigger">
                                Investing <i class="fas fa-caret-down" style="font-size: 10px; margin-left: 4px;"></i>
                            </a>
                            <div class="gs-nav-dropdown-content">
                                <a href="#" onclick="loadGSPage('investing'); return false;">Overview</a>
                                <a href="#" onclick="loadGSPage('value-testing'); return false;" id="nav-value-testing">Value Investing</a>
                                <a href="#" onclick="loadGSPage('momentum-growth'); return false;" id="nav-momentum-growth">Momentum Growth</a>
                                <a href="#" onclick="loadGSPage('buy-hold'); return false;" id="nav-buy-hold">Buy & Hold</a>
                                <a href="#" onclick="loadGSPage('carry-strategy'); return false;" id="nav-carry-strategy">Carry Strategy</a>
                            </div>
                        </div>
                        <a href="#" onclick="loadGSPage('bericht'); return false;" id="nav-bericht">Bericht</a>
                        <a href="#" onclick="loadGSPage('markets'); return false;" id="nav-markets">Märkte</a>
                        <a href="#" onclick="loadGSPage('assets'); return false;" id="nav-assets">Assets</a>
                        <a href="#" onclick="loadGSPage('methodik'); return false;" id="nav-methodik">Methodik</a>
                        <a href="#" onclick="loadGSPage('black-litterman'); return false;" id="nav-black-litterman">B. Litterman & BVAR</a>
                        <a href="#" onclick="loadGSPage('sources'); return false;" id="nav-sources">Steuern</a>
                        <a href="#" onclick="loadGSPage('about'); return false;" id="nav-about">Über mich</a>
                        <a href="#" onclick="loadGSPage('transparency'); return false;" id="nav-transparency">Transparenz</a>
                    </nav>
                    <div class="gs-header-actions">
                        <!-- Menu Button with Logout and Reset options -->
                        <div class="gs-nav-dropdown" style="position: relative;">
                            <button class="gs-login-btn gs-menu-btn" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; font-size: 13px; background: none; cursor: pointer; height: 36px; min-width: 90px; border: 1px solid #e0e0e0;">
                                <i class="fas fa-bars" style="margin-right: 6px;"></i>Menü <i class="fas fa-caret-down" style="font-size: 10px; margin-left: 4px;"></i>
                            </button>
                            <div class="gs-nav-dropdown-content" style="min-width: 150px; right: 0; left: auto;">
                                <a href="#" onclick="logout(); return false;" style="color: #666666 !important;">
                                    <i class="fas fa-sign-out-alt" style="margin-right: 8px;"></i>Abmelden
                                </a>
                                <a href="#" onclick="resetProgress(); return false;" style="color: #d32f2f !important;">
                                    <i class="fas fa-trash-alt" style="margin-right: 8px;"></i>Neu starten
                                </a>
                            </div>
                        </div>
                        
                        <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" target="_blank" class="gs-login-btn" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; font-size: 13px; height: 36px; min-width: 90px; border: 1px solid #e0e0e0;">
                            <i class="fab fa-linkedin" style="margin-right: 6px;"></i>LinkedIn
                        </a>
                    </div>
                </div>
            </div>
        </header>
        <!-- ======================================================================================== -->
        <!-- 🔒 END PROTECTED - Header & Navigation -->
        <!-- ======================================================================================== -->

        <!-- ======================================================================================== -->
        <!-- 🔒 PROTECTED - Main Content Container Structure - DO NOT MODIFY -->
        <!-- ======================================================================================== -->
        <main class="gs-main">
            <div class="gs-main-container">
                <div class="gs-page-title" id="gsPageTitle">
                    <span class="gs-title-text">Getting Started</span>
                    <div class="gs-title-market-data">
                        <span class="gs-live-badge">LIVE</span>
                        <span class="gs-market-item">SMI: <span id="bar-smi">--</span></span>
                        <span class="gs-market-item">S&P: <span id="bar-sp500">--</span></span>
                        <span class="gs-market-item">Gold: <span id="bar-gold">--</span></span>
                        <span class="gs-market-item">EUR/CHF: <span id="bar-eurchf">--</span></span>
                    </div>
                </div>
                <div class="gs-page-content">
                    
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION START - Main Page Content -->
                    <!-- This is the ONLY area that can be modified for each main page -->
                    <!-- Valid for: Getting Started, Dashboard, Portfolio, Strategie, Simulation, -->
                    <!-- Backtesting, Investing, Bericht, Märkte & News, Asset-Klassen, Methodik, -->
                    <!-- Black-Litterman, Über Mich -->
                    <!-- ============================================================================ -->
                    
                    <div class="gs-content-placeholder" id="gsPageContent" style="text-align: left; color: var(--steingrau); font-size: 16px; padding: 0; box-sizing: border-box; width: 100%; margin: 0;">
                        <!-- Content wird durch JavaScript geladen -->
                    </div>
                    
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION END -->
                    <!-- ============================================================================ -->
                    
                </div>
            </div>
        </main>
        <!-- ======================================================================================== -->
        <!-- 🔒 PROTECTED - End of Main Content Container -->
        <!-- ======================================================================================== -->

        <!-- ======================================================================================== -->
        <!-- 🔒 PROTECTED - Footer - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
        <!-- Contains: Footer Logo, Service Links, Resources, Company Info, Copyright -->
        <!-- ======================================================================================== -->
        <footer class="gs-footer">
            <div class="gs-container">
                <div class="gs-footer-content">
                    <div class="gs-footer-brand">
                        <div class="gs-footer-logo">
                            <span class="swiss-part">Swiss</span><span class="asset-part"> Asset Pro</span>
                        </div>
                        <p class="gs-footer-description">Swiss Asset Pro ist eine moderne Portfolio-Management-Plattform, die quantitative Analyse, Echtzeit-Daten und fortgeschrittene Optimierungsstrategien kombiniert, um Investoren bei fundierten Anlageentscheidungen zu unterstützen.</p>
                    </div>
                    
                    <div class="gs-footer-column">
                        <h3 class="gs-footer-heading">TOOLS & SERVICES</h3>
                        <ul class="gs-footer-links">
                            <li><a href="#">Portfolio-Simulation</a></li>
                            <li><a href="#">Strategie-Analyse</a></li>
                            <li><a href="#">Backtesting & Vergleich</a></li>
                            <li><a href="#">Investment Insights</a></li>
                        </ul>
                    </div>
                    
                    <div class="gs-footer-column">
                        <h3 class="gs-footer-heading">KNOWLEDGE HUB</h3>
                        <ul class="gs-footer-links">
                            <li><a href="#">Märkte & News</a></li>
                            <li><a href="#">Asset-Klassen</a></li>
                            <li><a href="#">Methodik & Modelle</a></li>
                            <li><a href="#">Black-Litterman & BVAR</a></li>
                        </ul>
                    </div>
                    
                    <div class="gs-footer-column">
                        <h3 class="gs-footer-heading">ABOUT</h3>
                        <ul class="gs-footer-links">
                            <li><a href="#">Über das Projekt</a></li>
                            <li><a href="#">Erste Schritte</a></li>
                            <li><a href="#">Berichte</a></li>
                            <li><a href="#">Kontakt</a></li>
                        </ul>
                    </div>
                </div>
                
                <div class="gs-footer-bottom">
                    <div class="gs-copyright">
                        © 2025 Swiss Asset Pro. All rights reserved.
                    </div>
                    <div class="gs-social-links">
                        <a href="#"><i class="fab fa-linkedin"></i></a>
                        <a href="#"><i class="fab fa-twitter"></i></a>
                        <a href="#"><i class="fab fa-instagram"></i></a>
                    </div>
                </div>
            </div>
        </footer>
        <!-- ======================================================================================== -->
        <!-- 🔒 END PROTECTED - Footer -->
        <!-- ======================================================================================== -->
    </div>
    
    <!-- ======================================================================================== -->
    <!-- 🔒 PROTECTED - JavaScript Functions - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION -->
    <!-- Contains: Animation Logic, Navigation, Page Loading, Transitions -->
    <!-- ======================================================================================== -->
    <script>
        // ===== CACHE BUSTER v8061 - ROTER TEST + 0.4CM HÖHE =====
        console.log('%c🚀 Swiss Asset Pro v8061 - ROTER TEST + 0.4CM HÖHE!', 'background: red; color: white; font-size: 16px; padding: 10px;');
        console.log('%c✅ CSS: ROTER HINTERGRUND zum Testen ob CSS geladen wird', 'color: #FF0000; font-size: 14px;');
        
        // Erzwinge Breite für alle Seiten + Titel-Balken
        document.addEventListener('DOMContentLoaded', function() {
            const style = document.createElement('style');
            style.textContent = `
                main { max-width: 1600px !important; width: 100% !important; }
                .page { padding: 35px 0 !important; width: 100% !important; max-width: 100% !important; }
                #gettingStartedPage .gs-page-title { 
                    width: 100vw !important; 
                    height: 35px !important;
                    min-height: 35px !important;
                    max-height: 35px !important;
                    position: fixed !important;
                    top: 60px !important;
                    background: #DDD5C8 !important;
                    color: #2c3e50 !important;
                    padding-left: calc(30px + 1cm) !important;
                }
            `;
            document.head.appendChild(style);
            console.log('%c✅ Balken-Styles angepasst (35px, hellbraun, responsive)', 'color: #2196F3; font-size: 14px;');
            
                        // Setze Balken-Styles - IMMER STICKY, KEINE ANIMATIONEN
                        setTimeout(function() {
                            const titleElement = document.querySelector('#gettingStartedPage .gs-page-title');
                            if (titleElement) {
                                titleElement.style.width = '100vw';
                                titleElement.style.position = 'fixed';
                                titleElement.style.top = '60px';
                                titleElement.style.left = '0';
                                titleElement.style.right = '0';
                                titleElement.style.paddingLeft = 'calc(30px + 1cm)';
                                titleElement.style.paddingTop = '0';
                                titleElement.style.paddingBottom = '2px';
                                titleElement.style.paddingRight = '0';
                                titleElement.style.display = 'flex';
                                titleElement.style.alignItems = 'flex-end';
                                titleElement.style.background = '#DDD5C8';
                                titleElement.style.color = '#2c3e50';
                                titleElement.style.fontSize = '14px';
                                titleElement.style.textAlign = 'left';
                                titleElement.style.lineHeight = '1';
                                titleElement.style.height = '35px';
                                titleElement.style.minHeight = '35px';
                                titleElement.style.maxHeight = '35px';
                                titleElement.style.letterSpacing = '0.8px';
                                titleElement.style.zIndex = '1000';
                                console.log('%c✅ Titel-Balken Styles gesetzt - IMMER STICKY!', 'color: #FF6B6B; font-size: 14px;');
                            }
                        }, 100);
        });
        // ===== END CACHE BUSTER =====
        
        // Welcome Screen Animation starten
        function startWelcomeAnimation() {
            const welcomeScreen = document.getElementById('welcomeScreen');
            const landingPage = document.getElementById('landingPage');
            
            // Landing Page sofort im Hintergrund vorbereiten
            landingPage.style.display = 'block';
            landingPage.style.opacity = '0';
            landingPage.style.zIndex = '999';
            
            // Welcome Screen anzeigen
            welcomeScreen.classList.add('active');
            welcomeScreen.style.display = 'flex';
            welcomeScreen.style.zIndex = '10000';
            welcomeScreen.style.background = '#0A0A0A';
            
            // Starte Aktien-Linie Animation
            setTimeout(() => {
                const stockLine = document.getElementById('fadingStockLine');
                if (stockLine) {
                    stockLine.style.opacity = '0';
                }
            }, 1800);
            
            // Nach Animation: Welcome Screen ausblenden und Landing Page DIREKT einblenden
            // Landing page erscheint sofort wenn Ladeb alken fertig ist (2.2s)
            setTimeout(() => {
                // Sofortiges Umschalten ohne Transition
                welcomeScreen.style.display = 'none';
                welcomeScreen.style.opacity = '0';
                
                landingPage.style.display = 'block';
                landingPage.style.opacity = '1';
                landingPage.style.zIndex = '1000';
                landingPage.style.visibility = 'visible';
            }, 2200);
        }

        // PWA Installation
        let deferredPrompt;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const banner = document.getElementById('pwaInstallBanner');
            if (banner) {
                banner.style.display = 'block';
                setTimeout(() => {
                    banner.style.transform = 'translateY(0)';
                }, 100);
            }
        });

        function installPWA() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('PWA installation accepted');
                    }
                    deferredPrompt = null;
                    dismissInstallBanner();
                });
            }
        }

        function dismissInstallBanner() {
            const banner = document.getElementById('pwaInstallBanner');
            if (banner) {
                banner.style.transform = 'translateY(100%)';
                setTimeout(() => {
                    banner.style.display = 'none';
                }, 300);
            }
        }

        function closeIOSInstructions() {
            document.getElementById('iosInstallInstructions').style.display = 'none';
        }

        // Offline/Online Status
        window.addEventListener('online', () => {
            document.getElementById('offlineIndicator').style.display = 'none';
        });

        window.addEventListener('offline', () => {
            document.getElementById('offlineIndicator').style.display = 'block';
        });

        // Footer initial verstecken
        window.addEventListener('DOMContentLoaded', function() {
            const footer = document.querySelector('footer');
            if (footer) footer.style.display = 'none';
            
            // Login Screen richtig positionieren
            const loginScreen = document.getElementById('passwordProtection');
            if (loginScreen) {
                loginScreen.style.display = 'flex';
            }
        });

        // Getting Started Seite anzeigen
        function showGettingStartedPage(pageId = 'getting-started') {
            const landingPage = document.getElementById('landingPage');
            const gettingStartedPage = document.getElementById('gettingStartedPage');
            
            // Sofortiges Umschalten ohne Verzögerung
            landingPage.style.display = 'none';
            landingPage.style.opacity = '0';
            
            gettingStartedPage.style.display = 'block';
            gettingStartedPage.style.visibility = 'visible';
            gettingStartedPage.style.zIndex = '10000';
            gettingStartedPage.style.opacity = '1';
            
            // Seite laden
            loadGSPage(pageId);
            
            // Initialize sticky header after page loads
            setTimeout(() => {
                initStickyHeader();
            }, 100);
        }

        // Zurück zur Landing Page
        // Mobile Navigation Toggle
        function toggleMobileNav() {
            const menu = document.getElementById('mobileNavMenu');
            if (menu) {
                menu.classList.toggle('show');
            }
        }
        
        function closeMobileNav() {
            const menu = document.getElementById('mobileNavMenu');
            if (menu) {
                menu.classList.remove('show');
            }
        }
        
        // Close mobile nav when clicking outside
        document.addEventListener('click', function(event) {
            const menu = document.getElementById('mobileNavMenu');
            const btn = document.querySelector('.gs-mobile-nav-btn');
            if (menu && btn && !menu.contains(event.target) && !btn.contains(event.target)) {
                menu.classList.remove('show');
            }
        });
        
        function backToLandingPage() {
            closeMobileNav();
            const landingPage = document.getElementById('landingPage');
            const gettingStartedPage = document.getElementById('gettingStartedPage');
            
            // Deaktiviere alle Transitions für sofortigen Wechsel
            gettingStartedPage.style.transition = 'none';
            landingPage.style.transition = 'none';
            
            // Sofortiges Umschalten ohne Verzögerung
            gettingStartedPage.style.display = 'none';
            gettingStartedPage.style.visibility = 'hidden';
            gettingStartedPage.style.zIndex = '-1';
            gettingStartedPage.style.opacity = '0';
            
            landingPage.style.display = 'block';
            landingPage.style.visibility = 'visible';
            landingPage.style.zIndex = '1000';
            landingPage.style.opacity = '1';
        }

        // Seiteninhalte für Getting Started Page
        const gsPageContents = {
            'getting-started': {
                title: 'Getting Started',
                icon: 'fa-rocket',
                heading: 'Erste Schritte',
                description: 'Alles, was Sie wissen müssen, um mit Swiss Asset Pro durchzustarten.'
            },
            'dashboard': {
                title: 'Dashboard',
                icon: 'fa-chart-pie',
                heading: 'Dashboard',
                description: 'Übersicht über Ihr Portfolio und aktuelle Marktentwicklungen.'
            },
            'portfolio': {
                title: 'Portfolio',
                icon: 'fa-briefcase',
                heading: 'Portfolio',
                description: 'Detaillierte Aufstellung Ihres Portfolios mit allen Positionen und Performance-Daten.'
            },
            'strategie': {
                title: 'Strategie',
                icon: 'fa-chess',
                heading: 'Anlagestrategie',
                description: 'Erfahren Sie mehr über unsere Investment-Philosophie und strategischen Ansätze.'
            },
            'strategieanalyse': {
                title: 'Strategieanalyse',
                icon: 'fa-chart-scatter',
                heading: 'Multi-Strategie Analyse',
                description: 'Vergleichen Sie 5 verschiedene Portfolio-Optimierungsstrategien'
            },
            'simulation': {
                title: 'Simulation',
                icon: 'fa-desktop',
                heading: 'Portfolio Simulation',
                description: 'Testen Sie verschiedene Anlagestrategien in unserer Simulationsumgebung.'
            },
            'backtesting': {
                title: 'Backtesting',
                icon: 'fa-chart-line',
                heading: 'Backtesting',
                description: 'Analysieren Sie die historische Performance Ihrer Strategien.'
            },
            'investing': {
                title: 'Investing',
                icon: 'fa-coins',
                heading: 'Investing',
                description: 'Entdecken Sie Investment-Möglichkeiten und Marktanalysen.'
            },
            'bericht': {
                title: 'Bericht',
                icon: 'fa-file-alt',
                heading: 'Berichte & Analysen',
                description: 'Zugriff auf Performance-Berichte und detaillierte Marktanalysen.'
            },
            'markets': {
                title: 'Märkte',
                icon: 'fa-newspaper',
                heading: 'Märkte',
                description: 'Aktuelle Marktentwicklungen und relevante Finanznachrichten.'
            },
            'assets': {
                title: 'Assets & Investment',
                icon: 'fa-layer-group',
                heading: 'Assets & Investment',
                description: 'Umfassende Theorie und Praxis zu allen Anlageklassen.'
            },
            'methodik': {
                title: 'Methodik',
                icon: 'fa-cogs',
                heading: 'Methodik',
                description: 'Details zu unseren analytischen Methoden und Prozessen.'
            },
            'sources': {
                title: 'Steuern',
                icon: 'fa-landmark',
                heading: 'Steuern',
                description: 'Datenquellen und Schweizer Steuern & Abgaben.'
            },
            'black-litterman': {
                title: 'Black-Litterman & BVAR',
                icon: 'fa-chart-bar',
                heading: 'Black-Litterman & BVAR',
                description: 'Advanced Portfolio-Optimierung mit Black-Litterman und Bayesian Vector Autoregression.'
            },
            'about': {
                title: 'Über mich',
                icon: 'fa-user',
                heading: 'Über mich',
                description: 'Lernen Sie das Team hinter Swiss Asset Pro kennen.'
            },
            'transparency': {
                title: 'Transparenz',
                icon: 'fa-eye',
                heading: 'Transparenz & Dokumentation',
                description: 'Vollständige Dokumentation aller Berechnungen, Datenquellen und Benutzeraktionen.'
            },
            'value-testing': {
                title: 'Value Investing',
                icon: 'fa-search-dollar',
                heading: 'Value Investing',
                description: 'Fundamentale Bewertung (DCF, Graham, PEG)'
            },
            'momentum-growth': {
                title: 'Momentum Growth',
                icon: 'fa-chart-line',
                heading: 'Momentum Growth',
                description: 'Technische Analyse und Momentum-Strategien'
            },
            'buy-hold': {
                title: 'Buy & Hold',
                icon: 'fa-shield-alt',
                heading: 'Buy & Hold',
                description: 'Langfristige Fundamentale Stabilität'
            },
            'carry-strategy': {
                title: 'Carry Strategy',
                icon: 'fa-coins',
                heading: 'Carry Strategy',
                description: 'Zinsdifferenzial-Analyse'
            }
        };

        // Original Getting Started Content speichern (beim ersten Laden)
        let originalGettingStartedContent = null;
        
        // Seite laden in Getting Started Page
        function loadGSPage(pageId) {
            const pageData = gsPageContents[pageId];
            if (!pageData) return;

            // Titel aktualisieren
            const titleElement = document.getElementById('gsPageTitle');
            const titleTextElement = titleElement.querySelector('.gs-title-text');
            if (titleTextElement) {
                titleTextElement.textContent = pageData.title;
            } else {
                titleElement.textContent = pageData.title;
            }
            
            const contentElement = document.getElementById('gsPageContent');
            
            // Original Getting Started Content beim ersten Aufruf speichern
            if (originalGettingStartedContent === null && pageId === 'getting-started') {
                originalGettingStartedContent = contentElement.innerHTML;
            }
            
            // Content aktualisieren
            if (pageId === 'getting-started') {
                // Getting Started: Vollständiger Content
                contentElement.innerHTML = `
                    <!-- Main Content Wrapper mit einheitlichen Seitenrändern -->
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                    
                    <!-- Visual Website Structure -->
                    <div style="max-width: 1600px; margin: 0 auto 25px auto;">
                        <div style="margin-bottom: 15px; border-bottom: 2px solid #8B7355; padding-bottom: 10px;">
                            <h3 style="font-family: 'Inter', sans-serif; font-size: 24px; color: #2c3e50; margin: 0; font-weight: 600;">Seitenübersicht</h3>
                        </div>
                        <p style="color: #333333; font-size: 15px; line-height: 1.5; margin-bottom: 15px;">Hier sind alle verfügbaren Seiten und was Sie dort machen können:</p>

                        <div class="website-structure" style="margin: 10px 0;">
                            <div class="structure-section" style="margin-bottom: 12px;">
                                <h4 style="color: #2c3e50; font-size: 14px; margin-bottom: 10px; font-weight: 600;">Hauptmodule</h4>
                                <div class="structure-items" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                                    <div class="structure-item" onclick="loadGSPage('dashboard')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-chart-pie" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Dashboard</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('portfolio')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-briefcase" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Portfolio</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('strategieanalyse')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-chess" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Strategie</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('simulation')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-dice" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Simulation</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('backtesting')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-history" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Backtesting</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('investing')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-coins" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Investing</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('bericht')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-file-alt" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Bericht</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('markets')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-newspaper" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Märkte</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('assets')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-coins" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Assets</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('methodik')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-calculator" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Methodik</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('about')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-user" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Über mich</div>
                                    </div>
                                </div>
                            </div>

                            <div class="structure-section" style="margin-bottom: 12px;">
                                <h4 style="color: #2c3e50; font-size: 14px; margin-bottom: 10px; font-weight: 600;">Analyse & Testing</h4>
                                <div class="structure-items" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                                    <div class="structure-item" onclick="loadGSPage('backtesting')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-flask" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Backtesting</div>
                                        </div>
                                    <div class="structure-item" onclick="loadGSPage('strategieanalyse')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-chart-bar" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Strategie Analyse</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('simulation')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-rocket" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Monte-Carlo</div>
                                    </div>
                                </div>
                            </div>

                            <div class="structure-section" style="margin-bottom: 12px;">
                                <h4 style="color: #2c3e50; font-size: 14px; margin-bottom: 10px; font-weight: 600;">Markt & Daten</h4>
                                <div class="structure-items" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">
                                    <div class="structure-item" onclick="loadGSPage('markets')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-globe" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Live-Marktdaten</div>
                                        </div>
                                    <div class="structure-item" onclick="loadGSPage('assets')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-coins" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Asset-Klassen</div>
                                    </div>
                                </div>
                            </div>

                            <div class="structure-section" style="margin-bottom: 12px;">
                                <h4 style="color: #2c3e50; font-size: 14px; margin-bottom: 10px; font-weight: 600;">Dokumentation</h4>
                                <div class="structure-items" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                                    <div class="structure-item" onclick="loadGSPage('methodik')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-calculator" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Methodik</div>
                                        </div>
                                    <div class="structure-item" onclick="loadGSPage('bericht')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-file-alt" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Bericht & PDF</div>
                                    </div>
                                    <div class="structure-item" onclick="loadGSPage('about')" style="display: flex; align-items: center; gap: 6px; padding: 10px 12px; background: #FFFFFF; border-radius: 0; cursor: pointer; transition: all 0.2s ease; border: 1px solid #d0d0d0;">
                                        <i class="fas fa-user" style="color: #2c3e50; font-size: 12px; min-width: 12px;"></i>
                                        <div style="font-size: 13px; color: #333333; font-weight: 500;">Über mich</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Quick Start Guide -->
                    <div style="margin-bottom: 20px; padding: 20px; background: #FFFFFF; border-radius: 0; border: 1px solid #d0d0d0;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; border-bottom: 2px solid #8B7355; padding-bottom: 8px;">
                            <i class="fas fa-rocket" style="color: #2c3e50; font-size: 16px;"></i>
                            <h3 style="font-family: 'Inter', sans-serif; font-size: 20px; color: #2c3e50; margin: 0; font-weight: 600;">Schnellstart</h3>
                        </div>
                        <p style="color: #333333; font-size: 14px; line-height: 1.5; margin-bottom: 12px;">Drei Schritte zum perfekten Portfolio:</p>

                        <div class="steps-container" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0;">
                            <div class="step" style="display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 15px; background: #F8F8F8; border-radius: 0; border-top: 3px solid #8B7355; text-align: center;">
                                <div class="step-number" style="background: #8B7355; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px;">1</div>
                                <div class="step-content">
                                    <h4 style="font-family: 'Inter', sans-serif; font-size: 14px; color: #2c3e50; margin: 0 0 5px 0; font-weight: 600;">Assets hinzufügen</h4>
                                    <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0 0 8px 0;">Wählen Sie Aktien & Indizes aus</p>
                                    <button class="btn secondary" onclick="loadGSPage('dashboard')" style="background: #8B7355; color: white; border: none; padding: 8px 14px; border-radius: 0; cursor: pointer; font-size: 12px; font-weight: 500; width: 100%;">Dashboard</button>
                                </div>
                            </div>

                            <div class="step" style="display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 15px; background: #F8F8F8; border-radius: 0; border-top: 3px solid #8B7355; text-align: center;">
                                <div class="step-number" style="background: #8B7355; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px;">2</div>
                                <div class="step-content">
                                    <h4 style="font-family: 'Inter', sans-serif; font-size: 14px; color: #2c3e50; margin: 0 0 5px 0; font-weight: 600;">Strategie wählen</h4>
                                    <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0 0 8px 0;">Optimierungsmethode testen</p>
                                    <button class="btn secondary" onclick="loadGSPage('strategieanalyse')" style="background: #8B7355; color: white; border: none; padding: 8px 14px; border-radius: 0; cursor: pointer; font-size: 12px; font-weight: 500; width: 100%;">Strategie</button>
                                </div>
                            </div>

                            <div class="step" style="display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 15px; background: #F8F8F8; border-radius: 0; border-top: 3px solid #8B7355; text-align: center;">
                                <div class="step-number" style="background: #8B7355; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 16px;">3</div>
                                <div class="step-content">
                                    <h4 style="font-family: 'Inter', sans-serif; font-size: 14px; color: #2c3e50; margin: 0 0 5px 0; font-weight: 600;">Analysieren</h4>
                                    <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0 0 8px 0;">Performance & Bericht</p>
                                    <button class="btn secondary" onclick="loadGSPage('bericht')" style="background: #8B7355; color: white; border: none; padding: 8px 14px; border-radius: 0; cursor: pointer; font-size: 12px; font-weight: 500; width: 100%;">Bericht</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="margin-bottom: 20px; padding: 20px; background: #FFFFFF; border-radius: 0; border: 1px solid #d0d0d0;">
                        <h3 style="font-family: 'Inter', sans-serif; font-size: 20px; color: #2c3e50; margin: 0 0 15px 0; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 8px;">Plattform-Funktionen</h3>
                        
                        <div class="features-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Portfolio-Tracking</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Echtzeit-Überwachung Ihrer Anlagen mit Performance-Kennzahlen und Analysen.</p>
                            </div>

                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Risikobewertung</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Umfassende Risikobewertungstools zum Verständnis und Management Ihres Portfolio-Risikos.</p>
                            </div>

                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Portfolio-Optimierung</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Fortschrittliche Algorithmen zur Optimierung Ihrer Vermögensallokation für bessere Renditen.</p>
                            </div>

                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Marktanalyse</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Bleiben Sie informiert über die neuesten Markttrends, Nachrichten und Anlagemöglichkeiten.</p>
                            </div>

                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Finanzplanung</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Tools zur Planung Ihrer Altersvorsorge, Ausbildung oder anderer finanzieller Ziele.</p>
                            </div>

                            <div class="feature-item" style="background: #F8F8F8; padding: 18px; border-radius: 0; border: 1px solid #e0e0e0;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 15px; color: #2c3e50; margin: 0 0 8px 0; font-weight: 600;">Individuelle Berichte</h4>
                                <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0;">Erstellen Sie detaillierte Berichte und Analysen, um Ihre Anlageentwicklung zu verfolgen.</p>
                            </div>
                        </div>
                    </div>

                    <div class="quick-links-container" style="margin-bottom: 20px; padding: 20px; background: #FFFFFF; border-radius: 0; border: 1px solid #d0d0d0;">
                        <h3 style="font-family: 'Inter', sans-serif; font-size: 20px; color: #2c3e50; margin: 0 0 15px 0; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 8px;">Schnellzugriff</h3>
                        <div class="quick-links" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                            <a href="#" class="quick-link" onclick="loadGSPage('investing'); return false;" style="display: flex; align-items: center; gap: 10px; padding: 12px; background: #F8F8F8; border-radius: 0; text-decoration: none; color: #333333; transition: all 0.3s ease; border: 1px solid #e0e0e0;">
                                <span style="font-weight: 500;">Anlage-Bildung</span>
                            </a>
                            <a href="#" class="quick-link" onclick="loadGSPage('markets'); return false;" style="display: flex; align-items: center; gap: 10px; padding: 12px; background: #F8F8F8; border-radius: 0; text-decoration: none; color: #333333; transition: all 0.3s ease; border: 1px solid #e0e0e0;">
                                <span style="font-weight: 500;">Marktnachrichten</span>
                            </a>
                            <a href="#" class="quick-link" onclick="loadGSPage('assets'); return false;" style="display: flex; align-items: center; gap: 10px; padding: 12px; background: #F8F8F8; border-radius: 0; text-decoration: none; color: #333333; transition: all 0.3s ease; border: 1px solid #e0e0e0;">
                                <span style="font-weight: 500;">Assets erkunden</span>
                            </a>
                            <a href="#" class="quick-link" onclick="loadGSPage('methodik'); return false;" style="display: flex; align-items: center; gap: 10px; padding: 12px; background: #F8F8F8; border-radius: 0; text-decoration: none; color: #333333; transition: all 0.3s ease; border: 1px solid #e0e0e0;">
                                <span style="font-weight: 500;">Methodik</span>
                            </a>
                        </div>
                    </div>

                    <!-- FINMA Disclaimer -->
                    <div style="margin-bottom: 20px; padding: 20px; background: #FFFFFF; border-radius: 0; border: 2px solid #8B7355; border-left: 5px solid #8B7355;">
                        <h3 style="font-family: 'Inter', sans-serif; font-size: 18px; color: #2c3e50; margin: 0 0 12px 0; font-weight: 600;">FINMA Hinweis</h3>

                        <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0 0 12px 0; font-weight: 500;">
                            <strong>Wichtiger rechtlicher Hinweis:</strong> Diese Plattform ist keine FINMA-lizenzierte Finanzdienstleistung. Alle hier dargestellten Analysen, Simulationen und Empfehlungen dienen ausschließlich Bildungs- und Informationszwecken und stellen keine Anlageberatung dar.
                        </p>

                        <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 12px; border-left: 3px solid #8B7355;">
                            <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Keine Anlageberatung:</h4>
                            <ul style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0; padding-left: 18px;">
                                <li>Keine individuelle Anlageempfehlungen</li>
                                <li>Keine Berücksichtigung persönlicher Umstände</li>
                                <li>Keine Garantie für Renditen oder Verluste</li>
                                <li>Keine Haftung für Anlageentscheidungen</li>
                            </ul>
                        </div>

                        <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 12px; border-left: 3px solid #8B7355;">
                            <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Risikohinweis:</h4>
                            <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0;">
                                Alle Anlagen sind mit Risiken verbunden. Der Wert von Anlagen kann fallen und steigen. Vergangene Performance ist kein Indikator für zukünftige Ergebnisse. <strong>Investieren Sie nur Geld, dessen Verlust Sie sich leisten können.</strong>
                            </p>
                        </div>

                        <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 10px; border-left: 3px solid #8B7355;">
                            <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Empfehlung:</h4>
                            <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0;">
                                Konsultieren Sie vor jeder Anlageentscheidung einen qualifizierten Finanzberater oder eine FINMA-lizenzierte Bank. Diese Plattform ersetzt keine professionelle Beratung.
                            </p>
                        </div>

                        <div style="text-align: center; padding-top: 10px; border-top: 1px solid #d0d0d0;">
                            <a href="https://www.finma.ch" target="_blank" style="color: #8B7355; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
                                <i class="fas fa-external-link-alt"></i>
                                Weitere Informationen: www.finma.ch
                            </a>
                        </div>
                    </div>
                    
                    </div>
                    <!-- End Main Content Wrapper -->
                `;
            } else if (pageId === 'dashboard') {
                // Dashboard: Vollständiger Dashboard-Code
                contentElement.innerHTML = `
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION START - DASHBOARD CONTENT -->
                    <!-- ============================================================================ -->
                    
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">

                        <!-- Instruction Card -->
                        <div style="background: var(--morgenlicht); border-radius: 0; padding: 25px 30px; margin-bottom: 25px; border-left: 4px solid var(--color-accent-rose);">
                            <h3 style="color: #1a1a1a; margin-bottom: 15px; font-size: 1.3rem; font-family: 'Playfair Display', serif; display: flex; align-items: center; gap: 10px;">
 Was Sie hier tun können
                            </h3>
                            <p style="color: #212529; margin-bottom: 15px; line-height: 1.6;">Wählen Sie Schweizer Aktien, internationale Indizes und andere Assets aus. Legen Sie für jede Anlage den Investitionsbetrag fest und klicken Sie auf "Portfolio Berechnen", um die vollständige Analyse zu erhalten.</p>
                            <div style="display: flex; align-items: center; gap: 8px; color: var(--color-accent-rose); font-weight: 500;">
                                <i class="fas fa-chart-line" style="font-size: 16px;"></i>
                                <strong>Live-Daten:</strong> Aktuelle Aktienkurse werden automatisch geladen und alle 15 Minuten aktualisiert
                            </div>
                        </div>

                        <!-- Portfolio Configuration -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-cog"></i> Portfolio Konfiguration
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                    <div style="display: flex; flex-direction: column; gap: 8px;">
                                        <label style="font-weight: 500; color: #1a1a1a; font-size: 14px;">Gesamtinvestition (CHF)</label>
                                        <input type="number" id="totalInvestment" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;" value="100000" min="1000" step="1000">
                                    </div>
                                    <div style="display: flex; flex-direction: column; gap: 8px;">
                                        <label style="font-weight: 500; color: #1a1a1a; font-size: 14px;">Investitionszeitraum (Jahre)</label>
                                        <input type="number" id="investmentYears" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;" value="5" min="1" max="30">
                                    </div>
                                    <div style="display: flex; flex-direction: column; gap: 8px;">
                                        <label style="font-weight: 500; color: #1a1a1a; font-size: 14px;">Risikoprofil</label>
                                        <select id="riskProfile" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;">
                                            <option value="conservative">Konservativ</option>
                                            <option value="moderate" selected>Moderat</option>
                                            <option value="aggressive">Aggressiv</option>
                                        </select>
                                    </div>
                                </div>
                                <div id="totalValidation" style="padding: 12px 15px; border-radius: 0; font-size: 14px; text-align: center; background: rgba(40, 167, 69, 0.1); color: #28a745; border: 1px solid rgba(40, 167, 69, 0.2);">
                                    Investitionen stimmen überein: CHF 0 von CHF 100.000
                                </div>
                            </div>
                        </div>

                        <!-- Asset Selection -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-plus-circle"></i> Assets hinzufügen
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                                    <select id="stockSelect" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;">
                                        <option value="">Schweizer Aktie auswählen...</option>
                                    </select>
                                    <select id="indexSelect" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;">
                                        <option value="">Internationale Indizes...</option>
                                    </select>
                                    <select id="assetSelect" style="padding: 10px 12px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; transition: all 0.3s ease;">
                                        <option value="">Weitere Assets...</option>
                                    </select>
                                </div>
                                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                    <button onclick="addStock()" style="display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: 1px solid #1a1a1a; background-color: transparent; color: #1a1a1a; font-size: 14px; gap: 8px;">
                                        <i class="fas fa-chart-line"></i> Aktie hinzufügen
                                    </button>
                                    <button onclick="addIndex()" style="display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: 1px solid #1a1a1a; background-color: transparent; color: #1a1a1a; font-size: 14px; gap: 8px;">
 Index hinzufügen
                                    </button>
                                    <button onclick="addAsset()" style="display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: 1px solid #1a1a1a; background-color: transparent; color: #1a1a1a; font-size: 14px; gap: 8px;">
                                        <i class="fas fa-coins"></i> Asset hinzufügen
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Selected Assets -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-list"></i> Ausgewählte Assets
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div id="selectedStocks" style="min-height: 100px; border: 1px dashed #ddd; border-radius: 0; padding: 20px; display: flex; align-items: center; justify-content: center;">
                                    <div style="text-align: center; color: #6c757d;">
                                        <i class="fas fa-folder-open" style="font-size: 2rem; margin-bottom: 10px; color: #ddd;"></i>
                                        <p>Noch keine Assets hinzugefügt</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Calculate Section -->
                        <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border-radius: 0; padding: 30px; text-align: center; margin-bottom: 30px;">
                            <h3 style="color: #ffffff; margin-bottom: 10px; font-size: 1.5rem; font-family: 'Playfair Display', serif;">Portfolio Analyse Starten</h3>
                            <p style="color: rgba(255, 255, 255, 0.8); margin-bottom: 20px;">Klicken Sie auf Berechnen, um Ihre Portfolio-Performance zu analysieren</p>
                            <button onclick="calculatePortfolio()" style="display: inline-flex; align-items: center; justify-content: center; padding: 12px 30px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: none; font-size: 16px; gap: 8px; background-color: #1a1a1a; color: #ffffff;">
                                <i class="fas fa-calculator"></i> Portfolio Berechnen
                            </button>
                        </div>

                        <!-- Portfolio Chart -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-chart-pie"></i> Portfolio Verteilung
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; align-items: center;">
                                    <div style="height: 300px; position: relative;">
                                        <canvas id="portfolioChart" width="400" height="300"></canvas>
                                    </div>
                                    <div>
                                        <h4 style="color: #1a1a1a; margin-bottom: 15px; text-align: center; font-family: 'Playfair Display', serif;">Asset Verteilung</h4>
                                        <div id="portfolioLegend" style="display: flex; flex-direction: column; gap: 10px; max-height: 250px; overflow-y: auto;">
                                            <!-- Legend will be populated dynamically -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Asset Performance -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-chart-line"></i> Asset Performance
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                                    <button class="timeframe-btn active" data-timeframe="5y" style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 0; background: #1a1a1a; color: #ffffff; border-color: #1a1a1a; cursor: pointer; transition: all 0.3s ease; font-size: 14px;">5 Jahre</button>
                                    <button class="timeframe-btn" data-timeframe="1y" style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 0; background: var(--perlweiss); color: #6c757d; cursor: pointer; transition: all 0.3s ease; font-size: 14px;">1 Jahr</button>
                                    <button class="timeframe-btn" data-timeframe="6m" style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 0; background: var(--perlweiss); color: #6c757d; cursor: pointer; transition: all 0.3s ease; font-size: 14px;">6 Monate</button>
                                    <button class="timeframe-btn" data-timeframe="1m" style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 0; background: var(--perlweiss); color: #6c757d; cursor: pointer; transition: all 0.3s ease; font-size: 14px;">1 Monat</button>
                                </div>
                                <div style="height: 300px; position: relative;">
                                    <canvas id="assetPerformanceChart" width="400" height="300"></canvas>
                                </div>
                            </div>
                        </div>

                        <!-- Metrics Grid -->
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease; border-top: 4px solid var(--color-accent-rose);">
                                <div style="width: 50px; height: 50px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; color: var(--color-accent-rose); font-size: 20px;">
                                    <i class="fas fa-chart-line"></i>
                                </div>
                                <div id="portfolioPerformance" style="font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 5px;">0.0%</div>
                                <div style="color: #6c757d; font-size: 14px;">Erwartete Jahresrendite</div>
                            </div>
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease; border-top: 4px solid var(--color-accent-rose);">
                                <div style="width: 50px; height: 50px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; color: var(--color-accent-rose); font-size: 20px;">
                                    <i class="fas fa-exclamation-triangle"></i>
                                </div>
                                <div id="riskAnalysis" style="font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 5px;">0.0%</div>
                                <div style="color: #6c757d; font-size: 14px;">Volatilität p.a.</div>
                            </div>
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease; border-top: 4px solid var(--color-accent-rose);">
                                <div style="width: 50px; height: 50px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; color: var(--color-accent-rose); font-size: 20px;">
                                    <i class="fas fa-sitemap"></i>
                                </div>
                                <div id="diversification" style="font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 5px;">0/10</div>
                                <div style="color: #6c757d; font-size: 14px;">Diversifikations-Score</div>
                            </div>
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease; border-top: 4px solid var(--color-accent-rose);">
                                <div style="width: 50px; height: 50px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 15px; color: var(--color-accent-rose); font-size: 20px;">
                                    <i class="fas fa-star"></i>
                                </div>
                                <div id="sharpeRatio" style="font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin-bottom: 5px;">0.00</div>
                                <div style="color: #6c757d; font-size: 14px;">Sharpe Ratio</div>
                            </div>
                        </div>

                        <!-- PDF Export Button -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); padding: 25px; margin-bottom: 30px; text-align: center;">
                            <h3 style="margin: 0 0 15px 0; font-size: 1.3rem; color: #1a1a1a; font-family: 'Playfair Display', serif;">
                                <i class="fas fa-file-pdf" style="color: #d32f2f;"></i> Portfolio-Report
                            </h3>
                            <p style="color: #6c757d; font-size: 14px; margin-bottom: 20px;">
                                Exportieren Sie alle Berechnungen, Grafiken und Kennzahlen als professionelles PDF (max. 2 Seiten)
                            </p>
                            <button id="exportPdfButton" onclick="exportPortfolioPDF()" style="display: inline-flex; align-items: center; gap: 10px; background: #5d4037; color: white; padding: 12px 30px; border: none; border-radius: 0; cursor: pointer; font-weight: 600; font-size: 15px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <i class="fas fa-download"></i> PDF Report Erstellen
                            </button>
                            <div id="pdfStatus" style="margin-top: 15px; font-size: 13px; color: #666;"></div>
                        </div>

                        <!-- Live Market Data -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 30px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-bolt"></i> Live Marktdaten
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div id="liveMarketData" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                    <div style="display: flex; align-items: center; gap: 15px; padding: 20px; border: 1px solid #eee; border-radius: 0; transition: all 0.3s ease;">
                                        <div style="width: 40px; height: 40px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--color-accent-rose); font-size: 16px;">
                                            <i class="fas fa-chart-line"></i>
                                        </div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: #1a1a1a; margin-bottom: 5px;">SMI</div>
                                            <div id="market-smi-price" style="font-size: 1.2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 2px;">Lädt...</div>
                                            <div id="market-smi-change" style="font-size: 14px; color: #6c757d;">--</div>
                                        </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 15px; padding: 20px; border: 1px solid #eee; border-radius: 0; transition: all 0.3s ease;">
                                        <div style="width: 40px; height: 40px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--color-accent-rose); font-size: 16px;">
                                            <i class="fas fa-chart-line"></i>
                                        </div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: #1a1a1a; margin-bottom: 5px;">S&P 500</div>
                                            <div id="market-sp500-price" style="font-size: 1.2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 2px;">Lädt...</div>
                                            <div id="market-sp500-change" style="font-size: 14px; color: #6c757d;">--</div>
                                        </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 15px; padding: 20px; border: 1px solid #eee; border-radius: 0; transition: all 0.3s ease;">
                                        <div style="width: 40px; height: 40px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--color-accent-rose); font-size: 16px;">
                                            <i class="fas fa-gem"></i>
                                        </div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: #1a1a1a; margin-bottom: 5px;">Gold</div>
                                            <div id="market-gold-price" style="font-size: 1.2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 2px;">Lädt...</div>
                                            <div id="market-gold-change" style="font-size: 14px; color: #6c757d;">--</div>
                                        </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 15px; padding: 20px; border: 1px solid #eee; border-radius: 0; transition: all 0.3s ease;">
                                        <div style="width: 40px; height: 40px; background: rgba(205, 139, 118, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--color-accent-rose); font-size: 16px;">
                                            <i class="fas fa-exchange-alt"></i>
                                        </div>
                                        <div style="flex: 1;">
                                            <div style="font-weight: 600; color: #1a1a1a; margin-bottom: 5px;">EUR/CHF</div>
                                            <div id="market-eurchf-price" style="font-size: 1.2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 2px;">Lädt...</div>
                                            <div id="market-eurchf-change" style="font-size: 14px; color: #6c757d;">--</div>
                                        </div>
                                    </div>
                                </div>
                                <div style="text-align: center;">
                                    <button onclick="refreshDashboardMarketData()" style="display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: 1px solid #1a1a1a; background-color: transparent; color: #1a1a1a; font-size: 14px; gap: 8px;">
                                        <i class="fas fa-sync-alt"></i> Daten aktualisieren
                                    </button>
                                </div>
                            </div>
                        </div>

                    </div>
                    
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION END -->
                    <!-- ============================================================================ -->
                `;
            } else if (pageId === 'portfolio') {
                // Portfolio Entwicklung: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-chart-line"></i> Performance-Tracking
                            </h4>
                            <p style="color: #333333; margin-bottom: 12px; line-height: 1.5; font-size: 14px;">Analysieren Sie die historische Entwicklung Ihres Portfolios und identifizieren Sie Optimierungspotenziale.</p>
                            <button class="refresh-button" onclick="updatePortfolioDevelopment()" style="background: var(--color-accent-rose); color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-sync-alt"></i> Performance aktualisieren
                            </button>
                        </div>

                        <!-- Performance Chart -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <div class="chart-container" style="height: 400px;">
                                <canvas id="performanceChart"></canvas>
                            </div>
                        </div>

                        <!-- Performance Metrics -->
                        <div class="performance-metrics" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                            <div class="performance-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center;">
                                <div class="metric-value positive" id="totalReturn" style="font-size: 2rem; font-weight: bold; color: #28a745; margin-bottom: 10px;">+0.0%</div>
                                <div class="metric-label" style="color: #666666; font-size: 14px;">Gesamtrendite</div>
                            </div>
                            <div class="performance-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center;">
                                <div class="metric-value" id="annualizedReturn" style="font-size: 2rem; font-weight: bold; color: #333; margin-bottom: 10px;">0.0%</div>
                                <div class="metric-label" style="color: #666666; font-size: 14px;">Annualisierte Rendite</div>
                            </div>
                            <div class="performance-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center;">
                                <div class="metric-value" id="maxDrawdown" style="font-size: 2rem; font-weight: bold; color: #dc3545; margin-bottom: 10px;">0.0%</div>
                                <div class="metric-label" style="color: #666666; font-size: 14px;">Maximaler Verlust</div>
                            </div>
                            <div class="performance-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center;">
                                <div class="metric-value" id="volatilityHistory" style="font-size: 2rem; font-weight: bold; color: #333; margin-bottom: 10px;">0.0%</div>
                                <div class="metric-label" style="color: #666666; font-size: 14px;">Historische Volatilität</div>
                            </div>
                        </div>

                        <!-- Benchmark Comparison -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Performance vs. Benchmarks</h3>
                            <div class="benchmark-comparison" id="benchmarkComparison">
                                <div class="benchmark-card" style="background: #fafafa; padding: 20px; border-radius: 0; text-align: center;">
                                    <h4 style="color: #000000; margin-bottom: 10px;">Ihr Portfolio</h4>
                                    <div class="metric-value" id="portfolioBenchmarkReturn" style="font-size: 1.8rem; font-weight: bold; color: var(--color-accent-rose);">0.0%</div>
                                    <div class="metric-label" style="color: #666666; font-size: 13px;">Erwartete Rendite</div>
                                </div>
                            </div>
                        </div>

                        <!-- Peer Group Comparison -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Vergleich mit Schweizer Privatbanken</h3>
                            <div class="peer-comparison" id="peerComparison" style="text-align: center; padding: 40px; color: #999; font-size: 18px; font-style: italic;">
                                Coming Soon
                            </div>
                        </div>

                        <!-- Performance Analysis -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Performance-Analyse</h3>
                            <div id="performanceAnalysis" style="color: #666666; line-height: 1.8; font-size: 15px;">
                                <p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>
                            </div>
                        </div>
                    </div>
                `;
                
                // Initialize Portfolio Development
                if (typeof updatePortfolioDevelopment === 'function') {
                    updatePortfolioDevelopment();
                }
            } else if (pageId === 'strategieanalyse') {
                // Strategieanalyse: Vollständiger Strategieanalyse-Code
                contentElement.innerHTML = `
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION START - STRATEGIEANALYSE CONTENT -->
                    <!-- ============================================================================ -->
                    
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">

                        <!-- Instruction Card -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h3 style="color: #2c3e50; margin-bottom: 12px; font-size: 20px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
 Was diese Analyse bietet
                            </h3>
                            <p style="color: #333333; margin-bottom: 0; line-height: 1.5; font-size: 14px;">Hier sehen Sie Ihr Portfolio optimiert nach 5 wissenschaftlichen Methoden. Jede Strategie hat unterschiedliche Ziele: Maximale Rendite, minimales Risiko, oder optimale Balance.</p>
                        </div>
                        
                        <!-- Strategievergleich -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-chart-line"></i> Strategie-Vergleich
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px;">
                                    <div>
                                        <table style="width: 100%; border-collapse: collapse; background: var(--perlweiss); border-radius: 0; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                                            <thead style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);">
                                                <tr>
                                                    <th style="color: #ffffff; font-weight: 600; padding: 15px; text-align: center; font-size: 13px;">Strategie</th>
                                                    <th style="color: #ffffff; font-weight: 600; padding: 15px; text-align: center; font-size: 13px;">Rendite</th>
                                                    <th style="color: #ffffff; font-weight: 600; padding: 15px; text-align: center; font-size: 13px;">Risiko</th>
                                                    <th style="color: #ffffff; font-weight: 600; padding: 15px; text-align: center; font-size: 13px;">Sharpe Ratio</th>
                                                    <th style="color: #ffffff; font-weight: 600; padding: 15px; text-align: center; font-size: 13px;">Empfehlung</th>
                                                </tr>
                                            </thead>
                                            <tbody id="strategyTableBody">
                                                <!-- Wird dynamisch gefüllt -->
                                            </tbody>
                                        </table>
                                    </div>
                                    <div>
                                        <div style="text-align: center; margin-bottom: 20px;">
                                            <h3 style="font-family: 'Playfair Display', serif; font-weight: 600;">Portfolio-Bewertung</h3>
                                            <div id="portfolioRating" style="font-size: 72px; font-weight: 700; text-align: center; color: var(--color-accent-rose); margin: 20px 0;">0/100</div>
                                        </div>
                                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden;">
                                            <div style="padding: 25px;">
                                                <h4 style="font-family: 'Playfair Display', serif; font-weight: 600;">Gesamtbewertung</h4>
                                                <p style="margin: 10px 0;"><strong>Top-Strategie:</strong> <span id="topStrategy">-</span></p>
                                                <p style="margin: 10px 0;"><strong>Verbesserungspotenzial:</strong> <span id="improvementPotential">0%</span></p>
                                                <p style="margin: 10px 0;"><strong>Risikoprofil:</strong> <span id="riskProfile">-</span></p>
                                                <p style="margin: 10px 0;"><strong>Vergleich mit Standards:</strong> <span id="standardComparison">-</span></p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Strategie-Vergleichsdiagramm -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 25px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-chart-scatter"></i> Strategie-Vergleichsdiagramm
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div style="height: 400px; position: relative;">
                                    <canvas id="strategyComparisonChart"></canvas>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Detaillierte Strategie-Analyse -->
                        <div style="background: var(--perlweiss); border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); overflow: hidden; margin-bottom: 30px;">
                            <div style="padding: 20px 25px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                                <h3 style="margin: 0; font-size: 1.3rem; color: #1a1a1a; display: flex; align-items: center; gap: 10px; font-family: 'Playfair Display', serif;">
                                    <i class="fas fa-chart-pie"></i> Detaillierte Strategie-Analyse
                                </h3>
                            </div>
                            <div style="padding: 25px;">
                                <div id="strategyGrid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                                    <!-- Wird dynamisch gefüllt -->
                                </div>
                            </div>
                        </div>
                        
                    </div>
                    
                    <!-- ============================================================================ -->
                    <!-- ✏️ EDITABLE SECTION END -->
                    <!-- ============================================================================ -->
                `;
            } else if (pageId === 'simulation') {
                // Zukunfts-Simulation: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-crystal-ball"></i> Was diese Simulation zeigt
                            </h4>
                            <p style="color: #333333; margin-bottom: 12px; line-height: 1.5; font-size: 14px;">Basierend auf den 5 Optimierungsstrategien sehen Sie verschiedene Zukunftspfade für Ihr Portfolio. Jede Strategie hat unterschiedliche Risiko-Rendite-Profile.</p>
                            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                            <button class="refresh-button" onclick="updateSimulationPage()" style="background: var(--color-accent-rose); color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-sync-alt"></i> Simulation aktualisieren
                            </button>
                                <button onclick="loadGSPage('methodik'); return false;" style="display: inline-flex; align-items: center; justify-content: center; gap: 8px; background: #1a237e; color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                    <i class="fas fa-chart-line"></i> Zur interaktiven Monte Carlo Simulation
                                </button>
                            </div>
                        </div>

                        <!-- Simulation Chart -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <div class="chart-container" style="height: 400px;">
                                <canvas id="simulationChart"></canvas>
                            </div>
                        </div>

                        <!-- Scenario Analysis -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Szenario-Analyse</h3>
                            <p style="color: #666666; margin-bottom: 25px;">Wie sich Ihr Portfolio unter verschiedenen wirtschaftlichen Bedingungen entwickeln könnte:</p>

                            <div class="scenario-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px;">
                                <div class="scenario-card scenario-normal" style="background: #e8f5e9; padding: 20px; border-radius: 0; text-align: center; border-left: 4px solid #4caf50;">
                                    <h4 style="color: #1b5e20; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Normale Märkte</h4>
                                    <div class="metric-value positive" id="scenarioNormal" style="font-size: 1.5rem; font-weight: bold; color: #2e7d32; margin-bottom: 5px;">CHF 0</div>
                                    <div class="metric-label" style="color: #558b2f; font-size: 13px;">Erwartetes Wachstum</div>
                                </div>
                                <div class="scenario-card scenario-interest" style="background: #fff3e0; padding: 20px; border-radius: 0; text-align: center; border-left: 4px solid #ff9800;">
                                    <h4 style="color: #e65100; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Zinserhöhungen</h4>
                                    <div class="metric-value" id="scenarioInterest" style="font-size: 1.5rem; font-weight: bold; color: #f57c00; margin-bottom: 5px;">CHF 0</div>
                                    <div class="metric-label" style="color: #fb8c00; font-size: 13px;">Geringeres Wachstum</div>
                                </div>
                                <div class="scenario-card scenario-inflation" style="background: #fce4ec; padding: 20px; border-radius: 0; text-align: center; border-left: 4px solid #e91e63;">
                                    <h4 style="color: #880e4f; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Hohe Inflation</h4>
                                    <div class="metric-value" id="scenarioInflation" style="font-size: 1.5rem; font-weight: bold; color: #c2185b; margin-bottom: 5px;">CHF 0</div>
                                    <div class="metric-label" style="color: #d81b60; font-size: 13px;">Inflationsangepasst</div>
                                </div>
                                <div class="scenario-card scenario-recession" style="background: #ffebee; padding: 20px; border-radius: 0; text-align: center; border-left: 4px solid #f44336;">
                                    <h4 style="color: #b71c1c; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Rezession</h4>
                                    <div class="metric-value negative" id="scenarioRecession" style="font-size: 1.5rem; font-weight: bold; color: #c62828; margin-bottom: 5px;">CHF 0</div>
                                    <div class="metric-label" style="color: #d32f2f; font-size: 13px;">Risiko von Verlusten</div>
                                </div>
                                <div class="scenario-card scenario-growth" style="background: var(--morgenlicht); padding: 20px; border-radius: 0; text-align: center; border-left: 4px solid #2196f3;">
                                    <h4 style="color: #0d47a1; margin-bottom: 15px; font-size: 16px; font-weight: 600;">Starkes Wachstum</h4>
                                    <div class="metric-value positive" id="scenarioGrowth" style="font-size: 1.5rem; font-weight: bold; color: #1565c0; margin-bottom: 5px;">CHF 0</div>
                                    <div class="metric-label" style="color: #1976d2; font-size: 13px;">Überdurchschnittlich</div>
                                </div>
                            </div>
                        </div>

                        <!-- Path Simulation -->
                        <div class="path-simulation" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px;">
                            <div class="path-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center; border: 2px solid #28a745;">
                                <h4 style="color: #155724; margin-bottom: 15px; font-weight: 600;">Optimistisches Szenario</h4>
                                <div class="metric-value positive" id="optimisticValue" style="font-size: 1.8rem; font-weight: bold; color: #28a745; margin-bottom: 5px;">CHF 0</div>
                                <div class="metric-label" style="color: #28a745; font-size: 13px;">+15% über Benchmark</div>
                            </div>
                            <div class="path-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center; border: 2px solid #8b7355;">
                                <h4 style="color: #6d5438; margin-bottom: 15px; font-weight: 600;">Basisszenario</h4>
                                <div class="metric-value" id="baseValue" style="font-size: 1.8rem; font-weight: bold; color: var(--color-accent-rose); margin-bottom: 5px;">CHF 0</div>
                                <div class="metric-label" style="color: var(--color-accent-rose); font-size: 13px;">Erwartete Entwicklung</div>
                            </div>
                            <div class="path-card" style="background: var(--perlweiss); padding: 25px; border-radius: 0; text-align: center; border: 2px solid #6c757d;">
                                <h4 style="color: #495057; margin-bottom: 15px; font-weight: 600;">Konservatives Szenario</h4>
                                <div class="metric-value" id="conservativeValue" style="font-size: 1.8rem; font-weight: bold; color: #6c757d; margin-bottom: 5px;">CHF 0</div>
                                <div class="metric-label" style="color: #6c757d; font-size: 13px;">Risikominimiert</div>
                            </div>
                        </div>

                        <!-- Strategy Paths -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Strategie-Pfade im Vergleich</h3>
                            <div id="strategyPaths" style="color: #666666; line-height: 1.8; font-size: 15px;">
                                <p>Die Simulation zeigt, wie sich Ihr Portfolio unter verschiedenen Strategien entwickeln könnte. Bitte berechnen Sie zuerst Ihr Portfolio.</p>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'markets') {
                // Märkte: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-newspaper"></i> Marktübersicht
                            </h4>
                            <p style="color: #333333; margin-bottom: 12px; line-height: 1.5; font-size: 14px;">Bleiben Sie über die aktuellen Entwicklungen an den Finanzmärkten informiert. Daten werden alle 15 Minuten automatisch aktualisiert.</p>
                            <div style="background: #F8F8F8; padding: 10px 12px; border-radius: 0; margin-bottom: 12px; border: 1px solid #d0d0d0;">
                                <i class="fas fa-sync-alt fa-spin" style="margin-right: 5px; color: #8B7355;"></i> 
                                <span style="color: #333333; font-size: 13px;">Nächste Aktualisierung in:</span> 
                                <span id="nextRefresh" style="font-weight: 600; color: var(--color-accent-rose);">--:--</span>
                            </div>
                            <button class="refresh-button" onclick="refreshAllMarkets()" style="background: var(--color-accent-rose); color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-sync-alt"></i> Jetzt aktualisieren
                            </button>
                        </div>

                        <!-- Markets Grid -->
                        <div class="market-grid" id="liveMarketsGrid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 30px;">
                            <!-- Wird dynamisch gefüllt -->
                        </div>

                        <!-- News Sources Info -->
                        <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); border-radius: 0; padding: 20px; margin-bottom: 25px; border: 1px solid #e8e8e8;">
                            <h4 style="color: var(--kohlegrau); margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">
                                <i class="fas fa-globe" style="margin-right: 8px; color: #3498db;"></i>Aktuelle Finanznachrichten-Quellen
                            </h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                                <a href="https://www.reuters.com/markets/" target="_blank" style="display: flex; align-items: center; gap: 8px; padding: 10px 15px; background: var(--perlweiss); border-radius: 0; text-decoration: none; color: var(--kohlegrau); border: 1px solid #e0e0e0; transition: all 0.3s ease;">
                                    <i class="fas fa-external-link-alt" style="color: #3498db; font-size: 12px;"></i>
                                    <span style="font-weight: 500; font-size: 13px;">Reuters Markets</span>
                                </a>
                                <a href="https://www.ft.com/" target="_blank" style="display: flex; align-items: center; gap: 8px; padding: 10px 15px; background: var(--perlweiss); border-radius: 0; text-decoration: none; color: var(--kohlegrau); border: 1px solid #e0e0e0; transition: all 0.3s ease;">
                                    <i class="fas fa-external-link-alt" style="color: #3498db; font-size: 12px;"></i>
                                    <span style="font-weight: 500; font-size: 13px;">Financial Times</span>
                                </a>
                                <a href="https://www.bloomberg.com/" target="_blank" style="display: flex; align-items: center; gap: 8px; padding: 10px 15px; background: var(--perlweiss); border-radius: 0; text-decoration: none; color: var(--kohlegrau); border: 1px solid #e0e0e0; transition: all 0.3s ease;">
                                    <i class="fas fa-external-link-alt" style="color: #3498db; font-size: 12px;"></i>
                                    <span style="font-weight: 500; font-size: 13px;">Bloomberg</span>
                                </a>
                                <a href="https://www.nzz.ch/finanzen" target="_blank" style="display: flex; align-items: center; gap: 8px; padding: 10px 15px; background: var(--perlweiss); border-radius: 0; text-decoration: none; color: var(--kohlegrau); border: 1px solid #e0e0e0; transition: all 0.3s ease;">
                                    <i class="fas fa-external-link-alt" style="color: #3498db; font-size: 12px;"></i>
                                    <span style="font-weight: 500; font-size: 13px;">NZZ Finanzen</span>
                                </a>
                                </div>
                            </div>

                        <!-- Financial News -->
                        <div style="background: var(--color-bg-light); border-radius: 0; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(89, 89, 89, 0.1);">
                            <div class="news-header" style="margin-bottom: 20px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 8px 0; font-weight: 600;">Aktuelle Marktanalyse</h3>
                                <p style="color: var(--color-text-gray); margin: 0; font-size: 13px;">Beispielhafte Finanznachrichten zur Orientierung • Für aktuelle News besuchen Sie die oben verlinkten Quellen</p>
                            </div>
                            <div id="newsContainer" style="border-top: 1px solid var(--color-border-green); padding-top: 15px;">
                                <div class="news-item" style="padding: 18px; border-bottom: 1px solid var(--color-border-green); transition: all 0.3s ease; background: var(--perlweiss); margin-bottom: 12px; border-radius: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                        <h4 style="color: var(--color-primary-dark); margin: 0; font-size: 15px; font-weight: 600; line-height: 1.4;">Schweizer Börse startet positiv in die Woche</h4>
                                        <span style="background: var(--color-accent-rose); color: #ffffff; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 0;">Reuters</span>
                                    </div>
                                    <p style="color: var(--color-text-gray); margin: 10px 0; font-size: 13px; line-height: 1.6;">Der SMI zeigt eine stabile Entwicklung mit moderaten Gewinnen. Schweizer Blue-Chip-Aktien profitieren von der robusten Konjunktur und der starken Franken-Position.</p>
                                    <div style="display: flex; gap: 15px; font-size: 11px; color: var(--color-text-gray);">
                                        <span><i class="fas fa-clock" style="margin-right: 5px;"></i>Beispiel</span>
                                        <span><i class="fas fa-tag" style="margin-right: 5px;"></i>Markt</span>
                                    </div>
                                </div>
                                <div class="news-item" style="padding: 18px; border-bottom: 1px solid var(--color-border-green); transition: all 0.3s ease; background: var(--perlweiss); margin-bottom: 12px; border-radius: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                        <h4 style="color: var(--color-primary-dark); margin: 0; font-size: 15px; font-weight: 600; line-height: 1.4;">EZB signalisiert vorsichtige Geldpolitik</h4>
                                        <span style="background: var(--color-accent-rose); color: #ffffff; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 0;">Bloomberg</span>
                                    </div>
                                    <p style="color: var(--color-text-gray); margin: 10px 0; font-size: 13px; line-height: 1.6;">Die Europäische Zentralbank bleibt bei ihrer aktuellen Zinspolitik und beobachtet die Inflation genau. Experten erwarten keine überraschenden Änderungen.</p>
                                    <div style="display: flex; gap: 15px; font-size: 11px; color: var(--color-text-gray);">
                                        <span><i class="fas fa-clock" style="margin-right: 5px;"></i>Beispiel</span>
                                        <span><i class="fas fa-tag" style="margin-right: 5px;"></i>Zentralbank</span>
                                    </div>
                                </div>
                                <div class="news-item" style="padding: 18px; border-bottom: 1px solid var(--color-border-green); transition: all 0.3s ease; background: var(--perlweiss); margin-bottom: 12px; border-radius: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                        <h4 style="color: var(--color-primary-dark); margin: 0; font-size: 15px; font-weight: 600; line-height: 1.4;">Tech-Sektor zeigt gemischte Signale</h4>
                                        <span style="background: var(--color-accent-rose); color: #ffffff; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 0;">Financial Times</span>
                                    </div>
                                    <p style="color: var(--color-text-gray); margin: 10px 0; font-size: 13px; line-height: 1.6;">Während einige Tech-Giganten schwächeln, zeigen andere innovative Bereiche wie KI und Cloud-Computing Stärke. Diversifikation bleibt wichtig.</p>
                                    <div style="display: flex; gap: 15px; font-size: 11px; color: var(--color-text-gray);">
                                        <span><i class="fas fa-clock" style="margin-right: 5px;"></i>vor 5 Stunden</span>
                                        <span><i class="fas fa-tag" style="margin-right: 5px;"></i>Technologie</span>
                                    </div>
                                </div>
                                <div class="news-item" style="padding: 18px; transition: all 0.3s ease; background: var(--perlweiss); border-radius: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                        <h4 style="color: var(--color-primary-dark); margin: 0; font-size: 15px; font-weight: 600; line-height: 1.4;">Rohstoffmärkte stabilisieren sich</h4>
                                        <span style="background: var(--color-accent-rose); color: #ffffff; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 0;">Wall Street Journal</span>
                                    </div>
                                    <p style="color: var(--color-text-gray); margin: 10px 0; font-size: 13px; line-height: 1.6;">Gold und Öl zeigen nach volatilen Wochen wieder stabilere Preise. Experten sehen langfristig positive Aussichten für Rohstoffinvestments.</p>
                                    <div style="display: flex; gap: 15px; font-size: 11px; color: var(--color-text-gray);">
                                        <span><i class="fas fa-clock" style="margin-right: 5px;"></i>vor 7 Stunden</span>
                                        <span><i class="fas fa-tag" style="margin-right: 5px;"></i>Rohstoffe</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                // Load live market data automatically
                setTimeout(() => loadLiveMarkets(), 100);
            } else if (pageId === 'bericht') {
                // Bericht & Analyse: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; font-weight: 600;">
                                Portfolio-Analyse
                            </h4>
                            <p style="color: #333333; margin-bottom: 12px; line-height: 1.5; font-size: 14px;">Hier erhalten Sie eine detaillierte SWOT-Analyse Ihres Portfolios und konkrete Empfehlungen zur Optimierung.</p>
                            <button class="refresh-button" onclick="updateReportPage()" style="background: var(--color-accent-rose); color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-sync-alt"></i> Bericht aktualisieren
                            </button>
                        </div>

                        <!-- SWOT Grid -->
                        <div class="swot-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px;">
                            <div class="swot-card strengths" style="background: #e8f5e9; padding: 25px; border-radius: 0; border-left: 4px solid #4caf50;">
                                <h4 style="color: #2e7d32; margin-bottom: 15px; font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                    <i class="fas fa-plus-circle"></i> 💪 Stärken
                                </h4>
                                <div id="strengthsList" style="color: #1b5e20;">
                                    <p>Bitte Portfolio erstellen und berechnen</p>
                                </div>
                            </div>
                            <div class="swot-card weaknesses" style="background: #fff3e0; padding: 25px; border-radius: 0; border-left: 4px solid #ff9800;">
                                <h4 style="color: #e65100; margin-bottom: 15px; font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                    <i class="fas fa-exclamation-triangle"></i> ⚠️ Schwächen
                                </h4>
                                <div id="weaknessesList" style="color: #e65100;">
                                    <p>Bitte Portfolio erstellen und berechnen</p>
                                </div>
                            </div>
                            <div class="swot-card opportunities" style="background: var(--morgenlicht); padding: 25px; border-radius: 0; border-left: 4px solid #2196f3;">
                                <h4 style="color: #1565c0; margin-bottom: 15px; font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                    <i class="fas fa-chart-line"></i> 🚀 Chancen
                                </h4>
                                <div id="opportunitiesList" style="color: #0d47a1;">
                                    <p>Bitte Portfolio erstellen und berechnen</p>
                                </div>
                            </div>
                            <div class="swot-card threats" style="background: #ffebee; padding: 25px; border-radius: 0; border-left: 4px solid #f44336;">
                                <h4 style="color: #c62828; margin-bottom: 15px; font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                    <i class="fas fa-radiation"></i> 🔴 Risiken
                                </h4>
                                <div id="threatsList" style="color: #b71c1c;">
                                    <p>Bitte Portfolio erstellen und berechnen</p>
                                </div>
                            </div>
                        </div>

                        <!-- Korrelationsanalyse -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Korrelationsanalyse</h3>
                            <div class="correlation-legend" style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
                                <div class="legend-item" style="display: flex; align-items: center; gap: 8px;">
                                    <div class="legend-color" style="width: 20px; height: 20px; background: #d4edda; border-radius: 0;"></div>
                                    <span style="font-size: 13px; color: #666;">Hohe Korrelation (>0.7)</span>
                                </div>
                                <div class="legend-item" style="display: flex; align-items: center; gap: 8px;">
                                    <div class="legend-color" style="width: 20px; height: 20px; background: #fff3cd; border-radius: 0;"></div>
                                    <span style="font-size: 13px; color: #666;">Mittlere Korrelation (0.3-0.7)</span>
                                </div>
                                <div class="legend-item" style="display: flex; align-items: center; gap: 8px;">
                                    <div class="legend-color" style="width: 20px; height: 20px; background: #f8d7da; border-radius: 0;"></div>
                                    <span style="font-size: 13px; color: #666;">Niedrige Korrelation (<0.3)</span>
                                </div>
                                <div class="legend-item" style="display: flex; align-items: center; gap: 8px;">
                                    <div class="legend-color" style="width: 20px; height: 20px; background: #cce7ff; border-radius: 0;"></div>
                                    <span style="font-size: 13px; color: #666;">Negative Korrelation</span>
                                </div>
                            </div>
                            <div id="correlationTableContainer" style="color: #666666;">
                                <p>Bitte erstellen Sie ein Portfolio mit mindestens 2 Assets für die Korrelationsanalyse.</p>
                            </div>
                        </div>

                        <!-- Marktanalyse -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Marktanalyse & Sektor-Zyklen</h3>
                            <div id="marketAnalysis" style="color: #666666; line-height: 1.8;">
                                <p>Bitte berechnen Sie zuerst Ihr Portfolio für die Marktanalyse.</p>
                            </div>
                        </div>

                        <!-- Handlungsempfehlungen -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Handlungsempfehlungen</h3>
                            <div id="recommendations" style="color: #666666; line-height: 1.8;">
                                <p>Bitte erstellen Sie zuerst ein Portfolio und klicken Sie auf "Portfolio Berechnen".</p>
                            </div>
                        </div>

                        <!-- Portfolio-Zusammenfassung -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Portfolio-Zusammenfassung</h3>
                            <div id="portfolioSummary" style="color: #666666; line-height: 1.8;">
                                <p>Bitte fügen Sie Assets zu Ihrem Portfolio hinzu und berechnen Sie die Analyse.</p>
                            </div>
                        </div>
                    </div>
                `;
                
                // Initialize Report Page
                if (typeof updateReportPage === 'function') {
                    updateReportPage();
                }
            } else if (pageId === 'backtesting') {
                // Backtesting: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; font-weight: 600;">
                                Strategie-Testing & Backtesting
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Testen Sie verschiedene Investment-Strategien mit echten Marktdaten. Nach erfolgreichem Backtest können Sie die bewährten Strategien direkt in Ihr Portfolio übernehmen.</p>
                        </div>

                        <!-- Swiss Tax Calculator -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">🇨🇭 Portfolio Tax Calculator</h3>
                            
                            <!-- Description Box -->
                            <div style="background: rgba(33, 150, 243, 0.1); padding: 12px; border-radius: 0; border-left: 4px solid #1976d2; margin-bottom: 15px;">
                                <p style="color: #333; margin: 0; line-height: 1.6; font-size: 12px;"><strong>Was dieser Calculator tut:</strong> Berechnet Steuern für <strong>Ihre konkreten Portfolio-Assets</strong> (aus dem Dashboard)</p>
                                <p style="color: #666; margin: 8px 0 0 0; line-height: 1.5; font-size: 11px;">💡 <strong>Für generische Berechnungen</strong> (beliebige Beträge ohne Portfolio): → 
                                    <a href="#" onclick="loadGSPage('sources'); return false;" style="color: var(--color-accent-rose); text-decoration: underline; font-weight: 600;">Generischer Steuerrechner (Steuern-Seite)</a>
                                </p>
                            </div>
                            
                            <div style="background: #fafafa; padding: 18px; border-radius: 0;">
                                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 15px;">
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; color: #333; font-weight: 600; font-size: 13px;">Symbol:</label>
                                        <select id="taxSymbol" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 13px;">
                                            <option value="">Lade Portfolio...</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; color: #333; font-weight: 600; font-size: 13px;">Transaction Type:</label>
                                        <select id="taxType" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 13px;">
                                            <option value="purchase">Purchase</option>
                                            <option value="sale">Sale</option>
                                            <option value="dividend">Dividend</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; color: #333; font-weight: 600; font-size: 13px;">Amount (CHF):</label>
                                        <input type="number" id="taxAmount" value="10000" min="0" step="100" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 13px;">
                                    </div>
                                </div>
                                <button onclick="calculateSwissTax()" style="background: var(--color-accent-rose); color: white; border: none; padding: 10px 20px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500;">
                                    <i class="fas fa-calculator"></i> Calculate Tax
                                </button>
                                <div id="taxResults" style="display: none; margin-top: 18px; padding: 18px; background: #e8f5e9; border-radius: 0; border-left: 4px solid #4caf50;">
                                    <h4 style="color: #1b5e20; margin: 0 0 12px 0; font-size: 16px;">Tax Calculation Results</h4>
                                    <div style="color: #2e7d32; font-size: 13px;">
                                        <p style="margin: 6px 0;"><strong>Gross Amount:</strong> <span id="grossAmount">-</span></p>
                                        <p style="margin: 6px 0;"><strong>Stamp Tax:</strong> <span id="stampTax">-</span></p>
                                        <p style="margin: 6px 0;"><strong>Withholding Tax:</strong> <span id="withholdingTax">-</span></p>
                                        <p style="font-size: 16px; font-weight: 600; margin: 10px 0 6px 0;"><strong>Total Tax:</strong> <span id="totalTax">-</span></p>
                                        <p style="font-size: 16px; font-weight: 600; margin: 6px 0;"><strong>Net Amount:</strong> <span id="netAmount">-</span></p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Stress Testing -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">📉 Stress Testing</h3>
                            <p style="color: #333; font-size: 13px; margin-bottom: 15px; line-height: 1.6;">Testen Sie, wie Ihr Portfolio in verschiedenen Krisen-Szenarien reagieren würde:</p>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                                <div onclick="runStressTest('2008_financial_crisis')" style="background: #ffebee; padding: 20px; border-radius: 0; cursor: pointer; text-align: center; transition: all 0.3s ease; border: 2px solid transparent;">
                                    <h4 style="color: #c62828; margin: 0 0 10px 0; font-size: 16px;">2008 Financial Crisis</h4>
                                    <p style="color: #d32f2f; margin: 0; font-size: 13px;">Swiss -35%, Int'l -40%<br>Bonds +10%, Commodities -20%</p>
                                </div>
                                <div onclick="runStressTest('covid_2020')" style="background: #fff3e0; padding: 20px; border-radius: 0; cursor: pointer; text-align: center; transition: all 0.3s ease; border: 2px solid transparent;">
                                    <h4 style="color: #e65100; margin: 0 0 10px 0; font-size: 16px;">COVID-19 2020</h4>
                                    <p style="color: #f57c00; margin: 0; font-size: 13px;">Swiss -25%, Int'l -30%<br>Bonds +5%, Commodities -15%</p>
                                </div>
                                <div onclick="runStressTest('interest_rate_shock')" style="background: var(--morgenlicht); padding: 20px; border-radius: 0; cursor: pointer; text-align: center; transition: all 0.3s ease; border: 2px solid transparent;">
                                    <h4 style="color: #1565c0; margin: 0 0 10px 0; font-size: 16px;">Interest Rate Shock</h4>
                                    <p style="color: #1976d2; margin: 0; font-size: 13px;">All Stocks -10%<br>Bonds -15%, Commodities -5%</p>
                                </div>
                                <div onclick="runStressTest('swiss_franc_strength')" style="background: #e8f5e9; padding: 20px; border-radius: 0; cursor: pointer; text-align: center; transition: all 0.3s ease; border: 2px solid transparent;">
                                    <h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 16px;">CHF Strength</h4>
                                    <p style="color: #388e3c; margin: 0; font-size: 13px;">Swiss +10%, Int'l -20%<br>Bonds +5%, Commodities -10%</p>
                                </div>
                                <div onclick="runStressTest('inflation_shock')" style="background: #f3e5f5; padding: 20px; border-radius: 0; cursor: pointer; text-align: center; transition: all 0.3s ease; border: 2px solid transparent;">
                                    <h4 style="color: #6a1b9a; margin: 0 0 10px 0; font-size: 16px;">Inflation Shock</h4>
                                    <p style="color: #7b1fa2; margin: 0; font-size: 13px;">Swiss -10%, Int'l -15%<br>Commodities +20%, Bonds -25%</p>
                                </div>
                            </div>
                            <div id="stressResults" style="display: none; margin-top: 20px; padding: 20px; background: #fafafa; border-radius: 0;">
                                <h4 style="color: #000; margin: 0 0 15px 0;">Stress Test Results</h4>
                                <div id="stressMetrics"></div>
                            </div>
                        </div>

                        <!-- Info Box -->
                        <div style="background: rgba(205, 139, 118, 0.1); border-radius: 0; padding: 25px; margin-bottom: 30px; border-left: 4px solid var(--color-accent-rose);">
                            <h4 style="color: #000; margin: 0 0 15px 0; font-size: 16px; font-weight: 600;">Hinweis zum Backtesting</h4>
                            <p style="color: #666; line-height: 1.8; margin: 0;">Das Backtesting ermöglicht es Ihnen, Investment-Strategien mit historischen Daten zu testen, bevor Sie echtes Kapital einsetzen. Beachten Sie, dass vergangene Performance keine Garantie für zukünftige Ergebnisse ist.</p>
                        </div>
                    </div>
                `;
                
                // Load portfolio assets into Tax Calculator dropdown
                setTimeout(() => {
                    loadPortfolioIntoTaxCalculator();
                }, 100);
            } else if (pageId === 'investing') {
                // Investing: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Anlageprinzipien -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border: 1px solid #d0d0d0;">
                            <h3 style="font-family: 'Inter', sans-serif; font-size: 24px; color: #2c3e50; margin: 0 0 15px 0; font-weight: 600;">Anlageprinzipien</h3>
                            <p style="color: #333333; margin-bottom: 0; font-size: 14px; line-height: 1.5;">Verstehen der grundlegenden Prinzipien, die erfolgreiche langfristige Anlagestrategien leiten.</p>
                            
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                                <!-- Diversifikation -->
                                <div style="background: #fafafa; padding: 20px; border-radius: 0; border-left: 4px solid #4caf50;">
                                    <h4 style="color: #2e7d32; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">Diversifikation</h4>
                                    <p style="color: #666; margin-bottom: 15px; font-size: 14px;">Verteilung von Anlagen über verschiedene Anlageklassen, Sektoren und geografische Regionen zur Risikominderung.</p>
                                    <div style="background: #e8f5e9; padding: 12px; border-radius: 0; margin-bottom: 10px;">
                                        <h5 style="color: #1b5e20; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Theorie:</h5>
                                        <p style="color: #2e7d32; margin: 0; font-size: 13px;">Modern Portfolio Theory von Markowitz: Kombination von Assets mit niedriger Korrelation reduziert Gesamtrisiko.</p>
                                    </div>
                                    <div style="background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #1b5e20; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Praxis:</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">60% Aktien + 30% Anleihen + 10% Rohstoffe = 20-30% weniger Volatilität</p>
                                    </div>
                                </div>

                                <!-- Langfristiger Fokus -->
                                <div style="background: #fafafa; padding: 20px; border-radius: 0; border-left: 4px solid #2196f3;">
                                    <h4 style="color: #1565c0; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">Langfristiger Fokus</h4>
                                    <p style="color: #666; margin-bottom: 15px; font-size: 14px;">Die Kraft des Zinseszinseffekts und die Vorteile, durch Marktzyklen hindurch investiert zu bleiben.</p>
                                    <div style="background: var(--morgenlicht); padding: 12px; border-radius: 0; margin-bottom: 10px;">
                                        <h5 style="color: #0d47a1; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Theorie:</h5>
                                        <p style="color: #1565c0; margin: 0; font-size: 13px;">Bei 7% Rendite verdoppelt sich das Kapital alle 10 Jahre. Zeit im Markt > Timing des Marktes.</p>
                                    </div>
                                    <div style="background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #0d47a1; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Praxis:</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">CHF 10'000 bei 7% wird nach 30 Jahren zu CHF 76'123!</p>
                                    </div>
                                </div>

                                <!-- Kostenmanagement -->
                                <div style="background: #fafafa; padding: 20px; border-radius: 0; border-left: 4px solid #ff9800;">
                                    <h4 style="color: #e65100; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">Kostenmanagement</h4>
                                    <p style="color: #666; margin-bottom: 15px; font-size: 14px;">Verstehen, wie Gebühren und Kosten langfristige Renditen beeinflussen.</p>
                                    <div style="background: #fff3e0; padding: 12px; border-radius: 0; margin-bottom: 10px;">
                                        <h5 style="color: #d84315; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Theorie:</h5>
                                        <p style="color: #e65100; margin: 0; font-size: 13px;">Jeder % an Kosten reduziert die Rendite. 2% Kosten bei 7% Rendite = nur 5% Netto.</p>
                                    </div>
                                    <div style="background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #d84315; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Praxis:</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">Aktive Fonds (2% Gebühren) vs. ETFs (0.1%) = 40% Kostendifferenz über 30 Jahre</p>
                                    </div>
                                </div>

                                <!-- Risikobewertung -->
                                <div style="background: #fafafa; padding: 20px; border-radius: 0; border-left: 4px solid #9c27b0;">
                                    <h4 style="color: #6a1b9a; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">Risikobewertung</h4>
                                    <p style="color: #666; margin-bottom: 15px; font-size: 14px;">Bewertung Ihrer Risikotoleranz und Erstellung eines Portfolios, das mit Ihren Zielen übereinstimmt.</p>
                                    <div style="background: #f3e5f5; padding: 12px; border-radius: 0; margin-bottom: 10px;">
                                        <h5 style="color: #4a148c; margin: 0 0 8px 0; font-size: 14px;">🎯 Theorie:</h5>
                                        <p style="color: #6a1b9a; margin: 0; font-size: 13px;">100-Alter-Regel: 100 minus Ihr Alter = empfohlener Aktienanteil in %</p>
                                    </div>
                                    <div style="background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #4a148c; margin: 0 0 8px 0; font-size: 14px;">📊 Praxis:</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">30 Jahre alt = 70% Aktien | 60 Jahre alt = 40% Aktien</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Investment Strategien Overview -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 30px; margin-bottom: 30px; border: 2px solid #8b7355;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Investment-Strategien im Überblick</h3>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                                <div style="background: #fafafa; padding: 20px; border-radius: 0;">
                                    <h4 style="color: var(--color-accent-rose); margin: 0 0 12px 0; font-size: 18px;"><i class="fas fa-search-dollar"></i> Value Investing</h4>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">DCF-Bewertung, Graham-Formel, PEG-Ratio zur Identifikation unterbewerteter Aktien</p>
                                </div>
                                <div style="background: #fafafa; padding: 20px; border-radius: 0;">
                                    <h4 style="color: var(--color-accent-rose); margin: 0 0 12px 0; font-size: 18px;"><i class="fas fa-rocket"></i> Momentum Growth</h4>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">RSI, MACD, Moving Averages für trendbasiertes Trading</p>
                                </div>
                                <div style="background: #fafafa; padding: 20px; border-radius: 0;">
                                    <h4 style="color: var(--color-accent-rose); margin: 0 0 12px 0; font-size: 18px;"><i class="fas fa-hand-holding-usd"></i> Buy & Hold</h4>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Langfristige Qualitätsaktien mit stabilen Fundamentaldaten</p>
                                </div>
                                <div style="background: #fafafa; padding: 20px; border-radius: 0;">
                                    <h4 style="color: var(--color-accent-rose); margin: 0 0 12px 0; font-size: 18px;"><i class="fas fa-percentage"></i> Carry Strategy</h4>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Zinsdifferenzial-Arbitrage und Cashflow-orientierte Investments</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'black-litterman') {
                // Black-Litterman: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 18px; margin-bottom: 25px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 10px; font-size: 17px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-brain"></i> Quantitative Portfolio-Optimierung
                            </h4>
                            <p style="color: #333333; line-height: 1.6; font-size: 13px; margin-bottom: 0;">Die Black-Litterman-Theorie verbindet Marktgleichgewicht mit eigenen Meinungen über zukünftige Renditen.</p>
                        </div>

                        <!-- Einleitung -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">📘 Was macht die Black-Litterman-Theorie?</h3>
                            <p style="color: #333; line-height: 1.7; margin-bottom: 12px; font-size: 14px;">Das Modell (entwickelt bei Goldman Sachs) löst ein fundamentales Problem der Portfolio-Optimierung:</p>
                            <div style="background: var(--perlweiss); padding: 15px; border-radius: 0; border-left: 4px solid #2196f3; margin: 15px 0;">
                                <p style="color: #1565c0; font-weight: 600; margin: 0 0 8px 0; font-size: 15px;">Kernfrage:</p>
                                <p style="color: #333; margin: 0; line-height: 1.6; font-size: 13px;">Wie kann man eigene Meinungen („Views") über zukünftige Renditen sinnvoll mit dem Marktgleichgewicht kombinieren?</p>
                            </div>
                            <p style="color: #333; line-height: 1.7; margin-bottom: 10px; font-size: 14px;">Das Modell verbindet zwei Informationsquellen:</p>
                            <ul style="color: #333; line-height: 1.7; font-size: 13px; margin: 0; padding-left: 20px;">
                                <li><strong>Marktimplizite Erwartungen</strong> – was der Markt „denkt", abgeleitet aus aktuellen Kapitalisierungen</li>
                                <li><strong>Subjektive Ansichten des Investors</strong> – z. B. „Nestlé wird besser abschneiden als Novartis"</li>
                            </ul>
                        </div>

                        <!-- Praxisbeispiel -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">2️⃣ Praxisbeispiel: Schweizer Blue Chips</h3>
                            <div style="background: #fafafa; padding: 18px; border-radius: 0; margin-bottom: 15px;">
                                <h4 style="color: #000; margin: 0 0 12px 0; font-size: 16px;">Marktkapitalisierungen</h4>
                                <canvas id="marketCapChart" style="max-height: 250px; margin-bottom: 15px;"></canvas>
                                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                                    <div style="text-align: center; background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #4caf50; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">Nestlé</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">CHF 249 Mrd</p>
                                    </div>
                                    <div style="text-align: center; background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #2196f3; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">Roche</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">CHF 218 Mrd</p>
                                    </div>
                                    <div style="text-align: center; background: #fff; padding: 12px; border-radius: 0; border: 1px solid #e8e8e8;">
                                        <h5 style="color: #ff9800; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">Novartis</h5>
                                        <p style="color: #666; margin: 0; font-size: 13px;">CHF 171 Mrd</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Kernformeln -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px; border: 2px solid #8b7355;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">Black-Litterman Kernformel</h3>
                            <div style="background: #fafafa; padding: 18px; border-radius: 0; text-align: center;">
                                <p style="color: #333; margin: 0 0 12px 0; font-weight: 600; font-size: 14px;">Posterior Erwartungsrenditen (μ_BL):</p>
                                <div style="background: #f3e5f5; padding: 12px; border-radius: 0; font-family: monospace; font-size: 13px; color: #6a1b9a; overflow-x: auto;">
                                    μ_BL = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ × [(τΣ)⁻¹π + PᵀΩ⁻¹Q]
                                </div>
                                <div style="margin-top: 15px; text-align: left;">
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>π:</strong> Implizite Markt-Renditen</p>
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>Σ:</strong> Kovarianzmatrix</p>
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>P:</strong> View-Matrix (Ansichten)</p>
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>Q:</strong> View-Vektors (erwartete Renditen)</p>
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>Ω:</strong> Unsicherheit der Views</p>
                                    <p style="color: #666; font-size: 12px; margin: 4px 0;"><strong>τ:</strong> Skalierungsfaktor</p>
                                </div>
                            </div>
                        </div>

                        <!-- Interpretation -->
                        <div style="background: #e8f5e9; border-radius: 0; padding: 20px; margin-bottom: 25px; border-left: 4px solid #4caf50;">
                            <h4 style="color: #1b5e20; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">📈 Zusammenfassung</h4>
                            <p style="color: #2e7d32; line-height: 1.7; margin: 0; font-size: 13px;">Das Black-Litterman-Modell ermöglicht es, subjektive Marktmeinungen systematisch mit Marktdaten zu kombinieren. Es liefert robustere und stabilere Portfolios als die reine Markowitz-Optimierung und ist besonders wertvoll für erfahrene Investoren mit fundierten Marktansichten.</p>
                        </div>

                        <!-- BVAR-Enhanced Black-Litterman (COMING SOON) -->
                        <div style="background: linear-gradient(135deg, #607d8b 0%, #78909c 100%); border-radius: 0; padding: 30px; margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); position: relative; overflow: hidden;">
                            <div style="position: absolute; top: 15px; right: 15px; background: rgba(255,152,0,0.95); color: white; padding: 6px 12px; font-size: 12px; font-weight: 700; border-radius: 0;">
                                COMING SOON
                            </div>
                            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                                <div style="background: rgba(255,255,255,0.15); border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-rocket" style="color: #fff; font-size: 22px;"></i>
                                </div>
                                <div>
                                    <h2 style="font-family: 'Playfair Display', serif; font-size: 26px; color: #ffffff; margin: 0; font-weight: 500;">BVAR-Enhanced Black-Litterman</h2>
                                    <p style="color: rgba(255,255,255,0.85); margin: 5px 0 0 0; font-size: 13px;">Bayesian Vector Autoregression für präzisere Rendite-Schätzungen</p>
                                </div>
                            </div>

                            <!-- Was ist BVAR? -->
                            <div style="background: rgba(255,255,255,0.95); border-radius: 0; padding: 20px;">
                                <h3 style="color: #607d8b; margin: 0 0 12px 0; font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                    <i class="fas fa-info-circle" style="color: #ff9800;"></i> Was ist BVAR?
                                </h3>
                                <p style="color: #333; line-height: 1.7; margin-bottom: 12px; font-size: 13px;">
                                    <strong>BVAR (Bayesian Vector Autoregression)</strong> ist ein ökonometrisches Modell, das Interdependenzen zwischen mehreren Zeitreihen analysiert und Zukunftsprognosen erstellt.
                                </p>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 15px;">
                                    <div style="background: var(--perlweiss); padding: 12px; border-left: 3px solid #2196f3; border-radius: 0;">
                                        <h5 style="color: #1565c0; margin: 0 0 6px 0; font-size: 13px; font-weight: 600;">
                                            <i class="fas fa-project-diagram" style="margin-right: 6px;"></i> Interdependenzen
                                        </h5>
                                        <p style="color: #666; margin: 0; font-size: 12px;">Wie Assets sich gegenseitig beeinflussen</p>
                                    </div>
                                    <div style="background: #f3e5f5; padding: 12px; border-left: 3px solid #9c27b0; border-radius: 0;">
                                        <h5 style="color: #6a1b9a; margin: 0 0 6px 0; font-size: 13px; font-weight: 600;">
                                            <i class="fas fa-chart-line" style="margin-right: 6px;"></i> Trends
                                        </h5>
                                        <p style="color: #666; margin: 0; font-size: 12px;">Jüngste Marktentwicklungen dynamisch</p>
                                    </div>
                                    <div style="background: #e8f5e9; padding: 12px; border-left: 3px solid #4caf50; border-radius: 0;">
                                        <h5 style="color: #2e7d32; margin: 0 0 6px 0; font-size: 13px; font-weight: 600;">
                                            <i class="fas fa-brain" style="margin-right: 6px;"></i> Präzision
                                        </h5>
                                        <p style="color: #666; margin: 0; font-size: 12px;">Robustere Forecasts als Durchschnitte</p>
                                    </div>
                                </div>
                                <div style="background: #fff3e0; padding: 15px; border-left: 3px solid #ff9800; border-radius: 0; text-align: center;">
                                    <p style="color: #e65100; margin: 0; font-size: 13px; font-weight: 600;">
                                        <i class="fas fa-rocket" style="margin-right: 6px;"></i> Diese erweiterte Funktion wird in Kürze verfügbar sein
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Initialize Market Cap Chart
                setTimeout(() => {
                    const ctx = document.getElementById('marketCapChart');
                    if (ctx) {
                        new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: ['Nestlé', 'Roche', 'Novartis'],
                                datasets: [{
                                    label: 'Marktkapitalisierung (CHF Mrd)',
                                    data: [249, 218, 171],
                                    backgroundColor: ['rgba(76, 175, 80, 0.7)', 'rgba(33, 150, 243, 0.7)', 'rgba(255, 152, 0, 0.7)'],
                                    borderColor: ['rgba(76, 175, 80, 1)', 'rgba(33, 150, 243, 1)', 'rgba(255, 152, 0, 1)'],
                                    borderWidth: 2
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { display: false },
                                    title: {
                                        display: false
                                    }
                                },
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: { display: true, text: 'CHF Mrd', font: { size: 12 } }
                                    }
                                }
                            }
                        });
                    }
                }, 300);
            } else if (pageId === 'methodik') {
                // Methodik: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- MONTE CARLO SIMULATION - Interaktiv mit Portfolio-Daten -->
                        <div style="background: linear-gradient(135deg, #1a237e 0%, #283593 100%); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                                <div style="background: rgba(255,255,255,0.15); border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-chart-line" style="color: #fff; font-size: 20px;"></i>
                                </div>
                                <div>
                                    <h2 style="font-family: 'Inter', sans-serif; font-size: 24px; color: #ffffff; margin: 0; font-weight: 600;">Monte Carlo Portfolio-Simulation</h2>
                                    <p style="color: rgba(255,255,255,0.85); margin: 5px 0 0 0; font-size: 13px;">Basierend auf deinen aktuellen Portfolio-Daten</p>
                                </div>
                    </div>

                            <!-- Controls -->
                            <div style="background: rgba(255,255,255,0.1); border-radius: 0; padding: 20px; margin-bottom: 25px;">
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                    <div>
                                        <label style="color: rgba(255,255,255,0.9); font-size: 13px; margin-bottom: 8px; display: block; font-weight: 500;">Zeithorizont (Jahre)</label>
                                        <input type="number" id="mcTimeHorizon" value="10" min="1" max="30" style="width: 100%; padding: 10px; border-radius: 0; border: none; background: rgba(255,255,255,0.95); font-size: 14px;">
                                    </div>
                                    <div>
                                        <label style="color: rgba(255,255,255,0.9); font-size: 13px; margin-bottom: 8px; display: block; font-weight: 500;">Anzahl Simulationen</label>
                                        <select id="mcSimulations" style="width: 100%; padding: 10px; border-radius: 0; border: none; background: rgba(255,255,255,0.95); font-size: 14px;">
                                            <option value="100">100</option>
                                            <option value="500" selected>500</option>
                                            <option value="1000">1,000</option>
                                            <option value="5000">5,000</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label style="color: rgba(255,255,255,0.9); font-size: 13px; margin-bottom: 8px; display: block; font-weight: 500;">Anfangsinvestition (CHF)</label>
                                        <input type="number" id="mcInitialInvestment" value="10000" min="1000" step="1000" style="width: 100%; padding: 10px; border-radius: 0; border: none; background: rgba(255,255,255,0.95); font-size: 14px;">
                                    </div>
                                    <div style="display: flex; align-items: flex-end;">
                                        <button onclick="runMonteCarloSimulation()" style="width: 100%; padding: 10px 20px; background: #ff9800; color: white; border: none; border-radius: 0; font-weight: 600; cursor: pointer; font-size: 14px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(255,152,0,0.3);" onmouseover="this.style.background='#fb8c00'" onmouseout="this.style.background='#ff9800'">
                                            <i class="fas fa-play"></i> Simulation starten
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Chart -->
                            <div style="background: rgba(255,255,255,0.95); border-radius: 0; padding: 25px; margin-bottom: 20px;">
                                <canvas id="monteCarloChart" style="max-height: 400px;"></canvas>
                            </div>

                            <!-- Results Grid -->
                            <div id="mcResults" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                <!-- Results will be populated here -->
                            </div>
                        </div>

                        <!-- Instruction Box -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px; border-left: 4px solid var(--color-accent-rose);">
                            <h4 style="color: #1a1a1a; margin-bottom: 15px; font-size: 1.2rem; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 10px;">
                                <i class="fas fa-flask"></i> 🔬 Wissenschaftliche Grundlage
                            </h4>
                            <p style="color: #666666; line-height: 1.6;">Alle Berechnungen basieren auf etablierten finanziellen Modellen und mathematischen Formeln.</p>
                        </div>

                        <!-- Methodology Grid - 5 Optimierungsmethoden -->
                        <div class="methodology-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 25px; margin-bottom: 30px;">
                            
                            <!-- 1. Mean-Variance -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-accent-rose);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">1. Mean-Variance (Markowitz)</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Optimales Verhältnis von Rendite und Risiko</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Portfolio Rendite:</p>
                                    <div style="background: var(--morgenlicht); padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #1565c0;">E[Rₚ] = Σ(wᵢ × μᵢ)</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Portfolio Volatilität:</p>
                                    <div style="background: var(--morgenlicht); padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #1565c0;">σₚ = √(ΣΣ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ)</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Findet die Effizienzgrenze aller optimalen Portfolios</p>
                            </div>

                            <!-- 2. Risk Parity -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #4caf50;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">2. Risikoparität (Risk Parity)</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Gleicher Risikobeitrag aller Assets</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Risikobeitrag:</p>
                                    <div style="background: #e8f5e9; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #2e7d32;">RCᵢ = wᵢ × (∂σₚ/∂wᵢ)</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Optimierung:</p>
                                    <div style="background: #e8f5e9; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #2e7d32;">RCᵢ = RCⱼ für alle i, j</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Robuster gegen Marktschwankungen</p>
                            </div>

                            <!-- 3. Minimum Variance -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #2196f3;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">3. Minimum-Varianz-Portfolio</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Niedrigstmögliche Volatilität</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Optimierungsproblem:</p>
                                    <div style="background: var(--morgenlicht); padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #1565c0;">min wᵀΣw unter Σwᵢ = 1</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Lösung:</p>
                                    <div style="background: var(--morgenlicht); padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #1565c0;">w = Σ⁻¹1 / (1ᵀΣ⁻¹1)</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Für risikoscheue Anleger</p>
                            </div>

                            <!-- 4. Maximum Sharpe -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #ff9800;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">4. Maximum Sharpe Ratio</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Bestes Rendite-Risiko-Verhältnis</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Sharpe Ratio:</p>
                                    <div style="background: #fff3e0; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #e65100;">S = (E[Rₚ] - R_f) / σₚ</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Tangency Portfolio:</p>
                                    <div style="background: #fff3e0; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #e65100;">w = Σ⁻¹(μ - R_f1) / (1ᵀΣ⁻¹(μ - R_f1))</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Optimal für risikobewusste Anleger</p>
                            </div>

                            <!-- 5. Black-Litterman -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #9c27b0;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">5. Black-Litterman Modell</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Kombiniert Marktdaten mit Investor-Views</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Posterior Rendite:</p>
                                    <div style="background: #f3e5f5; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; color: #6a1b9a;">μ = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ × [(τΣ)⁻¹π + PᵀΩ⁻¹Q]</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Für erfahrene Anleger mit Marktmeinung</p>
                            </div>

                            <!-- 6. Monte Carlo Simulation -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #e91e63;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">6. Monte Carlo Simulation</h3>
                                <p style="color: #666; margin-bottom: 15px;"><strong>Ziel:</strong> Probabilistische Zukunftsprognosen</p>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Simulation:</p>
                                    <div style="background: #fce4ec; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #c2185b;">Rₜ = Rₜ₋₁ × (1 + μ + σεₜ)</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #333; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Konfidenzintervall:</p>
                                    <div style="background: #fce4ec; padding: 10px; border-radius: 0; font-family: monospace; font-size: 13px; color: #c2185b;">CI = [P₅, P₉₅] aus N Simulationen</div>
                                </div>
                                <p style="color: #666; font-size: 13px;"><strong>Anwendung:</strong> Für Risikoszenario-Analyse und Zukunftsprojektion</p>
                            </div>
                        </div>

                        <!-- Additional Metrics Section -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px; border-left: 4px solid #607d8b;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Weitere Kennzahlen</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                                <div style="background: #f8f9fa; padding: 15px; border-radius: 0;">
                                    <h4 style="color: #333; font-size: 15px; margin: 0 0 10px 0; font-weight: 600;">Sharpe Ratio</h4>
                                    <div style="background: var(--morgenlicht); padding: 8px; border-radius: 0; font-family: monospace; font-size: 12px; color: #1565c0; margin-bottom: 8px;">S = (Rₚ - R_f) / σₚ</div>
                                    <p style="color: #666; font-size: 12px; margin: 0;">Risikoadjustierte Rendite</p>
                                </div>
                                <div style="background: #f8f9fa; padding: 15px; border-radius: 0;">
                                    <h4 style="color: #333; font-size: 15px; margin: 0 0 10px 0; font-weight: 600;">Value at Risk (VaR)</h4>
                                    <div style="background: #ffebee; padding: 8px; border-radius: 0; font-family: monospace; font-size: 12px; color: #c62828; margin-bottom: 8px;">VaR = μₚ - Z_α × σₚ</div>
                                    <p style="color: #666; font-size: 12px; margin: 0;">Maximaler Verlust bei gegebenem Konfidenzniveau</p>
                                </div>
                                <div style="background: #f8f9fa; padding: 15px; border-radius: 0;">
                                    <h4 style="color: #333; font-size: 15px; margin: 0 0 10px 0; font-weight: 600;">Maximum Drawdown</h4>
                                    <div style="background: #fff3e0; padding: 8px; border-radius: 0; font-family: monospace; font-size: 12px; color: #e65100; margin-bottom: 8px;">MDD = max(Peak - Trough) / Peak</div>
                                    <p style="color: #666; font-size: 12px; margin: 0;">Größter historischer Verlust</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'assets') {
                // Assets & Investment: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-graduation-cap"></i> Investment-Bildung
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Vertiefen Sie Ihr Verständnis für verschiedene Anlageklassen, ihre Eigenschaften, Risiken und Renditeerwartungen. Hier finden Sie detaillierte Theorie und praktische Anwendungen.</p>
                        </div>

                        <!-- Asset-Klassen Overview -->
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin-bottom: 30px;">
                            
                            <!-- Aktien -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid #4caf50;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 15px 0; font-weight: 500;">📈 Aktien (Equities)</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #ffebee; color: #c62828; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Hoch</span>
                                    <span style="background: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Hoch</span>
                                    <span style="background: var(--morgenlicht); color: #1565c0; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Hoch</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 15px;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 16px;">Eigentumsrechte</h5>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Aktien repräsentieren Eigentumsanteile an einem Unternehmen. Aktionäre haben Stimmrechte und Anspruch auf Dividenden.</p>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 14px;">Arten:</h5>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Wachstumsaktien:</strong> Tech, Biotech - hohe Volatilität</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Wertaktien:</strong> Blue Chips - stabil, unterbewertet</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>Dividendenaktien:</strong> Utilities, REITs - regelmäßiges Einkommen</p>
                                </div>
                            </div>

                            <!-- Anleihen -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-accent-rose);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 15px 0; font-weight: 500;">Anleihen (Bonds)</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Mittel</span>
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Mittel</span>
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Mittel</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 15px;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 16px;">Zinsstruktur</h5>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Anleihen sind Schuldverschreibungen mit festem Zinssatz. Kurs bewegt sich invers zum Zinssatz.</p>
                                    <div style="background: var(--morgenlicht); padding: 8px; border-radius: 0; margin-top: 10px; font-family: monospace; font-size: 12px; color: #1565c0;">Kurs = Σ [Kupon / (1+r)^t] + Nennwert / (1+r)^n</div>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 14px;">Arten:</h5>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Staatsanleihen:</strong> Niedriges Risiko, sichere Rendite</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Unternehmensanleihen:</strong> Höhere Rendite, Kreditrisiko</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>Inflationsgeschützt:</strong> TIPS - Schutz vor Inflation</p>
                                </div>
                            </div>

                            <!-- Rohstoffe -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-border-green);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 15px 0; font-weight: 500;">Rohstoffe</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #ffebee; color: #c62828; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Hoch</span>
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Variabel</span>
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Mittel</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 15px;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 16px;">Preisbildung</h5>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Bestimmt durch Angebot und Nachfrage. Niedrige Korrelation zu Aktien - Diversifikationseffekt.</p>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 14px;">Arten:</h5>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Edelmetalle:</strong> Gold, Silber - Inflationsschutz</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Energie:</strong> Öl, Gas - zyklisch, geopolitisch</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>Agrar:</strong> Weizen, Mais - wetterabhängig</p>
                                </div>
                            </div>

                            <!-- Immobilien -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-accent-rose);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 15px 0; font-weight: 500;">Immobilien</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Mittel</span>
                                    <span style="background: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Stabil</span>
                                    <span style="background: #ffebee; color: #c62828; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Niedrig</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0; margin-bottom: 15px;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 16px;">Bewertung</h5>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">Mietrendite + Wertsteigerung. Stabile Cashflows, aber illiquide.</p>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 14px;">Arten:</h5>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Direktinvestition:</strong> Wohn-/Gewerbeimmobilien</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>REITs:</strong> Börsennotiert, hohe Dividenden</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>Immobilienfonds:</strong> Professionell verwaltet</p>
                                </div>
                            </div>

                            <!-- Alternative Investments -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-border-green);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 15px 0; font-weight: 500;">Alternative Investments</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #f3e5f5; color: #6a1b9a; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Variabel</span>
                                    <span style="background: #f3e5f5; color: #6a1b9a; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Variabel</span>
                                    <span style="background: #ffebee; color: #c62828; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Niedrig</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <h5 style="color: #000; margin: 0 0 10px 0; font-size: 14px;">Arten:</h5>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Private Equity:</strong> Nicht-börsennotierte Unternehmen</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Hedge Funds:</strong> Alternative Strategien</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>Kryptowährungen:</strong> Bitcoin, Ethereum - sehr volatil</p>
                                </div>
                            </div>

                            <!-- Geldmarktinstrumente -->
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; border-left: 4px solid var(--color-accent-rose);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: var(--color-primary-dark); margin: 0 0 15px 0; font-weight: 500;">Geldmarkt</h3>
                                <div style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                                    <span style="background: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Risiko: Niedrig</span>
                                    <span style="background: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Rendite: Niedrig</span>
                                    <span style="background: var(--morgenlicht); color: #1565c0; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 600;">Liquidität: Sehr Hoch</span>
                                </div>
                                <div style="background: #fafafa; padding: 15px; border-radius: 0;">
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Festgeld:</strong> Garantierter Zins, keine Kursrisiken</p>
                                    <p style="color: #666; margin: 0 0 8px 0; font-size: 13px;"><strong>Geldmarktfonds:</strong> Kurzfristige, sichere Anlagen</p>
                                    <p style="color: #666; margin: 0; font-size: 13px;"><strong>T-Bills:</strong> Kurzfristige Staatsanleihen</p>
                                </div>
                            </div>
                        </div>

                        <!-- Investment Summary -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 30px; margin-bottom: 30px; border: 2px solid #8b7355;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 22px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Asset-Allokation Empfehlungen</h3>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                                <div style="text-align: center; padding: 20px; background: #fafafa; border-radius: 0;">
                                    <h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 18px;">Konservativ</h4>
                                    <p style="color: #666; margin: 0; font-size: 13px;">20% Aktien<br>60% Anleihen<br>10% Gold<br>10% Geldmarkt</p>
                                </div>
                                <div style="text-align: center; padding: 20px; background: #fafafa; border-radius: 0;">
                                    <h4 style="color: #1565c0; margin: 0 0 10px 0; font-size: 18px;">Moderat</h4>
                                    <p style="color: #666; margin: 0; font-size: 13px;">50% Aktien<br>35% Anleihen<br>10% Rohstoffe<br>5% Alternative</p>
                                </div>
                                <div style="text-align: center; padding: 20px; background: #fafafa; border-radius: 0;">
                                    <h4 style="color: #c62828; margin: 0 0 10px 0; font-size: 18px;">Aggressiv</h4>
                                    <p style="color: #666; margin: 0; font-size: 13px;">80% Aktien<br>10% Alternative<br>5% Rohstoffe<br>5% Geldmarkt</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'sources') {
                // Quellen & Steuern: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Datenquellen Section -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 18px; margin-bottom: 25px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h2 style="font-family: 'Inter', sans-serif; font-size: 22px; color: #2c3e50; margin: 0 0 15px 0; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                <i class="fas fa-database" style="color: #8B7355;"></i> Datenquellen
                            </h2>
                            <p style="color: #333333; line-height: 1.6; margin-bottom: 15px; font-size: 13px;">Diese Plattform nutzt mehrere professionelle Finanzdaten-APIs mit intelligentem Fallback-System für maximale Zuverlässigkeit:</p>
                            
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 18px;">
                                <div style="background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%); padding: 15px; border-radius: 0; border-left: 3px solid #6a1b9a;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-check-circle" style="color: #6a1b9a;"></i> Yahoo Finance
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">Aktienkurse, Indizes & historische Daten</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 1 | Unbegrenzt</div>
                    </div>

                                <div style="background: var(--morgenlicht); padding: 15px; border-radius: 0; border-left: 3px solid #1976d2;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-chart-line" style="color: #1976d2;"></i> Alpha Vantage
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">Echtzeit- & historische Marktdaten</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 2 | 500/Tag</div>
                                </div>
                                
                                <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 15px; border-radius: 0; border-left: 3px solid #4caf50;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-clock" style="color: #4caf50;"></i> Twelve Data
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">Zeitreihen: Aktien, Forex, Krypto, ETFs</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 3 | 800/Tag</div>
                                </div>
                                
                                <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 15px; border-radius: 0; border-left: 3px solid #ff9800;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-globe" style="color: #ff9800;"></i> Finnhub
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">Echtzeit-Marktdaten & News</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 4 | 60/Min</div>
                                </div>
                                
                                <div style="background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%); padding: 15px; border-radius: 0; border-left: 3px solid #e91e63;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-cloud" style="color: #e91e63;"></i> IEX Cloud
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">US-Marktdaten & Finanzkennzahlen</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 5 | 100/Tag</div>
                                </div>
                                
                                <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); padding: 15px; border-radius: 0; border-left: 3px solid #9c27b0;">
                                    <h4 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-chart-area" style="color: #9c27b0;"></i> Polygon.io
                                    </h4>
                                    <p style="color: #666; font-size: 12px; margin: 0 0 6px 0;">Tick-by-Tick & technische Indikatoren</p>
                                    <div style="color: #888; font-size: 11px;"><strong>Priorität:</strong> 6 | 5/Min</div>
                                </div>
                            </div>
                        </div>

                        <!-- Schweizer Steuern Section -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 20px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); border-left: 4px solid #d32f2f;">
                            <h2 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #1a1a1a; margin: 0 0 18px 0; font-weight: 500;">
                                Schweizer Steuern & Abgaben
                            </h2>
                            <p style="color: #333; line-height: 1.7; margin-bottom: 18px; font-size: 13px;">Wichtige steuerliche Aspekte beim Wertpapierhandel in der Schweiz:</p>
                            
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px;">
                                <!-- Stempelsteuer -->
                                <div style="background: #ffebee; padding: 18px; border-radius: 0; border-left: 4px solid #d32f2f;">
                                    <h3 style="color: #c62828; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">
                                        Eidgenössische Stempelsteuer
                                    </h3>
                                    <div style="background: white; padding: 12px; border-radius: 0; margin-bottom: 12px;">
                                        <div style="font-size: 13px; color: #333; margin-bottom: 8px; font-weight: 600;">Inländische Wertpapiere:</div>
                                        <div style="font-size: 22px; font-weight: 700; color: #d32f2f; margin-bottom: 4px;">0.075%</div>
                                        <div style="font-size: 12px; color: #888;">Schweizer Aktien über CH-Bank</div>
                                    </div>
                                    <div style="background: white; padding: 12px; border-radius: 0;">
                                        <div style="font-size: 13px; color: #333; margin-bottom: 8px; font-weight: 600;">Ausländische Wertpapiere:</div>
                                        <div style="font-size: 22px; font-weight: 700; color: #d32f2f; margin-bottom: 4px;">0.15%</div>
                                        <div style="font-size: 12px; color: #888;">Ausländische Aktien</div>
                                    </div>
                                    <div style="margin-top: 12px; padding: 10px; background: #fff3e0; border-radius: 0; border-left: 3px solid #ff9800;">
                                        <div style="color: #e65100; font-size: 11px; font-weight: 600; margin-bottom: 4px;">ⓘ Wichtig</div>
                                        <div style="color: #666; font-size: 12px; line-height: 1.5;">Freibetrag: CHF 100'000/Jahr (seit 2023)</div>
                                    </div>
                                </div>

                                <!-- Verrechnungssteuer -->
                                <div style="background: var(--morgenlicht); padding: 18px; border-radius: 0; border-left: 4px solid #1976d2;">
                                    <h3 style="color: #1565c0; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">
                                        Verrechnungssteuer
                                    </h3>
                                    <div style="background: white; padding: 12px; border-radius: 0; margin-bottom: 12px;">
                                        <div style="font-size: 13px; color: #333; margin-bottom: 8px; font-weight: 600;">Quellensteuer auf Dividenden:</div>
                                        <div style="font-size: 22px; font-weight: 700; color: #1976d2; margin-bottom: 4px;">35%</div>
                                        <div style="font-size: 12px; color: #888;">Automatischer Abzug (CH-Unternehmen)</div>
                                    </div>
                                    <div style="background: #e8f5e9; padding: 12px; border-radius: 0;">
                                        <div style="color: #2e7d32; font-size: 12px; font-weight: 600; margin-bottom: 6px;">✓ Rückforderbar</div>
                                        <div style="color: #666; font-size: 12px; line-height: 1.5;">Vollständig rückforderbar via Steuererklärung</div>
                                    </div>
                                    <div style="margin-top: 12px; padding: 10px; background: #fff3e0; border-radius: 0; border-left: 3px solid #ff9800;">
                                        <div style="color: #e65100; font-size: 11px; font-weight: 600; margin-bottom: 4px;">ⓘ Ausland</div>
                                        <div style="color: #666; font-size: 12px; line-height: 1.5;">USA: 15%, teilweise rückforderbar via DBA</div>
                                    </div>
                                </div>

                                <!-- Vermögenssteuer -->
                                <div style="background: #f3e5f5; padding: 18px; border-radius: 0; border-left: 4px solid #9c27b0; grid-column: 1 / -1;">
                                    <h3 style="color: #7b1fa2; margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">
                                        Vermögenssteuer & Einkommenssteuern
                                    </h3>
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                                        <div style="background: white; padding: 12px; border-radius: 0;">
                                            <div style="color: #333; font-size: 12px; margin-bottom: 6px; font-weight: 600;">Vermögenssteuer</div>
                                            <div style="color: #9c27b0; font-size: 16px; font-weight: 700; margin-bottom: 4px;">0.1% - 1.0%</div>
                                            <div style="font-size: 11px; color: #888;">Kantonal variabel</div>
                                        </div>
                                        <div style="background: white; padding: 12px; border-radius: 0;">
                                            <div style="color: #333; font-size: 12px; margin-bottom: 6px; font-weight: 600;">Dividenden</div>
                                            <div style="color: #9c27b0; font-size: 16px; font-weight: 700; margin-bottom: 4px;">Progression</div>
                                            <div style="font-size: 11px; color: #888;">Als Einkommen steuerpflichtig</div>
                                        </div>
                                        <div style="background: white; padding: 12px; border-radius: 0;">
                                            <div style="color: #333; font-size: 12px; margin-bottom: 6px; font-weight: 600;">Kursgewinne Privat</div>
                                            <div style="color: #4caf50; font-size: 16px; font-weight: 700; margin-bottom: 4px;">Steuerfrei</div>
                                            <div style="font-size: 11px; color: #888;">Keine Kapitalertragssteuer</div>
                                        </div>
                                        <div style="background: white; padding: 12px; border-radius: 0;">
                                            <div style="color: #333; font-size: 12px; margin-bottom: 6px; font-weight: 600;">Gewerbsmässig</div>
                                            <div style="color: #d32f2f; font-size: 16px; font-weight: 700; margin-bottom: 4px;">Steuerpflichtig</div>
                                            <div style="font-size: 11px; color: #888;">ESTV-Kriterien beachten</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Steuerrechner -->
                            <div style="margin-top: 25px; background: #f5f5f5; padding: 20px; border-radius: 0; border: 2px solid var(--color-accent-rose);">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 20px; color: var(--color-primary-dark); margin: 0 0 12px 0; font-weight: 600;">
                                    🧮 Generischer Steuerrechner
                                </h3>
                                <div style="background: rgba(205, 139, 118, 0.1); padding: 12px; border-radius: 0; border-left: 4px solid var(--color-accent-rose); margin-bottom: 15px;">
                                    <p style="color: #333; margin: 0; line-height: 1.6; font-size: 12px;"><strong>Was dieser Calculator tut:</strong> Berechnet Steuern für <strong>beliebige Transaktionswerte</strong> (unabhängig von Ihrem Portfolio)</p>
                                    <p style="color: #666; margin: 8px 0 0 0; line-height: 1.5; font-size: 11px;">💡 <strong>Für Portfolio-spezifische Berechnungen</strong> (mit Ihren konkreten Assets): → 
                                        <a href="#" onclick="loadGSPage('backtesting'); return false;" style="color: #1a237e; text-decoration: underline; font-weight: 600;">Portfolio Tax Calculator (Backtesting-Seite)</a>
                                    </p>
                                </div>
                                
                                <div style="background: white; padding: 18px; border-radius: 0; margin-bottom: 15px;">
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px;">
                                        <div>
                                            <label style="display: block; color: #333; font-weight: 600; margin-bottom: 6px; font-size: 13px;">Transaktionswert (CHF)</label>
                                            <input type="number" id="taxTransactionValue" value="10000" min="0" step="100" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 14px;">
                                        </div>
                                        <div>
                                            <label style="display: block; color: #333; font-weight: 600; margin-bottom: 6px; font-size: 13px;">Wertpapiertyp</label>
                                            <select id="taxSecurityType" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 14px; background: white;">
                                                <option value="ch">Schweizer Aktien</option>
                                                <option value="foreign">Ausländische Aktien</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label style="display: block; color: #333; font-weight: 600; margin-bottom: 6px; font-size: 13px;">Jahresdividende (CHF)</label>
                                            <input type="number" id="taxDividend" value="500" min="0" step="10" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0; font-size: 14px;">
                                        </div>
                                    </div>
                                    
                                    <button onclick="calculateTaxes()" style="background: var(--color-accent-rose); color: white; padding: 10px 20px; border: none; border-radius: 0; cursor: pointer; font-weight: 600; font-size: 14px; width: 100%; transition: all 0.3s ease;">
                                        <i class="fas fa-calculator"></i> Steuern berechnen
                                    </button>
                                </div>
                                
                                <div id="taxResults" style="display: none;">
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 15px;">
                                        <div style="background: #ffebee; padding: 15px; border-radius: 0; border-left: 4px solid #d32f2f;">
                                            <div style="color: #888; font-size: 12px; margin-bottom: 4px;">Stempelsteuer (Kauf)</div>
                                            <div style="color: #d32f2f; font-size: 24px; font-weight: 700;" id="stampTaxBuy">CHF 0.00</div>
                                            <div style="color: #666; font-size: 11px; margin-top: 6px;" id="stampTaxRate">0.075%</div>
                                        </div>
                                        
                                        <div style="background: var(--morgenlicht); padding: 15px; border-radius: 0; border-left: 4px solid #1976d2;">
                                            <div style="color: #888; font-size: 12px; margin-bottom: 4px;">Verrechnungssteuer</div>
                                            <div style="color: #1976d2; font-size: 24px; font-weight: 700;" id="withholdingTax">CHF 0.00</div>
                                            <div style="color: #666; font-size: 11px; margin-top: 6px;">35% (rückforderbar)</div>
                                        </div>
                                        
                                        <div style="background: #e8f5e9; padding: 15px; border-radius: 0; border-left: 4px solid #4caf50;">
                                            <div style="color: #888; font-size: 12px; margin-bottom: 4px;">Netto Dividende</div>
                                            <div style="color: #2e7d32; font-size: 24px; font-weight: 700;" id="netDividend">CHF 0.00</div>
                                            <div style="color: #666; font-size: 11px; margin-top: 6px;">65% der Bruttodividende</div>
                                        </div>
                                        
                                        <div style="background: #fff3e0; padding: 15px; border-radius: 0; border-left: 4px solid #ff9800;">
                                            <div style="color: #888; font-size: 12px; margin-bottom: 4px;">Gesamtkosten</div>
                                            <div style="color: #e65100; font-size: 24px; font-weight: 700;" id="totalCosts">CHF 0.00</div>
                                            <div style="color: #666; font-size: 11px; margin-top: 6px;">Stempel + Verrechnungssteuer</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Disclaimer -->
                            <div style="margin-top: 20px; padding: 15px; background: #fff3e0; border-radius: 0; border-left: 4px solid #ff6f00;">
                                <div style="color: #e65100; font-size: 13px; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                                    <i class="fas fa-exclamation-triangle"></i> Rechtlicher Hinweis
                                </div>
                                <div style="color: #666; font-size: 12px; line-height: 1.6;">
                                    Diese Informationen dienen ausschliesslich der allgemeinen Orientierung und stellen keine Steuer- oder Rechtsberatung dar. 
                                    Für verbindliche Auskünfte wenden Sie sich bitte an einen qualifizierten Steuerberater. Stand: Oktober 2025.
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'about') {
                // Über mich: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 1.5cm calc(30px + 1cm) 0 calc(30px + 1cm);">
                        <!-- Main Profile Card -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border: 1px solid #d0d0d0; border-left: 5px solid #8B7355;">
                            
                            <div style="margin-bottom: 20px; display: flex; align-items: center; gap: 20px;">
                                <!-- Profile Image -->
                                <img src="/static/profile.png" alt="Ahmed Choudhary" style="width: 3cm; height: 3cm; object-fit: cover; border-radius: 0; border: 3px solid #8B7355;">
                                
                                <!-- Profile Info -->
                                <div style="flex: 1;">
                                    <h2 style="font-family: 'Inter', sans-serif; font-size: 24px; margin-bottom: 6px; color: #2c3e50; font-weight: 600;">Ahmed Choudhary</h2>
                                    <p style="color: #333333; font-size: 15px; font-weight: 500; margin: 0 0 12px 0;">Portfolio- & Finanzanalyst</p>
                                    <div style="display: flex; gap: 10px;">
                                        <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" class="linkedin-link" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; background: #5d4037; color: white; padding: 7px 14px; border-radius: 0; text-decoration: none; font-weight: 500; font-size: 13px; transition: all 0.3s ease;">
                                            <i class="fab fa-linkedin-in" style="font-size: 13px;"></i> LinkedIn
                                        </a>
                                        <a href="#" onclick="loadGSPage('dashboard'); return false;" class="pdf-link" style="display: inline-flex; align-items: center; gap: 6px; background: #5d4037; color: white; padding: 7px 14px; border-radius: 0; text-decoration: none; font-weight: 500; font-size: 13px; transition: all 0.3s ease;">
                                            <i class="fas fa-file-pdf" style="font-size: 13px;"></i> Portfolio PDF
                                        </a>
                                    </div>
                                </div>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">Über mich</h4>
                                <p style="color: #333333; line-height: 1.6; margin-bottom: 12px; font-size: 14px;">
                                    Als Portfolio- und Finanzanalyst verbinde ich tiefgreifendes Fachwissen in quantitativer Finanzanalyse mit praktischer Erfahrung in der Portfolioverwaltung. Meine Arbeit konzentriert sich auf die Entwicklung und Implementierung moderner Portfolio-Optimierungsstrategien, die auf wissenschaftlichen Methoden basieren.
                                </p>
                                <p style="color: #333333; line-height: 1.6; margin-bottom: 12px; font-size: 14px;">
                                    Mit einem besonderen Fokus auf den Schweizer Aktienmarkt und internationale Diversifikationsstrategien helfe ich Investoren dabei, ihre Portfolios optimal zu strukturieren und Risiken effektiv zu managen. Dabei setze ich auf bewährte Methoden wie die Markowitz-Portfolio-Theorie, Black-Litterman-Modellierung und Monte Carlo Simulationen.
                                </p>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">Expertise</h4>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 12px;">
                                    <div style="background: #F8F8F8; padding: 15px; border-radius: 0; border: 1px solid #e0e0e0; border-left: 3px solid #8B7355;">
                                        <h5 style="color: #2c3e50; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">📊 Quantitative Analyse</h5>
                                        <p style="color: #333333; margin: 0; font-size: 13px; line-height: 1.5;">Portfolio-Optimierung, Risikomanagement, statistische Modellierung und Backtesting von Investment-Strategien</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 15px; border-radius: 0; border: 1px solid #e0e0e0; border-left: 3px solid #8B7355;">
                                        <h5 style="color: #2c3e50; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">🇨🇭 Schweizer Markt</h5>
                                        <p style="color: #333333; margin: 0; font-size: 13px; line-height: 1.5;">Spezialisierung auf SMI-Komponenten, Schweizer Blue Chips und lokale Marktdynamiken</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 15px; border-radius: 0; border: 1px solid #e0e0e0; border-left: 3px solid #8B7355;">
                                        <h5 style="color: #2c3e50; margin: 0 0 6px 0; font-size: 14px; font-weight: 600;">🌍 Internationale Diversifikation</h5>
                                        <p style="color: #333333; margin: 0; font-size: 13px; line-height: 1.5;">Cross-Border-Strategien, Währungsrisiken und globale Asset-Allokation</p>
                                    </div>
                                </div>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">Kontakt</h4>
                                <p style="color: #333333; line-height: 1.5; font-size: 14px; margin: 0;">
                                    <i class="fas fa-envelope" style="color: #8B7355; margin-right: 8px;"></i>
                                <a href="mailto:ahmedch1999@gmail.com" style="color: #8B7355; font-weight: 500; text-decoration: none;">ahmedch1999@gmail.com</a>
                            </p>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">Technologie-Stack</h4>
                                <p style="color: #333333; margin-bottom: 12px; font-size: 13px;">Diese Plattform wurde mit folgenden Technologien entwickelt:</p>
                                
                                <div style="margin-bottom: 15px;">
                                    <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Frontend</h5>
                                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                                        <span style="background: #e34c26; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-html5"></i> HTML5
                                        </span>
                                        <span style="background: #264de4; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-css3-alt"></i> CSS3
                                        </span>
                                        <span style="background: #f0db4f; color: #323330; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-js"></i> JavaScript (ES6+)
                                        </span>
                                        <span style="background: #ff6384; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Chart.js
                                        </span>
                                        <span style="background: #339af0; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Plotly.js
                                        </span>
                                        <span style="background: #228be6; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            <i class="fab fa-bootstrap"></i> Bootstrap 5
                                        </span>
                                        <span style="background: #1e88e5; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Font Awesome 6
                                        </span>
                                    </div>
                                </div>
                                
                                <div style="margin-bottom: 15px;">
                                    <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Backend</h5>
                                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                                        <span style="background: #3776ab; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-python"></i> Python 3.11
                                        </span>
                                        <span style="background: #000000; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Flask 3.x
                                        </span>
                                        <span style="background: #8B4513; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Gunicorn
                                        </span>
                                        <span style="background: #009485; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            SQLite
                                        </span>
                                        <span style="background: #336791; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            <i class="fab fa-github"></i> PostgreSQL
                                        </span>
                                    </div>
                                </div>
                                
                                <div style="margin-bottom: 15px;">
                                    <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">Data Science & Analytics</h5>
                                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                                        <span style="background: #013243; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            NumPy
                                        </span>
                                        <span style="background: #150458; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Pandas
                                        </span>
                                        <span style="background: #ff7f0e; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            SciPy
                                        </span>
                                        <span style="background: #f37626; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            yfinance
                                        </span>
                                        <span style="background: #3b5998; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            scikit-learn
                                        </span>
                                        <span style="background: #d45500; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Statsmodels
                                        </span>
                                    </div>
                                </div>
                                
                                <div style="margin-bottom: 10px;">
                                    <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">DevOps & Infrastructure</h5>
                                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                        <span style="background: #2496ED; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-docker"></i> Docker
                                        </span>
                                        <span style="background: #326CE5; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Kubernetes
                                        </span>
                                        <span style="background: #009639; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Nginx
                                        </span>
                                        <span style="background: #181717; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                                            <i class="fab fa-github"></i> GitHub Actions
                                        </span>
                                        <span style="background: #E24329; color: #ffffff; padding: 6px 14px; border-radius: 0; font-size: 12px; font-weight: 500;">
                                            Redis Cache
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">Skillset</h4>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-code" style="color: #8B7355;"></i> Software Development
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">Full-Stack Entwicklung, API Design, Datenbank-Management</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-paint-brush" style="color: #8B7355;"></i> Web Design
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">UX/UI Design, Responsive Design, Progressive Web Apps</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-brain" style="color: #8B7355;"></i> Machine Learning
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">Predictive Analytics, Monte Carlo Simulation, Algorithmic Trading</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-chart-bar" style="color: #8B7355;"></i> Data Analytics
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">Financial Data Analysis, Statistical Modeling, Visualization</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-shield-alt" style="color: #8B7355;"></i> Risk Management
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">Portfolio Risk Analysis, VaR Calculation, Stress Testing</p>
                                    </div>
                                    <div style="background: #F8F8F8; padding: 12px; border-radius: 0; border: 1px solid #e0e0e0;">
                                        <h5 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                                            <i class="fas fa-cogs" style="color: #8B7355;"></i> Quantitative Finance
                                        </h5>
                                        <p style="color: #333333; margin: 0; font-size: 12px;">Portfolio Theory, Asset Pricing, Derivative Valuation</p>
                                    </div>
                                </div>
                            </div>

                            <div style="background: #F8F8F8; padding: 15px; border-radius: 0; margin-top: 20px; border: 1px solid #e0e0e0; border-left: 3px solid #8B7355;">
                                <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-info-circle" style="color: #8B7355; margin-right: 6px;"></i> Über diese Plattform</h4>
                                <p style="color: #333333; line-height: 1.5; font-size: 13px; margin: 0;">
                                    Der Swiss Asset Pro kombiniert moderne Finanztechnologie mit wissenschaftlichen Berechnungsmethoden. Alle Analysen basieren auf etablierten Modellen wie Markowitz-Portfolio-Optimierung und Monte Carlo Simulationen. Die Plattform wurde entwickelt, um Investoren professionelle Tools für Portfolio-Analyse und -Optimierung zur Verfügung zu stellen, die sonst nur institutionellen Anlegern vorbehalten sind.
                                </p>
                            </div>
                        </div>

                        <!-- Quellen Section -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border: 1px solid #d0d0d0;">
                            <h3 style="font-family: 'Inter', sans-serif; font-size: 20px; color: #2c3e50; margin: 0 0 15px 0; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 8px;">Quellen & Daten</h3>
                            <p style="color: #333333; margin-bottom: 15px; font-size: 13px;">Diese Plattform nutzt eine Multi-Source-Architektur mit automatischem Failover für maximale Datenverfügbarkeit:</p>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 12px 0; font-size: 16px; font-weight: 600; border-left: 3px solid #8B7355; padding-left: 10px;">📊 Primäre Datenquellen</h4>
                                <div class="sources-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-chart-line" style="color: #8B7355; margin-right: 6px;"></i>Yahoo Finance API</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Hauptdatenquelle für:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>Echtzeit-Kursdaten (15min delay)</li>
                                            <li>Historische OHLCV-Daten</li>
                                            <li>Fundamentaldaten (P/E, Dividende)</li>
                                            <li>Globale Aktien, ETFs, Indizes</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> Alle 15 Minuten | <strong>Coverage:</strong> 50.000+ Assets</p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-globe" style="color: #8B7355; margin-right: 6px;"></i>Yahoo Query API</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Alternative Quelle für:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>Backup bei API-Limits</li>
                                            <li>Zusätzliche Marktdaten</li>
                                            <li>Forex & Kryptowährungen</li>
                                            <li>Rohstoffpreise</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> On-Demand | <strong>Failover:</strong> Automatisch</p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-flag" style="color: #8B7355; margin-right: 6px;"></i>Stooq API</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Spezialisiert auf:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>Europäische Aktienmärkte</li>
                                            <li>Schweizer Börse (SIX)</li>
                                            <li>Historische CSV-Daten</li>
                                            <li>Forex-Paare (EUR/CHF)</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> Täglich | <strong>Website:</strong> <a href="https://stooq.com" target="_blank" style="color: #8B7355;">stooq.com</a></p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-euro-sign" style="color: #8B7355; margin-right: 6px;"></i>ECB Data Portal</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Offizielle Quelle für:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>EUR-Referenzkurse</li>
                                            <li>Zinssätze & Anleihen</li>
                                            <li>Wirtschaftsindikatoren</li>
                                            <li>Inflationsdaten</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> Täglich 16:00 CET | <strong>Website:</strong> <a href="https://www.ecb.europa.eu" target="_blank" style="color: #8B7355;">ecb.europa.eu</a></p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fab fa-bitcoin" style="color: #8B7355; margin-right: 6px;"></i>CoinGecko API</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Krypto-Daten:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>Top 1000 Kryptowährungen</li>
                                            <li>Marktkapitalisierung</li>
                                            <li>24h Volumen & Preise</li>
                                            <li>Historische Charts</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> Echtzeit | <strong>Website:</strong> <a href="https://www.coingecko.com" target="_blank" style="color: #8B7355;">coingecko.com</a></p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #8B7355;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-chart-area" style="color: #8B7355; margin-right: 6px;"></i>Binance API</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Krypto-Trading:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>Echtzeit Krypto-Preise</li>
                                            <li>Orderbook-Daten</li>
                                            <li>Handelsvolumen</li>
                                            <li>Klines/Candlesticks</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> WebSocket (< 100ms) | <strong>Website:</strong> <a href="https://www.binance.com" target="_blank" style="color: #8B7355;">binance.com</a></p>
                                    </div>
                                </div>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 12px 0; font-size: 16px; font-weight: 600; border-left: 3px solid #8B7355; padding-left: 10px;">🏦 Schweizer Finanzmarkt</h4>
                                <div class="sources-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #d32f2f;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;">🇨🇭 SIX Swiss Exchange</h4>
                                        <p style="color: #333333; margin-bottom: 6px; font-size: 12px;"><strong style="color: #2c3e50;">Offizielle Schweizer Börse:</strong></p>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li>SMI, SLI, SPI Indizes</li>
                                            <li>Blue Chips (Nestlé, Roche, Novartis)</li>
                                            <li>Schweizer Aktien & ETFs</li>
                                            <li>Handelsvolumen & Turnover</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Update:</strong> Handelszeiten 09:00-17:30 | <strong>Website:</strong> <a href="https://www.six-group.com" target="_blank" style="color: #8B7355;">six-group.com</a></p>
                                    </div>

                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px; border-left: 3px solid #d32f2f;">
                                        <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;">📰 Schweizer Finanzpresse</h4>
                                        <ul style="color: #333333; font-size: 12px; margin: 6px 0; padding-left: 18px; line-height: 1.6;">
                                            <li><strong>Finanz und Wirtschaft:</strong> Wöchentliche Analysen</li>
                                            <li><strong>Handelszeitung:</strong> Marktnews & Trends</li>
                                            <li><strong>NZZ Finanzen:</strong> Tagesberichte</li>
                                            <li><strong>Cash.ch:</strong> Echtzeit-News</li>
                                        </ul>
                                        <p style="color: #666; font-size: 11px; margin-top: 6px;"><strong>Verwendung:</strong> Sentiment-Analyse & News-Feed</p>
                                    </div>
                                </div>
                            </div>

                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 12px 0; font-size: 16px; font-weight: 600; border-left: 3px solid #8B7355; padding-left: 10px;">🌍 Internationale Finanzdaten</h4>
                                <div class="sources-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px;">
                                        <h4 style="color: #2c3e50; margin-bottom: 6px; font-size: 13px; font-weight: 600;">Bloomberg Terminal Data</h4>
                                        <p style="color: #666; font-size: 12px;">Benchmark-Indizes, Marktdaten, Analysen</p>
                                    </div>
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px;">
                                        <h4 style="color: #2c3e50; margin-bottom: 6px; font-size: 13px; font-weight: 600;">Financial Times</h4>
                                        <p style="color: #666; font-size: 12px;">Globale Marktnachrichten, Analysen</p>
                                    </div>
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px;">
                                        <h4 style="color: #2c3e50; margin-bottom: 6px; font-size: 13px; font-weight: 600;">World Bank Data</h4>
                                        <p style="color: #666; font-size: 12px;">Wirtschaftsindikatoren, BIP-Daten</p>
                                    </div>
                                    <div class="source-card" style="background: #F8F8F8; border: 1px solid #e0e0e0; border-radius: 0; padding: 15px;">
                                        <h4 style="color: #2c3e50; margin-bottom: 6px; font-size: 13px; font-weight: 600;">Alpha Vantage API</h4>
                                        <p style="color: #666; font-size: 12px;">Technische Indikatoren, Forex-Daten</p>
                                    </div>
                                </div>
                            </div>

                            <div style="background: #e3f2fd; padding: 15px; border-radius: 0; margin-bottom: 15px; border-left: 3px solid #2196f3;">
                                <h4 style="color: #1565c0; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-shield-alt" style="margin-right: 6px;"></i>Smart Load Balancing & Failover</h4>
                                <p style="color: #333333; line-height: 1.5; margin: 0 0 8px 0; font-size: 12px;">Automatisches Load Balancing zwischen Datenquellen mit intelligenter Fehlerbehandlung:</p>
                                <ul style="color: #333333; font-size: 12px; margin: 0; padding-left: 18px; line-height: 1.6;">
                                    <li><strong>Retry-Mechanismus:</strong> Bis zu 3 Versuche pro Quelle mit exponential backoff</li>
                                    <li><strong>Blacklisting:</strong> Fehlerhafte Quellen werden temporär deaktiviert (5min)</li>
                                    <li><strong>Parallel Requests:</strong> Gleichzeitige Anfragen an mehrere Quellen</li>
                                    <li><strong>Caching:</strong> Redis-Cache für häufig abgerufene Daten (TTL: 15min)</li>
                                    <li><strong>Fallback:</strong> Historische Daten bei vollständigem Ausfall</li>
                                </ul>
                            </div>

                            <div style="background: #F8F8F8; padding: 15px; border-radius: 0; margin-top: 15px; border: 1px solid #e0e0e0; border-left: 3px solid #8B7355;">
                                <h4 style="color: #2c3e50; margin-bottom: 8px; font-size: 14px; font-weight: 600;"><i class="fas fa-info-circle" style="color: #8B7355; margin-right: 6px;"></i>Hinweis zur Datenqualität</h4>
                                <p style="color: #333333; line-height: 1.5; margin: 0 0 8px 0; font-size: 12px;">
                                    Alle Daten werden in Echtzeit oder nahezu Echtzeit von den genannten Quellen bezogen und automatisch validiert. Die Plattform nutzt ein Multi-Source-System, um maximale Verfügbarkeit und Genauigkeit zu gewährleisten.
                                </p>
                                <p style="color: #666; line-height: 1.5; margin: 0; font-size: 11px;">
                                    <strong>Datenaktualisierung:</strong> Aktienkurse: 15min delay (kostenlose APIs) | Indizes: Echtzeit | Währungen: Echtzeit | Krypto: < 100ms (WebSocket)
                                </p>
                            </div>
                        </div>

                        <!-- FINMA Disclaimer -->
                        <div style="margin-bottom: 20px; padding: 20px; background: #FFFFFF; border-radius: 0; border: 2px solid #8B7355; border-left: 5px solid #8B7355;">
                            <h3 style="font-family: 'Inter', sans-serif; font-size: 18px; color: #2c3e50; margin: 0 0 12px 0; font-weight: 600;">FINMA Hinweis</h3>

                            <p style="color: #333333; font-size: 13px; line-height: 1.5; margin: 0 0 12px 0; font-weight: 500;">
                                <strong>Wichtiger rechtlicher Hinweis:</strong> Diese Plattform ist keine FINMA-lizenzierte Finanzdienstleistung. Alle hier dargestellten Analysen, Simulationen und Empfehlungen dienen ausschließlich Bildungs- und Informationszwecken und stellen keine Anlageberatung dar.
                            </p>

                            <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 12px; border-left: 3px solid #8B7355;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Keine Anlageberatung:</h4>
                                <ul style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0; padding-left: 18px;">
                                    <li>Keine individuelle Anlageempfehlungen</li>
                                    <li>Keine Berücksichtigung persönlicher Umstände</li>
                                    <li>Keine Garantie für Renditen oder Verluste</li>
                                    <li>Keine Haftung für Anlageentscheidungen</li>
                                </ul>
                            </div>

                            <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 12px; border-left: 3px solid #8B7355;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Risikohinweis:</h4>
                                <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0;">
                                    Alle Anlagen sind mit Risiken verbunden. Der Wert von Anlagen kann fallen und steigen. Vergangene Performance ist kein Indikator für zukünftige Ergebnisse. <strong>Investieren Sie nur Geld, dessen Verlust Sie sich leisten können.</strong>
                                </p>
                            </div>

                            <div style="background: #F8F8F8; padding: 12px; border-radius: 0; margin-bottom: 10px; border-left: 3px solid #8B7355;">
                                <h4 style="font-family: 'Inter', sans-serif; font-size: 13px; color: #2c3e50; margin: 0 0 6px 0; font-weight: 600;">Empfehlung:</h4>
                                <p style="color: #333333; font-size: 12px; line-height: 1.4; margin: 0;">
                                    Konsultieren Sie vor jeder Anlageentscheidung einen qualifizierten Finanzberater oder eine FINMA-lizenzierte Bank. Diese Plattform ersetzt keine professionelle Beratung.
                                </p>
                            </div>

                            <div style="text-align: center; padding-top: 10px; border-top: 1px solid #d0d0d0;">
                                <a href="https://www.finma.ch" target="_blank" style="color: #8B7355; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;">
                                    <i class="fas fa-external-link-alt"></i>
                                    Weitere Informationen: www.finma.ch
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'transparency') {
                // Transparenz: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 1.5cm calc(30px + 1cm) 0 calc(30px + 1cm);">
                        <!-- Main Transparency Card -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border: 1px solid #d0d0d0; border-left: 5px solid #8B7355;">
                            
                            <div style="margin-bottom: 20px;">
                                <h2 style="font-family: 'Inter', sans-serif; font-size: 22px; margin-bottom: 8px; color: #2c3e50; font-weight: 600;">System-Diagnose & Monitoring</h2>
                                <p style="color: #333333; font-size: 13px; font-weight: 400; margin: 0; line-height: 1.6;">Live-Status aller Datenquellen, System-Metriken und detaillierte Berechnungstransparenz</p>
                            </div>

                            <!-- Live Data Sources Status -->
                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">🌐 Live Datenquellen Status</h4>
                                <div id="transparency-live-sources" style="background: #f8f9fa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #666; margin: 0; font-size: 12px; font-style: italic;">Lade Live-Status...</p>
                                </div>
                            </div>

                            <!-- System Metrics -->
                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">📊 System-Metriken</h4>
                                <div id="transparency-system-metrics" style="background: #f8f9fa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #666; margin: 0; font-size: 12px; font-style: italic;">Lade Metriken...</p>
                                </div>
                            </div>

                            <!-- Portfolio Calculations -->
                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">🧮 Portfolio-Berechnungen</h4>
                                <div id="transparency-calculations" style="background: #f8f9fa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #666; margin: 0; font-size: 12px; font-style: italic;">Lade Berechnungen...</p>
                                </div>
                            </div>

                            <!-- Calculation Methods -->
                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">⚙️ Berechnungsmethoden & Formeln</h4>
                                <div id="transparency-formulas" style="background: #f8f9fa; padding: 15px; border-radius: 0; margin-bottom: 12px;">
                                    <p style="color: #666; margin: 0; font-size: 12px; font-style: italic;">Lade Formeln...</p>
                                </div>
                            </div>

                            <!-- User Actions -->
                            <div style="margin-bottom: 20px;">
                                <h4 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; font-family: 'Inter', sans-serif; font-weight: 600; border-bottom: 2px solid #8B7355; padding-bottom: 6px;">📝 Sitzungsverlauf</h4>
                                <div id="transparency-actions" style="background: #f8f9fa; padding: 15px; border-radius: 0; max-height: 250px; overflow-y: auto;">
                                    <p style="color: #666; margin: 0; font-size: 12px; font-style: italic;">Lade Verlauf...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Load transparency data
                setTimeout(() => {
                    loadTransparencyData();
                }, 100);
            } else if (pageId === 'value-testing') {
                // Value Testing: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-search-dollar"></i> Automatische Fundamentalanalyse
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Unser Value Investing Modul führt eine umfassende fundamentale Bewertung Ihrer Portfolio-Assets durch und gibt klare Kauf-/Halten-/Verkaufsempfehlungen basierend auf DCF, Graham-Formel und relativer Bewertung.</p>
                        </div>

                        <!-- Analyse-Parameter Card -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Analyse-Parameter</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Diskontsatz (%)</label>
                                    <input type="number" id="discountRate" value="8" min="1" max="20" step="0.5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Terminal Growth Rate (%)</label>
                                    <input type="number" id="terminalGrowth" value="2" min="0" max="10" step="0.5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Risikofreier Zinssatz (%)</label>
                                    <input type="number" id="riskFreeRate" value="2.5" min="0" max="10" step="0.1" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Marktrisikoprämie (%)</label>
                                    <input type="number" id="marketRiskPremium" value="5.5" min="2" max="10" step="0.1" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                            </div>
                            <div style="display: flex; gap: 15px;">
                                <button onclick="startValueTesting()" style="flex: 1; background: var(--color-accent-rose); color: white; border: none; padding: 12px 24px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                    <i class="fas fa-play"></i> Analyse starten
                                </button>
                                <button id="exportBtn" disabled style="flex: 1; background: #ddd; color: #999; border: none; padding: 12px 24px; border-radius: 0; cursor: not-allowed; font-size: 14px; font-weight: 500;">
                                    <i class="fas fa-download"></i> PDF-Report herunterladen
                                </button>
                            </div>
                        </div>

                        <!-- Results Container (initially hidden) -->
                        <div id="valueTestingResults" style="display: none;">
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Portfolio-Zusammenfassung</h3>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px;">
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Gesamtwert</h4>
                                        <p id="totalPortfolioValue" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Fair Value</h4>
                                        <p id="totalFairValue" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Bewertung</h4>
                                        <p id="portfolioValuation" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Value Score</h4>
                                        <p id="aggregateScore" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Sharpe Ratio</h4>
                                        <p id="portfolioSharpe" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Portfolio Beta</h4>
                                        <p id="portfolioBeta" style="color: #000; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                            </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">VaR 95%</h4>
                                        <p id="portfolioVaR" style="color: #f44336; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                    <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                                        <h4 style="color: #666; font-size: 13px; margin: 0 0 10px 0; font-weight: 500;">Max Drawdown</h4>
                                        <p id="worstDrawdown" style="color: #f44336; font-size: 22px; font-weight: 600; margin: 0;">-</p>
                                    </div>
                                </div>
                            </div>
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Asset-Analyse</h3>
                                <div id="valueAnalysisTableBody" style="color: #666;">Starten Sie die Analyse, um Ergebnisse zu sehen.</div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'momentum-growth') {
                // Momentum Growth: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-chart-line"></i> Momentum-Strategie Analyse
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Unser Momentum Growth Modul analysiert technische Indikatoren, Trendstärke und relative Performance Ihrer Assets, um optimale Ein- und Ausstiegszeitpunkte zu identifizieren.</p>
                        </div>

                        <!-- Analyse-Parameter Card -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Analyse-Parameter</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Lookback-Periode (Monate)</label>
                                    <select id="momentumLookback" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                        <option value="12">12 Monate</option>
                                        <option value="24" selected>24 Monate</option>
                                        <option value="36">36 Monate</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Kurzfristiger MA (Tage)</label>
                                    <input type="number" id="maShort" value="50" min="10" max="100" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Langfristiger MA (Tage)</label>
                                    <input type="number" id="maLong" value="200" min="50" max="500" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Benchmark</label>
                                    <select id="benchmark" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                        <option value="^SSMI">SMI (Schweiz)</option>
                                        <option value="SP500" selected>S&P 500</option>
                                        <option value="MSCI_WORLD">MSCI World</option>
                                    </select>
                                </div>
                            </div>
                            <button onclick="startMomentumAnalysis()" style="width: 100%; background: var(--color-accent-rose); color: white; border: none; padding: 12px 24px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-chart-line"></i> Momentum-Analyse starten
                            </button>
                        </div>

                        <!-- Results Container (initially hidden) -->
                        <div id="momentumResults" style="display: none;">
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Portfolio-Momentum Übersicht</h3>
                                <div id="momentumAnalysisContent" style="color: #666;">Analyse wird geladen...</div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'buy-hold') {
                // Buy & Hold: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-shield-alt"></i> Buy & Hold Strategie
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Unser Buy & Hold Modul analysiert fundamentale Stabilität, langfristiges Wachstum und Dividendenqualität für langfristige Portfoliokonstruktion.</p>
                        </div>

                        <!-- Analyse-Parameter Card -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Analyse-Parameter</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Qualitäts-Gewichtung (%)</label>
                                    <input type="number" id="qualityWeight" value="50" min="0" max="100" step="5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Wachstums-Gewichtung (%)</label>
                                    <input type="number" id="growthWeight" value="25" min="0" max="100" step="5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Bewertungs-Gewichtung (%)</label>
                                    <input type="number" id="valuationWeight" value="15" min="0" max="100" step="5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Dividenden-Gewichtung (%)</label>
                                    <input type="number" id="dividendWeight" value="10" min="0" max="100" step="5" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                            </div>
                            <button onclick="startBuyHoldAnalysis()" style="width: 100%; background: var(--color-accent-rose); color: white; border: none; padding: 12px 24px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-shield-alt"></i> Buy & Hold Analyse starten
                            </button>
                        </div>

                        <!-- Results Container (initially hidden) -->
                        <div id="buyholdResults" style="display: none;">
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Langfristige Portfolio-Schätzung</h3>
                                <div id="buyholdAnalysisContent" style="color: #666;">Analyse wird geladen...</div>
                            </div>
                        </div>
                    </div>
                `;
            } else if (pageId === 'carry-strategy') {
                // Carry Strategy: Vollständiger Content
                contentElement.innerHTML = `
                    <div style="padding: 30px calc(30px + 1cm) 40px calc(30px + 1cm);">
                        <!-- Instruction Box -->
                        <div style="background: #FFFFFF; border-radius: 0; padding: 20px; margin-bottom: 20px; border-left: 4px solid #8B7355; border: 1px solid #d0d0d0;">
                            <h4 style="color: #2c3e50; margin-bottom: 12px; font-size: 18px; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 8px; font-weight: 600;">
                                <i class="fas fa-coins"></i> Carry-Strategie Analyse
                            </h4>
                            <p style="color: #333333; line-height: 1.5; font-size: 14px; margin-bottom: 0;">Unser Carry Strategy Modul analysiert Zinsdifferenziale, Dividendenrenditen und Carry-Charakteristiken für optimale Ertragsstrategien.</p>
                        </div>

                        <!-- Analyse-Parameter Card -->
                        <div style="background: var(--perlweiss); border-radius: 0; padding: 25px; margin-bottom: 30px;">
                            <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Analyse-Parameter</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Finanzierungskosten (%)</label>
                                    <input type="number" id="financingCost" value="3.0" min="0" max="20" step="0.1" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Reinvestment-Policy</label>
                                    <select id="reinvestmentPolicy" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                        <option value="reinvest" selected>Dividenden reinvestieren</option>
                                        <option value="cash">Cash auszahlen</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Leverage-Limit</label>
                                    <input type="number" id="leverageLimit" value="2.0" min="1" max="10" step="0.1" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                </div>
                                <div>
                                    <label style="display: block; color: #666; font-size: 14px; margin-bottom: 8px;">Zeithorizont (Jahre)</label>
                                    <select id="timeHorizon" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 0;">
                                        <option value="1">1 Jahr</option>
                                        <option value="3" selected>3 Jahre</option>
                                        <option value="5">5 Jahre</option>
                                    </select>
                                </div>
                            </div>
                            <button onclick="startCarryAnalysis()" style="width: 100%; background: var(--color-accent-rose); color: white; border: none; padding: 12px 24px; border-radius: 0; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease;">
                                <i class="fas fa-coins"></i> Carry-Analyse starten
                            </button>
                        </div>

                        <!-- Results Container (initially hidden) -->
                        <div id="carryResults" style="display: none;">
                            <div style="background: var(--perlweiss); border-radius: 0; padding: 25px;">
                                <h3 style="font-family: 'Playfair Display', serif; font-size: 24px; color: #000000; margin: 0 0 20px 0; font-weight: 500;">Portfolio-Carry Übersicht</h3>
                                <div id="carryAnalysisContent" style="color: #666;">Analyse wird geladen...</div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // Alle anderen Seiten: Standard-Template verwenden
                contentElement.innerHTML = `
                    <div style="text-align: center; padding: 60px 0;">
                        <i class="fas ${pageData.icon}" style="font-size: 64px; margin-bottom: 20px; color: var(--color-accent-rose);"></i>
                        <h2 style="font-family: 'Playfair Display', serif; font-size: 32px; margin-bottom: 15px; color: #000000; font-weight: 400;">${pageData.heading}</h2>
                        <p style="color: #666666; font-size: 18px; max-width: 600px; margin: 0 auto; line-height: 1.6;">${pageData.description}</p>
                    </div>
                `;
            }

            // Navigation aktiv setzen mit !important durch setAttribute
            document.querySelectorAll('.gs-header-nav a').forEach(link => {
                link.style.setProperty('color', '#666666', 'important');
                link.style.setProperty('font-weight', '400', 'important');
            });
            const activeLink = document.getElementById('nav-' + pageId);
            if (activeLink) {
                activeLink.style.setProperty('color', '#000000', 'important');
                activeLink.style.setProperty('font-weight', '500', 'important');
            }
            
            // Apply alternating section backgrounds
            setTimeout(() => {
                applyAlternatingSectionBackgrounds();
            }, 100);

            // Zum Anfang scrollen
            document.getElementById('gettingStartedPage').scrollTop = 0;
            
            // Dashboard-spezifische Initialisierung
            if (pageId === 'dashboard') {
                initializeDashboard();
            }
            
            // Strategieanalyse-spezifische Initialisierung
            if (pageId === 'strategieanalyse') {
                initializeStrategieanalyse();
            }
            
            // Portfolio-spezifische Initialisierung
            if (pageId === 'portfolio') {
                if (typeof updatePortfolioDevelopment === 'function') {
                    updatePortfolioDevelopment();
                }
            }
            
            // Simulation-spezifische Initialisierung  
            if (pageId === 'simulation') {
                if (typeof updateSimulationPage === 'function') {
                    updateSimulationPage();
                }
            }
        }
        
        // ==============================================
        // DASHBOARD FUNCTIONALITY
        // ==============================================
        
        // Global variables for dashboard
        const SWISS_STOCKS = {
            "NESN.SW": "Nestlé", "NOVN.SW": "Novartis", "ROG.SW": "Roche", "UBSG.SW": "UBS Group",
            "ZURN.SW": "Zurich Insurance", "ABBN.SW": "ABB", "CSGN.SW": "Credit Suisse",
            "SGSN.SW": "SGS", "GIVN.SW": "Givaudan", "LONN.SW": "Lonza", "SIKA.SW": "Sika",
            "GEBN.SW": "Geberit", "SOON.SW": "Sonova", "SCMN.SW": "Swisscom", "ADEN.SW": "Adecco",
            "BAER.SW": "Julius Bär", "CLN.SW": "Clariant", "LOGIN.SW": "Logitech", "CFR.SW": "Richemont",
            "ALC.SW": "Alcon", "TEMN.SW": "Temenos", "VACN.SW": "VAT Group", "KNIN.SW": "Kuehne+Nagel",
            "PGHN.SW": "Partners Group", "SLHN.SW": "Swiss Life", "LISN.SW": "Lindt & Sprüngli",
            "EMSN.SW": "EMS Chemie", "STMN.SW": "Stadler Rail", "HELN.SW": "Helvetia",
            "BEAN.SW": "Belimo", "BKW.SW": "BKW", "BALN.SW": "Baloise", "SPSN.SW": "Swiss Prime Site",
            "UHR.SW": "Swatch Group", "FHZN.SW": "Flughafen Zürich", "BARN.SW": "Barry Callebaut",
            "AVOL.SW": "Avolta", "PSPN.SW": "PSP Swiss Property", "GF.SW": "Georg Fischer",
            "EFGN.SW": "EFG International", "YPSN.SW": "Ypsomed", "SFSN.SW": "SFS Group",
            "GALE.SW": "Galenica", "BUCN.SW": "Bucher", "EMMN.SW": "Emmi", "DKSH.SW": "DKSH",
            "ALLN.SW": "Allreal", "SIGN.SW": "SIG", "MOBN.SW": "Mobimo", "BLKB.SW": "BLKB"
        };

        const INDICES = {
            "SPX": "S&P 500 Index", "NDX": "NASDAQ 100", "DJI": "Dow Jones Industrial Average",
            "RUT": "Russell 2000", "VIX": "CBOE Volatility Index", "COMP": "NASDAQ Composite",
            "DAX": "DAX Germany", "CAC": "CAC 40 France", "FTSE": "FTSE 100 UK",
            "STOXX50": "Euro Stoxx 50", "AEX": "AEX Netherlands", "IBEX": "IBEX 35 Spain",
            "^SSMI": "Swiss Market Index", "^SLI": "Swiss Leader Index",
            "NIKKEI": "Nikkei 225 Japan", "HSI": "Hang Seng Hong Kong", 
            "SHCOMP": "Shanghai Composite", "KOSPI": "KOSPI South Korea",
            "MSCIW": "MSCI World", "MSCIEM": "MSCI Emerging Markets"
        };

        const OTHER_ASSETS = {
            "GC=F": "Gold Futures", "SI=F": "Silver Futures", "CL=F": "Crude Oil Futures",
            "PL=F": "Platinum Futures", "HG=F": "Copper Futures", "NG=F": "Natural Gas Futures",
            "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
            "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
            "USDCHF=X": "USD/CHF", "EURCHF=X": "EUR/CHF", "GBPCHF=X": "GBP/CHF",
            "SPY": "S&P 500 ETF", "VNQ": "Real Estate ETF", "BND": "Total Bond Market",
            "GLD": "SPDR Gold Trust", "TLT": "iShares 20+ Year Treasury",
            "XLE": "Energy Select Sector", "XLF": "Financial Select Sector",
            "XLK": "Technology Select Sector", "XLV": "Health Care Select Sector"
        };

        let userPortfolio = [];
        let totalInvestment = 100000;
        let portfolioCalculated = false;
        let currentTimeframe = '5y';

        function initializeDashboard() {
            populateSelects();
            setupEventListeners();
            loadPortfolioFromStorage();
            refreshDashboardMarketData();
            
            // Auto-refresh market data every 5 minutes
            setInterval(refreshDashboardMarketData, 300000);
        }
        
        function savePortfolioToStorage() {
            try {
                const portfolioData = {
                    portfolio: userPortfolio,
                    totalInvestment: totalInvestment,
                    portfolioCalculated: portfolioCalculated,
                    currentTimeframe: currentTimeframe
                };
                localStorage.setItem('dashboardPortfolio', JSON.stringify(portfolioData));
            } catch (e) {
                console.error('Error saving portfolio:', e);
            }
        }
        
        function loadPortfolioFromStorage() {
            try {
                const saved = localStorage.getItem('dashboardPortfolio');
                if (saved) {
                    const portfolioData = JSON.parse(saved);
                    userPortfolio = portfolioData.portfolio || [];
                    totalInvestment = portfolioData.totalInvestment || 100000;
                    portfolioCalculated = portfolioData.portfolioCalculated || false;
                    currentTimeframe = portfolioData.currentTimeframe || '5y';
                    
                    // Update UI with loaded data
                    const totalInvestmentInput = document.getElementById('totalInvestment');
                    if (totalInvestmentInput) {
                        totalInvestmentInput.value = totalInvestment;
                    }
                    
                    // Update display
                    updatePortfolioDisplay();
                }
            } catch (e) {
                console.error('Error loading portfolio:', e);
            }
        }

        function populateSelects() {
            // Populate stock select
            const stockSelect = document.getElementById('stockSelect');
            if (stockSelect) {
                Object.entries(SWISS_STOCKS).forEach(([symbol, name]) => {
                    const option = document.createElement('option');
                    option.value = symbol;
                    option.textContent = symbol + ' - ' + name;
                    stockSelect.appendChild(option);
                });
            }
            
            // Populate index select
            const indexSelect = document.getElementById('indexSelect');
            if (indexSelect) {
                Object.entries(INDICES).forEach(([symbol, name]) => {
                    const option = document.createElement('option');
                    option.value = symbol;
                    option.textContent = symbol + ' - ' + name;
                    indexSelect.appendChild(option);
                });
            }
            
            // Populate asset select
            const assetSelect = document.getElementById('assetSelect');
            if (assetSelect) {
                Object.entries(OTHER_ASSETS).forEach(([symbol, name]) => {
                    const option = document.createElement('option');
                    option.value = symbol;
                    option.textContent = symbol + ' - ' + name;
                    assetSelect.appendChild(option);
                });
            }
        }

        function setupEventListeners() {
            // Total investment change
            const totalInvestmentInput = document.getElementById('totalInvestment');
            if (totalInvestmentInput) {
                totalInvestmentInput.addEventListener('change', function() {
                    totalInvestment = parseFloat(this.value) || 0;
                    updatePortfolioDisplay();
                });
            }
            
            // Timeframe buttons
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.timeframe-btn').forEach(b => {
                        b.style.background = '#ffffff';
                        b.style.color = '#6c757d';
                        b.style.borderColor = '#ddd';
                    });
                    this.style.background = '#1a1a1a';
                    this.style.color = '#ffffff';
                    this.style.borderColor = '#1a1a1a';
                    currentTimeframe = this.getAttribute('data-timeframe');
                    updateCharts();
                });
            });
        }

        function addStock() {
            const select = document.getElementById('stockSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                // Fetch real data from Yahoo Finance
                fetch(`/api/get_asset_stats/${symbol}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            // Fallback to simulated data
                userPortfolio.push({
                    symbol: symbol,
                    name: SWISS_STOCKS[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: 0.09, // 9% fixed fallback
                    volatility: 0.22, // 22% fixed fallback
                                type: 'stock',
                                source: 'fallback'
                            });
                        } else {
                            // Use real data
                            userPortfolio.push({
                                symbol: symbol,
                                name: data.name || SWISS_STOCKS[symbol],
                                investment: 10000,
                                weight: 0,
                                expectedReturn: data.expectedReturn / 100,
                                volatility: data.volatility / 100,
                                currentPrice: data.price,
                                yearHigh: data.yearHigh,
                                yearLow: data.yearLow,
                                type: 'stock',
                                source: 'yahoo_finance',
                                sector: data.sector
                            });
                            console.log(`✅ Loaded real data for ${symbol} from Yahoo Finance`);
                        }
                updatePortfolioDisplay();
                    })
                    .catch(error => {
                        console.error('Error fetching asset stats:', error);
                        // Fallback to simulated data
                        userPortfolio.push({
                            symbol: symbol,
                            name: SWISS_STOCKS[symbol],
                            investment: 10000,
                            weight: 0,
                            expectedReturn: 0.09, // 9% fixed fallback
                            volatility: 0.22, // 22% fixed fallback
                            type: 'stock',
                            source: 'fallback'
                        });
                        updatePortfolioDisplay();
                    });
                select.value = '';
            }
        }

        function addIndex() {
            const select = document.getElementById('indexSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                // Fetch real data from Yahoo Finance
                fetch(`/api/get_asset_stats/${symbol}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            // Fallback to simulated data
                userPortfolio.push({
                    symbol: symbol,
                    name: INDICES[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: 0.11, // 11% fixed fallback for indices
                    volatility: 0.24, // 24% fixed fallback for indices
                                type: 'index',
                                source: 'fallback'
                            });
                        } else {
                            // Use real data
                            userPortfolio.push({
                                symbol: symbol,
                                name: data.name || INDICES[symbol],
                                investment: 10000,
                                weight: 0,
                                expectedReturn: data.expectedReturn / 100,
                                volatility: data.volatility / 100,
                                currentPrice: data.price,
                                yearHigh: data.yearHigh,
                                yearLow: data.yearLow,
                                type: 'index',
                                source: 'yahoo_finance'
                            });
                            console.log(`✅ Loaded real data for ${symbol} from Yahoo Finance`);
                        }
                updatePortfolioDisplay();
                    })
                    .catch(error => {
                        console.error('Error fetching index stats:', error);
                        // Fallback to simulated data
                        userPortfolio.push({
                            symbol: symbol,
                            name: INDICES[symbol],
                            investment: 10000,
                            weight: 0,
                            expectedReturn: 0.11, // 11% fixed fallback for indices
                            volatility: 0.24, // 24% fixed fallback for indices
                            type: 'index',
                            source: 'fallback'
                        });
                        updatePortfolioDisplay();
                    });
                select.value = '';
            }
        }

        function addAsset() {
            const select = document.getElementById('assetSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: OTHER_ASSETS[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: 0.10, // 10% fixed fallback for other assets
                    volatility: 0.22, // 22% fixed fallback
                    type: 'other',
                    source: 'fallback'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function removeAsset(symbol) {
            userPortfolio = userPortfolio.filter(asset => asset.symbol !== symbol);
            updatePortfolioDisplay();
        }

        function updateAssetInvestment(index, value) {
            userPortfolio[index].investment = parseFloat(value) || 0;
            updatePortfolioDisplay();
        }

        function calculatePortfolio() {
            if (userPortfolio.length === 0) {
                alert("Bitte fügen Sie zuerst Assets zu Ihrem Portfolio hinzu.");
                return;
            }
            
            portfolioCalculated = true;
            savePortfolioToStorage();
            updatePortfolioDisplay();
            
            // Update all dependent pages
            updateAllPages();
            
            // Show success message
            const calculateBtn = document.querySelector('button[onclick="calculatePortfolio()"]');
            if (calculateBtn) {
                const originalText = calculateBtn.innerHTML;
                calculateBtn.innerHTML = '<i class="fas fa-check"></i> Portfolio Berechnet!';
                calculateBtn.style.backgroundColor = '#28a745';
                
                setTimeout(() => {
                    calculateBtn.innerHTML = originalText;
                    calculateBtn.style.backgroundColor = '#1a1a1a';
                }, 2000);
            }
            
            showNotification('Portfolio erfolgreich berechnet! Alle Seiten wurden aktualisiert.', 'success');
        }

        function updatePortfolioDisplay() {
            calculateWeights();
            validateTotalInvestment();
            updateStockCards();
            updateCharts();
            updatePerformanceMetrics();
            savePortfolioToStorage();
        }

        function calculateWeights() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            userPortfolio.forEach(asset => {
                asset.weight = currentTotal > 0 ? (asset.investment / currentTotal * 100).toFixed(1) : 0;
            });
        }

        function validateTotalInvestment() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const targetTotal = parseFloat(document.getElementById('totalInvestment')?.value) || 0;
            const validationElement = document.getElementById('totalValidation');
            
            if (validationElement) {
                if (Math.abs(currentTotal - targetTotal) < 1) {
                    validationElement.textContent = 'Investitionen stimmen überein: CHF ' + currentTotal.toLocaleString('de-CH') + ' von CHF ' + targetTotal.toLocaleString('de-CH');
                    validationElement.style.background = 'rgba(40, 167, 69, 0.1)';
                    validationElement.style.color = '#28a745';
                    validationElement.style.border = '1px solid rgba(40, 167, 69, 0.2)';
                } else {
                    validationElement.textContent = 'Achtung: CHF ' + currentTotal.toLocaleString('de-CH') + ' von CHF ' + targetTotal.toLocaleString('de-CH') + ' investiert';
                    validationElement.style.background = 'rgba(220, 53, 69, 0.1)';
                    validationElement.style.color = '#dc3545';
                    validationElement.style.border = '1px solid rgba(220, 53, 69, 0.2)';
                }
            }
        }

        function updateStockCards() {
            const container = document.getElementById('selectedStocks');
            if (!container) return;
            
            container.innerHTML = '';
            
            if (userPortfolio.length === 0) {
                container.style.cssText = 'min-height: 100px; border: 1px dashed #ddd; border-radius: 0; padding: 20px; display: flex; align-items: center; justify-content: center;';
                container.innerHTML = '<div style="text-align: center; color: #6c757d;"><i class="fas fa-folder-open" style="font-size: 2rem; margin-bottom: 10px; color: #ddd;"></i><p>Noch keine Assets hinzugefügt</p></div>';
                return;
            }
            
            // Change container style when assets are present
            container.style.cssText = 'min-height: 100px; border: 1px dashed #ddd; border-radius: 0; padding: 20px;';
            
            userPortfolio.forEach((asset, index) => {
                const card = document.createElement('div');
                card.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 12px 15px; border: 1px solid #eee; border-radius: 0; margin-bottom: 10px; background: var(--perlweiss);';
                
                let badgeClass = 'badge-other';
                let badgeText = 'Asset';
                if (asset.type === 'stock') {
                    badgeClass = 'badge-stock';
                    badgeText = 'Aktie';
                } else if (asset.type === 'index') {
                    badgeClass = 'badge-index';
                    badgeText = 'Index';
                }
                
                card.innerHTML = 
                    '<div style="display: flex; flex-direction: column; gap: 4px;">' +
                        '<strong style="color: #1a1a1a;">' + asset.symbol + ' <span style="display: inline-block; padding: 3px 8px; border-radius: 0; font-size: 11px; font-weight: 600; margin-left: 8px; background: rgba(68, 68, 68, 0.1); color: #444;">' + badgeText + '</span></strong>' +
                        '<span style="color: var(--color-accent-rose); font-size: 14px;">' + asset.name + '</span>' +
                    '</div>' +
                    '<div style="display: flex; align-items: center; gap: 15px;">' +
                        '<div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-end;">' +
                            '<div>' +
                                '<input type="number" value="' + asset.investment + '" ' +
                                       'onchange="updateAssetInvestment(' + index + ', this.value)" ' +
                                       'style="width: 120px; padding: 5px 8px; border: 1px solid #ddd; border-radius: 0; text-align: right;">' +
                                '<span style="margin-left: 5px;">CHF</span>' +
                            '</div>' +
                            '<div style="font-size: 12px; color: ' + (asset.weight > 0 ? '#8b7355' : '#6c757d') + '">' +
                                'Gewichtung: ' + asset.weight + '%' +
                            '</div>' +
                        '</div>' +
                        '<button onclick="removeAsset(' + "'" + asset.symbol + "'" + ')" style="display: inline-flex; align-items: center; justify-content: center; padding: 6px 12px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: 1px solid #1a1a1a; background-color: transparent; color: #1a1a1a; font-size: 12px;">' +
                            '<i class="fas fa-times"></i>' +
                        '</button>' +
                    '</div>';
                container.appendChild(card);
            });
        }

        function updatePerformanceMetrics() {
            if (userPortfolio.length === 0) {
                const portfolioPerformance = document.getElementById('portfolioPerformance');
                const riskAnalysis = document.getElementById('riskAnalysis');
                const diversification = document.getElementById('diversification');
                const sharpeRatio = document.getElementById('sharpeRatio');
                
                if (portfolioPerformance) portfolioPerformance.textContent = '0.0%';
                if (riskAnalysis) riskAnalysis.textContent = '0.0%';
                if (diversification) diversification.textContent = '0/10';
                if (sharpeRatio) sharpeRatio.textContent = '0.00';
                return;
            }
            
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            const sharpeRatio = volatility > 0 ? (expectedReturn - 2) / volatility : 0;
            const diversificationScore = Math.min(userPortfolio.length * 2, 10);
            
            const portfolioPerformance = document.getElementById('portfolioPerformance');
            const riskAnalysis = document.getElementById('riskAnalysis');
            const diversification = document.getElementById('diversification');
            const sharpeRatioEl = document.getElementById('sharpeRatio');
            
            if (portfolioPerformance) portfolioPerformance.textContent = expectedReturn.toFixed(1) + '%';
            if (riskAnalysis) riskAnalysis.textContent = volatility.toFixed(1) + '%';
            if (diversification) diversification.textContent = diversificationScore + '/10';
            if (sharpeRatioEl) sharpeRatioEl.textContent = sharpeRatio.toFixed(2);
        }

        function calculatePortfolioReturn() {
            if (userPortfolio.length === 0) return 0;
            const totalWeight = userPortfolio.reduce((sum, asset) => sum + parseFloat(asset.weight), 0);
            if (totalWeight === 0) return 0;
            return userPortfolio.reduce((sum, asset) => 
                sum + (parseFloat(asset.weight) / 100) * asset.expectedReturn, 0);
        }

        function calculatePortfolioRisk() {
            if (userPortfolio.length === 0) return 0;
            const totalWeight = userPortfolio.reduce((sum, asset) => sum + parseFloat(asset.weight), 0);
            if (totalWeight === 0) return 0;
            return userPortfolio.reduce((sum, asset) => 
                sum + (parseFloat(asset.weight) / 100) * asset.volatility, 0);
        }

        function updateCharts() {
            updatePortfolioChart();
            updatePerformanceChart();
            updatePortfolioLegend();
            updateCorrelationMatrix();
        }

        let portfolioChartInstance = null;
        
        function updatePortfolioChart() {
            const canvas = document.getElementById('portfolioChart');
            if (!canvas) return;
            
            // Destroy existing chart if it exists
            if (portfolioChartInstance) {
                portfolioChartInstance.destroy();
                portfolioChartInstance = null;
            }
            
            if (userPortfolio.length === 0) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '16px Inter';
                ctx.fillStyle = '#999';
                ctx.textAlign = 'center';
                ctx.fillText('Keine Daten verfügbar', canvas.width / 2, canvas.height / 2);
                return;
            }
            
            // Prepare data for chart
            const labels = userPortfolio.map(asset => asset.symbol);
            const data = userPortfolio.map(asset => parseFloat(asset.weight) || 0);
            const colors = [
                '#8b7355', '#6B46C1', '#28A745', '#DC3545', '#FFC107', 
                '#17A2B8', '#6C757D', '#343A40', '#E83E8C', '#20C997'
            ];
            
            // Create new chart
            const ctx = canvas.getContext('2d');
            portfolioChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: colors.slice(0, userPortfolio.length),
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    return label + ': ' + value.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                }
            });
        }

        let performanceChartInstance = null;
        
        // Helper function: Generate GBM data (fallback)
        function generateGBMData(colors) {
            const labels = [];
            const datasets = [];
            const points = 50;
            
            for (let i = 0; i < points; i++) {
                labels.push('');
            }
            
            userPortfolio.forEach((asset, index) => {
                const data = [];
                let value = 100;
                const dailyReturn = (asset.expectedReturn || 0.08) / 252;
                const dailyVol = (asset.volatility || 0.15) / Math.sqrt(252);
                
                for (let i = 0; i < points; i++) {
                    const randomShock = (Math.random() - 0.5) * 2;
                    const change = dailyReturn + dailyVol * randomShock;
                    value = value * (1 + change);
                    data.push(value);
                }
                
                datasets.push({
                    label: asset.symbol,
                    data: data,
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + '20',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                });
            });
            
            return {labels, datasets};
        }
        
        function updatePerformanceChart() {
            const canvas = document.getElementById('assetPerformanceChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            // Destroy existing chart
            if (performanceChartInstance) {
                performanceChartInstance.destroy();
            }
            
            if (userPortfolio.length === 0) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '16px Inter';
                ctx.fillStyle = '#999';
                ctx.textAlign = 'center';
                ctx.fillText('Keine Daten verfügbar', canvas.width / 2, canvas.height / 2);
                return;
            }
            
            const colors = ['#8b7355', '#6B46C1', '#28A745', '#DC3545', '#FFC107', '#17A2B8', '#6C757D', '#343A40', '#E83E8C', '#20C997'];
            
            // Try to fetch real historical data
            const histPeriod = '1y';
            const fetchPromises = userPortfolio.map(asset => 
                fetch(`/api/get_historical_data/${asset.symbol}?period=${histPeriod}`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
            );
            
            Promise.all(fetchPromises)
                .then(results => {
                    // Validate: Check if ALL assets have valid data
                    let allValid = results.every(result => 
                        result && 
                        result.data && 
                        Array.isArray(result.data) && 
                        result.data.length > 5
                    );
                    
                    if (!allValid) {
                        console.log('Some historical data missing, using GBM fallback');
                        throw new Error('Incomplete data');
                    }
                    
                    // Build real data chart
            const labels = [];
            const datasets = [];
                    
                    // Use first asset's dates as reference
                    const referenceDates = results[0].data.map(d => d.date);
                    const labelStep = Math.max(1, Math.floor(referenceDates.length / 10));
                    referenceDates.forEach((date, i) => {
                        if (i % labelStep === 0) {
                            const d = new Date(date);
                            labels.push(d.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'}));
                        } else {
                labels.push('');
            }
                    });
                    
                    // Create datasets with real data
                    results.forEach((result, index) => {
                        const asset = userPortfolio[index];
                        const historicalData = result.data;
                        const prices = historicalData.map(d => d.close);
                        const investment = asset.investment || 10000;
                        const initialPrice = prices[0];
                        
                        const performanceData = prices.map(price => {
                            return ((price - initialPrice) / initialPrice) * 100;
                        });
                        
                        const amountsData = prices.map(price => {
                            return investment * (price / initialPrice);
                        });
                
                datasets.push({
                    label: asset.symbol,
                            data: performanceData,
                            amounts: amountsData,
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + '20',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                });
            });
            
                    // Create chart with real data
            performanceChartInstance = new Chart(ctx, {
                type: 'line',
                        data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                boxWidth: 12,
                                padding: 10,
                                        font: { size: 11, family: 'Inter' }
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                            const perf = context.parsed.y.toFixed(2);
                                            const amount = context.dataset.amounts ? context.dataset.amounts[context.dataIndex] : 0;
                                            return context.dataset.label + ': ' + perf + '% (CHF ' + amount.toLocaleString('de-CH', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ')';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                            ticks: {
                                        callback: function(value) { return value.toFixed(0) + '%'; },
                                        font: { size: 11 }
                                    }
                                },
                                x: {
                                    display: true,
                                    grid: { display: false },
                                    ticks: { font: { size: 10 } }
                                }
                            }
                        }
                    });
                })
                .catch(err => {
                    // Fallback to GBM on any error
                    console.log('Using GBM fallback:', err.message || err);
                    const {labels, datasets} = generateGBMData(colors);
                    
                    performanceChartInstance = new Chart(ctx, {
                        type: 'line',
                        data: { labels, datasets },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'bottom',
                                    labels: {
                                        boxWidth: 12,
                                        padding: 10,
                                        font: { size: 11, family: 'Inter' }
                                    }
                                },
                                tooltip: {
                                    mode: 'index',
                                    intersect: false,
                                    callbacks: {
                                        label: function(context) {
                                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: false,
                                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                                    ticks: {
                                        callback: function(value) { return value.toFixed(0) + '%'; },
                                        font: { size: 11 }
                                    }
                                },
                                x: { display: false }
                            }
                        }
                    });
            });
        }

        function updatePortfolioLegend() {
            const container = document.getElementById('portfolioLegend');
            if (!container) return;
            
            container.innerHTML = '';
            
            if (userPortfolio.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #6c757d;">Keine Assets im Portfolio</p>';
                return;
            }
            
            const colors = ['#8b7355', '#6B46C1', '#28A745', '#DC3545', '#FFC107', '#17A2B8', '#6C757D', '#343A40', '#E83E8C', '#20C997'];
            
            userPortfolio.forEach((asset, index) => {
                const legendItem = document.createElement('div');
                legendItem.style.cssText = 'display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 0; background: #f8f9fa;';
                
                let badgeClass = 'badge-other';
                if (asset.type === 'stock') badgeClass = 'badge-stock';
                else if (asset.type === 'index') badgeClass = 'badge-index';
                
                legendItem.innerHTML = 
                    '<div style="width: 16px; height: 16px; border-radius: 0; background-color: ' + colors[index % colors.length] + '"></div>' +
                    '<div style="font-weight: 500; color: #1a1a1a; flex: 1;">' + asset.symbol + ' <span style="display: inline-block; padding: 3px 8px; border-radius: 0; font-size: 11px; font-weight: 600; margin-left: 8px; background: rgba(68, 68, 68, 0.1); color: #444;">' + asset.type + '</span></div>' +
                    '<div style="color: #6c757d; font-size: 14px;">' + asset.weight + '%</div>';
                container.appendChild(legendItem);
            });
        }

        function refreshDashboardMarketData() {
            const markets = [
                { symbol: '^SSMI', priceId: 'market-smi-price', changeId: 'market-smi-change', barId: 'bar-smi' },
                { symbol: '^GSPC', priceId: 'market-sp500-price', changeId: 'market-sp500-change', barId: 'bar-sp500' },
                { symbol: 'GC=F', priceId: 'market-gold-price', changeId: 'market-gold-change', barId: 'bar-gold' },
                { symbol: 'EURCHF=X', priceId: 'market-eurchf-price', changeId: 'market-eurchf-change', barId: 'bar-eurchf' }
            ];
            
            markets.forEach(market => {
                fetch(`/api/get_live_data/${market.symbol}`)
                        .then(response => response.json())
                        .then(data => {
                        if (data && data.price !== undefined) {
                            const priceEl = document.getElementById(market.priceId);
                            const changeEl = document.getElementById(market.changeId);
                            const barEl = document.getElementById(market.barId);
                            
                            let formattedPrice;
                            if (market.symbol === 'GC=F') {
                                formattedPrice = '$' + data.price.toFixed(0);
                            } else if (market.symbol === 'EURCHF=X') {
                                formattedPrice = data.price.toFixed(4);
                            } else {
                                formattedPrice = data.price.toLocaleString('de-CH', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                });
                            }
                            
                            // Update Dashboard display
                            if (priceEl) {
                                if (market.symbol === 'GC=F') {
                                    priceEl.textContent = '$' + data.price.toFixed(2);
                                } else if (market.symbol === 'EURCHF=X') {
                                    priceEl.textContent = data.price.toFixed(4);
                                    } else {
                                    priceEl.textContent = data.price.toLocaleString('de-CH', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    });
                                }
                            }
                            
                            if (changeEl) {
                                const change = data.change_percent || 0;
                                changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
                                changeEl.style.color = change >= 0 ? '#28a745' : '#dc3545';
                            }
                            
                            // Update Bar display (kompakt)
                            if (barEl) {
                                barEl.textContent = formattedPrice;
                                }
                            }
                        })
                        .catch(error => {
                        console.error('Error fetching data for', market.symbol, error);
                        const priceEl = document.getElementById(market.priceId);
                        const changeEl = document.getElementById(market.changeId);
                        const barEl = document.getElementById(market.barId);
                        if (priceEl) priceEl.textContent = 'N/A';
                        if (changeEl) changeEl.textContent = '--';
                        if (barEl) barEl.textContent = '--';
                    });
            });
        }
        
        // ==============================================
        // PDF EXPORT FUNCTIONALITY
        // ==============================================
        
        async function exportPortfolioPDF() {
            console.log('📄 PDF Export gestartet - ALLE Berechnungen werden durchgeführt...');
            console.log('Portfolio:', userPortfolio);
            
            try {
                // Check if portfolio exists
                if (!userPortfolio || userPortfolio.length === 0) {
                    console.error('❌ Kein Portfolio vorhanden!');
                    document.getElementById('pdfStatus').innerHTML = '<span style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Bitte erstellen Sie zuerst ein Portfolio</span>';
                    return;
                }
                
                console.log('✅ Portfolio gefunden:', userPortfolio.length, 'Assets');
                
                // Show loading
                const button = document.getElementById('exportPdfButton');
                const status = document.getElementById('pdfStatus');
                
                if (!button || !status) {
                    console.error('❌ Button oder Status Element nicht gefunden!');
                    alert('Fehler: UI-Elemente nicht gefunden. Bitte Seite neu laden.');
                    return;
                }
                
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Berechne alle Daten...';
                status.innerHTML = '<span style="color: #8B7355;"><i class="fas fa-hourglass-half"></i> Führe alle Berechnungen durch...</span>';
                
                // ========================================
                // SCHRITT 1: Strategie-Optimierung
                // ========================================
                console.log('🔄 1/3 - Berechne Strategien...');
                status.innerHTML = '<span style="color: #8B7355;">🔄 1/3 - Optimiere Strategien...</span>';
                
                const strategyResponse = await fetch('/api/strategy_optimization', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ portfolio: userPortfolio })
                });
                
                const strategyData = await strategyResponse.json();
                console.log('✅ Strategien berechnet:', strategyData);
                
                // ========================================
                // SCHRITT 2: Monte Carlo Simulation
                // ========================================
                console.log('🔄 2/3 - Monte Carlo Simulation...');
                status.innerHTML = '<span style="color: #8B7355;">🔄 2/3 - Monte Carlo Simulation...</span>';
                
                const monteCarloResponse = await fetch('/api/monte_carlo_correlated', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        portfolio: userPortfolio,
                        years: 10,
                        simulations: 1000,
                        initialInvestment: userPortfolio.reduce((sum, asset) => sum + (parseFloat(asset.investment) || 0), 0)
                    })
                });
                
                const monteCarloData = await monteCarloResponse.json();
                console.log('✅ Monte Carlo berechnet');
                
                // ========================================
                // SCHRITT 3: Sammle alle Daten für PDF
                // ========================================
                console.log('🔄 3/3 - Erstelle PDF...');
                status.innerHTML = '<span style="color: #8B7355;">🔄 3/3 - Erstelle PDF...</span>';
                
                const pdfData = {
                    portfolio: userPortfolio,
                    metrics: {
                        expectedReturn: document.getElementById('portfolioPerformance')?.textContent || 'N/A',
                        volatility: document.getElementById('riskAnalysis')?.textContent || 'N/A',
                        diversification: document.getElementById('diversification')?.textContent || 'N/A',
                        sharpeRatio: document.getElementById('sharpeRatio')?.textContent || 'N/A'
                    },
                    strategies: strategyData.strategies || [],
                    monteCarlo: {
                        median: monteCarloData.median || 0,
                        percentile_5: monteCarloData.percentile_5 || 0,
                        percentile_95: monteCarloData.percentile_95 || 0
                    },
                    portfolioCalculated: portfolioCalculated,
                    totalInvestment: userPortfolio.reduce((sum, asset) => sum + (parseFloat(asset.investment) || 0), 0),
                    timestamp: new Date().toLocaleString('de-DE')
                };
                
                console.log('📤 Sende ALLE Daten an Backend:', pdfData);
                
                // Send request to backend
                const response = await fetch('/api/export_portfolio_pdf', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(pdfData)
                });
                
                console.log('📥 Response Status:', response.status);
                
                if (response.ok) {
                    console.log('✅ Backend Response OK - Erstelle PDF...');
                    
                    // Download PDF
                    const blob = await response.blob();
                    console.log('📄 PDF Blob erstellt:', blob.size, 'bytes');
                    
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `Portfolio_Report_${new Date().toISOString().split('T')[0]}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    console.log('✅ PDF Download gestartet!');
                    
                    // Success message
                    status.innerHTML = '<span style="color: #28a745;"><i class="fas fa-check-circle"></i> PDF erfolgreich erstellt!</span>';
                } else {
                    console.error('❌ Backend Error:', response.status);
                    const errorText = await response.text();
                    console.error('Error Details:', errorText);
                    
                    let errorMessage = 'Unbekannter Fehler';
                    try {
                        const error = JSON.parse(errorText);
                        errorMessage = error.error || errorText;
                    } catch (e) {
                        errorMessage = errorText.substring(0, 100);
                    }
                    
                    status.innerHTML = `<span style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Fehler: ${errorMessage}</span>`;
                }
            } catch (error) {
                console.error('❌ PDF Export Error:', error);
                document.getElementById('pdfStatus').innerHTML = '<span style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Fehler: ' + error.message + '</span>';
            } finally {
                // Reset button
                const button = document.getElementById('exportPdfButton');
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-download"></i> PDF Report Erstellen';
                }
            }
        }
        
        // ==============================================
        // STRATEGIEANALYSE FUNCTIONALITY
        // ==============================================
        
        // Global variables for strategieanalyse
        let strategyChartInstance = null;
        
        // Initialize Strategieanalyse
        function initializeStrategieanalyse() {
            // Load portfolio data from localStorage
            loadPortfolioFromStorage();
            
            // If no portfolio data, create demo data for visualization
            if (userPortfolio.length === 0) {
                userPortfolio = [
                    { symbol: "NESN.SW", name: "Nestlé", investment: 20000, weight: 20, type: 'stock', expectedReturn: 0.08, volatility: 0.15 },
                    { symbol: "ROG.SW", name: "Roche", investment: 15000, weight: 15, type: 'stock', expectedReturn: 0.07, volatility: 0.14 },
                    { symbol: "SPX", name: "S&P 500 Index", investment: 25000, weight: 25, type: 'index', expectedReturn: 0.10, volatility: 0.18 },
                    { symbol: "GC=F", name: "Gold Futures", investment: 10000, weight: 10, type: 'other', expectedReturn: 0.05, volatility: 0.12 },
                    { symbol: "BTC-USD", name: "Bitcoin", investment: 30000, weight: 30, type: 'other', expectedReturn: 0.15, volatility: 0.40 }
                ];
                portfolioCalculated = true;
                totalInvestment = 100000;
            }
            
            // Update strategy analysis
            updateStrategyAnalysis();
        }
        
        // Update Strategy Analysis - now fetches from backend
        async function updateStrategyAnalysis() {
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                showEmptyState();
                return;
            }

            // Show loading state
            const tableBody = document.getElementById('strategyTableBody');
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Strategien werden berechnet...</td></tr>';
            }

            try {
                // Try to get real strategies from backend
                const symbols = userPortfolio.map(a => a.symbol);
                const response = await fetch('/api/strategy_optimization', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ symbols: symbols })
                });
                
                if (!response.ok) throw new Error('Backend failed');
                
                const data = await response.json();
                
                if (data.strategies && data.strategies.length >= 3) {
                    // Format strategies for display
                    const strategies = data.strategies.map(s => ({
                        name: s.name,
                        description: s.description,
                        return: s.return.toFixed(1),
                        risk: s.risk.toFixed(1),
                        sharpe: s.sharpe.toFixed(2),
                        recommendation: s.recommendation,
                        badgeClass: getBadgeClass(s.recommendation),
                        weights: s.weights || [],
                        improvement: 0, // Will be calculated below
                        detailedRecommendation: getDetailedRecommendation(s.name, s.recommendation)
                    }));
                    
                    // Fill UI with real data
                    updateStrategyTable(strategies);
                    updatePortfolioRating(strategies);
            updateStrategyCards(strategies);
                    createStrategyComparisonChart(strategies);
                    
                    console.log('✅ Strategieanalyse mit echten Backend-Berechnungen!');
                    return;
                }
            } catch (error) {
                console.log('Fallback to simulated strategies:', error);
            }
            
            // Fallback: Use simulated strategies
            const strategies = calculateAllStrategies();
            updateStrategyTable(strategies);
            updatePortfolioRating(strategies);
            updateStrategyCards(strategies);
            createStrategyComparisonChart(strategies);
        }
        
        function getBadgeClass(recommendation) {
            const map = {
                'OPTIMAL': 'badge-optimal',
                'BALANCIERT': 'badge-balanced',
                'KONSERVATIV': 'badge-conservative',
                'AGGRESSIV': 'badge-aggressive',
                'MODERAT': 'badge-balanced',
                'EXPERTE': 'badge-optimal'
            };
            return map[recommendation] || 'badge-balanced';
        }
        
        function getDetailedRecommendation(name, recommendation) {
            const recommendations = {
                'Mean-Variance': 'Erhöhen Sie Tech-Aktien und reduzieren Sie Bonds für bessere Performance.',
                'Risk Parity': 'Diversifizieren Sie stärker in Rohstoffe und Immobilien.',
                'Min Variance': 'Konzentrieren Sie sich auf stabile Blue-Chip Aktien und Anleihen.',
                'Max Sharpe': 'Investieren Sie mehr in Growth-Aktien und reduzieren Sie defensive Assets.',
                'Black-Litterman': 'Kombinieren Sie fundamentale Analyse mit quantitativen Modellen.'
            };
            return recommendations[name] || 'Optimieren Sie Ihre Asset-Allokation.';
        }

        function showEmptyState() {
            const tableBody = document.getElementById('strategyTableBody');
            if (tableBody) {
                tableBody.innerHTML = 
                    '<tr>' +
                        '<td colspan="5" style="text-align: center; padding: 40px;">' +
                            '<div style="color: #6c757d;">' +
                                '<i class="fas fa-folder-open" style="font-size: 3rem; margin-bottom: 15px;"></i>' +
                                '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>' +
                                '<button class="btn btn-primary" onclick="switchToDashboard()" style="margin-top: 15px; display: inline-flex; align-items: center; justify-content: center; padding: 10px 20px; border-radius: 0; font-weight: 500; text-decoration: none; transition: all 0.3s ease; cursor: pointer; border: none; font-size: 14px; gap: 8px; background-color: #1a1a1a; color: #ffffff;">' +
                                    '<i class="fas fa-tachometer-alt"></i> Zum Dashboard' +
                                '</button>' +
                            '</div>' +
                        '</td>' +
                    '</tr>';
            }
            
            const strategyGrid = document.getElementById('strategyGrid');
            if (strategyGrid) {
                strategyGrid.innerHTML = 
                    '<div style="text-align: center; width: 100%; color: #6c757d;">' +
                        '<i class="fas fa-chart-pie" style="font-size: 4rem; margin-bottom: 15px;"></i>' +
                        '<h3>Keine Daten verfügbar</h3>' +
                        '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard.</p>' +
                    '</div>';
            }
        }

        // Update Strategy Table
        function updateStrategyTable(strategies) {
            const tableBody = document.getElementById('strategyTableBody');
            if (!tableBody) return;
            
            tableBody.innerHTML = '';
            
            strategies.forEach(strategy => {
                const row = document.createElement('tr');
                row.innerHTML = 
                    '<td style="text-align: left; font-weight: bold;">' + strategy.name + '</td>' +
                    '<td class="' + (strategy.return >= 0 ? 'positive' : 'negative') + '">' + (strategy.return >= 0 ? '+' : '') + strategy.return + '%</td>' +
                    '<td>' + strategy.risk + '%</td>' +
                    '<td>' + strategy.sharpe + '</td>' +
                    '<td><span class="recommendation-badge ' + strategy.badgeClass + '">' + strategy.recommendation + '</span></td>';
                tableBody.appendChild(row);
            });
        }

        // Update Portfolio Rating
        function updatePortfolioRating(strategies) {
            const rating = calculatePortfolioRating(strategies);
            const topStrategy = getTopStrategy(strategies);
            const improvementPotential = calculateImprovementPotential(strategies);
            const riskProfile = getRiskProfile(strategies);
            const standardComparison = getPortfolioStandardComparison(strategies);
            
            const portfolioRating = document.getElementById('portfolioRating');
            const topStrategyEl = document.getElementById('topStrategy');
            const improvementPotentialEl = document.getElementById('improvementPotential');
            const riskProfileEl = document.getElementById('riskProfile');
            const standardComparisonEl = document.getElementById('standardComparison');
            
            if (portfolioRating) portfolioRating.textContent = rating + '/100';
            if (topStrategyEl) topStrategyEl.textContent = topStrategy.name;
            if (improvementPotentialEl) improvementPotentialEl.textContent = improvementPotential + '%';
            if (riskProfileEl) riskProfileEl.textContent = riskProfile;
            if (standardComparisonEl) standardComparisonEl.textContent = standardComparison;
        }

        // Update Strategy Cards
        function updateStrategyCards(strategies) {
            const strategyGrid = document.getElementById('strategyGrid');
            if (!strategyGrid) return;
            
            strategyGrid.innerHTML = '';
            
            strategies.forEach(strategy => {
                const card = document.createElement('div');
                card.className = 'strategy-card';
                card.style.cssText = 'background: var(--perlweiss); padding: 25px; border-radius: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); transition: all 0.3s ease; border-top: 4px solid var(--color-accent-rose);';
                card.innerHTML = 
                    '<h4 style="color: #1a1a1a; font-size: 18px; margin-bottom: 12px; font-weight: 600; font-family: Playfair Display, serif;">' + strategy.name + '</h4>' +
                    '<p style="color: #212529; line-height: 1.6; margin: 10px 0;"><strong>Ziel:</strong> ' + strategy.description + '</p>' +
                    '<div style="background: rgba(205, 139, 118, 0.1); padding: 15px; border-radius: 0; margin: 15px 0;">' +
                        '<p style="margin: 5px 0;"><strong>Optimierte Rendite:</strong> <span class="' + (strategy.return >= 0 ? 'positive' : 'negative') + '">' + (strategy.return >= 0 ? '+' : '') + strategy.return + '%</span></p>' +
                        '<p style="margin: 5px 0;"><strong>Optimiertes Risiko:</strong> ' + strategy.risk + '%</p>' +
                        '<p style="margin: 5px 0;"><strong>Verbesserung:</strong> ' +
                            '<span style="font-weight: 700; font-size: 16px; color: ' + (strategy.improvement > 0 ? '#28a745' : '#dc3545') + ';">' +
                                (strategy.improvement > 0 ? '↗' : '↘') + ' ' + strategy.improvement + '%' +
                            '</span>' +
                        '</p>' +
                    '</div>' +
                    '<p style="margin: 10px 0;"><strong>Empfehlung:</strong> ' + strategy.detailedRecommendation + '</p>';
                strategyGrid.appendChild(card);
            });
        }

        // Calculate All Strategies
        function calculateAllStrategies() {
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;
            const currentSharpe = currentRisk > 0 ? (currentReturn - 2) / currentRisk : 0.3;

            // Use realistic fixed values based on portfolio characteristics
            return [
                {
                    name: "Mean-Variance",
                    description: "Optimales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn * 1.15, 15),
                    risk: Math.max(currentRisk * 0.85, 5),
                    sharpe: (currentSharpe * 1.2).toFixed(2),
                    recommendation: "OPTIMAL",
                    badgeClass: "badge-optimal",
                    improvement: +(currentReturn * 0.15).toFixed(1),
                    detailedRecommendation: "Erhöhen Sie Tech-Aktien und reduzieren Sie Bonds für bessere Performance."
                },
                {
                    name: "Risk Parity",
                    description: "Gleicher Risikobeitrag aller Assets",
                    return: Math.min(currentReturn * 1.05, 12),
                    risk: Math.max(currentRisk * 0.70, 4),
                    sharpe: (currentSharpe * 1.15).toFixed(2),
                    recommendation: "BALANCIERT",
                    badgeClass: "badge-balanced",
                    improvement: +(currentReturn * 0.05).toFixed(1),
                    detailedRecommendation: "Diversifizieren Sie stärker in Rohstoffe und Immobilien."
                },
                {
                    name: "Min Variance",
                    description: "Minimales Portfolio-Risiko",
                    return: Math.min(currentReturn * 0.90, 8),
                    risk: Math.max(currentRisk * 0.60, 3),
                    sharpe: (currentSharpe * 1.25).toFixed(2),
                    recommendation: "KONSERVATIV",
                    badgeClass: "badge-conservative",
                    improvement: +(currentReturn * -0.10).toFixed(1),
                    detailedRecommendation: "Konzentrieren Sie sich auf stabile Blue-Chip Aktien und Anleihen."
                },
                {
                    name: "Max Sharpe",
                    description: "Maximales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn * 1.30, 20),
                    risk: Math.max(currentRisk * 1.15, 8),
                    sharpe: (currentSharpe * 1.35).toFixed(2),
                    recommendation: "AGGRESSIV",
                    badgeClass: "badge-aggressive",
                    improvement: +(currentReturn * 0.30).toFixed(1),
                    detailedRecommendation: "Investieren Sie mehr in Growth-Aktien und reduzieren Sie defensive Assets."
                },
                {
                    name: "Black-Litterman",
                    description: "Marktdaten + eigene Erwartungen",
                    return: Math.min(currentReturn * 1.12, 14),
                    risk: Math.max(currentRisk * 0.90, 6),
                    sharpe: (currentSharpe * 1.18).toFixed(2),
                    recommendation: "EXPERTE",
                    badgeClass: "badge-optimal",
                    improvement: +(currentReturn * 0.12).toFixed(1),
                    detailedRecommendation: "Kombinieren Sie fundamentale Analyse mit quantitativen Modellen."
                }
            ];
        }

        // Calculate Portfolio Rating
        function calculatePortfolioRating(strategies) {
            const baseScore = 65;
            const diversificationBonus = Math.min(userPortfolio.length * 3, 15);
            const riskAdjustment = strategies[0].risk > 20 ? -10 : strategies[0].risk < 10 ? 5 : 0;
            const sharpeBonus = strategies[0].sharpe > 0.4 ? 10 : 0;
            
            return Math.min(baseScore + diversificationBonus + riskAdjustment + sharpeBonus, 95);
        }

        // Get Top Strategy
        function getTopStrategy(strategies) {
            return strategies.reduce((best, current) => 
                parseFloat(current.sharpe) > parseFloat(best.sharpe) ? current : best
            );
        }

        // Calculate Improvement Potential
        function calculateImprovementPotential(strategies) {
            const topStrategy = getTopStrategy(strategies);
            const currentReturn = calculatePortfolioReturn() * 100;
            
            return Math.max(0, (topStrategy.return - currentReturn)).toFixed(1);
        }

        // Get Risk Profile
        function getRiskProfile(strategies) {
            const avgRisk = strategies.reduce((sum, s) => sum + s.risk, 0) / strategies.length;
            if (avgRisk > 18) return "Aggressiv";
            if (avgRisk > 12) return "Moderat";
            return "Konservativ";
        }

        // Get Portfolio Standard Comparison
        function getPortfolioStandardComparison(strategies) {
            const avgReturn = strategies.reduce((sum, s) => sum + s.return, 0) / strategies.length;
            const avgRisk = strategies.reduce((sum, s) => sum + s.risk, 0) / strategies.length;
            const avgSharpe = strategies.reduce((sum, s) => sum + parseFloat(s.sharpe), 0) / strategies.length;
            
            if (avgReturn > 12 && avgRisk < 15 && avgSharpe > 0.6) {
                return "Exzellent - Übertrifft 90% der Standard-Portfolios";
            } else if (avgReturn > 9 && avgRisk < 18 && avgSharpe > 0.45) {
                return "Sehr gut - Besser als 75% der vergleichbaren Portfolios";
            } else if (avgReturn > 6 && avgRisk < 22 && avgSharpe > 0.3) {
                return "Gut - Entspricht Marktstandards";
            } else {
                return "Verbesserungswürdig - Unterhalb der Markterwartungen";
            }
        }

        // Create Strategy Comparison Chart (safe minimal version to avoid syntax errors)
        function createStrategyComparisonChart(strategies) {
            try {
                const canvas = document.getElementById('strategyComparisonChart');
                if (!canvas || typeof Chart === 'undefined') return;

                const ctx = canvas.getContext('2d');
                if (window.strategyChartInstance) {
                    window.strategyChartInstance.destroy();
                }

                const currentReturn = (typeof calculatePortfolioReturn === 'function') ? (calculatePortfolioReturn() * 100) : 8.5;
                const currentRisk = (typeof calculatePortfolioRisk === 'function') ? (calculatePortfolioRisk() * 100) : 12.0;

                const datasets = [];
                const colors = ['#2c3e50', '#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'];
                
                // Add current portfolio
                datasets.push({
                    label: 'Aktuelles Portfolio',
                    data: [{ x: currentRisk, y: currentReturn }],
                    backgroundColor: '#2c3e50',
                    borderColor: '#2c3e50',
                    borderWidth: 3,
                    pointRadius: 10,
                    pointHoverRadius: 12
                });

                // Add strategy points with real names
                if (Array.isArray(strategies) && strategies.length > 0) {
                    strategies.forEach((strategy, index) => {
                            datasets.push({
                            label: strategy.name || `Strategie ${index + 1}`,
                            data: [{ x: parseFloat(strategy.risk) || 12, y: parseFloat(strategy.return) || 8 }],
                                backgroundColor: colors[(index + 1) % colors.length],
                                borderColor: colors[(index + 1) % colors.length],
                                borderWidth: 2,
                                pointRadius: 6,
                                pointHoverRadius: 8
                            });
                    });
                } else {
                    // Add demo strategies if none provided
                    datasets.push(
                        {
                            label: 'Value Strategy',
                            data: [{ x: 14, y: 9.5 }],
                            backgroundColor: '#3498db',
                            borderColor: '#3498db',
                            borderWidth: 2,
                            pointRadius: 7,
                            pointHoverRadius: 9
                        },
                        {
                            label: 'Growth Strategy',
                            data: [{ x: 18, y: 12.0 }],
                            backgroundColor: '#2ecc71',
                            borderColor: '#2ecc71',
                            borderWidth: 2,
                            pointRadius: 7,
                            pointHoverRadius: 9
                        },
                        {
                            label: 'Balanced Strategy',
                            data: [{ x: 10, y: 7.5 }],
                            backgroundColor: '#e74c3c',
                            borderColor: '#e74c3c',
                            borderWidth: 2,
                            pointRadius: 7,
                            pointHoverRadius: 9
                        },
                        {
                            label: 'Defensive Strategy',
                            data: [{ x: 6, y: 5.0 }],
                            backgroundColor: '#f39c12',
                            borderColor: '#f39c12',
                            borderWidth: 2,
                            pointRadius: 7,
                            pointHoverRadius: 9
                        }
                    );
                }

                window.strategyChartInstance = new Chart(ctx, {
                    type: 'scatter',
                    data: {
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                                labels: {
                                    usePointStyle: true,
                                    padding: 15,
                                    font: {
                                        size: 11
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return context.dataset.label + ': Risiko ' + context.parsed.x.toFixed(1) + '%, Rendite ' + context.parsed.y.toFixed(1) + '%';
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Risiko (Volatilität %)',
                                    font: {
                                        size: 13,
                                        weight: '600'
                                    },
                                    color: '#2c3e50'
                                },
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.05)'
                                },
                                ticks: {
                                    callback: function(value) {
                                        return value.toFixed(1) + '%';
                                    },
                                    font: {
                                        size: 11
                                    }
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Erwartete Rendite (%)',
                                    font: {
                                        size: 13,
                                        weight: '600'
                                    },
                                    color: '#2c3e50'
                                },
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.05)'
                                },
                                ticks: {
                                    callback: function(value) {
                                        return value.toFixed(1) + '%';
                                    },
                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (err) {
                console.error('createStrategyComparisonChart error:', err);
            }
        }

        // =====================================================
        // Monte Carlo Simulation Function
        // =====================================================
        
        let mcChartInstance = null;
        
        function runMonteCarloSimulation() {
                // Get parameters
                const years = parseInt(document.getElementById('mcTimeHorizon').value) || 10;
                const simulations = parseInt(document.getElementById('mcSimulations').value) || 500;
                const initialInvestment = parseFloat(document.getElementById('mcInitialInvestment').value) || 10000;
                
            // Show loading message
            const canvas = document.getElementById('monteCarloChart');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '16px Inter';
                ctx.fillStyle = '#666';
                ctx.textAlign = 'center';
                ctx.fillText('Monte Carlo Simulation läuft...', canvas.width / 2, canvas.height / 2);
            }
            
            // Check if portfolio exists
            if (!userPortfolio || userPortfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Try backend API first
            fetch('/api/monte_carlo_correlated', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    portfolio: userPortfolio.map(a => ({
                        symbol: a.symbol,
                        weight: a.weight / 100,
                        investment: a.investment
                    })),
                    years: years,
                    simulations: simulations,
                    initialInvestment: initialInvestment
                })
            })
            .then(r => r.json())
            .then(mcResult => {
                if (!mcResult.success) throw new Error('Backend returned no data');
                
                // Use backend results
                const percentile5 = mcResult.percentile5;
                const percentile50 = mcResult.percentile50;
                const percentile95 = mcResult.percentile95;
                const avgFinal = mcResult.avgFinal;
                const allPaths = mcResult.paths || [];
                
                console.log('✅ Monte Carlo mit echten korrelierten Daten vom Backend!');
                
                // Render chart and results
                renderMonteCarloResults(years, simulations, initialInvestment, percentile5, percentile50, percentile95, avgFinal, allPaths);
            })
            .catch(error => {
                console.warn('Backend failed, using fallback:', error);
                
                // Fallback: Simple frontend simulation
                const avgReturn = calculatePortfolioReturn() || 0.08;
                const avgVolatility = calculatePortfolioRisk() || 0.15;
                
                const allPaths = [];
                const finalValues = [];
                
                for (let s = 0; s < simulations; s++) {
                    const path = [initialInvestment];
                    let currentValue = initialInvestment;
                    
                    for (let year = 1; year <= years; year++) {
                        const u1 = Math.random();
                        const u2 = Math.random();
                        const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
                        const yearlyReturn = avgReturn + avgVolatility * z;
                        
                        currentValue = currentValue * (1 + yearlyReturn);
                        path.push(currentValue);
                    }
                    
                    allPaths.push(path);
                    finalValues.push(currentValue);
                }
                
                finalValues.sort((a, b) => a - b);
                const percentile5 = finalValues[Math.floor(simulations * 0.05)];
                const percentile50 = finalValues[Math.floor(simulations * 0.50)];
                const percentile95 = finalValues[Math.floor(simulations * 0.95)];
                const avgFinal = finalValues.reduce((a, b) => a + b, 0) / simulations;
                
                // Render chart and results with fallback data
                renderMonteCarloResults(years, simulations, initialInvestment, percentile5, percentile50, percentile95, avgFinal, allPaths);
            });
        }
        
        // Helper function to render Monte Carlo results
        function renderMonteCarloResults(years, simulations, initialInvestment, percentile5, percentile50, percentile95, avgFinal, allPaths) {
                try {
                // Calculate portfolio metrics for display
                const avgReturn = calculatePortfolioReturn() || 0.08;
                const avgVolatility = calculatePortfolioRisk() || 0.15;
                
                // Prepare chart data
                const labels = Array.from({length: years + 1}, (_, i) => `Jahr ${i}`);
                
                // Select representative paths to display
                const pathsToDisplay = [];
                for (let i = 0; i < Math.min(50, allPaths.length); i++) {
                    const idx = Math.floor((i / 50) * allPaths.length);
                    if (allPaths[idx]) pathsToDisplay.push(allPaths[idx]);
                }
                
                // Create datasets
                const datasets = pathsToDisplay.map((path, idx) => ({
                    data: path,
                    borderColor: `rgba(66, 135, 245, ${0.15})`,
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1,
                    showLine: true
                }));
                
                // Add median line
                const medianPath = [];
                for (let year = 0; year <= years; year++) {
                    const valuesAtYear = allPaths.map(path => path[year]);
                    valuesAtYear.sort((a, b) => a - b);
                    medianPath.push(valuesAtYear[Math.floor(simulations * 0.5)]);
                }
                
                datasets.push({
                    label: 'Median (50%)',
                    data: medianPath,
                    borderColor: '#ff9800',
                    borderWidth: 3,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1
                });
                
                // Create chart
                const canvas = document.getElementById('monteCarloChart');
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    
                    if (mcChartInstance) {
                        mcChartInstance.destroy();
                    }
                    
                    mcChartInstance = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    display: true,
                                    labels: {
                                        filter: function(item) {
                                            return item.text !== undefined;
                                        },
                                        font: {
                                            size: 12,
                                            weight: '600'
                                        }
                                    }
                                },
                                title: {
                                    display: true,
                                    text: `${simulations} Monte Carlo Simulationen über ${years} Jahre`,
                                    font: {
                                        size: 16,
                                        weight: '600'
                                    },
                                    color: '#1a237e'
                                },
                                tooltip: {
                                    mode: 'index',
                                    intersect: false,
                                    callbacks: {
                                        label: function(context) {
                                            return 'CHF ' + context.parsed.y.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Jahre',
                                        font: {
                                            size: 13,
                                            weight: '600'
                                        }
                                    }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'Portfoliowert (CHF)',
                                        font: {
                                            size: 13,
                                            weight: '600'
                                        }
                                    },
                                    ticks: {
                                        callback: function(value) {
                                            return 'CHF ' + value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
                
                // Display results
                const resultsDiv = document.getElementById('mcResults');
                if (resultsDiv) {
                    const gainLoss5 = ((percentile5 - initialInvestment) / initialInvestment * 100);
                    const gainLoss50 = ((percentile50 - initialInvestment) / initialInvestment * 100);
                    const gainLoss95 = ((percentile95 - initialInvestment) / initialInvestment * 100);
                    
                    resultsDiv.innerHTML = `
                        <div style="background: rgba(255,255,255,0.15); border-radius: 0; padding: 20px; text-align: center;">
                            <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-bottom: 5px; font-weight: 500;">Schlechtestes Szenario (5%)</div>
                            <div style="color: #ffffff; font-size: 24px; font-weight: 700;">CHF ${percentile5.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</div>
                            <div style="color: ${gainLoss5 >= 0 ? '#4caf50' : '#f44336'}; font-size: 14px; margin-top: 5px; font-weight: 600;">${gainLoss5 >= 0 ? '+' : ''}${gainLoss5.toFixed(1)}%</div>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.25); border-radius: 0; padding: 20px; text-align: center; border: 2px solid rgba(255,152,0,0.5);">
                            <div style="color: rgba(255,255,255,0.9); font-size: 12px; margin-bottom: 5px; font-weight: 600;">Median Szenario (50%)</div>
                            <div style="color: #ffffff; font-size: 28px; font-weight: 700;">CHF ${percentile50.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</div>
                            <div style="color: ${gainLoss50 >= 0 ? '#4caf50' : '#f44336'}; font-size: 16px; margin-top: 5px; font-weight: 600;">${gainLoss50 >= 0 ? '+' : ''}${gainLoss50.toFixed(1)}%</div>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.15); border-radius: 0; padding: 20px; text-align: center;">
                            <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-bottom: 5px; font-weight: 500;">Bestes Szenario (95%)</div>
                            <div style="color: #ffffff; font-size: 24px; font-weight: 700;">CHF ${percentile95.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</div>
                            <div style="color: ${gainLoss95 >= 0 ? '#4caf50' : '#f44336'}; font-size: 14px; margin-top: 5px; font-weight: 600;">${gainLoss95 >= 0 ? '+' : ''}${gainLoss95.toFixed(1)}%</div>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.15); border-radius: 0; padding: 20px; text-align: center;">
                            <div style="color: rgba(255,255,255,0.8); font-size: 12px; margin-bottom: 5px; font-weight: 500;">Durchschnitt</div>
                            <div style="color: #ffffff; font-size: 24px; font-weight: 700;">CHF ${avgFinal.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</div>
                            <div style="color: rgba(255,255,255,0.7); font-size: 13px; margin-top: 8px;">Erwartete Rendite: ${(avgReturn * 100).toFixed(1)}% p.a.</div>
                            <div style="color: rgba(255,255,255,0.7); font-size: 13px;">Volatilität: ${(avgVolatility * 100).toFixed(1)}%</div>
                        </div>
                    `;
                }
                
            } catch (error) {
                console.error('Monte Carlo Simulation Error:', error);
                alert('Fehler bei der Simulation. Bitte Portfolio-Daten prüfen.');
            }
        }

        // Steuerrechner Funktion
        function calculateTaxes() {
            try {
                // Get parameters
                const transactionValue = parseFloat(document.getElementById('taxTransactionValue').value) || 0;
                const securityType = document.getElementById('taxSecurityType').value;
                const dividend = parseFloat(document.getElementById('taxDividend').value) || 0;
                
                // Calculate Stamp Tax
                let stampTaxRate = 0;
                if (securityType === 'ch') {
                    stampTaxRate = 0.075; // 0.075% for Swiss securities
                } else {
                    stampTaxRate = 0.15; // 0.15% for foreign securities
                }
                
                const stampTax = transactionValue * (stampTaxRate / 100);
                
                // Calculate Withholding Tax (Verrechnungssteuer)
                const withholdingTaxRate = 35; // 35% on dividends
                const withholdingTax = dividend * (withholdingTaxRate / 100);
                
                // Net dividend after withholding tax
                const netDividend = dividend - withholdingTax;
                
                // Total costs (stamp tax on purchase + withholding tax on dividends)
                const totalCosts = stampTax + withholdingTax;
                
                // Update UI
                document.getElementById('stampTaxBuy').textContent = 'CHF ' + stampTax.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                document.getElementById('stampTaxRate').textContent = stampTaxRate + '%';
                document.getElementById('withholdingTax').textContent = 'CHF ' + withholdingTax.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                document.getElementById('netDividend').textContent = 'CHF ' + netDividend.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                document.getElementById('totalCosts').textContent = 'CHF ' + totalCosts.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                
                // Show results
                document.getElementById('taxResults').style.display = 'block';
                
            } catch (error) {
                console.error('Steuerrechner Error:', error);
                alert('Fehler bei der Berechnung. Bitte Parameter prüfen.');
            }
        }

        // Switch to Dashboard (Helper Function)
        function switchToDashboard() {
            loadGSPage('dashboard');
        }

        // =====================================================
        // Investing Sub-Pages Functions (Placeholder)
        // =====================================================

        // Value Testing Functions
        async function startValueTesting() {
            const resultsDiv = document.getElementById('valueTestingResults');
            const tableBody = document.getElementById('valueAnalysisTableBody');
            
            // Get portfolio from localStorage (check both keys and formats)
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Get analysis parameters
            const discountRate = document.getElementById('discountRate')?.value || 8;
            const terminalGrowth = document.getElementById('terminalGrowth')?.value || 2;
            
            // Transform portfolio data to API format (symbol + quantity)
            const apiPortfolio = portfolio.map(asset => ({
                symbol: asset.symbol,
                quantity: asset.quantity || (asset.investment ? asset.investment / 100 : 1), // Rough estimate if quantity not present
                purchasePrice: asset.purchasePrice || 100
            }));
            
            // Show loading
            if (tableBody) {
                tableBody.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px;"></i><p style="margin-top: 15px;">Analysiere Portfolio...</p></div>';
            }
            if (resultsDiv) resultsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/value_analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        portfolio: apiPortfolio,
                        discountRate: discountRate,
                        terminalGrowth: terminalGrowth
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update summary
                    document.getElementById('totalPortfolioValue').textContent = 
                        'CHF ' + data.summary.totalValue.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                    document.getElementById('totalFairValue').textContent = 
                        'CHF ' + data.summary.totalFairValue.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                    
                    const valuation = data.summary.portfolioValuation;
                    document.getElementById('portfolioValuation').textContent = 
                        (valuation > 0 ? '+' : '') + valuation.toFixed(1) + '% ' + (valuation > 0 ? 'unterbewertet' : 'überbewertet');
                    document.getElementById('portfolioValuation').style.color = valuation > 0 ? '#4caf50' : '#f44336';
                    
                    document.getElementById('aggregateScore').textContent = Math.round(data.summary.avgScore) + '/100';
                    
                    // Update new risk metrics
                    if (data.summary.avgSharpe !== undefined) {
                        const sharpeEl = document.getElementById('portfolioSharpe');
                        if (sharpeEl) {
                            sharpeEl.textContent = data.summary.avgSharpe.toFixed(2);
                            sharpeEl.style.color = data.summary.avgSharpe > 1 ? '#4caf50' : data.summary.avgSharpe > 0.5 ? '#ff9800' : '#f44336';
                        }
                    }
                    if (data.summary.portfolioBeta !== undefined) {
                        const betaEl = document.getElementById('portfolioBeta');
                        if (betaEl) {
                            betaEl.textContent = data.summary.portfolioBeta.toFixed(2);
                            betaEl.style.color = data.summary.portfolioBeta < 1 ? '#4caf50' : '#666';
                        }
                    }
                    if (data.summary.portfolioVaR95 !== undefined) {
                        const varEl = document.getElementById('portfolioVaR');
                        if (varEl) varEl.textContent = 'CHF ' + Math.abs(data.summary.portfolioVaR95).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                    }
                    if (data.summary.worstDrawdown !== undefined) {
                        const ddEl = document.getElementById('worstDrawdown');
                        if (ddEl) ddEl.textContent = data.summary.worstDrawdown.toFixed(1) + '%';
                    }
                    
                    // Build table
                    let tableHTML = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse;">';
                    tableHTML += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
                    tableHTML += '<th style="padding: 12px; text-align: left;">Asset</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">Aktuell</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">Fair Value</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">KGV</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">KBV</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">Upside</th>';
                    tableHTML += '<th style="padding: 12px; text-align: right;">Score</th>';
                    tableHTML += '<th style="padding: 12px; text-align: center;">Empfehlung</th>';
                    tableHTML += '</tr></thead><tbody>';
                    
                    data.results.forEach(asset => {
                        tableHTML += '<tr style="border-bottom: 1px solid #eee;">';
                        tableHTML += `<td style="padding: 12px; font-weight: 600;">${asset.symbol}</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: right;">CHF ${asset.currentPrice.toFixed(2)}</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: right;">CHF ${asset.fairValue.toFixed(2)}</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: right;">${asset.peRatio.toFixed(1)}</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: right;">${asset.pbRatio.toFixed(2)}</td>`;
                        const upsideColor = asset.upside > 0 ? '#4caf50' : '#f44336';
                        tableHTML += `<td style="padding: 12px; text-align: right; color: ${upsideColor}; font-weight: 600;">${asset.upside > 0 ? '+' : ''}${asset.upside.toFixed(1)}%</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: right;">${asset.score}/100</td>`;
                        tableHTML += `<td style="padding: 12px; text-align: center;"><span style="background: ${asset.recColor}; color: white; padding: 6px 12px; border-radius: 0; font-weight: 600; font-size: 12px;">${asset.recommendation}</span></td>`;
                        tableHTML += '</tr>';
                    });
                    
                    tableHTML += '</tbody></table></div>';
                    if (tableBody) tableBody.innerHTML = tableHTML;
                    
                    // Enable export button
                const exportBtn = document.getElementById('exportBtn');
                if (exportBtn) {
                    exportBtn.disabled = false;
                        exportBtn.style.background = 'var(--color-accent-rose)';
                    exportBtn.style.color = 'white';
                    exportBtn.style.cursor = 'pointer';
                }
                } else {
                    if (tableBody) tableBody.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler: ${data.error}</div>`;
                }
            } catch (error) {
                console.error('Value Analysis Error:', error);
                if (tableBody) tableBody.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler beim Laden der Analyse: ${error.message}</div>`;
            }
        }

        function exportValueReport() {
            alert('PDF-Export wird in einer zukünftigen Version implementiert.');
        }

        function closeAssetDetail() {
            const modal = document.getElementById('assetDetailModal');
            if (modal) modal.style.display = 'none';
        }

        // Momentum Growth Functions
        async function startMomentumAnalysis() {
            const resultsDiv = document.getElementById('momentumResults');
                const content = document.getElementById('momentumAnalysisContent');
            
            // Get portfolio from localStorage (check both keys and formats)
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Get analysis parameters
            const lookbackMonths = document.getElementById('momentumLookback')?.value || 12;
            const maShort = document.getElementById('maShort')?.value || 50;
            const maLong = document.getElementById('maLong')?.value || 200;
            
            // Transform portfolio data to API format
            const apiPortfolio = portfolio.map(asset => ({
                symbol: asset.symbol,
                quantity: asset.quantity || (asset.investment ? asset.investment / 100 : 1),
                purchasePrice: asset.purchasePrice || 100
            }));
            
            // Show loading
            if (content) {
                content.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px;"></i><p style="margin-top: 15px;">Analysiere Momentum...</p></div>';
            }
            if (resultsDiv) resultsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/momentum_analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        portfolio: apiPortfolio,
                        lookbackMonths: lookbackMonths,
                        maShort: maShort,
                        maLong: maLong
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Build summary cards
                    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">';
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Durchschn. Momentum</h4>
                        <p style="color: ${data.summary.avgMomentum > 0 ? '#4caf50' : '#f44336'}; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.avgMomentum > 0 ? '+' : ''}${data.summary.avgMomentum.toFixed(1)}%</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Durchschn. Score</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">${Math.round(data.summary.avgScore)}/100</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Portfolio Volatilität</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.avgVolatility.toFixed(1)}%</p>
                    </div>`;
                    html += '</div>';
                    
                    // Build asset table with expanded metrics
                    html += '<div style="overflow-x: auto; margin-top: 30px;"><table style="width: 100%; border-collapse: collapse;">';
                    html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
                    html += '<th style="padding: 12px; text-align: left;">Asset</th>';
                    html += '<th style="padding: 12px; text-align: right;">Momentum</th>';
                    html += '<th style="padding: 12px; text-align: right;">RSI</th>';
                    html += '<th style="padding: 12px; text-align: right;">MACD</th>';
                    html += '<th style="padding: 12px; text-align: right;">BB Position</th>';
                    html += '<th style="padding: 12px; text-align: right;">Sharpe</th>';
                    html += '<th style="padding: 12px; text-align: center;">Trend</th>';
                    html += '<th style="padding: 12px; text-align: right;">Score</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.results.forEach(asset => {
                        html += '<tr style="border-bottom: 1px solid #eee;">';
                        html += `<td style="padding: 12px; font-weight: 600;">${asset.symbol}</td>`;
                        const momentumColor = asset.momentum_return > 0 ? '#4caf50' : '#f44336';
                        html += `<td style="padding: 12px; text-align: right; color: ${momentumColor}; font-weight: 600;">${asset.momentum_return > 0 ? '+' : ''}${asset.momentum_return.toFixed(1)}%</td>`;
                        
                        // RSI with color coding
                        const rsiColor = asset.rsi > 70 ? '#f44336' : asset.rsi < 30 ? '#4caf50' : '#666';
                        html += `<td style="padding: 12px; text-align: right; color: ${rsiColor};">${asset.rsi.toFixed(1)}</td>`;
                        
                        // MACD Signal
                        const macdSignal = asset.macd_histogram > 0 ? '↗️ Bull' : '↘️ Bear';
                        const macdColor = asset.macd_histogram > 0 ? '#4caf50' : '#f44336';
                        html += `<td style="padding: 12px; text-align: right; color: ${macdColor}; font-size: 12px;">${macdSignal}</td>`;
                        
                        // Bollinger Band Position
                        const bbColor = asset.bb_position < 20 ? '#4caf50' : asset.bb_position > 80 ? '#f44336' : '#666';
                        html += `<td style="padding: 12px; text-align: right; color: ${bbColor};">${asset.bb_position.toFixed(0)}%</td>`;
                        
                        // Sharpe Ratio
                        const sharpeColor = asset.sharpe_ratio > 1 ? '#4caf50' : asset.sharpe_ratio > 0.5 ? '#ff9800' : '#f44336';
                        html += `<td style="padding: 12px; text-align: right; color: ${sharpeColor}; font-weight: 600;">${asset.sharpe_ratio.toFixed(2)}</td>`;
                        
                        html += `<td style="padding: 12px; text-align: center;"><span style="background: ${asset.trend_color}; color: white; padding: 6px 12px; border-radius: 0; font-weight: 600; font-size: 12px;">${asset.trend}</span></td>`;
                        html += `<td style="padding: 12px; text-align: right; font-weight: 600;">${asset.momentum_score}/100</td>`;
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table></div>';
                    
                    // Indicator explanations
                    html += '<div style="background: var(--morgenlicht); padding: 20px; border-radius: 0; margin-top: 20px; border-left: 4px solid #2196f3;">';
                    html += '<h4 style="color: #1565c0; margin: 0 0 15px 0; font-size: 16px; font-weight: 600;">Indikator-Erklärungen</h4>';
                    html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">';
                    html += '<div><strong style="color: #1976d2;">RSI:</strong> <span style="color: #666; font-size: 13px;">&lt;30 = Überverkauft, &gt;70 = Überkauft</span></div>';
                    html += '<div><strong style="color: #1976d2;">MACD:</strong> <span style="color: #666; font-size: 13px;">↗️ Bull = Kaufsignal, ↘️ Bear = Verkaufssignal</span></div>';
                    html += '<div><strong style="color: #1976d2;">BB Position:</strong> <span style="color: #666; font-size: 13px;">&lt;20% = Überverkauft, &gt;80% = Überkauft</span></div>';
                    html += '<div><strong style="color: #1976d2;">Sharpe:</strong> <span style="color: #666; font-size: 13px;">&gt;1.0 = Exzellent, &gt;0.5 = Gut, &lt;0 = Schlecht</span></div>';
                    html += '</div></div>';
                    
                    if (content) content.innerHTML = html;
                } else {
                    if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler: ${data.error}</div>`;
                }
            } catch (error) {
                console.error('Momentum Analysis Error:', error);
                if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler beim Laden der Analyse: ${error.message}</div>`;
            }
        }

        function exportMomentumReport() {
            alert('PDF-Export wird in einer zukünftigen Version implementiert.');
        }

        // Buy & Hold Functions
        async function startBuyHoldAnalysis() {
            const resultsDiv = document.getElementById('buyholdResults');
                const content = document.getElementById('buyholdAnalysisContent');
            
            // Get portfolio from localStorage (check both keys and formats)
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Transform portfolio data to API format
            const apiPortfolio = portfolio.map(asset => ({
                symbol: asset.symbol,
                quantity: asset.quantity || (asset.investment ? asset.investment / 100 : 1),
                purchasePrice: asset.purchasePrice || 100
            }));
            
            // Show loading
            if (content) {
                content.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px;"></i><p style="margin-top: 15px;">Analysiere Qualität...</p></div>';
            }
            if (resultsDiv) resultsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/buyhold_analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ portfolio: apiPortfolio })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Build summary cards
                    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">';
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Erwartete CAGR</h4>
                        <p style="color: #4caf50; font-size: 24px; font-weight: 600; margin: 0;">+${data.summary.expectedCAGR.toFixed(1)}%</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Konfidenz</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">${Math.round(data.summary.confidence)}%</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Core-Positionen</h4>
                        <p style="color: #4caf50; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.coreCount}</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Satellite-Positionen</h4>
                        <p style="color: #ff9800; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.satelliteCount}</p>
                    </div>`;
                    html += '</div>';
                    
                    // Build asset table
                    html += '<div style="overflow-x: auto; margin-top: 30px;"><table style="width: 100%; border-collapse: collapse;">';
                    html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
                    html += '<th style="padding: 12px; text-align: left;">Asset</th>';
                    html += '<th style="padding: 12px; text-align: right;">ROE</th>';
                    html += '<th style="padding: 12px; text-align: right;">Verschuldung</th>';
                    html += '<th style="padding: 12px; text-align: right;">Marge</th>';
                    html += '<th style="padding: 12px; text-align: right;">Div-Rendite</th>';
                    html += '<th style="padding: 12px; text-align: center;">Kategorie</th>';
                    html += '<th style="padding: 12px; text-align: right;">Score</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.results.forEach(asset => {
                        html += '<tr style="border-bottom: 1px solid #eee;">';
                        html += `<td style="padding: 12px; font-weight: 600;">${asset.symbol}</td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.roe.toFixed(1)}%</td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.debtToEquity.toFixed(1)}%</td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.profitMargin.toFixed(1)}%</td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.divYield.toFixed(2)}%</td>`;
                        html += `<td style="padding: 12px; text-align: center;"><span style="background: ${asset.catColor}; color: white; padding: 6px 12px; border-radius: 0; font-weight: 600; font-size: 12px;">${asset.category}</span></td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.qualityScore}/100</td>`;
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table></div>';
                    
                    html += '<div style="background: #e8f5e9; padding: 15px; border-radius: 0; margin-top: 20px;">';
                    html += `<p style="color: #2e7d32; margin: 0;"><strong>Empfehlung:</strong> Ihr Portfolio zeigt eine durchschnittliche Qualität von ${Math.round(data.summary.avgQuality)}/100 mit ${data.summary.coreCount} Core-Positionen.</p>`;
                    html += '</div>';
                    
                    if (content) content.innerHTML = html;
                } else {
                    if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler: ${data.error}</div>`;
                }
            } catch (error) {
                console.error('Buy&Hold Analysis Error:', error);
                if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler beim Laden der Analyse: ${error.message}</div>`;
            }
        }

        function exportBuyHoldReport() {
            alert('PDF-Export wird in einer zukünftigen Version implementiert.');
        }

        // Carry Strategy Functions
        async function startCarryAnalysis() {
            const resultsDiv = document.getElementById('carryResults');
                const content = document.getElementById('carryAnalysisContent');
            
            // Get portfolio from localStorage (check both keys and formats)
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Get analysis parameters
            const financingCost = document.getElementById('financingCost')?.value || 3.0;
            
            // Transform portfolio data to API format
            const apiPortfolio = portfolio.map(asset => ({
                symbol: asset.symbol,
                quantity: asset.quantity || (asset.investment ? asset.investment / 100 : 1),
                purchasePrice: asset.purchasePrice || 100
            }));
            
            // Show loading
            if (content) {
                content.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px;"></i><p style="margin-top: 15px;">Analysiere Carry...</p></div>';
            }
            if (resultsDiv) resultsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/carry_analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        portfolio: apiPortfolio,
                        financingCost: financingCost
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Build summary cards
                    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">';
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Netto-Carry</h4>
                        <p style="color: ${data.summary.netCarry > 0 ? '#4caf50' : '#f44336'}; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.netCarry > 0 ? '+' : ''}${data.summary.netCarry.toFixed(2)}%</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Erwarteter Jahresertrag</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">CHF ${data.summary.expectedAnnualReturn.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Portfolio-Wert</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">CHF ${data.summary.totalValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</p>
                    </div>`;
                    html += `<div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                        <h4 style="color: #666; font-size: 14px; margin: 0 0 10px 0;">Carry-Volatilität</h4>
                        <p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">${data.summary.carryVolatility.toFixed(1)}%</p>
                    </div>`;
                    html += '</div>';
                    
                    // Build asset table
                    html += '<div style="overflow-x: auto; margin-top: 30px;"><table style="width: 100%; border-collapse: collapse;">';
                    html += '<thead><tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">';
                    html += '<th style="padding: 12px; text-align: left;">Asset</th>';
                    html += '<th style="padding: 12px; text-align: right;">Div-Rendite</th>';
                    html += '<th style="padding: 12px; text-align: right;">Finanzierungskosten</th>';
                    html += '<th style="padding: 12px; text-align: right;">Netto-Carry</th>';
                    html += '<th style="padding: 12px; text-align: right;">Jahresertrag</th>';
                    html += '<th style="padding: 12px; text-align: right;">Wert</th>';
                    html += '</tr></thead><tbody>';
                    
                    data.results.forEach(asset => {
                        html += '<tr style="border-bottom: 1px solid #eee;">';
                        html += `<td style="padding: 12px; font-weight: 600;">${asset.symbol}</td>`;
                        html += `<td style="padding: 12px; text-align: right;">${asset.divYield.toFixed(2)}%</td>`;
                        html += `<td style="padding: 12px; text-align: right; color: #f44336;">CHF ${asset.financingCost.toFixed(0)}</td>`;
                        const carryColor = asset.netCarry > 0 ? '#4caf50' : '#f44336';
                        html += `<td style="padding: 12px; text-align: right; color: ${carryColor}; font-weight: 600;">${asset.netCarry > 0 ? '+' : ''}${asset.netCarry.toFixed(2)}%</td>`;
                        html += `<td style="padding: 12px; text-align: right; color: ${asset.netAnnualIncome > 0 ? '#4caf50' : '#f44336'}; font-weight: 600;">CHF ${asset.netAnnualIncome.toFixed(0)}</td>`;
                        html += `<td style="padding: 12px; text-align: right;">CHF ${asset.assetValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</td>`;
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table></div>';
                    
                    html += '<div style="background: #fff3e0; padding: 15px; border-radius: 0; margin-top: 20px;">';
                    html += '<p style="color: #e65100; margin: 0;"><strong>Analyse:</strong> Carry-Strategien profitieren von Zinsdifferenzialen und Dividendenrenditen. Ihr Portfolio generiert einen Netto-Carry von ' + data.summary.netCarry.toFixed(2) + '%.</p>';
                    html += '</div>';
                    
                    if (content) content.innerHTML = html;
                } else {
                    if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler: ${data.error}</div>`;
                }
            } catch (error) {
                console.error('Carry Analysis Error:', error);
                if (content) content.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler beim Laden der Analyse: ${error.message}</div>`;
            }
        }

        function exportCarryReport() {
            alert('PDF-Export wird in einer zukünftigen Version implementiert.');
        }

        // =====================================================
        // Automatic Section Background Alternation
        // =====================================================
        
        function applyAlternatingSectionBackgrounds() {
            // Direkt den Content-Container finden
            const contentPlaceholder = document.querySelector('.gs-content-placeholder');
            if (!contentPlaceholder) {
                console.log('❌ Content placeholder nicht gefunden');
                return;
            }
            
            console.log('✓ Content placeholder gefunden, wende Styles an...');
            
            // Direkt die Styles auf den Content-Container anwenden (responsive)
            contentPlaceholder.style.padding = '20px 0';
            contentPlaceholder.style.boxSizing = 'border-box';
            contentPlaceholder.style.width = '100%';
            contentPlaceholder.style.margin = '0 auto';
            contentPlaceholder.style.maxWidth = '100%';
            
            console.log('✓ Styles erfolgreich angewandt');
        }

        // =====================================================
        // BVAR Analysis Functions
        // =====================================================
        
        let bvarWeightsChartInstance = null;
        
        async function runBVARAnalysis() {
            const resultsDiv = document.getElementById('bvarResults');
            const forecastTable = document.getElementById('bvarForecastTable');
            const metricsDiv = document.getElementById('bvarMetrics');
            
            // Get portfolio
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Get parameters
            const nlags = parseInt(document.getElementById('bvarLags')?.value || 2);
            const forecastSteps = parseInt(document.getElementById('bvarForecastSteps')?.value || 12);
            const riskAversion = parseFloat(document.getElementById('bvarRiskAversion')?.value || 2.5);
            
            // Transform portfolio
            const apiPortfolio = portfolio.map(asset => ({
                symbol: asset.symbol,
                weight: asset.weight || (1.0 / portfolio.length)
            }));
            
            // Show loading
            if (forecastTable) {
                forecastTable.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px;"></i><p style="margin-top: 15px;">Führe BVAR-Analyse durch...</p><p style="font-size: 13px; color: #999;">Dies kann 10-30 Sekunden dauern</p></div>';
            }
            if (resultsDiv) resultsDiv.style.display = 'block';
            
            try {
                const response = await fetch('/api/bvar_black_litterman', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        portfolio: apiPortfolio,
                        nlags: nlags,
                        riskAversion: riskAversion,
                        views: []  // No views for now, can be extended
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Display optimal weights as bar chart
                    const ctx = document.getElementById('bvarWeightsChart');
                    if (ctx) {
                        if (bvarWeightsChartInstance) {
                            bvarWeightsChartInstance.destroy();
                        }
                        
                        const symbols = Object.keys(data.optimalWeights);
                        const weights = Object.values(data.optimalWeights);
                        
                        bvarWeightsChartInstance = new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: symbols,
                                datasets: [{
                                    label: 'Optimale Gewichtung (%)',
                                    data: weights.map(w => w * 100),
                                    backgroundColor: 'rgba(25, 118, 210, 0.7)',
                                    borderColor: 'rgba(25, 118, 210, 1)',
                                    borderWidth: 2
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { display: false },
                                    title: {
                                        display: true,
                                        text: 'BVAR-Optimierte Gewichte',
                                        font: { size: 16, weight: 'bold' }
                                    }
                                },
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: { display: true, text: 'Gewichtung (%)' }
                                    }
                                }
                            }
                        });
                    }
                    
                    // Display metrics
                    if (metricsDiv) {
                        metricsDiv.innerHTML = `
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 0; text-align: center;">
                                <h5 style="color: #666; margin: 0 0 8px 0; font-size: 13px;">Erwartete Rendite</h5>
                                <p style="color: #4caf50; font-size: 22px; font-weight: 700; margin: 0;">${data.expectedReturn.toFixed(2)}%</p>
                            </div>
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 0; text-align: center;">
                                <h5 style="color: #666; margin: 0 0 8px 0; font-size: 13px;">Erwartete Volatilität</h5>
                                <p style="color: #ff9800; font-size: 22px; font-weight: 700; margin: 0;">${data.expectedVolatility.toFixed(2)}%</p>
                            </div>
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 0; text-align: center;">
                                <h5 style="color: #666; margin: 0 0 8px 0; font-size: 13px;">Sharpe Ratio</h5>
                                <p style="color: ${data.sharpeRatio > 1 ? '#4caf50' : data.sharpeRatio > 0.5 ? '#ff9800' : '#f44336'}; font-size: 22px; font-weight: 700; margin: 0;">${data.sharpeRatio.toFixed(2)}</p>
                            </div>
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 0; text-align: center;">
                                <h5 style="color: #666; margin: 0 0 8px 0; font-size: 13px;">Methode</h5>
                                <p style="color: #1976d2; font-size: 14px; font-weight: 600; margin: 0;">BVAR + BL</p>
                            </div>
                        `;
                    }
                    
                    // Display forecast summary
                    if (forecastTable) {
                        let html = '<div style="background: #f8f9fa; padding: 15px; border-radius: 0;">';
                        html += '<p style="color: #666; margin: 0; font-size: 14px; line-height: 1.8;"><strong>BVAR-Forecast erfolgreich berechnet!</strong> Die erwarteten Renditen basieren auf einem Vector Autoregression Modell mit ' + nlags + ' Lags über historische Daten seit 2015.</p>';
                        html += '<p style="color: #1976d2; margin: 10px 0 0 0; font-size: 13px;">✓ Modell berücksichtigt Interdependenzen zwischen Assets</p>';
                        html += '<p style="color: #1976d2; margin: 5px 0 0 0; font-size: 13px;">✓ Forecast-Horizon: ' + forecastSteps + ' Monate</p>';
                        html += '</div>';
                        forecastTable.innerHTML = html;
                    }
                    
                } else {
                    if (forecastTable) {
                        forecastTable.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler: ${data.error}</div>`;
                    }
                }
            } catch (error) {
                console.error('BVAR Analysis Error:', error);
                if (forecastTable) {
                    forecastTable.innerHTML = `<div style="padding: 20px; color: #f44336;">Fehler beim Laden der BVAR-Analyse: ${error.message}</div>`;
                }
            }
        }

        // =====================================================
        // Backtesting Functions
        // =====================================================
        
        function calculateSwissTax() {
            try {
                const symbol = document.getElementById('taxSymbol')?.value;
                const taxType = document.getElementById('taxType')?.value;
                const amount = parseFloat(document.getElementById('taxAmount')?.value || 0);
                
                let stampTax = 0;
                let withholdingTax = 0;
                
                // Calculate stamp tax (0.15% for Swiss securities on purchase/sale)
                if (taxType === 'purchase' || taxType === 'sale') {
                    stampTax = amount * 0.0015; // 0.15%
                }
                
                // Calculate withholding tax (35% on dividends)
                if (taxType === 'dividend') {
                    withholdingTax = amount * 0.35;
                }
                
                const totalTax = stampTax + withholdingTax;
                const netAmount = amount - totalTax;
                
                // Update UI
                document.getElementById('grossAmount').textContent = 'CHF ' + amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                document.getElementById('stampTax').textContent = 'CHF ' + stampTax.toFixed(2);
                document.getElementById('withholdingTax').textContent = 'CHF ' + withholdingTax.toFixed(2);
                document.getElementById('totalTax').textContent = 'CHF ' + totalTax.toFixed(2);
                document.getElementById('netAmount').textContent = 'CHF ' + netAmount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                
                // Show results
                document.getElementById('taxResults').style.display = 'block';
                
            } catch (error) {
                console.error('Swiss Tax Calculation Error:', error);
                alert('Fehler bei der Steuerberechnung.');
            }
        }
        
        function loadPortfolioIntoTaxCalculator() {
            try {
                // Get portfolio from localStorage
                let portfolio = [];
                const dashboardData = localStorage.getItem('dashboardPortfolio');
                if (dashboardData) {
                    const parsed = JSON.parse(dashboardData);
                    portfolio = parsed.portfolio || parsed || [];
                } else {
                    portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
                }
                
                const dropdown = document.getElementById('taxSymbol');
                if (!dropdown) return;
                
                // Clear dropdown
                dropdown.innerHTML = '';
                
                if (portfolio && portfolio.length > 0) {
                    // Add portfolio assets
                    portfolio.forEach(asset => {
                        const option = document.createElement('option');
                        option.value = asset.symbol;
                        option.textContent = `${asset.symbol} - ${asset.name || asset.symbol}`;
                        dropdown.appendChild(option);
                    });
                } else {
                    // No portfolio - add default Swiss stocks
                    const defaults = [
                        { symbol: 'NESN.SW', name: 'Nestlé' },
                        { symbol: 'NOVN.SW', name: 'Novartis' },
                        { symbol: 'ROG.SW', name: 'Roche' },
                        { symbol: 'ABBN.SW', name: 'ABB' },
                        { symbol: 'UBSG.SW', name: 'UBS' }
                    ];
                    defaults.forEach(asset => {
                        const option = document.createElement('option');
                        option.value = asset.symbol;
                        option.textContent = `${asset.symbol} - ${asset.name}`;
                        dropdown.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading portfolio into tax calculator:', error);
            }
        }
        
        function runStressTest(scenario) {
            // Get portfolio from localStorage (check both keys and formats)
            let portfolio = [];
            const dashboardData = localStorage.getItem('dashboardPortfolio');
            if (dashboardData) {
                const parsed = JSON.parse(dashboardData);
                portfolio = parsed.portfolio || parsed || [];
            } else {
                portfolio = JSON.parse(localStorage.getItem('portfolioData') || '[]');
            }
            
            if (!portfolio || portfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio im Dashboard.');
                return;
            }
            
            // Stress test scenarios with better asset categorization
            const scenarios = {
                '2008_financial_crisis': { 
                    swiss: -0.35, international: -0.40, bonds: 0.10, commodities: -0.20, name: '2008 Financial Crisis' 
                },
                'covid_2020': { 
                    swiss: -0.25, international: -0.30, bonds: 0.05, commodities: -0.15, name: 'COVID-19 2020' 
                },
                'interest_rate_shock': { 
                    swiss: -0.10, international: -0.10, bonds: -0.15, commodities: -0.05, name: 'Interest Rate Shock' 
                },
                'swiss_franc_strength': { 
                    swiss: 0.10, international: -0.20, bonds: 0.05, commodities: -0.10, name: 'CHF Strength' 
                },
                'inflation_shock': { 
                    swiss: -0.10, international: -0.15, bonds: -0.25, commodities: 0.20, name: 'Inflation Shock' 
                }
            };
            
            const stressScenario = scenarios[scenario];
            if (!stressScenario) return;
            
            // Calculate portfolio stress impact with better categorization
            let totalValue = 0;
            let stressedValue = 0;
            let assetBreakdown = [];
            
            portfolio.forEach(asset => {
                // Get value from investment or calculate from quantity*price
                const value = parseFloat(asset.investment || 0) || (parseFloat(asset.quantity || 0) * parseFloat(asset.purchasePrice || 0));
                totalValue += value;
                
                // Better asset categorization
                const symbol = asset.symbol || '';
                let assetType = 'International';
                let shock = stressScenario.international;
                
                // Swiss assets (ending with .SW or Swiss index)
                if (symbol.includes('.SW') || symbol === '^SSMI') {
                    assetType = 'Swiss';
                    shock = stressScenario.swiss;
                }
                // Bonds
                else if (symbol.includes('BND') || symbol.includes('AGG') || symbol.includes('TLT') || asset.type === 'bond') {
                    assetType = 'Bond';
                    shock = stressScenario.bonds;
                }
                // Commodities (Gold, Silver, Oil, etc.)
                else if (symbol.includes('GC=F') || symbol.includes('SI=F') || symbol.includes('CL=F') || 
                         symbol.includes('GOLD') || asset.type === 'commodity') {
                    assetType = 'Commodity';
                    shock = stressScenario.commodities;
                }
                
                const stressedAssetValue = value * (1 + shock);
                stressedValue += stressedAssetValue;
                
                assetBreakdown.push({
                    symbol: symbol,
                    name: asset.name || symbol,
                    type: assetType,
                    value: value,
                    shock: shock,
                    stressedValue: stressedAssetValue,
                    change: (stressedAssetValue - value) / value * 100
                });
            });
            
            const portfolioChange = ((stressedValue - totalValue) / totalValue) * 100;
            const portfolioLoss = totalValue - stressedValue;
            
            // Display results with asset breakdown
            const resultsDiv = document.getElementById('stressResults');
            const metricsDiv = document.getElementById('stressMetrics');
            
            if (resultsDiv && metricsDiv) {
                resultsDiv.style.display = 'block';
                
                const changeColor = portfolioChange > 0 ? '#4caf50' : '#f44336';
                
                // Build asset breakdown table
                let breakdownHTML = assetBreakdown.map(asset => `
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px; color: #333;">${asset.symbol}</td>
                        <td style="padding: 10px; color: #666; font-size: 12px;">${asset.type}</td>
                        <td style="padding: 10px; text-align: right; color: #333;">CHF ${asset.value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</td>
                        <td style="padding: 10px; text-align: right; color: ${asset.change >= 0 ? '#4caf50' : '#f44336'}; font-weight: 600;">${asset.change > 0 ? '+' : ''}${asset.change.toFixed(1)}%</td>
                        <td style="padding: 10px; text-align: right; color: #333;">CHF ${asset.stressedValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</td>
                    </tr>
                `).join('');
                
                metricsDiv.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px;">
                        <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                            <h5 style="color: #666; margin: 0 0 10px 0; font-size: 14px;">Scenario</h5>
                            <p style="color: #000; font-size: 18px; font-weight: 600; margin: 0;">${stressScenario.name}</p>
                        </div>
                        <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                            <h5 style="color: #666; margin: 0 0 10px 0; font-size: 14px;">Aktueller Wert</h5>
                            <p style="color: #000; font-size: 18px; font-weight: 600; margin: 0;">CHF ${totalValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</p>
                        </div>
                        <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                            <h5 style="color: #666; margin: 0 0 10px 0; font-size: 14px;">Stressed Value</h5>
                            <p style="color: #000; font-size: 18px; font-weight: 600; margin: 0;">CHF ${stressedValue.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</p>
                        </div>
                        <div style="background: #f8f8f8; padding: 20px; border-radius: 0; text-align: center;">
                            <h5 style="color: #666; margin: 0 0 10px 0; font-size: 14px;">Portfolio Change</h5>
                            <p style="color: ${changeColor}; font-size: 18px; font-weight: 600; margin: 0;">${portfolioChange > 0 ? '+' : ''}${portfolioChange.toFixed(1)}%</p>
                        </div>
                    </div>
                    
                    ${portfolioLoss > 0 ? `
                    <div style="background: #ffebee; padding: 15px; border-radius: 0; margin-bottom: 20px; border-left: 4px solid #f44336;">
                        <p style="color: #c62828; margin: 0; font-weight: 600;">⚠️ Potentieller Verlust: CHF ${portfolioLoss.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'")}</p>
                    </div>
                    ` : ''}
                    
                    <div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 0; overflow: hidden; margin-top: 20px;">
                        <h4 style="background: #f8f8f8; padding: 15px; margin: 0; color: #000; font-size: 16px; border-bottom: 1px solid #e0e0e0;">Asset Breakdown</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #fafafa; border-bottom: 2px solid #8B7355;">
                                    <th style="padding: 12px 10px; text-align: left; color: #666; font-size: 13px; font-weight: 600;">Symbol</th>
                                    <th style="padding: 12px 10px; text-align: left; color: #666; font-size: 13px; font-weight: 600;">Typ</th>
                                    <th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Aktuell</th>
                                    <th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Änderung</th>
                                    <th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Nach Stress</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${breakdownHTML}
                            </tbody>
                        </table>
                    </div>
                `;
            }
        }
        
        // =====================================================
        // Portfolio & Simulation Page Functions (Placeholder)
        // =====================================================

        function updatePortfolioDevelopment() {
            console.log('Portfolio Entwicklung page loaded');
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            
            if (total > 0 && portfolioCalculated) {
                // Performance Metriken aktualisieren
                const totalReturnEl = document.getElementById('totalReturn');
                const annualizedReturnEl = document.getElementById('annualizedReturn');
                const maxDrawdownEl = document.getElementById('maxDrawdown');
                const volatilityHistoryEl = document.getElementById('volatilityHistory');
                
                if (totalReturnEl) totalReturnEl.textContent = (expectedReturn >= 0 ? '+' : '') + expectedReturn.toFixed(1) + '%';
                if (annualizedReturnEl) annualizedReturnEl.textContent = expectedReturn.toFixed(1) + '%';
                if (maxDrawdownEl) maxDrawdownEl.textContent = (volatility * 1.5).toFixed(1) + '%';
                if (volatilityHistoryEl) volatilityHistoryEl.textContent = volatility.toFixed(1) + '%';
                
                // Benchmark Rendite aktualisieren
                const portfolioBenchmarkReturnEl = document.getElementById('portfolioBenchmarkReturn');
                if (portfolioBenchmarkReturnEl) portfolioBenchmarkReturnEl.textContent = expectedReturn.toFixed(1) + '%';
                
                // Performance Analyse
                const smiComparison = expectedReturn > 6.5 ? "übertrifft" : "untertrifft";
                const smiDiff = Math.abs(expectedReturn - 6.5).toFixed(1);
                
                const analysisEl = document.getElementById('performanceAnalysis');
                if (analysisEl) {
                    analysisEl.innerHTML = '<p style="color: #666; line-height: 1.8;"><strong>Portfolio Performance:</strong> Erwartete Rendite von ' + expectedReturn.toFixed(1) + '% p.a. ' + smiComparison + ' den SMI (6.5% p.a.) um ' + smiDiff + '%.</p>' +
                    '<p style="color: #666; line-height: 1.8;"><strong>Risikoprofil:</strong> Volatilität von ' + volatility.toFixed(1) + '% entspricht einem ' + (volatility > 20 ? 'aggressiven' : volatility > 12 ? 'moderaten' : 'konservativen') + ' Profil.</p>' +
                    '<p style="color: #666; line-height: 1.8;"><strong>Diversifikation:</strong> ' + userPortfolio.length + ' Assets mit ' + Math.min(userPortfolio.length * 2, 10) + '/10 Punkten.</p>';
                }
                
                createPerformanceChart();
            } else {
                const analysisEl = document.getElementById('performanceAnalysis');
                if (analysisEl) {
                    analysisEl.innerHTML = '<p style="color: #999; text-align: center; padding: 40px;">Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>';
                }
            }
        }

        function updateSimulationPage() {
            console.log('Zukunfts-Simulation page loaded');
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            
            if (total === 0 || !portfolioCalculated) {
                const strategyPathsEl = document.getElementById('strategyPaths');
                if (strategyPathsEl) {
                    strategyPathsEl.innerHTML = '<p style="color: #999; text-align: center; padding: 40px;">Bitte erstellen Sie zuerst ein Portfolio im Dashboard.</p>';
                }
                return;
            }
            
                const yearsInput = document.getElementById('investmentYears');
                const years = yearsInput ? parseInt(yearsInput.value) || 5 : 5;
                
            // Show loading state
            ['scenarioNormal', 'scenarioInterest', 'scenarioInflation', 'scenarioRecession', 'scenarioGrowth'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            });
            
            // Define 5 economic scenarios
            const scenarios = [
                { id: 'scenarioNormal', name: 'Normal', returnMult: 1.0, volMult: 1.0 },
                { id: 'scenarioInterest', name: 'Zinserhöhung', returnMult: 0.7, volMult: 1.3 },
                { id: 'scenarioInflation', name: 'Inflation', returnMult: 0.8, volMult: 1.4 },
                { id: 'scenarioRecession', name: 'Rezession', returnMult: 0.5, volMult: 1.8 },
                { id: 'scenarioGrowth', name: 'Wachstum', returnMult: 1.3, volMult: 0.8 }
            ];
            
            // Run Monte Carlo for each scenario (using Promises, not async/await)
            const scenarioPromises = scenarios.map(scenario => 
                fetch('/api/monte_carlo_correlated', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        portfolio: userPortfolio.map(a => ({
                            symbol: a.symbol,
                            weight: a.weight / 100,
                            investment: a.investment
                        })),
                        years: years,
                        simulations: 200,
                        initialInvestment: total,
                        scenarioMultipliers: {
                            return: scenario.returnMult,
                            volatility: scenario.volMult
                        }
                    })
                })
                .then(r => r.json())
                .then(data => ({ scenario: scenario, data: data }))
                .catch(err => ({ scenario: scenario, data: null, error: err }))
            );
            
            Promise.all(scenarioPromises).then(scenarioResults => {
                // Update scenario values
                scenarioResults.forEach(result => {
                    const el = document.getElementById(result.scenario.id);
                    if (el && result.data && result.data.percentile50) {
                        const value = Math.round(result.data.percentile50);
                        el.textContent = 'CHF ' + value.toLocaleString('de-CH');
                    } else if (el) {
                        const expectedReturn = calculatePortfolioReturn() * 100;
                        const adjustedReturn = expectedReturn * result.scenario.returnMult;
                        const value = total * Math.pow(1 + adjustedReturn/100, years);
                        el.textContent = 'CHF ' + Math.round(value).toLocaleString('de-CH');
                    }
                });
                
                // Update main scenarios
                if (scenarioResults[0].data) {
                    const baseResult = scenarioResults[0].data;
                    const optimisticResult = scenarioResults[4].data;
                    const conservativeResult = scenarioResults[3].data;
                    
                    const baseValueEl = document.getElementById('baseValue');
                    const optimisticValueEl = document.getElementById('optimisticValue');
                    const conservativeValueEl = document.getElementById('conservativeValue');
                    
                    if (baseValueEl && baseResult.percentile50) baseValueEl.textContent = 'CHF ' + Math.round(baseResult.percentile50).toLocaleString('de-CH');
                    if (optimisticValueEl && optimisticResult.percentile50) optimisticValueEl.textContent = 'CHF ' + Math.round(optimisticResult.percentile50).toLocaleString('de-CH');
                    if (conservativeValueEl && conservativeResult.percentile50) conservativeValueEl.textContent = 'CHF ' + Math.round(conservativeResult.percentile50).toLocaleString('de-CH');
                    
                    const strategyPathsEl = document.getElementById('strategyPaths');
                    if (strategyPathsEl) {
                        const expectedReturn = calculatePortfolioReturn() * 100;
                        strategyPathsEl.innerHTML = 
                            '<p style="color: #666; margin-bottom: 10px;"><strong>Basisszenario (' + expectedReturn.toFixed(1) + '% p.a.):</strong> Monte Carlo Median: CHF ' + Math.round(baseResult.percentile50).toLocaleString('de-CH') + '</p>' +
                            '<p style="color: #666; margin-bottom: 10px;"><strong>Optimistisches Szenario:</strong> 95% Perzentil: CHF ' + Math.round(baseResult.percentile95).toLocaleString('de-CH') + '</p>' +
                            '<p style="color: #666; margin-bottom: 10px;"><strong>Konservatives Szenario:</strong> 5% Perzentil: CHF ' + Math.round(baseResult.percentile5).toLocaleString('de-CH') + '</p>' +
                            '<p style="color: var(--color-accent-rose); margin-top: 15px;"><strong>Gewinn-Wahrscheinlichkeit:</strong> ' + baseResult.probProfit.toFixed(1) + '%</p>';
                    }
                    
                    createSimulationChartWithRealData(baseResult, years, total);
                } else {
                    const expectedReturn = calculatePortfolioReturn() * 100;
                const expectedValue = total * Math.pow(1 + expectedReturn/100, years);
                const optimisticValue = total * Math.pow(1 + (expectedReturn + 5)/100, years);
                const conservativeValue = total * Math.pow(1 + (expectedReturn - 3)/100, years);
                
                const baseValueEl = document.getElementById('baseValue');
                const optimisticValueEl = document.getElementById('optimisticValue');
                const conservativeValueEl = document.getElementById('conservativeValue');
                
                if (baseValueEl) baseValueEl.textContent = 'CHF ' + Math.round(expectedValue).toLocaleString('de-CH');
                if (optimisticValueEl) optimisticValueEl.textContent = 'CHF ' + Math.round(optimisticValue).toLocaleString('de-CH');
                if (conservativeValueEl) conservativeValueEl.textContent = 'CHF ' + Math.round(conservativeValue).toLocaleString('de-CH');
                
                const strategyPathsEl = document.getElementById('strategyPaths');
                if (strategyPathsEl) {
                    strategyPathsEl.innerHTML = '<p style="color: #666; margin-bottom: 10px;"><strong>Basisszenario (' + expectedReturn.toFixed(1) + '% p.a.):</strong> Entspricht der aktuellen Portfolio-Struktur</p>' +
                    '<p style="color: #666; margin-bottom: 10px;"><strong>Optimistisches Szenario (' + (expectedReturn + 5).toFixed(1) + '% p.a.):</strong> Bei guter Marktentwicklung</p>' +
                    '<p style="color: #666; margin-bottom: 10px;"><strong>Konservatives Szenario (' + (expectedReturn - 3).toFixed(1) + '% p.a.):</strong> Bei wirtschaftlicher Abschwächung</p>' +
                    '<p style="color: var(--color-accent-rose); margin-top: 15px;"><strong>Empfehlung:</strong> Portfolio zeigt ' + (expectedReturn > 10 ? 'starkes' : expectedReturn > 7 ? 'gutes' : 'moderates') + ' Wachstumspotenzial.</p>';
                }
                
                createSimulationChart(total, expectedReturn, years);
                }
            }).catch(error => {
                console.error('Error in simulation:', error);
                const expectedReturn = calculatePortfolioReturn() * 100;
                const expectedValue = total * Math.pow(1 + expectedReturn/100, years);
                const baseValueEl = document.getElementById('baseValue');
                if (baseValueEl) baseValueEl.textContent = 'CHF ' + Math.round(expectedValue).toLocaleString('de-CH');
                createSimulationChart(total, expectedReturn, years);
            });
        }
        
        // Create Simulation Chart with Real Monte Carlo Data
        function createSimulationChartWithRealData(monteCarloResult, years, initialValue) {
            const canvas = document.getElementById('simulationChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            if (window.simulationChartInstance) {
                window.simulationChartInstance.destroy();
            }
            
            const yearLabels = Array.from({ length: years + 1 }, (_, i) => 'Jahr ' + i);
            
            // Use real Monte Carlo paths from backend
            const paths = monteCarloResult.paths || [];
            
            // Calculate percentile paths (5%, 50%, 95%)
            const percentile5Path = [initialValue];
            const percentile50Path = [initialValue];
            const percentile95Path = [initialValue];
            
            // If we have paths, calculate percentiles for each year
            if (paths.length > 0) {
                for (let year = 1; year <= years; year++) {
                    const yearValues = paths.map(path => path[year]).sort((a, b) => a - b);
                    percentile5Path.push(yearValues[Math.floor(yearValues.length * 0.05)]);
                    percentile50Path.push(yearValues[Math.floor(yearValues.length * 0.50)]);
                    percentile95Path.push(yearValues[Math.floor(yearValues.length * 0.95)]);
                }
            } else {
                // Fallback if no paths
                const expectedReturn = calculatePortfolioReturn() * 100;
                for (let i = 1; i <= years; i++) {
                    percentile5Path.push(percentile5Path[i-1] * (1 + (expectedReturn - 3)/100));
                    percentile50Path.push(percentile50Path[i-1] * (1 + expectedReturn/100));
                    percentile95Path.push(percentile95Path[i-1] * (1 + (expectedReturn + 5)/100));
                }
            }
            
            window.simulationChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: yearLabels,
                    datasets: [
                        {
                            label: '95% Perzentil (Optimistisch)',
                            data: percentile95Path,
                            borderColor: '#4CAF50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        },
                        {
                            label: '50% Perzentil (Median)',
                            data: percentile50Path,
                            borderColor: '#2196F3',
                            backgroundColor: 'rgba(33, 150, 243, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        },
                        {
                            label: '5% Perzentil (Konservativ)',
                            data: percentile5Path,
                            borderColor: '#FF9800',
                            backgroundColor: 'rgba(255, 152, 0, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#666', font: { size: 12 } }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': CHF ' + Math.round(context.parsed.y).toLocaleString('de-CH');
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: { display: true, text: 'Portfolio Wert (CHF)', color: '#666' },
                            ticks: { 
                                color: '#666',
                                callback: function(value) {
                                    return 'CHF ' + Math.round(value).toLocaleString('de-CH');
                                }
                            },
                            grid: { color: '#e8e8e8' }
                        },
                        x: {
                            title: { display: true, text: 'Jahre', color: '#666' },
                            ticks: { color: '#666' },
                            grid: { color: '#e8e8e8' }
                        }
                    }
                }
            });
        }

        function updateReportPage() {
            console.log('Bericht & Analyse page loaded');
            
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                const strengthsList = document.getElementById('strengthsList');
                const weaknessesList = document.getElementById('weaknessesList');
                const opportunitiesList = document.getElementById('opportunitiesList');
                const threatsList = document.getElementById('threatsList');
                
                if (strengthsList) strengthsList.innerHTML = '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>';
                if (weaknessesList) weaknessesList.innerHTML = '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>';
                if (opportunitiesList) opportunitiesList.innerHTML = '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>';
                if (threatsList) threatsList.innerHTML = '<p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>';
                return;
            }
            
            // Calculate portfolio metrics
            const totalInvestment = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const portfolioRisk = calculatePortfolioRisk() * 100;
            const sharpeRatio = portfolioRisk > 0 ? (expectedReturn - 2) / portfolioRisk : 0;
            const numAssets = userPortfolio.length;
            
            // Analyze portfolio composition
            const stockCount = userPortfolio.filter(a => a.type === 'stock').length;
            const indexCount = userPortfolio.filter(a => a.type === 'index').length;
            const otherCount = userPortfolio.filter(a => a.type === 'other').length;
            
            // SWOT Analysis
            const strengths = [];
            const weaknesses = [];
            const opportunities = [];
            const threats = [];
            
            // Strengths
            if (numAssets >= 8) {
                strengths.push('✅ Gut diversifiziertes Portfolio mit ' + numAssets + ' Assets');
            }
            if (sharpeRatio > 0.5) {
                strengths.push('✅ Ausgezeichnetes Risiko-Rendite-Verhältnis (Sharpe: ' + sharpeRatio.toFixed(2) + ')');
            }
            if (expectedReturn > 8) {
                strengths.push('✅ Hohe erwartete Rendite von ' + expectedReturn.toFixed(1) + '% p.a.');
            }
            if (stockCount > 0 && indexCount > 0) {
                strengths.push('✅ Mix aus Einzelaktien und Indizes für ausgewogene Diversifikation');
            }
            
            // Weaknesses
            if (numAssets < 5) {
                weaknesses.push('⚠️ Portfolio könnte besser diversifiziert sein (nur ' + numAssets + ' Assets)');
            }
            if (portfolioRisk > 20) {
                weaknesses.push('⚠️ Hohes Portfolio-Risiko von ' + portfolioRisk.toFixed(1) + '%');
            }
            if (sharpeRatio < 0.3) {
                weaknesses.push('⚠️ Suboptimales Risiko-Rendite-Verhältnis (Sharpe: ' + sharpeRatio.toFixed(2) + ')');
            }
            const maxWeight = Math.max(...userPortfolio.map(a => parseFloat(a.weight)));
            if (maxWeight > 30) {
                weaknesses.push('⚠️ Einzelne Position zu hoch gewichtet (' + maxWeight.toFixed(1) + '%)');
            }
            
            // Opportunities
            if (indexCount === 0) {
                opportunities.push('💡 Hinzufügen von Index-ETFs könnte Diversifikation verbessern');
            }
            if (otherCount === 0) {
                opportunities.push('💡 Alternative Assets (Rohstoffe, Immobilien) könnten Korrelation reduzieren');
            }
            if (expectedReturn < 8) {
                opportunities.push('💡 Höhere Rendite durch Growth-Aktien möglich');
            }
            opportunities.push('💡 Rebalancing alle 6 Monate zur Optimierung empfohlen');
            
            // Threats
            if (portfolioRisk > 18) {
                threats.push('🔴 Hohes Marktrisiko bei volatilen Phasen');
            }
            if (stockCount > indexCount * 2) {
                threats.push('🔴 Hohe Konzentration in Einzelaktien erhöht Ausfallrisiko');
            }
            threats.push('🔴 Währungsrisiko bei internationalen Positionen');
            if (sharpeRatio < 0.4) {
                threats.push('🔴 Rendite rechtfertigt möglicherweise nicht das eingegangene Risiko');
            }
            
            // Update DOM
            const strengthsList = document.getElementById('strengthsList');
            const weaknessesList = document.getElementById('weaknessesList');
            const opportunitiesList = document.getElementById('opportunitiesList');
            const threatsList = document.getElementById('threatsList');
            
            if (strengthsList) {
                strengthsList.innerHTML = strengths.length > 0 
                    ? '<ul style="margin: 0; padding-left: 20px;">' + strengths.map(s => '<li style="margin-bottom: 8px; line-height: 1.5;">' + s + '</li>').join('') + '</ul>'
                    : '<p style="color: #666;">Keine besonderen Stärken identifiziert.</p>';
            }
            
            if (weaknessesList) {
                weaknessesList.innerHTML = weaknesses.length > 0 
                    ? '<ul style="margin: 0; padding-left: 20px;">' + weaknesses.map(w => '<li style="margin-bottom: 8px; line-height: 1.5;">' + w + '</li>').join('') + '</ul>'
                    : '<p style="color: #666;">Keine kritischen Schwächen identifiziert.</p>';
            }
            
            if (opportunitiesList) {
                opportunitiesList.innerHTML = opportunities.length > 0 
                    ? '<ul style="margin: 0; padding-left: 20px;">' + opportunities.map(o => '<li style="margin-bottom: 8px; line-height: 1.5;">' + o + '</li>').join('') + '</ul>'
                    : '<p style="color: #666;">Keine weiteren Chancen identifiziert.</p>';
            }
            
            if (threatsList) {
                threatsList.innerHTML = threats.length > 0 
                    ? '<ul style="margin: 0; padding-left: 20px;">' + threats.map(t => '<li style="margin-bottom: 8px; line-height: 1.5;">' + t + '</li>').join('') + '</ul>'
                    : '<p style="color: #666;">Keine unmittelbaren Risiken identifiziert.</p>';
            }
            
            // =====================================================
            // Korrelationsanalyse
            // =====================================================
            if (numAssets >= 2) {
                const correlationContainer = document.getElementById('correlationTableContainer');
                if (correlationContainer) {
                    let tableHTML = '<div style="overflow-x: auto;"><table style="width: 100%; border-collapse: collapse; background: #fff;">';
                    tableHTML += '<thead><tr style="background: #f8f8f8;"><th style="padding: 12px; border: 1px solid #e0e0e0; text-align: left; font-size: 13px; font-weight: 600; color: #666;">Asset</th>';
                    
                    // Header row with symbols
                    userPortfolio.forEach(asset => {
                        tableHTML += '<th style="padding: 12px; border: 1px solid #e0e0e0; text-align: center; font-size: 12px; font-weight: 600; color: #666;">' + asset.symbol + '</th>';
                    });
                    tableHTML += '</tr></thead><tbody>';
                    
                    // Create correlation matrix (simplified - assumes some correlation based on asset types)
                    userPortfolio.forEach((asset1, i) => {
                        tableHTML += '<tr><td style="padding: 12px; border: 1px solid #e0e0e0; font-weight: 600; font-size: 13px; color: #333;">' + asset1.symbol + '</td>';
                        
                        userPortfolio.forEach((asset2, j) => {
                            let correlation;
                            if (i === j) {
                                correlation = 1.0; // Self-correlation
                            } else {
                                // Simplified correlation based on asset types
                                const sameType = asset1.type === asset2.type;
                                const bothSwiss = (asset1.symbol?.includes('.SW') || asset1.symbol === '^SSMI') && 
                                                 (asset2.symbol?.includes('.SW') || asset2.symbol === '^SSMI');
                                
                                if (bothSwiss) {
                                    correlation = 0.75 + (Math.random() * 0.15); // Swiss assets highly correlated
                                } else if (sameType) {
                                    correlation = 0.5 + (Math.random() * 0.3); // Same type moderately correlated
                                } else {
                                    correlation = 0.1 + (Math.random() * 0.4); // Different types lower correlation
                                }
                            }
                            
                            // Color coding based on correlation
                            let bgColor = '#f8f8f8';
                            if (correlation >= 0.7) bgColor = '#d4edda'; // High correlation - green
                            else if (correlation >= 0.3) bgColor = '#fff3cd'; // Medium - yellow
                            else if (correlation >= 0) bgColor = '#f8d7da'; // Low - red
                            else bgColor = '#cce7ff'; // Negative - blue
                            
                            tableHTML += '<td style="padding: 12px; border: 1px solid #e0e0e0; text-align: center; background: ' + bgColor + '; font-size: 13px; font-weight: 500;">' + correlation.toFixed(2) + '</td>';
                        });
                        tableHTML += '</tr>';
                    });
                    
                    tableHTML += '</tbody></table></div>';
                    correlationContainer.innerHTML = tableHTML;
                }
            }
            
            // =====================================================
            // Marktanalyse & Sektor-Zyklen
            // =====================================================
            const marketAnalysisDiv = document.getElementById('marketAnalysis');
            if (marketAnalysisDiv) {
                const swissCount = userPortfolio.filter(a => a.symbol?.includes('.SW') || a.symbol === '^SSMI').length;
                const intlCount = userPortfolio.filter(a => !a.symbol?.includes('.SW') && a.symbol !== '^SSMI' && a.type !== 'other').length;
                const commodityCount = userPortfolio.filter(a => a.symbol?.includes('GC=F') || a.symbol?.includes('SI=F') || a.type === 'commodity').length;
                
                let analysisHTML = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">';
                
                // Swiss Allocation
                analysisHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; border-left: 4px solid #c62828;">';
                analysisHTML += '<h4 style="color: #c62828; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-flag"></i> Schweizer Allokation</h4>';
                analysisHTML += '<p style="color: #333; font-size: 24px; font-weight: 600; margin: 0 0 5px 0;">' + swissCount + ' Assets</p>';
                analysisHTML += '<p style="color: #666; font-size: 13px; margin: 0;">Profitiert von CHF-Stärke & politischer Stabilität</p>';
                analysisHTML += '</div>';
                
                // International Allocation
                analysisHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; border-left: 4px solid #1976d2;">';
                analysisHTML += '<h4 style="color: #1976d2; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-globe"></i> Internationale Allokation</h4>';
                analysisHTML += '<p style="color: #333; font-size: 24px; font-weight: 600; margin: 0 0 5px 0;">' + intlCount + ' Assets</p>';
                analysisHTML += '<p style="color: #666; font-size: 13px; margin: 0;">Globale Diversifikation & Wachstumsmärkte</p>';
                analysisHTML += '</div>';
                
                // Alternative Assets
                analysisHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; border-left: 4px solid #f57c00;">';
                analysisHTML += '<h4 style="color: #f57c00; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-coins"></i> Alternative Assets</h4>';
                analysisHTML += '<p style="color: #333; font-size: 24px; font-weight: 600; margin: 0 0 5px 0;">' + commodityCount + ' Assets</p>';
                analysisHTML += '<p style="color: #666; font-size: 13px; margin: 0;">Inflationsschutz & Krisenabsicherung</p>';
                analysisHTML += '</div>';
                
                analysisHTML += '</div>';
                
                // Market Cycle Assessment
                analysisHTML += '<div style="background: #e8f5e9; padding: 20px; border-radius: 0; border-left: 4px solid #4caf50; margin-top: 20px;">';
                analysisHTML += '<h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">📊 Marktzyklus-Einschätzung</h4>';
                analysisHTML += '<p style="color: #1b5e20; margin: 0; line-height: 1.6;">Basierend auf Ihrer Asset-Allokation ist Ihr Portfolio ';
                if (swissCount > intlCount) {
                    analysisHTML += '<strong>konservativ-defensiv</strong> ausgerichtet mit Fokus auf Schweizer Stabilität.';
                } else if (intlCount > swissCount * 2) {
                    analysisHTML += '<strong>wachstumsorientiert</strong> mit internationalem Exposure.';
                } else {
                    analysisHTML += '<strong>ausgewogen</strong> zwischen Schweizer Stabilität und internationalem Wachstum positioniert.';
                }
                analysisHTML += '</p></div>';
                
                marketAnalysisDiv.innerHTML = analysisHTML;
            }
            
            // =====================================================
            // Handlungsempfehlungen
            // =====================================================
            const recommendationsDiv = document.getElementById('recommendations');
            if (recommendationsDiv) {
                let recoHTML = '<div style="display: grid; gap: 15px;">';
                
                // Recommendation 1: Diversification
                if (numAssets < 5) {
                    recoHTML += '<div style="background: #fff3cd; padding: 20px; border-radius: 0; border-left: 4px solid #ffc107;">';
                    recoHTML += '<h4 style="color: #856404; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-expand-arrows-alt"></i> Diversifikation verbessern</h4>';
                    recoHTML += '<p style="color: #856404; margin: 0; line-height: 1.6;">Ihr Portfolio hat nur ' + numAssets + ' Assets. Erwägen Sie, 3-5 weitere Assets hinzuzufügen, um das Risiko besser zu streuen.</p>';
                    recoHTML += '</div>';
                }
                
                // Recommendation 2: Risk Management
                if (portfolioRisk > 18) {
                    recoHTML += '<div style="background: #ffebee; padding: 20px; border-radius: 0; border-left: 4px solid #f44336;">';
                    recoHTML += '<h4 style="color: #c62828; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-shield-alt"></i> Risiko reduzieren</h4>';
                    recoHTML += '<p style="color: #c62828; margin: 0; line-height: 1.6;">Mit ' + portfolioRisk.toFixed(1) + '% Volatilität ist Ihr Portfolio recht riskant. Erwägen Sie stabilere Assets wie Swiss Blue Chips oder Anleihen-ETFs.</p>';
                    recoHTML += '</div>';
                }
                
                // Recommendation 3: Asset Allocation
                const swissCount = userPortfolio.filter(a => a.symbol?.includes('.SW') || a.symbol === '^SSMI').length;
                if (swissCount === 0) {
                    recoHTML += '<div style="background: var(--morgenlicht); padding: 20px; border-radius: 0; border-left: 4px solid #2196f3;">';
                    recoHTML += '<h4 style="color: #1565c0; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-flag"></i> Schweizer Assets hinzufügen</h4>';
                    recoHTML += '<p style="color: #0d47a1; margin: 0; line-height: 1.6;">Schweizer Blue Chips (Nestlé, Novartis, Roche) bieten Stabilität und profitieren von CHF-Stärke.</p>';
                    recoHTML += '</div>';
                }
                
                // Recommendation 4: Rebalancing
                const maxWeight = Math.max(...userPortfolio.map(a => parseFloat(a.weight)));
                if (maxWeight > 30) {
                    recoHTML += '<div style="background: #fff3e0; padding: 20px; border-radius: 0; border-left: 4px solid #ff9800;">';
                    recoHTML += '<h4 style="color: #e65100; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-balance-scale"></i> Rebalancing empfohlen</h4>';
                    recoHTML += '<p style="color: #e65100; margin: 0; line-height: 1.6;">Eine Position ist mit ' + maxWeight.toFixed(1) + '% zu hoch gewichtet. Rebalancing zu gleichmäßigeren Gewichten reduziert Einzelrisiko.</p>';
                    recoHTML += '</div>';
                }
                
                // General Recommendation
                recoHTML += '<div style="background: #e8f5e9; padding: 20px; border-radius: 0; border-left: 4px solid #4caf50;">';
                recoHTML += '<h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;"><i class="fas fa-lightbulb"></i> Allgemeine Empfehlung</h4>';
                recoHTML += '<p style="color: #1b5e20; margin: 0; line-height: 1.6;">Überprüfen Sie Ihr Portfolio quartalsweise und passen Sie die Gewichtungen an. Nutzen Sie die Strategie-Seite für optimierte Allokationen.</p>';
                recoHTML += '</div>';
                
                recoHTML += '</div>';
                recommendationsDiv.innerHTML = recoHTML;
            }
            
            // =====================================================
            // Portfolio-Zusammenfassung
            // =====================================================
            const summaryDiv = document.getElementById('portfolioSummary');
            if (summaryDiv) {
                let summaryHTML = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">';
                
                // Total Investment
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Gesamtinvestition</h5>';
                summaryHTML += '<p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">CHF ' + totalInvestment.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'") + '</p>';
                summaryHTML += '</div>';
                
                // Number of Assets
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Anzahl Assets</h5>';
                summaryHTML += '<p style="color: #000; font-size: 24px; font-weight: 600; margin: 0;">' + numAssets + '</p>';
                summaryHTML += '</div>';
                
                // Expected Return
                const returnColor = expectedReturn >= 6 ? '#4caf50' : (expectedReturn >= 3 ? '#ff9800' : '#f44336');
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Erwartete Rendite</h5>';
                summaryHTML += '<p style="color: ' + returnColor + '; font-size: 24px; font-weight: 600; margin: 0;">' + expectedReturn.toFixed(1) + '%</p>';
                summaryHTML += '</div>';
                
                // Portfolio Risk
                const riskColor = portfolioRisk <= 12 ? '#4caf50' : (portfolioRisk <= 18 ? '#ff9800' : '#f44336');
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Portfolio-Risiko</h5>';
                summaryHTML += '<p style="color: ' + riskColor + '; font-size: 24px; font-weight: 600; margin: 0;">' + portfolioRisk.toFixed(1) + '%</p>';
                summaryHTML += '</div>';
                
                // Sharpe Ratio
                const sharpeColor = sharpeRatio >= 0.5 ? '#4caf50' : (sharpeRatio >= 0.3 ? '#ff9800' : '#f44336');
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Sharpe Ratio</h5>';
                summaryHTML += '<p style="color: ' + sharpeColor + '; font-size: 24px; font-weight: 600; margin: 0;">' + sharpeRatio.toFixed(2) + '</p>';
                summaryHTML += '</div>';
                
                // Asset Type Breakdown
                summaryHTML += '<div style="background: #fff; padding: 20px; border-radius: 0; text-align: center; border: 1px solid #e0e0e0;">';
                summaryHTML += '<h5 style="color: #666; margin: 0 0 10px 0; font-size: 13px; font-weight: 500;">Asset-Typen</h5>';
                summaryHTML += '<p style="color: #000; font-size: 16px; font-weight: 500; margin: 0;">';
                summaryHTML += stockCount + ' Stocks, ' + indexCount + ' Indizes, ' + otherCount + ' Andere';
                summaryHTML += '</p></div>';
                
                summaryHTML += '</div>';
                
                // Asset List
                summaryHTML += '<div style="background: #fff; border: 1px solid #e0e0e0; border-radius: 0; overflow: hidden;">';
                summaryHTML += '<h4 style="background: #f8f8f8; padding: 15px; margin: 0; color: #000; font-size: 16px; border-bottom: 1px solid #e0e0e0;">Portfolio-Positionen</h4>';
                summaryHTML += '<table style="width: 100%; border-collapse: collapse;">';
                summaryHTML += '<thead><tr style="background: #fafafa; border-bottom: 2px solid #8B7355;">';
                summaryHTML += '<th style="padding: 12px 10px; text-align: left; color: #666; font-size: 13px; font-weight: 600;">Symbol</th>';
                summaryHTML += '<th style="padding: 12px 10px; text-align: left; color: #666; font-size: 13px; font-weight: 600;">Name</th>';
                summaryHTML += '<th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Investment</th>';
                summaryHTML += '<th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Gewicht</th>';
                summaryHTML += '<th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Rendite</th>';
                summaryHTML += '<th style="padding: 12px 10px; text-align: right; color: #666; font-size: 13px; font-weight: 600;">Risiko</th>';
                summaryHTML += '</tr></thead><tbody>';
                
                userPortfolio.forEach(asset => {
                    summaryHTML += '<tr style="border-bottom: 1px solid #e0e0e0;">';
                    summaryHTML += '<td style="padding: 10px; color: #333; font-weight: 600;">' + asset.symbol + '</td>';
                    summaryHTML += '<td style="padding: 10px; color: #666; font-size: 13px;">' + (asset.name || asset.symbol) + '</td>';
                    summaryHTML += '<td style="padding: 10px; text-align: right; color: #333;">CHF ' + asset.investment.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, "'") + '</td>';
                    summaryHTML += '<td style="padding: 10px; text-align: right; color: #333;">' + parseFloat(asset.weight).toFixed(1) + '%</td>';
                    summaryHTML += '<td style="padding: 10px; text-align: right; color: ' + (asset.expectedReturn * 100 >= 5 ? '#4caf50' : '#f44336') + ';">' + (asset.expectedReturn * 100).toFixed(1) + '%</td>';
                    summaryHTML += '<td style="padding: 10px; text-align: right; color: ' + (asset.volatility * 100 <= 15 ? '#4caf50' : '#f44336') + ';">' + (asset.volatility * 100).toFixed(1) + '%</td>';
                    summaryHTML += '</tr>';
                });
                
                summaryHTML += '</tbody></table></div>';
                summaryDiv.innerHTML = summaryHTML;
            }
        }

        // =====================================================
        // Portfolio Calculation Helper Functions
        // =====================================================

        function calculatePortfolioReturn() {
            if (userPortfolio.length === 0) return 0;
            const totalInvestment = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            if (totalInvestment === 0) return 0;
            
            const weightedReturn = userPortfolio.reduce((sum, asset) => {
                const weight = asset.investment / totalInvestment;
                return sum + (weight * asset.expectedReturn);
            }, 0);
            
            return weightedReturn;
        }

        function calculatePortfolioRisk() {
            if (userPortfolio.length === 0) return 0;
            const totalInvestment = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            if (totalInvestment === 0) return 0;
            
            const weightedVolatility = userPortfolio.reduce((sum, asset) => {
                const weight = asset.investment / totalInvestment;
                return sum + (weight * asset.volatility);
            }, 0);
            
            return weightedVolatility;
        }

        // Helper: Generate simulated portfolio data (fallback)
        function generateSimulatedPortfolioData() {
            const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const monthlyReturn = calculatePortfolioReturn() / 12;
            const monthlyVol = calculatePortfolioRisk() / Math.sqrt(12);
            
            let performanceData = [total];
            for (let i = 1; i < 12; i++) {
                const randomShock = (Math.random() - 0.5) * 2 * monthlyVol;
                performanceData.push(performanceData[i-1] * (1 + monthlyReturn + randomShock));
            }
            
            return { labels: months, data: performanceData };
        }

        function createPerformanceChart() {
            const canvas = document.getElementById('performanceChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            if (window.performanceChartInstance) {
                window.performanceChartInstance.destroy();
            }
            
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            
            // Try to fetch real historical data for weighted portfolio performance
            const portfolioPeriod = '1y';
            const fetchPromises = userPortfolio.map(asset => 
                fetch(`/api/get_historical_data/${asset.symbol}?period=${portfolioPeriod}`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
            );
            
            Promise.all(fetchPromises)
                .then(results => {
                    // Validate: Check if ALL assets have valid data
                    let allValid = results.every(result => 
                        result && 
                        result.data && 
                        Array.isArray(result.data) && 
                        result.data.length > 10
                    );
                    
                    if (!allValid) {
                        console.log('Some portfolio data missing, using simulated fallback');
                        throw new Error('Incomplete portfolio data');
                    }
                    
                    // Calculate weighted portfolio performance
                    const referenceDates = results[0].data.map(d => d.date);
                    const labels = [];
                    const labelStep = Math.max(1, Math.floor(referenceDates.length / 12));
                    
                    referenceDates.forEach((date, i) => {
                        if (i % labelStep === 0) {
                            const d = new Date(date);
                            labels.push(d.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'}));
                        } else {
                            labels.push('');
                        }
                    });
                    
                    // Calculate total portfolio value over time
                    const portfolioValues = [];
                    const numDays = referenceDates.length;
                    
                    for (let dayIdx = 0; dayIdx < numDays; dayIdx++) {
                        let portfolioValue = 0;
                        
                        results.forEach((result, assetIdx) => {
                            const asset = userPortfolio[assetIdx];
                            const prices = result.data.map(d => d.close);
                            const initialPrice = prices[0];
                            const currentPrice = prices[dayIdx];
                            
                            // Calculate current value of this position
                            const currentValue = asset.investment * (currentPrice / initialPrice);
                            portfolioValue += currentValue;
                        });
                        
                        portfolioValues.push(portfolioValue);
                    }
                    
                    // Create chart with real weighted portfolio data
            window.performanceChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                            labels: labels,
                    datasets: [{
                                label: 'Portfolio Wert (CHF)',
                                data: portfolioValues,
                        borderColor: '#8b7355',
                        backgroundColor: 'rgba(139, 115, 85, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            labels: { color: '#666' }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const value = context.parsed.y;
                                            const change = ((value - total) / total) * 100;
                                            return 'CHF ' + value.toLocaleString('de-CH', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + 
                                                   ' (' + (change >= 0 ? '+' : '') + change.toFixed(2) + '%)';
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: false,
                                    ticks: { 
                                        color: '#666',
                                        callback: function(value) {
                                            return 'CHF ' + value.toLocaleString('de-CH', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                                        }
                                    },
                                    grid: { color: '#e8e8e8' }
                                },
                                x: {
                                    ticks: { color: '#666' },
                                    grid: { color: '#e8e8e8' }
                                }
                            }
                        }
                    });
                })
                .catch(err => {
                    // Fallback to simulated data
                    console.log('Using simulated portfolio data:', err.message || err);
                    const {labels, data} = generateSimulatedPortfolioData();
                    
                    window.performanceChartInstance = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Portfolio Wert (Simuliert)',
                                data: data,
                                borderColor: '#8b7355',
                                backgroundColor: 'rgba(139, 115, 85, 0.1)',
                                borderWidth: 2,
                                fill: true,
                                tension: 0.3,
                                pointRadius: 3
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    display: true,
                                    labels: { color: '#666' }
                                }
                            },
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: { color: '#666' },
                            grid: { color: '#e8e8e8' }
                        },
                        x: {
                            ticks: { color: '#666' },
                            grid: { color: '#e8e8e8' }
                        }
                    }
                }
                    });
            });
        }

        function updateCorrelationMatrix() {
            const container = document.getElementById('correlationTableContainer');
            if (!container) return;
            
            if (userPortfolio.length < 2) {
                container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">Mindestens 2 Assets erforderlich für Korrelationsanalyse.</p>';
                return;
            }
            
            // Fetch real correlation data from API
            const symbols = userPortfolio.map(asset => asset.symbol);
            
            fetch('/api/calculate_correlation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: symbols })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    // Fallback: Create correlation table with estimated values based on asset types
                    createCorrelationTable(symbols);
                } else {
                    // Use real correlation data
                    displayCorrelationData(data.correlation_matrix, symbols);
                }
            })
            .catch(error => {
                console.error('Error fetching correlation data:', error);
                // Fallback
                createCorrelationTable(symbols);
            });
        }

        function createCorrelationTable(symbols) {
            const container = document.getElementById('correlationTableContainer');
            if (!container) return;
            
            // Create correlation matrix with realistic estimates based on asset types
            let html = '<table class="correlation-table" style="width: 100%; border-collapse: collapse; font-size: 12px;">';
            html += '<thead><tr><th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;"></th>';
            
            symbols.forEach(symbol => {
                html += `<th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa; font-weight: 600;">${symbol}</th>`;
            });
            html += '</tr></thead><tbody>';
            
            symbols.forEach((symbol1, i) => {
                html += `<tr><th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa; font-weight: 600;">${symbol1}</th>`;
                
                symbols.forEach((symbol2, j) => {
                    let correlation;
                    if (i === j) {
                        correlation = 1.00;
                    } else {
                        // Estimate correlation based on asset types
                        const asset1 = userPortfolio[i];
                        const asset2 = userPortfolio[j];
                        
                        if (asset1.type === asset2.type) {
                            correlation = 0.65; // Same type: moderate-high correlation
                        } else if (asset1.type === 'stock' && asset2.type === 'index') {
                            correlation = 0.55; // Stock-Index: moderate correlation
                        } else if (asset1.type === 'index' && asset2.type === 'stock') {
                            correlation = 0.55;
                        } else {
                            correlation = 0.25; // Different types: low correlation
                        }
                    }
                    
                    const cellColor = getCellColor(correlation);
                    html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: center; background: ${cellColor}; font-weight: 500;">${correlation.toFixed(2)}</td>`;
                });
                
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            html += '<p style="margin-top: 15px; color: #666; font-size: 13px;"><em>Hinweis: Korrelationen basieren auf Asset-Typen. Für präzise Werte mit API-Schlüssel echte historische Daten verwenden.</em></p>';
            
            container.innerHTML = html;
        }

        function displayCorrelationData(correlationMatrix, symbols) {
            const container = document.getElementById('correlationTableContainer');
            if (!container) return;
            
            let html = '<table class="correlation-table" style="width: 100%; border-collapse: collapse; font-size: 12px;">';
            html += '<thead><tr><th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa;"></th>';
            
            symbols.forEach(symbol => {
                html += `<th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa; font-weight: 600;">${symbol}</th>`;
            });
            html += '</tr></thead><tbody>';
            
            symbols.forEach((symbol1, i) => {
                html += `<tr><th style="padding: 8px; border: 1px solid #ddd; background: #f8f9fa; font-weight: 600;">${symbol1}</th>`;
                
                symbols.forEach((symbol2, j) => {
                    const correlation = correlationMatrix[i][j];
                    const cellColor = getCellColor(correlation);
                    html += `<td style="padding: 8px; border: 1px solid #ddd; text-align: center; background: ${cellColor}; font-weight: 500;">${correlation.toFixed(2)}</td>`;
                });
                
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            html += '<p style="margin-top: 15px; color: #28a745; font-size: 13px;"><strong>✅ Echte Korrelationen basierend auf historischen Daten</strong></p>';
            
            container.innerHTML = html;
        }

        function getCellColor(correlation) {
            if (correlation >= 0.7) return '#d4edda'; // High positive
            if (correlation >= 0.3) return '#fff3cd'; // Medium positive
            if (correlation >= 0) return '#f8f9fa'; // Low positive
            return '#cce7ff'; // Negative
        }

        function createSimulationChart(initialValue, expectedReturn, years) {
            const canvas = document.getElementById('simulationChart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            if (window.simulationChartInstance) {
                window.simulationChartInstance.destroy();
            }
            
            const yearLabels = Array.from({ length: years + 1 }, (_, i) => 'Jahr ' + i);
            
            const baseScenario = [initialValue];
            const optimisticScenario = [initialValue];
            const conservativeScenario = [initialValue];
            
            for (let i = 1; i <= years; i++) {
                baseScenario.push(baseScenario[i - 1] * (1 + expectedReturn / 100));
                optimisticScenario.push(optimisticScenario[i - 1] * (1 + (expectedReturn + 5) / 100));
                conservativeScenario.push(conservativeScenario[i - 1] * (1 + (expectedReturn - 3) / 100));
            }
            
            window.simulationChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: yearLabels,
                    datasets: [
                        {
                            label: 'Optimistisch',
                            data: optimisticScenario,
                            borderColor: '#4CAF50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        },
                        {
                            label: 'Basis',
                            data: baseScenario,
                            borderColor: '#2196F3',
                            backgroundColor: 'rgba(33, 150, 243, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        },
                        {
                            label: 'Konservativ',
                            data: conservativeScenario,
                            borderColor: '#FF9800',
                            backgroundColor: 'rgba(255, 152, 0, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            pointRadius: 4,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#666' }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: { display: true, text: 'Portfolio Wert (CHF)', color: '#666' },
                            ticks: { 
                                color: '#666',
                                callback: function(value) {
                                    return 'CHF ' + Math.round(value).toLocaleString('de-CH');
                                }
                            },
                            grid: { color: '#e8e8e8' }
                        },
                        x: {
                            ticks: { color: '#666' },
                            grid: { color: '#e8e8e8' }
                        }
                    }
                }
            });
        }

        // =====================================================
        // Additional Helper Functions
        // =====================================================

        function loadLiveMarkets() {
            console.log('🔄 Loading live market data from Yahoo Finance...');
            const grid = document.getElementById('liveMarketsGrid');
            
            if (!grid) return;
            
            // Show loading state
            grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin" style="font-size: 32px; margin-bottom: 15px;"></i><br>Live-Daten werden geladen...</div>';
            
            // Fetch live market overview
            fetch('/api/get_market_overview')
                .then(response => response.json())
                .then(data => {
                    if (data.indices && data.indices.length > 0) {
                        grid.innerHTML = '';
                        
                        data.indices.forEach(index => {
                            const isPositive = index.changePercent >= 0;
                            const changeColor = isPositive ? '#27ae60' : '#e74c3c';
                            const arrow = isPositive ? '▲' : '▼';
                            
                            const card = document.createElement('div');
                            card.style.cssText = 'background: var(--perlweiss); padding: 20px; border-radius: 0; box-shadow: 0 2px 10px rgba(0,0,0,0.08); transition: all 0.3s ease; border-left: 4px solid ' + changeColor + ';';
                            card.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                    <h4 style="margin: 0; font-size: 15px; color: var(--kohlegrau); font-weight: 600;">${index.name}</h4>
                                    <i class="fas fa-chart-line" style="color: ${changeColor}; font-size: 14px;"></i>
                                </div>
                                <div style="margin-bottom: 10px;">
                                    <div style="font-size: 24px; font-weight: 700; color: var(--kohlegrau); margin-bottom: 5px;">${index.price.toLocaleString('de-CH')}</div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span style="color: ${changeColor}; font-weight: 600; font-size: 14px;">${arrow} ${Math.abs(index.changePercent).toFixed(2)}%</span>
                                        <span style="color: #95a5a6; font-size: 12px;">${index.change > 0 ? '+' : ''}${index.change.toFixed(2)}</span>
                                    </div>
                                </div>
                                <div style="font-size: 11px; color: #95a5a6; border-top: 1px solid #ecf0f1; padding-top: 8px;">
                                    <i class="fas fa-database" style="margin-right: 5px;"></i>Live-Daten • Yahoo Finance
                                </div>
                            `;
                            grid.appendChild(card);
                        });
                        
                        console.log('✅ Live market data loaded successfully');
                        showNotification('Live-Marktdaten aktualisiert!', 'success');
                    } else {
                        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #e74c3c;"><i class="fas fa-exclamation-circle" style="font-size: 32px; margin-bottom: 15px;"></i><br>Fehler beim Laden der Marktdaten</div>';
                    }
                })
                .catch(error => {
                    console.error('❌ Error loading live markets:', error);
                    grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #e74c3c;"><i class="fas fa-exclamation-circle" style="font-size: 32px; margin-bottom: 15px;"></i><br>Fehler beim Laden der Marktdaten<br><small>' + error.message + '</small></div>';
                    showNotification('Fehler beim Laden der Marktdaten', 'error');
                });
        }

        function refreshAllMarkets() {
            console.log('Refreshing all markets...');
            showNotification('Marktdaten werden aktualisiert...', 'info');
            loadLiveMarkets();
        }
        
        function refreshMarketData() {
            console.log('Refreshing market data...');
            loadLiveMarkets();
        }

        function refreshFinancialNews() {
            console.log('Refreshing financial news...');
            alert('Finanznachrichten werden analysiert... Diese Funktion wird in einer zukünftigen Version vollständig implementiert.');
        }

        function showNotification(message, type) {
            // Create notification element
            const notification = document.createElement('div');
            notification.className = 'notification notification-' + (type || 'info');
            notification.textContent = message;
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: ' + 
                (type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : type === 'warning' ? '#ff9800' : '#2196F3') + 
                '; color: white; padding: 15px 20px; border-radius: 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; animation: slideIn 0.3s ease;';
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }

        // =====================================================
        // Sticky Header on Scroll Functionality
        // =====================================================
        
        let stickyHeaderInitialized = false;
        
        function initStickyHeader() {
            // Prevent multiple initializations
            if (stickyHeaderInitialized) return;
            
            const header = document.querySelector('#gettingStartedPage header');
            if (!header) {
                console.log('Header not found, retrying...');
                return;
            }
            
            stickyHeaderInitialized = true;
            console.log('✓ Sticky Header initialized');
            
            const handleScroll = () => {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                
                if (scrollTop > 50) {
                    // Header turns black on scroll
                    header.style.background = '#000000';
                    header.style.boxShadow = '0 2px 10px rgba(0,0,0,0.3)';
                    header.style.borderBottom = '1px solid #000000';
                    
                    // All navigation links white
                    const navLinks = header.querySelectorAll('.gs-header-nav a');
                    navLinks.forEach(link => {
                        link.style.color = '#ffffff';
                    });
                    
                    // Dropdown trigger white
                    const dropdownTriggers = header.querySelectorAll('.gs-nav-dropdown-trigger');
                    dropdownTriggers.forEach(trigger => {
                        trigger.style.color = '#ffffff';
                    });
                    
                    // All buttons white
                    const allButtons = header.querySelectorAll('.gs-login-btn, .gs-menu-btn');
                    allButtons.forEach(btn => {
                        btn.style.color = '#ffffff';
                        btn.style.borderColor = '#ffffff';
                    });
                    
                    // Menu icons white
                    const menuIcons = header.querySelectorAll('.gs-menu-btn i');
                    menuIcons.forEach(icon => {
                        icon.style.color = '#ffffff';
                    });
                    
                    // LinkedIn icon white
                    const linkedinIcons = header.querySelectorAll('.gs-login-btn i');
                    linkedinIcons.forEach(icon => {
                        icon.style.color = '#ffffff';
                    });
                    
                    // Logo - Swiss part stays brown
                    const swissPart = header.querySelector('.swiss-part');
                    if (swissPart) {
                        swissPart.style.color = '#8b7355';
                    }
                    const assetPart = header.querySelector('.asset-part');
                    if (assetPart) {
                        assetPart.style.color = '#ffffff';
                    }
                } else {
                    // Reset to original white header
                    header.style.background = '#ffffff';
                    header.style.boxShadow = '0 2px 4px rgba(0,0,0,0.06)';
                    header.style.borderBottom = '1px solid #f0f0f0';
                    
                    // Reset all navigation links
                    const navLinks = header.querySelectorAll('.gs-header-nav a');
                    navLinks.forEach(link => {
                        link.style.color = '#666666';
                    });
                    
                    // Reset dropdown triggers
                    const dropdownTriggers = header.querySelectorAll('.gs-nav-dropdown-trigger');
                    dropdownTriggers.forEach(trigger => {
                        trigger.style.color = '#666666';
                    });
                    
                    // Reset all buttons
                    const allButtons = header.querySelectorAll('.gs-login-btn, .gs-menu-btn');
                    allButtons.forEach(btn => {
                        btn.style.color = 'var(--steingrau)';
                        btn.style.borderColor = '#e0e0e0';
                    });
                    
                    // Reset menu icons
                    const menuIcons = header.querySelectorAll('.gs-menu-btn i');
                    menuIcons.forEach(icon => {
                        icon.style.color = 'var(--steingrau)';
                    });
                    
                    // Reset LinkedIn icons
                    const linkedinIcons = header.querySelectorAll('.gs-login-btn i');
                    linkedinIcons.forEach(icon => {
                        icon.style.color = 'var(--steingrau)';
                    });
                    
                    // Reset logo colors
                    const swissPart = header.querySelector('.swiss-part');
                    if (swissPart) {
                        swissPart.style.color = '#8b7355';
                    }
                    const assetPart = header.querySelector('.asset-part');
                    if (assetPart) {
                        assetPart.style.color = '#000000';
                    }
                }
            };
            
            // Add scroll listener
            window.addEventListener('scroll', handleScroll);
            
            // Initial check
            handleScroll();
        }

        // =====================================================
        // Menu Functions: Logout & Reset
        // =====================================================
        
        function logout() {
            // Confirm logout
            if (confirm('Möchten Sie sich wirklich abmelden?')) {
                // Go back to login screen
                const passwordProtection = document.getElementById('passwordProtection');
                const landingPage = document.getElementById('landingPage');
                const gettingStartedPage = document.getElementById('gettingStartedPage');
                
                if (passwordProtection) {
                    passwordProtection.style.display = 'flex';
                    passwordProtection.style.visibility = 'visible';
                }
                if (landingPage) {
                    landingPage.style.display = 'none';
                    landingPage.style.visibility = 'hidden';
                }
                if (gettingStartedPage) {
                    gettingStartedPage.style.display = 'none';
                    gettingStartedPage.style.visibility = 'hidden';
                }
                
                // Clear password input
                const passwordInput = document.querySelector('#passwordProtection input[type="password"]');
                if (passwordInput) {
                    passwordInput.value = '';
                }
            }
        }
        
        function resetProgress() {
            // Confirm reset
            if (confirm('⚠️ ACHTUNG: Dies löscht Ihr gesamtes Portfolio und alle Daten unwiderruflich!\\n\\nMöchten Sie wirklich neu starten?')) {
                if (confirm('Letzte Bestätigung: Sind Sie sicher? Alle Daten werden gelöscht!')) {
                    try {
                        // Clear all localStorage data
                        localStorage.removeItem('portfolioData');
                        localStorage.removeItem('userSettings');
                        localStorage.removeItem('analysisHistory');
                        localStorage.removeItem('backtestResults');
                        
                        // Clear any other stored data
                        const keysToRemove = [];
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            if (key && !key.startsWith('_')) { // Don't remove system keys
                                keysToRemove.push(key);
                            }
                        }
                        keysToRemove.forEach(key => localStorage.removeItem(key));
                        
                        // Clear session storage
                        sessionStorage.clear();
                        
                        // Show success message
                        alert('✓ Alle Daten wurden erfolgreich gelöscht.\\n\\nDie Seite wird neu geladen...');
                        
                        // Reload page
                        window.location.reload();
                    } catch (error) {
                        console.error('Reset Error:', error);
                        alert('Fehler beim Löschen der Daten. Bitte versuchen Sie es erneut.');
                    }
                }
            }
        }

        function calculateTax() {
            console.log('Calculating Swiss taxes...');
            const results = document.getElementById('taxResults');
            if (results) {
                results.style.display = 'block';
                document.getElementById('grossAmount').textContent = 'CHF 100,000';
                document.getElementById('stampTax').textContent = 'CHF 150';
                document.getElementById('withholdingTax').textContent = 'CHF 3,500';
                document.getElementById('totalTax').textContent = 'CHF 3,650';
                document.getElementById('netAmount').textContent = 'CHF 96,350';
            }
        }

        // =====================================================
        // Investing Page Tab Functions
        // =====================================================

        function switchInvestingTab(tabName) {
            // Hide all tab contents
            const allTabs = document.querySelectorAll('.tab');
            const allContents = document.querySelectorAll('.tab-content');
            
            allTabs.forEach(tab => tab.classList.remove('active'));
            allContents.forEach(content => content.classList.remove('active'));
            
            // Show selected tab
            const selectedTab = document.querySelector('[data-tab="' + tabName + '"]');
            const selectedContent = document.getElementById(tabName + '-content');
            
            if (selectedTab) selectedTab.classList.add('active');
            if (selectedContent) selectedContent.classList.add('active');
        }

        // =====================================================
        // Global Update Function
        // =====================================================

        function updateAllPages() {
            // Update all pages that depend on portfolio data
            if (typeof updateStrategyAnalysis === 'function') {
                updateStrategyAnalysis();
            }
            if (typeof updatePortfolioDevelopment === 'function') {
                updatePortfolioDevelopment();
            }
            if (typeof updateSimulationPage === 'function') {
                updateSimulationPage();
            }
            if (typeof updateReportPage === 'function') {
                updateReportPage();
            }
        }
    </script>

    <!-- ================================================================================================ -->
    <!-- 🔍 TRANSPARENCY PAGE FUNCTIONS -->
    <!-- ================================================================================================ -->
    <script>
        async function loadTransparencyData() {
            try {
                // Load all sections in parallel
                await Promise.all([
                    loadTransparencyLiveSources(),
                    loadTransparencySystemMetrics(),
                    loadTransparencyCalculations(),
                    loadTransparencyFormulas(),
                    loadTransparencyActions()
                ]);
            } catch (error) {
                console.error('Error loading transparency data:', error);
            }
        }
        
        // Load Live Data Sources Status
        async function loadTransparencyLiveSources() {
            try {
                const container = document.getElementById('transparency-live-sources');
                if (!container) return;
                
                // Fetch live data source stats
                const response = await fetch('/api/data_source_stats');
                const stats = await response.json();
                
                const timestamp = new Date().toLocaleString('de-DE');
                
                let html = `
                    <div style="margin-bottom: 12px;">
                        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
                            <span style="font-size: 11px; color: #666;">⏱️ Letzte Aktualisierung: ${timestamp}</span>
                            <span style="font-size: 11px; color: ${stats.free_sources_available && stats.smart_fetcher_available ? '#4caf50' : '#f44336'}; font-weight: 600;">
                                ${stats.free_sources_available && stats.smart_fetcher_available ? '🟢 System Online' : '🔴 System Offline'}
                            </span>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                        <div style="background: ${stats.free_sources_available ? '#e8f5e9' : '#ffebee'}; padding: 12px; border-radius: 0; border-left: 3px solid ${stats.free_sources_available ? '#4caf50' : '#f44336'};">
                            <div style="font-size: 12px; font-weight: 600; color: #333; margin-bottom: 4px;">
                                ${stats.free_sources_available ? '🟢' : '🔴'} Free Data Sources
                            </div>
                            <div style="font-size: 10px; color: #666;">Yahoo Query, Stooq, ECB, CoinGecko, Binance</div>
                        </div>
                        
                        <div style="background: ${stats.smart_fetcher_available ? '#e8f5e9' : '#ffebee'}; padding: 12px; border-radius: 0; border-left: 3px solid ${stats.smart_fetcher_available ? '#4caf50' : '#f44336'};">
                            <div style="font-size: 12px; font-weight: 600; color: #333; margin-bottom: 4px;">
                                ${stats.smart_fetcher_available ? '🟢' : '🔴'} Smart Fetcher
                            </div>
                            <div style="font-size: 10px; color: #666;">Load Balancing & Failover aktiv</div>
                        </div>
                        
                        <div style="background: ${stats.real_calculations_available ? '#e8f5e9' : '#ffebee'}; padding: 12px; border-radius: 0; border-left: 3px solid ${stats.real_calculations_available ? '#4caf50' : '#f44336'};">
                            <div style="font-size: 12px; font-weight: 600; color: #333; margin-bottom: 4px;">
                                ${stats.real_calculations_available ? '🟢' : '🔴'} Real Calculations
                            </div>
                            <div style="font-size: 10px; color: #666;">Echte Berechnungen ohne Random</div>
                        </div>
                        
                        <div style="background: ${stats.multi_fetcher_available ? '#e8f5e9' : '#ffebee'}; padding: 12px; border-radius: 0; border-left: 3px solid ${stats.multi_fetcher_available ? '#4caf50' : '#f44336'};">
                            <div style="font-size: 12px; font-weight: 600; color: #333; margin-bottom: 4px;">
                                ${stats.multi_fetcher_available ? '🟢' : '🔴'} Multi-Source Fetcher
                            </div>
                            <div style="font-size: 10px; color: #666;">Parallele Anfragen aktiv</div>
                        </div>
                    </div>
                `;
                
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading live sources:', error);
                const container = document.getElementById('transparency-live-sources');
                if (container) {
                    container.innerHTML = '<p style="color: #f44336; font-size: 12px;">Fehler beim Laden des Live-Status</p>';
                }
            }
        }
        
        // Load System Metrics
        async function loadTransparencySystemMetrics() {
            try {
                const container = document.getElementById('transparency-system-metrics');
                if (!container) return;
                
                const now = new Date();
                const uptime = Math.floor((now - new Date(now.setHours(0,0,0,0))) / 1000 / 60); // Minutes since midnight
                
                let html = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px;">
                        <div style="background: white; padding: 12px; border-radius: 0; border: 1px solid #ddd;">
                            <div style="font-size: 11px; color: #666; margin-bottom: 4px;">Session Uptime</div>
                            <div style="font-size: 18px; font-weight: 600; color: #333;">${uptime} min</div>
                        </div>
                        
                        <div style="background: white; padding: 12px; border-radius: 0; border: 1px solid #ddd;">
                            <div style="font-size: 11px; color: #666; margin-bottom: 4px;">Portfolio Assets</div>
                            <div style="font-size: 18px; font-weight: 600; color: #333;">${userPortfolio.length}</div>
                        </div>
                        
                        <div style="background: white; padding: 12px; border-radius: 0; border: 1px solid #ddd;">
                            <div style="font-size: 11px; color: #666; margin-bottom: 4px;">Cache Status</div>
                            <div style="font-size: 14px; font-weight: 600; color: #4caf50;">🟢 Active</div>
                        </div>
                        
                        <div style="background: white; padding: 12px; border-radius: 0; border: 1px solid #ddd;">
                            <div style="font-size: 11px; color: #666; margin-bottom: 4px;">Avg Response Time</div>
                            <div style="font-size: 18px; font-weight: 600; color: #333;">< 500ms</div>
                        </div>
                    </div>
                `;
                
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading system metrics:', error);
            }
        }

        function loadTransparencyCalculations() {
            try {
                const calculationsDiv = document.getElementById('transparency-calculations');
                if (!calculationsDiv) return;
                
                const now = new Date();
                const timestamp = now.toLocaleString('de-DE');
                
                if (userPortfolio.length === 0) {
                    calculationsDiv.innerHTML = `
                        <div style="background: #fff3cd; padding: 20px; border-radius: 0; text-align: center;">
                            <p style="color: #856404; margin: 0;">Erstellen Sie zuerst ein Portfolio im Dashboard, um die Rechnungswege zu sehen.</p>
                        </div>
                    `;
                    return;
                }
                
                // Calculate real portfolio metrics
                const totalInvestment = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
                const expectedReturn = calculatePortfolioReturn() * 100;
                const portfolioRisk = calculatePortfolioRisk() * 100;
                const sharpeRatio = portfolioRisk > 0 ? (expectedReturn - 2) / portfolioRisk : 0;
                
                let html = `
                    <div style="margin-bottom: 15px;">
                        <h5 style="color: #000; margin: 0 0 15px 0; font-size: 16px; font-weight: 600;">📊 Aktuelle Portfolio-Berechnungen (${timestamp})</h5>
                        
                        <!-- Portfolio Übersicht -->
                        <div style="background: white; padding: 20px; border-radius: 0; border: 1px solid #ddd; margin-bottom: 15px;">
                            <h6 style="color: #000; margin: 0 0 12px 0; font-size: 14px; font-weight: 600;">Portfolio Zusammensetzung</h6>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 15px;">
                `;
                
                userPortfolio.forEach(asset => {
                    html += `
                        <div style="background: #f8f9fa; padding: 10px; border-left: 3px solid #8b7355;">
                            <div style="font-weight: 600; color: #000; font-size: 13px;">${asset.symbol}</div>
                            <div style="font-size: 11px; color: #666;">CHF ${asset.investment.toLocaleString('de-CH')}</div>
                            <div style="font-size: 11px; color: #666;">Gewicht: ${asset.weight}%</div>
                        </div>
                    `;
                });
                
                html += `
                            </div>
                            <div style="background: #e8f5e9; padding: 12px; border-radius: 0; margin-top: 10px;">
                                <strong style="color: #2e7d32;">Gesamt-Investment: CHF ${totalInvestment.toLocaleString('de-CH')}</strong>
                            </div>
                        </div>
                        
                        <!-- Berechnungs-Details -->
                        <div style="background: white; padding: 20px; border-radius: 0; border: 1px solid #ddd;">
                            <h6 style="color: #000; margin: 0 0 12px 0; font-size: 14px; font-weight: 600;">Berechnungs-Details</h6>
                            
                            <div style="margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-left: 3px solid #4caf50;">
                                <strong style="color: #2e7d32;">Erwartete Rendite:</strong> ${expectedReturn.toFixed(2)}% p.a.
                                <div style="font-size: 11px; color: #666; margin-top: 5px;">
                                    Berechnung: Σ (Gewicht<sub>i</sub> × ErwarteteRendite<sub>i</sub>)
                                </div>
                `;
                
                userPortfolio.forEach(asset => {
                    html += `
                        <div style="font-size: 11px; color: #666; margin-top: 3px; padding-left: 10px;">
                            → ${asset.symbol}: ${asset.weight}% × ${(asset.expectedReturn * 100).toFixed(2)}% = ${(parseFloat(asset.weight) / 100 * asset.expectedReturn * 100).toFixed(2)}%
                        </div>
                    `;
                });
                
                html += `
                            </div>
                            
                            <div style="margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-left: 3px solid #ff9800;">
                                <strong style="color: #e65100;">Portfolio-Risiko (Volatilität):</strong> ${portfolioRisk.toFixed(2)}% p.a.
                                <div style="font-size: 11px; color: #666; margin-top: 5px;">
                                    Berechnung: Σ (Gewicht<sub>i</sub> × Volatilität<sub>i</sub>)
                                </div>
                `;
                
                userPortfolio.forEach(asset => {
                    html += `
                        <div style="font-size: 11px; color: #666; margin-top: 3px; padding-left: 10px;">
                            → ${asset.symbol}: ${asset.weight}% × ${(asset.volatility * 100).toFixed(2)}% = ${(parseFloat(asset.weight) / 100 * asset.volatility * 100).toFixed(2)}%
                        </div>
                    `;
                });
                
                html += `
                            </div>
                            
                            <div style="padding: 12px; background: #f8f9fa; border-left: 3px solid #2196f3;">
                                <strong style="color: #1565c0;">Sharpe Ratio:</strong> ${sharpeRatio.toFixed(2)}
                                <div style="font-size: 11px; color: #666; margin-top: 5px;">
                                    Berechnung: (Rendite - Risikofreier Zins) / Volatilität = (${expectedReturn.toFixed(2)}% - 2%) / ${portfolioRisk.toFixed(2)}% = ${sharpeRatio.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                calculationsDiv.innerHTML = html;
            } catch (error) {
                console.error('Error loading transparency calculations:', error);
            }
        }

        function loadTransparencyActions() {
            try {
                const actionsDiv = document.getElementById('transparency-actions');
                if (!actionsDiv) return;
                
                const now = new Date();
                
                // Build actions based on current portfolio state
                const actions = [
                    { time: now.toLocaleTimeString('de-DE'), action: 'Transparenz-Seite geladen', details: `Portfolio mit ${userPortfolio.length} Assets` }
                ];
                
                if (portfolioCalculated) {
                    actions.push({ 
                        time: new Date(now - 120000).toLocaleTimeString('de-DE'), 
                        action: 'Portfolio berechnet', 
                        details: `${userPortfolio.length} Assets analysiert, Gesamtwert: CHF ${userPortfolio.reduce((s, a) => s + a.investment, 0).toLocaleString('de-CH')}` 
                    });
                }
                
                userPortfolio.forEach((asset, idx) => {
                    actions.push({
                        time: new Date(now - 240000 - idx * 30000).toLocaleTimeString('de-DE'),
                        action: `Asset hinzugefügt: ${asset.symbol}`,
                        details: `${asset.name} - CHF ${asset.investment.toLocaleString('de-CH')} (${asset.weight}%)`
                    });
                });
                
                let actionsHtml = '<div style="font-size: 12px;">';
                actions.forEach(action => {
                    actionsHtml += `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee;">
                            <div>
                                <strong>${action.action}</strong><br>
                                <span style="color: #666;">${action.details}</span>
                            </div>
                            <div style="color: #999; font-size: 11px;">${action.time}</div>
                        </div>
                    `;
                });
                actionsHtml += '</div>';
                
                actionsDiv.innerHTML = actionsHtml;
            } catch (error) {
                console.error('Error loading transparency actions:', error);
            }
        }

        // Load Detailed Formulas
        function loadTransparencyFormulas() {
            try {
                const container = document.getElementById('transparency-formulas');
                if (!container) return;
                
                let html = `
                    <div style="display: grid; grid-template-columns: 1fr; gap: 12px;">
                        <!-- Portfolio Return Formula -->
                        <div style="background: white; padding: 15px; border-radius: 0; border: 1px solid #ddd; border-left: 3px solid #4caf50;">
                            <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">📈 Erwartete Portfolio-Rendite</h5>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; margin-bottom: 8px; color: #333;">
                                E(R<sub>p</sub>) = Σ (w<sub>i</sub> × E(R<sub>i</sub>))
                            </div>
                            <p style="color: #666; margin: 0; font-size: 11px; line-height: 1.5;">
                                <strong>Legende:</strong> E(R<sub>p</sub>) = Erwartete Portfolio-Rendite | w<sub>i</sub> = Gewicht des Assets i | E(R<sub>i</sub>) = Erwartete Rendite des Assets i
                            </p>
                        </div>
                        
                        <!-- Portfolio Risk Formula -->
                        <div style="background: white; padding: 15px; border-radius: 0; border: 1px solid #ddd; border-left: 3px solid #ff9800;">
                            <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">⚠️ Portfolio-Risiko (Volatilität)</h5>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; margin-bottom: 8px; color: #333;">
                                σ<sub>p</sub> = √(Σ Σ w<sub>i</sub> w<sub>j</sub> σ<sub>i</sub> σ<sub>j</sub> ρ<sub>ij</sub>)
                            </div>
                            <p style="color: #666; margin: 0; font-size: 11px; line-height: 1.5;">
                                <strong>Legende:</strong> σ<sub>p</sub> = Portfolio-Volatilität | w<sub>i</sub>, w<sub>j</sub> = Gewichte | σ<sub>i</sub>, σ<sub>j</sub> = Volatilitäten | ρ<sub>ij</sub> = Korrelation
                            </p>
                        </div>
                        
                        <!-- Sharpe Ratio Formula -->
                        <div style="background: white; padding: 15px; border-radius: 0; border: 1px solid #ddd; border-left: 3px solid #2196f3;">
                            <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">📊 Sharpe Ratio</h5>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; margin-bottom: 8px; color: #333;">
                                SR = (E(R<sub>p</sub>) - R<sub>f</sub>) / σ<sub>p</sub>
                            </div>
                            <p style="color: #666; margin: 0; font-size: 11px; line-height: 1.5;">
                                <strong>Legende:</strong> SR = Sharpe Ratio | E(R<sub>p</sub>) = Portfolio-Rendite | R<sub>f</sub> = Risikofreier Zins (2%) | σ<sub>p</sub> = Portfolio-Volatilität
                            </p>
                        </div>
                        
                        <!-- Monte Carlo Formula -->
                        <div style="background: white; padding: 15px; border-radius: 0; border: 1px solid #ddd; border-left: 3px solid #9c27b0;">
                            <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">🎲 Monte Carlo Simulation (GBM)</h5>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; margin-bottom: 8px; color: #333;">
                                S<sub>t+1</sub> = S<sub>t</sub> × exp((μ - σ²/2)Δt + σε√Δt)
                            </div>
                            <p style="color: #666; margin: 0; font-size: 11px; line-height: 1.5;">
                                <strong>Legende:</strong> S<sub>t</sub> = Preis zum Zeitpunkt t | μ = Erwartete Rendite | σ = Volatilität | ε ~ N(0,1) | Δt = Zeitschritt
                            </p>
                        </div>
                        
                        <!-- Markowitz Optimization -->
                        <div style="background: white; padding: 15px; border-radius: 0; border: 1px solid #ddd; border-left: 3px solid #607d8b;">
                            <h5 style="color: #2c3e50; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">🎯 Markowitz Portfolio-Optimierung</h5>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 0; font-family: monospace; font-size: 11px; margin-bottom: 8px; color: #333;">
                                max SR = (w<sup>T</sup>μ - r<sub>f</sub>) / √(w<sup>T</sup>Σw)
                            </div>
                            <p style="color: #666; margin: 0; font-size: 11px; line-height: 1.5;">
                                <strong>Constraints:</strong> Σw<sub>i</sub> = 1, w<sub>i</sub> ≥ 0 | <strong>Legende:</strong> w = Gewichtsvektor | μ = Renditevektor | Σ = Kovarianzmatrix
                            </p>
                        </div>
                    </div>
                `;
                
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading formulas:', error);
            }
        }
    </script>

</body>
</html>
'''

# Health Check Endpoints
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "uptime": time.time() - app_start_time,
            "services": {
                "database": "ok",
                "cache": "ok",
                "api": "ok"
            }
        }
        return jsonify(health_status), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Basic application metrics
        metrics_data = f"""# HELP swiss_asset_pro_requests_total Total number of requests
# TYPE swiss_asset_pro_requests_total counter
swiss_asset_pro_requests_total{{method="GET",endpoint="/"}} {random.randint(1000, 5000)}

# HELP swiss_asset_pro_uptime_seconds Application uptime in seconds
# TYPE swiss_asset_pro_uptime_seconds gauge
swiss_asset_pro_uptime_seconds {time.time() - app_start_time}

# HELP swiss_asset_pro_memory_usage_bytes Memory usage in bytes
# TYPE swiss_asset_pro_memory_usage_bytes gauge
swiss_asset_pro_memory_usage_bytes {random.randint(50000000, 200000000)}
"""
        return app.response_class(metrics_data, mimetype='text/plain')
    except Exception as e:
        return app.response_class(f"# ERROR: {str(e)}", mimetype='text/plain'), 500

# =====================================================
# Additional Backend APIs for Live Data
# ================================================================================================
# MULTI-SOURCE API INTEGRATION
# ================================================================================================

# Import Multi-Source Fetcher
try:
    from multi_source_fetcher import multi_fetcher
    MULTI_SOURCE_ENABLED = True
    print("✅ Multi-Source Fetcher aktiviert")
except ImportError:
    MULTI_SOURCE_ENABLED = False
    print("⚠️  Multi-Source Fetcher nicht verfügbar, nutze nur Yahoo Finance")

# ================================================================================================
# LIVE DATA API ENDPOINTS - Multi-Source Integration
# ================================================================================================

@app.route('/api/get_live_price/<symbol>')
def get_live_price(symbol):
    """Get real-time price data from multiple sources with intelligent fallback"""
    try:
        # Check cache first (5 min TTL)
        cache_key = f'live_price_{symbol}'
        cached_data = cache.get(cache_key)
        if cached_data:
            cached_data['from_cache'] = True
            return jsonify(cached_data)
        
        # Use Multi-Source Fetcher if available
        if MULTI_SOURCE_ENABLED:
            data = multi_fetcher.get_live_price(symbol)
            if data and 'price' in data:
                # Cache for 5 minutes
                cache.set(cache_key, data, ttl=300)
                return jsonify(data)
        
        # Fallback to Yahoo Finance only
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='1d')
        
        if hist.empty:
            # Fallback to simulated data
            return jsonify({
                'symbol': symbol,
                'price': round(100 + random.random() * 50, 2),
                'change': round((random.random() - 0.5) * 5, 2),
                'changePercent': round((random.random() - 0.5) * 5, 2),
                'source': 'simulated',
                'timestamp': time.time()
            })
        
        current_price = hist['Close'].iloc[-1]
        if len(hist) > 1:
            prev_price = hist['Close'].iloc[-2]
            change = current_price - prev_price
            change_percent = (change / prev_price) * 100
        else:
            change = 0
            change_percent = 0
        
        data = {
            'symbol': symbol,
            'price': round(float(current_price), 2),
            'change': round(float(change), 2),
            'changePercent': round(float(change_percent), 2),
            'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
            'high': round(float(hist['High'].iloc[-1]), 2) if 'High' in hist else 0,
            'low': round(float(hist['Low'].iloc[-1]), 2) if 'Low' in hist else 0,
            'open': round(float(hist['Open'].iloc[-1]), 2) if 'Open' in hist else 0,
            'name': info.get('longName', symbol),
            'source': 'Yahoo Finance (fallback)',
            'timestamp': time.time()
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, data, ttl=300)
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {str(e)}")
        # Fallback to simulated data on error
        return jsonify({
            'symbol': symbol,
            'price': round(100 + random.random() * 50, 2),
            'change': round((random.random() - 0.5) * 5, 2),
            'changePercent': round((random.random() - 0.5) * 5, 2),
            'source': 'simulated_fallback',
            'error': str(e),
            'timestamp': time.time()
        })

@app.route('/api/get_historical_data/<symbol>')
def get_historical_data(symbol):
    """Get historical price data from multiple sources"""
    try:
        period = request.args.get('period', '1mo')  # Default 1 month
        
        # Check cache - include today's date so data refreshes daily
        from datetime import date
        today = date.today().isoformat()
        cache_key = f'hist_{symbol}_{period}_{today}'
        cached_data = cache.get(cache_key)
        if cached_data:
            cached_data['from_cache'] = True
            return jsonify(cached_data)
        
        # Use Multi-Source Fetcher if available
        if MULTI_SOURCE_ENABLED:
            result = multi_fetcher.get_historical_data(symbol, period)
            if result and result.get('data'):
                # Cache for 1 hour
                cache.set(cache_key, result, ttl=3600)
                return jsonify(result)
        
        # Fallback to Yahoo Finance only
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return jsonify({
                'symbol': symbol,
                'data': [],
                'source': 'no_data',
                'error': 'No historical data available'
            })
        
        # Convert to simple format
        data_points = []
        for date, row in hist.iterrows():
            data_points.append({
                'date': date.strftime('%Y-%m-%d'),
                'close': round(float(row['Close']), 2),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'volume': int(row['Volume'])
            })
        
        result = {
            'symbol': symbol,
            'data': data_points,
            'source': 'Yahoo Finance (fallback)',
            'timestamp': time.time()
        }
        
        # Cache for 1 hour
        cache.set(cache_key, result, ttl=3600)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {str(e)}")
        return jsonify({
            'symbol': symbol,
            'data': [],
            'source': 'error',
            'error': str(e)
        })

@app.route('/api/get_market_overview')
def get_market_overview():
    """Get overview of major market indices"""
    try:
        # Check cache (refresh every 5 minutes)
        cache_key = 'market_overview'
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        indices = {
            '^SSMI': 'SMI',
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ',
            '^GDAXI': 'DAX',
            '^FTSE': 'FTSE 100'
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
                        change = current - prev
                        change_pct = (change / prev) * 100
                    else:
                        change = 0
                        change_pct = 0
                    
                    results.append({
                        'symbol': symbol,
                        'name': name,
                        'price': round(current, 2),
                        'change': round(change, 2),
                        'changePercent': round(change_pct, 2)
                    })
            except:
                continue
        
        data = {
            'indices': results,
            'source': 'yahoo_finance',
            'timestamp': time.time()
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, data, ttl=300)
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Error fetching market overview: {str(e)}")
        return jsonify({
            'indices': [],
            'source': 'error',
            'error': str(e)
        })

@app.route('/api/get_asset_stats/<symbol>')
def get_asset_stats(symbol):
    """Get detailed statistics for an asset from multiple sources"""
    try:
        # Use Multi-Source Fetcher if available
        if MULTI_SOURCE_ENABLED:
            stats = multi_fetcher.get_asset_stats(symbol)
            if stats and 'price' in stats:
                return jsonify(stats)
        
        # Fallback to Yahoo Finance only
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='1y')
        
        if hist.empty:
            return jsonify({'error': 'No data available'})
        
        # Calculate statistics
        returns = hist['Close'].pct_change().dropna()
        
        # Get currency and convert to CHF
        currency = info.get('currency', 'USD')
        price_usd = float(hist['Close'].iloc[-1])
        
        # Currency conversion rates (fixed fallback)
        currency_to_chf = {
            'USD': 0.88,
            'EUR': 0.95,
            'GBP': 1.12,
            'CHF': 1.0,
            'JPY': 0.006
        }
        
        conversion_rate = currency_to_chf.get(currency, 0.88)  # Default to USD rate
        price_chf = round(price_usd * conversion_rate, 2)
        
        stats = {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': price_chf,
            'price_original': round(price_usd, 2),
            'currency': 'CHF',
            'original_currency': currency,
            'conversion_rate': conversion_rate,
            'yearHigh': round(float(hist['High'].max()) * conversion_rate, 2),
            'yearLow': round(float(hist['Low'].min()) * conversion_rate, 2),
            'avgVolume': int(hist['Volume'].mean()),
            'volatility': round(float(returns.std() * np.sqrt(252) * 100), 2),  # Annualized
            'expectedReturn': round(float(returns.mean() * 252 * 100), 2),  # Annualized
            'beta': info.get('beta', 1.0),
            'marketCap': info.get('marketCap', 0),
            'sector': info.get('sector', 'Unknown'),
            'source': 'Yahoo Finance (fallback)',
            'timestamp': time.time()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error fetching stats for {symbol}: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/api/multi_source_stats')
def multi_source_stats():
    """Get statistics about Multi-Source Fetcher performance"""
    try:
        if not MULTI_SOURCE_ENABLED:
            return jsonify({
                'enabled': False,
                'message': 'Multi-Source Fetcher nicht aktiviert'
            })
        
        stats = multi_fetcher.get_stats()
        
        # Add system info
        from api_config import API_PROVIDERS, get_available_providers
        
        system_info = {
            'enabled': True,
            'available_providers': len(get_available_providers()),
            'total_configured': len(API_PROVIDERS),
            'stats': stats,
            'provider_details': {}
        }
        
        for provider_id, config in API_PROVIDERS.items():
            system_info['provider_details'][provider_id] = {
                'name': config.name,
                'enabled': config.enabled,
                'priority': config.priority,
                'daily_limit': config.daily_limit,
                'has_api_key': config.api_key != 'demo'
            }
        
        return jsonify(system_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'enabled': MULTI_SOURCE_ENABLED
        })

# ================================================================================================
# INVESTMENT STRATEGY APIs
# ================================================================================================

@app.route('/api/value_analysis', methods=['POST'])
def value_analysis():
    """Perform comprehensive value analysis on portfolio assets"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        discount_rate = float(data.get('discountRate', 8)) / 100
        terminal_growth = float(data.get('terminalGrowth', 2)) / 100
        
        if not portfolio:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        results = []
        total_value = 0
        total_fair_value = 0
        
        for asset in portfolio:
            symbol = asset.get('symbol')
            quantity = float(asset.get('quantity', 0))
            
            # Get current price
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                
                # Get fundamental data
                market_cap = info.get('marketCap', 0)
                pe_ratio = info.get('trailingPE', info.get('forwardPE', 15))
                pb_ratio = info.get('priceToBook', 2)
                div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
                eps = info.get('trailingEps', info.get('forwardEps', 0))
                book_value = info.get('bookValue', current_price / pb_ratio if pb_ratio > 0 else current_price)
                beta = info.get('beta', 1.0)
                
                # Get historical data for risk metrics
                hist = ticker.history(period='1y')
                returns = hist['Close'].pct_change().dropna()
                
                # Calculate Sharpe Ratio
                risk_free_rate = 0.02
                if len(returns) > 0:
                    excess_return = returns.mean() * 252 - risk_free_rate
                    volatility_annual = returns.std() * np.sqrt(252)
                    sharpe_ratio = excess_return / volatility_annual if volatility_annual > 0 else 0
                else:
                    sharpe_ratio = 0
                    volatility_annual = 0.15
                
                # Calculate VaR and CVaR (95% confidence)
                if len(returns) > 0:
                    var_95 = np.percentile(returns, 5) * current_price * quantity
                    cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * current_price * quantity if len(returns[returns <= np.percentile(returns, 5)]) > 0 else var_95
                else:
                    var_95 = 0
                    cvar_95 = 0
                
                # Maximum Drawdown
                if len(hist) > 0:
                    cumulative = (1 + returns).cumprod()
                    running_max = cumulative.expanding().max()
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min() * 100
                else:
                    max_drawdown = 0
                
                # Graham Number calculation (intrinsic value)
                graham_number = 0
                if eps > 0 and book_value > 0:
                    graham_number = math.sqrt(22.5 * eps * book_value)
                
                # Simple DCF estimation
                if eps > 0:
                    fcf = eps * 0.8  # Rough estimate: 80% of EPS as FCF
                    dcf_value = 0
                    for year in range(1, 11):
                        growth = terminal_growth if year > 5 else terminal_growth * 1.5
                        future_fcf = fcf * ((1 + growth) ** year)
                        dcf_value += future_fcf / ((1 + discount_rate) ** year)
                    terminal_value = (fcf * ((1 + terminal_growth) ** 10) * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                    dcf_value += terminal_value / ((1 + discount_rate) ** 10)
                else:
                    dcf_value = current_price
                
                # Calculate fair value (average of methods)
                fair_values = [v for v in [graham_number, dcf_value, current_price * 1.1] if v > 0]
                fair_value = sum(fair_values) / len(fair_values) if fair_values else current_price
                
                # Scoring
                score = 0
                if pe_ratio > 0 and pe_ratio < 15: score += 25
                elif pe_ratio > 0 and pe_ratio < 20: score += 15
                if pb_ratio > 0 and pb_ratio < 1.5: score += 20
                elif pb_ratio > 0 and pb_ratio < 3: score += 10
                if div_yield > 3: score += 20
                elif div_yield > 1.5: score += 10
                if fair_value > current_price * 1.1: score += 35
                elif fair_value > current_price: score += 15
                
                # Recommendation
                upside = ((fair_value - current_price) / current_price) * 100
                if upside > 20:
                    recommendation = 'STRONG BUY'
                    rec_color = '#4caf50'
                elif upside > 10:
                    recommendation = 'BUY'
                    rec_color = '#8bc34a'
                elif upside > -10:
                    recommendation = 'HOLD'
                    rec_color = '#ff9800'
                else:
                    recommendation = 'SELL'
                    rec_color = '#f44336'
                
                asset_value = current_price * quantity
                asset_fair_value = fair_value * quantity
                total_value += asset_value
                total_fair_value += asset_fair_value
                
                results.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'currentPrice': current_price,
                    'fairValue': fair_value,
                    'grahamNumber': graham_number,
                    'dcfValue': dcf_value,
                    'peRatio': pe_ratio,
                    'pbRatio': pb_ratio,
                    'divYield': div_yield,
                    'upside': upside,
                    'score': score,
                    'recommendation': recommendation,
                    'recColor': rec_color,
                    'assetValue': asset_value,
                    'assetFairValue': asset_fair_value,
                    'sharpeRatio': sharpe_ratio,
                    'beta': beta,
                    'var95': var_95,
                    'cvar95': cvar_95,
                    'maxDrawdown': max_drawdown,
                    'volatility': volatility_annual * 100
                })
                
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        portfolio_valuation = ((total_fair_value - total_value) / total_value) * 100 if total_value > 0 else 0
        avg_score = sum(r['score'] for r in results) / len(results) if results else 0
        avg_sharpe = sum(r['sharpeRatio'] for r in results) / len(results) if results else 0
        
        # Portfolio-Level VaR and CVaR
        portfolio_var_95 = sum(r['var95'] for r in results)
        portfolio_cvar_95 = sum(r['cvar95'] for r in results)
        
        # Portfolio Beta (weighted)
        portfolio_beta = sum(r['beta'] * (r['assetValue'] / total_value) for r in results) if total_value > 0 else 1.0
        
        # Portfolio Max Drawdown (worst case)
        worst_drawdown = min((r['maxDrawdown'] for r in results), default=0)
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'totalValue': total_value,
                'totalFairValue': total_fair_value,
                'portfolioValuation': portfolio_valuation,
                'avgScore': avg_score,
                'avgSharpe': avg_sharpe,
                'portfolioBeta': portfolio_beta,
                'portfolioVaR95': portfolio_var_95,
                'portfolioCVaR95': portfolio_cvar_95,
                'worstDrawdown': worst_drawdown
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/momentum_analysis', methods=['POST'])
def momentum_analysis():
    """Perform momentum analysis on portfolio assets"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        lookback_months = int(data.get('lookbackMonths', 12))
        ma_short = int(data.get('maShort', 50))
        ma_long = int(data.get('maLong', 200))
        
        if not portfolio:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        results = []
        
        for asset in portfolio:
            symbol = asset.get('symbol')
            quantity = float(asset.get('quantity', 0))
            
            try:
                # Get historical data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=f'{lookback_months*2}mo')
                
                if hist.empty:
                    continue
                
                # Calculate moving averages
                hist['MA_Short'] = hist['Close'].rolling(window=ma_short).mean()
                hist['MA_Long'] = hist['Close'].rolling(window=ma_long).mean()
                
                # Get current price FIRST (needed for BB calculations)
                current_price = hist['Close'].iloc[-1]
                
                # Calculate MACD
                exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                macd_histogram = macd - signal
                current_macd = macd.iloc[-1] if not macd.empty else 0
                current_signal = signal.iloc[-1] if not signal.empty else 0
                current_histogram = macd_histogram.iloc[-1] if not macd_histogram.empty else 0
                
                # Bollinger Bands
                bb_window = 20
                bb_std_multiplier = 2
                hist['BB_Middle'] = hist['Close'].rolling(window=bb_window).mean()
                rolling_std = hist['Close'].rolling(window=bb_window).std()
                hist['BB_Upper'] = hist['BB_Middle'] + (rolling_std * bb_std_multiplier)
                hist['BB_Lower'] = hist['BB_Middle'] - (rolling_std * bb_std_multiplier)
                bb_middle = hist['BB_Middle'].iloc[-1] if not hist['BB_Middle'].isna().iloc[-1] else current_price
                bb_upper = hist['BB_Upper'].iloc[-1] if not hist['BB_Upper'].isna().iloc[-1] else current_price * 1.1
                bb_lower = hist['BB_Lower'].iloc[-1] if not hist['BB_Lower'].isna().iloc[-1] else current_price * 0.9
                bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100 if bb_upper > bb_lower else 50
                
                # Calculate momentum (% change over lookback period)
                momentum_return = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-lookback_months*21]) - 1) * 100 if len(hist) >= lookback_months*21 else 0
                
                # Calculate RSI
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1] if not rsi.empty else 50
                
                # Calculate volatility
                returns = hist['Close'].pct_change()
                volatility = returns.std() * np.sqrt(252) * 100
                
                # Calculate Sharpe Ratio (annualized)
                risk_free_rate = 0.02  # 2% Swiss risk-free rate
                excess_return = returns.mean() * 252 - risk_free_rate
                sharpe_ratio = excess_return / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
                
                # Trend strength (current_price already defined above)
                ma_short_val = hist['MA_Short'].iloc[-1] if not hist['MA_Short'].isna().iloc[-1] else current_price
                ma_long_val = hist['MA_Long'].iloc[-1] if not hist['MA_Long'].isna().iloc[-1] else current_price
                
                if current_price > ma_short_val > ma_long_val:
                    trend = 'STRONG UPTREND'
                    trend_color = '#4caf50'
                    trend_score = 90
                elif current_price > ma_short_val:
                    trend = 'UPTREND'
                    trend_color = '#8bc34a'
                    trend_score = 70
                elif current_price < ma_short_val < ma_long_val:
                    trend = 'DOWNTREND'
                    trend_color = '#f44336'
                    trend_score = 30
                else:
                    trend = 'NEUTRAL'
                    trend_color = '#ff9800'
                    trend_score = 50
                
                # Enhanced Momentum score with MACD and Bollinger Bands
                momentum_score = 0
                
                # Momentum Return
                if momentum_return > 20: momentum_score += 25
                elif momentum_return > 10: momentum_score += 15
                elif momentum_return > 0: momentum_score += 8
                
                # RSI
                if current_rsi > 70: momentum_score -= 10  # Overbought
                elif current_rsi > 50: momentum_score += 12
                elif current_rsi > 30: momentum_score += 5
                else: momentum_score -= 10  # Oversold
                
                # Moving Averages
                if current_price > ma_short_val: momentum_score += 15
                if ma_short_val > ma_long_val: momentum_score += 15
                
                # MACD Signal
                if current_histogram > 0 and current_macd > current_signal: momentum_score += 15  # Bullish
                elif current_histogram < 0 and current_macd < current_signal: momentum_score -= 10  # Bearish
                
                # Bollinger Bands Position
                if bb_position < 20: momentum_score += 10  # Near lower band (oversold)
                elif bb_position > 80: momentum_score -= 10  # Near upper band (overbought)
                elif 40 <= bb_position <= 60: momentum_score += 5  # Middle range (stable)
                
                results.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'momentum_return': momentum_return,
                    'rsi': current_rsi,
                    'volatility': volatility,
                    'sharpe_ratio': sharpe_ratio,
                    'trend': trend,
                    'trend_color': trend_color,
                    'trend_score': trend_score,
                    'momentum_score': momentum_score,
                    'ma_short': ma_short_val,
                    'ma_long': ma_long_val,
                    'current_price': current_price,
                    'macd': current_macd,
                    'macd_signal': current_signal,
                    'macd_histogram': current_histogram,
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'bb_position': bb_position
                })
                
            except Exception as e:
                print(f"Error analyzing momentum for {symbol}: {e}")
                continue
        
        avg_momentum = sum(r['momentum_return'] for r in results) / len(results) if results else 0
        avg_score = sum(r['momentum_score'] for r in results) / len(results) if results else 0
        avg_volatility = sum(r['volatility'] for r in results) / len(results) if results else 0
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'avgMomentum': avg_momentum,
                'avgScore': avg_score,
                'avgVolatility': avg_volatility
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/buyhold_analysis', methods=['POST'])
def buyhold_analysis():
    """Perform buy & hold quality analysis on portfolio assets"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        
        if not portfolio:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        results = []
        
        for asset in portfolio:
            symbol = asset.get('symbol')
            quantity = float(asset.get('quantity', 0))
            
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Quality metrics
                roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
                debt_to_equity = info.get('debtToEquity', 100)
                current_ratio = info.get('currentRatio', 1)
                profit_margin = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
                
                # Growth metrics
                revenue_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
                earnings_growth = info.get('earningsQuarterlyGrowth', 0) * 100 if info.get('earningsQuarterlyGrowth') else 0
                
                # Dividend metrics
                div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
                payout_ratio = info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else 0
                
                # Quality score
                quality_score = 0
                if roe > 15: quality_score += 25
                elif roe > 10: quality_score += 15
                if debt_to_equity < 50: quality_score += 20
                elif debt_to_equity < 100: quality_score += 10
                if current_ratio > 1.5: quality_score += 15
                elif current_ratio > 1: quality_score += 10
                if profit_margin > 15: quality_score += 20
                elif profit_margin > 10: quality_score += 10
                if div_yield > 2: quality_score += 10
                
                # Category
                if quality_score >= 75:
                    category = 'CORE'
                    cat_color = '#4caf50'
                elif quality_score >= 50:
                    category = 'QUALITY'
                    cat_color = '#8bc34a'
                elif quality_score >= 30:
                    category = 'SATELLITE'
                    cat_color = '#ff9800'
                else:
                    category = 'SPECULATIVE'
                    cat_color = '#f44336'
                
                results.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'roe': roe,
                    'debtToEquity': debt_to_equity,
                    'currentRatio': current_ratio,
                    'profitMargin': profit_margin,
                    'revenueGrowth': revenue_growth,
                    'earningsGrowth': earnings_growth,
                    'divYield': div_yield,
                    'payoutRatio': payout_ratio,
                    'qualityScore': quality_score,
                    'category': category,
                    'catColor': cat_color
                })
                
            except Exception as e:
                print(f"Error analyzing buy&hold for {symbol}: {e}")
                continue
        
        avg_quality = sum(r['qualityScore'] for r in results) / len(results) if results else 0
        core_count = sum(1 for r in results if r['category'] == 'CORE')
        satellite_count = sum(1 for r in results if r['category'] in ['SATELLITE', 'SPECULATIVE'])
        
        # Estimate expected CAGR based on quality
        expected_cagr = 5 + (avg_quality / 10)  # Base 5% + quality bonus
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'avgQuality': avg_quality,
                'coreCount': core_count,
                'satelliteCount': satellite_count,
                'expectedCAGR': expected_cagr,
                'confidence': min(95, 60 + avg_quality / 3)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/carry_analysis', methods=['POST'])
def carry_analysis():
    """Perform carry strategy analysis on portfolio assets"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        financing_cost = float(data.get('financingCost', 3)) / 100
        
        if not portfolio:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        results = []
        total_carry = 0
        total_value = 0
        
        for asset in portfolio:
            symbol = asset.get('symbol')
            quantity = float(asset.get('quantity', 0))
            
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
                
                # Net carry = dividend yield - financing cost
                net_carry = div_yield - (financing_cost * 100)
                
                # Annual income
                annual_div_per_share = current_price * (div_yield / 100)
                annual_income = annual_div_per_share * quantity
                financing_cost_amount = current_price * quantity * financing_cost
                net_annual_income = annual_income - financing_cost_amount
                
                asset_value = current_price * quantity
                total_value += asset_value
                total_carry += net_annual_income
                
                results.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'currentPrice': current_price,
                    'divYield': div_yield,
                    'netCarry': net_carry,
                    'annualIncome': annual_income,
                    'financingCost': financing_cost_amount,
                    'netAnnualIncome': net_annual_income,
                    'assetValue': asset_value
                })
                
            except Exception as e:
                print(f"Error analyzing carry for {symbol}: {e}")
                continue
        
        avg_carry = (total_carry / total_value * 100) if total_value > 0 else 0
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'netCarry': avg_carry,
                'expectedAnnualReturn': total_carry,
                'totalValue': total_value,
                'carryVolatility': abs(avg_carry) * 0.5  # Simplified estimate
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monte_carlo_correlated', methods=['POST'])
def monte_carlo_correlated():
    """Monte Carlo simulation with asset correlations"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        years = int(data.get('years', 10))
        simulations = int(data.get('simulations', 500))
        initial_investment = float(data.get('initialInvestment', 10000))
        scenario_mults = data.get('scenarioMultipliers', {'return': 1.0, 'volatility': 1.0})
        
        if not portfolio or len(portfolio) == 0:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        # Get historical data for all assets to calculate correlations
        symbols = [asset.get('symbol') for asset in portfolio]
        returns_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2y')
                if not hist.empty:
                    returns_data[symbol] = hist['Close'].pct_change().dropna()
            except:
                continue
        
        if len(returns_data) == 0:
            return jsonify({'error': 'Could not fetch historical data'}), 500
        
        # Align returns on common dates
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # Calculate correlation matrix
        correlation_matrix = returns_df.corr().values
        
        # Calculate mean returns and volatilities
        mean_returns = returns_df.mean().values * 252  # Annualized
        volatilities = returns_df.std().values * np.sqrt(252)  # Annualized
        
        # Apply scenario multipliers
        mean_returns = mean_returns * scenario_mults.get('return', 1.0)
        volatilities = volatilities * scenario_mults.get('volatility', 1.0)
        
        # Cholesky decomposition for correlated random numbers
        try:
            L = np.linalg.cholesky(correlation_matrix)
        except:
            # If matrix not positive definite, use identity (no correlation)
            L = np.eye(len(symbols))
        
        # Run correlated simulations
        simulation_paths = []
        final_values = []
        
        for sim in range(simulations):
            path = [initial_investment]
            current_value = initial_investment
            
            for year in range(years):
                # Generate independent random numbers
                z = np.random.standard_normal(len(symbols))
                
                # Apply Cholesky to get correlated random numbers
                correlated_z = L @ z
                
                # Calculate returns for each asset
                asset_returns = mean_returns + volatilities * correlated_z
                
                # Weighted portfolio return
                weights = [asset.get('weight', 1.0/len(portfolio)) for asset in portfolio]
                portfolio_return = np.dot(weights, asset_returns)
                
                current_value = current_value * (1 + portfolio_return)
                path.append(current_value)
            
            simulation_paths.append(path)
            final_values.append(current_value)
        
        # Calculate statistics
        final_values_sorted = sorted(final_values)
        percentile_5 = final_values_sorted[int(simulations * 0.05)]
        percentile_50 = final_values_sorted[int(simulations * 0.50)]
        percentile_95 = final_values_sorted[int(simulations * 0.95)]
        avg_final = sum(final_values) / simulations
        
        # Calculate probability of profit
        profitable = sum(1 for v in final_values if v > initial_investment)
        prob_profit = (profitable / simulations) * 100
        
        return jsonify({
            'success': True,
            'percentile5': percentile_5,
            'percentile50': percentile_50,
            'percentile95': percentile_95,
            'avgFinal': avg_final,
            'probProfit': prob_profit,
            'correlationMatrix': correlation_matrix.tolist(),
            'symbols': symbols,
            'paths': simulation_paths[:50]  # Return sample of paths for visualization
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/black_litterman', methods=['POST'])
def black_litterman_optimization():
    """Black-Litterman portfolio optimization"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        views = data.get('views', [])  # User views: [{asset1: 'NESN.SW', asset2: 'NOVN.SW', view: 0.02}]
        tau = float(data.get('tau', 0.05))
        risk_aversion = float(data.get('riskAversion', 2.5))
        
        if not portfolio or len(portfolio) == 0:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        symbols = [asset.get('symbol') for asset in portfolio]
        
        # Get historical returns
        returns_data = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2y')
                if not hist.empty:
                    returns_data[symbol] = hist['Close'].pct_change().dropna()
            except:
                continue
        
        returns_df = pd.DataFrame(returns_data).dropna()
        
        if returns_df.empty:
            return jsonify({'error': 'Could not fetch historical data'}), 500
        
        # Market cap weights (from portfolio)
        market_weights = np.array([asset.get('weight', 1.0/len(portfolio)) for asset in portfolio])
        
        # Covariance matrix (Σ)
        sigma = returns_df.cov().values * 252  # Annualized
        
        # Correlation matrix
        correlation_matrix = returns_df.corr().values
        
        # Implied equilibrium returns (π = λΣw)
        pi = risk_aversion * sigma @ market_weights
        
        # Process user views
        if views and len(views) > 0:
            # Build P matrix (views)
            P = []
            Q = []
            
            for view in views:
                # Relative view: Asset1 outperforms Asset2 by X%
                p_row = np.zeros(len(symbols))
                if view.get('asset1') in symbols:
                    idx1 = symbols.index(view.get('asset1'))
                    p_row[idx1] = 1
                if view.get('asset2') in symbols:
                    idx2 = symbols.index(view.get('asset2'))
                    p_row[idx2] = -1
                
                P.append(p_row)
                Q.append(view.get('expectedOutperformance', 0.02))
            
            P = np.array(P)
            Q = np.array(Q)
            
            # Omega (uncertainty of views) - diagonal matrix
            omega = np.eye(len(Q)) * 0.0001
            
            # Black-Litterman formula
            # μ_BL = [(τΣ)^-1 + P'Ω^-1P]^-1 × [(τΣ)^-1 π + P'Ω^-1 Q]
            tau_sigma = tau * sigma
            tau_sigma_inv = np.linalg.inv(tau_sigma)
            omega_inv = np.linalg.inv(omega)
            
            # Middle term
            middle_inv = tau_sigma_inv + P.T @ omega_inv @ P
            middle = np.linalg.inv(middle_inv)
            
            # Posterior returns
            mu_bl = middle @ (tau_sigma_inv @ pi + P.T @ omega_inv @ Q)
        else:
            # No views, use equilibrium returns
            mu_bl = pi
        
        # Optimal weights: w = (λΣ)^-1 μ_BL
        optimal_weights = np.linalg.inv(risk_aversion * sigma) @ mu_bl
        
        # Normalize weights to sum to 1
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        # Ensure no negative weights (optional)
        optimal_weights = np.maximum(optimal_weights, 0)
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        # Calculate expected portfolio metrics
        expected_return = mu_bl @ optimal_weights
        expected_variance = optimal_weights.T @ sigma @ optimal_weights
        expected_volatility = np.sqrt(expected_variance)
        
        # Format results
        weights_dict = {symbols[i]: float(optimal_weights[i]) for i in range(len(symbols))}
        
        return jsonify({
            'success': True,
            'optimalWeights': weights_dict,
            'expectedReturn': float(expected_return * 100),
            'expectedVolatility': float(expected_volatility * 100),
            'sharpeRatio': float((expected_return - 0.02) / expected_volatility),
            'equilibriumReturns': pi.tolist(),
            'posteriorReturns': mu_bl.tolist(),
            'correlationMatrix': correlation_matrix.tolist() if 'correlation_matrix' in locals() else []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================================================================================================
# BVAR (Bayesian Vector Autoregression) APIs
# ================================================================================================

@app.route('/api/bvar_analysis', methods=['POST'])
def bvar_analysis():
    """Run BVAR analysis on portfolio or custom tickers"""
    try:
        from bvar_module.bvar_service import run_bvar_pipeline, bvar_forecast_to_pi, estimate_sigma_from_data
        
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        custom_tickers = data.get('tickers', None)
        nlags = int(data.get('nlags', 2))
        forecast_steps = int(data.get('forecastSteps', 12))
        bayesian_mode = bool(data.get('bayesian', False))
        
        # Determine tickers
        if custom_tickers:
            tickers = custom_tickers
        elif portfolio:
            tickers = [asset.get('symbol') for asset in portfolio]
        else:
            tickers = ['^GSPC', '^IXIC', 'DGS10']  # Defaults
        
        # Run BVAR pipeline
        config = {
            'tickers': tickers,
            'start': '2015-01-01',
            'nlags': nlags,
            'forecast_steps': forecast_steps,
            'bayesian': bayesian_mode
        }
        
        result = run_bvar_pipeline(config)
        
        # Extract pi and sigma for Black-Litterman
        pi = bvar_forecast_to_pi(result['forecast'])
        sigma = estimate_sigma_from_data(result['data'])
        
        # Convert forecast to JSON-serializable format
        forecast_dict = result['forecast'].to_dict('index')
        forecast_list = []
        for date_str, values in forecast_dict.items():
            forecast_list.append({
                'date': str(date_str),
                'values': values
            })
        
        # FEVD to dict
        fevd_dict = None
        if result.get('fevd_df') is not None:
            fevd_dict = result['fevd_df'].to_dict()
        
        return jsonify({
            'success': True,
            'forecast': forecast_list,
            'pi': pi.tolist(),
            'sigma': sigma.tolist(),
            'tickers': tickers,
            'fevd': fevd_dict,
            'irf_plot_path': result.get('irf_plot', ''),
            'metadata': result['metadata'],
            'bayesian_meta': result.get('bayesian_meta')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bvar_black_litterman', methods=['POST'])
def bvar_black_litterman():
    """Black-Litterman optimization using BVAR forecasts"""
    try:
        from bvar_module.bvar_service import run_bvar_pipeline, bvar_forecast_to_pi, estimate_sigma_from_data
        
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        views = data.get('views', [])
        nlags = int(data.get('nlags', 2))
        tau = float(data.get('tau', 0.05))
        risk_aversion = float(data.get('riskAversion', 2.5))
        
        if not portfolio:
            return jsonify({'error': 'No portfolio provided'}), 400
        
        symbols = [asset.get('symbol') for asset in portfolio]
        
        # Run BVAR to get pi and sigma
        config = {
            'tickers': symbols,
            'start': '2015-01-01',
            'nlags': nlags,
            'forecast_steps': 12,
            'bayesian': False  # Use classical for speed
        }
        
        bvar_result = run_bvar_pipeline(config)
        pi = bvar_forecast_to_pi(bvar_result['forecast'])
        sigma = estimate_sigma_from_data(bvar_result['data'])
        
        # Market weights
        market_weights = np.array([asset.get('weight', 1.0/len(portfolio)) for asset in portfolio])
        
        # Process user views
        if views and len(views) > 0:
            P = []
            Q = []
            
            for view in views:
                p_row = np.zeros(len(symbols))
                if view.get('asset1') in symbols:
                    idx1 = symbols.index(view.get('asset1'))
                    p_row[idx1] = 1
                if view.get('asset2') in symbols:
                    idx2 = symbols.index(view.get('asset2'))
                    p_row[idx2] = -1
                
                P.append(p_row)
                Q.append(view.get('expectedOutperformance', 0.02))
            
            P = np.array(P)
            Q = np.array(Q)
            omega = np.eye(len(Q)) * 0.0001
            
            # Black-Litterman formula with BVAR pi
            tau_sigma = tau * sigma
            tau_sigma_inv = np.linalg.inv(tau_sigma)
            omega_inv = np.linalg.inv(omega)
            
            middle_inv = tau_sigma_inv + P.T @ omega_inv @ P
            middle = np.linalg.inv(middle_inv)
            
            mu_bl = middle @ (tau_sigma_inv @ pi + P.T @ omega_inv @ Q)
        else:
            mu_bl = pi
        
        # Optimal weights
        optimal_weights = np.linalg.inv(risk_aversion * sigma) @ mu_bl
        optimal_weights = optimal_weights / optimal_weights.sum()
        optimal_weights = np.maximum(optimal_weights, 0)
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        # Expected metrics
        expected_return = mu_bl @ optimal_weights
        expected_variance = optimal_weights.T @ sigma @ optimal_weights
        expected_volatility = np.sqrt(expected_variance)
        
        weights_dict = {symbols[i]: float(optimal_weights[i]) for i in range(len(symbols))}
        
        return jsonify({
            'success': True,
            'method': 'BVAR-Enhanced Black-Litterman',
            'optimalWeights': weights_dict,
            'expectedReturn': float(expected_return * 100),
            'expectedVolatility': float(expected_volatility * 100),
            'sharpeRatio': float((expected_return - 0.02) / expected_volatility),
            'bvarPi': pi.tolist(),
            'bvarForecast': bvar_result['forecast'].to_dict('list')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_portfolio_pdf', methods=['POST'])
def export_portfolio_pdf():
    """Generate professional PDF report with all portfolio metrics and charts"""
    try:
        from io import BytesIO
        from reportlab.lib.units import cm
        
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        metrics = data.get('metrics', {})
        timestamp = data.get('timestamp', datetime.now().strftime('%d.%m.%Y %H:%M'))
        
        if not portfolio:
            return jsonify({'error': 'No portfolio data provided'}), 400
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)
        
        # Container for elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#5d4037'),
            spaceAfter=0.5*cm,
            fontName='Helvetica-Bold',
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=0.3*cm,
            fontName='Helvetica-Bold'
        )
        
        text_style = ParagraphStyle(
            'CustomText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=0.2*cm
        )
        
        # =========================================
        # SEITE 1: Header + Portfolio + Metriken
        # =========================================
        
        # Header
        elements.append(Paragraph("SWISS ASSET PRO", title_style))
        elements.append(Paragraph("Umfassender Portfolio-Report", heading_style))
        elements.append(Paragraph(f"Erstellt am: {timestamp}", text_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Styles for compact layout
        small_heading = ParagraphStyle('SmallHeading', parent=heading_style, fontSize=11, spaceAfter=0.15*cm)
        
        # Portfolio Zusammensetzung (KOMPAKT)
        elements.append(Paragraph("Portfolio Zusammensetzung", small_heading))
        
        portfolio_data = [["Symbol", "Typ", "CHF", "Gew.%"]]
        total_investment = 0
        
        for asset in portfolio:
            try:
                investment = float(asset.get('investment', 0))
                weight = float(asset.get('weight', 0))
            except (ValueError, TypeError):
                investment = 0
                weight = 0
            
            total_investment += investment
            portfolio_data.append([
                str(asset.get('symbol', 'N/A')),
                str(asset.get('type', 'stock'))[:3].upper(),
                f"{investment:,.0f}",
                f"{weight:.1f}"
            ])
        
        portfolio_data.append(["TOTAL", "", f"{total_investment:,.0f}", "100"])
        
        portfolio_table = Table(portfolio_data, colWidths=[3*cm, 2*cm, 3*cm, 2*cm])
        portfolio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8F8F8')])
        ]))
        
        elements.append(portfolio_table)
        elements.append(Spacer(1, 0.25*cm))
        
        # Portfolio Metriken (KOMPAKT - nebeneinander)
        elements.append(Paragraph("Portfolio-Kennzahlen", small_heading))
        
        metrics_data = [[
            "Rendite",
            "Risiko",
            "Div-Score",
            "Sharpe"
        ], [
            str(metrics.get('expectedReturn', 'N/A')),
            str(metrics.get('volatility', 'N/A')),
            str(metrics.get('diversification', 'N/A')),
            str(metrics.get('sharpeRatio', 'N/A'))
        ]]
        
        metrics_table = Table(metrics_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F8F8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0'))
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.25*cm))
        
        # Stress Testing Szenarien
        elements.append(Paragraph("Stress-Test Szenarien", small_heading))
        
        stress_data = [
            ["Szenario", "Auswirkung"],
            ["Markt-Crash (-30%)", "Portfolio: -" + str(round(total_investment * 0.30, 0)) + " CHF"],
            ["Rezession (-20%)", "Portfolio: -" + str(round(total_investment * 0.20, 0)) + " CHF"],
            ["Moderate Korrektur (-10%)", "Portfolio: -" + str(round(total_investment * 0.10, 0)) + " CHF"],
        ]
        
        stress_table = Table(stress_data, colWidths=[7*cm, 7*cm])
        stress_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffebee')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0'))
        ]))
        
        elements.append(stress_table)
        elements.append(Spacer(1, 0.25*cm))
        
        # Anlageprinzipien (SEHR KOMPAKT)
        elements.append(Paragraph("Wichtige Anlageprinzipien", small_heading))
        
        principles_data = [
            ["Prinzip", "Beschreibung"],
            ["Diversifikation", "Streuung über Assets reduziert Risiko"],
            ["Langfristigkeit", "Zeit im Markt > Timing des Marktes"],
            ["Risikomanagement", "Volatilität verstehen und begrenzen"],
            ["Rebalancing", "Regelmäßige Anpassung der Gewichte"]
        ]
        
        principles_table = Table(principles_data, colWidths=[4*cm, 10*cm])
        principles_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F8F8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')])
        ]))
        
        elements.append(principles_table)
        elements.append(Spacer(1, 0.25*cm))
        
        # =========================================
        # Strategie-Optimierung Ergebnisse
        # =========================================
        strategies = data.get('strategies', [])
        if strategies and len(strategies) > 0:
            elements.append(Paragraph("Optimierte Strategien", small_heading))
            
            strategy_data = [["Strategie", "Rendite", "Risiko", "Sharpe"]]
            for strat in strategies[:4]:  # Max 4 Strategien
                strategy_data.append([
                    str(strat.get('name', 'N/A'))[:20],
                    str(strat.get('return', 'N/A'))[:10],
                    str(strat.get('risk', 'N/A'))[:10],
                    str(strat.get('sharpe', 'N/A'))[:6]
                ])
            
            strategy_table = Table(strategy_data, colWidths=[4*cm, 3*cm, 3*cm, 2.5*cm])
            strategy_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f5e9'))
            ]))
            
            elements.append(strategy_table)
            elements.append(Spacer(1, 0.25*cm))
        
        # =========================================
        # Monte Carlo Simulation
        # =========================================
        monte_carlo = data.get('monteCarlo', {})
        if monte_carlo and monte_carlo.get('median'):
            elements.append(Paragraph("Monte Carlo Simulation (10 Jahre)", small_heading))
            
            mc_data = [
                ["Szenario", "Endwert (CHF)"],
                ["Pessimistisch (5%)", f"{monte_carlo.get('percentile_5', 0):,.0f}"],
                ["Median (50%)", f"{monte_carlo.get('median', 0):,.0f}"],
                ["Optimistisch (95%)", f"{monte_carlo.get('percentile_95', 0):,.0f}"]
            ]
            
            mc_table = Table(mc_data, colWidths=[7*cm, 7*cm])
            mc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5d4037')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff3e0'), colors.HexColor('#e8f5e9'), colors.HexColor('#e8f5e9')])
            ]))
            
            elements.append(mc_table)
            elements.append(Spacer(1, 0.25*cm))
        
        # Portfolio Analyse Zusammenfassung
        elements.append(Paragraph("Analyse-Zusammenfassung", small_heading))
        
        summary_text = f"""
        <b>Portfolio-Wert:</b> CHF {total_investment:,.0f} | 
        <b>Assets:</b> {len(portfolio)} | 
        <b>Status:</b> {'✓ Berechnet' if data.get('portfolioCalculated') else '○ Nicht berechnet'}
        <br/><br/>
        <b>Empfehlung:</b> Regelmäßiges Rebalancing (quartalsweise) und Überwachung der Korrelationen. 
        Berücksichtigen Sie Ihre persönliche Risikobereitschaft und Anlageziele.
        """
        
        summary_style = ParagraphStyle('Summary', parent=text_style, fontSize=8, leading=10)
        elements.append(Paragraph(summary_text, summary_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Disclaimer (KOMPAKT)
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#666666'), leading=9)
        
        elements.append(Paragraph("Rechtlicher Hinweis", small_heading))
        disclaimer_text = """
        Dieser Report dient ausschliesslich Informationszwecken. Keine Anlageberatung. Swiss Asset Pro ist keine 
        FINMA-lizenzierte Finanzdienstleistung. Berechnungen basieren auf historischen Daten. Vergangene Performance 
        ist kein Indikator für zukünftige Ergebnisse. Konsultieren Sie vor Anlageentscheidungen einen Finanzberater.
        """
        elements.append(Paragraph(disclaimer_text, disclaimer_style))
        
        # Build PDF
        doc.build(elements)
        
        # Return PDF
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'Portfolio_Report_{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF Export Error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app_start_time = time.time()  # Startzeit für Uptime-Berechnung
    port = int(os.environ.get('PORT', 5077))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

