-- AgriDoc Liberia
-- Add official portal roles and geographical assignments.
-- This migration is intended for review before execution.

BEGIN;

-- 1. Extend the existing profile roles.
ALTER TABLE public.profiles
    DROP CONSTRAINT IF EXISTS profiles_role_check;

ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (
        role IN (
            'admin',
            'field_officer',
            'doa',
            'cac',
            'minister'
        )
    );

-- 2. CAC assignments: one official may manage multiple counties.
CREATE TABLE IF NOT EXISTS public.official_county_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    profile_id UUID NOT NULL
        REFERENCES public.profiles(id) ON DELETE CASCADE,

    county TEXT NOT NULL
        CHECK (length(trim(county)) > 0),

    assigned_by UUID
        REFERENCES public.profiles(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT official_county_assignments_unique
        UNIQUE (profile_id, county)
);

-- 3. DOA assignments: one official may manage multiple districts,
-- including districts belonging to different counties.
CREATE TABLE IF NOT EXISTS public.official_district_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    profile_id UUID NOT NULL
        REFERENCES public.profiles(id) ON DELETE CASCADE,

    county TEXT NOT NULL
        CHECK (length(trim(county)) > 0),

    district TEXT NOT NULL
        CHECK (length(trim(district)) > 0),

    assigned_by UUID
        REFERENCES public.profiles(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT official_district_assignments_unique
        UNIQUE (profile_id, county, district)
);

-- 4. Indexes for retrieving assignments efficiently.
CREATE INDEX IF NOT EXISTS idx_official_county_assignments_profile
    ON public.official_county_assignments(profile_id);

CREATE INDEX IF NOT EXISTS idx_official_county_assignments_county
    ON public.official_county_assignments(county);

CREATE INDEX IF NOT EXISTS idx_official_district_assignments_profile
    ON public.official_district_assignments(profile_id);

CREATE INDEX IF NOT EXISTS idx_official_district_assignments_location
    ON public.official_district_assignments(county, district);

-- 5. Enable RLS. Policies will be designed after reviewing
-- the existing live Supabase policies and access model.
ALTER TABLE public.official_county_assignments
    ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.official_district_assignments
    ENABLE ROW LEVEL SECURITY;

-- 6. Document the intended assignment ownership.
COMMENT ON TABLE public.official_county_assignments IS
    'Geographical county assignments for CAC officials.';

COMMENT ON TABLE public.official_district_assignments IS
    'Geographical district assignments for DOA officials.';

COMMENT ON COLUMN public.profiles.role IS
    'Supported roles: admin, field_officer, doa, cac, minister.';


-- 7. Enforce that assignment records match the official's role.
CREATE OR REPLACE FUNCTION public.enforce_official_assignment_role()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    actual_role TEXT;
    required_role TEXT;
BEGIN
    required_role := CASE TG_TABLE_NAME
        WHEN 'official_county_assignments' THEN 'cac'
        WHEN 'official_district_assignments' THEN 'doa'
    END;

    SELECT role
    INTO actual_role
    FROM public.profiles
    WHERE id = NEW.profile_id;

    IF actual_role IS DISTINCT FROM required_role THEN
        RAISE EXCEPTION
            'This assignment requires a profile with role %, but the profile has role %.',
            required_role,
            COALESCE(actual_role, 'not found');
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER check_official_county_assignment_role
BEFORE INSERT OR UPDATE OF profile_id
ON public.official_county_assignments
FOR EACH ROW
EXECUTE FUNCTION public.enforce_official_assignment_role();

CREATE TRIGGER check_official_district_assignment_role
BEFORE INSERT OR UPDATE OF profile_id
ON public.official_district_assignments
FOR EACH ROW
EXECUTE FUNCTION public.enforce_official_assignment_role();

-- 8. Prevent changing an official's role while incompatible assignments exist.
CREATE OR REPLACE FUNCTION public.prevent_incompatible_official_role_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.role IS NOT DISTINCT FROM OLD.role THEN
        RETURN NEW;
    END IF;

    IF NEW.role <> 'cac'
       AND EXISTS (
           SELECT 1
           FROM public.official_county_assignments
           WHERE profile_id = NEW.id
       ) THEN
        RAISE EXCEPTION
            'Remove this official''s county assignments before changing the CAC role.';
    END IF;

    IF NEW.role <> 'doa'
       AND EXISTS (
           SELECT 1
           FROM public.official_district_assignments
           WHERE profile_id = NEW.id
       ) THEN
        RAISE EXCEPTION
            'Remove this official''s district assignments before changing the DOA role.';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER check_official_role_before_change
BEFORE UPDATE OF role
ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.prevent_incompatible_official_role_change();

-- Trigger functions are not intended for direct application execution.
REVOKE ALL ON FUNCTION public.enforce_official_assignment_role()
    FROM PUBLIC;

REVOKE ALL ON FUNCTION public.prevent_incompatible_official_role_change()
    FROM PUBLIC;

COMMIT;
