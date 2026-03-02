from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import database as db
from config import DEFAULT_SETTINGS
from keyboards.admin_kb import *
from utils.reports import report_today, report_weekly, report_monthly, format_order

# ══════════════════════════════════════════════
# ADMIN HANDLER — Do'kon egasi
# ══════════════════════════════════════════════

# Conversation states
(
    SETUP_NAME,
    ADD_PROD_NAME, ADD_PROD_PRICE, ADD_PROD_DESC, ADD_PROD_PHOTO, ADD_PROD_CAT,
    EDIT_VALUE,
    SETTINGS_VALUE,
    ADD_CAT_NAME,
    BROADCAST_TEXT,
) = range(10)

# ──────────────────────────────────────────────
# START / SETUP
# ──────────────────────────────────────────────

async def admin_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    shop = db.get_shop(user.id)

    if not shop:
        await update.message.reply_text(
            "🏪 *Xush kelibsiz!*\n\n"
            "Do'koningiz hali yaratilmagan.\n"
            "Do'kon nomini kiriting:",
            parse_mode=ParseMode.MARKDOWN
        )
        return SETUP_NAME

    await update.message.reply_text(
        f"👋 *{shop['name']}* — Admin paneli\n\n"
        f"Quyidagi bo'limlardan birini tanlang:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_kb()
    )
    return ConversationHandler.END

async def setup_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❗️ Nom kamida 2 ta harf bo'lishi kerak.")
        return SETUP_NAME

    shop_id = db.create_shop(update.effective_user.id, name)
    ctx.user_data["shop_id"] = shop_id

    await update.message.reply_text(
        f"✅ *{name}* do'koni yaratildi!\n\n"
        f"Endi mahsulotlar qo'shishingiz mumkin.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_kb()
    )
    return ConversationHandler.END

# ──────────────────────────────────────────────
# MAHSULOTLAR
# ──────────────────────────────────────────────

async def products_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *Mahsulotlar bo'limi*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=products_menu_kb()
    )

async def products_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return

    products = db.get_products(shop["id"], in_stock_only=False)
    if not products:
        await query.edit_message_text(
            "📦 Hali mahsulotlar yo'q.\n\nQo'shish uchun '➕ Mahsulot qo'shish' tugmasini bosing.",
            reply_markup=products_menu_kb()
        )
        return

    text = f"📦 *Mahsulotlar ({len(products)} ta):*\n\n"
    buttons = []
    for p in products:
        stock = "✅" if p["in_stock"] else "❌"
        text_btn = f"{stock} {p['name']} — {p['price']:,} so'm"
        buttons.append([InlineKeyboardButton(text_btn, callback_data=f"prod:view:{p['id']}")])

    buttons.append([InlineKeyboardButton("➕ Qo'shish", callback_data="prod:add")])
    from telegram import InlineKeyboardMarkup
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=InlineKeyboardMarkup(buttons))

async def product_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[2])
    p = db.get_product(product_id)
    if not p:
        return

    stock = "✅ Sotuvda" if p["in_stock"] else "❌ Sotuvda yo'q"
    text = (
        f"📦 *{p['name']}*\n\n"
        f"💰 Narx: *{p['price']:,} so'm*\n"
        f"📊 Holat: {stock}\n"
    )
    if p.get("description"):
        text += f"📄 Tavsif: {p['description']}\n"

    if p.get("photo_url"):
        await query.message.reply_photo(
            photo=p["photo_url"],
            caption=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=product_actions_kb(product_id, bool(p["in_stock"]))
        )
    else:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=product_actions_kb(product_id, bool(p["in_stock"]))
        )

async def add_product_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("📝 Mahsulot nomini kiriting:")
    else:
        await update.message.reply_text("📝 Mahsulot nomini kiriting:")
    return ADD_PROD_NAME

async def add_product_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_prod"] = {"name": update.message.text.strip()}
    await update.message.reply_text("💰 Narxini kiriting (so'mda, faqat raqam):")
    return ADD_PROD_PRICE

async def add_product_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(" ", "").replace(",", ""))
        ctx.user_data["new_prod"]["price"] = price
    except ValueError:
        await update.message.reply_text("❗️ Faqat raqam kiriting. Qayta urinib ko'ring:")
        return ADD_PROD_PRICE

    await update.message.reply_text(
        "📄 Tavsif kiriting (ixtiyoriy):\n\n"
        "O'tkazib yuborish uchun /skip yozing"
    )
    return ADD_PROD_DESC

