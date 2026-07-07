# -*- coding: utf-8 -*-
"""
PRINTFUL - crea la felpa Tekno Monkey con scimmia DAVANTI + DIETRO. Made in Italy.
Front = print_monkey_chest.png (faccia scimmia), Back = print_tekno_monkey.png (grande).
Trova i variant-id catalogo dalla felpa esistente e crea il nuovo sync_product.
USO: python printful_monkey_frontback.py
"""
import json, urllib.request, os

PROJ = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(PROJ, "_printful_secret.json"), encoding="utf-8"))
TOK, SID = S["token"], str(S["store_id"])
FRONT_URL = "https://teknosteps.com/assets/merch_out/print_monkey_chest.png"
BACK_URL = "https://teknosteps.com/assets/merch_out/print_tekno_monkey.png"
RETAIL = "58.00"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://api.printful.com" + path, data=data, method=method,
                               headers={"Authorization": "Bearer " + TOK, "X-PF-Store-Id": SID,
                                        "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:600]); raise


def hoodie_variants():
    """Ricava {size: catalog_variant_id} da una felpa gia' nel negozio."""
    prods = api("GET", "/store/products?limit=100")["result"]
    hood = next((p for p in prods if "hoodie" in p["name"].lower()), None)
    if not hood:
        raise SystemExit("Nessuna felpa trovata nel negozio da cui prendere i variant-id.")
    det = api("GET", "/store/products/%s" % hood["id"])["result"]
    out = {}
    for sv in det["sync_variants"]:
        size = sv.get("size") or (sv.get("name", "").split("/")[-1].strip())
        cid = sv.get("variant_id")
        if size and cid and size not in out:
            out[size] = cid
    print("Felpa base:", det["sync_product"]["name"], "| taglie:", out)
    return out


def main():
    sizes = hoodie_variants()
    variants = [{
        "variant_id": cid,
        "retail_price": RETAIL,
        "files": [
            {"type": "front", "url": FRONT_URL},
            {"type": "back", "url": BACK_URL},
        ],
    } for size, cid in sizes.items()]
    body = {
        "sync_product": {"name": "Tekno Monkey Hoodie - Front & Back (Black)",
                         "thumbnail": BACK_URL},
        "sync_variants": variants,
    }
    res = api("POST", "/store/products", body)
    pid = res["result"]["id"]
    print("CREATO prodotto id:", pid, "(scimmia davanti+dietro,", RETAIL, "EUR)")
    det = api("GET", "/store/products/%s" % pid)["result"]
    print("Sync variants (per store.html):")
    for sv in det["sync_variants"]:
        print("  ", sv.get("size") or sv.get("name"), "-> sync_variant_id", sv["id"])


if __name__ == "__main__":
    main()
