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
        
        prompt = """You are an expert in Bengali language and Banglish (Bengali written in Roman/Latin script).

Analyze this audio recording of a retail field visit conversation.

=== SCRIPT RULE — STRICTLY ENFORCED ===
ALL transcribed text MUST be written in Roman/Latin script (Banglish).
DO NOT use any Bengali Unicode characters (e.g. ক, খ, আ, ি, া, ্, etc.) anywhere in the output.
Even if the speaker says something purely in Bengali, write it phonetically in English letters.
Example: "ami bujhte parchi na" NOT "আমি বুঝতে পারছি না"
This rule has NO exceptions.

=== SCENE CONTEXT ===
An SMR (Sales Monitoring Representative / field sales agent) has walked INTO a retail shop.
The Shopkeeper is the OWNER or ATTENDANT who is already at the shop.

=== HOW TO IDENTIFY WHO IS WHO ===
You MUST use these behavioural cues to assign roles — do NOT guess based on voice alone:

SMR (the visiting field agent) — typically:
  • INITIATES the conversation and greets the shopkeeper first
  • ASKS questions: about stock, sales, product availability, competitor products
  • OFFERS or MENTIONS specific products, brands, SKUs, promotions, or prices
  • CHECKS or VERIFIES information ("apnar kache ki ache?", "ki ki lagbe?", "SO visit korche?")
  • Gives instructions or suggestions ("ei product ta rakhun", "order diye den")
  • Drives the conversation forward — usually speaks MORE and asks follow-up questions

Shopkeeper (the shop owner/attendant) — typically:
  • RESPONDS to and ANSWERS the SMR's questions
  • States what they HAVE in stock ("atta ache, mayda nai")
  • States what they NEED or want to ORDER ("2 carton din", "dam ta koto?")
  • Confirms or REJECTS offers ("theek ache", "na lagbe na")
  • May ask the price or delivery date, but rarely initiates new topics

=== KEY RULE ===
In a typical exchange:
  - The person who ASKS = SMR
  - The person who ANSWERS = Shopkeeper
If you are uncertain about a segment, look at the NEXT segment — if the next speaker is clearly the SMR asking again, the current speaker is almost certainly the Shopkeeper replying.

=== TASKS ===
1. TRANSCRIPTION: Provide a complete, accurate transcription in Banglish — Roman/Latin letters ONLY, no Bengali Unicode. Include all words (grocery items like Atta, Moyda, Suji, product names, brand names, etc.) written phonetically in English letters.

2. SPEAKER DIARIZATION: Label every segment as exactly "SMR" or "Shopkeeper" using the behavioural rules above.

3. TIME SYNCHRONIZATION: Provide approximate start and end timestamps in seconds.

=== SELF-CHECK BEFORE RESPONDING ===
Before finalising, verify:
- Does the SMR speak first and ask questions throughout?
- Does the Shopkeeper respond and provide information?
- Are question-answer pairs correctly paired between SMR and Shopkeeper?
If not, swap the labels and re-verify.

Format your response as a JSON object:
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
        
        prompt = f"""You are analyzing a Banglish retail field visit conversation transcript between:
- SMR (Sales Monitoring Representative): the visiting field sales agent who ASKS questions, checks stock, and offers products
- Shopkeeper: the shop owner/attendant who ANSWERS, states their stock, and places or refuses orders

IMPORTANT ROLE REMINDER:
- Segments labelled "SMR" = the field agent who initiated the visit
- Segments labelled "Shopkeeper" = the person at the shop responding to the SMR
- Questions in the transcript come from the SMR; answers come from the Shopkeeper

TRANSCRIPT:
{transcript_text}

QUESTIONS TO ANSWER:
{questions_text}

Answer each question with a JSON array:
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

Rules:
- Confidence between 0.0 and 1.0
- Reasoning must cite specific phrases from the transcript
- Base answers strictly on what was said, not assumed
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
