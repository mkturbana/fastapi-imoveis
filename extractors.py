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

    elif site == "buscacuritiba":
        # 🔍 Procurar um <p> que contenha "Referência:"
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            # Extrair o texto do <p> e pegar apenas o código
            match = re.search(r"Referência:\s*([\w-]+)", reference_element.text)
            return match.group(1) if match else None

    return None

def extract_property_code_from_message(message: str):
    """
    Extrai o código do imóvel de uma mensagem do Portal Busca Curitiba.

    Retorna o código do imóvel se encontrado, ou None se não for encontrado.
    """
    match = re.search(r"Referência:\s*([A-Za-z0-9\-]+)", message, re.IGNORECASE)
    
    if match:
        return match.group(1)  # Retorna o código completo (exemplo: AP0237-C41)

    return None  # Retorna None se não encontrar nada
