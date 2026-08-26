#!/usr/bin/env python3
"""Migrate Verve's public data and Supabase credentials to Neon Postgres."""

import argparse
import getpass
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, insert, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / '.env')
load_dotenv(PROJECT_ROOT / '.env.local', override=True)

from app.database import db  # noqa: E402
from app.data.standard_sets import HAUPTSTAEDTE_DATA  # noqa: E402
from app.models import Card, User, VocabSet  # noqa: E402,F401


TABLES = ('users', 'vocab_sets', 'cards')


def safe_endpoint(database_url: str) -> str:
    """Return a connection identifier without credentials."""
    url = make_url(database_url)
    return f"{url.host}/{url.database}"


def fetch_source_data(source_engine):
    """Read app rows plus portable password/OAuth identity data from Supabase."""
    inspector = inspect(source_engine)
    available_tables = set(inspector.get_table_names(schema='public'))
    app_tables = set(TABLES)

    if not available_tables.intersection(app_tables):
        return [], [], []

    missing_tables = app_tables - available_tables
    if missing_tables:
        missing = ', '.join(sorted(missing_tables))
        raise RuntimeError(f'Source schema is incomplete; missing tables: {missing}')

    card_columns = {column['name'] for column in inspector.get_columns('cards')}
    practice_expr = 'last_practice_wrong' if 'last_practice_wrong' in card_columns else 'false AS last_practice_wrong'
    shuffle_expr = 'shuffle_order' if 'shuffle_order' in card_columns else 'null::integer AS shuffle_order'

    with source_engine.connect() as connection:
        users = [dict(row) for row in connection.execute(text("""
            SELECT id::text AS id, username, lower(email) AS email, created_at, avatar_file
            FROM public.users
            ORDER BY created_at, id
        """)).mappings()]

        vocab_sets = [dict(row) for row in connection.execute(text("""
            SELECT id::text AS id, name, user_id::text AS user_id, is_shared, created_at, updated_at
            FROM public.vocab_sets
            ORDER BY created_at, id
        """)).mappings()]

        cards = [dict(row) for row in connection.execute(text(f"""
            SELECT id::text AS id, vocab_set_id::text AS vocab_set_id, front, back,
                   level, next_review, {practice_expr}, {shuffle_expr}
            FROM public.cards
            ORDER BY id
        """)).mappings()]

        password_hashes = {
            row.id: row.encrypted_password
            for row in connection.execute(text("""
                SELECT id::text AS id, encrypted_password
                FROM auth.users
                WHERE encrypted_password IS NOT NULL AND encrypted_password <> ''
            """))
        }

        google_subjects = {
            row.user_id: row.google_sub
            for row in connection.execute(text("""
                SELECT user_id::text AS user_id,
                       coalesce(provider_id::text, identity_data ->> 'sub') AS google_sub
                FROM auth.identities
                WHERE provider = 'google'
            """))
            if row.google_sub
        }

    for user in users:
        user['password_hash'] = password_hashes.get(user['id'])
        user['google_sub'] = google_subjects.get(user['id'])

    return users, vocab_sets, cards


def ensure_default_set(vocab_sets, cards) -> None:
    """Seed the built-in shared set when the source has no equivalent data."""
    if any(vocab_set['name'] == 'Hauptstädte' and vocab_set['is_shared'] for vocab_set in vocab_sets):
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    set_id = str(uuid.uuid4())
    vocab_sets.append({
        'id': set_id,
        'name': 'Hauptstädte',
        'user_id': None,
        'is_shared': True,
        'created_at': now,
        'updated_at': now,
    })
    cards.extend({
        'id': str(uuid.uuid4()),
        'vocab_set_id': set_id,
        'front': item['front'],
        'back': item['back'],
        'level': 1,
        'next_review': now,
        'last_practice_wrong': False,
        'shuffle_order': None,
    } for item in HAUPTSTAEDTE_DATA)


def ensure_empty_target(target_engine) -> None:
    """Create the target schema and refuse to merge into populated tables."""
    db.metadata.create_all(target_engine)

    with target_engine.connect() as connection:
        counts = {
            table: connection.execute(text(f'SELECT count(*) FROM public.{table}')).scalar_one()
            for table in TABLES
        }

    populated = {table: count for table, count in counts.items() if count}
    if populated:
        details = ', '.join(f'{table}={count}' for table, count in populated.items())
        raise RuntimeError(f'Target database is not empty ({details}); migration stopped without overwriting data.')


def insert_target_data(target_engine, users, vocab_sets, cards) -> None:
    """Insert all rows atomically in foreign-key order."""
    with target_engine.begin() as connection:
        if users:
            connection.execute(insert(User.__table__), users)
        if vocab_sets:
            connection.execute(insert(VocabSet.__table__), vocab_sets)
        if cards:
            connection.execute(insert(Card.__table__), cards)


def verify_target(target_engine, expected_counts) -> None:
    """Verify row counts and foreign-key relationships after insertion."""
    with target_engine.connect() as connection:
        actual_counts = {
            table: connection.execute(text(f'SELECT count(*) FROM public.{table}')).scalar_one()
            for table in TABLES
        }
        orphaned_sets = connection.execute(text("""
            SELECT count(*)
            FROM public.vocab_sets AS vocab_set
            LEFT JOIN public.users AS app_user ON app_user.id = vocab_set.user_id
            WHERE vocab_set.user_id IS NOT NULL AND app_user.id IS NULL
        """)).scalar_one()
        orphaned_cards = connection.execute(text("""
            SELECT count(*)
            FROM public.cards AS card
            LEFT JOIN public.vocab_sets AS vocab_set ON vocab_set.id = card.vocab_set_id
            WHERE vocab_set.id IS NULL
        """)).scalar_one()

    if actual_counts != expected_counts:
        raise RuntimeError(f'Row-count verification failed: expected {expected_counts}, got {actual_counts}')
    if orphaned_sets or orphaned_cards:
        raise RuntimeError(
            f'Foreign-key verification failed: orphaned sets={orphaned_sets}, cards={orphaned_cards}'
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--target-url',
        help='Neon connection string. Omit it to enter the value without terminal echo.',
    )
    args = parser.parse_args()

    source_url = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if not source_url:
        raise RuntimeError(
            'SQLALCHEMY_DATABASE_URI is missing from .env or .env.local; '
            'the Supabase source is required.'
        )

    target_url = args.target_url or getpass.getpass('Neon database URL: ')
    if not target_url:
        raise RuntimeError('A Neon target URL is required.')
    if safe_endpoint(source_url) == safe_endpoint(target_url):
        raise RuntimeError('Source and target resolve to the same database.')

    print(f'Source: {safe_endpoint(source_url)}')
    print(f'Target: {safe_endpoint(target_url)}')

    source_engine = create_engine(source_url, poolclass=NullPool, pool_pre_ping=True)
    target_engine = create_engine(target_url, poolclass=NullPool, pool_pre_ping=True)

    try:
        users, vocab_sets, cards = fetch_source_data(source_engine)
        ensure_default_set(vocab_sets, cards)
        expected_counts = {
            'users': len(users),
            'vocab_sets': len(vocab_sets),
            'cards': len(cards),
        }
        print(f'Read source rows: {expected_counts}')

        ensure_empty_target(target_engine)
        insert_target_data(target_engine, users, vocab_sets, cards)
        verify_target(target_engine, expected_counts)
        print('Migration and integrity verification completed successfully.')
        return 0
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
