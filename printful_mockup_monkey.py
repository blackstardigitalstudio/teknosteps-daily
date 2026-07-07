# -*- coding: utf-8 -*-
"""
PRINTFUL — mockup della t-shirt TEKNO MONKEY. TeknoSteps · Made in Italy.
Usa il design scimmietta gia' online e scarica i mockup realistici.
USO:  python printful_mockup_monkey.py
"""
import json, urllib.request, urllib.error, os, time

PROJ = os.path.dirname(os.path.abspath(__file__))
try:
    import pip_system_certs.wrapt_requests  # noqa
except Exception:
    pass
S = json.load(open(os.path.join(PROJ, "_printful_secret.json"), encoding="utf-8"))
TOK, SID = S["token"], str(S["store_id"])
PRINT_URL = "https://teknosteps.com/assets/merch_out/print_teknosteps_monkey6.png"
OUT = os.path.join(PROJ, "assets", "merch_out")


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://api.printful.com" + path, data=data, method=method,
        headers={"Authorization": "Bearer " + TOK, "X-PF-Store-Id": SID,
                 "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:600]); raise


def gen(product_id, variant_ids, tag):
    task = api("POST", "/mockup-generator/create-task/%d" % product_id, {
        "variant_ids": variant_ids,
        "format": "jpg",
        "files": [{"placement": "front", "image_url": PRINT_URL,
                   "position": {"area_width": 1800, "area_height": 2400,
                                "width": 1700, "height": 2266,
                                "top": 67, "left": 50}}],
    })
    key = task["result"]["task_key"]
    print("task", key, "...")
    for _ in range(50):
        time.sleep(3)
        r = api("GET", "/mockup-generator/task?task_key=" + key)["result"]
        if r["status"] == "completed":
            for i, m in enumerate(r["mockups"]):
                dst = os.path.join(OUT, "mockup_%s_%d.jpg" % (tag, i))
                req = urllib.request.Request(m["mockup_url"], headers={"User-Agent": "Mozilla/5.0"})
                open(dst, "wb").write(urllib.request.urlopen(req).read())
                print("saved", dst)
            return
        if r["status"] == "failed":
            print("FAILED", r); return
    print("timeout")


if __name__ == "__main__":
    gen(71, [4017, 4018], "tee_monkey")  # Bella+Canvas 3001, M+L nere
