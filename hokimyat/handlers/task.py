from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.task import TaskState, AdminTaskState
from keyboards.reply import get_main_menu, get_cancel_kb
from keyboards.inline import (
    get_tasks_keyboard, get_task_detail_keyboard,
    get_admin_task_keyboard, get_task_stats_keyboard
)
from utils.api import (
    get_user_tasks, get_task_detail, update_task_status,
    submit_task_progress, get_task_stats
)
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()

def get_file_icon(file_type: str) -> str:
    icons = {
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
        'pdf': '📑',
        'doc': '📝', 'docx': '📝',
        'xls': '📊', 'xlsx': '📊',
        'ppt': '📽️', 'pptx': '📽️'
    }
    return icons.get(file_type.lower(), '📄')

def format_task_message(task: dict) -> str:
    status_emoji = {
        'pending': '⏳',
        'in_progress': '🔄',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '🚫'
    }.get(task.get('status'), '⏳')
    
    deadline = task.get('deadline', '').split('T')[0]
    
    message = (
        f"📌 <b>{task.get('title', 'Mavjud emas')}</b>\n\n"
        f"📝 <b>Tavsif:</b> {task.get('description', 'Mavjud emas')}\n"
        f"👤 <b>Yaratuvchi:</b> {task.get('creator_name', 'Mavjud emas')}\n"
        f"📅 <b>Muddati:</b> {deadline}\n"
        f"🔄 <b>Holati:</b> {status_emoji} {task.get('status_display', 'Mavjud emas')}\n"
        f"📊 <b>Bajarilish:</b> {task.get('percentage_count', 0)}%\n"
    )
    
    if task.get('status') == 'failed' and task.get('rejection_reason'):
        message += f"\n❌ <b>Rad etish sababi:</b> {task['rejection_reason']}\n"
    
    return message

