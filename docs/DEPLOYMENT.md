# Verve Deployment Guide

This is the canonical reference for production configuration, hosting, schema changes, and one-time data migrations. Local setup and tests are documented in [DEVELOPMENT.md](DEVELOPMENT.md).

## Production Configuration

Configure these values as protected environment variables in the hosting platform:

- `FLASK_CONFIG=production`
- `SECRET_KEY`: a long, unique random value
- `SQLALCHEMY_DATABASE_URI`: the pooled Neon connection string with `sslmode=require`
- `NEON_AUTH_BASE_URL`: managed Auth URL for the same Neon database branch

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

The command reads `.env` and `.env.local`, applies all committed SQL migrations in `migrations/`, and verifies every expected constraint and index. To avoid storing a direct URL, omit `SQLALCHEMY_DATABASE_URI` and enter the URL at the hidden prompt. An explicit direct URL can also be supplied temporarily:

```bash
python scripts/apply_neon_schema.py --database-url "postgresql://..."
```

Treat shell history as sensitive when passing credentials as arguments; the hidden prompt is preferred.

## Neon Auth

Enable managed Better Auth for the database branch. Add the app's exact HTTPS origin under trusted domains. For production Google sign-in, configure your own Google OAuth client in Neon and add `{NEON_AUTH_BASE_URL}/callback/google` to its authorized redirect URIs in Google Cloud. Shared Google credentials are intended for development.

The browser uses the official Neon SDK through `/auth/neon`; Flask forwards only managed Auth cookies and an explicit list of authentication endpoints. State-changing requests require Verve CSRF tokens. Protected requests validate the managed session upstream, so revoked sessions stop authorizing access. Cookies are HTTP-only, host-only, and Secure in production.

Apply `migrations/002_neon_auth.sql` before deploying this revision. It adds `users.neon_auth_id` and its unique index without replacing existing Verve IDs or learning data. `scripts/apply_neon_schema.py` applies both committed migrations.

Existing Google accounts link on their first Neon sign-in through the original Google subject ID. Existing local accounts need to register the same email with Neon and verify the emailed code; their original application ID and learning data are then linked. Existing password hashes and browser sessions do not authenticate against Neon. Legacy credential columns remain migration data until all existing users are linked; do not delete them as part of the initial cutover.

Password recovery and email verification are handled by Neon. Verification and password reset use emailed codes, which work with Neon's shared email provider. Configure custom SMTP in Neon for production email branding and delivery. Profile email is read-only because it belongs to the managed identity. Account deletion removes the linked Neon identity and Verve learning data in one PostgreSQL transaction. Neon provider accounts and sessions cascade from that identity. The database role must have DELETE access to `neon_auth."user"`; the application never accepts an identity ID from the deletion request.

After deploying and verifying sign-in, sign-out, session restoration, email verification, account ownership, and learning data, remove the old `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` deployment variables. Google credentials are now maintained in Neon.

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
5. Verify local login, Google login, set creation, import, review, and account deletion.
6. Inspect deployment logs without copying personal data or credentials into issues.
