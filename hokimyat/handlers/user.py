from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.user import LoginState, TaskState
from utils.api import APIClient
from keyboards.reply import get_phone_number_kb, get_main_menu
from keyboards.inline import get_tasks_keyboard, get_task_detail_keyboard
from utils.api import verify_user, get_user_info, get_user_tasks, get_task_detail, submit_task_progress, download_telegram_file
from utils.logger import setup_logger
import os
import tempfile

logger = setup_logger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    try:
        response, status = await get_user_info(message.from_user.id)
        
        if status == 200 and response.get('status') == 'success':
            user = response.get('user', {})
            welcome_text = (
                f"Xush kelibsiz, {user.get('full_name', 'Foydalanuvchi')}!\n\n"
                f"Lavozim: {user.get('job_title_name', 'Mavjud emas')}\n"
                f"Mahalla: {user.get('mahalla_name', 'Mavjud emas')}\n"
                f"Tuman: {user.get('tuman_name', 'Mavjud emas')}"
            )
            await message.answer(welcome_text, reply_markup=get_main_menu())
            logger.info(f"User {message.from_user.id} logged in successfully")
        else:
            await state.set_state(LoginState.phone_number)
            await message.answer(
                "Assalomu alaykum! Botdan foydalanish uchun ro'yxatdan o'ting.\n"
                "Telefon raqamingizni yuboring:",
                reply_markup=get_phone_number_kb()
            )
            logger.info(f"User {message.from_user.id} started registration")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan /start buyrug'ini yuboring."
        )

@router.message(LoginState.phone_number)
async def process_phone(message: Message, state: FSMContext):
    """Process phone number"""
    try:
        if not message.contact and not message.text:
            await message.answer(
                "Iltimos, telefon raqamingizni yuboring yoki kiriting.\n"
                "Format: +998 XX XXX XX XX"
            )
            return

        phone = message.contact.phone_number if message.contact else message.text
        
        await state.update_data(phone_number=phone)
        await state.set_state(LoginState.jshir)
        await message.answer(
            "Endi JSHIR raqamingizni kiriting:\n"
            "Masalan: 12345678901234"
        )
        logger.info(f"User {message.from_user.id} provided phone number: {phone}")
    except Exception as e:
        logger.error(f"Error in process_phone: {e}")
        await message.answer(
            "Xatolik yuz berdi. Iltimos, qaytadan telefon raqamingizni yuboring."
        )


