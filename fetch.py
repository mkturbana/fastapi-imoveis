import os
import logging
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from fastapi import HTTPException

# Criar pasta de usuário para armazenar cookies e histórico
USER_DATA_DIR = "user_data"

browser_instance = None  # Variável global para manter o navegador aberto

async def get_browser():
    """Inicia um navegador Playwright com um User-Agent realista."""
    global browser_instance
    if not browser_instance:
        logging.info("🔵 Iniciando navegador Playwright em modo headless...")

        p = await async_playwright().start()
        
        browser_instance = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Definir um User-Agent mais realista
        await browser_instance.add_init_script("""
            navigator.__defineGetter__('userAgent', () => 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36');
        """)

    return browser_instance

SCRAPERAPI_KEY = "2448343edc77475cfabfa7643d45d9cc"

async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página usando ScraperAPI para evitar bloqueios."""
    scraper_url = f"https://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={url}"
    
    browser = await get_browser()
    page = await browser.new_page()

    await stealth_async(page)

    try:
        logging.info(f"🔍 Acessando página via ScraperAPI: {scraper_url}")
        await page.goto(scraper_url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)

        html = await page.content()
        await page.close()
        return html

    except Exception as e:
        logging.exception(f"❌ Erro ao carregar página: {e}")
        await page.close()
        raise HTTPException(status_code=500, detail=str(e))

