import sys
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import re
import os
import json
import httpx
import random
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup, Comment

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36"
]

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logging.info("Iniciando Playwright...")

# ------------------------------------------------------------------------------
# Tratamento de Exceções
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_detail = exc.detail if exc.detail and str(exc.detail).strip() else "Internal Server Error"
    logging.error(f"Erro HTTP: {error_detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": error_detail})

@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc).strip() if str(exc).strip() else "Internal Server Error"
    logging.error(f"Erro interno: {error_detail}")
    return JSONResponse(status_code=500, content={"detail": error_detail})

# ------------------------------------------------------------------------------
# Função para capturar HTML com Playwright
async def fetch_html_with_playwright(url: str, site: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            if not os.path.exists("state.json"):
                with open("state.json", "w") as f:
                    f.write('{"cookies": [], "origins": []}')
                logging.info("Arquivo state.json criado.")

            user_agent = random.choice(USER_AGENTS)

            try:
                context = await browser.new_context(
                    user_agent=user_agent,
                    bypass_csp=True,
                    storage_state="state.json",
                    permissions=["geolocation", "notifications", "camera", "microphone"],
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR"
                )
            except Exception:
                logging.error("Erro ao carregar state.json, recriando...")
                os.remove("state.json")
                raise HTTPException(status_code=500, detail="Erro ao carregar state.json")

            page = await context.new_page()
            await stealth_async(page)
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(5000, 15000))

            html = await page.content()

            if "Just a moment" in html or "challenge-platform" in html:
                logging.error("🚨 Página bloqueada pela Cloudflare!")
                raise HTTPException(status_code=403, detail="Página bloqueada pela Cloudflare")

            await browser.close()
            logging.info("✅ HTML extraído com sucesso.")
            return html
    except Exception as e:
        logging.error(f"❌ Erro em fetch_html_with_playwright: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# Endpoints
@app.get("/extract-code/imovelweb/")
async def extract_code_imovelweb(url_anuncio: str):
    """Extrai o código do imóvel no site ImovelWeb."""
    html = await fetch_html_with_playwright(url_anuncio, "imovelweb")
    match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
    if match:
        return {"codigo_imovel": match.group(1)}
    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

@app.get("/extract-code/buscacuritiba/")
async def extract_code_buscacuritiba(url_anuncio: str):
    """Extrai o código do imóvel no site BuscaCuritiba."""
    html = await fetch_html_with_playwright(url_anuncio, "buscacuritiba")
    soup = BeautifulSoup(html, "html.parser")
    reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
    if reference_element:
        strong_tag = reference_element.find("strong")
        property_code = strong_tag.text.strip() if strong_tag else None
        if property_code:
            return {"codigo_imovel": property_code}

    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

@app.get("/extract-code/chavesnamao/")
async def extract_property_code_chavesnamao(url_anuncio: str):
    """Extrai o código do imóvel do site Chaves na Mão."""
    html = await fetch_html_with_playwright(url_anuncio, "chavesnamao")
    soup = BeautifulSoup(html, "html.parser")

    # Busca nos comentários HTML
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        match = re.search(r"Ref:\s*([\w-]+)", comment)
        if match:
            return {"codigo_imovel": match.group(1)}

    raise HTTPException(status_code=404, detail="Código do imóvel não encontrado.")

@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Busca informações de um imóvel no XML."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(xml_url)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")
        property_info = soup.find("ListingID", string=lambda text: text and text.strip() == property_code.strip())

        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        return {"property_code": property_code}
    except Exception as e:
        logging.error(f"Erro ao buscar XML: {e}")
        raise HTTPException(status_code=500, detail=str(e))
