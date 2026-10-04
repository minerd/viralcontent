---
title: "Baïkal CalDAV Not Working on iOS: The .well-known Redirect"
slug: baikal-caldav-ios-not-syncing
meta_description: "iOS refuses the account or finds no calendars while the same URL works elsewhere. The well-known redirect, the exact path, and the HTTPS requirement."
updated: October 2026
cluster: round 13 (tech) — Baïkal GitHub issues and sabre/dav docs
competition: LOW
---

# Baïkal CalDAV Not Working on iOS: The `.well-known` Redirect

iOS's CalDAV client does service discovery differently from Thunderbird or DAVx⁵. It expects `/.well-known/caldav` to redirect it to the real endpoint. If your web server doesn't serve that redirect, iOS reports "cannot connect" or adds the account and finds zero calendars — while every other client works fine with the same URL.

That asymmetry is the diagnostic: **works everywhere except iOS = discovery, not credentials.**

## 1. Add the well-known redirects

Baïkal's documented endpoints are under `/dav.php`. iOS looks at the domain root.

**nginx:**

```nginx
location = /.well-known/caldav {
    return 301 $scheme://$host/dav.php/;
}
location = /.well-known/carddav {
    return 301 $scheme://$host/dav.php/;
}
```

**Apache:**

```apache
Redirect 301 /.well-known/caldav /dav.php/
Redirect 301 /.well-known/carddav /dav.php/
```

Use **301**, and keep the trailing slash on `/dav.php/`. A 302 works in most clients but 301 is what the specification expects and what iOS handles most reliably. Omitting the trailing slash causes an extra redirect hop that some iOS versions abandon.

Verify from outside:

```bash
curl -sI https://dav.example.com/.well-known/caldav | head -5
```

You want `HTTP/2 301` and a `location:` header pointing at `/dav.php/`.

## 2. Don't let the redirect strip credentials

A subtle one: if your redirect sends the client from HTTPS to HTTP, or across hostnames, iOS drops the `Authorization` header and you get a loop of 401s. Keep the scheme and host identical — which is what `$scheme://$host` above does, and why hardcoding a URL there is a mistake.

## 3. The account settings iOS actually needs

On the device: **Settings → Calendar → Accounts → Add Account → Other → Add CalDAV Account**, then use **Advanced Settings**:

| Field | Value |
|---|---|
| Server | `dav.example.com` (hostname only, no path) |
| User Name | the Baïkal username |
| Password | the Baïkal password |
| Use SSL | **on** |
| Port | 443 |
| Account URL | `https://dav.example.com/dav.php/principals/USERNAME/` |

Filling **Account URL** explicitly bypasses discovery entirely, which is the reliable fallback if you can't change the web server config. Note the `principals/USERNAME/` path with its trailing slash — the calendar-home path (`calendars/USERNAME/`) also works in some versions but principals is the correct discovery root.

**SSL is effectively mandatory.** iOS will refuse a plain-HTTP CalDAV account outright in current versions, and a self-signed certificate must be installed and *trusted* in Settings → General → About → Certificate Trust Settings. Installing a profile is not enough; the trust toggle is a separate step people miss.

## 4. Baïkal-side checks

```bash
curl -s -u user:pass -X PROPFIND \
  -H 'Depth: 0' \
  https://dav.example.com/dav.php/principals/user/ | head -20
```

An XML multistatus response means Baïkal is serving DAV correctly and the problem is client-side. A 401 means credentials; a 404 means the path; a 500 means check Baïkal's own log and PHP error log.

Specific Baïkal issues worth ruling out:

- **`WEBDAV` methods blocked by the web server.** Some hardened configs allow only GET/POST/HEAD. CalDAV needs `PROPFIND`, `REPORT`, `MKCALENDAR`, `PROPPATCH`. A `limit_except` or ModSecurity rule blocking them gives 405s.
- **PHP `Authorization` header not reaching PHP** (FastCGI). Classic symptom: works with a password in the URL, 401 otherwise. Fix:

```apache
CGIPassAuth On
```

or for nginx/php-fpm, ensure `fastcgi_param HTTP_AUTHORIZATION $http_authorization;` is present.

- **The `Specific/` directory not writable.** Baïkal's config and SQLite database live there; a read-only mount lets reads work and writes fail, so calendars appear but events don't save.

## What not to do

- **Don't put `/dav.php/` in the iOS "Server" field.** That field is a hostname. The path goes in Account URL.
- **Don't use a self-signed certificate without trusting it on the device.** The failure is indistinguishable from a wrong password.
- **Don't redirect `/.well-known/caldav` to the Baïkal web admin.** It must point at the DAV endpoint; the admin UI returns HTML and iOS gives up.
- **Don't test with one client only.** Trying DAVx⁵ or Thunderbird takes two minutes and tells you whether the server or the client is at fault.

## Prevention

| Habit | Why |
|---|---|
| Add both `.well-known` redirects at install time | Every Apple device and several others depend on them |
| Real certificate (Let's Encrypt) | Removes an entire category of opaque iOS failures |
| Keep `Specific/` on a writable volume and back it up | It holds all your calendar data |
| Test with a second client before debugging the first | Splits server from client immediately |

## FAQ

**Does macOS behave the same as iOS?**
Yes — same discovery expectations, same well-known requirement.

**Can I use one account for calendars and contacts?**
They're separate accounts on iOS (CalDAV and CardDAV), both against the same server and credentials.

**Events sync but reminders/alarms don't.**
iOS handles `VALARM` locally per device; alarms set on another client may not transfer. That's client behaviour, not Baïkal.

**Is Radicale easier for iOS?**
It has the same well-known requirement. The redirect is a web-server concern either way.
