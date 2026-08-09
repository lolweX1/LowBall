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
    if store == "walmart":
        return f"https://www.walmart.com/search?q={query_text}"
    if store == "target":
        return f"https://www.target.com/s?searchTerm={quote(query, safe='').replace('%20', '+')}"
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
        return "Unknown"
    text = re.sub(r"\s+", " ", raw).strip()
    if not text:
        return "Unknown"
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:/\s*5|out of 5|stars?|star)", text, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)}/5 stars"
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        return f"{match.group(1)}/5 stars"
    return "Unknown"


def normalize_product_link(raw_link: Optional[str], store: str) -> str:
    if not raw_link:
        return ""
    link = raw_link.strip()
    if not link or link.startswith("javascript:"):
        return ""
    if link.startswith("//"):
        link = "https:" + link
    if link.startswith("/"):
        if store == "amazon":
            link = f"https://www.amazon.com{link}"
        elif store == "alibaba":
            link = f"https://www.alibaba.com{link}"
        elif store == "temu":
            link = f"https://www.temu.com{link}"
    if link.startswith("http://") and store == "amazon":
        link = link.replace("http://", "https://")
    if link.startswith("http://") and store == "alibaba":
        link = link.replace("http://", "https://")
    if link.startswith("http://") and store == "temu":
        link = link.replace("http://", "https://")
    return link


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s*[)\]]+\s*a\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[)\]}]+\s*$", "", cleaned)
    return cleaned.strip()


def is_junk_title(title: str) -> bool:
    lowered = title.lower()
    junk_markers = [
        "please wait",
        "we are checking",
        "verifying you",
        "captcha",
        "login",
        "sign in",
        "search results",
        "home",
        "all categories",
    ]
    if any(marker in lowered for marker in junk_markers):
        return True
    if lowered.endswith(")a") or lowered.endswith("a"):
        return True
    return False


def detect_blocker(html: str, store: str) -> Optional[str]:
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
        link = normalize_product_link(link_el.get("href", "") if link_el else "", "amazon")
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
        "a[href*='product'], a[href*='offer'], a[href*='item'], a[href*='detail'], a[href*='goods'], li, article, .search-card, .organic-product, .offer-card, .item"
    )

    for card in candidate_cards:
        anchor = card if card.name == "a" else card.select_one("a[href]")
        if not anchor:
            continue

        href = normalize_product_link(anchor.get("href", ""), "alibaba")
        if not href or not any(key in href.lower() for key in ["product", "offer", "item", "detail", "goods"]):
            continue

        title_el = (
            card.select_one(".search-card-e-title")
            or card.select_one(".title")
            or card.select_one("h3")
            or card.select_one("span")
            or anchor
        )
        title = clean_text(title_el.get_text(" ", strip=True) if title_el else "")
        if not title or len(title) < 3:
            continue
        if is_junk_title(title):
            continue

        price_el = (
            card.select_one(".price")
            or card.select_one(".search-card-e-price")
            or card.select_one("[class*='price']")
            or (anchor.parent.select_one("[class*='price']") if anchor.parent else None)
        )
        price = normalize_price(price_el.get_text(" ", strip=True) if price_el else None)
        products.append({"title": title, "price": price, "rating": "N/A", "link": href})

    if not products:
        for anchor in soup.select("a[href]"):
            href = normalize_product_link(anchor.get("href", ""), "alibaba")
            if not href or not any(key in href.lower() for key in ["product", "offer", "item", "detail", "goods"]):
                continue
            title = clean_text(anchor.get_text(" ", strip=True))
            if not title or len(title) < 3:
                continue
            if is_junk_title(title):
                continue
            products.append({"title": title, "price": "N/A", "rating": "N/A", "link": href})

    if not products:
        raw_links = set()
        for match in re.findall(r"(?:https?:)?//(?:[A-Za-z0-9.-]+\.)?alibaba\.com(?:/[A-Za-z0-9_\-/?&%=.:]+)?", html, flags=re.IGNORECASE):
            normalized = normalize_product_link(match, "alibaba")
            if normalized and any(key in normalized.lower() for key in ["product", "offer", "item", "detail", "goods"]):
                raw_links.add(normalized)
        for match in re.findall(r"/(?:product|offer|item|detail|goods)[A-Za-z0-9_\-/?&%=.:]*", html, flags=re.IGNORECASE):
            normalized = normalize_product_link(match, "alibaba")
            if normalized and any(key in normalized.lower() for key in ["product", "offer", "item", "detail", "goods"]):
                raw_links.add(normalized)

        for index, href in enumerate(sorted(raw_links), start=1):
            products.append({
                "title": f"Alibaba Product {index}",
                "price": "N/A",
                "rating": "N/A",
                "link": href,
            })

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
        link = normalize_product_link(card.get("href", "") or card.get("data-href", ""), "temu")
        products.append({"title": title, "price": price, "rating": "N/A", "link": link})

    if not products:
        for card in soup.select("a"):
            title = clean_text(card.get_text(" ", strip=True))
            if title and len(title) > 6 and "search" not in title.lower():
                products.append({"title": title, "price": "N/A", "rating": "N/A", "link": normalize_product_link(card.get("href", ""), "temu")})

    return products


def parse_store_results(store: str, html: str) -> List[Dict[str, str]]:
    blocker = detect_blocker(html, store)
    if blocker:
        raise RuntimeError(blocker)

    if store == "amazon":
        return parse_amazon(html)
    if store == "alibaba":
        return parse_alibaba(html)
    if store == "walmart":
        return parse_amazon(html)
    if store == "target":
        return parse_amazon(html)
    if store == "temu":
        return parse_temu(html)
    return []


def dedupe_products(products: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}

    def normalize_for_store(link: str) -> str:
        lowered = link.lower()
        if "alibaba.com" in lowered:
            return normalize_product_link(link, "alibaba")
        if "temu.com" in lowered:
            return normalize_product_link(link, "temu")
        return normalize_product_link(link, "amazon")

    for product in products:
        if not product:
            continue

        link = (product.get("link") or "").strip()
        if not link:
            continue

        normalized = normalize_for_store(link)
        if not normalized:
            continue
        link = normalized

        if link not in merged:
            merged[link] = {
                "title": product.get("title", "") or "",
                "price": product.get("price", "") or "",
                "rating": product.get("rating", "") or "",
                "link": link,
            }
            continue

        current = merged[link]
        for field_name, value in {
            "title": product.get("title", "") or "",
            "price": product.get("price", "") or "",
            "rating": product.get("rating", "") or "",
        }.items():
            current_value = (current.get(field_name) or "").strip()
            new_value = (value or "").strip()

            if field_name == "title":
                if not current_value and new_value:
                    current[field_name] = new_value
                elif new_value and current_value and len(new_value) > len(current_value):
                    current[field_name] = new_value
            else:
                if current_value in ("", "N/A", "n/a") and new_value not in ("", "N/A", "n/a"):
                    current[field_name] = new_value

        current["link"] = link

    filtered = []
    for product in merged.values():
        title = (product.get("title") or "").strip()
        price = (product.get("price") or "").strip()
        rating = (product.get("rating") or "").strip()
        link = (product.get("link") or "").strip()

        if not link or not title:
            continue
        if price in ("", "N/A", "n/a") and rating in ("", "N/A", "n/a"):
            continue

        filtered.append({
            "title": title,
            "price": price or "N/A",
            "rating": rating or "N/A",
            "link": link,
        })

    return filtered


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
        raise
    finally:
        if not getattr(driver, "_keep_open", False):
            driver.quit()
