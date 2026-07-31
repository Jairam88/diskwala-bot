import asyncio
import json
import os
import re
from aiohttp import ClientSession, ClientTimeout, web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# =========================================================
# MEE TELEGRAM DETAILS (REPLACE WITH YOUR REAL CREDENTIALS):
# =========================================================
API_ID = 30918158  # Quotes LEKUNDA mee Numeric API ID ivvali
API_HASH = "795178cb0ef1cc68690b1bbe82960214"  # Quotes LONA mee API Hash string
BOT_TOKEN = "7999558903:AAFmnpddylgWzlofbslPYtviziARBYya-i0"  # Quotes LONA mee BotFather Token
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# Render Web Server Keep-Alive
async def handle_health(request):
    return web.Response(text="Diskwala Bot is Live & Active!")


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
        file_id_match = re.search(
            r"/(?:app|file|e)/([a-zA-Z0-9]+)", diskwala_url
        )
        file_id = file_id_match.group(1) if file_id_match else None

        async with ClientSession(
            headers=HEADERS, timeout=ClientTimeout(total=15)
        ) as session:
            if file_id:
                for api in [
                    f"https://www.diskwala.com/api/file/{file_id}",
                    f"https://www.diskwala.com/api/stream/{file_id}",
                ]:
                    try:
                        async with session.get(api) as res:
                            if res.status == 200:
                                json_data = await res.json()
                                found = find_url_in_json(json_data)
                                if found:
                                    if found.startswith("/"):
                                        found = (
                                            "https://www.diskwala.com" + found
                                        )
                                    return found, None
                    except Exception:
                        pass

            async with session.get(diskwala_url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    match = re.search(
                        r'<script id="__NEXT_DATA__"'
                        r' type="application/json">(.*?)</script>',
                        html,
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

            return None, "Direct link extract avvaledhu."
    except Exception as e:
        return None, str(e)


# Pyrogram Bot Client
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
        "⚡ **Welcome to Diskwala Direct Bot.**\n"
        "Diskwala link pampi, direct Telegram Video File teeskondi!"
    )


@bot.on_message(filters.text & filters.private)
async def handle_msg(client, message):
    text = message.text.strip()
    if text.startswith("/") or "http" not in text:
        return

    status = await message.reply_text("🔎 **Fetching Diskwala Direct Link...**")
    stream_url, err = await extract_url(text)

    if not stream_url:
        await status.edit_text(f"❌ **Extraction Failed!**\nDetails: `{err}`")
        return

    buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎬 Watch / Stream Online", url=stream_url)],
            [InlineKeyboardButton("📥 Fast Direct Download", url=stream_url)],
        ]
    )

    file_path = f"video_{message.id}.mp4"

    try:
        await status.edit_text("📥 **Downloading Video from Diskwala...**")

        async with ClientSession(
            headers=HEADERS, timeout=ClientTimeout(total=300)
        ) as session:
            async with session.get(stream_url) as resp:
                if resp.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(
                            1024 * 1024
                        ):
                            if chunk:
                                f.write(chunk)
                else:
                    await status.edit_text(
                        "⚡ **Direct Link Extracted!**\n\nChoose an option below:",
                        reply_markup=buttons,
                    )
                    return

        await status.edit_text("📤 **Uploading Video to Telegram...**")

        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption="⚡ **Downloaded via Diskwala Bot**",
            reply_markup=buttons,
            supports_streaming=True,
        )

        await status.delete()

    except Exception:
        await status.edit_text(
            "⚡ **Direct Link Extracted Successfully!**\n\nChoose an option below:",
            reply_markup=buttons,
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# Clean Multi-task Execution Method
async def main():
    await start_web_server()
    await bot.start()
    print("🚀 Diskwala Bot Successfully Live!")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
    
