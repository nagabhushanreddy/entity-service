# Configuration Directory

This directory contains JSON configuration files. At startup, the service prefers the shared configuration from `utils-service` and falls back to these local files only if the shared config isn't available.

## Files
- app.json: API and service metadata (includes `version` used in API prefix).
- database.json: Database connection settings.
- paths.json: Directories that should exist; created automatically on startup.
- logging.json: Logging destinations and dictConfig for console/file handlers.

## Notes
- Preference: load config via `utils.config` (env-first placeholder resolution). If unavailable, local `config/*.json` files are merged and used.
- Paths under `paths.*` are created automatically; default includes `logs/` and `data/`.
- Logging defaults to stdout plus a rotating file at `logs/entity-service.log`; errors also go to `logs/entity-service.error.log`.
- Database defaults to SQLite (`sqlite+aiosqlite:///./entity.db`). Override via environment variable `DATABASE_URL` if desired and update `database.json` accordingly.
