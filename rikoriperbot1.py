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
# ==============================
#           الأزرار
# ==============================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    register(q.from_user)

    # ---------- الرئيسية ----------
    if q.data == "home":
        context.user_data.pop("waiting_text", None)
        u = get_user(user_id)
        await q.edit_message_text(
            welcome_text(q.from_user, u["points"]),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )

    # ---------- التصليح ----------
    elif q.data == "repair":
        context.user_data["waiting_text"] = True
        await q.edit_message_text(
            "🛠️ <b>تصليح الثغرات</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "أرسل أي نص، والبوت يولّد لك القائمة تلقائياً.\n\n"
            f"💰 التكلفة: <b>{POINTS_COST}</b> نقاط",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

    # ---------- صنع ثغرة ----------
    elif q.data == "guess":
        with db() as con:
            u = con.execute(
                "SELECT points FROM users WHERE user_id=?", (user_id,)
            ).fetchone()

            if user_id != OWNER_ID and u["points"] < GUESS_COST:
                await q.edit_message_text(
                    "❌ <b>رصيدك غير كافٍ</b>\n\n"
                    f"تحتاج <b>{GUESS_COST}</b> نقاط، لديك <b>{u['points']}</b>.\n\n"
                    "🎁 اجمع نقاطاً عبر دعوة أصدقائك من زر الإحالات.",
                    reply_markup=back_keyboard(),
                    parse_mode="HTML"
                )
                return

            if user_id != OWNER_ID:
                con.execute(
                    "UPDATE users SET points=points-? WHERE user_id=?",
                    (GUESS_COST, user_id)
                )

        result = format_output()
        output = "\n".join(result)

        await q.edit_message_text(
            "🔮 <b>صنع ثغرة</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"<code>{output}</code>\n"
            "━━━━━━━━━━━━━━━\n"
            f"<b>{SCAM_FOOTER}</b>\n"
            f"👨‍💻 <b>@{OWNER_USERNAME}</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 خُصم <b>{GUESS_COST}</b> نقطة",
            reply_markup=guess_again_keyboard(),
            parse_mode="HTML"
        )

    # ---------- حسابي ----------
    elif q.data == "account":
        u = get_user(user_id)
        await q.edit_message_text(
            "👤 <b>حسابي</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"🔹 <b>اليوزر:</b> @{u['username'] or 'غير محدد'}\n"
            f"💰 <b>النقاط:</b> {u['points']:,}\n"
            f"🛠️ <b>مرات التصليح:</b> {u['repairs']}\n"
            f"🎁 <b>الإحالات:</b> {u['referrals']}",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

    # ---------- الإحالات ----------
    elif q.data == "referrals":
        link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        u = get_user(user_id)
        referred = get_referred_users(user_id)

        if referred:
            lines = []
            for i, r in enumerate(referred, 1):
                name = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
                lines.append(f"{i}. {name}")
            referred_list = "\n".join(lines)
        else:
            referred_list = "لا يوجد أحد بعد."

        await q.edit_message_text(
            "🎁 <b>نظام الإحالات</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"كل دعوة ناجحة = <b>{REFERRAL_REWARD}</b> نقطة\n\n"
            f"👥 <b>عدد دعواتك:</b> {u['referrals']}\n\n"
            "📋 <b>الأشخاص الذين دخلوا عبر رابطك:</b>\n"
            f"{referred_list}\n\n"
            "🔗 <b>رابطك الخاص:</b>\n"
            f"<code>{link}</code>",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

    # ---------- الإحصائيات ----------
    elif q.data == "status":
        with db() as con:
            users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            repairs = con.execute("SELECT SUM(repairs) n FROM users").fetchone()["n"] or 0
            refs = con.execute("SELECT COUNT(*) n FROM referrals").fetchone()["n"]

        await q.edit_message_text(
            "📊 <b>إحصائيات البوت</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"👥 <b>المستخدمون:</b> {users:,}\n"
            f"🛠️ <b>عمليات التصليح:</b> {repairs:,}\n"
            f"🎁 <b>الإحالات:</b> {refs:,}\n"
            "━━━━━━━━━━━━━━━\n"
            "🟢 <b>الحالة:</b> يعمل",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )


# ==============================
#         استقبال النص
# ==============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    register(user)

    if not context.user_data.get("waiting_text"):
        u = get_user(user.id)
        await msg.reply_text(
            welcome_text(user, u["points"]),
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )
        return

    context.user_data["waiting_text"] = False

    with db() as con:
        u = con.execute(
            "SELECT points FROM users WHERE user_id=?", (user.id,)
        ).fetchone()

        if user.id != OWNER_ID and u["points"] < POINTS_COST:
            await msg.reply_text(
                "❌ <b>رصيدك غير كافٍ</b>\n\n"
                f"تحتاج <b>{POINTS_COST}</b> نقاط، لديك <b>{u['points']}</b>.\n\n"
                "🎁 اجمع نقاطاً عبر دعوة أصدقائك من زر الإحالات.",
                reply_markup=main_keyboard(),
                parse_mode="HTML"
            )
            return

        if user.id != OWNER_ID:
            con.execute(
                "UPDATE users SET points=points-? WHERE user_id=?",
                (POINTS_COST, user.id)
            )
        con.execute(
            "UPDATE users SET repairs=repairs+1 WHERE user_id=?",
            (user.id,)
        )

    result = format_output()
    output = "\n".join(result)

    await msg.reply_text(
        "✅ <b>تم التصليح بنجاح</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"<code>{output}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        f"<b>{SCAM_FOOTER}</b>\n"
        f"👨‍💻 <b>@{OWNER_USERNAME}</b>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# ==============================
#          أوامر المالك
# ==============================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.effective_message.reply_text("هذا الأمر للمالك فقط.")
        return

    await update.effective_message.reply_text(
        "👑 <b>لوحة المالك</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "/stats — الإحصائيات\n"
        "/points ID AMOUNT — إضافة/خصم نقاط\n"
        "/broadcast TEXT — رسالة جماعية",
        parse_mode="HTML"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    with db() as con:
        users = con.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        points = con.execute("SELECT SUM(points) n FROM users").fetchone()["n"] or 0
        repairs = con.execute("SELECT SUM(repairs) n FROM users").fetchone()["n"] or 0

    await update.effective_message.reply_text(
        "📊 <b>إحصائيات كاملة</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون: <b>{users:,}</b>\n"
        f"💰 إجمالي النقاط: <b>{points:,}</b>\n"
        f"🛠️ عمليات التصليح: <b>{repairs:,}</b>",
        parse_mode="HTML"
    )


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 2:
        await update.effective_message.reply_text(
            "الاستخدام: <code>/points USER_ID AMOUNT</code>",
            parse_mode="HTML"
        )
        return
    try:
        target, amount = map(int, context.args)
    except ValueError:
        await update.effective_message.reply_text("اكتب أرقاماً صحيحة.")
        return

    with db() as con:
        cur = con.execute(
            "UPDATE users SET points=MAX(0, points+?) WHERE user_id=? AND user_id!=?",
            (amount, target, OWNER_ID)
        )
        if cur.rowcount == 0:
            await update.effective_message.reply_text(
                "المستخدم غير موجود أو لا يمكن تعديل رصيد المالك."
            )
            return
        balance = con.execute(
            "SELECT points FROM users WHERE user_id=?", (target,)
        ).fetchone()["points"]

    await update.effective_message.reply_text(
        f"✅ تم التحديث.\n💰 الرصيد الحالي: <b>{balance:,}</b>",
        parse_mode="HTML"
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.effective_message.reply_text(
            "الاستخدام: <code>/broadcast النص</code>",
            parse_mode="HTML"
        )
        return

    text = " ".join(context.args)
    with db() as con:
        users = con.execute("SELECT user_id FROM users").fetchall()

    sent, failed = 0, 0
    for row in users:
        try:
            await context.bot.send_message(chat_id=row["user_id"], text=text)
            sent += 1
        except Exception:
            failed += 1

    await update.effective_message.reply_text(
        f"✅ تم الإرسال.\n\n✔️ نجح: {sent}\n❌ فشل: {failed}"
    )


# ==============================
#          خطأ عام
# ==============================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"⚠️ خطأ: {context.error}")


# ==============================
#           التشغيل
# ==============================
def main():
    if not BOT_TOKEN:
        raise RuntimeError("ضع توكن البوت في متغير البيئة BOT_TOKEN أولاً.")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(
        buttons,
        pattern="^(home|repair|guess|account|referrals|status)$"
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler
    ))
    app.add_error_handler(error_handler)

    print("🛡️ RIKO SECURITY is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
