---
title: "Homepage Widgets Showing \"API Error\""
slug: homepage-widget-api-error
meta_description: "Service widgets show API Error, HTTP 500 or errno -3001. The URL rules, the Docker network problem and the token formats that catch people."
updated: October 2026
cluster: round 14 (tech) — gethomepage/homepage GitHub discussions
competition: LOW
---

# Homepage Widgets Showing "API Error"

"API Error" is Homepage telling you the request to that service failed. The useful detail is in the container log, not the tile:

```bash
docker logs homepage --tail 100 | grep -iE 'error|widget'
```

Common codes and what they mean:

| In the log | Cause |
|---|---|
| `EHOSTUNREACH` / `ECONNREFUSED` | Homepage can't reach the host — section 1 |
| `errno -3001` (`EAI_AGAIN`) | DNS failure inside the container |
| `HTTP 401` / `403` | Credentials or token — section 3 |
| `HTTP 500` | The service errored; check *its* log |
| `Unexpected token < in JSON` | You got HTML — wrong URL or a login page |

## 1. Reachability from inside the container

This is the biggest cause, and the test is one command:

```bash
docker exec homepage wget -qO- --timeout=5 http://192.168.1.10:8096/System/Info/Public | head -c 200
```

Rules that follow from it:

- **`localhost` in a widget URL means the Homepage container.** Never the host, never another container.
- **A container name only resolves if both containers share a user-defined Docker network.** Default bridge does not provide name resolution.
- **A host-gateway address is needed** to reach services on the host:

```yaml
services:
  homepage:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

then use `http://host.docker.internal:8096`.

The pragmatic default: use the host's **LAN IP** in every widget URL. It works from everywhere, survives network changes, and removes an entire class of problems.

## 2. URL format

```yaml
# services.yaml
- Media:
    - Jellyfin:
        icon: jellyfin.png
        href: https://jellyfin.example.com
        widget:
          type: jellyfin
          url: http://192.168.1.10:8096
          key: your-api-key
```

- **No trailing slash on `url`.** Each widget appends its own path; a trailing slash produces a double slash and a 404 on some services.
- **No API path in `url`.** `http://host:8096`, not `http://host:8096/api`. The widget knows its own endpoints.
- **`url` is what Homepage calls; `href` is what your browser opens.** They are often different (internal IP vs. external hostname) and that's correct.
- **Scheme must match.** An HTTPS service with `http://` gives a connection reset.

## 3. Credentials per service

The formats that cause most 401s:

**Proxmox** — the username must include the realm and the token id:

```yaml
        widget:
          type: proxmox
          url: https://192.168.1.5:8006
          username: homepage@pve!homepage
          password: 01234567-89ab-cdef-0123-456789abcdef
```

`user@realm!tokenid` as the username, the token's **secret** as the password. Nothing else works, and a plain username/password is not supported for the widget.

**Pi-hole v6** — the v6 API replaced the old token with password-based session auth. A v5 `key` against a v6 instance fails. Use the `key` field with your admin password on v6, and check that the widget `type` matches your major version.

**Self-signed certificates** — Homepage validates TLS. For an internal service with a self-signed cert:

```yaml
        widget:
          type: proxmox
          url: https://192.168.1.5:8006
          ...
```
and set, on the container:

```yaml
    environment:
      - NODE_TLS_REJECT_UNAUTHORIZED=0
```

That disables verification globally for Homepage — acceptable on a LAN-only dashboard, not something to do lightly.

## 4. Version mismatches

A widget for a service version Homepage doesn't support yet (or a widget `type` that doesn't exist) gives an API error with nothing useful. Two checks:

- Is the widget `type` spelled exactly as the docs list it? An unknown type isn't flagged as a config error.
- Is your Homepage image recent? Widgets for new service versions arrive in Homepage releases:

```yaml
    image: ghcr.io/gethomepage/homepage:latest
```

PBS, Pi-hole v6 and several *arr majors have each needed a Homepage update.

## 5. Errors that resolve on their own

Some widgets show API Error for the first few seconds after a restart, while the service is still starting. If it clears within a minute, there is nothing to fix — order your containers with `depends_on` if it bothers you.

## What not to do

- **Don't put `localhost` in widget URLs.** It is the most common mistake by a wide margin.
- **Don't disable TLS verification to fix a wrong URL.** Confirm reachability first.
- **Don't give Homepage an admin API key** where a read-only one exists. The dashboard only reads.
- **Don't edit config while the container has it cached.** Homepage reloads config automatically, but a syntax error in `services.yaml` makes the whole file fail silently — check the log after every edit.

## Prevention

| Habit | Why |
|---|---|
| LAN IPs in every `url`, hostnames in `href` | Removes DNS and network-scope problems |
| One read-only token per service, documented | Least privilege and easy rotation |
| Watch the log after each config edit | YAML errors are not surfaced in the UI |
| Keep the image current | Widgets track upstream API changes |

## FAQ

**Can I hide the error and keep the tile?**
Yes — remove the `widget:` block and keep the link.

**Do widgets poll constantly?**
Each has its own interval. Many widgets against a weak host add up; trim what you don't read.

**Docker widget shows nothing.**
That needs the socket or a socket-proxy configured in `docker.yaml`, which is separate from service widgets.

**Can I use environment variables for keys?**
Yes — `{{HOMEPAGE_VAR_JELLYFIN_KEY}}` with the variable set on the container keeps secrets out of the YAML.
