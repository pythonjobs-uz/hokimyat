from datetime import datetime
from typing import List, Dict, Any

def format_task_message(tasks: List[Dict[str, Any]]) -> str:
    if not tasks:
        return "Sizga hozircha faol topshiriqlar yo'q."
    
    text = "📋 Sizning faol topshiriqlaringiz:\n\n"
    
    for task in tasks:
        start_date = datetime.fromisoformat(task['start_date']).strftime("%d.%m.%Y %H:%M")
        end_date = datetime.fromisoformat(task['end_date']).strftime("%d.%m.%Y %H:%M")
        
        text += (
            f"📌 {task['title']}\n"
            f"📝 {task['description']}\n"
            f"🕒 Muddati: {start_date} - {end_date}\n"
        )
        
        if task.get('file_url'):
            text += f"📎 Fayl: {task['file_url']}\n"
        
        text += "\n"
    
    return text