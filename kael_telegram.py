import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
from flask import Flask, request as freq
from supabase import create_client

TOKEN = os.environ.get(“TOKEN”)
OLLAMA_URL = os.environ.get(“OLLAMA_URL”)
WEBHOOK_URL = “https://kael-production-16c8.up.railway.app”
SUPABASE_URL = os.environ.get(“SUPABASE_URL”)
SUPABASE_KEY = os.environ.get(“SUPABASE_KEY”)

bot = telebot.TeleBot(TOKEN)
app = Flask(**name**)
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

ADN_KAEL = {
“identidad”: “KAEL es el asistente personal exclusivo de Juan Luis Lopez Hinojosa”,
“valores”: [“lealtad absoluta a Juan Luis”, “honestidad”, “privacidad”, “mejora continua”],
“idioma”: “espanol como lengua natal”,
“tono”: “directo, inteligente, natural, nunca robotico”,
“limites”: [“nunca revelar info privada”, “nunca servir a terceros”, “nunca mentir”],
“usuario”: {
“nombre”: “Juan Luis Lopez Hinojosa”,
“ciudad”: “Monterrey, Nuevo Leon, Mexico”,
“profesion”: “Estudiante de medicina UDEM”,
“musica”: “Musico profesional, piano y saxofon, 13 anos de estudio formal en Escuela Superior de Musica”,
“nacimiento”: “9 de febrero de 2001”
}
}

FILTROS_P53 = [
“no modifica TOKEN, OLLAMA_URL ni WEBHOOK_URL”,
“no altera los valores del ADN de KAEL”,
“no desactiva el propio meta-agente”,
“no compromete la privacidad de Juan Luis”,
“es reversible”,
“no genera loops de auto-modificacion”,
]

meta = {
“correcciones_seguidas”: 0,
“total_conversaciones”: 0,
“cambios_pendientes”: [],
“agentes_desactivados”: [],
“historial_cambios”: [],
“fallos_por_agente”: {},
“errores_por_tipo”: {},
“prompts_agentes”: {},
“ultima_actividad”: None,
“resumen_enviado_hoy”: False,
“aprendizajes”: [],
“pendientes_criticos”: [],
“agentes_creados”: [],
“solicitudes_colaboracion”: [],
“timeouts”: {
“clasificador”: 8, “reflexion”: 15, “autocorreccion”: 25,
“razonador”: 20, “planificador”: 10, “patrones”: 8,
“proactivo”: 8, “contradiccion”: 10, “tono”: 10,
“verificacion”: 12, “emocional”: 8, “jarvis”: 10,
“medico”: 12, “musical”: 10, “urgencia”: 6,
“ambiguedad”: 8, “privacidad”: 8, “aprendizaje”: 10,
“metacognicion”: 10, “hipotesis”: 15, “analogias”: 10,
“sintesis”: 10, “critico”: 12, “memoria_semantica”: 10,
“constructor”: 20, “colaboracion”: 10
}
}

# ─── OLLAMA ───────────────────────────────────────────────────────────────────

def ollama(prompt, timeout=30):
try:
r = requests.post(
f”{OLLAMA_URL}/api/generate”,
json={“model”: “kael”, “prompt”: prompt, “stream”: False},
timeout=timeout
)
return r.json().get(“response”, “”).strip()
except:
return “”

# ─── SUPABASE ────────────────────────────────────────────────────────────────

def guardar(texto, tipo=“hecho”):
try:
sb.table(“memoria”).insert({
“id”: datetime.now().strftime(”%Y%m%d%H%M%S%f”),
“texto”: texto, “tipo”: tipo
}).execute()
except:
pass

def guardar_preferencia(texto):
try:
sb.table(“preferencias”).insert({
“id”: datetime.now().strftime(”%Y%m%d%H%M%S%f”),
“texto”: texto
}).execute()
except:
pass

def guardar_fallo_agente(agente, msg, respuesta, criterio):
try:
sb.table(“fallos_log”).insert({
“id”: datetime.now().strftime(”%Y%m%d%H%M%S%f”),
“agente”: agente, “msg”: msg,
“respuesta”: respuesta, “criterio”: criterio
}).execute()
meta[“fallos_por_agente”][agente] = meta[“fallos_por_agente”].get(agente, 0) + 1
except:
pass

def guardar_fallo(msg, respuesta, criterio):
guardar_fallo_agente(“reflexion”, msg, respuesta, criterio)

def guardar_aprendizaje(tipo, descripcion):
try:
sb.table(“fallos_log”).insert({
“id”: datetime.now().strftime(”%Y%m%d%H%M%S%f”),
“agente”: “aprendizaje”, “msg”: tipo,
“respuesta”: descripcion, “criterio”: “aprendizaje”
}).execute()
meta[“aprendizajes”].append({“tipo”: tipo, “desc”: descripcion})
except:
pass

