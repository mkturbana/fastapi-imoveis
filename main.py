import re
import json
import httpx
import logging
from bs4 import BeautifulSoup
from starlette.requests import Request
from fastapi.responses import Response, JSONResponse
from fetch import fetch_html_with_playwright
from extractors import extract_property_code
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from exceptions import http_exception_handler, custom_exception_handler

app = FastAPI()

# Configuração dos handlers de erro
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, custom_exception_handler)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("API Iniciada!")

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
        
        # Criar um novo Response com o mesmo conteúdo
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
    print(f"URL recebida: {url}")
    print(f"Site recebido: {site}")
    """Extrai o código do imóvel de acordo com o site informado."""
    html = await fetch_html_with_playwright(url)
    if not html:
        raise HTTPException(status_code=500, detail="Erro ao carregar página do imóvel.")
 
    codigo = extract_property_code(html, site)
    
    if not codigo:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado.")

    return {"codigo_imovel": codigo}

@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código extraído."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"
    
    try:
        response = httpx.get(xml_url, timeout=10)
        response.raise_for_status()  # Garante que erros HTTP sejam tratados corretamente

        soup = BeautifulSoup(response.text, "xml")
        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            logging.warning(f"⚠️ Código do imóvel {property_code} não encontrado no XML.")
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        listing = property_info.find_parent("Listing") if property_info else None
        if not listing:
            logging.warning(f"⚠️ Não foi possível encontrar detalhes do imóvel {property_code}.")
            raise HTTPException(status_code=404, detail="Detalhes do imóvel não encontrados.")

        contact_info = listing.find("ContactInfo") if listing else None

        realtor_name = contact_info.find("Name").text if contact_info and contact_info.find("Name") else "Não informado"
        realtor_email = contact_info.find("Email").text if contact_info and contact_info.find("Email") else "Não informado"
        realtor_phone = contact_info.find("Telephone").text if contact_info and contact_info.find("Telephone") else "Não informado"

        return {
            "realtor_name": realtor_name,
            "realtor_email": realtor_email,
            "realtor_phone": realtor_phone
        }

    except httpx.HTTPStatusError as e:
        logging.error(f"Erro HTTP ao acessar XML: {e}")
        raise HTTPException(status_code=e.response.status_code, detail="Erro ao acessar XML.")
    except Exception as e:
        logging.exception(f"Erro ao buscar XML: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar XML.")
