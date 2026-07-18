# ContBak 1.3.0

## User-interface improvements

- Backup requests now start as background jobs and return immediately.
- The clicked button changes instantly to `Backup startet …` and is disabled while running.
- Each container card displays live progress, the current step and a small live log.
- Toast notifications report start, success and failure.
- The page refreshes automatically after a successful backup.

## Compatibility

The synchronous `/backup/{container_id}` endpoint remains available as a fallback. The backup engine and the mount exclusions introduced in 1.2.3 remain unchanged.
