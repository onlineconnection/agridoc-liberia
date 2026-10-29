CREATE TABLE public.password_reset_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'resolved')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL
);

CREATE INDEX password_reset_requests_status_requested_idx
    ON public.password_reset_requests (status, requested_at DESC);

CREATE UNIQUE INDEX password_reset_requests_one_pending_per_officer_idx
    ON public.password_reset_requests (officer_id)
    WHERE status = 'pending';

ALTER TABLE public.password_reset_requests ENABLE ROW LEVEL SECURITY;
