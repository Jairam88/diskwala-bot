import asyncio
import json
import os
import re
from aiohttp import web
from curl_cffi.requests import AsyncSession
from pyrogram import Client, filters

# =========================================================
# MEE TELEGRAM DETAILS (ALREADY WORKING):
# =========================================================
API_ID = 30918158  # Quotes lekunda numeric ID
API_HASH = "795178cb0ef1cc68690b1bbe82960214"  # Mee Hash string
BOT_TOKEN = "7999558903:AAFmnpddylgWzlofbslPYtviziARBYya-i0"  # Mee Bot token
# =========================================================


# Render Health Check Keeper
async def handle_health(request):
    return web.Response(text="Diskwala Auto-Uploader Bot is Alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


def find_url_in_json(data):
    if isinstance(data, dict):
        for k, v in data.items():
            k_str = str(k).lower()
            if isinstance(v, str):
                clean_v = v.replace("\\u0026", "&")
                if clean_v.startswith("http") or clean_v.startswith("/"):
                    if not any(
                        clean_v.endswith(ext)
                        for ext in [
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".svg",
                            ".css",
                            ".js",
                            ".ico",
                        ]
                    ):
                        if (
                            "diskwala.com/app" not in clean_v
                            and "next" not in clean_v
                        ):
                            if any(
                                x in k_str or x in clean_v.lower()
                                for x in [
                                    "stream",
                                    "download",
                                    "file",
                                    "url",
                                    "path",
                                    "link",
                                ]
                            ):
                                return clean_v
            res = find_url_in_json(v)
            if res:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_url_in_json(item)
            if res:
                return res
    return None


async def extract_url(diskwala_url):
    try:
        file_id_match = re.search(r"/app/([a-zA-Z0-9]+)", diskwala_url)
        file_id = file_id_match.group(1) if file_id_match else None

        async with AsyncSession(impersonate="chrome120") as session:
            # 1. Internal API
            if file_id:
                for api in [
                    f"https://www.diskwala.com/api/file/{file_id}",
                    f"https://www.diskwala.com/api/stream/{file_id}",
                ]:
                    try:
                        res = await session.get(api, timeout=5)
                        if res.status_code == 200:
                            found = find_url_in_json(res.json())
                            if found:
                                if found.startswith("/"):
                                    found = "https://www.diskwala.com" + found
                                return found, None
                    except Exception:
                        pass

            # 2. Next.js Page Data
            resp = await session.get(diskwala_url, timeout=15)
            if resp.status_code == 200:
                match = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    resp.text,
                    re.DOTALL,
                )
                if match:
                    found = find_url_in_json(json.loads(match.group(1)))
                    if found:
                        if found.startswith("/"):
                            found = "https://www.diskwala.com" + found
                        return found, None

            if file_id:
                return f"https://www.diskwala.com/stream/{file_id}", None

            return None, "Direct link find avvaledhu."
    except Exception as e:
        return None, str(e)


bot = Client(
    "diskwala_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "⚡ **Welcome to Diskwala Direct Video Bot.**\n"
        "Diskwala link pampi, direct ga Telegram Video file teeskondi!"
    )


@bot.on_message(filters.text & filters.private)
async def handle_msg(client, message):
    text = message.text.strip()
    if text.startswith("/") or "http" not in text:
        return

    status = await message.reply_text("🔎 **Extracting Video Stream Link...**")
    stream_url, err = await extract_url(text)

    if not stream_url:
        await status.edit_text(f"❌ **Extraction Failed!**\nDetails: `{err}`")
        return

    file_path = f"video_{message.id}.mp4"

    try:
        await status.edit_text("📥 **Downloading Video from Diskwala...**")

        async with AsyncSession(impersonate="chrome120") as session:
            async with session.get(
                stream_url, timeout=120, stream=True
            ) as resp:
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in resp.aiter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                else:
                    await status.edit_text(
                        f"❌ Download Failed! Status: {resp.status_code}"
                    )
                    return

        await status.edit_text("📤 **Uploading Video to Telegram...**")

        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption="⚡ **Downloaded via Diskwala Bot**",
            supports_streaming=True,
        )

        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Processing Error: {str(e)}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    print("🚀 Diskwala Auto-Uploader Bot is Starting...")
    bot.run()
    
