from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

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
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")


async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")


def get_database():
    return db.client.get_default_database()
