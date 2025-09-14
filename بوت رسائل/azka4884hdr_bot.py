#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت الأذكار في ملف واحد
- يعمل بالـ polling
- يتعرّف على القنوات والمجموعات التي هو فيها
- لكل دردشة يتم إنشاء مهمة مسماة باسم chat_id ترسل ذكر كل ساعتين
- يحذف الرسالة السابقة إن أمكن ثم يرسل الذكر التالي
- التوكن مدمج داخل الملف كما طلبت
"""
import logging
from typing import Dict, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# ======= ضع التوكن هنا (كما طلبت) =======
BOT_TOKEN = "8402234547:AAEoQZWPToTRkdHUc5qvy91JQB5619QUG9U"
# ==========================================

# إعداد اللوق
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("singlefile_azkar_bot")

# قائمة الأذكار — عدّلها متى شئت
AZKAR_LIST = [
    "اللهم بك أصبحنا وبك أمسينا وبك نحيى وبك نموت وإليك النشور",
    "اللهم أنت ربي لا إله إلا أنت خلقتني وأنا عبدك فأغفر لي",
    "لا إله إلا الله وحده لا شريك له له الملك وله الحمد وهو على كل شيء قدير",
    "آية الكرسي",
    "يا حي يا قيوم برحمتك أستغيث أصلح لي شأني كله ولا تكلني إلى نفسي",
    "بسم الله الذي لا يضر مع اسمه شيء في الأرض ولا في السماء وهو السميع العليم",
    "اللهم إني أسألك من الخير كله عاجله وآجله",
    "اللهم أصلح لي ديني الذي هو عصمة أمري",
    "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار",
    "يا مقلب القلوب ثبت قلبي على دينك",
    "رب اغفر لي وتب علي إنك أنت التواب الغفور",
    "اللهم صل وسلم على نبينا محمد وآله وصحبه أجمعين",
]

class SimpleAzkarBot:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(self.token).build()
        # حالة كل دردشة: مؤشر ذكر (index)
        self.chat_states: Dict[int, int] = {}
        self.setup_handlers()

    def setup_handlers(self) -> None:
        # أمر start
        self.application.add_handler(CommandHandler("start", self.start))
        # تتبع إضافات البوت وتغير الحالة في المجموعات/القنوات
        self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
        # التقاط منشورات القنوات والرسائل في المجموعات/السوبر جروب
        channel_post_filter = filters.UpdateType.CHANNEL_POST
        group_msg_filter = (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP) & ~filters.COMMAND
        # ندمج الفلترين في معالج واحد ليشغّل نفس المنطق
        self.application.add_handler(MessageHandler(channel_post_filter | group_msg_filter, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """رد ترحيبي في المحادثة الخاصة أو رسالة تأكيد في المجموعة إن أمكن"""
        try:
            chat = update.effective_chat
            if chat and chat.type == "private":
                await update.message.reply_text("أهلاً بك\nأنا بوت الأذكار سأرسل ذكرًا كل ساعتين للمجموعات والقنوات التي أُضيف إليها")
            else:
                if update.message:
                    await update.message.reply_text("بوت الأذكار جاهز سيتم إرسال الأذكار كل ساعتين")
        except Exception:
            logger.debug("تعذّر إرسال رسالة start وربما نوع القناة لا يسمح بالرد")

    def get_next_zikr(self, chat_id: int) -> str:
        """إرجاع الذكر التالي وتحديث مؤشر الدردشة"""
        if chat_id not in self.chat_states:
            self.chat_states[chat_id] = 0
        idx = self.chat_states[chat_id]
        zikr = AZKAR_LIST[idx]
        self.chat_states[chat_id] = (idx + 1) % len(AZKAR_LIST)
        return zikr

    async def send_zikr(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        الدالة التي يناديها job_queue
        تحذف الرسالة السابقة (إذا محفوظة) ثم ترسل الذكر الجديد وتحفظ معرف الرسالة
        """
        job = context.job
        chat_id: Optional[int] = getattr(job, "chat_id", None)
        if chat_id is None:
            return

        # الحصول على آخر معرف رسالة محفوظ
        last_msg_id = None
        if getattr(job, "data", None) and isinstance(job.data, dict):
            last_msg_id = job.data.get("last_message_id")

        try:
            if last_msg_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
                except Exception as e:
                    # تجاهل الأخطاء الشائعة مثل عدم وجود صلاحية الحذف أو محذوف مسبقاً
                    logger.debug(f"لم أتمكن من حذف الرسالة السابقة في {chat_id} سبب: {e}")

            zikr = self.get_next_zikr(chat_id)
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=f"📿 ذكر ودعاء\n\n{zikr}",
                parse_mode=ParseMode.HTML,
            )
            # حفظ معرف الرسالة داخل data الخاصة بالمهمة
            job.data = {"last_message_id": sent.message_id}
        except Exception as e:
            msg = str(e).lower()
            logger.error(f"خطأ في إرسال ذكر إلى {chat_id}: {e}")
            # إذا طُرد البوت أو فقد الدردشة نوقف المهمة
            if "bot was kicked" in msg or "chat not found" in msg or "forbidden" in msg or "not enough rights" in msg:
                logger.info(f"إيقاف مهمة الدردشة {chat_id} لأن البوت فقد صلاحيات الوصول")
                try:
                    for j in context.job_queue.get_jobs_by_name(str(chat_id)):
                        j.schedule_removal()
                except Exception:
                    pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        عند أي منشور قناة أو رسالة مجموعة:
        - إذا لم توجد مهمة مسماة باسم chat_id نبدأ مهمة جديدة
        هذا يضمن تشغيل المهمة عند أول تفاعل أو عند إضافة البوت
        """
        chat = update.effective_chat
        if not chat:
            return
        chat_id = chat.id
        existing = context.job_queue.get_jobs_by_name(str(chat_id))
        if not existing:
            title = getattr(chat, "title", str(chat_id))
            logger.info(f"بدء مهمة جديدة للدردشة {title} id={chat_id}")
            self.start_zikr_job(context, chat_id, title)

    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        تتبع إضافة البوت أو تغيير حالته
        إذا أصبح البوت member أو administrator نبدأ المهمة للدردشة
        """
        if not update.chat_member:
            return
        chat = update.chat_member.chat
        if not chat:
            return
        new_member = update.chat_member.new_chat_member
        if not new_member:
            return
        # تأكد أن التحديث يخص البوت نفسه
        try:
            bot_id = context.bot.id
        except Exception:
            return
        if new_member.user.id != bot_id:
            return
        new_status = new_member.status
        if new_status in ("member", "administrator"):
            title = getattr(chat, "title", str(chat.id))
            logger.info(f"البوت أُضيف أو ترقّي في {title} id={chat.id} نبدأ المهمة")
            self.start_zikr_job(context, chat.id, title)

    def start_zikr_job(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, chat_title: str) -> None:
        """
        بدء مهمة متكررة مسماة باسم chat_id
        الفاصل الزمني 7200 ثانية = ساعتان
        """
        logger.info(f"بدء/تحديث مهمة الأذكار للدردشة {chat_title} ({chat_id})")
        # إزالة أي مهام سابقة بنفس الاسم
        for job in context.job_queue.get_jobs_by_name(str(chat_id)):
            job.schedule_removal()
        # شغّل المهمة ومرر data فارغة لحفظ last_message_id لاحقاً
        context.job_queue.run_repeating(
            callback=self.send_zikr,
            interval=7200,  # 2 ساعة
            first=1,        # بداية بعد ثانية واحدة لتفعيل سريع
            name=str(chat_id),
            chat_id=chat_id,
            data={},
        )

    def run(self) -> None:
        """تشغيل البوت بالـ polling"""
        logger.info("تشغيل بوت الأذكار بالـ polling")
        # تشغيل بشكل متواصل
        self.application.run_polling()

def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN.strip() == "":
        logger.error("لم يتم تهيئة التوكن BOT_TOKEN داخل الملف")
        return
    bot = SimpleAzkarBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
