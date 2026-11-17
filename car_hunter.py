#!/usr/bin/env python3
"""
Outaouais Car Deal Hunter & True Cost of Ownership (TCO) Scorer
Region: Gatineau (QC) & Ottawa (ON) — Postal Code: J8P1P3 (75km radius)
Reliability Engine powered by 4 sources:
  1. Consumer Reports (30% weight)
  2. AutoReliability.index (25% weight)
  3. iSeeCars.com (25% weight)
  4. CarComplaints.com (20% weight)

LIVE AVAILABILITY SYNC:
Every time this script runs, it re-verifies every previously saved deal in
data/outaouais_best_deals.json. If a listing is sold, expired, or removed (404/vendu),
it is automatically deleted so your JSON file only contains currently available cars.
"""

import json
import os
import re
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. USER TCO & 4-SOURCE RELIABILITY CONFIG
# ==========================================
CONFIG = {
    "postal_code": "J8P1P3",
    "radius_km": 75,
    "max_price_cad": 28000,
    "max_odometer_km": 90000,
    "min_reliability_score": 80,
    "min_tech_score": 75,
    "min_winter_score": 75,
    "reliability_source_weights": {
        "consumer_reports": 30,
        "auto_reliability_index": 25,
        "iseecars": 25,
        "car_complaints": 20,
    },
    "current_car_monthly_tco": 646,
    "current_car_trade_in": 24060,
    "annual_km": 13000,
    "gas_price_qc": 1.62,
    "qc_tax_multiplier": 1.14975,  # GST 5% + QST 9.975%
}

