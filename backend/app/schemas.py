from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TranscriptSegment(BaseModel):
    """Single segment of transcript with speaker info"""
    speaker: str
    text: str
    timestamp_start: float
    timestamp_end: float

class SpeakerDiarization(BaseModel):
    """Speaker information"""
    speaker_id: str
    role: str  # e.g., "Customer", "Shopkeeper"
    segment_count: int

class QAResult(BaseModel):
    """Q&A result for a single question"""
    question: str
    answer: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

class AudioAnalysisResponse(BaseModel):
    """Response model for completed audio analysis"""
    id: str
    filename: str
    transcript: List[TranscriptSegment]
    speakers: List[SpeakerDiarization]
    qa_results: List[QAResult]
    processing_time: int  # seconds
    created_at: datetime
    
    class Config:
        from_attributes = True

class AudioAnalysisRequest(BaseModel):
    """Request body for audio analysis"""
    # This is mainly for documentation; actual file is uploaded via form-data

class AnalysisStatus(BaseModel):
    """Status of an ongoing/completed analysis"""
    id: str
    filename: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0  # 0-1
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class QAQuestion(BaseModel):
    """Predefined Q&A question for analysis"""
    id: str
    question: str
    category: str  # e.g., "product_inquiry", "confirmation"
    context: str = ""

class BanglishTranscript(BaseModel):
    """Banglish transcript with speaker identification"""
    segments: List[TranscriptSegment]
    speakers: Dict[str, str]  # speaker_id -> role mapping
