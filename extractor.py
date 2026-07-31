import asyncio
from playwright.async_api import async_playwright

async def extract_direct_url(diskwala_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        found_url = None

        async def handle_request(request):
            nonlocal found_url
            url = request.url
            if ".mp4" in url or ".m3u8" in url or "stream" in url:
                if not found_url and "googlevideo" not in url:
                    found_url = url

        page.on("request", handle_request)

        try:
            await page.goto(diskwala_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Error while fetching: {e}")
        finally:
            await browser.close()
            
        return found_url
      
