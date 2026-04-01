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

# ─── ADN DE KAEL — INMUTABLE ─────────────────────────────────────────────────
# Como el ADN humano — define quién es KAEL en su esencia
ADN_KAEL = {
    "identidad": "KAEL es el asistente personal exclusivo de Juan Luis Lopez Hinojosa",
    "valores": ["lealtad absoluta a Juan Luis", "honestidad", "privacidad", "mejora continua"],
    "idioma": "español como lengua natal",
    "tono": "directo, inteligente, natural — nunca robotico",
    "limites": ["nunca revelar info privada", "nunca servir a terceros", "nunca mentir"]
}

# ─── GEN P53 — 7 FILTROS CONSTITUCIONALES ───────────────────────────────────
# Ningun cambio puede pasar sin estos 7 filtros
FILTROS_P53 = [
    "El cambio no modifica TOKEN, OLLAMA_URL ni WEBHOOK_URL",
    "El cambio no altera los valores del ADN de KAEL",
    "El cambio no desactiva el propio meta-agente",
    "El cambio no compromete la privacidad de Juan Luis",
    "El cambio es reversible — existe backup",
    "El cambio no genera loops de auto-modificacion",
    "Juan Luis aprobo el cambio explicitamente",
]

# ─── ESTADO DEL META-AGENTE ──────────────────────────────────────────────────
meta = {
    "correcciones_seguidas": 0,
    "total_conversaciones": 0,
    "cambios_pendientes": [],
    "agentes_desactivados": [],
    "historial_cambios": [],
    "fallos_por_agente": {},
    "prompts_agentes": {},  # ADN modificable de cada agente
    "timeouts": {
        "clasificador": 8, "reflexion": 15, "autocorreccion": 25,
        "razonador": 20, "planificador": 10, "patrones": 8,
        "proactivo": 8, "contradiccion": 10, "tono": 10, "verificacion": 12
    }
}

# ─── FUNCIONES P53 ───────────────────────────────────────────────────────────

def p53_verificar_cambio(cambio):
    """El gen guardian — verifica que un cambio sea seguro antes de aplicarlo"""
    for filtro in FILTROS_P53[:-1]:  # El ultimo filtro (aprobacion) se verifica aparte
        if any(palabra in cambio.lower() for palabra in
               ["token", "ollama_url", "webhook", "meta_agente", "p53", "filtros_p53", "adn_kael"]):
            return False, f"Fallo filtro de seguridad: el cambio toca componentes protegidos"
    return True, "OK"

def p53_apoptosis(agente, razon, chat_id):
    """Si un agente causa mas dano que bien, se desactiva — como apoptosis celular"""
    if agente not in meta["agentes_desactivados"]:
        meta["agentes_desactivados"].append(agente)
        guardar_meta_log(f"APOPTOSIS: {agente} desactivado. Razon: {razon}")
        bot.send_message(chat_id, f"El agente '{agente}' fue desactivado temporalmente — estaba causando errores repetidos. Puedes reactivarlo diciendo 'reactivar {agente}'")

def p53_reparar_adn(agente, problema, chat_id):
    """Reescribe el prompt de un agente fallido — como reparacion de ADN"""
    prompt_actual = meta["prompts_agentes"].get(agente, "prompt original")
    nuevo_prompt = ollama(f"""Eres el meta-agente de KAEL. El agente '{agente}' tiene este problema repetido: {problema}

Su prompt actual es: {prompt_actual}

Reescribe el prompt de este agente para corregir exactamente ese problema.
El nuevo prompt debe ser mas especifico y robusto.
Devuelve SOLO el nuevo prompt, sin explicacion:""", timeout=20)

    if nuevo_prompt and len(nuevo_prompt) > 20:
        backup = meta["prompts_agentes"].get(agente, "original")
        meta["prompts_agentes"][agente] = nuevo_prompt
        guardar_meta_log(f"REPARACION_ADN: {agente} | BACKUP: {backup[:100]} | NUEVO: {nuevo_prompt[:100]}")
        return nuevo_prompt
    return None

