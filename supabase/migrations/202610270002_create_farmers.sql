-- 202610270002_create_farmers.sql
-- Migration: Create farmers table for AgriDoc Liberia
-- Purpose: Store farmer registry records
-- Review required before applying to Supabase

-- Create sequence for farmer_id generation
CREATE SEQUENCE public.farmer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Create the farmers table
CREATE TABLE public.farmers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id TEXT NOT NULL UNIQUE
    DEFAULT ('AGL-' || lpad(nextval('public.farmer_id_seq')::text, 6, '0')),
    age INTEGER CHECK (age >= 0 AND age <= 120),
    tribe TEXT,
    full_name TEXT NOT NULL,
    phone_number TEXT,
    county TEXT NOT NULL,
    district TEXT NOT NULL,
    community TEXT NOT NULL,
    registered_by UUID NOT NULL REFERENCES public.profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security on the table
ALTER TABLE public.farmers ENABLE ROW LEVEL SECURITY;