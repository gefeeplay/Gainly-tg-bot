import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Создание директории для логов, если её нет
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Настройка логирования
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# Настройка root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Обработчик для записи в файл с ротацией
file_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, 'bot.log'),
    maxBytes=10 * 1024 * 1024,  # 10 МБ
    backupCount=5,  # Хранить до 5 файлов бэкапов
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format, date_format))

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format, date_format))

# Добавление обработчиков
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Отключение избыточного логирования httpx (HTTP запросы к Telegram API)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Получение logger для текущего модуля
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_APP_FORMAT, SELECTING_FEEDBACK_TYPE, ENTERING_MESSAGE = range(3)

# Словарь для хранения данных формы обратной связи
user_data = {}

# Чтобы узнать свой chat_id, отправьте боту команду /get_chat_id
# 909844183 - Миша
RECIPIENTS = {
    ('android', 'wishes'): 844693564,  #@Yur4Arkhipov
    ('android', 'features'): 946851965,  #@s0rg1
    ('miniapp', 'wishes'): 909844183,  #@gefeeRu
    ('miniapp', 'features'): 946851965,  #@s0rg1
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    welcome_message = """
🤖 Добро пожаловать в Gainly App!

📋 Доступные команды:
/start - Показать информацию о боте и командах
/feedback - Отправить обратную связь
/get_chat_id - Получить ваш chat_id (для разработчиков)

💡 Используйте /feedback для отправки ваших предложений и пожеланий!
    """
    await update.message.reply_text(welcome_message)


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /get_chat_id - получение chat_id пользователя"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username or "не указан"
    
    message = (
        f"📋 Ваши данные:\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"User ID: `{user_id}`\n"
        f"Username: @{username}\n\n"
        f"Используйте Chat ID для настройки получателей в коде бота."
    )
    await update.message.reply_text(message, parse_mode='Markdown')


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /feedback - начало формы обратной связи"""
    user_id = update.effective_user.id
    username = update.effective_user.username or 'без_username'
    logger.info(f"Начало формы обратной связи: пользователь {user_id} (@{username})")
    
    # Инициализация данных пользователя
    user_data[user_id] = {}
    
    keyboard = [
        [
            InlineKeyboardButton("📱 Android", callback_data='appformat_android'),
            InlineKeyboardButton("🌐 Mini App Telegram", callback_data='appformat_miniapp'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 Форма обратной связи\n\n"
        "Шаг 1/3: Выберите формат приложения:",
        reply_markup=reply_markup
    )
    
    return SELECTING_APP_FORMAT


async def app_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора формата приложения"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    app_format = query.data.split('_')[1]  # 'android' или 'miniapp'
    
    user_data[user_id]['app_format'] = app_format
    
    keyboard = [
        [
            InlineKeyboardButton("💭 Пожелания", callback_data='feedbacktype_wishes'),
            InlineKeyboardButton("✨ Предложение новых функций", callback_data='feedbacktype_features'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    app_format_text = "📱 Android" if app_format == 'android' else "🌐 Mini App Telegram"
    await query.edit_message_text(
        f"📝 Форма обратной связи\n\n"
        f"Выбрано: {app_format_text}\n\n"
        f"Шаг 2/3: Выберите тип обратной связи:",
        reply_markup=reply_markup
    )
    
    return SELECTING_FEEDBACK_TYPE


async def feedback_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора типа обратной связи"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    feedback_type = query.data.split('_')[1]  # 'wishes' или 'features'
    
    user_data[user_id]['feedback_type'] = feedback_type
    
    feedback_type_text = "💭 Пожелания" if feedback_type == 'wishes' else "✨ Предложение новых функций"
    app_format_text = "📱 Android" if user_data[user_id]['app_format'] == 'android' else "🌐 Mini App Telegram"
    
    await query.edit_message_text(
        f"📝 Форма обратной связи\n\n"
        f"Формат приложения: {app_format_text}\n"
        f"Тип обратной связи: {feedback_type_text}\n\n"
        f"Шаг 3/3: Введите ваше сообщение:"
    )
    
    return ENTERING_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик получения текстового сообщения"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text(
            "❌ Сессия истекла. Пожалуйста, начните заново с команды /feedback"
        )
        return ConversationHandler.END
    
    message_text = update.message.text
    user_data[user_id]['message'] = message_text
    
    # Определение получателя
    app_format = user_data[user_id]['app_format']
    feedback_type = user_data[user_id]['feedback_type']
    recipient = RECIPIENTS.get((app_format, feedback_type))
    
    # Проверка наличия получателя
    if recipient is None:
        await update.message.reply_text(
            "❌ Получатель не настроен. Обратитесь к администратору."
        )
        del user_data[user_id]
        return ConversationHandler.END
    
    # Формирование сообщения для отправки
    app_format_text = "📱 Android" if app_format == 'android' else "🌐 Mini App Telegram"
    feedback_type_text = "💭 Пожелания" if feedback_type == 'wishes' else "✨ Предложение новых функций"
    user_info = f"От: @{update.effective_user.username or 'без_username'} (ID: {user_id})"
    
    feedback_message = (
        f"📝 Новая обратная связь\n\n"
        f"Формат приложения: {app_format_text}\n"
        f"Тип обратной связи: {feedback_type_text}\n"
        f"{user_info}\n\n"
        f"Сообщение:\n{message_text}"
    )
    
    # Отправка сообщения получателю
    try:
        logger.info(
            f"Отправка обратной связи: пользователь {user_id} (@{update.effective_user.username or 'без_username'}), "
            f"формат: {app_format}, тип: {feedback_type}, получатель: {recipient}"
        )
        logger.info(f"Содержимое сообщения:\n{feedback_message}")
        await context.bot.send_message(
            chat_id=recipient,
            text=feedback_message
        )
        logger.info(f"Обратная связь успешно отправлена получателю {recipient}")
        await update.message.reply_text(
            "✅ Спасибо! Ваше сообщение успешно отправлено."
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения получателю {recipient}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Произошла ошибка при отправке сообщения. Попробуйте позже.\n"
            f"Ошибка: {str(e)}"
        )
    
    # Очистка данных пользователя
    del user_data[user_id]
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик отмены формы"""
    user_id = update.effective_user.id
    
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text("❌ Форма обратной связи отменена.")
    return ConversationHandler.END


def main() -> None:
    """Основная функция запуска бота"""
    # Получение токена из переменных окружения
    TOKEN = os.getenv('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("BOT_TOKEN не найден в переменных окружения. Убедитесь, что файл .env существует и содержит BOT_TOKEN.")
        raise ValueError("BOT_TOKEN не установлен. Создайте файл .env и добавьте BOT_TOKEN=ваш_токен")
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик команды /get_chat_id
    application.add_handler(CommandHandler("get_chat_id", get_chat_id))
    
    # ConversationHandler для формы обратной связи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("feedback", feedback)],
        states={
            SELECTING_APP_FORMAT: [CallbackQueryHandler(app_format_callback, pattern='^appformat_')],
            SELECTING_FEEDBACK_TYPE: [CallbackQueryHandler(feedback_type_callback, pattern='^feedbacktype_')],
            ENTERING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()


