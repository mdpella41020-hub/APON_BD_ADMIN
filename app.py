# ============================================
# 🌸 Premium Unified Bot Controller (Fixed Edition v6.2)
# ============================================
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import subprocess
import os
import json
import threading
import time
import asyncio
import requests
from datetime import datetime

# ============================================
# 🔐 BOT CONFIGURATION
# ============================================
TOKEN = "8381632107:AAHT5CauVp6o5lDLbazhyB2Rnv9xgQLdBZ8"
ADMIN_IDS = ["8423357174", "7952918120", "1234567891", "1234567892", "1234567893"]
YOUR_USERNAME = "@BD_ADMIN_20"
ADMIN_LINK = "https://t.me/BD_ADMIN_20"

# 🆕 API URLs
ADD_FRIEND_API_URL = "https://pnl-frind-add-api.vercel.app/adding_friend"
REMOVE_FRIEND_API_URL = "https://danger-friend-management.vercel.app/remove_friend"

# ============================================
# 🏩 DATA STORAGE
# ============================================
user_data = {}
running_bots = {}
system_locked = False
locked_users = set()
admin_announcements = []
sent_messages = {}
admin_notifications = []
selected_bot = {}

# ============================================
# 🎨 TINY TEXT CONVERTER (Small Caps)
# ============================================

def tiny(text):
    """Convert text to small caps / tiny letters"""
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    tiny = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    return ''.join(tiny[normal.index(c)] if c in normal else c for c in text)

# ============================================
# 🎨 BEAUTIFUL DECORATIONS
# ============================================

EMOJI = {
    'rose': '🌹', 'blossom': '🌸', 'green_heart': '💚', 'red_heart': '❤️',
    'blue_heart': '💙', 'fire': '🔥', 'robot': '🤖', 'crown': '👑',
    'lock': '🔏', 'unlock': '🔐', 'sms': '💬', 'trash': '🛒',
    'file': '📮', 'control': '🔮', 'project': '🏩', 'contact': '📠',
    'online': '💚', 'offline': '❤️', 'start': '▶️', 'stop': '⏹️',
    'delete': '🛒', 'back': '🔙', 'check': '✅', 'cross': '❌',
    'warning': '⚠️', 'info': 'ℹ️', 'user': '👤', 'admin': '👑',
    'sparkle': '✨', 'diamond': '🤍', 'star': '⭐', 'zap': '⚡',
    'folder': '📮', 'gear': '🌍', 'phone': '📱', 'link': '🔗',
    'users': '👥', 'photo': '📷', 'add': '👥', 'remove': '🔘',
    'friend': '👫', 'list': '📋', 'loading': '⏳', 'success': '🎉',
    'error': '💥', 'api': '🔌', 'world': '🌍', 'magic': '🔮',
    'manager': '👔', 'target': '🎯', 'bot': '🤖', 'key': '🔑',
    'id': '💙', 'password': '🔏', 'name': '🖊️', 'run': '🚀',
    'complete': '🎯', 'welcome': '👋', 'notification': '🔔',
    'done': '✅', 'sent': '📤', 'remove_done': '🗑️'
}

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

def is_locked(user_id):
    return system_locked or str(user_id) in locked_users

# ============================================
# 🎨 PREMIUM LOADING ANIMATION
# ============================================

async def show_loading(message, context, steps=None):
    """Show premium loading animation with progress bar"""
    if steps is None:
        steps = [
            ("🌹 ʟᴏᴀᴅɪɴɢ", "[▱▱▱▱▱▱▱▱▱▱]", "0%", "🌑"),
            ("🌺 ʟᴏᴀᴅɪɴɢ", "[▰▱▱▱▱▱▱▱▱▱]", "10%", "🌒"),
            ("🌸 ʟᴏᴀᴅɪɴɢ", "[▰▰▱▱▱▱▱▱▱▱]", "20%", "🌓"),
            ("🪷 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▱▱▱▱▱▱▱]", "30%", "🌔"),
            ("🌲 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▱▱▱▱▱▱]", "40%", "🌕"),
            ("🍁 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▰▱▱▱▱▱]", "50%", "🌖"),
            ("🌿 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▰▰▱▱▱▱]", "60%", "🌗"),
            ("🌻 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▰▰▰▱▱▱]", "70%", "🌘"),
            ("🌳 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▰▰▰▰▱▱]", "80%", "🌑"),
            ("🌼 ʟᴏᴀᴅɪɴɢ", "[▰▰▰▰▰▰▰▰▰▱]", "90%", "🌒"),
            ("💞 ᴄᴏᴍᴘʟᴇᴛᴇ", "[▰▰▰▰▰▰▰▰▰▰]", "100%", "✨")
        ]
    
    msg = await message.reply_text(f"{steps[0][3]} {steps[0][0]}: {steps[0][1]} {steps[0][2]}")
    
    for i in range(1, len(steps)):
        await asyncio.sleep(0.4)
        await msg.edit_text(f"{steps[i][3]} {steps[i][0]}: {steps[i][1]} {steps[i][2]}")
    
    return msg

# ============================================
# 🎨 KEYBOARD LAYOUTS
# ============================================

