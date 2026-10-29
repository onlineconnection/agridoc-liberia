-- AgriDoc Liberia: add field officer details.
-- Review this migration before applying it to Supabase.

ALTER TABLE public.profiles
    ADD COLUMN full_name TEXT,
    ADD COLUMN phone_number TEXT,
    ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT false;
