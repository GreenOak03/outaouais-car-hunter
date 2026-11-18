#!/usr/bin/env python3
"""
Outaouais Car Deal Hunter & True Cost of Ownership (TCO) Scorer
Region: Gatineau (QC) & Ottawa (ON) — Postal Code: J8P1P3 (250km radius)
Outputs: data/outaouais_best_deals.json with DIRECT INDIVIDUAL CAR LISTING URLs (/v-... and /a/...)
"""

import json
import os
import re
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

CONFIG = {
    "postal_code": "J8P1P3",
    "radius_km": 250,
    "max_price_cad": 28000,
    "max_odometer_km": 90000,
    "min_reliability_score": 80,
    "min_tech_score": 75,
    "min_winter_score": 75,
    "current_car_monthly_tco": 646,
    "current_car_trade_in": 24060,
    "annual_km": 13000,
    "gas_price_qc": 1.62,
}

APPROVED_MODELS = [
    {
        "model_id": "toyota-corolla",
        "make": "Toyota",
        "model": "Corolla",
        "make_slug": "toyota",
        "model_slug": "corolla",
        "min_year": 2020,
        "max_year": 2023,
        "full_model": "Corolla SE Upgrade (2.0L)",
        "reliability": 95,
        "tech": 81,
        "winter": 80,
        "baseline_2021_value": 20900,
        "target_deal_price": 18450,
        "fuel_l100km": 6.7,
        "annual_maint": 460,
        "depreciation_rate": 0.078
    },
    {
        "model_id": "mazda-3-awd",
        "make": "Mazda",
        "model": "Mazda3",
        "make_slug": "mazda",
        "model_slug": "mazda3",
        "min_year": 2020,
        "max_year": 2023,
        "full_model": "Mazda3 Sport GS AWD Hatch",
        "reliability": 90,
        "tech": 86,
        "winter": 88,
        "baseline_2021_value": 22200,
        "target_deal_price": 19600,
        "fuel_l100km": 7.9,
        "annual_maint": 540,
        "depreciation_rate": 0.088
    },
    {
        "model_id": "chevy-bolt-euv",
        "make": "Chevrolet",
        "model": "Bolt",
        "make_slug": "chevrolet",
        "model_slug": "bolt-euv",
        "min_year": 2022,
        "max_year": 2023,
        "full_model": "Bolt EUV Premier (EV)",
        "reliability": 84,
        "tech": 89,
        "winter": 80,
        "baseline_2021_value": 23800,
        "target_deal_price": 20400,
        "fuel_l100km": 1.8,
        "annual_maint": 320,
        "depreciation_rate": 0.105
    },
    {
        "model_id": "honda-civic",
        "make": "Honda",
        "model": "Civic",
        "make_slug": "honda",
        "model_slug": "civic",
        "min_year": 2020,
        "max_year": 2023,
        "full_model": "Civic Touring / Sport",
        "reliability": 89,
        "tech": 85,
        "winter": 80,
        "baseline_2021_value": 22400,
        "target_deal_price": 19900,
        "fuel_l100km": 6.9,
        "annual_maint": 520,
        "depreciation_rate": 0.082
    },
    {
        "model_id": "mazda-cx5",
        "make": "Mazda",
        "model": "CX-5",
        "make_slug": "mazda",
        "model_slug": "cx-5",
        "min_year": 2020,
        "max_year": 2024,
        "full_model": "CX-5 GS / GT (AWD)",
        "reliability": 91,
        "tech": 83,
        "winter": 91,
        "baseline_2021_value": 24800,
        "target_deal_price": 21400,
        "fuel_l100km": 8.8,
        "annual_maint": 640,
        "depreciation_rate": 0.092
    },
    {
        "model_id": "toyota-prius-prime",
        "make": "Toyota",
        "model": "Prius",
        "make_slug": "toyota",
        "model_slug": "prius-prime",
        "min_year": 2020,
        "max_year": 2023,
        "full_model": "Prius Prime / Corolla Hybrid",
        "reliability": 96,
        "tech": 84,
        "winter": 82,
        "baseline_2021_value": 24600,
        "target_deal_price": 21800,
        "fuel_l100km": 4.3,
        "annual_maint": 450,
        "depreciation_rate": 0.075
    },
    {
        "model_id": "subaru-crosstrek",
        "make": "Subaru",
        "model": "Crosstrek",
        "make_slug": "subaru",
        "model_slug": "crosstrek",
        "min_year": 2021,
        "max_year": 2024,
        "full_model": "Crosstrek Outdoor 2.5L AWD",
        "reliability": 85,
        "tech": 83,
        "winter": 96,
        "baseline_2021_value": 23900,
        "target_deal_price": 21200,
        "fuel_l100km": 7.9,
        "annual_maint": 720,
        "depreciation_rate": 0.085
    },
    {
        "model_id": "hyundai-kona-ev",
        "make": "Hyundai",
        "model": "Kona",
        "make_slug": "hyundai",
        "model_slug": "kona-electric",
        "min_year": 2021,
        "max_year": 2023,
        "full_model": "Kona Electric Ultimate (Heat Pump)",
        "reliability": 82,
        "tech": 90,
        "winter": 83,
        "baseline_2021_value": 24900,
        "target_deal_price": 21500,
        "fuel_l100km": 1.7,
        "annual_maint": 350,
        "depreciation_rate": 0.11
    },
    {
        "model_id": "toyota-camry-hybrid",
        "make": "Toyota",
        "model": "Camry",
        "make_slug": "toyota",
        "model_slug": "camry",
        "min_year": 2020,
        "max_year": 2023,
        "full_model": "Camry Hybrid SE / LE",
        "reliability": 95,
        "tech": 85,
        "winter": 82,
        "baseline_2021_value": 26800,
        "target_deal_price": 23600,
        "fuel_l100km": 5.1,
        "annual_maint": 490,
        "depreciation_rate": 0.078
    },
    {
        "model_id": "toyota-rav4-hybrid",
        "make": "Toyota",
        "model": "RAV4",
        "make_slug": "toyota",
        "model_slug": "rav4",
        "min_year": 2019,
        "max_year": 2023,
        "full_model": "RAV4 Hybrid LE/XLE (AWD)",
        "reliability": 94,
        "tech": 86,
        "winter": 90,
        "baseline_2021_value": 31200,
        "target_deal_price": 27600,
        "fuel_l100km": 6,
        "annual_maint": 540,
        "depreciation_rate": 0.072
    },
    {
        "model_id": "hyundai-ioniq5",
        "make": "Hyundai",
        "model": "Ioniq",
        "make_slug": "hyundai",
        "model_slug": "ioniq-5",
        "min_year": 2022,
        "max_year": 2024,
        "full_model": "Ioniq 5 Preferred Long Range",
        "reliability": 81,
        "tech": 96,
        "winter": 87,
        "baseline_2021_value": 32500,
        "target_deal_price": 28200,
        "fuel_l100km": 1.9,
        "annual_maint": 380,
        "depreciation_rate": 0.115
    }
]

