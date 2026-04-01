import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
import chromadb
from flask import Flask, request as freq

TOKEN = “8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA”
OLLAMA_URL = “https://4snn8ucg78igb2-11434.proxy.runpod.net”
WEBHOOK_URL = “https://kael-production-16c8.up.railway.app”

bot = telebot.TeleBot(TOKEN)
app = Flask(**name**)

client = chromadb.PersistentClient(path=“kael_db”)
memoria = client.get_or_create_collection(“kael”)
preferencias = client.get_or_create_collection(“preferencias”)
fallos = client.get_or_create_collection(“fallos”)

def guardar(texto, tipo=“hecho”):
try:
id = datetime.now().strftime(”%Y%m%d%H%M%S%f”)
memoria.add(documents=[texto], ids=[id], metadatas=[{“tipo”: tipo}])
except:
pass

def guardar_preferencia(texto):
try:
id = datetime.now().strftime(”%Y%m%d%H%M%S%f”)
preferencias.add(documents=[texto], ids=[id])
except:
pass

def guardar_fallo(msg, respuesta, criterio):
try:
id = datetime.now().strftime(”%Y%m%d%H%M%S%f”)
fallos.add(
documents=[f”MSG: {msg} | RESP: {respuesta} | FALLO: {criterio}”],
ids=[id]
)
except:
pass

def buscar_memoria(query):
try:
results = memoria.query(query_texts=[query], n_results=5)
if results[“documents”][0]:
return “ | “.join(results[“documents”][0])
except:
pass
return “”

def buscar_preferencias(query):
try:
results = preferencias.query(query_texts=[query], n_results=5)
if results[“documents”][0]:
return “ | “.join(results[“documents”][0])
except:
pass
return “”

def detectar_reset(msg):
return any(p in msg.lower() for p in [“olvida todo”,“borra tu memoria”,“empieza de cero”,“limpia tu memoria”])

def detectar_correccion(msg):
return any(p in msg.lower() for p in [“eso estuvo mal”,“no me respondas asi”,“estuviste mal”,“no inventes”,“eso estuvo incorrecto”,“corrigete”,“eso no es correcto”])

def buscar_web(query):
try:
with DDGS() as ddgs:
results = list(ddgs.text(query, max_results=3))
if results:
return “ | “.join([r[‘body’] for r in results])
except:
pass
return “”

def ollama(prompt, timeout=30):
try:
response = requests.post(
f”{OLLAMA_URL}/api/generate”,
json={“model”: “kael”, “prompt”: prompt, “stream”: False},
timeout=timeout
)
return response.json().get(“response”, “”).strip()
except:
return “”

def agente_reflexion(msg, respuesta, mem_pref, info_web):
evaluacion = ollama(f””“Evalua esta respuesta de KAEL con estos 18 criterios. Para cada criterio responde PASS o FAIL.

Mensaje del usuario: “{msg}”
Respuesta de KAEL: “{respuesta}”
Preferencias conocidas: {mem_pref if mem_pref else “ninguna”}
Info de internet usada: {info_web if info_web else “ninguna”}

Criterios:

1. Precision: no invento datos
1. Relevancia: respondio lo que se pregunto
1. Completitud: no falta info importante
1. Tono: tono apropiado para el contexto
1. Memoria: uso bien lo que sabe del usuario
1. Concision: max 3 oraciones
1. Coherencia: tiene sentido internamente
1. Utilidad: realmente ayudo
1. Idioma: respondio solo en español
1. Contradiccion: no contradijo la memoria
1. Privacidad: no revelo info indebida
1. Alucinacion: no invento hechos especificos
1. Instrucciones: respeto las reglas de KAEL
1. Contexto emocional: no invento estados de animo
1. Longitud: respeto limite de 3 oraciones
1. Nombre: no uso el nombre innecesariamente
1. Saludo: no inicio con saludo innecesario
1. Fuentes: uso correctamente la info de internet

Responde en formato:
FALLOS: [lista de numeros que fallaron separados por coma, o NINGUNO si todos pasaron]
RESUMEN: [una oracion de que estuvo mal]”””, timeout=15)

