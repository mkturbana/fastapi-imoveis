import re
import logging
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
from fastapi.responses import RedirectResponse

# Inicializa o FastAPI
app = FastAPI()

# Configuração do logging
logging.basicConfig(level=logging.INFO)

# Função para capturar HTML usando Playwright
async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página carregada usando Playwright"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Modo headless para servidor
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                device_scale_factor=1,
                is_mobile=False
            )
            page = await context.new_page()
            await page.goto(url, wait_until="load")
            await page.wait_for_load_state("networkidle")  # Aguarda carregamento total
            await page.wait_for_timeout(5000)  # Espera adicional
            html = await page.content()
            await browser.close()
            return html

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao capturar HTML: {str(e)}")

# 🔹 Função genérica para extrair código do imóvel de qualquer site
def extract_property_code_from_html(html: str, site: str) -> str:
    """Extrai o código do imóvel baseado no site"""
    if site == "imovelweb.com.br":
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        return match.group(1) if match else None
    
    elif site == "chavesnamao.com.br":
        match = re.search(r'Ref:\s*\-\s*>\s*([\w-]+)', html)
        return match.group(1) if match else None

    elif site == "buscacuritiba.com.br":
        soup = BeautifulSoup(html, "html.parser")
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            strong_tag = reference_element.find("strong")
            return strong_tag.text.strip() if strong_tag else None

    # Padrão genérico para outros sites
    match = re.search(r'(ID[:.\s]*\d+|Código[:.\s]*\d+|ref[:.\s]*\d+)', html)
    return match.group(1) if match else None

# 🔹 Função para detectar site a partir da URL
@app.get("/detect-site/")
async def detect_site(url: str):
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

# 🔹 Endpoint para **ImovelWeb**
@app.get("/extract-code/imovelweb/")
async def extract_property_code_imovelweb(url_anuncio: str):
    """Extrai código do imóvel no ImovelWeb"""
    html = await fetch_html_with_playwright(url_anuncio)
    property_code = extract_property_code_from_html(html, "imovelweb.com.br")

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")
    return {"codigo_imovel": property_code}

# 🔹 Endpoint para **Chaves na Mão**
@app.get("/extract-code/chavesnamao/")
async def extract_property_code_chavesnamao(url_anuncio: str):
    """Extrai código do imóvel no Chaves na Mão"""
    html = await fetch_html_with_playwright(url_anuncio)
    property_code = extract_property_code_from_html(html, "chavesnamao.com.br")

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")
    return {"codigo_imovel": property_code}

# 🔹 Endpoint para **Busca Curitiba**
@app.get("/extract-code/buscacuritiba/")
async def extract_property_code_buscacuritiba(url_anuncio: str):
    """Extrai código do imóvel no Busca Curitiba"""
    html = await fetch_html_with_playwright(url_anuncio)
    property_code = extract_property_code_from_html(html, "buscacuritiba.com.br")

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")
    return {"codigo_imovel": property_code}

# 🔹 Endpoint genérico para **outros sites**
@app.get("/extract-code/")
async def extract_property_code(url_anuncio: str):
    """Detecta site e extrai código do imóvel automaticamente"""
    site_info = await detect_site(url_anuncio)
    site_detectado = site_info["site"]

    html = await fetch_html_with_playwright(url_anuncio)
    property_code = extract_property_code_from_html(html, site_detectado)

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")
    return {"codigo_imovel": property_code}

# 🔹 Endpoint para buscar informações do imóvel no XML
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
