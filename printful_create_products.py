"""
PRINTFUL — crea prodotti merch via API.  TeknoSteps · Made in Italy.
====================================================================
Usa il token in _printful_secret.json (account-level, store nativo/API).
Crea i "sync product" nel negozio Printful con il design gia' pubblicato
online (Printful scarica la stampa dall'URL).

USO:  python printful_create_products.py
"""
import json, urllib.request, os

PROJ = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(PROJ, "_printful_secret.json"), encoding="utf-8"))
TOK, SID = S["token"], str(S["store_id"])

PRINT_URL = "https://teknosteps.com/assets/merch_out/print_teknosteps_logo.png"

# Bella + Canvas 3001 (catalog product 71) — varianti NERE
BLACK = {"S": 4016, "M": 4017, "L": 4018, "XL": 4019, "2XL": 4020}
RETAIL = "29.00"   # prezzo di vendita (il blank+stampa costa ~14-16)


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        "https://api.printful.com" + path, data=data, method=method,
        headers={"Authorization": "Bearer " + TOK, "X-PF-Store-Id": SID,
                 "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:600]); raise


def make_tshirt():
    variants = [{
        "variant_id": vid,
        "retail_price": RETAIL,
        "files": [{"type": "front", "url": PRINT_URL}],
    } for size, vid in BLACK.items()]
    body = {
        "sync_product": {"name": "TeknoSteps — Logo Tee (Black)",
                         "thumbnail": PRINT_URL},
        "sync_variants": variants,
    }
    res = api("POST", "/store/products", body)
    print("CREATO sync_product id:", res["result"]["id"])
    return res["result"]["id"]


if __name__ == "__main__":
    make_tshirt()
