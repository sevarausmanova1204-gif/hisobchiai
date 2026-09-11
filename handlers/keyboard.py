from telegram import ReplyKeyboardMarkup

BTN_REPORT = "📊 Hisobot"
BTN_BALANCE = "💼 Balans"
BTN_DASHBOARD = "📈 Dashboard"
BTN_ADVISOR = "🧠 AI Maslahatchi"
BTN_HELP = "ℹ️ Yordam"

INPUT_PLACEHOLDER = "Masalan: bugun taksiga 25 ming berdim"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [BTN_REPORT, BTN_BALANCE],
        [BTN_DASHBOARD, BTN_ADVISOR],
        [BTN_HELP],
    ],
    resize_keyboard=True,
    input_field_placeholder=INPUT_PLACEHOLDER,
)
