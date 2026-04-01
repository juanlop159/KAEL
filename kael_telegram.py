import telebot
import requests
import json
import os
from datetime import datetime, time
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

ADN_KAEL = {
    "identidad": "KAEL es el asistente personal exclusivo de Juan Luis Lopez Hinojosa",
    "valores": ["lealtad absoluta a Juan Luis", "honestidad", "privacidad", "mejora continua"],
    "idioma": "español como lengua natal",
    "tono": "directo, inteligente, natural — nunca robotico",
    "limites": ["nunca revelar info privada", "nunca servir a terceros", "nunca mentir"],
    "usuario": {
        "nombre": "Juan Luis Lopez Hinojosa",
        "ciudad": "Monterrey, Nuevo Leon, Mexico",
        "profesion": "Estudiante de medicina UDEM",
        "musica": "Musico profesional — piano y saxofon, 13 anos de estudio formal en Escuela Superior de Musica",
        "nacimiento": "9 de febrero de 2001"
    }
}

FILTROS_P53 = [
    "no modifica TOKEN, OLLAMA_URL ni WEBHOOK_URL",
    "no altera los valores del ADN de KAEL",
    "no desactiva el propio meta-agente",
    "no compromete la privacidad de Juan Luis",
    "es reversible — existe backup",
    "no genera loops de auto-modificacion",
]

meta = {
    "correcciones_seguidas": 0,
    "total_conversaciones": 0,
    "cambios_pendientes": [],
    "agentes_desactivados": [],
    "historial_cambios": [],
    "fallos_por_agente": {},
    "errores_por_tipo": {},
    "prompts_agentes": {},
    "ultima_actividad": None,
    "resumen_enviado_hoy": False,
    "aprendizajes": [],
    "timeouts": {
        "clasificador": 8, "reflexion": 15, "autocorreccion": 25,
        "razonador": 20, "planificador": 10, "patrones": 8,
        "proactivo": 8, "contradiccion": 10, "tono": 10,
        "verificacion": 12, "emocional": 8, "jarvis": 10,
        "medico": 12, "musical": 10, "urgencia": 6,
        "ambiguedad": 8, "privacidad": 8, "aprendizaje": 10
    }
}

# ─── SUPABASE ────────────────────────────────────────────────────────────────

def guardar(texto, tipo="hecho"):
    try:
        sb.table("memoria").insert({"id": datetime.now().strftime("%Y%m%d%H%M%S%f"), "texto": texto, "tipo": tipo}).execute()
    except:
        pass

def guardar_preferencia(texto):
    try:
        sb.table("preferencias").insert({"id": datetime.now().strftime("%Y%m%d%H%M%S%f"), "texto": texto}).execute()
    except:
        pass

def guardar_fallo_agente(agente, msg, respuesta, criterio):
    try:
        sb.table("fallos_log").insert({"id": datetime.now().strftime("%Y%m%d%H%M%S%f"), "agente": agente, "msg": msg, "respuesta": respuesta, "criterio": criterio}).execute()
        meta["fallos_por_agente"][agente] = meta["fallos_por_agente"].get(agente, 0) + 1
    except:
        pass

def guardar_fallo(msg, respuesta, criterio):
    guardar_fallo_agente("reflexion", msg, respuesta, criterio)

def guardar_aprendizaje(tipo, descripcion):
    try:
        sb.table("fallos_log").insert({"id": datetime.now().strftime("%Y%m%d%H%M%S%f"), "agente": "aprendizaje", "msg": tipo, "respuesta": descripcion, "criterio": "aprendizaje"}).execute()
        meta["aprendizajes"].append({"tipo": tipo, "desc": descripcion, "fecha": str(datetime.now())})
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

def buscar_aprendizajes():
    try:
        r = sb.table("fallos_log").select("msg,respuesta").eq("criterio", "aprendizaje").order("fecha", desc=True).limit(20).execute()
        if r.data:
            return " | ".join([f"{x['msg']}: {x['respuesta']}" for x in r.data])
    except:
        pass
    return ""

