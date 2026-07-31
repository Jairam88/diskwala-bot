import asyncio
import re
from playwright.async_api import async_playwright


async def extract_direct_url(diskwala_url):
    async with async_playwright() as p:
        # Launch Chromium with anti-bot detection flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        page = await context.new_page()

        # Bypass navigator.webdriver detection
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () =>"
            " undefined})"
        )

        found_url = None

        # 1. Listen to all Network Responses (Captures API JSON & Stream Requests)
        async def handle_response(response):
            nonlocal found_url
            try:
                url = response.url

                # Check direct stream extensions
                if any(
                    ext in url for ext in [".m3u8", ".mp4", ".m4s", "stream"]
                ):
                    if not found_url and "googlevideo" not in url:
                        if not url.endswith(
                            (".js", ".css", ".png", ".jpg", ".jpeg", ".svg")
                        ):
                            found_url = url
                            return

                # Check JSON responses sent by Diskwala backend APIs
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type and "diskwala" in url:
                    json_data = await response.json()
                    json_str = str(json_data)
                    match = re.search(
                        r"https?://[^\s\"']+\.(?:m3u8|mp4)[^\s\"']*", json_str
                    )
                    if match and not found_url:
                        found_url = match.group(0)
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            # Navigate to page
            await page.goto(
                diskwala_url, wait_until="domcontentloaded", timeout=35000
            )
            await page.wait_for_timeout(4000)

            # Auto-click play elements on screen
            play_selectors = [
                "video",
                ".vjs-big-play-button",
                "button",
                "iframe",
                "a",
            ]
            for selector in play_selectors:
                try:
                    if await page.is_visible(selector):
                        await page.click(selector, timeout=1500)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

            # 2. Fallback: Deep HTML Regex Scan
            if not found_url:
                html_content = await page.content()
                matches = re.findall(
                    r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*", html_content
                )
                for m in matches:
                    if "googlevideo" not in m and not m.endswith(
                        (".png", ".jpg", ".js", ".css")
                    ):
                        found_url = m
                        break

            # 3. Fallback: Query DOM elements
            if not found_url:
                found_url = await page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v && v.src) return v.src;
                    const s = document.querySelector('video source');
                    if (s && s.src) return s.src;
                    const iframe = document.querySelector('iframe');
                    if (iframe && iframe.src && (iframe.src.includes('m3u8') || iframe.src.includes('mp4'))) return iframe.src;
                    return null;
                }""")

        except Exception as e:
            print(f"Extraction Error: {e}")
        finally:
            await browser.close()

        return found_url
        