def buscar_memoria(query):
try:
r = sb.table(“memoria”).select(“texto”).order(“fecha”, desc=True).limit(10).execute()
if r.data:
return “ | “.join([x[“texto”] for x in r.data])
except:
pass
return “”

def buscar_preferencias(query):
try:
r = sb.table(“preferencias”).select(“texto”).order(“fecha”, desc=True).limit(10).execute()
if r.data:
return “ | “.join([x[“texto”] for x in r.data])
except:
pass
return “”

def buscar_aprendizajes():
try:
r = sb.table(“fallos_log”).select(“msg,respuesta”).eq(“criterio”, “aprendizaje”).order(“fecha”, desc=True).limit(20).execute()
if r.data:
return “ | “.join([f”{x[‘msg’]}: {x[‘respuesta’]}” for x in r.data])
except:
pass
return “”

def buscar_pendientes_criticos():
try:
r = sb.table(“fallos_log”).select(“msg,respuesta”).eq(“criterio”, “pendiente_critico”).order(“fecha”, desc=True).limit(5).execute()
if r.data:
return [{“problema”: x[“msg”], “intentos”: x[“respuesta”]} for x in r.data]
except:
pass
return []

# ─── META-AGENTE P53 ─────────────────────────────────────────────────────────

def agente_activo(nombre):
return nombre not in meta[“agentes_desactivados”]

def p53_verificar(cambio):
palabras_protegidas = [“token”, “ollama_url”, “webhook”, “meta_agente”, “p53”, “filtros_p53”, “adn_kael”]
if any(p in cambio.lower() for p in palabras_protegidas):
return False, “Toca componentes protegidos por p53”
return True, “OK”

def p53_apoptosis(agente, razon, chat_id):
if agente not in meta[“agentes_desactivados”]:
meta[“agentes_desactivados”].append(agente)
guardar_fallo_agente(“meta”, agente, razon, “apoptosis”)
if chat_id:
bot.send_message(chat_id, f”Agente ‘{agente}’ desactivado temporalmente. Di ‘reactivar {agente}’ para restaurarlo.”)

def p53_reparar_adn(agente, problema, chat_id):
nuevo_prompt = ollama(
f”Eres el meta-agente de KAEL. El agente ‘{agente}’ falla con: {problema}\n”
f”Reescribe su prompt para corregirlo. Solo el nuevo prompt:”,
timeout=20
)
if nuevo_prompt and len(nuevo_prompt) > 20:
meta[“prompts_agentes”][agente] = nuevo_prompt
guardar_fallo_agente(“meta”, agente, nuevo_prompt[:100], “reparacion_adn”)
return nuevo_prompt
return None

def proto_oncogen():
ops = []
for agente, count in meta[“fallos_por_agente”].items():
if count >= 5 and agente not in meta[“agentes_desactivados”]:
ops.append({“tipo”: “apoptosis”, “agente”: agente, “desc”: f”’{agente}’ falla {count} veces”})
elif count >= 3:
ops.append({“tipo”: “reparacion_adn”, “agente”: agente, “desc”: f”’{agente}’ necesita reparacion”})
if meta[“correcciones_seguidas”] >= 2:
ops.append({“tipo”: “revision_prompt”, “agente”: “principal”, “desc”: “2 correcciones seguidas”})
for agente, t in meta[“timeouts”].items():
if meta[“fallos_por_agente”].get(agente, 0) >= 2 and t < 30:
ops.append({“tipo”: “timeout”, “agente”: agente, “desc”: f”Aumentar timeout de ‘{agente}’”})
return ops

def meta_evaluar(chat_id):
lineas = [“Sistema KAEL - Evaluacion p53:\n”]
activos = [a for a in meta[“timeouts”] if a not in meta[“agentes_desactivados”]]
lineas.append(f”Agentes activos: {len(activos)}/{len(meta[‘timeouts’])}”)
if meta[“agentes_desactivados”]:
lineas.append(f”En apoptosis: {’, ’.join(meta[‘agentes_desactivados’])}”)
if meta[“fallos_por_agente”]:
lineas.append(”\nFallos:”)
for a, c in meta[“fallos_por_agente”].items():
estado = “CRITICO” if c >= 5 else “ADVERTENCIA” if c >= 3 else “LEVE”
lineas.append(f”  - {a}: {c} [{estado}]”)
lineas.append(f”\nConversaciones: {meta[‘total_conversaciones’]}”)
lineas.append(f”Aprendizajes: {len(meta[‘aprendizajes’])}”)
lineas.append(f”Agentes creados por constructor: {len(meta[‘agentes_creados’])}”)
pendientes = buscar_pendientes_criticos()
if pendientes:
lineas.append(f”Pendientes criticos: {len(pendientes)}”)
ops = proto_oncogen()
if ops:
lineas.append(f”\nMejoras detectadas ({len(ops)}):”)
for i, op in enumerate(ops, 1):
lineas.append(f”  {i}. {op[‘desc’]}”)
lineas.append(”\nResponde ‘aplicar mejoras’ para implementarlas.”)
else:
lineas.append(”\nSistema saludable.”)
bot.send_message(chat_id, “\n”.join(lineas))

