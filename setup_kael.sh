#!/bin/bash
echo "Instalando KAEL..."
apt-get install -y zstd
curl -fsSL https://ollama.com/install.sh | sh
pip3 install pyTelegramBotAPI duckduckgo-search --break-system-packages -q
ollama serve &
sleep 10
ollama pull llama3.1:8b
ollama create kael -f /workspace/Modelfile
python3 /workspace/kael_telegram.py &
echo "KAEL listo!"
