---
title: "Outline: OIDC Authentication Failed on a Self-Hosted Install"
slug: outline-oidc-login-failed
meta_description: "\"State not return in OAuth flow\", failed to obtain access token, or the provider button missing entirely. Clock skew, scopes and Docker DNS."
updated: October 2026
cluster: round 14 (tech) — outline/outline GitHub discussions
competition: LOW
---

# Outline: OIDC Authentication Failed on a Self-Hosted Install

The error text maps to the cause more cleanly than usual:

| Error | Cause |
|---|---|
| Custom provider button not shown at all | Required env vars missing — section 1 |
| `InternalOAuthError: Failed to obtain access token` | Outline can't reach the IdP — section 2 |
| `State not return in OAuth flow` | Clock skew or cookie problem — section 3 |
| `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | Self-signed IdP certificate — section 4 |
| Authentication callback error, no detail | Missing email scope — section 5 |

## 1. No provider button on the login page

Outline shows a provider only when **every** variable for it is set. Missing one gives no button and no error:

```env
OIDC_CLIENT_ID=outline
OIDC_CLIENT_SECRET=...
OIDC_AUTH_URI=https://auth.example.com/api/oidc/authorization
OIDC_TOKEN_URI=https://auth.example.com/api/oidc/token
OIDC_USERINFO_URI=https://auth.example.com/api/oidc/userinfo
OIDC_LOGOUT_URI=https://auth.example.com/logout
OIDC_USERNAME_CLAIM=preferred_username
OIDC_DISPLAY_NAME=Authelia
OIDC_SCOPES="openid profile email"
```

Check what the container has:

```bash
docker exec outline env | grep OIDC
```

An empty value counts as missing. Note these are the **full endpoint URLs**, not a discovery document URL — Outline does not fetch `.well-known/openid-configuration` to populate them.

## 2. Failed to obtain access token

Outline's **server** calls the token endpoint. It must be able to resolve and reach that hostname from inside the container:

```bash
docker exec outline wget -qO- --timeout=5 https://auth.example.com/api/oidc/token
```

The reported cause in practice is Docker DNS: the external hostname resolves to your public IP, your router doesn't hairpin, and the container times out. Two fixes:

- Use the IdP's **internal** address for `OIDC_TOKEN_URI` and `OIDC_USERINFO_URI`, keeping the external one for `OIDC_AUTH_URI` (which the browser uses). This is correct and commonly needed.
- Or add a hosts entry so the container resolves the public name internally:

```yaml
    extra_hosts:
      - "auth.example.com:192.168.1.10"
```

The distinction matters: `AUTH_URI` is for the browser; `TOKEN_URI` and `USERINFO_URI` are for the server. They can legitimately differ.

## 3. "State not return in OAuth flow"

OAuth state is carried in a short-lived cookie. This error means the cookie wasn't there on return. Causes, in order of likelihood:

- **Clock skew.** If the Outline container's clock is ahead, the cookie it sets expires immediately in the browser's view. Check:

```bash
docker exec outline date; date
```

Fix the host's NTP; containers inherit the host clock.

- **`URL` env var wrong.** Outline builds the callback and the cookie domain from it:

```env
URL=https://docs.example.com
FORCE_HTTPS=true
```

No trailing slash, and it must be exactly what users type. A mismatch between `URL` and the browser's address means the cookie is set on one domain and read on another.

- **`FORCE_HTTPS=true` behind a proxy that doesn't send `X-Forwarded-Proto`.** Outline then redirects to `http://`, the cookie (Secure) isn't sent, and state is lost:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Host $host;
```

- **Cookies blocked** by a strict browser setting or an ad blocker on the auth domain.

## 4. Self-signed IdP certificate

```env
NODE_TLS_REJECT_UNAUTHORIZED=0
```

Works, and disables verification for all of Outline's outbound TLS. Better: mount your CA and point Node at it:

```yaml
    volumes:
      - ./ca.crt:/usr/local/share/ca-certificates/internal.crt:ro
    environment:
      - NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/internal.crt
```

## 5. Missing email scope, and changed emails

Outline keys users on **email**. Consequences:

- `OIDC_SCOPES` must include `email`, and the IdP must actually return it. Without it the callback errors with little detail.
- **Changing a user's email in the IdP breaks their login** — Outline sees a new identity and either creates a duplicate user or refuses, depending on version. There is no in-app merge; fix it in the database or recreate the user and transfer documents.

That second point is worth planning around: pick a stable email per user before onboarding anyone.

## 6. Infinite logout loop

Reported pattern: authentication succeeds, then Outline bounces the user back to login repeatedly. Usually `URL`/cookie-domain mismatch (section 3) or a proxy stripping `Set-Cookie`. Check the browser's devtools → Application → Cookies for `accessToken` on your domain; if it isn't there, the proxy is the suspect.

## What not to do

- **Don't set `NODE_TLS_REJECT_UNAUTHORIZED=0` as a first move.** Confirm it's a certificate problem.
- **Don't put a discovery URL in `OIDC_AUTH_URI`.** Outline wants the explicit endpoints.
- **Don't change user emails in the IdP after onboarding.** It orphans their Outline account.
- **Don't debug without reading the container log.** The useful error is there, not in the browser.

## Prevention

| Habit | Why |
|---|---|
| Internal URLs for token/userinfo, external for auth | Removes the hairpin-DNS class |
| NTP on the host, verified | Clock skew causes the most confusing error here |
| `X-Forwarded-Proto` set at the proxy | Required for the Secure cookie to work |
| Stable per-user email in the IdP | Email is Outline's primary key |

## FAQ

**Can I have local accounts as a fallback?**
Outline is SSO-only in self-hosted mode (email magic links aside). Keep your IdP's own break-glass account working.

**Multiple providers at once?**
Yes — Google, Slack, Azure and generic OIDC can coexist; each adds a button.

**Users land in the wrong team.**
Outline self-hosted is single-team; the team is created on first login. A second "team" means a second deployment.

**How do I make someone an admin?**
First user is admin. After that, promote from Settings → Members.
