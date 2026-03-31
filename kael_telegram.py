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
        results = memoria.query(query_texts=[query], n_results=3)
        if results["documents"][0]:
            return " | ".join(results["documents"][0])
    except:
        pass
    return ""

def detectar_reset(msg):
    palabras = ["olvida todo","borra tu memoria","resetea","empieza de cero","limpia tu memoria"]
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
    if detectar_reset(msg):
        client.delete_collection("kael")
        client.get_or_create_collection("kael")
        return "Memoria limpiada."

    guardar(f"Usuario: {msg}", "conversacion")

    necesita_busqueda = any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar_web(msg) if necesita_busqueda else ""

    mem = buscar_memoria(msg)

    p = "Eres KAEL, asistente personal inteligente. Conversas de forma natural y directa. Sin saludos repetitivos. Sin inventar datos. En español.\n\n"
    if mem:
        p += f"Contexto relevante: {mem}\n\n"
    if info_web:
        p += f"Info de internet: {info_web}\n\n"
    p += f"Usuario: {msg}\nKAEL:"

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": p, "stream": False},
            timeout=25
        )
        resp = response.json().get("response", "No pude conectarme.").strip()
    except:
        resp = "Estoy en modo reposo."

    guardar(f"KAEL: {resp}", "conversacion")
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL activo")
bot.polling(none_stop=True)
