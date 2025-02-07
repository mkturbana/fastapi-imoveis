import os
import logging
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from fastapi import HTTPException

# Criar pasta de usuário para armazenar dados do navegador (cookies, histórico, etc.)
USER_DATA_DIR = "user_data"

browser_instance = None  # Variável global para manter o navegador aberto

async def get_browser():
    """Inicia um navegador real com persistência de dados."""
    global browser_instance
    if not browser_instance:
        logging.info("🔵 Iniciando navegador real com persistência de dados...")

        p = await async_playwright().start()
        
        browser_instance = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,  # 🔴 Mantém cookies e login!
            headless=False,  # 🔴 Rode visível primeiro para testar
            args=["--disable-blink-features=AutomationControlled"],  # 🔴 Evita detecção
        )
    return browser_instance

async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página evitando bloqueios e mantendo sessão."""
    browser = await get_browser()
    page = await browser.new_page()

    # 🔹 Ativando Playwright-Stealth para evitar detecção
    await stealth_async(page)
    await page.evaluate("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'en-US'] });
    """)

    try:
        logging.info(f"🔍 Acessando página: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)  # Pequena espera inicial

        # 🔹 Simulação de interações humanas
        logging.info("👨‍💻 Simulando interações humanas...")
        await page.mouse.move(200, 200)
        await page.wait_for_timeout(1000)
        await page.mouse.wheel(0, 500)  # Scroll para baixo
        await page.wait_for_timeout(2000)
        await page.keyboard.press("ArrowDown")
        await page.keyboard.press("ArrowDown")
        await page.keyboard.press("ArrowDown")
        await page.wait_for_timeout(2000)
        await page.keyboard.press("End")  # Rolar até o final da página
        await page.wait_for_timeout(3000)

        # 🔹 Capturar HTML após as interações
        html = await page.content()

        # 🚨 Verificar bloqueio do Cloudflare
        if "Just a moment" in html or "challenge-platform" in html:
            logging.error("🚨 Página bloqueada pela Cloudflare!")
            raise HTTPException(status_code=403, detail="Página bloqueada pela Cloudflare")

        await page.close()
        logging.info("✅ HTML extraído com sucesso.")
        return html

    except Exception as e:
        logging.exception(f"❌ Erro ao carregar página: {e}")
        await page.close()
        raise HTTPException(status_code=500, detail=str(e))
