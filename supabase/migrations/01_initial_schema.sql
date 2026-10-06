-- LocalLens v4 — Supabase Schema & Initial Migration
-- File: supabase/migrations/01_initial_schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table (tied to auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. User Preferences
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    default_profile TEXT DEFAULT 'family',
    default_priorities JSONB DEFAULT '["education", "healthcare", "transport", "daily_life"]'::jsonb,
    distance_preferences JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Report Credits (3 free credits on verified email)
CREATE TABLE IF NOT EXISTS public.report_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    credits_remaining INT NOT NULL DEFAULT 3 CHECK (credits_remaining >= 0),
    credits_used INT NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Search History
CREATE TABLE IF NOT EXISTS public.search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    locality_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    searched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    provider TEXT
);

-- 5. Saved Locations
CREATE TABLE IF NOT EXISTS public.saved_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    locality_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    label TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Reports Table
CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    locality_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    comparison_locality_name TEXT,
    comparison_lat DOUBLE PRECISION,
    comparison_lng DOUBLE PRECISION,
    user_profile TEXT,
    user_priorities JSONB,
    sections_included JSONB,
    verification_hash TEXT NOT NULL,
    pdf_storage_path TEXT,
    qr_code_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('generating', 'ready', 'failed')) DEFAULT 'generating'
);

-- 7. Report Data Snapshots (Only Storable Providers: OSM Overpass + Open-Meteo)
CREATE TABLE IF NOT EXISTS public.report_data_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    raw_evidence JSONB NOT NULL,
    aggregated_metrics JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    providers_used JSONB NOT NULL
);

-- 8. Report Properties (User-declared context)
CREATE TABLE IF NOT EXISTS public.report_properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    property_address TEXT,
    floor_level TEXT,
    unit_facing TEXT,
    water_source_declared TEXT,
    power_backup_declared TEXT,
    rent_or_price TEXT,
    user_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. Feedback
CREATE TABLE IF NOT EXISTS public.feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    locality_name TEXT,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('incorrect_data', 'missing_place', 'general')),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. Enable Row Level Security (RLS) on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_data_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- 11. RLS Policies (auth.uid() = user_id)
CREATE POLICY "Users can manage own profile" ON public.profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users can manage own preferences" ON public.user_preferences FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own credits" ON public.report_credits FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own search history" ON public.search_history FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own saved locations" ON public.saved_locations FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own reports" ON public.reports FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own report data snapshots" ON public.report_data_snapshots FOR ALL USING (
    EXISTS (SELECT 1 FROM public.reports WHERE reports.id = report_data_snapshots.report_id AND reports.user_id = auth.uid())
);
CREATE POLICY "Users can view own report properties" ON public.report_properties FOR ALL USING (
    EXISTS (SELECT 1 FROM public.reports WHERE reports.id = report_properties.report_id AND reports.user_id = auth.uid())
);
CREATE POLICY "Anyone can submit feedback" ON public.feedback FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can view own feedback" ON public.feedback FOR SELECT USING (auth.uid() = user_id);

-- 12. Public Verification View (NO PII, NO private notes, accessible to public anon)
CREATE OR REPLACE VIEW public.public_report_verifications AS
SELECT 
    id,
    title,
    locality_name,
    comparison_locality_name,
    created_at,
    verification_hash,
    status
FROM public.reports;

GRANT SELECT ON public.public_report_verifications TO anon, authenticated;

-- 13. Trigger to initialize profile and 3 credits upon user signup/verification
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email));

    INSERT INTO public.user_preferences (user_id)
    VALUES (NEW.id);

    -- If user is email-verified upon creation, grant 3 credits
    IF NEW.email_confirmed_at IS NOT NULL THEN
        INSERT INTO public.report_credits (user_id, credits_remaining, credits_used)
        VALUES (NEW.id, 3, 0)
        ON CONFLICT (user_id) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger to grant 3 credits when email is confirmed later
CREATE OR REPLACE FUNCTION public.handle_user_email_confirmed()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.email_confirmed_at IS NULL AND NEW.email_confirmed_at IS NOT NULL THEN
        INSERT INTO public.report_credits (user_id, credits_remaining, credits_used)
        VALUES (NEW.id, 3, 0)
        ON CONFLICT (user_id) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_email_confirmed
    AFTER UPDATE OF email_confirmed_at ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_user_email_confirmed();
