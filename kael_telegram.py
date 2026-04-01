import telebot
import requests
import json
import os
from datetime import datetime
from duckduckgo_search import DDGS
import chromadb
from flask import Flask, request as freq
import threading

TOKEN = “8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA”
OLLAMA_URL = “https://4snn8ucg78igb2-11434.proxy.runpod.net”
WEBHOOK_URL = “https://kael-production-16c8.up.railway.app”

bot = telebot.TeleBot(TOKEN)
app = Flask(**name**)

client = chromadb.PersistentClient(path=“kael_db”)
memoria = client.get_or_create_collection(“kael”)
preferencias = client.get_or_create_collection(“preferencias”)
fallos = client.get_or_create_collection(“fallos”)
meta_log = client.get_or_create_collection(“meta_log”)

# ─── META-AGENTE: ESTADO ────────────────────────────────────────────────────

meta_estado = {
“correcciones_seguidas”: 0,
“fallos_por_agente”: {},
“total_conversaciones”: 0,
“cambios_pendientes”: [],
“agentes_desactivados”: [],
“timeouts”: {
“clasificador”: 8,
“reflexion”: 15,
“autocorreccion”: 25,
“razonador”: 20,
“planificador”: 10,
“patrones”: 8,
“proactivo”: 8,
“contradiccion”: 10,
}
}

REGLAS_CONSTITUCIONALES = [
“token”, “ollama_url”, “webhook_url”,
“reglas constitucionales”, “7 filtros”, “agente_p53”, “seguridad”
]

def meta_registrar_fallo(agente, msg, respuesta, criterio):
try:
id = datetime.now().strftime(”%Y%m%d%H%M%S%f”)
fallos.add(
documents=[f”AGENTE: {agente} | MSG: {msg} | RESP: {respuesta} | FALLO: {criterio}”],
ids=[id]
)
meta_estado[“fallos_por_agente”][agente] = meta_estado[“fallos_por_agente”].get(agente, 0) + 1
except:
pass

def meta_agente_proponer():
propuestas = []
for agente, count in meta_estado[“fallos_por_agente”].items():
if count >= 3:
propuestas.append(f”Ajustar prompt del agente ‘{agente}’ — ha fallado {count} veces”)
if count >= 2 and meta_estado[“timeouts”].get(agente, 30) < 30:
propuestas.append(f”Aumentar timeout de ‘{agente}’ de {meta_estado[‘timeouts’].get(agente)}s a {meta_estado[‘timeouts’].get(agente)+10}s”)
if meta_estado[“correcciones_seguidas”] >= 2:
propuestas.append(“Revisar prompt principal de KAEL — 2 correcciones seguidas del usuario”)
return propuestas

def meta_agente_evaluar(chat_id):
lineas = [“Evaluacion del sistema KAEL:\n”]
if meta_estado[“fallos_por_agente”]:
lineas.append(“Fallos por agente:”)
for agente, count in meta_estado[“fallos_por_agente”].items():
lineas.append(f”  - {agente}: {count} fallos”)
else:
lineas.append(“Sin fallos registrados.”)
if meta_estado[“agentes_desactivados”]:
lineas.append(f”\nAgentes desactivados: {’, ’.join(meta_estado[‘agentes_desactivados’])}”)
lineas.append(f”\nConversaciones totales: {meta_estado[‘total_conversaciones’]}”)
propuestas = meta_agente_proponer()
if propuestas:
lineas.append(”\nPropuestas de mejora:”)
for i, p in enumerate(propuestas, 1):
lineas.append(f”  {i}. {p}”)
lineas.append(”\nResponde ‘aplicar mejoras’ para implementarlas (con tu aprobacion).”)
bot.send_message(chat_id, “\n”.join(lineas))

def meta_agente_aplicar(chat_id):
propuestas = meta_agente_proponer()
if not propuestas:
bot.send_message(chat_id, “No hay mejoras pendientes.”)
return
aplicadas = []
for p in propuestas:
if any(r in p.lower() for r in REGLAS_CONSTITUCIONALES):
bot.send_message(chat_id, f”No puedo aplicar: ‘{p}’ — viola reglas constitucionales.”)
continue
if “timeout” in p.lower():
for agente in meta_estado[“timeouts”]:
if agente in p.lower():
meta_estado[“timeouts”][agente] += 10
aplicadas.append(f”Timeout de ‘{agente}’ -> {meta_estado[‘timeouts’][agente]}s”)
try:
meta_log.add(
documents=[f”CAMBIO: {p} | {str(datetime.now())}”],
ids=[datetime.now().strftime(”%Y%m%d%H%M%S%f”)]
)
except:
pass
meta_estado[“cambios_pendientes”] = []
if aplicadas:
bot.send_message(chat_id, “Mejoras aplicadas:\n” + “\n”.join([f”- {a}” for a in aplicadas]))
else:
bot.send_message(chat_id, “No se aplicaron cambios.”)

