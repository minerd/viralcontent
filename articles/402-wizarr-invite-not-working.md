---
title: "Wizarr: Invitations Not Working for Jellyfin"
slug: wizarr-invite-not-working
meta_description: "Invite links fail, users aren't created, or the code is rejected. The server URL and API key Wizarr needs, the external URL, and whitespace in codes."
updated: October 2026
cluster: round 14 (tech) — wizarrrr/wizarr GitHub issues
competition: LOW
---

# Wizarr: Invitations Not Working for Jellyfin

Wizarr sits between your invitee and your media server: it collects their details, then **creates the account on Jellyfin through the API**. So a failing invite is almost always one of three things — Wizarr can't reach Jellyfin, the key lacks permission, or the invitee can't reach Wizarr.

## 1. Wizarr → Jellyfin

In Wizarr's settings you configure the server type, URL and API key.

```bash
docker exec wizarr sh -c \
  "wget -qO- 'http://jellyfin:8096/System/Info?api_key=YOUR_KEY' | head -c 300"
```

That one command settles it:

- **Connection refused / timeout** — wrong address. `localhost` means the Wizarr container. Use the service name or LAN IP.
- **401** — the API key is wrong or was revoked.
- **HTML** — you hit a reverse proxy login page; use the internal address.
- **JSON with the server name** — good; the problem is elsewhere.

The API key comes from **Jellyfin → Dashboard → API Keys**. Jellyfin's API keys are server-wide and can create users, which is what Wizarr needs — there is no narrower scope to grant, so treat the key as sensitive.

## 2. The invitee → Wizarr

The invite link contains Wizarr's **external** URL. If that's wrong, the link resolves nowhere or lands on a page that can't complete the flow.

```yaml
services:
  wizarr:
    image: ghcr.io/wizarrrr/wizarr:latest
    environment:
      - APP_URL=https://join.example.com
      - DISABLE_BUILTIN_AUTH=false
    ports:
      - "127.0.0.1:5690:5690"
    volumes:
      - ./data:/data
```

Then at the proxy:

```nginx
location / {
    proxy_pass http://127.0.0.1:5690;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Specific traps:

- **Forward-auth in front of Wizarr defeats the entire purpose.** Your invitee has no account on your IdP. Exempt the invite paths, or host Wizarr without forward-auth. This is the most common self-inflicted failure.
- **`X-Forwarded-Proto` missing** makes Wizarr build `http://` links that break on an HTTPS site.
- Binding to `127.0.0.1` keeps the app private; the proxy is the only entrance.

## 3. Invitation codes

Two reported quirks worth knowing:

- **Whitespace in a code.** Invitations whose code contains a space have been impossible to delete in some versions (fixed in later releases). If you have a stuck invitation, check for a stray space, and upgrade.
- **Codes are case-sensitive** in some versions. Copy and paste rather than typing.

Generate codes from the admin UI and share the full link rather than the code alone — it removes transcription errors entirely.

## 4. User created on Jellyfin but can't log in

The invite worked; the account configuration didn't.

- **No library access.** Wizarr applies the libraries selected on the invitation. An invitation with none selected creates a user who sees an empty server. Check **Jellyfin → Dashboard → Users → (the user) → Access**.
- **Password policy.** If your invitee set a password Jellyfin rejects, the creation can partially succeed.
- **A user template.** Wizarr can copy settings from an existing user; if that template user is restricted, so is the new account.

## 5. Nothing in the logs

```bash
docker logs wizarr --tail 100
```

An invite attempt should log the request and the Jellyfin API call. If you see the page load and no API call, the form submission failed client-side — usually the websocket/proxy configuration, or a browser blocking a mixed-content request.

If you see the API call and an error, the message is Jellyfin's and is specific.

## 6. Plex, Emby and Jellyfin behave differently

Wizarr supports several servers, and the invite mechanics differ:

- **Jellyfin / Emby** — Wizarr creates the account directly. Needs an admin API key.
- **Plex** — Wizarr sends a library share invitation to the invitee's existing Plex account. It cannot create Plex accounts, and the invitee must already have one. "The invite doesn't create a user" is correct behaviour for Plex.

Mixing up these models accounts for a fair number of reports. Check which server type the invitation targets.

## What not to do

- **Don't put your invite page behind forward-auth.** Guests can't authenticate to your IdP.
- **Don't share the API key.** It can create and delete users on your media server.
- **Don't expose Wizarr's port directly** alongside the proxy. Bind to localhost.
- **Don't create invitations with no libraries selected.** The account works and sees nothing.

## Prevention

| Habit | Why |
|---|---|
| Verify the Jellyfin API call with one wget after any change | Splits Wizarr from Jellyfin instantly |
| Correct `APP_URL` and `X-Forwarded-Proto` | Working links for the people you invite |
| Default library set on every invitation | Avoids the empty-server experience |
| Expiring, single-use invitations | Limits damage if a link leaks |

## FAQ

**Can it remove users later?**
Yes — Wizarr tracks the accounts it created and can expire them, which is its main ongoing value.

**Does it handle requests (Jellyseerr/Overseerr)?**
It can link to them in the onboarding flow; it doesn't manage them.

**Multiple media servers from one Wizarr?**
Supported in recent versions, each with its own connection.

**The onboarding pages are blank.**
Static assets not reaching the browser — a proxy path or subpath problem. Wizarr expects to be served at the root of its hostname.
