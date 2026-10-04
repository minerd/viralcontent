---
title: "docker-mailserver: \"Relay access denied\" When Sending"
slug: docker-mailserver-relay-access-denied
meta_description: "554 5.7.1 Relay access denied on mail you're trying to send. Submission versus port 25, SASL auth, and the relay host settings."
updated: October 2026
cluster: round 13 (tech) — docker-mailserver GitHub issues
competition: LOW
---

# docker-mailserver: "Relay access denied" When Sending

```
554 5.7.1 <recipient@elsewhere.com>: Relay access denied
```

This is Postfix refusing to forward mail for a client it doesn't trust. It is **correct behaviour** — an open relay is worse than a broken one. The question is why your client isn't being trusted, and there are four distinct answers.

## 1. You're connecting on port 25 instead of 587

Port 25 is for **server-to-server** delivery to *your* domains. It does not relay for clients, by design. Authenticated client submission is port **587** (STARTTLS) or **465** (implicit TLS).

A mail client configured for port 25 gets exactly this error on any external recipient, while mail to a local mailbox works fine. That asymmetry — internal works, external denied — is the signature.

```yaml
ports:
  - "25:25"      # inbound from other servers
  - "143:143"    # IMAP
  - "465:465"    # submissions (implicit TLS)
  - "587:587"    # submission (STARTTLS)
  - "993:993"    # IMAPS
```

In the client: server `mail.example.com`, port 587, STARTTLS, **normal password**, username = the full email address.

## 2. Authentication isn't happening

Even on 587, Postfix relays only for authenticated senders. Check the log:

```bash
docker exec mailserver tail -n 50 /var/log/mail/mail.log | grep -iE 'sasl|auth|relay'
```

- **No `sasl_username=` in the log line** → the client never authenticated. Usually the client has authentication disabled, or is set to "no authentication" because an earlier test worked against a local mailbox.
- **`SASL LOGIN authentication failed`** → wrong credentials. The username is the **full address**, not the local part:

```bash
docker exec mailserver setup email list
docker exec mailserver setup email update user@example.com
```

- **`authentication failed: Invalid authentication mechanism`** → the client is offering a mechanism Dovecot isn't configured for. `PLAIN` and `LOGIN` over TLS is the standard pairing; CRAM-MD5 requires plaintext password storage and is off by default.

## 3. You're trying to send *as* a domain you don't own

```
Sender address rejected: not owned by user
```

A related but different error. docker-mailserver enforces that the authenticated user matches the `From:` address. Sending as `noreply@otherdomain.com` while authenticated as `user@example.com` is refused.

For an application that needs a different From, either create that mailbox or configure an alias:

```bash
docker exec mailserver setup alias add noreply@example.com user@example.com
```

And if you genuinely need one account to send as several addresses, that's `POSTFIX_DAGENT`-adjacent territory — the supported route is `setup alias` plus the `postfix-send-access` configuration, not disabling the check.

## 4. Relaying *through* another provider

If your ISP blocks port 25 outbound (most residential ones do) you must relay through a smarthost. The symptom without it is different — mail queues and times out rather than being denied — but misconfigured relay settings produce denial from the *upstream*, which looks identical in your client.

```yaml
environment:
  - RELAY_HOST=smtp.provider.com
  - RELAY_PORT=587
  - RELAY_USER=your-smtp-user
  - RELAY_PASSWORD=your-smtp-password
```

Then verify the credentials file was generated:

```bash
docker exec mailserver cat /etc/postfix/sasl_passwd
docker exec mailserver postconf relayhost
```

Points that matter:

- **The provider must allow your From address.** Most transactional providers require a verified sender domain. A "relay access denied" from *their* server means your domain isn't verified there, not that your Postfix is wrong — read the full log line to see which server rejected it.
- **Per-domain relays** are configured through `postfix-relaymap.cf` if you need different upstreams per domain.
- Changing relay env vars requires a container restart; they're processed at startup.

## Reading the log correctly

The single most useful habit: find which hostname issued the rejection.

```bash
docker exec mailserver grep -i 'relay access denied' /var/log/mail/mail.log | tail -5
```

```
NOQUEUE: reject: RCPT from unknown[192.168.1.44]: 554 5.7.1 <x@y.com>: Relay access denied;
  from=<user@example.com> to=<x@y.com> proto=ESMTP helo=<client>
```

`RCPT from unknown[192.168.1.44]` with no `sasl_username=` is the unauthenticated-client case (sections 1–2). A rejection appearing as a bounce *from* the smarthost is section 4.

## What not to do

- **Don't add your network to `mynetworks` to make it work.** That's creating an open relay for anything on that subnet, and if the container's network includes other containers, for all of them. It's the most commonly suggested and most dangerous "fix".
- **Don't disable the sender-ownership check.** It's what prevents one compromised account spoofing every address you host.
- **Don't test with `telnet` on port 25 and conclude relaying is broken.** It's supposed to be.
- **Don't open 587 to the internet without fail2ban or rate limiting.** docker-mailserver includes fail2ban support; enable it.

## Prevention

| Habit | Why |
|---|---|
| Clients always on 587/465 with auth | Removes the dominant cause |
| Full email address as username, documented | The second-most-common cause |
| `ENABLE_FAIL2BAN=1` | Authenticated submission ports attract brute force immediately |
| SPF, DKIM and DMARC configured | Mail that relays successfully but is rejected downstream is the next problem you'd hit |

## FAQ

**Mail sends but lands in spam.**
Different problem: SPF/DKIM/DMARC and the reverse DNS on your sending IP. `setup config dkim` generates the keys.

**Can I receive on 25 and send via a relay?**
Yes, and that's the normal home setup. Inbound on 25 (if your ISP allows it), outbound via a smarthost.

**"Relay access denied" only for some recipients.**
Then it's probably the upstream relay refusing specific domains, or a recipient-side policy. Check which server issued the code.

**Does it need a valid certificate?**
For STARTTLS clients, effectively yes. `SSL_TYPE=letsencrypt` with a mounted certificate directory is the usual configuration.
