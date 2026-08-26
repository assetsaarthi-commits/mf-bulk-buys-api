from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE = {}
TTL = 300  # 5 minutes

def fetch_nse_bulk_deals():
    """Fetch bulk deals from NSE with browser-like headers"""
    session = requests.Session()
    
    # Set headers exactly like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/",
        "Origin": "https://www.nseindia.com",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # First, visit the homepage to set cookies
    home_resp = session.get("https://www.nseindia.com", headers=headers, timeout=10)
    if home_resp.status_code != 200:
        raise Exception("Failed to reach NSE homepage")
    
    # Now fetch bulk deals
    url = "https://www.nseindia.com/api/bulk-deals"
    resp = session.get(url, headers=headers, timeout=10)
    
    if resp.status_code != 200:
        raise Exception(f"NSE API returned {resp.status_code}")
    
    data = resp.json()
    # The data is a list of dicts
    return data

def get_data(days: int):
    now = time.time()
    cached = CACHE.get(days)
    if cached and now - cached["ts"] < TTL:
        return cached["data"]

    try:
        raw = fetch_nse_bulk_deals()
        df = pd.DataFrame(raw)
        
        # Filter for mutual fund buyers (buyerName contains "MUTUAL FUND")
        mf = df[df['buyerName'].str.contains('MUTUAL FUND', case=False, na=False)]
        
        # Convert date column
        mf['dealDate'] = pd.to_datetime(mf['dealDate'])
        cutoff = datetime.now() - timedelta(days=days)
        mf = mf[mf['dealDate'] >= cutoff]
        
        # Sort by quantity descending
        mf = mf.sort_values('quantity', ascending=False)
        
        result = {
            "status": "success",
            "count": len(mf),
            "cached_at": int(now),
            "data": mf[["dealDate", "symbol", "buyerName", "quantity", "dealPrice"]].to_dict("records")
        }
    except Exception as e:
        # Serve stale cache if available
        if cached:
            return cached["data"]
        return {"status": "error", "message": str(e)}

    CACHE[days] = {"ts": now, "data": result}
    return result

@app.get("/api/mf-bulk-buys")
def get_buys(days: int = Query(30, ge=1, le=90)):
    return get_data(days)
