from database import get_stats_today, get_stats_period, get_top_products, get_orders
from config import Status, STATUS_EMOJI

# ══════════════════════════════════════════════
# HISOBOTLAR
# ══════════════════════════════════════════════

def format_money(amount: int) -> str:
    return f"{amount:,} so'm".replace(",", " ")

def report_today(shop_id: int) -> str:
    stats = get_stats_today(shop_id)
    return (
        f"📊 *Bugungi hisobot*\n\n"
        f"🛒 Buyurtmalar: *{stats['orders_count']} ta*\n"
        f"💰 Daromad: *{format_money(stats['revenue'])}*\n"
        f"👥 Xaridorlar: *{stats['unique_customers']} ta*\n"
    )

def report_weekly(shop_id: int) -> str:
    data = get_stats_period(shop_id, days=7)
    total_orders  = sum(d["orders"]  for d in data)
    total_revenue = sum(d["revenue"] for d in data)

    text = f"📈 *Haftalik hisobot*\n\n"

    if not data:
        return text + "Hali buyurtmalar yo'q."

    # Har kun uchun mini chart
    max_rev = max(d["revenue"] for d in data) or 1
    for d in data:
        bar_len = int((d["revenue"] / max_rev) * 8)
        bar = "█" * bar_len + "░" * (8 - bar_len)
        text += f"`{d['day'][-5:]}` {bar} {format_money(d['revenue'])}\n"

    text += f"\n📦 Jami: *{total_orders} ta*\n"
    text += f"💰 Jami: *{format_money(total_revenue)}*\n"

    # Top mahsulotlar
    top = get_top_products(shop_id, limit=3)
    if top:
        text += f"\n🏆 *Top mahsulotlar:*\n"
        for i, (name, qty) in enumerate(top, 1):
            text += f"{i}. {name} — {qty} ta\n"

    return text

def report_monthly(shop_id: int) -> str:
    data = get_stats_period(shop_id, days=30)
    total_orders  = sum(d["orders"]  for d in data)
    total_revenue = sum(d["revenue"] for d in data)

    text = f"📅 *Oylik hisobot*\n\n"
    text += f"📦 Jami buyurtmalar: *{total_orders} ta*\n"
    text += f"💰 Jami daromad: *{format_money(total_revenue)}*\n"

    if total_orders > 0:
        avg = total_revenue // total_orders
        text += f"📊 O'rtacha buyurtma: *{format_money(avg)}*\n"

    # Faol kunlar
    active_days = len([d for d in data if d["orders"] > 0])
    text += f"📆 Faol kunlar: *{active_days}/30*\n"

    # Top mahsulotlar
    top = get_top_products(shop_id, limit=5)
    if top:
        text += f"\n🏆 *Top 5 mahsulot:*\n"
        for i, (name, qty) in enumerate(top, 1):
            text += f"{i}. {name} — {qty} ta\n"

    return text

def format_order(order: dict, for_admin: bool = True) -> str:
    """Buyurtmani chiroyli formatda ko'rsatish"""
    emoji = STATUS_EMOJI.get(order["status"], "📦")

    text = f"{emoji} *Buyurtma #{order['id']}*\n"
    text += f"📅 {order['created_at'][:16]}\n\n"

    # Mahsulotlar
    text += "🛒 *Tarkib:*\n"
    total = 0
    for item in order["items"]:
        name  = item.get("name", "?")
        qty   = item.get("qty", 1)
        price = item.get("price", 0)
        subtotal = qty * price
        total += subtotal
        text += f"  • {name} × {qty} = {format_money(subtotal)}\n"

    text += f"\n💰 Mahsulotlar: *{format_money(order['total_price'])}*\n"
    if order.get("delivery_fee", 0) > 0:
        text += f"🚗 Yetkazib berish: *{format_money(order['delivery_fee'])}*\n"
        text += f"💳 Jami: *{format_money(order['total_price'] + order['delivery_fee'])}*\n"

    text += f"\n💳 To'lov: *{order.get('tolov_usuli', 'naqd')}*\n"

    if order.get("address"):
        text += f"📍 Manzil: {order['address']}\n"
    if order.get("phone"):
        text += f"📞 Telefon: {order['phone']}\n"
    if order.get("note"):
        text += f"📝 Izoh: {order['note']}\n"

    if for_admin and order.get("first_name"):
        text += f"\n👤 Xaridor: {order['first_name']}"
        if order.get("username"):
            text += f" (@{order['username']})"
        text += "\n"

    return text
