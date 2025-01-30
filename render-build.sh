#!/bin/bash

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🔧 Instalando Playwright..."
pip install playwright

echo "🌍 Baixando navegadores Playwright..."
playwright install chromium

echo "✅ Configuração concluída!"
