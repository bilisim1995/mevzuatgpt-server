"""
MongoDB service for Yargitay metadata storage.
"""

from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings


class YargitayMongoService:
    def __init__(self):
        if not settings.MONGODB_CONNECTION_STRING:
            raise ValueError("Missing MONGODB_CONNECTION_STRING configuration")

        self._client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_STRING)
        self._db = self._client[settings.MONGODB_DATABASE]
        self._collection = self._db[settings.MONGODB_YARGI_COLLECTION]

    async def insert_metadata(self, payload: dict) -> str:
        result = await self._collection.insert_one(payload)
        return str(result.inserted_id)


yargitay_mongo_service = YargitayMongoService()