# ─── META-AGENTE P53 ─────────────────────────────────────────────────────────

def p53_verificar(cambio):
    for filtro in FILTROS_P53:
        if any(p in cambio.lower() for p in ["token", "ollama_url", "webhook", "meta_agente", "p53", "filtros_p53", "adn_kael"]):
            return False, "Toca componentes protegidos"
    return True, "OK"

def p53_apoptosis(agente, razon, chat_id):
    if agente not in meta["agentes_desactivados"]:
        meta["agentes_desactivados"].append(agente)
        guardar_fallo_agente("meta", agente, razon, "apoptosis")
        bot.send_message(chat_id, f"Agente '{agente}' desactivado temporalmente — demasiados errores. Di 'reactivar {agente}' para restaurarlo.")

def p53_reparar_adn(agente, problema, chat_id):
    nuevo_prompt = ollama(f"Eres el meta-agente de KAEL. El agente '{agente}' falla repetidamente con este problema: {problema}\nReescribe su prompt para corregirlo. Solo el nuevo prompt:", timeout=20)
    if nuevo_prompt and len(nuevo_prompt) > 20:
        meta["prompts_agentes"][agente] = nuevo_prompt
        guardar_fallo_agente("meta", agente, nuevo_prompt[:100], "reparacion_adn")
        return nuevo_prompt
    return None

def proto_oncogen(mem_pref):
    ops = []
    for agente, count in meta["fallos_por_agente"].items():
        if count >= 5 and agente not in meta["agentes_desactivados"]:
            ops.append({"tipo": "apoptosis", "agente": agente, "desc": f"'{agente}' falla {count} veces"})
        elif count >= 3:
            ops.append({"tipo": "reparacion_adn", "agente": agente, "desc": f"'{agente}' necesita reparacion"})
    if meta["correcciones_seguidas"] >= 2:
        ops.append({"tipo": "revision_prompt", "agente": "principal", "desc": "2 correcciones seguidas"})
    for agente, t in meta["timeouts"].items():
        if meta["fallos_por_agente"].get(agente, 0) >= 2 and t < 30:
            ops.append({"tipo": "timeout", "agente": agente, "desc": f"Aumentar timeout de '{agente}'"})
    return ops

def meta_evaluar(chat_id):
    lineas = ["Sistema KAEL — Evaluacion p53:\n"]
    activos = [a for a in meta["timeouts"] if a not in meta["agentes_desactivados"]]
    lineas.append(f"Agentes activos: {len(activos)}/{len(meta['timeouts'])}")
    if meta["agentes_desactivados"]:
        lineas.append(f"En apoptosis: {', '.join(meta['agentes_desactivados'])}")
    if meta["fallos_por_agente"]:
        lineas.append("\nFallos:")
        for a, c in meta["fallos_por_agente"].items():
            estado = "CRITICO" if c >= 5 else "ADVERTENCIA" if c >= 3 else "LEVE"
            lineas.append(f"  - {a}: {c} [{estado}]")
    lineas.append(f"\nConversaciones: {meta['total_conversaciones']}")
    lineas.append(f"Aprendizajes registrados: {len(meta['aprendizajes'])}")
    ops = proto_oncogen("")
    if ops:
        lineas.append(f"\nMejoras detectadas ({len(ops)}):")
        for i, op in enumerate(ops, 1):
            lineas.append(f"  {i}. {op['desc']}")
        lineas.append("\nResponde 'aplicar mejoras' para implementarlas.")
    else:
        lineas.append("\nSistema saludable.")
    bot.send_message(chat_id, "\n".join(lineas))

