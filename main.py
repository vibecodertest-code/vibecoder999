# File: main.py — основной бот FAQ-Telegram-бот (логика меню, FAQ, заявки, уведомления админу)

import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

# Загрузка переменных из .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Проверка наличия токена и ID админа при запуске
if not TELEGRAM_TOKEN:
    raise ValueError("Ошибка: переменная TELEGRAM_TOKEN не найдена в файле .env")
if not ADMIN_CHAT_ID:
    raise ValueError("Ошибка: переменная ADMIN_CHAT_ID не найдена в файле .env")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise ValueError("Ошибка: ADMIN_CHAT_ID должен быть целым числом (например, 123456789)")

# Состояния для ConversationHandler (форма заявки)
NAME, CONTACT = range(2)

# Клавиатура главного меню
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("FAQ"), KeyboardButton("Оставить заявку")],
        [KeyboardButton("Позвать человека")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура "В меню"
def get_menu_button():
    keyboard = [[KeyboardButton("В меню")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура FAQ с кнопками-вопросами
def get_faq_keyboard():
    keyboard = [
        [KeyboardButton("❓ Как оплатить?")],
        [KeyboardButton("📦 Доставка")],
        [KeyboardButton("🔄 Возврат товара")],
        [KeyboardButton("💰 Есть ли скидки?")],
        [KeyboardButton("В меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Словарь FAQ (вопрос → ответ)
FAQ_DICT = {
    "❓ Как оплатить?": "Вы можете оплатить картой на сайте или переводом по реквизитам. Напишите 'заявка', и мы пришлём счёт.",
    "📦 Доставка": "Доставка от 2 до 5 дней. Стоимость — 300 рублей.",
    "🔄 Возврат товара": "Возврат товара возможен в течение 14 дней. Напишите заявку, и менеджер свяжется с вами.",
    "💰 Есть ли скидки?": "Скидки для постоянных клиентов от 5% до 15%. Подробности в заявке.",
}

# Функция сохранения заявки в leads.csv
def save_lead_to_csv(name, contact, user_id, username):
    file_exists = os.path.isfile("leads.csv")
    with open("leads.csv", "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["created_at", "name", "contact", "tg_user_id", "tg_username"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "contact": contact,
            "tg_user_id": user_id,
            "tg_username": username
        })

# Команда /start
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Здравствуйте! Я бот-помощник.\n\n"
        "Я отвечу на частые вопросы, приму заявку или позову человека.\n\n"
        "Выберите действие в меню:",
        reply_markup=get_main_keyboard()
    )

# Обработчик текстовых сообщений (меню и навигация)
async def handle_message(update: Update, context):
    text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "Нет username"

    # Кнопка "В меню" — очищаем состояние и возвращаем в главное меню
    if text == "В меню":
        context.user_data.clear()
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_keyboard()
        )
        return

    # FAQ — показываем кнопки с вопросами
    if text == "FAQ":
        await update.message.reply_text(
            "Выберите интересующий вас вопрос:",
            reply_markup=get_faq_keyboard()
        )
        return

    # Проверяем, есть ли вопрос в словаре FAQ
    if text in FAQ_DICT:
        await update.message.reply_text(
            f"📖 {FAQ_DICT[text]}\n\n"
            "Выберите другой вопрос или нажмите 'В меню'.",
            reply_markup=get_faq_keyboard()
        )
        return

    # Оставить заявку — запускаем диалог (возвращаем None, чтобы ConversationHandler перехватил)
    if text == "Оставить заявку":
        return None

    # Позвать человека
    if text == "Позвать человека":
        await update.message.reply_text(
            "Ок, передал команде. Скоро с вами свяжутся.",
            reply_markup=get_main_keyboard()
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 Пользователь позвал человека!\n\n"
                 f"ID: {user_id}\n"
                 f"Username: @{username}"
        )
        return

    # Если ничего не подошло — предложить меню
    await update.message.reply_text(
        "Пожалуйста, используйте кнопки меню.",
        reply_markup=get_main_keyboard()
    )

# ConversationHandler для формы заявки
async def ask_name(update: Update, context):
    await update.message.reply_text("Как вас зовут?", reply_markup=get_menu_button())
    return NAME

async def ask_contact(update: Update, context):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым. Введите имя:")
        return NAME
    context.user_data["lead_name"] = name
    await update.message.reply_text(
        "Укажите контакт для связи (телефон, Telegram @username или email):"
    )
    return CONTACT

async def save_lead(update: Update, context):
    contact = update.message.text.strip()
    if not contact:
        await update.message.reply_text("Контакт не может быть пустым. Укажите контакт:")
        return CONTACT

    name = context.user_data["lead_name"]
    user_id = update.effective_user.id
    username = update.effective_user.username or "Нет username"

    save_lead_to_csv(name, contact, user_id, username)

    await update.message.reply_text(
        "✅ Заявка принята! Мы свяжемся с вами в ближайшее время.\n\n"
        "Вернуться в меню — нажмите 'В меню'.",
        reply_markup=get_menu_button()
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📋 Новая заявка!\n\n"
             f"Имя: {name}\n"
             f"Контакт: {contact}\n"
             f"TG ID: {user_id}\n"
             f"Username: @{username}"
    )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_to_menu(update: Update, context):
    if update.message.text == "В меню":
        context.user_data.clear()
        await update.message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    return None

# Основная функция
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Оставить заявку$"), ask_name)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_lead)],
        },
        fallbacks=[MessageHandler(filters.Regex("^В меню$"), cancel_to_menu)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен и работает (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()