#!/bin/bash
set -eux

# Baixa e instala o Google Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Baixa e instala o ChromeDriver compatível
CHROME_VERSION=$(google-chrome --version | grep -o '[0-9]\+' | head -1)
wget -q https://chromedriver.storage.googleapis.com/$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION})/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
