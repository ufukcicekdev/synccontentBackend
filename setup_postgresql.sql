-- PostgreSQL Database Setup for SyncContents
-- Run these commands as a PostgreSQL superuser (usually 'postgres')

-- Create database
CREATE DATABASE synccontents_db;

-- Create dedicated user
CREATE USER synccontents_user WITH PASSWORD 'your_strong_password_here';

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE synccontents_db TO synccontents_user;

-- Connect to the database and grant schema privileges
\c synccontents_db;
GRANT ALL ON SCHEMA public TO synccontents_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO synccontents_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO synccontents_user;

-- Set default privileges for future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO synccontents_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO synccontents_user;

-- Optional: Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- For text search improvements

-- Verify the setup
\l  -- List databases
\du -- List users

-- Exit
\q