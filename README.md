# DockBack v2

Neu:
- mehrere Container per Checkbox auswählen
- einzelner Container separat sichern
- pro Container einzelne Named Volumes oder Bind-Mounts auswählen
- selektiver Restore einzelner gesicherter Mounts
- tägliche Zeitpläne pro Container

Installation:
1. `.env.example` nach `.env` kopieren und Kennwort ändern.
2. `docker compose up -d --build`
3. WebUI: `http://NAS-IP:8787`

Hinweis: Zeitpläne sichern derzeit immer alle Mounts des jeweiligen Containers.


## Wichtig: Host-Pfad für Hilfscontainer
`BACKUP_ROOT=/backups` ist der Pfad innerhalb von DockBack. Temporäre Hilfscontainer werden jedoch vom Docker-Daemon gestartet und benötigen den realen Pfad auf dem Synology-Host:

```dotenv
BACKUP_ROOT=/backups
BACKUP_HOST_PATH=/volume1/docker/dockback/backups
```

Ohne `BACKUP_HOST_PATH` würde Docker versuchen, den Host-Pfad `/backups` einzubinden und mit `Bind mount failed: '/backups' does not exist` abbrechen.

## Version 2.2
- Backup-Liste durchsucht den kompletten Backup-Pfad rekursiv.
- Vorhandene Archive ohne `manifest.json` werden als `incomplete` angezeigt.
- Das Manifest wird künftig vor dem Kopieren angelegt und nach Erfolg auf `complete` gesetzt.
