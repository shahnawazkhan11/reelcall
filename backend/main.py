"""
ReelCall Backend - Second Brain for Instagram Reels
FastAPI server that processes Instagram reel URLs
"""

import os
import re
import json
import tempfile
from pathlib import Path
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import yt_dlp
from groq import Groq

from database import get_db, Reel
from embeddings import get_embedding, create_reel_text_for_embedding

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ReelCall API",
    description="Second Brain for Instagram Reels - Extract, Transcribe, and Tag",
    version="2.0.0"
)

# Add CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ============ Pydantic Models ============

class ProcessRequest(BaseModel):
    """Request model for processing a reel URL"""
    url: str


class ReelResponse(BaseModel):
    """Response model for a reel"""
    id: str
    url: str
    transcript: Optional[str]
    summary: Optional[str]
    tags: List[str]
    category: Optional[str]
    duration_seconds: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class ReelListResponse(BaseModel):
    """Response model for list of reels"""
    reels: List[ReelResponse]
    total: int
    page: int
    per_page: int


class TagCount(BaseModel):
    """Tag with count"""
    name: str
    count: int


class TagsResponse(BaseModel):
    """Response model for tags"""
    tags: List[TagCount]


class CategoryCount(BaseModel):
    """Category with count"""
    name: str
    count: int


class CategoriesResponse(BaseModel):
    """Response model for categories"""
    categories: List[CategoryCount]


class ProcessResponse(BaseModel):
    """Response model for processed reel"""
    id: str
    url: str
    transcript: str
    summary: str
    tags: List[str]
    category: str
    created_at: str


class ChatRequest(BaseModel):
    """Request model for chat"""
    question: str
    top_k: int = 5  # Number of relevant reels to retrieve


class ChatResponse(BaseModel):
    """Response model for chat"""
    answer: str
    sources: List[dict]  # Relevant reels used to generate the answer


