import json
import re
from curl_cffi.requests import AsyncSession


async def extract_direct_url(diskwala_url):
    debug_info = {
        "status": None,
        "title": "Unknown",
        "cloudflare_blocked": False,
        "error": None,
    }
    found_url = None

    try:
        # Chrome 120 TLS fingerprint impersonation to bypass Cloudflare
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.get(diskwala_url, timeout=20)
            debug_info["status"] = response.status_code
            html_content = response.text

            # Check if still blocked by Cloudflare challenge
            if (
                "Just a moment" in html_content
                or "cf-mitigation" in html_content
                or "challenge-platform" in html_content
            ):
                debug_info["cloudflare_blocked"] = True

            # 1. Next.js __NEXT_DATA__ Script Search (Ultra Fast)
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html_content,
                re.DOTALL,
            )
            if match:
                json_str = match.group(1)
                urls = re.findall(
                    r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*", json_str
                )
                for u in urls:
                    if "googlevideo" not in u:
                        found_url = u.replace("\\u0026", "&")
                        break

            # 2. General HTML Page Regex Fallback
            if not found_url:
                urls = re.findall(
                    r"https?://[^\s\"'<>]+\.(?:m3u8|mp4)[^\s\"'<>]*", html_content
                )
                for u in urls:
                    if "googlevideo" not in u and not u.endswith(
                        (".png", ".jpg", ".js", ".css")
                    ):
                        found_url = u.replace("\\u0026", "&")
                        break

    except Exception as e:
        debug_info["error"] = str(e)
        print(f"Extraction Error: {e}")

    return found_url, debug_info
    
