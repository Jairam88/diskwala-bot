import asyncio
import os
from aiohttp import web
from pyrogram import Client, filters
import config
from extractor import extract_direct_url


async def handle_health(request):
    return web.Response(text="Bot is Alive & Running 24/7!")


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
        "👋 **Hi Babai!**\n\n"
        "Diskwala link emaina unte ikkada paste cheyyi. Direct stream link"
        " extract chesi istha!"
    )


@bot.on_message(filters.text & filters.private)
async def handle_diskwala_link(client, message):
    user_text = message.text.strip()

    if "http" not in user_text:
        await message.reply_text("❌ Please valid Diskwala URL pampu mowa!")
        return

    status_msg = await message.reply_text(
        "⏳ **Processing Link...** Diskwala link bypass chesthunna, 5-10 seconds"
        " wait cheyyi..."
    )

    try:
        stream_link, debug_info = await extract_direct_url(user_text)

        if stream_link:
            reply_content = (
                "🎉 **Video Link Extracted!**\n\n"
                f"🔗 **Direct Stream URL:**\n`{stream_link}`\n\n"
                "💡 *Tip: Ee link ni VLC media player lo paste chesi watch"
                " cheyyochu!*"
            )
            await status_msg.edit_text(reply_content)
        else:
            cf_status = (
                "YES 🔴 (Render IP Blocked by Cloudflare)"
                if debug_info.get("cloudflare_blocked")
                else "NO 🟢"
            )
            title = debug_info.get("title", "Unknown")
            status = debug_info.get("status", "N/A")
            err = debug_info.get("error", "None")

            debug_msg = (
                "⚠️ **Video link dorakaledhu babai.**\n\n"
                "🔍 **Diagnostic Info:**\n"
                f"• **Page Title:** `{title}`\n"
                f"• **HTTP Status Code:** `{status}`\n"
                f"• **Cloudflare Blocked?:** `{cf_status}`\n"
                f"• **Error Details:** `{err}`"
            )
            await status_msg.edit_text(debug_msg)

    except Exception as err:
        await status_msg.edit_text(f"❌ Critical Error: {str(err)}")


async def main():
    await start_web_server()
    await bot.start()
    print("Bot started running successfully...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