def get_main_keyboard(user_id):
    """Main keyboard layout with premium styling"""
    uid = str(user_id)
    is_adm = is_admin(uid)
    
    row1 = [
        KeyboardButton(f"{EMOJI['control']} ᴄᴏɴᴛʀᴏʟ"),
        KeyboardButton(f"{EMOJI['file']} ғɪʟᴇ")
    ]
    
    if is_adm:
        lock_emoji = EMOJI['unlock'] if system_locked else EMOJI['lock']
        lock_text = "ᴜɴʟᴏᴄᴋ" if system_locked else "ʟᴏᴄᴋ"
        row2 = [
            KeyboardButton(f"{EMOJI['project']} ᴘʀᴏᴊᴇᴄᴛ"),
            KeyboardButton(f"{lock_emoji} {lock_text}")
        ]
    else:
        row2 = []
    
    if is_adm:
        row3 = [KeyboardButton(f"{EMOJI['sms']} sᴍs ᴀʟʟ")]
    else:
        row3 = []
    
    # 🆕 ADD MANAGER & REMOVE MANAGER - ADMIN ONLY
    if is_adm:
        row4 = [
            KeyboardButton(f"{EMOJI['add']} ᴀᴅᴅ ᴍᴀɴᴀɢᴇʀ"),
            KeyboardButton(f"{EMOJI['remove']} ʀᴇᴍᴏᴠᴇ ᴍᴀɴᴀɢᴇʀ")
        ]
    else:
        row4 = []
    
    row5 = [KeyboardButton(f"{EMOJI['contact']} 📠 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ 📠")]
    
    keyboard = [row1]
    if row2:
        keyboard.append(row2)
    if row3:
        keyboard.append(row3)
    if row4:
        keyboard.append(row4)
    keyboard.append(row5)
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_bot_control_keyboard(bot_name, is_running):
    toggle_emoji = EMOJI['stop'] if is_running else EMOJI['start']
    toggle_text = "sᴛᴏᴘ" if is_running else "sᴛᴀʀᴛ"
    
    return ReplyKeyboardMarkup([
        [KeyboardButton(f"{toggle_emoji} {toggle_text}")],
        [KeyboardButton(f"{EMOJI['delete']} ᴅᴇʟᴇᴛᴇ")],
        [KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]
    ], resize_keyboard=True)

def get_back_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]], resize_keyboard=True)

def get_lock_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton(f"{EMOJI['lock']} ʟᴏᴄᴋ ᴀʟʟ ᴜsᴇʀs")],
        [KeyboardButton(f"{EMOJI['user']} ʟᴏᴄᴋ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ")],
        [KeyboardButton(f"{EMOJI['unlock']} ᴜɴʟᴏᴄᴋ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ")],
        [KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]
    ], resize_keyboard=True)

def get_sms_type_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton(f"{EMOJI['sms']} ᴛᴇxᴛ ᴍᴇssᴀɢᴇ")],
        [KeyboardButton(f"{EMOJI['photo']} ᴘʜᴏᴛᴏ ᴍᴇssᴀɢᴇ")],
        [KeyboardButton(f"{EMOJI['users']} sᴇɴᴅ ᴛᴏ ᴀʟʟ")],
        [KeyboardButton(f"{EMOJI['user']} sᴇɴᴅ ᴛᴏ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ")],
        [KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]
    ], resize_keyboard=True)

# ============================================
# 🎨 UI BOX FORMATTING - PREMIUM EDITION
# ============================================

def create_box(title, content, emoji="", width=28):
    title_tiny = tiny(title)
    lines = content.split('\n') if isinstance(content, str) else [content]
    
    box = f"{emoji}\n"
    box += f"╔{'═'*width}╗\n"
    box += f"║ {title_tiny.center(width-2)} ║\n"
    box += f"╠{'═'*width}╣\n"
    
    for line in lines:
        if line.strip():
            box += f"║ {line[:width-4].center(width-2)} ║\n"
    
    box += f"╚{'═'*width}╝\n"
    box += f"{emoji}"
    return box

def small_box(title, bangla, emoji=""):
    return create_box(title, bangla, emoji, 22)

def success_box(title, bangla, emoji=EMOJI['success']):
    return create_box(title, bangla, emoji, 28)

def error_box(title, bangla, emoji=EMOJI['error']):
    return create_box(title, bangla, emoji, 28)

def api_box(title, content, emoji=EMOJI['api']):
    return create_box(title, content, emoji, 30)

# 🆕 NEW: Custom response box for Add/Remove Manager
def manager_response_box(action_english, action_bangla, emoji, width=28):
    """Create a response box with English on top and Bengali below"""
    box = f"{emoji}\n"
    box += f"╔{'═'*width}╗\n"
    box += f"║ {action_english.center(width-2)} ║\n"
    box += f"╠{'═'*width}╣\n"
    box += f"║ {action_bangla.center(width-2)} ║\n"
    box += f"╚{'═'*width}╝\n"
    box += f"{emoji}"
    return box