BLACKLIST_KEYWORDS = [
    "rebuilt", "salvage", "vga", "accidenté", "pour pièces", "damaged",
    "nissan rogue", "hyundai / kia tucson", "ford escape", "volkswagen tiguan"
]

UNAVAILABLE_PATTERNS = [
    "cette annonce n'est plus disponible",
    "annonce expirée",
    "véhicule vendu",
    "this listing is no longer available",
    "listing has been removed",
    "page introuvable",
    "sorry, this vehicle is sold",
]

SEEN_FILE = "data/seen_listings.json"
DEALS_OUTPUT_FILE = "data/outaouais_best_deals.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CA,fr;q=0.9,en-CA;q=0.8"
}


def compute_quebec_monthly_tco(price: float, market_val: float, model_cfg: dict) -> float:
    taxable_diff = max(0.0, price - CONFIG["current_car_trade_in"])
    taxes = taxable_diff * 0.14975
    annual_fuel = (CONFIG["annual_km"] / 100.0) * model_cfg["fuel_l100km"] * CONFIG["gas_price_qc"]
    annual_ins_saaq = (160 * 12) + 285
    five_yr_end_val = market_val * ((1 - model_cfg["depreciation_rate"]) ** 5)
    five_yr_depreciation = (price - five_yr_end_val) + taxes
    five_yr_total = five_yr_depreciation + (annual_fuel + annual_ins_saaq + model_cfg["annual_maint"]) * 5
    return round(five_yr_total / 60.0, 2)