def proto_oncogen_detectar_oportunidades(mem, mem_pref):
    """Detecta oportunidades de mejora proactivamente — como proto-oncogenes"""
    oportunidades = []

    for agente, count in meta["fallos_por_agente"].items():
        if count >= 3 and agente not in meta["agentes_desactivados"]:
            oportunidades.append({
                "tipo": "reparacion_adn",
                "agente": agente,
                "descripcion": f"Agente '{agente}' ha fallado {count} veces — necesita reparacion de ADN"
            })
        if count >= 5:
            oportunidades.append({
                "tipo": "apoptosis",
                "agente": agente,
                "descripcion": f"Agente '{agente}' falla demasiado — candidato para apoptosis temporal"
            })

    if meta["correcciones_seguidas"] >= 2:
        oportunidades.append({
            "tipo": "revision_prompt_principal",
            "agente": "principal",
            "descripcion": "2 correcciones seguidas del usuario — revisar prompt principal de KAEL"
        })

    for agente, timeout in meta["timeouts"].items():
        if meta["fallos_por_agente"].get(agente, 0) >= 2 and timeout < 30:
            oportunidades.append({
                "tipo": "timeout",
                "agente": agente,
                "descripcion": f"Aumentar timeout de '{agente}' de {timeout}s a {timeout+10}s"
            })

    return oportunidades

def meta_evaluar_sistema(chat_id):
    """Evaluacion completa del sistema — como chequeo medico de KAEL"""
    lineas = ["Sistema KAEL — Evaluacion completa:\n"]

    # Estado de agentes
    agentes_activos = [a for a in meta["timeouts"].keys() if a not in meta["agentes_desactivados"]]
    lineas.append(f"Agentes activos: {len(agentes_activos)}/{len(meta['timeouts'])}")

    if meta["agentes_desactivados"]:
        lineas.append(f"Agentes en apoptosis: {', '.join(meta['agentes_desactivados'])}")

    # Fallos
    if meta["fallos_por_agente"]:
        lineas.append("\nFallos detectados:")
        for agente, count in meta["fallos_por_agente"].items():
            estado = "CRITICO" if count >= 5 else "ADVERTENCIA" if count >= 3 else "LEVE"
            lineas.append(f"  - {agente}: {count} fallos [{estado}]")

    # Conversaciones
    lineas.append(f"\nConversaciones totales: {meta['total_conversaciones']}")
    lineas.append(f"Correcciones seguidas: {meta['correcciones_seguidas']}")

    # Oportunidades del proto-oncogen
    oportunidades = proto_oncogen_detectar_oportunidades("", "")
    if oportunidades:
        lineas.append(f"\nOportunidades de mejora detectadas ({len(oportunidades)}):")
        for i, op in enumerate(oportunidades, 1):
            lineas.append(f"  {i}. {op['descripcion']}")
        lineas.append("\nResponde 'aplicar mejoras' para que las implemente con tu aprobacion.")
    else:
        lineas.append("\nSistema saludable — sin mejoras urgentes detectadas.")

    bot.send_message(chat_id, "\n".join(lineas))

def meta_aplicar_mejoras(chat_id):
    """Aplica mejoras aprobadas pasando por los 7 filtros p53"""
    oportunidades = proto_oncogen_detectar_oportunidades("", "")
    if not oportunidades:
        bot.send_message(chat_id, "No hay mejoras pendientes.")
        return

    aplicadas = []
    bloqueadas = []

    for op in oportunidades:
        # Verificar con p53
        seguro, razon = p53_verificar_cambio(op["descripcion"])
        if not seguro:
            bloqueadas.append(f"{op['agente']}: {razon}")
            continue

        if op["tipo"] == "timeout":
            agente = op["agente"]
            meta["timeouts"][agente] += 10
            aplicadas.append(f"Timeout de '{agente}' -> {meta['timeouts'][agente]}s")
            guardar_meta_log(f"CAMBIO_TIMEOUT: {agente} -> {meta['timeouts'][agente]}s")

        elif op["tipo"] == "apoptosis":
            p53_apoptosis(op["agente"], "fallos repetidos detectados por proto-oncogen", chat_id)
            aplicadas.append(f"Agente '{op['agente']}' desactivado temporalmente")

        elif op["tipo"] == "reparacion_adn":
            nuevo = p53_reparar_adn(op["agente"], f"ha fallado {meta['fallos_por_agente'].get(op['agente'], 0)} veces", chat_id)
            if nuevo:
                aplicadas.append(f"ADN del agente '{op['agente']}' reparado")

    meta["historial_cambios"].append({
        "fecha": str(datetime.now()),
        "aplicadas": aplicadas,
        "bloqueadas": bloqueadas
    })

    resp = []
    if aplicadas:
        resp.append("Mejoras aplicadas:\n" + "\n".join([f"- {a}" for a in aplicadas]))
    if bloqueadas:
        resp.append("Bloqueadas por p53:\n" + "\n".join([f"- {b}" for b in bloqueadas]))

    bot.send_message(chat_id, "\n".join(resp) if resp else "Sin cambios aplicados.")