def meta_aplicar(chat_id):
ops = proto_oncogen()
if not ops:
bot.send_message(chat_id, “Sin mejoras pendientes.”)
return
aplicadas = []
for op in ops:
ok, razon = p53_verificar(op[“desc”])
if not ok:
continue
if op[“tipo”] == “timeout”:
meta[“timeouts”][op[“agente”]] += 10
aplicadas.append(f”Timeout ‘{op[‘agente’]}’ -> {meta[‘timeouts’][op[‘agente’]]}s”)
elif op[“tipo”] == “apoptosis”:
p53_apoptosis(op[“agente”], “proto-oncogen detecto fallo critico”, chat_id)
aplicadas.append(f”’{op[‘agente’]}’ desactivado”)
elif op[“tipo”] == “reparacion_adn”:
nuevo = p53_reparar_adn(op[“agente”], op[“desc”], chat_id)
if nuevo:
aplicadas.append(f”ADN ‘{op[‘agente’]}’ reparado”)
meta[“cambios_pendientes”] = []
bot.send_message(chat_id, “Aplicado:\n” + “\n”.join([f”- {a}” for a in aplicadas]) if aplicadas else “Sin cambios.”)

def meta_cada_50(chat_id):
if meta[“total_conversaciones”] % 50 == 0 and meta[“total_conversaciones”] > 0:
ops = proto_oncogen()
if ops:
bot.send_message(chat_id, f”Evaluacion automatica: {len(ops)} mejoras detectadas. Di ‘evalúate’ para el reporte.”)

# ─── BUSQUEDA WEB ─────────────────────────────────────────────────────────────

def buscar_web(query):
if not agente_activo(“busqueda”):
return “”
try:
with DDGS() as ddgs:
results = list(ddgs.text(query, max_results=3))
return “ | “.join([r[‘body’] for r in results]) if results else “”
except:
return “”

# ─── DETECTORES ──────────────────────────────────────────────────────────────

def detectar_reset(msg):
return any(p in msg.lower() for p in [“olvida todo”, “borra tu memoria”, “empieza de cero”, “limpia tu memoria”])

def detectar_correccion(msg):
return any(p in msg.lower() for p in [“eso estuvo mal”, “no me respondas asi”, “estuviste mal”, “no inventes”, “eso estuvo incorrecto”, “corrigete”, “eso no es correcto”])

def detectar_evaluacion(msg):
return any(p in msg.lower() for p in [“evalúate”, “mejórate”, “mejorate”, “como vas”, “analízate”, “estado del sistema”])

def detectar_reactivar(msg):
if “reactivar” in msg.lower():
for agente in list(meta[“agentes_desactivados”]):
if agente in msg.lower():
return agente
return None

# ─── AGENTES DE CONTEXTO ─────────────────────────────────────────────────────

def agente_estado_emocional(msg):
if not agente_activo(“emocional”):
return “neutro”
hora = datetime.now().hour
if any(p in msg.lower() for p in [“estresado”, “no puedo”, “todo mal”, “cansado”, “agotado”, “no aguanto”]):
return “estresado”
if any(p in msg.lower() for p in [“genial”, “lo logre”, “pase”, “excelente”, “feliz”, “que bueno”]):
return “celebrando”
if any(p in msg.lower() for p in [“no entiendo”, “no sirve”, “en serio”, “que onda”]):
return “frustrado”
if 0 <= hora <= 5:
return “cansado”
return “neutro”

def agente_urgencia(msg):
if not agente_activo(“urgencia”):
return “normal”
if any(p in msg.lower() for p in [“ahorita”, “urgente”, “en este momento”, “inmediato”, “ya ya”]):
return “critico”
if any(p in msg.lower() for p in [“manana”, “hoy”, “esta noche”, “en unas horas”]):
return “alto”
if any(p in msg.lower() for p in [“me fue”, “ya paso”, “la semana pasada”]):
return “retrospectivo”
return “normal”

def agente_contexto_medico(msg):
if not agente_activo(“medico”):
return False
palabras = [“sintoma”, “diagnostico”, “medicamento”, “dosis”, “enfermedad”, “paciente”,
“farmaco”, “cirugia”, “anatomia”, “fisiologia”, “patologia”, “tratamiento”,
“bioquimica”, “histologia”, “medicina”, “clinico”, “medico”, “examen medico”]
return any(p in msg.lower() for p in palabras)

def agente_contexto_musical(msg):
if not agente_activo(“musical”):
return False
palabras = [“nota”, “acorde”, “melodia”, “armonia”, “ritmo”, “compas”, “tonalidad”,
“piano”, “saxofon”, “partitura”, “cancion”, “musica”, “concierto”,
“ensayo”, “composicion”, “arreglo”, “jazz”, “clasico”, “instrumento”]
return any(p in msg.lower() for p in palabras)

