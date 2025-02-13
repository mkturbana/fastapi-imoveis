import os
import re
import json
import httpx
import logging
import asyncio
import aiohttp
import uuid
from bs4 import BeautifulSoup
from starlette.requests import Request
from fastapi.responses import Response, JSONResponse
from fetch import fetch_html_with_playwright
from extractors import extract_property_code
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from cachetools import TTLCache
from exceptions import http_exception_handler, custom_exception_handler

app = FastAPI()

# Pega o Verify Token do ambiente
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "token-bothub-redeurbana#2025")

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

# Configuração dos handlers de erro
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, custom_exception_handler)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("API Iniciada!")

XML_URL = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

# Cache para armazenar o XML por 60 segundos
xml_cache = TTLCache(maxsize=1, ttl=60)

# 🔄 Dicionário para armazenar os resultados temporários do Playwright
extract_results = {}

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
