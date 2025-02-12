import re
import json
import httpx
import logging
import asyncio
from bs4 import BeautifulSoup
from starlette.requests import Request
from fastapi.responses import Response, JSONResponse
from fetch import fetch_html_with_playwright
from extractors import extract_property_code
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from exceptions import http_exception_handler, custom_exception_handler

app = FastAPI()

# Configuração dos handlers de erro
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, custom_exception_handler)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("API Iniciada!")

# 🔄 Função para manter o servidor ativo
@app.on_event("startup")
async def keep_alive():
    """Evita que o Render encerre o servidor por inatividade."""
    while True:
        await asyncio.sleep(60)  # Aguarda 60 segundos
        logging.info("💡 Keep-alive: Servidor ainda está rodando...")

class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logging.info(f"🔹 RECEBENDO REQUISIÇÃO: {request.method} {request.url}")

        try:
            body = await request.body()
            if body:
                logging.info(f"📩 Corpo da Requisição: {body.decode('utf-8')}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao capturar o corpo da requisição: {e}")

        # Processar a requisição
        response = await call_next(request)

        # Criar uma cópia segura da resposta
        response_body = [chunk async for chunk in response.body_iterator]
        response = Response(content=b"".join(response_body), status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

        try:
            response_content = response.body.decode()
            logging.info(f"✅ RESPOSTA: {response.status_code} - {response_content}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao capturar a resposta: {e}")

        return response

# Adiciona o middleware na API
app.add_middleware(LogMiddleware)

# ------------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "API de Imóveis está online! 🚀"}

@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai uma URL de uma mensagem enviada pelo usuário."""
    match = re.search(r"https?://[^\s]+", message)
    if match:
        return {"url_extraida": match.group(0)}
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")

@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/.]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

@app.get("/extract-code/")
async def extract_code(url: str, site: str):
    """Extrai o código do imóvel de acordo com o site informado."""
    logging.info(f"🔍 Extraindo código do imóvel para URL: {url} | Site: {site}")
    html = await fetch_html_with_playwright(url)
    
    if not html:
        raise HTTPException(status_code=500, detail="Erro ao carregar página do imóvel.")
 
    codigo = extract_property_code(html, site)
    
    if not codigo:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado.")

    logging.info(f"✅ Código do imóvel extraído: {codigo}")
    return {"codigo_imovel": codigo}

async def process_fetch_xml(property_code: str):
    """Processa a requisição ao XML e envia os dados para o webhook."""
    logging.info(f"📡 Buscando informações do imóvel no XML para código {property_code}...")

    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(xml_url, timeout=15)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        property_info = soup.find("ListingID", string=property_code)

        if not property_info:
            logging.warning(f"⚠️ Código do imóvel {property_code} não encontrado no XML.")
            return

        listing = property_info.find_parent("Listing") if property_info else None
        contact_info = listing.find("ContactInfo") if listing else None

        realtor_name = contact_info.find("Name").text if contact_info and contact_info.find("Name") else "Não informado"
        realtor_email = contact_info.find("Email").text if contact_info and contact_info.find("Email") else "Não informado"
        realtor_phone = contact_info.find("Telephone").text if contact_info and contact_info.find("Telephone") else "Não informado"

        logging.info(f"🏡 Dados do imóvel encontrados: {realtor_name}, {realtor_email}, {realtor_phone}")

        # 🔹 Envia os dados para o webhook do BotConversa
        webhook_url = "https://backend.botconversa.com.br/api/v1/webhook"  # Substituir pela URL correta do webhook
        await client.post(webhook_url, json={
            "property_code": property_code,
            "realtor_name": realtor_name,
            "realtor_email": realtor_email,
            "realtor_phone": realtor_phone
        })

    except httpx.HTTPStatusError as e:
        logging.error(f"❌ Erro HTTP ao acessar XML: {e}")
    except Exception as e:
        logging.exception(f"🔥 Erro ao buscar XML: {e}")

@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Processa imediatamente para evitar que o servidor desligue antes de completar."""
    logging.info(f"🔄 Processando XML para {property_code}...")
    await process_fetch_xml(property_code)  # Aguarda a função terminar antes de responder
    return {"status": "completed", "property_code": property_code}
