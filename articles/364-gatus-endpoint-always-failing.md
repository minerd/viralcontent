---
title: "Gatus: An Endpoint That Is Always Failing"
slug: gatus-endpoint-always-failing
meta_description: "A monitor shows red constantly while the service is fine. Conditions assert the wrong thing — here's how to write ones that mean something."
updated: October 2026
cluster: round 14 (tech) — TwiN/gatus GitHub issues
competition: LOW
---

# Gatus: An Endpoint That Is Always Failing

A permanently-red Gatus endpoint is usually not an outage. It is a **condition asserting something that will never be true**. Gatus requires at least one condition per endpoint, and the default most people copy asserts a 200.

## 1. Find out what the endpoint actually returns

```bash
curl -s -o /dev/null -w 'status=%{http_code} time=%{time_total}\n' https://app.example.com
```

Then write the condition to match reality:

```yaml
endpoints:
  - name: app
    url: https://app.example.com
    interval: 60s
    conditions:
      - "[STATUS] == 200"
```

The cases where 200 is the wrong assertion:

| Reality | Correct condition |
|---|---|
| Behind forward-auth (Authelia, authentik) | `[STATUS] == 401` |
| Behind basic auth | `[STATUS] == 401` |
| Redirects to a login page | `[STATUS] == 302` or `any(200, 302)` |
| An API that needs a key | `[STATUS] == 401`, or supply the key |

Asserting 401 on an auth-protected route is not a cop-out: it proves the route resolves, the proxy is up, and the auth layer is enforcing. That is exactly what you want to know.

```yaml
    conditions:
      - "[STATUS] == 401"
      - "[RESPONSE_TIME] < 500"
```

## 2. Redirects

Gatus does not follow redirects by default in all versions. An endpoint that 301s to HTTPS will fail a `== 200` check:

```yaml
  - name: app
    url: https://app.example.com
    client:
      follow-redirects: true
    conditions:
      - "[STATUS] == 200"
```

Or point the monitor at the final URL and keep redirects off, which is cleaner — you learn when the redirect target breaks.

## 3. Body conditions

```yaml
    conditions:
      - "[STATUS] == 200"
      - "[BODY].status == UP"
      - "[BODY].version != "
```

Things that go wrong:

- **The body isn't JSON.** `[BODY].field` on an HTML page never matches. Use `[BODY]` with `pat(...)` for text:

```yaml
      - "[BODY] == pat(*Welcome*)"
```

- **The path is wrong.** JSON paths are dot-separated with `[n]` for arrays: `[BODY].data[0].name`.
- **Gzip or chunked responses** can confuse body matching on some versions; test with `curl` and the same headers Gatus sends.

## 4. Headers and TLS

```yaml
    client:
      timeout: 10s
      insecure: true          # self-signed internal certs
    headers:
      Authorization: Bearer my-token
      User-Agent: gatus
```

Two notes:

- **Headers have not been sent correctly in every version.** If an authenticated check fails while the same request works with curl, test by moving the token into the URL as a query parameter (where the API supports it) to confirm the header is the variable.
- **`insecure: true`** is needed for self-signed certs. Without it you get a TLS error that reads like a connection failure.

For certificate expiry monitoring:

```yaml
    conditions:
      - "[CERTIFICATE_EXPIRATION] > 240h"
```

## 5. Gatus won't start at all

A real behaviour worth knowing: in some versions, **a failure while setting up one endpoint aborted startup**, so a single bad entry took the whole service down rather than showing one red tile.

```bash
docker logs gatus --tail 50
```

The log names the offending endpoint. Also common at startup:

- **DNS resolution of an endpoint hostname fails** inside the container
- **A storage path that isn't writable** (`storage.path` for SQLite)
- **A malformed condition** — an unparseable condition is a config error, not a failing check

```yaml
storage:
  type: sqlite
  path: /data/data.db
```

Mount `/data` and make sure it's writable by the container's user.

## 6. Alerts firing or not firing

```yaml
    alerts:
      - type: ntfy
        failure-threshold: 3
        success-threshold: 2
        send-on-resolved: true
alerting:
  ntfy:
    url: https://ntfy.example.com
    topic: alerts
```

`failure-threshold: 1` with a 30-second interval generates noise on every blip. Three consecutive failures at a 60-second interval is a reasonable default. `send-on-resolved` is off by default and is usually what you want on.

## What not to do

- **Don't assert 200 on something that returns 401.** You're monitoring the wrong thing and training yourself to ignore red.
- **Don't monitor at 10-second intervals.** You're adding load and catching noise.
- **Don't use `insecure: true` for public endpoints.** Certificate validity is part of what you're checking.
- **Don't leave one bad endpoint in the config** assuming it's isolated. It may take startup with it.

## Prevention

| Habit | Why |
|---|---|
| Write the condition from a `curl` of the real endpoint | Eliminates the entire false-red class |
| `[RESPONSE_TIME]` alongside `[STATUS]` | Catches degradation, not just outages |
| `failure-threshold: 3` as a default | Alerts you believe |
| Validate config changes against the log | A bad endpoint can stop startup |

## FAQ

**Can it check TCP or DNS, not just HTTP?**
Yes — `url: tcp://host:port`, `dns://`, `icmp://` and more, each with their own placeholders.

**How do I monitor something behind auth properly?**
Supply a token and assert 200 on a real endpoint. That's strictly better than asserting 401, when you can.

**Does it store history?**
In the configured storage backend. With `type: memory` it resets on restart.

**Group endpoints?**
`group:` on each endpoint; the dashboard sections by it.
