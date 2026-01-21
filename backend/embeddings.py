"""
Embedding service for ReelCall RAG
Uses HuggingFace Inference API for generating embeddings
"""

import os
import requests
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2

# Updated HuggingFace API URL (they changed from api-inference to router)
HF_API_URL = f"https://router.huggingface.co/hf-inference/pipeline/feature-extraction/{EMBEDDING_MODEL}"


def get_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for a single text using HuggingFace Inference API
    
    Args:
        text: The text to embed
        
    Returns:
        List of floats representing the embedding vector, or None if failed
    """
    if not HF_API_KEY:
        print("Warning: HF_API_KEY not set, skipping embedding generation")
        return None
    
    if not text or not text.strip():
        return None
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json={
                "inputs": text,
                "options": {"wait_for_model": True}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            embedding = response.json()
            # The API returns the embedding directly as a list
            if isinstance(embedding, list):
                # If it's nested (batch response), get first item
                if isinstance(embedding[0], list):
                    return embedding[0]
                return embedding
            return None
        else:
            print(f"HuggingFace API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None


def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors (or None for failed texts)
    """
    if not HF_API_KEY:
        print("Warning: HF_API_KEY not set, skipping embedding generation")
        return [None] * len(texts)
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json={
                "inputs": texts,
                "options": {"wait_for_model": True}
            },
            timeout=60
        )
        
        if response.status_code == 200:
            embeddings = response.json()
            return embeddings
        else:
            print(f"HuggingFace API error: {response.status_code} - {response.text}")
            return [None] * len(texts)
            
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        return [None] * len(texts)


def create_reel_text_for_embedding(transcript: str, summary: str, tags: List[str], category: str) -> str:
    """
    Create a combined text from reel data for embedding
    This ensures semantic search captures all aspects of the reel
    """
    parts = []
    
    if summary:
        parts.append(f"Summary: {summary}")
    
    if category:
        parts.append(f"Category: {category}")
    
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    
    if transcript:
        # Truncate transcript if too long (to stay within token limits)
        max_transcript_chars = 1500
        truncated_transcript = transcript[:max_transcript_chars]
        if len(transcript) > max_transcript_chars:
            truncated_transcript += "..."
        parts.append(f"Transcript: {truncated_transcript}")
    
    return "\n".join(parts)