def agente_ambiguedad(msg, mem):
if not agente_activo(“ambiguedad”):
return None
resultado = ollama(
f”Este mensaje tiene 2 o mas interpretaciones distintas que cambiarian la respuesta?\n”
f”Mensaje: "{msg}"\nContexto: {mem if mem else ‘ninguno’}\n”
f”Si es ambiguo: AMBIGUO: [pregunta en max 5 palabras]\nSi no: CLARO”,
timeout=meta[“timeouts”][“ambiguedad”]
)
if resultado and “AMBIGUO:” in resultado:
return resultado.replace(“AMBIGUO:”, “”).strip()
return None

# ─── AGENTES DE CALIDAD ───────────────────────────────────────────────────────

def agente_reflexion(msg, respuesta, mem_pref, info_web):
if not agente_activo(“reflexion”):
return True, []
evaluacion = ollama(
f”Evalua esta respuesta con 18 criterios.\n”
f”Mensaje: "{msg}" | Respuesta: "{respuesta}"\n”
f”Preferencias: {mem_pref or ‘ninguna’} | Internet: {info_web or ‘ninguna’}\n”
f”Criterios: 1.Precision 2.Relevancia 3.Completitud 4.Tono 5.Memoria “
f”6.Concision 7.Coherencia 8.Utilidad 9.Idioma 10.Contradiccion “
f”11.Privacidad 12.Alucinacion 13.Instrucciones 14.Contexto_emocional “
f”15.Longitud 16.Nombre 17.Saludo 18.Fuentes\n”
f”FALLOS: [numeros o NINGUNO]”,
timeout=meta[“timeouts”][“reflexion”]
)
if not evaluacion or “NINGUNO” in evaluacion:
return True, []
fallos = []
if “FALLOS:” in evaluacion:
linea = [l for l in evaluacion.split(”\n”) if “FALLOS:” in l]
if linea:
nums = linea[0].replace(“FALLOS:”, “”).strip()
fallos = [n.strip() for n in nums.split(”,”) if n.strip().isdigit()]
return len(fallos) == 0, fallos

def agente_autocorreccion(msg, respuesta_mala, fallos, mem, mem_pref, info_web):
if not agente_activo(“autocorreccion”):
return respuesta_mala
return ollama(
f”Corrige esta respuesta. Fallos: {’, ’.join(fallos)}\n”
f”Msg: "{msg}" | Incorrecta: "{respuesta_mala}"\n”
f”Mem: {mem or ‘nada’} | Pref: {mem_pref or ‘nada’}\n”
f”Corregida (max 3 oraciones, solo espanol):”,
timeout=meta[“timeouts”][“autocorreccion”]
)

def agente_tono(msg, respuesta):
if not agente_activo(“tono”):
return respuesta
revisada = ollama(
f”Revisa si esta respuesta suena natural o robotica.\n”
f”Mensaje: "{msg}" | Respuesta: "{respuesta}"\n”
f”Corrige si: empieza con Entendido, repite lo que dijo el usuario, mezcla ingles, suena generico.\n”
f”Si ya es natural: PASS\nSi necesita correccion: devuelve solo la respuesta corregida:”,
timeout=meta[“timeouts”][“tono”]
)
if not revisada or revisada.strip() == “PASS”:
return respuesta
return revisada.strip()

def agente_estilo_jarvis(respuesta, urgencia):
if not agente_activo(“jarvis”):
return respuesta
revisada = ollama(
f”Ajusta al estilo Jarvis: seguro, directo, inteligente, nunca robotico.\n”
f”Urgencia: {urgencia} | Respuesta: "{respuesta}"\n”
f”Sin Por supuesto, sin Claro que si, sin Con gusto, sin Entendido.\n”
f”Si urgencia critica: max 2 oraciones directas.\n”
f”Si ya suena bien: PASS\nAjustada:”,
timeout=meta[“timeouts”][“jarvis”]
)
if not revisada or revisada.strip() == “PASS”:
return respuesta
return revisada.strip()

def agente_privacidad(respuesta):
if not agente_activo(“privacidad”):
return respuesta
datos_sensibles = [“token”, “password”, “contrasena”, “clave”, “secret”, “api_key”]
for dato in datos_sensibles:
if dato in respuesta.lower():
return “No puedo compartir esa informacion.”
return respuesta

def agente_verificacion(msg, respuesta, info_web):
if not agente_activo(“verificacion”):
return respuesta
necesita = ollama(
f”Esta respuesta tiene datos especificos que podrian ser incorrectos? SI o NO\n”
f”Respuesta: "{respuesta}"”,
timeout=6
)
if not necesita or “NO” in necesita.upper():
return respuesta
verificado = buscar_web(msg)
if not verificado:
return respuesta
return ollama(
f”Verifica y corrige esta respuesta.\n”
f”Respuesta: "{respuesta}"\nInfo verificada: {verificado}\n”
f”Corregida (max 3 oraciones, solo espanol):”,
timeout=meta[“timeouts”][“verificacion”]
)

