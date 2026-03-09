import os
import uuid
import time
from fastapi import UploadFile
from app.config import get_settings
from app.gemini_service import GeminiService
from app import store

settings = get_settings()

# Predefined Q&A questions for SMR-Shopkeeper retail monitoring
PREDEFINED_QUESTIONS = [
    {
        "id": "q1",
        "question": "Did the SMR ask the shopkeeper about their current stock?",
        "category": "stock_inquiry"
    },
    {
        "id": "q2",
        "question": "Did the SMR ask whether the shopkeeper needs any product?",
        "category": "need_assessment"
    },
    {
        "id": "q3",
        "question": "Did the shopkeeper place an order or agree to restock?",
        "category": "order_placement"
    },
    {
        "id": "q4",
        "question": "Did the SMR ask whether the shopkeeper needs Coca-Cola?",
        "category": "cocacola_inquiry"
    },
    {
        "id": "q5",
        "question": "Did the SMR ask the shopkeeper whether the SO (Sales Officer) has visited?",
        "category": "so_reference"
    }
]

class AudioAnalysisService:
    """Service for orchestrating audio analysis workflow"""
    
    @staticmethod
    def validate_audio_file(filename: str) -> bool:
        """Validate if file is an allowed audio format"""
        ext = filename.split(".")[-1].lower()
        return ext in settings.allowed_formats_list
    
    @staticmethod
    async def save_uploaded_file(upload_file: UploadFile) -> str:
        """Save uploaded file to temporary storage"""
        if not AudioAnalysisService.validate_audio_file(upload_file.filename):
            raise ValueError(f"File format not allowed. Allowed: {settings.allowed_formats_list}")
        
        # Create unique filename
        file_ext = upload_file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            if len(content) > settings.max_file_size:
                os.remove(file_path)
                raise ValueError(f"File size exceeds maximum allowed ({settings.max_file_size} bytes)")
            f.write(content)
        
        return file_path
    
    @staticmethod
    def cleanup_file(file_path: str) -> None:
        """Delete temporary file after processing"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {str(e)}")
    
    @staticmethod
    def process_audio_analysis(file_path: str, analysis_id: str) -> None:
        """
        Main orchestration function for audio analysis.

        Workflow:
        1. Upload audio to Gemini API
        2. Stage 1: Transcription + Diarization
        3. Stage 2: Q&A Analysis
        4. Store results in memory
        5. Cleanup temp file
        """
        start_time = time.time()

        try:
            store.save_analysis(analysis_id, {"status": "processing"})

            # Upload file to Gemini
            gemini_file = GeminiService.upload_audio_file(file_path)

            # Stage 1: Transcription and Diarization
            transcript_segments, speaker_diarization = GeminiService.transcribe_and_diarize(gemini_file)

            # Build transcript text for Q&A
            transcript_text = "\n".join([
                f"{seg.speaker} ({seg.timestamp_start:.1f}s): {seg.text}"
                for seg in transcript_segments
            ])

            # Stage 2: Q&A Analysis using live questions from store
            from app import store as _store
            live_questions = _store.get_all_questions()
            qa_results = GeminiService.analyze_qa(transcript_text, live_questions)

            # Store results in memory
            store.save_analysis(analysis_id, {
                "status": "completed",
                "transcript": [seg.model_dump() for seg in transcript_segments],
                "speakers": [s.model_dump() for s in speaker_diarization],
                "qa_results": [q.model_dump() for q in qa_results],
                "processing_time": int(time.time() - start_time),
            })

            print(f"Analysis {analysis_id} completed in {int(time.time() - start_time)}s")

        except Exception as e:
            print(f"Error processing audio {analysis_id}: {str(e)}")
            store.save_analysis(analysis_id, {
                "status": "failed",
                "error_message": str(e),
                "processing_time": int(time.time() - start_time),
            })

        finally:
            AudioAnalysisService.cleanup_file(file_path)


def get_audio_analysis_service():
    """Factory function to get audio analysis service"""
    return AudioAnalysisService()
