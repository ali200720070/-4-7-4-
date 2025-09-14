#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
بوت الأذكار البسيط
===============
- يرسل ذكرًا كل ساعتين في أي مجموعة يتم إضافته إليها
- يحذف الرسالة السابقة عند إرسال رسالة جديدة
- يعمل مع جميع إصدارات مكتبة التليجرام
- بدون أي تعقيدات أو إعدادات معقدة
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# تحميل مكتبات التليجرام
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ChatMemberHandler,
    ContextTypes,
)
from telegram.ext import filters

# --- إعدادات التسجيل ---
# ====================

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- قائمة الأذكار ---
# =================

AZKAR_LIST = [
    "🌸 اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ. (متفق عليه)",
    "🍃 اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ. (متفق عليه)",
    "🌿 لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ. (متفق عليه)",
    "🌸 ﴿اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَآ تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ ۚ لَهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ ۗ مَنْ ذَا الَّذِي يَشْفَعُ عِنْدَهُ إِلَّا بِإِذْنِهِ ۚ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ ۖ وَلَا يُحِيطُونَ بِشَيْءٍ مِنْ عِلْمِهِ إِلَّا بِمَا شَاءَ ۚ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ ۖ وَلَا يَئُودُهُ حِفْظُهُمَا ۚ وَهُوَ الْعَلِيُّ الْعَظِيمُ﴾ (البقرة:255)",
    "🌿 يَا حَيُّ يَا قَيُّومُ بِرَحْمَتِكَ أَسْتَغِيثُ، أَصْلِحْ لِي شَأْنِي كُلَّهُ، وَلَا تَكِلْنِي إِلَى نَفْسِي طَرْفَةَ عَيْنٍ. (متفق عليه)",
    "🍃 بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ. (ثلاث مرات) (رواه مسلم)",
    "🌸 اللَّهُمَّ إِنِّي أَسْأَلُكَ مِنَ الْخَيْرِ كُلِّهِ عَاجِلِهِ وَآجِلِهِ، مَا عَلِمْتُ مِنْهُ وَمَا لَمْ أَعْلَمْ، وَأَعُوذُ بِكَ مِنَ الشَّرِّ كُلِّهِ عَاجِلِهِ وَآجِلِهِ، مَا عَلِمْتُ مِنْهُ وَمَا لَمْ أَعْلَمْ. (رواه مسلم)",
    "🌿 اللَّهُمَّ أَصْلِحْ لِي دِينِي الَّذِي هُوَ عِصْمَةُ أَمْرِي، وَأَصْلِحْ لِي دُنْيَايَ الَّتِي فِيهَا مَعَاشِي، وَأَصْلِحْ لِي آخِرَتِي الَّتِي فِيهَا مَعَادِي. (متفق عليه)",
    "🍃 اللَّهُمَّ رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ. (متفق عليه)",
    "🌸 يَا مُقَلِّبَ الْقُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ. (رواه مسلم)",
    "🌿 رَبِّ اغْفِرْ لِي وَتُبْ عَلَيَّ إِنَّكَ أَنْتَ التَّوَّابُ الغَفُورُ. (متفق عليه)",
    "🍃 اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ ﷺ وَعَلَى آلِهِ وَصَحْبِهِ أَجْمَعِينَ. (متفق عليه)",
]

# --- الفئة الرئيسية ---
# ==================

class SimpleAzkarBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.chat_states = {}  # تخزين حالة كل دردشة (المؤشر الحالي)
        self.setup_handlers()
    
    def setup_handlers(self):
        """إضافة المعالجات الضرورية"""
        self.application.add_handler(CommandHandler("start", self.start))
        # تتبع إضافة البوت إلى المجموعات أو القنوات
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
        # بدء المهمة عند إرسال أي رسالة في قناة أو مجموعة
        self.application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST | filters.UpdateType.MESSAGE, self.handle_message))
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """رسالة ترحيب بسيطة"""
        await update.message.reply_text(
            "أهلاً بك! أنا بوت الأذكار، سأرسل ذكرًا كل ساعتين في هذه المجموعة."
        )
    
    def get_next_zikr(self, chat_id):
        """الحصول على الذكر التالي مع تحديث المؤشر"""
        if chat_id not in self.chat_states:
            self.chat_states[chat_id] = 0
        
        current_index = self.chat_states[chat_id]
        zikr = AZKAR_LIST[current_index]
        
        # تحديث المؤشر للذكر التالي
        self.chat_states[chat_id] = (current_index + 1) % len(AZKAR_LIST)
        
        return zikr
    
    async def send_zikr(self, context: ContextTypes.DEFAULT_TYPE):
        """إرسال الذكر وحذف الرسالة السابقة"""
        job = context.job
        chat_id = job.chat_id
        
        try:
            # حذف الرسالة السابقة إذا وجدت
            if job.data and 'last_message_id' in job.data:
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=job.data['last_message_id']
                    )
                except Exception:
                    pass  # تجاهل أخطاء الحذف
            
            # إرسال الذكر الجديد
            zikr = self.get_next_zikr(chat_id)
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"📿 *ذكر ودعاء*\n\n{zikr}",
                parse_mode="Markdown"
            )
            
            # حفظ معرف الرسالة لحذفها لاحقًا
            job.data = {'last_message_id': message.message_id}
            
        except Exception as e:
            error_msg = str(e).lower()
            # التحقق من أخطاء شائعة
            if "bot was kicked" in error_msg or "chat not found" in error_msg or "not found" in error_msg:
                # تم إزالة البوت من المجموعة
                context.job_queue.scheduler.remove_job(job.id)
            else:
                logger.error(f"خطأ في إرسال الذكر إلى {chat_id}: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل الجديدة في المجموعات أو القنوات لبدء المهمة إذا لم تكن موجودة"""
        chat = update.effective_chat
        if chat:
            chat_id = chat.id
            # التأكد من عدم وجود مهمة حالية قبل البدء
            if not context.job_queue.get_jobs_by_name(str(chat_id)):
                self.start_zikr_job(context, chat_id, chat.title)
    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تتبع إضافة البوت إلى المجموعات الجديدة"""
        if not update.chat_member:
            return
        
        chat = update.chat_member.chat
        chat_id = chat.id
        new_status = update.chat_member.new_chat_member.status
        bot_id = context.bot.id
        
        # التأكد أن التحديث خاص بالبوت
        if update.chat_member.new_chat_member.user.id != bot_id:
            return
        
        if new_status in ["member", "administrator"]:
            # تم إضافة البوت إلى المجموعة
            self.start_zikr_job(context, chat_id, chat.title)

    def start_zikr_job(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, chat_title: str):
        """بدء مهمة إرسال الأذكار لدردشة معينة"""
        logger.info(f"بدء مهمة الأذكار لـ {chat_title} ({chat_id})")

        # إزالة أي مهام موجودة مسبقًا لهذه الدردشة
        for job in context.job_queue.get_jobs_by_name(str(chat_id)):
            job.schedule_removal()

        # بدء مهمة إرسال الأذكار (كل 30 ثانية)
        context.job_queue.run_repeating(
            self.send_zikr,
            interval=7200,  # 7200 ثانية = ساعتان
            first=1,      # يبدأ بعد ثانية واحدة من التشغيل
            chat_id=chat_id,
            name=str(chat_id)
        )
    def run(self):
        """تشغيل البوت"""
        logger.info("يتم تشغيل بوت الأذكار...")
        self.application.run_polling()

# --- الدالة الرئيسية ---
# ===================

def main():
    # تحميل متغيرات البيئة من ملف .env
    load_dotenv()

    # تحميل رمز البوت من متغير البيئة
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("يرجى تعيين متغير البيئة BOT_TOKEN")
        return
    
    bot = SimpleAzkarBot(token)
    bot.run()

if __name__ == '__main__':
    main()