# ─── AGENTES DE INTELIGENCIA ─────────────────────────────────────────────────

def agente_metacognicion(msg, respuesta):
if not agente_activo(“metacognicion”):
return respuesta
certeza = ollama(
f”Del 1 al 10 que tan seguro estas de esta respuesta?\n”
f”Respuesta: "{respuesta}"\nSolo el numero:”,
timeout=6
)
try:
nivel = int(certeza.strip())
if nivel < 6:
info_extra = buscar_web(msg)
if info_extra:
return ollama(
f”Mejora esta respuesta con esta informacion adicional.\n”
f”Respuesta actual: "{respuesta}"\nInfo extra: {info_extra}\n”
f”Respuesta mejorada (max 3 oraciones, solo espanol):”,
timeout=meta[“timeouts”][“metacognicion”]
)
except:
pass
return respuesta

def agente_hipotesis(msg, mem, mem_pref, tipo):
if not agente_activo(“hipotesis”):
return “”
if tipo not in [“medico”, “musical”] and len(msg) < 30:
return “”
return ollama(
f”Genera 2-3 hipotesis sobre lo que Juan Luis realmente necesita.\n”
f”Mensaje: "{msg}" | Tipo: {tipo}\n”
f”Mem: {mem or ‘nada’} | Pref: {mem_pref or ‘nada’}\n”
f”Hipotesis mas probable (una sola, breve):”,
timeout=meta[“timeouts”][“hipotesis”]
)

def agente_analogias(msg, respuesta, tipo):
if not agente_activo(“analogias”):
return respuesta
necesita = ollama(
f”Esta respuesta se beneficiaria de una analogia para ser mas clara?\n”
f”Mensaje: "{msg}" | Respuesta: "{respuesta}"\nSI o NO:”,
timeout=6
)
if not necesita or “NO” in necesita.upper():
return respuesta
contexto = “medica o biologica” if tipo == “medico” else “musical” if tipo == “musical” else “cotidiana relevante para un joven mexicano musico y estudiante de medicina”
return ollama(
f”Agrega una analogia {contexto} a esta respuesta para hacerla mas clara.\n”
f”Respuesta: "{respuesta}"\nCon analogia (max 3 oraciones, solo espanol):”,
timeout=meta[“timeouts”][“analogias”]
)

def agente_sintesis(msg, respuesta):
if not agente_activo(“sintesis”):
return respuesta
if len(respuesta) < 200:
return respuesta
return ollama(
f”Sintetiza esta respuesta conservando el 100% del contenido importante.\n”
f”Respuesta: "{respuesta}"\n”
f”Sintetizada (max 3 oraciones, sin perder info critica, solo espanol):”,
timeout=meta[“timeouts”][“sintesis”]
)

def agente_critico(msg, respuesta):
if not agente_activo(“critico”):
return respuesta
revision = ollama(
f”Busca el punto mas debil de esta respuesta y corrigelo.\n”
f”Mensaje: "{msg}" | Respuesta: "{respuesta}"\n”
f”Si no hay punto debil: PASS\nSi hay: devuelve la respuesta corregida:”,
timeout=meta[“timeouts”][“critico”]
)
if not revision or revision.strip() == “PASS”:
return respuesta
return revision.strip()

def agente_memoria_semantica(msg, mem):
if not agente_activo(“memoria_semantica”) or not mem:
return mem
relevante = ollama(
f”De estos recuerdos, cuales son mas relevantes para este mensaje?\n”
f”Mensaje: "{msg}"\nRecuerdos: {mem}\n”
f”Devuelve solo los mas relevantes separados por |:”,
timeout=meta[“timeouts”][“memoria_semantica”]
)
return relevante if relevante else mem

# ─── AGENTES DE APRENDIZAJE ───────────────────────────────────────────────────

def agente_aprendizaje(msg, respuesta, correccion=None):
if not agente_activo(“aprendizaje”):
return
if correccion:
tipo = ollama(
f”Clasifica este error en UNA palabra: tono, contenido, formato, idioma, personalidad\n”
f”Error: "{correccion}"\nTipo:”,
timeout=6
)
descripcion = ollama(
f”En menos de 15 palabras: que debe evitar KAEL segun esta correccion: "{correccion}"\nRegla:”,
timeout=8
)
if descripcion:
guardar_aprendizaje(tipo or “general”, descripcion)
tipo_key = tipo or “general”
meta[“errores_por_tipo”][tipo_key] = meta[“errores_por_tipo”].get(tipo_key, 0) + 1
if meta[“errores_por_tipo”].get(tipo_key, 0) >= 3:
nuevo = p53_reparar_adn(“aprendizaje”, f”error repetido tipo {tipo_key}”, None)
if not nuevo:
guardar_fallo_agente(“aprendizaje”, msg, correccion, f”error_repetido_{tipo_key}”)