@router.message(LoginState.jshir)
async def process_jshir(message: Message, state: FSMContext):
    """Process JSHIR"""
    try:
        if not message.text:
            await message.answer("Iltimos, JSHIR raqamingizni kiriting.")
            return

        user_data = await state.get_data()
        phone = user_data.get('phone_number')

        processing_msg = await message.answer("Ma'lumotlar tekshirilmoqda...")

        try:
            response, status = await verify_user(phone, message.text, message.from_user.id)
            logger.info(f"Verify user response: {response}, status: {status}")
            
            if status == 200 and response.get('status') == 'success':
                user = response.get('user', {})
                
                await state.clear()
                
                welcome_text = (
                    f"Xush kelibsiz, {user.get('full_name', 'Foydalanuvchi')}!\n\n"
                    f"Lavozim: {user.get('job_title_name', 'Mavjud emas')}\n"
                    f"Mahalla: {user.get('mahalla_name', 'Mavjud emas')}\n"
                    f"Tuman: {user.get('tuman_name', 'Mavjud emas')}"
                )
                
                await processing_msg.delete()
                await message.answer(
                    welcome_text,
                    reply_markup=get_main_menu()
                )
                
                help_text = (
                    "🔍 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
                    "1️⃣ <b>Topshiriqlarni ko'rish</b>\n"
                    "   • 📋 Mening topshiriqlarim - faol topshiriqlarni ko'rish\n\n"
                    "2️⃣ <b>Topshiriq bilan ishlash</b>\n"
                    "   • ✅ Bajarildi - topshiriqni bajarilgan deb belgilash\n"
                    "   • 📝 Hisobot - topshiriq bo'yicha hisobot yuborish\n"
                    "   • 📊 Statistika - topshiriq statistikasini ko'rish\n\n"
                    "❓ Yordam kerak bo'lsa, /help buyrug'ini yuboring"
                )
                await message.answer(help_text, parse_mode="HTML")
                
                logger.info(f"User {message.from_user.id} successfully logged in")
                
            else:
                error_message = response.get('message', 'Xatolik yuz berdi')
                await processing_msg.delete()
                await message.answer(
                    f"{error_message}\n\n"
                    "Qaytadan urinish uchun /start buyrug'ini yuboring."
                )
                await state.clear()
                logger.warning(f"Login failed for phone: {phone}, JSHIR: {message.text}. Status: {status}")
                
        except Exception as e:
            await processing_msg.delete()
            await message.answer(
                "Serverda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.\n"
                "Qaytadan urinish uchun /start buyrug'ini yuboring."
            )
            await state.clear()
            logger.error(f"Error in verify_user request: {e}")
            
    except Exception as e:
        logger.error(f"Error in process_jshir: {e}")
        await message.answer(
            "Xatolik yuz berdi. Qaytadan urinish uchun /start buyrug'ini yuboring."
        )
        await state.clear()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    try:
        help_text = (
            "🔍 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
            "1️⃣ <b>Topshiriqlarni ko'rish</b>\n"
            "   • 📋 Mening topshiriqlarim - faol topshiriqlarni ko'rish\n\n"
            "2️⃣ <b>Topshiriq bilan ishlash</b>\n"
            "   • ✅ Bajarildi - topshiriqni bajarilgan deb belgilash\n"
            "   • 📝 Hisobot - topshiriq bo'yicha hisobot yuborish\n"
            "   • 📊 Statistika - topshiriq statistikasini ko'rish\n\n"
            "3️⃣ <b>Fayl yuborish</b>\n"
            "   • 📎 Rasm, PDF, Word, Excel va PowerPoint fayllarini yuborish mumkin\n\n"
            "❓ Qo'shimcha savollar bo'lsa, administrator bilan bog'laning"
        )
        await message.answer(help_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@router.message(F.text == "📋 Mening topshiriqlarim")
async def show_tasks(message: Message):
    """Show user's tasks"""
    try:
        tasks, status = await get_user_tasks(message.from_user.id)
        
        if status == 200 and tasks.get('status') == 'success':
            task_list = tasks.get('tasks', [])
            if task_list:
                pending_tasks = []
                in_progress_tasks = []
                other_tasks = []
                
                for task in task_list:
                    if task.get('status') == 'pending':
                        pending_tasks.append(task)
                    elif task.get('status') == 'in_progress':
                        in_progress_tasks.append(task)
                    else:
                        other_tasks.append(task)
                
                if pending_tasks:
                    await message.answer(
                        "⏳ <b>Kutilayotgan topshiriqlar:</b>",
                        parse_mode="HTML",
                        reply_markup=get_tasks_keyboard(pending_tasks)
                    )
                
                if in_progress_tasks:
                    await message.answer(
                        "🔄 <b>Jarayondagi topshiriqlar:</b>",
                        parse_mode="HTML",
                        reply_markup=get_tasks_keyboard(in_progress_tasks)
                    )
                
                if other_tasks:
                    await message.answer(
                        "📋 <b>Boshqa topshiriqlar:</b>",
                        parse_mode="HTML",
                        reply_markup=get_tasks_keyboard(other_tasks)
                    )
            else:
                await message.answer("Sizda hozircha faol topshiriqlar yo'q.")
        else:
            await message.answer("Topshiriqlarni olishda xatolik yuz berdi.")
    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@router.callback_query(F.data.startswith("task_view_"))
async def process_task_view(callback: CallbackQuery):
    try:
        task_id = int(callback.data.split('_')[2])
        task_data, status = await get_task_detail(task_id)
        
        if status == 200 and task_data.get('status') == 'success':
            task = task_data.get('task', {})
            
            deadline = task.get('deadline', '').split('T')[0]
            status_emoji = {
                'pending': '⏳',
                'in_progress': '🔄',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(task.get('status'), '⏳')
            
            message_text = (
                f"📌 <b>{task.get('title', 'Mavjud emas')}</b>\n\n"
                f"📝 <b>Tavsif:</b> {task.get('description', 'Mavjud emas')}\n"
                f"👤 <b>Yaratuvchi:</b> {task.get('creator_name', 'Mavjud emas')}\n"
                f"📅 <b>Muddati:</b> {deadline}\n"
                f"🔄 <b>Holati:</b> {status_emoji} {task.get('status_display', 'Mavjud emas')}\n"
                f"📊 <b>Bajarilish:</b> {task.get('percentage_count', 0)}%\n"
            )
            
            if task.get('status') == 'failed' and task.get('rejection_reason'):
                message_text += f"\n❌ <b>Rad etish sababi:</b> {task.get('rejection_reason')}\n"
            
            await callback.message.edit_text(
                message_text, 
                reply_markup=get_task_detail_keyboard(task_id, task.get('status')),
                parse_mode="HTML"
            )
            
            files = task.get('files', [])
            if files:
                try:
                    file_message = "📎 <b>Ilova qilingan fayllar:</b>\n\n"
                    for i, file in enumerate(files, 1):
                        file_url = file.get('file_url')
                        file_name = file.get('name')
                        file_type = file.get('file_type', '').lower()
                        
                        icon = '📄'
                        if file_type in ['jpg', 'jpeg', 'png', 'gif']:
                            icon = '🖼️'
                        elif file_type in ['pdf']:
                            icon = '📑'
                        elif file_type in ['doc', 'docx']:
                            icon = '📝'
                        elif file_type in ['xls', 'xlsx']:
                            icon = '📊'
                        elif file_type in ['ppt', 'pptx']:
                            icon = '📽️'
                        
                        file_message += f"{i}. {icon} <a href='{file_url}'>{file_name}</a>\n"
                    
                    await callback.message.answer(file_message, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error sending files: {e}")
                    await callback.message.answer("Fayllarni yuklashda xatolik yuz berdi.")
    except Exception as e:
        logger.error(f"Error in process_task_view: {e}")
        await callback.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", show_alert=True)

@router.callback_query(F.data == "tasks_list")
async def back_to_tasks(callback: CallbackQuery):
    """Handle back to tasks list button"""
    try:
        await callback.message.delete()
        await show_tasks(callback.message)
    except Exception as e:
        logger.error(f"Error in back_to_tasks: {e}")
        await callback.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", show_alert=True)