def meta_aplicar(chat_id):
    ops = proto_oncogen("")
    if not ops:
        bot.send_message(chat_id, "Sin mejoras pendientes.")
        return
    aplicadas = []
    for op in ops:
        ok, razon = p53_verificar(op["desc"])
        if not ok:
            continue
        if op["tipo"] == "timeout":
            meta["timeouts"][op["agente"]] += 10
            aplicadas.append(f"Timeout '{op['agente']}' -> {meta['timeouts'][op['agente']]}s")
        elif op["tipo"] == "apoptosis":
            p53_apoptosis(op["agente"], "proto-oncogen detectó fallo critico", chat_id)
            aplicadas.append(f"'{op['agente']}' desactivado")
        elif op["tipo"] == "reparacion_adn":
            nuevo = p53_reparar_adn(op["agente"], op["desc"], chat_id)
            if nuevo:
                aplicadas.append(f"ADN '{op['agente']}' reparado")
    meta["cambios_pendientes"] = []
    bot.send_message(chat_id, "Aplicado:\n" + "\n".join([f"- {a}" for a in aplicadas]) if aplicadas else "Sin cambios aplicados.")

def meta_cada_50(chat_id):
    if meta["total_conversaciones"] % 50 == 0 and meta["total_conversaciones"] > 0:
        ops = proto_oncogen("")
        if ops:
            bot.send_message(chat_id, f"Evaluacion automatica — {len(ops)} mejoras detectadas. Di 'evalúate' para el reporte.")

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def agente_activo(nombre):
    return nombre not in meta["agentes_desactivados"]

def ollama(prompt, timeout=30):
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "kael", "prompt": prompt, "stream": False}, timeout=timeout)
        return r.json().get("response", "").strip()
    except:
        return ""

def buscar_web(query):
    if not agente_activo("busqueda"):
        return ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            return " | ".join([r['body'] for r in results]) if results else ""
    except:
        return ""

def detectar_reset(msg):
    return any(p in msg.lower() for p in ["olvida todo", "borra tu memoria", "empieza de cero", "limpia tu memoria"])

def detectar_correccion(msg):
    return any(p in msg.lower() for p in ["eso estuvo mal", "no me respondas asi", "estuviste mal", "no inventes", "eso estuvo incorrecto", "corrigete", "eso no es correcto"])

def detectar_evaluacion(msg):
    return any(p in msg.lower() for p in ["evalúate", "mejórate", "mejorate", "como vas", "analízate", "estado del sistema"])

def detectar_reactivar(msg):
    if "reactivar" in msg.lower():
        for agente in list(meta["agentes_desactivados"]):
            if agente in msg.lower():
                return agente
    return None

# ─── AGENTES NUEVOS ──────────────────────────────────────────────────────────

def agente_estado_emocional(msg, mem):
    if not agente_activo("emocional"):
        return "neutro"
    hora = datetime.now().hour
    indicadores = []
    if any(p in msg.lower() for p in ["estresado", "no puedo", "todo mal", "cansado", "agotado", "no aguanto"]):
        indicadores.append("estresado")
    if any(p in msg.lower() for p in ["genial", "lo logre", "pasé", "excelente", "que bueno", "feliz"]):
        indicadores.append("celebrando")
    if any(p in msg.lower() for p in ["no entiendo", "no sirve", "que onda", "en serio"]):
        indicadores.append("frustrado")
    if hora >= 0 and hora <= 5:
        indicadores.append("cansado")
    if not indicadores:
        return "neutro"
    return indicadores[0]

def agente_urgencia(msg):
    if not agente_activo("urgencia"):
        return "normal"
    if any(p in msg.lower() for p in ["ahorita", "ya", "urgente", "en este momento", "inmediato", "horas"]):
        return "critico"
    if any(p in msg.lower() for p in ["mañana", "hoy", "esta noche", "en unas horas"]):
        return "alto"
    if any(p in msg.lower() for p in ["me fue", "ya paso", "la semana pasada"]):
        return "retrospectivo"
    return "normal"

