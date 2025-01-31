#!/bin/bash
set -ex  # Mostra cada comando antes de executar e para em erros

echo "🚀 Instalando dependências do Python..."
pip install -r requirements.txt

echo "🛠 Instalando Playwright..."
pip install playwright

echo "✅ Configuração concluída!"
