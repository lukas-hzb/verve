-- Preserve existing application IDs and their vocabulary foreign keys.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS neon_auth_id varchar(36);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_neon_auth_id ON public.users (neon_auth_id);
-- google_sub and password_hash remain migration data until every legacy account
-- has been linked. They no longer authenticate users in the application.