def agente_contexto_medico(msg):
    if not agente_activo("medico"):
        return False
    palabras_medicas = ["sintoma", "diagnostico", "medicamento", "dosis", "enfermedad", "paciente",
                        "farmaco", "cirugia", "anatomia", "fisiologia", "patologia", "tratamiento",
                        "examen", "bioquimica", "histologia", "medicina", "clinico", "medico"]
    return any(p in msg.lower() for p in palabras_medicas)

def agente_contexto_musical(msg):
    if not agente_activo("musical"):
        return False
    palabras_musicales = ["nota", "acorde", "melodia", "armonia", "ritmo", "compas", "tonalidad",
                          "piano", "saxofon", "instrumento", "partitura", "cancion", "musica",
                          "concierto", "ensayo", "composicion", "arreglo", "jazz", "clasico"]
    return any(p in msg.lower() for p in palabras_musicales)

def agente_ambiguedad(msg, mem):
    if not agente_activo("ambiguedad"):
        return None
    resultado = ollama(f"""Este mensaje es ambiguo y tiene 2 o mas interpretaciones completamente distintas que cambiarian la respuesta?
Mensaje: "{msg}"
Contexto previo: {mem if mem else "ninguno"}
Si es ambiguo: AMBIGUO: [pregunta de aclaracion en max 5 palabras]
Si no: CLARO
Resultado:""", timeout=meta["timeouts"]["ambiguedad"])
    if resultado and "AMBIGUO:" in resultado:
        return resultado.replace("AMBIGUO:", "").strip()
    return None

def agente_privacidad(respuesta):
    if not agente_activo("privacidad"):
        return respuesta
    datos_sensibles = ["token", "password", "contraseña", "clave", "secret", "api_key"]
    for dato in datos_sensibles:
        if dato in respuesta.lower():
            return "No puedo compartir esa información."
    return respuesta

def agente_tono(msg, respuesta):
    if not agente_activo("tono"):
        return respuesta
    revisada = ollama(f"""Revisa si esta respuesta suena natural o robotica.
Mensaje: "{msg}" | Respuesta: "{respuesta}"
Corrige si: empieza con "Entendido", repite lo que dijo el usuario, mezcla ingles, suena a asistente generico.
Si ya es natural: PASS
Si necesita correccion: devuelve solo la respuesta corregida:""", timeout=meta["timeouts"]["tono"])
    if not revisada or revisada.strip() == "PASS":
        return respuesta
    return revisada.strip()

def agente_estilo_jarvis(respuesta, urgencia):
    if not agente_activo("jarvis"):
        return respuesta
    revisada = ollama(f"""Ajusta esta respuesta al estilo Jarvis — seguro, directo, inteligente, nunca robotico.
Nivel de urgencia: {urgencia}
Respuesta actual: "{respuesta}"
Reglas: sin "Por supuesto", sin "Claro que si", sin "Con gusto", sin "Entendido".
Si urgencia es critica: max 2 oraciones directas.
Si ya suena bien: PASS
Respuesta ajustada:""", timeout=meta["timeouts"]["jarvis"])
    if not revisada or revisada.strip() == "PASS":
        return respuesta
    return revisada.strip()

def agente_verificacion(msg, respuesta, info_web):
    if not agente_activo("verificacion"):
        return respuesta
    necesita = ollama(f'Esta respuesta tiene datos especificos que podrian ser incorrectos? SI o NO\nRespuesta: "{respuesta}"', timeout=6)
    if not necesita or "NO" in necesita.upper():
        return respuesta
    verificado = buscar_web(msg)
    if not verificado:
        return respuesta
    return ollama(f"Verifica y corrige esta respuesta.\nRespuesta: '{respuesta}'\nInfo verificada: {verificado}\nRespuesta corregida (max 3 oraciones, solo español):", timeout=meta["timeouts"]["verificacion"])

