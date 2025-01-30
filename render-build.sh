#!/bin/bash

echo "🚀 Iniciando configuração do ambiente..."

# Criar diretórios para armazenar os binários
mkdir -p /opt/chrome /opt/chromedriver

# Baixar Google Chrome portátil
echo "🔽 Baixando Google Chrome..."
curl -Lo /opt/chrome/chrome.zip "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

# Extrair o Chrome
dpkg -x /opt/chrome/chrome.zip /opt/chrome/

# Criar link simbólico para facilitar a execução
ln -sf /opt/chrome/opt/google/chrome/google-chrome /usr/local/bin/google-chrome

# Baixar e instalar o ChromeDriver
echo "🔽 Baixando ChromeDriver..."
CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
curl -Lo /opt/chromedriver/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"

# Extrair ChromeDriver
unzip /opt/chromedriver/chromedriver.zip -d /opt/chromedriver/

# Tornar o ChromeDriver executável
chmod +x /opt/chromedriver/chromedriver

# Criar link simbólico do ChromeDriver
ln -sf /opt/chromedriver/chromedriver /usr/local/bin/chromedriver

# Instalar dependências do Python
echo "🐍 Instalando dependências do Python..."
pip install --no-cache-dir -r requirements.txt

# Verificar instalações
echo "✅ Verificando instalação..."
google-chrome --version
chromedriver --version

echo "🎉 Configuração concluída com sucesso!"
