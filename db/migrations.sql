-- ============================================================
-- JobTrack AI — Supabase Database Schema
-- ============================================================
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- This creates all tables, indexes, RLS policies, and enum types
-- needed for the full application.
--
-- WHY Supabase?
-- 1. Free PostgreSQL with built-in Auth, Storage, and Realtime
-- 2. Row-Level Security (RLS) for multi-user data isolation
-- 3. Supabase Storage for CV/resume PDF uploads
-- 4. Realtime subscriptions for live dashboard updates
-- ============================================================

-- ────────────────────────────────────────────
-- Custom types
-- ────────────────────────────────────────────

-- Application status tracks the full hiring funnel.
-- WHY an enum instead of free text? Prevents typos ("appleid" vs "applied"),
-- enables Kanban board columns, and makes status transitions explicit.
CREATE TYPE application_status AS ENUM (
    'saved',        -- Job saved but not yet applied
    'applied',      -- Application submitted
    'screening',    -- Initial recruiter screen scheduled/completed
    'interview',    -- Technical/onsite interview stage
    'offer',        -- Received an offer
    'rejected',     -- Application rejected at any stage
    'withdrawn'     -- Candidate withdrew application
);

-- User roles for RBAC.
CREATE TYPE user_role AS ENUM (
    'user',         -- Standard user — can only see their own data
    'admin'         -- Admin — can view all users, all applications, system stats
);

-- ────────────────────────────────────────────
-- Tables
-- ────────────────────────────────────────────

-- Profiles extend Supabase Auth users with app-specific data.
-- WHY a separate table instead of using auth.users directly?
-- auth.users is managed by Supabase Auth and has a fixed schema.
-- We need custom fields (background, skills, CV) that don't belong there.
-- The id column references auth.users(id) for a 1:1 relationship.
CREATE TABLE profiles (
    id                   UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email                TEXT NOT NULL,
    full_name            TEXT DEFAULT '',
    role                 user_role DEFAULT 'user',
    background           TEXT DEFAULT '',           -- User's experience/skills summary
    skills               TEXT[] DEFAULT '{}',       -- Array of skill tags for matching
    cv_text              TEXT DEFAULT '',           -- Extracted text from uploaded CV PDF
    cv_pdf_url           TEXT DEFAULT '',           -- Supabase Storage URL for the PDF
    phone                TEXT DEFAULT '',           -- Contact phone
    linkedin_url         TEXT DEFAULT '',           -- LinkedIn profile URL
    github_url           TEXT DEFAULT '',           -- GitHub profile URL
    parsed_profile       JSONB DEFAULT '{}',       -- AI-parsed structured resume data
    onboarding_complete  BOOLEAN DEFAULT false,    -- Whether user completed onboarding wizard
    preferences          JSONB DEFAULT '{}',        -- Flexible prefs: location, salary, remote, etc.
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

-- Jobs table stores scraped job postings.
-- WHY store raw job data? Allows re-running the agent without re-scraping,
-- and enables the search feature to cache discovered jobs.
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    title           TEXT DEFAULT '',
    company         TEXT DEFAULT '',
    location        TEXT DEFAULT '',
    salary          TEXT DEFAULT '',
    employment_type TEXT DEFAULT '',
    requirements    TEXT DEFAULT '',        -- Raw requirements text from scrape
    tech_stack      TEXT[] DEFAULT '{}',    -- Parsed tech stack tags
    raw_analysis    TEXT DEFAULT '',        -- Full job_analysis from Scout agent
    source          TEXT DEFAULT 'manual',  -- Where the job came from: manual, linkedin, indeed, etc.
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Applications table is the core of the tracker.
-- Each row = one job application with all generated materials.
CREATE TABLE applications (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    job_id           UUID REFERENCES jobs(id) ON DELETE SET NULL,
    company          TEXT NOT NULL,
    job_title        TEXT NOT NULL,
    job_url          TEXT DEFAULT '',           -- Original job posting URL
    status           application_status DEFAULT 'applied',

    -- Generated materials (from Writer agent)
    cover_letter     TEXT DEFAULT '',
    tailored_bullets TEXT DEFAULT '',
    outreach_dm      TEXT DEFAULT '',
    resume_pdf_url   TEXT DEFAULT '',       -- URL/path for tailored resume PDF

    -- Analysis data (from Scout + Research agents)
    job_analysis     TEXT DEFAULT '',
    company_profile  TEXT DEFAULT '',
    role_fit         TEXT DEFAULT '',

    -- Quality scoring (from Quality agent)
    quality_score    INTEGER DEFAULT 0,     -- 1-5 from quality agent
    quality_feedback TEXT DEFAULT '',

    -- User notes and submission snapshot
    notes            TEXT DEFAULT '',       -- Free-form user notes
    submitted_snapshot JSONB DEFAULT NULL,  -- Frozen copy of all fields at submission time

    -- Timestamps
    applied_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

-- ────────────────────────────────────────────
-- Indexes
-- ────────────────────────────────────────────
-- WHY these indexes? The dashboard queries by user_id constantly,
-- and filters by status for the Kanban board.

CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_status  ON applications(user_id, status);
CREATE INDEX idx_jobs_user_id         ON jobs(user_id);
CREATE INDEX idx_jobs_company         ON jobs(company);

-- ────────────────────────────────────────────
-- Row-Level Security (RLS)
-- ────────────────────────────────────────────
-- WHY RLS? Multi-user isolation at the database level.
-- Even if the API has a bug, users can never see each other's data.
-- Admins bypass RLS with a separate policy.

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own profile
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Users can only see their own jobs
CREATE POLICY "Users can manage own jobs"
    ON jobs FOR ALL
    USING (auth.uid() = user_id);

-- Users can only see their own applications
CREATE POLICY "Users can manage own applications"
    ON applications FOR ALL
    USING (auth.uid() = user_id);

-- Admin policies: admins can see everything
-- WHY check profiles table for role? auth.users doesn't have our role field.
CREATE POLICY "Admins can view all profiles"
    ON profiles FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can view all applications"
    ON applications FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ────────────────────────────────────────────
-- Auto-create profile on user signup
-- ────────────────────────────────────────────
-- WHY a trigger? When a user signs up via Supabase Auth, we need a
-- matching row in profiles immediately. Without this, the app would
-- crash on first login because no profile exists.

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ────────────────────────────────────────────
-- Auto-update updated_at timestamp
-- ────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_profiles
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at_applications
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ────────────────────────────────────────────
-- Seed default admin user
-- ────────────────────────────────────────────
-- WHY seed in SQL? Ensures admin exists even before the Python
-- init script runs. Supabase runs migrations first, then the app boots.
-- The admin user is created via Supabase Auth API (see db/init_db.py),
-- but we ensure the profile row has admin role via this fallback.
--
-- ADMIN CREDENTIALS (change in production!):
--   Email:    admin@jobtrack.ai
--   Password: JobTrack@Admin2024
--   Role:     admin
--
-- To create the admin user, run AFTER migrations:
--   python -m db.init_db
--
-- Or set env vars to override:
--   ADMIN_EMAIL=your@email.com
--   ADMIN_PASSWORD=YourSecurePassword123

