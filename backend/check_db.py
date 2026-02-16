
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

async def check_user_db():
    print(f"Connecting to {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    try:
        await client.admin.command('ping')
        print("Connected successfully!")
        
        db_name = os.getenv("MONGO_DB_NAME")
        col_name = os.getenv("KNOWLEDGE_COLLECTION")
        count = await client[db_name][col_name].count_documents({})
        print(f"Documents in {db_name}.{col_name}: {count}")
        
        if count > 0:
            doc = await client[db_name][col_name].find_one()
            print("Sample doc ID:", doc.get("_id"))
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_db())
