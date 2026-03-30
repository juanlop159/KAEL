import telebot
import subprocess
import json
import os
from datetime import datetime

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

def ctx():
    m = load()
    if not m:
        return ""
    lines = "\n".join([f"- Juan Luis dijo: {x['u']}" for x in m[-10:]])
    return f"Estas son las ultimas cosas que Juan Luis te dijo. Usaias para responder con coherencia:\n{lines}\n\n"

def chat(msg):
    c = ctx()
    p = f"{c}Juan Luis te dice ahora: {msg}\nResponde como KAEL, directo y coherente."
    r = subprocess.run(["ollama", "run", "kael", p], capture_output=True, text=True, timeout=120)
    resp = r.stdout.strip()
    save(msg, resp)
    return resp

@bot.message_handler(func=lambda m: True)
def reply(m):
    bot.send_chat_action(m.chat.id, "typing")
    bot.reply_to(m, chat(m.text))

print("KAEL activo")
bot.polling(none_stop=True)
