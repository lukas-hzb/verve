# Contributing to Verve

Bug reports and focused feature proposals are welcome. Because Verve is proprietary source-available software, code contributions require prior written authorization from the maintainer before creating a public fork or submitting a pull request.

## Documentation and Commands

Keep `README.md` focused on using Verve. Local setup, testing, troubleshooting, and repository commands belong in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Hosting, production configuration, schema, and data-migration commands belong in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

When adding a contributor or maintainer workflow, extend the most relevant guide and link to it instead of duplicating command sequences in the README or this file. Credentials, private service endpoints, and personal operational notes must remain outside the repository.

## Report a Bug

Use the repository's [bug report form](https://github.com/lukas-hzb/verve/issues/new?template=bug_report.yml) and include:

- The affected deployment or commit
- Browser, operating system, and device type
- The sign-in method involved, when relevant
- Reproduction steps, expected behavior, and actual behavior
- Relevant logs with credentials and personal information removed

Security vulnerabilities must follow [SECURITY.md](SECURITY.md) and must not be disclosed in a public issue.

## Propose a Feature

Use the [feature request form](https://github.com/lukas-hzb/verve/issues/new?template=feature_request.yml) to describe the user problem, expected workflow, and alternatives considered. Keep proposals focused on vocabulary learning and Verve's spaced-repetition workflow.

## Submit an Authorized Change

1. Obtain written authorization from the maintainer for the proposed contribution and public fork.
2. Create a focused branch from the latest `main`.
3. Follow [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup and tests.
4. Add or update tests for behavioral changes.
5. Use English Conventional Commits, for example `fix: preserve practice progress after reload`.
6. Open a pull request using the repository template.

Do not commit generated files, logs, credentials, database exports, OAuth secrets, deployment metadata, or user data.

## Contribution Terms

By submitting a contribution, you agree to section 5 of [LICENSE](LICENSE), including its contributor grant and representations. Third-party material must be clearly identified and compatible with Verve's distribution model.
