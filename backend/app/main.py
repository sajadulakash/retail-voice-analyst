import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app import store
from app.audio_service import AudioAnalysisService, PREDEFINED_QUESTIONS
from app.schemas import QuestionCreate

settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_title,
    description="Multimodal Audio Transcription & Insight Engine",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    os.makedirs(settings.upload_dir, exist_ok=True)
    store.init_questions(PREDEFINED_QUESTIONS)
    print(f"Starting {settings.app_title}")
    print(f"Upload directory: {settings.upload_dir}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_title,
        "version": "1.0.0"
    }


@app.post("/api/v1/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Upload and process audio file.
    Accepts .mp3, .wav, .m4a files and starts two-stage analysis.
    """
    try:
        audio_service = AudioAnalysisService()
        if not audio_service.validate_audio_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed: {settings.allowed_formats_list}"
            )

        file_path = await audio_service.save_uploaded_file(file)

        analysis_id = str(uuid.uuid4())
        store.save_analysis(analysis_id, {
            "id": analysis_id,
            "filename": file.filename,
            "status": "pending",
        })

        background_tasks.add_task(
            audio_service.process_audio_analysis,
            file_path,
            analysis_id,
        )

        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "message": "Audio file received. Processing started.",
            "status": "pending"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/api/v1/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get analysis results or status."""
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.get("/api/v1/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """Get lightweight status of analysis (for polling)."""
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "id": analysis.get("id"),
        "filename": analysis.get("filename"),
        "status": analysis.get("status"),
        "created_at": analysis.get("created_at"),
        "updated_at": analysis.get("updated_at"),
    }


@app.get("/api/v1/analyses")
async def list_analyses(skip: int = 0, limit: int = 20):
    """List all analyses with pagination."""
    items, total = store.list_analyses(skip, limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "analyses": items,
    }


@app.delete("/api/v1/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Delete an analysis record."""
    if not store.delete_analysis(analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"message": "Analysis deleted successfully"}


@app.get("/api/v1/questions")
async def get_qa_questions():
    """Get all Q&A questions used in analysis."""
    return {"questions": store.get_all_questions()}


@app.post("/api/v1/questions", status_code=201)
async def create_question(payload: QuestionCreate):
    """Add a new analysis question."""
    question_id = f"q{uuid.uuid4().hex[:8]}"
    new_question = {
        "id": question_id,
        "question": payload.question.strip(),
        "category": payload.category.strip(),
    }
    store.save_question(question_id, new_question)
    return new_question


@app.put("/api/v1/questions/{question_id}")
async def update_question(question_id: str, payload: QuestionCreate):
    """Update an existing question."""
    existing = store.get_question(question_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
    updated = {
        "id": question_id,
        "question": payload.question.strip(),
        "category": payload.category.strip(),
    }
    store.save_question(question_id, updated)
    return updated


@app.delete("/api/v1/questions/{question_id}")
async def delete_question(question_id: str):
    """Delete a question."""
    if not store.delete_question(question_id):
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted successfully"}


# Mount frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
