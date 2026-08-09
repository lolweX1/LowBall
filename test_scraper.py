import json

import scraper


def test_build_driver_uses_selenium(monkeypatch):
    class FakeWebDriver:
        def __init__(self, *args, **kwargs):
            self.page_source = "<html><body>loaded</body></html>"
            self._keep_open = False

        def get(self, url):
            self.url = url

        def quit(self):
            return None

    monkeypatch.setattr(scraper.webdriver, "Chrome", FakeWebDriver, raising=False)
    monkeypatch.setattr(scraper, "Service", lambda *args, **kwargs: object(), raising=False)
    monkeypatch.setattr(scraper, "Options", lambda: type("FakeOptions", (), {"add_argument": lambda self, *a, **k: None, "add_experimental_option": lambda self, *a, **k: None})(), raising=False)
    monkeypatch.setattr(scraper, "ChromeDriverManager", lambda: type("FakeManager", (), {"install": lambda self: "driver-path"})(), raising=False)

    driver = scraper.build_driver()

    assert driver.page_source == "<html><body>loaded</body></html>"
    driver.get("https://example.com")
    driver.quit()


def test_normalize_product_url_handles_relative_links():
    assert scraper.normalize_product_link("/gp/product/ABC", "amazon") == "https://www.amazon.com/gp/product/ABC"
    assert scraper.normalize_product_link("//www.temu.com/goods/123", "temu") == "https://www.temu.com/goods/123"
    assert scraper.normalize_product_link("", "amazon") == ""
    assert scraper.normalize_product_link("javascript:alert(1)", "amazon") == ""


def test_parse_alibaba_falls_back_to_generic_product_links():
    html = '''
    <div>
      <a href="/product/123">
        <span>RTX 5080 Graphics Card</span>
      </a>
      <span class="price">$999.00</span>
    </div>
    '''
    products = scraper.parse_alibaba(html)
    assert len(products) == 1
    assert products[0]["title"] == "RTX 5080 Graphics Card"
    assert products[0]["link"] == "https://www.alibaba.com/product/123"


def test_normalize_rating_is_numeric_when_possible():
    assert scraper.normalize_rating("4.7 out of 5 stars") == "4.7/5 stars"
    assert scraper.normalize_rating("N/A") == "Unknown"
    assert scraper.normalize_rating("No reviews") == "Unknown"


def test_build_url_supports_walmart_and_target():
    assert scraper.build_url("walmart", "wireless mouse", 1) == "https://www.walmart.com/search?q=wireless%20mouse"
    assert scraper.build_url("target", "wireless mouse", 1) == "https://www.target.com/s?searchTerm=wireless+mouse"


def test_dedupe_products_removes_incomplete_records_and_merges_same_link():
    products = [
        {"title": "RTX 5080", "price": "N/A", "rating": "N/A", "link": "https://example.com/product/1"},
        {"title": "RTX 5080 Graphics Card", "price": "$999.00", "rating": "N/A", "link": "https://example.com/product/1"},
        {"title": "Broken item", "price": "N/A", "rating": "N/A", "link": ""},
        {"title": "Incomplete item", "price": "N/A", "rating": "N/A", "link": "https://example.com/product/2"},
    ]

    deduped = scraper.dedupe_products(products)

    assert len(deduped) == 1
    assert deduped[0]["title"] == "RTX 5080 Graphics Card"
    assert deduped[0]["price"] == "$999.00"
    assert deduped[0]["link"] == "https://example.com/product/1"


if __name__ == "__main__":
    query = "rtx 5080"
    for store in ["amazon", "alibaba", "temu"]:
        try:
            products = scraper.collect_products(store, query, pages_to_scan=1)
            print(f"{store}: {len(products)}")
            for product in products[:3]:
                print(json.dumps(product, ensure_ascii=False))
        except Exception as exc:
            print(f"{store}: ERROR {exc}")
