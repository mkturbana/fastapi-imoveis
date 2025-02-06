import logging
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
from exceptions import http_exception_handler, custom_exception_handler
from fetch import fetch_html_with_playwright

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

@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

@app.get("/fetch-page/")
async def fetch_page(url: str):
    """Endpoint para capturar o HTML de uma página"""
    html = await fetch_html_with_playwright(url)
    return {"html": html}
