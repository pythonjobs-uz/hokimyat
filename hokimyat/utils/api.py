import aiohttp
import asyncio
from typing import Dict, Any, Tuple, List, Optional, Union
from datetime import datetime
import json
import backoff
from aiohttp import ClientTimeout, TCPConnector, ClientSession
from functools import wraps
import hashlib
from contextlib import suppress
import mimetypes
import os
from aiogram import Bot
from config import (
    API_URL,
    API_TIMEOUT,
    API_RETRY_COUNT,
    API_RETRY_DELAY,
    API_POOL_SIZE,
    API_MAX_RETRIES,
    BOT_TOKEN,
    CACHE_TTL
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Simple in-memory cache
cache = {}

def cache_key(func_name: str, *args, **kwargs) -> str:
    """Generate cache key from function name and arguments"""
    key = f"{func_name}:{str(args)}:{str(kwargs)}"
    return hashlib.md5(key.encode()).hexdigest()

def cached(ttl: int = CACHE_TTL):
    """Cache decorator for API responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache_key(func.__name__, *args, **kwargs)
            
            # Check cache
            cached_data = cache.get(key)
            if cached_data:
                timestamp, data = cached_data
                if (datetime.now() - timestamp).seconds < ttl:
                    logger.debug(f"Cache hit for {key}")
                    return data

            # Get fresh data
            result = await func(*args, **kwargs)
            
            # Cache successful responses only
            if isinstance(result, tuple) and result[1] == 200:
                cache[key] = (datetime.now(), result)
                
                # Clean old cache entries
                current_time = datetime.now()
                expired_keys = [
                    k for k, (timestamp, _) in cache.items()
                    if (current_time - timestamp).seconds > ttl
                ]
                for k in expired_keys:
                    cache.pop(k, None)
            
            return result
        return wrapper
    return decorator

class APIResponse:
    """Wrapper for API responses with proper typing and error handling"""
    def __init__(
        self,
        data: Dict[str, Any],
        status_code: int,
        error: Optional[str] = None
    ):
        self.data = data
        self.status_code = status_code
        self.error = error
        self.success = 200 <= status_code < 300 and not error

    @property
    def message(self) -> str:
        """Get human-readable message from response"""
        if self.error:
            return self.error
        return self.data.get('message', '')

    def __bool__(self) -> bool:
        return self.success

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class APIClient:
    """Asynchronous API client with connection pooling and retry logic"""
    _instance = None
    _initialized = False
    _session: Optional[ClientSession] = None
    _bot: Optional[Bot] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not APIClient._initialized:
            self.base_url = API_URL.rstrip('/')
            self.timeout = ClientTimeout(total=API_TIMEOUT)
            self.retry_count = API_RETRY_COUNT
            self.retry_delay = API_RETRY_DELAY
            self.logger = setup_logger('api_client')
            APIClient._initialized = True

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close session on exit to reuse it
        pass

    @classmethod
    async def ensure_session(cls) -> ClientSession:
        """Ensure session exists and is active"""
        if cls._session is None or cls._session.closed:
            connector = TCPConnector(
                limit=API_POOL_SIZE,
                ttl_dns_cache=300,
                enable_cleanup_closed=True
            )
            cls._session = ClientSession(
                connector=connector,
                timeout=ClientTimeout(total=API_TIMEOUT)
            )
        return cls._session

    @classmethod
    async def get_bot(cls) -> Bot:
        """Get or create bot instance"""
        if cls._bot is None:
            cls._bot = Bot(token=BOT_TOKEN)
        return cls._bot

    @classmethod
    async def close(cls):
        """Close all connections"""
        if cls._session and not cls._session.closed:
            with suppress(Exception):
                await cls._session.close()
            cls._session = None
        if cls._bot:
            with suppress(Exception):
                await cls._bot.session.close()
            cls._bot = None

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError, APIError),
        max_tries=API_MAX_RETRIES,
        max_time=API_TIMEOUT
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Union[Dict, aiohttp.FormData]] = None,
        params: Optional[Dict] = None,
        files: Optional[List[Dict]] = None
    ) -> APIResponse:
        """Make HTTP request with retry logic and proper error handling"""
        session = await self.ensure_session()
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {}

        # Prepare request
        if isinstance(data, dict):
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data)
        
        # Log request
        self.logger.debug(f"Making {method} request to {url}")
        
        try:
            async with session.request(
                method=method,
                url=url,
                data=data,
                params=params,
                headers=headers,
                timeout=self.timeout
            ) as response:
                try:
                    result = await response.json()
                    return APIResponse(result, response.status)
                except aiohttp.ContentTypeError:
                    text = await response.text()
                    self.logger.error(f"Invalid JSON response: {text}")
                    raise APIError("Invalid response format", response.status)

        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout for {url}")
            raise APIError("Request timeout", 408)
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            raise APIError(str(e))

    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """Clean and validate phone number"""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 9:
            return f"998{digits}"
        elif len(digits) == 12 and digits.startswith('998'):
            return digits
        raise ValueError("Invalid phone number format")

    @staticmethod
    def validate_jshir(jshir: str) -> str:
        """Validate JSHIR format"""
        jshir = jshir.strip()
        if not jshir.isdigit() or len(jshir) != 14:
            raise ValueError("Invalid JSHIR format")
        return jshir

    @cached(ttl=300)  # Cache for 5 minutes
    async def get_user_info(self, telegram_id: int) -> APIResponse:
        """Get user information"""
        return await self._make_request(
            'GET',
            'user-info/',
            params={'telegram_id': telegram_id}
        )

    async def verify_user(
        self,
        phone: str,
        jshir: str,
        telegram_id: int
    ) -> APIResponse:
        """Verify user with phone and JSHIR"""
        try:
            phone = self.clean_phone_number(phone)
            jshir = self.validate_jshir(jshir)

            return await self._make_request(
                'POST',
                'verify-user/',
                {
                    'phone': phone,
                    'jshir': jshir,
                    'telegram_id': telegram_id
                }
            )
        except ValueError as e:
            return APIResponse({'message': str(e)}, 400, str(e))

    @cached(ttl=60)  # Cache for 1 minute
    async def get_user_tasks(self, telegram_id: int) -> APIResponse:
        """Get user tasks"""
        return await self._make_request(
            'GET',
            'tasks/',
            params={'telegram_id': telegram_id}
        )

    @cached(ttl=60)
    async def get_task_detail(self, task_id: int) -> APIResponse:
        """Get task details"""
        return await self._make_request('GET', f'tasks/{task_id}/')

    @cached(ttl=60)
    async def get_task_stats(self, task_id: int) -> APIResponse:
        """Get task statistics"""
        return await self._make_request('GET', f'tasks/{task_id}/stats/')

    async def update_task_status(
        self,
        task_id: int,
        status: str,
        telegram_id: int,
        rejection_reason: Optional[str] = None
    ) -> APIResponse:
        """Update task status"""
        data = {
            'status': status,
            'telegram_id': telegram_id
        }
        if rejection_reason:
            data['rejection_reason'] = rejection_reason
        
        return await self._make_request(
            'PATCH',
            f'tasks/{task_id}/status/',
            data
        )

    async def submit_task_progress(
        self,
        task_id: int,
        telegram_id: int,
        description: str,
        files: Optional[List[Dict[str, str]]] = None
    ) -> APIResponse:
        """Submit task progress with optional files"""
        form = aiohttp.FormData()
        form.add_field('task_id', str(task_id))
        form.add_field('telegram_id', str(telegram_id))
        form.add_field('description', description)

        if files:
            for file_data in files:
                file_id = file_data.get('file_id')
                if file_id:
                    file_content = await self.download_telegram_file(file_id)
                    if file_content:
                        form.add_field(
                            'files[]',
                            file_content[0],
                            filename=file_content[1],
                            content_type=file_content[2]
                        )

        return await self._make_request('POST', 'submit-progress/', form)

    async def download_telegram_file(
        self,
        file_id: str
    ) -> Optional[Tuple[bytes, str, str]]:
        """Download file from Telegram"""
        try:
            bot = await self.get_bot()
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_name = os.path.basename(file_path)
            content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            file_content = await bot.download_file(file_path)
            return file_content.read(), file_name, content_type
        except Exception as e:
            self.logger.error(f"File download error: {e}")
            return None

# Create global API client instance
api_client = APIClient()

# Function wrappers for easier access
async def verify_user(
    phone: str,
    jshir: str,
    telegram_id: int
) -> APIResponse:
    return await api_client.verify_user(phone, jshir, telegram_id)

async def get_user_info(telegram_id: int) -> APIResponse:
    return await api_client.get_user_info(telegram_id)

async def get_user_tasks(telegram_id: int) -> APIResponse:
    return await api_client.get_user_tasks(telegram_id)

async def get_task_detail(task_id: int) -> APIResponse:
    return await api_client.get_task_detail(task_id)

async def get_task_stats(task_id: int) -> APIResponse:
    return await api_client.get_task_stats(task_id)

async def update_task_status(
    task_id: int,
    status: str,
    telegram_id: int,
    rejection_reason: Optional[str] = None
) -> APIResponse:
    return await api_client.update_task_status(
        task_id,
        status,
        telegram_id,
        rejection_reason
    )

async def submit_task_progress(
    task_id: int,
    telegram_id: int,
    description: str,
    files: Optional[List[Dict[str, str]]] = None
) -> APIResponse:
    return await api_client.submit_task_progress(
        task_id,
        telegram_id,
        description,
        files
    )

async def download_telegram_file(
    file_id: str
) -> Optional[Tuple[bytes, str, str]]:
    return await api_client.download_telegram_file(file_id)