import json
import logging
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from typing import Dict, Any

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Firebase
cred = credentials.Certificate('telegram-1-d817e-firebase-adminsdk-fbsvc-81a9eb1ae8.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://telegram-1-d817e-default-rtdb.firebaseio.com'
})

# Update load_data function to fetch from Firebase root
def load_data() -> Dict[str, Any]:
    try:
        # Get reference to root since data is at root level
        ref = db.reference('/')
        # Get all data
        data = ref.get()
        if data is None:
            logger.error("No data found in Firebase database")
            return {}
        return data
    except Exception as e:
        logger.error(f"Error loading Firebase data: {e}")
        return {}


########################################################
# Replace with your channel IDs and invite links
CHANNEL_ID_1 = '-1002286799839'
CHANNEL_ID_2 = '-1002362999159'
CHANNEL_INVITE_LINK_1 = 'https://t.me/+Q7W_zkJh7T44YmQ1'
CHANNEL_INVITE_LINK_2 = 'https://t.me/+AfsQ9_u-iZNjNjZl'
#######################################################
# Replace with your bot's token
BOT_TOKEN = '7605122418:AAHxDl6qd9uxEvmUk2mJyEhH9sXYXJyOHak'

# Remove these global data loads
# data_telugu = load_data('telugu_movies_database.json')
# data_hindi = load_data('hindi_movies_database.json')
########################################################

# Add this constant at the top with other constants
welcome_image_url = 'https://wallpapercave.com/wp/wp6622443.jpg'
###############################################################
# Add this constant near other constants at the top
DEFAULT_DESCRIPTION = "*🚀🔥 Exclusive Download Alert! 🔥🚀\n       Click below to grab your file \n      📥📥📥📥📥📥📥📥📥📥📥 *"

def to_math_bold(text: str) -> str:
    bold_map = {chr(i): chr(i + 0x1D400 - 0x41) for i in range(0x41, 0x5A + 1)}
    bold_map.update({chr(i): chr(i + 0x1D41A - 0x61) for i in range(0x61, 0x7A + 1)})
    return ''.join(bold_map.get(c, c) for c in text)

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Reset content delivery status for new deep link
    if context.args:
        deep_link = context.args[0]
        # Store deep link and reset content_sent flag
        context.user_data['deep_link'] = deep_link
        context.user_data['content_sent'] = False
        logger.info(f"New deep link request from user {user_id}: {deep_link}")

        # Check channel membership
        member_status_1, member_status_2 = await verify_membership(context, user_id)

        if member_status_1 and member_status_2:
            # User is already a member of both channels, process deep link
            await process_deep_link(update, context)
        else:
            # User is not a member of both channels, show join message
            await show_join_channels_message(update)
    else:
        # No deep link provided, send welcome message
        await send_welcome_message(update, context)

async def process_deep_link(update: Update, context: CallbackContext) -> None:
    """Process deep link parameter and send content"""
    deep_link = context.user_data.get('deep_link')
    already_sent = context.user_data.get('content_sent', False)

    if deep_link and not already_sent:
        # Load fresh data from Firebase
        content_data = load_data()
        if not content_data:
            await update.message.reply_text(
                "Sorry, the content database is currently unavailable. Please try again later."
            )
            return
            
        link_info = content_data.get(deep_link)
        if link_info:
            await send_content(update, link_info)
            context.user_data['content_sent'] = True
            logger.info(f"Content sent for deep link: {deep_link}")
        else:
            logger.error(f"Invalid deep link parameter: {deep_link}")
            await update.message.reply_text("Sorry, the requested content is unavailable as it has been removed due to copyright restrictions.")
    elif deep_link and already_sent:
        await update.message.reply_text(
            "You've already received this content.\n"
            "Please use a different deep link to get new content."
        )
    else:
        await send_welcome_message(update)