def validate_instagram_url(url: str) -> bool:
    """Validate that the URL is a valid Instagram reel/post URL"""
    instagram_patterns = [
        r'https?://(www\.)?instagram\.com/reel/[\w-]+',
        r'https?://(www\.)?instagram\.com/p/[\w-]+',
        r'https?://(www\.)?instagram\.com/reels/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in instagram_patterns)


def extract_audio(url: str) -> str:
    """
    Extract audio from Instagram reel using yt-dlp
    Returns path to the extracted audio file
    """
    # Create a temporary directory for the audio file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "audio.mp3")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(temp_dir, 'audio'),
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # yt-dlp adds the extension, so check for the file
        if os.path.exists(output_path):
            return output_path
        
        # Sometimes the file might have a different name
        for file in os.listdir(temp_dir):
            if file.endswith('.mp3'):
                return os.path.join(temp_dir, file)
        
        raise Exception("Audio file not found after extraction")
        
    except Exception as e:
        raise Exception(f"Failed to extract audio: {str(e)}")


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using Groq's Whisper model
    """
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
            )
        return transcription
    except Exception as e:
        raise Exception(f"Failed to transcribe audio: {str(e)}")


def extract_metadata(transcript: str) -> dict:
    """
    Extract metadata (summary, tags, category) from transcript using Groq's Llama 3
    """
    prompt = f"""Analyze the following transcript and extract metadata as JSON.

Transcript:
{transcript}

Return a JSON object with the following fields:
- summary: A brief 1-2 sentence summary of the content
- tags: An array of 3-5 relevant tags/keywords
- category: A single category that best describes the content (e.g., "Tutorial", "Entertainment", "News", "Education", "Lifestyle", "Tech", "Food", "Fitness", "Music", "Comedy")

Return ONLY the JSON object, no additional text."""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        
        response_text = chat_completion.choices[0].message.content
        metadata = json.loads(response_text)
        
        # Ensure all required fields are present
        return {
            "summary": metadata.get("summary", "No summary available"),
            "tags": metadata.get("tags", []),
            "category": metadata.get("category", "Uncategorized")
        }
    except Exception as e:
        raise Exception(f"Failed to extract metadata: {str(e)}")


def cleanup_temp_file(file_path: str):
    """Clean up temporary audio file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            # Also try to remove the parent temp directory
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
    except Exception:
        pass  # Ignore cleanup errors


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "ReelCall API is running", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============ Reel Endpoints ============

@app.post("/process", response_model=ProcessResponse)
async def process_reel(request: ProcessRequest, db: Session = Depends(get_db)):
    """
    Process an Instagram reel URL
    
    1. Check if URL already exists in database
    2. If not, validate URL and extract audio
    3. Transcribe audio using Groq Whisper
    4. Extract metadata using Groq Llama 3
    5. Save to database and return response
    """
    url = request.url.strip()
    
    print(f"Processing [{url}]...")
    
    # Step 0: Check if URL already exists
    existing_reel = db.query(Reel).filter(Reel.url == url).first()
    if existing_reel:
        print(f"Reel already exists with ID: {existing_reel.id}")
        return ProcessResponse(
            id=str(existing_reel.id),
            url=existing_reel.url,
            transcript=existing_reel.transcript or "",
            summary=existing_reel.summary or "",
            tags=existing_reel.tags or [],
            category=existing_reel.category or "Uncategorized",
            created_at=existing_reel.created_at.isoformat() if existing_reel.created_at else ""
        )
    
    # Step 1: Validate URL
    if not validate_instagram_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Instagram URL. Please provide a valid Instagram reel or post URL."
        )
    
    audio_path = None
    
    try:
        # Step 2: Extract audio
        print("Extracting audio...")
        audio_path = extract_audio(url)
        print(f"Audio extracted to: {audio_path}")
        
        # Step 3: Transcribe audio
        print("Transcribing audio...")
        transcript = transcribe_audio(audio_path)
        print(f"Transcript: {transcript}")
        
        # Step 4: Extract metadata
        print("Extracting metadata...")
        metadata = extract_metadata(transcript)
        print(f"Metadata: {metadata}")
        
        # Step 5: Generate embedding for RAG
        print("Generating embedding...")
        reel_text = create_reel_text_for_embedding(
            transcript=transcript,
            summary=metadata["summary"],
            tags=metadata["tags"],
            category=metadata["category"]
        )
        embedding = get_embedding(reel_text)
        print(f"Embedding generated: {embedding is not None}")
        
        # Step 6: Save to database
        print("Saving to database...")
        new_reel = Reel(
            url=url,
            transcript=transcript,
            summary=metadata["summary"],
            tags=metadata["tags"],
            category=metadata["category"],
            embedding=embedding
        )
        db.add(new_reel)
        db.commit()
        db.refresh(new_reel)
        print(f"Saved reel with ID: {new_reel.id}")
        
        # Step 7: Return response
        return ProcessResponse(
            id=str(new_reel.id),
            url=url,
            transcript=transcript,
            summary=metadata["summary"],
            tags=metadata["tags"],
            category=metadata["category"],
            created_at=new_reel.created_at.isoformat() if new_reel.created_at else ""
        )
        
    except Exception as e:
        print(f"Error processing reel: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process reel: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        if audio_path:
            cleanup_temp_file(audio_path)


@app.get("/reels", response_model=ReelListResponse)
async def get_reels(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Get all saved reels with optional filtering
    """
    query = db.query(Reel)
    
    # Filter by category
    if category:
        query = query.filter(Reel.category == category)
    
    # Filter by tag - use any() for PostgreSQL ARRAY
    if tag:
        query = query.filter(Reel.tags.any(tag))
    
    # Search in transcript and summary
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Reel.transcript.ilike(search_term)) |
            (Reel.summary.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Paginate and order by newest first
    reels = query.order_by(Reel.created_at.desc()) \
                 .offset((page - 1) * per_page) \
                 .limit(per_page) \
                 .all()
    
    return ReelListResponse(
        reels=[ReelResponse(
            id=str(r.id),
            url=r.url,
            transcript=r.transcript,
            summary=r.summary,
            tags=r.tags or [],
            category=r.category,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None
        ) for r in reels],
        total=total,
        page=page,
        per_page=per_page
    )


@app.get("/reels/{reel_id}", response_model=ReelResponse)
async def get_reel(reel_id: str, db: Session = Depends(get_db)):
    """Get a single reel by ID"""
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel:
            raise HTTPException(status_code=404, detail="Reel not found")
        
        return ReelResponse(
            id=str(reel.id),
            url=reel.url,
            transcript=reel.transcript,
            summary=reel.summary,
            tags=reel.tags or [],
            category=reel.category,
            duration_seconds=reel.duration_seconds,
            created_at=reel.created_at.isoformat() if reel.created_at else None,
            updated_at=reel.updated_at.isoformat() if reel.updated_at else None
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/reels/{reel_id}")
async def delete_reel(reel_id: str, db: Session = Depends(get_db)):
    """Delete a reel by ID"""
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel:
            raise HTTPException(status_code=404, detail="Reel not found")
        
        db.delete(reel)
        db.commit()
        return {"message": "Reel deleted successfully", "id": reel_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tags", response_model=TagsResponse)
async def get_tags(db: Session = Depends(get_db)):
    """Get all unique tags with counts"""
    # Get all reels with tags
    reels = db.query(Reel).filter(Reel.tags != None).all()
    
    # Count tags
    tag_counts = {}
    for reel in reels:
        if reel.tags:
            for tag in reel.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort by count descending
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return TagsResponse(
        tags=[TagCount(name=name, count=count) for name, count in sorted_tags]
    )


@app.get("/categories", response_model=CategoriesResponse)
async def get_categories(db: Session = Depends(get_db)):
    """Get all unique categories with counts"""
    results = db.query(
        Reel.category,
        func.count(Reel.id).label('count')
    ).filter(Reel.category != None) \
     .group_by(Reel.category) \
     .order_by(func.count(Reel.id).desc()) \
     .all()
    
    return CategoriesResponse(
        categories=[CategoryCount(name=r[0], count=r[1]) for r in results]
    )


# ============ RAG Chat Endpoint ============

@app.post("/chat", response_model=ChatResponse)
async def chat_with_reels(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with your saved reels using RAG (Retrieval Augmented Generation)
    
    1. Generate embedding for the user's question
    2. Find similar reels using vector similarity search
    3. Build context from relevant reels
    4. Generate answer using Groq Llama 3
    """
    question = request.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    print(f"Chat question: {question}")
    
    try:
        # Step 1: Generate embedding for the question
        print("Generating question embedding...")
        question_embedding = get_embedding(question)
        
        if question_embedding is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate embedding for question"
            )
        
        # Step 2: Find similar reels using pgvector
        print(f"Searching for {request.top_k} similar reels...")
        
        # Use pgvector's <-> operator for cosine distance
        # Lower distance = more similar
        similar_reels = db.query(Reel).filter(
            Reel.embedding != None
        ).order_by(
            Reel.embedding.cosine_distance(question_embedding)
        ).limit(request.top_k).all()
        
        if not similar_reels:
            return ChatResponse(
                answer="I don't have any saved reels to answer your question. Try saving some Instagram reels first!",
                sources=[]
            )
        
        print(f"Found {len(similar_reels)} relevant reels")
        
        # Step 3: Build context from relevant reels
        context_parts = []
        sources = []
        
        for i, reel in enumerate(similar_reels, 1):
            context_parts.append(f"""
--- Reel {i} ---
Category: {reel.category or 'Unknown'}
Tags: {', '.join(reel.tags) if reel.tags else 'None'}
Summary: {reel.summary or 'No summary'}
Transcript: {reel.transcript[:500] if reel.transcript else 'No transcript'}...
""")
            sources.append({
                "id": str(reel.id),
                "summary": reel.summary,
                "category": reel.category,
                "tags": reel.tags or [],
                "url": reel.url
            })
        
        context = "\n".join(context_parts)
        
        # Step 4: Generate answer using Groq Llama 3
        print("Generating answer...")
        
        system_prompt = """You are a helpful assistant that answers questions based on the user's saved Instagram reels. 
Use the provided context from their saved reels to answer their question.
If the context doesn't contain relevant information, say so honestly.
Be concise and helpful. Reference specific reels when appropriate."""

        user_prompt = f"""Based on the following saved Instagram reels, answer the user's question.

CONTEXT FROM SAVED REELS:
{context}

USER'S QUESTION: {question}

Provide a helpful answer based on the content from these reels:"""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=1024
        )
        
        answer = chat_completion.choices[0].message.content
        print(f"Answer generated: {answer[:100]}...")
        
        return ChatResponse(
            answer=answer,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat: {str(e)}"
        )


