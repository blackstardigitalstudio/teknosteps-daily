# -*- coding: utf-8 -*-
"""
PRINTFUL — evadi un ordine merch (crea una BOZZA).  TeknoSteps · Made in Italy.
=============================================================================
Quando arriva un ordine (email da order.php dopo il pagamento PayPal), copia i
dati in  order_da_evadere.json  e lancia:  python printful_create_order.py

Crea una BOZZA d'ordine su Printful (confirm=0): NIENTE addebito automatico.
Vai poi sul cruscotto Printful, controlla e CONFERMA tu per far partire stampa
e spedizione. Cosi' verifichi sempre che il pagamento PayPal sia arrivato.

order_da_evadere.json (esempio):
{
  "variant_id": 4017,          // 4016=S 4017=M 4018=L 4019=XL 4020=2XL (Tee nera)
  "name": "Jane Doe",
  "email": "jane@email.com",
  "address": "Via Roma 1",
  "city": "Milano",
  "zip": "20100",
  "country_code": "IT",        // codice ISO 2 lettere (IT, US, FR, DE, ES, GB...)
  "state_code": ""             // opzionale (per US/CA/AU): es. "CA"
}
"""
import os, json, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(BASE, "_printful_secret.json"), encoding="utf-8"))
TOK, SID = S["token"], str(S["store_id"])
PRINT_URL = "https://teknosteps.com/assets/merch_out/print_teknosteps_logo.png"
ORDER_FILE = os.path.join(BASE, "order_da_evadere.json")


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://api.printful.com" + path, data=data, method=method,
        headers={"Authorization": "Bearer " + TOK, "X-PF-Store-Id": SID,
                 "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:600]); raise


def main():
    if not os.path.exists(ORDER_FILE):
        print("[X] Manca order_da_evadere.json — copia i dati dell'ordine dentro (vedi esempio in cima).")
        return
    o = json.load(open(ORDER_FILE, encoding="utf-8"))
    for k in ("variant_id", "name", "address", "city", "zip", "country_code"):
        if not o.get(k):
            print(f"[X] Campo mancante: {k}"); return

    body = {
        "recipient": {
            "name": o["name"], "address1": o["address"], "city": o["city"],
            "zip": str(o["zip"]), "country_code": o["country_code"].upper(),
            "state_code": (o.get("state_code") or "").upper() or None,
            "email": o.get("email", ""),
        },
        # sync_variant_id = l'id del prodotto NEL NEGOZIO (ha gia' il suo design:
        # felpa retro, scimmia fronte+retro, shorts all-over, ecc.). Printful stampa
        # il file giusto in automatico -> NIENTE piu' stampe sbagliate.
        "items": [{
            "sync_variant_id": int(o["variant_id"]), "quantity": int(o.get("quantity", 1)),
        }],
    }
    res = api("POST", "/orders?confirm=0", body)  # BOZZA (non confermata)
    oid = res["result"]["id"]
    cost = res["result"].get("costs", {}).get("total", "?")
    print(f"[OK] Bozza ordine creata su Printful. ID: {oid}  (costo stimato: {cost})")
    print("     Controlla e CONFERMA qui: https://www.printful.com/dashboard/orders")
    print("     (Conferma solo dopo aver verificato il pagamento PayPal.)")


if __name__ == "__main__":
    main()
