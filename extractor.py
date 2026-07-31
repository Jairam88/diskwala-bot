import asyncio
from playwright.async_api import async_playwright


async def extract_direct_url(diskwala_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        found_url = None

        # Network requests interceptor
        async def handle_request(request):
            nonlocal found_url
            url = request.url
            # Filter standard video formats and streaming APIs
            if (
                any(
                    ext in url
                    for ext in [".mp4", ".m3u8", ".m4s", "stream", "video/"]
                )
                and "googlevideo" not in url
            ):
                if not found_url and not url.endswith(
                    (".js", ".css", ".png", ".jpg", ".jpeg", ".svg")
                ):
                    found_url = url

        page.on("request", handle_request)

        try:
            # Full network load ayyevaraku wait chestam
            await page.goto(
                diskwala_url, wait_until="domcontentloaded", timeout=40000
            )
            await page.wait_for_timeout(4000)

            # Auto-click play elements on Diskwala page to trigger video stream
            play_selectors = [
                "video",
                ".vjs-big-play-button",
                "button:has-text('Play')",
                ".play-btn",
                "#player",
                "iframe",
            ]
            for selector in play_selectors:
                try:
                    if await page.is_visible(selector):
                        await page.click(selector, timeout=2000)
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            # DOM fallback check (If video tag exists directly)
            if not found_url:
                video_src = await page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v && v.src && v.src.startsWith('http')) return v.src;
                    const s = document.querySelector('source');
                    if (s && s.src && s.src.startsWith('http')) return s.src;
                    return null;
                }""")
                if video_src:
                    found_url = video_src

        except Exception as e:
            print(f"Extraction Error: {e}")
        finally:
            await browser.close()

        return found_url
        
