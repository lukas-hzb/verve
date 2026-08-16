-- Harden the migrated Neon schema without modifying application data.

begin;

alter table public.users
    alter column username set not null,
    alter column email set not null,
    alter column created_at set not null;

alter table public.vocab_sets
    alter column name set not null,
    alter column is_shared set not null,
    alter column created_at set not null,
    alter column updated_at set not null;

alter table public.cards
    alter column vocab_set_id set not null,
    alter column front set not null,
    alter column back set not null,
    alter column level set not null,
    alter column next_review set not null,
    alter column last_practice_wrong set not null;

create unique index if not exists uq_users_username_lower
    on public.users (lower(username));

create unique index if not exists uq_users_email_lower
    on public.users (lower(email));

create index if not exists ix_vocab_sets_user_id
    on public.vocab_sets (user_id);

create index if not exists ix_cards_set_due
    on public.cards (vocab_set_id, next_review);

create index if not exists ix_cards_set_shuffle
    on public.cards (vocab_set_id, shuffle_order);

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'uq_vocab_sets_user_name'
          and conrelid = 'public.vocab_sets'::regclass
    ) then
        alter table public.vocab_sets
            add constraint uq_vocab_sets_user_name unique (user_id, name);
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'ck_vocab_sets_owner_or_shared'
          and conrelid = 'public.vocab_sets'::regclass
    ) then
        alter table public.vocab_sets
            add constraint ck_vocab_sets_owner_or_shared
            check ((is_shared and user_id is null) or (not is_shared and user_id is not null));
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'ck_cards_level_positive'
          and conrelid = 'public.cards'::regclass
    ) then
        alter table public.cards
            add constraint ck_cards_level_positive check (level >= 1);
    end if;
end $$;

commit;
