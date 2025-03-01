from aiogram import Router, F, Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models.base import User, Channel
from keyboards import inline
from services.broadcaster import broadcast_message
from services.excel import generate_users_excel
from utils.logger import setup_logger
from keyboards.inline import get_task_management_kb, get_task_status_kb
from utils.api import get_user_tasks, submit_task_progress
from config import ADMIN_IDS


logger = setup_logger(__name__)
router = Router()

MAIN_ADMIN_IDS = [6236467772, 5645086563]

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_channel = State()
    waiting_admin_id = State()

async def is_admin(user_id: int) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        return user and user.is_admin
    finally:
        db.close()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    await message.reply(
        "Admin Panel",
        reply_markup=inline.admin_keyboard()
    )

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.telegram_id.isnot(None)).count()
        admin_count = db.query(User).filter(User.is_admin == True).count()
        
        stats = (
            f"📊 Statistika:\n\n"
            f"Jami foydalanuvchilar: {total_users}\n"
            f"Faol foydalanuvchilar: {active_users}\n"
            f"Adminlar soni: {admin_count}"
        )
        
        await callback.message.edit_text(
            stats,
            reply_markup=inline.admin_keyboard()
        )
    finally:
        db.close()

@router.callback_query(F.data == "admin_add")
async def add_admin_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    await callback.message.answer(
        "Yangi admin ID raqamini yuboring:"
    )
    await state.set_state(AdminStates.waiting_admin_id)

@router.message(AdminStates.waiting_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        new_admin_id = int(message.text)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == new_admin_id).first()
            if not user:
                await message.reply("Bu foydalanuvchi tizimda ro'yxatdan o'tmagan!")
                return
            
            if user.is_admin:
                await message.reply("Bu foydalanuvchi allaqachon admin!")
                return
            
            await message.reply(
                f"Foydalanuvchini admin qilishni tasdiqlaysizmi?\n\n"
                f"👤 {user.full_name}\n"
                f"📞 {user.phone_number}\n"
                f"🏢 {user.mahalla.name}",
                reply_markup=inline.confirm_admin_keyboard(new_admin_id)
            )
        finally:
            db.close()
    except ValueError:
        await message.reply("Noto'g'ri ID format!")
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("confirm_admin:"))
async def confirm_new_admin(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.split(":")[1])
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.is_admin = True
            db.commit()
            await callback.message.edit_text(
                f"✅ {user.full_name} admin qilib tayinlandi!"
            )
            
            try:
                await callback.bot.send_message(
                    user_id,
                    "🎉 Tabriklaymiz! Siz admin etib tayinlandingiz.\n"
                    "Admin paneliga kirish uchun /admin buyrug'ini yuboring."
                )
            except Exception as e:
                logger.error(f"Failed to notify new admin: {e}")
    except Exception as e:
        logger.error(f"Failed to add admin: {e}")
        await callback.message.edit_text("❌ Xatolik yuz berdi!")
    finally:
        db.close()

@router.callback_query(F.data == "cancel_admin")
async def cancel_admin_add(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text("❌ Admin qo'shish bekor qilindi!")

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    await callback.message.answer("Yubormoqchi bo'lgan xabaringizni yuboring:")
    await state.set_state(AdminStates.waiting_broadcast)

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    successful, failed = await broadcast_message(bot, message.text)
    await message.reply(
        f"Xabar yuborildi:\n"
        f"✅ Muvaffaqiyatli: {successful}\n"
        f"❌ Muvaffaqiyatsiz: {failed}"
    )
    await state.clear()

@router.callback_query(F.data == "admin_export")
async def export_users(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
        return
    
    try:
        buffer = generate_users_excel()
        await bot.send_document(
            callback.from_user.id,
            document=("users.xlsx", buffer),
            caption="Foydalanuvchilar ro'yxati"
        )
        logger.info(f"Excel fayl adminga yuborildi {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Excel faylni yuborishda xatolik: {e}")
        await callback.message.answer("Excel faylni yaratishda xatolik yuz berdi")

@router.callback_query(F.data == "admin_channel")
async def add_channel_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    await callback.message.answer("Kanal usernameni yuboring (Masalan: @channel):")
    await state.set_state(AdminStates.waiting_channel)

@router.message(AdminStates.waiting_channel)
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        chat = await bot.get_chat(message.text)
        db = SessionLocal()
        try:
            channel = Channel(
                channel_id=str(chat.id),
                username=message.text
            )
            db.add(channel)
            db.commit()
            logger.info(f"Yangi kanal qo'shildi: {message.text}")
            await message.reply("Kanal muvaffaqiyatli qo'shildi!")
        except Exception as e:
            logger.error(f"Kanalni qo'shishda xatolik {message.text}: {e}")
            db.rollback()
            await message.reply("Kanalni qo'shishda xatolik yuz berdi")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Kanal ma'lumotlarini olishda xatolik {message.text}: {e}")
        await message.reply("Noto'g'ri kanal usernamesi")
    finally:
        await state.clear()

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    """Handle /tasks command for admins"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return

    try:
        tasks, status = await get_user_tasks()
        if status == 200 and tasks.get('status') == 'success':
            task_list = tasks.get('tasks', [])
            if task_list:
                await message.answer(
                    "Mavjud topshiriqlar:",
                    reply_markup=get_task_management_kb(task_list)
                )
            else:
                await message.answer("Hozircha topshiriqlar yo'q.")
        else:
            await message.answer("Topshiriqlarni olishda xatolik yuz berdi.")
    except Exception as e:
        logger.error(f"Error in tasks command: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@router.callback_query(F.data.startswith("task_"))
async def process_task_callback(callback: CallbackQuery):
    """Handle task management callbacks"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Bu amal faqat adminlar uchun.", show_alert=True)
        return

    try:
        action, task_id = callback.data.split("_")[1:]
        
        if action == "status":
            await callback.message.edit_reply_markup(
                reply_markup=get_task_status_kb(task_id)
            )
        elif action == "mark":
            status = task_id.split("-")[1]  # task_mark_123-completed
            task_id = task_id.split("-")[0]
            
            result, status_code = await submit_task_progress(task_id, status)
            
            if status_code == 200:
                await callback.answer(
                    "Topshiriq statusi muvaffaqiyatli o'zgartirildi!",
                    show_alert=True
                )
                # Update task list
                tasks, _ = await get_user_tasks()
                if tasks.get('status') == 'success':
                    await callback.message.edit_reply_markup(
                        reply_markup=get_task_management_kb(tasks.get('tasks', []))
                    )
            else:
                await callback.answer(
                    "Xatolik yuz berdi. Qaytadan urinib ko'ring.",
                    show_alert=True
                )
    except Exception as e:
        logger.error(f"Error in task callback: {e}")
        await callback.answer(
            "Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            show_alert=True
        )


def register_handlers(dp: Dispatcher):
    dp.include_router(router)