async def send_task_files(message: Message, files: list):
    try:
        file_message = "📎 <b>Ilova qilingan fayllar:</b>\n\n"
        for i, file in enumerate(files, 1):
            file_type = file.get('file_type', '').lower()
            icon = get_file_icon(file_type)
            file_message += (
                f"{i}. {icon} <a href='{file.get('file_url')}'>"
                f"{file.get('name', 'Fayl')}</a>\n"
            )
        
        await message.answer(file_message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending files: {e}")
        await message.answer("Fayllarni yuklashda xatolik yuz berdi.")

@router.message(F.text == "📋 Mening topshiriqlarim")
async def show_tasks(message: Message):
    try:
        response, status = await get_user_tasks(message.from_user.id)
        
        if status == 200 and response.get('status') == 'success':
            tasks = response.get('tasks', [])
            if not tasks:
                await message.answer("Sizda hozircha faol topshiriqlar yo'q.")
                return

            tasks_by_status = {
                'pending': [],
                'in_progress': [],
                'other': []
            }
            
            for task in tasks:
                status = task.get('status')
                if status in ['pending', 'in_progress']:
                    tasks_by_status[status].append(task)
                else:
                    tasks_by_status['other'].append(task)
            
            status_headers = {
                'pending': '⏳ Kutilayotgan topshiriqlar:',
                'in_progress': '🔄 Jarayondagi topshiriqlar:',
                'other': '📋 Boshqa topshiriqlar:'
            }
            
            for status, task_list in tasks_by_status.items():
                if task_list:
                    await message.answer(
                        status_headers[status],
                        reply_markup=get_tasks_keyboard(task_list)
                    )
        else:
            await message.answer("Topshiriqlarni olishda xatolik yuz berdi.")
    except Exception as e:
        logger.error(f"Error in show_tasks: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@router.callback_query(F.data.startswith("task_view_"))
async def process_task_view(callback: CallbackQuery):
    try:
        task_id = int(callback.data.split('_')[2])
        response, status = await get_task_detail(task_id)
        
        if status == 200 and response.get('status') == 'success':
            task = response.get('task', {})
            message_text = format_task_message(task)
            keyboard = (
                get_admin_task_keyboard(task_id)
                if task.get('is_admin')
                else get_task_detail_keyboard(task_id, task.get('status'))
            )
            
            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            if task.get('files'):
                await send_task_files(callback.message, task['files'])
        else:
            await callback.answer(
                "Vazifa ma'lumotlarini olishda xatolik",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error in process_task_view: {e}")
        await callback.answer(
            "Xatolik yuz berdi. Qaytadan urinib ko'ring",
            show_alert=True
        )

@router.callback_query(F.data.startswith("task_stats_"))
async def show_task_stats(callback: CallbackQuery):
    try:
        task_id = int(callback.data.split('_')[2])
        response, status = await get_task_stats(task_id)
        
        if status == 200 and response.get('status') == 'success':
            stats = response.get('stats', {})
            message_text = (
                f"📊 Statistika:\n\n"
                f"✅ Bajarilgan: {stats.get('completed', 0)}\n"
                f"🔄 Jarayonda: {stats.get('in_progress', 0)}\n"
                f"⏳ Kutilmoqda: {stats.get('pending', 0)}\n"
                f"❌ Rad etilgan: {stats.get('failed', 0)}"
            )
            await callback.message.edit_text(
                message_text,
                reply_markup=get_task_stats_keyboard(task_id)
            )
        else:
            await callback.answer("Statistikani olishda xatolik", show_alert=True)
    except Exception as e:
        logger.error(f"Error in show_task_stats: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("task_complete_"))
async def complete_task(callback: CallbackQuery, state: FSMContext):
    try:
        task_id = int(callback.data.split("_")[2])
        await state.update_data(task_id=task_id)
        await state.set_state(TaskState.files)
        await callback.message.answer(
            "Topshiriq bo'yicha fayllarni yuklang",
            reply_markup=get_cancel_kb()
        )
    except Exception as e:
        logger.error(f"Error in complete_task: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)

@router.message(TaskState.files)
async def process_task_files(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Bekor qilish":
            await state.clear()
            await message.answer(
                "Amal bekor qilindi",
                reply_markup=get_main_menu()
            )
            return

        if not message.document and not message.photo:
            await message.answer("Iltimos, fayl yoki rasm yuboring")
            return

        data = await state.get_data()
        task_id = data["task_id"]
        files = []

        if message.document:
            files.append({
                "file_id": message.document.file_id,
                "name": message.document.file_name
            })
        elif message.photo:
            files.append({
                "file_id": message.photo[-1].file_id,
                "name": f"photo_{message.photo[-1].file_id}.jpg"
            })

        response, status = await submit_task_progress(
            task_id,
            message.from_user.id,
            "Topshiriq bajarildi",
            files
        )
        
        if status == 200 and response.get('status') == 'success':
            await state.clear()
            await message.answer(
                "✅ Topshiriq muvaffaqiyatli yuklandi",
                reply_markup=get_main_menu()
            )
            
            task_data, _ = await get_task_detail(task_id)
            if task_data.get('status') == 'success':
                task = task_data.get('task', {})
                await message.answer(
                    format_task_message(task),
                    reply_markup=get_task_detail_keyboard(task_id, task.get('status')),
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                "Xatolik yuz berdi. Qaytadan urinib ko'ring",
                reply_markup=get_main_menu()
            )
    except Exception as e:
        logger.error(f"Error in process_task_files: {e}")
        await message.answer(
            "Xatolik yuz berdi. Qaytadan urinib ko'ring",
            reply_markup=get_main_menu()
        )
        await state.clear()

@router.callback_query(F.data.startswith("task_reject_"))
async def reject_task(callback: CallbackQuery, state: FSMContext):
    try:
        task_id = int(callback.data.split("_")[2])
        await state.update_data(task_id=task_id)
        await state.set_state(AdminTaskState.rejection_reason)
        await callback.message.answer(
            "Rad etish sababini kiriting:",
            reply_markup=get_cancel_kb()
        )
    except Exception as e:
        logger.error(f"Error in reject_task: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)

@router.message(AdminTaskState.rejection_reason)
async def process_rejection_reason(message: Message, state: FSMContext):
    try:
        if message.text == "❌ Bekor qilish":
            await state.clear()
            await message.answer(
                "Rad etish bekor qilindi",
                reply_markup=get_main_menu()
            )
            return

        data = await state.get_data()
        task_id = data.get('task_id')
        
        response, status = await update_task_status(
            task_id,
            'failed',
            message.from_user.id,
            message.text
        )
        
        if status == 200 and response.get('status') == 'success':
            await message.answer(
                f"❌ Vazifa rad etildi\n\nSabab: {message.text}",
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(
                "Vazifani rad etishda xatolik yuz berdi",
                reply_markup=get_main_menu()
            )
        
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_rejection_reason: {e}")
        await message.answer(
            "Xatolik yuz berdi. Qaytadan urinib ko'ring",
            reply_markup=get_main_menu()
        )
        await state.clear()

@router.callback_query(F.data.startswith("task_approve_"))
async def approve_task(callback: CallbackQuery):
    try:
        task_id = int(callback.data.split("_")[2])
        response, status = await update_task_status(
            task_id,
            "completed",
            callback.from_user.id
        )
        
        if status == 200 and response.get('status') == 'success':
            task_data, _ = await get_task_detail(task_id)
            if task_data.get('status') == 'success':
                task = task_data.get('task', {})
                await callback.message.edit_text(
                    format_task_message(task),
                    reply_markup=get_admin_task_keyboard(task_id),
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    "✅ Vazifa tasdiqlandi",
                    reply_markup=get_admin_task_keyboard(task_id)
                )
        else:
            await callback.answer("Xatolik yuz berdi", show_alert=True)
    except Exception as e:
        logger.error(f"Error in approve_task: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)