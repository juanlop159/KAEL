import telebot
import subprocess
import json
import os
from datetime import datetime
from duckduckgo_search import DDGS

TOKEN = "8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA"
MF = "/workspace/kael_memoria.json"
ML = "/workspace/kael_largo_plazo.json"
bot = telebot.TeleBot(TOKEN)

def load(f):
    if os.path.exists(f):
        with open(f) as x:
            return json.load(x)
    return []

def save_corta(u, k):
    m = load(MF)
    m.append({"f": str(datetime.now()), "u": u, "k": k})
    m = m[-30:]
    with open(MF, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def save_larga(hecho):
    m = load(ML)
    if hecho not in m:
        m.append(hecho)
    with open(ML, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def detectar_preferencia(msg):
    palabras = ["no me llames","prefiero","no me digas","me gusta","no me gusta","recuerda que","soy","me llamo","estudio","trabajo","vivo","mi color","mi pelicula","mi cancion","odio","amo"]
    return any(p in msg.lower() for p in palabras)

def buscar(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return " | ".join([r['body'] for r in results])
    except:
        pass
    return ""

def ctx():
    largo = load(ML)
    corto = load(MF)
    p = ""
    if largo:
        p += "Lo que sabes de Juan Luis:\n"
        p += "\n".join([f"- {x}" for x in largo])
        p += "\n\n"
    if corto:
        p += "Conversacion reciente:\n"
        p += "\n".join([f"JL: {x['u']}" for x in corto[-5:]])
        p += "\n\n"
    return p

def chat(msg):
    if detectar_preferencia(msg):
        extrae = subprocess.run(
            ["ollama", "run", "kael", f"De este mensaje extrae SOLO el hecho importante sobre Juan Luis en una frase corta, sin explicacion: '{msg}'"],
            capture_output=True, text=True, timeout=60
        )
        hecho = extrae.stdout.strip()
        if hecho:
            save_larga(hecho)

    necesita_busqueda = any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar(msg) if necesita_busqueda else ""

    p = ctx()
    if info_web:
        p += f"Info de internet: {info_web}\n\n"
    p += f"JL dice: {msg}\nResponde como KAEL. Directo, maximo 3 oraciones, sin listas, sin emojis."

    r = subprocess.run(["ollama", "run", "kael", p], capture_output=True, text=True, timeout=120)
    resp = r.stdout.strip()
    save_corta(msg, resp)
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL con memoria inteligente activo")
bot.polling(none_stop=True)
