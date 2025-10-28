import re
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup

BASE = "https://{subdomain}.deposits.org"

# Простая HTML-выгребалка ставок депозитов и кредитов с deposits.org.
# ВАЖНО: HTML может меняться. Код сделан максимально устойчивым, но иногда потребуется доработка селекторов.
#
# Страницы продуктов обычно:
#   - {country}/deposits/
#   - {country}/personal-loan/
#   - {country}/home-loans/  (ипотека)
#   - {country}/car-loans/
#
# Мы пытаемся вытянуть название банка/продукта и ставку (%).
#
async def fetch_html(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def parse_rate_from_text(text: str) -> Optional[float]:
    # Ищем число вида 3.45% или 3,45%
    m = re.search(r"(\d+[.,]?\d*)\s*%", text)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))

def normalize_country(country: str) -> str:
    return country.lower().strip().replace(" ", "-")

async def list_deposit_offers(client: httpx.AsyncClient, country: str) -> List[Dict]:
    """Возвращает список предложений по депозитам с полями:
       { country, bank, product, apy, term_months, url }
    """
    country_slug = normalize_country(country)
    subdomain = country_slug if country_slug not in ("world",) else "www"
    url = BASE.format(subdomain=subdomain) + f"/{country_slug}/deposits/"
    html = await fetch_html(client, url)
    offers = []
    if not html:
        return offers
    soup = BeautifulSoup(html, "lxml")
    # Кажется, таблицы/карточки содержат ставки в элементах с %
    for card in soup.select("a, div, li, tr"):
        text = card.get_text(" ", strip=True)
        if not text or "%" not in text:
            continue
        apy = parse_rate_from_text(text)
        if not apy:
            continue
        # Простейшее выделение банка/продукта из текста
        bank = None
        product = None
        # эвристика: до процента часто идёт название продукта или банка
        words = text.split()
        bank = words[0] if words else None
        product = " ".join(words[:8]) if words else None
        offers.append({
            "country": country_slug,
            "bank": bank,
            "product": product,
            "apy": apy,
            "term_months": None,
            "url": url
        })
    # Убираем явные дубли по (bank, apy)
    uniq = {}
    for o in offers:
        key = (o["bank"], o["apy"])
        if key not in uniq:
            uniq[key] = o
    return list(uniq.values())

async def list_loan_offers(client: httpx.AsyncClient, country: str) -> List[Dict]:
    """Возвращает список кредитных предложений с полями:
       { country, bank, product, apr, url, loan_type }
    """
    country_slug = normalize_country(country)
    subdomain = country_slug if country_slug not in ("world",) else "www"
    loan_paths = [
        "personal-loan",
        "home-loans",
        "car-loans"
    ]
    offers = []
    for path in loan_paths:
        url = BASE.format(subdomain=subdomain) + f"/{country_slug}/{path}/"
        html = await fetch_html(client, url)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for card in soup.select("a, div, li, tr"):
            text = card.get_text(" ", strip=True)
            if not text or "%" not in text:
                continue
            apr = parse_rate_from_text(text)
            if not apr:
                continue
            words = text.split()
            bank = words[0] if words else None
            product = " ".join(words[:8]) if words else None
            offers.append({
                "country": country_slug,
                "bank": bank,
                "product": product,
                "apr": apr,
                "url": url,
                "loan_type": path
            })
    # Убираем явные дубли
    uniq = {}
    for o in offers:
        key = (o["loan_type"], o["bank"], o.get("apr"))
        if key not in uniq:
            uniq[key] = o
    return list(uniq.values())
