-- migrations/000_init.sql
-- Full initial schema for LLM Workflow Assistant — MVP
-- Uses gen_random_uuid() from pgcrypto for UUID primary keys.
-- Timestamps use timestamptz.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- optional, useful for text search performance

--------------------------------------------------------------------------------
-- USERS / TEAMS / PROJECTS
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  hashed_password TEXT,
  auth_provider TEXT,            -- e.g., "auth0" or NULL for local
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_team ON projects(team_id);

--------------------------------------------------------------------------------
-- PROMPTS / PROMPT VERSIONS
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  template TEXT NOT NULL,            -- handlebars/jinja style
  default_model TEXT,
  tags TEXT[] DEFAULT '{}',
  latest_version_id UUID,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- GIN index for tag queries
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts USING GIN (tags);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  template TEXT NOT NULL,
  diff TEXT,
  created_by UUID REFERENCES users(id),
  created_at timestamptz DEFAULT now(),
  UNIQUE (prompt_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt ON prompt_versions(prompt_id);

--------------------------------------------------------------------------------
-- SESSIONS AND MESSAGES
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  created_by UUID REFERENCES users(id),
  title TEXT,
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}' ,     -- arbitrary metadata (client, pipeline, etc.)
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_tags ON sessions USING GIN (tags);

CREATE TABLE IF NOT EXISTS session_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,               -- 'user' | 'assistant' | 'system'
  prompt_id UUID REFERENCES prompts(id),
  prompt_version_id UUID REFERENCES prompt_versions(id),
  content TEXT NOT NULL,
  model TEXT,                       -- model used for the assistant response; null for user messages
  tokens_prompt INTEGER DEFAULT 0,
  tokens_response INTEGER DEFAULT 0,
  cost_usd NUMERIC(12,6) DEFAULT 0,
  embed_indexed BOOLEAN DEFAULT false,
  s3_raw_path TEXT,                 -- S3 path if full content archived
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_messages_session_created ON session_messages(session_id, created_at DESC);

--------------------------------------------------------------------------------
-- USAGE EVENTS (for token & cost analytics)
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  project_id UUID REFERENCES projects(id),
  session_message_id UUID REFERENCES session_messages(id),
  model TEXT NOT NULL,
  tokens_prompt INTEGER DEFAULT 0,
  tokens_response INTEGER DEFAULT 0,
  cost_usd NUMERIC(12,6) DEFAULT 0,
  latency_ms INTEGER,
  feedback SMALLINT,                -- 1=useful,0=neutral,-1=bad (manual user feedback)
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_by_project_time ON usage_events(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_by_user_time ON usage_events(user_id, created_at DESC);

--------------------------------------------------------------------------------
-- EMBEDDINGS (metadata mapping to vector DB entries)
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_message_id UUID REFERENCES session_messages(id) ON DELETE CASCADE,
  vector_id TEXT,                    -- id used in Pinecone / vector DB
  text_snippet TEXT,
  namespace TEXT,                    -- e.g., "prompts", "responses", "sessions"
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_vector_id ON embeddings(vector_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_namespace ON embeddings(namespace);

--------------------------------------------------------------------------------
-- FILES / ATTACHMENTS (S3 pointers)
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  uploader_id UUID REFERENCES users(id),
  s3_path TEXT NOT NULL,
  size_bytes BIGINT,
  mime_type TEXT,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);

--------------------------------------------------------------------------------
-- AGGREGATES / MATERIALIZED TABLES (optional fast analytics)
--------------------------------------------------------------------------------
-- daily usage aggregates per project (populate with a daily worker job)
CREATE TABLE IF NOT EXISTS usage_aggregates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  date date NOT NULL,
  tokens_total BIGINT DEFAULT 0,
  cost_total NUMERIC(14,6) DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  UNIQUE (project_id, date)
);

CREATE INDEX IF NOT EXISTS idx_usage_aggregates_project_date ON usage_aggregates(project_id, date DESC);

--------------------------------------------------------------------------------
-- AUDIT / ACTIVITY LOG (optional)
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id UUID,
  payload JSONB,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);

--------------------------------------------------------------------------------
-- HELPERS: triggers to update updated_at timestamps
--------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach to tables that have updated_at column
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_users'
  ) THEN
    CREATE TRIGGER set_updated_at_users
      BEFORE UPDATE ON users
      FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_prompts'
  ) THEN
    CREATE TRIGGER set_updated_at_prompts
      BEFORE UPDATE ON prompts
      FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_sessions'
  ) THEN
    CREATE TRIGGER set_updated_at_sessions
      BEFORE UPDATE ON sessions
      FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
  END IF;
END;
$$;

--------------------------------------------------------------------------------
-- SAMPLE DATA (optional seed)
--------------------------------------------------------------------------------
-- Insert a default team and project for first-time use (safe if run repeatedly)
INSERT INTO users (email, name)
  SELECT 'demo@local'::text, 'Demo User'
  WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'demo@local');

WITH demo_user AS (
  SELECT id AS user_id FROM users WHERE email = 'demo@local'
)
INSERT INTO teams (name, owner_id)
  SELECT 'default', demo_user.user_id FROM demo_user
  WHERE NOT EXISTS (SELECT 1 FROM teams WHERE name = 'default')
RETURNING id INTO TEMP TABLE tmp_demo_team;

-- Create a demo project linked to the default team if missing
WITH team_row AS (
  SELECT id FROM teams WHERE name = 'default' LIMIT 1
)
INSERT INTO projects (team_id, name, description)
  SELECT team_row.id, 'Demo Project', 'Starter project' FROM team_row
  WHERE NOT EXISTS (
    SELECT 1 FROM projects WHERE team_id = team_row.id AND name = 'Demo Project'
  );

--------------------------------------------------------------------------------
-- END OF MIGRATION
--------------------------------------------------------------------------------
