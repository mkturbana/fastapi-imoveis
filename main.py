import re
import logging
import httpx
from fastapi import FastAPI, HTTPException, Query
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

app = FastAPI()

# URL fixa do XML da imobiliária
XML_URL = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

logging.basicConfig(level=logging.INFO)

# 🏡 Função para buscar HTML com Selenium
def fetch_html_with_selenium(url: str) -> str:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Adiciona User-Agent realista
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    )

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    html = driver.page_source

    # Salva o HTML para depuração
    with open("pagina.html", "w", encoding="utf-8") as f:
        f.write(html)

    driver.quit()

    # Verifica se houve bloqueio
    if "Acesso negado" in html or "Verifique que você não é um robô" in html:
        raise HTTPException(status_code=403, detail="O site bloqueou o acesso via Selenium.")

    return html

# 🔎 Detecta o site de origem
@app.get("/detect-site/")
async def detect_site(url: str = Query(..., description="URL do imóvel")):
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return {"site": match.group(1)}
    raise HTTPException(status_code=400, detail="URL inválida.")

# 🌍 Busca o HTML da página
@app.get("/fetch-html/")
async def fetch_property_info(property_code: str = Query(..., description="Código do imóvel")):
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"

    try:
        response = httpx.get(XML_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")

        # Busca pelo código do imóvel dentro da tag <ListingID>
        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        # 🏡 Extrai informações da imobiliária
        real_estate = soup.find("CompanyName").text if soup.find("CompanyName") else "Desconhecido"
        agent_name = soup.find("ContactName").text if soup.find("ContactName") else "Não informado"
        contact = soup.find("PhoneNumber").text if soup.find("PhoneNumber") else "Não disponível"

        return {
            "property_code": property_code,
            "real_estate": real_estate,
            "agent_name": agent_name,
            "contact": contact
        }

    except Exception as e:
        logging.error(f"Erro ao acessar XML: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao buscar XML.")

# 🔢 Extrai código do imóvel com regras específicas para cada site
@app.get("/extract-code/")
async def extract_property_code(url: str):
    """Extrai o código do imóvel do HTML, de acordo com cada site."""
    html = fetch_html_with_selenium(url)
    soup = BeautifulSoup(html, "html.parser")

    site_info = await detect_site(url)
    site = site_info["site"]
    property_code = None

    if "imovelweb" in site:
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        property_code = match.group(1) if match else None
    elif "chavesnamao" in site:
        match = re.search(r'Ref:\s*<!--\s*-->\s*([\w-]+)', html)
        property_code = match.group(1) if match else None
    elif "buscacuritiba" in site:
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            strong_tag = reference_element.find("strong")
            property_code = strong_tag.text.strip() if strong_tag else None
    else:
        match = re.search(r'(ID[:.\s]*\d+|Código[:.\s]*\d+|ref[:.\s]*\d+)', html)
        property_code = match.group(1) if match else None

    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

    return {"property_code": property_code}

# 📄 Busca informações do imóvel no XML
@app.get("/fetch-xml/")

async def fetch_property_info(property_code: str):
    """Busca informações do imóvel no XML usando o código do imóvel."""
    xml_url = "https://redeurbana.com.br/imoveis/rede/c6280d26-b925-405f-8aab-dd3afecd2c0b"
    
    try:
        response = httpx.get(xml_url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erro ao acessar XML.")

        soup = BeautifulSoup(response.text, "xml")

        # 🏠 Busca pelo código do imóvel dentro da tag <ListingID>
        property_info = soup.find("ListingID", string=property_code)
        if not property_info:
            raise HTTPException(status_code=404, detail="Imóvel não encontrado no XML.")

        # 🔍 Pega o elemento pai para acessar os dados completos do imóvel
        listing = property_info.find_parent("Listing")
        
        # 📋 Extrai as informações da imobiliária
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
        raise HTTPException(status_code=500, detail=str(e))


# 🔗 Extrai URL de uma mensagem enviada pelo usuário
@app.post("/extract-url/")
async def extract_url_from_message(message: str):
    """Extrai a URL de uma mensagem."""
    url_match = re.search(r'(https?://[^\s]+)', message)
    if url_match:
        return {"url": url_match.group(1)}
    
    raise HTTPException(status_code=400, detail="Nenhuma URL encontrada na mensagem.")
