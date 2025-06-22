import threading
import telebot
from telebot import types
import time
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# تحميل بيانات التوكن من ملف .env
load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
ADMIN_ID = os.getenv("ADMIN_ID")

# ملفات تخزين البيانات
DATA_FILE = "groups_data.json"
KHATMA_FILE = "khatma_data.json"

# الأوقات المتاحة للاختيار
AVAILABLE_TIMES = [
    "01:00", "03:00", "05:00", 
    "07:00", "09:00", "11:00", 
    "13:00", "15:00", "17:00", 
    "19:00", "21:00", "23:00"
]

# تحميل البيانات
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                # تحويل البيانات القديمة إلى التنسيق الجديد
                for chat_id, group_data in data.items():
                    if "image_time" in group_data:
                        group_data["image_times"] = [group_data.pop("image_time")] if group_data["image_time"] else []
                    if "khatma_time" in group_data:
                        group_data["khatma_times"] = [group_data.pop("khatma_time")] if group_data["khatma_time"] else []
                return data
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def load_khatma_data():
    try:
        if os.path.exists(KHATMA_FILE):
            with open(KHATMA_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading khatma data: {e}")
        return {}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(groups_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def save_khatma_data():
    try:
        with open(KHATMA_FILE, "w", encoding='utf-8') as f:
            json.dump(khatma_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving khatma data: {e}")

groups_data = load_data()
khatma_data = load_khatma_data()

# ========== نظام الصور القرآنية ==========
def get_page_info(page):
    """ الحصول على معلومات الصفحة من API مع حساب الجزء """
    try:
        response = requests.get(f"https://api.alquran.cloud/v1/page/{page}/quran-uthmani", timeout=10)
        if response.status_code == 200:
            data = response.json()
            surah_name = data["data"]["ayahs"][0]["surah"]["name"]
            juz_number = ((page - 1) // 20) + 1
            return {"surah": surah_name, "juz": juz_number}
        return {"surah": "غير معروف", "juz": "غير معروف"}
    except Exception as e:
        print(f"Error fetching page info: {e}")
        return {"surah": "غير معروف", "juz": "غير معروف"}

def get_image_url(page):
    """ الحصول على صورة الصفحة من GitHub """
    return f"https://raw.githubusercontent.com/Mohamed-Nagdy/Quran-App-Data/main/quran_images/{page}.png"

# ========== نظام الختمة بالآيات ==========
def get_random_ayah():
    """ جلب آية عشوائية من API """
    try:
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.alafasy", timeout=10)
        if response.status_code == 200:
            ayah = response.json()["data"]
            return f"{ayah['text']}\n(سورة {ayah['surah']['name']} - الآية {ayah['numberInSurah']})"
        return "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ"
    except Exception as e:
        print(f"Error fetching random ayah: {e}")
        return "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ"

# ========== التحقق من صلاحيات الأدمن ==========
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_chat(message):
    try:
        if bot.get_me().id in [user.id for user in message.new_chat_members]:
            if not check_admin(message.chat.id):
                bot.send_message(
                    message.chat.id,
                    "⚠️ يُرجى ترقيتي إلى «أدمن» مع صلاحية إرسال الرسائل لأتمكن من العمل!",
                    parse_mode="Markdown"
                )
    except Exception as e:
        print(f"Error in new chat handler: {e}")

def check_admin(chat_id):
    try:
        member = bot.get_chat_member(chat_id, bot.get_me().id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

# ========== أوامر البوت الأساسية ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        chat_id = str(message.chat.id)
        if message.chat.type in ["group", "supergroup"]:
            if check_admin(chat_id):
                if chat_id not in groups_data:
                    groups_data[chat_id] = {
                        "current_page": 1,
                        "image_times": [],
                        "images_active": False,
                        "last_image_sent": None,
                        "current_part": 1,
                        "khatma_times": [],
                        "khatma_active": False,
                        "last_khatma_sent": None,
                        "completed_khatmas": 0
                    }
                    save_data()
                
                welcome_msg = """
🕌 *بوت ختمة القرآن الكريم* - الإصدار المطور 🕌

⚙️ *الأوامر المتاحة:*

📖 *نظام الصور:*
/set_image_time - اختيار وقت إرسال الصور
/set_start_page - تحديد صفحة البدء (فردية)
/start_images - تفعيل إرسال الصور
/stop_images - إيقاف إرسال الصور
/test_images - اختبار إرسال الصور

📜 *نظام الختمة:*
/set_khatma_time - اختيار وقت إرسال الختمة
/set_start_part - تحديد جزء البدء
/start_khatma - تفعيل تذكير الختمة
/stop_khatma - إيقاف تذكير الختمة
/test_khatma - اختبار إرسال الختمة
/khatma_status - عرض عدد الختمات

⚙️ *أخرى:*
/status - عرض جميع الإعدادات
"""
                bot.reply_to(message, welcome_msg, parse_mode="Markdown")
            else:
                bot.reply_to(message, "⚠️ يجب أن تكون أدمن في المجموعة لاستخدام البوت")
        else:
            bot.reply_to(message, "⚠️ هذا البوت مخصص للمجموعات فقط")
    except Exception as e:
        print(f"Error in welcome handler: {e}")
        bot.reply_to(message, "حدث خطأ أثناء معالجة الأمر. يرجى المحاولة لاحقاً.")

# ========== الأوامر الجديدة ==========
@bot.message_handler(commands=['set_start_page'])
def set_start_page(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            msg = bot.reply_to(message, "📖 أرسل رقم الصفحة التي تريد البدء منها (يجب أن يكون رقمًا فرديًا بين 1 و603):")
            bot.register_next_step_handler(msg, process_start_page)
    except Exception as e:
        print(f"Error in set_start_page: {e}")

def process_start_page(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            try:
                page = int(message.text)
                if 1 <= page <= 603 and page % 2 == 1:
                    groups_data[chat_id]["current_page"] = page
                    save_data()
                    bot.reply_to(message, f"✅ تم تعيين صفحة البدء إلى {page}")
                else:
                    bot.reply_to(message, "⚠️ يجب أن يكون الرقم فرديًا بين 1 و603")
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح فقط")
    except Exception as e:
        print(f"Error in process_start_page: {e}")

@bot.message_handler(commands=['set_start_part'])
def set_start_part(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            msg = bot.reply_to(message, "📖 أرسل رقم الجزء الذي تريد البدء منه (بين 1 و30):")
            bot.register_next_step_handler(msg, process_start_part)
    except Exception as e:
        print(f"Error in set_start_part: {e}")

def process_start_part(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            try:
                part = int(message.text)
                if 1 <= part <= 30:
                    groups_data[chat_id]["current_part"] = part
                    save_data()
                    bot.reply_to(message, f"✅ تم تعيين جزء البدء إلى {part}")
                else:
                    bot.reply_to(message, "⚠️ يجب أن يكون الرقم بين 1 و30")
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح فقط")
    except Exception as e:
        print(f"Error in process_start_part: {e}")

# ========== دوال إعداد الأوقات ==========
def create_time_keyboard(prefix):
    """ إنشاء لوحة مفاتيح لاختيار الوقت """
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for time_str in AVAILABLE_TIMES:
        hour = int(time_str.split(":")[0])
        time_display = f"{hour}:00 {'ص' if hour < 12 else 'م'}"
        callback_data = f"{prefix}_{time_str}"
        
        # تحديد إذا كان الوقت محدد مسبقاً
        chat_id = str(call.message.chat.id) if prefix == "image" else str(call.message.chat.id)
        if prefix == "image":
            selected = time_str in groups_data.get(chat_id, {}).get("image_times", [])
        else:
            selected = time_str in groups_data.get(chat_id, {}).get("khatma_times", [])
            
        if selected:
            time_display = "✅ " + time_display
            
        buttons.append(types.InlineKeyboardButton(
            text=time_display,
            callback_data=callback_data
        ))
    
    # تقسيم الأزرار إلى صفوف كل 3 أزرار
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    
    # زر إنهاء الاختيار
    markup.row(types.InlineKeyboardButton(
        text="تم الاختيار",
        callback_data=f"done_{prefix}"
    ))
    
    return markup

@bot.message_handler(commands=['set_image_time'])
def set_image_time(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            bot.send_message(
                chat_id,
                "⏰ اختر وقت إرسال الصور اليومية (يمكن اختيار أكثر من وقت):",
                reply_markup=create_time_keyboard("image_time")
            )
    except Exception as e:
        print(f"Error in set_image_time: {e}")

@bot.message_handler(commands=['set_khatma_time'])
def set_khatma_time(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            bot.send_message(
                chat_id,
                "⏰ اختر وقت إرسال تذكير الختمة اليومية (يمكن اختيار أكثر من وقت):",
                reply_markup=create_time_keyboard("khatma_time")
            )
    except Exception as e:
        print(f"Error in set_khatma_time: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("image_time_", "khatma_time_", "done_")))
def handle_time_selection(call):
    try:
        chat_id = str(call.message.chat.id)
        if not check_admin(chat_id):
            bot.answer_callback_query(call.id, "⚠️ يجب أن تكون أدمن لاستخدام هذا الأمر")
            return
            
        if call.data.startswith("done_"):
            prefix = call.data.split("_")[1]
            bot.answer_callback_query(call.id, "تم حفظ الأوقات المحددة")
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
            return
            
        prefix, selected_time = call.data.split("_", 1)
        time_display = f"{int(selected_time.split(':')[0])}:00 {'ص' if int(selected_time.split(':')[0]) < 12 else 'م'}"
        
        if prefix == "image":
            times_list = groups_data[chat_id].get("image_times", [])
            if selected_time in times_list:
                times_list.remove(selected_time)
                action = "إزالة"
            else:
                times_list.append(selected_time)
                action = "إضافة"
            groups_data[chat_id]["image_times"] = times_list
        else:
            times_list = groups_data[chat_id].get("khatma_times", [])
            if selected_time in times_list:
                times_list.remove(selected_time)
                action = "إزالة"
            else:
                times_list.append(selected_time)
                action = "إضافة"
            groups_data[chat_id]["khatma_times"] = times_list
        
        save_data()
        bot.answer_callback_query(call.id, f"{action} الوقت {time_display}")
        
        # تحديث لوحة المفاتيح لتعكس التغييرات
        new_prefix = "image" if prefix == "image" else "khatma"
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=create_time_keyboard(f"{new_prefix}_time")
        )
        
    except Exception as e:
        print(f"Error in time selection: {e}")

# ========== دوال إرسال الصور المحدثة ==========
def send_quran_pages(chat_id):
    try:
        data = groups_data[chat_id]
        if not data.get("images_active", False):
            return False
            
        current_page = data["current_page"]
        
        # التحقق من وجود الصفحة
        if current_page > 604 or current_page < 1:
            current_page = 1
            data["current_page"] = 1

        page_info = get_page_info(current_page)
        
        # إعداد الوسائط مع التحقق من الصور
        media = [
            types.InputMediaPhoto(
                get_image_url(current_page),
                caption=f"📖 الصفحات {current_page}-{current_page+1}\n"
                        f"الجزء: {page_info['juz']}\n"
                        f"السورة: {page_info['surah']}"
            ),
            types.InputMediaPhoto(
                get_image_url(current_page + 1),
                caption=""
            )
        ]
        
        # إرسال الصور مع معالجة الأخطاء
        try:
            sent_msg = bot.send_media_group(chat_id, media)
            print(f"تم الإرسال بنجاح إلى {chat_id}: {sent_msg}")
        except Exception as send_error:
            print(f"Error in sending: {send_error}")
            raise  # لإظهار الخطأ للدالة الأم

        # تحديث الصفحة
        new_page = current_page + 2
        if new_page > 604:
            new_page = 1
            bot.send_message(
                chat_id,
                "🎉 *تم الانتهاء من القرآن الكريم!*\n\nاللهم ارحمني بالقرآن واجعله لي نوراً وهدى ورحمة",
                parse_mode="Markdown"
            )

        data["current_page"] = new_page
        data["last_image_sent"] = datetime.now().strftime("%d/%m/%Y")
        save_data()
        return True
        
    except Exception as e:
        print(f"Error sending pages: {e}")
        bot.send_message(ADMIN_ID, f"⚠️ خطأ في إرسال الصفحات: {str(e)}")
        return False

@bot.message_handler(commands=['start_images'])
def start_images(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            if not groups_data[chat_id]["image_times"]:
                bot.reply_to(message, "⚠️ يرجى تحديد وقت الإرسال أولاً باستخدام /set_image_time")
            else:
                groups_data[chat_id]["images_active"] = True
                save_data()
                bot.reply_to(message, "✅ تم تفعيل إرسال الصور القرآنية")
    except Exception as e:
        print(f"Error in start_images: {e}")

@bot.message_handler(commands=['stop_images'])
def stop_images(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            groups_data[chat_id]["images_active"] = False
            save_data()
            bot.reply_to(message, "❌ تم إيقاف إرسال الصور القرآنية")
    except Exception as e:
        print(f"Error in stop_images: {e}")

@bot.message_handler(commands=['test_images'])
def test_images(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            if not groups_data[chat_id]["images_active"]:
                bot.reply_to(message, "⚠️ إرسال الصور معطل حالياً. استخدم /start_images لتفعيله.")
                return
                
            bot.send_message(chat_id, "🔍 جاري اختبار إرسال الصفحات...")
            if send_quran_pages(chat_id):
                bot.send_message(chat_id, "✅ تم اختبار إرسال الصور بنجاح")
            else:
                bot.send_message(chat_id, "❌ فشل في إرسال الصور")
    except Exception as e:
        print(f"Error in test_images: {e}")

# ========== دوال إرسال الختمة ==========
def send_khatma_reminder(chat_id):
    try:
        data = groups_data[chat_id]
        if not data.get("khatma_active", False):
            return False
            
        today = datetime.now().strftime("%d/%m/%Y")
        part = (data.get("current_part", 1) % 30) or 30
        
        # إعداد رسالة التذكير
        message = f"""
🕌 *تذكير ورد اليوم*  
السلام عليكم ورحمة الله وبركاته  

📅 *التاريخ:* {today}  
📖 *الجزء:* {part} من 30  
🔄 *الختمات المكتملة:* {data.get("completed_khatmas", 0)}  

✨ *آية اليوم:*  
{get_random_ayah()}  

اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا.
"""
        bot.send_message(chat_id, message, parse_mode="Markdown")
        
        # التحقق من اكتمال الختمة
        if part == 30:
            bot.send_message(
                chat_id,
                "🎉 *تهانينا!* لقد أكملت ختمة كاملة!\n\nاللهم ارزقنا تلاوته آناء الليل وأطراف النهار",
                parse_mode="Markdown"
            )
            data["completed_khatmas"] = data.get("completed_khatmas", 0) + 1
        
        # تحديث الجزء التالي
        data["current_part"] = part + 1
        data["last_khatma_sent"] = today
        save_data()
        return True
        
    except Exception as e:
        print(f"Error in khatma reminder: {e}")
        bot.send_message(ADMIN_ID, f"⚠️ خطأ في إرسال الختمة: {str(e)}")
        return False

@bot.message_handler(commands=['start_khatma'])
def start_khatma(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            if not groups_data[chat_id]["khatma_times"]:
                bot.reply_to(message, "⚠️ يرجى تحديد وقت الإرسال أولاً باستخدام /set_khatma_time")
            else:
                groups_data[chat_id]["khatma_active"] = True
                save_data()
                bot.reply_to(message, "✅ تم تفعيل تذكير الختمة اليومية")
    except Exception as e:
        print(f"Error in start_khatma: {e}")

@bot.message_handler(commands=['stop_khatma'])
def stop_khatma(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            groups_data[chat_id]["khatma_active"] = False
            save_data()
            bot.reply_to(message, "❌ تم إيقاف تذكير الختمة اليومية")
    except Exception as e:
        print(f"Error in stop_khatma: {e}")

@bot.message_handler(commands=['test_khatma'])
def test_khatma(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            if not groups_data[chat_id]["khatma_active"]:
                bot.reply_to(message, "⚠️ إرسال الختمة معطل حالياً. استخدم /start_khatma لتفعيله.")
                return
                
            if send_khatma_reminder(chat_id):
                bot.reply_to(message, "✅ تم اختبار إرسال الختمة بنجاح")
            else:
                bot.reply_to(message, "❌ فشل في إرسال الختمة")
    except Exception as e:
        print(f"Error in test_khatma: {e}")

@bot.message_handler(commands=['khatma_status'])
def khatma_status(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            bot.reply_to(message, f"عدد الختمات المكتملة: {groups_data.get(chat_id, {}).get('completed_khatmas', 0)}")
    except Exception as e:
        print(f"Error in khatma_status: {e}")

@bot.message_handler(commands=['status'])
def show_status(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            data = groups_data.get(chat_id, {})
            
            # تحويل الأوقات إلى تنسيق 12 ساعة
            image_times = data.get("image_times", [])
            image_times_display = []
            for time_str in image_times:
                hour = int(time_str.split(":")[0])
                image_times_display.append(f"{hour}:00 {'ص' if hour < 12 else 'م'}")
            
            khatma_times = data.get("khatma_times", [])
            khatma_times_display = []
            for time_str in khatma_times:
                hour = int(time_str.split(":")[0])
                khatma_times_display.append(f"{hour}:00 {'ص' if hour < 12 else 'م'}")
            
            status_text = f"""
⚙️ *الإعدادات الحالية:*

📖 *نظام الصور:*
- الحالة: {'✅ مفعل' if data.get('images_active', False) else '❌ معطل'}
- الصفحة الحالية: {data.get('current_page', 1)}
- أوقات الإرسال: {', '.join(image_times_display) if image_times_display else 'غير محدد'}

📜 *نظام الختمة:*
- الحالة: {'✅ مفعل' if data.get('khatma_active', False) else '❌ معطل'}
- الجزء الحالي: {data.get('current_part', 1)}
- أوقات الإرسال: {', '.join(khatma_times_display) if khatma_times_display else 'غير محدد'}
- الختمات المكتملة: {data.get('completed_khatmas', 0)}
"""
            bot.reply_to(message, status_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in status: {e}")

# ========== دوال الجدولة الرئيسية ==========
def scheduler():
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            today = datetime.now().strftime("%d/%m/%Y")
            
            for chat_id, data in list(groups_data.items()):
                try:
                    # إرسال الصور
                    if (data.get("images_active", False) and 
                        now in data.get("image_times", []) and 
                        data.get("last_image_sent") != today):
                        if send_quran_pages(chat_id):
                            data["last_image_sent"] = today
                    
                    # إرسال الختمة
                    if (data.get("khatma_active", False) and 
                        now in data.get("khatma_times", []) and 
                        data.get("last_khatma_sent") != today):
                        if send_khatma_reminder(chat_id):
                            data["last_khatma_sent"] = today
                    
                    save_data()
                        
                except Exception as e:
                    print(f"Error in chat {chat_id}: {e}")
                    if "Forbidden" in str(e):  # إذا تم طرد البوت من المجموعة
                        del groups_data[chat_id]
                        save_data()
            
            time.sleep(30)  # التحقق كل 30 ثانية
            
        except Exception as e:
            print(f"Critical error in scheduler: {e}")
            bot.send_message(ADMIN_ID, f"🚨 البوت تعطل: {str(e)}")
            time.sleep(60)
            
if __name__ == "__main__":
    # حل نهائي لمشكلة التوكن المكرر
    from telebot import apihelper
    apihelper.SESSION_TIME_TO_LIVE = 60
    
    # بدء البوت مع التعامل مع الأخطاء
    while True:
        try:
            # بدء الجدولة في خيط منفصل
            threading.Thread(target=scheduler, daemon=True).start()
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(15)
