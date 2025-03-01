from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def get_phone_number_kb() -> ReplyKeyboardMarkup:
    """Generate keyboard with phone number request button"""
    keyboard = [
        [
            KeyboardButton(
                text="📱 Telefon raqamni yuborish",
                request_contact=True
            )
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_main_menu() -> ReplyKeyboardMarkup:
    """Generate main menu keyboard"""
    keyboard = [
        [
            KeyboardButton(text="📋 Mening topshiriqlarim")
        ],
        [
            KeyboardButton(text="📊 Statistika"),
            KeyboardButton(text="⚙️ Sozlamalar")
        ],
        [
            KeyboardButton(text="📞 Yordam")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_kb(with_finish: bool = False) -> ReplyKeyboardMarkup:
    """Generate cancel keyboard"""
    keyboard = []
    
    if with_finish:
        keyboard.append([
            KeyboardButton(text="✅ Yuborishni yakunlash")
        ])
        
    keyboard.append([
        KeyboardButton(text="❌ Bekor qilish")
    ])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)