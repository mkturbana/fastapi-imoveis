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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            bypass_csp=True,
            storage_state="state.json",
            viewport={"width": 1280, "height": 720},
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document"
            }
        )
    return browser_instance, context_instance

async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página evitando bloqueios e simulando interações humanas."""
    browser, context = await get_browser()
    page = await context.new_page()

    # Ativando Playwright-Stealth para evitar detecção
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
        await page.wait_for_timeout(3000)  # Pequena espera inicial

        # 🔹 Simulação de interações humanas para evitar bloqueio
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
