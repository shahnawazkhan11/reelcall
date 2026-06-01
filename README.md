# ReelCall ([Demo](https://drive.google.com/file/d/1LVzW4A3M2CVCA2kE8URYU0G39HJlzh9a/view))

**Your second brain for Instagram Reels** — save reels, get transcripts and AI summaries, browse your library, and ask questions across everything you've saved.

Paste a reel URL or share from Instagram → ReelCall transcribes the audio, extracts tags and categories, stores everything in PostgreSQL, and lets you **chat with your library** using RAG (Retrieval-Augmented Generation).

---

## Features

| Feature | Description |
|---------|-------------|
| **Reel processing** | Extract audio (`yt-dlp`), transcribe (`Groq Whisper`), generate summary/tags/category (`Groq Llama 3`) |
| **Library** | Browse all saved reels with search, category filters, and tag filters |
| **Result view** | Transcript, summary, tags, category, source URL, share-to-clipboard |
| **RAG chat** | Ask natural-language questions; semantic search finds relevant reels, LLM answers with sources |
| **Share intent (Android)** | Share an Instagram link from another app directly into ReelCall |
| **Deduplication** | Same URL is not processed twice — returns existing record |

---

## Architecture

![ReelCall Architecture — Library, Add Reel, and Ask data flows](docs/Architecture_ReelCall.png)

The diagram above shows the full data flow across the three app tabs:

| Block | Role |
|-------|------|
| **Flutter App** | Library (browse), Add Reel (ingest), Ask (RAG chat) |
| **FastAPI Backend** | `GET /reels`, `POST /process`, `POST /chat` |
| **External Services** | yt-dlp + FFmpeg → Groq Whisper → Groq Llama 3 → HuggingFace MiniLM |
| **Supabase** | PostgreSQL + pgvector — stores metadata and 384-dim embeddings |

### Flow summary

**① LIBRARY** — `GET /reels` → query Supabase → display reels by category (no AI)

**② ADD REEL** — `POST /process { url }` → download audio → transcribe → extract summary/tags/category → embed → save to DB → Result screen

**③ ASK** — `POST /chat { question }` → embed question → cosine similarity (top 5) → Llama 3 answer with source reels

---

### What each tab sends and receives

| Tab | User action | API call | Data in | Data out |
|-----|-------------|----------|---------|----------|
| **Library** | Open tab, search, filter by category/tag, delete | `GET /reels`, `GET /categories`, `DELETE /reels/{id}` | Query params: `search`, `category`, `tag`, `page` | List of reels from DB (no AI) |
| **Add Reel** | Paste URL or share from Instagram | `POST /process` | `{ "url": "instagram.com/reel/..." }` | Transcript, summary, tags, category → saved to DB |
| **Ask** | Type a question | `POST /chat` | `{ "question": "...", "top_k": 5 }` | Natural-language answer + reels used as sources |

---

### Data stored per reel

```mermaid
erDiagram
    REELS {
        uuid id PK
        string url UK
        text transcript
        text summary
        string_array tags
        string category
        vector embedding "384 dimensions — used by Ask tab"
        int duration_seconds
        timestamptz created_at
        timestamptz updated_at
    }
```

| Field | Written by | Read by |
|-------|------------|---------|
| `transcript`, `summary`, `tags`, `category` | Add Reel (`POST /process`) | Library, Ask (as context) |
| `embedding` | Add Reel (via HuggingFace MiniLM) | Ask only (pgvector search) |
| `url` | Add Reel | Library, Ask sources |

The embedding text is built from `summary + category + tags + transcript` so the Ask tab can find reels by meaning, not just keywords.

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **Mobile** | Flutter 3, Riverpod, go_router, `receive_sharing_intent`, `http` |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, uvicorn |
| **AI** | Groq (Whisper + Llama 3.3 70B), HuggingFace Inference (MiniLM embeddings) |
| **Media** | yt-dlp, FFmpeg |
| **Database** | PostgreSQL (Supabase), pgvector |

---

## Project structure

```
reelcall/
├── docs/
│   └── Architecture_ReelCall.png   # System architecture diagram
├── backend/
│   ├── main.py              # FastAPI app & all endpoints
│   ├── database.py          # SQLAlchemy models (Reel + vector column)
│   ├── embeddings.py        # HuggingFace embedding + text builder for RAG
│   ├── migrations/
│   │   └── 002_add_embedding_column.sql
│   ├── pyproject.toml
│   └── .env                 # Secrets (not committed)
├── reel_vault/              # Flutter app
│   └── lib/
│       ├── main.dart        # Router + bottom nav (Library / Ask / Add)
│       ├── screens/
│       │   ├── library_screen.dart
│       │   ├── chat_screen.dart
│       │   ├── home_screen.dart
│       │   ├── processing_screen.dart
│       │   └── result_screen.dart
│       └── services/
│           └── api_service.dart
└── README.md
```

