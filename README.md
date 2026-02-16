# Mediafirewall Chatbot

A smart, persistent chatbot powered by **Arcee Trinity** (via OpenRouter) that remembers your conversations using **MongoDB**.

## 🚀 Features

-   **Smart AI**: Uses `arcee-ai/trinity-large-preview:free` for high-quality responses.
-   **Memory**: Remembers persistent chat history using MongoDB.
-   **Modern UI**: Clean, responsive dark-mode interface.
-   **Fast Backend**: Built with FastAPI and Motor (Async MongoDB driver).

## � Prerequisites

Before running, make sure you have:

1.  **Python 3.8+** installed.
2.  **MongoDB** installed and running locally (`mongodb://localhost:27017`).
    *   [Download MongoDB Community Server](https://www.mongodb.com/try/download/community)

## ⚙️ Installation & Setup

### 1. Backend Setup

Open a terminal in the `backend` folder:

```bash
cd backend
```

Create and activate a virtual environment (recommended):

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configuration

Ensure you have a `.env` file in the `backend` folder with your API key:

```ini
OPENROUTER_API_KEY= [Your Key]
MONGO_URL=mongodb://localhost:27017
```

*(Note: The API key is pre-configured for this project.)*

## ▶️ How to Run

### 1. Start MongoDB
Make sure your MongoDB server is running. On Windows, you might need to start it from Services or run `mongod` in a terminal.

### 2. Start the Backend Server
In your `backend` terminal:

```bash
uvicorn main:app --reload --port 8001
```

You should see: `Uvicorn running on http://127.0.0.1:8001`

### 3. Open the Frontend
Simply open the `index.html` file in your browser:

*   Go to the `frontend` folder.
*   Double-click `index.html`.

## 💡 Usage

1.  Type a message (e.g., "My name is Vasanth").
2.  The bot will answer.
3.  Refresh the page.
4.  Ask "What is my name?".
5.  The bot will remember! (Thanks to MongoDB).
