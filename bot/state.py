import asyncio

import httpx

from bot.config import API_BASE_URL, MAUTHAPI_KEY

request_queue: asyncio.Queue = asyncio.Queue()
active_numbers: dict = {}
last_range: dict = {}

_api_headers = {
    "User-Agent": "BEST-OTP-BOT/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
if MAUTHAPI_KEY:
    _api_headers["mauthapi"] = MAUTHAPI_KEY

client_async = httpx.AsyncClient(
    http2=True,
    timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=15.0),
    headers=_api_headers,
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
)

API_ENDPOINTS = {
    "getnum": f"{API_BASE_URL}/getnum",
    "liveaccess": f"{API_BASE_URL}/liveaccess",
    "success_otp": f"{API_BASE_URL}/success-otp",
    "console": f"{API_BASE_URL}/console",
}
