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

# تحميل البيانات
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
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
    """ الحصول على معلومات الصفحة من API """
    try:
        response = requests.get(f"https://api.alquran.cloud/v1/page/{page}/ar.alafasy")
        if response.status_code == 200:
            data = response.json()
            surah = data["data"]["surah"]["name"] if "surah" in data["data"] else "غير معروف"
            juz = data["data"]["juz"] if "juz" in data["data"] else "غير معروف"
            return {"surah": surah, "juz": juz}
        return {"surah": "غير معروف", "juz": "غير معروف"}
    except Exception as e:
        print(f"Error fetching page info: {e}")
        return {"surah": "غير معروف", "juz": "غير معروف"}

def get_image_url(page):
    """ الحصول على صورة الصفحة من API """
    return f"https://api.alquran.cloud/v1/page/{page}/ar.alafasy"

# ========== نظام الختمة بالآيات ==========
def get_random_ayah():
    """ جلب آية عشوائية من API """
    try:
        response = requests.get("https://api.alquran.cloud/v1/ayah/random/ar.alafasy")
        if response.status_code == 200:
            ayah = response.json()["data"]
            return f"{ayah['text']}\n(سورة {ayah['surah']['name']} - الآية {ayah['numberInSurah']})"
        return "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ"
    except Exception as e:
        print(f"Error fetching random ayah: {e}")
        return "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ"

# ========== أوامر البوت الأساسية ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
            if chat_id not in groups_data:
                groups_data[chat_id] = {
                    # إعدادات الصور
                    "current_page": 1,
                    "image_times": ["08:00", "20:00"],
                    "images_active": False,
                    "last_image_sent": None,
                    
                    # إعدادات الختمة
                    "current_part": 1,
                    "khatma_times": ["05:00", "15:00"],
                    "khatma_active": False,
                    "last_khatma_sent": None,
                    "completed_khatmas": 0
                }
                save_data()
            
            bot.reply_to(message, """
🕌 بوت ختمة القرآن الكريم - الإصدار المطور 🕌

⚙️ الأوامر المتاحة:

📖 نظام الصور:
/start_images - تفعيل إرسال الصور
/stop_images - إيقاف إرسال الصور
/set_image_times - ضبط أوقات الصور
/test_images - اختبار إرسال الصور

📜 نظام الختمة:
/start_khatma - تفعيل تذكير الختمة
/stop_khatma - إيقاف تذكير الختمة
/set_khatma_times - ضبط أوقات الختمة
/test_khatma - اختبار إرسال الختمة
/khatma_status - عرض عدد الختمات

⚙️ أخرى:
/status - عرض جميع الإعدادات
""")
    except Exception as e:
        print(f"Error in welcome handler: {e}")

