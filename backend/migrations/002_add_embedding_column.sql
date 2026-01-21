-- Migration: Add embedding column to reels table for RAG support
-- Run this in your Supabase SQL Editor

-- First, make sure pgvector extension is enabled (should already be done)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add the embedding column (384 dimensions for all-MiniLM-L6-v2)
ALTER TABLE reels 
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Create an index for faster similarity searches
CREATE INDEX IF NOT EXISTS reels_embedding_idx 
ON reels 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'reels' AND column_name = 'embedding';
