---
title: "Wallos: Subscription Notifications Not Sending (Test Works)"
slug: wallos-notifications-not-sending
meta_description: "The test button succeeds and real reminders never arrive. The three places notifications must be enabled, and the cron that does the sending."
updated: October 2026
cluster: round 14 (tech) — ellite/Wallos GitHub issues and Cloudron forum
competition: LOW
---

# Wallos: Subscription Notifications Not Sending (Test Works)

The distinctive symptom: **the test notification arrives, the actual reminders don't.** That rules out credentials and transport, and points at one of three things.

## 1. Notifications must be enabled in three places

This is the cause most of the time, and it's easy to miss because each switch is in a different screen.

1. **Globally** — Settings → Notifications → the channel (email, Discord, Pushover, Telegram, Gotify, ntfy, webhook) enabled, with its credentials.
2. **The notification schedule** — Settings → Notifications → *how many days before* a renewal to notify. If this is unset or zero, nothing is scheduled.
3. **Per subscription** — each subscription has its own **Notify** toggle. A subscription with notifications off is silently skipped, no matter what the global settings say.

The test button only exercises (1). That's why it succeeds while nothing real sends.

```
Subscriptions → (each one) → edit → Notifications: on
```

If you have many subscriptions added before you configured notifications, they may all be off. There is no bulk toggle in some versions — this is tedious but it is the fix.

## 2. The cron job is what actually sends

Wallos sends notifications from a scheduled task, not on page load. In the Docker image this runs inside the container; on a bare-metal install you must install it.

```bash
docker exec wallos crontab -l
docker exec wallos ls -la /var/www/html/endpoints/cronjobs/
```

Expected: a daily entry invoking the notification script. If `crontab -l` is empty, nothing is scheduled and nothing will ever send.

For a manual install:

```bash
# as the web user
0 9 * * * php /var/www/html/endpoints/cronjobs/notifications.php
```

Run it by hand to see errors, which the UI never shows you:

```bash
docker exec wallos php /var/www/html/endpoints/cronjobs/notifications.php
```

That single command is the most useful diagnostic here — it either sends or prints the reason.

## 3. Timezone and the "already notified" flag

- **Container timezone.** If the container runs UTC and you expect a 9am local reminder, it fires at the wrong time, and for a notification scheduled "1 day before" it can fall on the wrong side of midnight:

```yaml
    environment:
      - TZ=Europe/Istanbul
```

- **Wallos records that it notified.** Once a renewal has been notified, it won't notify again for that cycle. So testing by changing the date forward and back doesn't re-trigger. To test properly, add a throwaway subscription with a renewal date inside your notification window.

## 4. Channel-specific gaps

A real and reported case: **email works while ntfy doesn't**, with the ntfy test showing "Success". Two things to check for ntfy specifically:

```
Server URL: https://ntfy.example.com
Topic:      wallos
```

- The URL must **not** include the topic — topic is a separate field. A URL of `https://ntfy.example.com/wallos` with topic `wallos` posts to `/wallos/wallos`, which silently succeeds at the HTTP level and goes nowhere you're subscribed.
- A protected topic needs the token/credentials field populated. The test may pass against an open topic and fail against a protected one.

For **Discord/Gotify webhooks**, the URL must be the full webhook URL including the token. For **Telegram**, the chat ID of a group is negative (`-100...`) and easy to mistype.

## 5. Verify at the receiving end

```bash
# subscribe to your ntfy topic and watch
curl -s https://ntfy.example.com/wallos/json
```

Leave that running while you execute the cron script by hand. If the message appears there and not on your phone, the problem is your ntfy subscription, not Wallos.

## What not to do

- **Don't retest the global channel repeatedly.** It already works; that's the point.
- **Don't change renewal dates to test.** The notified flag defeats it. Create a test subscription instead.
- **Don't assume the Docker image's cron is running** after a custom entrypoint or a restart policy change. Check it.
- **Don't put the topic in the ntfy URL.** It's the most common channel-specific mistake.

## Prevention

| Habit | Why |
|---|---|
| Turn on per-subscription notifications when adding each one | Avoids a bulk cleanup later |
| `TZ` set on the container | Reminders at the hour you expect |
| Run the cron script by hand after any change | The only place errors are visible |
| One test subscription, dated inside the window | Repeatable testing without touching real data |

## FAQ

**Can I get a single daily digest instead of one per subscription?**
Not in the stock notification logic; it notifies per renewal.

**Does it notify for monthly subscriptions every month?**
Yes, once per cycle, based on the next renewal date.

**Nothing in the logs at all.**
Then the cron isn't running. Section 2.

**Can I use my own SMTP relay?**
Yes — host, port, encryption, username and password in the email channel settings. Port 587 with STARTTLS is the usual working combination.