# Approved models with 4-Source Reliability (Consumer Reports, AutoReliability.index, iSeeCars, CarComplaints)
APPROVED_MODELS = [
    {
        "make": "Toyota",
        "model": "Corolla",
        "reliability": 95,
        "reliability_sources": {
            "consumer_reports": 93,
            "auto_reliability_index": 97,
            "iseecars": 93,
            "car_complaints": 96,
            "car_complaints_badge": "Seal of Awesome (2020–2023)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/toyota/corolla/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Toyota%20Corolla",
            "iSeeCars": "https://www.iseecars.com/toyota-corolla",
            "carComplaints": "https://www.carcomplaints.com/Toyota/Corolla/"
        },
        "tech": 81,
        "winter": 80,
        "baseline_2021_value": 20900,
        "fuel_l100km": 6.7,
        "annual_maint": 460,
        "depreciation_rate": 0.078
    },
    {
        "make": "Mazda",
        "model": "Mazda3",
        "reliability": 90,
        "reliability_sources": {
            "consumer_reports": 89,
            "auto_reliability_index": 92,
            "iseecars": 87,
            "car_complaints": 91,
            "car_complaints_badge": "Seal of Pretty Good"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/mazda/mazda3/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Mazda%203",
            "iSeeCars": "https://www.iseecars.com/mazda-mazda3",
            "carComplaints": "https://www.carcomplaints.com/Mazda/MAZDA3/"
        },
        "tech": 86,
        "winter": 88,
        "baseline_2021_value": 22200,
        "fuel_l100km": 7.9,
        "annual_maint": 540,
        "depreciation_rate": 0.088
    },
    {
        "make": "Chevrolet",
        "model": "Bolt",
        "reliability": 84,
        "reliability_sources": {
            "consumer_reports": 81,
            "auto_reliability_index": 85,
            "iseecars": 83,
            "car_complaints": 88,
            "car_complaints_badge": "Low Powertrain Complaints (Post-2022 Pack)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/chevrolet/bolt-euv/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Chevrolet%20Bolt",
            "iSeeCars": "https://www.iseecars.com/chevrolet-bolt-euv",
            "carComplaints": "https://www.carcomplaints.com/Chevrolet/Bolt_EUV/"
        },
        "tech": 89,
        "winter": 80,
        "baseline_2021_value": 23800,
        "fuel_l100km": 1.8,
        "annual_maint": 320,
        "depreciation_rate": 0.105
    },
    {
        "make": "Honda",
        "model": "Civic",
        "reliability": 89,
        "reliability_sources": {
            "consumer_reports": 86,
            "auto_reliability_index": 91,
            "iseecars": 92,
            "car_complaints": 87,
            "car_complaints_badge": "Low Severity (Watch A/C Condenser)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/honda/civic/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Honda%20Civic",
            "iSeeCars": "https://www.iseecars.com/honda-civic",
            "carComplaints": "https://www.carcomplaints.com/Honda/Civic/"
        },
        "tech": 85,
        "winter": 80,
        "baseline_2021_value": 22400,
        "fuel_l100km": 6.9,
        "annual_maint": 520,
        "depreciation_rate": 0.082
    },
    {
        "make": "Mazda",
        "model": "CX-5",
        "reliability": 91,
        "reliability_sources": {
            "consumer_reports": 91,
            "auto_reliability_index": 93,
            "iseecars": 88,
            "car_complaints": 92,
            "car_complaints_badge": "Seal of Awesome (2020+)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/mazda/cx-5/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Mazda%20CX-5",
            "iSeeCars": "https://www.iseecars.com/mazda-cx-5",
            "carComplaints": "https://www.carcomplaints.com/Mazda/CX-5/"
        },
        "tech": 83,
        "winter": 91,
        "baseline_2021_value": 24800,
        "fuel_l100km": 8.8,
        "annual_maint": 640,
        "depreciation_rate": 0.092
    },
    {
        "make": "Toyota",
        "model": "Prius",
        "reliability": 96,
        "reliability_sources": {
            "consumer_reports": 95,
            "auto_reliability_index": 98,
            "iseecars": 95,
            "car_complaints": 97,
            "car_complaints_badge": "Seal of Awesome (#1 Hybrid)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/toyota/prius-prime/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Toyota%20Prius",
            "iSeeCars": "https://www.iseecars.com/toyota-prius-prime",
            "carComplaints": "https://www.carcomplaints.com/Toyota/Prius_Prime/"
        },
        "tech": 84,
        "winter": 82,
        "baseline_2021_value": 24600,
        "fuel_l100km": 4.3,
        "annual_maint": 450,
        "depreciation_rate": 0.075
    },
    {
        "make": "Subaru",
        "model": "Crosstrek",
        "reliability": 85,
        "reliability_sources": {
            "consumer_reports": 87,
            "auto_reliability_index": 83,
            "iseecars": 84,
            "car_complaints": 86,
            "car_complaints_badge": "Seal of Pretty Good (2021+)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/subaru/crosstrek/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Subaru%20Crosstrek",
            "iSeeCars": "https://www.iseecars.com/subaru-crosstrek",
            "carComplaints": "https://www.carcomplaints.com/Subaru/Crosstrek/"
        },
        "tech": 83,
        "winter": 96,
        "baseline_2021_value": 23900,
        "fuel_l100km": 7.9,
        "annual_maint": 720,
        "depreciation_rate": 0.085
    },
    {
        "make": "Hyundai",
        "model": "Kona",
        "reliability": 82,
        "reliability_sources": {
            "consumer_reports": 79,
            "auto_reliability_index": 84,
            "iseecars": 81,
            "car_complaints": 85,
            "car_complaints_badge": "Low Complaint Severity"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/hyundai/kona-electric/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Hyundai%20Kona",
            "iSeeCars": "https://www.iseecars.com/hyundai-kona-electric",
            "carComplaints": "https://www.carcomplaints.com/Hyundai/Kona_Electric/"
        },
        "tech": 90,
        "winter": 83,
        "baseline_2021_value": 24900,
        "fuel_l100km": 1.7,
        "annual_maint": 350,
        "depreciation_rate": 0.11
    },
    {
        "make": "Toyota",
        "model": "Camry",
        "reliability": 95,
        "reliability_sources": {
            "consumer_reports": 94,
            "auto_reliability_index": 96,
            "iseecars": 96,
            "car_complaints": 95,
            "car_complaints_badge": "Seal of Awesome (300k+ mi Top Ranked)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/toyota/camry/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Toyota%20Camry",
            "iSeeCars": "https://www.iseecars.com/toyota-camry-hybrid",
            "carComplaints": "https://www.carcomplaints.com/Toyota/Camry_Hybrid/"
        },
        "tech": 85,
        "winter": 82,
        "baseline_2021_value": 26800,
        "fuel_l100km": 5.1,
        "annual_maint": 490,
        "depreciation_rate": 0.078
    },
    {
        "make": "Toyota",
        "model": "RAV4",
        "reliability": 94,
        "reliability_sources": {
            "consumer_reports": 93,
            "auto_reliability_index": 95,
            "iseecars": 95,
            "car_complaints": 92,
            "car_complaints_badge": "Seal of Pretty Good (2021–2023)"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/toyota/rav4-hybrid/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Toyota%20RAV4",
            "iSeeCars": "https://www.iseecars.com/toyota-rav4-hybrid",
            "carComplaints": "https://www.carcomplaints.com/Toyota/RAV4_Hybrid/"
        },
        "tech": 86,
        "winter": 90,
        "baseline_2021_value": 31200,
        "fuel_l100km": 6,
        "annual_maint": 540,
        "depreciation_rate": 0.072
    },
    {
        "make": "Hyundai",
        "model": "Ioniq",
        "reliability": 81,
        "reliability_sources": {
            "consumer_reports": 78,
            "auto_reliability_index": 83,
            "iseecars": 81,
            "car_complaints": 83,
            "car_complaints_badge": "Watch ICCU Recall Campaign"
        },
        "research_links": {
            "consumerReports": "https://www.consumerreports.org/cars/hyundai/ioniq-5/",
            "autoReliabilityIndex": "https://www.autoreliabilityindex.com/?s=Hyundai%20Ioniq%205",
            "iSeeCars": "https://www.iseecars.com/hyundai-ioniq-5",
            "carComplaints": "https://www.carcomplaints.com/Hyundai/Ioniq_5/"
        },
        "tech": 96,
        "winter": 87,
        "baseline_2021_value": 32500,
        "fuel_l100km": 1.9,
        "annual_maint": 380,
        "depreciation_rate": 0.115
    }
]

