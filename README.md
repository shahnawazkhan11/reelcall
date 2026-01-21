# ReelCall

**Your Second Brain for Instagram Reels** - Transform saved reels into a searchable, organized database.

## Project Structure

```
reelcall/
├── backend/           # Python FastAPI backend
│   ├── main.py       # API server
│   ├── .env          # Environment variables
│   └── pyproject.toml
├── reel_vault/       # Flutter mobile app
│   └── lib/
│       ├── main.dart
│       ├── screens/
│       └── services/
└── PRD.md            # Product Requirements Document
```

## Prerequisites

### System Dependencies
1. **Python 3.9+** - Backend runtime
2. **uv** - Python package manager (install: `pip install uv`)
3. **Flutter** - Mobile app framework
4. **FFmpeg** - Audio processing
   - Windows: `winget install Gyan.FFmpeg`
   - Mac: `brew install ffmpeg`

### API Keys
- **Groq API Key** - Get from [console.groq.com](https://console.groq.com)

## Backend Setup

1. Navigate to backend folder:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment:
   ```bash
   # Edit .env file and add your Groq API key
   GROQ_API_KEY=your_key_here
   ```

4. Run the server:
   ```bash
   uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Test the API:
   - Health check: `http://localhost:8000/health`
   - API docs: `http://localhost:8000/docs`

## Flutter App Setup

1. Navigate to Flutter app folder:
   ```bash
   cd reel_vault
   ```

2. Get dependencies:
   ```bash
   flutter pub get
   ```

3. Run the app:
   ```bash
   flutter run
   ```

### Network Configuration

- **Android Emulator**: The app uses `10.0.2.2:8000` (localhost alias)
- **Physical Device**: Update `baseUrl` in `lib/services/api_service.dart` to your PC's local IP

## How It Works

1. **Share a Reel**: From Instagram, tap Share → More → ReelCall
2. **Audio Extraction**: `yt-dlp` extracts audio from the reel
3. **Transcription**: Groq's Whisper model transcribes the audio
4. **AI Analysis**: Groq's Llama 3 generates summary, tags, and category
5. **Results**: View and save the organized content

## API Endpoints

### POST /process
Process an Instagram reel URL.

**Request:**
```json
{
  "url": "https://instagram.com/reel/..."
}
```

**Response:**
```json
{
  "url": "...",
  "transcript": "...",
  "summary": "...",
  "tags": ["tag1", "tag2"],
  "category": "Education"
}
```


