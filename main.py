import logging
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from bs4 import BeautifulSoup
from exceptions import http_exception_handler, custom_exception_handler
from fetch import fetch_html_with_playwright
from extractors import extract_property_code

app = FastAPI()

# Configuração dos handlers de erro
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, custom_exception_handler)

logging.basicConfig(level=logging.INFO)
logging.info("API Iniciada!")

# ------------------------------------------------------------------------------

@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai uma URL de uma mensagem enviada pelo usuário."""
    match = re.search(r"https?://[^\s]+", message)
    if match:
        return {"url_extraida": match.group(0)}
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")

@app.get("/extract-code/")
async def extract_code(url: str, site: str):
    """Extrai o código do imóvel de acordo com o site informado."""
    html = await fetch_html_with_playwright(url)
    codigo = extract_property_code(html, site)
    
    if not codigo:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado.")

    return {"site": site, "codigo_imovel": codigo}

@app.get("/fetch-xml/")
async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código extraído."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c628
