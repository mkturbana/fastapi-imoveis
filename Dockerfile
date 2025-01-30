FROM python:3.11-slim

# Instala o Google Chrome e o ChromeDriver
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Define variáveis de ambiente para o Selenium
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH="$PATH:/usr/bin/"

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