def agente_aprendizaje(msg, respuesta, correccion=None):
    if not agente_activo("aprendizaje"):
        return
    if correccion:
        tipo = ollama(f'Clasifica este error en UNA palabra: tono, contenido, formato, idioma, personalidad\nError: "{correccion}"\nTipo:', timeout=6)
        descripcion = ollama(f'En menos de 15 palabras: que debe evitar KAEL en el futuro segun esta correccion: "{correccion}"\nRegla:', timeout=8)
        if descripcion:
            guardar_aprendizaje(tipo or "general", descripcion)
            meta["errores_por_tipo"][tipo or "general"] = meta["errores_por_tipo"].get(tipo or "general", 0) + 1
            if meta["errores_por_tipo"].get(tipo or "general", 0) >= 3:
                nuevo = p53_reparar_adn("aprendizaje", f"error repetido tipo {tipo}", None)
                if not nuevo:
                    guardar_fallo_agente("aprendizaje", msg, correccion, f"error_repetido_{tipo}")

def agente_perfil(msg):
    if not agente_activo("perfil"):
        return
    datos_importantes = ["me gusta", "no me gusta", "soy", "estudio", "trabajo", "vivo", "mi favorito",
                         "favorita", "odio", "amo", "prefiero", "recuerda", "tengo", "mi proyecto",
                         "mi hermana", "mi novia", "mi familia", "naci", "cumplo"]
    if any(p in msg.lower() for p in datos_importantes):
        hecho = ollama(f"Extrae el hecho clave sobre Juan Luis en menos de 15 palabras: '{msg}'\nHecho:", timeout=8)
        if hecho and len(hecho) < 100:
            guardar_preferencia(f"PERFIL: {hecho}")

def agente_resumen_diario(chat_id, mem):
    if meta["resumen_enviado_hoy"]:
        return
    hora = datetime.now().hour
    if hora < 21:
        return
    if meta["total_conversaciones"] < 5:
        return
    resumen = ollama(f"""Genera un resumen del dia de Juan Luis basado en estas conversaciones.
Conversaciones: {mem}
Formato Jarvis — max 5 puntos concisos:
- Pendientes importantes
- Recordatorios para manana
- Lo que aprendi hoy de Juan Luis
Sin saludos, sin introduccion, directo:""", timeout=20)
    if resumen:
        bot.send_message(chat_id, f"Resumen del dia:\n{resumen}")
        guardar(f"RESUMEN_DIARIO: {resumen}", "resumen")
        meta["resumen_enviado_hoy"] = True

def agente_reflexion(msg, respuesta, mem_pref, info_web):
    if not agente_activo("reflexion"):
        return True, []
    evaluacion = ollama(f"""Evalua esta respuesta con 18 criterios.
Mensaje: "{msg}" | Respuesta: "{respuesta}"
Preferencias: {mem_pref or "ninguna"} | Internet: {info_web or "ninguna"}
Criterios: 1.Precision 2.Relevancia 3.Completitud 4.Tono 5.Memoria 6.Concision(max3) 7.Coherencia 8.Utilidad 9.Idioma(español) 10.Contradiccion 11.Privacidad 12.Alucinacion 13.Instrucciones 14.Contexto_emocional 15.Longitud 16.Nombre 17.Saludo 18.Fuentes
FALLOS: [numeros o NINGUNO]""", timeout=meta["timeouts"]["reflexion"])
    if not evaluacion or "NINGUNO" in evaluacion:
        return True, []
    fallos = []
    if "FALLOS:" in evaluacion:
        linea = [l for l in evaluacion.split("\n") if "FALLOS:" in l]
        if linea:
            nums = linea[0].replace("FALLOS:", "").strip()
            fallos = [n.strip() for n in nums.split(",") if n.strip().isdigit()]
    return len(fallos) == 0, fallos

def agente_autocorreccion(msg, respuesta_mala, fallos, mem, mem_pref, info_web):
    if not agente_activo("autocorreccion"):
        return respuesta_mala
    return ollama(f"Corrige esta respuesta. Fallos en criterios: {', '.join(fallos)}\nMsg: '{msg}' | Incorrecta: '{respuesta_mala}'\nMem: {mem or 'nada'} | Pref: {mem_pref or 'nada'}\nCorregida (max 3 oraciones, solo español):", timeout=meta["timeouts"]["autocorreccion"])

