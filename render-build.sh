#!/bin/bash

# Atualiza os pacotes do sistema
echo "🔄 Atualizando pacotes..."
apt-get update && apt-get install -y unzip wget curl

# 📌 INSTALAÇÃO DO GOOGLE CHROME PORTÁTIL
echo "🚀 Baixando e configurando o Chrome portátil..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -x google-chrome-stable_current_amd64.deb "$HOME/chrome"
rm google-chrome-stable_current_amd64.deb

# Define o caminho do Chrome portátil
export CHROME_BIN="$HOME/chrome/opt/google/chrome/chrome"
export PATH="$HOME/chrome/opt/google/chrome:$PATH"

# 📌 INSTALAÇÃO DO CHROMEDRIVER PORTÁTIL (CERTIFIQUE-SE DA VERSÃO CORRETA)
echo "📥 Baixando e configurando o ChromeDriver portátil..."
CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip -d "$HOME/chromedriver"
rm chromedriver_linux64.zip
chmod +x "$HOME/chromedriver/chromedriver"

# Define o caminho do ChromeDriver portátil
export CHROMEDRIVER_PATH="$HOME/chromedriver/chromedriver"
export PATH="$HOME/chromedriver:$PATH"

# Exibe as versões instaladas para conferência
echo "🛠 Versões instaladas:"
$CHROME_BIN --version
$CHROMEDRIVER_PATH --version

# Instala as dependências do projeto
echo "📦 Instalando dependências do Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Finaliza a instalação e inicia o servidor
echo "✅ Build concluído! Pronto para iniciar o servidor."
