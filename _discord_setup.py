"""TeknoSteps - setup completo del server Discord. Idempotente. Made in Italy.
Crea categorie/canali/ruoli mancanti, canali info in sola-lettura, pubblica
regole + benvenuto (pinnati) e il messaggio ruoli-genere. Rimuove i canali di
default italiani. Rilanciabile senza duplicare. ESEGUIRE UNA VOLTA SOLA."""
import json, sys, discord
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CFG = json.load(open("_discord_secret.json", encoding="utf-8"))
RADIO = CFG.get("radio_url", "https://teknosteps.com")
GENRE_ROLES = {"🔊": "Techno", "🌀": "Psytrance", "➖": "Minimal", "✨": "Trance"}

STRUCTURE = {
    "📢 INFO": ["welcome", "rules", "announcements"],
    "🎵 RADIO": ["now-playing", "live-streams", "requests"],
    "🎧 COMMUNITY": ["general", "your-tracks", "your-walks", "feedback"],
}
READONLY = {"welcome", "rules", "announcements"}
DEFAULT_JUNK_TEXT = {"generale", "general-1"}     # canali testo di default da rimuovere
DEFAULT_JUNK_VOICE = {"Generale"}                 # canale voce di default da rimuovere
DEFAULT_JUNK_CAT = {"Canali testuali", "Canali vocali"}

RULES = (
    "🕺 **TEKNOSTEPS — HOUSE RULES**\n\n"
    "No faces. Just steps and bass. Keep it that way.\n\n"
    "1. Respect everyone. No racism, hate, harassment. Zero tolerance.\n"
    "2. No spam, no self-promo outside #your-tracks / #your-walks.\n"
    "3. Keep channels on-topic.\n"
    "4. No NSFW, no illegal content, no leaks.\n"
    "5. Staff decisions are final.\n\n"
    "By staying here you accept these rules. Now walk. 🌍\n"
    f"▶️ 24/7 radio: {RADIO}"
)
WELCOME = (
    "🌍 **Welcome to the TeknoSteps movement.**\n\n"
    "A worldwide walk. One beat. No faces — just steps and bass.\n"
    f"▶️ Listen live 24/7: {RADIO}\n"
    "🎧 Grab your genre role in **#general**.\n"
    "🎵 Share your music in **#your-tracks** · your walks in **#your-walks**\n\n"
    "You're in. Let's move."
)

intents = discord.Intents.default(); intents.members = True; intents.message_content = True
c = discord.Client(intents=intents)


async def bot_already_posted(ch):
    async for m in ch.history(limit=30):
        if m.author.id == c.user.id:
            return m
    return None


@c.event
async def on_ready():
    g = c.guilds[0]
    me = g.me
    print("Server:", g.name)

    # 1) ruoli-genere
    existing = {r.name for r in g.roles}
    for name in GENRE_ROLES.values():
        if name not in existing:
            await g.create_role(name=name, mentionable=True); print("  + ruolo:", name)

    # 2) categorie + canali
    cats = {cat.name: cat for cat in g.categories}
    chans = {ch.name: ch for ch in g.channels}
    for cat_name, ch_names in STRUCTURE.items():
        cat = cats.get(cat_name) or await g.create_category(cat_name)
        if cat_name not in cats:
            print("  + categoria:", cat_name); cats[cat_name] = cat
        for cn in ch_names:
            if cn not in chans:
                ow = {}
                if cn in READONLY:
                    ow = {g.default_role: discord.PermissionOverwrite(send_messages=False),
                          me: discord.PermissionOverwrite(send_messages=True)}
                chans[cn] = await g.create_text_channel(cn, category=cat, overwrites=ow)
                print("  + canale:", cn)
    if not discord.utils.get(g.voice_channels, name="The Walk"):
        await g.create_voice_channel("The Walk", category=cats.get("🎧 COMMUNITY"))
        print("  + vocale: The Walk")

    chans = {ch.name: ch for ch in g.channels}

    # 3) regole + benvenuto (pin best-effort: se manca "Gestire messaggi" pubblica comunque)
    async def _pin(m):
        try: await m.pin()
        except Exception: pass
    if (ch := chans.get("rules")) and not await bot_already_posted(ch):
        m = await ch.send(RULES); await _pin(m); print("  > regole pubblicate")
    if (ch := chans.get("welcome")) and not await bot_already_posted(ch):
        m = await ch.send(WELCOME); await _pin(m); print("  > welcome pubblicato")

    # 4) messaggio ruoli-genere in #general
    if (gen := chans.get("general")) and not await bot_already_posted(gen):
        lines = "\n".join(f"{e} → **{r}**" for e, r in GENRE_ROLES.items())
        emb = discord.Embed(title="🎧 Pick your sound",
                            description=f"React to grab your role:\n\n{lines}", color=0xB6FF00)
        msg = await gen.send(embed=emb)
        for e in GENRE_ROLES:
            await msg.add_reaction(e)
        print("  > messaggio ruoli pubblicato in #general")

    # 5) pulizia: rimuovi canali/categorie di default italiani
    for ch in list(g.text_channels):
        if ch.name in DEFAULT_JUNK_TEXT:
            await ch.delete(); print("  - rimosso canale default:", ch.name)
    for ch in list(g.voice_channels):
        if ch.name in DEFAULT_JUNK_VOICE:
            await ch.delete(); print("  - rimosso vocale default:", ch.name)
    for cat in list(g.categories):
        if cat.name in DEFAULT_JUNK_CAT and not cat.channels:
            await cat.delete(); print("  - rimossa categoria default:", cat.name)

    print("SETUP OK")
    await c.close()


import logging
c.run(CFG["token"], log_level=logging.INFO)