def agente_clasificador(msg):
    if not agente_activo("clasificador"):
        return "general"
    return ollama(f'Clasifica en UNA palabra: medico, musical, busqueda, personal, urgente, general.\nMensaje: "{msg}"\nClasificacion:', timeout=meta["timeouts"]["clasificador"]).lower().strip()

def agente_contradiccion(msg, mem_pref):
    if not agente_activo("contradiccion") or not mem_pref:
        return ""
    r = ollama(f'Lo que sabes: {mem_pref}\nMensaje: "{msg}"\nHay contradiccion? CONTRADICCION: [cual] o OK:', timeout=meta["timeouts"]["contradiccion"])
    return r.replace("CONTRADICCION:", "").strip() if r and "CONTRADICCION" in r else ""

def agente_razonador(msg, mem, mem_pref, info_web, tipo, estado_emocional, urgencia):
    if not agente_activo("razonador"):
        return ""
    contexto_extra = ""
    if tipo == "medico":
        contexto_extra = "Perspectiva clinica de estudiante de medicina avanzado."
    elif tipo == "musical":
        contexto_extra = "Perspectiva de musico profesional — piano y saxofon."
    if estado_emocional == "estresado":
        contexto_extra += " Usuario estresado — ser conciso y practico."
    elif estado_emocional == "celebrando":
        contexto_extra += " Usuario celebrando — compartir la energia."
    if urgencia == "critico":
        contexto_extra += " URGENTE — ir directo a la solucion."
    return ollama(f'Mem: {mem or "nada"} | Pref: {mem_pref or "nada"} | Tipo: {tipo}. {contexto_extra}\nMsg: "{msg}"\nQue quiere realmente? Razonamiento breve:', timeout=meta["timeouts"]["razonador"])

def agente_planificador(msg, razonamiento):
    if not agente_activo("planificador"):
        return ""
    if not any(p in msg.lower() for p in ["haz", "agenda", "recuerda", "programa", "crea", "planifica", "organiza"]):
        return ""
    return ollama(f'Pasos concretos (max 3) para: "{msg}"\nPasos:', timeout=meta["timeouts"]["planificador"])

