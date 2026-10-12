import os
import sqlite3
import random
from contextlib import contextmanager
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ==============================
#            الإعدادات
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = 7555222167
OWNER_USERNAME = "w0_nv"
CHANNEL_USERNAME = "Ezxi2"
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}"

OWNER_POINTS = 99999999
WELCOME_POINTS = 3
REFERRAL_REWARD = 1
POINTS_COST = 1
GUESS_COST = 2
MIN_OUTPUT = 4
MAX_OUTPUT = 6
DB_PATH = "riko.sqlite3"

SCAM_FOOTER = "3 نيو + VPN لوس انجلس"

CATEGORIES = {
    "هيت":     {"names": ["هيت"],                                                "max_num": 10},
    "مضايقه":  {"names": ["مضايقه خيار اول", "مضايقه خيار ثاني", "مضايقه خيار ثالث"], "max_num": 7},
    "عنف":     {"names": ["عنف اول", "عنف ثاني", "دعوة عنف", "عرض عنف"],          "max_num": 7},
    "اباحي":   {"names": ["اباحي خيار اول", "اباحي خيار ثالث", "اباحي خيار رابع"], "max_num": 10},
    "مخدرات":  {"names": ["مخدرات اول", "مخدرات ثاني", "مخدرات ثالث"],            "max_num": 7},
    "سكام":    {"names": ["سكام اول", "سكام ثاني", "سكام ثالث", "سكام رابع"],     "max_num": 12},
    "سيلف":    {"names": ["سيلف"],                                               "max_num": 12},
    "سبام":    {"names": ["سبام"],                                               "max_num": 10},
}


# ==============================
#         قاعدة البيانات
# ==============================
@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            repairs INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER,
            created_at TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS referrals(
            invited_id INTEGER PRIMARY KEY,
            referrer_id INTEGER
        )""")
        con.execute("""
        INSERT INTO users(user_id, username, points, created_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            points=?
        """, (
            OWNER_ID, OWNER_USERNAME, OWNER_POINTS,
            datetime.now(timezone.utc).isoformat(), OWNER_POINTS
        ))


def register(user):
    with db() as con:
        old = con.execute(
            "SELECT user_id FROM users WHERE user_id=?", (user.id,)
        ).fetchone()

        if old is None:
            start_points = OWNER_POINTS if user.id == OWNER_ID else WELCOME_POINTS
            con.execute("""
            INSERT INTO users(user_id, username, points, created_at)
            VALUES(?, ?, ?, ?)
            """, (
                user.id, user.username, start_points,
                datetime.now(timezone.utc).isoformat()
            ))
        else:
            con.execute(
                "UPDATE users SET username=? WHERE user_id=?",
                (user.username, user.id)
            )


def get_user(user_id):
    with db() as con:
        return con.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)
        ).fetchone()


def get_referred_users(user_id, limit=15):
    with db() as con:
        return con.execute("""
            SELECT u.user_id, u.username, u.created_at
            FROM users u
            JOIN referrals r ON r.invited_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY u.created_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()


# ==============================
#            الواجهات
# ==============================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠️ تصليح الثغرات", callback_data="repair")],
        [InlineKeyboardButton("🔮 صنع ثغرة", callback_data="guess")],
        [
            InlineKeyboardButton("👤 حسابي", callback_data="account"),
            InlineKeyboardButton("🎁 الإحالات", callback_data="referrals"),
        ],
        [
            InlineKeyboardButton("📊 إحصائيات", callback_data="status"),
            InlineKeyboardButton("👨‍💻 المطوّر", url="https://t.me/w0_nv"),
        ],
        [InlineKeyboardButton("📢 قناة المطوّر", url=CHANNEL_LINK)],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
    ])


def guess_again_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 صنع مرة ثانية", callback_data="guess")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="home")],
    ])


# ==============================
#          توليد الناتج
# ==============================
def format_output(min_lines=MIN_OUTPUT, max_lines=MAX_OUTPUT):
    all_names = []
    for cat in CATEGORIES.values():
        for name in cat["names"]:
            all_names.append((name, cat["max_num"]))

    count = random.randint(min_lines, max_lines)

    out = []
    for _ in range(count):
        name, max_num = random.choice(all_names)
        num = random.randint(1, max_num)
        out.append(f"{num}{name}")
    return out


# ==============================
#      رسالة الترحيب الرئيسية
# ==============================
def welcome_text(user, points):
    name = user.first_name or "صديقي"
    return (
        f"🛡️ <b>RIKO SECURITY</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"👋 أهلاً بك <b>{name}</b>\n"
        f"💰 رصيدك الحالي: <b>{points:,}</b> نقطة\n"
        "━━━━━━━━━━━━━━━\n"
        "اختر خدمة من القائمة أدناه 👇"
    )


# ==============================
#         أمر /start
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    with db() as con:
        old = con.execute(
            "SELECT user_id FROM users WHERE user_id=?", (user.id,)
        ).fetchone()

    register(user)

    if old is None and context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            await _apply_referral(update, context, user, arg)

    u = get_user(user.id)
    await update.effective_message.reply_text(
        welcome_text(user, u["points"]),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


async def _apply_referral(update, context, user, arg):
    try:
        referrer = int(arg[4:])
    except ValueError:
        return

    if referrer == user.id:
        return

    with db() as con:
        exists = con.execute(
            "SELECT user_id FROM users WHERE user_id=?", (referrer,)
        ).fetchone()
        if not exists:
            return
        try:
            con.execute(
                "INSERT INTO referrals VALUES(?, ?)",
                (user.id, referrer)
            )
            con.execute(
                "UPDATE users SET referred_by=? WHERE user_id=?",
                (referrer, user.id)
            )
            con.execute(
                "UPDATE users SET points=points+?, referrals=referrals+1 WHERE user_id=?",
                (REFERRAL_REWARD, referrer)
            )
        except sqlite3.IntegrityError:
            return

    username = f"@{user.username}" if user.username else user.first_name

    try:
        await context.bot.send_message(
            chat_id=referrer,
            text=(
                "🎉 <b>إحالة جديدة!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                f"👤 <b>الاسم:</b> {user.first_name}\n"
                f"🔹 <b>اليوزر:</b> {username}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                "━━━━━━━━━━━━━━━\n"
                f"💰 حصلت على <b>{REFERRAL_REWARD}</b> نقطة."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass
