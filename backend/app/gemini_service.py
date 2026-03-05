import json
import time
from typing import Dict, List, Tuple
import google.generativeai as genai
from app.config import get_settings
from app.schemas import QAResult, TranscriptSegment, SpeakerDiarization

settings = get_settings()

# Configure Gemini API
genai.configure(api_key=settings.gemini_api_key)

class GeminiService:
    """Service for interacting with Google Gemini API for audio analysis"""
    
    MODEL = "gemini-2.5-flash"
    
    @staticmethod
    def upload_audio_file(file_path: str):
        """
        Upload audio file to Gemini API for processing
        Returns: Gemini File object for use in generate_content
        """
        print(f"Uploading audio file: {file_path}")
        
        file_response = genai.upload_file(file_path, mime_type="audio/mpeg")
        print(f"Uploaded file: {file_response.name}")
        
        # Wait for file to become active
        import time as _time
        while file_response.state.name == "PROCESSING":
            print("Waiting for file to be processed...")
            _time.sleep(2)
            file_response = genai.get_file(file_response.name)
        
        if file_response.state.name == "FAILED":
            raise ValueError(f"File processing failed: {file_response.state.name}")
        
        print(f"File ready: {file_response.name}")
        return file_response
    
    @staticmethod
    def transcribe_and_diarize(gemini_file) -> Tuple[List[TranscriptSegment], List[SpeakerDiarization]]:
        """
        Stage 1: Perform transcription and speaker diarization
        
        Uses Gemini's multimodal capabilities to:
        1. Transcribe audio in Banglish format
        2. Identify different speakers (Customer, Shopkeeper, etc.)
        3. Provide time-synced transcript
        
        Args:
            gemini_file: Gemini File object returned from upload_audio_file
            
        Returns:
            Tuple of (transcript_segments, speaker_diarization)
        """
        print("Starting transcription and speaker diarization...")
        
        prompt = """You are an expert in Bengali language and Banglish (Bengali written in Latin script or mixed with English).
        
Analyze this audio recording of a retail field visit conversation. The conversation is in Banglish.

CONTEXT: This is a conversation between an SMR (Sales Monitoring Representative) who visits retail shops, and a Shopkeeper. The SMR checks what products the shop has in stock and what they need to reorder.

Please perform the following tasks:

1. TRANSCRIPTION: Provide a complete, accurate transcription of the conversation in Banglish. Include all words, including grocery items like "Atta," "Moyda," "Suji," etc.

2. SPEAKER DIARIZATION: Identify the different speakers in the conversation. Classify each speaker as either "SMR" (the visiting sales representative) or "Shopkeeper".

3. TIME SYNCHRONIZATION: For each utterance, provide approximate start and end times in seconds.

Format your response as a JSON object with the following structure:
{
    "transcript": [
        {
            "speaker": "SMR",
            "text": "bhai, apnar stock e ki ki ache?",
            "timestamp_start": 0.5,
            "timestamp_end": 2.3
        },
        {
            "speaker": "Shopkeeper", 
            "text": "atta ache, kintu moyda lagbe",
            "timestamp_start": 2.5,
            "timestamp_end": 4.1
        }
    ],
    "speakers": [
        {
            "speaker_id": "SPEAKER_1",
            "role": "SMR",
            "segment_count": 5
        },
        {
            "speaker_id": "SPEAKER_2",
            "role": "Shopkeeper",
            "segment_count": 6
        }
    ]
}

Be very careful to:
- Accurately capture Banglish terms and phonetics
- Correctly identify grocery and retail items
- Preserve the exact meaning even if written in English transliteration
- Mark speaker changes clearly
- The SMR is typically the one asking questions about stock and offering products
- The Shopkeeper is the one responding about what they have and what they need
"""
        
        try:
            model = genai.GenerativeModel(GeminiService.MODEL)
            response = model.generate_content(
                [prompt, gemini_file]
            )
            
            # Parse the response
            response_text = response.text
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            result = json.loads(json_str)
            
            # Convert to Pydantic models
            transcript_segments = [
                TranscriptSegment(**segment) for segment in result.get("transcript", [])
            ]
            
            speaker_diarization = [
                SpeakerDiarization(**speaker) for speaker in result.get("speakers", [])
            ]
            
            print(f"Successfully transcribed {len(transcript_segments)} segments from {len(speaker_diarization)} speakers")
            return transcript_segments, speaker_diarization
            
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            raise
    
    @staticmethod
    def analyze_qa(transcript_text: str, questions: List[Dict]) -> List[QAResult]:
        """
        Stage 2: Perform Q&A analysis on the transcript
        
        Takes the generated transcript and answers predefined Yes/No questions
        to extract business insights (product inquiry, availability confirmation, etc.)
        
        Args:
            transcript_text: Full transcript from Stage 1
            questions: List of question dictionaries with 'id' and 'question' keys
            
        Returns:
            List of QAResult objects with answers and confidence scores
        """
        print("Starting Q&A analysis...")
        
        questions_text = "\n".join([f"{i+1}. {q['question']}" for i, q in enumerate(questions)])
        
        prompt = f"""Based on the following Banglish retail field visit conversation transcript between an SMR (Sales Monitoring Representative) and a Shopkeeper, answer the following Yes/No questions.

CONTEXT: The SMR visits retail shops to check stock levels, take orders, and understand shopkeeper needs.

TRANSCRIPT:
{transcript_text}

QUESTIONS:
{questions_text}

For each question, respond with a JSON array of objects in this format:
[
    {{
        "question": "Did the SMR ask the shopkeeper about current stock/inventory?",
        "answer": true,
        "confidence": 0.95,
        "reasoning": "The SMR asked 'apnar stock e ki ki ache?' (what do you have in stock?)"
    }},
    {{
        "question": "Did the shopkeeper mention any product they need?",
        "answer": true,
        "confidence": 0.92,
        "reasoning": "The shopkeeper said 'moyda lagbe' (need flour/moyda)"
    }}
]

Confidence should be between 0.0 and 1.0.
Reasoning should explain your answer based on specific parts of the transcript.
"""
        
        try:
            model = genai.GenerativeModel(GeminiService.MODEL)
            response = model.generate_content(prompt)
            
            response_text = response.text
            
            # Extract JSON from response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            results = json.loads(json_str)
            
            # Convert to QAResult models
            qa_results = [QAResult(**result) for result in results]
            
            print(f"Successfully analyzed {len(qa_results)} questions")
            return qa_results
            
        except Exception as e:
            print(f"Error during Q&A analysis: {str(e)}")
            raise

def get_gemini_service():
    """Factory function to get Gemini service instance"""
    return GeminiService()
