-- Allow crop reports without a farming activity selection.
ALTER TABLE public.farmer_crop_reports
ALTER COLUMN activity DROP NOT NULL;