# Hard-blocked models/keywords ("Cheap Traps" to ignore even if cheap)
BLACKLIST_KEYWORDS = [
    "rebuilt", "salvage", "vga", "accidenté", "pour pièces",
    "nissan rogue", "hyundai / kia tucson", "ford escape", "volkswagen tiguan"
]

# Markers indicating a car listing has been sold or removed
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
    "Accept-Language": "fr-CA,fr;q=0.9,en-CA;q=0.8"
}


def estimate_fair_market_value(model_cfg: dict, year: int, km: int) -> float:
    """Adjusts 2021 baseline market value for model year and odometer delta."""
    year_delta = year - 2021
    expected_km = max(25000, (2026 - year) * 18000)
    km_delta = km - expected_km

    year_adjusted = model_cfg["baseline_2021_value"] * ((1 + model_cfg["depreciation_rate"]) ** year_delta)
    km_adjustment = -km_delta * 0.085
    return max(6000.0, round(year_adjusted + km_adjustment, -2))


def compute_quebec_monthly_tco(price: float, market_val: float, model_cfg: dict) -> float:
    """Calculates 5-year True Monthly Cost in Gatineau, QC including trade-in tax credit."""
    taxable_diff = max(0.0, price - CONFIG["current_car_trade_in"])
    taxes = taxable_diff * 0.14975
    annual_fuel = (CONFIG["annual_km"] / 100.0) * model_cfg["fuel_l100km"] * CONFIG["gas_price_qc"]
    annual_ins_saaq = (165 * 12) + 285
    five_yr_end_val = market_val * ((1 - model_cfg["depreciation_rate"]) ** 5)

    five_yr_depreciation = (price - five_yr_end_val) + taxes
    five_yr_total = five_yr_depreciation + (annual_fuel + annual_ins_saaq + model_cfg["annual_maint"]) * 5
    return round(five_yr_total / 60.0, 2)


