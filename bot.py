import os
import logging
from threading import Thread

from flask import Flask
from google import genai

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


# ============================================================
# GEMINI AI
# ============================================================

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


# ============================================================
# RENDER WEB SERVER
# ============================================================

server = Flask(__name__)


@server.route("/")
def home():
    return "Vartman Pravah AI Bot is running successfully!"


@server.route("/health")
def health():
    return "OK"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    server.run(
        host="0.0.0.0",
        port=port
    )


# ============================================================
# START COMMAND
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "નમસ્તે 🙏\n\n"
        "વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે. 🤖\n\n"
        "તમે ગુજરાતીમાં કોઈપણ પ્રશ્ન પૂછી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "• ગુજરાતના આજના સમાચાર\n"
        "• આજના 5 મહત્વના સમાચાર\n"
        "• સામાન્ય જ્ઞાનનો પ્રશ્ન\n"
        "• બંધારણ વિશે માહિતી\n"
        "• Current Affairs\n"
        "• પરીક્ષા માટે MCQ\n\n"
        "તમારો પ્રશ્ન મોકલો 👇"
    )

    await update.message.reply_text(message)


# ============================================================
# HELP COMMAND
# ============================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "🤖 Vartman Pravah AI Bot\n\n"
        "આ Botમાં તમે ગુજરાતીમાં પ્રશ્નો પૂછી શકો છો.\n\n"
        "Commands:\n"
        "/start - Bot શરૂ કરો\n"
        "/help - મદદ\n\n"
        "સામાન્ય રીતે પ્રશ્ન લખીને મોકલો."
    )

    await update.message.reply_text(message)


# ============================================================
# GEMINI RESPONSE
# ============================================================

async def ask_gemini(question: str):

    system_instruction = """
તમે 'વર્તમાન પ્રવાહ' નામના ગુજરાતી Current Affairs અને General Knowledge
Telegram Bot માટે AI સહાયક છો.

હંમેશા સરળ અને સ્પષ્ટ ગુજરાતીમાં જવાબ આપો.

જો પ્રશ્ન Current Affairs અથવા સમાચાર અંગે હોય તો:
- જવાબમાં તારીખ સ્પષ્ટ લખો.
- માહિતી ઉપલબ્ધ ન હોય તો ખોટી માહિતી બનાવશો નહીં.
- ખાતરી ન હોય ત્યારે સ્પષ્ટ કહો કે માહિતી ચકાસવી જરૂરી છે.

જો user પરીક્ષા માટે પ્રશ્ન પૂછે તો:
- ગુજરાતી માધ્યમના વિદ્યાર્થીઓને અનુકૂળ જવાબ આપો.
- જરૂરી હોય ત્યારે MCQ format આપો.
- જવાબ અને ટૂંકી સમજૂતી આપો.

જો user Englishમાં પ્રશ્ન પૂછે તો પણ શક્ય હોય ત્યાં સુધી
ગુજરાતીમાં જવાબ આપો.

જવાબ ટૂંકો, ઉપયોગી અને Telegram માટે યોગ્ય રાખો.
"""

    prompt = f"""
{system_instruction}

User Question:
{question}
"""

    response = gemini_client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    if response.text:
        return response.text

    return "માફ કરશો, હાલમાં જવાબ મળી શક્યો નથી."


# ============================================================
# MESSAGE HANDLER
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    question = update.message.text.strip()

    if not question:
        return

    try:

        # Typing indicator
        await update.message.chat.send_action("typing")

        answer = await __import__("asyncio").to_thread(
            ask_gemini,
            question
        )

        # Telegram message limit protection
        max_length = 4000

        if len(answer) <= max_length:

            await update.message.reply_text(answer)

        else:

            for i in range(0, len(answer), max_length):

                part = answer[i:i + max_length]

                await update.message.reply_text(part)

    except Exception as e:

        logger.exception("Gemini error: %s", e)

        error_message = (
            "❌ હાલમાં AI જવાબ આપવામાં સમસ્યા આવી છે.\n\n"
            "થોડા સમય પછી ફરી પ્રયાસ કરો."
        )

        await update.message.reply_text(error_message)


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Telegram error:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # Render web server
    Thread(
        target=run_web,
        daemon=True
    ).start()

    logger.info("Starting Vartman Pravah AI Bot...")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    # Normal text messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot started successfully!")

    # Start Telegram polling
    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
