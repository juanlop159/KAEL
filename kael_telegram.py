import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
import chromadb

TOKEN = "8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA"
OLLAMA_URL = "https://4snn8ucg78igb2-11434.proxy.runpod.net"
bot = telebot.TeleBot(TOKEN)

client = chromadb.PersistentClient(path="kael_db")
memoria = client.get_or_create_collection("kael")

def guardar(texto, tipo="hecho"):
    try:
        id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        memoria.add(documents=[texto], ids=[id], metadatas=[{"tipo": tipo}])
    except:
        pass

def buscar_memoria(query):
    try:
        results = memoria.query(query_texts=[query], n_results=5)
        if results["documents"][0]:
            return " | ".join(results["documents"][0])
    except:
        pass
    return ""

def detectar_correccion(msg):
    palabras = ["eso estuvo mal","no me respondas asi","no hagas eso","estuviste mal","no inventes","eso estuvo incorrecto","no me digas asi","corrigete"]
    return any(p in msg.lower() for p in palabras)

def detectar_preferencia(msg):
    palabras = ["no me llames","prefiero","no me digas","me gusta","no me gusta","recuerda","soy","me llamo","estudio","trabajo","vivo","odio","amo","mi color","mi peli","mi cancion","llamame"]
    return any(p in msg.lower() for p in palabras)

def buscar_web(query):
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
        guardar(f"REGLA: Nunca hacer esto: {msg}", "regla")

    if detectar_preferencia(msg):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "kael", "prompt": f"Extrae el hecho clave en menos de 8 palabras: '{msg}'", "stream": False},
                timeout=60
            )
            hecho = response.json().get("response", "").strip()
            if hecho:
                guardar(hecho, "preferencia")
        except:
            pass

    guardar(f"Usuario dijo: {msg}", "conversacion")

    necesita_busqueda = any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar_web(msg) if necesita_busqueda else ""

    mem = buscar_memoria(msg)

    p = ""
    if mem:
        p += f"Lo que recuerdas relevante: {mem}\n\n"
    if info_web:
        p += f"Info internet: {info_web}\n\n"
    p += f"Usuario dice: {msg}\nResponde en UNA oracion. SOLO usa informacion que tienes en memoria. Si no tienes el dato exacto di que no lo sabes. Sin saludos."

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": p, "stream": False},
            timeout=120
        )
        resp = response.json().get("response", "No pude conectarme.").strip()
    except:
        resp = "Estoy en modo reposo. Enciéndeme para respuestas completas."

    guardar(f"KAEL respondio: {resp}", "conversacion")
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL con memoria vectorial activo")
bot.polling(none_stop=True)
