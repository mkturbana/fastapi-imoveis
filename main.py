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
from fastapi.responses import Response, JSONResponse, RedirectResponse
from fetch import fetch_html_with_playwright
from extractors import extract_property_code
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from exceptions import http_exception_handler, custom_exception_handler
from cachetools import TTLCache

app = FastAPI(
    title="Minha API de Imóveis",
    description="Documentação da API gerada automaticamente pelo FastAPI.",
    version="1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

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

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redireciona automaticamente para a documentação do FastAPI."""
    return RedirectResponse(url="/docs")

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

@app.get("/start-extract/")
async def start_extract(url: str, site: str, background_tasks: BackgroundTasks):
    """Inicia a extração do código do imóvel e retorna um task_id para buscar o resultado depois."""
    task_id = str(uuid.uuid4())  # Gera um ID único para a tarefa
    extract_results[task_id] = {"status": "processing", "codigo_imovel": None}  # Define status inicial

    # Inicia a extração em segundo plano
    background_tasks.add_task(extract_code_async, url, site, task_id)

    return {"task_id": task_id}

async def extract_code_async(url: str, site: str, task_id: str):
    """Executa a extração do código do imóvel em background e salva o resultado."""
    logging.info(f"🔍 [Tarefa {task_id}] Extraindo código do imóvel para URL: {url} | Site: {site}")

    try:
        html = await fetch_html_with_playwright(url)  # Chama o Playwright
        codigo = extract_property_code(html, site)

        if codigo:
            extract_results[task_id] = {"status": "completed", "codigo_imovel": codigo}
            logging.info(f"✅ [Tarefa {task_id}] Código extraído: {codigo}")
        else:
            extract_results[task_id] = {"status": "error", "codigo_imovel": None}
            logging.warning(f"⚠️ [Tarefa {task_id}] Código não encontrado.")

    except Exception as e:
        extract_results[task_id] = {"status": "error", "codigo_imovel": None}
        logging.error(f"❌ [Tarefa {task_id}] Erro ao extrair código: {e}")

# 🔹 Endpoint para buscar o resultado da extração
@app.get("/get-extract-result/")
async def get_extract_result(task_id: str):
    """Retorna o status e o código do imóvel extraído."""
    result = extract_results.get(task_id)

    if not result:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    return result

# 🔍 Função auxiliar para buscar detalhes no XML com cache
async def fetch_xml_data():
    """Baixa o XML e armazena no cache para otimizar múltiplas chamadas."""
    if "xml_data" in xml_cache:
        return xml_cache["xml_data"]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(XML_URL, timeout=5) as response:
                response.raise_for_status()
                xml_data = await response.text()
                xml_cache["xml_data"] = xml_data  # Salva no cache
                return xml_data
    except Exception as e:
        logging.error(f"Erro ao baixar XML: {e}")
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
