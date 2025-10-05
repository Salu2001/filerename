import os
import logging
import tempfile
import uuid
from datetime import datetime
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app for Vercel
app = Flask(__name__)

# Get bot token from environment variable (for security)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# Store user preferences (in production, use a database)
user_preferences = {}

class FileRenamerBot:
    def __init__(self):
        self.supported_formats = {
            'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
            'video': ['.mp4', '.avi', '.mov', '.mkv'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
    
    def get_file_category(self, file_extension):
        for category, extensions in self.supported_formats.items():
            if file_extension.lower() in extensions:
                return category
        return 'other'
    
    def generate_new_filename(self, original_name, user_id, prefix=None, suffix=None):
        name, ext = os.path.splitext(original_name)
        
        # Get user preferences
        user_pref = user_preferences.get(user_id, {})
        
        # Apply custom prefix/suffix or use defaults
        custom_prefix = prefix or user_pref.get('prefix', 'renamed_')
        custom_suffix = suffix or user_pref.get('suffix', '')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        new_name = f"{custom_prefix}{name}{custom_suffix}_{timestamp}{ext}"
        return new_name

renamer = FileRenamerBot()

# Start command with inline keyboard
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🤖 *Welcome to Advanced File Renamer Bot* 🚀

*Features:*
• Rename any file with custom prefixes/suffixes
• Support for multiple file types
• Batch renaming options
• Custom naming patterns
• File format validation

*Available Commands:*
/start - Show this welcome message
/help - Get help and instructions
/settings - Configure renaming preferences
/formats - Show supported file formats
/rename - Manual renaming with custom name

Send me a file to get started!
    """
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("📁 Send File", callback_data="send_file"),
        InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    keyboard.add(
        InlineKeyboardButton("📋 Formats", callback_data="formats"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    )
    
    bot.send_message(message.chat.id, welcome_text, 
                    parse_mode='Markdown', reply_markup=keyboard)

# Help command
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
*How to use this bot:*

1. *Quick Rename*: Simply send any file and it will be renamed with a prefix
2. *Custom Rename*: Use /rename command followed by your custom name, then send the file
3. *Settings*: Use /settings to configure default prefixes/suffixes

*Supported File Types:*
• Documents: PDF, DOC, DOCX, TXT, etc.
• Images: JPG, PNG, GIF, etc.
• Audio: MP3, WAV, OGG, etc.
• Video: MP4, AVI, MOV, etc.
• Archives: ZIP, RAR, 7Z, etc.

*Example for custom rename:*
/rename my_custom_file
Then send your file
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Settings command
@bot.message_handler(commands=['settings'])
def show_settings(message):
    user_id = message.from_user.id
    user_pref = user_preferences.get(user_id, {})
    
    settings_text = f"""
*Current Settings:*

Default Prefix: `{user_pref.get('prefix', 'renamed_')}`
Default Suffix: `{user_pref.get('suffix', '')}`

*To change settings:*
/setprefix your_prefix
/setsuffix your_suffix

*To reset settings:*
/resetsettings
    """
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔄 Set Prefix", callback_data="set_prefix"),
        InlineKeyboardButton("🔧 Set Suffix", callback_data="set_suffix")
    )
    keyboard.add(
        InlineKeyboardButton("🗑️ Reset Settings", callback_data="reset_settings")
    )
    
    bot.send_message(message.chat.id, settings_text, 
                    parse_mode='Markdown', reply_markup=keyboard)

# Set prefix command
@bot.message_handler(commands=['setprefix'])
def set_prefix(message):
    try:
        prefix = message.text.split(' ', 1)[1].strip()
        user_id = message.from_user.id
        
        if user_id not in user_preferences:
            user_preferences[user_id] = {}
        
        user_preferences[user_id]['prefix'] = prefix
        bot.reply_to(message, f"✅ Prefix set to: `{prefix}`", parse_mode='Markdown')
    
    except IndexError:
        bot.reply_to(message, "❌ Please provide a prefix. Example: `/setprefix myprefix_`", 
                    parse_mode='Markdown')

# Set suffix command
@bot.message_handler(commands=['setsuffix'])
def set_suffix(message):
    try:
        suffix = message.text.split(' ', 1)[1].strip()
        user_id = message.from_user.id
        
        if user_id not in user_preferences:
            user_preferences[user_id] = {}
        
        user_preferences[user_id]['suffix'] = suffix
        bot.reply_to(message, f"✅ Suffix set to: `{suffix}`", parse_mode='Markdown')
    
    except IndexError:
        bot.reply_to(message, "❌ Please provide a suffix. Example: `/setsuffix _mysuffix`", 
                    parse_mode='Markdown')

# Reset settings command
@bot.message_handler(commands=['resetsettings'])
def reset_settings(message):
    user_id = message.from_user.id
    if user_id in user_preferences:
        del user_preferences[user_id]
    bot.reply_to(message, "✅ Settings reset to defaults")

# Formats command
@bot.message_handler(commands=['formats'])
def show_formats(message):
    formats_text = "*Supported File Formats:*\n\n"
    
    for category, extensions in renamer.supported_formats.items():
        formats_text += f"*{category.title()}:*\n"
        formats_text += ", ".join(extensions) + "\n\n"
    
    bot.send_message(message.chat.id, formats_text, parse_mode='Markdown')

# Rename command for custom naming
rename_requests = {}

@bot.message_handler(commands=['rename'])
def request_custom_name(message):
    try:
        custom_name = message.text.split(' ', 1)[1].strip()
        user_id = message.from_user.id
        rename_requests[user_id] = custom_name
        bot.reply_to(message, f"✅ Custom name set to: `{custom_name}`\n\nNow send me the file you want to rename.", 
                    parse_mode='Markdown')
    
    except IndexError:
        bot.reply_to(message, "❌ Please provide a custom name. Example: `/rename my_custom_file`", 
                    parse_mode='Markdown')

# Main file handler
@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        user_id = message.from_user.id
        file_name = message.document.file_name
        file_id = message.document.file_id
        file_size = message.document.file_size
        
        # Check file size (limit to 20MB for Vercel)
        if file_size > 20 * 1024 * 1024:
            bot.reply_to(message, "❌ File size too large. Maximum size is 20MB.")
            return
        
        file_extension = os.path.splitext(file_name)[1]
        file_category = renamer.get_file_category(file_extension)
        
        if file_category == 'other':
            bot.reply_to(message, "⚠️ This file format might not be supported. Trying to process anyway...")
        
        # Show processing message
        processing_msg = bot.reply_to(message, "⏳ Processing your file...")
        
        # Download the file
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Generate new filename
        if user_id in rename_requests:
            custom_name = rename_requests[user_id]
            new_file_name = f"{custom_name}{file_extension}"
            del rename_requests[user_id]  # Clean up
        else:
            new_file_name = renamer.generate_new_filename(file_name, user_id)
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(downloaded_file)
            temp_path = temp_file.name
        
        # Send the renamed file
        with open(temp_path, 'rb') as file_to_send:
            bot.send_document(
                message.chat.id,
                file_to_send,
                caption=f"✅ File renamed successfully!\nOriginal: `{file_name}`\nNew: `{new_file_name}`",
                parse_mode='Markdown',
                visible_file_name=new_file_name
            )
        
        # Clean up
        os.unlink(temp_path)
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        logger.info(f"File processed: {file_name} -> {new_file_name} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        bot.reply_to(message, "❌ An error occurred while processing your file. Please try again.")
        
        # Clean up temporary files on error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)

# Callback query handler for inline buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "send_file":
        bot.answer_callback_query(call.id, "Send me any file to rename it!")
    elif call.data == "settings":
        show_settings(call.message)
    elif call.data == "formats":
        show_formats(call.message)
    elif call.data == "help":
        send_help(call.message)
    elif call.data == "set_prefix":
        bot.answer_callback_query(call.id, "Use /setprefix command to set your prefix")
    elif call.data == "set_suffix":
        bot.answer_callback_query(call.id, "Use /setsuffix command to set your suffix")
    elif call.data == "reset_settings":
        reset_settings(call.message)
        bot.answer_callback_query(call.id, "Settings reset!")

# Error handler
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text and not message.text.startswith('/'):
        bot.reply_to(message, "🤖 Send me a file to rename it, or use /help to see available commands.")

# Webhook route for Vercel
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# Set webhook (call this once when deploying)
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://{request.host}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook set to: {webhook_url}'

# Health check route
@app.route('/')
def index():
    return '🤖 File Renamer Bot is running!'

# For local development
if __name__ == '__main__':
    if os.environ.get('VERCEL') is None:  # Local development
        bot.remove_webhook()
        bot.polling()
else:
    # For Vercel deployment
    app = app