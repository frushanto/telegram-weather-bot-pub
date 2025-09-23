from typing import Dict, Tuple

from ..core.exceptions import SpamProtectionError
from ..domain.services import SpamProtectionService
from .spam_protection import spam_protection as legacy_spam_protection


class LegacySpamProtectionService(SpamProtectionService):

    def __init__(self):
        self._legacy_service = legacy_spam_protection

    async def is_spam(
        self, user_id: int, message_text: str = "", user_lang: str = "ru"
    ) -> Tuple[bool, str]:

        try:
            return await self._legacy_service.is_spam(
                user_id, message_text, user_lang=user_lang
            )
        except Exception as e:
            raise SpamProtectionError(f"Spam check error: {e}")

    async def unblock_user(self, user_id: int) -> bool:

        try:
            return await self._legacy_service.unblock_user(user_id)
        except Exception as e:
            raise SpamProtectionError(f"Unblock error: {e}")

    async def get_user_stats(self, user_id: int) -> Dict:

        try:
            return await self._legacy_service.get_user_stats(user_id)
        except Exception as e:
            raise SpamProtectionError(f"Stats retrieval error: {e}")
