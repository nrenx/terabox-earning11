from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
import pyperclip

# Define your bot names here
BOT_NAMES = ["ntr_neel_bot", "Bot2", "Bot3","Bot4"]

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send any text to get started.')

async def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text.replace(' ', '_')
    keyboard = [[InlineKeyboardButton(bot, callback_data=f"{bot}:{text}")] for bot in BOT_NAMES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose one bot:', reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    bot_name, user_text = query.data.split(':')
    deeplink = f"https://t.me/{bot_name}?start={user_text}"
    await query.edit_message_text(text=f"Here is your deeplink:\n\n\n`{deeplink}`", parse_mode='Markdown')
    pyperclip.copy(deeplink)
    print(f"Deeplink copied to clipboard: {deeplink}")

def main() -> None:
    # Replace 'YOUR_TOKEN' with your actual bot token
    application = Application.builder().token("7723831298:AAGwwzXKXAUck4926j0thiwuePUkv5kB0V0").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
