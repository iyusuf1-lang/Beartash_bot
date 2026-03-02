from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import database as db
from config import Status, STATUS_EMOJI, STATUS_TEXT, DEFAULT_SETTINGS
from customer_kb import *
from reports import format_order, format_money

# ══════════════════════════════════════════════
# XARIDOR HANDLER
# ══════════════════════════════════════════════

# Conversation states
(
    ORDER_PHONE,
    ORDER_ADDRESS,
    ORDER_PAYMENT,
    ORDER_NOTE,
    ORDER_CONFIRM,
) = range(5)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def get_cart(ctx) -> dict:
    return ctx.user_data.get("cart", {})

def set_cart(ctx, cart: dict):
    ctx.user_data["cart"] = cart

def cart_total(cart: dict) -> int:
    return sum(item["price"] * item["qty"] for item in cart.values())

def cart_summary(cart: dict) -> str:
    if not cart:
        return "🛒 Savat bo'sh"
    text = "🛒 *Savat:*\n\n"
    for item in cart.values():
        subtotal = item["price"] * item["qty"]
        text += f"• {item['name']} × {item['qty']} = {format_money(subtotal)}\n"
    text += f"\n💰 *Jami: {format_money(cart_total(cart))}*"
    return text

async def get_shop_for_customer(ctx) -> dict | None:
    """Birinchi aktiv do'konni qaytarish"""
    shop_id = ctx.user_data.get("shop_id")
    if shop_id:
        return db.get_shop_by_id(shop_id)
    # Birinchi do'konni topish
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM shop WHERE is_active=1 LIMIT 1").fetchone()
        if row:
            shop = dict(row)
            ctx.user_data["shop_id"] = shop["id"]
            return shop
    return None

# ──────────────────────────────────────────────
# START
# ──────────────────────────────────────────────

async def customer_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_customer(user.id, user.username, user.first_name)

    shop = await get_shop_for_customer(ctx)
    if not shop:
        await update.message.reply_text("❗️ Do'kon hali ochilmagan.")
        return

    await update.message.reply_text(
        f"👋 *{shop['name']}* ga xush kelibsiz!\n\n"
        f"{shop.get('description') or 'Buyurtma berish uchun katalogdan tanlang.'}\n\n"
        f"📦 Mahsulotlarni ko'rish uchun 'Katalog' tugmasini bosing.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=customer_main_kb()
    )

# ──────────────────────────────────────────────
# KATALOG
# ──────────────────────────────────────────────

async def catalog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = await get_shop_for_customer(ctx)
    if not shop:
        return

    cats = db.get_categories(shop["id"])
    if not cats:
        await update.message.reply_text("📭 Hali mahsulotlar yo'q.")
        return

    await update.message.reply_text(
        "📂 *Kategoriyani tanlang:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=catalog_kb(cats)
    )

async def catalog_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split(":")[2])
    ctx.user_data["current_cat"] = cat_id
    ctx.user_data["cat_page"] = 0

    shop = await get_shop_for_customer(ctx)
    if not shop:
        return

    products = db.get_products(shop["id"], category_id=cat_id)
    cart = get_cart(ctx)

    if not products:
        await query.edit_message_text("📭 Bu kategoriyada mahsulotlar yo'q.")
        return

    await query.edit_message_text(
        f"📦 *{len(products)} ta mahsulot:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=products_list_kb(products, cart)
    )

async def product_view_customer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[2])
    p = db.get_product(product_id)
    if not p:
        return

    cart = get_cart(ctx)
    in_cart = cart.get(str(product_id), {}).get("qty", 0)

    text = (
        f"📦 *{p['name']}*\n\n"
        f"💰 Narx: *{format_money(p['price'])}*\n"
    )
    if p.get("description"):
        text += f"\n{p['description']}\n"

    if p.get("photo_url"):
        await query.message.reply_photo(
            photo=p["photo_url"],
            caption=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=product_kb(product_id, in_cart)
        )
    else:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=product_kb(product_id, in_cart)
        )

# ──────────────────────────────────────────────
# SAVAT
# ──────────────────────────────────────────────

async def cart_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Savatga qo'shildi!")

    product_id = str(query.data.split(":")[2])
    p = db.get_product(int(product_id))
    if not p:
        return

    cart = get_cart(ctx)
    if product_id in cart:
        cart[product_id]["qty"] += 1
    else:
        cart[product_id] = {"name": p["name"], "price": p["price"], "qty": 1}
    set_cart(ctx, cart)

    in_cart = cart[product_id]["qty"]
    await query.edit_message_reply_markup(reply_markup=product_kb(int(product_id), in_cart))

