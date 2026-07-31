import asyncio
import os
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import config
from extractor import extract_diskwala_data


# Render Health Check Web Server
async def handle_health(request):
    return web.Response(text="Diskwala Pro Bot is Running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


bot = Client(
    "diskwala_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)


@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "⚡ **Welcome to Diskwala Direct Downloader Bot.**\n\n"
        "Diskwala link pampi direct video stream & download links ready teeskondi!"
    )


@bot.on_message(filters.text & filters.private)
async def process_link(client, message):
    text = message.text.strip()

    if text.startswith("/"):
        return

    if "http" not in text:
        await message.reply_text("❌ Please valid Diskwala link pampandi!")
        return

    status_msg = await message.reply_text("🔎 **Fetching Link Details...**")

    try:
        res = await extract_diskwala_data(text)

        if res.get("stream_url"):
            stream_url = res["stream_url"]
            title = res.get("title", "Diskwala Video File")

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎬 Watch / Stream Online", url=stream_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📥 Direct Fast Download", url=stream_url
                        )
                    ],
                ]
            )

            caption_text = (
                f"📂 **File Name:** `{title}`\n"
                "⚡ **Status:** Direct Link Extracted Successfully!\n\n"
                "👇 Choose an option below to play or download:"
            )

            await status_msg.edit_text(caption_text, reply_markup=buttons)
        else:
            err = res.get("error") or "Could not extract stream link."
            await status_msg.edit_text(
                f"❌ **Extraction Failed!**\n\nDetails: `{err}`"
            )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def main():
    await start_web_server()
    await bot.start()
    print("✅ Diskwala Pro Bot Started Successfully!")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