async def add_product_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip":
        ctx.user_data["new_prod"]["description"] = update.message.text.strip()

    await update.message.reply_text(
        "🖼 Rasm yuboring (ixtiyoriy):\n\n"
        "O'tkazib yuborish uchun /skip yozing"
    )
    return ADD_PROD_PHOTO

async def add_product_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "/skip" and update.message.photo:
        file = await update.message.photo[-1].get_file()
        ctx.user_data["new_prod"]["photo_url"] = file.file_path

    # Kategoriya tanlash
    shop = db.get_shop(update.effective_user.id)
    cats = db.get_categories(shop["id"])

    if cats:
        await update.message.reply_text(
            "🗂 Kategoriyani tanlang:",
            reply_markup=categories_kb(cats, action="select_prod")
        )
        return ADD_PROD_CAT
    else:
        return await save_product(update, ctx, category_id=None)

async def add_product_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split(":")[2])
    return await save_product(query, ctx, category_id=cat_id)

async def save_product(update_or_query, ctx, category_id=None):
    prod = ctx.user_data.get("new_prod", {})
    user_id = update_or_query.effective_user.id if hasattr(update_or_query, 'effective_user') else update_or_query.from_user.id
    shop = db.get_shop(user_id)

    product_id = db.add_product(
        shop_id=shop["id"],
        name=prod["name"],
        price=prod["price"],
        category_id=category_id,
        description=prod.get("description"),
        photo_url=prod.get("photo_url"),
    )

    msg = f"✅ *{prod['name']}* qo'shildi!\n💰 Narx: *{prod['price']:,} so'm*"
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update_or_query.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN, reply_markup=products_menu_kb()
        )

    ctx.user_data.pop("new_prod", None)
    return ConversationHandler.END

async def toggle_product_stock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[2])
    db.toggle_stock(product_id)
    p = db.get_product(product_id)
    status = "✅ Sotuvga chiqarildi" if p["in_stock"] else "❌ Sotuvdan olindi"
    await query.answer(status, show_alert=True)
    # Sahifani yangilash
    stock = "✅ Sotuvda" if p["in_stock"] else "❌ Sotuvda yo'q"
    await query.edit_message_text(
        f"📦 *{p['name']}*\n💰 {p['price']:,} so'm\n📊 {stock}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=product_actions_kb(product_id, bool(p["in_stock"]))
    )

async def delete_product_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split(":")[2])
    p = db.get_product(product_id)
    await query.edit_message_text(
        f"🗑 *{p['name']}* ni o'chirishni tasdiqlaysizmi?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_delete_kb("prod", product_id)
    )

async def delete_product_execute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, item_type, item_id = query.data.split(":")
    item_id = int(item_id)

    if item_type == "prod":
        db.delete_product(item_id)
        await query.edit_message_text("✅ Mahsulot o'chirildi.", reply_markup=products_menu_kb())

# ──────────────────────────────────────────────
# BUYURTMALAR
# ──────────────────────────────────────────────

async def orders_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return

    new_orders = db.get_orders(shop["id"], status="yangi")
    text = f"🛒 *Buyurtmalar*\n\n🆕 Yangi: *{len(new_orders)} ta*"

    msg = update.message or update.callback_query.message
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=orders_filter_kb())

async def orders_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    status = query.data.split(":")[1]
    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return

    if status == "all":
        orders = db.get_orders(shop["id"], limit=20)
    else:
        orders = db.get_orders(shop["id"], status=status)

    if not orders:
        await query.edit_message_text(
            "📭 Buyurtmalar yo'q.",
            reply_markup=orders_filter_kb()
        )
        return

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from config import STATUS_EMOJI
    buttons = []
    for o in orders[:10]:
        emoji = STATUS_EMOJI.get(o["status"], "📦")
        label = f"{emoji} #{o['id']} — {o['total_price']:,} so'm ({o['first_name'] or '?'})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"order:view:{o['id']}")])
    buttons.append([InlineKeyboardButton("◀️ Orqaga", callback_data="orders:back")])

    await query.edit_message_text(
        f"📋 *{len(orders)} ta buyurtma:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def order_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split(":")[2])
    order = db.get_order(order_id)
    if not order:
        return

    text = format_order(order, for_admin=True)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=order_status_kb(order_id, order["status"])
    )

