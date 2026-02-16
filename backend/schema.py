
from typing import Dict, Any

def get_collection_schema() -> str:
    """
    Returns a string representation of the MongoDB collection schema
    to be used in the LLM prompt.
    """
    return """
The collection contains documents representing media moderation events.
Each document has the following structure (showing key fields):

{
  "_id": "String (Unique Event ID, e.g., V1333...)",
  "userId": "String",
  "orgId": "String",
  "requestType": "String (e.g., 'URL')",
  "eventStartTime": "Date (ISO8601)",
  "processExitStatus": "Boolean",
  "operationsPerFeature": {
    "Minor": "Integer",
    "Scamster": "Integer",
    "Nudity": "Integer",
    "ImageSearch": "Integer"
  },
  "eventLog": {
    "ImageSearch": {
      "processingStartTime": "String (ISO8601)",
      "processingEndTime": "String (ISO8601)",
      "report": { ... }
    },
    "Nudity": {
      "processingStartTime": "String (ISO8601)",
      "processingEndTime": "String (ISO8601)",
      "report": {
        "documentReport": {
          "report": {
            "Model": "String",
            "Predictions": "String (JSON string of probabilities, e.g. \"{'na/selfie': 0.58...}\")",
            "StatusCode": "String",
            "MediaProcessingTimeInSeconds": "String (Float as string)"
          }
        }
      }
    },
    "Minor": { ... },
    "Scamster": { ... }
  },
  "processStatus": {
    "completedProcesses": "Integer",
    "complete": "Boolean",
    "featureStatus": {
      "Minor": "Boolean",
      "Scamster": "Boolean",
      "Nudity": "Boolean",
      "ImageSearch": "Boolean"
    }
  },
  "media": {
    "inputMediaURL": "String",
    "type": "String (e.g., 'IMAGE')"
  },
  "safe": "Boolean",
  "complete": "Boolean",
  "moderationCode": "String"
}

Important Notes:
1. `eventLog` contains details for each feature (Nudity, Minor, Scamster, ImageSearch).
2. `eventLog.<Feature>.report.documentReport.report.Predictions` is often a JSON string.
3. **CRITICAL**: For processing time or duration queries, ALWAYS use `eventLog.<Feature>.report.documentReport.report.MediaProcessingTimeInSeconds`. Do NOT try to calculate it from `processingStartTime` and `processingEndTime` because the date format is non-standard and will cause errors. You will need to convert the string to a double (e.g., `{{ "$toDouble": "$eventLog.Minor.report.documentReport.report.MediaProcessingTimeInSeconds" }}`).
4. Timestamps are strings in a custom ISO-like format (e.g. `2025-06-10T00:01:15:005433`).
"""
