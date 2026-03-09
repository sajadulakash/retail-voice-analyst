# Retail Voice Analyst

AI-powered audio analysis tool for retail field visits. Processes Banglish (Bengali-English) conversations between SMRs (Sales Monitoring Representatives) and shopkeepers. Uses Google Gemini to transcribe audio with speaker diarization and answers fully customisable Yes/No business questions with confidence scores.

## Features

- 🎙️ **Audio transcription** — Banglish (Roman script) output, no Bengali Unicode
- 👥 **Speaker diarization** — Accurately identifies SMR vs Shopkeeper using conversational behaviour cues
- ❓ **Dynamic Q&A** — Add, edit, and delete analysis questions from the UI at any time
- 💾 **Question persistence** — Questions saved to `backend/data/questions.json` and survive server restarts
- 📋 **Analysis history** — View past analyses with full transcript and Q&A results
- 📊 **Confidence scores** — Every answer includes a confidence % and reasoning

## Tech Stack

- **Backend**: Python, FastAPI
- **AI Model**: Google Gemini 2.5 Flash
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Storage**: In-memory (analyses) + JSON file (questions)

## Project Structure

```
RetailVoiceAnalyst/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & API routes
│   │   ├── config.py            # Settings from .env
│   │   ├── gemini_service.py    # Gemini API integration (transcription + Q&A)
│   │   ├── audio_service.py     # Analysis orchestration & default questions
│   │   ├── schemas.py           # Pydantic models
│   │   └── store.py             # In-memory store + question persistence
│   ├── data/
│   │   └── questions.json       # Persisted questions (auto-created on first run)
│   ├── temp_uploads/            # Temporary audio files (auto-cleaned)
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
git clone https://github.com/<your-username>/RetailVoiceAnalyst.git
cd RetailVoiceAnalyst
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

To access from another device on the same network:

```
http://<your-ip>:8765
```

## How It Works

1. **Upload** an MP3/WAV/M4A audio file of an SMR–Shopkeeper conversation
2. **Stage 1** — Gemini transcribes the audio in Banglish (Roman script) with speaker diarization
   - SMR identified as the one **asking questions** and driving the conversation
   - Shopkeeper identified as the one **responding** and stating stock/order needs
3. **Stage 2** — Gemini answers your configured Yes/No questions about the conversation
4. **Results** — View the full transcript and Q&A answers with confidence scores and reasoning

## Managing Questions

Questions are fully dynamic — no code changes needed:

- Click **⚙️ Manage** next to "Analysis Questions" on the upload page
- **Add** new questions with an optional category tag
- **Edit** any existing question inline
- **Delete** questions you no longer need
- Changes take effect immediately for the next audio upload
- All changes are saved to `backend/data/questions.json` and persist across restarts

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload-audio` | Upload audio file for analysis |
| `GET` | `/api/v1/analysis/{id}` | Get full analysis results |
| `GET` | `/api/v1/analysis/{id}/status` | Poll analysis status |
| `GET` | `/api/v1/analyses` | List all analyses (paginated) |
| `DELETE` | `/api/v1/analysis/{id}` | Delete an analysis record |
| `GET` | `/api/v1/questions` | Get all questions |
| `POST` | `/api/v1/questions` | Add a new question |
| `PUT` | `/api/v1/questions/{id}` | Update a question |
| `DELETE` | `/api/v1/questions/{id}` | Delete a question |
| `GET` | `/health` | Health check |
