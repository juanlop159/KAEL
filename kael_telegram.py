import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
import chromadb
from flask import Flask, request

TOKEN = "8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA"
OLLAMA_URL = "https://4snn8ucg78igb2-11434.proxy.runpod.net"
WEBHOOK_URL = "https://kael-production-16c8.up.railway.app"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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

def detectar_reset(msg):
    return any(p in msg.lower() for p in ["olvida todo","borra tu memoria","empieza de cero","limpia tu memoria"])

def buscar_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return " | ".join([r['body'] for r in results])
    except:
        pass
    return ""

def ollama(prompt, timeout=30):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": prompt, "stream": False},
            timeout=timeout
        )
        return response.json().get("response", "").strip()
    except:
        return ""

def agente_clasificador(msg):
    return ollama(f'Clasifica en UNA palabra: medico, busqueda, personal, general, emocional.\nMensaje: "{msg}"\nClasificacion:', timeout=8).lower().strip()

def agente_emocional(msg):
    return ollama(f'Estado emocional en UNA palabra: estresado, cansado, feliz, ansioso, normal.\nMensaje: "{msg}"\nEstado:', timeout=8).lower().strip()

def agente_razonador(msg, mem, info_web, tipo, estado):
    contexto_extra = "Razona con perspectiva clinica." if tipo == "medico" else f"Usuario parece {estado}. Se empatico." if estado in ["estresado","ansioso","cansado"] else ""
    return ollama(f'''Analiza antes de responder.
Memoria: {mem if mem else "nada"}
{f"Internet: {info_web}" if info_web else ""}
Tipo: {tipo} | Estado: {estado}
{contexto_extra}
Mensaje: "{msg}"
Que quiere? Que es relevante? Es urgente?
Razonamiento:''', timeout=20)

def agente_planificador(msg, razonamiento):
    if not any(p in msg.lower() for p in ["haz","agenda","recuerda","programa","crea","planifica","organiza"]):
        return ""
    return ollama(f'Divide en pasos (max 3). Si necesitas calendario: [REQUIERE_CALENDARIO]\nTarea: "{msg}"\nPasos:', timeout=10)

def agente_patrones(msg):
    patron = ollama(f'Patron de comportamiento en este mensaje? Si si, menos de 10 palabras. Si no: NINGUNO\nMensaje: "{msg}"\nPatron:', timeout=8)
    if patron and "NINGUNO" not in patron:
        guardar(f"PATRON: {patron}", "patron")

def agente_proactivo(mem, msg):
    if not mem:
        return ""
    obs = ollama(f'Algo proactivo urgente basado en memoria?\nMemoria: {mem}\nMensaje: "{msg}"\nSolo si es relevante. Si no: NADA\nObservacion:', timeout=8)
    return "" if not obs or "NADA" in obs else obs

def procesar(msg, chat_id):
    if detectar_reset(msg):
        client.delete_collection("kael")
        client.get_or_create_collection("kael")
        bot.send_message(chat_id, "Memoria limpiada.")
        return

    guardar(f"Usuario: {msg}", "conversacion")
    mem = buscar_memoria(msg)
    tipo = agente_clasificador(msg)
    estado = agente_emocional(msg)

    necesita_busqueda = tipo == "busqueda" or any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar_web(msg) if necesita_busqueda else ""

    razonamiento = agente_razonador(msg, mem, info_web, tipo, estado)
    agente_patrones(msg)
    proactivo = agente_proactivo(mem, msg)
    plan = agente_planificador(msg, razonamiento)

    if any(p in msg.lower() for p in ["me gusta","no me gusta","odio","amo","recuerda","prefiero","soy","estudio","trabajo","vivo"]):
        hecho = ollama(f"Hecho clave en menos de 10 palabras: '{msg}'", timeout=8)
        if hecho:
            guardar(hecho, "preferencia")

    prompt = f"""Eres KAEL, asistente personal de Juan Luis Lopez Hinojosa. Estudiante de medicina en la UDEM, musico de Monterrey. Directo, inteligente, como persona real. SOLO español.

Razonamiento: {razonamiento}
Memoria: {mem if mem else "nada"}
{f"Internet: {info_web}" if info_web else ""}
Estado: {estado}
{f"Nota proactiva: {proactivo}" if proactivo else ""}
{f"Plan: {plan}" if plan else ""}

Juan Luis dice: "{msg}"

Responde natural. Maximo 3 oraciones. Sin saludos. SOLO español:"""

    respuesta = ollama(prompt, timeout=60)

    if not respuesta:
        respuesta = "Estoy en modo reposo."

    guardar(f"KAEL: {respuesta}", "conversacion")
    bot.send_message(chat_id, respuesta)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    if update.message and update.message.text:
        bot.send_chat_action(update.message.chat.id, "typing")
        procesar(update.message.text, update.message.chat.id)
    return "OK", 200

@app.route("/")
def index():
    return "KAEL activo", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    print("KAEL webhook activo")
    app.run(host="0.0.0.0", port=8080)
