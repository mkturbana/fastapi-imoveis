import os

import re
import logging
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

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

# 3️⃣ 🔢 Extrai código do imóvel e captura HTML automaticamente

@app.get("/extract-code/")
async def extract_property_code(url_anuncio: str, site_detectado: str):
    """Captura o HTML da página e extrai o código do imóvel com Playwright."""
    
    # 📩 Captura o HTML usando Playwright
    html = await fetch_html_with_playwright(url_anuncio)
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

    return {"codigo_imovel": property_code}

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

# 🏡 Função interna para buscar HTML

async def fetch_html_with_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Executa o navegador no modo headless
        page = await browser.new_page()
        await page.goto(url, timeout=60000)  # Acessa a página (timeout de 60s)
        
        html = await page.content()  # Obtém o HTML da página
        await browser.close()
        return html

async def extract_property_code(url):
    html = await fetch_html_with_playwright(url)
    
    # 🔹 Salva o HTML para depuração
    with open("pagina.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 🔹 Usa BeautifulSoup para extrair os dados
    soup = BeautifulSoup(html, "html.parser")
    
    # 🔹 Exemplo de extração do código do imóvel (ajuste conforme necessário)
    codigo = soup.find("span", class_="property-code")
    
    if codigo:
        return codigo.get_text(strip=True)
    return "Código não encontrado"