# ============================================
# 🚀 HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "Unknown"
    
    if is_locked(user_id) and not is_admin(user_id):
        await update.message.reply_text(
            create_box("SYSTEM LOCKED", "🔒 আপনার অ্যাকাউন্ট লক", EMOJI['lock'], 26),
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if user_id not in user_data:
        user_data[user_id] = {
            'username': username,
            'step': None,
            'uid': None,
            'password': None,
            'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 🆕 DIFFERENT WELCOME FOR ADMIN vs NORMAL USER
    if is_admin(user_id):
        # ADMIN WELCOME - FULL FEATURES
        welcome_text = f"""{EMOJI['sparkle']} {tiny('APON BOT CONTROLLER')} {EMOJI['sparkle']}

{EMOJI['crown']} {tiny('WELCOME ADMIN')} @{username}! {EMOJI['crown']}

┌─ {EMOJI['control']} ᴄᴏɴᴛʀᴏʟ ─ UID & Password সেট করুন
├─ {EMOJI['file']} ғɪʟᴇ ─ আপনার বটগুলো দেখুন  
├─ {EMOJI['project']} ᴘʀᴏᴊᴇᴄᴛ ─ সব প্রোজেক্ট দেখুন
├─ {EMOJI['lock']} ʟᴏᴄᴋ/ᴜɴʟᴏᴄᴋ ─ সিস্টেম লক করুন
├─ {EMOJI['sms']} sᴍs ᴀʟʟ ─ সবাইকে মেসেজ পাঠান
├─ {EMOJI['add']} ᴀᴅᴅ ᴍᴀɴᴀɢᴇʀ ─ ম্যানেজার যোগ করুন
├─ {EMOJI['remove']} ʀᴇᴍᴏᴠᴇ ᴍᴀɴᴀɢᴇʀ ─ ম্যানেজার সরান
└─ {EMOJI['contact']} ᴄᴏɴᴛᴀᴄᴛ ─ এডমিনের সাথে যোগাযোগ

{EMOJI['diamond']} নিচের বাটনগুলো থেকে বেছে নিন:"""
    else:
        # NORMAL USER WELCOME - LIMITED FEATURES
        welcome_text = f"""{EMOJI['sparkle']} {tiny('APON BOT CONTROLLER')} {EMOJI['sparkle']}

{EMOJI['welcome']} {tiny('WELCOME')} @{username}! {EMOJI['welcome']}

┌─ {EMOJI['control']} ᴄᴏɴᴛʀᴏʟ ─ UID & Password সেট করুন
├─ {EMOJI['file']} ғɪʟᴇ ─ আপনার বটগুলো দেখুন  
└─ {EMOJI['contact']} ᴄᴏɴᴛᴀᴄᴛ ─ এডমিনের সাথে যোগাযোগ

{EMOJI['diamond']} নিচের বাটনগুলো থেকে বেছে নিন:"""
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(user_id))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global system_locked, locked_users
    
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip() if update.message.text else ""
    username = update.message.from_user.username or "Unknown"
    
    if user_id not in user_data:
        user_data[user_id] = {
            'username': username,
            'step': None,
            'uid': None,
            'password': None,
            'registered_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    user = user_data[user_id]
    step = user.get('step')
    
    if is_locked(user_id) and not is_admin(user_id):
        if "ʙᴀᴄᴋ" not in text:
            await update.message.reply_text(
                create_box("YOUR ACCOUNT LOCKED", "🔏 এডমিনের সাথে যোগাযোগ করুন", EMOJI['lock'], 26)
            )
            return
    
    # ==================== BACK BUTTON ====================
    if "ʙᴀᴄᴋ" in text:
        user['step'] = None
        selected_bot.pop(user_id, None)
        # Clear all temporary data
        for key in ['sms_type', 'sms_target', 'sms_photo', 'sms_caption', 'sms_target_id',
                    'manager_action', 'manager_uid', 'manager_password', 'manager_target_uid']:
            user.pop(key, None)
        
        await update.message.reply_text(
            create_box("MAIN MENU", "🏘️ মূল মেনুতে ফিরে এসেছেন", EMOJI['back'], 24),
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ==================== LOCK MENU ====================
    if step == 'lock_menu':
        if text == f"{EMOJI['lock']} ʟᴏᴄᴋ ᴀʟʟ ᴜsᴇʀs":
            loading_msg = await show_loading(update.message, context)
            await asyncio.sleep(0.5)
            system_locked = True
            user['step'] = None
            # 🆕 BOX STYLE LOCK MESSAGE
            await loading_msg.edit_text(
                create_box("SYSTEM LOCKED", "🔏 সিস্টেম লক হয়েছে!", EMOJI['lock'], 26)
            )
            await update.message.reply_text(
                reply_markup=get_main_keyboard(user_id)
            )
            return
            
        elif text == f"{EMOJI['user']} ʟᴏᴄᴋ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ":
            user['step'] = 'waiting_lock_user_id'
            await update.message.reply_text(
                small_box("ENTER USER ID", "লক করতে ইউজার আইডি দিন", EMOJI['lock']),
                reply_markup=get_back_keyboard()
            )
            return
            
        elif text == f"{EMOJI['unlock']} ᴜɴʟᴏᴄᴋ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ":
            user['step'] = 'waiting_unlock_user_id'
            await update.message.reply_text(
                small_box("ENTER USER ID", "আনলক করতে ইউজার আইডি দিন", EMOJI['unlock']),
                reply_markup=get_back_keyboard()
            )
            return
    
    elif step == 'waiting_lock_user_id':
        loading_msg = await show_loading(update.message, context)
        await asyncio.sleep(0.5)
        locked_users.add(text)
        user['step'] = None
        await loading_msg.edit_text(
            success_box("LOCK SUCCESSFUL", f"👤 {text}\n🔒 লক হয়ে গেছে", EMOJI['lock'])
        )
        await update.message.reply_text(
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    elif step == 'waiting_unlock_user_id':
        loading_msg = await show_loading(update.message, context)
        await asyncio.sleep(0.5)
        was_locked = text in locked_users
        if was_locked:
            locked_users.discard(text)
        user['step'] = None
        
        if was_locked:
            await loading_msg.edit_text(
                success_box("UNLOCK SUCCESSFUL", f"👤 {text}\n🔓 আনলক হয়ে গেছে", EMOJI['unlock'])
            )
        else:
            await loading_msg.edit_text(
                error_box("NOT LOCKED", f"👤 {text}\n⚠️ এই ইউজার লক ছিল না", EMOJI['warning'])
            )
        await update.message.reply_text(
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ==================== MAIN BUTTONS ====================
    
    if text == f"{EMOJI['control']} ᴄᴏɴᴛʀᴏʟ":
        user['step'] = 'waiting_uid'
        # 🆕 BOX STYLE UID REQUEST
        await update.message.reply_text(
            create_box("ENTER UID", f"{EMOJI['id']} আপনার UID দিন", EMOJI['id'], 24),
            reply_markup=get_back_keyboard()
        )
        return
    
    elif text == f"{EMOJI['file']} ғɪʟᴇ":
        await show_file_manager(update, user_id)
        return
    
    elif text == f"{EMOJI['project']} ᴘʀᴏᴊᴇᴄᴛ":
        if not is_admin(user_id):
            await update.message.reply_text("⛔ ᴀᴅᴍɪɴ ᴏɴʟʏ!")
            return
        await show_project_details(update)
        return
    
    elif text.startswith(f"{EMOJI['lock']} ʟᴏᴄᴋ") or text.startswith(f"{EMOJI['unlock']} ᴜɴʟᴏᴄᴋ"):
        if not is_admin(user_id):
            return
        
        if system_locked:
            loading_msg = await show_loading(update.message, context)
            await asyncio.sleep(0.5)
            system_locked = False
            # 🆕 BOX STYLE UNLOCK MESSAGE
            await loading_msg.edit_text(
                create_box("SYSTEM UNLOCKED", "🔓 সবাই আনলক হয়ে গেছে", EMOJI['unlock'], 26)
            )
            await update.message.reply_text(
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            user['step'] = 'lock_menu'
            await update.message.reply_text(
                create_box("LOCK SYSTEM", "🔏 লক অপশন নির্বাচন করুন", EMOJI['lock'], 28),
                reply_markup=get_lock_menu_keyboard()
            )
        return
    
    elif text == f"{EMOJI['sms']} sᴍs ᴀʟʟ":
        if not is_admin(user_id):
            return
        user['step'] = 'waiting_sms_type'
        await update.message.reply_text(
            small_box("SELECT TYPE", "কি পাঠাতে চান?", EMOJI['sms']),
            reply_markup=get_sms_type_keyboard()
        )
        return
    
    # 🆕 ADD MANAGER BUTTON
    elif text == f"{EMOJI['add']} ᴀᴅᴅ ᴍᴀɴᴀɢᴇʀ":
        if not is_admin(user_id):
            await update.message.reply_text("⛔ ᴀᴅᴍɪɴ ᴏɴʟʏ!")
            return
        user['step'] = 'waiting_manager_uid'
        user['manager_action'] = 'add'
        # 🆕 BOX STYLE
        await update.message.reply_text(
            create_box("ADD MANAGER", f"{EMOJI['id']} আপনার UID দিন", EMOJI['add'], 26),
            reply_markup=get_back_keyboard()
        )
        return
    
    # 🆕 REMOVE MANAGER BUTTON
    elif text == f"{EMOJI['remove']} ʀᴇᴍᴏᴠᴇ ᴍᴀɴᴀɢᴇʀ":
        if not is_admin(user_id):
            await update.message.reply_text("⛔ ᴀᴅᴍɪɴ ᴏɴʟʏ!")
            return
        
        user['step'] = 'waiting_manager_uid'
        user['manager_action'] = 'remove'
        # 🆕 BOX STYLE
        await update.message.reply_text(
            create_box("REMOVE MANAGER", f"{EMOJI['id']} আপনার UID দিন", EMOJI['remove'], 26),
            reply_markup=get_back_keyboard()
        )
        return
    
    elif text == f"{EMOJI['contact']} 📠 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ 📠":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📠 Contact Owner", url=ADMIN_LINK)]
        ])
        
        await update.message.reply_text(
            f"""{EMOJI['crown']} **BD ADMIN** {EMOJI['crown']}
📠 Contact Owner

Click to contact Owner: {datetime.now().strftime('%I:%M %p')}""",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # ==================== MANAGER FLOW (ADD & REMOVE) ====================
    # Step 1: Get UID
    elif step == 'waiting_manager_uid':
        user['manager_uid'] = text
        user['step'] = 'waiting_manager_password'
        # 🆕 BOX STYLE PASSWORD REQUEST
        await update.message.reply_text(
            create_box("ENTER PASSWORD", f"{EMOJI['password']} পাসওয়ার্ড দিন", EMOJI['lock'], 24),
            reply_markup=get_back_keyboard()
        )
        return
    
    # Step 2: Get Password
    elif step == 'waiting_manager_password':
        user['manager_password'] = text
        user['step'] = 'waiting_manager_target_uid'
        # 🆕 BOX STYLE TARGET REQUEST
        await update.message.reply_text(
            create_box("ENTER TARGET UID", f"{EMOJI['target']} টার্গেট UID দিন", EMOJI['target'], 26),
            reply_markup=get_back_keyboard()
        )
        return
    
    # Step 3: Get Target UID and Call API (ADD or REMOVE)
    elif step == 'waiting_manager_target_uid':
        target_uid = text
        uid = user.get('manager_uid')
        password = user.get('manager_password')
        action = user.get('manager_action', 'add')  # 'add' or 'remove'
        
        loading_msg = await show_loading(update.message, context)
        
        try:
            # 🆕 SELECT API URL BASED ON ACTION
            if action == 'add':
                api_url = f"{ADD_FRIEND_API_URL}?uid={uid}&password={password}&friend_uid={target_uid}"
                action_text = "ADD"
                # 🆕 CUSTOM SUCCESS MESSAGE FORMAT: English top, Bengali bottom
                success_english = "ᴀᴅᴅ sᴇɴᴛ sᴜᴄᴄᴇssғᴜʟʟʏ"
                success_bangla = "✅ ফ্রেন্ড রিকোয়েস্ট পাঠানো হয়েছে"
                error_english = "ᴀᴅᴅ ғᴀɪʟᴇᴅ"
                error_bangla = "❌ ফ্রেন্ড রিকোয়েস্ট ব্যর্থ"
            else:  # remove
                api_url = f"{REMOVE_FRIEND_API_URL}?uid={uid}&password={password}&friend_uid={target_uid}"
                action_text = "REMOVE"
                # 🆕 CUSTOM SUCCESS MESSAGE FORMAT: English top, Bengali bottom
                success_english = "ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ"
                success_bangla = "✅ ফ্রেন্ড রিমুভ করা হয়েছে"
                error_english = "ʀᴇᴍᴏᴠᴇ ғᴀɪʟᴇᴅ"
                error_bangla = "❌ ফ্রেন্ড রিমুভ ব্যর্থ"
            
            print(f"🔌 Calling API ({action_text}): {api_url}")
            
            response = requests.get(api_url, timeout=15)
            
            print(f"📡 Response Status: {response.status_code}")
            print(f"📄 Response Text: {response.text[:500]}")
            
            # Try to parse JSON response
            try:
                result = response.json()
                is_json = True
                print(f"✅ JSON Parsed: {result}")
            except Exception as e:
                result = {"success": False, "message": response.text}
                is_json = False
                print(f"❌ JSON Parse Error: {e}")
            
            # 🆕 FIXED RESPONSE HANDLING - Check multiple success indicators
            api_success = False
            
            if response.status_code == 200:
                # Check various success indicators from API
                if is_json:
                    # Check if API returned success=True or message contains success keywords
                    if result.get('success') == True:
                        api_success = True
                    elif result.get('status') == 'success':
                        api_success = True
                    elif 'success' in str(result.get('message', '')).lower():
                        api_success = True
                    elif 'sent' in str(result.get('message', '')).lower():
                        api_success = True
                    elif 'added' in str(result.get('message', '')).lower():
                        api_success = True
                    elif 'removed' in str(result.get('message', '')).lower():
                        api_success = True
                    elif 'delete' in str(result.get('message', '')).lower():
                        api_success = True
                    # If API returns any message without explicit error, consider it success
                    elif result.get('message') and 'error' not in str(result.get('message', '')).lower():
                        api_success = True
                    # If API returns data field, likely success
                    elif result.get('data') is not None:
                        api_success = True
                else:
                    # Non-JSON but HTTP 200, likely success
                    if 'error' not in response.text.lower():
                        api_success = True
            
            # 🎉 SHOW SUCCESS OR ERROR MESSAGE
            if api_success:
                # 🎉 SUCCESS - Show custom formatted message
                await loading_msg.edit_text(
                    manager_response_box(success_english, success_bangla, EMOJI['success'])
                )
            else:
                # ❌ FAILED - Show error with API message if available
                if is_json and result.get('message'):
                    error_detail = result.get('message')[:40]
                    error_bangla_full = f"❌ {error_detail}"
                else:
                    error_bangla_full = error_bangla
                
                await loading_msg.edit_text(
                    manager_response_box(error_english, error_bangla_full, EMOJI['cross'])
                )
                
        except requests.exceptions.Timeout:
            await loading_msg.edit_text(
                error_box("TIMEOUT", "⏱️ API রেসপন্স দিচ্ছে না", EMOJI['warning'])
            )
        except requests.exceptions.ConnectionError:
            await loading_msg.edit_text(
                error_box("CONNECTION ERROR", "🔌 ইন্টারনেট সমস্যা", EMOJI['warning'])
            )
        except Exception as e:
            await loading_msg.edit_text(
                error_box("ERROR", f"❌ {str(e)[:40]}", EMOJI['cross'])
            )
        
        # Clear user data
        user['step'] = None
        user.pop('manager_action', None)
        user.pop('manager_uid', None)
        user.pop('manager_password', None)
        
        await update.message.reply_text(
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    # ==================== SMS ====================
    elif step == 'waiting_sms_type':
        if text == f"{EMOJI['sms']} ᴛᴇxᴛ ᴍᴇssᴀɢᴇ":
            user['sms_type'] = 'text'
            user['step'] = 'waiting_sms_target'
            await update.message.reply_text(
                small_box("SELECT TARGET", "কাকে পাঠাতে চান?", EMOJI['sms']),
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton(f"{EMOJI['users']} sᴇɴᴅ ᴛᴏ ᴀʟʟ")],
                    [KeyboardButton(f"{EMOJI['user']} sᴇɴᴅ ᴛᴏ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ")],
                    [KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]
                ], resize_keyboard=True)
            )
            return
            
        elif text == f"{EMOJI['photo']} ᴘʜᴏᴛᴏ ᴍᴇssᴀɢᴇ":
            user['sms_type'] = 'photo'
            user['step'] = 'waiting_sms_target'
            await update.message.reply_text(
                small_box("SELECT TARGET", "কাকে ফটো পাঠাতে চান?", EMOJI['photo']),
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton(f"{EMOJI['users']} sᴇɴᴅ ᴛᴏ ᴀʟʟ")],
                    [KeyboardButton(f"{EMOJI['user']} sᴇɴᴅ ᴛᴏ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ")],
                    [KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")]
                ], resize_keyboard=True)
            )
            return
    
    elif step == 'waiting_sms_target':
        if text == f"{EMOJI['users']} sᴇɴᴅ ᴛᴏ ᴀʟʟ":
            user['sms_target'] = 'all'
            sms_type = user.get('sms_type', 'text')
            
            if sms_type == 'photo':
                user['step'] = 'waiting_sms_photo'
                await update.message.reply_text(
                    small_box("SEND PHOTO", "ফটো পাঠান", EMOJI['photo']),
                    reply_markup=get_back_keyboard()
                )
            else:
                user['step'] = 'waiting_sms_text'
                await update.message.reply_text(
                    small_box("TYPE MESSAGE", "সবাইকে পাঠান", EMOJI['sms']),
                    reply_markup=get_back_keyboard()
                )
            return
            
        elif text == f"{EMOJI['user']} sᴇɴᴅ ᴛᴏ sᴘᴇᴄɪғɪᴄ ᴜsᴇʀ":
            user['sms_target'] = 'specific'
            user['step'] = 'waiting_sms_user_id_input'
            await update.message.reply_text(
                small_box("ENTER USER ID", "ইউজার আইডি দিন", EMOJI['user']),
                reply_markup=get_back_keyboard()
            )
            return
    
    elif step == 'waiting_sms_user_id_input':
        user['sms_target_id'] = text
        sms_type = user.get('sms_type', 'text')
        
        if sms_type == 'photo':
            user['step'] = 'waiting_sms_photo'
            await update.message.reply_text(
                small_box("SEND PHOTO", f"👤 {text} কে ফটো পাঠান", EMOJI['photo']),
                reply_markup=get_back_keyboard()
            )
        else:
            user['step'] = 'waiting_sms_text'
            await update.message.reply_text(
                small_box("TYPE MESSAGE", f"👤 {text} কে মেসেজ পাঠান", EMOJI['sms']),
                reply_markup=get_back_keyboard()
            )
        return
    
    elif step == 'waiting_sms_text':
        await handle_sms_text_send(update, context, user_id, text)
        return
    
    # ==================== FILE MANAGER ====================
    if user_id in running_bots:
        for bot in running_bots[user_id]:
            if text == f"{EMOJI['gear']} {bot['name']}" or text == bot['name']:
                selected_bot[user_id] = bot['name']
                await show_bot_control_menu(update, user_id, bot['name'])
                return
    
    # ==================== BOT CONTROL ====================
    if text in [f"{EMOJI['start']} sᴛᴀʀᴛ", f"{EMOJI['stop']} sᴛᴏᴘ"]:
        if user_id in selected_bot:
            bot_name = selected_bot[user_id]
            for bot in running_bots.get(user_id, []):
                if bot['name'] == bot_name:
                    is_running = bot['process'].poll() is None if bot['process'] else False
                    
                    loading_msg = await show_loading(update.message, context)
                    await asyncio.sleep(1)
                    
                    if is_running:
                        await stop_bot_action(update, user_id, bot_name, loading_msg)
                    else:
                        await start_bot_action(update, user_id, bot_name, loading_msg)
                    
                    await show_bot_control_menu(update, user_id, bot_name)
                    return
        return
    
    elif text == f"{EMOJI['delete']} ᴅᴇʟᴇᴛᴇ":
        if user_id in selected_bot:
            bot_name = selected_bot[user_id]
            loading_msg = await show_loading(update.message, context)
            await delete_bot_action(update, user_id, bot_name, loading_msg)
        return
    
    # ==================== CONTROL FLOW (ORIGINAL BOT ADD) ====================
    if step == 'waiting_uid':
        if not text.isdigit():
            await update.message.reply_text(
                error_box("INVALID INPUT", "❌ শুধু নম্বর দিন!", EMOJI['warning'])
            )
            return
        user['uid'] = text
        user['step'] = 'waiting_password'
        # 🆕 BOX STYLE PASSWORD REQUEST
        await update.message.reply_text(
            create_box("ENTER PASSWORD", f"{EMOJI['password']} পাসওয়ার্ড দিন", EMOJI['lock'], 24)
        )
        return
    
    elif step == 'waiting_password':
        user['password'] = text
        user['step'] = 'waiting_verification'
        
        # 🆕 VERIFICATION WITH BOX STYLE
        msg = await update.message.reply_text(
            create_box("VERIFYING", "🔄 যাচাই করা হচ্ছে...", EMOJI['loading'], 26)
        )
        
        for i, percent in enumerate([20, 40, 60, 80, 100]):
            await asyncio.sleep(0.5)
            filled = "▰" * (i + 1) + "▱" * (4 - i)
            status = "✅ ᴠᴇʀɪғɪᴇᴅ" if percent == 100 else "🧭 ᴠᴇʀɪғʏɪɴɢ"
            await msg.edit_text(
                create_box("VERIFYING", f"{status}: [{filled}] {percent}%", EMOJI['loading'], 26)
            )
        
        await msg.edit_text(
            success_box("VERIFIED", "✅ যাচাই সফল!", EMOJI['check'])
        )
        
        user['step'] = 'waiting_bot_name'
        # 🆕 BOX STYLE BOT NAME REQUEST
        await update.message.reply_text(
            create_box("ENTER BOT NAME", f"{EMOJI['name']} বটের নাম দিন", EMOJI['robot'], 26)
        )
        return
    
    elif step == 'waiting_bot_name':
        bot_name = text
        uid = user['uid']
        password = user['password']
        
        loading_msg = await show_loading(update.message, context)
        success = await add_bot(user_id, uid, password, bot_name)
        
        if success:
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=int(admin_id),
                        text=f"""{EMOJI['crown']} ɴᴇᴡ ʙᴏᴛ ᴀᴅᴅᴇᴅ!
👤 User: @{username}
🆔 ID: `{user_id}`
🤖 Bot: `{bot_name}`
🔮 UID: `{uid}`
🔑 Pass: `{password}`
⏰ {datetime.now().strftime('%H:%M:%S')}""",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            
            # 🆕 SUCCESS MESSAGE WITH FILE MANAGER INSTRUCTION
            await loading_msg.edit_text(
                success_box("BOT ADDED", f"🤖 {bot_name}\n✅ সফলভাবে যোগ হয়েছে", EMOJI['check'])
            )
            
            # 🆕 ADDITIONAL MESSAGE TO GO TO FILE MANAGER
            await update.message.reply_text(
                create_box("NEXT STEP", f"{EMOJI['file']} ফাইল ম্যানেজার এ গিয়ে\nরান করুন", EMOJI['run'], 28),
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await loading_msg.edit_text(
                error_box("FAILED", "❌ বট যোগ করতে ব্যর্থ!", EMOJI['cross'])
            )
            await update.message.reply_text(
                reply_markup=get_main_keyboard(user_id)
            )
        
        user['step'] = None
        return

# ============================================
# 📸 PHOTO HANDLER
# ============================================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id not in user_data:
        return
    
    user = user_data[user_id]
    step = user.get('step')
    
    if step == 'waiting_sms_photo':
        photo = update.message.photo[-1]
        user['sms_photo'] = photo.file_id
        caption = update.message.caption or ""
        user['sms_caption'] = caption
        
        await handle_sms_photo_send(update, context, user_id)
    else:
        await update.message.reply_text("❌ এই মুহূর্তে ফটো গ্রহণযোগ্য নয়!")

# ============================================
# 🔧 UTILITY FUNCTIONS
# ============================================

async def handle_sms_text_send(update, context, user_id, text):
    user = user_data[user_id]
    target = user.get('sms_target', 'all')
    msg_id = str(int(time.time()))
    
    sent_messages[msg_id] = {
        'text': text,
        'photo': None,
        'caption': None,
        'time': datetime.now().strftime("%H:%M:%S"),
        'recipients': [],
        'sender': user_id,
        'type': 'text'
    }
    
    loading_msg = await show_loading(update.message, context)
    
    count = 0
    failed = 0
    
    if target == 'all':
        for uid in list(user_data.keys()):
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"""{EMOJI['sms']}
┌{'─'*22}┐
│  {tiny('ANNOUNCEMENT').center(18)}  │
├{'─'*22}┤
│  {text[:20].ljust(18)}  │
│  {text[20:40].ljust(18) if len(text) > 20 else ''}  │
│  {text[40:60].ljust(18) if len(text) > 40 else ''}  │
└{'─'*22}┘
⏰ {datetime.now().strftime('%H:%M')}"""
                )
                sent_messages[msg_id]['recipients'].append(uid)
                count += 1
            except Exception as e:
                print(f"Failed to send to {uid}: {e}")
                failed += 1
    else:
        target_id = user.get('sms_target_id')
        if target_id:
            try:
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"""{EMOJI['sms']}
┌{'─'*22}┐
│  {tiny('NEW MESSAGE').center(18)}  │
├{'─'*22}┤
│  {text[:20].ljust(18)}  │
│  {text[20:40].ljust(18) if len(text) > 20 else ''}  │
│  {text[40:60].ljust(18) if len(text) > 40 else ''}  │
└{'─'*22}┘
⏰ {datetime.now().strftime('%H:%M')}"""
                )
                sent_messages[msg_id]['recipients'].append(target_id)
                count += 1
            except Exception as e:
                print(f"Failed to send to {target_id}: {e}")
                failed += 1
    
    user['step'] = None
    user.pop('sms_type', None)
    user.pop('sms_target', None)
    user.pop('sms_target_id', None)
    
    await loading_msg.edit_text(
        success_box("SMS SENT", f"✅ {count} জনকে পাঠানো হয়েছে\n❌ {failed} জন ব্যর্থ", EMOJI['check'])
    )
    
    await update.message.reply_text(
        reply_markup=get_main_keyboard(user_id)
    )

