import os
import logging
import async
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

async def fetch_html_with_playwright(url: str, timeout: int = 10000, max_retries: int = 3) -> str:
    """Obtém o HTML de uma página usando Playwright com retries"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                await page.goto(url, timeout=timeout)
                html = await page.content()
                
                await browser.close()
                return html
        
        except Exception as e:
            retry_count += 1
            print(f"Erro ao carregar {url}. Tentativa {retry_count}/{max_retries}: {e}")

    raise Exception(f"Falha ao carregar a página {url} após {max_retries} tentativas.")
