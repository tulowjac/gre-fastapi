from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime
import feedparser

app = FastAPI(title="GRE Custom Actions API")

# In-memory storage for progress tracking
progress_db: List[Dict[str, Any]] = []

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
    # Stub implementation: generate dummy questions
    quiz = []
    for i in range(request.numQuestions):
        quiz.append(
            QuizItem(
                question_id=f"{request.section[:1]}-{i+1}",
                question=f"Sample {request.section} question {i+1} (difficulty {request.difficulty})?",
                choices=["A", "B", "C", "D"],
                answer="A",
                explanation="This is the sample explanation."
            )
        )
    return QuizResponse(quiz=quiz)

# ----------------------
# Endpoint: trackProgress
# ----------------------
@app.post("/v1/gre/progress", response_model=ProgressTrend)
def track_progress(entry: ProgressEntry):
    progress_db.append(entry.dict())
    # Compute simple trend: averages
    total = {'verbal': 0.0, 'quant': 0.0, 'awa': 0.0}
    for e in progress_db:
        total['verbal'] += e['verbal']
        total['quant'] += e['quant']
        total['awa'] += e['awa']
    count = len(progress_db)
    trend = ProgressTrend(
        average_verbal=total['verbal']/count,
        average_quant=total['quant']/count,
        average_awa=total['awa']/count,
        entries=[ProgressEntry(**e) for e in progress_db]
    )
    return trend

# ----------------------
# Endpoint: fetchETSUpdates
# ----------------------
@app.get("/v1/gre/fetchETSUpdates")
def fetch_ets_updates():
    rss_url = "https://www.ets.org/gre/news/rss"
    feed = feedparser.parse(rss_url)
    if feed.bozo:
        raise HTTPException(status_code=502, detail="Failed to fetch ETS news feed.")
    updates = []
    for entry in feed.entries[:5]:  # return latest 5
        updates.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return {"updates": updates}
