import aiohttp
from config import NEXUS_API_URL, NEXUS_API_KEY


class NexusAPIClient:
    def __init__(self):
        self.base_url = NEXUS_API_URL.rstrip("/")
        self.api_key = NEXUS_API_KEY

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Nexus-Bot-Key"] = self.api_key
        return headers

    async def get_user_by_discord_id(self, discord_id):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/discord/user/{discord_id}"
            async with session.get(url, headers=self._headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

    async def get_user_channels(self, discord_id):
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            return []
        return user.get("channels", [])

    async def send_notification(self, notification_type, data):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/discord/notify"
            payload = {"type": notification_type, **data}
            async with session.post(url, json=payload, headers=self._headers()) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None


nexus_api = NexusAPIClient()
