import re
from bs4 import BeautifulSoup, Comment

def extract_property_code(html: str, site: str):
    """Extrai o código do imóvel baseado no site informado."""
    soup = BeautifulSoup(html, "html.parser")

    if site == "imovelweb":
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        return match.group(1) if match else None

    elif site == "chavesnamao":
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            match = re.search(r"Ref:\s*([\w-]+)", comment)
            if match:
                return match.group(1)
        
        match = re.search(r"ref:\s*do imóvel[:\s]*([\w-]+)", html, re.IGNORECASE)
        return match.group(1) if match else None

def extract_property_code_from_message(message: str):
    """
    Extrai o código do imóvel de uma mensagem.
    Se encontrar, retorna o código (ex.: AP0237-C41).
    Se não encontrar, retorna mensagem de erro.
    """
    # (?:Referência:\s*)? significa "pode ter 'Referência:' seguido de espaços, ou não"
    # ([A-Za-z0-9-]+) captura a sequência de letras, dígitos ou hífens
    match = re.search(r"(?:Referência:\s*)?([A-Za-z0-9-]+)", message, re.IGNORECASE)
    
    if match:
        return match.group(1)
    
    return "Código do imóvel não encontrado na mensagem"
