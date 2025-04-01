import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import logging
from fastapi import HTTPException

# Global variables
USER_DATA_DIR = "user_data"
SCRAPERAPI_KEY = "2448343edc77475cfabfa7643d45d9cc"
browser_instance = None

async def get_browser():
    """Initialize a Playwright browser with a persistent context."""
    global browser_instance
    if not browser_instance:
        logging.info("Starting Playwright browser in headless mode...")
        p = await async_playwright().start()
        browser_instance = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        # Set a realistic User-Agent
        await browser_instance.add_init_script("""
            navigator.__defineGetter__('userAgent', () => 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36');
        """)
    return browser_instance

async def fetch_html_with_playwright(url: str) -> str:
    """Fetch HTML content using Playwright and ScraperAPI."""
    scraper_url = f"https://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={url}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        )
        context = await browser.new_context()

        # Bloquear carregamento de imagens, fontes e CSS para acelerar
        async def block_unwanted_resources(route):
            if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
                await route.abort()
            else:
                await route.continue_()

        page = await context.new_page()
        await page.route("**/*", block_unwanted_resources)

        try:
            logging.info(f"🔍 Acessando página via ScraperAPI: {scraper_url}")
            await page.goto(scraper_url, wait_until="domcontentloaded", timeout=60000)  
            await page.wait_for_load_state("domcontentloaded")  # Garante que a página carregou

            # Mantém a página aberta por um curto tempo antes de capturar o HTML
            await asyncio.sleep(1)

            html = await page.content()
            return html

        except Exception as e:
            logging.exception(f"Error loading page: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            await page.close()
            await browser.close()

async def fetch_multiple_urls(urls):
    """Fetch multiple URLs concurrently."""
    tasks = [fetch_html_with_playwright(url) for url in urls]
    return await asyncio.gather(*tasks)

# Example usage
if __name__ == "__main__":
    urls = ["https://example.com", "https://example.org"]
    asyncio.run(fetch_multiple_urls(urls))

print("Optimized code implemented.")
