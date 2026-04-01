import telebot
import requests
import json
import os
from datetime import datetime
from ddgs import DDGS
from flask import Flask, request as freq
from supabase import create_client

TOKEN = os.environ.get("TOKEN")
OLLAMA_URL = os.environ.get("OLLAMA_URL")
WEBHOOK_URL = "https://kael-production-16c8.up.railway.app"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

meta_estado = {
    "correcciones_seguidas": 0,
    "fallos_por_agente": {},
    "total_conversaciones": 0,
    "cambios_pendientes": [],
    "agentes_desactivados": [],
    "timeouts": {
        "clasificador": 8,
        "reflexion": 15,
        "autocorreccion": 25,
        "razonador": 20,
        "planificador": 10,
        "patrones": 8,
        "proactivo": 8,
        "contradiccion": 10,
    }
}

REGLAS_CONSTITUCIONALES = [
    "token", "ollama_url", "webhook_url",
    "reglas constitucionales", "7 filtros", "agente_p53", "seguridad"
]

def meta_registrar_fallo(agente, msg, respuesta, criterio):
    try:
        sb.table("fallos_log").insert({
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "agente": agente, "msg": msg, "respuesta": respuesta, "criterio": criterio
        }).execute()
        meta_estado["fallos_por_agente"][agente] = meta_estado["fallos_por_agente"].get(agente, 0) + 1
    except:
        pass

def meta_agente_proponer():
    propuestas = []
    for agente, count in meta_estado["fallos_por_agente"].items():
        if count >= 3:
            propuestas.append(f"Ajustar prompt del agente '{agente}' — ha fallado {count} veces")
        if count >= 2 and meta_estado["timeouts"].get(agente, 30) < 30:
            propuestas.append(f"Aumentar timeout de '{agente}' de {meta_estado['timeouts'].get(agente)}s a {meta_estado['timeouts'].get(agente)+10}s")
    if meta_estado["correcciones_seguidas"] >= 2:
        propuestas.append("Revisar prompt principal de KAEL — 2 correcciones seguidas del usuario")
    return propuestas

def meta_agente_evaluar(chat_id):
    lineas = ["Evaluacion del sistema KAEL:\n"]
    if meta_estado["fallos_por_agente"]:
        lineas.append("Fallos por agente:")
        for agente, count in meta_estado["fallos_por_agente"].items():
            lineas.append(f"  - {agente}: {count} fallos")
    else:
        lineas.append("Sin fallos registrados.")
    lineas.append(f"\nConversaciones totales: {meta_estado['total_conversaciones']}")
    propuestas = meta_agente_proponer()
    if propuestas:
        lineas.append("\nPropuestas de mejora:")
        for i, p in enumerate(propuestas, 1):
            lineas.append(f"  {i}. {p}")
        lineas.append("\nResponde 'aplicar mejoras' para implementarlas.")
    bot.send_message(chat_id, "\n".join(lineas))

def meta_agente_aplicar(chat_id):
    propuestas = meta_agente_proponer()
    if not propuestas:
        bot.send_message(chat_id, "No hay mejoras pendientes.")
        return
    aplicadas = []
    for p in propuestas:
        if any(r in p.lower() for r in REGLAS_CONSTITUCIONALES):
            continue
        if "timeout" in p.lower():
            for agente in meta_estado["timeouts"]:
                if agente in p.lower():
                    meta_estado["timeouts"][agente] += 10
                    aplicadas.append(f"Timeout de '{agente}' -> {meta_estado['timeouts'][agente]}s")
    meta_estado["cambios_pendientes"] = []
    if aplicadas:
        bot.send_message(chat_id, "Mejoras aplicadas:\n" + "\n".join([f"- {a}" for a in aplicadas]))
    else:
        bot.send_message(chat_id, "No se aplicaron cambios.")

def meta_agente_cada_50(chat_id):
    if meta_estado["total_conversaciones"] % 50 == 0 and meta_estado["total_conversaciones"] > 0:
        propuestas = meta_agente_proponer()
        if propuestas:
            bot.send_message(chat_id, "Evaluacion automatica:\n" +
                "\n".join([f"- {p}" for p in propuestas]) +
                "\n\nResponde 'aplicar mejoras' si quieres que las implemente.")

