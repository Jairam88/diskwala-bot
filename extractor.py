import json
import re
from curl_cffi.requests import AsyncSession


def search_json_recursive(data):
    stream_url = None
    title = None

    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower()
            if not title and k_lower in ["title", "filename", "name"]:
                if isinstance(v, str):
                    title = v

            if any(
                term in k_lower
                for term in [
                    "downloadurl",
                    "streamurl",
                    "fileurl",
                    "directurl",
                    "videourl",
                    "stream",
                    "download",
                ]
            ):
                if (
                    isinstance(v, str)
                    and (v.startswith("http") or v.startswith("/"))
                    and "diskwala.com/app" not in v
                ):
                    stream_url = v

        if not stream_url:
            for v in data.values():
                res_url, res_title = search_json_recursive(v)
                if res_url and not stream_url:
                    stream_url = res_url
                if res_title and not title:
                    title = res_title

    elif isinstance(data, list):
        for item in data:
            res_url, res_title = search_json_recursive(item)
            if res_url and not stream_url:
                stream_url = res_url
            if res_title and not title:
                title = res_title

    return stream_url, title


async def extract_diskwala_data(url):
    data_out = {"stream_url": None, "title": "Diskwala Media File", "error": None}

    try:
        async with AsyncSession(impersonate="chrome120") as session:
            resp = await session.get(url, timeout=20)
            if resp.status_code != 200:
                data_out["error"] = f"HTTP Status {resp.status_code}"
                return data_out

            html = resp.text

            # Parse __NEXT_DATA__
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                next_json = json.loads(match.group(1))
                s_url, s_title = search_json_recursive(next_json)
                if s_url:
                    if s_url.startswith("/"):
                        s_url = "https://www.diskwala.com" + s_url
                    data_out["stream_url"] = s_url.replace("\\u0026", "&")
                if s_title:
                    data_out["title"] = s_title

            # Fallback Regex
            if not data_out["stream_url"]:
                raw_urls = re.findall(r'https?://[^\s"\'<>]+', html)
                for u in raw_urls:
                    u_clean = u.replace("\\u0026", "&")
                    if (
                        any(
                            x in u_clean.lower()
                            for x in ["stream", "download", "cdn"]
                        )
                        and "diskwala.com/app" not in u_clean
                    ):
                        if not any(
                            u_clean.endswith(ext)
                            for ext in [
                                ".png",
                                ".jpg",
                                ".js",
                                ".css",
                                ".svg",
                                ".ico",
                            ]
                        ):
                            data_out["stream_url"] = u_clean
                            break

    except Exception as e:
        data_out["error"] = str(e)

    return data_out
    
