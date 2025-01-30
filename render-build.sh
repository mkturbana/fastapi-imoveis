#!/bin/bash

echo "🚀 Baixando e configurando o Chrome portátil..."
mkdir -p /opt/render/chrome
cd /opt/render/chrome

# Baixa a versão portátil do Google Chrome
curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
ar x google-chrome-stable_current_amd64.deb
tar -xvf data.tar.xz
mv opt/google/chrome /opt/render/chrome/

# Configura as permissões
chmod +x /opt/render/chrome/google-chrome

echo "📥 Baixando e configurando o ChromeDriver portátil..."
mkdir -p /opt/render/chromedriver
cd /opt/render/chromedriver

# Baixa o ChromeDriver compatível com a versão do Chrome instalado
curl -LO https://storage.googleapis.com/chrome-for-testing-public/114.0.5735.90/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /opt/render/chromedriver/

# Configura as permissões
chmod +x /opt/render/chromedriver/chromedriver

# Atualiza as variáveis de ambiente
export CHROME_BIN="/opt/render/chrome/google-chrome"
export PATH="$PATH:/opt/render/chromedriver"

