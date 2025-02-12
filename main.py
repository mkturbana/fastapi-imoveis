import os
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

XML_URL = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

# 🔄 Função para manter o servidor ativo no Render
async def keep_alive_task():
    while True:
        await asyncio.sleep(60)
        logging.info("💡 Keep-alive: Servidor ainda está rodando...")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_task())

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
        response_bytes = b"".join(response_body)  # Garante que os bytes sejam unidos corretamente
        response_content = response_bytes.decode()  # Decodifica os bytes para string

        try:
            logging.info(f"✅ RESPOSTA: {response.status_code} - {response_content}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao capturar a resposta: {e}")

        return Response(content=response_bytes, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

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

# 🔍 Função auxiliar para buscar detalhes no XML
async def get_property_info(property_code: str):
    """Busca os detalhes do imóvel no XML usando o código extraído."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(XML_URL, timeout=10)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        property_info = soup.find("ListingID", string=property_code)

        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        listing = property_info.find_parent("Listing")
        return listing.find("ContactInfo") if listing else None

    except httpx.HTTPStatusError as e:
        logging.error(f"Erro HTTP ao acessar XML: {e}")
        raise HTTPException(status_code=e.response.status_code, detail="Erro ao acessar XML.")
    except Exception as e:
        logging.exception(f"Erro ao buscar XML: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar XML.")

# 🔹 Endpoints separados para obter dados individuais
@app.get("/fetch-realtor-name/")
async def fetch_realtor_name(property_code: str):
    """Retorna apenas o nome da imobiliária."""
    contact_info = await get_property_info(property_code)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Detalhes do imóvel não encontrados.")

    realtor_name = contact_info.find("Name").text if contact_info.find("Name") else "Não informado"
    return {"realtor_name": realtor_name}

@app.get("/fetch-realtor-email/")
async def fetch_realtor_email(property_code: str):
    """Retorna apenas o e-mail da imobiliária."""
    contact_info = await get_property_info(property_code)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Detalhes do imóvel não encontrados.")

    realtor_email = contact_info.find("Email").text if contact_info.find("Email") else "Não informado"
    return {"realtor_email": realtor_email}

@app.get("/fetch-realtor-phone/")
async def fetch_realtor_phone(property_code: str):
    """Retorna apenas o telefone da imobiliária."""
    contact_info = await get_property_info(property_code)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Detalhes do imóvel não encontrados.")

    realtor_phone = contact_info.find("Telephone").text if contact_info.find("Telephone") else "Não informado"
    return {"realtor_phone": realtor_phone}
