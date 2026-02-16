
import logging
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI

from database import (
    find_one_document,
    dumps_json,
)
from db import resolve_knowledge_collection
from query_generator import generate_pipeline_from_llm, execute_aggregation, generate_natural_response

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = "arcee-ai/trinity-large-preview:free" # Or any other capable model

if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY is not set. LLM features will fail.")

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Regex to detect specific Media/Event IDs
_EVENT_ID_PATTERN = re.compile(r"\bV\d+_\d+_[A-Z]+_\d+\b")

async def orchestrate_llm(user_message: str, history: List[Dict[str, Any]]) -> str:
    """
    Main entry point for handling user messages.
    """
    try:
        collection_name = await resolve_knowledge_collection()
        
        # 1. Check for specific ID lookup intent first (keep it fast and deterministic)
        media_id_match = _EVENT_ID_PATTERN.search(user_message)
        if media_id_match:
            media_id = media_id_match.group(0)
            # Simple heuristic: if user provides an ID, fetch the doc.
            logger.info(f"Detected Media ID: {media_id}")
            doc = await find_one_document(
                collection=collection_name,
                filter={"_id": media_id}
            )
            if doc:
                # If doc found, let the LLM answer based on this single doc
                return await generate_natural_response(client, MODEL_ID, user_message, doc)
            else:
                 return f"I couldn't find any record with ID {media_id}."

        # 2. If no ID, treat as an aggregation query
        logger.info("Generating aggregation pipeline...")
        pipeline = await generate_pipeline_from_llm(client, MODEL_ID, user_message)
        
        if not pipeline:
             return "I'm sorry, I couldn't understand how to query the data for that question."

        logger.info(f"Executing pipeline: {pipeline}")
        results = await execute_aggregation(pipeline)
        
        if isinstance(results, str) and results.startswith("Error"):
             return f"I encountered an error querying the database: {results}"
             
        # 3. Generate natural language response
        return await generate_natural_response(client, MODEL_ID, user_message, results)

    except Exception as e:
        logger.exception("Error in orchestrate_llm")
        return "I encountered an error processing your request."
