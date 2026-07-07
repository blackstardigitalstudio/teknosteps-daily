# -*- coding: utf-8 -*-
"""
GENERA VOCI — TeknoSteps · Made in Italy.
=========================================
Voci radio TTS neurali (edge-tts, gratis, no-copyright) in 4 lingue: EN/IT/FR/ES.
Il sito sceglie ogni giorno una lingua diversa (rotazione deterministica).
Produce, per ogni lingua, in assets/audio/<lang>/:
  - voice_<kick|clap|bass|hat|lead>.mp3   (hype "di costruzione")
  - greet_<morning|afternoon|evening|night>.mp3  (saluti, + nome citta')
  - city_<nome>.mp3                         (nomi citta')
  - jingle1..3.mp3                          (sigle stazione)
E un vocal brand unico: assets/audio/blackstar.mp3  ("Blackstar on the fire!").

USO:  pip install edge-tts   poi   python genera_voci.py
"""
import asyncio, os
import edge_tts

BASE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(BASE, "assets", "audio")

# voce neurale maschile ed energica per lingua
VOICES = {
    "en": "en-US-GuyNeural",
    "it": "it-IT-DiegoNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
}

BUILD = {
    "en": {"kick": "Feel the kick.", "clap": "Clap it up.", "bass": "Bring the bass.", "hat": "Ride the hats.", "lead": "Take the lead."},
    "it": {"kick": "Senti la cassa.", "clap": "Batti le mani.", "bass": "Dai il basso.", "hat": "Su con gli hi-hat.", "lead": "Prendi la melodia."},
    "fr": {"kick": "Sens le kick.", "clap": "Tape des mains.", "bass": "Envoie la basse.", "hat": "Monte les hi-hats.", "lead": "Prends le lead."},
    "es": {"kick": "Siente el bombo.", "clap": "Aplaude.", "bass": "Sube el bajo.", "hat": "Dale a los hats.", "lead": "Lleva la melodía."},
}
GREET = {
    "en": {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening", "night": "Good night"},
    "it": {"morning": "Buongiorno", "afternoon": "Buon pomeriggio", "evening": "Buonasera", "night": "Buonanotte"},
    "fr": {"morning": "Bonjour", "afternoon": "Bon après-midi", "evening": "Bonsoir", "night": "Bonne nuit"},
    "es": {"morning": "Buenos días", "afternoon": "Buenas tardes", "evening": "Buenas noches", "night": "Buenas noches"},
}
CITIES = {
    "milano": "Milano", "london": "London", "berlin": "Berlin", "paris": "Paris",
    "amsterdam": "Amsterdam", "moscow": "Moscow", "tokyo": "Tokyo", "mumbai": "Mumbai",
    "sydney": "Sydney", "newyork": "New York", "losangeles": "Los Angeles", "saopaulo": "São Paulo",
}
JINGLES = {
    "en": ["TeknoSteps. Global walk, one beat.", "You're listening to TeknoSteps.", "TeknoSteps. Twenty-four seven."],
    "it": ["TeknoSteps. Un solo battito, in tutto il mondo.", "Stai ascoltando TeknoSteps.", "TeknoSteps. Ventiquattro ore su ventiquattro."],
    "fr": ["TeknoSteps. Une seule pulsation, partout.", "Tu écoutes TeknoSteps.", "TeknoSteps. Vingt-quatre heures sur vingt-quatre."],
    "es": ["TeknoSteps. Un solo latido, en todo el mundo.", "Estás escuchando TeknoSteps.", "TeknoSteps. Veinticuatro horas."],
}
SHOUT_TEXT = "Blackstar on the fire!"
SHOUT_VOICE = "en-US-GuyNeural"


async def tts(text, voice, out, rate="+6%"):
    try:
        await edge_tts.Communicate(text, voice, rate=rate).save(out)
        print("  [OK]", os.path.relpath(out, BASE))
    except Exception as e:
        print("  [!]", os.path.relpath(out, BASE), "->", str(e)[:70])


async def main():
    for lang, voice in VOICES.items():
        d = os.path.join(AUDIO, lang); os.makedirs(d, exist_ok=True)
        print(f"== {lang} ({voice}) ==")
        for k, txt in BUILD[lang].items():
            await tts(txt, voice, os.path.join(d, f"voice_{k}.mp3"))
        for k, txt in GREET[lang].items():
            await tts(txt, voice, os.path.join(d, f"greet_{k}.mp3"), rate="+0%")
        for cid, name in CITIES.items():
            await tts(name, voice, os.path.join(d, f"city_{cid}.mp3"), rate="+0%")
        for i, txt in enumerate(JINGLES[lang], 1):
            await tts(txt, voice, os.path.join(d, f"jingle{i}.mp3"))
    print("== brand shout ==")
    await tts(SHOUT_TEXT, SHOUT_VOICE, os.path.join(AUDIO, "blackstar.mp3"), rate="+8%")
    print("\nFatto. Voci in assets/audio/<lang>/ + assets/audio/blackstar.mp3")


if __name__ == "__main__":
    asyncio.run(main())