async def cart_plus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = str(query.data.split(":")[2])
    p = db.get_product(int(product_id))
    cart = get_cart(ctx)
    if product_id in cart:
        cart[product_id]["qty"] += 1
    else:
        cart[product_id] = {"name": p["name"], "price": p["price"], "qty": 1}
    set_cart(ctx, cart)
    await query.answer(f"+1 qo'shildi")
    in_cart = cart[product_id]["qty"]
    await query.edit_message_reply_markup(reply_markup=product_kb(int(product_id), in_cart))

async def cart_minus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = str(query.data.split(":")[2])
    cart = get_cart(ctx)
    if product_id in cart:
        cart[product_id]["qty"] -= 1
        if cart[product_id]["qty"] <= 0:
            del cart[product_id]
    set_cart(ctx, cart)
    in_cart = cart.get(product_id, {}).get("qty", 0)
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=product_kb(int(product_id), in_cart))

async def cart_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    cart = get_cart(ctx)
    text = cart_summary(cart)

    shop = await get_shop_for_customer(ctx)
    settings = db.get_shop_settings(shop["owner_id"]) if shop else {}
    delivery_fee = settings.get("yetkazib_berish_narxi", DEFAULT_SETTINGS["yetkazib_berish_narxi"])

    if cart:
        text += f"\n🚗 Yetkazib berish: *{format_money(delivery_fee)}*"
        text += f"\n💳 Umumiy: *{format_money(cart_total(cart) + delivery_fee)}*"

    msg = query.message if query else update.message
    if query:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=cart_kb(cart) if cart else None
        )
    else:
        await msg.reply_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=cart_kb(cart) if cart else None
        )

async def cart_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🗑 Savat tozalandi")
    set_cart(ctx, {})
    await query.edit_message_text("🛒 Savat bo'shatildi.")

# ──────────────────────────────────────────────
# BUYURTMA BERISH
# ──────────────────────────────────────────────

async def checkout_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = get_cart(ctx)
    if not cart:
        await query.edit_message_text("🛒 Savat bo'sh!")
        return ConversationHandler.END

    await query.message.reply_text(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=share_phone_kb()
    )
    return ORDER_PHONE

async def order_get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    elif update.message.text and update.message.text != "❌ Bekor qilish":
        phone = update.message.text.strip()
    else:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=customer_main_kb())
        return ConversationHandler.END

    ctx.user_data["order_phone"] = phone

    await update.message.reply_text(
        "📍 Manzilingizni yuboring yoki yozing:",
        reply_markup=share_location_kb()
    )
    return ORDER_ADDRESS

async def order_get_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        lat = update.message.location.latitude
        lng = update.message.location.longitude
        ctx.user_data["order_address"] = f"📍 {lat:.4f}, {lng:.4f}"
    elif update.message.text and update.message.text not in ["❌ Bekor qilish", "✍️ Manzilni yozaman"]:
        if update.message.text == "❌ Bekor qilish":
            await update.message.reply_text("❌ Bekor qilindi.", reply_markup=customer_main_kb())
            return ConversationHandler.END
        ctx.user_data["order_address"] = update.message.text.strip()
    else:
        if update.message.text != "✍️ Manzilni yozaman":
            await update.message.reply_text("❌ Bekor qilindi.", reply_markup=customer_main_kb())
            return ConversationHandler.END
        await update.message.reply_text("✍️ Manzilni yozing:")
        return ORDER_ADDRESS

    await update.message.reply_text(
        "💳 To'lov usulini tanlang:",
        reply_markup=payment_kb()
    )
    return ORDER_PAYMENT

async def order_get_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment = query.data.split(":")[1]
    ctx.user_data["order_payment"] = payment

    # Buyurtmani tasdiqlash
    cart = get_cart(ctx)
    shop = await get_shop_for_customer(ctx)
    settings = db.get_shop_settings(shop["owner_id"]) if shop else {}
    delivery_fee = settings.get("yetkazib_berish_narxi", DEFAULT_SETTINGS["yetkazib_berish_narxi"])
    total = cart_total(cart)

    from config import TOLOV_USULLARI
    text = (
        f"📋 *Buyurtmani tasdiqlang:*\n\n"
        f"{cart_summary(cart)}\n\n"
        f"📍 Manzil: {ctx.user_data.get('order_address')}\n"
        f"📞 Telefon: {ctx.user_data.get('order_phone')}\n"
        f"💳 To'lov: {TOLOV_USULLARI.get(payment, payment)}\n"
        f"🚗 Yetkazib berish: {format_money(delivery_fee)}\n"
        f"💰 *Umumiy: {format_money(total + delivery_fee)}*"
    )

    await query.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=order_confirm_kb()
    )
    return ORDER_CONFIRM