def score_listing(listing: dict, model_cfg: dict) -> dict:
    """Computes composite Deal Score & Switch-Now Verdict."""
    title_lower = listing["title"].lower()
    if any(bad in title_lower for bad in BLACKLIST_KEYWORDS):
        return None

    if (model_cfg["reliability"] < CONFIG["min_reliability_score"] or
        model_cfg["tech"] < CONFIG["min_tech_score"]):
        return None

    fair_value = estimate_fair_market_value(model_cfg, listing["year"], listing["km"])
    discount_cad = fair_value - listing["price"]
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

    verdict = "HOLD / PASS"
    if discount_pct >= 10 and monthly_savings_vs_current >= -35:
        verdict = "🔥 SWITCH NOW (STRONG DEAL)"
    elif discount_pct >= 6:
        verdict = "👀 NEGOTIATE TARGET"

    now_iso = datetime.utcnow().isoformat()
    return {
        **listing,
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
        "verdict": verdict,
        "status": "AVAILABLE",
        "found_at": listing.get("found_at", now_iso),
        "last_verified": now_iso
    }


def verify_listing_still_available(deal: dict) -> tuple[bool, float]:
    """
    Checks a previously saved deal's direct URL to confirm the car is still available.
    Returns (is_available, latest_price). If sold/404/expired, returns (False, price).
    """
    url = deal.get("url", "")
    if not url:
        return False, deal.get("price", 0)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code in (404, 410) or resp.status_code >= 500:
            return False, deal["price"]

        # Redirected to generic search results page means listing was removed
        if "/results" in resp.url or resp.url.rstrip("/").endswith("/cars"):
            return False, deal["price"]

        page_text = resp.text.lower()
        if any(marker in page_text for marker in UNAVAILABLE_PATTERNS):
            return False, deal["price"]

        # Also check if the seller lowered the price on the live page
        soup = BeautifulSoup(resp.text, "html.parser")
        latest_price = deal["price"]
        for script in soup.find_all("script", type="application/ld+json"):
            data = json.loads(script.string or "{}")
            if data.get("@type") == "Vehicle" or "offers" in data:
                live_price = float(data.get("offers", {}).get("price", 0))
                if 5000 < live_price <= CONFIG["max_price_cad"]:
                    latest_price = live_price
                    break

        return True, latest_price
    except Exception as exc:
        print(f"[!] Transient warning checking {url}: {exc}")
        return True, deal["price"]


def search_autotrader_outaouais(model_cfg: dict) -> list:
    """Queries AutoTrader.ca / AutoHebdo.net around Gatineau/Ottawa."""
    make = model_cfg["make"].lower()
    model = model_cfg["model"].lower()
    params = {
        "rcp": 25,
        "rcs": 0,
        "srt": 9,  # Sort by newest
        "yRng": "2019,2025",
        "pRng": f"8000,{CONFIG['max_price_cad']}",
        "oRng": f"0,{CONFIG['max_odometer_km']}",
        "prx": CONFIG["radius_km"],
        "loc": CONFIG["postal_code"],
        "hprc": "True",
        "wcp": "True",
        "sts": "Used"
    }
    url = f"https://www.autotrader.ca/cars/{make}/{model}/?{urllib.parse.urlencode(params)}"
    print(f"[*] Scanning Outaouais listings for {model_cfg['make']} {model_cfg['model']} -> {url}")
    listings = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            data = json.loads(script.string or "{}")
            if data.get("@type") == "Vehicle" or "offers" in data:
                price = float(data.get("offers", {}).get("price", 0))
                km = int(data.get("mileageFromOdometer", {}).get("value", 0))
                year = int(data.get("modelDate", 2021))
                if 5000 < price <= CONFIG["max_price_cad"] and 0 < km <= CONFIG["max_odometer_km"]:
                    listings.append({
                        "id": data.get("sku", data.get("url", "")),
                        "title": data.get("name", f"{year} {model_cfg['make']} {model_cfg['model']}"),
                        "year": year,
                        "price": price,
                        "km": km,
                        "url": data.get("offers", {}).get("url", url)
                    })
    except Exception as exc:
        print(f"[!] Warning scraping {make} {model}: {exc}")
    return listings