async def handle_sms_photo_send(update, context, user_id):
    user = user_data[user_id]
    target = user.get('sms_target', 'all')
    photo_file_id = user.get('sms_photo')
    caption = user.get('sms_caption', '')
    msg_id = str(int(time.time()))
    
    sent_messages[msg_id] = {
        'text': caption,
        'photo': photo_file_id,
        'caption': caption,
        'time': datetime.now().strftime("%H:%M:%S"),
        'recipients': [],
        'sender': user_id,
        'type': 'photo'
    }
    
    loading_msg = await show_loading(update.message, context)
    
    count = 0
    failed = 0
    
    if target == 'all':
        for uid in list(user_data.keys()):
            try:
                await context.bot.send_photo(
                    chat_id=int(uid),
                    photo=photo_file_id,
                    caption=f"""{EMOJI['photo']} {tiny('PHOTO MESSAGE')}
⏰ {datetime.now().strftime('%H:%M')}

{caption}"""
                )
                sent_messages[msg_id]['recipients'].append(uid)
                count += 1
            except Exception as e:
                print(f"Failed to send photo to {uid}: {e}")
                failed += 1
    else:
        target_id = user.get('sms_target_id')
        if target_id:
            try:
                await context.bot.send_photo(
                    chat_id=int(target_id),
                    photo=photo_file_id,
                    caption=f"""{EMOJI['photo']} {tiny('PHOTO MESSAGE')}
⏰ {datetime.now().strftime('%H:%M')}

{caption}"""
                )
                sent_messages[msg_id]['recipients'].append(target_id)
                count += 1
            except Exception as e:
                print(f"Failed to send photo to {target_id}: {e}")
                failed += 1
    
    user['step'] = None
    user.pop('sms_type', None)
    user.pop('sms_target', None)
    user.pop('sms_target_id', None)
    user.pop('sms_photo', None)
    user.pop('sms_caption', None)
    
    await loading_msg.edit_text(
        success_box("PHOTO SENT", f"✅ {count} জনকে পাঠানো হয়েছে\n❌ {failed} জন ব্যর্থ", EMOJI['check'])
    )
    
    await update.message.reply_text(
        reply_markup=get_main_keyboard(user_id)
    )