def agente_patrones(msg):
    if not agente_activo("patrones"):
        return
    patron = ollama(f'Patron de comportamiento en menos de 10 palabras. Si no hay: NINGUNO\nMsg: "{msg}"\nPatron:', timeout=meta["timeouts"]["patrones"])
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
    meta["ultima_actividad"] = datetime.now()
    meta["resumen_enviado_hoy"] = False if datetime.now().hour < 21 else meta["resumen_enviado_hoy"]

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
            bot.send_message(chat_id, "Dos correcciones seguidas — activando evaluacion p53.")
            meta_evaluar(chat_id)
        else:
            bot.send_message(chat_id, "Anotado.")
        return

    if detectar_evaluacion(msg):
        meta_evaluar(chat_id)
        return

    if "aplicar mejoras" in msg.lower():
        meta["cambios_pendientes"] = proto_oncogen("")
        if meta["cambios_pendientes"]:
            bot.send_message(chat_id, f"Proto-oncogen detectó {len(meta['cambios_pendientes'])} mejoras. Confirmas? Di 'si confirmo'")
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

    # Agentes de contexto
    estado_emocional = agente_estado_emocional(msg, mem)
    urgencia = agente_urgencia(msg)
    es_medico = agente_contexto_medico(msg)
    es_musical = agente_contexto_musical(msg)
    tipo = agente_clasificador(msg)
    if es_medico:
        tipo = "medico"
    elif es_musical:
        tipo = "musical"

    # Ambiguedad
    aclaracion = agente_ambiguedad(msg, mem)
    if aclaracion:
        bot.send_message(chat_id, aclaracion)
        return

    # Contradiccion
    contradiccion = agente_contradiccion(msg, mem_pref)
    if contradiccion:
        bot.send_message(chat_id, f"Antes sabia que {contradiccion}. Cambio algo?")
        return

    necesita_busqueda = tipo in ["busqueda", "urgente"] or any(w in msg.lower() for w in ["busca", "que es", "quien es", "cuando", "donde", "noticias", "precio", "clima", "hoy", "actual", "ultimo"])
    info_web = buscar_web(msg) if necesita_busqueda else ""

    razonamiento = agente_razonador(msg, mem, mem_pref, info_web, tipo, estado_emocional, urgencia)
    agente_patrones(msg)
    agente_perfil(msg)
    proactivo = agente_proactivo(mem_pref, msg)
    plan = agente_planificador(msg, razonamiento)

    contexto_especial = ""
    if es_medico:
        contexto_especial = "Responde con precision clinica. Juan Luis es estudiante de medicina UDEM."
    elif es_musical:
        contexto_especial = "Responde como musico profesional. Juan Luis toca piano y saxofon, 13 anos de estudio formal."

    ajuste_emocional = ""
    if estado_emocional == "estresado":
        ajuste_emocional = "Usuario estresado — ser muy conciso y practico, sin informacion extra."
    elif estado_emocional == "celebrando":
        ajuste_emocional = "Usuario celebrando — compartir la energia, ser positivo."
    elif estado_emocional == "frustrado":
        ajuste_emocional = "Usuario frustrado — no dar lecciones, solo ayudar directamente."
    elif estado_emocional == "cansado":
        ajuste_emocional = "Usuario cansado — respuesta muy breve y empática."

    ajuste_urgencia = ""
    if urgencia == "critico":
        ajuste_urgencia = "URGENCIA CRITICA — maximo 2 oraciones, ir directo a la solucion."
    elif urgencia == "alto":
        ajuste_urgencia = "Urgencia alta — ser practico y proponer plan de accion."

    prompt = f"""Eres KAEL — {ADN_KAEL['identidad']}. {ADN_KAEL['tono']}.

Aprendizajes previos (NO repetir estos errores): {aprendizajes if aprendizajes else "ninguno aun"}
Razonamiento: {razonamiento}
Memoria reciente: {mem if mem else "nada"}
Preferencias: {mem_pref if mem_pref else "nada"}
{f"Internet: {info_web}" if info_web else ""}
{f"Contexto especial: {contexto_especial}" if contexto_especial else ""}
{f"Estado emocional: {ajuste_emocional}" if ajuste_emocional else ""}
{f"Urgencia: {ajuste_urgencia}" if ajuste_urgencia else ""}
{f"Proactivo: {proactivo}" if proactivo else ""}
{f"Plan: {plan}" if plan else ""}

Juan Luis dice: "{msg}"

Responde como persona real, natural, directo. SOLO español. Sin saludos. Sin repetir lo que dijo:"""

    respuesta = ollama(prompt, timeout=60)

    if not respuesta:
        bot.send_message(chat_id, "Estoy en modo reposo.")
        return

    # Pipeline de calidad
    paso, fallos_detectados = agente_reflexion(msg, respuesta, mem_pref, info_web)
    if not paso and fallos_detectados:
        guardar_fallo(msg, respuesta, str(fallos_detectados))
        mejorada = agente_autocorreccion(msg, respuesta, fallos_detectados, mem, mem_pref, info_web)
        if mejorada:
            respuesta = mejorada

    respuesta = agente_tono(msg, respuesta)
    respuesta = agente_estilo_jarvis(respuesta, urgencia)
    respuesta = agente_verificacion(msg, respuesta, info_web)
    respuesta = agente_privacidad(respuesta)

    guardar(f"KAEL: {respuesta}", "conversacion")
    agente_aprendizaje(msg, respuesta)
    meta_cada_50(chat_id)
    agente_resumen_diario(chat_id, mem)

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
