from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import nselib
import pandas as pd
import time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE = {}
TTL = 300  # 5 minutes

def get_data(days: int):
    now = time.time()
    cached = CACHE.get(days)
    if cached and now - cached["ts"] < TTL:
        return cached["data"]

    try:
        deals = nselib.capital_market.bulk_deal_data(period=f"{days}D")
        mf = deals[deals["buyer_name"].str.contains("mutual fund", case=False, na=False)]
        result = {
            "status": "success",
            "count": len(mf),
            "cached_at": int(now),
            "data": mf[["deal_date", "symbol", "buyer_name", "quantity", "deal_price"]].to_dict("records")
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
