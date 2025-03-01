import pandas as pd
from io import BytesIO
from sqlalchemy import create_engine, text
from utils.logger import setup_logger
from config import DATABASE_URL

logger = setup_logger(__name__)

def generate_users_excel() -> BytesIO:
    try:
        engine = create_engine(DATABASE_URL)
        
        query = text("""
            SELECT 
                u.telegram_id,
                u.username,
                u.phone_number,
                u.full_name,
                u.jshir,
                j.name as job_title,
                m.name as mahalla,
                u.created_at
            FROM api_user u
            LEFT JOIN api_mahalla m ON u.mahalla_id = m.id
            LEFT JOIN api_jobtitle j ON u.job_title_id = j.id
            ORDER BY u.created_at DESC
        """)
        
        df = pd.read_sql(query, engine)
        
        # Rename columns to Uzbek
        df.columns = [
            'Telegram ID',
            'Username',
            'Telefon raqami',
            'F.I.O',
            'JSHIR',
            'Lavozimi',
            'Mahallasi',
            'Ro\'yxatdan o\'tgan sana'
        ]
        
        # Format date
        df['Ro\'yxatdan o\'tgan sana'] = pd.to_datetime(df['Ro\'yxatdan o\'tgan sana']).dt.strftime('%d.%m.%Y %H:%M')
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(
                writer,
                index=False,
                sheet_name='Foydalanuvchilar'
            )
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Foydalanuvchilar']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length
        
        buffer.seek(0)
        logger.info("Excel fayl muvaffaqiyatli yaratildi")
        return buffer
        
    except Exception as e:
        logger.error(f"Excel fayl yaratishda xatolik: {e}")
        raise
    finally:
        if 'engine' in locals():
            engine.dispose()