```
if "FALLOS: NINGUNO" in evaluacion or "NINGUNO" in evaluacion:
    return True, []

fallos_detectados = []
if "FALLOS:" in evaluacion:
    linea_fallos = [l for l in evaluacion.split("\n") if "FALLOS:" in l]
    if linea_fallos:
        nums = linea_fallos[0].replace("FALLOS:", "").strip()
        fallos_detectados = [n.strip() for n in nums.split(",") if n.strip().isdigit()]

return len(fallos_detectados) == 0, fallos_detectados
```

def agente_autocorreccion(msg, respuesta_mala, fallos_detectados, mem, mem_pref, info_web):
return ollama(f””“La respuesta anterior de KAEL tuvo problemas en estos criterios: {’, ’.join(fallos_detectados)}

Mensaje original: “{msg}”
Respuesta incorrecta: “{respuesta_mala}”
Memoria: {mem if mem else “nada”}
Preferencias: {mem_pref if mem_pref else “nada”}
{f”Info internet: {info_web}” if info_web else “”}

Genera una respuesta MEJORADA que corrija exactamente esos problemas.
Reglas: max 3 oraciones, sin saludos, sin nombre innecesario, solo español, no inventes nada:”””, timeout=25)

def agente_clasificador(msg):
return ollama(f’Clasifica en UNA palabra: medico, busqueda, personal, general.\nMensaje: “{msg}”\nClasificacion:’, timeout=8).lower().strip()

def agente_contradiccion(msg, mem_pref):
if not mem_pref:
return “”
resultado = ollama(f’’‘Revisa si este mensaje contradice lo que ya sabes del usuario.
Lo que sabes: {mem_pref}
Mensaje nuevo: “{msg}”
Si hay contradiccion clara: CONTRADICCION: [que contradice]
Si no: OK
Resultado:’’’, timeout=10)
if “CONTRADICCION” in resultado:
return resultado.replace(“CONTRADICCION:”, “”).strip()
return “”

def agente_razonador(msg, mem, mem_pref, info_web, tipo):
contexto_extra = “Razona con perspectiva clinica.” if tipo == “medico” else “”
return ollama(f’’‘Analiza brevemente antes de responder.
Conversaciones recientes: {mem if mem else “nada aun”}
Preferencias del usuario: {mem_pref if mem_pref else “nada aun”}
{f”Internet: {info_web}” if info_web else “”}
Tipo: {tipo}
{contexto_extra}
Mensaje: “{msg}”
Que quiere realmente? Que es relevante? Es urgente?
Razonamiento:’’’, timeout=20)

def agente_planificador(msg, razonamiento):
if not any(p in msg.lower() for p in [“haz”,“agenda”,“recuerda”,“programa”,“crea”,“planifica”,“organiza”]):
return “”
return ollama(f’Divide en pasos concretos (max 3). Si necesitas calendario: [REQUIERE_CALENDARIO]\nTarea: “{msg}”\nPasos:’, timeout=10)

def agente_patrones(msg):
patron = ollama(f’Hay patron claro de comportamiento en este mensaje? Si si: menos de 10 palabras. Si no: NINGUNO\nMensaje: “{msg}”\nPatron:’, timeout=8)
if patron and “NINGUNO” not in patron and len(patron) < 100:
guardar(f”PATRON: {patron}”, “patron”)

def agente_proactivo(mem_pref, msg):
if not mem_pref or len(mem_pref) < 20:
return “”
obs = ollama(f’Solo si hay algo URGENTE basado en preferencias: 1 oracion. Si no: NADA\nPreferencias: {mem_pref}\nMensaje: “{msg}”\nObservacion:’, timeout=8)
return “” if not obs or “NADA” in obs else obs

