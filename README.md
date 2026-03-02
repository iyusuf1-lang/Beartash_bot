# 🏪 Biznes Bot

Kichik do'konlar uchun Telegram bot — katalog, buyurtma, hisobot, broadcast.

## 🚀 Ishga tushirish

### 1. Bot tokeni olish
1. [@BotFather](https://t.me/BotFather) ga boring
2. `/newbot` buyrug'i bilan yangi bot yarating
3. Tokenni nusxalang

### 2. config.py da token o'rnating
```python
BOT_TOKEN = "1234567890:AAExxxxxxxxxxxxxxxxxxxxxxx"
```

### 3. Lokal ishga tushirish
```bash
pip install -r requirements.txt
python bot.py
```

### 4. Railway deploy
1. GitHub ga push qiling
2. [railway.app](https://railway.app) da yangi project oching
3. GitHub repo ulang
4. **Variables** ga `BOT_TOKEN` qo'shing
5. Deploy!

---

## 📱 Foydalanish

### 👨‍💼 Admin (Do'kon egasi)
1. `/start` → do'kon nomi kiriting
2. **📦 Mahsulotlar** → qo'shish, tahrirlash
3. **🛒 Buyurtmalar** → ko'rish, status o'zgartirish
4. **📊 Hisobot** → bugun/hafta/oy statistikasi
5. **📢 Xabar yuborish** → barcha xaridorlarga broadcast

### 👤 Xaridor
1. `/start` → do'kon sahifasi
2. **🛍 Katalog** → mahsulotlarni ko'rish
3. **🛒 Savatim** → tanlangan mahsulotlar
4. Buyurtma → telefon + manzil + to'lov
5. **📋 Buyurtmalarim** → tarix va holat

---

## 📁 Fayl strukturasi

```
biznes_bot/
├── bot.py              ← Asosiy fayl
├── config.py           ← Sozlamalar
├── database.py         ← SQLite
├── requirements.txt
├── railway.toml
├── handlers/
│   ├── admin.py        ← Admin logika
│   └── customer.py     ← Xaridor logika
├── keyboards/
│   ├── admin_kb.py     ← Admin tugmalar
│   └── customer_kb.py  ← Xaridor tugmalar
└── utils/
    └── reports.py      ← Hisobotlar
```

---

## ⚙️ Sozlamalar

Admin `/start` bosib do'kon yaratgandan keyin:
- **⚙️ Sozlamalar** → nom, telefon, manzil, ish vaqti
- Yetkazib berish narxini o'zgartirish: `config.py` → `DEFAULT_SETTINGS`

## 🛠 Kengaytirish (v2.0)

- [ ] PayMe/Click integratsiya
- [ ] Ko'p do'kon (SaaS model)
- [ ] Web admin panel
- [ ] Excel hisobot export
