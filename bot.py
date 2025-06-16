import telebot
from telebot import types
import time
import schedule
import os
import json
from datetime import datetime

bot = telebot.TeleBot("TOKEN")
ADMIN_ID = "ADMIN_ID"  # آيدي المطور (لإدارة البوت العام)

# تخزين إعدادات كل مجموعة
groups_data = {}

# ملف لتخزين البيانات
DATA_FILE = "groups_data.json"


# تحميل البيانات من الملف
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


# حفظ البيانات في الملف
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=4)


groups_data = load_data()


# روابط الصور من GitHub
def get_image_url(page):
    return f"https://raw.githubusercontent.com/Mohamed-Nagdy/Quran-App-Data/main/quran_images/{page}.png"


# عند إضافة البوت إلى مجموعة
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_chat(message):
    if bot.get_me().id in [user.id for user in message.new_chat_members]:
        bot.send_message(message.chat.id, "شكرًا لإضافتي! يرجى ترقيتي إلى «آدمن» لأبدأ بالإرسال.")


# عند ترقية البوت إلى آدمن
@bot.message_handler(func=lambda m: True, content_types=['migrate_to_chat_id', 'new_chat_title', 'left_chat_member'])
def check_admin_status(message):
    chat_id = str(message.chat.id)
    if bot.get_chat_member(chat_id, bot.get_me().id).status == "administrator":
        if chat_id not in groups_data:
            groups_data[chat_id] = {
                "current_page": 1,
                "times": ["04:30", "12:30", "16:30"],
                "is_active": True,
                "last_sent": None
            }
            save_data()
            bot.send_message(chat_id,
                             "✅ تم تفعيل البوت في هذه المجموعة!\nاستخدم /set_time لضبط الأوقات\n/start_from لبدء من صفحة معينة")


# عرض لوحة الأوقات
@bot.message_handler(commands=['set_time'])
def handle_set_time(message):
    chat_id = str(message.chat.id)
    if chat_id in groups_data and bot.get_chat_member(chat_id, bot.get_me().id).status == "administrator":
        markup = types.InlineKeyboardMarkup(row_width=2)

        # أزرار الأوقات الصباحية
        markup.add(
            types.InlineKeyboardButton("🕟 4:30 ص", callback_data="time_04:30"),
            types.InlineKeyboardButton("🕕 6:30 ص", callback_data="time_06:30")
        )

        # أزرار الأوقات المسائية
        markup.add(
            types.InlineKeyboardButton("🕧 12:30 م", callback_data="time_12:30"),
            types.InlineKeyboardButton("🕝 2:30 م", callback_data="time_14:30")
        )

        markup.add(
            types.InlineKeyboardButton("🕟 4:30 م", callback_data="time_16:30"),
            types.InlineKeyboardButton("🕡 6:30 م", callback_data="time_18:30")
        )

        markup.add(types.InlineKeyboardButton("✅ حفظ الأوقات", callback_data="save_times"))

        bot.send_message(chat_id, "⏰ اختر أوقات الإرسال:", reply_markup=markup)


# معالجة اختيار الأوقات
@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def handle_time_selection(call):
    chat_id = str(call.message.chat.id)
    selected_time = call.data.split("_")[1]

    if chat_id in groups_data:
        if selected_time in groups_data[chat_id]["times"]:
            groups_data[chat_id]["times"].remove(selected_time)
            bot.answer_callback_query(call.id, f"تم إلغاء {selected_time} ❌")
        else:
            groups_data[chat_id]["times"].append(selected_time)
            bot.answer_callback_query(call.id, f"تم اختيار {selected_time} ✅")

        save_data()


# حفظ الأوقات المختارة
@bot.callback_query_handler(func=lambda call: call.data == "save_times")
def save_times_callback(call):
    chat_id = str(call.message.chat.id)
    if chat_id in groups_data:
        bot.answer_callback_query(call.id, "تم حفظ الأوقات بنجاح ✅")
        bot.send_message(chat_id, f"⏰ الأوقات المحددة:\n{', '.join(groups_data[chat_id]['times'])}")


# البدء من صفحة معينة
@bot.message_handler(commands=['start_from'])
def handle_start_from(message):
    chat_id = str(message.chat.id)
    if chat_id in groups_data and bot.get_chat_member(chat_id, bot.get_me().id).status == "administrator":
        try:
            new_page = int(message.text.split()[1])
            if 1 <= new_page <= 604:
                if new_page % 2 != 0:  # التأكد من أن الرقم فردي
                    groups_data[chat_id]["current_page"] = new_page
                    save_data()
                    bot.reply_to(message, f"✅ سيبدأ الإرسال من الصفحة {new_page}")
                else:
                    bot.reply_to(message, "⚠️ الرجاء إدخال رقم صفحة فردي (1, 3, 5, ...)")
            else:
                bot.reply_to(message, "⚠️ رقم الصفحة يجب أن يكون بين 1 و 604")
        except (IndexError, ValueError):
            bot.reply_to(message, "⚙️ الاستخدام: /start_from <رقم_صفحة_فردي>")


# إرسال الصفحات
def send_two_pages():
    for chat_id, data in groups_data.items():
        if data["is_active"] and data["times"]:
            current_page = data["current_page"]

            # التحقق من الوقت الحالي
            now = datetime.now().strftime("%H:%M")
            if now in data["times"] and now != data.get("last_sent"):
                try:
                    # إرسال الصفحتين
                    bot.send_photo(
                        chat_id,
                        get_image_url(current_page),
                        caption=f"الصفحة {current_page}"
                    )
                    bot.send_photo(
                        chat_id,
                        get_image_url(current_page + 1),
                        caption=f"الصفحة {current_page + 1}"
                    )

                    # تحديث الصفحة الحالية
                    new_page = current_page + 2
                    if new_page > 604:  # إذا انتهى المصحف
                        new_page = 1
                        schedule.every().day.at((datetime.now().hour + 1) % 24).do(
                            send_khatma_dua, chat_id
                        )

                    groups_data[chat_id]["current_page"] = new_page
                    groups_data[chat_id]["last_sent"] = now
                    save_data()

                except Exception as e:
                    print(f"Error in {chat_id}: {e}")


# إرسال دعاء الختمة
def send_khatma_dua(chat_id):
    dua = """
    🕌 دعاء ختم القرآن الكريم:

    اللهم ارحمني بالقرآن العظيم، واجعله لي إماماً ونوراً وهدىً ورحمة.
    اللهم ذكرني منه ما نسيت، وعلمني منه ما جهلت، وارزقني تلاوته آناء الليل وأطراف النهار.
    """
    bot.send_message(chat_id, dua)


# تشغيل البوت
if __name__ == "__main__":
    # تشغيل الجدولة كل دقيقة للتحقق من الأوقات
    schedule.every(1).minutes.do(send_two_pages)

    while True:
        try:
            bot.polling(none_stop=True)
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(15)