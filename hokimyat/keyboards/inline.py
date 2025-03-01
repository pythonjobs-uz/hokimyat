from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_tasks_keyboard(tasks: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Generate keyboard with tasks"""
    keyboard = []
    
    for task in tasks:
        task_id = task.get('id')
        title = task.get('title')
        status = task.get('status')
        deadline = task.get('deadline', '').split('T')[0]
        
        # Add emoji based on status
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }.get(status, '⏳')
        
        # Truncate title if too long
        if len(title) > 30:
            title = title[:27] + "..."
            
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {title} ({deadline})",
                callback_data=f"task_view_{task_id}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_task_detail_keyboard(task_id: int, status: str = 'pending') -> InlineKeyboardMarkup:
    """Generate keyboard for task details"""
    keyboard = []
    
    # Show action buttons only for pending or in_progress tasks
    if status in ['pending', 'in_progress']:
        keyboard.extend([
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi deb belgilash",
                    callback_data=f"task_complete_{task_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Hisobot yuborish",
                    callback_data=f"task_progress_{task_id}"
                )
            ]
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="📊 Statistika",
                callback_data=f"task_stats_{task_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Orqaga",
                callback_data="tasks_list"
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Generate keyboard for admin task management"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Tasdiqlash",
                callback_data=f"task_approve_{task_id}"
            ),
            InlineKeyboardButton(
                text="❌ Rad etish",
                callback_data=f"task_reject_{task_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Statistika",
                callback_data=f"task_stats_{task_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Orqaga",
                callback_data="tasks_list"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_task_stats_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Generate keyboard for task statistics"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Yangilash",
                callback_data=f"task_stats_{task_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Vazifaga qaytish",
                callback_data=f"task_view_{task_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)