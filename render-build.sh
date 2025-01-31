#!/bin/bash
set -e  # Interrompe o script se houver erro

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🛠 Instalando Playwright..."
pip install playwright

echo "🌍 Baixando navegador Chromium para Playwright..."
playwright install chromium || { echo "🚨 Erro ao instalar Chromium!"; exit 1; }

echo "✅ Configuração concluída!"
