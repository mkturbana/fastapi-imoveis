@app.get("/extract-code/")
async def extract_property_code(url_anuncio: str, site_detectado: str):
    """Captura o HTML da página e extrai o código do imóvel com Playwright."""
    
    # 📩 Captura o HTML usando Playwright
    html = await fetch_html_with_playwright(url_anuncio)
    soup = BeautifulSoup(html, "html.parser")

    property_code = None

    if "imovelweb.com.br" in site_detectado:
        match = re.search(r'publisher_house_id\s*=\s*"([\w-]+)"', html)
        property_code = match.group(1) if match else None

    elif "chavesnamao.com.br" in site_detectado:
        match = re.search(r'Ref:\s*<!--\s*-->\s*([\w-]+)', html)
        property_code = match.group(1) if match else None

    elif "buscacuritiba.com.br" in site_detectado:
        reference_element = soup.find("p", string=re.compile("Referência:", re.IGNORECASE))
        if reference_element:
            strong_tag = reference_element.find("strong")
            property_code = strong_tag.text.strip() if strong_tag else None

    else:
        match = re.search(r'(ID[:.\s]*\d+|Código[:.\s]*\d+|ref[:.\s]*\d+)', html)
        property_code = match.group(1) if match else None

    # 🔍 Se nenhum código for encontrado, retorna erro 404
    if not property_code:
        raise HTTPException(status_code=404, detail="Código do imóvel não encontrado no HTML.")

    return {"codigo_imovel": property_code}
