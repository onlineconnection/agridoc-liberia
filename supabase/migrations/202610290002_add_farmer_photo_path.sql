-- Add optional private-storage path for each farmer's photo.
-- Review required before applying to Supabase.

ALTER TABLE public.farmers
ADD COLUMN photo_path TEXT;

COMMENT ON COLUMN public.farmers.photo_path IS
'Object path of the farmer photo in the private farmer-photos storage bucket.';
