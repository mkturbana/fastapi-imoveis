import os
import re
import logging
import httpx
from fastapi import FastAPI, HTTPException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fastapi import HTTPException  # Certifique-se de importar HTTPException

# Define os caminhos para o Chrome
os.environ["CHROME_BIN"] = "/opt/render/chrome/opt/google/chrome/chrome"
os.environ["CHROMEDRIVER_PATH"] = "/opt/render/.local/chromedriver/chromedriver"
os.environ["PATH"] += os.pathsep + "/opt/render/chromedriver"

# Adiciona ao PATH
os.environ["PATH"] += os.pathsep + "/usr/local/bin"

app = FastAPI()

# URL fixa do XML da imobiliária
XML_URL = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

logging.basicConfig(level=logging.INFO)

# 1️⃣ 🔗 Extrai URL de uma mensagem enviada pelo usuário

@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai a URL de uma mensagem."""
    url_match = re.search(r'(https?://[^\s]+)', message)
    if url_match:
        return {"url_anuncio": url_match.group(1)}
    
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")

# 2️⃣ 🔎 Detecta o site de origem

@app.get("/detect-site/")
async def detect_site(url: str):
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

# 3️⃣ 🔢 Extrai código do imóvel e captura HTML automaticamente com Selenium

@app.get("/extract-code/")
async def extract_property_code(url_anuncio: str, site_detectado: str):
    """Captura o HTML da página e extrai o código do imóvel."""

    # 📩 Captura o HTML usando Selenium
    html = fetch_html_with_selenium(url_anuncio)
    soup = BeautifulSoup(html, "html.parser")

    property_code = None

    if "imovelweb.com.br" in site_detectado:
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        property_code = match.group(1) if match else None

    elif "chavesnamao.com.br" in site_detectado:
        match = re.search(r'Ref:\s*<!--\s*-->\s*([\w-]+)', html)
        property_code = match.group(1) if match else None

    elif "buscacuritiba.com.br" in site_detectado:
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            strong_tag = reference_element.find("strong")
            property_code = strong_tag.text.strip() if strong_tag else None

    else:
        match = re.search(r'(ID[:.\s]*\d+|Código[:.\s]*\d+|ref[:.\s]*\d+)', html)
        property_code = match.group(1) if match else None

    # 🔍 Se nenhum código for encontrado, retorna erro 404
    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

    return {"codigo_imovel": property_code}  # 🔹 Retorno dentro da função

# 4️⃣ 📄 Busca informações do imóvel no XML

@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código do imóvel."""
    
    try:
        response = httpx.get(XML_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")

        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        return {"codigo_imovel": property_code}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🏡 Função interna para buscar HTML com Selenium (agora chamada dentro de /extract-code/)

def fetch_html_with_selenium(url: str) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = os.environ["CHROME_BIN"]
   
    # Adiciona User-Agent realista
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    )

    service = ChromeService("/opt/render/chromedriver/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    # Define tempo máximo de carregamento
    driver.set_page_load_timeout(30)

    try:
        driver.get(url)
        html = driver.page_source

        # Verifica se houve bloqueio
        if "Acesso negado" in html or "Verifique que você não é um robô" in html:
            raise HTTPException(status_code=403, detail="O site bloqueou o acesso via Selenium.")

        # Salva o HTML localmente para reutilização
        with open("pagina.html", "w", encoding="utf-8") as f:
            f.write(html)

        return html  # Retorna o HTML capturado

    except Exception as e:
        print(f"Erro ao capturar HTML: {e}")
        return ""

    finally:
        driver.quit()  # Fecha o navegador para evitar processos em aberto
