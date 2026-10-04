---
title: "listmonk: Bounces Not Being Processed"
slug: listmonk-bounce-not-processed
meta_description: "Zero bounces recorded even for invalid addresses. The Return-Path problem, the headers listmonk needs to see, and why POP3 often reads nothing useful."
updated: October 2026
cluster: round 14 (tech) — knadh/listmonk GitHub issues
competition: LOW
---

# listmonk: Bounces Not Being Processed

Bounce processing fails for a structural reason more often than a configuration one: **listmonk identifies a bounce by finding its campaign and subscriber UUIDs in the bounced message**, and many mail systems don't preserve them where it looks.

## 1. Understand what listmonk needs to find

When listmonk sends, it embeds identifiers. On a bounce it needs to recover them. Two paths:

- **The `Return-Path` / envelope sender** carries a per-message address (VERP-style)
- **The original message headers**, returned inside the bounce as a `text/rfc822-headers` part

The reported failure: **the UUIDs are in the `text/rfc822-headers` MIME part, and listmonk only inspects the top-level bounce headers** — so it reads the mailbox, finds a message, and can't attribute it. The result is "0 bounces" with mail clearly bouncing.

That's why the first thing to check is not your settings but an actual bounce message:

```bash
# fetch one from the bounce mailbox and look at it
python3 - <<'PY'
import imaplib, email
m = imaplib.IMAP4_SSL('imap.example.com')
m.login('bounces@example.com', 'password')
m.select('INBOX')
_, data = m.search(None, 'ALL')
ids = data[0].split()
_, msg = m.fetch(ids[-1], '(RFC822)')
e = email.message_from_bytes(msg[0][1])
print(e.get('Return-Path'), e.get('To'), e.get_content_type())
for p in e.walk():
    print('--', p.get_content_type())
PY
```

If the UUID appears only inside a nested part, listmonk's header-based matching won't see it on the affected versions.

## 2. Configure the Return-Path properly

```
Settings → Bounces → enable
Settings → SMTP → (your server) → ... 
```

The documented limitation: **listmonk's `Return-Path` has been the same as `From`**, and setting it via custom campaign headers doesn't change it. So bounces go to your From address rather than a dedicated bounce mailbox, and anything relying on a distinct envelope sender doesn't work.

What to do about it:

- **Use the From address as your bounce mailbox.** Point listmonk's bounce POP3/IMAP settings at the same mailbox your From address delivers to. Less elegant, works.
- **Prefer webhook bounce processing** if your sending provider offers it (section 3). It sidesteps the whole header-parsing question.
- Check your version's release notes — Return-Path handling has had changes, and a newer build may do what you need.

## 3. Webhooks beat mailbox scraping

listmonk supports bounce webhooks from Amazon SES, SendGrid, Postmark, Mailgun and a generic format. If you send through any of them, use the webhook:

```
Settings → Bounces → Enable bounce webhooks
  → SES / SendGrid / Postmark / Mailgun
```

Then configure that provider to POST to:

```
https://listmonk.example.com/webhooks/service/ses
```

The provider has already classified the bounce as hard or soft and knows which message it belongs to, so none of the UUID-recovery problem arises. This is the reliable path and it's worth switching to if mailbox-based processing is failing.

For the generic webhook you supply the campaign and subscriber UUIDs yourself, which means it's only useful if your sending pipeline tracks them.

## 4. POP3/IMAP settings that silently read nothing

```
Host: imap.example.com
Port: 993
Auth: login
Username: bounces@example.com
Password: ...
TLS: yes
Scan interval: 15m
```

Things that produce "no bounces" with no error:

- **The wrong folder.** listmonk scans INBOX. If your provider files bounces into a `Junk` or a filtered folder, it never sees them. Disable server-side filters for that mailbox.
- **Messages already marked read** by another client. listmonk's scan behaviour around read/unread differs by version; a mail client checking the same mailbox can consume them first. Use a dedicated mailbox nothing else touches.
- **TLS mismatch** — port 993 with TLS off, or 143 with TLS on, fails to connect; the log says so:

```bash
docker logs listmonk --tail 100 | grep -iE 'bounce|pop|imap'
```

## 5. Transactional email bounces

A separate, documented gap: **bounced transactional messages are not added to the blocklist**, while campaign bounces are. If you rely on transactional sends to clean your list, that won't happen. Treat list hygiene as a campaign-driven process, or handle transactional bounces yourself via the API.

## 6. "Campaign marked finished but not everyone received it"

Related and worth checking at the same time:

```bash
docker logs listmonk --tail 200 | grep -iE 'error|dial|timeout|server misbehaving'
```

```
error sending message: dial tcp: lookup smtp.example.com: server misbehaving
```

That's DNS inside the container, not a bounce issue. A campaign can be marked finished with many messages failed if the SMTP errors are transient — check the campaign's stats against your list count, and set up a sane `max_conns` and retry configuration in the SMTP settings.

## What not to do

- **Don't share the bounce mailbox with a mail client.** Message state gets consumed.
- **Don't rely on bounce processing for list hygiene without verifying it works.** Send to a known-invalid address and confirm the count increments.
- **Don't set the bounce action to "blocklist" on the first bounce.** Soft bounces (full mailbox, temporary failure) are normal; blocklisting on one is how you lose real subscribers. Use a threshold.
- **Don't debug settings before reading an actual bounce message.** It tells you whether the identifiers are even recoverable.

## Prevention

| Habit | Why |
|---|---|
| Webhook-based bounces where your provider supports it | Removes the entire parsing problem |
| A dedicated bounce mailbox nothing else reads | Prevents state being consumed |
| Test with a deliberately invalid address after any change | The only proof it works |
| Bounce threshold of 2–3 before blocklisting | Soft bounces aren't dead addresses |

## FAQ

**How many bounces before an address is dead?**
Three consecutive hard bounces is conservative and safe. One hard bounce for "user unknown" is usually definitive, if you can distinguish hard from soft — which webhooks give you and mailbox parsing often doesn't.

**Can I import a bounce list from elsewhere?**
Blocklist the addresses via the subscribers import with the blocklisted status.

**Does a high bounce rate hurt deliverability?**
Yes, substantially. It's the main reason to get this working.

**Soft and hard bounces treated the same?**
Configure separate actions per type where your version supports it; otherwise use a threshold so soft bounces don't accumulate into a blocklist.
