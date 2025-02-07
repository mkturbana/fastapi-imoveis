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
        await page.wait_for_timeout(6000)  # Pequena espera inicial

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