def send_webhook_notification(new_deals: list, removed_count: int):
    """Sends Discord notification when new high-scoring deals appear."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url or not new_deals:
        return
    lines = [
        f"🚗 **Outaouais Car Deal Hunter Sync** ({len(new_deals)} new deals | {removed_count} sold/expired removed)"
    ]
    for d in new_deals[:5]:
        lines.append(
            f"• **{d['title']}** — **${d['price']:,.0f}** (Market: ${d['fair_market_value']:,.0f} | **-{d['discount_pct']}%**)\n"
            f"  📍 {d['km']:,} km | Rel: {d['reliability_score']}/100 | Tech: {d['tech_score']}/100 | "
            f"QC TCO: ${d['est_monthly_tco_qc']}/mo | **{d['verdict']}**\n  <{d['url']}>"
        )
    requests.post(webhook_url, json={"content": "\n".join(lines)}, timeout=10)


def main():
    os.makedirs("data", exist_ok=True)
    seen = set()
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen = set(json.load(f))

    # 1. Load previously saved deals so we can verify if they are still available
    previous_deals_by_id = {}
    if os.path.exists(DEALS_OUTPUT_FILE):
        try:
            with open(DEALS_OUTPUT_FILE, "r") as f:
                for old_deal in json.load(f):
                    if "id" in old_deal:
                        previous_deals_by_id[old_deal["id"]] = old_deal
        except Exception as exc:
            print(f"[!] Could not read existing deals file: {exc}")

    model_cfg_map = {
        (m["make"], m["model"]): m for m in APPROVED_MODELS
    }

    active_deals_by_id = {}
    fresh_alerts = []

    # 2. Scan live search pages for new & currently active listings
    for model_cfg in APPROVED_MODELS:
        raw_listings = search_autotrader_outaouais(model_cfg)
        for item in raw_listings:
            prev = previous_deals_by_id.get(item["id"])
            if prev:
                item["found_at"] = prev.get("found_at")
            scored = score_listing(item, model_cfg)
            if not scored:
                continue
            if prev and scored["price"] < prev.get("price", scored["price"]):
                scored["price_drop_cad"] = prev["price"] - scored["price"]
            active_deals_by_id[scored["id"]] = scored

            if scored["id"] not in seen and scored["deal_score"] >= 75:
                fresh_alerts.append(scored)
                seen.add(scored["id"])
        time.sleep(2)

    # 3. Verify every previously saved deal not seen in Step 2; remove if sold/expired
    removed_count = 0
    for old_id, old_deal in previous_deals_by_id.items():
        if old_id in active_deals_by_id:
            continue  # Already confirmed active in fresh scan

        print(f"[*] Verifying availability of saved deal: {old_deal.get('title')}...")
        is_available, latest_price = verify_listing_still_available(old_deal)
        if not is_available:
            removed_count += 1
            print(f"[-] Removed sold/unavailable listing: {old_deal.get('title')} ({old_deal.get('url')})")
            continue

        # Still available: re-score in case price changed and keep in active list
        m_cfg = model_cfg_map.get((old_deal.get("make"), old_deal.get("model")))
        if m_cfg:
            old_deal["price"] = latest_price
            rescored = score_listing(old_deal, m_cfg)
            if rescored:
                active_deals_by_id[old_id] = rescored
        else:
            old_deal["last_verified"] = datetime.utcnow().isoformat()
            active_deals_by_id[old_id] = old_deal
        time.sleep(1)

    # 4. Save clean, up-to-date list of ONLY available deals
    all_active_sorted = sorted(
        active_deals_by_id.values(), key=lambda x: x["deal_score"], reverse=True
    )
    with open(DEALS_OUTPUT_FILE, "w") as f:
        json.dump(all_active_sorted, f, indent=2)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

    send_webhook_notification(fresh_alerts, removed_count)
    print(
        f"[+] Sync complete: {len(all_active_sorted)} available deals kept, "
        f"{removed_count} sold/unavailable deals removed, {len(fresh_alerts)} new alerts sent."
    )


if __name__ == "__main__":
    main()