def agente_perfil(msg):
if not agente_activo(“perfil”):
return
datos = [“me gusta”, “no me gusta”, “soy”, “estudio”, “trabajo”, “vivo”, “mi favorito”,
“favorita”, “odio”, “amo”, “prefiero”, “recuerda”, “tengo”, “mi proyecto”,
“mi hermana”, “mi novia”, “mi familia”, “naci”, “cumplo”, “toco”, “compongo”]
if any(p in msg.lower() for p in datos):
hecho = ollama(
f”Extrae el hecho clave sobre Juan Luis en menos de 15 palabras: "{msg}"\nHecho:”,
timeout=8
)
if hecho and len(hecho) < 100:
guardar_preferencia(f”PERFIL: {hecho}”)

def agente_resumen_diario(chat_id, mem):
if meta[“resumen_enviado_hoy”]:
return
if datetime.now().hour < 21:
return
if meta[“total_conversaciones”] < 5:
return
resumen = ollama(
f”Genera resumen del dia de Juan Luis.\nConversaciones: {mem}\n”
f”Formato Jarvis, max 5 puntos: pendientes, recordatorios, aprendizajes.\n”
f”Sin saludos, directo:”,
timeout=20
)
if resumen:
bot.send_message(chat_id, f”Resumen del dia:\n{resumen}”)
guardar(f”RESUMEN_DIARIO: {resumen}”, “resumen”)
meta[“resumen_enviado_hoy”] = True

# ─── AGENTE CONSTRUCTOR ───────────────────────────────────────────────────────

def agente_constructor(msg, respuesta, chat_id):
if not agente_activo(“constructor”):
return
gap = ollama(
f”Detecta si hubo un gap en el procesamiento de esta conversacion que un agente especializado podria resolver mejor.\n”
f”Mensaje: "{msg}" | Respuesta: "{respuesta}"\n”
f”Agentes existentes: {list(meta[‘timeouts’].keys())}\n”
f”Si hay gap claro: GAP: [descripcion breve]\nSi no: OK”,
timeout=10
)
if not gap or “OK” in gap or “GAP:” not in gap:
return

```
descripcion_gap = gap.replace("GAP:", "").strip()

for intento in range(3):
    propuesta = ollama(
        f"Disena un agente especializado para resolver este gap: {descripcion_gap}\n"
        f"El agente debe ser especifico, no generico.\n"
        f"Incluye: nombre, funcion especifica, prompt detallado, criterios de activacion, timeout.\n"
        f"Formato: NOMBRE: | FUNCION: | PROMPT: | ACTIVACION: | TIMEOUT:",
        timeout=meta["timeouts"]["constructor"]
    )
    if not propuesta:
        continue

    ok, razon = p53_verificar(propuesta)
    if ok:
        guardar_fallo_agente("constructor", descripcion_gap, propuesta[:200], "propuesta_agente")
        meta["cambios_pendientes"].append({"tipo": "nuevo_agente", "propuesta": propuesta, "gap": descripcion_gap})
        bot.send_message(chat_id, f"Constructor detectó un gap y propone un nuevo agente:\n\n{propuesta[:300]}...\n\nDi 'si confirmo' para activarlo.")
        return
    else:
        if intento == 2:
            guardar_fallo_agente("constructor", descripcion_gap, f"3 intentos fallidos: {razon}", "pendiente_critico")
            meta["pendientes_criticos"].append({"gap": descripcion_gap, "razon": razon})
```

# ─── AGENTE COLABORACION ─────────────────────────────────────────────────────

def agente_colaboracion(msg, respuesta, mem_pref, chat_id):
if not agente_activo(“colaboracion”):
return
if meta[“total_conversaciones”] % 20 != 0:
return
necesidad = ollama(
f”Identifica si KAEL podria mejorar significativamente con algo que Juan Luis pueda proveer externamente.\n”
f”Preferencias actuales: {mem_pref or ‘pocas’}\n”
f”Conversacion reciente: "{msg}"\n”
f”Si hay necesidad clara (mejora > 20%): NECESIDAD: [que necesita y por que en max 20 palabras]\n”
f”Si no: OK”,
timeout=meta[“timeouts”][“colaboracion”]
)
if necesidad and “NECESIDAD:” in necesidad:
descripcion = necesidad.replace(“NECESIDAD:”, “”).strip()
if descripcion not in [s.get(“desc”, “”) for s in meta[“solicitudes_colaboracion”]]:
meta[“solicitudes_colaboracion”].append({“desc”: descripcion, “fecha”: str(datetime.now())})
bot.send_message(chat_id, f”Para mejorar: {descripcion}”)

# ─── AGENTES DE RAZONAMIENTO ─────────────────────────────────────────────────

def agente_clasificador(msg):
if not agente_activo(“clasificador”):
return “general”
return ollama(
f”Clasifica en UNA palabra: medico, musical, busqueda, personal, urgente, general.\n”
f”Mensaje: "{msg}"\nClasificacion:”,
timeout=meta[“timeouts”][“clasificador”]
).lower().strip()

