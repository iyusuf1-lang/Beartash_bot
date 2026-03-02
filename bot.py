#!/usr/bin/env python3
"""Biznes Bot — hammasi bitta faylda, import muammosi yoq"""
import logging, os, json, sqlite3
from contextlib import contextmanager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8611968517:AAEg9YzYdc12SiBL_D498bD7vcgyRUkt3sI")
DB_PATH   = os.getenv("DB_PATH", "biznes.db")

STATUS_EMOJI = {"yangi":"🆕","qabul":"✅","tayyorlanmoqda":"👨‍🍳","yetkazilmoqda":"🚗","yetkazildi":"🎉","bekor":"❌"}
STATUS_TEXT  = {"yangi":"Yangi buyurtma","qabul":"Qabul qilindi","tayyorlanmoqda":"Tayyorlanmoqda","yetkazilmoqda":"Yetkazilmoqda","yetkazildi":"Yetkazildi","bekor":"Bekor qilindi"}
TOLOV = {"naqd":"💵 Naqd pul","payme":"📱 Payme","click":"📲 Click"}
DEFAULT_FEE = 15_000
SETUP_NAME,ADD_PROD_NAME,ADD_PROD_PRICE,ADD_PROD_DESC,ADD_PROD_PHOTO,SETTINGS_VALUE,BROADCAST_TEXT,ORDER_PHONE,ORDER_ADDRESS,ORDER_PAYMENT,ORDER_CONFIRM = range(11)

