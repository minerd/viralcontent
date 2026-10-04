---
title: "Healthchecks: Pings Not Being Received by a Self-Hosted Instance"
slug: healthchecks-ping-not-received
meta_description: "curl works and your runner doesn't, or pings vanish. Slug collisions returning 409, the rate limit, timeouts and the SITE_ROOT setting."
updated: October 2026
cluster: round 14 (tech) — healthchecks GitHub discussions and docs
competition: LOW
---

# Healthchecks: Pings Not Being Received by a Self-Hosted Instance

Establish first whether the ping reaches the server at all:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://hc.example.com/ping/YOUR-UUID
```

| Response | Meaning |
|---|---|
| 200 | Received and recorded |
| 404 | Wrong UUID, or the check was deleted |
| 409 | **Slug collision** — section 2 |
| 429 | Rate limited — section 3 |
| 000 / timeout | Network, TLS, or the server is down |

## 1. curl works, your tool doesn't

The most instructive reported case: `runitor` failed to ping while `curl` to the same URL succeeded — and the fix was **raising the client timeout from 5 to 6 seconds.**

That generalises. Tools that ping with a short, hard timeout fail against a self-hosted instance that is slightly slower than the hosted service (TLS handshake, a cold database connection, a reverse proxy warming up). Check your tool's timeout:

```bash
runitor -api-url https://hc.example.com/ping/ -api-timeout 10s -uuid YOUR-UUID -- /path/to/job
```

For cron-based pings, give curl explicit, generous timeouts and retries:

```bash
curl -fsS -m 15 --retry 5 --retry-delay 2 --retry-connrefused \
  https://hc.example.com/ping/YOUR-UUID
```

`-m 15` is the whole-operation timeout; `--retry-connrefused` covers a restarting server. Without retries, a single blip marks your job as late.

## 2. 409 Conflict: slug collisions

A documented behaviour that surprises people using the slug-based ping URLs:

> **Slugs are not guaranteed unique.** If you ping using a non-unique slug, Healthchecks returns **409 Conflict** and ignores the request.

```
https://hc.example.com/ping/PROJECT-PING-KEY/my-backup
```

Two checks in the same project both named "my-backup" (or named such that they generate the same slug) make that URL ambiguous, and every ping is dropped with a 409. Nothing appears in the UI, which is why it reads as "pings not received".

Fix: rename one check so the slugs differ, or switch that job to the UUID-based URL, which is unambiguous by construction. For automation, UUID URLs are the safer default.

## 3. 429: the rate limit

> **More than 5 pings per minute** to the same check may be rate limited and not recorded.

So a job in a tight loop, a test script hammering the endpoint, or a misconfigured systemd timer firing every ten seconds will silently lose pings. If you need high-frequency monitoring, that's not what a cron monitor is for — use a metrics system and alert on absence.

## 4. Server-side configuration

```yaml
services:
  healthchecks:
    image: healthchecks/healthchecks:latest
    environment:
      SITE_ROOT: https://hc.example.com
      SITE_NAME: Healthchecks
      ALLOWED_HOSTS: hc.example.com
      DB: postgres
      DB_HOST: db
      DB_NAME: healthchecks
      DB_USER: healthchecks
      DB_PASSWORD: secret
      SECRET_KEY: a-long-random-string
      DEFAULT_FROM_EMAIL: hc@example.com
      EMAIL_HOST: smtp.example.com
      EMAIL_PORT: "587"
      EMAIL_USE_TLS: "True"
    volumes:
      - ./data:/data
```

Things that break pings specifically:

- **`ALLOWED_HOSTS`** not including the hostname you ping. Django returns 400 for a disallowed Host header, and your cron job's `curl -fsS` prints nothing useful.
- **`SITE_ROOT`** wrong, which affects the URLs shown in the UI (and therefore the ones you copy) rather than reception.
- **The `sendalerts` / `sendreports` management commands not running.** In the Docker image these are handled; in a manual install they're separate processes. Without them, pings are recorded and **no alerts ever fire** — which people report as "pings not received" because nothing happens.

```bash
docker exec healthchecks ./manage.py sendalerts --help
```

## 5. Behind a reverse proxy

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

- **`Host` must be forwarded** or `ALLOWED_HOSTS` rejects it.
- **Forward-auth in front of `/ping/` breaks everything.** Your cron jobs can't authenticate. The ping URL's UUID *is* the credential; exempt `/ping/` from any auth layer.
- **Rate limiting at the proxy** can be stricter than Healthchecks' own.

## 6. Pings recorded, status still "down"

- **The period and grace** are wrong for the job. A nightly backup needs a 1-day period with a grace long enough to cover the run.
- **Start/success signalling.** If you use `/start` and the job never pings success, the check goes down even though it started. Use the `--retry`-wrapped pair:

```bash
curl -fsS -m 10 --retry 3 https://hc.example.com/ping/UUID/start
/path/to/backup.sh && curl -fsS -m 10 --retry 3 https://hc.example.com/ping/UUID \
  || curl -fsS -m 10 --retry 3 https://hc.example.com/ping/UUID/fail
```

## What not to do

- **Don't put auth in front of `/ping/`.** Nothing can satisfy it.
- **Don't use slug URLs for automation** unless you've guaranteed uniqueness.
- **Don't ping more than a few times a minute.** You'll be rate limited.
- **Don't run a manual install without `sendalerts`.** You get a dashboard and no alerts.

## Prevention

| Habit | Why |
|---|---|
| UUID ping URLs in automation | Immune to slug collisions |
| `curl -fsS -m 15 --retry 5` as the standard invocation | Survives blips without false alarms |
| `/ping/` exempted from auth, documented | The one path that must stay open |
| Verify an alert fires after setup | Pings without alerts is the silent failure |

## FAQ

**Can I ping by email instead?**
Yes — each check has an email address; sending to it counts as a ping. Useful for appliances that can only email.

**Does it support HEAD or POST?**
Both; POST lets you attach a log body, which is visible in the check's event list.

**How long is ping history kept?**
Configurable, and the database grows with it. Prune on a schedule for busy instances.

**Alerts work, then stop.**
Check the notification channel (SMTP credentials expiring is common) and that `sendalerts` is still running.
