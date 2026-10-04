---
title: "FreshRSS: Can't Enable an Extension, or the API Doesn't Work"
slug: freshrss-extension-api-error
meta_description: "\"Server cannot write in /p/api\", Service Unavailable in reader apps, or Fever clients failing. The write permission and the API access toggle."
updated: October 2026
cluster: round 14 (tech) — FreshRSS/FreshRSS GitHub issues
competition: LOW
---

# FreshRSS: Can't Enable an Extension, or the API Doesn't Work

Two separate problems that are frequently tangled together, because some extensions need the API path writable.

## 1. "Server cannot write in /var/www/FreshRSS/p/api"

Certain extensions write into FreshRSS's `p/api` directory at runtime. If the web server user can't, enabling them fails with that message.

```bash
docker exec -u root freshrss chmod 777 /var/www/FreshRSS/p/api
```

That's the documented quick fix, and it works. Understand the trade-off: `777` makes it world-writable. The narrower version:

```bash
docker exec -u root freshrss chown www-data:www-data /var/www/FreshRSS/p/api
docker exec -u root freshrss chmod 775 /var/www/FreshRSS/p/api
```

For a bare-metal install:

```bash
sudo chown -R www-data:www-data /var/www/FreshRSS/p/api /var/www/FreshRSS/data
sudo chmod 755 /var/www/FreshRSS/p/api
```

The change does not survive container recreation unless you persist it. Either mount that directory:

```yaml
    volumes:
      - ./freshrss-data:/var/www/FreshRSS/data
      - ./freshrss-extensions:/var/www/FreshRSS/extensions
      - ./freshrss-api:/var/www/FreshRSS/p/api
```

or bake the permission into a derived image. Mounting it is cleaner, and it means a new container inherits the right ownership.

## 2. API access must be enabled

Since FreshRSS 1.26.4, extensions using the `api_misc` entrypoint **require API access to be switched on**, or their generated feed URLs return **Service Unavailable**.

```
Administration → Authentication → "Allow API access" → enabled
```

Then set an **API password** per user:

```
Settings → Profile → API password
```

This is separate from your login password and is what reader apps use. A blank API password means every client gets a 401 regardless of the toggle.

## 3. The URL reader apps need

The single most common client-side mistake is adding a path.

| Client type | URL to give it |
|---|---|
| Google Reader API (most apps) | `https://rss.example.com/api/greader.php` |
| Fever API | `https://rss.example.com/api/fever.php` |
| Some apps want the base | `https://rss.example.com` |

Reported specifically: entering `domain.com/api/` when the client expects `domain.com` fails. There is no universal answer — it depends on whether the app appends the path itself. Try the base URL first; if that fails, the full endpoint.

Verify the endpoint exists before blaming the app:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://rss.example.com/api/greader.php
curl -s https://rss.example.com/api/fever.php | head -c 200
```

A 200 or a JSON error from `fever.php` means the API is reachable. A 404 means the path is wrong; a login page means a proxy is in the way (section 4).

Test authentication end to end:

```bash
curl -s -d 'Email=youruser&Passwd=yourapipassword' \
  'https://rss.example.com/api/greader.php/accounts/ClientLogin'
```

A response containing `Auth=` is success. Anything else and the credentials or the toggle are wrong.

## 4. Reverse proxy problems

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
    proxy_pass_header Authorization;
}
```

- **Forward-auth (Authelia, authentik) in front of FreshRSS breaks every reader app.** They can't complete an interactive login. Exempt `/api/` — the API password is the credential for that path.
- **The `Authorization` header must survive.** Many proxy configurations strip it; the Fever API in particular depends on it, and the symptom is a 401 with correct credentials.
- Reported case: the API unreachable from an external network behind nginx while working locally — that's this, or `Host` not being forwarded.

Also set the base URL so FreshRSS generates correct links:

```php
// data/config.php
'base_url' => 'https://rss.example.com',
```

## 5. Extension-specific notes

- **The Fever API is now in FreshRSS core.** The old standalone `freshrss-fever-api` plugin is obsolete; having it installed alongside a modern FreshRSS is a conflict, not a feature. Remove it.
- **FlareSolverr-type extensions** need outbound access from the container to the solver, and the solver's URL set in the extension's configuration.
- Extensions live in `extensions/` and need a correctly-named directory (the extension's own name, as in its `metadata.json`). A wrongly-named folder simply doesn't appear in the list.

```bash
docker exec freshrss ls -la /var/www/FreshRSS/extensions/
docker exec freshrss cat /var/www/FreshRSS/extensions/xExtension-Foo/metadata.json
```

## What not to do

- **Don't put forward-auth in front of `/api/`.** No reader app can authenticate through it.
- **Don't leave `p/api` at 777 permanently** if the instance is public. Narrow it and persist it properly.
- **Don't install the old Fever plugin** on a current FreshRSS.
- **Don't use your login password in a reader app.** Set the API password.

## Prevention

| Habit | Why |
|---|---|
| `p/api` and `extensions/` on mounted volumes | Permissions and extensions survive container updates |
| API access enabled and API password set at install | Prerequisite for every reader app |
| `/api/` exempted from auth layers, documented | The one path that must stay reachable |
| Test with `ClientLogin` via curl after changes | Unambiguous, and faster than reconfiguring an app |

## FAQ

**Which reader apps work?**
Anything supporting the Google Reader API — several iOS and Android readers, plus desktop clients. Fever support is broader but older and read-only in places.

**Can I use the API without exposing FreshRSS publicly?**
Over a VPN, yes. Reader apps need network reachability, not public DNS.

**Feeds update in the browser but not in the app.**
The refresh cron must be running; the API serves what's in the database.

**Does the API support marking read both ways?**
Yes with the Google Reader API; Fever is more limited.
