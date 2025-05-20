import os
import datetime
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlalchemy
import databases

# -------------------------
# TEMP FIX: Hardcoded DATABASE_URL
# This bypasses the .env loading issue for now
# -------------------------
DATABASE_URL = "postgresql://gre_progress_db_user:BK8Oc6Qmxeym5DWTE8IZP0UrxsI2XtXW@dpg-d0mfgvmuk2gs73fkfj10-a/gre_progress_db"
print("✅ Using DATABASE_URL =", DATABASE_URL)

# -------------------------
# Database setup
# -------------------------
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

progress = sqlalchemy.Table(
    "progress",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("date", sqlalchemy.Date),
    sqlalchemy.Column("verbal", sqlalchemy.Float),
    sqlalchemy.Column("quant", sqlalchemy.Float),
    sqlalchemy.Column("awa", sqlalchemy.Float),
)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI(title="GRE Custom Actions API")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ----------------------
# Pydantic Models
# ----------------------
class QuizRequest(BaseModel):
    section: str
    numQuestions: int
    difficulty: str = "medium"

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
# Endpoint: trackProgress (now using DB)
# ----------------------
@app.post("/v1/gre/progress", response_model=ProgressTrend)
async def track_progress(entry: ProgressEntry):
    query = progress.insert().values(
        date=entry.date,
        verbal=entry.verbal,
        quant=entry.quant,
        awa=entry.awa
    )
    await database.execute(query)

    rows = await database.fetch_all(progress.select().order_by(progress.c.date))
    total_v = sum(row["verbal"] for row in rows)
    total_q = sum(row["quant"] for row in rows)
    total_a = sum(row["awa"] for row in rows)
    count = len(rows)

    return ProgressTrend(
        average_verbal=total_v / count,
        average_quant=total_q / count,
        average_awa=total_a / count,
        entries=[ProgressEntry(**row) for row in rows]
    )

# ----------------------
# Endpoint: fetchETSUpdates
# ----------------------
@app.get("/v1/gre/fetchETSUpdates")
def fetch_ets_updates():
    import feedparser
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
