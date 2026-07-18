# Security Policy

## Reporting a vulnerability

Do not publish exploitable security details in a public issue. Open a private security advisory in the GitHub repository.

## Docker socket warning

ContBak requires access to `/var/run/docker.sock`. Any application with this access effectively has administrative control over the Docker host. Do not expose ContBak directly to the public Internet. Use a trusted LAN, VPN, firewall, or an authenticated reverse proxy.

Use a unique, long `CONTBAK_PASSWORD`. Keep the configuration and backup directories accessible only to administrators.
