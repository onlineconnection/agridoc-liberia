CREATE TABLE public.agricultural_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    farmer_id UUID NOT NULL
        REFERENCES public.farmers(id) ON DELETE RESTRICT,

    report_type TEXT NOT NULL
        CHECK (report_type IN (
            'pest',
            'disease',
            'flooding',
            'drought',
            'crop_condition',
            'other'
        )),

    county TEXT NOT NULL,
    district TEXT NOT NULL,
    community TEXT NOT NULL,

    crop_type TEXT,

    description TEXT NOT NULL
        CHECK (length(trim(description)) > 0),

    severity TEXT
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'under_review',
            'verified',
            'dismissed'
        )),

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
)

);

CREATE INDEX idx_agricultural_reports_created_at
    ON public.agricultural_reports (created_at DESC);

CREATE INDEX idx_agricultural_reports_type_status
    ON public.agricultural_reports (report_type, status);

CREATE INDEX idx_agricultural_reports_location
    ON public.agricultural_reports (county, district, community);

CREATE INDEX idx_agricultural_reports_farmer_created
    ON public.agricultural_reports (farmer_id, created_at DESC);

ALTER TABLE public.agricultural_reports
    ENABLE ROW LEVEL SECURITY;