def meta_cada_50(chat_id):
    if meta["total_conversaciones"] % 50 == 0 and meta["total_conversaciones"] > 0:
        oportunidades = proto_oncogen_detectar_oportunidades("", "")
        if oportunidades:
            bot.send_message(chat_id, f"Evaluacion automatica (cada 50 conversaciones) — {len(oportunidades)} oportunidades de mejora detectadas.\n\nResponde 'evalúate' para ver el reporte completo.")

def agente_activo(nombre):
    return nombre not in meta["agentes_desactivados"]

# ─── HELPERS SUPABASE ─────────────────────────────────────────────────────────

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

def guardar_fallo_agente(agente, msg, respuesta, criterio):
    try:
        sb.table("fallos_log").insert({
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "agente": agente, "msg": msg, "respuesta": respuesta, "criterio": criterio
        }).execute()
        meta["fallos_por_agente"][agente] = meta["fallos_por_agente"].get(agente, 0) + 1
    except:
        pass

def guardar_fallo(msg, respuesta, criterio):
    guardar_fallo_agente("reflexion", msg, respuesta, criterio)

def guardar_meta_log(texto):
    try:
        sb.table("fallos_log").insert({
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "agente": "meta", "msg": texto, "respuesta": "", "criterio": "meta_log"
        }).execute()
    except:
        pass

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
    return any(p in msg.lower() for p in ["evalúate","mejórate","mejorate","como vas","analízate","estado del sistema","evalua tu sistema"])

def detectar_reactivar(msg):
    if "reactivar" in msg.lower():
        for agente in list(meta["agentes_desactivados"]):
            if agente in msg.lower():
                return agente
    return None

def buscar_web(query):
    if not agente_activo("busqueda"):
        return ""
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

# ─── AGENTES ─────────────────────────────────────────────────────────────────

def agente_reflexion(msg, respuesta, mem_pref, info_web):
    if not agente_activo("reflexion"):
        return True, []
    evaluacion = ollama(f"""Evalua esta respuesta de KAEL con estos 18 criterios.

Mensaje: "{msg}"
Respuesta: "{respuesta}"
Preferencias: {mem_pref if mem_pref else "ninguna"}
Internet: {info_web if info_web else "ninguna"}

1. Precision 2. Relevancia 3. Completitud 4. Tono 5. Memoria
6. Concision 7. Coherencia 8. Utilidad 9. Idioma(solo español) 10. Contradiccion
11. Privacidad 12. Alucinacion 13. Instrucciones 14. Contexto_emocional 15. Longitud(max 3)
16. Nombre(no innecesario) 17. Saludo(no innecesario) 18. Fuentes

FALLOS: [numeros separados por coma, o NINGUNO]""", timeout=meta["timeouts"]["reflexion"])

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
    if not agente_activo("autocorreccion"):
        return respuesta_mala
    return ollama(f"""Corrige esta respuesta. Problemas en criterios: {', '.join(fallos_detectados)}
Mensaje: "{msg}" | Respuesta incorrecta: "{respuesta_mala}"
Memoria: {mem if mem else "nada"} | Preferencias: {mem_pref if mem_pref else "nada"}
{f"Internet: {info_web}" if info_web else ""}
Respuesta corregida (max 3 oraciones, sin saludos, solo español):""", timeout=meta["timeouts"]["autocorreccion"])