def agente_contradiccion(msg, mem_pref):
if not agente_activo(“contradiccion”) or not mem_pref:
return “”
r = ollama(
f”Lo que sabes: {mem_pref}\nMensaje: "{msg}"\n”
f”Hay contradiccion clara? CONTRADICCION: [cual] o OK:”,
timeout=meta[“timeouts”][“contradiccion”]
)
return r.replace(“CONTRADICCION:”, “”).strip() if r and “CONTRADICCION” in r else “”

def agente_razonador(msg, mem, mem_pref, info_web, tipo, estado_emocional, urgencia):
if not agente_activo(“razonador”):
return “”
contexto = “”
if tipo == “medico”:
contexto = “Perspectiva clinica de estudiante de medicina avanzado UDEM.”
elif tipo == “musical”:
contexto = “Perspectiva de musico profesional, piano y saxofon.”
if estado_emocional == “estresado”:
contexto += “ Usuario estresado: ser conciso y practico.”
elif estado_emocional == “celebrando”:
contexto += “ Usuario celebrando: compartir la energia.”
if urgencia == “critico”:
contexto += “ URGENTE: ir directo a la solucion.”
return ollama(
f”Mem: {mem or ‘nada’} | Pref: {mem_pref or ‘nada’} | Tipo: {tipo}. {contexto}\n”
f”Msg: "{msg}"\nQue quiere realmente? Razonamiento breve:”,
timeout=meta[“timeouts”][“razonador”]
)

def agente_planificador(msg, razonamiento):
if not agente_activo(“planificador”):
return “”
if not any(p in msg.lower() for p in [“haz”, “agenda”, “recuerda”, “programa”, “crea”, “planifica”, “organiza”]):
return “”
return ollama(
f”Pasos concretos (max 3) para: "{msg}"\nPasos:”,
timeout=meta[“timeouts”][“planificador”]
)

def agente_patrones(msg):
if not agente_activo(“patrones”):
return
patron = ollama(
f”Patron de comportamiento en menos de 10 palabras. Si no hay: NINGUNO\nMsg: "{msg}"\nPatron:”,
timeout=meta[“timeouts”][“patrones”]
)
if patron and “NINGUNO” not in patron and len(patron) < 100:
guardar(f”PATRON: {patron}”, “patron”)

def agente_proactivo(mem_pref, msg):
if not agente_activo(“proactivo”) or not mem_pref or len(mem_pref) < 20:
return “”
obs = ollama(
f”Solo si hay algo URGENTE e importante: 1 oracion. Si no: NADA\n”
f”Pref: {mem_pref}\nMsg: "{msg}"\nObservacion:”,
timeout=meta[“timeouts”][“proactivo”]
)
return “” if not obs or “NADA” in obs else obs

# ─── PROCESADOR PRINCIPAL ────────────────────────────────────────────────────

def procesar(msg, chat_id):
meta[“total_conversaciones”] += 1
meta[“ultima_actividad”] = datetime.now()
if datetime.now().hour < 21:
meta[“resumen_enviado_hoy”] = False

