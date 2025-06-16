import threading
import telebot
from telebot import types
import time
import schedule
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# تحميل بيانات التوكن من ملف .env
load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
ADMIN_ID = os.getenv("ADMIN_ID")

# ملف تخزين بيانات المجموعات
DATA_FILE = "groups_data.json"
groups_data = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=4)

groups_data = load_data()

# رابط الصور على GitHub
def get_image_url(page):
    return f"https://raw.githubusercontent.com/Mohamed-Nagdy/Quran-App-Data/main/quran_images/{page}.png"

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_chat(message):
    if bot.get_me().id in [user.id for user in message.new_chat_members]:
        bot.send_message(message.chat.id, "شكرًا لإضافتي! الرجاء ترقيتي إلى «آدمن» لأبدأ بالإرسال.")

def check_admin(chat_id):
    try:
        member = bot.get_chat_member(chat_id, bot.get_me().id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    if check_admin(chat_id):
        if chat_id not in groups_data:
            groups_data[chat_id] = {
                "current_page": 1,
                "times": ["04:30"],
                "is_active": True,
                "last_sent": None
            }
            save_data()
        bot.reply_to(message, """
مرحبًا! أنا بوت ختم القرآن الكريم 🕌
        
الأوامر المتاحة:
/set_time - ضبط أوقات الإرسال
/start_from [رقم] - بدء من صفحة معينة
/status - عرض الإعدادات الحالية
/toggle - تفعيل/تعطيل البوت
""")

@bot.message_handler(commands=['set_time'])
def handle_set_time(message):
    chat_id = str(message.chat.id)
    if check_admin(chat_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        times = [
            ("🕟 4:30 ص", "04:30"),
            ("🕕 6:30 ص", "06:30"),
            ("🕧 12:30 م", "12:30"),
            ("🕝 2:30 م", "14:30"),
            ("🕟 4:30 م", "16:30"),
            ("🕡 6:30 م", "18:30")
        ]
        
        for text, time_val in times:
            if time_val in groups_data.get(chat_id, {}).get("times", []):
                text += " ✅"
            markup.add(types.InlineKeyboardButton(text, callback_data=f"time_{time_val}"))
        
        markup.add(types.InlineKeyboardButton("💾 حفظ الأوقات", callback_data="save_times"))
        bot.send_message(chat_id, "⏰ اختر أوقات الإرسال:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def handle_time_selection(call):
    chat_id = str(call.message.chat.id)
    if check_admin(chat_id):
        selected_time = call.data.split("_")[1]
        if chat_id not in groups_data:
            groups_data[chat_id] = {
                "current_page": 1,
                "times": [],
                "is_active": True,
                "last_sent": None
            }
        
        if selected_time in groups_data[chat_id]["times"]:
            groups_data[chat_id]["times"].remove(selected_time)
            bot.answer_callback_query(call.id, f"تم إلغاء {selected_time} ❌")
        else:
            groups_data[chat_id]["times"].append(selected_time)
            bot.answer_callback_query(call.id, f"تم اختيار {selected_time} ✅")
        
        save_data()
        # تحديث الواجهة
        handle_set_time(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "save_times")
def save_times_callback(call):
    chat_id = str(call.message.chat.id)
    if check_admin(chat_id):
        bot.answer_callback_query(call.id, "تم حفظ الأوقات بنجاح ✅")
        bot.send_message(chat_id, f"⏰ الأوقات المحددة:\n{', '.join(groups_data[chat_id]['times'])}")

@bot.message_handler(commands=['start_from'])
def handle_start_from(message):
    chat_id = str(message.chat.id)
    if check_admin(chat_id):
        try:
            new_page = int(message.text.split()[1])
            if 1 <= new_page <= 604:
                groups_data[chat_id]["current_page"] = new_page
                save_data()
                bot.reply_to(message, f"✅ تم التحديث إلى الصفحة {new_page}")
            else:
                bot.reply_to(message, "⚠️ رقم الصفحة يجب أن يكون بين 1 و 604")
        except:
            bot.reply_to(message, "⚙️ الاستخدام: /start_from <رقم_الصفحة>")

@bot.message_handler(commands=['status'])
def show_status(message):
    chat_id = str(message.chat.id)
    if check_admin(chat_id):
        data = groups_data.get(chat_id, {})
        status_text = f"""
⚙️ الإعدادات الحالية:
- الصفحة الحالية: {data.get('current_page', 1)}
- الأوقات المحددة: {', '.join(data.get('times', [])) or 'غير محدد'}
- الحالة: {'✅ مفعل' if data.get('is_active', False) else '❌ معطل'}
"""
        bot.reply_to(message, status_text)

@bot.message_handler(commands=['toggle'])
def toggle_bot(message):
    chat_id = str(message.chat.id)
    if check_admin(chat_id):
        if chat_id in groups_data:
            groups_data[chat_id]["is_active"] = not groups_data[chat_id].get("is_active", False)
            save_data()
            status = "✅ مفعل" if groups_data[chat_id]["is_active"] else "❌ معطل"
            bot.reply_to(message, f"تم تغيير حالة البوت إلى: {status}")

def send_pages():
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            for chat_id, data in list(groups_data.items()):
                try:
                    if data.get("is_active", False) and now in data.get("times", []):
                        if data.get("last_sent") != now:
                            current_page = data["current_page"]
                            
                            # إرسال الصفحتين
                            for i in range(2):
                                page_num = current_page + i
                                if page_num > 604:
                                    page_num = 1
                                
                                try:
                                    bot.send_photo(
                                        chat_id,
                                        get_image_url(page_num),
                                        caption=f"📖 الصفحة {page_num}"
                                    )
                                except Exception as e:
                                    print(f"Error sending page {page_num} to {chat_id}: {e}")
                            
                            # تحديث الصفحة
                            new_page = current_page + 2
                            if new_page > 604:
                                new_page = 1
                                bot.send_message(
                                    chat_id,
                                    "🎉 تم الانتهاء من القرآن الكريم!\n"
                                    "اللهم ارحمني بالقرآن واجعله لي نوراً وهدى ورحمة"
                                )
                            
                            # حفظ البيانات
                            data["current_page"] = new_page
                            data["last_sent"] = now
                            save_data()
                except Exception as e:
                    print(f"Error processing chat {chat_id}: {e}")
                    if "Forbidden" in str(e):
                        groups_data.pop(chat_id, None)
                        save_data()
            
            time.sleep(60)  # انتظر دقيقة قبل الفحص التالي
        except Exception as e:
            print(f"Error in send_pages loop: {e}")
            time.sleep(300)

def run_bot():
    try:
        print("Starting bot polling...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot polling error: {e}")
        time.sleep(15)
        run_bot()

if __name__ == "__main__":
    # بدء ثانوي لإرسال الصفحات
    sender_thread = threading.Thread(target=send_pages)
    sender_thread.daemon = True
    sender_thread.start()
    
    # بدء البوت
    run_bot()
