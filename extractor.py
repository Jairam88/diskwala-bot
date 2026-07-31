import json
import re
from curl_cffi.requests import AsyncSession


def find_urls_in_dict(obj):
    links = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                links.extend(find_urls_in_dict(v))
            elif isinstance(v, str) and (
                v.startswith("http://") or v.startswith("https://")
            ):
                if not v.endswith(
                    (".png", ".jpg", ".jpeg", ".svg", ".css", ".js", ".ico")
                ):
                    links.append((k, v))
    elif isinstance(obj, list):
        for item in obj:
            links.extend(find_urls_in_dict(item))
    return links


async def extract_direct_url(diskwala_url):
    debug_info = {
        "status": None,
        "title": "Unknown",
        "cloudflare_blocked": False,
        "error": None,
    }
    found_url = None

    try:
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.get(diskwala_url, timeout=20)
            debug_info["status"] = response.status_code
            html_content = response.text

            # 1. Parse __NEXT_DATA__ JSON State
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html_content,
                re.DOTALL,
            )
            if match:
                try:
                    next_json = json.loads(match.group(1))
                    all_urls = find_urls_in_dict(next_json)

                    # Check for video / stream / download keys
                    for key, url in all_urls:
                        if any(
                            term in key.lower() or term in url.lower()
                            for term in [
                                "stream",
                                "download",
                                "file",
                                "video",
                                "m3u8",
                                "mp4",
                                "url",
                            ]
                        ):
                            if "googlevideo" not in url and "next" not in url:
                                found_url = url.replace("\\u0026", "&")
                                break

                    # Fallback to any non-diskwala external stream URL in JSON
                    if not found_url and all_urls:
                        for key, url in all_urls:
                            if "diskwala.com" not in url:
                                found_url = url.replace("\\u0026", "&")
                                break
                except Exception as json_err:
                    print(f"JSON Parse Error: {json_err}")

            # 2. Try Diskwala Internal API Route
            file_id_match = re.search(r"/app/([a-zA-Z0-9]+)", diskwala_url)
            if not found_url and file_id_match:
                file_id = file_id_match.group(1)
                api_endpoints = [
                    f"https://www.diskwala.com/api/file/{file_id}",
                    f"https://www.diskwala.com/api/files/{file_id}",
                    f"https://www.diskwala.com/api/stream/{file_id}",
                ]
                for api_url in api_endpoints:
                    try:
                        api_res = await session.get(api_url, timeout=10)
                        if api_res.status_code == 200:
                            api_data = api_res.json()
                            api_links = find_urls_in_dict(api_data)
                            if api_links:
                                found_url = api_links[0][1].replace(
                                    "\\u0026", "&"
                                )
                                break
                    except Exception:
                        pass

            # 3. Fallback: Raw HTML Regex Search
            if not found_url:
                urls = re.findall(
                    r"https?://[^\s\"'<>]+\.(?:m3u8|mp4|mkv)[^\s\"'<>]*",
                    html_content,
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
    
