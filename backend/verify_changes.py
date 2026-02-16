
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import orchestrate_llm

load_dotenv()

async def run_verification():
    print("--- Starting Verification ---")
    
    # Test 1: Single Item Lookup (Mock ID, assuming one exists or using a made up one that matches regex)
    # matching the pattern in schema: V1333211397980873_910_URL_60845
    test_id = "V1333211397980873_910_URL_60845" 
    print(f"\nTest 1: Lookup {test_id}")
    response = await orchestrate_llm(f"Show me details for {test_id}", [])
    print(f"Response: {response}")

    # Test 2: Simple Count Aggregation
    print("\nTest 2: Count Aggregation (Nudity=True)")
    response = await orchestrate_llm("How many events have Nudity as true?", [])
    print(f"Response: {response}")

    # Test 3: Average Processing Time
    print("\nTest 3: Average Processing Time")
    response = await orchestrate_llm("What is the average processing time for Minor feature?", [])
    print(f"Response: {response}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(run_verification())