def score_listing(listing: dict, model_cfg: dict) -> dict:
    title_lower = listing["title"].lower()
    if any(bad in title_lower for bad in BLACKLIST_KEYWORDS):
        return None

    fair_value = float(model_cfg["baseline_2021_value"])
    discount_cad = max(0.0, fair_value - listing["price"])
    discount_pct = round((discount_cad / fair_value) * 100, 1)
    monthly_tco = compute_quebec_monthly_tco(listing["price"], fair_value, model_cfg)
    monthly_savings_vs_current = round(CONFIG["current_car_monthly_tco"] - monthly_tco, 2)

    quality_score = round(
        model_cfg["reliability"] * 0.50 +
        model_cfg["tech"] * 0.30 +
        model_cfg["winter"] * 0.20, 1
    )
    discount_score = min(100, max(0, discount_pct * 5.2))
    deal_score = round(discount_score * 0.55 + quality_score * 0.45, 1)

    now_iso = datetime.utcnow().isoformat()
    return {
        **listing,
        "model_id": model_cfg["model_id"],
        "make": model_cfg["make"],
        "model": model_cfg["model"],
        "fair_market_value": fair_value,
        "discount_cad": discount_cad,
        "discount_pct": discount_pct,
        "est_monthly_tco_qc": monthly_tco,
        "monthly_delta_vs_current": monthly_savings_vs_current,
        "reliability_score": model_cfg["reliability"],
        "tech_score": model_cfg["tech"],
        "deal_score": deal_score,
        "status": "AVAILABLE",
        "last_verified": now_iso
    }


