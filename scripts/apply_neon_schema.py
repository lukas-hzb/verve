#!/usr/bin/env python3
"""Apply Verve's idempotent Neon schema-hardening migration."""

import argparse
import getpass
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = PROJECT_ROOT / 'migrations' / '001_neon_hardening.sql'


def direct_database_url(database_url: str) -> str:
    """Convert a Neon pooled URL to its direct migration endpoint."""
    url = make_url(database_url)
    if url.host and '-pooler.' in url.host:
        url = url.set(host=url.host.replace('-pooler.', '.'))
    return url.render_as_string(hide_password=False)


def safe_endpoint(database_url: str) -> str:
    url = make_url(database_url)
    return f'{url.host}/{url.database}'


def main() -> int:
    load_dotenv(PROJECT_ROOT / '.env')
    load_dotenv(PROJECT_ROOT / '.env.local', override=True)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--database-url',
        help='Direct Neon URL. Omit to use SQLALCHEMY_DATABASE_URI or a hidden prompt.',
    )
    args = parser.parse_args()

    configured_url = args.database_url or os.environ.get('SQLALCHEMY_DATABASE_URI')
    if not configured_url:
        configured_url = getpass.getpass('Neon database URL: ')
    if not configured_url:
        raise RuntimeError('A Neon database URL is required.')

    database_url = direct_database_url(configured_url)
    migration_sql = MIGRATION_FILE.read_text(encoding='utf-8')
    engine = create_engine(database_url, poolclass=NullPool, pool_pre_ping=True)

    print(f'Applying schema hardening to {safe_endpoint(database_url)}')
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(migration_sql)

        with engine.connect() as connection:
            constraints = connection.execute(text("""
                select count(*)
                from pg_constraint
                where conname in (
                    'uq_vocab_sets_user_name',
                    'ck_vocab_sets_owner_or_shared',
                    'ck_cards_level_positive'
                )
            """)).scalar_one()
            indexes = connection.execute(text("""
                select count(*)
                from pg_indexes
                where schemaname = 'public'
                  and indexname in (
                    'uq_users_username_lower',
                    'uq_users_email_lower',
                    'ix_vocab_sets_user_id',
                    'ix_cards_set_due',
                    'ix_cards_set_shuffle'
                  )
            """)).scalar_one()

        if constraints != 3 or indexes != 5:
            raise RuntimeError(
                f'Schema verification failed: constraints={constraints}/3, indexes={indexes}/5'
            )
        print('Schema hardening completed and verified.')
        return 0
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
