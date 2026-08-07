from pathlib import Path

path = Path('/app/main.py')
source = path.read_text(encoding='utf-8')

old = """   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   if not restorable:raise RuntimeError('This backup contains no restorable mount archives.')
   restore_step(f'Preflight started for {len(restorable)} mount(s).')
   prepared=[];rel=target.relative_to(BACKUP_ROOT)
"""

new = """   restorable=[m for m in manifest.get('mounts',[]) if m.get('archive')]
   if restorable:
    restore_step(f'Preflight started for {len(restorable)} mount(s).')
   else:
    restore_step('Backup contains no restorable mount archives; continuing with container configuration only.','warning')
   prepared=[];rel=target.relative_to(BACKUP_ROOT)
"""

old_message = """   message=f\"Restore completed: container '{c.name}' is available and {len(restored)} mount(s) were restored.\"
"""
new_message = """   if restored:
    message=f\"Restore completed: container '{c.name}' is available and {len(restored)} mount(s) were restored.\"
   elif created:
    message=f\"Restore completed: container '{c.name}' was recreated from its saved configuration. This backup contained no persistent mount archives.\"
   else:
    message=f\"Restore completed: container '{c.name}' already exists. This backup contained no persistent mount archives, so no data was changed.\"
"""

old_info = """ return {'path':rel_path,'original_name':name,'image':image,'can_recreate':bool(image and inspect_file.is_file()),'containers':existing,'mounts':manifest.get('mounts') or []}
"""
new_info = """ mounts=manifest.get('mounts') or []
 restorable_count=sum(1 for m in mounts if m.get('archive'))
 skipped_count=sum(1 for m in mounts if not m.get('archive'))
 return {'path':rel_path,'original_name':name,'image':image,'can_recreate':bool(image and inspect_file.is_file()),'containers':existing,'mounts':mounts,'restorable_count':restorable_count,'skipped_count':skipped_count,'config_only':restorable_count==0}
"""

for label, before, after in (
    ('restorable mount handling', old, new),
    ('restore completion message', old_message, new_message),
    ('restore info counts', old_info, new_info),
):
    if before not in source:
        raise SystemExit(f'ContBak 1.6.1 patch: {label} pattern not found; refusing unsafe patch.')
    source = source.replace(before, after, 1)

path.write_text(source, encoding='utf-8')
