---
title: "ZITADEL: redirect_uri Mismatch or No Redirect After Login"
slug: zitadel-redirect-uri-mismatch
meta_description: "Login succeeds and nothing redirects, or the URI is rejected. The default redirect URI nobody sets, localhost validation and the IDP callback path."
updated: October 2026
cluster: round 14 (tech) — zitadel/zitadel GitHub issues
competition: LOW
---

# ZITADEL: redirect_uri Mismatch or No Redirect After Login

Four distinct problems. Match the symptom first, because the fixes don't overlap.

| Symptom | Section |
|---|---|
| "The requested redirect_uri is missing in the client configuration" | 1 |
| Login succeeds, lands on a static success page, no redirect | 2 |
| `redirect_uri_mismatch` during external IdP login | 3 |
| `http://localhost` rejected as invalid in the console | 4 |

## 1. The URI must be registered exactly

```
Console → Project → Application → Redirect Settings
```

The matching is exact string comparison, with the usual OAuth strictness:

- **Scheme, host, port and path must all match**, including a trailing slash or its absence
- `https://app.example.com/oidc_callback` and `https://app.example.com/oidc_callback/` are different
- A wildcard is not accepted in production mode

```
Redirect URIs:
  https://app.example.com/oidc_callback
Post Logout URIs:
  https://app.example.com/
```

Find what your application is actually sending — don't guess:

```bash
# in the browser, copy the authorize URL and decode it
python3 -c "
import urllib.parse,sys
q=urllib.parse.urlparse(sys.argv[1]).query
print(urllib.parse.parse_qs(q).get('redirect_uri'))
" 'https://auth.example.com/oauth/v2/authorize?...'
```

Paste that string verbatim into ZITADEL. Most mismatches are a trailing slash or `http` versus `https` behind a proxy that doesn't send `X-Forwarded-Proto`.

## 2. Login succeeds, no redirect: the default redirect URI

This is the one that reads as a bug and is a missing setting.

Documented behaviour: **ZITADEL's `defaultRedirectUri` in the login policy is not set by default.** After certain flows — password initialisation, email verification, or any time the auth request context is lost — ZITADEL shows a **static success page** rather than returning the user to your application.

So the user logs in, sees "you have successfully logged in", and stops. No redirect, no error.

Set it:

```bash
curl -s -X PUT 'https://auth.example.com/admin/v1/policies/login' \
  -H "Authorization: Bearer $PAT" \
  -H 'Content-Type: application/json' \
  -d '{
    "allowUsernamePassword": true,
    "allowRegister": false,
    "allowExternalIdp": true,
    "defaultRedirectUri": "https://app.example.com/"
  }'
```

Or in the console: **Settings → Login Behaviour and Security → Default Redirect URI**.

The same setting governs what happens when a user navigates to the login page **directly**, outside any OIDC flow — without it they authenticate into a dead end.

## 3. IdP callback URI wrong (missing slash)

A documented bug worth knowing if you use an external identity provider with the new login UI and a custom base URI: the generated callback URL came out as

```
https://auth.example.com/ui/v2/loginidps/callback
```

instead of

```
https://auth.example.com/ui/v2/login/idps/callback
```

— a missing slash — and the external IdP then rejects the request with `redirect_uri_mismatch`.

The console **displays** the incorrect URI, so copying it into your IdP propagates the error. Check the string character by character and register the correct form at the IdP. If your version produces the broken URL in the actual request (not just the display), upgrading is the fix; there's nothing to configure around it.

## 4. `http://localhost` rejected in the console

Reported: the console's redirect-URI validation flags `http://localhost` as invalid, even though the OAuth specification permits loopback over plain HTTP for native applications.

Workarounds:

- **Set the application to Development mode.** ZITADEL relaxes URI validation for applications marked as development, which is the intended mechanism:

```
Console → Application → Configuration → Development Mode: on
```

- Use `http://127.0.0.1:PORT/callback` instead of `localhost`, which some validators accept where `localhost` is rejected.
- For a native app, follow the loopback-with-ephemeral-port pattern and register `http://127.0.0.1/callback` without a port — specification-compliant clients vary the port.

Do not leave Development mode on for a production application; it also loosens other checks.

## 5. Behind a reverse proxy

Most "mismatch" problems on self-hosted ZITADEL trace back to the proxy:

```nginx
location / {
    grpc_pass grpc://zitadel:8080;      # ZITADEL uses gRPC-Web + HTTP
}
```

or for the HTTP/2 path:

```nginx
location / {
    proxy_pass http://zitadel:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

```yaml
# zitadel config
ExternalDomain: auth.example.com
ExternalPort: 443
ExternalSecure: true
```

`ExternalSecure: true` with `ExternalDomain` and `ExternalPort` set correctly is what makes ZITADEL build `https://` URLs. Get this wrong and every generated URI — including the IdP callback — is wrong, which looks like section 3.

ZITADEL needs **HTTP/2** end to end for its gRPC APIs. A proxy that downgrades to HTTP/1.1 breaks the console in ways that look unrelated to redirects.

## 6. Console always redirects to the wrong place

A reported case: the console login redirecting to the **instance-level** `defaultRedirectUri` rather than respecting the ZITADEL organisation's or the default organisation's policy. If you set an instance default for your application, the console inherits it.

Keep the instance default pointed at something sensible and neutral (your portal, or ZITADEL's own console), and set application-specific behaviour on the applications.

## What not to do

- **Don't leave Development mode on in production.** It relaxes validation you want.
- **Don't copy the IdP callback URI from the console without checking it.** Section 3.
- **Don't omit `X-Forwarded-Proto`.** Every generated URL depends on it.
- **Don't register a wildcard redirect URI.** It's an open redirector.

## Prevention

| Habit | Why |
|---|---|
| `defaultRedirectUri` set at install time | Removes the dead-end success page |
| `ExternalDomain`/`ExternalSecure` verified after any proxy change | Determines every URI ZITADEL builds |
| Decode the actual `redirect_uri` from the request before editing config | Stops guessing |
| HTTP/2 through the proxy | Required for the gRPC APIs |

## FAQ

**Can one application have several redirect URIs?**
Yes — list them all; the request must match one exactly.

**Why does my mobile app need a custom scheme?**
Native apps use `myapp://callback` or a loopback address. Register exactly what the SDK sends.

**Logout doesn't return to my app.**
Post-logout URIs are a separate list. Register them too.

**Emails link to the wrong host.**
Same `ExternalDomain` setting; notification templates build URLs from it.
