import json
from scraper import collect_products

query = "rtx 5080"
for store in ["amazon", "alibaba", "temu"]:
    try:
        products = collect_products(store, query, pages_to_scan=1)
        print(f"{store}: {len(products)}")
        for product in products[:3]:
            print(json.dumps(product, ensure_ascii=False))
    except Exception as exc:
        print(f"{store}: ERROR {exc}")
