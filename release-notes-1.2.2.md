# ContBak 1.2.2

## Fixed

- Directory bind mounts are archived as before.
- Regular file bind mounts are now backed up and restored correctly.
- Special mounts such as `/var/run/docker.sock` are skipped instead of being passed to `tar -C`.
- Prevents `tar: can't change directory to '/source': Not a directory`.