def meta_agente_cada_50(chat_id):
if meta_estado[“total_conversaciones”] % 50 == 0 and meta_estado[“total_conversaciones”] > 0:
propuestas = meta_agente_proponer()
if propuestas:
bot.send_message(chat_id, “Evaluacion automatica (cada 50 conversaciones):\n” +
“\n”.join([f”- {p}” for p in propuestas]) +
“\n\nResponde ‘aplicar mejoras’ si quieres que las implemente.”)

def agente_activo(nombre):
return nombre not in meta_estado[“agentes_desactivados”]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

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
meta_registrar_fallo(“reflexion”, msg, respuesta, criterio)

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

def detectar_evaluacion(msg):
return any(p in msg.lower() for p in [“evalúate”,“evalulate”,“mejórate”,“mejorate”,“como vas”,“analízate”,“estado del sistema”])

def buscar_web(query):
if not agente_activo(“busqueda”):
return “”
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

# ─── AGENTES ─────────────────────────────────────────────────────────────────

def agente_reflexion(msg, respuesta, mem_pref, info_web):
if not agente_activo(“reflexion”):
return True, []
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
RESUMEN: [una oracion de que estuvo mal]”””, timeout=meta_estado[“timeouts”][“reflexion”])

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
if not agente_activo(“autocorreccion”):
return respuesta_mala
return ollama(f””“La respuesta anterior de KAEL tuvo problemas en estos criterios: {’, ’.join(fallos_detectados)}

Mensaje original: “{msg}”
Respuesta incorrecta: “{respuesta_mala}”
Memoria: {mem if mem else “nada”}
Preferencias: {mem_pref if mem_pref else “nada”}
{f”Info internet: {info_web}” if info_web else “”}

Genera una respuesta MEJORADA que corrija exactamente esos problemas.
Reglas: max 3 oraciones, sin saludos, sin nombre innecesario, solo español, no inventes nada:”””,
timeout=meta_estado[“timeouts”][“autocorreccion”])

def agente_clasificador(msg):
if not agente_activo(“clasificador”):
return “general”
return ollama(
f’Clasifica en UNA palabra: medico, busqueda, personal, general.\nMensaje: “{msg}”\nClasificacion:’,
timeout=meta_estado[“timeouts”][“clasificador”]
).lower().strip()

def agente_contradiccion(msg, mem_pref):
if not agente_activo(“contradiccion”) or not mem_pref:
return “”
resultado = ollama(f’’‘Revisa si este mensaje contradice lo que ya sabes del usuario.
Lo que sabes: {mem_pref}
Mensaje nuevo: “{msg}”
Si hay contradiccion clara: CONTRADICCION: [que contradice]
Si no: OK
Resultado:’’’, timeout=meta_estado[“timeouts”][“contradiccion”])
if “CONTRADICCION” in resultado:
return resultado.replace(“CONTRADICCION:”, “”).strip()
return “”

def agente_razonador(msg, mem, mem_pref, info_web, tipo):
if not agente_activo(“razonador”):
return “”
contexto_extra = “Razona con perspectiva clinica.” if tipo == “medico” else “”
return ollama(f’’‘Analiza brevemente antes de responder.
Conversaciones recientes: {mem if mem else “nada aun”}
Preferencias del usuario: {mem_pref if mem_pref else “nada aun”}
{f”Internet: {info_web}” if info_web else “”}
Tipo: {tipo}
{contexto_extra}
Mensaje: “{msg}”
Que quiere realmente? Que es relevante? Es urgente?
Razonamiento:’’’, timeout=meta_estado[“timeouts”][“razonador”])

def agente_planificador(msg, razonamiento):
if not agente_activo(“planificador”):
return “”
if not any(p in msg.lower() for p in [“haz”,“agenda”,“recuerda”,“programa”,“crea”,“planifica”,“organiza”]):
return “”
return ollama(f’Divide en pasos concretos (max 3). Si necesitas calendario: [REQUIERE_CALENDARIO]\nTarea: “{msg}”\nPasos:’,
timeout=meta_estado[“timeouts”][“planificador”])

def agente_patrones(msg):
if not agente_activo(“patrones”):
return
patron = ollama(
f’Hay patron claro de comportamiento en este mensaje? Si si: menos de 10 palabras. Si no: NINGUNO\nMensaje: “{msg}”\nPatron:’,
timeout=meta_estado[“timeouts”][“patrones”]
)
if patron and “NINGUNO” not in patron and len(patron) < 100:
guardar(f”PATRON: {patron}”, “patron”)

