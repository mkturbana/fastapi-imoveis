#!/bin/bash

echo "Iniciando configuração do ambiente..."

# Criar diretório para Chrome e WebDriver
mkdir -p /opt/google/chrome
mkdir -p /opt/webdriver

# Baixar e instalar o Chrome portátil
echo "Baixando Google Chrome portátil..."
curl -o /opt/google/chrome/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -x /opt/google/chrome/google-chrome-stable_current_amd64.deb /opt/google/chrome/

# Definir permissões corretas para execução
chmod +x /opt/google/chrome/opt/google/chrome/google-chrome

# Criar link simbólico para facilitar acesso ao binário do Chrome
ln -sf /opt/google/chrome/opt/google/chrome/google-chrome /usr/local/bin/google-chrome

# Instalar dependências do Python
echo "Instalando dependências do Python..."
pip install --no-cache-dir -r requirements.txt

# Verificar se o Chrome e WebDriver estão disponíveis
echo "Verificando instalação..."
/usr/local/bin/google-chrome --version

echo "Configuração concluída com sucesso!"
