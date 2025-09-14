#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت الأذكار المبسّط - نسخة مدمج معها التوكن مباشرة
جاهز للرفع على Railway أو أي استضافة أخرى
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

# --- التوكن الخاص بالبوت ---
BOT_TOKEN = "8402234547:AAEoQZWPToTRkdHUc5qvy91JQB5619QUG9U"

# --- إعدادات اللوج ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("azkar_bot")

# --- قائمة الأذكار ---
AZKAR_LIST = [
    "اللهم بك أصبحنا وبك أمسينا وبك نحيى وبك نموت وإليك النشور",
    "اللهم أنت ربي لا إله إلا أنت خلقتني وأنا عبدك ... اغفر لي",
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
        self.application = Application.builder().token(token).build()
        self.chat_states: Dict[int, int] = {}
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(
            ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
        )
        self.application.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_message)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text(
                "أهلاً بك! أنا بوت الأذكار سأرسل ذكرًا كل ساعتين في المجموعات"
            )

    def get_next_zikr(self, chat_id: int) -> str:
        if chat_id not in self.chat_states:
            self.chat_states[chat_id] = 0
        idx = self.chat_states[chat_id]
        zikr = AZKAR_LIST[idx]
        self.chat_states[chat_id] = (idx + 1) % len(AZKAR_LIST)
        return zikr

    async def send_zikr(self, context: ContextTypes.DEFAULT_TYPE):
        job = context.job
        chat_id = job.chat_id
        if not chat_id:
            return

        last_msg_id = job.data.get("last_message_id") if job.data else None
        try:
            if last_msg_id:
                try:
                    await context.bot.delete_message(chat_id, last_msg_id)
                except Exception:
                    pass

            zikr = self.get_next_zikr(chat_id)
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"📿 ذكر ودعاء\n\n{zikr}",
                parse_mode=ParseMode.MARKDOWN,
            )
            job.data = {"last_message_id": msg.message_id}
        except Exception as e:
            logger.error(f"خطأ في الإرسال {chat_id}: {e}")
            if "kicked" in str(e).lower() or "not found" in str(e).lower():
                for j in context.job_queue.get_jobs_by_name(str(chat_id)):
                    j.schedule_removal()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat:
            return
        chat_id = chat.id
        if not context.job_queue.get_jobs_by_name(str(chat_id)):
            self.start_zikr_job(context, chat_id, getattr(chat, "title", ""))

    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.chat_member:
            return
        bot_id = context.bot.id
        if update.chat_member.new_chat_member.user.id != bot_id:
            return
        status = update.chat_member.new_chat_member.status
        chat = update.chat_member.chat
        if status in ("member", "administrator"):
            self.start_zikr_job(context, chat.id, getattr(chat, "title", ""))

    def start_zikr_job(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, title: str):
        logger.info(f"بدء مهمة الأذكار للدردشة {title} ({chat_id})")
        for j in context.job_queue.get_jobs_by_name(str(chat_id)):
            j.schedule_removal()
        context.job_queue.run_repeating(
            self.send_zikr, interval=7200, first=1, name=str(chat_id), chat_id=chat_id, data={}
        )

    def run(self):
        logger.info("تشغيل البوت...")
        self.application.run_polling()


def main():
    bot = SimpleAzkarBot(BOT_TOKEN)
    bot.run()


if __name__ == "__main__":
    main()
