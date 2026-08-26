# Verve Deployment Guide

This is the canonical reference for production configuration, hosting, schema changes, and one-time data migrations. Local setup and tests are documented in [DEVELOPMENT.md](DEVELOPMENT.md).

## Production Configuration

Configure these values as protected environment variables in the hosting platform:

- `FLASK_CONFIG=production`
- `SECRET_KEY`: a long, unique random value
- `SQLALCHEMY_DATABASE_URI`: the pooled Neon connection string with `sslmode=require`
- Optional `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: enable Google OpenID Connect

Never commit production credentials, exported databases, Vercel project metadata, or OAuth secrets.

## Vercel

The production entry point is `wsgi.py`. Vercel detects the Flask application without a repository-specific `vercel.json`; a connected GitHub project can deploy updates from the configured production branch.

Vercel's filesystem is read-only during requests. Verve therefore uses stream logging and skips schema creation and seed work during Vercel cold starts. Apply schema changes before deploying application code that depends on them.

## Neon Postgres

Use the pooled Neon endpoint for application and serverless traffic. Use the direct endpoint for schema changes and one-time migrations. The provided schema utility converts a configured `-pooler` host to its direct counterpart before applying SQL.

After creating or importing the database, apply the idempotent constraints and indexes:

```bash
python scripts/apply_neon_schema.py
```

The command reads `.env` and `.env.local`, applies `migrations/001_neon_hardening.sql`, and verifies every expected constraint and index. To avoid storing a direct URL, omit `SQLALCHEMY_DATABASE_URI` and enter the URL at the hidden prompt. An explicit direct URL can also be supplied temporarily:

```bash
python scripts/apply_neon_schema.py --database-url "postgresql://..."
```

Treat shell history as sensitive when passing credentials as arguments; the hidden prompt is preferred.

## Migrate an Existing Supabase Database

The migration copies users, password hashes, Google identity links, vocabulary sets, and cards, then verifies row counts and foreign-key integrity. It refuses to merge into populated target tables.

1. Back up the source database.
2. Put the direct Supabase source URL in `SQLALCHEMY_DATABASE_URI` inside `.env.local`.
3. Run the migration and enter the direct Neon target URL at the hidden prompt.

```bash
python scripts/migrate_to_neon.py
```

4. Replace `SQLALCHEMY_DATABASE_URI` locally and in the deployment with the pooled Neon URL.
5. Run `python scripts/apply_neon_schema.py` against Neon.
6. Remove all Supabase credentials after the migration has been verified.

Do not migrate against a production target without a current backup and a rollback plan.

## Alternative WSGI Deployments

`Procfile` starts Gunicorn with a 120-second timeout:

```text
web: gunicorn --timeout 120 wsgi:app
```

Container platforms can build the included `Dockerfile`, which exposes port `8000` and starts the same WSGI application. The hosting platform must provide the production environment variables and a reachable Postgres database.

## Deployment Checklist

1. Run `python -m unittest discover -s tests`.
2. Apply required schema changes using the direct Neon endpoint.
3. Confirm production secrets and the pooled application URL.
4. Deploy the new application revision.
5. Verify local login, optional Google login, set creation, import, review, and account deletion.
6. Inspect deployment logs without copying personal data or credentials into issues.