# ── DB ──
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS shop(id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id INTEGER UNIQUE NOT NULL,name TEXT NOT NULL DEFAULT 'Dokonim',phone TEXT,address TEXT,is_active INTEGER DEFAULT 1,settings TEXT DEFAULT '{}',created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,shop_id INTEGER NOT NULL,name TEXT NOT NULL,emoji TEXT DEFAULT '📦');
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,shop_id INTEGER NOT NULL,category_id INTEGER,name TEXT NOT NULL,description TEXT,price INTEGER NOT NULL,photo_id TEXT,in_stock INTEGER DEFAULT 1,created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER UNIQUE NOT NULL,username TEXT,first_name TEXT,phone TEXT,total_orders INTEGER DEFAULT 0,total_spent INTEGER DEFAULT 0,created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,shop_id INTEGER NOT NULL,customer_id INTEGER NOT NULL,items TEXT NOT NULL DEFAULT '[]',total_price INTEGER NOT NULL DEFAULT 0,delivery_fee INTEGER DEFAULT 0,address TEXT,phone TEXT,tolov_usuli TEXT DEFAULT 'naqd',status TEXT DEFAULT 'yangi',note TEXT,created_at TEXT DEFAULT(datetime('now')),updated_at TEXT DEFAULT(datetime('now')));
        """); c.commit()
    logger.info("✅ DB ready")

@contextmanager
def db():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    try: yield c; c.commit()
    except: c.rollback(); raise
    finally: c.close()

def get_shop(owner_id):
    with db() as c: r=c.execute("SELECT * FROM shop WHERE owner_id=?",(owner_id,)).fetchone(); return dict(r) if r else None
def get_shop_by_id(sid):
    with db() as c: r=c.execute("SELECT * FROM shop WHERE id=?",(sid,)).fetchone(); return dict(r) if r else None
def get_first_shop():
    with db() as c: r=c.execute("SELECT * FROM shop WHERE is_active=1 LIMIT 1").fetchone(); return dict(r) if r else None
def create_shop(owner_id,name):
    with db() as c:
        cur=c.execute("INSERT INTO shop(owner_id,name) VALUES(?,?)",(owner_id,name)); sid=cur.lastrowid
        c.execute("INSERT INTO categories(shop_id,name,emoji) VALUES(?,?,?)",(sid,"Asosiy","📦")); return sid
def update_shop(owner_id,**kw):
    f=", ".join(f"{k}=?" for k in kw); v=list(kw.values())+[owner_id]
    with db() as c: c.execute(f"UPDATE shop SET {f} WHERE owner_id=?",v)
def is_admin(uid):
    with db() as c: return c.execute("SELECT id FROM shop WHERE owner_id=?",(uid,)).fetchone() is not None
def get_settings(owner_id):
    s=get_shop(owner_id);
    if not s: return {}
    try: return json.loads(s.get("settings") or "{}")
    except: return {}
def save_settings(owner_id,settings):
    with db() as c: c.execute("UPDATE shop SET settings=? WHERE owner_id=?",(json.dumps(settings,ensure_ascii=False),owner_id))
def get_categories(sid):
    with db() as c: return [dict(r) for r in c.execute("SELECT * FROM categories WHERE shop_id=? ORDER BY id",(sid,)).fetchall()]
def get_products(sid,cat_id=None,stock_only=True):
    with db() as c:
        q="SELECT p.*,c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.shop_id=?"; params=[sid]
        if cat_id: q+=" AND p.category_id=?"; params.append(cat_id)
        if stock_only: q+=" AND p.in_stock=1"
        q+=" ORDER BY p.id"; return [dict(r) for r in c.execute(q,params).fetchall()]
def get_product(pid):
    with db() as c: r=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone(); return dict(r) if r else None
def add_product(sid,name,price,cat_id=None,desc=None,photo_id=None):
    with db() as c: cur=c.execute("INSERT INTO products(shop_id,category_id,name,price,description,photo_id) VALUES(?,?,?,?,?,?)",(sid,cat_id,name,price,desc,photo_id)); return cur.lastrowid
def del_product(pid):
    with db() as c: c.execute("DELETE FROM products WHERE id=?",(pid,))
def toggle_stock(pid):
    with db() as c: c.execute("UPDATE products SET in_stock=CASE WHEN in_stock=1 THEN 0 ELSE 1 END WHERE id=?",(pid,))
def get_customer(uid):
    with db() as c: r=c.execute("SELECT * FROM customers WHERE user_id=?",(uid,)).fetchone(); return dict(r) if r else None
def upsert_customer(uid,username=None,first_name=None):
    with db() as c: c.execute("INSERT INTO customers(user_id,username,first_name) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name",(uid,username or "",first_name or "Mehmon"))
    return get_customer(uid)
def get_all_customers(sid):
    with db() as c: return [dict(r) for r in c.execute("SELECT c.* FROM customers c INNER JOIN orders o ON o.customer_id=c.id WHERE o.shop_id=? GROUP BY c.id ORDER BY c.total_orders DESC",(sid,)).fetchall()]
def create_order(sid,cid,items,total,fee,address,phone,tolov,note=None):
    with db() as c:
        cur=c.execute("INSERT INTO orders(shop_id,customer_id,items,total_price,delivery_fee,address,phone,tolov_usuli,note) VALUES(?,?,?,?,?,?,?,?,?)",(sid,cid,json.dumps(items,ensure_ascii=False),total,fee,address,phone,tolov,note))
        oid=cur.lastrowid; c.execute("UPDATE customers SET total_orders=total_orders+1,total_spent=total_spent+? WHERE id=?",(total+fee,cid)); return oid
def get_order(oid):
    with db() as c:
        r=c.execute("SELECT o.*,c.first_name,c.username,c.user_id as customer_user_id FROM orders o LEFT JOIN customers c ON o.customer_id=c.id WHERE o.id=?",(oid,)).fetchone()
        if not r: return None
        d=dict(r); d["items"]=json.loads(d["items"]); return d
def get_orders(sid,status=None,limit=50):
    with db() as c:
        q="SELECT o.*,c.first_name,c.username FROM orders o LEFT JOIN customers c ON o.customer_id=c.id WHERE o.shop_id=?"; params=[sid]
        if status: q+=" AND o.status=?"; params.append(status)
        q+=" ORDER BY o.created_at DESC LIMIT ?"; params.append(limit)
        res=[]
        for r in c.execute(q,params).fetchall(): d=dict(r); d["items"]=json.loads(d["items"]); res.append(d)
        return res
def update_order_status(oid,status):
    with db() as c: c.execute("UPDATE orders SET status=?,updated_at=datetime('now') WHERE id=?",(status,oid))
def get_customer_orders(cid,sid,limit=10):
    with db() as c:
        res=[]
        for r in c.execute("SELECT * FROM orders WHERE customer_id=? AND shop_id=? ORDER BY created_at DESC LIMIT ?",(cid,sid,limit)).fetchall():
            d=dict(r); d["items"]=json.loads(d["items"]); res.append(d)
        return res
def stats_today(sid):
    with db() as c: return dict(c.execute("SELECT COUNT(*) as orders_count,COALESCE(SUM(total_price+delivery_fee),0) as revenue,COUNT(DISTINCT customer_id) as unique_customers FROM orders WHERE shop_id=? AND date(created_at)=date('now') AND status!='bekor'",(sid,)).fetchone())
def stats_period(sid,days=7):
    with db() as c: return [dict(r) for r in c.execute("SELECT date(created_at) as day,COUNT(*) as orders,COALESCE(SUM(total_price+delivery_fee),0) as revenue FROM orders WHERE shop_id=? AND created_at>=date('now',?) AND status!='bekor' GROUP BY date(created_at) ORDER BY day",(sid,f"-{days} days")).fetchall()]
def top_products(sid,limit=5):
    with db() as c: rows=c.execute("SELECT items FROM orders WHERE shop_id=? AND status!='bekor'",(sid,)).fetchall()
    counts={}
    for r in rows:
        for item in json.loads(r["items"]): n=item.get("name","?"); counts[n]=counts.get(n,0)+item.get("qty",1)
    return sorted(counts.items(),key=lambda x:x[1],reverse=True)[:limit]

# ── Helpers ──
def fmt(n): return f"{n:,} som".replace(",", " ")
def cart_total(cart): return sum(v["price"]*v["qty"] for v in cart.values())
def cart_text(cart):
    if not cart: return "🛒 Savat bosh"
    t="🛒 *Savat:*\n\n"
    for v in cart.values(): t+=f"• {v['name']} x{v['qty']} = {fmt(v['price']*v['qty'])}\n"
    return t+f"\n💰 *Jami: {fmt(cart_total(cart))}*"
def order_text(order,admin=True):
    e=STATUS_EMOJI.get(order["status"],"📦"); t=f"{e} *Buyurtma #{order['id']}*\n📅 {order['created_at'][:16]}\n\n🛒 *Tarkib:*\n"
    for item in order["items"]: t+=f"  • {item.get('name','?')} x{item.get('qty',1)} = {fmt(item.get('price',0)*item.get('qty',1))}\n"
    t+=f"\n💰 Mahsulotlar: *{fmt(order['total_price'])}*\n"
    if order.get("delivery_fee",0)>0: t+=f"🚗 Yetkazib berish: *{fmt(order['delivery_fee'])}*\n💳 Jami: *{fmt(order['total_price']+order['delivery_fee'])}*\n"
    t+=f"\n💳 Tolov: *{TOLOV.get(order.get('tolov_usuli','naqd'),'Naqd')}*\n"
    if order.get("address"): t+=f"📍 Manzil: {order['address']}\n"
    if order.get("phone"): t+=f"📞 Telefon: {order['phone']}\n"
    if admin and order.get("first_name"): t+=f"\n👤 Xaridor: {order['first_name']}"+(" (@"+order['username']+")" if order.get('username') else "")
    return t
def report_today(sid):
    s=stats_today(sid); return f"📊 *Bugungi hisobot*\n\n🛒 Buyurtmalar: *{s['orders_count']} ta*\n💰 Daromad: *{fmt(s['revenue'])}*\n👥 Xaridorlar: *{s['unique_customers']} ta*\n"
def report_week(sid):
    data=stats_period(sid,7); tot_o=sum(d["orders"] for d in data); tot_r=sum(d["revenue"] for d in data)
    t="📈 *Haftalik hisobot*\n\n"
    if not data: return t+"Hali buyurtmalar yoq."
    mx=max(d["revenue"] for d in data) or 1
    for d in data:
        bar="█"*int(d["revenue"]/mx*8)+"░"*(8-int(d["revenue"]/mx*8)); t+=f"`{d['day'][-5:]}` {bar} {fmt(d['revenue'])}\n"
    t+=f"\n📦 Jami: *{tot_o} ta* | 💰 *{fmt(tot_r)}*\n"
    tp=top_products(sid,3)
    if tp: t+="\n🏆 *Top:*\n"+"".join(f"{i}. {n} — {q} ta\n" for i,(n,q) in enumerate(tp,1))
    return t

# ── Keyboards ──
def adm_kb(): return ReplyKeyboardMarkup([["📦 Mahsulotlar","🛒 Buyurtmalar"],["📊 Hisobot","👥 Xaridorlar"],["⚙️ Sozlamalar","📢 Xabar yuborish"]],resize_keyboard=True)
def cust_kb(): return ReplyKeyboardMarkup([["🛍 Katalog","🛒 Savatim"],["📋 Buyurtmalarim","📞 Boglanish"],["ℹ️ Dokon haqida"]],resize_keyboard=True)
def prod_menu_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("➕ Mahsulot qoshish",callback_data="prod:add")],[InlineKeyboardButton("📋 Royxat",callback_data="prod:list")]])
def prod_act_kb(pid,stock): return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sotuvdan olish" if stock else "✅ Sotuvga chiqarish",callback_data=f"prod:toggle:{pid}")],[InlineKeyboardButton("🗑 Ochirish",callback_data=f"prod:del:{pid}")],[InlineKeyboardButton("◀️ Orqaga",callback_data="prod:list")]])
def ord_status_kb(oid,cur): 
    btns=[[InlineKeyboardButton(f"{STATUS_EMOJI[s]} {STATUS_TEXT[s]}",callback_data=f"order:status:{oid}:{s}")] for s in ["qabul","tayyorlanmoqda","yetkazilmoqda","yetkazildi","bekor"] if s!=cur]
    btns.append([InlineKeyboardButton("◀️ Orqaga",callback_data="orders:all")]); return InlineKeyboardMarkup(btns)
def catalog_kb(cats): return InlineKeyboardMarkup([[InlineKeyboardButton(f"{c['emoji']} {c['name']}",callback_data=f"cat:browse:{c['id']}")] for c in cats])
def prods_kb(prods,cart):
    btns=[]
    for p in prods:
        qty=cart.get(str(p["id"]),{}).get("qty",0); lbl=f"{'✅ ' if qty else ''}{p['name']} — {p['price']:,} som"; btns.append([InlineKeyboardButton(lbl,callback_data=f"prod:view_c:{p['id']}")])
    btns.append([InlineKeyboardButton("🛒 Savatim",callback_data="cart:view")]); btns.append([InlineKeyboardButton("◀️ Kategoriyalar",callback_data="cat:back")]); return InlineKeyboardMarkup(btns)
def prod_kb(pid,n=0):
    if n>0: return InlineKeyboardMarkup([[InlineKeyboardButton("➖",callback_data=f"cart:minus:{pid}"),InlineKeyboardButton(f"🛒 {n} ta",callback_data="cart:view"),InlineKeyboardButton("➕",callback_data=f"cart:plus:{pid}")],[InlineKeyboardButton("◀️ Orqaga",callback_data="cat:back")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Savatga qoshish",callback_data=f"cart:add:{pid}")],[InlineKeyboardButton("◀️ Orqaga",callback_data="cat:back")]])
def cart_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Buyurtma berish",callback_data="order:checkout")],[InlineKeyboardButton("🗑 Tozalash",callback_data="cart:clear")],[InlineKeyboardButton("◀️ Katalog",callback_data="cat:back")]])
def pay_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("💵 Naqd",callback_data="pay:naqd")],[InlineKeyboardButton("📱 Payme",callback_data="pay:payme")],[InlineKeyboardButton("📲 Click",callback_data="pay:click")]])
def confirm_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash",callback_data="order:confirm"),InlineKeyboardButton("❌ Bekor",callback_data="order:cancel")]])
def phone_kb(): return ReplyKeyboardMarkup([[KeyboardButton("📞 Telefon ulashish",request_contact=True)],[KeyboardButton("❌ Bekor")]],resize_keyboard=True,one_time_keyboard=True)
def loc_kb(): return ReplyKeyboardMarkup([[KeyboardButton("📍 Manzil yuborish",request_location=True)],[KeyboardButton("✍️ Manzil yozaman")],[KeyboardButton("❌ Bekor")]],resize_keyboard=True,one_time_keyboard=True)
def settings_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Nom",callback_data="settings:name")],[InlineKeyboardButton("📞 Telefon",callback_data="settings:phone")],[InlineKeyboardButton("📍 Manzil",callback_data="settings:address")],[InlineKeyboardButton("🚗 Yetkazib berish narxi",callback_data="settings:fee")]])
def reports_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("📅 Bugun",callback_data="report:today")],[InlineKeyboardButton("📆 Hafta",callback_data="report:week")]])
def orders_filter_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🆕 Yangi",callback_data="orders:yangi")],[InlineKeyboardButton("👨‍🍳 Tayyorlanmoqda",callback_data="orders:tayyorlanmoqda")],[InlineKeyboardButton("✅ Hammasi",callback_data="orders:all")]])

# ══════════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════════

async def cmd_start(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    usr=u.effective_user
    if is_admin(usr.id):
        shop=get_shop(usr.id)
        if not shop:
            await u.message.reply_text("🏪 *Xush kelibsiz!*\n\nDokon nomini kiriting:",parse_mode=ParseMode.MARKDOWN); return SETUP_NAME
        await u.message.reply_text(f"👋 *{shop['name']}* — Admin paneli",parse_mode=ParseMode.MARKDOWN,reply_markup=adm_kb()); return ConversationHandler.END
    else:
        upsert_customer(usr.id,usr.username,usr.first_name)
        shop=get_first_shop()
        if not shop: await u.message.reply_text("❗️ Dokon hali ochilmagan."); return ConversationHandler.END
        ctx.user_data["shop_id"]=shop["id"]
        await u.message.reply_text(f"👋 *{shop['name']}* ga xush kelibsiz!\n\nKatalogdan mahsulot tanlang.",parse_mode=ParseMode.MARKDOWN,reply_markup=cust_kb()); return ConversationHandler.END

async def setup_name(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    name=u.message.text.strip()
    if len(name)<2: await u.message.reply_text("❗️ Kamida 2 harf."); return SETUP_NAME
    create_shop(u.effective_user.id,name)
    await u.message.reply_text(f"✅ *{name}* yaratildi!",parse_mode=ParseMode.MARKDOWN,reply_markup=adm_kb()); return ConversationHandler.END

async def cmd_cancel(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    kb=adm_kb() if is_admin(u.effective_user.id) else cust_kb()
    await u.message.reply_text("❌ Bekor.",reply_markup=kb); return ConversationHandler.END

# Admin text
async def handle_text(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    t=u.message.text; uid=u.effective_user.id
    if is_admin(uid):
        if t=="📦 Mahsulotlar": await u.message.reply_text("📦 *Mahsulotlar*",parse_mode=ParseMode.MARKDOWN,reply_markup=prod_menu_kb())
        elif t=="🛒 Buyurtmalar":
            shop=get_shop(uid); n=len(get_orders(shop["id"],status="yangi")) if shop else 0
            await u.message.reply_text(f"🛒 *Buyurtmalar*\n🆕 Yangi: *{n} ta*",parse_mode=ParseMode.MARKDOWN,reply_markup=orders_filter_kb())
        elif t=="📊 Hisobot": await u.message.reply_text("📊 *Hisobotlar*",parse_mode=ParseMode.MARKDOWN,reply_markup=reports_kb())
        elif t=="⚙️ Sozlamalar":
            shop=get_shop(uid); s=get_settings(uid) if shop else {}; fee=s.get("fee",DEFAULT_FEE)
            if shop: await u.message.reply_text(f"⚙️ *Sozlamalar*\n\n🏪 Nom: *{shop['name']}*\n📞 Tel: *{shop.get('phone') or 'kiritilmagan'}*\n📍 Manzil: *{shop.get('address') or 'kiritilmagan'}*\n🚗 Yetkazib berish: *{fmt(fee)}*",parse_mode=ParseMode.MARKDOWN,reply_markup=settings_kb())
        elif t=="👥 Xaridorlar":
            shop=get_shop(uid)
            if shop:
                custs=get_all_customers(shop["id"])
                if not custs: await u.message.reply_text("👥 Hali xaridorlar yoq."); return
                text=f"👥 *Xaridorlar ({len(custs)} ta):*\n\n"
                for i,c in enumerate(custs[:20],1): text+=f"{i}. *{c.get('first_name','Mehmon')}*{' @'+c['username'] if c.get('username') else ''} — {c['total_orders']} buyurtma\n"
                await u.message.reply_text(text,parse_mode=ParseMode.MARKDOWN)
    else:
        if t=="🛍 Katalog":
            sid=ctx.user_data.get("shop_id") or (get_first_shop() or {}).get("id")
            if not sid: return
            cats=get_categories(sid)
            if not cats: await u.message.reply_text("📭 Mahsulotlar yoq."); return
            await u.message.reply_text("📂 *Kategoriyani tanlang:*",parse_mode=ParseMode.MARKDOWN,reply_markup=catalog_kb(cats))
        elif t=="🛒 Savatim":
            cart=ctx.user_data.get("cart",{}); text=cart_text(cart)
            sid=ctx.user_data.get("shop_id")
            if sid and cart:
                shop=get_shop_by_id(sid); s=get_settings(shop["owner_id"]) if shop else {}; fee=s.get("fee",DEFAULT_FEE)
                text+=f"\n🚗 Yetkazib berish: *{fmt(fee)}*\n💳 Umumiy: *{fmt(cart_total(cart)+fee)}*"
            await u.message.reply_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=cart_kb() if cart else None)
        elif t=="📋 Buyurtmalarim":
            cust=get_customer(u.effective_user.id); shop=get_first_shop()
            if not cust or not shop: await u.message.reply_text("Hali buyurtmalar yoq."); return
            ords=get_customer_orders(cust["id"],shop["id"])
            if not ords: await u.message.reply_text("📭 Hali buyurtmalar yoq.",reply_markup=cust_kb()); return
            text=f"📋 *Buyurtmalar ({len(ords)} ta):*\n\n"
            for o in ords[:5]: text+=f"{STATUS_EMOJI.get(o['status'],'📦')} #{o['id']} — {fmt(o['total_price'])} — {o['created_at'][:10]}\n"
            await u.message.reply_text(text,parse_mode=ParseMode.MARKDOWN)
        elif t=="📞 Boglanish":
            shop=get_first_shop()
            if shop: await u.message.reply_text(f"📞 *Boglanish*\n\n🏪 {shop['name']}\n📞 {shop.get('phone') or 'kiritilmagan'}",parse_mode=ParseMode.MARKDOWN)
        elif t=="ℹ️ Dokon haqida":
            shop=get_first_shop()
            if shop:
                s=get_settings(shop["owner_id"]); fee=s.get("fee",DEFAULT_FEE)
                await u.message.reply_text(f"🏪 *{shop['name']}*\n\n📞 Tel: {shop.get('phone') or 'kiritilmagan'}\n📍 Manzil: {shop.get('address') or 'kiritilmagan'}\n🚗 Yetkazib berish: {fmt(fee)}",parse_mode=ParseMode.MARKDOWN)

# Callbacks
async def handle_cb(u:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; d=q.data
    # Admin
    if d=="prod:list":
        await q.answer(); shop=get_shop(u.effective_user.id)
        if not shop: return
        prods=get_products(shop["id"],stock_only=False)
        if not prods: await q.edit_message_text("📭 Mahsulotlar yoq.",reply_markup=prod_menu_kb()); return
        btns=[[InlineKeyboardButton(f"{'✅' if p['in_stock'] else '❌'} {p['name']} — {p['price']:,} som",callback_data=f"prod:view:{p['id']}")] for p in prods]
        btns.append([InlineKeyboardButton("➕ Qoshish",callback_data="prod:add")])
        await q.edit_message_text(f"📦 *{len(prods)} ta mahsulot:*",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith("prod:view:") and "view_c" not in d:
        await q.answer(); pid=int(d.split(":")[2]); p=get_product(pid)
        if not p: return
        text=f"📦 *{p['name']}*\n💰 {p['price']:,} som\n{'✅ Sotuvda' if p['in_stock'] else '❌ Sotuvda yoq'}"
        if p.get("description"): text+=f"\n📄 {p['description']}"
        if p.get("photo_id"):
            try: await q.message.reply_photo(photo=p["photo_id"],caption=text,parse_mode=ParseMode.MARKDOWN,reply_markup=prod_act_kb(pid,bool(p["in_stock"]))); return
            except: pass
        await q.edit_message_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=prod_act_kb(pid,bool(p["in_stock"])))
    elif d=="prod:add":
        await q.answer(); await q.edit_message_text("📝 Mahsulot nomini kiriting:"); return ADD_PROD_NAME
    elif d.startswith("prod:toggle:"):
        pid=int(d.split(":")[2]); toggle_stock(pid); p=get_product(pid)
        await q.answer("✅ Sotuvga chiqarildi" if p["in_stock"] else "❌ Sotuvdan olindi",show_alert=True)
        await q.edit_message_text(f"📦 *{p['name']}*\n💰 {p['price']:,} som\n{'✅ Sotuvda' if p['in_stock'] else '❌ Sotuvda yoq'}",parse_mode=ParseMode.MARKDOWN,reply_markup=prod_act_kb(pid,bool(p["in_stock"])))
    elif d.startswith("prod:del:"):
        await q.answer(); pid=int(d.split(":")[2]); p=get_product(pid); del_product(pid)
        await q.edit_message_text(f"🗑 *{p['name']}* ochirildi.",parse_mode=ParseMode.MARKDOWN,reply_markup=prod_menu_kb())
    elif d.startswith("orders:"):
        await q.answer(); shop=get_shop(u.effective_user.id)
        if not shop: return
        if d=="orders:back": await q.edit_message_text("🛒 *Buyurtmalar*",parse_mode=ParseMode.MARKDOWN,reply_markup=orders_filter_kb()); return
        st=None if d=="orders:all" else d.split(":")[1]
        ords=get_orders(shop["id"],status=st)
        if not ords: await q.edit_message_text("📭 Buyurtmalar yoq.",reply_markup=orders_filter_kb()); return
        btns=[[InlineKeyboardButton(f"{STATUS_EMOJI.get(o['status'],'📦')} #{o['id']} — {o['total_price']:,} som ({o.get('first_name','?')})",callback_data=f"order:view:{o['id']}")] for o in ords]
        btns.append([InlineKeyboardButton("◀️ Orqaga",callback_data="orders:back")])
        await q.edit_message_text(f"📋 *{len(ords)} ta:*",parse_mode=ParseMode.MARKDOWN,reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith("order:view:"):
        await q.answer(); oid=int(d.split(":")[2]); order=get_order(oid)
        if not order: return
        await q.edit_message_text(order_text(order,admin=True),parse_mode=ParseMode.MARKDOWN,reply_markup=ord_status_kb(oid,order["status"]))
    elif d.startswith("order:status:"):
        await q.answer(); _,_,oid,new_st=d.split(":"); oid=int(oid); order=get_order(oid)
        update_order_status(oid,new_st); await q.answer(f"{STATUS_EMOJI[new_st]} {STATUS_TEXT[new_st]}",show_alert=True)
        try: await ctx.bot.send_message(chat_id=order["customer_user_id"],text=f"📦 *Buyurtma #{oid} holati:*\n{STATUS_EMOJI[new_st]} {STATUS_TEXT[new_st]}",parse_mode=ParseMode.MARKDOWN)
        except: pass
        updated=get_order(oid); await q.edit_message_text(order_text(updated,admin=True),parse_mode=ParseMode.MARKDOWN,reply_markup=ord_status_kb(oid,new_st))
    elif d.startswith("report:"):
        await q.answer(); shop=get_shop(u.effective_user.id)
        if not shop: return
        t=report_today(shop["id"]) if d.split(":")[1]=="today" else report_week(shop["id"])
        await q.edit_message_text(t,parse_mode=ParseMode.MARKDOWN)
    elif d.startswith("settings:"):
        await q.answer(); field=d.split(":")[1]
        ctx.user_data["settings_field"]=field
        prompts={"name":"🏪 Yangi dokon nomi:","phone":"📞 Telefon:","address":"📍 Manzil:","fee":"🚗 Yetkazib berish narxi (raqam):"}
        await q.edit_message_text(prompts.get(field,"Yangi qiymat:")); return SETTINGS_VALUE
    # Customer
    elif d.startswith("cat:browse:"):
        await q.answer(); cat_id=int(d.split(":")[2])
        sid=ctx.user_data.get("shop_id") or (get_first_shop() or {}).get("id")
        if not sid: return
        ctx.user_data["shop_id"]=sid
        prods=get_products(sid,cat_id=cat_id); cart=ctx.user_data.get("cart",{})
        if not prods: await q.edit_message_text("📭 Bu kategoriyada mahsulotlar yoq."); return
        await q.edit_message_text(f"📦 *{len(prods)} ta mahsulot:*",parse_mode=ParseMode.MARKDOWN,reply_markup=prods_kb(prods,cart))
    elif d.startswith("prod:view_c:"):
        await q.answer(); pid=int(d.split(":")[2]); p=get_product(pid)
        if not p: return
        cart=ctx.user_data.get("cart",{}); n=cart.get(str(pid),{}).get("qty",0)
        text=f"📦 *{p['name']}*\n\n💰 Narx: *{fmt(p['price'])}*"
        if p.get("description"): text+=f"\n\n{p['description']}"
        if p.get("photo_id"):
            try: await q.message.reply_photo(photo=p["photo_id"],caption=text,parse_mode=ParseMode.MARKDOWN,reply_markup=prod_kb(pid,n)); return
            except: pass
        await q.edit_message_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=prod_kb(pid,n))
    elif d.startswith("cart:add:"):
        pid=str(d.split(":")[2]); p=get_product(int(pid)); cart=ctx.user_data.get("cart",{})
        if not p: await q.answer(); return
        cart[pid]={"name":p["name"],"price":p["price"],"qty":cart[pid]["qty"]+1} if pid in cart else {"name":p["name"],"price":p["price"],"qty":1}
        ctx.user_data["cart"]=cart; await q.answer("✅ Savatga qoshildi!")
        await q.edit_message_reply_markup(reply_markup=prod_kb(int(pid),cart[pid]["qty"]))
    elif d.startswith("cart:plus:"):
        pid=str(d.split(":")[2]); p=get_product(int(pid)); cart=ctx.user_data.get("cart",{})
        cart[pid]={"name":p["name"],"price":p["price"],"qty":cart[pid]["qty"]+1} if pid in cart else {"name":p["name"],"price":p["price"],"qty":1}
        ctx.user_data["cart"]=cart; await q.answer()
        await q.edit_message_reply_markup(reply_markup=prod_kb(int(pid),cart[pid]["qty"]))
    elif d.startswith("cart:minus:"):
        pid=str(d.split(":")[2]); cart=ctx.user_data.get("cart",{})
        if pid in cart:
            cart[pid]["qty"]-=1
            if cart[pid]["qty"]<=0: del cart[pid]
        ctx.user_data["cart"]=cart; n=cart.get(pid,{}).get("qty",0); await q.answer()
        await q.edit_message_reply_markup(reply_markup=prod_kb(int(pid),n))
    elif d=="cart:view":
        await q.answer(); cart=ctx.user_data.get("cart",{}); text=cart_text(cart)
        sid=ctx.user_data.get("shop_id")
        if sid and cart:
            shop=get_shop_by_id(sid); s=get_settings(shop["owner_id"]) if shop else {}; fee=s.get("fee",DEFAULT_FEE)
            text+=f"\n🚗 Yetkazib berish: *{fmt(fee)}*\n💳 Umumiy: *{fmt(cart_total(cart)+fee)}*"
        await q.edit_message_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=cart_kb() if cart else None)
    elif d=="cart:clear":
        await q.answer("🗑 Savat tozalandi"); ctx.user_data["cart"]={}; await q.edit_message_text("🛒 Savat boshlatildi.")
    elif d=="cat:back":
        await q.answer(); sid=ctx.user_data.get("shop_id") or (get_first_shop() or {}).get("id")
        cats=get_categories(sid) if sid else []
        if cats: await q.edit_message_text("📂 *Kategoriyani tanlang:*",parse_mode=ParseMode.MARKDOWN,reply_markup=catalog_kb(cats))

# Conversations
async def add_prod_name(u,ctx): ctx.user_data["np"]={"name":u.message.text.strip()}; await u.message.reply_text("💰 Narxini kiriting (raqam):"); return ADD_PROD_PRICE
async def add_prod_price(u,ctx):
    try:
        price=int(u.message.text.replace(" ","").replace(",",""))
        ctx.user_data["np"]["price"]=price; await u.message.reply_text("📄 Tavsif kiriting yoki /skip:"); return ADD_PROD_DESC
    except: await u.message.reply_text("❗️ Faqat raqam:"); return ADD_PROD_PRICE
async def add_prod_desc(u,ctx):
    if u.message.text!="/skip": ctx.user_data["np"]["description"]=u.message.text.strip()
    await u.message.reply_text("🖼 Rasm yuboring yoki /skip:"); return ADD_PROD_PHOTO
async def add_prod_photo(u,ctx):
    if u.message.photo: ctx.user_data["np"]["photo_id"]=u.message.photo[-1].file_id
    shop=get_shop(u.effective_user.id); np=ctx.user_data.pop("np",{})
    add_product(shop["id"],np["name"],np["price"],desc=np.get("description"),photo_id=np.get("photo_id"))
    await u.message.reply_text(f"✅ *{np['name']}* qoshildi!\n💰 {np['price']:,} som",parse_mode=ParseMode.MARKDOWN,reply_markup=adm_kb()); return ConversationHandler.END
async def settings_save(u,ctx):
    field=ctx.user_data.get("settings_field"); val=u.message.text.strip()
    if field in ("name","phone","address"): update_shop(u.effective_user.id,**{field:val})
    elif field=="fee":
        try:
            fee=int(val.replace(" ","").replace(",","")); s=get_settings(u.effective_user.id); s["fee"]=fee; save_settings(u.effective_user.id,s)
        except: await u.message.reply_text("❗️ Faqat raqam:"); return SETTINGS_VALUE
    await u.message.reply_text("✅ Saqlandi!",reply_markup=adm_kb()); return ConversationHandler.END
async def broadcast_start(u,ctx): await u.message.reply_text("📢 Xabar kiriting:"); return BROADCAST_TEXT
async def broadcast_send(u,ctx):
    shop=get_shop(u.effective_user.id)
    if not shop: return ConversationHandler.END
    custs=get_all_customers(shop["id"]); sent=0
    for c in custs:
        try: await ctx.bot.send_message(c["user_id"],f"📢 *{shop['name']}*\n\n{u.message.text}",parse_mode=ParseMode.MARKDOWN); sent+=1
        except: pass
    await u.message.reply_text(f"✅ *{sent} ta* xaridorga yuborildi!",parse_mode=ParseMode.MARKDOWN,reply_markup=adm_kb()); return ConversationHandler.END
async def checkout_start(u,ctx):
    q=u.callback_query; await q.answer()
    if not ctx.user_data.get("cart"): await q.edit_message_text("🛒 Savat bosh!"); return ConversationHandler.END
    await q.message.reply_text("📞 Telefon raqamingizni yuboring:",reply_markup=phone_kb()); return ORDER_PHONE
async def order_get_phone(u,ctx):
    if u.message.contact: ctx.user_data["oPhone"]=u.message.contact.phone_number
    elif u.message.text!="❌ Bekor": ctx.user_data["oPhone"]=u.message.text.strip()
    else: await u.message.reply_text("❌ Bekor.",reply_markup=cust_kb()); return ConversationHandler.END
    await u.message.reply_text("📍 Manzilingizni yuboring yoki yozing:",reply_markup=loc_kb()); return ORDER_ADDRESS
async def order_get_address(u,ctx):
    if u.message.text=="❌ Bekor": await u.message.reply_text("❌ Bekor.",reply_markup=cust_kb()); return ConversationHandler.END
    if u.message.location: ctx.user_data["oAddr"]=f"📍 {u.message.location.latitude:.4f}, {u.message.location.longitude:.4f}"
    elif u.message.text!="✍️ Manzil yozaman": ctx.user_data["oAddr"]=u.message.text.strip()
    else: await u.message.reply_text("✍️ Manzil yozing:"); return ORDER_ADDRESS
    await u.message.reply_text("💳 Tolov usulini tanlang:",reply_markup=pay_kb()); return ORDER_PAYMENT
async def order_get_payment(u,ctx):
    q=u.callback_query; await q.answer(); pay=q.data.split(":")[1]; ctx.user_data["oPay"]=pay
    cart=ctx.user_data.get("cart",{}); sid=ctx.user_data.get("shop_id")
    shop=get_shop_by_id(sid) if sid else get_first_shop(); s=get_settings(shop["owner_id"]) if shop else {}; fee=s.get("fee",DEFAULT_FEE)
    text=f"📋 *Tasdiqlang:*\n\n{cart_text(cart)}\n\n📍 {ctx.user_data.get('oAddr')}\n📞 {ctx.user_data.get('oPhone')}\n💳 {TOLOV.get(pay,pay)}\n🚗 {fmt(fee)}\n💰 *Umumiy: {fmt(cart_total(cart)+fee)}*"
    await q.message.reply_text(text,parse_mode=ParseMode.MARKDOWN,reply_markup=confirm_kb()); return ORDER_CONFIRM
async def order_confirm(u,ctx):
    q=u.callback_query; await q.answer()
    if q.data=="order:cancel": await q.edit_message_text("❌ Bekor."); return ConversationHandler.END
    cart=ctx.user_data.get("cart",{}); sid=ctx.user_data.get("shop_id")
    shop=get_shop_by_id(sid) if sid else get_first_shop()
    if not shop: return ConversationHandler.END
    s=get_settings(shop["owner_id"]); fee=s.get("fee",DEFAULT_FEE); cust=get_customer(u.effective_user.id)
    items=[{"name":v["name"],"price":v["price"],"qty":v["qty"]} for v in cart.values()]
    oid=create_order(shop["id"],cust["id"],items,cart_total(cart),fee,ctx.user_data.get("oAddr",""),ctx.user_data.get("oPhone",""),ctx.user_data.get("oPay","naqd"))
    ctx.user_data["cart"]={}
    await q.edit_message_text(f"✅ *Buyurtma #{oid} qabul qilindi!*\n\nDokon tez orada boglanadi.",parse_mode=ParseMode.MARKDOWN,reply_markup=cust_kb())
    order=get_order(oid)
    try: await ctx.bot.send_message(chat_id=shop["owner_id"],text=f"🆕 *Yangi buyurtma!*\n\n{order_text(order,admin=True)}",parse_mode=ParseMode.MARKDOWN,reply_markup=ord_status_kb(oid,"yangi"))
    except: pass
    return ConversationHandler.END

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
def main():
    if not BOT_TOKEN: logger.error("❌ BOT_TOKEN topilmadi!"); return
    init_db()
    app=Application.builder().token(BOT_TOKEN).build()
    setup_conv=ConversationHandler(entry_points=[CommandHandler("start",cmd_start)],states={SETUP_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND,setup_name)]},fallbacks=[CommandHandler("cancel",cmd_cancel)])
    add_prod_conv=ConversationHandler(entry_points=[CallbackQueryHandler(handle_cb,pattern="^prod:add$")],states={ADD_PROD_NAME:[MessageHandler(filters.TEXT&~filters.COMMAND,add_prod_name)],ADD_PROD_PRICE:[MessageHandler(filters.TEXT&~filters.COMMAND,add_prod_price)],ADD_PROD_DESC:[MessageHandler(filters.TEXT|filters.COMMAND,add_prod_desc)],ADD_PROD_PHOTO:[MessageHandler(filters.PHOTO|filters.TEXT|filters.COMMAND,add_prod_photo)]},fallbacks=[CommandHandler("cancel",cmd_cancel)])
    order_conv=ConversationHandler(entry_points=[CallbackQueryHandler(checkout_start,pattern="^order:checkout$")],states={ORDER_PHONE:[MessageHandler(filters.CONTACT|(filters.TEXT&~filters.COMMAND),order_get_phone)],ORDER_ADDRESS:[MessageHandler(filters.LOCATION|(filters.TEXT&~filters.COMMAND),order_get_address)],ORDER_PAYMENT:[CallbackQueryHandler(order_get_payment,pattern="^pay:")],ORDER_CONFIRM:[CallbackQueryHandler(order_confirm,pattern="^order:(confirm|cancel)$")]},fallbacks=[CommandHandler("cancel",cmd_cancel)])
    settings_conv=ConversationHandler(entry_points=[CallbackQueryHandler(handle_cb,pattern="^settings:")],states={SETTINGS_VALUE:[MessageHandler(filters.TEXT&~filters.COMMAND,settings_save)]},fallbacks=[CommandHandler("cancel",cmd_cancel)])
    broadcast_conv=ConversationHandler(entry_points=[MessageHandler(filters.Regex("^📢 Xabar yuborish$"),broadcast_start)],states={BROADCAST_TEXT:[MessageHandler(filters.TEXT&~filters.COMMAND,broadcast_send)]},fallbacks=[CommandHandler("cancel",cmd_cancel)])
    for conv in [setup_conv,add_prod_conv,order_conv,settings_conv,broadcast_conv]: app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_cb))
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,handle_text))
    app.add_handler(CommandHandler("cancel",cmd_cancel))
    logger.info("🚀 Biznes Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=True)

if __name__=="__main__":
    main()
