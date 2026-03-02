#!/usr/bin/env python3
"""
🏪 Biznes Bot — Kichik do'konlar uchun Telegram bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Admin panel (mahsulot, buyurtma, hisobot)
✅ Xaridor panel (katalog, savat, buyurtma)
✅ Broadcast xabar
✅ Statistika va hisobotlar
"""

import sys
import os

# Railway va boshqa platformalarda modul yo'lini to'g'rilash
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)

from config import BOT_TOKEN
from database import init_db, is_admin

from admin import (
    admin_start, setup_name,
    products_menu, products_list, product_view,
    add_product_start, add_product_name, add_product_price,
    add_product_desc, add_product_photo, add_product_cat, save_product,
    toggle_product_stock, delete_product_confirm, delete_product_execute,
    orders_menu, orders_list, order_view, order_change_status,
    reports_menu, show_report,
    settings_menu, settings_change, settings_save,
    broadcast_start, broadcast_send,
    SETUP_NAME, ADD_PROD_NAME, ADD_PROD_PRICE, ADD_PROD_DESC,
    ADD_PROD_PHOTO, ADD_PROD_CAT, SETTINGS_VALUE, BROADCAST_TEXT,
)

from customer import (
    customer_start, catalog, catalog_category,
    product_view_customer,
    cart_add, cart_plus, cart_minus, cart_view, cart_clear,
    checkout_start, order_get_phone, order_get_address,
    order_get_payment, order_confirm,
    my_orders, order_status_check, shop_info, contact,
    ORDER_PHONE, ORDER_ADDRESS, ORDER_PAYMENT, ORDER_CONFIRM,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
# UNIVERSAL START — admin yoki xaridor?
# ══════════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        return await admin_start(update, ctx)
    return await customer_start(update, ctx)

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from admin_kb import admin_main_kb
    from customer_kb import customer_main_kb
    if is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=admin_main_kb())
    else:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=customer_main_kb())
    return ConversationHandler.END

# ══════════════════════════════════════════════
# TEXT MESSAGE ROUTER
# ══════════════════════════════════════════════

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if is_admin(user_id):
        # Admin menyu
        if text == "📦 Mahsulotlar":
            return await products_menu(update, ctx)
        elif text == "🛒 Buyurtmalar":
            return await orders_menu(update, ctx)
        elif text == "📊 Hisobot":
            return await reports_menu(update, ctx)
        elif text == "⚙️ Sozlamalar":
            return await settings_menu(update, ctx)
        elif text == "👁 Do'konni ko'rish":
            return await shop_info(update, ctx)
        elif text == "📢 Xabar yuborish":
            return await broadcast_start(update, ctx)
        elif text == "👥 Xaridorlar":
            return await customers_list(update, ctx)
    else:
        # Xaridor menyu
        if text == "🛍 Katalog":
            return await catalog(update, ctx)
        elif text == "🛒 Savatim":
            return await cart_view(update, ctx)
        elif text == "📋 Buyurtmalarim":
            return await my_orders(update, ctx)
        elif text == "📞 Bog'lanish":
            return await contact(update, ctx)
        elif text == "ℹ️ Do'kon haqida":
            return await shop_info(update, ctx)
        elif text.startswith("/status_"):
            return await order_status_check(update, ctx)

async def customers_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from database import get_shop, get_all_customers
    shop = get_shop(update.effective_user.id)
    if not shop:
        return
    customers = get_all_customers(shop["id"])
    if not customers:
        await update.message.reply_text("👥 Hali xaridorlar yo'q.")
        return
    text = f"👥 *Xaridorlar ({len(customers)} ta):*\n\n"
    for i, c in enumerate(customers[:20], 1):
        name = c.get("first_name") or "Mehmon"
        username = f" @{c['username']}" if c.get("username") else ""
        text += f"{i}. *{name}*{username} — {c['total_orders']} buyurtma\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ══════════════════════════════════════════════
# CALLBACK ROUTER
# ══════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    # Admin callbacklar
    if data.startswith("prod:list"):
        return await products_list(update, ctx)
    elif data.startswith("prod:view:"):
        return await product_view(update, ctx)
    elif data.startswith("prod:add"):
        return await add_product_start(update, ctx)
    elif data.startswith("prod:toggle:"):
        return await toggle_product_stock(update, ctx)
    elif data.startswith("prod:del:"):
        return await delete_product_confirm(update, ctx)
    elif data.startswith("confirm_del:"):
        return await delete_product_execute(update, ctx)
    elif data.startswith("orders:"):
        if data == "orders:back":
            await update.callback_query.answer()
            return await orders_menu(update, ctx)
        return await orders_list(update, ctx)
    elif data.startswith("order:status:"):
        return await order_change_status(update, ctx)
    elif data.startswith("order:view:"):
        return await order_view(update, ctx)
    elif data.startswith("report:"):
        return await show_report(update, ctx)
    elif data.startswith("settings:"):
        return await settings_change(update, ctx)

    # Xaridor callbacklar
    elif data.startswith("cat:browse:"):
        return await catalog_category(update, ctx)
    elif data.startswith("prod:view_c:"):
        return await product_view_customer(update, ctx)
    elif data.startswith("cart:add:"):
        return await cart_add(update, ctx)
    elif data.startswith("cart:plus:"):
        return await cart_plus(update, ctx)
    elif data.startswith("cart:minus:"):
        return await cart_minus(update, ctx)
    elif data == "cart:view":
        return await cart_view(update, ctx)
    elif data == "cart:clear":
        return await cart_clear(update, ctx)
    elif data == "cat:back":
        return await catalog(update, ctx)

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN topilmadi! config.py da o'rnating.")
        return

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # ── Admin setup conversation ──
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SETUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # ── Mahsulot qo'shish conversation ──
    add_prod_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product_start, pattern="^prod:add$")],
        states={
            ADD_PROD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            ADD_PROD_DESC:  [MessageHandler(filters.TEXT | filters.COMMAND, add_product_desc)],
            ADD_PROD_PHOTO: [
                MessageHandler(filters.PHOTO, add_product_photo),
                MessageHandler(filters.TEXT | filters.COMMAND, add_product_photo),
            ],
            ADD_PROD_CAT: [CallbackQueryHandler(add_product_cat, pattern="^cat:select_prod:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # ── Buyurtma berish conversation ──
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^order:checkout$")],
        states={
            ORDER_PHONE: [
                MessageHandler(filters.CONTACT, order_get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_phone),
            ],
            ORDER_ADDRESS: [
                MessageHandler(filters.LOCATION, order_get_address),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_address),
            ],
            ORDER_PAYMENT: [CallbackQueryHandler(order_get_payment, pattern="^pay:")],
            ORDER_CONFIRM: [CallbackQueryHandler(order_confirm, pattern="^order:(confirm|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # ── Sozlamalar conversation ──
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_change, pattern="^settings:")],
        states={
            SETTINGS_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # ── Broadcast conversation ──
    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 Xabar yuborish$"), broadcast_start)],
        states={
            BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Handlerlarni qo'shish (tartib muhim!)
    app.add_handler(setup_conv)
    app.add_handler(add_prod_conv)
    app.add_handler(order_conv)
    app.add_handler(settings_conv)
    app.add_handler(broadcast_conv)

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("cancel", cancel))

    logger.info("🚀 Biznes Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