def extract_kijiji_individual_ads(model_cfg: dict) -> list:
    """
    Scrapes Kijiji across a 250km radius around Gatineau (J8P1P3)
    (covering Outaouais, Ottawa/Eastern ON, Laurentians, Laval & Greater Montreal)
    and extracts DIRECT individual vehicle ad URLs (/v-autos-camions/... or /v-cars-trucks/...).
    """
    listings = []
    radius_km = float(CONFIG["radius_km"])
    search_urls = [
        f"https://www.kijiji.ca/b-autos-camions/gatineau/{model_cfg['make_slug']}-{model_cfg['model_slug']}/k0c174l1700185?radius={radius_km}&address={CONFIG['postal_code']}&ll=45.476545,-75.701272&price=7000__{CONFIG['max_price_cad']}&kilometers=__{CONFIG['max_odometer_km']}",
        f"https://www.kijiji.ca/b-cars-trucks/ottawa-gatineau-area/{model_cfg['make_slug']}-{model_cfg['model_slug']}/k0c174l1700184?radius={radius_km}&address={CONFIG['postal_code']}&ll=45.476545,-75.701272&price=7000__{CONFIG['max_price_cad']}&kilometers=__{CONFIG['max_odometer_km']}",
        f"https://www.kijiji.ca/b-autos-camions/grand-montreal/{model_cfg['make_slug']}-{model_cfg['model_slug']}/k0c174l80002?price=7000__{CONFIG['max_price_cad']}&kilometers=__{CONFIG['max_odometer_km']}"
    ]

    for s_url in search_urls:
        try:
            resp = requests.get(s_url, headers=HEADERS, timeout=14)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Try Next.js __NEXT_DATA__ Apollo State for exact individual vehicle ads
            next_data_tag = soup.find("script", id="__NEXT_DATA__")
            if next_data_tag and next_data_tag.string:
                raw_json = json.loads(next_data_tag.string)
                apollo = (
                    raw_json.get("props", {})
                    .get("pageProps", {})
                    .get("__APOLLO_STATE__", {})
                )
                for key, val in apollo.items():
                    if not isinstance(val, dict):
                        continue
                    ad_url = val.get("url") or val.get("vipUrl") or val.get("seoUrl") or ""
                    if ("/v-autos-camions/" in ad_url or "/v-cars-trucks/" in ad_url):
                        full_url = ad_url if ad_url.startswith("http") else f"https://www.kijiji.ca{ad_url}"
                        title = val.get("title", "")
                        if model_cfg["make"].lower() not in title.lower():
                            continue
                        # Price in cents or dollars
                        price_obj = val.get("price", {})
                        raw_amt = price_obj.get("amount", 0) if isinstance(price_obj, dict) else 0
                        price = float(raw_amt / 100.0) if raw_amt > 100000 else float(raw_amt or 0)
                        if not (6500 <= price <= CONFIG["max_price_cad"]):
                            continue

                        year_match = re.search(r"\b(201[8-9]|202[0-6])\b", title)
                        year = int(year_match.group(1)) if year_match else 2021
                        if not (model_cfg["min_year"] - 1 <= year <= model_cfg["max_year"] + 1):
                            continue

                        listings.append({
                            "id": f"kijiji-{val.get('id', int(price))}",
                            "title": title,
                            "year": year,
                            "price": round(price, 0),
                            "km": 62000,
                            "location": "Gatineau / Ottawa",
                            "source": "Kijiji Direct Ad",
                            "url": full_url
                        })

            # 2. Fallback HTML card parser for <a href="/v-autos-camions/...">
            for a_tag in soup.select('a[href*="/v-autos-camions/"], a[href*="/v-cars-trucks/"]'):
                href = a_tag.get("href", "")
                if not href or "/v-" not in href:
                    continue
                full_url = href if href.startswith("http") else f"https://www.kijiji.ca{href.split('?')[0]}"
                if any(existing["url"] == full_url for existing in listings):
                    continue

                card = a_tag.find_parent(["section", "li", "article", "div"])
                card_text = card.get_text(" ", strip=True) if card else a_tag.get_text(" ", strip=True)
                title = a_tag.get_text(" ", strip=True) or card_text[:70]
                if model_cfg["make"].lower() not in title.lower() and model_cfg["model"].lower() not in title.lower():
                    continue

                price_match = re.search(r"\$\s*([0-9]{2}[,\s]?[0-9]{3})", card_text)
                if not price_match:
                    continue
                price = float(re.sub(r"[^0-9]", "", price_match.group(1)))
                if not (6500 <= price <= CONFIG["max_price_cad"]):
                    continue

                km_match = re.search(r"([0-9]{2,3}[,\s]?[0-9]{3})\s*km", card_text, re.IGNORECASE)
                km = int(re.sub(r"[^0-9]", "", km_match.group(1))) if km_match else 64000
                if km > CONFIG["max_odometer_km"]:
                    continue

                year_match = re.search(r"\b(201[8-9]|202[0-6])\b", title)
                year = int(year_match.group(1)) if year_match else 2021

                listings.append({
                    "id": full_url.split("/")[-1],
                    "title": title[:85],
                    "year": year,
                    "price": price,
                    "km": km,
                    "location": "Gatineau / Outaouais, QC",
                    "source": "Kijiji Direct Ad",
                    "url": full_url
                })
                if len(listings) >= 5:
                    break
        except Exception as exc:
            print(f"[!] Kijiji direct ad scan warning ({model_cfg['make']}): {exc}")

        if listings:
            break

    return listings


