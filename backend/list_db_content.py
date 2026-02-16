
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

async def sample_data():
    client = AsyncIOMotorClient(MONGO_URL)
    
    candidates = [
        ("DB1", "910"),
        ("shopdb", "MFWall")
    ]
    
    for db_name, col_name in candidates:
        print(f"\n--- Sampling {db_name}.{col_name} ---")
        try:
            doc = await client[db_name][col_name].find_one()
            print(doc)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(sample_data())
