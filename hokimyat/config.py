
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://python_boss_robot_user:fMaBayriYAZRWXtwSpfOF4jYibSnufC2@dpg-cukn5hbtq21c73e9b48g-a.oregon-postgres.render.com/python_boss_robot')
API_URL="https://8000-idx-hokimyat-1740074206848.cluster-23wp6v3w4jhzmwncf7crloq3kw.cloudworkstations.dev"
ADMIN_IDS=5645086563, 6236467772
API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
API_RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', 3))
API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', 1))
API_VERIFY_SSL = os.getenv('API_VERIFY_SSL', 'True').lower() == 'true'

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')