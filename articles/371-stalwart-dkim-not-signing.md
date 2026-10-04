---
title: "Stalwart Mail Server: DKIM Not Signing Outbound Mail"
slug: stalwart-dkim-not-signing
meta_description: "\"DKIM signer not found\", or secondary domains silently unsigned. Where the signature record must live, the selector match, and the Ed25519 problem."
updated: October 2026
cluster: round 14 (tech) — stalwartlabs GitHub and support forum
competition: LOW
---

# Stalwart Mail Server: DKIM Not Signing Outbound Mail

Three failures, and the second is a genuine gap worth knowing about before you trust a multi-domain setup.

## 1. "DKIM signer not found"

```
WARN dkim.signer-not-found
```

Stalwart looked up a signature configuration for the sending domain and found none. Check that a signature actually exists and that it is listed under DKIM settings:

```
Settings → Authentication → DKIM → Signatures
```

Each signature needs a domain, a selector, an algorithm and a key. After adding one, **reload the configuration** — Stalwart caches signers and a new one is not picked up until it does:

```bash
# via the CLI/management API, or simply
systemctl reload stalwart
```

The warning is a warning, not an error: mail still goes out, unsigned. That's why it can run for weeks unnoticed until a recipient's DMARC report arrives.

## 2. Secondary domains silently unsigned

The documented problem: adding a DKIM key through the management UI for a **secondary** local domain is accepted without error, but **no DNS TXT records are produced and outbound mail from that domain goes unsigned**. No server-side log entry marks the failure.

So the UI appearing to succeed is not evidence. Verify directly:

```
Settings → Domains → (the secondary domain) → DKIM Signatures
```

What to confirm:

- A `DkimSignature` record exists **for that domain**
- Its `domainId` points at the **secondary** domain, not the primary

If the record is missing or bound to the wrong domain, recreate it with the domain selected explicitly, or create it through the API rather than the UI. Then publish the DNS records by hand — the UI's "here are your DNS records" panel is what silently produces nothing in this case.

The practical rule: **after adding any domain, send a test message from it and check the headers.** Do not assume the primary domain's working DKIM implies the others.

## 3. Selector and DNS must match exactly

```bash
dig +short TXT selector._domainkey.example.com
```

```
"v=DKIM1; k=rsa; p=MIIBIjANBgkqhki..."
```

The checks, in order:

- The **selector** in Stalwart's signature config must equal the label in DNS. `default._domainkey` in DNS and a selector of `stalwart` in config will never match.
- The published `p=` must be the **public** key corresponding to the private key Stalwart holds. Regenerating a key in the UI invalidates the old DNS record.
- Long RSA keys split across multiple quoted strings in DNS are fine — resolvers concatenate them — but a record split with a stray space inside the base64 is not.
- `k=` must match the algorithm: `rsa` for RSA, `ed25519` for Ed25519.

## 4. Ed25519 and the dual-signature problem

Stalwart can sign with Ed25519, and it's tempting: short keys, modern crypto. But a practical interoperability issue is well documented: **some large providers do not validate correctly when both RSA and Ed25519 signatures are present**, and the message fails DKIM at the receiver despite both being valid.

The pragmatic configuration today:

- **RSA-2048 only** for mail that must reach mainstream providers.
- Add Ed25519 only if you've verified delivery with your actual recipients.

If you're currently dual-signing and seeing DKIM failures at Gmail or Outlook, remove the Ed25519 signature and retest. That single change resolves a class of "my DKIM is valid but they reject it" reports.

## 5. Verify what actually left the server

The only test that counts is a received message's headers:

```
DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=stalwart;
    bh=...; h=from:to:subject:date; b=...
```

```
Authentication-Results: mx.google.com;
       dkim=pass header.i=@example.com;
       spf=pass; dmarc=pass
```

Send to a mailbox you control at a major provider and read the raw headers. `dkim=pass` with your domain in `header.i` is the goal. No `DKIM-Signature` header at all means section 1 or 2.

## What not to do

- **Don't treat the UI's success message as proof.** Check the signature record and send a test.
- **Don't rotate DKIM keys without publishing the new DNS record first.** Publish, wait for propagation, then switch the signer.
- **Don't enable Ed25519 alongside RSA** without verifying delivery.
- **Don't deploy a mail server without SPF and DMARC too.** DKIM alone won't get you delivered.

## Prevention

| Habit | Why |
|---|---|
| Send a test from every domain after adding it | Catches the silent secondary-domain failure |
| RSA-2048, one selector per domain, documented | Interoperable and easy to audit |
| DMARC with `rua=` reporting | You learn about signing failures from receivers |
| Keep private keys in your backups | A lost key means a key rotation under pressure |

## FAQ

**Does Stalwart handle SPF and DMARC too?**
Yes, both for inbound evaluation and for publishing guidance. The DNS records are still yours to publish.

**Can I use one key for several domains?**
Technically yes by publishing the same `p=` under each domain, but one key per domain is cleaner to rotate and revoke.

**How long should keys be?**
2048-bit RSA. 1024 is widely accepted but weak; 4096 can exceed DNS UDP limits and cause lookup failures.

**Mail signs but DMARC still fails.**
DMARC requires alignment: the `d=` in the DKIM signature must align with the `From:` domain. Signing with a different domain passes DKIM and fails DMARC.
