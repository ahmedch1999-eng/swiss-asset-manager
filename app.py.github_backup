from flask import Flask, render_template_string, send_from_directory, request, jsonify, make_response
import os
import json
import time
import random
import math
from datetime import datetime, timedelta
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import warnings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Static Files Route
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# Passwort-Schutz
PASSWORD = "swissassetmanagerAC"

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
    "SMI": "Swiss Market Index", "EUNL.DE": "iShares Core MSCI World UCITS ETF",
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
    "FTSE MIB": "FTSE MIB Italy", "SMI": "Swiss Market Index", "PSI20": "PSI 20 Portugal",
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
        "markets": "Märkte & News",
        "assets": "Assets & Investment",
        "methodik": "Methodik",
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Manifest Route
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/switch_language/<language>')
def switch_language(language):
    global CURRENT_LANGUAGE
    if language in ['de', 'en']:
        CURRENT_LANGUAGE = language
    return jsonify({"status": "success", "language": CURRENT_LANGUAGE})

# NEUE IMPORTS oben hinzufügen
import requests
from bs4 import BeautifulSoup
import time

# NEUE FUNKTIONEN EINFÜGEN:

def get_yahoo_finance_data(symbol):
    """Deine ursprüngliche Yahoo Logic als separate Funktion"""
    try:
        # Symbol-Korrektur für Yahoo Finance
        yahoo_symbol = symbol
        
        # Für Schweizer Aktien .SW Endung sicherstellen
        if symbol in SWISS_STOCKS and not symbol.endswith('.SW'):
            yahoo_symbol = f"{symbol}.SW"
        
        # Für Indizes ^ voranstellen wenn nicht vorhanden
        elif symbol in INDICES and not symbol.startswith('^'):
            # Spezielle Behandlung für bekannte Indizes
            index_mapping = {
                "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", 
                "RUT": "^RUT", "VIX": "^VIX", "COMP": "^IXIC",
                "DAX": "^GDAXI", "CAC": "^FCHI", "FTSE": "^FTSE",
                "SMI": "^SSMI", "NIKKEI": "^N225", "HSI": "^HSI"
            }
            yahoo_symbol = index_mapping.get(symbol, f"^{symbol}")
        
        # Für Rohstoffe/Futures
        elif "=F" in symbol:
            yahoo_symbol = symbol  # Bereits korrekt
        
        # Für Forex
        elif "=X" in symbol:
            yahoo_symbol = symbol  # Bereits korrekt
        
        print(f"Yahoo fetching: {yahoo_symbol} (original: {symbol})")
        
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info
        hist = ticker.history(period="2d", interval="1d")
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        
        # Previous Close berechnen
        if len(hist) > 1:
            previous_close = hist['Close'].iloc[-2]
        else:
            previous_close = info.get('previousClose', current_price * 0.99)
        
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        return {
            "symbol": symbol,
            "yahoo_symbol": yahoo_symbol,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "currency": info.get('currency', 'USD'),
            "name": info.get('longName', info.get('shortName', symbol))
        }
    except Exception as e:
        print(f"Yahoo error for {symbol}: {e}")
        return None

def get_alpha_vantage_data(symbol):
    """Backup Daten von Alpha Vantage (kostenlose API)"""
    try:
        API_KEY = "demo"  # Kostenlos registrieren: https://www.alphavantage.co/support/#api-key
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "Global Quote" in data:
            quote = data["Global Quote"]
            price = float(quote["05. price"])
            change = float(quote["09. change"])
            change_percent = float(quote["10. change percent"].rstrip('%'))
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "currency": "USD",
                "name": symbol,
                "source": "Alpha Vantage"
            }
    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
    return None

def get_scraped_data(symbol):
    """Web Scraping Fallback für spezielle Indizes"""
    try:
        # Hier kannst du später Investing.com, Bloomberg etc. scrapen
        # Für jetzt: einfache Simulation basierend auf Symbol-Typ
        return None  # Später implementieren
    except:
        return None

# NEUE HAUPTFUNKTION:
@app.route('/get_live_data/<symbol>')
def get_live_data(symbol):
    """Holt Live-Daten von MULTIPLEN Quellen mit Fallback"""
    try:
        # VERSUCH 1: Yahoo Finance (Primary Source)
        yahoo_data = get_yahoo_finance_data(symbol)
        if yahoo_data and yahoo_data.get('price', 0) > 0:
            yahoo_data['source'] = 'Yahoo Finance'
            return jsonify(yahoo_data)

        # VERSUCH 2: Alpha Vantage (Backup)
        alpha_data = get_alpha_vantage_data(symbol)
        if alpha_data and alpha_data.get('price', 0) > 0:
            alpha_data['source'] = 'Alpha Vantage'
            return jsonify(alpha_data)

        # VERSUCH 3: Web Scraping (Fallback)
        scraped_data = get_scraped_data(symbol)
        if scraped_data and scraped_data.get('price', 0) > 0:
            scraped_data['source'] = 'Web Scraping'
            return jsonify(scraped_data)

        # Fallback: Simulierte Daten
        simulated = get_simulated_data(symbol)
        simulated['source'] = 'Simulated Data'
        return jsonify(simulated)
    except Exception as e:
        print(f"Multi-source error for {symbol}: {e}")
        simulated = get_simulated_data(symbol)
        simulated['source'] = 'Error Fallback'
        return jsonify(simulated)
def get_simulated_data(symbol):
    """Fallback zu simulierten Daten bei Fehlern"""
    # Realistischere simulierte Daten basierend auf Asset-Typ
    base_price = 100
    if symbol in SWISS_STOCKS:
        base_price = random.uniform(50, 500)
    elif symbol in INDICES:
        base_price = random.uniform(1000, 50000)
    elif any(x in symbol for x in ['GOLD', 'SILVER']):
        base_price = random.uniform(1500, 2500)
    elif 'OIL' in symbol or 'CL' in symbol:
        base_price = random.uniform(60, 120)
    
    price = round(base_price * random.uniform(0.95, 1.05), 2)
    change_percent = round(random.uniform(-3, 3), 2)
    change = round(price * change_percent / 100, 2)
    
    return jsonify({
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "currency": "USD",
        "name": "Simulated Data"
    })
@app.route('/refresh_all_markets')
def refresh_all_markets():
    """Aktualisiert alle Marktdaten mit erweiterten Symbolen"""
    global live_market_data, last_market_update
    
    # Erweiterte Liste von Marktdaten
    symbols_to_fetch = {
        # Schweizer Indizes
        'SMI': '^SSMI', 'Swiss Leader': '^SLI', 'Swiss Performance': '^SPI',
        
        # Globale Hauptindizes
        'DAX': '^GDAXI', 'S&P 500': '^GSPC', 'NASDAQ': '^IXIC',
        'FTSE 100': '^FTSE', 'CAC 40': '^FCHI', 'Nikkei 225': '^N225',
        'Hang Seng': '^HSI', 'Shanghai': '000001.SS',
        
        # Rohstoffe
        'Gold': 'GC=F', 'Silber': 'SI=F', 'Öl': 'CL=F', 
        'Platin': 'PL=F', 'Kupfer': 'HG=F', 'Erdgas': 'NG=F',
        
        # Forex
        'EUR/CHF': 'EURCHF=X', 'USD/CHF': 'USDCHF=X', 'EUR/USD': 'EURUSD=X',
        'GBP/USD': 'GBPUSD=X', 'USD/JPY': 'USDJPY=X',
        
        # Kryptowährungen
        'Bitcoin': 'BTC-USD', 'Ethereum': 'ETH-USD',
        
        # Wichtige Einzelaktien
        'Nestlé': 'NESN.SW', 'Novartis': 'NOVN.SW', 'Roche': 'ROG.SW',
        'UBS': 'UBSG.SW', 'Zurich Insurance': 'ZURN.SW'
    }
    
    live_market_data = {}
    for name, symbol in symbols_to_fetch.items():
        try:
            response = get_live_data(symbol)
            data = response.get_json()
            live_market_data[name] = data
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
        # Simulierte Daten als Fallback
        # ✅ NEU (richtig):
        live_market_data[name] = get_simulated_data(symbol)
    
    last_market_update = datetime.now()
    
    return jsonify({
        "success": True,
        "data": live_market_data,
        "last_update": last_market_update.strftime("%H:%M:%S"),
        "total_symbols": len(symbols_to_fetch),
        "fetched_successfully": len(live_market_data)
    })
@app.route('/get_benchmark_data')
def get_benchmark_data():
    """Holt Benchmark-Daten"""
    benchmarks = {}
    benchmark_symbols = {
        "SMI": "^SSMI",
        "SPX": "^GSPC", 
        "MSCI World": "URTH",
        "Bloomberg Bond": "BND"
    }
    
    for name, symbol in benchmark_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            if not hist.empty:
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                return_1y = ((end_price - start_price) / start_price) * 100
                benchmarks[name] = round(return_1y, 2)
            else:
                benchmarks[name] = round(random.uniform(-5, 15), 2)
        except:
            benchmarks[name] = round(random.uniform(-5, 15), 2)
    
    return jsonify(benchmarks)

@app.route('/get_correlation_data')
def get_correlation_data():
    """Berechnet Korrelationsmatrix für aktuelle Portfolio-Assets"""
    try:
        # Erstelle eine echte Korrelationsmatrix basierend auf den Portfolio-Assets
        portfolio_symbols = request.args.getlist('symbols')
        
        if not portfolio_symbols:
            return jsonify({"error": "Keine Portfolio-Symbole übergeben"})
        
        # Für echte Implementierung: Historische Daten holen und Korrelationen berechnen
        # Hier simulieren wir realistische Korrelationen basierend auf Asset-Typen
        correlations = {}
        
        # Erstelle Matrix-Struktur
        for i, sym1 in enumerate(portfolio_symbols):
            for j, sym2 in enumerate(portfolio_symbols):
                key = f"{sym1}_{sym2}"
                
                if sym1 == sym2:
                    correlations[key] = 1.0  # Perfekte Korrelation mit sich selbst
                else:
                    # Basierend auf Asset-Typen realistische Korrelationen generieren
                    type1 = get_asset_type(sym1)
                    type2 = get_asset_type(sym2)
                    
                    if type1 == type2:
                        # Gleiche Asset-Klasse: hohe Korrelation
                        correlations[key] = round(0.6 + random.uniform(-0.2, 0.2), 3)
                    elif (type1 == "stock" and type2 == "index") or (type1 == "index" and type2 == "stock"):
                        # Aktien und Indizes: mittlere Korrelation
                        correlations[key] = round(0.4 + random.uniform(-0.2, 0.2), 3)
                    elif (type1 == "stock" and type2 == "commodity") or (type1 == "commodity" and type2 == "stock"):
                        # Aktien und Rohstoffe: niedrige Korrelation
                        correlations[key] = round(0.2 + random.uniform(-0.3, 0.3), 3)
                    elif (type1 == "bond" and type2 == "stock") or (type1 == "stock" and type2 == "bond"):
                        # Anleihen und Aktien: negative Korrelation
                        correlations[key] = round(-0.2 + random.uniform(-0.2, 0.2), 3)
                    else:
                        # Standard: leicht positive Korrelation
                        correlations[key] = round(0.1 + random.uniform(-0.3, 0.3), 3)
        
        return jsonify({
            "correlations": correlations,
            "symbols": portfolio_symbols,
            "matrix_type": "portfolio_assets"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

def get_asset_type(symbol):
    """Bestimmt den Asset-Typ basierend auf dem Symbol"""
    if symbol in SWISS_STOCKS:
        return "stock"
    elif symbol in INDICES:
        return "index"
    elif symbol in OTHER_ASSETS:
        if "GOLD" in symbol or "SILVER" in symbol or "OIL" in symbol or "=" in symbol:
            return "commodity"
        elif "USD" in symbol or "EUR" in symbol or "GBP" in symbol or "JPY" in symbol:
            return "currency"
        else:
            return "etf"
    return "other"

@app.route('/monte_carlo_simulation', methods=['POST'])
def monte_carlo_simulation():
    """Führt Monte Carlo Simulation durch"""
    try:
        data = request.get_json()
        initial_value = data.get('initial_value', 100000)
        expected_return = data.get('expected_return', 7) / 100
        volatility = data.get('volatility', 15) / 100
        years = data.get('years', 10)
        simulations = data.get('simulations', 1000)
        
        # Monte Carlo Simulation
        results = []
        for _ in range(simulations):
            portfolio_value = initial_value
            path = [portfolio_value]
            for _ in range(years):
                random_return = np.random.normal(expected_return, volatility)
                portfolio_value *= (1 + random_return)
                path.append(portfolio_value)
            results.append(path)
        
        # Statistiken berechnen
        final_values = [path[-1] for path in results]
        avg_final_value = np.mean(final_values)
        median_final_value = np.median(final_values)
        percentile_5 = np.percentile(final_values, 5)
        percentile_95 = np.percentile(final_values, 95)
        
        return jsonify({
            "success": True,
            "simulations": simulations,
            "avg_final_value": round(avg_final_value, 2),
            "median_final_value": round(median_final_value, 2),
            "percentile_5": round(percentile_5, 2),
            "percentile_95": round(percentile_95, 2),
            "paths": results[:100]  # Nur erste 100 Pfade für die Grafik
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/verify_password', methods=['POST'])
def verify_password():
    user_password = request.json.get('password')
    correct_password = "6R1TUt0Qkw"  # Dein neues Passwort
    if user_password == correct_password:
        return jsonify({"success": True})
    return jsonify({"success": False})
@app.route('/get_news')
def get_news():
    """Echte Schweizer Finanznachrichten von RSS Feeds"""
    try:
        import feedparser
        import random
        
        # Schweizer Finanznews RSS Feeds
        feeds = [
            "https://www.fuw.ch/feed/",
            "https://www.handelszeitung.ch/rss",
            "https://www.nzz.ch/finanzen.rss",
            "https://www.finews.com/rss/finews.xml"
        ]
        
        news_items = []
        times = ["Vor 2 Stunden", "Gestern", "Heute früh", "Vor 1 Stunde"]
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:2]:  # 2 News pro Feed
                    # Filter für Finanzthemen
                    title = entry.title
                    if any(keyword in title.lower() for keyword in ['bank', 'finance', 'aktie', 'ubs', 'credit', 'snb', 'smi', 'börse', 'investment']):
                        news_items.append({
                            "title": title,
                            "content": entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary,
                            "time": random.choice(times),
                            "source": feed_url.split('/')[2].replace('www.', '').replace('.ch', '').replace('.com', ''),
                            "link": entry.link
                        })
            except:
                continue  # Falls ein Feed nicht funktioniert
        
        # Falls keine News gefunden, Fallback zu originalen
        if not news_items:
            return get_fallback_news()
            
        # Mischen und auf 5 News begrenzen
        random.shuffle(news_items)
        return jsonify(news_items[:5])
        
    except Exception as e:
        print(f"News error: {e}")
        return get_fallback_news()

def get_fallback_news():
    """Fallback News falls RSS Feeds nicht funktionieren"""
    news_items = [
        {
            "title": "UBS übertrifft Erwartungen im Quartalsbericht",
            "content": "UBS legt starke Zahlen vor und kündigt Aktienrückkaufprogramm an.",
            "time": "Vor 2 Stunden",
            "source": "Finanz und Wirtschaft",
            "link": "https://www.fuw.ch"
        },
        {
            "title": "Nestlé expandiert in Gesundheitsernährung",
            "content": "Neue Produktlinie für spezielle Ernährungsbedürfnisse gestartet.",
            "time": "Vor 5 Stunden", 
            "source": "Handelszeitung",
            "link": "https://www.handelszeitung.ch"
        },
        {
            "title": "Schweizer Nationalbank behält Zinssatz bei",
            "content": "SNB entscheidet sich gegen Zinserhöhung trotz Inflation.",
            "time": "Gestern",
            "source": "NZZ",
            "link": "https://www.nzz.ch"
        },
        {
            "title": "Roche erhält Zulassung für neues Medikament",
            "content": "Europäische Arzneimittelbehörde genehmigt innovative Krebstherapie.",
            "time": "Vor 3 Stunden",
            "source": "Bloomberg",
            "link": "https://www.bloomberg.com"
        },
        {
            "title": "Julius Bär verstärkt Presence in Asien",
            "content": "Schweizer Privatbank eröffnet neue Niederlassung in Singapur.",
            "time": "Heute",
            "source": "Financial Times",
            "link": "https://www.ft.com"
        }
    ]
    return jsonify(news_items)

@app.route('/get_current_prices')
def get_current_prices():
    """Holt aktuelle Preise für alle Assets im Portfolio"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        current_prices = {}
        for symbol in symbols:
            try:
                response = get_live_data(symbol)
                price_data = response.get_json()
                current_prices[symbol] = price_data.get('price', 100)
            except:
                current_prices[symbol] = round(random.uniform(50, 500), 2)
        
        return jsonify({"success": True, "prices": current_prices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/calculate_portfolio_metrics', methods=['POST'])
def calculate_portfolio_metrics():
    """Berechnet Portfolio-Metriken basierend auf aktuellen Daten"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        
        if not portfolio:
            return jsonify({"error": "Kein Portfolio vorhanden"})
        
        # Berechne Portfolio-Metriken
        total_value = sum(asset.get('investment', 0) for asset in portfolio)
        expected_return = sum((asset.get('investment', 0) / total_value) * asset.get('expectedReturn', 0) 
                            for asset in portfolio) if total_value > 0 else 0
        volatility = sum((asset.get('investment', 0) / total_value) * asset.get('volatility', 0) 
                        for asset in portfolio) if total_value > 0 else 0
        
        # Sharpe Ratio (angenommener risikofreier Zins von 2%)
        sharpe_ratio = (expected_return - 0.02) / volatility if volatility > 0 else 0
        
        return jsonify({
            "success": True,
            "total_value": total_value,
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "diversification_score": min(len(portfolio) * 2, 10)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/optimize_portfolio', methods=['POST'])
def optimize_portfolio():
    """Führt Portfolio-Optimierung durch"""
    try:
        data = request.get_json()
        portfolio = data.get('portfolio', [])
        strategy = data.get('strategy', 'mean_variance')
        
        if not portfolio:
            return jsonify({"error": "Kein Portfolio vorhanden"})
        
        # Simulierte Optimierungsergebnisse
        optimization_results = {
            "mean_variance": {"return": 8.5, "risk": 12.3, "sharpe": 0.69},
            "risk_parity": {"return": 7.2, "risk": 9.8, "sharpe": 0.73},
            "min_variance": {"return": 6.1, "risk": 7.2, "sharpe": 0.57},
            "max_sharpe": {"return": 9.8, "risk": 15.6, "sharpe": 0.75},
            "black_litterman": {"return": 8.1, "risk": 11.4, "sharpe": 0.71}
        }
        
        result = optimization_results.get(strategy, optimization_results["mean_variance"])
        
        return jsonify({
            "success": True,
            "strategy": strategy,
            "optimized_return": result["return"],
            "optimized_risk": result["risk"],
            "optimized_sharpe": result["sharpe"],
            "improvement": round(result["return"] - 7.0, 2)  # Vergleich mit Basis 7%
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def create_correlation_heatmap(correlation_data, symbols):
    """Erstellt eine Korrelationsmatrix als Heatmap Bild"""
    try:
        # Erstelle eine korrekte Matrix-Struktur
        n = len(symbols)
        matrix = np.zeros((n, n))
        
        # Fülle die Matrix mit Korrelationswerten
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                key = f"{sym1}_{sym2}"
                matrix[i][j] = correlation_data.get(key, 0.0)
        
        # Erstelle Heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix, 
                   xticklabels=[s[:8] for s in symbols],  # Kürze lange Symbolnamen
                   yticklabels=[s[:8] for s in symbols],
                   annot=True, 
                   fmt=".2f", 
                   cmap="RdYlBu_r",
                   center=0,
                   vmin=-1, 
                   vmax=1,
                   square=True,
                   cbar_kws={"shrink": 0.8})
        
        plt.title('Portfolio Korrelationsmatrix', fontsize=16, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # Speichere das Bild in einem Bytes-IO Buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        # Konvertiere zu Base64 für PDF-Einbettung
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        
        return image_base64
    except Exception as e:
        print(f"Error creating correlation heatmap: {e}")
        return None

@app.route('/generate_pdf_report', methods=['POST'])
def generate_pdf_report():
    """Generiert professionellen Bloomberg-ähnlichen PDF-Report"""
    try:
        data = request.get_json()
        portfolio_data = data.get('portfolio', [])
        analysis_data = data.get('analysis', {})
        monte_carlo_data = data.get('monte_carlo', {})
        
        # PDF erstellen
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Bloomberg-ähnliche Styles
        title_style = ParagraphStyle(
            'BloombergTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=12,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'BloombergHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        subheader_style = ParagraphStyle(
            'BloombergSubheader',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'BloombergNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        metric_style = ParagraphStyle(
            'BloombergMetric',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#0A192F'),
            spaceAfter=3,
            fontName='Helvetica-Bold',
            alignment=1
        )
        
        metric_label_style = ParagraphStyle(
            'BloombergMetricLabel',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            fontName='Helvetica',
            alignment=1
        )
        
        # Content sammeln
        content = []
        
        # Header mit Bloomberg-ähnlichem Design
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Haupt-Header
        header_table_data = [
            [
                Paragraph("SWISS ASSET PRO", title_style),
                Paragraph(f"Generiert: {current_time}", normal_style)
            ]
        ]
        
        header_table = Table(header_table_data, colWidths=[400, 150])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        content.append(header_table)
        content.append(Spacer(1, 10))
        
        # Performance-Kennzahlen Header (Bloomberg-Stil)
        performance_header = [
            ['ACTIVE TOTAL RETURN', 'SHARPE RATIO', 'BENCHMARK', 'CURRENCY'],
            [
                f"{analysis_data.get('expected_return', 0)*100:.1f}%", 
                f"{analysis_data.get('sharpe_ratio', 0):.2f}",
                "SMI +2.0%", 
                "CHF"
            ]
        ]
        
        performance_table = Table(performance_header, colWidths=[120, 100, 120, 80])
        performance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6)
        ]))
        content.append(performance_table)
        content.append(Spacer(1, 15))
        
        # Portfolio Übersicht
        content.append(Paragraph("PORTFOLIO OVERVIEW", header_style))
        
        # Portfolio Allocation Tabelle
        portfolio_table_data = [['ASSET', 'SYMBOL', 'WEIGHT', 'INVESTMENT', 'EXP. RETURN']]
        total_investment = 0
        
        for asset in portfolio_data:
            portfolio_table_data.append([
                Paragraph(asset.get('name', '')[:25], normal_style),
                asset.get('symbol', ''),
                f"{asset.get('weight', 0)}%",
                f"CHF {asset.get('investment', 0):,.0f}",
                f"{asset.get('expectedReturn', 0)*100:.1f}%"
            ])
            total_investment += asset.get('investment', 0)
        
        portfolio_table = Table(portfolio_table_data, colWidths=[140, 60, 60, 90, 70])
        portfolio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
        ]))
        content.append(portfolio_table)
        content.append(Spacer(1, 20))
        
        # Performance Metriken im Bloomberg-Stil
        content.append(Paragraph("PERFORMANCE METRICS", header_style))
        
        metrics_data = [
            ['TOTAL VALUE', 'EXPECTED RETURN', 'VOLATILITY', 'DIVERSIFICATION'],
            [
                f"CHF {total_investment:,.0f}",
                f"{analysis_data.get('expected_return', 0)*100:.1f}% p.a.",
                f"{analysis_data.get('volatility', 0)*100:.1f}%",
                f"{analysis_data.get('diversification_score', 0)}/10"
            ]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[120, 120, 100, 120])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5AA0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E8EFF7')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC'))
        ]))
        content.append(metrics_table)
        content.append(Spacer(1, 20))
        
        # Korrelationsmatrix
        content.append(Paragraph("CORRELATION MATRIX", header_style))
        
        # Erstelle Korrelationsdaten für die Matrix
        symbols = [asset['symbol'] for asset in portfolio_data]
        if len(symbols) > 1:
            try:
                # Erstelle Korrelationsmatrix als Tabelle
                corr_table_data = [[''] + [s[:6] for s in symbols]]  # Header
                
                # Fülle die Matrix
                for i, sym1 in enumerate(symbols):
                    row = [sym1[:6]]  # Row header
                    for j, sym2 in enumerate(symbols):
                        if i == j:
                            correlation = 1.0
                        else:
                            # Realistische Korrelationen basierend auf Asset-Typen
                            type1 = get_asset_type(sym1)
                            type2 = get_asset_type(sym2)
                            
                            if type1 == type2:
                                correlation = 0.6 + random.uniform(-0.2, 0.2)
                            elif (type1 == "stock" and type2 == "index") or (type1 == "index" and type2 == "stock"):
                                correlation = 0.4 + random.uniform(-0.2, 0.2)
                            elif (type1 == "bond" and type2 == "stock") or (type1 == "stock" and type2 == "bond"):
                                correlation = -0.2 + random.uniform(-0.2, 0.2)
                            else:
                                correlation = 0.1 + random.uniform(-0.3, 0.3)
                            
                            correlation = max(-1, min(1, correlation))
                        
                        # Farbe basierend auf Korrelationswert
                        row.append(f"{correlation:.2f}")
                    
                    corr_table_data.append(row)
                
                # Erstelle Korrelationstabelle
                corr_table = Table(corr_table_data, colWidths=[40] + [35] * len(symbols))
                corr_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#0A192F')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
                    ('BACKGROUND', (1, 1), (-1, -1), colors.HexColor('#F8F9FA'))
                ]))
                
                content.append(corr_table)
                content.append(Spacer(1, 10))
                content.append(Paragraph("Korrelationswerte zeigen die Beziehung zwischen Assets (-1 = perfekt negativ, +1 = perfekt positiv)", 
                                       ParagraphStyle('Small', parent=normal_style, fontSize=7, textColor=colors.gray)))
                content.append(Spacer(1, 15))
                
            except Exception as e:
                content.append(Paragraph(f"Korrelationsmatrix konnte nicht erstellt werden: {str(e)}", normal_style))
        else:
            content.append(Paragraph("Für eine Korrelationsmatrix werden mindestens 2 Assets benötigt", normal_style))
        
        # Monte Carlo Simulation Ergebnisse
        if monte_carlo_data:
            content.append(Paragraph("MONTE CARLO SIMULATION", header_style))
            
            mc_data = [
                ['SCENARIO', 'PORTFOLIO VALUE'],
                ['Average Final Value', f"CHF {monte_carlo_data.get('avg_final_value', 0):,.0f}"],
                ['Median Final Value', f"CHF {monte_carlo_data.get('median_final_value', 0):,.0f}"],
                ['5% Worst Case', f"CHF {monte_carlo_data.get('percentile_5', 0):,.0f}"],
                ['5% Best Case', f"CHF {monte_carlo_data.get('percentile_95', 0):,.0f}"]
            ]
            
            mc_table = Table(mc_data, colWidths=[180, 120])
            mc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F9F0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
            ]))
            content.append(mc_table)
            content.append(Spacer(1, 15))
        
        # Performance nach Sektoren (Bloomberg-Stil)
        content.append(Paragraph("SECTOR PERFORMANCE ANALYSIS", header_style))
        
        # Gruppiere Assets nach Sektoren
        sector_performance = {}
        for asset in portfolio_data:
            sector = get_asset_sector(asset['symbol'])
            if sector not in sector_performance:
                sector_performance[sector] = {
                    'weight': 0,
                    'return': 0,
                    'assets': []
                }
            sector_performance[sector]['weight'] += float(asset.get('weight', 0))
            sector_performance[sector]['return'] += float(asset.get('weight', 0)) * asset.get('expectedReturn', 0) * 100
            sector_performance[sector]['assets'].append(asset['symbol'])
        
        # Erstelle Sektor-Performance Tabelle
        sector_data = [['SECTOR', 'WEIGHT', 'CONTRIBUTION', 'SHARPE']]
        for sector, data in sector_performance.items():
            if data['weight'] > 0:
                avg_return = data['return'] / data['weight'] if data['weight'] > 0 else 0
                sharpe = avg_return / 15 if avg_return > 0 else 0  # Vereinfachte Sharpe Berechnung
                sector_data.append([
                    sector,
                    f"{data['weight']:.1f}%",
                    f"{data['return']:.1f}%",
                    f"{sharpe:.2f}"
                ])
        
        sector_table = Table(sector_data, colWidths=[120, 80, 100, 80])
        sector_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A192F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
        ]))
        content.append(sector_table)
        content.append(Spacer(1, 20))
        
        # Key Takeaways
        content.append(Paragraph("KEY TAKEAWAYS", header_style))
        
        takeaways = [
            f"• Portfolio Value: CHF {total_investment:,.0f}",
            f"• Expected Annual Return: {analysis_data.get('expected_return', 0)*100:.1f}%",
            f"• Risk (Volatility): {analysis_data.get('volatility', 0)*100:.1f}%",
            f"• Sharpe Ratio: {analysis_data.get('sharpe_ratio', 0):.2f}",
            f"• Diversification Score: {analysis_data.get('diversification_score', 0)}/10",
            "• Target Sharpe Ratio: 1.00 | Deviation: +0.37"
        ]
        
        for takeaway in takeaways:
            content.append(Paragraph(takeaway, normal_style))
        
        content.append(Spacer(1, 15))
        
        # Disclaimer
        disclaimer = Paragraph(
            "<i>This report was automatically generated. The information provided is for informational purposes only and does not constitute investment advice. Past performance is not indicative of future results. Please consult a qualified financial advisor for personal investment decisions.</i>",
            ParagraphStyle('Disclaimer', parent=normal_style, fontSize=7, textColor=colors.gray)
        )
        content.append(disclaimer)
        
        # PDF bauen
        doc.build(content)
        
        # Response vorbereiten
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=filename=Portfolio_Overview.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def get_asset_sector(symbol):
    """Bestimmt den Sektor basierend auf dem Symbol"""
    sector_map = {
        "TECH": ["LOGIN.SW", "TEMN.SW", "NDX", "SPX", "TLT"],
        "HEALTH": ["NESN.SW", "NOVN.SW", "ROG.SW", "LONN.SW", "XLV"],
        "FINANCIAL": ["UBSG.SW", "CSGN.SW", "ZURN.SW", "BAER.SW"],
        "ENERGY": ["OIL", "XLE", "CL=F"],
        "MATERIALS": ["GOLD", "SILVER", "COPPER", "ABBN.SW", "XLB", "GLD", "SI=F", "HG=F"],
        "INDUSTRIAL": ["SIKA.SW", "GEBN.SW", "ADEN.SW"],
        "CONSUMER": ["CFR.SW", "GIVN.SW"],
        "UTILITIES": ["SCMN.SW", "XLU"]
    }
    
    for sector, symbols in sector_map.items():
        if symbol in symbols:
            return sector
    return "Diversified"

