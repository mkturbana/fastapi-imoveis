import os

import re
import logging
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Request
from playwright.async_api import async_playwright
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root(request: Request):
    return RedirectResponse(url="/docs")

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

    # Detecta o site automaticamente
    site_info = await detect_site(url_anuncio)
    site_detectado = site_info["site_detectado"]

    # Captura o HTML usando Playwright
    html = await fetch_html_with_playwright(url_anuncio)
    soup = BeautifulSoup(html, "html.parser")

    property_code = None

    if "imovelweb.com.br" in site_detectado:
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        property_code = match.group(1) if match else None

    elif "chavesnamao.com.br" in site_detectado:
        match = re.search(r'Ref:\s*\S*--\S*\s*([\w-]+)', html)
        property_code = match.group(1) if match else None

    else:
        match = re.search(r'(ID[:.\s]*\d+|Código[:.\s]*\d+|ref[:.\s]*\d+)', html)
        property_code = match.group(1) if match else None

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

    return {"codigo_imovel": property_code}

# 📄 Busca informações do imóvel no XML
@app.get("/fetch-xml/")

async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código do imóvel."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"
    
    try:
        response = httpx.get(xml_url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")

        # 🏠 Busca pelo código do imóvel dentro da tag <ListingID>
        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        # 🔍 Pega o elemento pai para acessar os dados completos do imóvel
        listing = property_info.find_parent("Listing")
        
        # 📋 Extrai as informações da imobiliária
        contact_info = listing.find("ContactInfo")
        realtor_name = contact_info.find("Name").text if contact_info and contact_info.find("Name") else "Não informado"
        realtor_email = contact_info.find("Email").text if contact_info and contact_info.find("Email") else "Não informado"
        realtor_phone = contact_info.find("Telephone").text if contact_info and contact_info.find("Telephone") else "Não informado"

        return {
            "property_code": property_code,
            "realtor_name": realtor_name,
            "realtor_email": realtor_email,
            "realtor_phone": realtor_phone
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🏡 Função interna para buscar HTML

async def fetch_html_with_playwright(url: str) -> str:

  async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 🌍 Acessa a URL e espera a página carregar completamente
        await page.goto(url, wait_until="load")  # Espera o carregamento total
        
        # 🕒 Opcional: Aguarda um tempo extra para garantir que tudo seja renderizado
        await page.wait_for_timeout(3000)  # Espera 3 segundos
        
        # 🏗️ Aguarda elementos específicos que garantem que o HTML esteja completo
        await page.wait_for_selector("body", timeout=5000)  # Aguarda a tag <body> carregar
        
        # 📄 Captura o HTML final renderizado
        html = await page.content()
        
        await browser.close()
        return html

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao capturar HTML: {str(e)}")