def guardar(texto, tipo="hecho"):
    try:
        sb.table("memoria").insert({
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "texto": texto, "tipo": tipo
        }).execute()
    except:
        pass

def guardar_preferencia(texto):
    try:
        sb.table("preferencias").insert({
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "texto": texto
        }).execute()
    except:
        pass

def guardar_fallo(msg, respuesta, criterio):
    meta_registrar_fallo("reflexion", msg, respuesta, criterio)

def buscar_memoria(query):
    try:
        r = sb.table("memoria").select("texto").order("fecha", desc=True).limit(10).execute()
        if r.data:
            return " | ".join([x["texto"] for x in r.data])
    except:
        pass
    return ""

def buscar_preferencias(query):
    try:
        r = sb.table("preferencias").select("texto").order("fecha", desc=True).limit(10).execute()
        if r.data:
            return " | ".join([x["texto"] for x in r.data])
    except:
        pass
    return ""

def detectar_reset(msg):
    return any(p in msg.lower() for p in ["olvida todo","borra tu memoria","empieza de cero","limpia tu memoria"])

def detectar_correccion(msg):
    return any(p in msg.lower() for p in ["eso estuvo mal","no me respondas asi","estuviste mal","no inventes","eso estuvo incorrecto","corrigete","eso no es correcto"])

def detectar_evaluacion(msg):
    return any(p in msg.lower() for p in ["evalúate","mejórate","mejorate","como vas","analízate","estado del sistema"])

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

def agente_reflexion(msg, respuesta, mem_pref, info_web):
    evaluacion = ollama(f"""Evalua esta respuesta de KAEL con estos 18 criterios.

Mensaje del usuario: "{msg}"
Respuesta de KAEL: "{respuesta}"
Preferencias conocidas: {mem_pref if mem_pref else "ninguna"}
Info de internet usada: {info_web if info_web else "ninguna"}

Criterios:
1. Precision: no invento datos
2. Relevancia: respondio lo que se pregunto
3. Completitud: no falta info importante
4. Tono: tono apropiado para el contexto
5. Memoria: uso bien lo que sabe del usuario
6. Concision: max 3 oraciones
7. Coherencia: tiene sentido internamente
8. Utilidad: realmente ayudo
9. Idioma: respondio solo en español
10. Contradiccion: no contradijo la memoria
11. Privacidad: no revelo info indebida
12. Alucinacion: no invento hechos especificos
13. Instrucciones: respeto las reglas de KAEL
14. Contexto emocional: no invento estados de animo
15. Longitud: respeto limite de 3 oraciones
16. Nombre: no uso el nombre innecesariamente
17. Saludo: no inicio con saludo innecesario
18. Fuentes: uso correctamente la info de internet

Responde en formato:
FALLOS: [lista de numeros separados por coma, o NINGUNO]
RESUMEN: [una oracion]""", timeout=15)

    if not evaluacion or "NINGUNO" in evaluacion:
        return True, []

    fallos_detectados = []
    if "FALLOS:" in evaluacion:
        linea = [l for l in evaluacion.split("\n") if "FALLOS:" in l]
        if linea:
            nums = linea[0].replace("FALLOS:", "").strip()
            fallos_detectados = [n.strip() for n in nums.split(",") if n.strip().isdigit()]

    return len(fallos_detectados) == 0, fallos_detectados

def agente_autocorreccion(msg, respuesta_mala, fallos_detectados, mem, mem_pref, info_web):
    return ollama(f"""La respuesta anterior tuvo problemas en: {', '.join(fallos_detectados)}

Mensaje: "{msg}"
Respuesta incorrecta: "{respuesta_mala}"
Memoria: {mem if mem else "nada"}
Preferencias: {mem_pref if mem_pref else "nada"}
{f"Internet: {info_web}" if info_web else ""}

Genera respuesta MEJORADA. Max 3 oraciones, sin saludos, solo español:""", timeout=25)