---

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — `pip install uv`
- **Flutter 3.10+**
- **FFmpeg** (required by yt-dlp for audio extraction)
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
- **Supabase** (or any PostgreSQL with pgvector)
- API keys:
  - [Groq](https://console.groq.com) — transcription + metadata + chat
  - [HuggingFace](https://huggingface.co/settings/tokens) — embeddings for RAG

---

## Database setup (Supabase)

1. Create a project at [supabase.com](https://supabase.com).

2. Enable the **pgvector** extension (SQL Editor):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Create the `reels` table:

```sql
CREATE TABLE IF NOT EXISTS reels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    transcript TEXT,
    summary TEXT,
    tags TEXT[],
    category TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

4. Add the embedding column (or run `backend/migrations/002_add_embedding_column.sql`):

```sql
ALTER TABLE reels
ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE INDEX IF NOT EXISTS reels_embedding_idx
ON reels
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

5. Copy the connection string → use as `DATABASE_URL` in `.env` (use the **Session pooler** or direct URI from Supabase settings).

---

## Backend setup

### 1. Install dependencies

```bash
cd backend
uv sync
```

### 2. Environment variables

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
HF_API_KEY=your_huggingface_token
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
PORT=8000
ENVIRONMENT=local
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | Whisper transcription, metadata extraction, RAG answers |
| `HF_API_KEY` | Yes | 384-dim embeddings for semantic search |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `PORT` | No | Default `8000` |

### 3. Run the server

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health  
- Interactive API docs: http://localhost:8000/docs  

### 4. Backfill embeddings (existing reels)

If reels were saved before embeddings worked, run once:

```bash
curl -X POST http://localhost:8000/reels/backfill-embeddings
```

---

## Flutter app setup

### 1. Install dependencies

```bash
cd reel_vault
flutter pub get
```

### 2. Point the app at your backend

Edit `reel_vault/lib/services/api_service.dart`:

```dart
static const String baseUrl = 'http://YOUR_BACKEND_URL';
```

| Environment | `baseUrl` |
|-------------|-----------|
| Android emulator | `http://10.0.2.2:8000` |
| Physical device (same Wi‑Fi) | `http://YOUR_PC_LAN_IP:8000` |
| Remote / tunnel | Your [ngrok](https://ngrok.com) HTTPS URL |

When using ngrok, the app already sends the `ngrok-skip-browser-warning` header.

### 3. Run or build

```bash
# Debug on connected device/emulator
flutter run

# Release APK (Android)
flutter build apk --release
# Output: reel_vault/build/app/outputs/flutter-apk/app-release.apk
```

---

## Using the app

### Add a reel

1. Open **Add Reel** tab  
2. Paste an Instagram reel/post URL, or  
3. From Instagram: **Share** → choose **ReelCall** (Android share intent)

Processing takes ~15–60 seconds depending on reel length and network.

### Library

- View all saved reels  
- Search by text in transcript/summary  
- Filter by **category** or **tag**  
- Delete reels  

### Ask (RAG chat)

Examples:

- *"What birthday reels do I have?"*  
- *"Summarize my tech content"*  
- *"What did I save about cricket?"*

Answers cite matching reels in the **Sources** section.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/process` | Process new Instagram URL |
| `GET` | `/reels` | List reels (`page`, `per_page`, `category`, `tag`, `search`) |
| `GET` | `/reels/{id}` | Get one reel |
| `DELETE` | `/reels/{id}` | Delete a reel |
| `GET` | `/tags` | All tags with counts |
| `GET` | `/categories` | All categories with counts |
| `POST` | `/chat` | RAG Q&A over saved reels |
| `POST` | `/reels/backfill-embeddings` | Generate missing embeddings |
| `POST` | `/reels/{id}/generate-embedding` | Embed a single reel |

### `POST /process`

**Request:**

```json
{
  "url": "https://www.instagram.com/reel/XXXXXXXX/"
}
```

**Response:**

```json
{
  "id": "uuid",
  "url": "https://www.instagram.com/reel/XXXXXXXX/",
  "transcript": "...",
  "summary": "...",
  "tags": ["birthday", "cake", "gift"],
  "category": "Lifestyle",
  "created_at": "2026-05-31T12:00:00"
}
```

### `POST /chat`

**Request:**

```json
{
  "question": "What birthday reels do I have?",
  "top_k": 5
}
```

**Response:**

```json
{
  "answer": "You have one birthday-related reel...",
  "sources": [
    {
      "id": "uuid",
      "summary": "...",
      "category": "Lifestyle",
      "tags": ["birthday", "cake"],
      "url": "https://www.instagram.com/reel/..."
    }
  ]
}
```

---

## How tags are generated

Tags are **not** rule-based keyword extraction. After transcription, **Groq Llama 3.3 70B** analyzes the transcript and returns structured JSON:

- `summary` — 1–2 sentences  
- `tags` — 3–5 semantic keywords  
- `category` — one label (e.g. Lifestyle, Tech, Education)

The same metadata is included in the text used for embeddings, which improves semantic search quality.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Chat returns 500 on embedding | Ensure `HF_API_KEY` is set and backend uses the router URL with `/models/` in the path (`embeddings.py`) |
| Chat finds no reels | Run `POST /reels/backfill-embeddings` so all reels have vectors |
| App can't reach backend | Check `baseUrl`, firewall, and that phone/emulator can reach the host |
| `yt-dlp` / audio errors | Install FFmpeg and ensure the Instagram URL is public |
| Groq rate limits | Wait and retry; reduce concurrent requests |

---

## Security notes

- Never commit `backend/.env` or API keys to git (`.gitignore` excludes them).  
- Rotate keys if they were exposed.  
- The backend uses `allow_origins=["*"]` for development — restrict CORS in production.  
- Instagram content is processed server-side; only derived text and embeddings are stored.

---

## License

MIT 
