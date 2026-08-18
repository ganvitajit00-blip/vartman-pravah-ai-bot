from threading import Thread
from flask import Flask

import os
import logging
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# SETTINGS
# -----------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -----------------------------
# START COMMAND
# -----------------------------

server = Flask(__name__)

@server.route('/')
def home():
    return "Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "નમસ્તે! 👋\n\n"
        "વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે. 🇮🇳\n\n"
        "તમે મને Current Affairs અથવા કોઈપણ સામાન્ય પ્રશ્ન પૂછો.\n\n"
        "ઉદાહરણ:\n"
        "• આજના Current Affairs આપો\n"
        "• ગુજરાતના આજના સમાચાર આપો\n"
        "• આજે ભારતના મહત્વના સમાચાર કયા છે?\n"
        "• RBIના તાજેતરના સમાચાર આપો\n\n"
        "હું શક્ય હોય ત્યાં તાજી માહિતી શોધીને જવાબ આપીશ. 🔎"
    )

    await update.message.reply_text(message)


# -----------------------------
# HELP COMMAND
# -----------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📚 મદદ\n\n"
        "તમે સીધો પ્રશ્ન મોકલી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "👉 આજના 10 Current Affairs આપો\n"
        "👉 ગુજરાતના આજના મહત્વના સમાચાર આપો\n"
        "👉 UPSC માટે આજના Current Affairs આપો\n"
        "👉 ભારતના આજના રાષ્ટ્રીય સમાચાર આપો\n"
    )

    await update.message.reply_text(message)


# -----------------------------
# AI RESPONSE
# -----------------------------

async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    question = update.message.text.strip()

    if not question:
        return

    # Loading message
    loading = await update.message.reply_text(
        "🔎 માહિતી શોધી રહ્યો છું... થોડી ક્ષણ રાહ જુઓ."
    )

    try:

        instructions = """
તમે 'વર્તમાન પ્રવાહ' નામના ગુજરાતી Current Affairs Telegram Bot છો.

તમારું મુખ્ય કામ:
1. તાજા Current Affairs અને સમાચાર અંગે સચોટ જવાબ આપવો.
2. જરૂરી હોય ત્યારે web search નો ઉપયોગ કરવો.
3. જવાબ મુખ્યત્વે ગુજરાતી ભાષામાં આપવો.
4. પરીક્ષાર્થીઓ માટે સરળ અને ઉપયોગી ભાષા રાખવી.
5. તારીખ, વ્યક્તિ, સ્થળ અને આંકડા અંગે ખાસ કાળજી રાખવી.
6. જો માહિતી તાજી હોય તો વિશ્વસનીય sources પર આધાર રાખવો.
7. જવાબના અંતે 'સ્રોતો' વિભાગ આપવો.
8. ખોટી માહિતી બનાવવી નહીં.
9. જો કોઈ માહિતીની ખાતરી ન હોય તો સ્પષ્ટપણે જણાવવું.

Current Affairs પ્રશ્ન હોય તો શક્ય હોય ત્યાં:
• ઘટના
• તારીખ
• સ્થળ
• સંબંધિત વ્યક્તિ/સંસ્થા
• પરીક્ષા માટે મહત્વ
આપો.

જવાબ ટૂંકો પરંતુ ઉપયોગી રાખો.
"""

        response = await client.responses.create(
            model="gpt-5.5",
            instructions=instructions,
            tools=[
                {
                    "type": "web_search"
                }
            ],
            input=question,
        )

        answer = response.output_text

        if not answer:
            answer = "માફ કરશો, હાલમાં જવાબ મેળવી શકાયો નથી."

        # Telegram message limit protection
        max_length = 4000

        if len(answer) <= max_length:
            await loading.edit_text(answer)
        else:
            await loading.edit_text(answer[:max_length])

            remaining = answer[max_length:]

            while remaining:
                chunk = remaining[:4000]
                remaining = remaining[4000:]
                await update.message.reply_text(chunk)

    except Exception as e:

        logging.exception("Error while processing question")

        await loading.edit_text(
            "❌ હાલમાં જવાબ મેળવવામાં સમસ્યા આવી છે.\n\n"
            "થોડીવાર પછી ફરી પ્રયાસ કરો."
        )


# -----------------------------
# ERROR HANDLER
# -----------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    logging.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# -----------------------------
# MAIN
# -----------------------------

def main():

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            answer_question
        )
    )

    application.add_error_handler(error_handler)

    print("Vartman Pravah AI Bot is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
