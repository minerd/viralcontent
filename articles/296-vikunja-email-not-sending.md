---
title: "Vikunja Not Sending Email? The Settings That Actually Work"
slug: vikunja-email-not-sending
meta_description: "Test mail works but reminders don't, or nothing sends at all. FORCESSL versus port 587, auth types, the empty mail log and reminder-specific behaviour."
updated: October 2026
cluster: round 12 (tech) — Vikunja community forum and GitHub issues
competition: LOW
---

# Vikunja Not Sending Email? The Settings That Actually Work

Two separate failures, and telling them apart saves an hour:

- **Nothing sends, mail log empty** → the mailer isn't configured/enabled
- **`testmail` works but reminders don't arrive** → delivery works; the notification path is the problem

## 1. Get a working SMTP configuration

The combination reported as working for Gmail is the useful starting point: **port 587, `FORCESSL: 0`, auth type `plain`**.

```yaml
environment:
  VIKUNJA_MAILER_ENABLED: 1
  VIKUNJA_MAILER_HOST: smtp.gmail.com
  VIKUNJA_MAILER_PORT: 587
  VIKUNJA_MAILER_AUTHTYPE: plain
  VIKUNJA_MAILER_USERNAME: you@example.com
  VIKUNJA_MAILER_PASSWORD: app-password-not-your-password
  VIKUNJA_MAILER_FROMEMAIL: you@example.com
  VIKUNJA_MAILER_FORCESSL: 0
```

Key points:
- **`FORCESSL: 0` with port 587** (STARTTLS). `FORCESSL: 1` is for implicit TLS on **465**. Mixing them gives EOF and connection errors — the most common misconfiguration
- **`VIKUNJA_MAILER_ENABLED: 1`** — the setting people forget entirely, which produces the empty mail log
- Gmail and Microsoft 365 need an **app password**, not your account password
- `AUTHTYPE`: try `plain`, then `login`, then `cram-md5`. Office 365 rejecting with *"Command not implemented"* usually means the wrong auth type

Then test:
```bash
docker exec vikunja /app/vikunja/vikunja testmail
```

## 2. Test mail works, reminders don't

This is the documented, confusing case. The log may even say the **mailer is disabled for reminder-specific functions** while `testmail` succeeds.

Check, in order:

- **`VIKUNJA_SERVICE_ENABLEEMAILREMINDERS`** (and the user's own notification preferences) — reminders are a separate switch from the mailer
- The user's **email address is confirmed** in their profile; unverified addresses don't receive notifications
- The user's **notification settings** (per-user, in the UI) allow email for that event type
- The task actually has a **reminder set**, with a time in the future, and in the timezone you think — `VIKUNJA_SERVICE_TIMEZONE` matters here
- The **cron/scheduler** inside Vikunja is running; reminders are dispatched by a periodic job, so a container that restarts constantly never gets there

## 3. Container and network causes

- Outbound **587/465 blocked** by the host, the ISP, or a cloud provider (many block 25 and some block 587 by default)
- From inside the container:
  ```bash
  docker exec -it vikunja sh -c "nc -vz smtp.gmail.com 587"
  ```
- Missing **`ca-certificates`** in a minimal image → TLS handshake failures that look like auth errors
- Wrong container **timezone** → reminders fire at the wrong hour and look like they never fired

## 4. Read the log properly

```bash
docker compose logs -f vikunja | grep -i -e mail -e smtp -e reminder
```

- **Empty mail log** → the mailer isn't enabled. Section 1
- **EOF / connection reset** → port and TLS mismatch. Section 1
- **535/534 auth errors** → credentials or app password
- **"mailer is disabled"** → the reminder-specific switch. Section 2
- Nothing at the time a reminder should fire → scheduler or timezone

## Prevention

1. Keep a **working config snippet** in your notes — this is a settings problem, and the settings are not obvious
2. Use a **dedicated SMTP account** or a transactional provider (fewer surprises than Gmail)
3. Set **`VIKUNJA_SERVICE_TIMEZONE`** explicitly
4. After upgrades, run **`testmail`** once as a smoke test
5. Confirm **users' email addresses** are verified, or notifications silently go nowhere

## FAQ

**Which port and SSL setting should I use?**
587 with `FORCESSL: 0` (STARTTLS), or 465 with `FORCESSL: 1`. Not mixed.

**Why does testmail work but reminders don't?**
They're separate paths: the reminder scheduler, per-user notification settings, verified addresses and timezone all have to line up.

**Do I need an app password?**
For Gmail and Microsoft accounts, yes.

**The mail log is empty.**
The mailer isn't enabled at all — set `VIKUNJA_MAILER_ENABLED: 1`.
