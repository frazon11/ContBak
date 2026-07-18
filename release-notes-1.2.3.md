# ContBak 1.2.3

This release fixes backups of monitoring containers such as Netdata. Host pseudo filesystems (`/proc`, `/sys`, `/dev`) and Docker sockets are skipped because they are runtime interfaces, not persistent application data. A failed individual mount is recorded and no longer turns the whole request into an HTTP 500 response.
