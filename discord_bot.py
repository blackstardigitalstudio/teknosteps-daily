"""
TEKNOSTEPS — Discord bot. Made in Italy.
=========================================
Il "comando" del server: da' il benvenuto, assegna i ruoli-genere con le
reaction, annuncia le live YouTube e la radio. Gira 24/7 (es. su Oracle Cloud
Free Tier, la stessa VM delle dirette).

SETUP (una volta sola):
  1. Crea il bot:  https://discord.com/developers/applications
     - New Application -> nome "TeknoSteps" -> tab "Bot" -> Add Bot.
     - In "Bot": attiva  SERVER MEMBERS INTENT  e  MESSAGE CONTENT INTENT.
     - "Reset Token" -> copia il token.
  2. Metti il token in  _discord_secret.json  (NON va online):
     { "token": "IL_TUO_BOT_TOKEN",
       "welcome_channel": "welcome",
       "roles_channel": "general",
       "radio_url": "https://teknosteps.com" }
  3. Invita il bot nel server: tab "OAuth2 > URL Generator" ->
     scopes: bot, applications.commands ->
     bot permissions: Manage Roles, Send Messages, Read Message History,
     Add Reactions -> apri l'URL generato e scegli il server TeknoSteps.
  4. Avvia:  pip install -U discord.py   poi   python discord_bot.py
     (comando /setup-roles nel canale per pubblicare il messaggio dei ruoli.)
"""
import json, os, time, random, datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "_discord_secret.json"), encoding="utf-8"))
RADIO = CFG.get("radio_url", "https://teknosteps.com")

# Ruoli-genere: emoji -> nome ruolo (deve esistere nel server)
GENRE_ROLES = {"🔊": "Techno", "🌀": "Psytrance", "➖": "Minimal", "✨": "Trance"}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

WELCOME = (
    "🕺 **Welcome to TeknoSteps, {name}!**\n"
    "No faces. Just steps and bass. One global walk, one beat.\n\n"
    "▶️ Listen 24/7: <{radio}>\n"
    "🎧 Grab your genre role in the roles message.\n"
    "🎵 Drop your tracks in **#your-tracks**, your walks in **#your-walks**.\n\n"
    "Now walk. 🌍"
)


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("sync err:", e)
    print(f"TeknoSteps bot online as {bot.user} — {len(bot.guilds)} server(s)")
    if not daily_dyk.is_running():
        daily_dyk.start()
    if not daily_story_dm.is_running():
        daily_story_dm.start()


@bot.event
async def on_member_join(member):
    ch = discord.utils.get(member.guild.text_channels, name=CFG.get("welcome_channel", "welcome"))
    msg = WELCOME.format(name=member.mention, radio=RADIO)
    if ch:
        await ch.send(msg)
    try:
        await member.send(msg)  # anche in DM (se aperti)
    except discord.Forbidden:
        pass


