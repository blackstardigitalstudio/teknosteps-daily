import json, asyncio, discord
CFG = json.load(open("_discord_secret.json", encoding="utf-8"))
intents = discord.Intents.default(); intents.members=True; intents.message_content=True
c = discord.Client(intents=intents)
@c.event
async def on_ready():
    print("LOGGED IN AS:", c.user)
    print("GUILDS:", [(g.name, g.id) for g in c.guilds] or "NESSUNO — il bot NON e' nel server")
    await c.close()
c.run(CFG["token"], log_handler=None)
