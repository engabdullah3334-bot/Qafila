#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
قافلة (Qafila) — بوت تيليجرام
=================================
تحويل أداة "قافلة" (qafila_cli.py) إلى بوت تيليجرام ذكي ومنظم لنشر المنشورات
في مجموعات فيسبوك يدوياً وبأمان تام 100% دون أي خطر لحظر الحساب.

مميزات البوت:
1. إدارة المجموعات: إضافة، حذف، عرض، وتصدير/استيراد ملفات JSON (متوافق تماماً مع groups.json ونسخة المتصفح).
2. تجهيز المنشور: دعم المنشورات النصية أو المنشورات مع صور/ميديا.
3. نسخ بنقرة واحدة: يظهر نص المنشور داخل قالب كود قابل للنسخ التلقائي بمجرد اللمس في تيليجرام.
4. انتقال مباشر: زر مخصص لفتح رابط كل جروب مباشرة في تطبيق أو متصفح فيسبوك.
5. قافلة متسلسلة تفاعلية: أزرار (تم النشر - التالي / تخطي / إنهاء)، ونصائح فاصل زمني لحماية الحساب.
6. ملخص نهائي لنتائج القافلة.
"""

import os
import sys
import json
import html
import tempfile
import time
import threading
import telebot
from telebot import types

# ---------------------------------------------------------------------------
# الإعدادات العامة والتوكن
# ---------------------------------------------------------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8977546165:AAF4xQYKIMuAyOR7-2zAhO59ZPW4hmV37Ro")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GROUPS_FILE = os.path.join(BASE_DIR, "groups.json")

# ---------------------------------------------------------------------------
# إدارة التخزين وحفظ المجموعات
# ---------------------------------------------------------------------------
def get_user_file(user_id):
    """مسار ملف المجموعات الخاص بالمستخدم"""
    return os.path.join(BASE_DIR, f"groups_{user_id}.json")

def load_user_groups(user_id):
    """
    تحميل مجموعات المستخدم.
    إذا لم يكن له ملف خاص، يتم فحص ملف groups.json المشترك كافتراضي.
    """
    user_file = get_user_file(user_id)
    target_file = user_file if os.path.exists(user_file) else DEFAULT_GROUPS_FILE
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # التحقق من سلامة البنية
                    valid_groups = []
                    for item in data:
                        if isinstance(item, dict) and "name" in item and "url" in item:
                            valid_groups.append({
                                "name": item["name"].strip(),
                                "url": item["url"].strip()
                            })
                    return valid_groups
        except (json.JSONDecodeError, OSError):
            pass
    return []

def save_user_groups(user_id, groups):
    """حفظ مجموعات المستخدم في ملفه الخاص وملف groups.json للتوافق"""
    user_file = get_user_file(user_id)
    try:
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False, indent=2)
        # تحديث groups.json العام أيضاً لسهولة المزامنة مع سكريبت CLI
        with open(DEFAULT_GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Error saving groups: {e}", file=sys.stderr)

# ---------------------------------------------------------------------------
# إدارة التخزين وحفظ النصوص المحفوظة (Saved Posts / Templates)
# ---------------------------------------------------------------------------
DEFAULT_POSTS_FILE = os.path.join(BASE_DIR, "saved_posts.json")

def get_user_posts_file(user_id):
    """مسار ملف النصوص المحفوظة الخاص بالمستخدم"""
    return os.path.join(BASE_DIR, f"saved_posts_{user_id}.json")

def load_user_saved_posts(user_id):
    """تحميل النصوص المحفوظة للمستخدم"""
    user_file = get_user_posts_file(user_id)
    target_file = user_file if os.path.exists(user_file) else DEFAULT_POSTS_FILE
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return []

def save_user_saved_posts(user_id, posts):
    """حفظ النصوص المحفوظة في ملف المستخدم والملف العام"""
    user_file = get_user_posts_file(user_id)
    try:
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        with open(DEFAULT_POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Error saving posts: {e}", file=sys.stderr)

def add_to_saved_posts(user_id, text):
    """إضافة نص إلى المحفوظات تلقائياً إذا لم يكن مضافاً من قبل"""
    clean_text = text.strip()
    if not clean_text:
        return
    posts = load_user_saved_posts(user_id)
    # التحقق من عدم التكرار المطابق
    for p in posts:
        if p.get("text", "").strip() == clean_text:
            return
    # إنشاء عنوان مختصر من أول 30 حرف
    first_line = clean_text.split("\n")[0].strip()
    title = (first_line[:35] + "...") if len(first_line) > 35 else first_line
    if not title:
        title = "نص بدون عنوان"
    import time
    posts.insert(0, {
        "id": int(time.time() * 1000),
        "title": title,
        "text": clean_text,
        "date": time.strftime("%Y-%m-%d %H:%M")
    })
    # الاحتفاظ بآخر 50 نص كحد أقصى
    posts = posts[:50]
    save_user_saved_posts(user_id, posts)

# ---------------------------------------------------------------------------
# إدارة نظام التذكير الدوري (Periodic Caravan Reminder - Every 4 Hours)
# ---------------------------------------------------------------------------
REMINDERS_FILE = os.path.join(BASE_DIR, "reminders.json")
DEFAULT_REMINDER_INTERVAL = 4 * 3600  # 4 ساعات بالثواني (14400 ثانية)

def load_reminders():
    """تحميل قائمة المشتركين في التذكير الدوري"""
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def save_reminders(data):
    """حفظ بيانات التذكير الدوري"""
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Error saving reminders: {e}", file=sys.stderr)

def register_reminder_user(chat_id, user_name=None):
    """تسجيل أو تحديث المستخدم في نظام التذكير الدوري (مفعل افتراضياً كل 4 ساعات)"""
    reminders = load_reminders()
    cid_str = str(chat_id)
    now = time.time()
    if cid_str not in reminders:
        reminders[cid_str] = {
            "enabled": True,
            "interval": DEFAULT_REMINDER_INTERVAL,
            "last_sent": now,
            "name": user_name or "User"
        }
        save_reminders(reminders)
    else:
        if user_name and reminders[cid_str].get("name") != user_name:
            reminders[cid_str]["name"] = user_name
            save_reminders(reminders)

def set_reminder_status(chat_id, enabled):
    """تفعيل أو تعطيل التذكير للمستخدم"""
    reminders = load_reminders()
    cid_str = str(chat_id)
    if cid_str not in reminders:
        reminders[cid_str] = {
            "enabled": enabled,
            "interval": DEFAULT_REMINDER_INTERVAL,
            "last_sent": time.time(),
            "name": "User"
        }
    else:
        reminders[cid_str]["enabled"] = enabled
        if enabled:
            reminders[cid_str]["last_sent"] = time.time()
    save_reminders(reminders)

def reminder_worker():
    """خيط خلفي يفحص ويرسل التذكيرات للمستخدمين كل 4 ساعات"""
    while True:
        try:
            now = time.time()
            reminders = load_reminders()
            updated = False
            for cid_str, info in list(reminders.items()):
                if not info.get("enabled", True):
                    continue
                interval = info.get("interval", DEFAULT_REMINDER_INTERVAL)
                last_sent = info.get("last_sent", 0)
                if (now - last_sent) >= interval:
                    chat_id = int(cid_str)
                    try:
                        kb = types.InlineKeyboardMarkup(row_width=1)
                        kb.add(
                            types.InlineKeyboardButton("🚀 إطلاق قافلة نشر الآن", callback_data="remind_start_caravan"),
                            types.InlineKeyboardButton("📝 اختيار من النصوص المحفوظة", callback_data="show_saved_posts_list"),
                            types.InlineKeyboardButton("⚙️ إعدادات التذكير", callback_data="show_reminder_settings")
                        )
                        bot.send_message(
                            chat_id,
                            "⏰ <b>تذكير دوري — موعد القافلة!</b> 🐪\n\n"
                            "مرت <b>4 ساعات</b> على موعدك الدوري.\n"
                            "حان وقت نشر بوست جديد في جروبات فيسبوك للحفاظ على تفاعل ونشاط حسابك بانتظام 🚀\n\n"
                            "💡 <i>اضغط على الزر أدناه لبدء القافلة فوراً:</i>",
                            reply_markup=kb
                        )
                        info["last_sent"] = now
                        updated = True
                    except telebot.apihelper.ApiTelegramException as te:
                        if te.error_code in [403, 400]:
                            info["enabled"] = False
                            updated = True
                    except Exception as err:
                        print(f"Error sending reminder to {cid_str}: {err}", file=sys.stderr)
            if updated:
                save_reminders(reminders)
        except Exception as e:
            print(f"Reminder worker loop error: {e}", file=sys.stderr)
        time.sleep(30)

# ---------------------------------------------------------------------------
# إدارة حالة المستخدمين (User State / Sessions)
# ---------------------------------------------------------------------------
user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "state": "IDLE",            # IDLE, WAITING_POST, WAITING_GROUP_NAME, WAITING_GROUP_URL, SELECTING_GROUPS, IN_CAMPAIGN
            "temp_group_name": None,
            "post_text": "",
            "post_photo": None,         # file_id للصورة إن وجدت
            "selected_indices": [],     # قائمة الاندكسات المختارة
            "campaign": {
                "step": 0,
                "total": 0,
                "done": 0,
                "skipped": 0,
                "groups": []
            }
        }
    return user_sessions[user_id]

def reset_session(user_id):
    session = get_session(user_id)
    session["state"] = "IDLE"
    session["temp_group_name"] = None
    session["post_text"] = ""
    session["post_photo"] = None
    session["selected_indices"] = []
    session["campaign"] = {"step": 0, "total": 0, "done": 0, "skipped": 0, "groups": []}

# ---------------------------------------------------------------------------
# لوحات المفاتيح والأزرار (Keyboards)
# ---------------------------------------------------------------------------
def get_main_keyboard():
    """لوحة المفاتيح الرئيسية السفلية"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🚀 بدء قافلة نشر جديدة"),
        types.KeyboardButton("📝 النصوص المحفوظة")
    )
    kb.add(
        types.KeyboardButton("📋 قائمة الجروبات"),
        types.KeyboardButton("➕ إضافة جروب")
    )
    kb.add(
        types.KeyboardButton("⏰ إعدادات التذكير (4 ساعات)"),
        types.KeyboardButton("📤 تصدير / 📥 استيراد")
    )
    kb.add(
        types.KeyboardButton("ℹ️ دليل الاستخدام والأمان")
    )
    return kb

