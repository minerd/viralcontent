---
title: "Kavita OPDS: Reader App Can't Fetch the Feed"
slug: kavita-opds-not-connecting
meta_description: "\"Failed to fetch feed\" in your e-reader app. The URL format with the API key, the OPDS toggle, and the clients that append /opds themselves."
updated: October 2026
cluster: round 14 (tech) — Kavita GitHub issues and KOReader issues
competition: LOW
---

# Kavita OPDS: Reader App Can't Fetch the Feed

Three things must be true, and the second is off by default.

## 1. Get the exact URL from Kavita

Don't construct it by hand. Kavita generates it per user:

```
Kavita → (your avatar) → Settings → OPDS
```

The format is:

```
https://kavita.example.com/api/opds/0a1b2c3d-4e5f-6071-8293-a4b5c6d7e8f9
```

That trailing segment is your **API key**, not a path you choose. Points that matter:

- It is `/api/opds/<key>` — not `/opds`, not `/api/opds` without the key.
- The key belongs to a specific user, and that user's library permissions determine what the feed contains. A key for a user with no library access returns an empty feed rather than an error.
- Regenerating the API key in Kavita invalidates every configured client.

## 2. OPDS must be enabled server-side

```
Kavita → Admin → Settings → General → Enable OPDS
```

It is **disabled by default**. With it off, the endpoint returns an error and every client reports a generic fetch failure. This is the single most common cause.

Verify from a shell before touching the app:

```bash
curl -s "https://kavita.example.com/api/opds/YOUR-KEY" | head -20
```

You want XML beginning with `<feed`. What the failures mean:

- **401 / 403** — wrong key, or OPDS disabled
- **404** — wrong path
- **HTML** — you hit a proxy login page or the SPA, not the API
- **500** — check Kavita's own log

## 3. Clients that append `/opds` themselves

A real and confusing behaviour: some clients (Crosspoint among them) **automatically append `/opds`** to whatever you give them. Paste the full Kavita URL and you end up requesting:

```
https://kavita.example.com/api/opds/YOUR-KEY/opds     ← 404
```

If your client has a "catalog URL" field and you're getting 404s with a URL that works in curl, try giving it the URL **without** the trailing part the client adds — or check the client's documentation for whether it wants a base URL or a full catalog URL. This is client-specific and not something Kavita can fix.

Conversely, clients that want the full URL and get a base URL produce the same 404 from the other direction.

## 4. Reverse proxy

```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 0;
    proxy_read_timeout 300s;
}
```

Specific to OPDS:

- **Forward-auth (Authelia, authentik) in front of Kavita breaks OPDS.** Reader apps can't complete an interactive login. Exempt `/api/opds` from forward-auth, or accept that OPDS only works on the LAN. The API key *is* the authentication for that path, so exempting it is defensible.
- **`client_max_body_size 0`** — downloading a large CBZ or EPUB through the feed goes through the proxy.
- Basic auth has the same problem as forward-auth: most OPDS clients support it, but combining it with the API key confuses some.

## 5. Feed loads, downloads fail

Separate step. The feed gives links; the client then fetches the file.

- A **relative URL** problem: if Kavita's configured base URL doesn't match how clients reach it, the download links point somewhere wrong. Set it correctly:

```
Admin → Settings → General → Base URL
```

- **Timeouts** on large files — raise `proxy_read_timeout`.
- **Format support.** OPDS serves what's on disk. A client that can't read CBZ will fail on a comic regardless of the feed working.

## 6. Progress sync is a different feature

Reading-position sync (KOReader-style) is **not** part of OPDS. Kavita exposes a sync endpoint, and compatibility with specific client plugin versions has varied. If your feed works and progress doesn't sync, that's a separate integration — don't reconfigure OPDS to chase it.

## What not to do

- **Don't put forward-auth in front of `/api/opds`.** No reader app can satisfy it.
- **Don't share your OPDS URL.** The key in it is a credential with that user's library access.
- **Don't regenerate the API key casually.** Every configured device breaks.
- **Don't debug in the app first.** `curl` the URL; it answers in one command.

## Prevention

| Habit | Why |
|---|---|
| Enable OPDS at install time, note it in your setup docs | It's off by default and nobody remembers |
| One Kavita user per family member, own key | Scoped libraries and revocable access |
| `/api/opds` exempted from forward-auth, documented why | Keeps the rest of the app protected |
| Test with curl after any proxy change | Separates server from client instantly |

## FAQ

**Which reader apps work well?**
Anything with solid OPDS support — several iOS and Android readers, Thorium on desktop, and KOReader on e-ink. Behaviour around URL handling differs, per section 3.

**Can I browse by library?**
Yes, the feed is hierarchical: libraries, series, volumes.

**Does it support search?**
Kavita's OPDS feed includes an OpenSearch description, which capable clients use.

**Empty feed, no error.**
The user behind that API key has no library permissions. Check in Admin → Users.
