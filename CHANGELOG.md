# Changelog

## 1.0.2 - 2026-07-17

### Fixed
- Helper-container host bind now uses `CONTBAK_BACKUP_PATH`.
- Target-container restart is guaranteed after backup attempts.
- Docker exceptions no longer cause an unhandled HTTP 500.
- Recursive backup discovery includes legacy archives.
- GitHub Actions always provides a build tag and only pushes release tags.
