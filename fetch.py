import os
import json
import logging
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from fastapi import HTTPException

# Criar state.json se não existir
if not os.path.exists("state.json"):
    with open("state.json", "w") as f:
        f.write('{"cookies": [], "origins": []}')
    logging.info("Arquivo state.json criado.")

# Criar um navegador persistente para evitar fechamento prematuro
browser_instance = None
context_instance = None

async def get_browser():
    global browser_instance, context_instance
    if not browser_instance:
        logging.info("🔵 Iniciando navegador Playwright...")
        p = await async_playwright().start()
        browser_instance = await p.chromium.launch(headless=True)
        context_instance = await browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            bypass_csp=True,
            storage_state="state.json",
            viewport={"width": 1280, "height": 720}
        )
    return browser_instance, context_instance

async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página evitando bloqueios e fechamentos inesperados"""
    browser, context = await get_browser()
    page = await context.new_page()
    await stealth_async(page)

    try:
        await page.goto(url, wait_until="domcontentloaded")
        html = await page.content()

        # Verificação para bloqueios (Cloudflare)
        if "Just a moment" in html or "challenge-platform" in html:
            logging.error("🚨 Página bloqueada pela Cloudflare!")
            raise HTTPException(status_code=403, detail="Página bloqueada pela Cloudflare")

        # Salvar estado atualizado
        await context.storage_state(path="state.json")
        await page.close()  # 🔴 AGORA FECHAMOS APENAS A PÁGINA, NÃO O NAVEGADOR

        logging.info("✅ HTML extraído com sucesso.")
        return html

    except Exception as e:
        logging.exception(f"❌ Erro ao carregar página: {e}")
        await page.close()
        raise HTTPException(status_code=500, detail=str(e))
