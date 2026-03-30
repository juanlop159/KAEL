import telebot
import subprocess
import json
import os
from datetime import datetime
from duckduckgo_search import DDGS

TOKEN = "8279085726:AAHOD1RkAfCppGH8gCFYCRAJ4t4tGTSuaxA"
MF = "/workspace/kael_memoria.json"
bot = telebot.TeleBot(TOKEN)

def load():
    if os.path.exists(MF):
        with open(MF) as f:
            return json.load(f)
    return []

def save(u, k):
    m = load()
    m.append({"f": str(datetime.now()), "u": u, "k": k})
    m = m[-50:]
    with open(MF, "w") as f:
        json.dump(m, f, ensure_ascii=False)

def buscar(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return " | ".join([r['body'] for r in results])
    except:
        pass
    return ""

def ctx():
    m = load()
    if not m:
        return ""
    lines = "\n".join([f"- Juan Luis dijo: {x['u']}" for x in m[-5:]])
    return f"Conversaciones previas:\n{lines}\n\n"

def chat(msg):
    necesita_busqueda = any(w in msg.lower() for w in ["busca","buscar","que es","quien es","cuando","donde","noticias","precio","clima","hoy","actual","ultimo","reciente"])
    info_web = ""
    if necesita_busqueda:
        info_web = buscar(msg)

    c = ctx()
    p = f"{c}"
    if info_web:
        p += f"Estos son los resultados REALES de internet,usalos exactamente:\n{info_web}\n\n"
    p += f"Juan Luis dice: {msg}\nResponde como KAEL. Si tienes info de internet usala tal cual. NO inventes datos. Si no tienes info real dilo. Maximo 3 oraciones."

    r = subprocess.run(["ollama", "run", "kael", p], capture_output=True, text=True, timeout=120)
    resp = r.stdout.strip()
    save(msg, resp)
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL con internet activo")
bot.polling(none_stop=True)
