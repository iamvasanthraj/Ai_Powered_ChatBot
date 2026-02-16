
import json
import logging
import re
from typing import Any, Dict, List, Optional
from db import get_db, resolve_knowledge_collection
from schema import get_collection_schema

logger = logging.getLogger(__name__)

QUERY_GENERATION_PROMPT = """
You are a MongoDB Expert. Your task is to generate a MongoDB Aggregation Pipeline to answer the user's question based on the provided schema.

Schema:
{schema}

User Question: "{question}"

Rules:
1. Return ONLY a valid JSON array representing the aggregation pipeline.
2. Do NOT explain your answer.
3. Do NOT include markdown code blocks (like ```json ... ```). Just the raw JSON.
4. If the user asks for a specific document by ID (e.g., "V1333..."), generate a match query for that `_id`.
5. For aggregations (counts, averages), use appropriate stages ($match, $group, $project).
6. Handle type conversions if necessary (e.g., converting "MediaProcessingTimeInSeconds" from string to double using $toDouble).
7. Ensure the pipeline is read-only. No $out, $merge, or $update.

Example Output:
[
  {{ "$match": {{ "safe": false }} }},
  {{ "$count": "unsafe_count" }}
]
"""

async def generate_pipeline_from_llm(client, model: str, question: str) -> List[Dict[str, Any]]:
    """
    Generates a MongoDB aggregation pipeline using the LLM.
    """
    schema_desc = get_collection_schema()
    prompt = QUERY_GENERATION_PROMPT.format(schema=schema_desc, question=question)

    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates MongoDB aggregation pipelines."},
        {"role": "user", "content": prompt}
    ]

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0, # Deterministic output
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Clean up potential markdown formatting
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?", "", response_text)
            response_text = re.sub(r"```$", "", response_text)
        
        pipeline = json.loads(response_text)
        if not isinstance(pipeline, list):
            raise ValueError("Output is not a list")
            
        return pipeline

    except Exception as e:
        logger.error(f"Error generating pipeline: {e}")
        return []

async def execute_aggregation(pipeline: List[Dict[str, Any]]) -> Any:
    """
    Executes the aggregation pipeline against the database.
    """
    if not pipeline:
        return None
        
    try:
        collection_name = await resolve_knowledge_collection()
        db = get_db()
        collection = db[collection_name]
        
        # Safety check
        for stage in pipeline:
            if any(k in stage for k in ["$out", "$merge", "$write"]):
                 raise ValueError("Unsafe aggregation stage detected.")

        results = await collection.aggregate(pipeline).to_list(length=100) # Limit results for safety
        return results
    except Exception as e:
        logger.error(f"Error executing aggregation: {e}")
        return str(e)

async def generate_natural_response(client, model: str, question: str, data: Any) -> str:
    """
    Generates a natural language response based on the query results.
    """
    messages = [
        {"role": "system", "content": "You are a helpful data analyst. Answer the user's question based on the provided data."},
        {"role": "user", "content": f"User Questions: {question}\n\nData Retrieved from Database: {json.dumps(data, default=str)}\n\nProvide a concise and accurate answer."}
    ]
    
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "I was unable to generate a response."
