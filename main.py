import asyncio
import json
import os
import re
from aiohttp import web
from curl_cffi.requests import AsyncSession
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# =========================================================
# 1. MEE TELEGRAM DETAILS IKKADA DIRECT GA PASTE CHEYYI:
# =========================================================
API_ID = 30918158  # Quotes lekunda numeric ID mathrame ivvali
API_HASH = "795178cb0ef1cc68690b1bbe82960214"  # Quotes lona Hash string paste cheyyi
BOT_TOKEN = "7999558903:AAFmnpddylgWzlofbslPYtviziARBYya-i0"  # Quotes lona BotFather token paste cheyyi
# =========================================================


# Render Port Keeping Web Server
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


# Diskwala Direct Link Extractor Engine
async def extract_url(diskwala_url):
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            resp = await session.get(diskwala_url, timeout=15)
            if resp.status_code != 200:
                return None, f"HTTP Error {resp.status_code}"

            html = resp.text

            # Check Next.js State
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                try:
                    data = json.loads(match.group(1))

                    def find_link(obj):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if any(
                                    x in str(k).lower()
                                    for x in [
                                        "stream",
                                        "download",
                                        "file",
                                        "link",
                                        "url",
                                    ]
                                ):
                                    if (
                                        isinstance(v, str)
                                        and (
                                            v.startswith("http")
                                            or v.startswith("/")
                                        )
                                        and "diskwala.com/app" not in v
                                    ):
                                        return v
                                res = find_link(v)
                                if res:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = find_link(item)
                                if res:
                                    return res
                        return None

                    found = find_link(data)
                    if found:
                        if found.startswith("/"):
                            found = "https://www.diskwala.com" + found
                        return found.replace("\\u0026", "&"), None
                except Exception:
                    pass

            # Raw Regex Fallback
            urls = re.findall(r'https?://[^\s"\'<>]+', html)
            for u in urls:
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
                        return u_clean, None

            return None, "No direct video link found on page"
    except Exception as e:
        return None, str(e)


# Pyrogram Bot Handlers
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
                    
