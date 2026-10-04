---
title: "Authentik Login Loop After an Upgrade? Cookies, Flows and the Proxy Provider"
slug: authentik-login-loop-after-upgrade
meta_description: "You log into authentik and land back at the login page, or the dashboard loads with no permissions. Cookie domain, flow changes, outpost version skew and how to recover."
updated: October 2026
cluster: round 10 (tech) — goauthentik GitHub issues only
competition: LOW
---

# Authentik Login Loop After an Upgrade? Cookies, Flows and the Proxy Provider

You upgrade authentik, sign in — and it bounces you straight back to the login page. Or the dashboard loads but every API call is forbidden. Being locked out of your own identity provider is a bad afternoon, so work in a fixed order.

## 0. Get yourself a way back in

Before experimenting: authentik ships a **recovery flow** you can reach with a one-time URL generated from the server. From the container:

```
docker compose run --rm server create_recovery_key 1 akadmin
```

That prints a URL valid for a limited time. Keep it in the terminal scrollback. If your only admin account is behind a broken MFA stage, this is the route back.

## 1. Clear cookies — properly

Stale session cookies cause a large share of these loops, including the known case where an **HTTPS session followed by an HTTP connection** produces a login loop.

- Clear cookies **for the authentik domain and the application's domain**
- Test in a **private window**, which is faster and non-destructive
- If private browsing works and your normal window doesn't, it's cookies and nothing else

## 2. Check you're consistently on HTTPS

Mixed HTTP/HTTPS is a direct cause. The session cookie is set `Secure` and then isn't sent back over plain HTTP, so the server never sees you as authenticated:

- Reach authentik **only over HTTPS**, including on the LAN
- Behind a reverse proxy, forward `X-Forwarded-Proto: https` — without it authentik generates `http://` redirects and loops
- No mixed-scheme redirects anywhere in the chain

## 3. Permissions after upgrade (dashboard loads, API forbidden)

The reported 2024.4-era failure: login succeeds, you reach the dashboard, and the API returns **forbidden** because the user has no authorisations. That's a **permissions model migration**, not a credential problem.

- Check the user's **group membership** and that the group still carries admin permissions
- Newer versions moved to finer-grained **RBAC**; permissions that were implicit can need granting explicitly
- Use the recovery key to get in as `akadmin` and inspect the groups
- Read the release notes for the version you jumped to — breaking permission changes are called out there

## 4. Flows and stages changed under you

Upgrades add and modify default flows and stage behaviour, and loops appear at the point where a stage can't complete:

- **Authentication flow** bound to the brand/tenant — is it still the one you expect?
- **WebAuthn / passkey** validation: a reported 2025.6-era regression made passkeys fail with repeated resubmission. If passkeys loop, test a password-only flow
- A **sign-in loop upon changing flows** is a known shape — revert the flow binding, then change it deliberately
- Check **Events → Logs** in the admin UI: each failed attempt is recorded with the stage it died at. This is the single most useful screen and most people never open it

## 5. Proxy provider / outpost loops

If the loop is on a **protected application** rather than on authentik itself:

- **Outpost version must match the core version.** Version skew after an upgrade is a classic reload loop. Embedded outposts update with the server; standalone ones you must update yourself
- Check the outpost shows **healthy** and its last seen time in the admin UI
- The proxy provider's **external host** must match exactly what the browser uses, scheme included
- Forward-auth setups need the right headers from nginx/Traefik; a missing `X-Forwarded-Host` produces a redirect loop
- Cookie **domain scope** — a provider issuing a cookie for a different domain than the app runs on will loop forever

## 6. Infrastructure

- **PostgreSQL migrations** that didn't finish: check `docker compose logs worker` and `server` for migration errors at startup. An interrupted migration leaves a half-upgraded schema
- **Redis** unreachable → sessions can't be stored → every login looks like it failed
- **Clock skew** between containers breaks token validation
- Both **server and worker** must be on the **same version**

## Recovery order

1. Private window / clear cookies
2. **Events → Logs** — find the stage that fails
3. Confirm HTTPS end to end and `X-Forwarded-Proto`
4. `docker compose logs server worker` — migrations, Redis, version mismatch
5. Recovery key → check groups and permissions
6. Update outposts to match the core version
7. Roll back to the previous image tag if you're stuck, then upgrade again after reading the notes

## FAQ

**Why do I get in but have no permissions?**
A permissions/RBAC migration. Check group membership and grants for your user.

**My passkey loops but my password works.**
That points at the WebAuthn validation stage — test it, and check the release notes for your version.

**Protected apps loop but authentik itself is fine.**
Outpost version skew or proxy headers. Those are the two.

**Is rolling back safe?**
Database migrations are not always reversible, so take a database backup before any upgrade — that's what makes rollback an option at all.
