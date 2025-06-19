
import telebot
from telebot import types
import json
import time
import threading
from datetime import datetime

bot_token = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(bot_token)

DATA_FILE = "groups_data.json"
ALLOWED_TIMES = ["1 AM", "3 AM", "5 AM", "11 AM", "12 PM", "2 PM", "4 PM", "6 PM"]

# -------------------- Utils --------------------

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(groups_data, f, indent=4)

def get_image_url(page):
    return f"https://raw.githubusercontent.com/Mohamed-Nagdy/Quran-App-Data/main/quran_images/{page}.png"

def get_page_info(page):
    # Mocked version - replace with real API call if needed
    # You can integrate with an actual Quran API here
    return {
        "surah": f"سورة {page}",  # Replace with real surah name
        "juz": (page // 20) + 1
    }

def get_random_ayah():
    return "إِنَّ مَعَ الْعُسْرِ يُسْرًا"

# -------------------- Command Handlers --------------------

@bot.message_handler(commands=["start"])
def start(msg):
    cid = str(msg.chat.id)
    if cid not in groups_data:
        groups_data[cid] = {
            "current_page": 1,
            "current_part": 1,
            "image_active": True,
            "image_time": "11 AM",
            "khatma_active": True,
            "khatma_time": "2 PM",
            "last_image_sent": "",
            "last_khatma_sent": "",
            "completed_khatmas": 0
        }
        save_data()
    bot.send_message(msg.chat.id, "👋 أهلاً بك! سأقوم بإرسال صفحتين من القرآن وتذكير بختمة يومياً.")

@bot.message_handler(commands=["set_image_time"])
def set_image_time(msg):
    send_time_selector(msg.chat.id, "images")

@bot.message_handler(commands=["set_khatma_time"])
def set_khatma_time(msg):
    send_time_selector(msg.chat.id, "khatma")

def send_time_selector(chat_id, for_service):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=t, callback_data=f"{for_service}_time_{t}") for t in ALLOWED_TIMES]
    markup.add(*buttons)
    bot.send_message(chat_id, f"⏰ اختر وقت إرسال {'الصور' if for_service == 'images' else 'الختمة'}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("images_time_") or call.data.startswith("khatma_time_"))
def handle_time_selection(call):
    chat_id = str(call.message.chat.id)
    _, service, time_selected = call.data.split("_", 2)
    if service == "images":
        groups_data[chat_id]["image_time"] = time_selected
    elif service == "khatma":
        groups_data[chat_id]["khatma_time"] = time_selected
    save_data()
    bot.edit_message_text(f"✅ تم تعيين وقت الإرسال: {time_selected}", chat_id, call.message.message_id)

@bot.my_chat_member_handler()
def check_bot_added(event):
    chat = event.chat
    if event.new_chat_member.status == "member":
        bot.send_message(chat.id, "⚠️ من فضلك اجعلني *أدمن* حتى أستطيع إرسال الصور والتذكيرات.")

# -------------------- Daily Functions --------------------

def send_quran_pages(chat_id):
    try:
        page = groups_data[chat_id]["current_page"]
        info = get_page_info(page)
        caption = f"📖 الصفحتان {page}-{page+1}\n🕋 سورة: {info['surah']}\n📚 الجزء: {info['juz']}"
        media = [
            types.InputMediaPhoto(get_image_url(page), caption=caption),
            types.InputMediaPhoto(get_image_url(page + 1))
        ]
        bot.send_media_group(chat_id, media)
        next_page = page + 2 if page + 2 <= 604 else 1
        groups_data[chat_id]["current_page"] = next_page
        groups_data[chat_id]["last_image_sent"] = datetime.now().strftime("%d/%m/%Y")
        save_data()
    except Exception as e:
        print(f"Error sending quran pages: {e}")

def send_khatma_reminder(chat_id):
    try:
        data = groups_data[chat_id]
        part = data.get("current_part", 1)
        today = datetime.now().strftime("%d/%m/%Y")
        message = f"📘 تذكير الختمة اليومية\n📅 التاريخ: {today}\n📖 الجزء: {part} من 30\n✨ آية اليوم:\n{get_random_ayah()}"
        bot.send_message(chat_id, message)
        if part == 30:
            bot.send_message(chat_id, "🎉 تهانينا! أتممت ختمة كاملة 🌟\nاللهم اجعل القرآن ربيع قلوبنا.")
            data["completed_khatmas"] += 1
            data["current_part"] = 1
        else:
            data["current_part"] = part + 1
        data["last_khatma_sent"] = today
        save_data()
    except Exception as e:
        print(f"Error in send_khatma_reminder: {e}")

# -------------------- Scheduler --------------------

def scheduler():
    while True:
        now_time = datetime.now().strftime("%I %p")
        today = datetime.now().strftime("%d/%m/%Y")
        for chat_id, data in groups_data.items():
            try:
                if data.get("image_active") and data.get("image_time") == now_time and data.get("last_image_sent") != today:
                    send_quran_pages(chat_id)
                if data.get("khatma_active") and data.get("khatma_time") == now_time and data.get("last_khatma_sent") != today:
                    send_khatma_reminder(chat_id)
            except Exception as e:
                print(f"Error in scheduler for chat {chat_id}: {e}")
        time.sleep(60)

# -------------------- Init --------------------

groups_data = load_data()

threading.Thread(target=scheduler, daemon=True).start()
bot.infinity_polling()
