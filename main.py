import os

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL not set")

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime
import feedparser

app = FastAPI(title="GRE Custom Actions API")

# ----------------------
# In-memory storage now per user_id
# ----------------------
progress_db: Dict[str, List[Dict[str, Any]]] = {}

# ----------------------
# Request/Response Models
# ----------------------
class QuizRequest(BaseModel):
    section: str  # 'verbal' | 'quant' | 'awa'
    numQuestions: int
    difficulty: Optional[str] = 'medium'  # 'easy' | 'medium' | 'hard'

class QuizItem(BaseModel):
    question_id: str
    question: str
    choices: List[str]
    answer: str
    explanation: str

class QuizResponse(BaseModel):
    quiz: List[QuizItem]

class ProgressEntry(BaseModel):
    date: datetime.date
    verbal: float
    quant: float
    awa: float

class ProgressTrend(BaseModel):
    average_verbal: float
    average_quant: float
    average_awa: float
    entries: List[ProgressEntry]

# ----------------------
# Endpoint: generatePracticeQuiz
# ----------------------
@app.post("/v1/gre/quiz", response_model=QuizResponse)
def generate_practice_quiz(request: QuizRequest):
    prompt = f"""
Generate {request.numQuestions} GRE-style multiple choice questions for the {request.section.upper()} section.
Each question should be {request.difficulty} difficulty and include:
- question_id (e.g., q1)
- question
- choices (4 options)
- answer (e.g., "B")
- explanation

Respond in JSON format as an array of question objects.
"""

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        raw_json = response.text.strip()

        import json
        parsed = json.loads(raw_json)
        return QuizResponse(quiz=[QuizItem(**q) for q in parsed])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini generation failed: {e}")


# ----------------------
# Endpoint: trackProgress (in-memory per user)
# ----------------------
@app.post("/v1/gre/progress", response_model=ProgressTrend)
def track_progress(request: Request, entry: ProgressEntry):
    user_id = request.headers.get("OpenAI-User-ID")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing OpenAI-User-ID header")

    if user_id not in progress_db:
        progress_db[user_id] = []

    progress_db[user_id].append(entry.dict())
    user_entries = progress_db[user_id]

    total = {'verbal': 0.0, 'quant': 0.0, 'awa': 0.0}
    for e in user_entries:
        total['verbal'] += e['verbal']
        total['quant'] += e['quant']
        total['awa'] += e['awa']
    count = len(user_entries)

    trend = ProgressTrend(
        average_verbal=total['verbal'] / count,
        average_quant=total['quant'] / count,
        average_awa=total['awa'] / count,
        entries=[ProgressEntry(**e) for e in user_entries]
    )
    return trend

# ----------------------
# Endpoint: fetchETSUpdates
# ----------------------
@app.get("/v1/gre/fetchETSUpdates")
def fetch_ets_updates():
    rss_url = "https://www.ets.org/gre/news/rss"
    feed = feedparser.parse(rss_url)

    if feed.bozo or not feed.entries:
        return {
            "updates": [
                {"title": "New GRE format now live", "link": "https://www.ets.org/gre", "published": "2025-01-01"},
                {"title": "Score delivery timeline shortened", "link": "https://www.ets.org/gre/scores", "published": "2024-12-15"},
            ]
        }

    updates = []
    for entry in feed.entries[:5]:
        updates.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return {"updates": updates}
