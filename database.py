import sqlite3
import json
from contextlib import contextmanager
from config import DB_PATH

# ══════════════════════════════════════════════
# DATABASE — Barcha operatsiyalar
# ══════════════════════════════════════════════

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        -- Do'kon
        CREATE TABLE IF NOT EXISTS shop (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id     INTEGER UNIQUE NOT NULL,
            name         TEXT NOT NULL DEFAULT 'Mening Do''konim',
            phone        TEXT,
            address      TEXT,
            description  TEXT,
            logo_url     TEXT,
            is_active    INTEGER DEFAULT 1,
            settings     TEXT DEFAULT '{}',
            created_at   TEXT DEFAULT (datetime('now'))
        );

        -- Kategoriyalar
        CREATE TABLE IF NOT EXISTS categories (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id   INTEGER NOT NULL,
            name      TEXT NOT NULL,
            emoji     TEXT DEFAULT '📦',
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (shop_id) REFERENCES shop(id)
        );

        -- Mahsulotlar
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id     INTEGER NOT NULL,
            category_id INTEGER,
            name        TEXT NOT NULL,
            description TEXT,
            price       INTEGER NOT NULL,
            photo_url   TEXT,
            in_stock    INTEGER DEFAULT 1,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (shop_id) REFERENCES shop(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        -- Xaridorlar
        CREATE TABLE IF NOT EXISTS customers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER UNIQUE NOT NULL,
            username      TEXT,
            first_name    TEXT,
            phone         TEXT,
            address       TEXT,
            total_orders  INTEGER DEFAULT 0,
            total_spent   INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        -- Buyurtmalar
        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id      INTEGER NOT NULL,
            customer_id  INTEGER NOT NULL,
            items        TEXT NOT NULL DEFAULT '[]',
            total_price  INTEGER NOT NULL DEFAULT 0,
            delivery_fee INTEGER DEFAULT 0,
            address      TEXT,
            phone        TEXT,
            tolov_usuli  TEXT DEFAULT 'naqd',
            status       TEXT DEFAULT 'yangi',
            note         TEXT,
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (shop_id) REFERENCES shop(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        -- Adminlar (ko'p do'kon uchun)
        CREATE TABLE IF NOT EXISTS admins (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id  INTEGER NOT NULL,
            user_id  INTEGER NOT NULL,
            role     TEXT DEFAULT 'admin',
            UNIQUE(shop_id, user_id),
            FOREIGN KEY (shop_id) REFERENCES shop(id)
        );
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ──────────────────────────────────────────────
# SHOP
# ──────────────────────────────────────────────

def get_shop(owner_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM shop WHERE owner_id=?", (owner_id,)).fetchone()
        return dict(row) if row else None

def get_shop_by_id(shop_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM shop WHERE id=?", (shop_id,)).fetchone()
        return dict(row) if row else None

def create_shop(owner_id: int, name: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO shop (owner_id, name) VALUES (?, ?)",
            (owner_id, name)
        )
        shop_id = cur.lastrowid
        # Default kategoriya qo'shish
        conn.execute(
            "INSERT INTO categories (shop_id, name, emoji) VALUES (?, ?, ?)",
            (shop_id, "Asosiy", "📦")
        )
        return shop_id

def update_shop(owner_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [owner_id]
    with get_db() as conn:
        conn.execute(f"UPDATE shop SET {fields} WHERE owner_id=?", values)

def get_shop_settings(owner_id: int) -> dict:
    shop = get_shop(owner_id)
    if not shop:
        return {}
    try:
        return json.loads(shop["settings"] or "{}")
    except Exception:
        return {}

def save_shop_settings(owner_id: int, settings: dict):
    with get_db() as conn:
        conn.execute(
            "UPDATE shop SET settings=? WHERE owner_id=?",
            (json.dumps(settings, ensure_ascii=False), owner_id)
        )

def is_admin(user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM shop WHERE owner_id=?", (user_id,)).fetchone()
        return row is not None

# ──────────────────────────────────────────────
# CATEGORIES
# ──────────────────────────────────────────────

def get_categories(shop_id: int) -> list:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM categories WHERE shop_id=? ORDER BY sort_order, id",
            (shop_id,)
        ).fetchall()]

def add_category(shop_id: int, name: str, emoji: str = "📦") -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO categories (shop_id, name, emoji) VALUES (?, ?, ?)",
            (shop_id, name, emoji)
        )
        return cur.lastrowid

def delete_category(category_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))

# ──────────────────────────────────────────────
# PRODUCTS
# ──────────────────────────────────────────────

def get_products(shop_id: int, category_id: int = None, in_stock_only: bool = True) -> list:
    with get_db() as conn:
        q = "SELECT p.*, c.name as cat_name, c.emoji as cat_emoji FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.shop_id=?"
        params = [shop_id]
        if category_id:
            q += " AND p.category_id=?"
            params.append(category_id)
        if in_stock_only:
            q += " AND p.in_stock=1"
        q += " ORDER BY p.sort_order, p.id"
        return [dict(r) for r in conn.execute(q, params).fetchall()]

def get_product(product_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return dict(row) if row else None

def add_product(shop_id: int, name: str, price: int, category_id: int = None,
                description: str = None, photo_url: str = None) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO products (shop_id, category_id, name, price, description, photo_url) VALUES (?, ?, ?, ?, ?, ?)",
            (shop_id, category_id, name, price, description, photo_url)
        )
        return cur.lastrowid

def update_product(product_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [product_id]
    with get_db() as conn:
        conn.execute(f"UPDATE products SET {fields} WHERE id=?", values)

def delete_product(product_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))

def toggle_stock(product_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET in_stock = CASE WHEN in_stock=1 THEN 0 ELSE 1 END WHERE id=?",
            (product_id,)
        )

# ──────────────────────────────────────────────
# CUSTOMERS
# ──────────────────────────────────────────────

def get_customer(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customers WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def upsert_customer(user_id: int, username: str = None, first_name: str = None) -> dict:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO customers (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user_id, username or "", first_name or "Mehmon"))
    return get_customer(user_id)

def update_customer(user_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    with get_db() as conn:
        conn.execute(f"UPDATE customers SET {fields} WHERE user_id=?", values)

def get_all_customers(shop_id: int) -> list:
    with get_db() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT c.* FROM customers c
            INNER JOIN orders o ON o.customer_id=c.id
            WHERE o.shop_id=?
            GROUP BY c.id
            ORDER BY c.total_orders DESC
        """, (shop_id,)).fetchall()]

# ──────────────────────────────────────────────
# ORDERS
# ──────────────────────────────────────────────

def create_order(shop_id: int, customer_id: int, items: list,
                 total_price: int, delivery_fee: int, address: str,
                 phone: str, tolov_usuli: str, note: str = None) -> int:
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO orders (shop_id, customer_id, items, total_price, delivery_fee,
                                address, phone, tolov_usuli, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (shop_id, customer_id, json.dumps(items, ensure_ascii=False),
              total_price, delivery_fee, address, phone, tolov_usuli, note))
        order_id = cur.lastrowid
        # Xaridor statistikasini yangilash
        conn.execute("""
            UPDATE customers
            SET total_orders = total_orders + 1,
                total_spent  = total_spent + ?
            WHERE id=?
        """, (total_price + delivery_fee, customer_id))
        return order_id

def get_order(order_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("""
            SELECT o.*, c.first_name, c.username, c.user_id as customer_user_id
            FROM orders o
            LEFT JOIN customers c ON o.customer_id=c.id
            WHERE o.id=?
        """, (order_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d

def get_orders(shop_id: int, status: str = None, limit: int = 50) -> list:
    with get_db() as conn:
        q = """
            SELECT o.*, c.first_name, c.username
            FROM orders o
            LEFT JOIN customers c ON o.customer_id=c.id
            WHERE o.shop_id=?
        """
        params = [shop_id]
        if status:
            q += " AND o.status=?"
            params.append(status)
        q += " ORDER BY o.created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result

def update_order_status(order_id: int, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, order_id)
        )

def get_customer_orders(customer_id: int, shop_id: int, limit: int = 10) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM orders
            WHERE customer_id=? AND shop_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (customer_id, shop_id, limit)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result

# ──────────────────────────────────────────────
# STATISTIKA (hisobotlar uchun)
# ──────────────────────────────────────────────

def get_stats_today(shop_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as orders_count,
                COALESCE(SUM(total_price + delivery_fee), 0) as revenue,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM orders
            WHERE shop_id=?
              AND date(created_at)=date('now')
              AND status != 'bekor'
        """, (shop_id,)).fetchone()
        return dict(row)

def get_stats_period(shop_id: int, days: int = 7) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                date(created_at) as day,
                COUNT(*) as orders,
                COALESCE(SUM(total_price + delivery_fee), 0) as revenue
            FROM orders
            WHERE shop_id=?
              AND created_at >= date('now', ?)
              AND status != 'bekor'
            GROUP BY date(created_at)
            ORDER BY day
        """, (shop_id, f"-{days} days")).fetchall()
        return [dict(r) for r in rows]

def get_top_products(shop_id: int, limit: int = 5) -> list:
    """Eng ko'p sotilgan mahsulotlar"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM orders
            WHERE shop_id=? AND status != 'bekor'
        """, (shop_id,)).fetchall()

    counts = {}
    for row in rows:
        items = json.loads(row["items"])
        for item in items:
            name = item.get("name", "?")
            qty  = item.get("qty", 1)
            counts[name] = counts.get(name, 0) + qty

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:limit]
