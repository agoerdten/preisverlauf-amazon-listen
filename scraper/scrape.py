"""Ruft Amazon.de-Produktseiten und -Listen ab und schreibt den Tagespreis in docs/data/."""

import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "tracking.json"
DATA_DIR = ROOT / "docs" / "data"
PRODUCTS_DIR = DATA_DIR / "products"
INDEX_PATH = DATA_DIR / "index.json"

MAX_HISTORY_LENGTH = 365
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

ASIN_PATTERN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})", re.IGNORECASE)

# Selektoren wie in content-scripts/amazon.js der Chrome-Extension, erster Treffer gewinnt.
PRICE_SELECTORS = [
    "#corePrice_feature_div .a-price .a-offscreen",
    "#corePriceDisplay_desktop_feature_div .a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#corePrice_desktop .a-price .a-offscreen",
]


def extract_asin(url):
    match = ASIN_PATTERN.search(url)
    return match.group(1).upper() if match else None


def parse_price_string(text):
    cleaned = re.sub(r"[^0-9,.-]", "", text)
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.RequestException as error:
        print(f"  [WARN] Abruf fehlgeschlagen für {url}: {error}")
        return None


def extract_product_from_page(html, url):
    asin = extract_asin(url)
    if not asin:
        print(f"  [WARN] Keine ASIN in URL erkennbar: {url}")
        return None

    soup = BeautifulSoup(html, "lxml")

    price_text = None
    for selector in PRICE_SELECTORS:
        element = soup.select_one(selector)
        if element and element.get_text(strip=True):
            price_text = element.get_text(strip=True)
            break

    if price_text is None:
        print(f"  [WARN] Kein Preis-Element gefunden für {asin} (z.B. ausverkauft) – übersprungen.")
        return None

    price = parse_price_string(price_text)
    if price is None:
        print(f"  [WARN] Preis konnte nicht geparst werden ('{price_text}') für {asin} – übersprungen.")
        return None

    title_element = soup.select_one("#productTitle")
    title = title_element.get_text(strip=True) if title_element else soup.title.get_text(strip=True) if soup.title else asin

    return {"asin": asin, "title": title, "url": url, "currency": "EUR", "price": price}


def extract_products_from_list_page(html, list_url):
    # Selektoren gegen eine echte, öffentlich geteilte Amazon-Liste verifiziert:
    # jedes Item ist ein <li class="... g-item-sortable"> mit der ASIN in einem
    # verschachtelten [data-csa-c-item-type="asin"]-Element und dem Preis direkt
    # als data-price-Attribut (Punkt-Dezimalzahl, NICHT über parse_price_string
    # laufen lassen – das würde den Dezimalpunkt fälschlich als Tausendertrennzeichen entfernen).
    soup = BeautifulSoup(html, "lxml")
    products = []

    for item in soup.select("li.g-item-sortable"):
        price_attr = item.get("data-price")
        if not price_attr:
            continue
        try:
            price = float(price_attr)
        except ValueError:
            continue

        asin = None
        asin_container = item.select_one('[data-csa-c-item-type="asin"]')
        if asin_container:
            asin = asin_container.get("data-csa-c-item-id", "").strip().upper()
        if not asin:
            params = item.get("data-reposition-action-params", "")
            match = re.search(r"ASIN:([A-Z0-9]{10})", params, re.IGNORECASE)
            if match:
                asin = match.group(1).upper()
        if not asin:
            continue

        title_link = item.select_one('a[id^="itemName_"]')
        title = title_link.get_text(strip=True) if title_link else asin

        products.append(
            {
                "asin": asin,
                "title": title,
                "url": f"https://www.amazon.de/dp/{asin}",
                "currency": "EUR",
                "price": price,
            }
        )

    if not products:
        print(f"  [WARN] Keine Produkte auf Listen-Seite gefunden: {list_url} (Selektoren prüfen!)")

    return products


def today_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_product_entry(asin):
    path = PRODUCTS_DIR / f"{asin}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_product_entry(entry):
    path = PRODUCTS_DIR / f"{entry['productId']}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")


def update_product_entry(product):
    asin = product["asin"]
    entry = load_product_entry(asin)
    today = today_iso()

    if entry is None:
        entry = {
            "platform": "amazon.de",
            "productId": asin,
            "title": product["title"],
            "url": product["url"],
            "currency": product["currency"],
            "history": [],
        }

    entry["title"] = product["title"]
    entry["url"] = product["url"]

    history = entry["history"]
    if history and history[-1]["date"] == today:
        history[-1]["price"] = product["price"]
    else:
        history.append({"date": today, "price": product["price"]})

    if len(history) > MAX_HISTORY_LENGTH:
        entry["history"] = history[-MAX_HISTORY_LENGTH:]

    entry["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    save_product_entry(entry)
    return entry


def rebuild_index(entries):
    index = {
        "products": [
            {"productId": e["productId"], "title": e["title"], "url": e["url"], "currency": e["currency"]}
            for e in entries
        ]
    }
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def gather_products(config):
    products_by_asin = {}

    for list_url in config.get("lists", []):
        print(f"Liste abrufen: {list_url}")
        html = fetch(list_url)
        time.sleep(random.uniform(2, 6))
        if html is None:
            continue
        for product in extract_products_from_list_page(html, list_url):
            products_by_asin[product["asin"]] = product

    for product_url in config.get("products", []):
        asin = extract_asin(product_url)
        if asin and asin in products_by_asin:
            continue
        print(f"Produktseite abrufen: {product_url}")
        html = fetch(product_url)
        time.sleep(random.uniform(2, 6))
        if html is None:
            continue
        product = extract_product_from_page(html, product_url)
        if product:
            products_by_asin[product["asin"]] = product

    return list(products_by_asin.values())


def main():
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    products = gather_products(config)

    if not products:
        print("Keine Produkte gefunden/konfiguriert – nichts zu tun.")
        return

    entries = [update_product_entry(product) for product in products]
    rebuild_index(entries)
    print(f"Fertig: {len(entries)} Produkt(e) aktualisiert.")


if __name__ == "__main__":
    main()
