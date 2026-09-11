from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

import config


def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if config.ALLOWED_USER_IDS and user_id not in config.ALLOWED_USER_IDS:
            await update.message.reply_text(
                "Kechirasiz, bu botdan foydalanishga ruxsatingiz yo'q."
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