def extract_autohebdo_individual_ads(model_cfg: dict) -> list:
    """
    Scrapes AutoHebdo.net / AutoTrader.ca for direct '/a/{make}/{model}/...' vehicle ads.
    """
    listings = []
    search_url = (
        f"https://www.autohebdo.net/autos/{model_cfg['make_slug']}/{model_cfg['model_slug']}/qc/gatineau/"
        f"?rcp=20&rcs=0&srt=3&yRng={model_cfg['min_year']}%2C{model_cfg['max_year']}"
        f"&pRng=7000%2C{CONFIG['max_price_cad']}&oRng=0%2C{CONFIG['max_odometer_km']}"
        f"&prx={CONFIG['radius_km']}&prv=Quebec&loc={CONFIG['postal_code']}&hprc=True&wcp=True&sts=Occasion"
    )
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=14)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.select('a[href*="/a/"]'):
                href = a_tag.get("href", "")
                if f"/a/{model_cfg['make_slug']}/" not in href.lower():
                    continue
                full_url = href if href.startswith("http") else f"https://www.autohebdo.net{href.split('?')[0]}"
                if any(existing["url"] == full_url for existing in listings):
                    continue

                card = a_tag.find_parent(["div", "article", "li"])
                card_text = card.get_text(" ", strip=True) if card else ""
                title = a_tag.get_text(" ", strip=True) or f"2021 {model_cfg['make']} {model_cfg['full_model']}"

                price_match = re.search(r"([0-9]{2}[\s,][0-9]{3})\s*\$", card_text) or re.search(r"\$\s*([0-9]{2}[\s,][0-9]{3})", card_text)
                if not price_match:
                    continue
                price = float(re.sub(r"[^0-9]", "", price_match.group(1)))
                if not (6500 <= price <= CONFIG["max_price_cad"]):
                    continue

                km_match = re.search(r"([0-9]{2,3}[\s,][0-9]{3})\s*km", card_text, re.IGNORECASE)
                km = int(re.sub(r"[^0-9]", "", km_match.group(1))) if km_match else 60000

                year_match = re.search(r"\b(201[8-9]|202[0-6])\b", title)
                year = int(year_match.group(1)) if year_match else 2021

                listings.append({
                    "id": full_url,
                    "title": title[:85],
                    "year": year,
                    "price": price,
                    "km": km,
                    "location": "Gatineau / Outaouais, QC",
                    "source": "AutoHebdo Direct Ad",
                    "url": full_url
                })
                if len(listings) >= 4:
                    break
    except Exception as exc:
        print(f"[!] AutoHebdo direct ad scan warning ({model_cfg['make']}): {exc}")
    return listings


def verify_listing_still_available(deal: dict) -> bool:
    url = deal.get("url", "")
    # Automatically prune old generic search-page fallback URLs so only real car ads remain
    if not url or "/?rcp=" in url or "/k0c174" in url:
        return False
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code in (404, 410):
            return False
        if "/b-autos-camions/" in resp.url or "/b-cars-trucks/" in resp.url:
            return False  # Redirected back to general search page = ad expired
        page_text = resp.text.lower()
        if any(marker in page_text for marker in UNAVAILABLE_PATTERNS):
            return False
        return True
    except Exception:
        return True


def main():
    os.makedirs("data", exist_ok=True)
    seen = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen = set(json.load(f))
        except Exception:
            seen = set()

    previous_deals = {}
    if os.path.exists(DEALS_OUTPUT_FILE):
        try:
            with open(DEALS_OUTPUT_FILE, "r") as f:
                for d in json.load(f):
                    if "id" in d:
                        previous_deals[d["id"]] = d
        except Exception:
            pass

    active_deals = {}
    for model_cfg in APPROVED_MODELS:
        found = extract_kijiji_individual_ads(model_cfg) + extract_autohebdo_individual_ads(model_cfg)
        print(f"[*] Found {len(found)} direct vehicle ads for {model_cfg['make']} {model_cfg['full_model']}")
        for item in found:
            scored = score_listing(item, model_cfg)
            if scored:
                active_deals[scored["id"]] = scored
                seen.add(scored["id"])
        time.sleep(1)

    for old_id, old_deal in previous_deals.items():
        if old_id not in active_deals:
            if verify_listing_still_available(old_deal):
                active_deals[old_id] = old_deal

    sorted_deals = sorted(active_deals.values(), key=lambda x: x["deal_score"], reverse=True)
    with open(DEALS_OUTPUT_FILE, "w") as f:
        json.dump(sorted_deals, f, indent=2)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)
    print(f"[+] Saved {len(sorted_deals)} direct individual car ads to {DEALS_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
