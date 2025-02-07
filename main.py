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

@app.get("/detect-site/")
async def detect_site(url: str):
    """Detecta o site a partir da URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site_detectado": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

@app.get("/extract-code/")
async def extract_code(url: str, site: str):
    """Extrai o código do imóvel de acordo com o site informado."""
    html = await fetch_html_with_playwright(url)
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

    except httpx.HTTPStatusError as e:
        logging.error(f"Erro HTTP ao acessar XML: {e}")
        raise HTTPException(status_code=e.response.status_code, detail="Erro ao acessar XML.")
    except Exception as e:
        logging.exception(f"Erro ao buscar XML: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar XML.")