def get_cancel_keyboard():
    """زر لإلغاء أي عملية جارية"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(types.KeyboardButton("❌ إلغاء والعودة للقائمة الرئيسية"))
    return kb

# ---------------------------------------------------------------------------
# رسائل الترحيب والمساعدة
# ---------------------------------------------------------------------------
WELCOME_TEXT = (
    "👋 <b>مرحباً بك في بوت قافلة (Qafila)!</b> 🐪\n\n"
    "أداتك الذكية لتنظيم نشر المنشورات في جروبات فيسبوك المتعددة "
    "<b>يدوياً وبأمان 100%</b>، دون تعريض حسابك للحظر أو إدخال أي كلمات سر.\n\n"
    "✨ <b>كيف يعمل البوت؟</b>\n"
    "1️⃣ تحفظ جروباتك هنا مرة واحدة.\n"
    "2️⃣ ترسل نص المنشور أو تختار من نصوصك المحفوظة.\n"
    "3️⃣ يفتح لك البوت كل جروب بالترتيب، وينسخ النص لك بلمسة واحدة!\n"
    "4️⃣ <b>ينبهك تلقائياً كل 4 ساعات</b> لتسيير قافلة جديدة والحفاظ على استمرارية التفاعل!\n\n"
    "اختر من القائمة أدناه للبدء:"
)

HELP_TEXT = (
    "📖 <b>دليل الاستخدام والأمان — قافلة:</b>\n\n"
    "🔒 <b>لماذا النشر اليدوي المنظم وليس التلقائي؟</b>\n"
    "فيسبوك يحظر فوراً أي برامج تدّعي النشر التلقائي لأنها تنتهك شروطه، "
    "بينما «قافلة» تبسّط لك النشر البشري الطبيعي ليكون فائق السرعة وبلا تعب.\n\n"
    "💡 <b>نصائح لحماية حسابك:</b>\n"
    "• لا تنشر بسرعة جنونية، خذ وقتاً طبيعياً بين الجروب والآخر (30-60 ثانية).\n"
    "• اضغط على النص الرمادي في رسالة النشر ليتم <b>نسخه تلقائياً بنقرة واحدة</b>.\n"
    "• استخدم زر «فتح الجروب» لتنتقل مباشرة لفيسبوك وتلصق المحتوى فوراً.\n\n"
    "📌 <b>الأوامر السريعة المتاحة:</b>\n"
    "/start - القائمة الرئيسية\n"
    "/newpost - تجهيز بوست وبدء قافلة\n"
    "/posts - عرض وإدارة النصوص المحفوظة\n"
    "/remind - إعدادات التذكير الدوري (كل 4 ساعات)\n"
    "/groups - عرض المجموعات وإدارتها\n"
    "/addgroup - إضافة مجموعة جديدة\n"
    "/export - تصدير المجموعات كملف JSON\n"
    "/cancel - إلغاء أي خطوة حالية"
)

# ---------------------------------------------------------------------------
# معالجة الأوامر الأساسية
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    reset_session(user_id)
    register_reminder_user(message.chat.id, message.from_user.first_name)
    bot.send_message(
        message.chat.id,
        WELCOME_TEXT,
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        HELP_TEXT,
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    reset_session(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "✅ تم إلغاء العملية والعودة للقائمة الرئيسية.",
        reply_markup=get_main_keyboard()
    )

# ---------------------------------------------------------------------------
# إدارة المجموعات: إضافة / عرض / حذف / استيراد وتصدير
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['groups'])
@bot.message_handler(func=lambda msg: msg.text == "📋 قائمة الجروبات")
def handle_show_groups(message):
    user_id = message.from_user.id
    groups = load_user_groups(user_id)
    
    if not groups:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ أضف أول جروب الآن", callback_data="add_group_prompt"))
        bot.send_message(
            message.chat.id,
            "📭 <b>لا توجد أي جروبات محفوظة حالياً.</b>\n"
            "قم بإضافة جروباتك أولاً لتتمكن من استخدام القافلة.",
            reply_markup=kb
        )
        return

    text = f"📋 <b>قائمة الجروبات المحفوظة ({len(groups)} جروب):</b>\n\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for i, g in enumerate(groups, 1):
        g_name = html.escape(g['name'])
        g_url = html.escape(g['url'])
        text += f"<b>{i}.</b> <a href=\"{g_url}\">{g_name}</a>\n"
    
    kb.add(
        types.InlineKeyboardButton("➕ إضافة جروب جديد", callback_data="add_group_prompt"),
        types.InlineKeyboardButton("🗑️ حذف جروب من القائمة", callback_data="delete_group_menu"),
        types.InlineKeyboardButton("📤 تصدير القائمة (ملف JSON)", callback_data="export_groups")
    )

    bot.send_message(
        message.chat.id,
        text,
        disable_web_page_preview=True,
        reply_markup=kb
    )

@bot.message_handler(commands=['addgroup'])
@bot.message_handler(func=lambda msg: msg.text == "➕ إضافة جروب")
def handle_add_group_start(message):
    user_id = message.from_user.id
    session = get_session(user_id)
    session["state"] = "WAITING_GROUP_NAME"
    
    bot.send_message(
        message.chat.id,
        "✍️ <b>أرسل اسم الجروب الآن:</b>\n(مثال: جروب رواد الأعمال أو سوق المستعمل)",
        reply_markup=get_cancel_keyboard()
    )

def handle_group_name_input(message):
    user_id = message.from_user.id
    session = get_session(user_id)
    name = message.text.strip()
    
    if not name:
        bot.send_message(message.chat.id, "⚠️ يرجى إدخال اسم صحيح للجروب.")
        return

    session["temp_group_name"] = name
    session["state"] = "WAITING_GROUP_URL"
    bot.send_message(
        message.chat.id,
        f"🔗 ممتاز، اسم الجروب: <b>{html.escape(name)}</b>\n\n"
        "الآن أرسل رابط الجروب على فيسبوك:\n"
        "(يجب أن يبدأ بـ <code>https://</code> أو <code>http://</code>)",
        reply_markup=get_cancel_keyboard()
    )

def handle_group_url_input(message):
    user_id = message.from_user.id
    session = get_session(user_id)
    url = message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        bot.send_message(
            message.chat.id,
            "⚠️ الرابط غير صالح! يجب أن يبدأ بـ <code>https://</code> أو <code>http://</code>.\nأعد إرسال الرابط:"
        )
        return

    name = session.get("temp_group_name", "جروب بدون اسم")
    groups = load_user_groups(user_id)
    groups.append({"name": name, "url": url})
    save_user_groups(user_id, groups)
    
    reset_session(user_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ <b>تمت إضافة الجروب بنجاح!</b>\n"
        f"📌 الاسم: <b>{html.escape(name)}</b>\n"
        f"🔗 الرابط: <a href=\"{html.escape(url)}\">{html.escape(url)}</a>\n\n"
        f"إجمالي الجروبات الآن: {len(groups)}",
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "add_group_prompt")
def callback_add_group_prompt(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    session["state"] = "WAITING_GROUP_NAME"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "✍️ <b>أرسل اسم الجروب الآن:</b>",
        reply_markup=get_cancel_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "delete_group_menu")
def callback_delete_group_menu(call):
    user_id = call.from_user.id
    groups = load_user_groups(user_id)
    bot.answer_callback_query(call.id)
    
    if not groups:
        bot.send_message(call.message.chat.id, "📭 لا توجد جروبات لحذفها.")
        return
        
    kb = types.InlineKeyboardMarkup(row_width=1)
    for idx, g in enumerate(groups):
        kb.add(types.InlineKeyboardButton(f"❌ حذف: {g['name']}", callback_data=f"del_grp_{idx}"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="show_groups_callback"))
    
    bot.edit_message_text(
        "🗑️ <b>اختر الجروب الذي تريد حذفه من القائمة:</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_grp_"))
def callback_do_delete_group(call):
    user_id = call.from_user.id
    idx = int(call.data.replace("del_grp_", ""))
    groups = load_user_groups(user_id)
    
    if 0 <= idx < len(groups):
        deleted = groups.pop(idx)
        save_user_groups(user_id, groups)
        bot.answer_callback_query(call.id, f"تم حذف {deleted['name']}")
    else:
        bot.answer_callback_query(call.id, "الجروب غير موجود.")

    # إعادة فتح قائمة الجروبات
    handle_show_groups(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "show_groups_callback")
def callback_show_groups(call):
    bot.answer_callback_query(call.id)
    handle_show_groups(call.message)

# ---------------------------------------------------------------------------
# تصدير واستيراد المجموعات (JSON)
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['export'])
@bot.message_handler(func=lambda msg: msg.text == "📤 تصدير / 📥 استيراد")
@bot.callback_query_handler(func=lambda call: call.data == "export_groups")
def handle_export_import(event):
    message = event if isinstance(event, types.Message) else event.message
    user_id = event.from_user.id
    groups = load_user_groups(user_id)
    
    if isinstance(event, types.CallbackQuery):
        bot.answer_callback_query(event.id)

    if not groups:
        bot.send_message(
            message.chat.id,
            "📭 لا توجد جروبات محفوظة لتصديرها. قم بإضافة جروباتك أولاً أو أرسل ملف JSON لاستيرادها."
        )
        return

    # إنشاء ملف JSON مؤقت لإرساله للمستخدم
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json", delete=False) as tmp:
        json.dump(groups, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    with open(tmp_path, "rb") as doc:
        caption = (
            "📦 <b>نسخة احتياطية لجروباتك (JSON):</b>\n\n"
            f"• تحتوي على: <b>{len(groups)}</b> جروب.\n"
            "• متوافقة تماماً مع سكريبت التيرمينال (qafila_cli.py) وأداة المتصفح (HTML).\n\n"
            "💡 <i>لإعادة استيراد جروبات في أي وقت، فقط أرسل ملف JSON إلى البوت مباشرة وسيقوم بقرائته تلقائياً!</i>"
        )
        bot.send_document(message.chat.id, doc, visible_file_name="groups.json", caption=caption)

    try:
        os.remove(tmp_path)
    except OSError:
        pass

# استيراد ملف JSON إذا أرسله المستخدم كمستند
@bot.message_handler(content_types=['document'])
def handle_document_import(message):
    doc = message.document
    if not (doc.file_name.endswith('.json') or doc.mime_type == 'application/json'):
        bot.reply_to(message, "⚠️ يرجى إرسال ملف بصيغة <code>.json</code> يحتوي على قائمة الجروبات.")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        data = json.loads(downloaded.decode('utf-8'))
        
        imported = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "url" in item:
                    imported.append({
                        "name": str(item["name"]).strip(),
                        "url": str(item["url"]).strip()
                    })

        if not imported:
            bot.reply_to(message, "⚠️ لم يتم العثور على جروبات صالحة في هذا الملف.")
            return

        user_id = message.from_user.id
        current = load_user_groups(user_id)
        
        # دمج بدون تكرار الرابط
        existing_urls = {g["url"] for g in current}
        new_count = 0
        for g in imported:
            if g["url"] not in existing_urls:
                current.append(g)
                existing_urls.add(g["url"])
                new_count += 1

        save_user_groups(user_id, current)
        bot.reply_to(
            message,
            f"🎉 <b>تم الاستيراد بنجاح!</b>\n\n"
            f"• تم إضافة: <b>{new_count}</b> جروب جديد.\n"
            f"• إجمالي الجروبات الآن: <b>{len(current)}</b> جروب.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء قراءة الملف: {html.escape(str(e))}")

# ---------------------------------------------------------------------------
# إدارة النصوص المحفوظة (Saved Posts / Drafts)
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['posts'])
@bot.message_handler(func=lambda msg: msg.text == "📝 النصوص المحفوظة")
def handle_show_saved_posts(event):
    message = event if isinstance(event, types.Message) else event.message
    user_id = event.from_user.id
    posts = load_user_saved_posts(user_id)
    
    if isinstance(event, types.CallbackQuery):
        bot.answer_callback_query(event.id)

    if not posts:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ حفظ أول نص الآن", callback_data="add_saved_post_prompt"))
        bot.send_message(
            message.chat.id,
            "📭 <b>لا توجد نصوص محفوظة حالياً.</b>\n"
            "يمكنك كتابة وحفظ نصوص منشوراتك هنا لاستخدامها مراراً وتكراراً في القوافل القادمة دون إعادة كتابتها.",
            reply_markup=kb
        )
        return

    text = f"📝 <b>النصوص المحفوظة ({len(posts)} نص):</b>\n\nاختر أي نص لعرضه كاملاً، نسخه، أو النشر به مباشرة:\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for p in posts:
        title = html.escape(p.get("title", "نص محفوظ"))
        p_id = p.get("id")
        kb.add(types.InlineKeyboardButton(f"📄 {title}", callback_data=f"view_post_{p_id}"))
        
    kb.add(types.InlineKeyboardButton("➕ حفظ نص جديد", callback_data="add_saved_post_prompt"))
    
    if isinstance(event, types.CallbackQuery):
        try:
            bot.edit_message_text(text, chat_id=message.chat.id, message_id=message.message_id, reply_markup=kb)
            return
        except Exception:
            pass

    bot.send_message(message.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "show_saved_posts_list")
def callback_show_saved_posts_list(call):
    handle_show_saved_posts(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_post_"))
def callback_view_saved_post(call):
    user_id = call.from_user.id
    p_id = call.data.replace("view_post_", "")
    posts = load_user_saved_posts(user_id)
    target = next((p for p in posts if str(p.get("id")) == p_id), None)
    
    bot.answer_callback_query(call.id)
    if not target:
        bot.send_message(call.message.chat.id, "⚠️ النص غير موجود أو تم حذفه.")
        return

    body = (
        f"📄 <b>{html.escape(target.get('title', 'نص محفوظ'))}</b>\n"
        f"🕒 تاريخ الحفظ: <code>{target.get('date', '')}</code>\n\n"
        "📋 <b>النص (انقر للنسخ):</b>\n"
        f"<pre>{html.escape(target.get('text', ''))}</pre>"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🚀 انطلق بالقافلة بهذا النص", callback_data=f"use_post_{p_id}"),
        types.InlineKeyboardButton("🗑️ حذف هذا النص", callback_data=f"del_post_{p_id}"),
        types.InlineKeyboardButton("🔙 رجوع لقائمة النصوص", callback_data="show_saved_posts_list")
    )
    
    try:
        bot.edit_message_text(body, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    except Exception:
        bot.send_message(call.message.chat.id, body, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_post_"))
def callback_delete_saved_post(call):
    user_id = call.from_user.id
    p_id = call.data.replace("del_post_", "")
    posts = load_user_saved_posts(user_id)
    new_posts = [p for p in posts if str(p.get("id")) != p_id]
    
    save_user_saved_posts(user_id, new_posts)
    bot.answer_callback_query(call.id, "🗑️ تم حذف النص بنجاح.")
    handle_show_saved_posts(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("use_post_"))
def callback_use_saved_post_for_caravan(call):
    user_id = call.from_user.id
    p_id = call.data.replace("use_post_", "")
    posts = load_user_saved_posts(user_id)
    target = next((p for p in posts if str(p.get("id")) == p_id), None)
    
    if not target:
        bot.answer_callback_query(call.id, "⚠️ النص غير متوفر.")
        return
        
    groups = load_user_groups(user_id)
    if not groups:
        bot.answer_callback_query(call.id, "⚠️ لا توجد جروبات محفوظة بعد!")
        return

    session = get_session(user_id)
    session["post_text"] = target.get("text", "")
    session["post_photo"] = None
    session["state"] = "SELECTING_GROUPS"
    session["selected_indices"] = list(range(len(groups)))
    
    bot.answer_callback_query(call.id, "✅ تم اختيار النص، اختر الجروبات الآن.")
    send_group_selection_interface(call.message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "add_saved_post_prompt")
def callback_add_saved_post_prompt(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    session["state"] = "WAITING_SAVED_POST_TEXT"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "✍️ <b>أرسل الآن النص الذي تريد حفظه:</b>\n(سيتم حفظه في قائمة نصوصك لاستخدامه وقتما تشاء)",
        reply_markup=get_cancel_keyboard()
    )

def handle_save_new_post_input(message):
    user_id = message.from_user.id
    text = message.text or message.caption or ""
    if not text.strip():
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال نص صالح لحفظه.")
        return
    add_to_saved_posts(user_id, text)
    reset_session(user_id)
    bot.send_message(
        message.chat.id,
        "💾 <b>تم حفظ النص بنجاح في نصوصك المحفوظة!</b>\n"
        "يمكنك استخدامه في أي وقت بنقرة واحدة عند إطلاق أي قافلة نشر.",
        reply_markup=get_main_keyboard()
    )
    handle_show_saved_posts(message)

# ---------------------------------------------------------------------------
# أوجهات التحكم في نظام التذكير الدوري (كل 4 ساعات)
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['remind', 'reminder'])
@bot.message_handler(func=lambda msg: msg.text == "⏰ إعدادات التذكير (4 ساعات)")
def handle_reminder_settings_command(message):
    register_reminder_user(message.chat.id, message.from_user.first_name)
    show_reminder_settings_ui(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "show_reminder_settings")
def callback_show_reminder_settings(call):
    bot.answer_callback_query(call.id)
    show_reminder_settings_ui(call.message.chat.id, message_id=call.message.message_id)

def show_reminder_settings_ui(chat_id, message_id=None):
    reminders = load_reminders()
    cid_str = str(chat_id)
    info = reminders.get(cid_str, {"enabled": True, "interval": DEFAULT_REMINDER_INTERVAL, "last_sent": time.time()})
    
    is_enabled = info.get("enabled", True)
    last_sent = info.get("last_sent", time.time())
    interval = info.get("interval", DEFAULT_REMINDER_INTERVAL)
    now = time.time()
    
    status_str = "مفعل ✅" if is_enabled else "معطل 🔕"
    
    # حساب الوقت المتبقي
    elapsed = max(0, now - last_sent)
    remaining = max(0, interval - elapsed)
    rem_hours = int(remaining // 3600)
    rem_mins = int((remaining % 3600) // 60)
    
    if is_enabled:
        if remaining > 0:
            next_str = f"بعد {rem_hours} ساعة و {rem_mins} دقيقة"
        else:
            next_str = "خلال لحظات ⏳"
    else:
        next_str = "متوقف مؤقتاً"

    body = (
        "⏰ <b>نظام التذكير الدوري بنشر القوافل:</b> 🐪\n\n"
        f"• الحالة الحالية: <b>{status_str}</b>\n"
        "• معدل التكرار: <b>كل 4 ساعات</b>\n"
        f"• موعد التذكير القادم: <b>{next_str}</b>\n\n"
        "💡 <i>يقوم البوت بتنبيهك تلقائياً كل 4 ساعات لتسيير قافلة ونشر منشوراتك في الجروبات للحفاظ على استمرارية التفاعل والنشاط.</i>"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    if is_enabled:
        kb.add(types.InlineKeyboardButton("🔕 إيقاف التذكيرات مؤقتاً", callback_data="remind_disable"))
    else:
        kb.add(types.InlineKeyboardButton("🔔 تفعيل التذكيرات (كل 4 ساعات)", callback_data="remind_enable"))
        
    kb.add(
        types.InlineKeyboardButton("🧪 تجربة التنبيه الآن", callback_data="remind_test_now"),
        types.InlineKeyboardButton("🚀 انطلق بالقافلة الآن", callback_data="remind_start_caravan")
    )
    
    if message_id:
        try:
            bot.edit_message_text(body, chat_id=chat_id, message_id=message_id, reply_markup=kb)
            return
        except Exception:
            pass
            
    bot.send_message(chat_id, body, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data in ["remind_enable", "remind_disable"])
def callback_toggle_reminder(call):
    chat_id = call.message.chat.id
    if call.data == "remind_enable":
        set_reminder_status(chat_id, True)
        bot.answer_callback_query(call.id, "✅ تم تفعيل التذكير كل 4 ساعات!")
    else:
        set_reminder_status(chat_id, False)
        bot.answer_callback_query(call.id, "🔕 تم إيقاف التذكير.")
    show_reminder_settings_ui(chat_id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "remind_test_now")
def callback_test_reminder_now(call):
    bot.answer_callback_query(call.id, "📨 تم إرسال تذكير تجريبي!")
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🚀 إطلاق قافلة نشر الآن", callback_data="remind_start_caravan"),
        types.InlineKeyboardButton("📝 استخدام نص محفوظ", callback_data="show_saved_posts_list"),
        types.InlineKeyboardButton("⚙️ إعدادات التذكير", callback_data="show_reminder_settings")
    )
    bot.send_message(
        call.message.chat.id,
        "⏰ <b>[رسالة تجريبية] تذكير دوري — موعد القافلة!</b> 🐪\n\n"
        "مرت <b>4 ساعات</b> على موعدك الدوري.\n"
        "حان وقت نشر بوست جديد في جروبات فيسبوك للحفاظ على تفاعل ونشاط حسابك بانتظام 🚀\n\n"
        "💡 <i>اضغط على الزر أدناه لبدء القافلة فوراً:</i>",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "remind_start_caravan")
def callback_remind_start_caravan(call):
    bot.answer_callback_query(call.id)
    handle_start_caravan(call.message)

# ---------------------------------------------------------------------------
# بدء قافلة النشر: استقبال المنشور واختيار المجموعات
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['newpost'])
@bot.message_handler(func=lambda msg: msg.text == "🚀 بدء قافلة نشر جديدة")
def handle_start_caravan(message):
    user_id = message.from_user.id
    groups = load_user_groups(user_id)
    
    if not groups:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ أضف جروباتك أولاً", callback_data="add_group_prompt"))
        bot.send_message(
            message.chat.id,
            "⚠️ <b>لا توجد جروبات محفوظة بعد!</b>\n"
            "أضف جروباتك أولاً للبدء.",
            reply_markup=kb
        )
        return

    session = get_session(user_id)
    session["state"] = "WAITING_POST"
    session["post_text"] = ""
    session["post_photo"] = None
    session["selected_indices"] = []

    saved_posts = load_user_saved_posts(user_id)
    
    kb = None
    prompt_text = (
        "✍️ <b>الخطوة الأولى: تحديد محتوى المنشور</b>\n\n"
        "• يمكنك إرسال <b>نص جديد الآن</b> (أو صورة مع كابشن).\n"
    )
    
    if saved_posts:
        prompt_text += (
            "• أو <b>اختر من نصوصك المحفوظة سابقاً</b> من الأزرار بالأسفل:\n\n"
            "💡 <i>أي نص جديد ترسله سيتم حفظه تلقائياً لتعيد استخدامه لاحقاً بسهولة.</i>"
        )
        kb = types.InlineKeyboardMarkup(row_width=1)
        # عرض آخر 5 نصوص محفوظة كاختيارات سريعة
        for p in saved_posts[:5]:
            kb.add(types.InlineKeyboardButton(f"📑 {p.get('title')}", callback_data=f"use_post_{p.get('id')}"))
        if len(saved_posts) > 5:
            kb.add(types.InlineKeyboardButton("📚 عرض باقي النصوص المحفوظة", callback_data="show_saved_posts_list"))
    else:
        prompt_text += (
            "\n💡 <i>ملاحظة: سيتم حفظ هذا النص تلقائياً لتعيد استخدامه لاحقاً بضغطة زر دون كتابته من الصفر.</i>"
        )

    bot.send_message(
        message.chat.id,
        prompt_text,
        reply_markup=kb
    )
    bot.send_message(
        message.chat.id,
        "بانتظار إرسال المنشور (أو الإلغاء عبر الزر أدناه):",
        reply_markup=get_cancel_keyboard()
    )

def handle_post_received(message):
    user_id = message.from_user.id
    session = get_session(user_id)
    
    text = ""
    photo_id = None
    
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
        text = message.caption or ""
    elif message.content_type == 'text':
        text = message.text
        
    if not text.strip() and not photo_id:
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال نص أو صورة للمنشور.")
        return

    # حفظ النص تلقائياً في النصوص المحفوظة للمستخدم
    if text.strip():
        add_to_saved_posts(user_id, text)

    session["post_text"] = text
    session["post_photo"] = photo_id
    session["state"] = "SELECTING_GROUPS"
    
    groups = load_user_groups(user_id)
    # افتراضياً تحديد كل الجروبات
    session["selected_indices"] = list(range(len(groups)))
    
    send_group_selection_interface(message.chat.id, user_id)

def build_group_selection_markup(user_id):
    session = get_session(user_id)
    groups = load_user_groups(user_id)
    selected = set(session.get("selected_indices", []))
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    # خيارات سريعة
    kb.row(
        types.InlineKeyboardButton("✅ تحديد الكل", callback_data="sel_all"),
        types.InlineKeyboardButton("❌ إلغاء التحديد", callback_data="sel_none")
    )
    
    # قائمة الجروبات مع مؤشر صح/خطأ
    for idx, g in enumerate(groups):
        is_chk = idx in selected
        prefix = "✅ " if is_chk else "⬜ "
        kb.add(types.InlineKeyboardButton(f"{prefix}{g['name']}", callback_data=f"toggle_grp_{idx}"))
        
    count = len(selected)
    kb.row(
        types.InlineKeyboardButton(f"🚀 انطلق بالقافلة ({count} جروب)", callback_data="start_campaign_now")
    )
    return kb

def send_group_selection_interface(chat_id, user_id, message_id=None):
    session = get_session(user_id)
    groups = load_user_groups(user_id)
    selected_count = len(session.get("selected_indices", []))
    
    preview_text = html.escape(session['post_text'][:150] + ("..." if len(session['post_text']) > 150 else ""))
    if not preview_text:
        preview_text = "<i>(منشور يحتوي على صورة فقط)</i>"

    body = (
        "🎯 <b>الخطوة الثانية: اختيار الجروبات المستهدفة</b>\n\n"
        f"📝 <b>معاينة المنشور:</b>\n<code>{preview_text}</code>\n\n"
        f"حدد الجروبات التي تود النشر فيها بالضغط عليها:\n"
        f"• محدد حالياً: <b>{selected_count} من {len(groups)}</b>"
    )
    
    markup = build_group_selection_markup(user_id)
    
    if message_id:
        try:
            bot.edit_message_text(body, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
            
    bot.send_message(chat_id, body, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["sel_all", "sel_none"] or call.data.startswith("toggle_grp_"))
def handle_selection_callbacks(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    groups = load_user_groups(user_id)
    selected = set(session.get("selected_indices", []))
    
    if call.data == "sel_all":
        session["selected_indices"] = list(range(len(groups)))
    elif call.data == "sel_none":
        session["selected_indices"] = []
    elif call.data.startswith("toggle_grp_"):
        idx = int(call.data.replace("toggle_grp_", ""))
        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)
        session["selected_indices"] = sorted(list(selected))
        
    bot.answer_callback_query(call.id)
    send_group_selection_interface(call.message.chat.id, user_id, message_id=call.message.message_id)

# ---------------------------------------------------------------------------
# تشغيل القافلة المتسلسلة (Caravan Campaign Execution)
# ---------------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data == "start_campaign_now")
def handle_start_campaign_callback(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    groups = load_user_groups(user_id)
    selected_indices = session.get("selected_indices", [])
    
    if not selected_indices:
        bot.answer_callback_query(call.id, "⚠️ يرجى اختيار جروب واحد على الأقل!", show_alert=True)
        return
        
    bot.answer_callback_query(call.id, "🐪 القافلة تسير الآن!")
    
    # إعداد مسار القافلة
    campaign_groups = [groups[i] for i in selected_indices if i < len(groups)]
    session["campaign"] = {
        "step": 0,
        "total": len(campaign_groups),
        "done": 0,
        "skipped": 0,
        "groups": campaign_groups
    }
    session["state"] = "IN_CAMPAIGN"
    
    bot.send_message(
        call.message.chat.id,
        f"🏁 <b>انطلقت القافلة بنجاح!</b>\n"
        f"سيتم المرور على <b>{len(campaign_groups)}</b> جروب بالترتيب.\n"
        "انسخ النص بلمسة واحدة، ثم افتح الجروب وانشر براحتك.",
        reply_markup=get_main_keyboard()
    )
    
    send_caravan_step(call.message.chat.id, user_id)

def send_caravan_step(chat_id, user_id):
    session = get_session(user_id)
    camp = session.get("campaign", {})
    step = camp.get("step", 0)
    total = camp.get("total", 0)
    groups = camp.get("groups", [])
    
    if step >= total or step >= len(groups):
        # انتهاء القافلة
        finish_campaign(chat_id, user_id)
        return

    current_group = groups[step]
    post_text = session.get("post_text", "")
    photo_id = session.get("post_photo", None)
    
    step_num = step + 1
    g_name = html.escape(current_group["name"])
    g_url = current_group["url"]
    
    body = (
        f"🐪 <b>المحطة [{step_num} من {total}]</b>\n"
        f"📌 الجروب: <b>{g_name}</b>\n\n"
        "📋 <b>اضغط على النص أدناه لنسخه فوراً:</b>\n"
        f"<pre>{html.escape(post_text)}</pre>\n\n"
        "💡 <i>اضغط «🌐 فتح الجروب في فيسبوك» للصق المنشور ونشره، ثم اضغط «✅ تم النشر» للمتابعة.</i>"
    )
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🌐 فتح الجروب في فيسبوك", url=g_url),
        types.InlineKeyboardButton("✅ تم النشر — التالي ➡️", callback_data="camp_next"),
        types.InlineKeyboardButton("⏭️ تخطي هذا الجروب", callback_data="camp_skip"),
        types.InlineKeyboardButton("🛑 إنهاء القافلة الآن", callback_data="camp_stop")
    )
    
    if photo_id:
        bot.send_photo(chat_id, photo_id, caption=body, reply_markup=kb)
    else:
        bot.send_message(chat_id, body, reply_markup=kb, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data in ["camp_next", "camp_skip", "camp_stop"])
def handle_campaign_navigation(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    
    if session.get("state") != "IN_CAMPAIGN":
        bot.answer_callback_query(call.id, "القافلة غير جارية حالياً.")
        return

    camp = session.get("campaign", {})
    action = call.data
    
    if action == "camp_next":
        camp["done"] += 1
        camp["step"] += 1
        bot.answer_callback_query(call.id, "✅ تم تسجيل النشر! جاري فتح الجروب التالي...")
        send_caravan_step(call.message.chat.id, user_id)
    elif action == "camp_skip":
        camp["skipped"] += 1
        camp["step"] += 1
        bot.answer_callback_query(call.id, "⏭️ تم تخطي الجروب.")
        send_caravan_step(call.message.chat.id, user_id)
    elif action == "camp_stop":
        bot.answer_callback_query(call.id, "🛑 تم إيقاف القافلة.")
        finish_campaign(call.message.chat.id, user_id, stopped_early=True)

def finish_campaign(chat_id, user_id, stopped_early=False):
    session = get_session(user_id)
    camp = session.get("campaign", {})
    done = camp.get("done", 0)
    skipped = camp.get("skipped", 0)
    total = camp.get("total", 0)
    
    status_title = "🛑 <b>تم إيقاف القافلة مبكراً</b>" if stopped_early else "🎉 <b>اكتملت مسيرة القافلة بنجاح!</b>"
    
    summary = (
        f"{status_title}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>تقرير الإنجاز:</b>\n"
        f"✅ تم النشر في: <b>{done}</b> جروب\n"
        f"⏭️ تم تخطي: <b>{skipped}</b> جروب\n"
        f"📦 إجمالي الجروبات المستهدفة: <b>{total}</b> جروب\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🐪 <i>شكراً لاستخدامك قافلة! يمكنك بدء جولة جديدة في أي وقت.</i>"
    )
    
    reset_session(user_id)
    bot.send_message(chat_id, summary, reply_markup=get_main_keyboard())

# ---------------------------------------------------------------------------
# معالجة الرسائل النصية العامة والتحكم بالخطوات (Fallback Handler)
# ---------------------------------------------------------------------------
@bot.message_handler(content_types=['text', 'photo'])
def handle_general_messages(message):
    user_id = message.from_user.id
    register_reminder_user(message.chat.id, message.from_user.first_name)
    session = get_session(user_id)
    state = session.get("state", "IDLE")
    
    # معالجة زر الإلغاء العام
    if message.content_type == 'text' and message.text == "❌ إلغاء والعودة للقائمة الرئيسية":
        reset_session(user_id)
        bot.send_message(message.chat.id, "تم الإلغاء.", reply_markup=get_main_keyboard())
        return

    if state == "WAITING_GROUP_NAME":
        handle_group_name_input(message)
    elif state == "WAITING_GROUP_URL":
        handle_group_url_input(message)
    elif state == "WAITING_SAVED_POST_TEXT":
        handle_save_new_post_input(message)
    elif state == "WAITING_POST":
        handle_post_received(message)
    elif message.content_type == 'text' and message.text == "📝 النصوص المحفوظة":
        handle_show_saved_posts(message)
    elif message.content_type == 'text' and message.text == "⏰ إعدادات التذكير (4 ساعات)":
        handle_reminder_settings_command(message)
    elif message.content_type == 'text' and message.text == "ℹ️ دليل الاستخدام والأمان":
        cmd_help(message)
    else:
        # إذا أرسل المستخدم نصاً مباشرة بدون الضغط على زر
        if message.content_type in ['text', 'photo']:
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("🚀 تجهيز هذا المنشور للنشر", callback_data="quick_publish"),
                types.InlineKeyboardButton("💾 حفظ في النصوص المحفوظة فقط", callback_data="quick_save_draft")
            )
            kb.add(
                types.InlineKeyboardButton("📋 فتح القائمة الرئيسية", callback_data="show_main_menu")
            )
            # تخزين النص تحسباً لاختيار النشر السريع
            session["post_text"] = message.text or message.caption or ""
            session["post_photo"] = message.photo[-1].file_id if message.content_type == 'photo' else None
            
            bot.reply_to(
                message,
                "💡 هل تود استخدام هذا المنشور لبدء قافلة نشر في جروبات فيسبوك الآن، أم حفظه لاستخدامه لاحقاً؟",
                reply_markup=kb
            )

@bot.callback_query_handler(func=lambda call: call.data == "quick_save_draft")
def callback_quick_save_draft(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    text = session.get("post_text", "")
    if text.strip():
        add_to_saved_posts(user_id, text)
        bot.answer_callback_query(call.id, "💾 تم حفظ النص في نصوصك المحفوظة!")
        bot.send_message(
            call.message.chat.id,
            "✅ <b>تم حفظ النص بنجاح في «النصوص المحفوظة»!</b>\nيمكنك استخدامه في أي وقت بنقرة واحدة عند إطلاق القافلة.",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "⚠️ لا يوجد نص لحفظه.")

@bot.callback_query_handler(func=lambda call: call.data == "quick_publish")
def callback_quick_publish(call):
    user_id = call.from_user.id
    session = get_session(user_id)
    groups = load_user_groups(user_id)
    bot.answer_callback_query(call.id)
    
    if not groups:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ أضف جروباتك أولاً", callback_data="add_group_prompt"))
        bot.send_message(
            call.message.chat.id,
            "⚠️ لا توجد جروبات محفوظة حالياً. أضف جروباً أولاً:",
            reply_markup=kb
        )
        return

    # حفظ النص تلقائياً في النصوص المحفوظة
    if session.get("post_text", "").strip():
        add_to_saved_posts(user_id, session["post_text"])
        
    session["state"] = "SELECTING_GROUPS"
    session["selected_indices"] = list(range(len(groups)))
    send_group_selection_interface(call.message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "show_main_menu")
def callback_show_main_menu(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, WELCOME_TEXT, reply_markup=get_main_keyboard())

# ---------------------------------------------------------------------------
# تشغيل البوت
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("   🐪 قافلة (Qafila) — بوت تيليجرام قيد التشغيل")
    print("=" * 55)
    print("✓ تم تحميل النظام بنجاح...")
    
    # تشغيل خيط التذكير الدوري في الخلفية (كل 4 ساعات)
    reminder_thread = threading.Thread(target=reminder_worker, daemon=True)
    reminder_thread.start()
    print("✓ تم تشغيل نظام التذكير الدوري (كل 4 ساعات)...")
    
    print("✓ بانتظار الرسائل والتفاعل من المستخدمين...")
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت بنجاح.")
    except Exception as e:
        print(f"\n❌ حدث خطأ غير متوقع: {e}")
