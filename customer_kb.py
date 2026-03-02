from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ══════════════════════════════════════════════
# XARIDOR TUGMALAR
# ══════════════════════════════════════════════

def customer_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["🛍 Katalog",        "🛒 Savatim"],
        ["📋 Buyurtmalarim",  "📞 Bog'lanish"],
        ["ℹ️ Do'kon haqida"],
    ], resize_keyboard=True)

def catalog_kb(categories: list) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat:browse:{cat['id']}"
        )])
    return InlineKeyboardMarkup(buttons)

def product_kb(product_id: int, in_cart: int = 0) -> InlineKeyboardMarkup:
    if in_cart > 0:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➖", callback_data=f"cart:minus:{product_id}"),
                InlineKeyboardButton(f"🛒 {in_cart} ta", callback_data=f"cart:view"),
                InlineKeyboardButton("➕", callback_data=f"cart:plus:{product_id}"),
            ],
            [InlineKeyboardButton("◀️ Katalogga qaytish", callback_data="cat:back")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Savatga qo'shish", callback_data=f"cart:add:{product_id}")],
        [InlineKeyboardButton("◀️ Katalogga qaytish", callback_data="cat:back")],
    ])

def products_list_kb(products: list, cart: dict, page: int = 0) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati — sahifalash bilan"""
    PER_PAGE = 6
    start = page * PER_PAGE
    end   = start + PER_PAGE
    page_products = products[start:end]

    buttons = []
    for p in page_products:
        qty = cart.get(str(p["id"]), 0)
        label = f"{p['name']} — {p['price']:,} so'm"
        if qty > 0:
            label = f"✅ {label} ({qty})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"prod:view_c:{p['id']}")])

    # Navigatsiya
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"prod:page:{page-1}"))
    if end < len(products):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"prod:page:{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🛒 Savatim", callback_data="cart:view")])
    buttons.append([InlineKeyboardButton("◀️ Kategoriyalar", callback_data="cat:back")])
    return InlineKeyboardMarkup(buttons)

def cart_kb(cart: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✅ Buyurtma berish",   callback_data="order:checkout")],
        [InlineKeyboardButton("🗑 Savatni tozalash",  callback_data="cart:clear")],
        [InlineKeyboardButton("◀️ Katalogga qaytish", callback_data="cat:back")],
    ]
    return InlineKeyboardMarkup(buttons)

def payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Naqd pul",  callback_data="pay:naqd")],
        [InlineKeyboardButton("📱 Payme",     callback_data="pay:payme")],
        [InlineKeyboardButton("📲 Click",     callback_data="pay:click")],
    ])

def order_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash",   callback_data="order:confirm"),
            InlineKeyboardButton("❌ Bekor",         callback_data="order:cancel"),
        ]
    ])

def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📞 Telefon raqamni ulashish", request_contact=True)],
        [KeyboardButton("❌ Bekor qilish")],
    ], resize_keyboard=True, one_time_keyboard=True)

def share_location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📍 Manzilimni yuborish", request_location=True)],
        [KeyboardButton("✍️ Manzilni yozaman")],
        [KeyboardButton("❌ Bekor qilish")],
    ], resize_keyboard=True, one_time_keyboard=True)

def order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Holat yangilash", callback_data=f"cust:refresh:{order_id}")]
    ])
