-- AgriDoc Liberia
-- Store farmer crop information submissions for Ministry analytics.

CREATE TABLE public.farmer_crop_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    farmer_id UUID NOT NULL
        REFERENCES public.farmers(id) ON DELETE RESTRICT,

    crop_type TEXT NOT NULL
        CHECK (length(trim(crop_type)) > 0),

    farm_size NUMERIC(12,2)
        CHECK (farm_size IS NULL OR farm_size > 0),

    farm_size_unit TEXT
        CHECK (farm_size_unit IN ('acres', 'hectares')),

    activity TEXT NOT NULL
        CHECK (activity IN (
            'planned',
            'planted',
            'harvesting',
            'harvested'
        )),

    county TEXT NOT NULL,
    district TEXT NOT NULL,
    community TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'verified',
            'dismissed'
        )),

    source TEXT NOT NULL DEFAULT 'ussd'
        CHECK (source IN ('ussd', 'field_officer')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    reviewed_by UUID
        REFERENCES public.profiles(id) ON DELETE SET NULL,

    reviewed_at TIMESTAMPTZ,

    CHECK (
        (reviewed_by IS NULL AND reviewed_at IS NULL)
        OR
        (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    ),

    CHECK (
        status NOT IN ('verified', 'dismissed')
        OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    ),

    CHECK (
        (farm_size IS NULL AND farm_size_unit IS NULL)
        OR
        (farm_size IS NOT NULL AND farm_size_unit IS NOT NULL)
    )
);

CREATE INDEX idx_farmer_crop_reports_farmer
    ON public.farmer_crop_reports (farmer_id, created_at DESC);

CREATE INDEX idx_farmer_crop_reports_location
    ON public.farmer_crop_reports (county, district, community);

CREATE INDEX idx_farmer_crop_reports_crop_activity
    ON public.farmer_crop_reports (crop_type, activity);

CREATE INDEX idx_farmer_crop_reports_status
    ON public.farmer_crop_reports (status, created_at DESC);

ALTER TABLE public.farmer_crop_reports
    ENABLE ROW LEVEL SECURITY;