async def order_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "order:cancel":
        await query.edit_message_text("❌ Buyurtma bekor qilindi.")
        return ConversationHandler.END

    # Buyurtmani saqlash
    cart = get_cart(ctx)
    shop = await get_shop_for_customer(ctx)
    settings = db.get_shop_settings(shop["owner_id"]) if shop else {}
    delivery_fee = settings.get("yetkazib_berish_narxi", DEFAULT_SETTINGS["yetkazib_berish_narxi"])

    customer = db.get_customer(update.effective_user.id)
    items = [
        {"name": v["name"], "price": v["price"], "qty": v["qty"]}
        for v in cart.values()
    ]

    order_id = db.create_order(
        shop_id=shop["id"],
        customer_id=customer["id"],
        items=items,
        total_price=cart_total(cart),
        delivery_fee=delivery_fee,
        address=ctx.user_data.get("order_address", ""),
        phone=ctx.user_data.get("order_phone", ""),
        tolov_usuli=ctx.user_data.get("order_payment", "naqd"),
    )

    # Savatni tozalash
    set_cart(ctx, {})

    await query.edit_message_text(
        f"✅ *Buyurtma #{order_id} qabul qilindi!*\n\n"
        f"Do'kon tez orada siz bilan bog'lanadi.\n"
        f"Buyurtma holati: /status_{order_id}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=customer_main_kb()
    )

    # Adminga xabar
    order = db.get_order(order_id)
    order_text = format_order(order, for_admin=True)
    try:
        from admin_kb import order_status_kb
        await ctx.bot.send_message(
            chat_id=shop["owner_id"],
            text=f"🆕 *Yangi buyurtma!*\n\n{order_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=order_status_kb(order_id, "yangi")
        )
    except Exception:
        pass

    return ConversationHandler.END

# ──────────────────────────────────────────────
# BUYURTMALAR TARIXI
# ──────────────────────────────────────────────

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    customer = db.get_customer(update.effective_user.id)
    if not customer:
        await update.message.reply_text("Hali buyurtmalar yo'q.")
        return

    shop = await get_shop_for_customer(ctx)
    if not shop:
        return

    orders = db.get_customer_orders(customer["id"], shop["id"])
    if not orders:
        await update.message.reply_text(
            "📭 Hali buyurtmalar yo'q.\n\nBuyurtma berish uchun '🛍 Katalog' ni oching.",
            reply_markup=customer_main_kb()
        )
        return

    text = f"📋 *Buyurtmalaringiz ({len(orders)} ta):*\n\n"
    for o in orders[:5]:
        emoji = STATUS_EMOJI.get(o["status"], "📦")
        text += f"{emoji} #{o['id']} — {format_money(o['total_price'])} — {o['created_at'][:10]}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def order_status_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        order_id = int(update.message.text.split("_")[1])
        order = db.get_order(order_id)
        if not order:
            await update.message.reply_text("Buyurtma topilmadi.")
            return

        customer = db.get_customer(update.effective_user.id)
        if not customer or order["customer_id"] != customer["id"]:
            await update.message.reply_text("❗️ Bu buyurtma sizga tegishli emas.")
            return

        text = format_order(order, for_admin=False)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except (IndexError, ValueError):
        pass

# ──────────────────────────────────────────────
# DO'KON MA'LUMOTLARI
# ──────────────────────────────────────────────

async def shop_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = await get_shop_for_customer(ctx)
    if not shop:
        return

    settings = db.get_shop_settings(shop["owner_id"])
    settings = db.get_shop_settings(shop["owner_id"])
    phone_val = shop.get("phone") or "kiritilmagan"
    addr_val = shop.get("address") or "kiritilmagan"
    hours_val = settings.get("ish_vaqti", "09:00 - 22:00")
    delivery_val = "Ha" if settings.get("yetkazib_berish", True) else "Yoq"
    text = (
        f"🏪 *{shop['name']}*\n\n"
        f"📞 Telefon: {phone_val}\n"
        f"📍 Manzil: {addr_val}\n"
        f"⏰ Ish vaqti: {hours_val}\n"
        f"🚗 Yetkazib berish: {delivery_val}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = await get_shop_for_customer(ctx)
    if not shop:
        return

    phone = shop.get("phone") or "ko'rsatilmagan"
    await update.message.reply_text(
        f"📞 *Bog'lanish*\n\n"
        f"🏪 {shop['name']}\n"
        f"📞 {phone}",
        parse_mode=ParseMode.MARKDOWN
    )