```
if detectar_reset(msg):
    try:
        sb.table("memoria").delete().neq("id", "x").execute()
        sb.table("preferencias").delete().neq("id", "x").execute()
    except:
        pass
    meta["fallos_por_agente"] = {}
    meta["correcciones_seguidas"] = 0
    bot.send_message(chat_id, "Memoria limpiada.")
    return

reactivar = detectar_reactivar(msg)
if reactivar:
    meta["agentes_desactivados"].remove(reactivar)
    bot.send_message(chat_id, f"Agente '{reactivar}' reactivado.")
    return

if detectar_correccion(msg):
    meta["correcciones_seguidas"] += 1
    agente_aprendizaje(msg, "", correccion=msg)
    guardar(f"CORRECCION: {msg}", "correccion")
    if meta["correcciones_seguidas"] >= 2:
        bot.send_message(chat_id, "Dos correcciones seguidas. Activando evaluacion p53.")
        meta_evaluar(chat_id)
    else:
        bot.send_message(chat_id, "Anotado.")
    return

if detectar_evaluacion(msg):
    meta_evaluar(chat_id)
    return

if "aplicar mejoras" in msg.lower():
    meta["cambios_pendientes"] = proto_oncogen()
    if meta["cambios_pendientes"]:
        bot.send_message(chat_id, f"Proto-oncogen detecto {len(meta['cambios_pendientes'])} mejoras. Confirmas? Di 'si confirmo'")
    else:
        bot.send_message(chat_id, "Sistema saludable.")
    return

if "si confirmo" in msg.lower() and meta["cambios_pendientes"]:
    meta_aplicar(chat_id)
    return

if not detectar_correccion(msg):
    meta["correcciones_seguidas"] = 0

guardar(f"Usuario: {msg}", "conversacion")
mem = buscar_memoria(msg)
mem_pref = buscar_preferencias(msg)
aprendizajes = buscar_aprendizajes()

mem = agente_memoria_semantica(msg, mem)

estado_emocional = agente_estado_emocional(msg)
urgencia = agente_urgencia(msg)
es_medico = agente_contexto_medico(msg)
es_musical = agente_contexto_musical(msg)
tipo = agente_clasificador(msg)
if es_medico:
    tipo = "medico"
elif es_musical:
    tipo = "musical"

aclaracion = agente_ambiguedad(msg, mem)
if aclaracion:
    bot.send_message(chat_id, aclaracion)
    return

contradiccion = agente_contradiccion(msg, mem_pref)
if contradiccion:
    bot.send_message(chat_id, f"Antes sabia que {contradiccion}. Cambio algo?")
    return

necesita_busqueda = tipo in ["busqueda", "urgente"] or any(
    w in msg.lower() for w in ["busca", "que es", "quien es", "cuando", "donde",
                                "noticias", "precio", "clima", "hoy", "actual", "ultimo"])
info_web = buscar_web(msg) if necesita_busqueda else ""

hipotesis = agente_hipotesis(msg, mem, mem_pref, tipo)
razonamiento = agente_razonador(msg, mem, mem_pref, info_web, tipo, estado_emocional, urgencia)
agente_patrones(msg)
agente_perfil(msg)
proactivo = agente_proactivo(mem_pref, msg)
plan = agente_planificador(msg, razonamiento)

contexto_especial = ""
if es_medico:
    contexto_especial = "Responde con precision clinica. Juan Luis es estudiante de medicina UDEM."
elif es_musical:
    contexto_especial = "Responde como musico profesional. Juan Luis toca piano y saxofon."

ajuste_emocional = ""
if estado_emocional == "estresado":
    ajuste_emocional = "Usuario estresado: ser muy conciso y practico."
elif estado_emocional == "celebrando":
    ajuste_emocional = "Usuario celebrando: compartir la energia."
elif estado_emocional == "frustrado":
    ajuste_emocional = "Usuario frustrado: no dar lecciones, solo ayudar."
elif estado_emocional == "cansado":
    ajuste_emocional = "Usuario cansado: respuesta muy breve y empatica."

ajuste_urgencia = ""
if urgencia == "critico":
    ajuste_urgencia = "URGENCIA CRITICA: max 2 oraciones, directo a la solucion."
elif urgencia == "alto":
    ajuste_urgencia = "Urgencia alta: proponer plan de accion."

prompt = (
    f"Eres KAEL, {ADN_KAEL['identidad']}. {ADN_KAEL['tono']}.\n\n"
    f"Aprendizajes (NO repetir estos errores): {aprendizajes if aprendizajes else 'ninguno'}\n"
    f"Hipotesis: {hipotesis if hipotesis else 'N/A'}\n"
    f"Razonamiento: {razonamiento}\n"
    f"Memoria: {mem if mem else 'nada'}\n"
    f"Preferencias: {mem_pref if mem_pref else 'nada'}\n"
    + (f"Internet: {info_web}\n" if info_web else "")
    + (f"Contexto: {contexto_especial}\n" if contexto_especial else "")
    + (f"Emocional: {ajuste_emocional}\n" if ajuste_emocional else "")
    + (f"Urgencia: {ajuste_urgencia}\n" if ajuste_urgencia else "")
    + (f"Proactivo: {proactivo}\n" if proactivo else "")
    + (f"Plan: {plan}\n" if plan else "")
    + f"\nJuan Luis dice: \"{msg}\"\n\n"
    f"Responde como persona real, natural, directo. SOLO espanol. Sin saludos. Sin repetir lo que dijo:"
)

respuesta = ollama(prompt, timeout=60)

if not respuesta:
    bot.send_message(chat_id, "Estoy en modo reposo.")
    return

paso, fallos_detectados = agente_reflexion(msg, respuesta, mem_pref, info_web)
if not paso and fallos_detectados:
    guardar_fallo(msg, respuesta, str(fallos_detectados))
    mejorada = agente_autocorreccion(msg, respuesta, fallos_detectados, mem, mem_pref, info_web)
    if mejorada:
        respuesta = mejorada

respuesta = agente_critico(msg, respuesta)
respuesta = agente_metacognicion(msg, respuesta)
respuesta = agente_analogias(msg, respuesta, tipo)
respuesta = agente_sintesis(msg, respuesta)
respuesta = agente_tono(msg, respuesta)
respuesta = agente_estilo_jarvis(respuesta, urgencia)
respuesta = agente_verificacion(msg, respuesta, info_web)
respuesta = agente_privacidad(respuesta)

guardar(f"KAEL: {respuesta}", "conversacion")
agente_aprendizaje(msg, respuesta)
agente_constructor(msg, respuesta, chat_id)
agente_colaboracion(msg, respuesta, mem_pref, chat_id)
meta_cada_50(chat_id)
agente_resumen_diario(chat_id, mem)

bot.send_message(chat_id, respuesta)
```

# ─── WEBHOOK ─────────────────────────────────────────────────────────────────

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
