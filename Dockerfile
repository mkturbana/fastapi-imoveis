FROM python:3.11-slim

# Instala dependências do sistema necessárias para o Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    fonts-liberation \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências do Python
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# Instala os navegadores do Playwright
RUN playwright install --with-deps chromium

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
