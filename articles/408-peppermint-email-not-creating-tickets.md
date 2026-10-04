---
title: "Peppermint: Emails Not Creating Tickets"
slug: peppermint-email-not-creating-tickets
meta_description: "The IMAP mailbox connects and \"loop completed, no new messages\" repeats. Folder names, read-state handling and the queue configuration."
updated: October 2026
cluster: round 14 (tech) — Peppermint-Lab/peppermint GitHub discussions
competition: LOW
---

# Peppermint: Emails Not Creating Tickets

The characteristic log line:

```
loop completed No new messages
```

Peppermint connected, authenticated, polled the mailbox, and considered everything already handled. So the question is not "can it connect" — it's "why does it think there's nothing new".

```bash
docker logs peppermint --tail 100 | grep -iE 'imap|mail|queue|loop'
```

## 1. The folder it polls

Peppermint polls **INBOX**. Reported confusion around `+INBOX` versus `INBOX` is worth settling explicitly, because IMAP folder naming varies by server:

```bash
python3 - <<'PY'
import imaplib
m = imaplib.IMAP4_SSL('imap.example.com')
m.login('support@example.com', 'password')
print(m.list())
PY
```

That prints the exact folder names your server uses. Some servers present `INBOX`, some `INBOX.` with a delimiter, some nest everything under a namespace prefix. If Peppermint's configuration lets you set the folder, use the string from that listing verbatim.

Also: **server-side filters.** If your provider files support mail into a sub-folder (or Gmail applies a label and skips the inbox), INBOX is genuinely empty. Disable filtering for that mailbox — this is a common cause when the mailbox "obviously has mail" in a web client.

## 2. Read state

The usual mechanism for "new" is **unread**. Two things break it:

- **Another client has read the mail.** Your phone's mail app, a webmail session left open, or a monitoring check marks messages read, and Peppermint then skips them. Use a **dedicated mailbox nothing else touches** — this single change resolves a large share of these reports.
- **The server marks messages read on fetch** in some configurations, so a failed processing attempt leaves the message read and permanently skipped.

Test the state directly:

```bash
python3 - <<'PY'
import imaplib
m = imaplib.IMAP4_SSL('imap.example.com')
m.login('support@example.com','password')
m.select('INBOX')
print('unseen:', m.search(None, 'UNSEEN'))
print('all:', m.search(None, 'ALL'))
PY
```

`unseen: ('OK', [b''])` with messages in `all` is the whole explanation.

To reprocess, mark a message unread from a mail client and watch Peppermint's next loop.

## 3. Mailbox configuration in the admin area

IMAP listening is configured per mailbox in Peppermint's admin area, not in environment variables in current versions. Points to verify:

- **Host, port, TLS** — 993 with TLS, or 143 with STARTTLS. A mismatch fails to connect (a different error from "no new messages").
- **Credentials** — for Gmail/Microsoft, an app password or OAuth, not the account password.
- **The mailbox is enabled.** A configured-but-disabled mailbox polls nothing.

If you configured it through environment variables following an older guide, those may be ignored entirely by your version. Re-enter it in the admin UI.

## 4. Mail arrives, ticket isn't created

Different from section 1 — the log shows a message being processed and no ticket appears.

- **No default client/queue mapping.** Peppermint associates incoming mail with a client or queue; without a mapping, processing can fail silently. Create a catch-all.
- **The sender isn't a known contact** and your configuration requires one. Allow ticket creation from unknown senders if you want a public support address.
- **Database write failure.** Check Postgres:

```bash
docker logs peppermint --tail 100 | grep -iE 'prisma|postgres|database'
```

- **Attachment handling.** A message with a large attachment can fail the whole ticket creation if storage isn't writable.

## 5. Verify with a controlled test

```bash
# send a plain-text test from a different address
printf 'Subject: test ticket %s\n\nbody\n' "$(date +%s)" \
  | msmtp -a default support@example.com
```

Then watch:

```bash
docker logs -f peppermint | grep -iE 'imap|ticket'
```

A single controlled message removes the ambiguity of "is there even new mail". If that message is picked up and a real customer's wasn't, compare them — HTML-only bodies, unusual encodings and `multipart/report` (bounces) have all caused processing to skip a message.

## 6. Scale back the ambition if needed

Email-to-ticket is the least mature part of several self-hosted helpdesks, Peppermint included — the feature is present and the reliability reports are mixed. If it's blocking you:

- Use the **web portal** for ticket creation and treat email as notification-only
- Or forward mail into a tool with a more established mail pipeline and link to Peppermint

That's a legitimate architectural choice rather than a workaround, and worth making deliberately before spending a week on IMAP.

## What not to do

- **Don't share the support mailbox with a mail client.** Read state gets consumed.
- **Don't leave server-side filters on** for the polled mailbox.
- **Don't use the account password for Gmail/365.** App password or OAuth.
- **Don't assume env vars configure it.** Check the admin UI for your version.

## Prevention

| Habit | Why |
|---|---|
| Dedicated mailbox, no filters, no other clients | Removes the dominant cause |
| Exact folder name from an IMAP LIST | No guessing about INBOX naming |
| A controlled test message after every change | The only unambiguous signal |
| Catch-all client/queue mapping | Unknown senders still produce tickets |

## FAQ

**Does it support POP3?**
IMAP is the supported path; POP3's lack of flags makes "new message" tracking worse, not better.

**Can replies append to an existing ticket?**
Via the ticket reference in the subject or headers. Stripping the reference in a reply creates a new ticket.

**Outbound notifications work, inbound doesn't.**
Different configuration entirely (SMTP vs IMAP). Fixing one tells you nothing about the other.

**How often does it poll?**
On a loop with a fixed interval; the log shows each pass. There's no push/IDLE support in current versions.
