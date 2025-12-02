import os
import io
import sqlite3
import qrcode
from PIL import Image
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import requests
from urllib.parse import urlparse

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.getenv("8375342510:AAHuzeCpsfXrxXjqmFV_mvIO9x_0taThmiQ")  # ✅ Render environment variable से लेगा
DATABASE_NAME = "utility_bot.db"

# ==================== DATABASE SETUP ====================
def init_database():
    """Initialize database for utility bot"""
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            total_tasks INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Task history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_type TEXT,
            input_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

# ==================== FEATURE 1: SMART QR GENERATOR ====================
class QRGenerator:
    """Advanced QR Code Generator"""
    
    @staticmethod
    def create_qr(data, size=400, color="black", bg_color="white"):
        """Create QR code with custom size and colors"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color=color, back_color=bg_color).convert('RGB')
            qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
            return qr_img
        except Exception as e:
            print(f"QR creation error: {e}")
            return None

# ==================== FEATURE 4: URL SHORTENER ====================
class URLShortener:
    """URL Shortening Service"""
    
    @staticmethod
    def shorten(url, service='tinyurl'):
        """Shorten URL using different services"""
        try:
            if service == 'tinyurl':
                api_url = f"https://tinyurl.com/api-create.php?url={url}"
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    return response.text
        except Exception as e:
            print(f"URL shortening error: {e}")
        
        return url  # Return original if shortening fails
    
    @staticmethod
    def is_valid_url(url):
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with main menu"""
    user = update.effective_user
    
    # Save user to database
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name) 
        VALUES (?, ?, ?)
    ''', (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()
    
    keyboard = [
        [
            InlineKeyboardButton("🎯 Generate QR", callback_data="menu_qr"),
            InlineKeyboardButton("🔗 Shorten URL", callback_data="menu_url")
        ],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="menu_stats"),
            InlineKeyboardButton("🆘 Help", callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✨ **Welcome {user.first_name}!**\n\n"
        "🚀 **UTILITY BOT**\n\n"
        "**Features:**\n"
        "• **SMART QR GENERATOR** - Any text/link to QR\n"
        "• **URL SHORTENER** - Make long links short\n\n"
        "👇 **Choose what you need:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_qr_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle QR menu selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_qr":
        await query.edit_message_text(
            "🎯 **QR CODE GENERATOR**\n\n"
            "Send me any URL or text and I'll create a QR code!\n\n"
            "Examples:\n"
            "• https://google.com\n"
            "• Your contact info\n"
            "• Any message\n\n"
            "Send your text now:",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for'] = 'qr_url'

async def handle_url_shortener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URL shortener"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔗 **URL SHORTENER**\n\n"
        "Send me any long URL and I'll shorten it:\n\n"
        "Example:\n"
        "Input: https://www.example.com/very-long-path-name\n"
        "Output: https://tinyurl.com/abc123\n\n"
        "Send your URL now!",
        parse_mode='Markdown'
    )
    context.user_data['waiting_for'] = 'shorten_url'

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user stats"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # Get user stats
    cursor.execute("SELECT total_tasks, join_date FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM task_history WHERE user_id = ?", (user_id,))
    total_actions = cursor.fetchone()[0]
    
    conn.close()
    
    if user_data:
        total_tasks, join_date = user_data
        await query.edit_message_text(
            f"📊 **YOUR STATISTICS**\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"📈 Total Tasks: {total_tasks}\n"
            f"✅ Actions Performed: {total_actions}\n"
            f"📅 Joined: {join_date}\n\n"
            f"🎯 Keep using the bot!",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ No statistics found. Use /start first!",
            parse_mode='Markdown'
        )

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🆘 **HELP & SUPPORT**\n\n"
        "**Available Commands:**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n\n"
        "**Features:**\n"
        "• QR Code Generator - Create QR from any text/URL\n"
        "• URL Shortener - Shorten long URLs\n\n"
        "**How to use:**\n"
        "1. Click 'Generate QR'\n"
        "2. Send URL/text\n"
        "3. Get QR code!\n\n"
        "**For URL Shortener:**\n"
        "1. Click 'Shorten URL'\n"
        "2. Send long URL\n"
        "3. Get shortened link!",
        parse_mode='Markdown'
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    data = query.data
    
    if data == "menu_qr":
        await handle_qr_menu(update, context)
    elif data == "menu_url":
        await handle_url_shortener(update, context)
    elif data == "menu_stats":
        await handle_stats(update, context)
    elif data == "menu_help":
        await handle_help(update, context)
    else:
        await query.answer("Coming soon!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all incoming messages"""
    user_id = update.effective_user.id
    message_text = update.message.text if update.message.text else ""
    
    # Check what user wants to do
    if 'waiting_for' in context.user_data:
        task_type = context.user_data['waiting_for']
        
        if task_type == 'qr_url':
            # Create QR from any text/URL
            if message_text.strip():
                qr_img = QRGenerator.create_qr(message_text)
                
                if qr_img:
                    # Convert to bytes
                    img_byte_arr = io.BytesIO()
                    qr_img.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    
                    # Truncate long text for caption
                    display_text = message_text[:50] + "..." if len(message_text) > 50 else message_text
                    
                    await update.message.reply_photo(
                        photo=InputFile(img_byte_arr, filename="qr_code.png"),
                        caption=f"✅ **QR Code Generated!**\n\n"
                               f"**Content:** {display_text}\n"
                               f"**Size:** 400x400 pixels\n\n"
                               f"💡 *Scan with any QR scanner app*",
                        parse_mode='Markdown'
                    )
                    
                    # Save to history
                    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET total_tasks = total_tasks + 1 WHERE user_id = ?",
                        (user_id,)
                    )
                    cursor.execute(
                        "INSERT INTO task_history (user_id, task_type, input_data) VALUES (?, ?, ?)",
                        (user_id, 'qr_generation', message_text[:100])
                    )
                    conn.commit()
                    conn.close()
                else:
                    await update.message.reply_text("❌ Error creating QR. Please try again.")
            else:
                await update.message.reply_text("❌ Please send some text or URL")
            
            del context.user_data['waiting_for']
            return
        
        elif task_type == 'shorten_url':
            # Shorten URL
            if URLShortener.is_valid_url(message_text):
                shortened = URLShortener.shorten(message_text)
                
                await update.message.reply_text(
                    f"✅ **URL Shortened!**\n\n"
                    f"**Original:** {message_text}\n"
                    f"**Short:** `{shortened}`\n\n"
                    f"💡 *Click to copy and share*",
                    parse_mode='Markdown'
                )
                
                # Save to history
                conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET total_tasks = total_tasks + 1 WHERE user_id = ?",
                    (user_id,)
                )
                cursor.execute(
                    "INSERT INTO task_history (user_id, task_type, input_data) VALUES (?, ?, ?)",
                        (user_id, 'url_shortening', message_text[:100])
                )
                conn.commit()
                conn.close()
            else:
                await update.message.reply_text("❌ Please send a valid URL (e.g., https://example.com)")
            
            del context.user_data['waiting_for']
            return
    
    # If no waiting state, show main menu
    if message_text.startswith('/'):
        # Handle other commands if any
        pass
    elif message_text:
        # Auto-detect URL and suggest actions
        if message_text.startswith(('http://', 'https://')):
            keyboard = [
                [
                    InlineKeyboardButton("🎯 Create QR Code", callback_data="menu_qr"),
                    InlineKeyboardButton("🔗 Shorten URL", callback_data="menu_url")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔗 I detected a URL! What would you like to do?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # For regular text, offer QR creation
            keyboard = [
                [
                    InlineKeyboardButton("🎯 Create QR Code", callback_data="menu_qr")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📝 I see you sent some text. Want to make a QR code?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Update {update} caused error {context.error}")

# ==================== MAIN FUNCTION ====================
def main():
    """Main function to run the bot"""
    
    # Check if token is available
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found in environment variables!")
        print("💡 Make sure to set BOT_TOKEN in Render environment variables")
        return
    
    print("🚀 Initializing Utility Bot...")
    
    # Initialize database
    init_database()
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", handle_help))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    print("✅ Bot setup complete. Starting...")
    
    # Start the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
