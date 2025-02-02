import json
import firebase_admin
from firebase_admin import credentials, db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters
from datetime import datetime
import random
import string

# Initialize Firebase
cred = credentials.Certificate("telegram-1-d817e-firebase-adminsdk-fbsvc-81a9eb1ae8.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://telegram-1-d817e-default-rtdb.firebaseio.com'
})
root_ref = db.reference('/')

TITLE, NAME, URL, CONFIRM_DELETE, SHOW_NEXT = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Show Data", callback_data='show_data_0')],
        [InlineKeyboardButton("Add New Data", callback_data='add_data')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text('Choose an option:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text('Choose an option:', reply_markup=reply_markup)

def load_json():
    try:
        data = root_ref.get()
        print(f"Loaded data: {data}")  # Debugging statement
        return data if data else {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def save_json(data):
    try:
        print(f"Saving data: {data}")  # Debugging statement
        root_ref.set(data)
    except Exception as e:
        print(f"Error saving data: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('show_data'):
        data = load_json()
        keyboard = []
        # Sort titles by timestamp in descending order
        sorted_titles = sorted(data.keys(), key=lambda x: data[x].get('timestamp', ''), reverse=True)
        start_index = int(query.data.split('_')[-1])
        end_index = start_index + 10
        for title in sorted_titles[start_index:end_index]:
            keyboard.append([
                InlineKeyboardButton(title, callback_data=f'view_title_{title}'),
                InlineKeyboardButton("❌", callback_data=f'confirm_delete_{title}')
            ])
        navigation_buttons = []
        if start_index > 0:
            navigation_buttons.append(InlineKeyboardButton("Previous 10 Titles", callback_data=f'show_data_{start_index - 10}'))
        if end_index < len(sorted_titles):
            navigation_buttons.append(InlineKeyboardButton("Next 10 Titles", callback_data=f'show_data_{end_index}'))
        if navigation_buttons:
            keyboard.append(navigation_buttons)
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data='start')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📚 new title shows first dont go down: Available Titles:", reply_markup=reply_markup)
        return ConversationHandler.END
    
    elif query.data == 'start':
        await start(update, context)
        return ConversationHandler.END

    elif query.data.startswith('confirm_delete_'):
        title = query.data.replace('confirm_delete_', '')
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f'delete_{title}'),
                InlineKeyboardButton("❌ No, Cancel", callback_data='show_data_0')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"⚠️ Are you sure you want to delete '{title}'?", reply_markup=reply_markup)
        return CONFIRM_DELETE

    elif query.data.startswith('delete_'):
        title = query.data.replace('delete_', '')
        data = load_json()
        if title in data:
            del data[title]
            save_json(data)
            keyboard = [
                [InlineKeyboardButton("🔙 Main Menu", callback_data='start')],
                [InlineKeyboardButton("Show Data", callback_data='show_data_0')],
                [InlineKeyboardButton("Add New Data", callback_data='add_data')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(f"✅ Deleted '{title}' successfully!", reply_markup=reply_markup)
            return ConversationHandler.END
    
    elif query.data.startswith('view_title_'):
        title = query.data.replace('view_title_', '')
        data = load_json()
        if title in data:
            entry = data[title]
            message = f"📌 Title: {title}\n\n📝 Name: {entry['name']}\n\n🔗 URL: {entry['url']}"
            keyboard = [[InlineKeyboardButton("Back to Titles", callback_data='show_data_0')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(message, reply_markup=reply_markup)
        return ConversationHandler.END
    
    elif query.data == 'add_data':
        keyboard = [
            [InlineKeyboardButton("Generate Random Name", callback_data='generate_random_name')],
            [InlineKeyboardButton("Enter Name", callback_data='enter_name')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Do you want to generate a random name or enter a name?", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == 'generate_random_name':
        random_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        context.user_data['name'] = random_name
        context.user_data['title'] = generate_unique_title(load_json())
        await query.message.edit_text(f"Generated name: {random_name}\n\nEnter the URL to save:")
        return URL

    elif query.data == 'enter_name':
        await query.message.edit_text("Enter the name:")
        return NAME

    elif query.data == 'add_more_url':
        await query.message.edit_text("Enter another URL:")
        return URL

    elif query.data.startswith('remove_url_'):
        index = int(query.data.split('_')[-1])
        context.user_data['urls'].pop(index)
        await preview_urls(update, context)
        return URL
        
    elif query.data == 'save_urls':
        data = load_json()
        title = context.user_data['title']
        combined_urls = '\n'.join(context.user_data['urls'])
        data[title] = {
            'name': context.user_data['name'],
            'url': combined_urls,
            'timestamp': datetime.now().isoformat()  # Add timestamp
        }
        save_json(data)
        context.user_data.pop('urls', None)
        keyboard = [
            [InlineKeyboardButton("🔙 Main Menu", callback_data='start')],
            [InlineKeyboardButton("Show Data", callback_data='show_data_0')],
            [InlineKeyboardButton("Add New Data", callback_data='add_data')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"Here is your title:\n\n`{title}`", parse_mode='Markdown', reply_markup=reply_markup)
        return ConversationHandler.END

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    context.user_data['title'] = generate_unique_title(load_json())
    await update.message.reply_text("Enter the URL to save:")
    return URL

def generate_unique_title(data):
    while True:
        random_title = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if random_title not in data:
            return random_title

async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if 'urls' not in context.user_data:
        context.user_data['urls'] = []
    context.user_data['urls'].append(url)
    await preview_urls(update, context)
    return URL

async def preview_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urls = context.user_data['urls']
    message = "Current URLs:\n\n" + "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
    keyboard = [
        [InlineKeyboardButton(f"Remove URL {i+1}", callback_data=f'remove_url_{i}') for i in range(len(urls))],
        [InlineKeyboardButton("Add Another URL", callback_data='add_more_url')],
        [InlineKeyboardButton("Save URLs", callback_data='save_urls')],
        [InlineKeyboardButton("🔙 Main Menu", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
    return ConversationHandler.END

def main():
    application = Application.builder().token('7059970653:AAEKBkNUXaHGfyDNbMjWPc2T2s70_5jZToQ').build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(button_callback, pattern='^(start|show_data_.*|view_title_.*|confirm_delete_.*|delete_.*|add_data|generate_random_name|enter_name|add_more_url|remove_url_.*|save_urls|cancel)$')
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_url),
                CallbackQueryHandler(button_callback, pattern='^(add_more_url|remove_url_.*|save_urls)$')
            ],
            CONFIRM_DELETE: [CallbackQueryHandler(button_callback, pattern='^(delete_.*|show_data_0)$')]
        },
        fallbacks=[CallbackQueryHandler(button_callback, pattern='^cancel$')],
        per_message=False,
        name="my_conversation"
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
