from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import Status, STATUS_EMOJI, STATUS_TEXT

# ══════════════════════════════════════════════
# ADMIN TUGMALAR
# ══════════════════════════════════════════════

def admin_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["📦 Mahsulotlar",    "🛒 Buyurtmalar"],
        ["📊 Hisobot",        "👥 Xaridorlar"],
        ["⚙️ Sozlamalar",     "📢 Xabar yuborish"],
        ["👁 Do'konni ko'rish"],
    ], resize_keyboard=True)

def products_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mahsulot qo'shish",    callback_data="prod:add")],
        [InlineKeyboardButton("📋 Mahsulotlar ro'yxati", callback_data="prod:list")],
        [InlineKeyboardButton("🗂 Kategoriyalar",        callback_data="cat:list")],
    ])

def product_actions_kb(product_id: int, in_stock: bool) -> InlineKeyboardMarkup:
    stock_text = "❌ Sotuvdan olib tashlash" if in_stock else "✅ Sotuvga chiqarish"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Tahrirlash",  callback_data=f"prod:edit:{product_id}")],
        [InlineKeyboardButton(stock_text,       callback_data=f"prod:toggle:{product_id}")],
        [InlineKeyboardButton("🗑 O'chirish",   callback_data=f"prod:del:{product_id}")],
        [InlineKeyboardButton("◀️ Orqaga",      callback_data="prod:list")],
    ])

def product_edit_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Nom",          callback_data=f"edit:name:{product_id}")],
        [InlineKeyboardButton("💰 Narx",         callback_data=f"edit:price:{product_id}")],
        [InlineKeyboardButton("📄 Tavsif",       callback_data=f"edit:desc:{product_id}")],
        [InlineKeyboardButton("🖼 Rasm",         callback_data=f"edit:photo:{product_id}")],
        [InlineKeyboardButton("◀️ Orqaga",       callback_data=f"prod:view:{product_id}")],
    ])

def orders_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Yangi",          callback_data="orders:yangi")],
        [InlineKeyboardButton("👨‍🍳 Tayyorlanmoqda", callback_data="orders:tayyorlanmoqda")],
        [InlineKeyboardButton("🚗 Yetkazilmoqda",  callback_data="orders:yetkazilmoqda")],
        [InlineKeyboardButton("✅ Hammasi",         callback_data="orders:all")],
    ])

def order_status_kb(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    statuses = [
        Status.QABUL,
        Status.TAYYORLANMOQDA,
        Status.YETKAZILMOQDA,
        Status.YETKAZILDI,
        Status.BEKOR,
    ]
    buttons = []
    for s in statuses:
        if s == current_status:
            continue
        buttons.append([InlineKeyboardButton(
            f"{STATUS_EMOJI[s]} {STATUS_TEXT[s]}",
            callback_data=f"order:status:{order_id}:{s}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Orqaga", callback_data="orders:all")])
    return InlineKeyboardMarkup(buttons)

def confirm_delete_kb(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirm_del:{item_type}:{item_id}"),
            InlineKeyboardButton("❌ Yo'q",       callback_data=f"cancel_del"),
        ]
    ])

def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Do'kon nomi",       callback_data="settings:name")],
        [InlineKeyboardButton("📞 Telefon",           callback_data="settings:phone")],
        [InlineKeyboardButton("📍 Manzil",            callback_data="settings:address")],
        [InlineKeyboardButton("🚗 Yetkazib berish",   callback_data="settings:delivery")],
        [InlineKeyboardButton("⏰ Ish vaqti",          callback_data="settings:hours")],
    ])

def categories_kb(categories: list, action: str = "select") -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat:{action}:{cat['id']}"
        )])
    if action == "select":
        buttons.append([InlineKeyboardButton("➕ Kategoriya qo'shish", callback_data="cat:add")])
    return InlineKeyboardMarkup(buttons)
