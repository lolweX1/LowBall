import re
import time
from typing import Callable, List, Dict, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--window-size=1400,1400")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def build_url(store: str, query: str, page: int = 1) -> str:
    query_text = quote(query, safe="")
    if store == "amazon":
        return f"https://www.amazon.com/s?k={query_text}&page={page}"
    if store == "alibaba":
        return f"https://www.alibaba.com/trade/search?SearchText={query_text}&page={page}"
    if store == "temu":
        return f"https://www.temu.com/search_result.html?search_key={query_text}"
    raise ValueError(f"Unsupported store: {store}")


def normalize_price(raw: Optional[str]) -> str:
    if not raw:
        return "N/A"
    text = re.sub(r"\s+", " ", raw).strip()
    if text.startswith("$"):
        return text
    match = re.search(r"\$?\d+(?:[.,]\d{1,2})?", text)
    if match:
        return f"${match.group(0).replace('$', '')}"
    return text or "N/A"


def normalize_rating(raw: Optional[str]) -> str:
    if not raw:
        return "N/A"
    text = re.sub(r"\s+", " ", raw).strip()
    if not text:
        return "N/A"
    return text


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def detect_blocker(html: str, store: str) -> Optional[str]:
    text = clean_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True)).lower()
    if not text:
        return None

    login_markers = [
        "sign in",
        "log in",
        "login",
        "please sign in",
        "create account",
        "verify your identity",
        "verify it’s you",
        "verify your account",
        "suspicious activity",
        "unusual traffic",
        "robot verification",
        "captcha",
        "challenge",
        "human verification",
        "security check",
        "access denied",
        "please try again later",
    ]

    if store == "temu" and any(marker in text for marker in ["login", "sign in", "captcha", "verify", "security check"]):
        return "Verification required"

    if any(marker in text for marker in login_markers):
        return "Verification required"

    return None


def parse_amazon(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, str]] = []

    candidate_cards = soup.select(
        "div[data-component-type='s-search-result'], div.s-result-item, li.s-result-item, div[data-asin]"
    )

    for card in candidate_cards:
        title_el = (
            card.select_one("h2 span")
            or card.select_one("h2")
            or card.select_one("h3")
            or card.select_one("a span")
            or card.select_one("a")
        )
        price_el = (
            card.select_one("span.a-price span.a-offscreen")
            or card.select_one("span.a-price")
            or card.select_one(".a-price-whole")
        )
        rating_el = (
            card.select_one("span.a-icon-alt")
            or card.select_one(".a-row .a-size-small")
            or card.select_one("span[aria-label*='out of']")
        )
        link_el = card.select_one("h2 a") or card.select_one("a.a-link-normal") or card.select_one("a")
        if not title_el:
            continue

        title = clean_text(title_el.get_text(" ", strip=True))
        if not title or len(title) < 3:
            continue

        price = normalize_price(price_el.get_text(" ", strip=True) if price_el else None)
        rating = normalize_rating(rating_el.get_text(" ", strip=True) if rating_el else None)
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = f"https://www.amazon.com{link}"
        products.append({"title": title, "price": price, "rating": rating, "link": link})

    if not products:
        for card in soup.select("a[href*='/dp/']"):
            title = clean_text(card.get_text(" ", strip=True))
            if title and len(title) > 3:
                products.append({"title": title, "price": "N/A", "rating": "N/A", "link": card.get("href", "")})

    return products


def parse_alibaba(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, str]] = []

    candidate_cards = soup.select(
        "div.search-card, .search-card-e-container, .organic-product, .item, .offer-card, a[href*='product']"
    )

    for card in candidate_cards:
        title_el = (
            card.select_one(".search-card-e-title")
            or card.select_one(".title")
            or card.select_one("h3")
            or card.select_one("a")
            or card.select_one("span")
        )
        price_el = (
            card.select_one(".price")
            or card.select_one(".search-card-e-price")
            or card.select_one("[class*='price']")
        )
        if not title_el:
            continue

        title = clean_text(title_el.get_text(" ", strip=True))
        if not title or len(title) < 3:
            continue

        price = normalize_price(price_el.get_text(" ", strip=True) if price_el else None)
        link_el = card.select_one("a")
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = f"https://www.alibaba.com{link}"
        products.append({"title": title, "price": price, "rating": "N/A", "link": link})

    return products


def parse_temu(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, str]] = []

    candidate_cards = soup.select("a[href*='goods'], a[href*='item'], a[href*='product'], div[class*='product']")
    for card in candidate_cards:
        title_el = card.select_one("span, div, h3")
        if not title_el:
            continue
        title = clean_text(title_el.get_text(" ", strip=True))
        if not title or len(title) < 5:
            continue
        price_el = card.select_one("[class*='price'], span")
        price = normalize_price(price_el.get_text(" ", strip=True) if price_el else None)
        link = card.get("href", "") or card.get("data-href", "")
        if link and not link.startswith("http"):
            link = f"https://www.temu.com{link}"
        products.append({"title": title, "price": price, "rating": "N/A", "link": link})

    if not products:
        for card in soup.select("a"):
            title = clean_text(card.get_text(" ", strip=True))
            if title and len(title) > 6 and "search" not in title.lower():
                products.append({"title": title, "price": "N/A", "rating": "N/A", "link": card.get("href", "")})

    return products


def parse_store_results(store: str, html: str) -> List[Dict[str, str]]:
    blocker = detect_blocker(html, store)
    if blocker:
        raise RuntimeError(blocker)

    if store == "amazon":
        return parse_amazon(html)
    if store == "alibaba":
        return parse_alibaba(html)
    if store == "temu":
        return parse_temu(html)
    return []


def dedupe_products(products: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for product in products:
        key = product.get("title", "").lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(product)
    return deduped


def collect_products(
    store: str,
    query: str,
    pages_to_scan: int = 1,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, str]]:
    driver = build_driver()
    products: List[Dict[str, str]] = []
    try:
        for page in range(1, pages_to_scan + 1):
            if progress_callback:
                progress_callback(f"Scanning {store} page {page}")
            url = build_url(store, query, page)
            driver.get(url)
            time.sleep(3)

            if store == "temu" and pages_to_scan > 1:
                for _ in range(min(3, pages_to_scan)):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    try:
                        buttons = driver.find_elements("xpath", "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]")
                        if buttons:
                            buttons[0].click()
                            time.sleep(1)
                    except Exception:
                        pass

            html = driver.page_source
            page_products = parse_store_results(store, html)
            products.extend(page_products)
            if progress_callback:
                progress_callback(f"Found {len(page_products)} products on page {page}")

        return dedupe_products(products)[:40]
    except RuntimeError as exc:
        if str(exc) == "Verification required":
            driver._keep_open = True
        raise
    finally:
        if not getattr(driver, "_keep_open", False):
            driver.quit()
