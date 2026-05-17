from bs4 import BeautifulSoup
import requests
import json
import re

# ── URLs ──────────────────────────────────────────────────────────────────────
URLS = {
    "stocks":       "https://groww.in/pricing/stocks",
    "fno":          "https://groww.in/pricing/futures-and-options",
    "mutual_funds": "https://groww.in/pricing/mutual-funds",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Noise patterns to drop ────────────────────────────────────────────────────
# Matches nav links, fund names, stock tickers, legal disclaimers, etc.
NOISE_PATTERNS = [
    r"^(Stocks|Mutual Funds|F&O|ETF|IPO|Commodities|Groww Terminal)",  # nav
    r"Groww (Arbitrage|ELSS|Banking|Gold|Short|Aggressive|Nifty|Liquid|"
    r"Dynamic|Multicap|Large|Overnight|Value|Silver)",                 # fund names
    r"(NIFTY|SENSEX|BSE|NSE|MCX)\s+\d",                               # index tickers
    r"Tata Motors|HDFC|SBI|Infosys|Wipro|ICICI|Reliance|Adani",       # stock names
    r"Calculator|SIP calculator|Brokerage calculator",                  # tool links
    r"Mutual fund investments are subject",                             # disclaimers
    r"Investment in Securities Market are subject",
    r"Groww objectively evaluates",
    r"Groww Invest Tech Pvt",                                           # legal boilerplate
    r"KYC is a one time",
    r"Prevent Unauthori[sz]ed",
    r"SEBI SCORES",
    r"issued in the interest of",
    r"Vaishnavi Tech Park",
    r"©\s*20\d\d",
    r"^(A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z)\s",   # alphabet nav
]

_noise_re = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)


def is_noise(text: str) -> bool:
    return bool(_noise_re.search(text))


def clean(text: str) -> str:
    return " ".join(text.split()).strip()


# ── Pricing signal: must contain ₹ or % or 'charge' / 'fee' ─────────────────
_pricing_re = re.compile(r"[₹%]|charge|fee|brokerage|tax|duty|penalty|GST|STT|MTF",
                         re.IGNORECASE)


def is_pricing(text: str) -> bool:
    return bool(_pricing_re.search(text))


# ── Scrape a single table ─────────────────────────────────────────────────────
def scrape_table(table_tag):
    rows = []
    for tr in table_tag.find_all("tr"):
        cells = [clean(td.get_text(" ", strip=True))
                 for td in tr.find_all(["th", "td"])]
        cells = [c for c in cells if c]
        if cells:
            rows.append(cells)
    return rows or None


# ── Extract pricing divs (the ₹/% cards) ─────────────────────────────────────
def scrape_pricing_items(soup):
    seen, items = set(), []
    for div in soup.find_all("div"):
        # skip deeply nested containers (likely wrappers)
        if len(div.find_all("div")) > 4:
            continue
        text = clean(div.get_text(" ", strip=True))
        if (
            10 < len(text) < 300
            and is_pricing(text)
            and not is_noise(text)
            and text not in seen
        ):
            seen.add(text)
            items.append(text)
    return items


# ── Extract tables ────────────────────────────────────────────────────────────
def scrape_tables(soup):
    tables = []
    for tbl in soup.find_all("table"):
        rows = scrape_table(tbl)
        if rows:
            tables.append(rows)
    return tables


# ── Main ──────────────────────────────────────────────────────────────────────
def fee_scraper(output_path="./data/groww_pricing.json"):
    result = {}

    for key, url in URLS.items():
        print(f"Scraping {key}: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  ERROR: {e}")
            result[key] = {"url": url, "error": str(e)}
            continue

        soup = BeautifulSoup(resp.text, "lxml")

        result[key] = {
            "url": url,
            "pricing_items": scrape_pricing_items(soup),
            "tables": scrape_tables(soup),
        }

        print(f"  → {len(result[key]['pricing_items'])} items, "
              f"{len(result[key]['tables'])} tables")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")
    return result


if __name__ == "__main__":
    fee_scraper()