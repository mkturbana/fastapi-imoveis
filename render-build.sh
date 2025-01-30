#!/bin/bash

export TERM=xterm-256color

echo "🚀 Configurando ambiente para Chrome e ChromeDriver..."

# Baixa o ChromeDriver correto
mkdir -p /opt/render/chromedriver
cd /opt/render/chromedriver
curl -LO https://storage.googleapis.com/chrome-for-testing-public/114.0.5735.90/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /opt/render/chromedriver/
chmod +x /opt/render/chromedriver/chromedriver

# Define variáveis de ambiente para o Selenium
export CHROME_BIN="/usr/bin/google-chrome"
export PATH="$PATH:/opt/render/chromedriver"

echo "✅ Configuração concluída!"
