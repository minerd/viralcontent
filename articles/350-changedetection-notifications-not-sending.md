---
title: "changedetection.io: Changes Detected But No Notifications"
slug: changedetection-notifications-not-sending
meta_description: "The diff shows but nothing is sent, or the test button works and real changes don't. Apprise URL syntax, per-watch overrides and the SMTP regressions."
updated: October 2026
cluster: round 14 (tech) — changedetection.io GitHub issues
competition: LOW
---

# changedetection.io: Changes Detected But No Notifications

Split the problem in one step: does the **Send test notification** button work?

- **Test fails** → the Apprise URL is wrong (section 1)
- **Test works, real changes send nothing** → scope or trigger (section 2)
- **Both work, nothing arrives** → the delivery service (section 3)

## 1. Test notification fails

The error text is Apprise's, and it is specific.

**`Unparseable <service> URL`** — the URL syntax is wrong. The formats that trip people up most:

```
# Telegram — bot token then chat id, no @ on the bot name
tgram://123456789:AAbbCCddEEff.../-1001234567890

# ntfy — host then topic
ntfy://ntfy.example.com/mytopic
ntfys://user:pass@ntfy.example.com/mytopic

# Gotify — token as the path
gotify://gotify.example.com/AbCdEfGhIjKlMnO

# Email via SMTP
mailto://user:pass@smtp.example.com:587/?to=you@example.com&from=cd@example.com
```

Characters that need URL-encoding in a password (`@`, `/`, `#`, `:`) are a frequent cause of "unparseable" — percent-encode them.

**`windows:// is not a valid AppRise URL`** — desktop notification backends only work where that backend exists. In a container, it never will.

**SMTP errors like `SMTPServerDisconnected: please run connect() first`** — this has appeared as a regression in specific releases. If your mail config worked before an update and now throws this, pin the previous version and check the issue tracker rather than rewriting the config:

```yaml
    image: ghcr.io/dgtlmoon/changedetection.io:0.45.18
```

Also relevant: **mail servers addressed by IP** rather than hostname have failed in some versions. Use a hostname if you can.

## 2. Test works but changes don't notify

- **No notification URL at the watch level and none in Settings.** The global default is under **Settings → Notifications**; a watch with its own (possibly empty) override ignores it. Check the individual watch's Notifications tab — an empty field there can mean "none", not "inherit", depending on version.
- **"Send a notification when..." unchecked.** Each watch has trigger checkboxes (changed, error, filter not found). If only *error* is selected, a normal change is silent.
- **The filter removes everything.** With a CSS/XPath filter that matches nothing, there is no text to diff, so there is no change. The watch shows "filter not found" rather than a change — enable notification on that condition too, so you find out.
- **`trigger_text` / "only trigger when this text appears"** set, and the change doesn't include it.

Check the watch's history: if the diff page shows a change but no notification was logged, it's a trigger setting. The log says what was attempted:

```bash
docker logs changedetection --tail 50 | grep -i notif
```

## 3. Sent but not delivered

- **Encoding.** Special characters in the page content have broken specific backends (notably generic `posts://`) in some versions. Reduce the notification body to a plain template to test:

```
{{watch_url}} changed
```

The body template supports `{{diff}}`, `{{diff_full}}`, `{{current_snapshot}}` and more — a huge `{{diff_full}}` can exceed a service's message size limit and be dropped silently.

- **Rate limits.** Telegram and Pushover throttle. A watch with a 1-minute interval on a frequently-changing page will get cut off.
- **ntfy topic access.** A protected topic needs credentials in the URL (`ntfys://user:pass@...`).

## What not to do

- **Don't put `{{diff_full}}` in the body by default.** It's the most common cause of silently dropped messages.
- **Don't test with a 30-second check interval.** You'll hit rate limits and misread them as failures.
- **Don't use a CSS filter you haven't verified.** Use the visual selector and confirm the preview contains text.
- **Don't delete and re-add the watch.** You lose its history, which is the evidence.

## Prevention

| Habit | Why |
|---|---|
| One global notification URL in Settings, overrides only where needed | Removes the empty-override confusion |
| Short body template, link to the diff | Immune to size limits and encoding bugs |
| Enable the "filter not found" notification | You hear when a site redesign breaks a watch |
| Pin the image tag | Notification regressions have shipped more than once |

## FAQ

**Can one watch notify several services?**
Yes — one Apprise URL per line.

**Why do I get a notification on first check?**
The first fetch establishes a baseline. Some versions notify on it; mark it as read and ignore.

**It notifies constantly on a page I didn't change.**
Ads, timestamps or session tokens in the captured text. Add an ignore-text rule or tighten the filter.

**Does it work with a self-hosted ntfy behind auth?**
Yes, with credentials in the URL and the topic's access rules allowing that user.