@app.post("/reels/{reel_id}/generate-embedding")
async def generate_reel_embedding(reel_id: str, db: Session = Depends(get_db)):
    """
    Generate embedding for an existing reel (for backfilling old reels)
    """
    try:
        reel = db.query(Reel).filter(Reel.id == reel_id).first()
        if not reel:
            raise HTTPException(status_code=404, detail="Reel not found")
        
        # Generate embedding
        reel_text = create_reel_text_for_embedding(
            transcript=reel.transcript or "",
            summary=reel.summary or "",
            tags=reel.tags or [],
            category=reel.category or ""
        )
        embedding = get_embedding(reel_text)
        
        if embedding:
            reel.embedding = embedding
            db.commit()
            return {"message": "Embedding generated successfully", "id": reel_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reels/backfill-embeddings")
async def backfill_embeddings(db: Session = Depends(get_db)):
    """
    Generate embeddings for all reels that don't have them yet
    """
    try:
        reels_without_embedding = db.query(Reel).filter(
            Reel.embedding == None
        ).all()
        
        updated = 0
        failed = 0
        
        for reel in reels_without_embedding:
            reel_text = create_reel_text_for_embedding(
                transcript=reel.transcript or "",
                summary=reel.summary or "",
                tags=reel.tags or [],
                category=reel.category or ""
            )
            embedding = get_embedding(reel_text)
            
            if embedding:
                reel.embedding = embedding
                updated += 1
            else:
                failed += 1
        
        db.commit()
        
        return {
            "message": "Backfill complete",
            "updated": updated,
            "failed": failed,
            "total": len(reels_without_embedding)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