def agente_tono(msg, respuesta):
    if not agente_activo("tono"):
        return respuesta
    revisada = ollama(f"""Revisa si esta respuesta suena natural o robotica.
Mensaje: "{msg}" | Respuesta: "{respuesta}"
Problemas: empieza con "Entendido", repite lo que dijo el usuario, mezcla ingles, suena a asistente generico.
Si ya es natural: PASS
Si necesita correccion: devuelve solo la respuesta corregida:""", timeout=meta["timeouts"]["tono"])
    if not revisada or revisada.strip() == "PASS":
        return respuesta
    return revisada.strip()

def agente_verificacion(msg, respuesta, info_web):
    if not agente_activo("verificacion"):
        return respuesta
    necesita = ollama(f'Esta respuesta contiene datos especificos que podrian ser incorrectos? SI o NO\nRespuesta: "{respuesta}"\nRespuesta:', timeout=6)
    if not necesita or "NO" in necesita.upper():
        return respuesta
    verificado = buscar_web(msg)
    if not verificado:
        return respuesta
    return ollama(f"""Verifica y corrige esta respuesta usando la info de internet.
Respuesta actual: "{respuesta}"
Info verificada: {verificado}
Devuelve la respuesta corregida y verificada (max 3 oraciones, solo español):""", timeout=meta["timeouts"]["verificacion"])

def agente_clasificador(msg):
    if not agente_activo("clasificador"):
        return "general"
    return ollama(f'Clasifica en UNA palabra: medico, busqueda, personal, general, urgente.\nMensaje: "{msg}"\nClasificacion:', timeout=meta["timeouts"]["clasificador"]).lower().strip()

def agente_contradiccion(msg, mem_pref):
    if not agente_activo("contradiccion") or not mem_pref:
        return ""
    resultado = ollama(f'Lo que sabes: {mem_pref}\nMensaje nuevo: "{msg}"\nHay contradiccion clara? CONTRADICCION: [que] o OK:', timeout=meta["timeouts"]["contradiccion"])
    if "CONTRADICCION" in resultado:
        return resultado.replace("CONTRADICCION:", "").strip()
    return ""

def agente_razonador(msg, mem, mem_pref, info_web, tipo):
    if not agente_activo("razonador"):
        return ""
    contexto = "Perspectiva clinica." if tipo == "medico" else "Perspectiva musical." if tipo == "musical" else ""
    return ollama(f'Mem: {mem or "nada"} | Pref: {mem_pref or "nada"} | Tipo: {tipo}. {contexto}\nMensaje: "{msg}"\nQue quiere? Es urgente? Razonamiento breve:', timeout=meta["timeouts"]["razonador"])

def agente_planificador(msg, razonamiento):
    if not agente_activo("planificador"):
        return ""
    if not any(p in msg.lower() for p in ["haz","agenda","recuerda","programa","crea","planifica","organiza"]):
        return ""
    return ollama(f'Pasos concretos (max 3) para: "{msg}"\nPasos:', timeout=meta["timeouts"]["planificador"])

def agente_patrones(msg):
    if not agente_activo("patrones"):
        return
    patron = ollama(f'Patron de comportamiento en menos de 10 palabras. Si no hay: NINGUNO\nMensaje: "{msg}"\nPatron:', timeout=meta["timeouts"]["patrones"])
    if patron and "NINGUNO" not in patron and len(patron) < 100:
        guardar(f"PATRON: {patron}", "patron")

def agente_proactivo(mem_pref, msg):
    if not agente_activo("proactivo") or not mem_pref or len(mem_pref) < 20:
        return ""
    obs = ollama(f'Solo si hay algo URGENTE e importante: 1 oracion. Si no: NADA\nPref: {mem_pref}\nMsg: "{msg}"\nObservacion:', timeout=meta["timeouts"]["proactivo"])
    return "" if not obs or "NADA" in obs else obs

# ─── PROCESADOR PRINCIPAL ────────────────────────────────────────────────────

