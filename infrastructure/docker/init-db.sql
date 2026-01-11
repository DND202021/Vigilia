-- ERIOP Database Initialization Script

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS eriop;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT ALL ON SCHEMA eriop TO eriop;
GRANT ALL ON SCHEMA audit TO eriop;

-- Set search path
ALTER DATABASE eriop SET search_path TO eriop, public;

-- Placeholder comment: Tables will be created by Alembic migrations
