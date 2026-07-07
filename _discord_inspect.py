"""Ispeziona lo stato del server Discord: categorie, canali, ruoli, messaggi bot."""
import json, discord
CFG = json.load(open("_discord_secret.json", encoding="utf-8"))
intents = discord.Intents.default(); intents.members=True; intents.message_content=True
c = discord.Client(intents=intents)

@c.event
async def on_ready():
    g = c.guilds[0]
    print("SERVER:", g.name)
    print("\n== RUOLI ==")
    from collections import Counter
    rc = Counter(r.name for r in g.roles)
    for name, n in rc.items():
        print(f"  {name}{'  x'+str(n)+' !!!DOPPIO' if n>1 else ''}")
    print("\n== CATEGORIE ==")
    cc = Counter(cat.name for cat in g.categories)
    for name, n in cc.items():
        print(f"  {name}{'  x'+str(n)+' !!!DOPPIA' if n>1 else ''}")
    print("\n== CANALI TESTO ==")
    tc = Counter(ch.name for ch in g.text_channels)
    for name, n in tc.items():
        print(f"  {name}{'  x'+str(n)+' !!!DOPPIO' if n>1 else ''}")
    print("\n== CANALI VOCE ==")
    for ch in g.voice_channels:
        print(" ", ch.name)
    print("\n== MESSAGGI DEL BOT per canale ==")
    for ch in g.text_channels:
        cnt = 0
        try:
            async for m in ch.history(limit=20):
                if m.author.id == c.user.id:
                    cnt += 1
        except Exception:
            cnt = -1
        if cnt != 0:
            print(f"  #{ch.name}: {cnt} messaggi bot")
    await c.close()

c.run(CFG["token"], log_handler=None)
