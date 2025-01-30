#!/bin/bash

# Cria um diretório para o Chrome
mkdir -p /opt/google/chrome
cd /opt/google/chrome

# Baixa o Chrome portátil
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Extrai os arquivos necessários
ar x google-chrome-stable_current_amd64.deb
tar -xvf data.tar.xz

# Move o executável para um local acessível
mv opt/google/chrome/google-chrome /usr/local/bin/google-chrome
chmod +x /usr/local/bin/google-chrome
