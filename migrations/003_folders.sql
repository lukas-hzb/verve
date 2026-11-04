-- Personal folders preserve existing sets, card IDs, and learning progress.
BEGIN;
CREATE TABLE IF NOT EXISTS public.folders (
    id varchar(36) PRIMARY KEY,
    user_id varchar(36) NOT NULL REFERENCES public.users(id),
    name varchar(100) NOT NULL,
    CONSTRAINT uq_folders_user_name UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS ix_folders_user_id ON public.folders(user_id);
CREATE TABLE IF NOT EXISTS public.folder_sets (
    set_id varchar(36) PRIMARY KEY REFERENCES public.vocab_sets(id) ON DELETE CASCADE,
    folder_id varchar(36) NOT NULL REFERENCES public.folders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_folder_sets_folder_id ON public.folder_sets(folder_id);
COMMIT;
