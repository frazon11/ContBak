# ContBak 1.4.0

This release adds portable backup transfer between ContBak installations.

## Added
- Single-backup download
- Multi-backup export
- WebUI upload/import
- `.contbak` archive format
- SHA256 integrity verification
- Duplicate handling: rename, skip, replace
- Backup size display

The `.contbak` format is a gzip-compressed tar archive containing one or more complete backup sets and an `export-manifest.json` file with per-file checksums.