def agente_clasificador(msg):
    return ollama(f'Clasifica en UNA palabra: medico, busqueda, personal, general.\nMensaje: "{msg}"\nClasificacion:', timeout=8).lower().strip()

def agente_contradiccion(msg, mem_pref):
    if not mem_pref:
        return ""
    resultado = ollama(f'''Revisa si este mensaje contradice lo que sabes del usuario.
Lo que sabes: {mem_pref}
Mensaje nuevo: "{msg}"
Si hay contradiccion: CONTRADICCION: [que contradice]
Si no: OK''', timeout=10)
    if "CONTRADICCION" in resultado:
        return resultado.replace("CONTRADICCION:", "").strip()
    return ""

def agente_razonador(msg, mem, mem_pref, info_web, tipo):
    contexto_extra = "Razona con perspectiva clinica." if tipo == "medico" else ""
    return ollama(f'''Analiza brevemente.
Conversaciones recientes: {mem if mem else "nada"}
Preferencias: {mem_pref if mem_pref else "nada"}
{f"Internet: {info_web}" if info_web else ""}
Tipo: {tipo}. {contexto_extra}
Mensaje: "{msg}"
Que quiere? Es urgente?
Razonamiento:''', timeout=20)

def agente_planificador(msg, razonamiento):
    if not any(p in msg.lower() for p in ["haz","agenda","recuerda","programa","crea","planifica","organiza"]):
        return ""
    return ollama(f'Divide en pasos concretos (max 3).\nTarea: "{msg}"\nPasos:', timeout=10)

def agente_patrones(msg):
    patron = ollama(f'Patron de comportamiento en este mensaje en menos de 10 palabras. Si no hay: NINGUNO\nMensaje: "{msg}"\nPatron:', timeout=8)
    if patron and "NINGUNO" not in patron and len(patron) < 100:
        guardar(f"PATRON: {patron}", "patron")

def agente_proactivo(mem_pref, msg):
    if not mem_pref or len(mem_pref) < 20:
        return ""
    obs = ollama(f'Solo si hay algo URGENTE: 1 oracion. Si no: NADA\nPreferencias: {mem_pref}\nMensaje: "{msg}"\nObservacion:', timeout=8)
    return "" if not obs or "NADA" in obs else obs

def procesar(msg, chat_id):
    meta_estado["total_conversaciones"] += 1

    if detectar_reset(msg):
        try:
            sb.table("memoria").delete().neq("id", "x").execute()
            sb.table("preferencias").delete().neq("id", "x").execute()
        except:
            pass
        meta_estado["fallos_por_agente"] = {}
        meta_estado["correcciones_seguidas"] = 0
        bot.send_message(chat_id, "Memoria limpiada.")
        return

    if detectar_correccion(msg):
        meta_estado["correcciones_seguidas"] += 1
        guardar_fallo("correccion_usuario", msg, "usuario_corrigio")
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

Razonamiento: {razonamiento}
Conversaciones recientes: {mem if mem else "nada aun"}
Preferencias: {mem_pref if mem_pref else "nada aun"}
{f"Internet: {info_web}" if info_web else ""}
{f"Nota proactiva: {proactivo}" if proactivo else ""}
{f"Plan de accion: {plan}" if plan else ""}

Juan Luis dice: "{msg}"

Responde natural y directo. Maximo 3 oraciones. Sin saludos. SOLO español:"""

    respuesta = ollama(prompt, timeout=60)

    if not respuesta:
        respuesta = "Estoy en modo reposo."
        bot.send_message(chat_id, respuesta)
        return

    paso, fallos_detectados = agente_reflexion(msg, respuesta, mem_pref, info_web)

    if not paso and fallos_detectados:
        guardar_fallo(msg, respuesta, str(fallos_detectados))
        respuesta_mejorada = agente_autocorreccion(msg, respuesta, fallos_detectados, mem, mem_pref, info_web)
        if respuesta_mejorada:
            respuesta = respuesta_mejorada

    guardar(f"KAEL: {respuesta}", "conversacion")
    meta_agente_cada_50(chat_id)
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
