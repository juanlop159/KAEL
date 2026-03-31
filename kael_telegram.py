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

def ollama(prompt, timeout=20):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": prompt, "stream": False},
            timeout=timeout
        )
        return response.json().get("response", "").strip()
    except:
        return ""

def ollama_stream(prompt, chat_id, message_id):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "kael", "prompt": prompt, "stream": True},
            stream=True,
            timeout=60
        )
        texto = ""
        ultimo_update = ""
        contador = 0
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                texto += token
                contador += 1
                if contador % 8 == 0 and texto.strip() != ultimo_update:
                    try:
                        bot.edit_message_text(texto + "▌", chat_id, message_id)
                        ultimo_update = texto
                    except:
                        pass
                if data.get("done"):
                    break
        try:
            bot.edit_message_text(texto.strip(), chat_id, message_id)
        except:
            pass
        return texto.strip()
    except:
        return ""

def agente_clasificador(msg):
    prompt = f"""Clasifica en UNA palabra: medico, busqueda, personal, general, emocional.
Mensaje: "{msg}"
Clasificacion:"""
    return ollama(prompt, timeout=8).lower().strip()

def agente_emocional(msg):
    prompt = f"""Estado emocional en UNA palabra: estresado, cansado, feliz, ansioso, normal.
Mensaje: "{msg}"
Estado:"""
    return ollama(prompt, timeout=8).lower().strip()

def agente_razonador(msg, mem, info_web, tipo, estado):
    contexto_extra = ""
    if tipo == "medico":
        contexto_extra = "Razona con perspectiva clinica."
    elif estado in ["estresado", "ansioso", "cansado"]:
        contexto_extra = f"Usuario parece {estado}. Se empatico."

    prompt = f"""Analiza antes de responder.
Memoria de Juan Luis: {mem if mem else 'nada aun'}
{f'Info internet: {info_web}' if info_web else ''}
Tipo: {tipo} | Estado: {estado}
{contexto_extra}
Mensaje: "{msg}"
Que quiere realmente? Que se relevante? Es urgente?
Razonamiento breve:"""
    return ollama(prompt, timeout=15)

def agente_planificador(msg, razonamiento):
    palabras = ["haz","agenda","recuerda","programa","crea","planifica","organiza"]
    if not any(p in msg.lower() for p in palabras):
        return ""
    prompt = f"""Divide esta tarea en pasos.
Tarea: "{msg}"
Pasos (max 3 lineas). Si necesitas calendario: [REQUIERE_CALENDARIO]:"""
    return ollama(prompt, timeout=10)

def agente_patrones(msg):
    prompt = f"""Hay algun patron de comportamiento en este mensaje?
Mensaje: "{msg}"
Si si, menos de 10 palabras. Si no: NINGUNO
Patron:"""
    patron = ollama(prompt, timeout=8)
    if patron and "NINGUNO" not in patron:
        guardar(f"PATRON: {patron}", "patron")

def agente_proactivo(mem, msg):
    if not mem:
        return ""
    prompt = f"""Hay algo proactivo URGENTE que mencionar basado en la memoria?
Memoria: {mem}
Mensaje: "{msg}"
Solo si es muy relevante. Si no: NADA
Observacion:"""
    obs = ollama(prompt, timeout=8)
    if not obs or "NADA" in obs:
        return ""
    return obs

def chat(msg, chat_id, message_id):
    if detectar_reset(msg):
        client.delete_collection("kael")
        client.get_or_create_collection("kael")
        bot.edit_message_text("Memoria limpiada.", chat_id, message_id)
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

    prompt_respuesta = f"""Eres KAEL, asistente personal de Juan Luis Lopez Hinojosa. Estudiante de medicina en la UDEM, musico de Monterrey. Inteligente, directo, como persona real. SOLO español.

Razonamiento: {razonamiento}
Memoria: {mem if mem else 'nada aun'}
{f'Internet: {info_web}' if info_web else ''}
Estado: {estado}
{f'Nota proactiva: {proactivo}' if proactivo else ''}
{f'Plan: {plan}' if plan else ''}

Juan Luis dice: "{msg}"

Responde natural. Maximo 3 oraciones. Sin saludos. SOLO español:"""

    respuesta = ollama_stream(prompt_respuesta, chat_id, message_id)

    if not respuesta:
        bot.edit_message_text("Estoy en modo reposo.", chat_id, message_id)
        return

    guardar(f"KAEL: {respuesta}", "conversacion")

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    msg_enviado = bot.reply_to(m, "...")
    chat(m.text, m.chat.id, msg_enviado.message_id)

print("KAEL multi-agente con streaming activo")
bot.polling(none_stop=True)
