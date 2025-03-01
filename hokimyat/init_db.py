from database import SessionLocal, engine
from models.base import Base, User, Mahalla
from utils.logger import setup_logger

logger = setup_logger(__name__)

def init_database():
    Base.metadata.create_all(engine)
    
    db = SessionLocal()
    try:
        # Add mahallas
        mahallas = {
            "Yangi Hayot": 1,
            "Tinchlik": 2,
            "Navoiy": 3,
            "Istiqlol": 4
        }
        
        for name, id in mahallas.items():
            if not db.query(Mahalla).filter(Mahalla.name == name).first():
                db.add(Mahalla(id=id, name=name))
                logger.info(f"Mahalla qo'shildi: {name}")
        
        # Add main admins
        main_admins = [
            {
                "telegram_id": 6236467772,
                "username": "ablaze_coder",
                "phone_number": "+998200029038",
                "full_name": "Admin 1",
                "job_title": "Bosh admin",
                "mahalla_id": 1,
                "is_admin": True
            },
            {
                "telegram_id": 5645086563,
                "username": "Salom73330",
                "phone_number": "+998903703838",
                "full_name": "Admin 2",
                "job_title": "Bosh admin",
                "mahalla_id": 1,
                "is_admin": True
            }
        ]
        
        for admin in main_admins:
            if not db.query(User).filter(User.phone_number == admin["phone_number"]).first():
                db.add(User(**admin))
                logger.info(f"Bosh admin qo'shildi: {admin['username']}")
        
        db.commit()
        logger.info("Ma'lumotlar bazasi muvaffaqiyatli yaratildi")
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasini yaratishda xatolik: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()