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
    m = m[-20:]
    with open(MF, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def save_larga(hecho):
    m = load(ML)
    if hecho not in m:
        m.append(hecho)
    with open(ML, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def detectar_preferencia(msg):
    palabras = ["no me llames","prefiero","no me digas","me gusta","no me gusta","recuerda","soy","me llamo","estudio","trabajo","vivo","odio","amo","mi color","mi peli","mi cancion","llamame"]
    return any(p in msg.lower() for p in palabras)

def buscar_memoria_relevante(msg):
    largo = load(ML)
    if not largo:
        return ""
    palabras_msg = set(msg.lower().split())
    relevantes = []
    for hecho in largo:
        palabras_hecho = set(hecho.lower().split())
        if palabras_msg & palabras_hecho:
            relevantes.append(hecho)
    if relevantes:
        return "Recuerdas esto relevante: " + " | ".join(relevantes[:3])
    return ""

def buscar(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return " | ".join([r['body'] for r in results])
    except:
        pass
    return ""

def chat(msg):
    if detectar_preferencia(msg):
        extrae = subprocess.run(
            ["ollama", "run", "kael", f"Extrae el hecho clave de esta frase en menos de 10 palabras: '{msg}'"],
            capture_output=True, text=True, timeout=60
        )
        hecho = extrae.stdout.strip()
        if hecho:
            save_larga(hecho)

    necesita_busqueda = any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar(msg) if necesita_busqueda else ""

    mem_relevante = buscar_memoria_relevante(msg)
    corto = load(MF)

    p = ""
    if mem_relevante:
        p += f"{mem_relevante}\n\n"
    if corto:
        p += "Ultimos mensajes:\n" + "\n".join([f"JL: {x['u']}" for x in corto[-3:]]) + "\n\n"
    if info_web:
        p += f"Info internet: {info_web}\n\n"
    p += f"JL dice: {msg}\nResponde directo, maximo 2 oraciones, sin saludos, sin emojis."

    r = subprocess.run(["ollama", "run", "kael", p], capture_output=True, text=True, timeout=300)
    resp = r.stdout.strip()
    save_corta(msg, resp)
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL activo")
bot.polling(none_stop=True)
