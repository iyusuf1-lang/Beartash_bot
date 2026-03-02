import os

# ══════════════════════════════════════════════
# BIZNES BOT — Konfiguratsiya
# ══════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DB_PATH   = os.getenv("DB_PATH", "biznes.db")

# Do'kon sozlamalari (admin /settings orqali o'zgartira oladi)
DEFAULT_SETTINGS = {
    "ish_vaqti_bosh":       "09:00",
    "ish_vaqti_oxir":       "22:00",
    "yetkazib_berish":      True,
    "yetkazib_berish_narxi": 15_000,
    "min_buyurtma":          50_000,
    "til":                  "uz",
    "valyuta":              "so'm",
}

# Buyurtma statuslari
class Status:
    YANGI       = "yangi"
    QABUL       = "qabul"
    TAYYORLANMOQDA = "tayyorlanmoqda"
    YETKAZILMOQDA  = "yetkazilmoqda"
    YETKAZILDI  = "yetkazildi"
    BEKOR       = "bekor"

STATUS_EMOJI = {
    Status.YANGI:          "🆕",
    Status.QABUL:          "✅",
    Status.TAYYORLANMOQDA: "👨‍🍳",
    Status.YETKAZILMOQDA:  "🚗",
    Status.YETKAZILDI:     "🎉",
    Status.BEKOR:          "❌",
}

STATUS_TEXT = {
    Status.YANGI:          "Yangi buyurtma",
    Status.QABUL:          "Qabul qilindi",
    Status.TAYYORLANMOQDA: "Tayyorlanmoqda",
    Status.YETKAZILMOQDA:  "Yetkazilmoqda",
    Status.YETKAZILDI:     "Yetkazildi",
    Status.BEKOR:          "Bekor qilindi",
}

# To'lov usullari
TOLOV_USULLARI = {
    "naqd":  "💵 Naqd pul",
    "payme": "📱 Payme",
    "click": "📲 Click",
}

# Kategoriyalar
DEFAULT_KATEGORIYALAR = [
    "🍕 Ovqatlar",
    "🥤 Ichimliklar",
    "🍰 Shirinliklar",
    "📦 Boshqa",
]