def check_admin(chat_id):
    try:
        member = bot.get_chat_member(chat_id, bot.get_me().id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

# ========== دوال إرسال الصور ==========
def send_quran_pages(chat_id):
    try:
        data = groups_data[chat_id]
        current_page = data["current_page"]
        
        # إرسال الصفحتين معاً
        page1_info = get_page_info(current_page)
        page2_info = get_page_info(current_page + 1)
        
        media = [
            types.InputMediaPhoto(
                get_image_url(current_page),
                caption=f"📖 الصفحات {current_page}-{current_page+1}\nسورة {page1_info['surah']} | الجزء {page1_info['juz']}"
            ),
            types.InputMediaPhoto(
                get_image_url(current_page + 1),
                caption=""
            )
        ]
        
        bot.send_media_group(chat_id, media)
        
        # تحديث الصفحة التالية (صفحتين في كل مرة)
        new_page = current_page + 2
        if new_page > 604:
            new_page = 1
            bot.send_message(chat_id, "🎉 تم الانتهاء من القرآن الكريم!\nاللهم ارحمني بالقرآن واجعله لي نوراً وهدى ورحمة")
        
        groups_data[chat_id]["current_page"] = new_page
        save_data()
        
    except Exception as e:
        print(f"Error sending pages: {e}")
        bot.send_message(ADMIN_ID, f"⚠️ خطأ في إرسال الصفحات: {str(e)}")

@bot.message_handler(commands=['start_images'])
def start_images(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
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
            bot.send_message(chat_id, "🔍 جاري اختبار إرسال الصفحات...")
            send_quran_pages(chat_id)
    except Exception as e:
        print(f"Error in test_images: {e}")

# ========== دوال إرسال الختمة ==========
def send_khatma_reminder(chat_id):
    try:
        today = datetime.now().strftime("%d/%m/%Y")
        part = (groups_data[chat_id].get("current_part", 1) % 30) or 30
        
        message = f"""
🕌 **تذكير ورد اليوم**  
السلام عليكم ورحمة الله وبركاته  

📅 التاريخ: {today}  
📖 الجزء: {part} من 30  
🔄 الختمات المكتملة: {groups_data[chat_id].get("completed_khatmas", 0)}  

✨ آية اليوم:  
{get_random_ayah()}  

اللهم اجعل القرآن ربيع قلوبنا.
"""
        bot.send_message(chat_id, message)
        
        if part == 30:
            bot.send_message(chat_id, "🎉 *تهانينا!* لقد أكملت ختمة كاملة!\nاللهم ارزقنا تلاوته آناء الليل وأطراف النهار")
            groups_data[chat_id]["completed_khatmas"] += 1
        
        groups_data[chat_id]["current_part"] = part + 1
        save_data()
        
    except Exception as e:
        print(f"Error in khatma reminder: {e}")
        bot.send_message(ADMIN_ID, f"⚠️ خطأ في إرسال الختمة: {str(e)}")

@bot.message_handler(commands=['start_khatma'])
def start_khatma(message):
    try:
        chat_id = str(message.chat.id)
        if check_admin(chat_id):
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
            send_khatma_reminder(chat_id)
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
            status_text = f"""
⚙️ الإعدادات الحالية:

📖 نظام الصور:
- الحالة: {'✅ مفعل' if data.get('images_active', False) else '❌ معطل'}
- الصفحة الحالية: {data.get('current_page', 1)}
- أوقات الإرسال: {', '.join(data.get('image_times', [])) or 'غير محدد'}

📜 نظام الختمة:
- الحالة: {'✅ مفعل' if data.get('khatma_active', False) else '❌ معطل'}
- الجزء الحالي: {data.get('current_part', 1)}
- أوقات الإرسال: {', '.join(data.get('khatma_times', [])) or 'غير محدد'}
- الختمات المكتملة: {data.get('completed_khatmas', 0)}
"""
            bot.reply_to(message, status_text)
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
                    if data["images_active"] and now in data["image_times"] and data["last_image_sent"] != now:
                        send_quran_pages(chat_id)
                        data["last_image_sent"] = now
                    
                    # إرسال الختمة
                    if data["khatma_active"] and now in data["khatma_times"] and data["last_khatma_sent"] != today:
                        send_khatma_reminder(chat_id)
                        data["last_khatma_sent"] = today
                    
                    save_data()
                        
                except Exception as e:
                    print(f"Error in chat {chat_id}: {e}")
                    if "Forbidden" in str(e):
                        del groups_data[chat_id]
                        save_data()
            
            time.sleep(30)
            
        except Exception as e:
            print(f"Critical error in scheduler: {e}")
            bot.send_message(ADMIN_ID, f"🚨 البوت تعطل: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    from telebot import apihelper
    apihelper.SESSION_TIME_TO_LIVE = 60
    
    scheduler_thread = threading.Thread(target=scheduler, daemon=True)
    scheduler_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            bot.send_message(ADMIN_ID, f"⚠️ خطأ في تشغيل البوت: {str(e)}")
            time.sleep(15)
