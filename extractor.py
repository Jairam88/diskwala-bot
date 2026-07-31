import json
import re
import aiohttp


async def extract_direct_url(diskwala_url):
    debug_info = {
        "status": None,
        "title": "Unknown",
        "cloudflare_blocked": False,
        "error": None,
    }
    found_url = None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                diskwala_url, headers=headers, timeout=15
            ) as response:
                debug_info["status"] = response.status
                html_content = await response.text()

                # Cloudflare check
                if (
                    "Just a moment" in html_content
                    or "cloudflare" in html_content.lower()
                ):
                    debug_info["cloudflare_blocked"] = True

                # 1. Next.js __NEXT_DATA__ JSON Parser (Ultra Fast)
                match = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    html_content,
                    re.DOTALL,
                )
                if match:
                    json_str = match.group(1)
                    # Extract m3u8 or mp4 links inside Next.js data
                    urls = re.findall(
                        r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*", json_str
                    )
                    for u in urls:
                        if "googlevideo" not in u:
                            found_url = u.replace("\\u0026", "&")
                            break

                # 2. General Page HTML Regex Search Fallback
                if not found_url:
                    urls = re.findall(
                        r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*",
                        html_content,
                    )
                    for u in urls:
                        if "googlevideo" not in u and not u.endswith(
                            (".png", ".jpg", ".js", ".css")
                        ):
                            found_url = u
                            break

    except Exception as e:
        debug_info["error"] = str(e)
        print(f"Extraction Error: {e}")

    return found_url, debug_info
    
