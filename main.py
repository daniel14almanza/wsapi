from fastapi import FastAPI, HTTPException, status, Path
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:5173"], 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/screening")
async def screening(name: str, source: str):
    if source == "offshore":
        return await search_offshore(name)
    elif source == "worldbank":
        return await search_worldbank(name)
    elif source == "ofac":
        # return await search_ofac(name)
        return None
    else:
        raise HTTPException(status_code=400, detail="Invalid source")





async def search_offshore(name: str):
    reconcile_url = "https://offshoreleaks.icij.org/api/v1/reconcile"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        resp = await client.post(reconcile_url, json={"query": name, "type": "Entity"})
        
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"Error querying Offshore Leaks: {resp.status_code}, {resp.text}"
            )
        
        candidates = resp.json().get("result", [])

    # Return raw matches (without node lookup yet)
    return {
        "source": "offshore",
        "hits": len(candidates),
        "results": [
            {
                "Entity": c.get("name"),
                "Description": c.get("description"),
                "Score": c.get("score"),
                "Id": c.get("id")
            }
            for c in candidates
        ]
    }


async def search_worldbank(name: str):
    url = "https://apigwext.worldbank.org/dvsvc/v1.0/json/APPLICATION/ADOBE_EXPRNCE_MGR/FIRM/SANCTIONED_FIRM"

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "apikey": "z9duUaFUiEUYSHs97CU38fcZO7ipOPvm",  
        "content-type": "application/json; charset=utf-8",
        "origin": "https://projects.worldbank.org",
        "referer": "https://projects.worldbank.org/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Error querying World Bank: {resp.text}"
            )

        data = resp.json().get("response", {}).get("ZPROCSUPP", [])

    search_term = name.strip().lower()
    results = []

    for firm in data:
        firm_name = firm.get("SUPP_NAME", "").lower()
        if search_term in firm_name:
            results.append({
                "Firm Name": firm.get("SUPP_NAME"),
                "Address": firm.get("SUPP_ADDR"),
                "Country": firm.get("COUNTRY_NAME"),
                "From Date": firm.get("DEBAR_FROM_DATE"),
                "To Date": firm.get("DEBAR_TO_DATE"),
                "Grounds": firm.get("DEBAR_REASON")
            })

    return {
        "source": "worldbank",
        "hits": len(results),
        "results": results
    }
