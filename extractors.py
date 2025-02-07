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
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            strong_tag = reference_element.find("strong")
            return strong_tag.text.strip() if strong_tag else None

    return None
