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
    server.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# SETTINGS
# =========================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")


if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")


# OpenAI client
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "નમસ્તે! 👋\n\n"
        "🇮🇳 વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે.\n\n"
        "તમે મને Current Affairs, General Knowledge "
        "અથવા કોઈપણ સામાન્ય પ્રશ્ન પૂછી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "• આજના Current Affairs આપો\n"
        "• ગુજરાતના આજના સમાચાર આપો\n"
        "• ભારતના આજના મહત્વના સમાચાર આપો\n"
        "• RBIના તાજેતરના સમાચાર આપો\n"
        "• UPSC માટે Current Affairs આપો\n\n"
        "તમારો પ્રશ્ન મોકલો. 🔎"
    )

    await update.message.reply_text(message)


# =========================================================
# HELP
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
        "👉 ભારતના રાષ્ટ્રીય સમાચાર આપો\n"
        "👉 UPSC માટે Current Affairs આપો\n"
    )

    await update.message.reply_text(message)


# =========================================================
# AI RESPONSE
# =========================================================

async def answer_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    question = update.message.text.strip()

    if not question:
        return

    # Loading message
    loading = await update.message.reply_text(
        "🔎 AI જવાબ તૈયાર કરી રહ્યો છું...\n"
        "થોડી ક્ષણ રાહ જુઓ."
    )

    try:

        system_prompt = """
તમે 'વર્તમાન પ્રવાહ AI' નામના ગુજરાતી
Current Affairs અને General Knowledge Bot છો.

તમારું કામ:
1. ગુજરાતીમાં જવાબ આપવો.
2. જવાબ સરળ અને સ્પષ્ટ રાખવો.
3. પરીક્ષાર્થીઓ માટે ઉપયોગી માહિતી આપવી.
4. પ્રશ્ન Current Affairsનો હોય તો શક્ય તેટલી
   સચોટ અને સ્પષ્ટ માહિતી આપવી.
5. જરૂરી હોય ત્યારે મુદ્દાવાર જવાબ આપવો.
6. માહિતી ખાતરીપૂર્વક ઉપલબ્ધ ન હોય તો ખોટી માહિતી
   બનાવવી નહીં.
"""

        logger.info(
            "Sending question to OpenAI: %s",
            question
        )

        # -------------------------------------------------
        # OPENAI REQUEST
        # -------------------------------------------------

        response = await client.chat.completions.create(

            model="gpt-4o-mini",

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": question
                }
            ],

            temperature=0.3,

            max_tokens=1500
        )

        # -------------------------------------------------
        # GET ANSWER
        # -------------------------------------------------

        answer = response.choices[0].message.content

        logger.info("OpenAI response received successfully.")

        if not answer:

            answer = (
                "માફ કરશો, હાલમાં AI તરફથી "
                "જવાબ મળ્યો નથી."
            )

        answer = answer.strip()

        # Telegram message limit handling
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

        # -------------------------------------------------
        # IMPORTANT:
        # ACTUAL ERROR WILL BE SHOWN IN TELEGRAM
        # -------------------------------------------------

        logger.exception(
            "OPENAI ERROR: %s",
            str(e)
        )

        error_text = str(e)

        if len(error_text) > 1500:
            error_text = error_text[:1500]

        await loading.edit_text(
            "❌ AI જવાબ આપવામાં સમસ્યા આવી.\n\n"
            "🔧 Error:\n"
            + error_text
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Telegram bot error:",
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

    logger.info(
        "Starting Vartman Pravah AI Bot..."
    )

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

    # Normal text messages
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

    logger.info(
        "Vartman Pravah AI Bot is running..."
    )

    # Start Telegram polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
