import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "arcee-ai/trinity-large-preview:free"

def query_llm(message: str, history: list = []):
    """
    Sends a message to the OpenRouter API.
    
    Args:
        message (str): The user's input message.
        history (list): List of previous messages [{"role": "user", "content": "..."}, ...]
        
    Returns:
        dict: The response from the model or an error message.
    """
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY is missing. Please check your .env file."}

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000", # Optional but recommended by OpenRouter
        "X-Title": "Mediafirewall" # Optional
    }

    # Construct messages list with history
    messages = history.copy()
    messages.append({"role": "user", "content": message})

    # OpenRouter uses the standard chat-completions format
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # OpenRouter might return 402 for payment required if free limits hit, or other codes
        if response.status_code != 200:
             return {"error": f"API Error {response.status_code}: {response.text}"}

        data = response.json()
        
        # Parse standard chat completion response
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            return {"response": content.strip()}
        elif "error" in data:
             return {"error": f"API Error: {data['error']}"}
        else:
            return {"error": "Unexpected response format from API."}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
