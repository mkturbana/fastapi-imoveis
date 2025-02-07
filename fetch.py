async def fetch_html_with_playwright(url: str) -> str:
    """Captura o HTML da página antes de extrair o código."""
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