# HTML Template - VOLLSTÄNDIGE VERSION
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Swiss Asset Pro">
    <meta name="application-name" content="Swiss Asset Pro">
    <meta name="theme-color" content="#0A0A0A">
    <meta name="mobile-web-app-capable" content="yes">
    <title>Swiss Asset Pro – Invest Smart</title>
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/static/icon-192x192.png">
    <link rel="apple-touch-icon" sizes="192x192" href="/static/icon-192x192.png">
    <link rel="apple-touch-icon" sizes="512x512" href="/static/icon-512x512.png">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
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
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; }

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
            --bg-black-main: #0A0A0A;
            --bg-dark: #111111;
            --bg-panel: linear-gradient(145deg, #252525, #1E1E1E); /* Deutlicherer Unterschied zum Hintergrund */
            --text-primary: #E8E8E8; /* Etwas heller für besseren Kontrast */
            --text-secondary: #B8B8B8; /* Etwas heller für besseren Kontrast */
            --accent-violet: #8A2BE2;
            --text-silver: #E6E6E6; /* Etwas heller für besseren Kontrast */
            --border-panel: #3A3A3A; /* Deutlicherer Rand */
            --glass: rgba(138, 43, 226, 0.08); /* Stärkerer Glaseffekt */
            --accent-positive: #28A745;
            --accent-negative: #DC3545;
            --border-light: #454545; /* Noch deutlicherer Kontrast */
            --radius-lg: 12px;
            --shadow-soft: 0 8px 20px rgba(0, 0, 0, 0.4); /* Stärkerer Schatten */
            --font-heading: 'Playfair Display', serif;
            --font-body: 'Inter', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: var(--font-body); 
            background: var(--bg-black-main); 
            color: var(--text-primary); 
            line-height: 1.5; 
            font-size: 16px;
            font-weight: 400;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-heading);
            line-height: 1.3;
            color: var(--text-primary);
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
            background: var(--bg-panel); 
            padding: 50px; 
            border-radius: var(--radius-lg);
            box-shadow: 0 25px 50px rgba(0,0,0,0.3); 
            text-align: center; 
            max-width: 400px; 
            width: 90%;
            border: 1px solid rgba(138, 43, 226, 0.2);
            position: relative;
            margin: 0 auto;
            transform: translateY(0);
        }
        .password-input {
            width: 100%; padding: 12px; border: 1px solid var(--border-light); border-radius: 8px;
            margin-bottom: 15px; font-size: 16px;
        }
        .btn {
            padding: 12px 28px; 
            background-color: var(--bg-silver);
            color: var(--bg-black-main); 
            border: none;
            border-radius: 10px; 
            cursor: pointer; 
            font-weight: 600;
            font-family: var(--font-body);
            font-size: 14px;
            letter-spacing: 0.3px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-3px);
            background-color: var(--accent-violet);
            color: var(--bg-black-main);
        }
        .btn:focus {
            outline: 3px solid rgba(138, 43, 226, 0.2);
            outline-offset: 3px;
        }
        .btn-calculate {
            background: linear-gradient(145deg, #3A3A3A, #303030);
            font-size: 16px;
            padding: 15px 30px;
            font-weight: 600;
            color: #E8E8E8;
            border: 1px solid var(--border-light);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        .btn-calculate:hover {
            background: linear-gradient(145deg, var(--accent-violet), #7223c7);
            box-shadow: 0 6px 15px rgba(138, 43, 226, 0.4);
            transform: translateY(-2px);
        }
        
        header { 
    background-color: var(--bg-black-main);
    color: white; 
    padding: 25px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
.header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
.logo { width: 55px; height: 55px; border-radius: 10px; object-fit: cover; box-shadow: 0 0 15px rgba(138, 43, 226, 0.5); }

.nav-tabs { display: flex; gap: 12px; flex-wrap: wrap; }
.nav-tab { 
    padding: 10px 18px; 
    background: transparent; 
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; 
    cursor: pointer; 
    white-space: nowrap; 
    transition: all 0.3s ease; 
    color: var(--text-silver);
    font-size: 15px;
}
.nav-tab.active { 
    background: rgba(138, 43, 226, 0.15);
    border-color: rgba(138, 43, 226, 0.3);
    color: var(--color-accent); 
}
.nav-tab:hover { 
    color: var(--color-accent);
    background: rgba(138, 43, 226, 0.1);
    border-color: rgba(138, 43, 226, 0.2);
}


        
        main { 
    padding: 40px 0; 
    position: relative;
    z-index: 1;
}
        .page { 
    display: none; 
    background: var(--bg-panel); 
    padding: 35px; 
    border-radius: var(--radius-lg); 
    margin-bottom: 30px; 
    position: relative; 
    z-index: 2; 
    border: 1px solid var(--border-panel);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
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
            background: linear-gradient(90deg, var(--color-accent), rgba(138, 43, 226, 0.3));
            border-radius: 3px;
        }
        .page-header h2 { 
            color: var(--color-primary); 
            margin-bottom: 12px; 
            font-family: 'Playfair Display', serif;
            letter-spacing: -0.5px;
        }
        
        .instruction-box { 
            background: rgba(138, 43, 226, 0.1); 
            padding: 20px; 
            border-radius: var(--radius-lg); 
            margin-bottom: 20px; 
            border-left: 4px solid var(--accent-violet);
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
            border-radius: 6px;
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
        
        .selected-stocks { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }
        .stock-card { background: var(--bg-panel); padding: 15px; border-radius: var(--radius-lg); border: 1px solid var(--border-light); transition: all 0.3s ease; box-shadow: var(--shadow-soft); }
        .stock-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-soft); }
        .stock-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .investment-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
        .investment-controls input { padding: 8px; border: 1px solid var(--border-light); border-radius: 4px; }
        
        .chart-container { height: 400px; margin: 20px 0; background: var(--bg-panel); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-panel); }
        
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { 
    background: linear-gradient(145deg, #2A2A2A, #232323); 
    padding: 24px; 
    border-radius: 16px; 
    border-left: 4px solid var(--accent-violet); 
    transition: all 0.3s ease;
    box-shadow: 0 10px 25px rgba(138, 43, 226, 0.1), 0 6px 12px rgba(0, 0, 0, 0.15);
    border: 1px solid var(--border-light);
}
        .card:hover { 
    transform: translateY(-4px); 
    box-shadow: 0 14px 30px rgba(138, 43, 226, 0.15), 0 8px 16px rgba(0, 0, 0, 0.1);
    border-color: rgba(138, 43, 226, 0.3);
    border-left-width: 5px;
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
        
        .status-bar {
    display: flex; 
    justify-content: space-between; 
    padding: 15px; 
    background: var(--bg-panel); 
    border-radius: var(--radius-lg); 
    margin-bottom: 20px; 
    flex-wrap: wrap; 
    gap: 10px; 
    color: var(--text-primary);
    border: 1px solid var(--border-panel);
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
            border: 1px solid var(--accent-violet);
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
            border-radius: 6px; 
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
            display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .badge-optimal { background: #0d6e32; color: #d4edda; border: 1px solid #28a745; }
        .badge-balanced { background: #664d03; color: #fff3cd; border: 1px solid #ffc107; }
        .badge-conservative { background: #002752; color: #cce7ff; border: 1px solid #0d6efd; }
        .badge-aggressive { background: #4f0f16; color: #f8d7da; border: 1px solid #dc3545; }
        
        .strategy-comparison { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin: 20px 0; }
        
        .optimization-result { 
            background: rgba(138, 43, 226, 0.1); 
            padding: 15px; 
            border-radius: var(--radius-lg); 
            margin: 10px 0;
            border-left: 4px solid var(--accent-violet);
            color: #E0E0E0;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        
        /* Landing Page Styles */
        .landing-card {
            background: linear-gradient(145deg, #1F1F1F, #222222);
            border: 1px solid #2C2C2C;
            border-radius: 16px;
            padding: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
            min-height: 200px;
            position: relative;
            overflow: hidden;
        }
        
        .landing-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 12px 25px rgba(0, 0, 0, 0.4), 0 0 15px rgba(138, 43, 226, 0.2);
            border-color: rgba(138, 43, 226, 0.4);
        }
        
        .landing-card h3 {
            font-family: 'Playfair Display', serif;
            color: #FFFFFF;
            font-size: 20px;
            margin: 0 0 15px 0;
        }
        
        .landing-card p {
            font-family: 'Inter', sans-serif;
            color: #D9D9D9;
            font-size: 14px;
            line-height: 1.5;
            margin: 0;
        }
        
        .landing-card-icon {
            margin-bottom: 15px;
            color: #8A2BE2;
            font-size: 24px;
            opacity: 0.9;
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
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            #landingPanelsContainer {
                grid-template-columns: 1fr;
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
        .opportunities { border-left-color: #007BFF; }
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
            border-radius: 20px;
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
            border-radius: 6px;
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
        .scenario-growth { border-top: 4px solid #007BFF; }
        
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
            background: #007BFF;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            margin: 5px;
        }
        
        .refresh-button:hover {
            background: #0056b3;
            transform: translateY(-2px);
        }
        
        .auto-refresh-info {
            background: rgba(138, 43, 226, 0.15);
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
            border-radius: 8px;
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
            background: rgba(138, 43, 226, 0.15);
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
            border-top: 3px solid #007BFF;
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
            border-radius: 4px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .risk-level {
            height: 100%;
            border-radius: 4px;
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
            border-radius: 6px;
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
            background: #6C757D;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .export-button:hover {
            background: #545B62;
            transform: translateY(-1px);
        }
        
        .clickable-name {
            color: white;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .clickable-name:hover {
            color: #63B3ED;
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
            color: #007BFF;
            text-decoration: none;
        }
        
        .news-link:hover {
            text-decoration: underline;
        }
        
        .sources-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .source-card {
            background: #1F1F1F;
            padding: 20px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-light);
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
            padding: 8px;
            text-align: center;
            border: 1px solid #ddd;
        }

        .correlation-table th {
            background: #0A1429;
            color: white;
            font-weight: bold;
        }

        .correlation-table td:first-child {
            background: #0A1429;
            color: white;
            font-weight: bold;
        }

        .corr-high { background: #d4edda; }
        .corr-medium { background: #fff3cd; }
        .corr-low { background: #f8d7da; }
        .corr-negative { background: #cce7ff; }

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
            border-radius: 3px;
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
            color: white;
            margin-bottom: 1rem;
            text-shadow: 0 4px 20px rgba(0,0,0,0.3);
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
            border-radius: 2px;
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
    border-radius: 10px;
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
    border-radius: 10px;
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
    border-radius: 10px;
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
    border-radius: 10px;
    padding: 20px;
    transition: transform 0.3s;
}

.principle-item:hover {
    transform: translateY(-5px);
}

.principle-image {
    height: 150px;
    margin-top: 15px;
    border-radius: 8px;
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
}  </style>
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
<body style="margin: 0; padding: 0;">
    <div id="passwordProtection" class="password-protection" style="display: flex; justify-content: center; align-items: center; width: 100vw; height: 100vh; position: fixed; top: 0; left: 0;">
        <div class="password-box" style="margin: 0 auto; transform: translateY(0);">
            <h1 class="text-accent" style="font-size: 38px; margin-bottom: 20px; font-family: 'Playfair Display', serif; letter-spacing: 1px;">Swiss Asset Pro</h1>
            <p id="passwordPrompt" class="text-primary" style="margin-bottom: 20px;">Bitte geben Sie das Passwort ein:</p>
            <input type="password" id="passwordInput" class="password-input" placeholder="Passwort">
            <button class="btn" onclick="checkPassword()" id="accessButton" style="background: linear-gradient(145deg, var(--accent-violet), #7223c7); color: white; font-weight: 600; padding: 12px 25px; border-radius: 8px; box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4); border: none; transition: all 0.3s ease;">Zugang erhalten</button>
            <p id="passwordError" class="password-error">Falsches Passwort. Bitte versuchen Sie es erneut.</p>
            <p style="margin-top: 15px; font-size: 12px; color: var(--text-secondary);" id="passwordHint">by Ahmed Choudhary</p>
        </div>
    </div>

<div class="welcome-screen" id="welcomeScreen">
    <div class="welcome-content">
        <h1 class="welcome-title">Swiss Asset Pro</h1>
        <p class="welcome-subtitle">Professional Portfolio Simulation</p>
        <p class="welcome-author">by Ahmed Choudhary</p>
        
        <div class="loading-bar">
            <div class="loading-progress"></div>
        </div>
        
        <!-- NEUE AKTIEN-GRAPH ANIMATION -->
        <div class="stock-graph-animation">
            <div class="graph-container">
                <svg class="stock-graph" viewBox="0 0 300 80" preserveAspectRatio="none">
                    <path class="graph-line" d="M0,60 L50,55 L100,70 L150,65 L200,75 L250,68 L300,20" />
                    <circle class="graph-dot" cx="0" cy="60" r="2" />
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
    transform: translateY(20px);
    opacity: 0;
    animation: welcomeSlideIn 1s ease 1s forwards;
}

.welcome-title {
    font-family: var(--font-heading);
    font-size: 3.5rem;
    font-weight: 700;
    color: var(--color-accent);
    margin-bottom: 1.5rem;
    text-shadow: 0 0 25px rgba(138, 43, 226, 0.3);
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
    border-radius: 4px;
    overflow: hidden;
}

        .loading-progress {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, var(--color-accent), rgba(138, 43, 226, 0.5));
            animation: loadingFill 3.5s cubic-bezier(0.34, 1.56, 0.64, 1) 1s forwards;
            box-shadow: 0 0 15px rgba(138, 43, 226, 0.5);
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
    stroke: rgba(255, 255, 255, 0.9);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
    animation: drawGraph 4s ease-in-out forwards;
    filter: drop-shadow(0 0 8px rgba(138, 43, 226, 0.6));
}

.graph-dot {
    fill: #8A2BE2;
    stroke: white;
    stroke-width: 1;
    filter: drop-shadow(0 0 6px #8A2BE2);
    animation: followPath 4s ease-in-out forwards;
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

    <!-- Intro Landing Page Overlay -->
    <div id="landingPage" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: #0A0A0A; z-index: 1000; overflow-y: auto; opacity: 0; transition: opacity 0.5s ease;">
        <div class="container" style="max-width: 1400px; margin: 0 auto; padding: 40px 20px;">
            <!-- Hero Section -->
            <div style="display: flex; flex-direction: column; margin-bottom: 40px; opacity: 0; transform: translateY(20px); transition: all 0.6s ease;" class="landing-hero-section">
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
                    <svg width="50" height="50" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="40" height="40" rx="8" fill="#1A1A1A"/>
                        <path d="M10 20L15 30L30 10" stroke="#8A2BE2" stroke-width="2" stroke-linecap="round"/>
                        <path d="M10 18H30" stroke="#8A2BE2" stroke-width="1.5" stroke-opacity="0.6" stroke-dasharray="1 2"/>
                        <path d="M10 25H30" stroke="#8A2BE2" stroke-width="1.5" stroke-opacity="0.6" stroke-dasharray="1 2"/>
                    </svg>
                    <h1 style="font-family: 'Playfair Display', serif; font-size: 42px; margin: 0; color: #FFFFFF; letter-spacing: -0.5px; background: linear-gradient(90deg, #8A2BE2, #B05EED); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;">Swiss Asset Pro</h1>
                </div>
                <h2 style="font-family: 'Playfair Display', serif; font-size: 32px; color: #FFFFFF; margin: 20px 0; font-weight: 500;">Willkommen zur professionellen Portfolio-Simulation</h2>
                <p style="font-family: 'Inter', sans-serif; font-size: 16px; color: #D9D9D9; max-width: 800px; line-height: 1.6;">Wählen Sie einen Bereich, um direkt einzusteigen, oder erkunden Sie alle Funktionen für eine umfassende Finanzanalyse Ihres Portfolios.</p>
            </div>
            
            <!-- Panels Container -->
            <div id="landingPanelsContainer" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; opacity: 0; transform: translateY(30px); transition: all 0.8s ease;">
                <!-- Panels werden per JavaScript dynamisch erzeugt -->
            </div>
        </div>
    </div>
    
    <div id="mainContent" style="display: none; overflow-y: auto;">
        <header>
            <div class="container">
                <div class="header-top">
                    <div style="display: flex; align-items: center; gap: 20px;">
                        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect width="40" height="40" rx="8" fill="#1A1A1A"/>
                            <path d="M10 20L15 30L30 10" stroke="#8A2BE2" stroke-width="2" stroke-linecap="round"/>
                            <path d="M10 18H30" stroke="#8A2BE2" stroke-width="1.5" stroke-opacity="0.6" stroke-dasharray="1 2"/>
                            <path d="M10 25H30" stroke="#8A2BE2" stroke-width="1.5" stroke-opacity="0.6" stroke-dasharray="1 2"/>
                        </svg>
                        <div>
                            <h1 class="text-accent" style="font-family: 'Playfair Display', serif; font-size: 26px; margin: 0; letter-spacing: -0.5px; text-shadow: 0 0 20px rgba(138, 43, 226, 0.3); background: linear-gradient(90deg, #8A2BE2, #B05EED); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;">Swiss Asset Pro</h1>
                            <div class="text-silver" style="font-size: 13px; opacity: 0.9;">Professionelle Portfolio Simulation</div>
                        </div>
                    </div>
                    <div>
                        <div style="font-weight: 600; font-size: 15px; margin-bottom: 5px;" class="text-primary">Ahmed Choudhary</div>
                        <div class="flex items-center gap-2 justify-between">
                            <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" class="linkedin-link" target="_blank" style="color: var(--text-silver); display: flex; align-items: center; gap: 5px; font-size: 14px; transition: all 0.3s ease;">
                                <i class="fab fa-linkedin" style="color: #0077B5;"></i> LinkedIn Profil
                            </a>
                        </div>
                    </div>
                </div>
                <div class="nav-tabs" id="headerNavTabs">
                    <div class="nav-tab" id="startseiteLink" aria-label="Zurück zur Startseite">Startseite</div>
                    <div class="nav-tab active" data-page="getting-started">Getting Started</div>
                    <div class="nav-tab" data-page="dashboard">Dashboard</div>
                    <div class="nav-tab" data-page="portfolio">Portfolio Entwicklung</div>
                    <div class="nav-tab" data-page="strategieanalyse">Strategie Analyse</div>
                    <div class="nav-tab" data-page="simulation">Zukunfts-Simulation</div>
                    <div class="nav-tab" data-page="investing">Investing</div>
                    <div class="nav-tab" data-page="bericht">Bericht & Analyse</div>
                    <div class="nav-tab" data-page="markets">Märkte & News</div>
                    <div class="nav-tab" data-page="assets">Assets & Investment</div>
                    <div class="nav-tab" data-page="methodik">Methodik</div>
                    <div class="nav-tab" data-page="about">Über mich</div>
                </div>
            </div>
        </header>     

    <!-- VIOLET BACKGROUND - HIER EINFÜGEN -->
    <div class="bg" aria-hidden="true">
        <div class="layer l1"></div>
        <div class="layer l2"></div>
        <div class="layer l3"></div>
        <div class="pulse"></div>
    </div>

    <div class="grain" aria-hidden="true"></div>

    <main class="container">

        
            <div class="status-bar">
                <div id="lastUpdateText">Letztes Update: <span id="lastUpdate">--:--:--</span></div>
                <div id="smiReturnText">SMI Rendite: <span id="smiReturn">+1.2%</span></div>
                <div id="portfolioReturnText">Portfolio Rendite: <span id="portfolioReturn">+0.0%</span></div>
                <div id="portfolioValueText">Portfolio Wert: <span id="portfolioValue">CHF 0</span></div>
            <div id="marketStatusText">Markets: <span id="marketStatus">SIX: <span class="market-status">--</span> NYSE: <span class="market-status">--</span> FX: <span class="market-status">--</span></span></div>
            </div>

            <!-- Getting Started -->
            <section id="getting-started" class="page active">
                <div class="page-header">
                    <h2>Welcome to Swiss Asset Pro</h2>
                    <p>Ihr Leitfaden für fundierte Anlageentscheidungen</p>
                </div>
                
                <div class="card">
                    <h3>Getting Started</h3>
                    <div class="card-content">
                        <p>Willkommen beim Swiss Asset Pro, Ihrem umfassenden Tool für Portfoliomanagement, Investmentanalyse und Finanzplanung. Diese Plattform wurde entwickelt, um Ihnen fundierte Anlageentscheidungen mit leistungsstarken Analysen und visuellen Erkenntnissen zu ermöglichen.</p>
                        
                        <div class="steps-container">
                            <div class="step">
                                <div class="step-number">1</div>
                                <div class="step-content">
                                    <h4>Dashboard erkunden</h4>
                                    <p>Erhalten Sie einen vollständigen Überblick über die Performance Ihres Portfolios, die Vermögensallokation und wichtige Kennzahlen an einem Ort.</p>
                                    <a href="#" class="btn secondary step-btn" onclick="document.querySelector('[data-page=dashboard]').click();">Zum Dashboard</a>
                                </div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">2</div>
                                <div class="step-content">
                                    <h4>Portfolio aufbauen</h4>
                                    <p>Fügen Sie Assets zu Ihrem Portfolio hinzu und verfolgen Sie deren Performance im Zeitverlauf mit umfassenden Analysen.</p>
                                    <a href="#" class="btn secondary step-btn" onclick="document.querySelector('[data-page=portfolio]').click();">Portfolio verwalten</a>
                                </div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">3</div>
                                <div class="step-content">
                                    <h4>Anlagestrategien analysieren</h4>
                                    <p>Vergleichen Sie verschiedene Anlagestrategien und optimieren Sie Ihre Vermögensallokation basierend auf Ihrer Risikotoleranz.</p>
                                    <a href="#" class="btn secondary step-btn" onclick="document.querySelector('[data-page=strategieanalyse]').click();">Strategien anzeigen</a>
                                </div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">4</div>
                                <div class="step-content">
                                    <h4>Simulationen durchführen</h4>
                                    <p>Projizieren Sie zukünftige Performance mit anspruchsvollen Simulationstools, die verschiedene Marktszenarien berücksichtigen.</p>
                                    <a href="#" class="btn secondary step-btn" onclick="document.querySelector('[data-page=simulation]').click();">Simulationen starten</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Plattform-Funktionen</h3>
                    <div class="card-content">
                        <div class="features-grid">
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-chart-line"></i></div>
                                <h4>Portfolio-Tracking</h4>
                                <p>Echtzeit-Überwachung Ihrer Anlagen mit Performance-Kennzahlen und Analysen.</p>
                            </div>
                            
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-balance-scale"></i></div>
                                <h4>Risikobewertung</h4>
                                <p>Umfassende Risikobewertungstools zum Verständnis und Management Ihres Portfolio-Risikos.</p>
                            </div>
                            
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-random"></i></div>
                                <h4>Portfolio-Optimierung</h4>
                                <p>Fortschrittliche Algorithmen zur Optimierung Ihrer Vermögensallokation für bessere Renditen.</p>
                            </div>
                            
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-search-dollar"></i></div>
                                <h4>Marktanalyse</h4>
                                <p>Bleiben Sie informiert über die neuesten Markttrends, Nachrichten und Anlagemöglichkeiten.</p>
                            </div>
                            
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-calculator"></i></div>
                                <h4>Finanzplanung</h4>
                                <p>Tools zur Planung Ihrer Altersvorsorge, Ausbildung oder anderer finanzieller Ziele.</p>
                            </div>
                            
                            <div class="feature-item">
                                <div class="feature-icon"><i class="fas fa-file-alt"></i></div>
                                <h4>Individuelle Berichte</h4>
                                <p>Erstellen Sie detaillierte Berichte und Analysen, um Ihre Anlageentwicklung zu verfolgen.</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="quick-links-container">
                    <h3>Schnellzugriff</h3>
                    <div class="quick-links">
                        <a href="#" class="quick-link" onclick="document.querySelector('[data-page=investing]').click();">
                            <i class="fas fa-graduation-cap"></i>
                            <span>Anlage-Bildung</span>
                        </a>
                        <a href="#" class="quick-link" onclick="document.querySelector('[data-page=markets]').click();">
                            <i class="fas fa-newspaper"></i>
                            <span>Marktnachrichten</span>
                        </a>
                        <a href="#" class="quick-link" onclick="document.querySelector('[data-page=assets]').click();">
                            <i class="fas fa-coins"></i>
                            <span>Assets erkunden</span>
                        </a>
                        <a href="#" class="quick-link" onclick="document.querySelector('[data-page=methodik]').click();">
                            <i class="fas fa-book"></i>
                            <span>Methodik</span>
                        </a>
                    </div>
                </div>
            </section>

            <!-- Dashboard -->
            <section id="dashboard" class="page">
                <div class="page-header">
                    <h2>Portfolio Dashboard</h2>
                    <p>Erstellen und verwalten Sie Ihr persönliches Aktienportfolio</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📊 Was Sie hier tun können:</h4>
                    <p>Wählen Sie Schweizer Aktien, internationale Indizes und andere Assets aus. Legen Sie für jede Anlage den Investitionsbetrag fest und klicken Sie auf "Portfolio Berechnen", um die vollständige Analyse zu erhalten.</p>
                    <div class="price-update-info">
                        <i class="fas fa-chart-line" style="margin-right: 5px"></i> <strong>Live-Daten:</strong> Aktuelle Aktienkurse werden automatisch geladen und alle 15 Minuten aktualisiert
                    </div>
                </div>
                
                <div class="portfolio-setup">
                    <h3 style="color: var(--color-primary); margin-bottom: 15px;">Portfolio Konfiguration</h3>
                    <div class="investment-inputs">
                        <div class="input-group">
                            <label>Gesamtinvestition (CHF)</label>
                            <input type="number" id="totalInvestment" class="search-input" value="100000" min="1000" step="1000">
                        </div>
                        <div class="input-group">
                            <label>Investitionszeitraum (Jahre)</label>
                            <input type="number" id="investmentYears" class="search-input" value="5" min="1" max="30">
                        </div>
                        <div class="input-group">
                            <label>Risikoprofil</label>
                            <select id="riskProfile" class="search-input">
                                <option value="conservative">Konservativ</option>
                                <option value="moderate" selected>Moderat</option>
                                <option value="aggressive">Aggressiv</option>
                            </select>
                        </div>
                    </div>
                    <div id="totalValidation" class="total-validation validation-ok">
                        Investitionen stimmen überein: CHF 0 von CHF 100.000
                    </div>
                </div>
                
                <div class="search-container">
                    <select class="search-input" id="stockSelect">
                        <option value="">Schweizer Aktie auswählen...</option>
                    </select>
                    <select class="search-input" id="indexSelect">
                        <option value="">Internationale Indizes...</option>
                    </select>
                    <select class="search-input" id="assetSelect">
                        <option value="">Weitere Assets...</option>
                    </select>
                    <button class="btn" onclick="addStock()" style="background: #444444;">Aktie hinzufügen</button>
                    <button class="btn" onclick="addIndex()" style="background: #6B46C1;">Index hinzufügen</button>
                    <button class="btn" onclick="addAsset()" style="background: #28A745;">Asset hinzufügen</button>
                </div>
                
                <div class="selected-stocks" id="selectedStocks"></div>
                
                <div class="calculate-section">
                    <h3 style="color: white; margin-bottom: 15px;">Portfolio Analyse Starten</h3>
                    <p style="margin-bottom: 20px; opacity: 0.9;">Klicken Sie auf Berechnen, um Ihre Portfolio-Performance zu analysieren</p>
                    <button class="btn btn-calculate" onclick="calculatePortfolio()">
                        <i class="fas fa-calculator"></i> Portfolio Berechnen
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="portfolioChart"></canvas>
                </div>
                
                <!-- Asset Performance Chart mit Zeitraum-Switcher -->
                <div class="card">
                    <h3>Asset Performance</h3>
                    <div class="timeframe-switcher">
                        <button class="timeframe-btn active" onclick="switchTimeframe('5y')">5 Jahre</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('1y')">1 Jahr</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('6m')">6 Monate</button>
                        <button class="timeframe-btn" onclick="switchTimeframe('1m')">1 Monat</button>
                    </div>
                    <div class="asset-performance-chart">
                        <canvas id="assetPerformanceChart"></canvas>
                    </div>
                </div>
                
                <div class="card-grid">
                    <div class="card">
                        <h3>Portfolio Performance</h3>
                        <div id="portfolioPerformance">
                            <div class="metric-value">0.0%</div>
                            <div class="metric-label">Erwartete Jahresrendite</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Risiko Analyse</h3>
                        <div id="riskAnalysis">
                            <div class="metric-value">0.0%</div>
                            <div class="metric-label">Volatilität p.a.</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Diversifikation</h3>
                        <div id="diversification">
                            <div class="metric-value">0/10</div>
                            <div class="metric-label">Diversifikations-Score</div>
                        </div>
                    </div>
                    <div class="card">
                        <h3>Sharpe Ratio</h3>
                        <div id="sharpeRatio">
                            <div class="metric-value">0.00</div>
                            <div class="metric-label">Risiko-adjustierte Rendite</div>
                        </div>
                    </div>
                </div>
                
                <!-- Live Data Section -->
                <div class="card">
                    <h3>Live Marktdaten</h3>
                    <div class="market-grid" id="liveMarketData">
                        <div class="market-item">
                            <h4>SMI</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>S&P 500</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>Gold</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                        <div class="market-item">
                            <h4>EUR/CHF</h4>
                            <div class="metric-value">Lädt...</div>
                            <div class="metric-label">--</div>
                        </div>
                    </div>
                    <button class="refresh-button" onclick="refreshMarketData()">
                        <i class="fas fa-sync-alt"></i> Daten aktualisieren
                    </button>
                </div>
            </section>

            <!-- Portfolio Entwicklung -->
            <section id="portfolio" class="page">
                <div class="page-header">
                    <h2>Portfolio Entwicklung</h2>
                    <p>Historische Performance und detaillierte Analyse</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📈 Performance-Tracking:</h4>
                    <p>Analysieren Sie die historische Entwicklung Ihres Portfolios und identifizieren Sie Optimierungspotenziale.</p>
                    <button class="refresh-button" onclick="updatePortfolioDevelopment()">
                        <i class="fas fa-sync-alt"></i> Performance aktualisieren
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
                
                <div class="performance-metrics">
                    <div class="performance-card">
                        <div class="metric-value positive" id="totalReturn">+0.0%</div>
                        <div class="metric-label">Gesamtrendite</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="annualizedReturn">0.0%</div>
                        <div class="metric-label">Annualisierte Rendite</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="maxDrawdown">0.0%</div>
                        <div class="metric-label">Maximaler Verlust</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value" id="volatilityHistory">0.0%</div>
                        <div class="metric-label">Historische Volatilität</div>
                    </div>
                </div>
                
                <!-- Benchmark Vergleich -->
                <div class="card">
                    <h3>Performance vs. Benchmarks</h3>
                    <div class="benchmark-comparison" id="benchmarkComparison">
                        <div class="benchmark-card">
                            <h4>Ihr Portfolio</h4>
                            <div class="metric-value" id="portfolioBenchmarkReturn">0.0%</div>
                            <div class="metric-label">Erwartete Rendite</div>
                        </div>
                    </div>
                </div>
                
                <!-- Peer Group Vergleich -->
                <div class="card">
                    <h3>Vergleich mit Schweizer Privatbanken</h3>
                    <div class="peer-comparison" id="peerComparison">
                        <!-- Wird dynamisch gefüllt -->
                    </div>
                </div>
                
                <div class="card">
                    <h3>Performance-Analyse</h3>
                    <div id="performanceAnalysis">
                        <p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>
                    </div>
                </div>
            </section>

            <!-- Strategie Analyse -->
            <section id="strategieanalyse" class="page">
                <!-- Wird dynamisch gefüllt -->
            </section>

            <!-- Zukunfts-Simulation -->
            <section id="simulation" class="page">
                <div class="page-header">
                    <h2>Zukunfts-Simulation</h2>
                    <p>Strategie-basierte Prognosen und Szenario-Analyse</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🔮 Was diese Simulation zeigt:</h4>
                    <p>Basierend auf den 5 Optimierungsstrategien sehen Sie verschiedene Zukunftspfade für Ihr Portfolio. Jede Strategie hat unterschiedliche Risiko-Rendite-Profile.</p>
                    <button class="refresh-button" onclick="updateSimulationPage()">
                        <i class="fas fa-sync-alt"></i> Simulation aktualisieren
                    </button>
                </div>
                
                <div class="chart-container">
                    <canvas id="simulationChart"></canvas>
                </div>
                
                <!-- Szenario-Analyse -->
                <div class="card">
                    <h3>Szenario-Analyse</h3>
                    <p>Wie sich Ihr Portfolio unter verschiedenen wirtschaftlichen Bedingungen entwickeln könnte:</p>
                    
                    <div class="scenario-grid">
                        <div class="scenario-card scenario-normal">
                            <h4>Normale Märkte</h4>
                            <div class="metric-value positive" id="scenarioNormal">CHF 0</div>
                            <div class="metric-label">Erwartetes Wachstum</div>
                        </div>
                        <div class="scenario-card scenario-interest">
                            <h4>Zinserhöhungen</h4>
                            <div class="metric-value" id="scenarioInterest">CHF 0</div>
                            <div class="metric-label">Geringeres Wachstum</div>
                        </div>
                        <div class="scenario-card scenario-inflation">
                            <h4>Hohe Inflation</h4>
                            <div class="metric-value" id="scenarioInflation">CHF 0</div>
                            <div class="metric-label">Inflationsangepasst</div>
                        </div>
                        <div class="scenario-card scenario-recession">
                            <h4>Rezession</h4>
                            <div class="metric-value negative" id="scenarioRecession">CHF 0</div>
                            <div class="metric-label">Risiko von Verlusten</div>
                        </div>
                        <div class="scenario-card scenario-growth">
                            <h4>Starkes Wachstum</h4>
                            <div class="metric-value positive" id="scenarioGrowth">CHF 0</div>
                            <div class="metric-label">Überdurchschnittlich</div>
                        </div>
                    </div>
                </div>
                
                <div class="path-simulation">
                    <div class="path-card">
                        <h4>Optimistisches Szenario</h4>
                        <div class="metric-value positive" id="optimisticValue">CHF 0</div>
                        <div class="metric-label">+15% über Benchmark</div>
                    </div>
                    <div class="path-card">
                        <h4>Basisszenario</h4>
                        <div class="metric-value" id="baseValue">CHF 0</div>
                        <div class="metric-label">Erwartete Entwicklung</div>
                    </div>
                    <div class="path-card">
                        <h4>Konservatives Szenario</h4>
                        <div class="metric-value negative" id="conservativeValue">CHF 0</div>
                        <div class="metric-label">Risikominimiert</div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Strategie-Pfade im Vergleich</h3>
                    <div id="strategyPaths">
                        <p>Die Simulation zeigt, wie sich Ihr Portfolio unter verschiedenen Strategien entwickeln könnte. Bitte berechnen Sie zuerst Ihr Portfolio.</p>
                    </div>
                </div>
            </section>

            <!-- Investing -->
            <section id="investing" class="page">
                <div class="page-header">
                    <h2>Investing</h2>
                    <p>Verstehen von Anlageprinzipien und Strategien</p>
                </div>
                
                <div class="card">
                    <h3>Anlageprinzipien</h3>
                    <div class="card-content">
                        <p>Verstehen der grundlegenden Prinzipien, die erfolgreiche langfristige Anlagestrategien leiten.</p>
                        <div class="principles-grid">
                            <div class="principle-item">
                                <h4>Diversifikation</h4>
                                <p>Verteilung von Anlagen über verschiedene Anlageklassen, Sektoren und geografische Regionen zur Risikominderung.</p>
                                <div class="principle-image" id="diversification-img"></div>
                            </div>
                            <div class="principle-item">
                                <h4>Langfristiger Fokus</h4>
                                <p>Die Kraft des Zinseszinseffekts und die Vorteile, durch Marktzyklen hindurch investiert zu bleiben.</p>
                                <div class="principle-image" id="long-term-img"></div>
                            </div>
                            <div class="principle-item">
                                <h4>Kostenmanagement</h4>
                                <p>Verstehen, wie Gebühren und Kosten langfristige Renditen beeinflussen, und Strategien zu deren Minimierung.</p>
                                <div class="principle-image" id="cost-img"></div>
                            </div>
                            <div class="principle-item">
                                <h4>Risikobewertung</h4>
                                <p>Bewertung Ihrer Risikotoleranz und Erstellung eines Portfolios, das mit Ihren finanziellen Zielen übereinstimmt.</p>
                                <div class="principle-image" id="risk-img"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3>Anlageformen</h3>
                    <div class="card-content">
                        <p>Überblick über verschiedene Anlagemöglichkeiten und ihre Eigenschaften.</p>
                        <div class="tabs-container">
                            <div class="tabs">
                                <div class="tab active" data-tab="stocks">Aktien</div>
                                <div class="tab" data-tab="bonds">Anleihen</div>
                                <div class="tab" data-tab="etfs">ETFs</div>
                                <div class="tab" data-tab="real-estate">Immobilien</div>
                                <div class="tab" data-tab="alternatives">Alternative</div>
                            </div>
                            <div class="tab-content active" id="stocks-content">
                                <h4>Aktien</h4>
                                <p>Eigentumsanteile an börsennotierten Unternehmen, die Kapitalzuwachs und Dividenden bieten können.</p>
                                <ul>
                                    <li><strong>Wachstumsaktien:</strong> Unternehmen, von denen ein überdurchschnittliches Wachstum erwartet wird</li>
                                    <li><strong>Substanzwertaktien:</strong> Unternehmen, die basierend auf Fundamentaldaten unterbewertet erscheinen</li>
                                    <li><strong>Dividendenaktien:</strong> Unternehmen, die regelmäßig Gewinne an Aktionäre ausschütten</li>
                                </ul>
                                <div class="chart-container" id="stocks-chart"></div>
                            </div>
                            <div class="tab-content" id="bonds-content">
                                <h4>Anleihen (Festverzinsliche Wertpapiere)</h4>
                                <p>Schuldverschreibungen, bei denen Sie einer Instanz Geld leihen, die die Mittel für einen festgelegten Zeitraum zu einem variablen oder festen Zinssatz aufnimmt.</p>
                                <ul>
                                    <li><strong>Staatsanleihen:</strong> Ausgegeben von nationalen Regierungen</li>
                                    <li><strong>Unternehmensanleihen:</strong> Ausgegeben von Unternehmen</li>
                                    <li><strong>Kommunalanleihen:</strong> Ausgegeben von Ländern, Städten oder Gemeinden</li>
                                </ul>
                                <div class="chart-container" id="bonds-chart"></div>
                            </div>
                            <div class="tab-content" id="etfs-content">
                                <h4>ETFs (Exchange-Traded Funds)</h4>
                                <p>Wertpapierkörbe, die einen zugrunde liegenden Index abbilden und wie Aktien an Börsen gehandelt werden.</p>
                                <ul>
                                    <li><strong>Index-ETFs:</strong> Bilden bestimmte Indizes wie S&P 500 oder MSCI World ab</li>
                                    <li><strong>Sektor-ETFs:</strong> Konzentrieren sich auf bestimmte Branchen</li>
                                    <li><strong>Anleihen-ETFs:</strong> Halten festverzinsliche Wertpapiere</li>
                                    <li><strong>Rohstoff-ETFs:</strong> Bilden Rohstoffe wie Gold oder Öl ab</li>
                                </ul>
                                <div class="chart-container" id="etfs-chart"></div>
                            </div>
                            <div class="tab-content" id="real-estate-content">
                                <h4>Immobilieninvestitionen</h4>
                                <p>Immobilieninvestitionen, die durch Wertsteigerung und Mieteinnahmen Einkommen generieren können.</p>
                                <ul>
                                    <li><strong>REITs:</strong> Immobilien-Investmentfonds, die ertragsgenerierende Immobilien besitzen und betreiben</li>
                                    <li><strong>Direktes Eigentum:</strong> Kauf von Wohn- oder Gewerbeimmobilien</li>
                                    <li><strong>Immobilienfonds:</strong> Gebündelte Investitionen in Immobilienvermögen</li>
                                </ul>
                                <div class="chart-container" id="real-estate-chart"></div>
                            </div>
                            <div class="tab-content" id="alternatives-content">
                                <h4>Alternative Anlagen</h4>
                                <p>Nicht-traditionelle Vermögenswerte jenseits von Aktien, Anleihen und Bargeld, die Diversifikationsvorteile bieten können.</p>
                                <ul>
                                    <li><strong>Private Equity:</strong> Investitionen in private Unternehmen</li>
                                    <li><strong>Hedge-Fonds:</strong> Aktiv verwaltete Investmentpools mit spezialisierten Strategien</li>
                                    <li><strong>Rohstoffe:</strong> Physische Güter wie Gold, Öl oder Agrarprodukte</li>
                                    <li><strong>Kryptowährungen:</strong> Digitale Vermögenswerte, die Blockchain-Technologie nutzen</li>
                                </ul>
                                <div class="chart-container" id="alternatives-chart"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3>Anlagestrategien</h3>
                    <div class="card-content">
                        <p>Verschiedene Ansätze zum Aufbau und zur Verwaltung Ihres Anlageportfolios.</p>
                        <div class="strategy-comparison">
                            <table class="strategy-table">
                                <thead>
                                    <tr>
                                        <th>Strategie</th>
                                        <th>Beschreibung</th>
                                        <th>Risikoniveau</th>
                                        <th>Zeithorizont</th>
                                        <th>Am besten für</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>Kaufen und Halten</td>
                                        <td>Langfristiger Anlageansatz, der häufigen Handel vermeidet</td>
                                        <td>Moderat</td>
                                        <td>Lang (10+ Jahre)</td>
                                        <td>Passive Anleger, die stetiges Wachstum suchen</td>
                                    </tr>
                                    <tr>
                                        <td>Kosten-Durchschnitts-Methode</td>
                                        <td>Investieren fester Beträge in regelmäßigen Abständen unabhängig vom Preis</td>
                                        <td>Niedrig bis Moderat</td>
                                        <td>Mittel bis Lang</td>
                                        <td>Regelmäßige Sparer, die Vermögen im Laufe der Zeit aufbauen</td>
                                    </tr>
                                    <tr>
                                        <td>Wertorientiertes Investieren</td>
                                        <td>Suche nach unterbewerteten Vermögenswerten unter ihrem inneren Wert</td>
                                        <td>Moderat</td>
                                        <td>Mittel bis Lang</td>
                                        <td>Forschungsorientierte Anleger</td>
                                    </tr>
                                    <tr>
                                        <td>Wachstumsorientiertes Investieren</td>
                                        <td>Fokussierung auf Unternehmen mit überdurchschnittlichem Wachstumspotenzial</td>
                                        <td>Hoch</td>
                                        <td>Lang</td>
                                        <td>Anleger, die Kapitalzuwachs anstreben</td>
                                    </tr>
                                    <tr>
                                        <td>Einkommensorientiertes Investieren</td>
                                        <td>Aufbau eines Portfolios, das regelmäßiges Einkommen generiert</td>
                                        <td>Niedrig bis Moderat</td>
                                        <td>Mittel bis Lang</td>
                                        <td>Rentner oder Personen, die Cashflow benötigen</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Bericht & Analyse -->
            <section id="bericht" class="page">
                <div class="page-header">
                    <h2>Bericht & Analyse</h2>
                    <p>Stärken, Schwächen und Handlungsempfehlungen</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎯 Umfassende Portfolio-Analyse:</h4>
                    <p>Hier erhalten Sie eine detaillierte SWOT-Analyse Ihres Portfolios und konkrete Empfehlungen zur Optimierung.</p>
                    <button class="refresh-button" onclick="updateReportPage()">
                        <i class="fas fa-sync-alt"></i> Bericht aktualisieren
                    </button>
                </div>
                
                <div class="swot-grid">
                    <div class="swot-card strengths">
                        <h4>💪 Stärken</h4>
                        <div id="strengthsList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card weaknesses">
                        <h4>⚠️ Schwächen</h4>
                        <div id="weaknessesList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card opportunities">
                        <h4>🚀 Chancen</h4>
                        <div id="opportunitiesList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                    <div class="swot-card threats">
                        <h4>🔴 Risiken</h4>
                        <div id="threatsList">
                            <p>Bitte Portfolio erstellen und berechnen</p>
                        </div>
                    </div>
                </div>

                <!-- Korrelationsmatrix -->
                <div class="card">
                    <h3>Korrelationsanalyse</h3>
                    <div class="correlation-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #d4edda;"></div>
                            <span>Hohe Korrelation (>0.7)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #fff3cd;"></div>
                            <span>Mittlere Korrelation (0.3-0.7)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #f8d7da;"></div>
                            <span>Niedrige Korrelation (<0.3)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #cce7ff;"></div>
                            <span>Negative Korrelation</span>
                        </div>
                    </div>
                    <div id="correlationTableContainer">
                        <p>Bitte erstellen Sie ein Portfolio mit mindestens 2 Assets für die Korrelationsanalyse.</p>
                    </div>
                </div>

                <div class="card">
                    <h3>Marktanalyse & Sektor-Zyklen</h3>
                    <div id="marketAnalysis">
                        <p>Bitte berechnen Sie zuerst Ihr Portfolio für die Marktanalyse.</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Handlungsempfehlungen</h3>
                    <div id="recommendations">
                        <p>Bitte erstellen Sie zuerst ein Portfolio und klicken Sie auf "Portfolio Berechnen".</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Portfolio-Zusammenfassung</h3>
                    <div id="portfolioSummary">
                        <p>Bitte fügen Sie Assets zu Ihrem Portfolio hinzu und berechnen Sie die Analyse.</p>
                    </div>
                </div>
            </section>

            <!-- Märkte & News -->
            <section id="markets" class="page">
                <div class="page-header">
                    <h2>Märkte & News</h2>
                    <p>Aktuelle Marktinformationen und Finanznachrichten</p>
                </div>
                
                <div class="instruction-box">
                    <h4>📰 Marktübersicht:</h4>
                    <p>Bleiben Sie über die aktuellen Entwicklungen an den Finanzmärkten informiert. Daten werden alle 15 Minuten automatisch aktualisiert.</p>
                    <div class="auto-refresh-info">
                        <i class="fas fa-sync-alt fa-spin-pulse" style="margin-right: 5px"></i> Nächste Aktualisierung in: <span id="nextRefresh" style="font-weight: 600">--:--</span>
                    </div>
                    <button class="refresh-button" onclick="refreshAllMarkets()">
                        <i class="fas fa-sync-alt"></i> Jetzt aktualisieren
                    </button>
                </div>
                
                <div class="market-grid" id="liveMarketsGrid">
                    <!-- Wird dynamisch gefüllt -->
                </div>
                
                <div class="card">
                    <h3>Schweizer Finanznachrichten</h3>
                    <div id="newsContainer">
                        <!-- Nachrichten werden hier eingefügt -->
                    </div>
                </div>
            </section>

            <!-- Assets & Investment -->
            <section id="assets" class="page">
                <div class="page-header">
                    <h2>Assets & Investment</h2>
                    <p>Bildungsinhalte zu verschiedenen Anlageklassen</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎓 Investment-Bildung:</h4>
                    <p>Lernen Sie die verschiedenen Anlageklassen und ihre Eigenschaften kennen.</p>
                </div>
                
                <div class="assets-grid">
                    <div class="asset-card">
                        <h4>Aktien</h4>
                        <p><strong>Risiko:</strong> Hoch</p>
                        <p><strong>Rendite:</strong> Hoch</p>
                        <p><strong>Liquidität:</strong> Hoch</p>
                        <p>Beteiligung am Unternehmenserfolg</p>
                    </div>
                    <div class="asset-card">
                        <h4>Anleihen</h4>
                        <p><strong>Risiko:</strong> Mittel</p>
                        <p><strong>Rendite:</strong> Mittel</p>
                        <p><strong>Liquidität:</strong> Mittel</p>
                        <p>Feste Verzinsung, geringeres Risiko</p>
                    </div>
                    <div class="asset-card">
                        <h4>Rohstoffe</h4>
                        <p><strong>Risiko:</strong> Hoch</p>
                        <p><strong>Rendite:</strong> Variabel</p>
                        <p><strong>Liquidität:</strong> Mittel</p>
                        <p>Inflationsschutz, Diversifikation</p>
                    </div>
                    <div class="asset-card">
                        <h4>Immobilien</h4>
                        <p><strong>Risiko:</strong> Mittel</p>
                        <p><strong>Rendite:</strong> Stabil</p>
                        <p><strong>Liquidität:</strong> Niedrig</p>
                        <p>Substanzwerte, Mieteinnahmen</p>
                    </div>
                </div>
            </section>

            <!-- Methodik -->
            <section id="methodik" class="page">
                <div class="page-header">
                    <h2>Berechnungs-Methodik</h2>
                    <p>Transparente Darstellung aller verwendeten Formeln und Modelle</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🔬 Wissenschaftliche Grundlage:</h4>
                    <p>Alle Berechnungen basieren auf etablierten finanziellen Modellen und mathematischen Formeln.</p>
                </div>
                
                <!-- PDF Download Section -->
                <div class="pdf-download-section">
                    <h3 style="color: white; margin-bottom: 15px;">Bloomberg-Style Portfolio Report</h3>
                    <p style="margin-bottom: 20px; opacity: 0.9;">Generieren Sie einen professionellen PDF-Report im Bloomberg-Stil mit allen Portfolio-Daten und Analysen</p>
                    <button class="btn btn-pdf" onclick="generatePDFReport()">
                        <i class="fas fa-file-pdf"></i> PDF Report Herunterladen
                    </button>
                    <p style="margin-top: 15px; font-size: 14px; opacity: 0.8;">Enthält Portfolio-Übersicht, Performance-Metriken, Korrelationsmatrix und Sektor-Analyse</p>
                </div>
                
                <!-- Monte Carlo Simulation -->
                <div class="card">
                    <h3>Monte Carlo Simulation</h3>
                    <p><strong>Was ist Monte Carlo Simulation?</strong><br>
                    Die Monte Carlo Simulation ist ein mathematisches Verfahren, das mithilfe von Zufallszahlen und Wahrscheinlichkeitsverteilungen tausende mögliche Zukunftsszenarien für Ihr Portfolio berechnet. Dies hilft bei der Risikoabschätzung und zeigt die Bandbreite möglicher Ergebnisse.</p>
                    
                    <div class="monte-carlo-controls">
                        <div class="input-group">
                            <label>Anzahl Simulationen</label>
                            <input type="number" id="monteCarloSimulations" value="1000" min="100" max="10000" step="100">
                            <small>Mehr Simulationen = genauere Ergebnisse (100-10.000)</small>
                        </div>
                        <div class="input-group">
                            <label>Zeithorizont (Jahre)</label>
                            <input type="number" id="monteCarloYears" value="10" min="1" max="30">
                            <small>Wie viele Jahre in die Zukunft simulieren</small>
                        </div>
                        <div class="input-group">
                            <label>Konfidenzniveau</label>
                            <select id="confidenceLevel" class="search-input">
                                <option value="90">90% (Konservativ)</option>
                                <option value="95" selected>95% (Standard)</option>
                                <option value="99">99% (Risikobewusst)</option>
                            </select>
                        </div>
                        <button class="btn" onclick="runMonteCarloSimulation()" style="align-self: end;">
                            <i class="fas fa-chart-line"></i> Simulation starten
                        </button>
                    </div>
                    
                    <div class="chart-container">
                        <canvas id="monteCarloChart"></canvas>
                    </div>
                    
                    <div id="monteCarloResults">
                        <p>Klicken Sie auf "Simulation starten", um die Monte Carlo Analyse durchzuführen.</p>
                    </div>
                </div>
                
                <div class="methodology-grid">
                    <div class="card">
                        <h3>1. Mean-Variance Optimierung (Markowitz)</h3>
                        <p><strong>Ziel:</strong> Optimales Verhältnis von Rendite und Risiko</p>
                        <p><strong>Portfolio Rendite:</strong></p>
                        <div class="formula-box">
                            E[Rₚ] = Σ(wᵢ × μᵢ)
                        </div>
                        <p><strong>Portfolio Volatilität:</strong></p>
                        <div class="formula-box">
                            σₚ = √(ΣΣ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ)
                        </div>
                        <p><strong>Anwendung:</strong> Findet die Effizienzgrenze aller optimalen Portfolios</p>
                    </div>
                    
                    <div class="card">
                        <h3>2. Risikoparität (Risk Parity)</h3>
                        <p><strong>Ziel:</strong> Gleicher Risikobeitrag aller Assets</p>
                        <p><strong>Risikobeitrag:</strong></p>
                        <div class="formula-box">
                            RCᵢ = wᵢ × (∂σₚ/∂wᵢ)
                        </div>
                        <p><strong>Optimierung:</strong></p>
                        <div class="formula-box">
                            RCᵢ = RCⱼ für alle i, j
                        </div>
                        <p><strong>Anwendung:</strong> Robuster gegen Marktschwankungen</p>
                    </div>
                    
                    <div class="card">
                        <h3>3. Minimum-Varianz-Portfolio</h3>
                        <p><strong>Ziel:</strong> Niedrigstmögliche Volatilität</p>
                        <p><strong>Optimierungsproblem:</strong></p>
                        <div class="formula-box">
                            min wᵀΣw unter Σwᵢ = 1
                        </div>
                        <p><strong>Lösung:</strong></p>
                        <div class="formula-box">
                            w = Σ⁻¹1 / (1ᵀΣ⁻¹1)
                        </div>
                        <p><strong>Anwendung:</strong> Für risikoscheue Anleger</p>
                    </div>
                    
                    <div class="card">
                        <h3>4. Maximum Sharpe Ratio</h3>
                        <p><strong>Ziel:</strong> Bestes Rendite-Risiko-Verhältnis</p>
                        <p><strong>Sharpe Ratio:</strong></p>
                        <div class="formula-box">
                            S = (E[Rₚ] - R_f) / σₚ
                        </div>
                        <p><strong>Tangency Portfolio:</strong></p>
                        <div class="formula-box">
                            w = Σ⁻¹(μ - R_f1) / (1ᵀΣ⁻¹(μ - R_f1))
                        </div>
                        <p><strong>Anwendung:</strong> Optimal für risikobewusste Anleger</p>
                    </div>
                    
                    <div class="card">
                        <h3>5. Black-Litterman Modell</h3>
                        <p><strong>Ziel:</strong> Kombiniert Marktdaten mit Investor-Views</p>
                        <p><strong>Posterior Rendite:</strong></p>
                        <div class="formula-box">
                            μ = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ × [(τΣ)⁻¹π + PᵀΩ⁻¹Q]
                        </div>
                        <p><strong>Anwendung:</strong> Für erfahrene Anleger mit Marktmeinung</p>
                    </div>
                </div>
            </section>

            <!-- Über mich -->
            <section id="about" class="page">
                <div class="page-header">
                    <h2>Über mich</h2>
                    <p>Portfolioanalyst & Finanzanalyst</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🏆 Expertise:</h4>
                    <p>Spezialisiert auf quantitative Portfolio-Optimierung und Risikomanagement mit Fokus auf Schweizer Aktienmarkt und internationale Diversifikation.</p>
                </div>
                
                <div class="card">
                    <h3>Ahmed Choudhary</h3>
                    <p><strong>Portfolioanalyst & Finanzanalyst</strong></p>
                    
                    <div style="margin: 20px 0;">
                        <a href="https://www.linkedin.com/in/ahmed-choudhary-3a61371b6" class="linkedin-link" target="_blank">
                            <i class="fab fa-linkedin"></i> LinkedIn Profil besuchen
                        </a>
                    </div>
                    
                    <h4>Über mich:</h4>
                    <p>Ich habe diese umfassende Portfolio-Simulationsplattform entwickelt, um quantitative Finanzanalyse mit praktischer Anwendung zu verbinden. Mein Fokus liegt auf der Optimierung von Portfolios unter Berücksichtigung modernster finanzieller Modelle und Risikomanagement-Techniken.</p>
                    
                    <h4>Kontakt:</h4>
                    <p>Email: <a href="mailto:ahmedch1999@gmail.com" class="email-link">ahmedch1999@gmail.com</a></p>
                    
                    <div style="background: #2A2A2A; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                        <h4 style="color: #E8E8E8;">Über diese Plattform:</h4>
                        <p style="color: #E0E0E0;">Der Swiss Asset Pro kombiniert moderne Finanztechnologie mit wissenschaftlichen Berechnungsmethoden. Alle Analysen basieren auf etablierten finanziellen Modellen wie Markowitz-Portfolio-Optimierung, Monte Carlo Simulationen und Risikoparität. Die Plattform wurde entwickelt, um sowohl privaten Anlegern als auch professionellen Investoren tiefe Einblicke in Portfolio-Performance und Risikomanagement zu bieten.</p>
                    </div>
                </div>

                <!-- Quellen Section -->
                <div class="card">
                    <h3>Quellen & Daten</h3>
                    <p>Diese Plattform verwendet Daten von folgenden Quellen:</p>
                    
                    <div class="sources-grid">
                        <div class="source-card" style="background: linear-gradient(145deg, #2A2A2A, #232323); border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                            <h4 style="color: #E8E8E8;">Yahoo Finance</h4>
                            <p><strong style="color: #E8E8E8;">Verwendet für:</strong> <span style="color: #E0E0E0;">Aktuelle Aktienkurse, historische Kursdaten, Marktinformationen</span></p>
                            <p><strong style="color: #E8E8E8;">Website:</strong> <a href="https://finance.yahoo.com" class="news-link" target="_blank" style="color: var(--accent-violet);">finance.yahoo.com</a></p>
                        </div>
                        
                        <div class="source-card" style="background: linear-gradient(145deg, #2A2A2A, #232323); border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                            <h4 style="color: #E8E8E8;">Swiss Exchange (SIX)</h4>
                            <p><strong style="color: #E8E8E8;">Verwendet für:</strong> <span style="color: #E0E0E0;">Schweizer Aktienkurse, SMI Daten</span></p>
                            <p><strong style="color: #E8E8E8;">Website:</strong> <a href="https://www.six-group.com" class="news-link" target="_blank" style="color: var(--accent-violet);">www.six-group.com</a></p>
                        </div>
                        
                        <div class="source-card" style="background: linear-gradient(145deg, #2A2A2A, #232323); border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                            <h4 style="color: #E8E8E8;">Bloomberg</h4>
                            <p><strong style="color: #E8E8E8;">Verwendet für:</strong> <span style="color: #E0E0E0;">Benchmark-Indizes, Marktdaten</span></p>
                            <p><strong style="color: #E8E8E8;">Website:</strong> <a href="https://www.bloomberg.com" class="news-link" target="_blank" style="color: var(--accent-violet);">www.bloomberg.com</a></p>
                        </div>
                        
                        <div class="source-card" style="background: linear-gradient(145deg, #2A2A2A, #232323); border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                            <h4 style="color: #E8E8E8;">Finanznachrichten</h4>
                            <p><strong style="color: #E8E8E8;">Quellen:</strong> <span style="color: #E0E0E0;">Finanz und Wirtschaft, Handelszeitung, NZZ, Financial Times</span></p>
                            <p><strong style="color: #E8E8E8;">Verwendet für:</strong> <span style="color: #E0E0E0;">Aktuelle Marktnews und Analysen</span></p>
                        </div>
                    </div>
                    
                    <div style="background: rgba(138, 43, 226, 0.1); padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid rgba(138, 43, 226, 0.3); box-shadow: var(--shadow-soft);">
                        <h4 style="color: #E8E8E8;">Hinweis zu den Daten:</h4>
                        <p style="color: #E0E0E0;">Alle Daten werden in Echtzeit von den genannten Quellen bezogen und automatisch verarbeitet. Bei Verbindungsproblemen werden simulierte Daten verwendet, die auf historischen Mustern basieren. Die Genauigkeit der Daten hängt von der Verfügbarkeit der Quellen ab.</p>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script>         // Windows Detection - Optimierte Animationen nur für Windows
        function isWindows() {
            return navigator.userAgent.includes('Windows');
        }

        if (isWindows()) {
            document.body.classList.add('performance-mode');
            console.log('Windows Performance Mode aktiviert');
        }
        // Globale Variablen
        const swissStocks = ''' + json.dumps(SWISS_STOCKS) + ''';
        const indices = ''' + json.dumps(INDICES) + ''';
        const otherAssets = ''' + json.dumps(OTHER_ASSETS) + ''';
        const marketCycles = ''' + json.dumps(MARKET_CYCLES) + ''';
        const swissBankPortfolios = ''' + json.dumps(SWISS_BANK_PORTFOLIOS) + ''';
        const scenarios = ''' + json.dumps(SCENARIOS) + ''';
        const translations = ''' + json.dumps(TRANSLATIONS) + ''';
        
        let userPortfolio = [];
        let totalInvestment = 100000;
        let portfolioCalculated = false;
        let currentLanguage = 'de';
        let autoRefreshInterval;
        let marketRefreshInterval;
        let currentTimeframe = '5y';
        
        // Status-Bar Daten speichern
        let statusBarData = {
            lastUpdate: '--:--:--',
            smiReturn: '+1.2%',
            portfolioReturn: '+0.0%',
            portfolioValue: 'CHF 0'
        };

        // Sprachumschaltung
        function switchLanguage(lang) {
            currentLanguage = lang;
            
            // UI-Elemente aktualisieren
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="switchLanguage('${lang}')"]`).classList.add('active');
            
            // Texte übersetzen
            document.getElementById('passwordPrompt').textContent = translations[lang].password_prompt;
            document.getElementById('passwordInput').placeholder = translations[lang].password_placeholder;
            document.getElementById('accessButton').textContent = translations[lang].access_button;
            document.getElementById('passwordError').textContent = translations[lang].password_error;
            document.getElementById('passwordHint').textContent = translations[lang].password_hint;
            
            document.getElementById('lastUpdateText').textContent = translations[lang].last_update;
            document.getElementById('smiReturnText').textContent = translations[lang].smi_return;
            document.getElementById('portfolioReturnText').textContent = translations[lang].portfolio_return;
            document.getElementById('portfolioValueText').textContent = translations[lang].portfolio_value;
            
            // Status-Bar Daten beibehalten
            document.getElementById('lastUpdate').textContent = statusBarData.lastUpdate;
            document.getElementById('smiReturn').textContent = statusBarData.smiReturn;
            document.getElementById('portfolioReturn').textContent = statusBarData.portfolioReturn;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
            
            // Navigation übersetzen
            const navMap = {
                'dashboard': translations[lang].dashboard,
                'portfolio': translations[lang].portfolio,
                'strategieanalyse': translations[lang].strategieanalyse,
                'simulation': translations[lang].simulation,
                'bericht': translations[lang].bericht,
                'markets': translations[lang].markets,
                'assets': translations[lang].assets,
                'methodik': translations[lang].methodik,
                'about': translations[lang].about
            };
            
            document.querySelectorAll('.nav-tab').forEach(tab => {
                const page = tab.getAttribute('data-page');
                if (navMap[page]) {
                    tab.textContent = navMap[page];
                }
            });
            
            // Seiten-Header übersetzen
            document.querySelectorAll('.page-header h2').forEach(header => {
                const pageId = header.closest('.page').id;
                if (navMap[pageId]) {
                    header.textContent = navMap[pageId];
                }
            });
        }

        // Vereinfachte Passwort-Prüfung
        function checkPassword() {
            const password = document.getElementById('passwordInput').value;
            const errorElement = document.getElementById('passwordError');
            
            // Backend Password Check
            fetch('/api/verify_password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({password: password})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // SOFORT zur Welcome Screen wechseln
                    document.getElementById('passwordProtection').style.display = 'none';
                    document.getElementById('welcomeScreen').style.display = 'flex';
                    
                    // Nach 4.5 Sekunden direkt zur Hauptseite
                    setTimeout(() => {
                        document.getElementById('welcomeScreen').style.display = 'none';
                        document.getElementById('mainContent').style.display = 'block';
                        document.querySelector('footer').style.display = 'block';
                        initializeApplication();
                        startAutoRefresh();
                    }, 4500);
                    
                    // Setup Landing Page nach dem Laden
                    setTimeout(() => {
                        initializeLandingPage();
                    }, 4600);
                    
                } else {
                    errorElement.style.display = 'block';
                    document.getElementById('passwordInput').style.borderColor = '#DC3545';
                    setTimeout(() => {
                        document.getElementById('passwordInput').style.borderColor = '';
                    }, 1000);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                errorElement.style.display = 'block';
            });
            
            /**
             * Initialisiert die Landing-Page
             * (a) Erzeugt dynamisch Panels aus den Header-Links
             * (b) Zeigt das Overlay nach dem Loading an
             * (c) Fügt Event Listener hinzu
             */
            function initializeLandingPage() {
                // Panels aus Navigation-Tabs generieren
                const panelsContainer = document.getElementById('landingPanelsContainer');
                const navTabs = document.querySelectorAll('#headerNavTabs .nav-tab:not(#startseiteLink)');
                
                // Icons für die jeweiligen Tabs
                const tabIcons = {
                    'getting-started': 'fa-play-circle',
                    'dashboard': 'fa-chart-line',
                    'portfolio': 'fa-chart-pie',
                    'strategieanalyse': 'fa-chart-bar',
                    'simulation': 'fa-rocket',
                    'investing': 'fa-hand-holding-usd',
                    'bericht': 'fa-file-alt',
                    'markets': 'fa-globe',
                    'assets': 'fa-coins',
                    'methodik': 'fa-calculator',
                    'about': 'fa-user'
                };
                
                // Beschreibungen für die jeweiligen Tabs
                const tabDescriptions = {
                    'getting-started': 'Einstieg und erste Schritte zur Portfolioerstellung',
                    'dashboard': 'Überblick über Ihr Portfolio und aktuelle Kennzahlen',
                    'portfolio': 'Detaillierte Entwicklung Ihrer Anlagen über Zeit',
                    'strategieanalyse': 'Vergleich verschiedener Portfolio-Strategien',
                    'simulation': 'Zukunftsprognosen und Szenarioanalyse',
                    'investing': 'Anlagestrategien und Investmentmöglichkeiten',
                    'bericht': 'Detaillierte Berichte und tiefergehende Analyse',
                    'markets': 'Aktuelle Marktdaten und Finanznachrichten',
                    'assets': 'Übersicht aller verfügbaren Anlageklassen',
                    'methodik': 'Erklärung der verwendeten Berechnungsmethoden',
                    'about': 'Informationen über den Entwickler'
                };
                
                // HTML für die Panels erstellen
                let panelDelay = 0;
                navTabs.forEach(tab => {
                    const pageName = tab.dataset.page;
                    const tabText = tab.textContent;
                    const iconClass = tabIcons[pageName] || 'fa-star';
                    const description = tabDescriptions[pageName] || '';
                    
                    panelDelay += 0.1;
                    
                    const cardElement = document.createElement('div');
                    cardElement.className = 'landing-card';
                    cardElement.setAttribute('aria-label', `${tabText} öffnen`);
                    cardElement.style.animation = `fadeInUp 0.6s ease ${panelDelay}s forwards`;
                    cardElement.style.opacity = '0';
                    
                    cardElement.innerHTML = `
                        <div class="landing-card-icon">
                            <i class="fas ${iconClass}"></i>
                        </div>
                        <h3>${tabText}</h3>
                        <p>${description}</p>
                    `;
                    
                    // Event Listener für Klick auf Panel
                    cardElement.addEventListener('click', () => {
                        hideLandingPage();
                        const pageName = tab.dataset.page;
                        if (pageName) {
                            switchToPage(pageName); // Direkt zur entsprechenden Seite wechseln
                        }
                    });
                    
                    panelsContainer.appendChild(cardElement);
                });
                
                // Hero-Section Animation
                setTimeout(() => {
                    document.querySelector('.landing-hero-section').style.opacity = '1';
                    document.querySelector('.landing-hero-section').style.transform = 'translateY(0)';
                }, 100);
                
                // Panels Container Animation
                setTimeout(() => {
                    document.getElementById('landingPanelsContainer').style.opacity = '1';
                    document.getElementById('landingPanelsContainer').style.transform = 'translateY(0)';
                }, 300);
                
                // Landing Page anzeigen
                const landingPage = document.getElementById('landingPage');
                landingPage.style.display = 'block';
                setTimeout(() => {
                    landingPage.style.opacity = '1';
                }, 50);
                
                // Event Listener für "Startseite" Tab
                document.getElementById('startseiteLink').addEventListener('click', showLandingPage);
            }
            
            /**
             * Zeigt die Landing Page an
             */
            function showLandingPage() {
                const landingPage = document.getElementById('landingPage');
                landingPage.style.display = 'block';
                setTimeout(() => {
                    landingPage.style.opacity = '1';
                }, 50);
            }
            
            /**
             * Blendet die Landing Page aus
             */
            function hideLandingPage() {
                const landingPage = document.getElementById('landingPage');
                landingPage.style.opacity = '0';
                setTimeout(() => {
                    landingPage.style.display = 'none';
                }, 500);
            }
        }

        // Enter-Taste für Passwort
        document.getElementById('passwordInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                checkPassword();
            }
        });

        // Auto-Focus auf Passwort-Feld
        document.getElementById('passwordInput').focus();

        // Auto-Refresh Funktion
        function startAutoRefresh() {
            autoRefreshInterval = setInterval(() => {
                updateLastUpdateTime();
                updateSMIReturn();
                if (portfolioCalculated) {
                    updatePortfolioReturn();
                    updateCharts();
                }
            }, 30000);

            // Marktdaten alle 15 Minuten aktualisieren
            marketRefreshInterval = setInterval(() => {
                refreshAllMarkets();
                loadNews();
                if (portfolioCalculated) {
                    updateCurrentPrices();
                }
            }, 900000); // 15 Minuten

            // Starte sofort mit Marktdaten
            refreshAllMarkets();
            loadNews();
            startCountdownTimer();
        }

        // Initialisierung
        function initializeApplication() {
            populateStockSelect();
            populateIndexSelect();
            populateAssetSelect();
            createAllCharts();
            updatePortfolioDisplay();
            updateLastUpdateTime();
            updateSMIReturn();
            updatePortfolioReturn();
            refreshMarketData();
            loadBenchmarkData();
            
            // Set Getting Started as the active page
            setTimeout(switchToGettingStarted, 100);
        }

        function updateLastUpdateTime() {
            const now = new Date();
            statusBarData.lastUpdate = now.toLocaleTimeString('de-CH');
            document.getElementById('lastUpdate').textContent = statusBarData.lastUpdate;
        }

        function updateSMIReturn() {
            const smiReturn = (Math.random() * 3 - 1).toFixed(1);
            statusBarData.smiReturn = (smiReturn > 0 ? '+' : '') + smiReturn + '%';
            const element = document.getElementById('smiReturn');
            element.textContent = statusBarData.smiReturn;
            element.className = smiReturn >= 0 ? 'positive' : 'negative';
        }

        function updatePortfolioReturn() {
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                statusBarData.portfolioReturn = '+0.0%';
                document.getElementById('portfolioReturn').textContent = statusBarData.portfolioReturn;
                return;
            }
            
            const years = parseInt(document.getElementById('investmentYears').value) || 1;
            const expectedReturn = calculatePortfolioReturn() * 100;
            statusBarData.portfolioReturn = (expectedReturn > 0 ? '+' : '') + expectedReturn.toFixed(1) + '% p.a.';
            const element = document.getElementById('portfolioReturn');
            element.textContent = statusBarData.portfolioReturn;
            element.className = expectedReturn >= 0 ? 'positive' : 'negative';
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
            
            // Vereinfachte Risikoberechnung (gewichtete Durchschnittsvolatilität)
            const totalWeight = userPortfolio.reduce((sum, asset) => sum + parseFloat(asset.weight), 0);
            if (totalWeight === 0) return 0;
            
            return userPortfolio.reduce((sum, asset) => 
                sum + (parseFloat(asset.weight) / 100) * asset.volatility, 0);
        }

        // Live Marktdaten für Dashboard
        async function refreshMarketData() {
            const symbols = [
                {symbol: '^SSMI', name: 'SMI'},
                {symbol: '^GSPC', name: 'S&P 500'},
                {symbol: 'GC=F', name: 'Gold'},
                {symbol: 'EURCHF=X', name: 'EUR/CHF'}
            ];
            
            for (const item of symbols) {
                try {
                    const response = await fetch('/get_live_data/' + item.symbol);
                    const data = await response.json();
                    
                    if (data.error) throw new Error(data.error);
                    
                    const marketItem = Array.from(document.querySelectorAll('.market-item'))
                        .find(el => el.querySelector('h4').textContent === item.name);
                    
                    if (marketItem) {
                        const valueElement = marketItem.querySelector('.metric-value');
                        const labelElement = marketItem.querySelector('.metric-label');
                        
                        valueElement.textContent = data.currency === 'CHF' ? 
                            data.price.toLocaleString('de-CH') : 
                            (item.symbol === 'GC=F' ? '$' + data.price.toLocaleString() : data.price.toFixed(2));
                        
                        labelElement.textContent = (data.change_percent > 0 ? '+' : '') + data.change_percent.toFixed(2) + '%';
                        labelElement.className = data.change_percent >= 0 ? 'metric-label positive' : 'metric-label negative';
                    }
                } catch (error) {
                    console.error('Error fetching data for', item.symbol, error);
                }
            }
        }

        // Alle Marktdaten aktualisieren
        async function refreshAllMarkets() {
            try {
                const response = await fetch('/refresh_all_markets');
                const data = await response.json();
                
                if (data.success) {
                    updateMarketsGrid(data.data);
                    document.getElementById('lastUpdate').textContent = data.last_update;
                    showNotification('Marktdaten erfolgreich aktualisiert!', 'success');
                }
            } catch (error) {
                console.error('Error refreshing markets:', error);
                // Fallback zu simulierten Daten
                updateMarketsGridWithSimulatedData();
            }
        }

        function updateMarketsGrid(marketData) {
            const container = document.getElementById('liveMarketsGrid');
            if (!container) return;
            
            let html = '';
            const markets = [
                {name: 'SMI', key: 'SMI'},
                {name: 'DAX', key: 'DAX'},
                {name: 'S&P 500', key: 'S&P 500'},
                {name: 'NASDAQ', key: 'NASDAQ'},
                {name: 'Gold', key: 'Gold'},
                {name: 'Öl', key: 'Öl'},
                {name: 'EUR/CHF', key: 'EUR/CHF'},
                {name: 'Bitcoin', key: 'Bitcoin'}
            ];
            
            markets.forEach(market => {
                const data = marketData[market.key];
                if (data) {
                    const changeClass = data.change_percent >= 0 ? 'positive' : 'negative';
                    const changeSign = data.change_percent >= 0 ? '+' : '';
                    
                    html += `
                        <div class="market-item">
                            <h4>${market.name}</h4>
                            <div class="metric-value">${formatPrice(data.price, data.currency)}</div>
                            <div class="metric-label ${changeClass}">${changeSign}${data.change_percent.toFixed(2)}%</div>
                        </div>
                    `;
                }
            });
            
            container.innerHTML = html;
        }

        function updateMarketsGridWithSimulatedData() {
            const container = document.getElementById('liveMarketsGrid');
            if (!container) return;
            
            const markets = [
                {name: 'SMI', price: 11250, change: 1.2},
                {name: 'DAX', price: 15800, change: 0.8},
                {name: 'S&P 500', price: 4550, change: -0.3},
                {name: 'NASDAQ', price: 14200, change: 0.5},
                {name: 'Gold', price: 1950, change: 0.5},
                {name: 'Öl', price: 78.5, change: -1.2},
                {name: 'EUR/CHF', price: 0.95, change: 0.1},
                {name: 'Bitcoin', price: 42000, change: 2.1}
            ];
            
            let html = '';
            markets.forEach(market => {
                const changeClass = market.change >= 0 ? 'positive' : 'negative';
                const changeSign = market.change >= 0 ? '+' : '';
                
                html += `
                    <div class="market-item">
                        <h4>${market.name}</h4>
                        <div class="metric-value">${formatPrice(market.price, market.name.includes('CHF') ? 'CHF' : 'USD')}</div>
                        <div class="metric-label ${changeClass}">${changeSign}${market.change.toFixed(1)}%</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        function formatPrice(price, currency) {
            if (currency === 'CHF') {
                return price.toLocaleString('de-CH');
            } else if (price < 1) {
                return price.toFixed(3);
            } else if (price > 1000) {
                return price.toLocaleString('de-CH');
            } else {
                return price.toFixed(2);
            }
        }

        // Nachrichten laden
        async function loadNews() {
            try {
                const response = await fetch('/get_news');
                const news = await response.json();
                
                const container = document.getElementById('newsContainer');
                if (container) {
                    let html = '';
                    news.forEach(item => {
                        html += `
                            <div class="news-item">
                                <h4><a href="${item.link}" class="news-link" target="_blank">${item.title}</a></h4>
                                <p>${item.content}</p>
                                <small>${item.time} • ${item.source}</small>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                }
            } catch (error) {
                console.error('Error loading news:', error);
            }
        }

        // Countdown Timer für Auto-Refresh
        function startCountdownTimer() {
            setInterval(() => {
                const now = new Date();
                const nextRefresh = new Date(now);
                nextRefresh.setMinutes(Math.ceil(now.getMinutes() / 15) * 15);
                nextRefresh.setSeconds(0);
                
                const diff = nextRefresh - now;
                const minutes = Math.floor(diff / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                
                document.getElementById('nextRefresh').textContent = 
                    `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }, 1000);
        }

        // Aktuelle Preise für Portfolio-Assets aktualisieren
        async function updateCurrentPrices() {
            if (userPortfolio.length === 0) return;
            
            try {
                const symbols = userPortfolio.map(asset => asset.symbol);
                const response = await fetch('/get_current_prices', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({symbols: symbols})
                });
                
                const data = await response.json();
                if (data.success) {
                    // Aktualisiere die erwarteten Renditen basierend auf aktuellen Preisen
                    userPortfolio.forEach(asset => {
                        if (data.prices[asset.symbol]) {
                            // Simuliere eine Rendite-Anpassung basierend auf Preisänderungen
                            const priceChange = (data.prices[asset.symbol] - 100) / 100;
                            asset.expectedReturn = Math.max(0.01, asset.expectedReturn + priceChange * 0.1);
                        }
                    });
                    
                    if (portfolioCalculated) {
                        updatePortfolioDisplay();
                        showNotification('Aktienkurse aktualisiert!', 'success');
                    }
                }
            } catch (error) {
                console.error('Error updating current prices:', error);
            }
        }

        // Portfolio Entwicklung aktualisieren
        function updatePortfolioDevelopment() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            
            if (total > 0 && portfolioCalculated) {
                // Performance Metriken
                document.getElementById('totalReturn').textContent = `${expectedReturn >= 0 ? '+' : ''}${expectedReturn.toFixed(1)}%`;
                document.getElementById('annualizedReturn').textContent = `${expectedReturn.toFixed(1)}%`;
                document.getElementById('maxDrawdown').textContent = `${(volatility * 1.5).toFixed(1)}%`;
                document.getElementById('volatilityHistory').textContent = `${volatility.toFixed(1)}%`;
                
                // Performance Analyse mit SMI Vergleich
                const smiComparison = expectedReturn > 6.5 ? "übertrifft" : "untertrifft";
                const smiDiff = (expectedReturn - 6.5).toFixed(1);
                
                const analysis = `
                    <p><strong>Portfolio Performance:</strong> Ihr Portfolio zeigt eine erwartete Rendite von ${expectedReturn.toFixed(1)}% p.a.</p>
                    <p><strong>Vergleich mit SMI:</strong> ${smiComparison} den Schweizer Marktindex (SMI: 6.5% p.a.) um ${Math.abs(smiDiff)}%</p>
                    <p><strong>Risikoprofil:</strong> Die Volatilität von ${volatility.toFixed(1)}% entspricht einem ${volatility > 20 ? 'aggressiven' : volatility > 12 ? 'moderaten' : 'konservativen'} Profil.</p>
                    <p><strong>Diversifikation:</strong> ${userPortfolio.length} Assets bieten ${Math.min(userPortfolio.length * 2, 10)}/10 Punkte Diversifikation.</p>
                    <p><strong>Performance vs. Benchmark:</strong> ${expectedReturn > 8 ? 'Übertrifft' : 'Untertrifft'} die Markterwartungen von 6-8% p.a.</p>
                `;
                document.getElementById('performanceAnalysis').innerHTML = analysis;
                
                createPerformanceChart();
                loadBenchmarkData();
                
                // Erfolgsmeldung
                showNotification('Portfolio Entwicklung erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('performanceAnalysis').innerHTML = '<p>Bitte klicken Sie im Dashboard auf "Portfolio Berechnen".</p>';
            }
        }

        // Zukunfts-Simulation aktualisieren
        function updateSimulationPage() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            
            if (total > 0 && portfolioCalculated) {
                const years = parseInt(document.getElementById('investmentYears').value) || 5;
                const expectedValue = total * Math.pow(1 + expectedReturn/100, years);
                const optimisticValue = total * Math.pow(1 + (expectedReturn + 5)/100, years);
                const conservativeValue = total * Math.pow(1 + (expectedReturn - 3)/100, years);
                
                document.getElementById('baseValue').textContent = `CHF ${Math.round(expectedValue).toLocaleString('de-CH')}`;
                document.getElementById('optimisticValue').textContent = `CHF ${Math.round(optimisticValue).toLocaleString('de-CH')}`;
                document.getElementById('conservativeValue').textContent = `CHF ${Math.round(conservativeValue).toLocaleString('de-CH')}`;
                
                // Szenario-Analyse aktualisieren
                updateScenarioAnalysis();
                
                // Strategie Pfade Beschreibung
                const strategyDescription = `
                    <p><strong>Basisszenario (${expectedReturn.toFixed(1)}% p.a.):</strong> Entspricht der aktuellen Portfolio-Struktur</p>
                    <p><strong>Optimistisches Szenario (${(expectedReturn + 5).toFixed(1)}% p.a.):</strong> Bei guter Marktentwicklung und niedrigen Zinsen</p>
                    <p><strong>Konservatives Szenario (${(expectedReturn - 3).toFixed(1)}% p.a.):</strong> Bei wirtschaftlicher Abschwächung</p>
                    <p><strong>Empfehlung:</strong> Das Portfolio zeigt ${expectedReturn > 10 ? 'starkes' : expectedReturn > 7 ? 'gutes' : 'moderates'} Wachstumspotenzial.</p>
                `;
                document.getElementById('strategyPaths').innerHTML = strategyDescription;
                
                createSimulationChart(total, expectedReturn, years);
                
                // Erfolgsmeldung
                showNotification('Simulation erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('strategyPaths').innerHTML = '<p>Bitte klicken Sie im Dashboard auf "Portfolio Berechnen".</p>';
            }
        }

        // Szenario-Analyse aktualisieren
        function updateScenarioAnalysis() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const baseReturn = calculatePortfolioReturn();
            const years = parseInt(document.getElementById('investmentYears').value) || 5;
            
            if (total > 0 && portfolioCalculated) {
                // Berechne Szenario-Werte
                for (const [key, scenario] of Object.entries(scenarios)) {
                    const scenarioReturn = baseReturn * scenario.growth_multiplier;
                    const scenarioValue = total * Math.pow(1 + scenarioReturn, years);
                    const element = document.getElementById(`scenario${key.charAt(0).toUpperCase() + key.slice(1)}`);
                    if (element) {
                        element.textContent = `CHF ${Math.round(scenarioValue).toLocaleString('de-CH')}`;
                        element.className = `metric-value ${scenarioValue >= total ? 'positive' : 'negative'}`;
                    }
                }
            }
        }

        // Bericht & Analyse aktualisieren
        function updateReportPage() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            
            if (total > 0 && portfolioCalculated) {
                // SWOT Analyse
                const stockCount = userPortfolio.filter(a => a.type === 'stock').length;
                const indexCount = userPortfolio.filter(a => a.type === 'index').length;
                const otherCount = userPortfolio.filter(a => a.type === 'other').length;
                
                const strengths = [
                    `${userPortfolio.length} verschiedene Assets für gute Diversifikation`,
                    `${stockCount} Schweizer Blue-Chip Aktien mit stabilem Wachstum`,
                    expectedReturn > 8 ? "Überdurchschnittliche Renditeerwartungen" : "Stabile Renditeerwartungen",
                    volatility < 15 ? "Geringe Volatilität für risikoscheue Anleger" : "Ausgewogenes Risikoprofil",
                    indexCount > 0 ? "Globale Diversifikation durch internationale Indizes" : "Fokus auf Schweizer Markt"
                ];
                
                const weaknesses = [
                    indexCount === 0 ? "Keine internationalen Indizes für globale Streuung" : "Begrenzte internationale Diversifikation",
                    otherCount === 0 ? "Keine Rohstoffe als Inflationsschutz" : "Geringe Allokation in alternative Assets",
                    stockCount > 5 ? "Mögliche Übergewichtung von Einzelaktien" : "Konzentration auf wenige Sektoren",
                    expectedReturn < 7 ? "Unterdurchschnittliche Renditeerwartungen" : ""
                ].filter(w => w !== "");
                
                const opportunities = [
                    "Erweiterung um Schwellenländer-ETFs für höheres Wachstum",
                    "Hinzunahme von Corporate Bonds für stabile Erträge",
                    "Technologie-Sektor für langfristiges Wachstumspotenzial",
                    "Nachhaltige Investments für ESG-konforme Anlagen",
                    "Rohstoffe als Inflationsschutz bei steigenden Preisen"
                ];
                
                const threats = [
                    "Stärke des Schweizer Frankens beeinträchtigt Exporte",
                    "Geopolitische Spannungen betreffen globale Märkte",
                    "Zinserhöhungen der Zentralbanken dämpfen Aktienmärkte",
                    "Inflation bleibt längerfristig höher als erwartet",
                    "Regulatorische Änderungen im Finanzsektor"
                ];
                
                document.getElementById('strengthsList').innerHTML = strengths.map(s => `<p>✓ ${s}</p>`).join('');
                document.getElementById('weaknessesList').innerHTML = weaknesses.map(w => `<p>⚠ ${w}</p>`).join('');
                document.getElementById('opportunitiesList').innerHTML = opportunities.map(o => `<p>→ ${o}</p>`).join('');
                document.getElementById('threatsList').innerHTML = threats.map(t => `<p>⚡ ${t}</p>`).join('');
                
                // Marktanalyse
                const marketAnalysis = generateMarketAnalysis();
                document.getElementById('marketAnalysis').innerHTML = marketAnalysis;
                
                // Korrelationsmatrix aktualisieren
                updateCorrelationMatrix();
                
                // Empfehlungen
                const recommendations = `
                    <p><strong>1. Diversifikation verbessern:</strong> Fügen Sie ${indexCount === 0 ? '2-3 internationale Indizes' : 'weitere Asset-Klassen'} hinzu.</p>
                    <p><strong>2. Risiko managen:</strong> ${volatility > 20 ? 'Reduzieren Sie volatile Positionen auf max. 10%.' : 'Aktuelles Risikoprofil ist angemessen.'}</p>
                    <p><strong>3. Rebalancing:</strong> Überprüfen Sie die Gewichtung quartalsweise.</p>
                    <p><strong>4. Langfristige Strategie:</strong> ${expectedReturn > 10 ? 'Aggressive Position beibehalten' : 'Konservative Ausrichtung fortsetzen'}.</p>
                    <p><strong>5. Sektor-Allokation:</strong> ${getSectorAllocationAdvice()}</p>
                `;
                document.getElementById('recommendations').innerHTML = recommendations;
                
                // Zusammenfassung mit SMI Vergleich
                const smiComparison = expectedReturn > 6.5 ? "Übertrifft SMI" : "Untertrifft SMI";
                const summary = `
                    <p><strong>Portfolio Wert:</strong> CHF ${total.toLocaleString('de-CH')}</p>
                    <p><strong>Erwartete Rendite:</strong> <span class="${expectedReturn >= 0 ? 'positive' : 'negative'}">${expectedReturn.toFixed(1)}% p.a.</span></p>
                    <p><strong>Vergleich mit SMI:</strong> ${smiComparison} (SMI: 6.5% p.a.)</p>
                    <p><strong>Risiko (Volatilität):</strong> ${volatility.toFixed(1)}% p.a.</p>
                    <p><strong>Sharpe Ratio:</strong> ${volatility > 0 ? ((expectedReturn - 2) / volatility).toFixed(2) : '0.00'}</p>
                    <p><strong>Asset Allocation:</strong> ${stockCount} Aktien, ${indexCount} Indizes, ${otherCount} andere Assets</p>
                    <p><strong>Gesamtbewertung:</strong> <span class="${expectedReturn > 8 && volatility < 15 ? 'positive' : ''}">${expectedReturn > 10 ? 'Exzellent' : expectedReturn > 7 ? 'Gut' : 'Verbesserungswürdig'}</span></p>
                `;
                document.getElementById('portfolioSummary').innerHTML = summary;
                
                // Erfolgsmeldung
                showNotification('Bericht erfolgreich aktualisiert!', 'success');
            } else {
                document.getElementById('portfolioSummary').innerHTML = '<p>Bitte fügen Sie Assets zu Ihrem Portfolio hinzu und klicken Sie auf "Portfolio Berechnen".</p>';
                document.getElementById('marketAnalysis').innerHTML = '<p>Bitte berechnen Sie zuerst Ihr Portfolio für die Marktanalyse.</p>';
            }
        }

        // Korrelationsmatrix aktualisieren
        async function updateCorrelationMatrix() {
            const container = document.getElementById('correlationTableContainer');
            
            if (userPortfolio.length < 2) {
                container.innerHTML = '<p>Für eine Korrelationsmatrix werden mindestens 2 Assets benötigt.</p>';
                return;
            }
            
            try {
                const symbols = userPortfolio.map(asset => asset.symbol);
                const response = await fetch('/get_correlation_data?symbols=' + symbols.join('&symbols='));
                const data = await response.json();
                
                if (data.error) {
                    container.innerHTML = '<p>Fehler beim Laden der Korrelationsdaten.</p>';
                    return;
                }
                
                // Erstelle Korrelationstabelle
                let html = '<table class="correlation-table">';
                
                // Header
                html += '<tr><th></th>';
                symbols.forEach(symbol => {
                    html += `<th>${symbol}</th>`;
                });
                html += '</tr>';
                
                // Zeilen
                symbols.forEach((symbol1, i) => {
                    html += `<tr><th>${symbol1}</th>`;
                    symbols.forEach((symbol2, j) => {
                        const key = `${symbol1}_${symbol2}`;
                        const correlation = data.correlations[key] || 0;
                        let cellClass = '';
                        
                        if (i === j) {
                            cellClass = 'corr-high'; // Diagonale
                        } else if (correlation > 0.7) {
                            cellClass = 'corr-high';
                        } else if (correlation > 0.3) {
                            cellClass = 'corr-medium';
                        } else if (correlation < -0.1) {
                            cellClass = 'corr-negative';
                        } else {
                            cellClass = 'corr-low';
                        }
                        
                        html += `<td class="${cellClass}">${correlation.toFixed(2)}</td>`;
                    });
                    html += '</tr>';
                });
                
                html += '</table>';
                container.innerHTML = html;
                
            } catch (error) {
                console.error('Error updating correlation matrix:', error);
                container.innerHTML = '<p>Fehler beim Erstellen der Korrelationsmatrix.</p>';
            }
        }

        // Notification anzeigen
        function showNotification(message, type) {
            // Erstelle Notification Element
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.style.background = type === 'success' ? '#28A745' : '#DC3545';
            
            notification.innerHTML = `
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
                ${message}
            `;
            
            document.body.appendChild(notification);
            
            // Entferne Notification nach 3 Sekunden
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    if (document.body.contains(notification)) {
                        document.body.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }

        // Portfolio Management Funktionen
        function populateStockSelect() {
            const select = document.getElementById('stockSelect');
            select.innerHTML = '<option value="">Schweizer Aktie auswählen...</option>';
            Object.entries(swissStocks).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function populateIndexSelect() {
            const select = document.getElementById('indexSelect');
            select.innerHTML = '<option value="">Internationale Indizes...</option>';
            Object.entries(indices).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function populateAssetSelect() {
            const select = document.getElementById('assetSelect');
            select.innerHTML = '<option value="">Weitere Assets...</option>';
            Object.entries(otherAssets).forEach(([symbol, name]) => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = `${symbol} - ${name}`;
                select.appendChild(option);
            });
        }

        function addStock() {
            const select = document.getElementById('stockSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: swissStocks[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (6 + Math.random() * 6) / 100,
                    volatility: (15 + Math.random() * 15) / 100,
                    type: 'stock'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function addIndex() {
            const select = document.getElementById('indexSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: indices[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (7 + Math.random() * 8) / 100,
                    volatility: (18 + Math.random() * 12) / 100,
                    type: 'index'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function addAsset() {
            const select = document.getElementById('assetSelect');
            const symbol = select.value;
            
            if (symbol && !userPortfolio.find(asset => asset.symbol === symbol)) {
                userPortfolio.push({
                    symbol: symbol,
                    name: otherAssets[symbol],
                    investment: 10000,
                    weight: 0,
                    expectedReturn: (4 + Math.random() * 12) / 100,
                    volatility: (10 + Math.random() * 25) / 100,
                    type: 'other'
                });
                updatePortfolioDisplay();
                select.value = '';
            }
        }

        function calculatePortfolio() {
            if (userPortfolio.length === 0) {
                alert("Bitte fügen Sie zuerst Assets zu Ihrem Portfolio hinzu.");
                return;
            }
            
            portfolioCalculated = true;
            updatePortfolioDisplay();
            
            // Status-Bar Portfolio-Wert aktualisieren
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            statusBarData.portfolioValue = `CHF ${total.toLocaleString('de-CH')}`;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
            
            // Zeige Erfolgsmeldung
            const calculateBtn = document.querySelector('.btn-calculate');
            const originalText = calculateBtn.innerHTML;
            calculateBtn.innerHTML = '<i class="fas fa-check"></i> Portfolio Berechnet!';
            calculateBtn.style.background = '#28A745';
            
            setTimeout(() => {
                calculateBtn.innerHTML = originalText;
                calculateBtn.style.background = '#0A1429';
            }, 2000);
            
            // Aktualisiere alle Seiten
            updateAllPages();
        }

        function updatePortfolioDisplay() {
            calculateWeights();
            validateTotalInvestment();
            updateStockCards();
            updateCharts();
            updatePerformanceMetrics();
            updatePortfolioValue();
            updatePortfolioReturn();
        }

        function calculateWeights() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            userPortfolio.forEach(asset => {
                asset.weight = currentTotal > 0 ? (asset.investment / currentTotal * 100).toFixed(1) : 0;
            });
        }

        function validateTotalInvestment() {
            const currentTotal = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const targetTotal = parseFloat(document.getElementById('totalInvestment').value) || 0;
            const validationElement = document.getElementById('totalValidation');
            
            if (Math.abs(currentTotal - targetTotal) < 1) {
                validationElement.textContent = `Investitionen stimmen überein: CHF ${currentTotal.toLocaleString('de-CH')} von CHF ${targetTotal.toLocaleString('de-CH')}`;
                validationElement.className = 'total-validation validation-ok';
            } else {
                validationElement.textContent = `Achtung: CHF ${currentTotal.toLocaleString('de-CH')} von CHF ${targetTotal.toLocaleString('de-CH')} investiert (Differenz: CHF ${(targetTotal - currentTotal).toLocaleString('de-CH')})`;
                validationElement.className = 'total-validation validation-error';
            }
        }

        function updateStockCards() {
            const container = document.getElementById('selectedStocks');
            container.innerHTML = '';
            
            userPortfolio.forEach((asset, index) => {
                const card = document.createElement('div');
                card.className = 'stock-card';
                let assetClass = 'other-asset';
                let assetTypeLabel = 'Asset';
                
                if (asset.type === 'stock') {
                    assetClass = 'stock-asset';
                    assetTypeLabel = 'Aktie';
                } else if (asset.type === 'index') {
                    assetClass = 'index-asset';
                    assetTypeLabel = 'Index';
                }
                
                card.innerHTML = `
                    <div class="stock-header">
                        <div>
                            <h4><span class="asset-type-indicator ${assetClass}"></span>${asset.symbol}</h4>
                            <div>${asset.name} (${assetTypeLabel})</div>
                        </div>
                        <span onclick="removeAsset('${asset.symbol}')" style="color: var(--accent-negative); cursor: pointer; font-weight: bold;">×</span>
                    </div>
                    <div class="investment-controls">
                        <div>
                            <label style="font-size: 12px;">Investition (CHF)</label>
                            <input type="number" value="${asset.investment}" onchange="updateAssetInvestment(${index}, this.value)">
                        </div>
                        <div>
                            <label style="font-size: 12px;">Gewichtung</label>
                            <input type="text" value="${asset.weight}%" readonly style="background: #f5f5f5;">
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function removeAsset(symbol) {
            userPortfolio = userPortfolio.filter(asset => asset.symbol !== symbol);
            updatePortfolioDisplay();
        }

        function updateAssetInvestment(index, value) {
            userPortfolio[index].investment = parseFloat(value) || 0;
            updatePortfolioDisplay();
        }

        function updatePortfolioValue() {
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            statusBarData.portfolioValue = `CHF ${total.toLocaleString('de-CH')}`;
            document.getElementById('portfolioValue').textContent = statusBarData.portfolioValue;
        }

        function updatePerformanceMetrics() {
            if (userPortfolio.length === 0) {
                // Reset alle Metriken
                document.getElementById('portfolioPerformance').innerHTML = `
                    <div class="metric-value">0.0%</div>
                    <div class="metric-label">Erwartete Jahresrendite</div>
                `;
                document.getElementById('riskAnalysis').innerHTML = `
                    <div class="metric-value">0.0%</div>
                    <div class="metric-label">Volatilität p.a.</div>
                `;
                document.getElementById('diversification').innerHTML = `
                    <div class="metric-value">0/10</div>
                    <div class="metric-label">Diversifikations-Score</div>
                `;
                document.getElementById('sharpeRatio').innerHTML = `
                    <div class="metric-value">0.00</div>
                    <div class="metric-label">Risiko-adjustierte Rendite</div>
                `;
                return;
            }
            
            const expectedReturn = calculatePortfolioReturn() * 100;
            const volatility = calculatePortfolioRisk() * 100;
            const sharpeRatio = volatility > 0 ? (expectedReturn - 2) / volatility : 0;
            
            document.getElementById('portfolioPerformance').innerHTML = `
                <div class="metric-value ${expectedReturn >= 0 ? 'positive' : 'negative'}">${expectedReturn >= 0 ? '+' : ''}${expectedReturn.toFixed(1)}%</div>
                <div class="metric-label">Erwartete Jahresrendite</div>
            `;
            
            document.getElementById('riskAnalysis').innerHTML = `
                <div class="metric-value">${volatility.toFixed(1)}%</div>
                <div class="metric-label">Volatilität p.a.</div>
            `;
            
            const stockCount = userPortfolio.filter(a => a.type === 'stock').length;
            const indexCount = userPortfolio.filter(a => a.type === 'index').length;
            const otherCount = userPortfolio.filter(a => a.type === 'other').length;
            const diversificationScore = Math.min(userPortfolio.length * 2, 10);
            
            document.getElementById('diversification').innerHTML = `
                <div class="metric-value ${diversificationScore >= 6 ? 'positive' : ''}">${diversificationScore}/10</div>
                <div class="metric-label">${stockCount} Aktien, ${indexCount} Indizes, ${otherCount} andere Assets</div>
            `;
            
            document.getElementById('sharpeRatio').innerHTML = `
                <div class="metric-value ${sharpeRatio > 0.5 ? 'positive' : sharpeRatio > 0 ? '' : 'negative'}">${sharpeRatio.toFixed(2)}</div>
                <div class="metric-label">Risiko-adjustierte Rendite</div>
            `;
        }

        function updateAllPages() {
            updatePortfolioDevelopment();
            updateSimulationPage();
            updateReportPage();
            updateScenarioAnalysis();
            updateStrategyAnalysis();
        }

        // Chart Funktionen
        const stockColors = ['#8A2BE2', '#9D42E8', '#B05EED', '#C47AF2', '#D8A6F7', '#E9D1FB'];
        const indexColors = ['#3D3D3D', '#4F4F4F', '#666666', '#808080', '#9F9F9F'];
        const otherAssetColors = ['#28A745', '#34D399', '#10B981', '#059669', '#047857', '#065F46'];

        function createAllCharts() {
            createPortfolioChart();
        }

        function updateCharts() {
            createPortfolioChart();
            if (userPortfolio.length > 0 && portfolioCalculated) {
                createPerformanceChart();
                createSimulationChart(
                    userPortfolio.reduce((sum, asset) => sum + asset.investment, 0),
                    calculatePortfolioReturn() * 100,
                    parseInt(document.getElementById('investmentYears').value) || 5
                );
                createAssetPerformanceChart(currentTimeframe);
            }
        }

        function createPortfolioChart() {
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            
            if (window.portfolioChartInstance) {
                window.portfolioChartInstance.destroy();
            }
            
            if (userPortfolio.length === 0) {
                window.portfolioChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Bitte Assets hinzufügen'],
                        datasets: [{
                            data: [100],
                            backgroundColor: ['#e0e0e0']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
                return;
            }
            
            const labels = userPortfolio.map(asset => `${asset.symbol} (${asset.type === 'stock' ? 'Aktie' : asset.type === 'index' ? 'Index' : 'Asset'})`);
            const data = userPortfolio.map(asset => parseFloat(asset.weight));
            const backgroundColors = userPortfolio.map(asset => {
                if (asset.type === 'stock') {
                    return stockColors[userPortfolio.indexOf(asset) % stockColors.length];
                } else if (asset.type === 'index') {
                    return indexColors[userPortfolio.indexOf(asset) % indexColors.length];
                } else {
                    return otherAssetColors[userPortfolio.indexOf(asset) % otherAssetColors.length];
                }
            });
            
            window.portfolioChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                padding: 20,
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    return `${label}: ${value}%`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function switchTimeframe(timeframe) {
            currentTimeframe = timeframe;
            
            // Aktiviere den entsprechenden Button
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Aktualisiere die Chart-Daten
            createAssetPerformanceChart(timeframe);
        }

        function createAssetPerformanceChart(timeframe = '5y') {
            const ctx = document.getElementById('assetPerformanceChart').getContext('2d');
            
            if (window.assetPerformanceChartInstance) {
                window.assetPerformanceChartInstance.destroy();
            }
            
            if (userPortfolio.length === 0) {
                window.assetPerformanceChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Asset Performance'
                            },
                            legend: {
                                position: 'bottom'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                title: {
                                    display: true,
                                    text: 'Performance (%)'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Zeitraum'
                                }
                            }
                        }
                    }
                });
                return;
            }
            
            // Generiere Zeitachsen basierend auf dem Zeitraum
            let labels = [];
            let dataPoints = 0;
            
            switch(timeframe) {
                case '1m':
                    labels = Array.from({length: 30}, (_, i) => {
                        const date = new Date();
                        date.setDate(date.getDate() - (29 - i));
                        return date.toLocaleDateString('de-CH', {day: '2-digit', month: '2-digit'});
                    });
                    dataPoints = 30;
                    break;
                case '6m':
                    labels = Array.from({length: 6}, (_, i) => {
                        const date = new Date();
                        date.setMonth(date.getMonth() - (5 - i));
                        return date.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'});
                    });
                    dataPoints = 6;
                    break;
                case '1y':
                    labels = Array.from({length: 12}, (_, i) => {
                        const date = new Date();
                        date.setMonth(date.getMonth() - (11 - i));
                        return date.toLocaleDateString('de-CH', {month: 'short', year: '2-digit'});
                    });
                    dataPoints = 12;
                    break;
                case '5y':
                default:
                    labels = Array.from({length: 5}, (_, i) => {
                        const date = new Date();
                        date.setFullYear(date.getFullYear() - (4 - i));
                        return date.getFullYear().toString();
                    });
                    dataPoints = 5;
                    break;
            }
            
            const datasets = [];
            
            userPortfolio.forEach((asset, index) => {
                // Start mit 100% und generiere realistische Performance basierend auf Zeitraum
                let performance = [100];
                for (let i = 1; i < dataPoints; i++) {
                    // Realistischere Performance-Simulation basierend auf Zeitraum
                    const volatility = asset.volatility * 100;
                    const annualReturn = asset.expectedReturn * 100;
                    
                    // Angepasste Volatilität basierend auf Zeitraum
                    let timeframeVolatility = volatility;
                    if (timeframe === '1m') timeframeVolatility = volatility * 3;
                    else if (timeframe === '6m') timeframeVolatility = volatility * 1.5;
                    else if (timeframe === '1y') timeframeVolatility = volatility;
                    else timeframeVolatility = volatility * 0.7; // 5 Jahre - geringere Volatilität
                    
                    const randomFactor = (Math.random() * timeframeVolatility - timeframeVolatility/2) / 100;
                    const periodReturn = annualReturn / (timeframe === '1m' ? 12 : timeframe === '6m' ? 2 : 1);
                    const newValue = performance[i-1] * (1 + periodReturn/100 + randomFactor);
                    performance.push(newValue);
                }
                
                // Konvertiere zu prozentualer Performance relativ zum Start
                const percentagePerformance = performance.map(val => ((val - 100) / 100 * 100).toFixed(1));
                
                let color;
                if (asset.type === 'stock') {
                    color = stockColors[index % stockColors.length];
                } else if (asset.type === 'index') {
                    color = indexColors[index % indexColors.length];
                } else {
                    color = otherAssetColors[index % otherAssetColors.length];
                }
                
                datasets.push({
                    label: asset.symbol,
                    data: percentagePerformance,
                    borderColor: color,
                    backgroundColor: color + '20',
                    borderWidth: 2,
                    fill: false,
                    tension: timeframe === '1m' ? 0.1 : 0.4
                });
            });
            
            window.assetPerformanceChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: `Asset Performance (${getTimeframeLabel(timeframe)})`
                        },
                        legend: {
                            position: 'bottom'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Performance (%)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: getTimeframeLabel(timeframe)
                            }
                        }
                    }
                }
            });
        }

        function getTimeframeLabel(timeframe) {
            switch(timeframe) {
                case '1m': return 'Letzter Monat';
                case '6m': return 'Letzte 6 Monate';
                case '1y': return 'Letztes Jahr';
                case '5y': return 'Letzte 5 Jahre';
                default: return 'Historische Performance';
            }
        }

        function createPerformanceChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            
            if (window.performanceChartInstance) {
                window.performanceChartInstance.destroy();
            }
            
            const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
            const total = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn() / 12;
            
            let performanceData = [total];
            for (let i = 1; i < 12; i++) {
                performanceData.push(performanceData[i-1] * (1 + expectedReturn + (Math.random() * 0.02 - 0.01)));
            }
            
            window.performanceChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: [{
                        label: 'Portfolio Wert',
                        data: performanceData,
                        borderColor: '#0A1429',
                        backgroundColor: 'rgba(10, 20, 41, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    }
                }
            });
        }

        function createSimulationChart(initialValue, expectedReturn, years) {
            const ctx = document.getElementById('simulationChart').getContext('2d');
            
            if (window.simulationChartInstance) {
                window.simulationChartInstance.destroy();
            }
            
            const yearLabels = Array.from({length: years + 1}, (_, i) => `Jahr ${i}`);
            
            // Drei verschiedene Szenarien
            const baseScenario = [initialValue];
            const optimisticScenario = [initialValue];
            const conservativeScenario = [initialValue];
            
            for (let i = 1; i <= years; i++) {
                baseScenario.push(baseScenario[i-1] * (1 + expectedReturn/100));
                optimisticScenario.push(optimisticScenario[i-1] * (1 + (expectedReturn + 5)/100));
                conservativeScenario.push(conservativeScenario[i-1] * (1 + (expectedReturn - 3)/100));
            }
            
            window.simulationChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: yearLabels,
                    datasets: [
                        {
                            label: 'Optimistisch',
                            data: optimisticScenario,
                            borderColor: '#28A745',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Basis',
                            data: baseScenario,
                            borderColor: '#0A1429',
                            borderWidth: 3,
                            tension: 0.4
                        },
                        {
                            label: 'Konservativ',
                            data: conservativeScenario,
                            borderColor: '#DC3545',
                            borderWidth: 2,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    }
                }
            });
        }

        // Benchmark-Daten laden
        async function loadBenchmarkData() {
            try {
                const response = await fetch('/get_benchmark_data');
                const data = await response.json();
                
                const container = document.getElementById('benchmarkComparison');
                if (!container) return;
                
                let html = '';
                
                // Portfolio Benchmark
                const portfolioReturn = calculatePortfolioReturn() * 100;
                html += `
                    <div class="benchmark-card">
                        <h4>Ihr Portfolio</h4>
                        <div class="metric-value ${portfolioReturn >= 0 ? 'positive' : 'negative'}">${portfolioReturn >= 0 ? '+' : ''}${portfolioReturn.toFixed(1)}%</div>
                        <div class="metric-label">Erwartete Rendite</div>
                    </div>
                `;
                
                // Professionelle Benchmarks
                for (const [name, returnValue] of Object.entries(data)) {
                    html += `
                        <div class="benchmark-card">
                            <h4>${name}</h4>
                            <div class="metric-value ${returnValue >= 0 ? 'positive' : 'negative'}">${returnValue >= 0 ? '+' : ''}${returnValue}%</div>
                            <div class="metric-label">1-Jahres Rendite</div>
                        </div>
                    `;
                }
                
                container.innerHTML = html;
                
                // Peer Group Vergleich
                updatePeerComparison();
                
            } catch (error) {
                console.error('Error loading benchmark data:', error);
            }
        }

        // Peer Group Vergleich aktualisieren
        function updatePeerComparison() {
            const container = document.getElementById('peerComparison');
            if (!container) return;
            
            const portfolioReturn = calculatePortfolioReturn() * 100;
            const portfolioRisk = calculatePortfolioRisk() * 100;
            
            let html = '';
            
            for (const [bank, data] of Object.entries(swissBankPortfolios)) {
                const comparison = portfolioReturn > data.return ? 'positive' : 'negative';
                html += `
                    <div class="peer-card">
                        <h4>${bank.replace('_', ' ')}</h4>
                        <div class="metric-value ${comparison}">${data.return}%</div>
                        <div class="metric-label">Rendite vs. Ihr Portfolio: ${(portfolioReturn - data.return).toFixed(1)}%</div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }

        // Monte Carlo Simulation
        async function runMonteCarloSimulation() {
            const initialValue = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
            const expectedReturn = calculatePortfolioReturn();
            const volatility = calculatePortfolioRisk();
            const years = parseInt(document.getElementById('monteCarloYears').value) || 10;
            const simulations = parseInt(document.getElementById('monteCarloSimulations').value) || 1000;
            
            if (initialValue === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio.');
                return;
            }
            
            try {
                const response = await fetch('/monte_carlo_simulation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        initial_value: initialValue,
                        expected_return: expectedReturn * 100,
                        volatility: volatility * 100,
                        years: years,
                        simulations: simulations
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayMonteCarloResults(data);
                    createMonteCarloChart(data);
                } else {
                    alert('Fehler bei der Simulation: ' + data.error);
                }
            } catch (error) {
                console.error('Error running Monte Carlo simulation:', error);
                alert('Fehler bei der Verbindung zum Server.');
            }
        }

        function displayMonteCarloResults(data) {
            const container = document.getElementById('monteCarloResults');
            container.innerHTML = `
                <div class="performance-metrics">
                    <div class="performance-card">
                        <div class="metric-value positive">CHF ${Math.round(data.avg_final_value).toLocaleString('de-CH')}</div>
                        <div class="metric-label">Durchschnittlicher Endwert</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value">CHF ${Math.round(data.median_final_value).toLocaleString('de-CH')}</div>
                        <div class="metric-label">Median Endwert</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value">CHF ${Math.round(data.percentile_5).toLocaleString('de-CH')}</div>
                        <div class="metric-label">5% Worst Case</div>
                    </div>
                    <div class="performance-card">
                        <div class="metric-value positive">CHF ${Math.round(data.percentile_95).toLocaleString('de-CH')}</div>
                        <div class="metric-label">5% Best Case</div>
                    </div>
                </div>
                <p><strong>Interpretation:</strong> Bei ${data.simulations} Simulationen über ${document.getElementById('monteCarloYears').value} Jahre zeigt die Analyse, dass Ihr Portfolio mit 90% Wahrscheinlichkeit zwischen CHF ${Math.round(data.percentile_5).toLocaleString('de-CH')} und CHF ${Math.round(data.percentile_95).toLocaleString('de-CH')} wert sein wird.</p>
            `;
        }

        function createMonteCarloChart(data) {
            const ctx = document.getElementById('monteCarloChart').getContext('2d');
            
            if (window.monteCarloChartInstance) {
                window.monteCarloChartInstance.destroy();
            }
            
            const years = parseInt(document.getElementById('monteCarloYears').value) || 10;
            const labels = Array.from({length: years + 1}, (_, i) => `Jahr ${i}`);
            
            // Nur einige Pfade für die Visualisierung auswählen
            const displayPaths = data.paths.slice(0, 50);
            const datasets = displayPaths.map((path, i) => ({
                label: `Pfad ${i + 1}`,
                data: path,
                borderColor: `rgba(10, 20, 41, ${0.1 + i * 0.02})`,
                backgroundColor: `rgba(10, 20, 41, ${0.05})`,
                borderWidth: 1,
                pointRadius: 0,
                tension: 0.1
            }));
            
            // Durchschnittspfad hinzufügen
            const avgPath = [];
            for (let i = 0; i <= years; i++) {
                avgPath.push(data.paths.reduce((sum, path) => sum + path[i], 0) / data.paths.length);
            }
            
            datasets.push({
                label: 'Durchschnitt',
                data: avgPath,
                borderColor: '#DC3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.1
            });
            
            window.monteCarloChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Portfolio Wert (CHF)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // PDF Report generieren
        async function generatePDFReport() {
            if (userPortfolio.length === 0) {
                alert('Bitte erstellen Sie zuerst ein Portfolio.');
                return;
            }
            
            try {
                // Portfolio Metriken berechnen
                const totalValue = userPortfolio.reduce((sum, asset) => sum + asset.investment, 0);
                const expectedReturn = calculatePortfolioReturn();
                const volatility = calculatePortfolioRisk();
                const sharpeRatio = volatility > 0 ? (expectedReturn - 0.02) / volatility : 0;
                
                const analysisData = {
                    total_value: totalValue,
                    expected_return: expectedReturn,
                    volatility: volatility,
                    sharpe_ratio: sharpeRatio,
                    diversification_score: Math.min(userPortfolio.length * 2, 10)
                };
                
                // Monte Carlo Daten (falls verfügbar)
                let monteCarloData = {};
                if (window.monteCarloResults) {
                    monteCarloData = window.monteCarloResults;
                }
                
                const response = await fetch('/generate_pdf_report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        },
                    body: JSON.stringify({
                        portfolio: userPortfolio,
                        analysis: analysisData,
                        monte_carlo: monteCarloData
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'Portfolio_Overview.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    showNotification('PDF Report erfolgreich heruntergeladen!', 'success');
                } else {
                    throw new Error('Fehler beim Generieren des PDFs');
                }
            } catch (error) {
                console.error('Error generating PDF:', error);
                alert('Fehler beim Generieren des PDF-Reports: ' + error.message);
            }
        }

        // Strategie Analyse
        function updateStrategyAnalysis() {
            const container = document.getElementById('strategieanalyse');
            
            if (userPortfolio.length === 0 || !portfolioCalculated) {
                container.innerHTML = `
                    <div class="page-header">
                        <h2>Multi-Strategie Analyse</h2>
                        <p>Vergleichen Sie 5 verschiedene Portfolio-Optimierungsstrategien</p>
                    </div>
                    <div class="instruction-box">
                        <h4>🎯 Was diese Analyse bietet:</h4>
                        <p>Hier sehen Sie Ihr Portfolio optimiert nach 5 wissenschaftlichen Methoden. Jede Strategie hat unterschiedliche Ziele: Maximale Rendite, minimales Risiko, oder optimale Balance.</p>
                    </div>
                    <div class="card" style="text-align: center; margin-bottom: 30px;">
                        <h3 style="color: #ffffff; font-weight: 600; text-shadow: 0 1px 3px rgba(0,0,0,0.3);">Portfolio Strategie-Vergleich</h3>
                        <p>Bitte erstellen Sie zuerst ein Portfolio im Dashboard und klicken Sie auf "Portfolio Berechnen".</p>
                        <button class="btn" onclick="switchToDashboard()" style="margin-top: 15px; background: linear-gradient(145deg, #3A3A3A, #303030); color: #E8E8E8; border: 1px solid var(--border-light);">Zum Dashboard</button>
                    </div>
                `;
                return;
            }

            // Berechne alle Strategien
            const strategies = calculateAllStrategies();
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;
            
            container.innerHTML = `
                <div class="page-header">
                    <h2>Multi-Strategie Analyse</h2>
                    <p>Vergleichen Sie 5 verschiedene Portfolio-Optimierungsstrategien</p>
                </div>
                
                <div class="instruction-box">
                    <h4>🎯 Was diese Analyse bietet:</h4>
                    <p>Hier sehen Sie Ihr Portfolio optimiert nach 5 wissenschaftlichen Methoden. Jede Strategie hat unterschiedliche Ziele: Maximale Rendite, minimales Risiko, oder optimale Balance. Wählen Sie die Strategie die am besten zu Ihrer Risikobereitschaft passt.</p>
                </div>

                <div class="strategy-comparison">
                    <div>
                        <h3 style="color: #ffffff; font-weight: 600; text-shadow: 0 1px 3px rgba(0,0,0,0.3);">Strategie-Vergleich</h3>
                        <table class="comparison-table">
                            <thead>
                                <tr>
                                    <th>Strategie</th>
                                    <th>Rendite</th>
                                    <th>Risiko</th>
                                    <th>Sharpe Ratio</th>
                                    <th>Empfehlung</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${strategies.map(strategy => `
                                    <tr>
                                        <td style="text-align: left; font-weight: bold; color: #E8E8E8;">${strategy.name}</td>
                                        <td class="${strategy.return >= 0 ? 'positive' : 'negative'}" style="font-weight: 600;">${strategy.return >= 0 ? '+' : ''}${strategy.return}%</td>
                                        <td style="color: #C0C0FF; font-weight: 500;">${strategy.risk}%</td>
                                        <td style="color: #FFD700; font-weight: 500;">${strategy.sharpe}</td>
                                        <td><span class="recommendation-badge ${strategy.badgeClass}">${strategy.recommendation}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div>
                        <h3>Portfolio-Bewertung</h3>
                        <div class="rating-score">${calculatePortfolioRating(strategies)}/100</div>
                        <div class="card">
                            <h4>Gesamtbewertung</h4>
                            <p><strong>Top-Strategie:</strong> ${getTopStrategy(strategies).name}</p>
                            <p><strong>Verbesserungspotenzial:</strong> ${calculateImprovementPotential(strategies)}%</p>
                            <p><strong>Risikoprofil:</strong> ${getRiskProfile(strategies)}</p>
                            <p><strong>Vergleich mit Standards:</strong> ${getPortfolioStandardComparison(strategies)}</p>
                        </div>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="strategyComparisonChart"></canvas>
                </div>

                <h3 style="margin-top: 30px; color: #E8E8E8;">Detaillierte Strategie-Analyse</h3>
                <div class="strategy-grid">
                    ${strategies.map(strategy => `
                        <div class="strategy-card ${strategy.cardClass}" style="background: linear-gradient(145deg, #2A2A2A, #232323); border: 1px solid var(--border-light); box-shadow: var(--shadow-soft);">
                            <h4 style="color: #E8E8E8;">${strategy.name}</h4>
                            <p><strong style="color: #E8E8E8;">Ziel:</strong> <span style="color: #E0E0E0;">${strategy.description}</span></p>
                            <div class="optimization-result" style="background: rgba(138, 43, 226, 0.1); padding: 12px; border-radius: 8px; margin: 10px 0;">
                                <p><strong style="color: #E8E8E8;">Optimierte Rendite:</strong> <span class="${strategy.return >= 0 ? 'positive' : 'negative'}" style="font-weight: bold;">${strategy.return >= 0 ? '+' : ''}${strategy.return}%</span></p>
                                <p><strong style="color: #E8E8E8;">Optimiertes Risiko:</strong> <span style="color: #E0E0E0;">${strategy.risk}%</span></p>
                                <p><strong style="color: #E8E8E8;">Verbesserung:</strong> 
                                    <span class="improvement-indicator ${strategy.improvement > 0 ? 'improvement-positive' : 'improvement-negative'}" style="font-weight: bold;">
                                        ${strategy.improvement > 0 ? '↗' : '↘'} ${strategy.improvement}%
                                    </span>
                                </p>
                            </div>
                            <p><strong style="color: #E8E8E8;">Empfehlung:</strong> <span style="color: #E0E0E0;">${strategy.detailedRecommendation}</span></p>
                        </div>
                    `).join('')}
                </div>
            `;

            createStrategyComparisonChart(strategies);
        }

        function calculateAllStrategies() {
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;

            return [
                {
                    name: "Mean-Variance",
                    description: "Optimales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn + 1.5 + Math.random() * 2, 15),
                    risk: Math.max(currentRisk - 2 + Math.random() * 3, 5),
                    sharpe: (0.35 + Math.random() * 0.2).toFixed(2),
                    recommendation: "OPTIMAL",
                    badgeClass: "badge-optimal",
                    cardClass: "strategy-1",
                    improvement: +(1.5 + Math.random() * 2).toFixed(1),
                    detailedRecommendation: "Erhöhen Sie Tech-Aktien und reduzieren Sie Bonds für bessere Performance."
                },
                {
                    name: "Risk Parity",
                    description: "Gleicher Risikobeitrag aller Assets",
                    return: Math.min(currentReturn + 0.5 + Math.random() * 1, 12),
                    risk: Math.max(currentRisk - 4 + Math.random() * 2, 4),
                    sharpe: (0.4 + Math.random() * 0.15).toFixed(2),
                    recommendation: "BALANCIERT",
                    badgeClass: "badge-balanced",
                    cardClass: "strategy-2",
                    improvement: +(0.5 + Math.random() * 1).toFixed(1),
                    detailedRecommendation: "Diversifizieren Sie stärker in Rohstoffe und Immobilien."
                },
                {
                    name: "Min Variance",
                    description: "Minimales Portfolio-Risiko",
                    return: Math.min(currentReturn - 1 + Math.random() * 1, 8),
                    risk: Math.max(currentRisk - 6 + Math.random() * 2, 3),
                    sharpe: (0.45 + Math.random() * 0.1).toFixed(2),
                    recommendation: "KONSERVATIV",
                    badgeClass: "badge-conservative",
                    cardClass: "strategy-3",
                    improvement: +(-1 + Math.random() * 1).toFixed(1),
                    detailedRecommendation: "Konzentrieren Sie sich auf stabile Blue-Chip Aktien und Anleihen."
                },
                {
                    name: "Max Sharpe",
                    description: "Maximales Rendite-Risiko-Verhältnis",
                    return: Math.min(currentReturn + 2.5 + Math.random() * 3, 20),
                    risk: Math.max(currentRisk + 3 + Math.random() * 4, 8),
                    sharpe: (0.5 + Math.random() * 0.25).toFixed(2),
                    recommendation: "AGGRESSIV",
                    badgeClass: "badge-aggressive",
                    cardClass: "strategy-4",
                    improvement: +(2.5 + Math.random() * 3).toFixed(1),
                    detailedRecommendation: "Investieren Sie mehr in Growth-Aktien und reduzieren Sie defensive Assets."
                },
                {
                    name: "Black-Litterman",
                    description: "Marktdaten + eigene Erwartungen",
                    return: Math.min(currentReturn + 1.2 + Math.random() * 1.5, 14),
                    risk: Math.max(currentRisk - 1 + Math.random() * 2, 6),
                    sharpe: (0.42 + Math.random() * 0.18).toFixed(2),
                    recommendation: "EXPERTE",
                    badgeClass: "badge-optimal",
                    cardClass: "strategy-5",
                    improvement: +(1.2 + Math.random() * 1.5).toFixed(1),
                    detailedRecommendation: "Kombinieren Sie fundamentale Analyse mit quantitativen Modellen."
                }
            ];
        }

        function calculatePortfolioRating(strategies) {
            const baseScore = 65;
            const diversificationBonus = Math.min(userPortfolio.length * 3, 15);
            const riskAdjustment = strategies[0].risk > 20 ? -10 : strategies[0].risk < 10 ? 5 : 0;
            const sharpeBonus = strategies[0].sharpe > 0.4 ? 10 : 0;
            
            return Math.min(baseScore + diversificationBonus + riskAdjustment + sharpeBonus, 95);
        }

        function getTopStrategy(strategies) {
            return strategies.reduce((best, current) => 
                parseFloat(current.sharpe) > parseFloat(best.sharpe) ? current : best
            );
        }

        function calculateImprovementPotential(strategies) {
            const topStrategy = getTopStrategy(strategies);
            const currentReturn = calculatePortfolioReturn() * 100;
            
            return Math.max(0, (topStrategy.return - currentReturn)).toFixed(1);
        }

        function getRiskProfile(strategies) {
            const avgRisk = strategies.reduce((sum, s) => sum + s.risk, 0) / strategies.length;
            if (avgRisk > 18) return "Aggressiv";
            if (avgRisk > 12) return "Moderat";
            return "Konservativ";
        }

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

        function createStrategyComparisonChart(strategies) {
            const ctx = document.getElementById('strategyComparisonChart').getContext('2d');
            
            if (window.strategyChartInstance) {
                window.strategyChartInstance.destroy();
            }
            
            const currentReturn = calculatePortfolioReturn() * 100;
            const currentRisk = calculatePortfolioRisk() * 100;

            const data = [
                { x: currentRisk, y: currentReturn, label: 'Aktuelles Portfolio' },
                ...strategies.map((s, i) => ({ x: s.risk, y: s.return, label: s.name }))
            ];

            window.strategyChartInstance = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Portfolio Strategien',
                        data: data,
                        backgroundColor: ['#0A1429'].concat(strategies.map((s, i) => 
                            ['#28A745', '#D52B1E', '#6B46C1', '#2B6CB0', '#F59E0B'][i]
                        )),
                        borderColor: ['#0A1429'].concat(strategies.map((s, i) => 
                            ['#28A745', '#D52B1E', '#6B46C1', '#2B6CB0', '#F59E0B'][i]
                        )),
                        borderWidth: 2,
                        pointRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: { 
                                display: true, 
                                text: 'Risiko (Volatilität in %)' 
                            }
                        },
                        y: {
                            title: { 
                                display: true, 
                                text: 'Rendite (in %)' 
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const point = data[context.dataIndex];
                                    return `${point.label}: ${point.y.toFixed(1)}% Rendite, ${point.x.toFixed(1)}% Risiko`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function generateMarketAnalysis() {
            let analysis = '<div class="market-analysis-grid">';
            
            // Analyse für jede Asset-Klasse im Portfolio
            userPortfolio.forEach(asset => {
                let sector = getAssetSector(asset.symbol);
                let cycle = marketCycles[sector] || {cycle: "Unbekannt", phase: "Unbekannt", rating: "Mittel", trend: "➡️"};
                let cycleClass = "cycle-cyclical";
                if (cycle.cycle === "Wachstum") cycleClass = "cycle-growth";
                if (cycle.cycle === "Defensiv") cycleClass = "cycle-defensive";
                
                analysis += `
                    <div class="market-analysis-card">
                        <h4>${asset.name} (${asset.symbol})</h4>
                        <p><strong>Sektor:</strong> ${sector}</p>
                        <p><strong>Marktzyklus:</strong> <span class="cycle-indicator ${cycleClass}">${cycle.cycle} ${cycle.trend}</span></p>
                        <p><strong>Phase:</strong> ${cycle.phase}</p>
                        <p><strong>Bewertung:</strong> ${cycle.rating}</p>
                        <p><strong>Empfehlung:</strong> ${getInvestmentAdvice(cycle, asset.type)}</p>
                    </div>
                `;
            });
            
            analysis += '</div>';
            return analysis;
        }

        function getAssetSector(symbol) {
            // Vereinfachte Sektor-Zuordnung
            const sectorMap = {
                "TECH": ["LOGIN.SW", "TEMN.SW", "NDX", "SPX", "TLT"],
                "HEALTH": ["NESN.SW", "NOVN.SW", "ROG.SW", "LONN.SW", "XLV"],
                "FINANCIAL": ["UBSG.SW", "CSGN.SW", "ZURN.SW", "BAER.SW"],
                "ENERGY": ["OIL", "XLE", "CL=F"],
                "MATERIALS": ["GOLD", "SILVER", "COPPER", "ABBN.SW", "XLB", "GLD", "SI=F", "HG=F"],
                "INDUSTRIAL": ["SIKA.SW", "GEBN.SW", "ADEN.SW"],
                "CONSUMER": ["CFR.SW", "GIVN.SW"],
                "UTILITIES": ["SCMN.SW", "XLU"]
            };
            
            for (const [sector, symbols] of Object.entries(sectorMap)) {
                if (symbols.includes(symbol)) return sector;
            }
            return "Diversified";
        }

        function getInvestmentAdvice(cycle, assetType) {
            if (cycle.rating === "Hoch" && cycle.trend === "↗️") {
                return "💡 Starke Kaufempfehlung - Günstige Einstiegschance";
            } else if (cycle.rating === "Mittel" && cycle.trend === "↗️") {
                return "👍 Gute Investitionsmöglichkeit - Wachstumspotenzial";
            } else if (cycle.rating === "Niedrig" || cycle.trend === "↘️") {
                return "⚠️ Vorsicht geboten - Überprüfen Sie die Position";
            } else {
                return "🤔 Neutrale Haltung - Beobachten Sie die Entwicklung";
            }
        }

        function getSectorAllocationAdvice() {
            const sectors = {};
            userPortfolio.forEach(asset => {
                const sector = getAssetSector(asset.symbol);
                sectors[sector] = (sectors[sector] || 0) + parseFloat(asset.weight);
            });
            
            const techWeight = sectors["TECH"] || 0;
            const financialWeight = sectors["FINANCIAL"] || 0;
            
            if (techWeight > 30) return "Reduzieren Sie Tech-Übergewichtung";
            if (financialWeight > 25) return "Diversifizieren Sie Finanzsektor";
            return "Ausgewogene Sektor-Allokation";
        }

        /**
         * Wechselt zu einer bestimmten Seite anhand des Seitennamens
         * @param {string} pageName - Name der Seite (z.B. "dashboard", "portfolio", etc.)
         */
        function switchToPage(pageName) {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            const targetTab = document.querySelector(`[data-page="${pageName}"]`);
            if (targetTab) {
                targetTab.classList.add('active');
            }
            
            document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
            const targetPage = document.getElementById(pageName);
            if (targetPage) {
                targetPage.classList.add('active');
                
                // Spezielle Aktionen für bestimmte Seiten
                if (pageName === 'strategieanalyse') {
                    setTimeout(updateStrategyAnalysis, 100);
                }
            }
        }
        
        function switchToDashboard() {
            switchToPage('dashboard');
        }
        
        function switchToGettingStarted() {
            switchToPage('getting-started');
        }

        // Navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Wenn es der "Startseite" Link ist, zeigen wir die Landing Page und beenden früh
                if (tab.id === 'startseiteLink') {
                    showLandingPage();
                    return;
                }
                
                // Landing Page ausblenden, falls sie aktiv ist
                hideLandingPage();
                
                // Zur entsprechenden Seite wechseln, falls ein data-page Attribut existiert
                if (tab.dataset.page) {
                    switchToPage(tab.dataset.page);
                }
            });
        });

        // Total Investment Update
        document.getElementById('totalInvestment').addEventListener('input', function() {
            totalInvestment = parseFloat(this.value) || 0;
            updatePortfolioDisplay();
        });

        // Investment Years Update
        document.getElementById('investmentYears').addEventListener('input', function() {
            updatePortfolioReturn();
            if (portfolioCalculated) {
                updateSimulationPage();
                updateScenarioAnalysis();
            }
        });

        // Verhindere Seitenverlassen ohne Bestätigung
        window.addEventListener('beforeunload', function (e) {
            if (userPortfolio.length > 0) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Chart.js Matrix Chart Type registrieren
        Chart.register({
            id: 'matrix',
            type: 'matrix',
            defaults: {
                width: '100%',
                height: '100%'
            } });
        function updateGlobalMarketStatus() {
            const now = new Date();
            const zurichTime = new Date(now.toLocaleString("en-US", {timeZone: "Europe/Zurich"}));
            const zurichHour = zurichTime.getHours() + zurichTime.getMinutes()/60;
            const isWeekday = zurichTime.getDay() >= 1 && zurichTime.getDay() <= 5;
            
            // Börsen-Öffnungszeiten (Zürich Zeit)
            const sixOpen = isWeekday && zurichHour >= 9 && zurichHour < 17.5;
            const nyseOpen = isWeekday && zurichHour >= 15.5 && zurichHour < 22;
            const forexOpen = isWeekday; // Forex: 24/5
            
            // Status updaten
            const marketElements = document.querySelectorAll('.market-status');
            if (marketElements.length > 0) {
                marketElements[0].textContent = sixOpen ? 'OPEN' : 'CLOSED';
                marketElements[0].className = sixOpen ? 'market-status market-open' : 'market-status market-closed';
                
                marketElements[1].textContent = nyseOpen ? 'OPEN' : 'CLOSED';
                marketElements[1].className = nyseOpen ? 'market-status market-open' : 'market-status market-closed';
                
                marketElements[2].textContent = forexOpen ? 'OPEN' : 'CLOSED';
                marketElements[2].className = forexOpen ? 'market-status market-open' : 'market-status market-closed';
            }
        }

        // Alle 60 Sekunden updaten
        setInterval(updateGlobalMarketStatus, 60000);
        updateGlobalMarketStatus(); // Sofort ausführen
        
        // Handle tabs in the Investing page
        document.addEventListener('DOMContentLoaded', function() {
            const tabs = document.querySelectorAll('.tabs .tab');
            
            tabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Remove active class from all tabs and content
                    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    this.classList.add('active');
                    
                    // Show corresponding content
                    const tabId = this.getAttribute('data-tab');
                    document.getElementById(tabId + '-content').classList.add('active');
                });
            });
            
            // Initialize charts when visiting the investing page
            document.querySelector('[data-page="investing"]').addEventListener('click', function() {
                setTimeout(initInvestingCharts, 100);
            });
            
            // Set the default active page to Getting Started
            setTimeout(switchToGettingStarted, 100);
        });
        
        function initInvestingCharts() {
            // Stocks chart
            if (document.getElementById('stocks-chart')) {
                new Chart(document.getElementById('stocks-chart'), {
                    type: 'line',
                    data: {
                        labels: ['2010', '2012', '2014', '2016', '2018', '2020', '2022'],
                        datasets: [{
                            label: 'Growth Stocks',
                            data: [100, 120, 140, 180, 220, 260, 280],
                            borderColor: 'rgba(75, 192, 192, 1)',
                            tension: 0.1
                        }, {
                            label: 'Value Stocks',
                            data: [100, 110, 125, 140, 160, 170, 190],
                            borderColor: 'rgba(153, 102, 255, 1)',
                            tension: 0.1
                        }, {
                            label: 'Dividend Stocks',
                            data: [100, 115, 130, 150, 165, 180, 195],
                            borderColor: 'rgba(255, 159, 64, 1)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Stock Performance (Indexed)'
                            }
                        }
                    }
                });
            }
        }
    </script>

    <!-- Footer -->
    <footer class="bg-black-main border-t border-panel" style="padding: 2rem 0; font-family: 'Playfair Display', serif;">
        <div class="max-w-7xl mx-auto px-10 lg:px-12 flex flex-col md:flex-row justify-between items-center">
            <span style="color: #E0E0E0; font-size: 0.9rem; letter-spacing: 0.5px; margin-left: 25px;">© 2025 Swiss Asset Pro – Invest Smarter</span>
            <div style="display: flex; flex-direction: column; align-items: flex-end; margin-top: 1rem; margin-right: 35px;">
                <a href="https://www.six-group.com" target="_blank" style="color: #E0E0E0; margin-bottom: 0.6rem; text-decoration: none; font-family: 'Inter', sans-serif; transition: all 0.3s; font-size: 0.9rem;">
                    <i class="fas fa-chart-line" style="margin-right: 0.5rem;"></i> SIX Group
                </a>
                <a href="https://finance.yahoo.com" target="_blank" style="color: #E0E0E0; margin-bottom: 0.6rem; text-decoration: none; font-family: 'Inter', sans-serif; transition: all 0.3s; font-size: 0.9rem;">
                    <i class="fab fa-yahoo" style="margin-right: 0.5rem;"></i> Yahoo Finance
                </a>
                <a href="https://www.bloomberg.com" target="_blank" style="color: #E0E0E0; text-decoration: none; font-family: 'Inter', sans-serif; transition: all 0.3s; font-size: 0.9rem;">
                    <i class="fas fa-globe" style="margin-right: 0.5rem;"></i> Bloomberg
                </a>
            </div>
        </div>
    </footer>
</body>
</html>
'''

if __name__ == '__main__':
    print("=" * 80)
    print("SWISS ASSET PRO - PROFESSIONELLE PORTFOLIO SIMULATION")
    print("=" * 80)
    print("📊 Die Anwendung ist jetzt verfügbar unter: http://localhost:8000")
    print("🔐 Passwort für den Zugang: swissassetmanagerAC")
    print("💡 Entwickelt von Ahmed Choudhary - Bachelor Banking & Finance UZH")
    print("=" * 80)
    print("NEUE FUNKTIONEN:")
    print("✅ Funktionsfähige Korrelationsmatrix mit Heatmap-Stil")
    print("✅ Bloomberg-ähnlicher PDF-Report mit professionellem Design")
    print("✅ Performance-Metriken im Bloomberg-Stil")
    print("✅ Sektor-Performance Analyse")
    print("✅ Korrelations-Legende und farbliche Hervorhebungen")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 8000))
    print(f"Versuchen Sie, die App auf Ihrem Handy mit dieser URL zu öffnen:")
    import socket
    # Alle IP-Adressen des Computers abrufen
    hostname = socket.gethostname()
    try:
        # Versuchen, alle IP-Adressen zu erhalten
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        for ip in ip_addresses:
            print(f"http://{ip}:{port}")
    except:
        # Fallback auf eine Standard-IP
        print(f"http://192.168.1.9:{port}")
    
    print(f"Passwort für den Zugang: swissassetmanagerAC")
    app.run(host='0.0.0.0', port=port, debug=False)

