#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت الأذكار - نسخة مدمجة التوكن ويتعرّف على القنوات والمجموعات
سلوك التطبيق
- عند إضافته لأي مجموعة أو قناة يبدأ مهمة ترسل ذكر كل ساعتين
- يحذف الرسالة السابقة إن أمكن قبل إرسال الذكر الجديد
- يتجاهل أخطاء الحذف أو فقد الصلاحيات بهدوء
- جاهز للرفع على Railway كـ worker
"""

import logging
from typing import Dict

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

# ====== التوكن مدمج حسب طلبك ======
BOT_TOKEN = "8402234547:AAEoQZWPToTRkdHUc5qvy91JQB5619QUG9U"
# ===================================

# إعداد اللوق
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("azkar_bot")

# قائمة الأذكار — ضع أو عدّل كما تحب
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
    """
    كلاس يدير البوت
    يخزن مؤشر كل دردشة في self.chat_states
    ويشغّل مهمة متكررة مسماة باسم chat_id لكي لا تتكرر المهام
    """

    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.chat_states: Dict[int, int] = {}
        self.setup_handlers()

    def setup_handlers(self) -> None:
        # أمر start للخاص والمجموعات
        self.application.add_handler(CommandHandler("start", self.start))

        # تتبع حالة البوت عند إضافته أو تغيّر صلاحيته في المجموعات/القنوات
        self.application.add_handler(
            ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
        )

        # استجابة عند أي منشور في القنوات أو رسالة في المجموعات/السوبرجروب
        # نستخدم UpdateType CHANNEL_POST للتأكد من التقاط منشورات القنوات
        channel_post_filter = filters.UpdateType.CHANNEL_POST
        group_msg_filter = (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP) & ~filters.COMMAND

        self.application.add_handler(
            MessageHandler(channel_post_filter | group_msg_filter, self.handle_message)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """رد ترحيبي بسيط في الخاص أو تأكيد في المجموعات"""
        try:
            chat = update.effective_chat
            if chat and chat.type == "private":
                await update.message.reply_text(
                    "أهلاً بك هذا بوت الأذكار سأرسل ذكرًا كل ساعتين للمجموعات والقنوات التي أُضاف إليها"
                )
            else:
                # في المجموعة نرد بشكل مبسّط إن أمكن
                if update.message:
                    await update.message.reply_text("بوت الأذكار جاهز سيتم إرسال الأذكار كل ساعتين")
        except Exception:
            logger.debug("تعذّر إرسال رسالة start (ربما في نوع قناة لا يسمح بالرد)")

    def get_next_zikr(self, chat_id: int) -> str:
        """إرجاع الذكر التالي مع تحديث مؤشر الدردشة"""
        if chat_id not in self.chat_states:
            self.chat_states[chat_id] = 0
        idx = self.chat_states[chat_id]
        zikr = AZKAR_LIST[idx]
        self.chat_states[chat_id] = (idx + 1) % len(AZKAR_LIST)
        return zikr

    async def send_zikr(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        المهمة المتكررة التي يضعها job_queue
        تحذف الرسالة السابقة إذا كان بإمكان البوت ثم ترسل الذكر الجديد
        """
        job = context.job
        chat_id = job.chat_id
        if chat_id is None:
            return

        # محاولة حذف الرسالة السابقة إن وُجدت
        last_msg_id = None
        if getattr(job, "data", None) and isinstance(job.data, dict):
            last_msg_id = job.data.get("last_message_id")

        try:
            if last_msg_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
                except Exception as e:
                    # قد لا تكون لديه صلاحية الحذف في القنوات أو حُذفت الرسالة مسبقاً
                    logger.debug(f"تعذر حذف الرسالة السابقة في {chat_id} سبب: {e}")

            # إرسال الذكر الجديد
            zikr = self.get_next_zikr(chat_id)
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=f"📿 ذكر ودعاء\n\n{zikr}",
                parse_mode=ParseMode.MARKDOWN,
            )

            # حفظ معرف الرسالة في بيانات المهمة لحذفها لاحقاً
            job.data = {"last_message_id": sent.message_id}

        except Exception as e:
            err = str(e).lower()
            logger.error(f"خطأ أثناء إرسال ذكر إلى {chat_id} — {e}")

            # حالات شائعة تستدعي إيقاف المهمة
            if "bot was kicked" in err or "chat not found" in err or "forbidden" in err:
                logger.info(f"إيقاف مهمة {chat_id} لأن البوت طُرد أو فقد صلاحية الوصول")
                try:
                    # إزالة المهمة المسماة بهذا chat_id إن وُجدت
                    for j in context.job_queue.get_jobs_by_name(str(chat_id)):
                        j.schedule_removal()
                except Exception:
                    pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        عند وجود منشور في قناة أو رسالة في مجموعة نبدأ المهمة إذا لم تكن تعمل
        يضمن هذا أن البوت يبدأ العمل عند إضافته أو عند أول تفاعل
        """
        chat = update.effective_chat
        if not chat:
            return

        chat_id = chat.id
        existing = context.job_queue.get_jobs_by_name(str(chat_id))
        if not existing:
            title = getattr(chat, "title", str(chat_id))
            logger.info(f"لم تُوجد مهمة سابقة، بدء مهمة جديدة للدردشة {title} ({chat_id})")
            self.start_zikr_job(context, chat_id, title)

    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        تتبع حالات البوت عند إضافته أو تغيّر صلاحيته
        سنشغّل المهمة عندما تكون حالة البوت member أو administrator
        """
        if not update.chat_member:
            return

        chat = update.chat_member.chat
        if not chat:
            return

        new_member = update.chat_member.new_chat_member
        if not new_member:
            return

        # تأكد أن التحديث عن البوت نفسه
        bot_id = context.bot.id
        if new_member.user.id != bot_id:
            return

        new_status = new_member.status
        # إذا أصبح البوت عضواً أو أدمن ابدأ المهمة
        if new_status in ("member", "administrator"):
            logger.info(f"تمت إضافة البوت أو ترقيته في {getattr(chat,'title',chat.id)} بدء المهمة")
            self.start_zikr_job(context, chat.id, getattr(chat, "title", str(chat.id)))

    def start_zikr_job(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, chat_title: str) -> None:
        """
        بدء مهمة متكررة مسماة باسم chat_id لتجنب التكرارات
        الفاصل = 7200 ثانية = ساعتان
        """
        logger.info(f"بدء/تحديث مهمة الأذكار للدردشة {chat_title} id={chat_id}")

        # إزالة أي مهام سابقة بنفس الاسم
        for job in context.job_queue.get_jobs_by_name(str(chat_id)):
            job.schedule_removal()

        # تشغيل المهمة المتكررة
        context.job_queue.run_repeating(
            callback=self.send_zikr,
            interval=7200,  # ساعتان
            first=1,        # نبدأ خلال ثانية واحدة لتفعيل المهمة فوراً
            name=str(chat_id),
            chat_id=chat_id,
            data={},        # حقل لحفظ last_message_id لاحقاً
        )

    def run(self) -> None:
        """تشغيل البوت بالـ polling"""
        logger.info("تشغيل بوت الأذكار (polling)")
        self.application.run_polling()

# ===== نقطة الدخول =====
def main() -> None:
    bot = SimpleAzkarBot(BOT_TOKEN)
    bot.run()


if __name__ == "__main__":
    main()
