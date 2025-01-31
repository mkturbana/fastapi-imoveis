#!/bin/bash
set -e  # Faz o script parar se algum comando falhar

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🛠 Instalando Playwright..."
pip install playwright

echo "🌍 Baixando navegadores Playwright..."
playwright install --with-deps

echo "✅ Configuração concluída!"
