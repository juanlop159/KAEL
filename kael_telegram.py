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

def ollama(prompt, timeout=25):
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
    prompt = f"""Clasifica este mensaje en UNA palabra: medico, busqueda, personal, general, emocional.
Mensaje: "{msg}"
Clasificacion:"""
    return ollama(prompt, timeout=10).lower().strip()

def agente_emocional(msg):
    prompt = f"""Detecta el estado emocional en este mensaje en UNA palabra: estresado, cansado, feliz, ansioso, normal.
Mensaje: "{msg}"
Estado:"""
    return ollama(prompt, timeout=10).lower().strip()

def agente_razonador(msg, mem, info_web, tipo, estado):
    contexto_extra = ""
    if tipo == "medico":
        contexto_extra = "Razona con perspectiva clinica y cientifica."
    elif tipo == "emocional" or estado in ["estresado", "ansioso", "cansado"]:
        contexto_extra = f"El usuario parece {estado}. Ajusta tu tono con empatia."

    prompt = f"""Eres KAEL. Analiza antes de responder.

Lo que recuerdas de Juan Luis: {mem if mem else 'nada aun'}
{f'Info internet: {info_web}' if info_web else ''}
Tipo de mensaje: {tipo}
Estado emocional detectado: {estado}
{contexto_extra}

Mensaje: "{msg}"

Razonamiento interno:
- Que quiere realmente
- Que se de el que sea relevante
- Hay algo que contradice lo que se
- Es urgente o importante

Razonamiento:"""
    return ollama(prompt, timeout=20)

def agente_critico(respuesta, msg):
    prompt = f"""Revisa esta respuesta de un asistente.
Pregunta: "{msg}"
Respuesta: "{respuesta}"

Inventa datos? Es vaga? Es util?
Si esta bien responde: OK
Si hay problema responde: PROBLEMA: [que esta mal]
Evaluacion:"""
    evaluacion = ollama(prompt, timeout=10)
    return "PROBLEMA" in evaluacion, evaluacion

def agente_proactivo(mem, msg):
    prompt = f"""Basandote en lo que recuerdas del usuario, hay algo proactivo importante que mencionar?
Memoria: {mem}
Mensaje actual: "{msg}"
Solo si hay algo MUY relevante responde con ello en 1 oracion.
Si no hay nada importante responde: NADA
Observacion:"""
    obs = ollama(prompt, timeout=10)
    if "NADA" in obs or not obs:
        return ""
    return obs

def agente_patrones(msg):
    prompt = f"""Este mensaje revela algun patron de comportamiento del usuario?
Mensaje: "{msg}"
Si si, extrae el patron en menos de 10 palabras.
Si no, responde: NINGUNO
Patron:"""
    patron = ollama(prompt, timeout=10)
    if "NINGUNO" not in patron and patron:
        guardar(f"PATRON: {patron}", "patron")

def agente_planificador(msg, razonamiento):
    palabras = ["haz","agenda","recuerda","programa","crea","añade","planifica","organiza"]
    if not any(p in msg.lower() for p in palabras):
        return ""
    prompt = f"""El usuario quiere que hagas algo. Divide la tarea en pasos.
Tarea: "{msg}"
Razonamiento: {razonamiento}

Lista los pasos en menos de 3 lineas.
Si necesitas calendario indica: [REQUIERE_CALENDARIO]
Si necesitas buscar info indica: [REQUIERE_BUSQUEDA]
Pasos:"""
    return ollama(prompt, timeout=15)

def chat(msg):
    if detectar_reset(msg):
        client.delete_collection("kael")
        client.get_or_create_collection("kael")
        return "Memoria limpiada."

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

    prompt_respuesta = f"""Eres KAEL, asistente personal de Juan Luis. Inteligente, directo, como persona real.

Tu razonamiento: {razonamiento}
Memoria relevante: {mem if mem else 'nada aun'}
{f'Info internet: {info_web}' if info_web else ''}
Estado emocional del usuario: {estado}
{f'Nota proactiva: {proactivo}' if proactivo else ''}
{f'Plan de accion: {plan}' if plan else ''}

Juan Luis dice: "{msg}"

Responde natural y directo. Maximo 3 oraciones. Sin saludos formales. Solo español:"""

    respuesta = ollama(prompt_respuesta, timeout=25)

    if not respuesta:
        return "Estoy en modo reposo."

    hay_problema, _ = agente_critico(respuesta, msg)
    if hay_problema:
        respuesta = ollama(f"""Mejora esta respuesta.
Pregunta: "{msg}"
Respuesta con problema: "{respuesta}"
Respuesta mejorada (max 3 oraciones, sin saludos):""", timeout=20)

    if any(p in msg.lower() for p in ["me gusta","no me gusta","odio","amo","recuerda","prefiero","soy","estudio","trabajo","vivo"]):
        hecho = ollama(f"Extrae el hecho clave en menos de 10 palabras: '{msg}'", timeout=10)
        if hecho:
            guardar(hecho, "preferencia")

    guardar(f"KAEL: {respuesta}", "conversacion")
    return respuesta

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL multi-agente activo")
bot.polling(none_stop=True)
