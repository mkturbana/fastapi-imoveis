#!/bin/bash
set -e  # Interrompe o script se houver erro

export NODE_VERSION=18

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🛠 Instalando Playwright..."
pip install playwright

echo "🌍 Baixando navegadores Playwright..."
playwright install chromium  # Instala apenas o Chromium

echo "✅ Configuração concluída!"
