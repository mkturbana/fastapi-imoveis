#!/bin/bash

set -eux  # Ativa modo de depuração e falha ao encontrar erros

echo "🔄 Atualizando pacotes..."
apt-get update && apt-get upgrade -y

echo "📦 Instalando dependências necessárias..."
apt-get install -y curl unzip wget libnss3 libatk1.0-0 libx11-xcb1 libxcb-dri3-0 libxcomposite1 libxdamage1 \
                   libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcups2 libdrm2 libasound2 libxshmfence1 \
                   libgtk-3-0 libxinerama1 libegl1

echo "🚀 Instalando Playwright e seus navegadores..."
pip install --upgrade pip
pip install playwright
playwright install chromium

echo "✅ Build concluído! Pronto para iniciar o servidor."