async def show_file_manager(update, user_id):
    if user_id not in running_bots or not running_bots[user_id]:
        await update.message.reply_text(
            create_box("FILE MANAGER", "📮 কোনো বট নেই\nᴄᴏɴᴛʀᴏʟ এ ক্লিক করে\nনতুন বট যোগ করুন", EMOJI['file'], 26),
            reply_markup=get_main_keyboard(user_id)
        )
        return
    
    bots_display = []
    keyboard = []
    
    for bot in running_bots[user_id]:
        is_running = bot['process'].poll() is None if bot['process'] else False
        bot['status'] = 'online' if is_running else 'offline'
        
        bots_display.append({
            'name': bot['name'],
            'status': bot['status'],
            'uid': bot['uid'],
            'time': bot['start_time']
        })
        keyboard.append([KeyboardButton(f"{EMOJI['gear']} {bot['name']}")])
    
    keyboard.append([KeyboardButton(f"{EMOJI['back']} ʙᴀᴄᴋ")])
    
    text = f"{EMOJI['folder']} ᴍʏ ғɪʟᴇ ᴍᴀɴᴀɢᴇʀ\n"
    text += "─" * 25 + "\n\n"
    
    for bot in bots_display:
        status_emoji = EMOJI['online'] if bot['status'] == 'online' else EMOJI['offline']
        status_text = "ᴏɴʟɪɴᴇ" if bot['status'] == 'online' else "ᴏғғʟɪɴᴇ"
        text += f"{status_emoji} {status_text} | {bot['name']}\n"
        text += f"   👤 UID: {bot['uid'][:12]}...\n"
        text += f"   ⏰ {bot['time']}\n\n"
    
    text += "📮 বট সিলেক্ট করুন:"
    
    await update.message.reply_text(
        create_box("FILE MANAGER", text, EMOJI['file'], 30),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def show_bot_control_menu(update, user_id, bot_name):
    bot_status = "offline"
    is_running = False
    for bot in running_bots.get(user_id, []):
        if bot['name'] == bot_name:
            is_running = bot['process'].poll() is None if bot['process'] else False
            bot_status = "online" if is_running else "offline"
            break
    
    status_emoji = EMOJI['online'] if bot_status == 'online' else EMOJI['offline']
    status_text = "ᴏɴʟɪɴᴇ" if bot_status == 'online' else "ᴏғғʟɪɴᴇ"
    toggle_action = "sᴛᴏᴘ" if is_running else "sᴛᴀʀᴛ"
    toggle_emoji = EMOJI['stop'] if is_running else EMOJI['start']
    
    content = f"""{status_emoji} {bot_name}
Status: {status_text}

[{toggle_emoji} {toggle_action}]
[{EMOJI['delete']} ᴅᴇʟᴇᴛᴇ]

✅ ক্লিক করে কাজ করুন:"""
    
    await update.message.reply_text(
        create_box("BOT CONTROL", content, EMOJI['gear'], 28),
        reply_markup=get_bot_control_keyboard(bot_name, is_running)
    )

async def start_bot_action(update, user_id, bot_name, loading_msg=None):
    for bot in running_bots.get(user_id, []):
        if bot['name'] == bot_name:
            try:
                if bot['process'] and bot['process'].poll() is None:
                    bot['process'].terminate()
                    try:
                        bot['process'].wait(timeout=3)
                    except:
                        bot['process'].kill()
                
                with open('apon.txt', 'w') as f:
                    f.write(f"uid={bot['uid']},password={bot['password']}\n")
                
                with open('token.json', 'w') as f:
                    json.dump({
                        "token": "temp",
                        "uid": bot['uid'],
                        "bot_name": bot_name,
                        "user_id": user_id,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }, f)
                
                process = subprocess.Popen(
                    ['python3', 'main.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                bot['process'] = process
                bot['status'] = 'online'
                
                await asyncio.sleep(2)
                
                if process.poll() is None:
                    if loading_msg:
                        await loading_msg.edit_text(
                            success_box("BOT STARTED", f"💚 {bot_name}\n✅ বট চালু হয়েছে", EMOJI['start'])
                        )
                    else:
                        await update.message.reply_text(
                            success_box("BOT STARTED", f"💚 {bot_name}\n✅ বট চালু হয়েছে", EMOJI['start'])
                        )
                else:
                    stdout, stderr = process.communicate()
                    error_detail = stderr.decode()[:50] if stderr else "Unknown error"
                    if loading_msg:
                        await loading_msg.edit_text(
                            error_box("START FAILED", f"❌ {error_detail}", EMOJI['cross'])
                        )
                    else:
                        await update.message.reply_text(
                            error_box("START FAILED", f"❌ {error_detail}", EMOJI['cross'])
                        )
                        
            except Exception as e:
                error_msg = str(e)[:50]
                if loading_msg:
                    await loading_msg.edit_text(
                        error_box("ERROR", f"❌ {error_msg}", EMOJI['cross'])
                    )
                else:
                    await update.message.reply_text(f"❌ Error: {error_msg}")
            return

async def stop_bot_action(update, user_id, bot_name, loading_msg=None):
    for bot in running_bots.get(user_id, []):
        if bot['name'] == bot_name:
            try:
                if bot['process']:
                    bot['process'].terminate()
                    try:
                        bot['process'].wait(timeout=3)
                    except:
                        bot['process'].kill()
                bot['status'] = 'offline'
                
                if loading_msg:
                    await loading_msg.edit_text(
                        success_box("BOT STOPPED", f"❤️ {bot_name}\n✅ বট বন্ধ হয়েছে", EMOJI['stop'])
                    )
                else:
                    await update.message.reply_text(
                        success_box("BOT STOPPED", f"❤️ {bot_name}\n✅ বট বন্ধ হয়েছে", EMOJI['stop'])
                    )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
            return

async def delete_bot_action(update, user_id, bot_name, loading_msg=None):
    for idx, bot in enumerate(list(running_bots.get(user_id, []))):
        if bot['name'] == bot_name:
            try:
                if bot['process']:
                    bot['process'].terminate()
                    try:
                        bot['process'].wait(timeout=3)
                    except:
                        bot['process'].kill()
            except:
                pass
            
            running_bots[user_id].pop(idx)
            selected_bot.pop(user_id, None)
            
            if loading_msg:
                await loading_msg.edit_text(
                    success_box("BOT DELETED", f"🛒 {bot_name}\n✅ বট মুছে ফেলা হয়েছে", EMOJI['delete'])
                )
            else:
                await update.message.reply_text(
                    success_box("BOT DELETED", f"🛒 {bot_name}\n✅ বট মুছে ফেলা হয়েছে", EMOJI['delete'])
                )
            
            await update.message.reply_text(
                reply_markup=get_main_keyboard(user_id)
            )
            return
    
    await update.message.reply_text("❌ বট পাওয়া যায়নি!")

async def show_project_details(update):
    if not user_data:
        await update.message.reply_text("⚠️ কোনো ইউজার নেই!")
        return
    
    text = ""
    for idx, (uid, data) in enumerate(user_data.items(), 1):
        username = data.get('username', 'Unknown')
        user_uid = data.get('uid', 'N/A')
        password = data.get('password', 'N/A')
        
        text += f"\n┌─ 👤 ᴜsᴇʀ #{idx} ─┐\n"
        text += f"│ @{username[:15]}\n"
        text += f"│ 🆔 {uid[:12]}...\n"
        text += f"│ 🔮 UID: {str(user_uid)[:12]}...\n"
        text += f"│ 🔑 Pass: {str(password)[:10]}...\n"
        
        if uid in running_bots:
            text += f"│ 🤖 Bots: {len(running_bots[uid])}\n"
        
        text += f"└{'─'*20}┘\n"
    
    await update.message.reply_text(
        create_box("ALL PROJECTS", text, EMOJI['project'], 32),
        reply_markup=get_main_keyboard(update.message.from_user.id)
    )

async def add_bot(user_id, uid, password, bot_name):
    try:
        if user_id not in running_bots:
            running_bots[user_id] = []
        
        for existing_bot in running_bots[user_id]:
            if existing_bot['name'] == bot_name:
                return False
        
        running_bots[user_id].append({
            'name': bot_name,
            'uid': uid,
            'password': password,
            'process': None,
            'start_time': datetime.now().strftime("%H:%M:%S"),
            'status': 'offline'
        })
        
        return True
    except Exception as e:
        print(f"Error adding bot: {e}")
        return False

# ============================================
# 🚀 MAIN
# ============================================

def main():
    print(f"{EMOJI['robot']} Bot Starting...")
    print(f"{EMOJI['api']} Add API: {ADD_FRIEND_API_URL}")
    print(f"{EMOJI['api']} Remove API: {REMOVE_FRIEND_API_URL}")
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print(f"{EMOJI['green_heart']} Bot Running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