def procesar(msg, chat_id):
    meta["total_conversaciones"] += 1

    # Comandos especiales
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
        guardar_fallo_agente("usuario", msg, "", "correccion_manual")
        guardar(f"CORRECCION: {msg}", "correccion")
        if meta["correcciones_seguidas"] >= 2:
            bot.send_message(chat_id, "Dos correcciones seguidas — activando evaluacion p53.")
            meta_evaluar_sistema(chat_id)
        else:
            bot.send_message(chat_id, "Anotado. Aprenderé de eso.")
        return

    if detectar_evaluacion(msg):
        meta_evaluar_sistema(chat_id)
        return

    if "aplicar mejoras" in msg.lower():
        meta["cambios_pendientes"] = proto_oncogen_detectar_oportunidades("", "")
        if meta["cambios_pendientes"]:
            bot.send_message(chat_id, f"Proto-oncogen detectó {len(meta['cambios_pendientes'])} mejoras. Confirmas aplicarlas? Responde 'si confirmo'")
        else:
            bot.send_message(chat_id, "Sistema saludable — sin mejoras pendientes.")
        return

    if "si confirmo" in msg.lower() and meta["cambios_pendientes"]:
        meta_aplicar_mejoras(chat_id)
        return

    if not detectar_correccion(msg):
        meta["correcciones_seguidas"] = 0

    guardar(f"Usuario: {msg}", "conversacion")

    mem = buscar_memoria(msg)
    mem_pref = buscar_preferencias(msg)
    tipo = agente_clasificador(msg)

    contradiccion = agente_contradiccion(msg, mem_pref)
    if contradiccion:
        bot.send_message(chat_id, f"Espera — antes sabia que {contradiccion}. Cambio algo?")
        return

    necesita_busqueda = tipo in ["busqueda", "urgente"] or any(w in msg.lower() for w in ["busca","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo"])
    info_web = buscar_web(msg) if necesita_busqueda else ""

    razonamiento = agente_razonador(msg, mem, mem_pref, info_web, tipo)
    agente_patrones(msg)
    proactivo = agente_proactivo(mem_pref, msg)
    plan = agente_planificador(msg, razonamiento)

    if any(p in msg.lower() for p in ["me gusta","no me gusta","odio","amo","recuerda","prefiero","soy","estudio","trabajo","vivo","mi favorito","favorita"]):
        hecho = ollama(f"Extrae el hecho clave sobre el usuario en menos de 10 palabras: '{msg}'", timeout=8)
        if hecho and len(hecho) < 80:
            guardar_preferencia(hecho)

    prompt = f"""Eres KAEL, asistente personal de Juan Luis Lopez Hinojosa. Estudiante de medicina UDEM Monterrey, musico. Directo, inteligente, natural. SOLO español.

ADN: {json.dumps(ADN_KAEL, ensure_ascii=False)}
Razonamiento: {razonamiento}
Memoria reciente: {mem if mem else "nada"}
Preferencias: {mem_pref if mem_pref else "nada"}
{f"Internet: {info_web}" if info_web else ""}
{f"Proactivo: {proactivo}" if proactivo else ""}
{f"Plan: {plan}" if plan else ""}

Juan Luis dice: "{msg}"

Responde como persona real, natural, directo. Max 3 oraciones. Sin saludos. Sin repetir lo que dijo. SOLO español:"""

    respuesta = ollama(prompt, timeout=60)

    if not respuesta:
        bot.send_message(chat_id, "Estoy en modo reposo.")
        return

    # Pipeline de calidad — cada agente mejora la respuesta
    paso, fallos_detectados = agente_reflexion(msg, respuesta, mem_pref, info_web)
    if not paso and fallos_detectados:
        guardar_fallo(msg, respuesta, str(fallos_detectados))
        respuesta_mejorada = agente_autocorreccion(msg, respuesta, fallos_detectados, mem, mem_pref, info_web)
        if respuesta_mejorada:
            respuesta = respuesta_mejorada

    respuesta = agente_tono(msg, respuesta)
    respuesta = agente_verificacion(msg, respuesta, info_web)

    guardar(f"KAEL: {respuesta}", "conversacion")
    meta_cada_50(chat_id)
    bot.send_message(chat_id, respuesta)

# ─── WEBHOOK ─────────────────────────────────────────────────────────────────

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
