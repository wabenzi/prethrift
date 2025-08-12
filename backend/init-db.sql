-- Initialize pgvector extension and create initial schema
-- This script runs when the PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table for caching
CREATE TABLE IF NOT EXISTS embeddings_cache (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    embedding vector(512),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_cache_embedding
ON embeddings_cache USING ivfflat (embedding vector_cosine_ops);

-- Create garments table if it doesn't exist (placeholder for demo)
CREATE TABLE IF NOT EXISTS garments (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    image_url VARCHAR(500),
    category VARCHAR(100),
    brand VARCHAR(100),
    size VARCHAR(50),
    color VARCHAR(50),
    embedding vector(512),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for garments search
CREATE INDEX IF NOT EXISTS idx_garments_embedding
ON garments USING ivfflat (embedding vector_cosine_ops);

-- Create search analytics table
CREATE TABLE IF NOT EXISTS search_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    query_text TEXT,
    search_type VARCHAR(50),
    results_count INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert sample data for testing
INSERT INTO garments (title, description, price, category, brand, size, color) VALUES
('Vintage Denim Jacket', 'Classic blue denim jacket in excellent condition', 45.00, 'jacket', 'Levis', 'M', 'blue'),
('Summer Floral Dress', 'Light summer dress with beautiful floral pattern', 35.00, 'dress', 'Zara', 'S', 'multicolor'),
('Black Leather Boots', 'Stylish black leather ankle boots', 85.00, 'shoes', 'Doc Martens', '8', 'black'),
('Wool Sweater', 'Cozy wool sweater perfect for winter', 55.00, 'sweater', 'H&M', 'L', 'gray'),
('Wide-Leg Star Appliqué Jeans', 'Vintage wide-leg jeans with star appliqués', 85.00, 'pants', 'Vintage', 'M', 'blue')
ON CONFLICT DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for garments table
DROP TRIGGER IF EXISTS update_garments_updated_at ON garments;
CREATE TRIGGER update_garments_updated_at
    BEFORE UPDATE ON garments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