async def order_change_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, _, order_id, new_status = query.data.split(":")
    order_id = int(order_id)
    order = db.get_order(order_id)
    db.update_order_status(order_id, new_status)

    from config import STATUS_EMOJI, STATUS_TEXT
    status_text = f"{STATUS_EMOJI[new_status]} {STATUS_TEXT[new_status]}"
    await query.answer(f"Status: {status_text}", show_alert=True)

    # Xaridorga xabar yuborish
    try:
        await ctx.bot.send_message(
            chat_id=order["customer_user_id"],
            text=(
                f"📦 *Buyurtma #{order_id} holati o'zgardi!*\n\n"
                f"{status_text}"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass

    await order_view(update, ctx)

# ──────────────────────────────────────────────
# HISOBOTLAR
# ──────────────────────────────────────────────

async def reports_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    await update.message.reply_text(
        "📊 *Hisobotlar*\nQaysi davrni ko'rmoqchisiz?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Bugun",   callback_data="report:today")],
            [InlineKeyboardButton("📆 Hafta",   callback_data="report:week")],
            [InlineKeyboardButton("🗓 Oy",      callback_data="report:month")],
        ])
    )

async def show_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return

    period = query.data.split(":")[1]
    if period == "today":
        text = report_today(shop["id"])
    elif period == "week":
        text = report_weekly(shop["id"])
    else:
        text = report_monthly(shop["id"])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

# ──────────────────────────────────────────────
# SOZLAMALAR
# ──────────────────────────────────────────────

async def settings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return

    settings = db.get_shop_settings(update.effective_user.id)
    text = (
        f"⚙️ *Sozlamalar*\n\n"
        f"🏪 Nom: *{shop['name']}*\n"
        f"📞 Telefon: *{shop['phone'] or 'kiritilmagan'}*\n"
        f"📍 Manzil: *{shop['address'] or 'kiritilmagan'}*\n"
        f"🚗 Yetkazib berish: *{('Ha' if settings.get('yetkazib_berish', True) else 'Yoq')}*\n"
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=settings_kb()
    )

async def settings_change(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    field = query.data.split(":")[1]
    ctx.user_data["settings_field"] = field

    prompts = {
        "name":     "🏪 Yangi do'kon nomini kiriting:",
        "phone":    "📞 Telefon raqamini kiriting (+998xxxxxxxxx):",
        "address":  "📍 Do'kon manzilini kiriting:",
        "hours":    "⏰ Ish vaqtini kiriting (masalan: 09:00 - 22:00):",
    }

    if field == "delivery":
        settings = db.get_shop_settings(update.effective_user.id)
        settings["yetkazib_berish"] = not settings.get("yetkazib_berish", True)
        db.save_shop_settings(update.effective_user.id, settings)
        status = "yoqildi ✅" if settings["yetkazib_berish"] else "o'chirildi ❌"
        await query.answer(f"Yetkazib berish {status}", show_alert=True)
        return

    await query.edit_message_text(prompts.get(field, "Yangi qiymat kiriting:"))
    return SETTINGS_VALUE

async def settings_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    field = ctx.user_data.get("settings_field")
    value = update.message.text.strip()

    if field in ("name", "phone", "address"):
        db.update_shop(update.effective_user.id, **{field: value})
    elif field == "hours":
        settings = db.get_shop_settings(update.effective_user.id)
        settings["ish_vaqti"] = value
        db.save_shop_settings(update.effective_user.id, settings)

    await update.message.reply_text(
        "✅ Sozlama saqlandi!",
        reply_markup=admin_main_kb()
    )
    return ConversationHandler.END

# ──────────────────────────────────────────────
# BROADCAST
# ──────────────────────────────────────────────

async def broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Barcha xaridorlarga xabar*\n\n"
        "Yubormoqchi bo'lgan matnni kiriting.\n"
        "Bekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )
    return BROADCAST_TEXT

async def broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop = db.get_shop(update.effective_user.id)
    if not shop:
        return ConversationHandler.END

    text = update.message.text
    customers = db.get_all_customers(shop["id"])

    sent = 0
    for c in customers:
        try:
            await ctx.bot.send_message(
                chat_id=c["user_id"],
                text=f"📢 *{shop['name']}*\n\n{text}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ *{sent} ta* xaridorga yuborildi!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_main_kb()
    )
    return ConversationHandler.END