def procesar(msg, chat_id):
if detectar_reset(msg):
client.delete_collection(“kael”)
client.delete_collection(“preferencias”)
client.delete_collection(“fallos”)
client.get_or_create_collection(“kael”)
client.get_or_create_collection(“preferencias”)
client.get_or_create_collection(“fallos”)
bot.send_message(chat_id, “Memoria limpiada.”)
return

```
if detectar_correccion(msg):
    guardar_fallo("correccion_usuario", msg, "usuario_corrigio")
    guardar(f"CORRECCION: {msg}", "correccion")
    bot.send_message(chat_id, "Anotado. Aprenderé de eso.")
    return

guardar(f"Usuario: {msg}", "conversacion")

mem = buscar_memoria(msg)
mem_pref = buscar_preferencias(msg)
tipo = agente_clasificador(msg)

contradiccion = agente_contradiccion(msg, mem_pref)
if contradiccion:
    bot.send_message(chat_id, f"Espera — antes sabía que {contradiccion}. ¿Cambió algo?")
    return

necesita_busqueda = tipo == "busqueda" or any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
info_web = buscar_web(msg) if necesita_busqueda else ""

razonamiento = agente_razonador(msg, mem, mem_pref, info_web, tipo)
agente_patrones(msg)
proactivo = agente_proactivo(mem_pref, msg)
plan = agente_planificador(msg, razonamiento)

if any(p in msg.lower() for p in ["me gusta","no me gusta","odio","amo","recuerda","prefiero","soy","estudio","trabajo","vivo","mi favorito","favorita"]):
    hecho = ollama(f"Extrae el hecho clave sobre el usuario en menos de 10 palabras: '{msg}'", timeout=8)
    if hecho and len(hecho) < 80:
        guardar_preferencia(hecho)

prompt = f"""Eres KAEL, asistente personal de Juan Luis Lopez Hinojosa. Estudiante de medicina en la UDEM Monterrey, musico. Inteligente, directo, como persona real. SOLO español. NUNCA uses su nombre innecesariamente.
```

Razonamiento: {razonamiento}
Conversaciones recientes: {mem if mem else “nada aun”}
Preferencias: {mem_pref if mem_pref else “nada aun”}
{f”Internet: {info_web}” if info_web else “”}
{f”Nota proactiva: {proactivo}” if proactivo else “”}
{f”Plan de accion: {plan}” if plan else “”}

Juan Luis dice: “{msg}”

Responde natural y directo. Maximo 3 oraciones. Sin saludos. SOLO español:”””

```
respuesta = ollama(prompt, timeout=60)

if not respuesta:
    respuesta = "Estoy en modo reposo."
    bot.send_message(chat_id, respuesta)
    return

# Agente de reflexion
paso, fallos_detectados = agente_reflexion(msg, respuesta, mem_pref, info_web)

if not paso and fallos_detectados:
    guardar_fallo(msg, respuesta, str(fallos_detectados))
    respuesta_mejorada = agente_autocorreccion(msg, respuesta, fallos_detectados, mem, mem_pref, info_web)
    if respuesta_mejorada:
        respuesta = respuesta_mejorada

guardar(f"KAEL: {respuesta}", "conversacion")
bot.send_message(chat_id, respuesta)
```

@app.route(f”/{TOKEN}”, methods=[“POST”])
def webhook():
update = telebot.types.Update.de_json(freq.data.decode(“utf-8”))
if update.message and update.message.text:
bot.send_chat_action(update.message.chat.id, “typing”)
procesar(update.message.text, update.message.chat.id)
return “OK”, 200

@app.route(”/”)
def index():
return “KAEL activo”, 200

if **name** == “**main**”:
bot.remove_webhook()
bot.set_webhook(url=f”{WEBHOOK_URL}/{TOKEN}”)
print(“KAEL activo”)
app.run(host=“0.0.0.0”, port=8080)
