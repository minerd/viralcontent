---
title: "Uptime Kuma Not Sending Notifications? Check the Monitor's Own Tick Box"
slug: uptime-kuma-notifications-not-working
meta_description: "A notification that tests fine but never fires is usually not attached to the monitor. Plus SMTP traps, missing 'up' notifications and resend-interval behaviour."
updated: October 2026
cluster: round 12 (tech) — Uptime Kuma GitHub issues
competition: LOW
---

# Uptime Kuma Not Sending Notifications? Check the Monitor's Own Tick Box

The order here matters, because the first item accounts for most reports and takes ten seconds.

## 1. The notification isn't attached to the monitor

A notification configured in **Settings → Notifications** does nothing on its own. It has to be **ticked on each monitor**.

- Edit the monitor → **Notifications** section → tick the one you want → **Save**
- Notifications created with **"Default enabled"** apply only to monitors created *afterwards*; existing monitors keep whatever they had
- Check a monitor you know is failing, not a healthy one

If the **Test** button delivers and real events don't, this is almost certainly why.

## 2. Test works, real alerts don't — the other causes

- **Resend interval**: with it set, Kuma repeats a notification every N checks. Set to 0 it notifies once per state change. If you expected repeats and got one, that's this setting
- **Retries**: a monitor with `Retries: 3` goes to *Pending* first and only notifies when it finally flips to Down. If your check fails intermittently and recovers inside the retry window, no notification is correct behaviour
- **Upside-down mode** or a changed accepted status code — the monitor isn't failing in the way you think
- Monitor **paused** (greyed out) after an import or an edit

## 3. You get Down but never Up

A reported pattern worth knowing: some monitors deliver down notifications but not recovery ones.

- Check the notification is attached (same tick box) — some people have two notification entries and only one is ticked
- Look at the monitor's events list: did Kuma actually record an **Up** event, or is it still flapping in Pending?
- For email, check the **up** message isn't being filed as spam while the down one isn't — different subject lines score differently

## 4. SMTP email specifically

Email is the most failure-prone channel:

- **Port and encryption** must match the provider: 587 with STARTTLS, or 465 with implicit TLS. Mismatching these gives timeouts
- **From address** must be one the server will accept — many providers reject a From that isn't the authenticated mailbox, and the message is accepted then dropped silently
- Gmail/Microsoft need an **app password**, not your account password
- A **test that reports success but never arrives** means the SMTP handshake worked and the message was dropped downstream: check the provider's sent/rejected logs, SPF/DKIM, and the spam folder
- From a container, confirm outbound 587/465 isn't blocked by the host or your ISP

## 5. Push services (ntfy, Gotify, Telegram, Discord)

- **Self-hosted endpoints** must be reachable *from the Kuma container* — not from your laptop. Exec in and curl it
- A **reverse proxy** in front that needs WebSocket or that rate-limits
- Telegram: the bot must have been **started** by the recipient, and the chat ID must be right (negative for groups)
- Discord/Slack: webhook URLs **expire** when the channel or app is removed

## 6. After an update

- **Docker tag pinned?** If you run `latest`, an update happened without you choosing it
- Check the container log around the event time — Kuma logs notification send failures with the provider's error
- Clear the browser cache after upgrading; a stale frontend can show settings that aren't what the server has

## Prevention

1. When you add a notification, **immediately tick it on every existing monitor** you care about
2. Keep **one deliberately failing monitor** (point it at a closed port) and pause/unpause it monthly as a live test of the whole chain
3. Use **two channels** for anything important — email plus a push service
4. **Pin the image tag**
5. Back up the `data` volume; it holds monitors, notifications and history

## FAQ

**Why does the test notification work but nothing else?**
Because the test bypasses monitor configuration. The notification almost certainly isn't ticked on the monitor.

**How do I get repeated alerts while something is down?**
Set a resend interval on the monitor.

**Why no notification for a brief outage?**
Retries. The monitor went Pending and recovered before it was declared Down.

**Should I use email?**
As a second channel. Push services are far more reliable for self-hosted alerting.
