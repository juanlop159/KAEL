import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS

TOKEN = "8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA"
MF = "kael_memoria.json"
ML = "kael_largo_plazo.json"
OLLAMA_URL = "https://4snn8ucg78igb2-11434.proxy.runpod.net"
bot = telebot.TeleBot(TOKEN)

def load(f):
    if os.path.exists(f):
        with open(f) as x:
            return json.load(x)
    return []

def save_corta(u, k):
    m = load(MF)
    m.append({"f": str(datetime.now()), "u": u, "k": k})
    m = m[-10:]
    with open(MF, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def save_larga(hecho):
    m = load(ML)
    if hecho not in m:
        m.append(hecho)
    with open(ML, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def detectar_correccion(msg):
    palabras = ["eso estuvo mal","no me respondas asi","no hagas eso","estuviste mal","no inventes","eso estuvo incorrecto","no me digas asi","corrigete"]
    return any(p in msg.lower() for p in palabras)

def detectar_preferencia(msg):
    palabras = ["no me llames","prefiero","no me digas","me gusta","no me gusta","recuerda","soy","me llamo","estudio","trabajo","vivo","odio","amo","mi color","mi peli","mi cancion","llamame"]
    return any(p in msg.lower() for p in palabras)

def ctx():
    largo = load(ML)
    if not largo:
        return ""
    return "Hechos y reglas del usuario: " + ", ".join(largo[:8]) + "\n\n"

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
    if detectar_correccion(msg):
        save_larga(f"REGLA: Nunca hacer esto: {msg}")

    if detectar_preferencia(msg):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "kael", "prompt": f"Extrae el hecho clave en menos de 8 palabras: '{msg}'", "stream": False},
                timeout=60
            )
            hecho = response.json().get("response", "").strip()
            if hecho:
                save_larga(hecho)
        except:
            pass

    necesita_busqueda = any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar(msg) if necesita_busqueda else ""

    p = ctx()
    if info_web:
        p += f"Info internet: {info_web}\n\n"
    p += f"Usuario dice: {msg}\nResponde en UNA oracion. Sin saludos. Sin inventar nada."

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": p, "stream": False},
            timeout=120
        )
        resp = response.json().get("response", "No pude conectarme al servidor.").strip()
    except:
        resp = "Estoy en modo reposo. Enciéndeme para respuestas completas."

    save_corta(msg, resp)
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL activo")
bot.polling(none_stop=True)
