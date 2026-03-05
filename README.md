# Retail Voice Analyst

AI-powered audio analysis tool for retail field visits. Processes Banglish (Bengali-English) conversations between SMRs (Sales Monitoring Representatives) and shopkeepers. Uses Google Gemini to transcribe audio with speaker diarization and answers predefined Yes/No business questions with confidence scores.

## Tech Stack

- **Backend**: Python, FastAPI
- **AI Model**: Google Gemini 2.5 Flash
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Storage**: In-memory 

## Project Structure

```
RetailVoiceAnalyst/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & API routes
│   │   ├── config.py            # Settings from .env
│   │   ├── gemini_service.py    # Gemini API integration
│   │   ├── audio_service.py     # Analysis orchestration & questions
│   │   ├── schemas.py           # Pydantic models
│   │   └── store.py             # In-memory storage
│   ├── requirements.txt
│   └── .env
├── frontend/
│   └── index.html
├── .gitignore
└── README.md
```

## Setup & Run

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/retail-voice-analyst.git
cd retail-voice-analyst
```

### 2. Create conda environment

```bash
conda create -n retailvoice python=3.11 -y
conda activate retailvoice
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure API key

Create `backend/.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
UPLOAD_DIR=./temp_uploads
MAX_FILE_SIZE=52428800
ALLOWED_AUDIO_FORMATS=mp3,wav,m4a
```

Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 5. Run the server

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

### 6. Open in browser

```
http://localhost:8765
```

To access from another PC on the same network, use your machine's IP:

```
http://<your-ip>:8765
```

## How It Works

1. **Upload** an MP3/WAV/M4A audio file of an SMR-Shopkeeper conversation
2. **Stage 1** — Gemini transcribes the audio with speaker diarization (SMR vs Shopkeeper)
3. **Stage 2** — Gemini answers predefined Yes/No questions about the conversation
4. **Results** — View transcript and Q&A answers with confidence scores

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/upload-audio` | Upload audio file for analysis |
| GET | `/api/v1/analysis/{id}` | Get analysis results |
| GET | `/api/v1/analysis/{id}/status` | Get analysis status |
| GET | `/api/v1/analyses` | List all analyses |
| DELETE | `/api/v1/analysis/{id}` | Delete an analysis |
| GET | `/api/v1/questions` | Get predefined questions |
