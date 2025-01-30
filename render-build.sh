#!/bin/bash

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🔧 Instalando Playwright e navegadores..."
playwright install --with-deps

echo "✅ Configuração concluída!"
