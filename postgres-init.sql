-- PostgreSQL initialization script for Own Firebase
-- Enables Row-Level Security (RLS) and sets up multi-tenant context variables

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema for custom functions
CREATE SCHEMA IF NOT EXISTS app_funcs;

-- Define app context variables (used by RLS policies)
-- These are set via Django middleware: SET app.current_project = '...' / SET app.current_user = '...'
ALTER DATABASE ownfirebase SET app.current_project = '';
ALTER DATABASE ownfirebase SET app.current_user = '';

-- Helper function to get current project (safe fallback to empty string)
CREATE OR REPLACE FUNCTION app_funcs.current_project()
RETURNS UUID AS $$
  SELECT current_setting('app.current_project', true)::UUID;
$$ LANGUAGE SQL STABLE;

-- Helper function to get current user (safe fallback to empty string)
CREATE OR REPLACE FUNCTION app_funcs.current_user()
RETURNS INTEGER AS $$
  SELECT NULLIF(current_setting('app.current_user', true), '')::INTEGER;
$$ LANGUAGE SQL STABLE;

-- Grant permissions
GRANT USAGE ON SCHEMA app_funcs TO PUBLIC;
GRANT EXECUTE ON FUNCTION app_funcs.current_project() TO PUBLIC;
GRANT EXECUTE ON FUNCTION app_funcs.current_user() TO PUBLIC;

-- Comment for documentation
COMMENT ON FUNCTION app_funcs.current_project() IS
  'Returns the current project_id from Postgres session context (set by Django middleware)';
COMMENT ON FUNCTION app_funcs.current_user() IS
  'Returns the current user_id from Postgres session context (set by Django middleware)';
