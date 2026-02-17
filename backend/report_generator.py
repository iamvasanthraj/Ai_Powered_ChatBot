
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import openpyxl
from db import get_db, resolve_knowledge_collection

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def _flatten_event_log(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens the eventLog structure into a single level dictionary for CSV/Excel.
    """
    flattened = {
        "_id": str(doc.get("_id", "")),
        "eventStartTime": doc.get("eventStartTime", ""),
        "eventEndTime": doc.get("eventEndTime", ""),
    }

    # Extract boolean feature status
    # Priority: processStatus.featureStatus > eventLog existence
    feature_status = doc.get("processStatus", {}).get("featureStatus", {})
    event_log = doc.get("eventLog", {})
    
    for feature in ["ImageSearch", "Nudity", "Minor"]:
        # Check if explicitly in featureStatus
        if feature in feature_status:
             flattened[feature] = feature_status[feature]
        else:
             # Fallback: check if it exists in eventLog and has data
             flattened[feature] = bool(event_log.get(feature))

    return flattened

import csv

def _clean_pipeline_for_report(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Removes aggregation stages that are not suitable for a report list (e.g. $count, $limit, $project).
    """
    cleaned = []
    for stage in pipeline:
        # Skip count, limit, and project stages to get full dataset with all fields
        if any(k in stage for k in ["$count", "$limit", "$project"]):
            continue
        cleaned.append(stage)
    return cleaned

from utils import convert_dates

async def generate_report(pipeline: List[Dict[str, Any]], filename_prefix: str = "report", format: str = "xlsx") -> Optional[str]:
    """
    Executes the pipeline, flattens results, saves to Excel or CSV, and returns the filename.
    """
    try:
        collection_name = await resolve_knowledge_collection()
        db = get_db()
        collection = db[collection_name]
        
        # Clean pipeline to ensure we get docs, not counts, and no limits
        pipeline = _clean_pipeline_for_report(pipeline)

        # Convert date strings to datetime objects (CRITICAL FIX)
        pipeline = convert_dates(pipeline)
        
        # Execute aggregation without limit
        cursor = collection.aggregate(pipeline)
        
        # Fetch all documents (warning: memory intensive for huge datasets, but requested)
        docs = await cursor.to_list(length=None)
        
        if not docs:
            return None

        # Flatten data
        flattened_docs = [_flatten_event_log(doc) for doc in docs]
        
        if not flattened_docs:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        headers = list(flattened_docs[0].keys())

        if format == "csv":
            filename = f"{filename_prefix}_{timestamp}.csv"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(flattened_docs)
                
            logger.info(f"CSV Report generated: {filepath}")
            return filename
            
        else:
            # Default to Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report"
            
            ws.append(headers)
            
            for item in flattened_docs:
                row = [str(item.get(h, "")) for h in headers]
                ws.append(row)
                
            filename = f"{filename_prefix}_{timestamp}.xlsx"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            wb.save(filepath)
            logger.info(f"Excel Report generated: {filepath}")
            return filename
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return None
