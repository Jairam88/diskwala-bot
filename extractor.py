import asyncio
import json
import re
from playwright.async_api import async_playwright


async def extract_direct_url(diskwala_url):
    debug_info = {
        "status": None,
        "title": "Unknown",
        "cloudflare_blocked": False,
        "error": None,
    }
    found_url = None

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1920,1080",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    " AppleWebKit/537.36 (KHTML, like Gecko)"
                    " Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Kolkata",
            )

            page = await context.new_page()

            # Anti-bot stealth scripts
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)

            # Network Response Interceptor (Captures API JSONs & Video Streams)
            async def handle_response(response):
                nonlocal found_url
                try:
                    url = response.url
                    # Catch stream/video links
                    if any(
                        ext in url
                        for ext in [".m3u8", ".mp4", ".m4s", "stream"]
                    ):
                        if not found_url and "googlevideo" not in url:
                            if not url.endswith(
                                (".js", ".css", ".png", ".jpg", ".jpeg", ".svg")
                            ):
                                found_url = url
                                return

                    # Catch JSON API responses
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            json_data = await response.json()
                            json_str = str(json_data)
                            match = re.search(
                                r"https?://[^\s\"']+\.(?:m3u8|mp4)[^\s\"']*",
                                json_str,
                            )
                            if match and not found_url:
                                found_url = match.group(0)
                        except Exception:
                            pass
                except Exception:
                    pass

            page.on("response", handle_response)

            # Navigate to URL
            response = await page.goto(
                diskwala_url, wait_until="domcontentloaded", timeout=35000
            )

            if response:
                debug_info["status"] = response.status

            await page.wait_for_timeout(3000)

            # Check Page Title & Cloudflare Detection
            try:
                title = await page.title()
                debug_info["title"] = title if title else "No Title"
                if any(
                    kw in title.lower()
                    for kw in [
                        "cloudflare",
                        "just a moment",
                        "attention required",
                        "verify you are human",
                    ]
                ):
                    debug_info["cloudflare_blocked"] = True
            except Exception:
                pass

            # 1. Extract from Next.js state (__NEXT_DATA__)
            if not found_url:
                try:
                    next_data_script = await page.query_selector(
                        "script#__NEXT_DATA__"
                    )
                    if next_data_script:
                        json_text = await next_data_script.inner_text()
                        matches = re.findall(
                            r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*",
                            json_text,
                        )
                        for m in matches:
                            if "googlevideo" not in m:
                                found_url = m
                                break
                except Exception as e:
                    print(f"Next.js extract error: {e}")

            # 2. Deep Page HTML Regex Search
            if not found_url:
                html_content = await page.content()
                matches = re.findall(
                    r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*",
                    html_content,
                )
                for m in matches:
                    if "googlevideo" not in m and not m.endswith(
                        (".png", ".jpg", ".js", ".css")
                    ):
                        found_url = m
                        break

            # 3. DOM Elements fallback
            if not found_url:
                found_url = await page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v && v.src && v.src.startsWith('http')) return v.src;
                    const s = document.querySelector('video source');
                    if (s && s.src && s.src.startsWith('http')) return s.src;
                    return null;
                }""")

        except Exception as e:
            debug_info["error"] = str(e)
            print(f"Extraction Exception: {e}")
        finally:
            await browser.close()

    return found_url, debug_info
    
