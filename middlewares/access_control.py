from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

import config

class AccessControlMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if user_id is None: # Если по какой-то причине ID не найден
            print(f"DEBUG: User ID not found in event: {event}")
            return await event.answer("Произошла ошибка доступа. Попробуйте еще раз.") # Или просто return
        
        if user_id in config.ALLOWED_USER_IDS:
            return await handler(event, data) # Разрешаем выполнение хендлера
        else:
            print(f"DEBUG: Доступ запрещен для пользователя с ID: {user_id}")
            if isinstance(event, Message):
                await event.answer("Извините, у вас нет доступа к этому боту.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Извините, у вас нет доступа к этому функционалу.", show_alert=True)
            # Возвращаем None, чтобы остановить обработку события дальше
            return