from fastapi import FastAPI, HTTPException, status, Path
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import requests
from bs4 import BeautifulSoup

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
        return await search_ofac(name)
    else:
        raise HTTPException(status_code=400, detail="Invalid source")



async def search_offshore(name: str, limit: int = 50):
    # Construct the search URL
    search_url = (
        "https://offshoreleaks.icij.org/search"
        f"?cat=Entity&q={name.replace(' ', '+')}&from=0&size={limit}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://offshoreleaks.icij.org/",
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        resp = await client.get(search_url)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Error fetching Offshore Leaks HTML: {resp.status_code}"
            )

        soup = BeautifulSoup(resp.content, "html.parser")

        # Select table rows
        table = soup.select_one("table.search__results__table tbody")
        if not table:
            return {"source": "offshore", "hits": 0, "results": []}

        results = []
        for row in table.find_all("tr")[:limit]:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue  # Skip malformed rows

            results.append({
                "Entity": cols[0].get_text(strip=True),
                "Jurisdiction": cols[1].get_text(strip=True),
                "Linked To": cols[2].get_text(strip=True),
                "Data From": cols[3].get_text(strip=True),
            })

    return {
        "source": "offshore",
        "hits": len(results),
        "results": results
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



async def search_ofac(name: str, limit: int = 50):
    
    # Search the OFAC Sanctions List for a given name.
    # Returns a dict with source, number of hits, and results.
    

    BASE_URL = "https://sanctionssearch.ofac.treas.gov/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Step 1: GET main page to fetch hidden form fields
        resp = await client.get(BASE_URL)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Error fetching OFAC page: {resp.status_code}"
            )

        soup = BeautifulSoup(resp.content, "html.parser")
        viewstate = soup.find("input", id="__VIEWSTATE")["value"]
        viewstategenerator = soup.find("input", id="__VIEWSTATEGENERATOR")["value"]

        # Step 2: POST search
        post_data = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "ctl00$MainContent$txtLastName": name,
            "ctl00$MainContent$txtAddress": "",
            "ctl00$MainContent$txtCity": "",
            "ctl00$MainContent$txtID": "",
            "ctl00$MainContent$txtState": "",
            "ctl00$MainContent$Slider1": str(limit),
            "ctl00$MainContent$Slider1_Boundcontrol": str(limit),
            "ctl00$MainContent$btnSearch": "Search",
        }

        post_resp = await client.post(BASE_URL, data=post_data)
        if post_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Error performing OFAC search: {post_resp.status_code}"
            )

        soup = BeautifulSoup(post_resp.content, "html.parser")
        table = soup.find("table", id="gvSearchResults")
        if not table:
            return {"source": "ofac", "hits": 0, "results": []}

        results = []
        rows = table.find_all("tr")
        for row in rows[:limit]:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue

            results.append({
                "Name": cols[0].get_text(strip=True),
                "Address": cols[1].get_text(strip=True),
                "Type": cols[2].get_text(strip=True),
                "Program": cols[3].get_text(strip=True),
                "List": cols[4].get_text(strip=True),
                "Score": cols[5].get_text(strip=True),
            })

    return {
        "source": "ofac",
        "hits": len(results),
        "results": results
    }