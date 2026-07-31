import asyncio
import json
import os
import re
from aiohttp import web
from curl_cffi.requests import AsyncSession
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# =========================================================
# 1. MEE TELEGRAM DETAILS (ALREADY WORKING ONES):
# =========================================================
API_ID = 30918158  # Quotes lekunda numeric ID
API_HASH = "795178cb0ef1cc68690b1bbe82960214"  # Mee Hash string
BOT_TOKEN = "7999558903:AAFmnpddylgWzlofbslPYtviziARBYya-i0"  # Mee Bot token
# =========================================================


# Render Port Keeper
async def handle_health(request):
    return web.Response(text="Diskwala Bot is Alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


def find_url_in_json(data):
    """Recursively search JSON tree for any media/stream link."""
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
                            ".webp",
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
                                    "src",
                                    "link",
                                    "media",
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
            # 1. Try Diskwala Internal API Routes
            if file_id:
                api_endpoints = [
                    f"https://www.diskwala.com/api/file/{file_id}",
                    f"https://www.diskwala.com/api/v1/file/{file_id}",
                    f"https://www.diskwala.com/api/download/{file_id}",
                    f"https://www.diskwala.com/api/stream/{file_id}",
                ]
                for api in api_endpoints:
                    try:
                        res = await session.get(api, timeout=5)
                        if res.status_code == 200:
                            data = res.json()
                            found = find_url_in_json(data)
                            if found:
                                if found.startswith("/"):
                                    found = "https://www.diskwala.com" + found
                                return found, None
                    except Exception:
                        pass

            # 2. Try HTML Page Next.js Data Parse
            resp = await session.get(diskwala_url, timeout=15)
            if resp.status_code == 200:
                html = resp.text
                match = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    html,
                    re.DOTALL,
                )
                if match:
                    try:
                        data = json.loads(match.group(1))
                        found = find_url_in_json(data)
                        if found:
                            if found.startswith("/"):
                                found = "https://www.diskwala.com" + found
                            return found, None
                    except Exception:
                        pass

            # 3. Fallback Stream URL Pattern
            if file_id:
                return f"https://www.diskwala.com/stream/{file_id}", None

            return None, "No direct stream link found on page"
    except Exception as e:
        return None, str(e)


# Pyrogram Bot
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
        "⚡ **Welcome to Diskwala Downloader Bot.**\n"
        "Diskwala link pampi direct video stream & download buttons teeskondi!"
    )


@bot.on_message(filters.text & filters.private)
async def handle_msg(client, message):
    text = message.text.strip()
    if text.startswith("/") or "http" not in text:
        return

    status = await message.reply_text("🔎 **Fetching direct link...**")
    stream_url, err = await extract_url(text)

    if stream_url:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎬 Watch / Stream Online", url=stream_url
                    )
                ],
                [InlineKeyboardButton("📥 Fast Direct Download", url=stream_url)],
            ]
        )
        await status.edit_text(
            "⚡ **Direct Link Extracted Successfully!**\n\nChoose an option below:",
            reply_markup=buttons,
        )
    else:
        await status.edit_text(f"❌ **Extraction Failed!**\nDetails: `{err}`")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    print("🚀 Diskwala Bot is Starting...")
    bot.run()
