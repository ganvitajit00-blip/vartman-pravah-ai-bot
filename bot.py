import os
import logging
from threading import Thread

from flask import Flask
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# RENDER WEB SERVER
# =========================================================

server = Flask(__name__)


@server.route("/")
def home():
    return "Vartman Pravah AI Bot is Live!"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")


# =========================================================
# OPENAI CLIENT
# =========================================================

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "નમસ્તે! 👋\n\n"
        "🇮🇳 વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે.\n\n"
        "તમે Current Affairs અથવા સામાન્ય પ્રશ્નો પૂછી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "• આજના Current Affairs આપો\n"
        "• ગુજરાતના આજના સમાચાર આપો\n"
        "• ભારતના આજના મહત્વના સમાચાર આપો\n"
        "• RBIના તાજેતરના સમાચાર આપો\n"
    )

    await update.message.reply_text(message)


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "📚 મદદ\n\n"
        "તમે સીધો પ્રશ્ન મોકલી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "👉 આજના 10 Current Affairs આપો\n"
        "👉 ગુજરાતના આજના મહત્વના સમાચાર આપો\n"
        "👉 UPSC માટે Current Affairs આપો\n"
        "👉 ભારતના રાષ્ટ્રીય સમાચાર આપો\n"
    )

    await update.message.reply_text(message)


# =========================================================
# AI ANSWER
# =========================================================

async def answer_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    question = update.message.text.strip()

    if not question:
        return

    loading = await update.message.reply_text(
        "🔎 જવાબ તૈયાર કરી રહ્યો છું... થોડી ક્ષણ રાહ જુઓ."
    )

    try:

        system_prompt = """
તમે 'વર્તમાન પ્રવાહ' નામના ગુજરાતી AI Bot છો.

તમારું કામ:
1. ગુજરાતી ભાષામાં જવાબ આપવો.
2. જવાબ સરળ અને સ્પષ્ટ રાખવો.
3. પરીક્ષાર્થીઓ માટે ઉપયોગી માહિતી આપવી.
4. Current Affairs પૂછવામાં આવે ત્યારે મુદ્દાસર જવાબ આપવો.
5. માહિતી વિશે ખાતરી ન હોય તો ખોટી માહિતી બનાવવી નહીં.
6. જરૂરી હોય ત્યારે તારીખ અને વર્ષ સ્પષ્ટ લખવું.
"""

        response = await client.responses.create(
            model="gpt-5.6-luna",
            instructions=system_prompt,
            input=question,
        )

        answer = response.output_text

        if not answer:
            answer = (
                "માફ કરશો, હાલમાં જવાબ મેળવી શકાયો નથી."
            )

        # Telegram message limit
        max_length = 4000

        if len(answer) <= max_length:

            await loading.edit_text(answer)

        else:

            await loading.edit_text(
                answer[:max_length]
            )

            remaining = answer[max_length:]

            while remaining:

                chunk = remaining[:4000]
                remaining = remaining[4000:]

                await update.message.reply_text(
                    chunk
                )

    except Exception as e:

        logger.exception(
            "OpenAI API Error"
        )

        # User-friendly message
        await loading.edit_text(
            "❌ હાલમાં AI જવાબ આપવામાં સમસ્યા આવી છે.\n\n"
            "થોડીવાર પછી ફરી પ્રયાસ કરો."
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram error:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # Start Render web server
    Thread(
        target=run_web,
        daemon=True
    ).start()

    # Telegram application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # Normal messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            answer_question
        )
    )

    # Error handler
    application.add_error_handler(
        error_handler
    )

    print(
        "🇮🇳 Vartman Pravah AI Bot is running..."
    )

    # Start Telegram bot
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
