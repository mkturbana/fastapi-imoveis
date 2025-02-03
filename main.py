import re
import httpx
import logging
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright

app = FastAPI()

logging.basicConfig(level=logging.INFO)


# 🔍 Função para capturar HTML usando Playwright e evitar bloqueios
async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página carregada, evitando bloqueios e verificações."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                device_scale_factor=1,
                is_mobile=False
            )
            page = await context.new_page()
            await page.goto(url, wait_until="load")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)  # Tempo extra para carregar tudo

            html = await page.content()

            # 🛑 Detecta bloqueios como Cloudflare, CAPTCHA, etc.
            blocked_keywords = ["Just a moment", "challenge", "verification", "Access denied", "Cloudflare"]
            if any(keyword.lower() in html.lower() for keyword in blocked_keywords):
                raise HTTPException(status_code=403, detail="A página parece estar bloqueada ou requer verificação manual.")

            await browser.close()
            return html

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao capturar HTML: {str(e)}")


# 🎯 Função para detectar o site baseado na URL
@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")


# 🔎 Extração de código do imóvel - Chaves na Mão
@app.get("/extract-code/chavesnamao/")
async def extract_code_chavesnamao(url_anuncio: str):
    """Extrai o código do imóvel do site Chaves na Mão."""
    html = await fetch_html_with_playwright(url_anuncio)
    match = re.search(r'Ref:\s*<\!--\s*->\s*([\w-]+)', html)
    if match:
        return {"codigo_imovel": match.group(1)}
    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")


# 🔎 Extração de código do imóvel - ImovelWeb
@app.get("/extract-code/imovelweb/")
async def extract_code_imovelweb(url_anuncio: str):
    """Extrai o código do imóvel do site ImovelWeb."""
    html = await fetch_html_with_playwright(url_anuncio)
    match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
    if match:
        return {"codigo_imovel": match.group(1)}
    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")


# 🔎 Extração de código do imóvel - Busca Curitiba
@app.get("/extract-code/buscacuritiba/")
async def extract_code_buscacuritiba(url_anuncio: str):
    """Extrai o código do imóvel do site Busca Curitiba."""
    html = await fetch_html_with_playwright(url_anuncio)
    soup = BeautifulSoup(html, "html.parser")
    reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
    if reference_element:
        strong_tag = reference_element.find("strong")
        property_code = strong_tag.text.strip() if strong_tag else None
        if property_code:
            return {"codigo_imovel": property_code}

    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")


# 🏡 Busca dados do imóvel a partir do XML - Baseado no código extraído
@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código extraído."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

    try:
        response = httpx.get(xml_url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")
        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        listing = property_info.find_parent("Listing")
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


# 📩 Extração de URL de mensagens enviadas
@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai uma URL de uma mensagem enviada pelo usuário."""
    match = re.search(r"https?://[^\s]+", message)
    if match:
        return {"url_extraida": match.group(0)}
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")
