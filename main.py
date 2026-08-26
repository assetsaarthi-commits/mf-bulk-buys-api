from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import time
from datetime import datetime, timedelta
from nselib import capital_market

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE = {}
TTL = 300

def get_data(days: int):
    now = time.time()
    cached = CACHE.get(days)
    if cached and now - cached["ts"] < TTL:
        return cached["data"]

    try:
        deals = capital_market.bulk_deal_data()  # ← Fixed function name
        df = pd.DataFrame(deals)
        mf = df[df['buyerName'].str.contains('MUTUAL FUND', case=False, na=False)]
        mf['dealDate'] = pd.to_datetime(mf['dealDate'])
        cutoff = datetime.now() - timedelta(days=days)
        mf = mf[mf['dealDate'] >= cutoff]
        mf = mf.sort_values('quantity', ascending=False)

        result = {
            "status": "success",
            "count": len(mf),
            "cached_at": int(now),
            "data": mf[["dealDate", "symbol", "buyerName", "quantity", "dealPrice"]].to_dict("records")
        }
    except Exception as e:
        if cached:
            return cached["data"]
        return {"status": "error", "message": str(e)}

    CACHE[days] = {"ts": now, "data": result}
    return result

@app.get("/api/mf-bulk-buys")
def get_buys(days: int = Query(30, ge=1, le=90)):
    return get_data(days)

@app.get("/mf-bulk-buys")
def get_buys_alt(days: int = Query(30, ge=1, le=90)):
    return get_data(days)

@app.get("/")
def root():
    return {"status": "online", "message": "MF Bulk Buys API is running"}
