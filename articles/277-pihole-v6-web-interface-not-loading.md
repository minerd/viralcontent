---
title: "Pi-hole v6 Web Interface Not Loading? lighttpd Is Still Holding Port 80"
slug: pihole-v6-web-interface-not-loading
meta_description: "DNS works but the v6 admin page won't load after upgrading from v5. The built-in web server, the lighttpd port conflict, IPv6 port entries and the 8080 fallback."
updated: October 2026
cluster: round 12 (tech) — Pi-hole Discourse threads only
competition: LOW
---

# Pi-hole v6 Web Interface Not Loading? lighttpd Is Still Holding Port 80

The signature of this problem: **DNS resolution keeps working perfectly** and only the admin page is gone. That tells you `pihole-FTL` is running and the web side is what's broken.

## What changed in v6

Pi-hole v6 serves its own web interface from **`pihole-FTL`** with an embedded web server and Lua pages. It no longer uses **lighttpd**. After an upgrade from v5:

- The old **lighttpd is often still installed and running**, holding port 80
- `pihole-FTL` can't bind port 80, so the interface doesn't come up where you expect it
- v6 falls back to **8080** (and 8443 for HTTPS) when 80/443 are taken

**First thing to try: `http://pi.hole:8080/admin` or `http://<ip>:8080/admin`.** If that loads, you've found it, and the rest is cleanup.

## Fix the port conflict

```bash
sudo ss -lntp | grep -E ':(80|443|8080) '
systemctl status lighttpd
```

If lighttpd is there:

```bash
sudo systemctl disable --now lighttpd
# optional, once you're sure nothing else used it:
sudo apt purge lighttpd
```

Then set Pi-hole's ports back to 80/443 in **`/etc/pihole/pihole.toml`**:

```toml
[webserver]
port = "80,[::]:80,443s,[::]:443s"
```

and restart:

```bash
sudo systemctl restart pihole-FTL
```

If you intentionally run **Apache/nginx** on that host, leave them on 80 and keep Pi-hole on 8080 — or reverse-proxy Pi-hole's port. Don't fight over 80.

## The IPv6 entry that breaks startup

Reported fix: **removing the IPv6 entries from the port list** in `pihole.toml` gets the web server loading on hosts where IPv6 isn't properly configured.

```toml
port = "80,443s"
```

Check the FTL log for a bind failure before and after:

```bash
sudo tail -50 /var/log/pihole/FTL.log
```

A failed bind on `[::]:80` stops the whole listener on some setups — exactly the "DNS fine, web dead" pattern.

## Other causes worth knowing

- **Corrupted web UI files** after a partial upgrade. `pihole -r` (repair) reinstalls components; a broken git checkout of the admin interface has needed `git-repair` in some reports
- **A reverse proxy** in front still pointing at the lighttpd-era path/port
- **`/admin` vs `/`** — v6 serves the admin UI at `/admin`; a bookmark to an old URL can 404
- **Docker**: the container's port mappings must match the ports in `pihole.toml`. Changing one without the other is a very common self-inflicted version of this
- **Firewall** rules written for 80 while FTL listens on 8080

## Order of operations

1. Try **:8080/admin**
2. `ss -lntp` — what owns 80?
3. Disable **lighttpd**
4. Set ports in **`pihole.toml`**, restart `pihole-FTL`
5. Read **FTL.log** for bind errors; drop IPv6 entries if needed
6. `pihole -r` only if files look damaged

## Prevention

1. Before upgrading v5 → v6, note whether you run **another web server** on that host
2. **Back up** `/etc/pihole/` (and `pihole.toml` afterwards) — it's your whole configuration
3. **Pin container tags**; don't let a major version land unattended on your DNS
4. Keep a **second resolver** configured so a broken Pi-hole isn't a household outage
5. Remember that **DNS working** is a strong clue the problem is only the web layer

## FAQ

**Why is my admin page on 8080 now?**
Because 80 was taken (usually by lighttpd), so FTL fell back.

**Do I still need lighttpd?**
No. v6 has its own web server. Disable it.

**Can I run Pi-hole's UI behind nginx?**
Yes — point the proxy at FTL's port and keep Pi-hole off 80.

**DNS stopped too. Is this the same problem?**
No. That's a different failure — check `pihole-FTL` itself and port 53.
