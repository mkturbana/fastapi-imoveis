import sys
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import re
import os
import json
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup, Comment

app = FastAPI()

# Exception handler para HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Se exc.detail for vazio, atribui "Internal Server Error"
    error_detail = exc.detail if (exc.detail and str(exc.detail).strip() != "") else "Internal Server Error"
    logging.error(f"Erro HTTP: {error_detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": error_detail},
    )

# Exception handler global para demais exceções
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc) if str(exc).strip() != "" else "Internal Server Error"
    logging.error(f"Erro interno: {error_detail}")
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail},
    )

logging.basicConfig(level=logging.INFO)
logging.info("Iniciando Playwright...")

# ------------------------------------------------------------------------------
# Endpoint para extrair URL de mensagens enviadas
@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai uma URL de uma mensagem enviada pelo usuário."""
    match = re.search(r"https?://[^\s]+", message)
    if match:
        return {"url_extraida": match.group(0)}
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")

# ------------------------------------------------------------------------------
# Endpoint para detectar o site a partir da URL
@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

# ------------------------------------------------------------------------------
async def fetch_html_with_playwright(url: str, site: str) -> str:
    """Captura o HTML da página com Playwright, ajustando configurações conforme o site."""
    try:
        async with async_playwright() as p:
            # Para depuração, você pode alterar headless para False
            browser = await p.chromium.launch(headless=True)

            # Criar state.json vazio se não existir
            if not os.path.exists("state.json"):
                with open("state.json", "w") as f:
                    f.write('{"cookies": [], "origins": []}')
                logging.info("Arquivo state.json foi criado.")

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
                viewport={"width": 1280, "height": 800},
                device_scale_factor=1,
                is_mobile=False,
                java_script_enabled=True,
                bypass_csp=True,
                storage_state="state.json"
            )

            page = await context.new_page()

            # Aplicando Playwright-Stealth
            logging.info("Aplicando stealth...")
            await stealth_async(page)

            # Ajuste das configurações para cada site
            if site == "chavesnamao":
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(15000)
                await page.mouse.move(200, 200)
                await page.mouse.wheel(0, 300)
                await page.keyboard.press("End")

            elif site == "imovelweb":
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(15000)
                await page.mouse.click(50, 50)  # Interação para desbloqueio
                await page.mouse.wheel(0, 300)
                await page.keyboard.press("End")

            elif site == "buscacuritiba":
                await page.goto(url, wait_until="load")
                await page.wait_for_timeout(15000)
                await page.mouse.click(50, 50)  # Interação para desbloqueio
                await page.mouse.wheel(0, 300)
                await page.keyboard.press("End")

            # Salva o estado atualizado no arquivo state.json
            await context.storage_state(path="state.json")

            # Exibe o conteúdo do state.json para depuração
            with open("state.json", "r") as f:
                data = json.load(f)
                logging.info("Conteúdo do state.json:\n%s", json.dumps(data, indent=2))

            html = await page.content()
            await browser.close()

            logging.info("HTML extraído com sucesso.")
            print(html[:5000])
            return html
    except Exception as e:
        logging.error(f"Erro em fetch_html_with_playwright: {e}")
        raise e

# ------------------------------------------------------------------------------
@app.get("/extract-code/chavesnamao/")
async def extract_chavesnamao(url_anuncio: str):
    html = await fetch_html_with_playwright(url_anuncio, "chavesnamao")
    return {"html": html}

@app.get("/extract-code/imovelweb/")
async def extract_imovelweb(url_anuncio: str):
    html = await fetch_html_with_playwright(url_anuncio, "imovelweb")
    return {"html": html}

@app.get("/extract-code/buscacuritiba/")
async def extract_buscacuritiba(url_anuncio: str):
    html = await fetch_html_with_playwright(url_anuncio, "buscacuritiba")
    return {"html": html}

# ------------------------------------------------------------------------------
# Endpoint para buscar informações do imóvel a partir do XML
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
        logging.error(f"Erro ao buscar XML: {e}")
        raise HTTPException(status_code=500, detail=str(e))
