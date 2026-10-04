---
title: "Authelia Redirect Loop: The Cookie Domain and Header Chain"
slug: authelia-redirect-loop
meta_description: "Logging in bounces you back to the login page forever. The session domain rule, the forwarded headers your proxy must send, and the HTTPS requirement."
updated: October 2026
cluster: round 13 (tech) — Authelia GitHub discussions
competition: LOW
---

# Authelia Redirect Loop: The Cookie Domain and Header Chain

You log in, Authelia accepts the password, redirects you to the app, and the app sends you straight back to the login page. Forever.

There are four causes and they're all configuration, not bugs. One of them — the cookie domain rule — accounts for most of it.

## 1. The session cookie domain rule

Authelia's session cookie must be readable by both Authelia and the protected app. That requires them to share a parent domain, and Authelia enforces a specific relationship:

```yaml
session:
  cookies:
    - name: authelia_session
      domain: example.com
      authelia_url: https://auth.example.com
      default_redirection_url: https://www.example.com
```

The rules:

- **`domain` must be the parent of `authelia_url`'s host.** Authelia at `auth.example.com` with `domain: example.com` is correct. `domain: auth.example.com` means the cookie is scoped to Authelia alone and no app can see it — instant loop.
- **The protected app must be under `domain` too.** `app.example.com` works. `app.other.com` cannot, ever — browsers won't send a cookie across registrable domains. Protecting apps on two different domains needs two cookie entries.
- **No leading dot.** `.example.com` is the old syntax and current versions reject or mis-handle it.
- **Not a public suffix.** `domain: com` is refused.

If you're looping, check this block first. It's a thirty-second check and the most likely answer.

## 2. HTTPS and `secure` cookies

Authelia sets the session cookie with `Secure`, so **the browser will not store it over plain HTTP**. Accessing anything by `http://` or by IP address produces a permanent loop with no error message anywhere.

This includes:

- Testing by IP (`http://192.168.1.10:9091`) — won't work, by design
- A proxy terminating TLS but passing `X-Forwarded-Proto: http` — Authelia builds `http` redirect URLs and loops

Run everything on HTTPS with real names from the start. Self-signed is fine for a lab; plain HTTP is not.

## 3. The forwarded headers

Authelia's forward-auth needs to know the original request. Missing headers mean it redirects to the wrong place or can't evaluate rules.

**Traefik** (the standard middleware):

```yaml
http:
  middlewares:
    authelia:
      forwardAuth:
        address: "http://authelia:9091/api/authz/forward-auth"
        trustForwardHeader: true
        authResponseHeaders:
          - "Remote-User"
          - "Remote-Groups"
          - "Remote-Email"
          - "Remote-Name"
```

**nginx**:

```nginx
location /internal/authelia/authz {
    internal;
    proxy_pass http://authelia:9091/api/authz/auth-request;
    proxy_set_header X-Original-Method $request_method;
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
    proxy_set_header Content-Length "";
    proxy_pass_request_body off;
}
```

The crucial one is `X-Original-URL` (nginx) or `trustForwardHeader` with Traefik's own `X-Forwarded-*`. Without it Authelia doesn't know where to send you back to, and the `rd` parameter in the redirect is missing or wrong — which produces the loop.

Also note the endpoint difference: `/api/authz/forward-auth` for Traefik/Caddy, `/api/authz/auth-request` for nginx, `/api/authz/ext-authz` for Envoy. Using the wrong one for your proxy gives a 401 or a loop depending on the version. Old guides use `/api/verify`, which is deprecated.

## 4. Access control rules

A rule that matches nothing, or a `deny` ahead of your `one_factor`, produces a loop because Authelia authenticates you and then refuses the resource:

```yaml
access_control:
  default_policy: deny
  rules:
    - domain: "auth.example.com"
      policy: bypass
    - domain: "app.example.com"
      policy: one_factor
```

**The `bypass` rule for Authelia's own domain is required.** Without it, Authelia protects its own login page and you loop immediately. This is the second most common cause after the cookie domain.

Rules are evaluated top to bottom, first match wins — a broad `domain: "*.example.com"` rule above a specific one makes the specific one dead code.

## Reading the evidence

```bash
docker logs authelia --tail 50
```

Useful lines mention the session, the requested URL and the policy applied. Also check the browser: open devtools → Application → Cookies and see whether `authelia_session` exists and on what domain. An absent cookie points at sections 1–2; a present cookie with a loop points at sections 3–4.

## What not to do

- **Don't set `domain` to the Authelia subdomain.** It's the single most common mistake and produces exactly this symptom.
- **Don't test over HTTP.** You'll conclude Authelia is broken when it's enforcing cookie security.
- **Don't copy a config from a guide written for an older major version.** The `session.domain` → `session.cookies[]` restructure and the authz endpoint changes both break silently.
- **Don't protect Authelia itself.** Bypass its domain.

## Prevention

| Habit | Why |
|---|---|
| One parent domain for everything behind Authelia | Removes the cross-domain cookie problem entirely |
| HTTPS with real names from day one | Avoids a whole class of invisible failures |
| Keep the `bypass` rule first in access_control | Prevents the self-protection loop |
| Pin the Authelia version and read release notes | Config schema changes between majors |

## FAQ

**Can I protect apps on two unrelated domains?**
Yes — add a second entry under `session.cookies` with its own `domain` and `authelia_url` on that domain. One Authelia, two cookie scopes.

**Login works but the app says unauthorised.**
Then Authelia is fine and the app isn't reading the `Remote-User` header. Check `authResponseHeaders` and whether the app expects a different header name.

**2FA page loops but password page doesn't.**
Usually a storage problem — the TOTP secret can't be written. Check the SQLite/Postgres storage backend and its permissions.

**Does it work with Cloudflare proxy?**
Yes, but ensure the real client IP reaches Authelia (`X-Forwarded-For` trust) or rate-limiting and logs will all show Cloudflare's IPs.