@bot.tree.command(description="Pubblica il messaggio per scegliere il ruolo-genere con le reaction.")
async def setup_roles(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("Solo un admin puo' farlo.", ephemeral=True)
    lines = "\n".join(f"{e} → **{r}**" for e, r in GENRE_ROLES.items())
    embed = discord.Embed(title="🎧 Pick your sound", description=f"React to grab your role:\n\n{lines}", color=0xB6FF00)
    await interaction.response.send_message("Fatto ✅", ephemeral=True)
    m = await interaction.channel.send(embed=embed)
    for e in GENRE_ROLES:
        await m.add_reaction(e)


async def _toggle_role(payload, add):
    if payload.user_id == bot.user.id:
        return
    name = GENRE_ROLES.get(str(payload.emoji))
    if not name:
        return
    guild = bot.get_guild(payload.guild_id)
    role = discord.utils.get(guild.roles, name=name)
    member = guild.get_member(payload.user_id)
    if not role or not member:
        return
    await (member.add_roles(role) if add else member.remove_roles(role))


@bot.event
async def on_raw_reaction_add(p):
    await _toggle_role(p, True)


@bot.event
async def on_raw_reaction_remove(p):
    await _toggle_role(p, False)


@bot.tree.command(description="Annuncia una diretta YouTube nel canale corrente.")
@app_commands.describe(url="Link della live YouTube")
async def live(interaction: discord.Interaction, url: str):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Solo staff.", ephemeral=True)
    embed = discord.Embed(title="🔴 WE ARE LIVE", description=f"The walk is streaming now.\n▶️ {url}", color=0xFF2244)
    await interaction.response.send_message(content="@everyone", embed=embed)


@bot.tree.command(description="Link alla radio 24/7.")
async def nowplaying(interaction: discord.Interaction):
    embed = discord.Embed(title="🎵 TeknoSteps Radio — 24/7", description=f"Steps and bass, non-stop.\n▶️ {RADIO}", color=0xB6FF00)
    await interaction.response.send_message(embed=embed)


# =======================================================================
#  ENGAGEMENT: livelli/XP, trivia, comandi fun, GM/GN  (fa tornare la gente)
# =======================================================================
LEVELS_FILE = os.path.join(HERE, "_levels_teknosteps.json")


def _load_levels():
    try:
        return json.load(open(LEVELS_FILE, encoding="utf-8"))
    except Exception:
        return {}


def _save_levels(d):
    try:
        json.dump(d, open(LEVELS_FILE, "w", encoding="utf-8"))
    except Exception:
        pass


levels = _load_levels()
_xp_cd = {}                     # user_id -> ultimo timestamp XP (anti-spam)


def _level_for(xp):
    return int((max(0, xp) / 100.0) ** 0.5)     # Lv1=100xp, Lv2=400, Lv3=900...


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    low = message.content.strip().lower()
    if low in ("gm", "good morning", "buongiorno"):
        try: await message.add_reaction("🌅")
        except Exception: pass
    elif low in ("gn", "good night", "buonanotte"):
        try: await message.add_reaction("🌙")
        except Exception: pass
    # XP con cooldown 60s: chattare fa salire di livello
    uid = str(message.author.id); now = time.time()
    if now - _xp_cd.get(uid, 0) >= 60:
        _xp_cd[uid] = now
        before = levels.get(uid, 0)
        levels[uid] = before + random.randint(8, 16)
        _save_levels(levels)
        if _level_for(levels[uid]) > _level_for(before):
            try:
                await message.channel.send(
                    f"🎚️ {message.author.mention} è salito al **livello {_level_for(levels[uid])}**! Keep walking. 🕺")
            except Exception:
                pass
    await bot.process_commands(message)


@bot.tree.command(description="Mostra il tuo livello e XP.")
async def rank(interaction: discord.Interaction):
    xp = levels.get(str(interaction.user.id), 0)
    embed = discord.Embed(title=f"🎚️ {interaction.user.display_name}",
                          description=f"Livello **{_level_for(xp)}** · **{xp} XP**\nChatta per salire. Steps and bass.",
                          color=0xB6FF00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(description="Classifica dei top TeknoSteppers.")
async def leaderboard(interaction: discord.Interaction):
    top = sorted(levels.items(), key=lambda kv: kv[1], reverse=True)[:10]
    lines = []
    for i, (uid, xp) in enumerate(top, 1):
        m = interaction.guild.get_member(int(uid)) if interaction.guild else None
        nm = m.display_name if m else f"user {uid}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
        lines.append(f"{medal} {nm} — Lv {_level_for(xp)} ({xp} XP)")
    embed = discord.Embed(title="🏆 TeknoSteps Leaderboard",
                          description="\n".join(lines) or "Ancora nessuno. Sii il primo a chattare!",
                          color=0xB6FF00)
    await interaction.response.send_message(embed=embed)


TRIVIA = [
    ("In che citta' e' nata la techno?", "Detroit (USA), anni '80."),
    ("Cosa significa BPM?", "Beats Per Minute - battiti al minuto."),
    ("Che BPM ha di solito la psytrance?", "circa 140-150 BPM."),
    ("Chi sono i 'Belleville Three' pionieri della techno?", "Juan Atkins, Derrick May, Kevin Saunderson."),
    ("Cos'e' un 'drop' in un brano?", "Il momento in cui rientra il beat pieno dopo il build-up."),
    ("Che macchina ha reso famoso il suono 'acid'?", "La Roland TB-303."),
    ("Come si chiama la cassa dritta in 4/4?", "Four-on-the-floor."),
    ("Che genere e' il 'frenchcore'?", "Hardcore/tekno francese veloce, ~200 BPM."),
    ("Cosa fa un sidechain sul kick?", "Abbassa gli altri suoni a ogni cassa = il 'pompaggio'."),
    ("Qual e' la capitale europea della techno?", "Berlino."),
    ("Che drum machine e' leggendaria per la cassa techno?", "La Roland TR-909."),
]


@bot.tree.command(description="Domanda a sorpresa sulla cultura techno.")
async def trivia(interaction: discord.Interaction):
    q, a = random.choice(TRIVIA)
    await interaction.response.send_message(f"🧠 **TEKNO TRIVIA**\n{q}\n\nRisposta (clicca per svelare): ||{a}||")


VIBES = [
    "No faces. Just steps and bass. 🕺", "Turn it up. The walk never stops. 🔊",
    "One global walk, one beat. 🌍", "Feel the kick in your chest. 💥",
    "Lost in the groove, found in the bass. 🎧", "Eyes closed, feet moving. 🌀",
    "The floor is calling. Answer it. 🔥", "24/7 tekno, no sleep for the beat. ⚡",
]


@bot.tree.command(description="Una vibe TeknoSteps + link radio.")
async def vibe(interaction: discord.Interaction):
    await interaction.response.send_message(f"✨ {random.choice(VIBES)}\n▶️ {RADIO}")


EIGHTBALL = ["Assolutamente si. 🔊", "Nessun dubbio. 🕺", "Meglio di no. 🚫", "Chiedi dopo il drop. 🌀",
             "Il basso dice si. 💥", "Non stasera. 🌙", "Certo, walk on. 🌍", "Le probabilita' dicono... forse. 🎧"]


@bot.tree.command(description="Palla magica techno.")
@app_commands.describe(domanda="La tua domanda")
async def eightball(interaction: discord.Interaction, domanda: str):
    await interaction.response.send_message(f"🎱 **{domanda}**\n{random.choice(EIGHTBALL)}")


@bot.tree.command(description="Lancia un dado.")
@app_commands.describe(facce="Numero di facce (default 6)")
async def roll(interaction: discord.Interaction, facce: int = 6):
    facce = max(2, min(1000, facce))
    await interaction.response.send_message(
        f"🎲 {interaction.user.display_name} ha tirato **{random.randint(1, facce)}** (d{facce})")


# =======================================================================
#  "LO SAPEVI CHE" — cultura tekno, IT/EN/ES con foto, ogni giorno automatico
# =======================================================================
DYK_FILE = os.path.join(HERE, "_dyk_teknosteps.json")
DYK_CHANNEL = CFG.get("dyk_channel", "did-you-know")

_I909 = "https://upload.wikimedia.org/wikipedia/commons/c/cc/Roland_TR-909.jpg"
_I808 = "https://upload.wikimedia.org/wikipedia/commons/b/be/Roland_TR-808_drum_machine.jpg"
_I303 = "https://upload.wikimedia.org/wikipedia/commons/f/fd/Roland_TB-303_Panel.jpg"
_IMS20 = "https://upload.wikimedia.org/wikipedia/commons/3/32/Korg_MS-20.jpg"
_IMOOG = "https://upload.wikimedia.org/wikipedia/commons/2/22/Minimoog.JPG"
_IDX7 = "https://upload.wikimedia.org/wikipedia/commons/0/0c/Yamaha_DX7.jpg"
_IVINYL = "https://upload.wikimedia.org/wikipedia/commons/7/72/Vinyl_collection_at_a_record_store_%28Unsplash%29.jpg"

FACTS = [
    {"it": "La techno è nata a Detroit negli anni '80, dai 'Belleville Three': Juan Atkins, Derrick May e Kevin Saunderson.",
     "en": "Techno was born in Detroit in the 1980s, from the 'Belleville Three': Juan Atkins, Derrick May and Kevin Saunderson.",
     "es": "El techno nació en Detroit en los años 80, de los 'Belleville Three': Juan Atkins, Derrick May y Kevin Saunderson.", "img": _I909},
    {"it": "La Roland TR-909 è la drum machine che ha definito cassa e hi-hat della techno.",
     "en": "The Roland TR-909 is the drum machine that defined techno's kick and hi-hats.",
     "es": "La Roland TR-909 es la caja de ritmos que definió el bombo y los hi-hats del techno.", "img": _I909},
    {"it": "Il suono 'acid' nacque per sbaglio: la Roland TB-303 doveva simulare un basso, ma quel gorgoglio creò un genere.",
     "en": "The 'acid' sound was born by accident: the Roland TB-303 was meant to fake a bass, but its squelch created a genre.",
     "es": "El sonido 'acid' nació por accidente: la Roland TB-303 debía imitar un bajo, pero su gorgoteo creó un género.", "img": _I303},
    {"it": "La Roland TR-808 è il 'boom' di hip-hop ed electro: il suo clap e il cowbell sono ovunque.",
     "en": "The Roland TR-808 is the 'boom' of hip-hop and electro: its clap and cowbell are everywhere.",
     "es": "La Roland TR-808 es el 'boom' del hip-hop y el electro: su clap y su cowbell están en todas partes.", "img": _I808},
    {"it": "La cassa dritta in 4/4 si chiama 'four-on-the-floor': è il battito cardiaco di techno e house.",
     "en": "The steady 4/4 kick is called 'four-on-the-floor': the heartbeat of techno and house.",
     "es": "El bombo constante en 4/4 se llama 'four-on-the-floor': el latido del techno y el house.", "img": _I909},
    {"it": "Ogni genere ha il suo BPM: techno ~130, house ~125, psytrance ~145, frenchcore ~200.",
     "en": "Every genre has its BPM: techno ~130, house ~125, psytrance ~145, frenchcore ~200.",
     "es": "Cada género tiene su BPM: techno ~130, house ~125, psytrance ~145, frenchcore ~200.", "img": _IVINYL},
    {"it": "Berlino è la capitale mondiale della techno: dopo la caduta del Muro (1989) gli edifici vuoti diventarono club.",
     "en": "Berlin is the world capital of techno: after the Wall fell (1989), empty buildings became clubs.",
     "es": "Berlín es la capital mundial del techno: tras la caída del Muro (1989), los edificios vacíos se volvieron clubes.", "img": _IVINYL},
    {"it": "L'acid house col suono della 303 accese la 'Second Summer of Love' in UK nel 1988.",
     "en": "Acid house, with the 303 sound, sparked the UK's 'Second Summer of Love' in 1988.",
     "es": "El acid house, con el sonido de la 303, encendió el 'Second Summer of Love' en el Reino Unido en 1988.", "img": _I303},
    {"it": "Il Minimoog rese portatile il sintetizzatore analogico e diede ai bassi elettronici il loro calore.",
     "en": "The Minimoog made the analog synth portable and gave electronic bass its warmth.",
     "es": "El Minimoog hizo portátil el sintetizador analógico y dio a los bajos electrónicos su calidez.", "img": _IMOOG},
    {"it": "Il Korg MS-20 è un semi-modulare leggendario, amato per i suoi suoni grezzi e aggressivi.",
     "en": "The Korg MS-20 is a legendary semi-modular synth, loved for its gritty, aggressive sounds.",
     "es": "El Korg MS-20 es un semimodular legendario, amado por sus sonidos ásperos y agresivos.", "img": _IMS20},
    {"it": "Lo Yamaha DX7 (sintesi FM) definì il suono digitale degli anni '80: campanelli, bassi metallici, pad cristallini.",
     "en": "The Yamaha DX7 (FM synthesis) defined the digital sound of the 80s: bells, metallic basses, crystal pads.",
     "es": "El Yamaha DX7 (síntesis FM) definió el sonido digital de los 80: campanas, bajos metálicos, pads cristalinos.", "img": _IDX7},
    {"it": "Il DJ 'beatmatcha' due dischi per far combaciare i BPM e tenere la pista in movimento senza pause.",
     "en": "A DJ 'beatmatches' two records to align their BPM and keep the floor moving without pauses.",
     "es": "El DJ 'beatmatchea' dos discos para alinear sus BPM y mantener la pista en movimiento sin pausas.", "img": _IVINYL},
    {"it": "Il 'sidechain' abbassa tutti i suoni a ogni cassa: è il classico 'pompaggio' che fa respirare il brano.",
     "en": "The 'sidechain' ducks every sound on each kick: the classic 'pump' that makes a track breathe.",
     "es": "El 'sidechain' baja todos los sonidos en cada bombo: el clásico 'pumping' que hace respirar el tema.", "img": _I909},
    {"it": "Il 'drop' è il momento in cui rientra il beat pieno dopo la salita: il picco di energia in pista.",
     "en": "The 'drop' is when the full beat returns after the build-up: the peak of energy on the floor.",
     "es": "El 'drop' es cuando vuelve el beat completo tras el build-up: el pico de energía en la pista.", "img": _I808},
    {"it": "I Kraftwerk, dalla Germania, sono i padri della musica elettronica: senza di loro non esisterebbe la techno.",
     "en": "Kraftwerk, from Germany, are the fathers of electronic music: without them techno wouldn't exist.",
     "es": "Kraftwerk, de Alemania, son los padres de la música electrónica: sin ellos no existiría el techno.", "img": _IMOOG},
    {"it": "La house è nata a Chicago: il nome viene dal club 'The Warehouse' dove suonava Frankie Knuckles.",
     "en": "House was born in Chicago: the name comes from 'The Warehouse' club where Frankie Knuckles played.",
     "es": "El house nació en Chicago: el nombre viene del club 'The Warehouse' donde pinchaba Frankie Knuckles.", "img": _I909},
    {"it": "La psytrance (goa trance) è nata sulle spiagge di Goa, in India, negli anni '90.",
     "en": "Psytrance (goa trance) was born on the beaches of Goa, India, in the 1990s.",
     "es": "El psytrance (goa trance) nació en las playas de Goa, India, en los años 90.", "img": _I303},
    {"it": "Il gabber e l'hardcore nascono a Rotterdam: BPM altissimi e cassa distorta.",
     "en": "Gabber and hardcore were born in Rotterdam: extreme BPM and a distorted kick.",
     "es": "El gabber y el hardcore nacieron en Rotterdam: BPM extremos y un bombo distorsionado.", "img": _I808},
    {"it": "Drum & bass e jungle nascono nel Regno Unito da breakbeat velocissimi + sub bass profondo.",
     "en": "Drum & bass and jungle were born in the UK from fast breakbeats + deep sub bass.",
     "es": "El drum & bass y el jungle nacieron en el Reino Unido de breakbeats rápidos + sub graves profundos.", "img": _IVINYL},
    {"it": "L''Amen break' è il breakbeat più campionato della storia: è ovunque in jungle, hip-hop e hardcore.",
     "en": "The 'Amen break' is the most sampled drum break in history: it's everywhere in jungle, hip-hop and hardcore.",
     "es": "El 'Amen break' es el break de batería más sampleado de la historia: está en todo el jungle, hip-hop y hardcore.", "img": _IVINYL},
    {"it": "Le Roland 808, 909 e 303 all'inizio furono un FLOP commerciale… poi sono diventate leggenda.",
     "en": "The Roland 808, 909 and 303 were commercial FLOPS at first… then they became legends.",
     "es": "Las Roland 808, 909 y 303 fueron un FRACASO comercial al principio… luego se volvieron leyenda.", "img": _I909},
    {"it": "La minimal techno toglie tutto il superfluo: spazio, groove e ipnosi. Meno è più.",
     "en": "Minimal techno strips away everything extra: space, groove and hypnosis. Less is more.",
     "es": "El minimal techno quita todo lo superfluo: espacio, groove e hipnosis. Menos es más.", "img": _IMS20},
    {"it": "La trance nasce in Germania nei primi anni '90: melodie euforiche e lunghe salite.",
     "en": "Trance was born in Germany in the early 1990s: euphoric melodies and long build-ups.",
     "es": "El trance nació en Alemania a principios de los 90: melodías eufóricas y largos build-ups.", "img": _IDX7},
    {"it": "Nella techno la cassa è spesso ACCORDATA alla tonalità del brano: così 'buca' senza stonare.",
     "en": "In techno the kick is often TUNED to the track's key, so it punches without clashing.",
     "es": "En el techno el bombo suele estar AFINADO a la tonalidad del tema, así pega sin desafinar.", "img": _I909},
    {"it": "Il free-party (teknival) è la scena rave illegale/autogestita: casse enormi in mezzo al nulla.",
     "en": "The free-party (teknival) is the illegal/self-run rave scene: huge sound systems in the middle of nowhere.",
     "es": "La free-party (teknival) es la escena rave ilegal/autogestionada: enormes sistemas de sonido en medio de la nada.", "img": _I808},
]


def _dyk_state():
    try:
        return json.load(open(DYK_FILE, encoding="utf-8"))
    except Exception:
        return {"last": ""}


def _dyk_save(s):
    try:
        json.dump(s, open(DYK_FILE, "w", encoding="utf-8"))
    except Exception:
        pass


async def _dyk_ch(guild):
    ch = discord.utils.get(guild.text_channels, name=DYK_CHANNEL)
    if ch is None:
        try:
            ch = await guild.create_text_channel(DYK_CHANNEL)
        except Exception:
            ch = discord.utils.get(guild.text_channels, name="announcements") \
                or (guild.text_channels[0] if guild.text_channels else None)
    return ch


def _dyk_embed(fact):
    embed = discord.Embed(
        title="🧠 Lo sapevi che… · Did you know… · ¿Sabías que…",
        description=f"🇮🇹 {fact['it']}\n\n🇬🇧 {fact['en']}\n\n🇪🇸 {fact['es']}",
        color=0xB6FF00)
    if fact.get("img"):
        embed.set_image(url=fact["img"])
    embed.set_footer(text="TeknoSteps · tekno culture · teknosteps.com")
    return embed


@tasks.loop(hours=1)
async def daily_dyk():
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    st = _dyk_state()
    if st.get("last") == today or now.hour < 9:      # una volta al giorno, dalle 9 UTC
        return
    day_index = (now.date() - datetime.date(2026, 1, 1)).days
    fact = FACTS[day_index % len(FACTS)]
    for g in bot.guilds:
        ch = await _dyk_ch(g)
        if ch:
            try:
                await ch.send(embed=_dyk_embed(fact))
            except Exception as e:
                print("dyk send err:", e)
    st["last"] = today
    _dyk_save(st)


@daily_dyk.before_loop
async def _before_dyk():
    await bot.wait_until_ready()


@bot.tree.command(description="Pubblica ORA un 'Lo sapevi che' (cultura tekno, IT/EN/ES).")
async def dyk(interaction: discord.Interaction):
    fact = random.choice(FACTS)
    await interaction.response.send_message(embed=_dyk_embed(fact))


# =======================================================================
#  STORY DEL GIORNO -> arrivano sul telefono via DM Discord (ping) + comando
# =======================================================================
STORY_DIR = os.path.join(os.path.expanduser("~"), "OneDrive", "TeknoSteps_Story")
STORY_FILES = ["story_teknosteps.mp4", "story_strangelight.mp4", "story_teknomonkey.mp4"]
STORY_STATE = os.path.join(HERE, "_story_dm_state.json")


def _story_paths():
    out = []
    for f in STORY_FILES:
        p = os.path.join(STORY_DIR, f)
        if os.path.exists(p):
            out.append(p)
    return out


def _set_owner(uid):
    CFG["owner_id"] = int(uid)
    try:
        json.dump(CFG, open(os.path.join(HERE, "_discord_secret.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception as e:
        print("owner save err:", e)


async def _send_stories(dest):
    paths = _story_paths()
    if not paths:
        return False
    files = [discord.File(p) for p in paths]
    await dest.send(
        content="📲 **Le tue Story di oggi** — 9:16, pronte da caricare su IG/TikTok/FB.\n"
                "Salvale sul telefono e postale come Story. 🌍",
        files=files)
    return True


@bot.tree.command(description="Registra TE come owner: da domani ricevi le Story in DM ogni giorno.")
async def setowner(interaction: discord.Interaction):
    _set_owner(interaction.user.id)
    await interaction.response.send_message(
        "✅ Registrato. Da ora ti mando le **Story del giorno** in DM ogni mattina. "
        "Prova subito con **/story**.", ephemeral=True)


@bot.tree.command(description="Mandami ORA le Story del giorno in DM (9:16 pronte da caricare).")
async def story(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        ok = await _send_stories(interaction.user)
    except discord.Forbidden:
        return await interaction.followup.send(
            "Ho i DM chiusi da te: apri i DM del server (Impostazioni privacy) e riprova.", ephemeral=True)
    await interaction.followup.send(
        "📲 Guarda i DM: te le ho mandate!" if ok else
        "Non trovo ancora le story di oggi (vengono create a fine pubblicazione).", ephemeral=True)


def _story_state():
    try:
        return json.load(open(STORY_STATE, encoding="utf-8"))
    except Exception:
        return {"last": ""}


@tasks.loop(minutes=30)
async def daily_story_dm():
    oid = CFG.get("owner_id")
    if not oid:
        return
    paths = _story_paths()
    if not paths:
        return
    # manda quando le story sono di OGGI e non le ho gia' mandate oggi
    today = datetime.date.today().isoformat()
    fresh = datetime.date.fromtimestamp(os.path.getmtime(paths[0])).isoformat()
    st = _story_state()
    if st.get("last") == today or fresh != today:
        return
    try:
        user = bot.get_user(int(oid)) or await bot.fetch_user(int(oid))
        if user and await _send_stories(user):
            st["last"] = today
            json.dump(st, open(STORY_STATE, "w", encoding="utf-8"))
            print("story DM inviate all'owner")
    except Exception as e:
        print("story DM err:", e)


@daily_story_dm.before_loop
async def _before_story():
    await bot.wait_until_ready()


if __name__ == "__main__":
    bot.run(CFG["token"])
