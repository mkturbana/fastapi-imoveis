import os
import re
import json
import httpx
import logging
import asyncio
import aiohttp
import datetime
import uuid
from bs4 import BeautifulSoup
from starlette.requests import Request
from fastapi.responses import Response, JSONResponse
from fetch import fetch_html_with_playwright
from extractors import extract_property_code, extract_property_code_from_message
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, Query
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from cachetools import TTLCache
from exceptions import http_exception_handler, custom_exception_handler

# ---------------------------------------------------
# Configuração e variáveis globais
# ---------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("API Iniciada!")

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "token-bothub-redeurbana#2025")
XML_URL = "https://redeurbana.com.br/imoveis/publico/97b375b0-05d4-48f5-9aeb-e9a1cae78c90"

# Cache para armazenar o XML por 12 horas (43200 segundos)
xml_cache = TTLCache(maxsize=1, ttl=43200)  # 12 horas

# ---------------------------------------------------
# Funções auxiliares para atualização do XML
# ---------------------------------------------------

def seconds_until_next_update(update_times: list) -> float:
    """
    Recebe uma lista de horários (objetos datetime.time) e retorna os segundos até o próximo horário.
    Exemplo: [datetime.time(14, 30), datetime.time(2, 30)]
    """
    now = datetime.datetime.now()
    today = now.date()
    
    # Combina cada objeto datetime.time com a data de hoje
    scheduled_times = [datetime.datetime.combine(today, ut) for ut in update_times]
    
    # Filtra os horários que ainda não passaram hoje
    future_times = [t for t in scheduled_times if t > now]
    
    if future_times:
        next_time = min(future_times)
    else:
        # Se todos os horários de hoje já passaram, o próximo será o primeiro do dia seguinte
        next_time = datetime.datetime.combine(today + datetime.timedelta(days=1), update_times[0])
    
    return (next_time - now).total_seconds()

async def update_xml_cache():
    """
    Faz a requisição para baixar o XML e atualiza o cache.
    Timeout ajustado para 600 segundos para suportar XML lento.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(XML_URL, timeout=600) as response:
                response.raise_for_status()
                xml_data = await response.text()
                xml_cache["xml_data"] = xml_data
                logging.info("XML atualizado no cache.")
                return xml_data
    except Exception as e:
        logging.error(f"Erro ao atualizar XML: {e}")
        # Aqui você pode optar por retornar None ou lançar uma exceção
        return None

# Função para agendar a atualização do cache em horários específicos (por exemplo, às 08:00 e às 20:00)
async def scheduled_xml_update():
    # Atualiza o cache às 11:30 e às 23:30
    update_times = [datetime.time(14, 13), datetime.time(2, 30)]
    while True:
        delay = seconds_until_next_update(update_times)
        logging.info(f"Aguardando {delay/60:.2f} minutos para a próxima atualização do XML.")
        await asyncio.sleep(delay)
        await update_xml_cache()

# ---------------------------------------------------
# Função para manter o servidor ativo (Keep-Alive)
# ---------------------------------------------------
async def keep_alive_task():
    while True:
        await asyncio.sleep(120)
        logging.info("💡 Keep-alive: Servidor ainda está rodando...")

# ---------------------------------------------------
# Criação da instância FastAPI e configuração
# ---------------------------------------------------
app = FastAPI()

# Configuração dos handlers de erro
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, custom_exception_handler)

# Middleware para log
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

        # Criar uma cópia segura da resposta (para lidar com _StreamingResponse)
        response_body = b"".join([chunk async for chunk in response.body_iterator])

        try:
            logging.info(f"✅ RESPOSTA: {response.status_code} - {response_body.decode()}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao capturar a resposta: {e}")

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

# Adiciona o middleware na API
app.add_middleware(LogMiddleware)

# ---------------------------------------------------
# Endpoints
# ---------------------------------------------------

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Verifica a assinatura do webhook no WhatsApp API."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)  # Responde com o desafio para validar
    else:
        return {"error": "Token inválido"}, 403 

@app.get("/")
async def root():
    return {"message": "API de Imóveis está online! 🚀"}

@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai uma URL de uma mensagem enviada pelo usuário."""
    match = re.search(r"https?://[^\s]+", message)
    if match:
        # Remove barra(s) no final do URL, caso exista(m)
        url_extracted = match.group(0).rstrip('/')
        return {"url_extraida": url_extracted}
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")

@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/.]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

# 🔹 Endpoint Único para extrair código do imóvel (Otimizado)

@app.get("/extract-code-html/")
async def extract_code_html_endpoint(url: str, site: str):
    """Extrai o código do imóvel o mais rápido possível."""

    logging.info(f"🔍 Extraindo código do imóvel para URL: {url} | Site: {site}")

    try:
        html = await fetch_html_with_playwright(url)
        codigo = extract_property_code(html, site)
    
        if not codigo:
            raise HTTPException(status_code=404, detail="Código do imóvel não encontrado.")

        return {"codigo_imovel": codigo}

    except Exception as e:
        logging.error(f"❌ Erro ao extrair código: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar a requisição.")

@app.post("/extract-code-message/")
async def extract_code_message_endpoint(message: str):
    codigo = extract_property_code_from_message(message)
    if not codigo:
        raise HTTPException(
            status_code=400,
            detail="Código do imóvel não encontrado na mensagem."
        )
    return codigo

# 🔍 Função auxiliar para buscar detalhes no XML com cache
async def fetch_xml_data():
    """Retorna o XML armazenado no cache. Se o cache estiver vazio, tenta buscar o XML diretamente com um timeout maior."""
    if "xml_data" in xml_cache:
        return xml_cache.get("xml_data")

    # Se o cache estiver vazio, faz o fallback com timeout aumentado
    try:
        async with aiohttp.ClientSession() as session:
            # Timeout de 600 segundos (10 minutos) para a requisição direta
            async with session.get(XML_URL, timeout=600) as response:
                response.raise_for_status()
                xml_data = await response.text()
                xml_cache["xml_data"] = xml_data  # Atualiza o cache para futuras chamadas
                logging.info("XML obtido via fallback e atualizado no cache.")
                return xml_data
    except Exception as e:
        logging.error(f"Erro ao buscar XML no fallback: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar XML.")

async def get_property_info_optimized(property_code: str, xml_data: str):
    """Busca os detalhes do imóvel no XML usando caching para melhor performance."""
    soup = BeautifulSoup(xml_data, "xml")
    property_info = soup.find("ListingID", string=property_code)

    if not property_info:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

    listing = property_info.find_parent("Listing")
    return listing.find("ContactInfo") if listing else None

# 🔹 Endpoint único para obter todas as informações do imóvel
@app.get("/fetch-xml/")
async def fetch_xml(property_code: str, xml_data: str = Depends(fetch_xml_data)):
    """Retorna todas as informações da imobiliária em uma única requisição, usando cache para otimizar a resposta."""
    contact_info = await get_property_info_optimized(property_code, xml_data)
    if not contact_info:
        raise HTTPException(status_code=404, detail="Detalhes do imóvel não encontrados.")

    return {
        "realtor_name": contact_info.find("Name").text if contact_info.find("Name") else "Não informado",
        "realtor_email": contact_info.find("Email").text if contact_info.find("Email") else "Não informado",
        "realtor_phone": contact_info.find("Telephone").text if contact_info.find("Telephone") else "Não informado",
    }

# ---------------------------------------------------
# Evento de Startup (único) para iniciar tarefas de background
# ---------------------------------------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_task())

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_xml_update())
