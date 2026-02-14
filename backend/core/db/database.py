from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

from commons.logger import logger

log = logger(__name__)

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")


class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def connect_to_mongo():
    try:
        db.client = AsyncIOMotorClient(MONGODB_URL)
        # Verify connection
        await db.client.admin.command("ping")
        log.info("Connected to MongoDB")
    except Exception as e:
        log.error(f"Error connecting to MongoDB: {e}")


async def close_mongo_connection():
    try:
        if db.client:
            db.client.close()
            log.info("Closed MongoDB connection")
    except Exception as e:
        log.error(f"Error closing MongoDB connection: {e}")


def get_database():
    """Get the voice_project database instance."""
    return db.client["voice_project"]
