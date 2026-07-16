# Security

ContBak requires access to `/var/run/docker.sock`. This grants extensive control over the Docker host.

- Do not expose ContBak directly to the public internet.
- Use a strong password, VPN or authenticated reverse proxy.
- Keep the image and helper image updated.
- Report vulnerabilities privately to the repository owner before public disclosure.