def agente_proactivo(mem_pref, msg):
if not agente_activo(“proactivo”) or not mem_pref or len(mem_pref) < 20:
return “”
obs = ollama(
f’Solo si hay algo URGENTE basado en preferencias: 1 oracion. Si no: NADA\nPreferencias: {mem_pref}\nMensaje: “{msg}”\nObservacion:’,
timeout=meta_estado[“timeouts”][“proactivo”]
)
return “” if not obs or “NADA” in obs else obs

# ─── PROCESADOR CON STREAMING ────────────────────────────────────────────────

def procesar_stream(msg, chat_id):
meta_estado[“total_conversaciones”] += 1

```
if detectar_reset(msg):
    client.delete_collection("kael")
    client.delete_collection("preferencias")
    client.delete_collection("fallos")
    client.get_or_create_collection("kael")
    client.get_or_create_collection("preferencias")
    client.get_or_create_collection("fallos")
    meta_estado["fallos_por_agente"] = {}
    meta_estado["correcciones_seguidas"] = 0
    bot.send_message(chat_id, "Memoria limpiada.")
    return

if detectar_correccion(msg):
    meta_estado["correcciones_seguidas"] += 1
    guardar_fallo(msg, "", "usuario_corrigio")
    guardar(f"CORRECCION: {msg}", "correccion")
    if meta_estado["correcciones_seguidas"] >= 2:
        bot.send_message(chat_id, "Anotado. Detecto 2 correcciones seguidas — evaluando el sistema.")
        meta_agente_evaluar(chat_id)
    else:
        bot.send_message(chat_id, "Anotado. Aprenderé de eso.")
    return

if detectar_evaluacion(msg):
    meta_agente_evaluar(chat_id)
    return

if "aplicar mejoras" in msg.lower():
    meta_estado["cambios_pendientes"] = meta_agente_proponer()
    if meta_estado["cambios_pendientes"]:
        bot.send_message(chat_id, f"Voy a aplicar {len(meta_estado['cambios_pendientes'])} mejoras. Confirmas? Responde 'si confirmo'")
    else:
        bot.send_message(chat_id, "No hay mejoras pendientes.")
    return

if "si confirmo" in msg.lower() and meta_estado["cambios_pendientes"]:
    meta_agente_aplicar(chat_id)
    return

if not detectar_correccion(msg):
    meta_estado["correcciones_seguidas"] = 0

guardar(f"Usuario: {msg}", "conversacion")

mem = buscar_memoria(msg)
mem_pref = buscar_preferencias(msg)
tipo = agente_clasificador(msg)

contradiccion = agente_contradiccion(msg, mem_pref)
if contradiccion:
    bot.send_message(chat_id, f"Espera — antes sabia que {contradiccion}. Cambio algo?")
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
# Streaming — manda mensaje vacío y lo va editando
mensaje_id = bot.send_message(chat_id, "...").message_id
respuesta_completa = ""
ultimo_update = ""

try:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "kael", "prompt": prompt, "stream": True},
        stream=True,
        timeout=120
    )
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            token = chunk.get("response", "")
            respuesta_completa += token
            if len(respuesta_completa) - len(ultimo_update) > 15:
                try:
                    bot.edit_message_text(respuesta_completa, chat_id, mensaje_id)
                    ultimo_update = respuesta_completa
                except:
                    pass
            if chunk.get("done"):
                break
    if respuesta_completa:
        bot.edit_message_text(respuesta_completa, chat_id, mensaje_id)
except:
    if not respuesta_completa:
        bot.edit_message_text("Estoy en modo reposo.", chat_id, mensaje_id)
        return

paso, fallos_detectados = agente_reflexion(msg, respuesta_completa, mem_pref, info_web)
if not paso and fallos_detectados:
    guardar_fallo(msg, respuesta_completa, str(fallos_detectados))
    respuesta_mejorada = agente_autocorreccion(msg, respuesta_completa, fallos_detectados, mem, mem_pref, info_web)
    if respuesta_mejorada:
        try:
            bot.edit_message_text(respuesta_mejorada, chat_id, mensaje_id)
            respuesta_completa = respuesta_mejorada
        except:
            pass

guardar(f"KAEL: {respuesta_completa}", "conversacion")
meta_agente_cada_50(chat_id)
```

# ─── WEBHOOK ─────────────────────────────────────────────────────────────────

@app.route(f”/{TOKEN}”, methods=[“POST”])
def webhook():
update = telebot.types.Update.de_json(freq.data.decode(“utf-8”))
if update.message and update.message.text:
bot.send_chat_action(update.message.chat.id, “typing”)
t = threading.Thread(target=procesar_stream, args=(update.message.text, update.message.chat.id))
t.daemon = True
t.start()
return “OK”, 200

@app.route(”/”)
def index():
return “KAEL activo”, 200

if **name** == “**main**”:
bot.remove_webhook()
bot.set_webhook(url=f”{WEBHOOK_URL}/{TOKEN}”)
print(“KAEL con meta-agente y streaming activo”)
app.run(host=“0.0.0.0”, port=8080)