async def show_join_channels_message(update: Update) -> None:
    """Show message asking user to join channels"""
    welcome_message = (
        "🎉 *Welcome!* 🎉\n\n"
        "To access the content:\n"
        "1️⃣ Join both channels below\n"
        "2️⃣ Click 'Try Again'\n\n"
        "Your content will be sent automatically after verification! 🚀"
    )
    keyboard = [
        [InlineKeyboardButton("Channel 1", url=CHANNEL_INVITE_LINK_1), 
         InlineKeyboardButton("Channel 2", url=CHANNEL_INVITE_LINK_2)],
        [InlineKeyboardButton("Try Again", callback_data='verify')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_photo(
        photo=welcome_image_url,
        caption=welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def verify(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    try:
        member_status_1, member_status_2 = await verify_membership(context, user_id)

        if member_status_1 and member_status_2:
            deep_link = context.user_data.get('deep_link')
            already_sent = context.user_data.get('content_sent', False)
            
            if deep_link and not already_sent:
                # Load fresh data from Firebase
                movies_data = load_data()
                if not movies_data:
                    await query.edit_message_text(
                        "Sorry, the content database is currently unavailable. Please try again later."
                    )
                    return
                    
                link_info = movies_data.get(deep_link)
                
                if link_info:
                    # Show verification success message
                    await query.answer('✅ Verification successful!')
                    
                    try:
                        # Send content
                        if "image" in link_info:
                            await query.message.reply_photo(
                                photo=link_info["image"],
                                caption=format_content_message(link_info),
                                parse_mode="Markdown"
                            )
                        else:
                            await query.message.reply_text(
                                text=format_content_message(link_info),
                                parse_mode="Markdown"
                            )
                        
                        # Mark content as sent
                        context.user_data['content_sent'] = True
                        
                        # Update original message
                        await query.edit_message_text(
                            "✅ Content has been sent above ⬆️\n\n"
                            "To get new content, please use a new deep link."
                        )
                        
                    except Exception as e:
                        logger.error(f"Error sending content: {e}")
                        await query.edit_message_text(
                            "❌ Error sending content. Please try using the deep link again."
                        )
                else:
                    await query.edit_message_text(
                        "Sorry, the requested content is not available."
                    )
            elif already_sent:
                await query.answer('Content already sent!')
                await query.edit_message_text(
                    "✅ You already received the content.\n\n"
                    "To get new content, please use a new deep link."
                )
            else:
                await query.answer('✅ Verification successful!')
                await query.edit_message_text(
                    "✅ You are a member of both channels!\n\n"
                    "Use a deep link to access specific content."
                )
        else:
            keyboard = [
                [InlineKeyboardButton("Channel 1", url=CHANNEL_INVITE_LINK_1), 
                 InlineKeyboardButton("Channel 2", url=CHANNEL_INVITE_LINK_2)],
                [InlineKeyboardButton("Try Again", callback_data='verify')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.answer('❌ Please join both channels first!')
            await query.edit_message_text(
                text="Verification failed. Please join both channels and try again.",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in verification: {e}")
        await query.answer('An error occurred. Please try again.')

# Update format_content_message function
def format_content_message(link_info: Dict[str, Any]) -> str:
    """Format the content message with default description and URL"""
    message_parts = [f'{DEFAULT_DESCRIPTION}']
    message_parts.append(f'\n\n[{link_info["url"]}]({link_info["url"]})')
    return ''.join(message_parts)

# Update send_content function
async def send_content(update, link_info, is_callback=False):
    message = format_content_message(link_info)
    
    if "image" in link_info:
        try:
            if is_callback:
                await update.message.reply_photo(
                    photo=link_info["image"],
                    caption=message,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_photo(
                    photo=link_info["image"],
                    caption=message,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            if is_callback:
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")
    else:
        if is_callback:
            await update.message.reply_text(message, parse_mode="Markdown")
        else:
            await update.message.reply_text(message, parse_mode="Markdown")

async def verify_membership(context: CallbackContext, user_id: int) -> tuple[bool, bool]:
    try:
        member_status_1 = (await context.bot.get_chat_member(CHANNEL_ID_1, user_id)).status in ['member', 'administrator', 'creator']
        member_status_2 = (await context.bot.get_chat_member(CHANNEL_ID_2, user_id)).status in ['member', 'administrator', 'creator']
        return member_status_1, member_status_2
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False, False

async def send_welcome_message(update: Update, context: CallbackContext) -> None:
    """Send the welcome message with photo after verifying channel membership."""
    user_id = update.message.from_user.id
    member_status_1, member_status_2 = await verify_membership(context, user_id)

    if member_status_1 and member_status_2:
        # Send welcome message only if user is member of both channels
        await update.message.reply_photo(
            photo=welcome_image_url,
            caption=(
                "👋 *Hello there!*\n"
                "🤖 I'm your friendly file-sharing bot, and here's what I can do for you:\n\n"
                "✨ *Quick and Easy File Sharing* – Share files in just a few taps.\n"
                "📂 *Multiple File Formats* – Support for documents, images, videos, and more.\n"
                "🔒 *Secure Transfers* – Your files are safe with me.\n"
                "⚡ *Fast Uploads* – No more waiting around!\n"
                "🎯 *User-Friendly* – Simple commands to make your experience seamless.\n\n"
                "Ready to share? Let's get started! 🚀"
            ),
            parse_mode="Markdown"
        )
    else:
        # Show join channels message if user is not member of both channels
        welcome_message = (
            "🎉 *Welcome!* 🎉\n\n"
            "To access the bot:\n"
            "1️⃣ Join both channels below\n"
            "2️⃣ Click 'Try Again'\n\n"
            "You'll get full access after verification! 🚀"
        )
        keyboard = [
            [InlineKeyboardButton("Channel 1", url=CHANNEL_INVITE_LINK_1), 
             InlineKeyboardButton("Channel 2", url=CHANNEL_INVITE_LINK_2)],
            [InlineKeyboardButton("Try Again", callback_data='verify')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            photo=welcome_image_url,
            caption=welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify, pattern='^verify$'))

    application.run_polling()

if __name__ == '__main__':
    main()


    application.run_polling()

if __name__ == '__main__':
    main()
