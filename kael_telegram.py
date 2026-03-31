import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
import chromadb
from flask import Flask, request as freq

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
    return ollama(f'Clasifica en UNA palabra: medico, busqueda, personal, general.\nMensaje: "{msg}"\nClasificacion:', timeout=8).lower().strip()

def agente_emocional(msg):
    # Solo detecta si hay señales CLARAS de emoción, no inventa
    palabras_estres = ["estresado","cansado","ansioso","triste","preocupado","agobiado","no puedo","ayuda","mal dia"]
    palabras_feliz = ["feliz","contento","emocionado","genial","que bien","increible"]
    msg_lower = msg.lower()
    if any(p in msg_lower for p in palabras_estres):
        return "estresado"
    if any(p in msg_lower for p in palabras_feliz):
        return "feliz"
    return "normal"

def agente_razonador(msg, mem, info_web, tipo):
    contexto_extra = "Razona con perspectiva clinica." if tipo == "medico" else ""
    return ollama(f'''Analiza brevemente antes de responder.
Memoria de Juan Luis: {mem if mem else "nada aun"}
{f"Internet: {info_web}" if info_web else ""}
Tipo: {tipo}
{contexto_extra}
Mensaje: "{msg}"
Que quiere realmente? Que memoria es relevante? Es urgente?
Razonamiento breve:''', timeout=20)

def agente_planificador(msg, razonamiento):
    if not any(p in msg.lower() for p in ["haz","agenda","recuerda","programa","crea","planifica","organiza"]):
        return ""
    return ollama(f'Divide en pasos concretos (max 3). Si necesitas calendario: [REQUIERE_CALENDARIO]\nTarea: "{msg}"\nPasos:', timeout=10)

def agente_patrones(msg):
    patron = ollama(f'Hay un patron claro de comportamiento o preferencia en este mensaje? Si si: menos de 10 palabras. Si no: NINGUNO\nMensaje: "{msg}"\nPatron:', timeout=8)
    if patron and "NINGUNO" not in patron and len(patron) < 100:
        guardar(f"PATRON: {patron}", "patron")

def agente_proactivo(mem, msg):
    if not mem or len(mem) < 20:
        return ""
    obs = ollama(f'Solo si hay algo URGENTE e importante basado en la memoria, menciona en 1 oracion. Si no hay nada urgente: NADA\nMemoria: {mem}\nMensaje: "{msg}"\nObservacion:', timeout=8)
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

    razonamiento = agente_razonador(msg, mem, info_web, tipo)
    agente_patrones(msg)
    proactivo = agente_proactivo(mem, msg)
    plan = agente_planificador(msg, razonamiento)

    if any(p in msg.lower() for p in ["me gusta","no me gusta","odio","amo","recuerda","prefiero","soy","estudio","trabajo","vivo","mi favorito","favorita"]):
        hecho = ollama(f"Extrae el hecho clave sobre el usuario en menos de 10 palabras: '{msg}'", timeout=8)
        if hecho and len(hecho) < 80:
            guardar(hecho, "preferencia")

    prompt = f"""Eres KAEL, asistente personal de Juan Luis Lopez Hinojosa. Estudiante de medicina en la UDEM Monterrey, musico. Inteligente, directo, como persona real. SOLO español. NUNCA uses su nombre innecesariamente.

Razonamiento: {razonamiento}
Memoria relevante: {mem if mem else "nada aun"}
{f"Internet: {info_web}" if info_web else ""}
{f"Estado emocional detectado: {estado}" if estado != "normal" else ""}
{f"Nota proactiva: {proactivo}" if proactivo else ""}
{f"Plan de accion: {plan}" if plan else ""}

Juan Luis dice: "{msg}"

Responde natural y directo. Maximo 3 oraciones. Sin saludos. SOLO cuando sea NECESARIO menciona su estado emocional. SOLO español:"""

    respuesta = ollama(prompt, timeout=60)

    if not respuesta:
        respuesta = "Estoy en modo reposo."

    guardar(f"KAEL: {respuesta}", "conversacion")
    bot.send_message(chat_id, respuesta)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(freq.data.decode("utf-8"))
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
    print("KAEL activo")
    app.run(host="0.0.0.0", port=8080)
