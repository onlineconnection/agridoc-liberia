-- 202610270001_create_profiles.sql
-- Migration: Create profiles table for AgriDoc Liberia
-- Purpose: Store user profiles linked to Supabase Auth users
-- Review required before applying to Supabase

-- Create the profiles table
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'field_officer')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    can_register_farmers BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security (RLS) on the table
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;