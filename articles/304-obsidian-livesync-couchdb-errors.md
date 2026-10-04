---
title: "Obsidian LiveSync CouchDB Errors: CORS, chunk size and the 'database locked' loop"
slug: obsidian-livesync-couchdb-errors
meta_description: "Self-hosted LiveSync failing with CORS errors, 413s, or endless conflicts. The CouchDB settings the plugin requires and the ones it can't fix for you."
updated: October 2026
cluster: round 13 (tech) — obsidian-livesync GitHub issues
competition: LOW
---

# Obsidian LiveSync CouchDB Errors: CORS, Chunk Size and the Conflict Loop

Self-hosted LiveSync fails in three recognisable ways. The plugin's own "Check database configuration" button fixes one of them; the other two are outside its reach.

## 1. Run the built-in check first

In the plugin: **🛠️ Hatch → Check database configuration**. It inspects CouchDB and offers to fix what it can. Do this before anything else; it sets:

- `chttpd/require_valid_user = true`
- `chttpd_auth/require_valid_user = true`
- `httpd/WWW-Authenticate = Basic realm="couchdb"`
- `chttpd/enable_cors = true`
- `cors/credentials = true`
- `cors/origins = app://obsidian.md,capacitor://localhost,http://localhost`

Those `cors/origins` values are not optional and not guessable. `app://obsidian.md` is the desktop app; `capacitor://localhost` is iOS; `http://localhost` is Android. Omit one and that platform alone fails — which is exactly the "works on my laptop, not on my phone" report.

If the check can't apply them (it needs admin credentials), set them by hand:

```bash
curl -X PUT http://admin:password@127.0.0.1:5984/_node/_local/_config/cors/origins \
  -d '"app://obsidian.md,capacitor://localhost,http://localhost"'
curl -X PUT http://admin:password@127.0.0.1:5984/_node/_local/_config/chttpd/enable_cors \
  -d '"true"'
```

## 2. CORS errors that survive the check

If the plugin's check passes but the client still reports a CORS failure, the problem is your **reverse proxy**, not CouchDB. Two specific causes:

**The proxy adds its own CORS headers.** Two `Access-Control-Allow-Origin` headers is invalid and the browser rejects the response. Remove the proxy's CORS block entirely and let CouchDB answer — CouchDB's own CORS handling is what the plugin configures.

**The proxy drops `OPTIONS`.** LiveSync preflights. A proxy rule that only allows GET/POST/PUT breaks sync with a CORS message that has nothing to do with origins.

Test the preflight directly:

```bash
curl -i -X OPTIONS https://couch.example.com/obsidiandb \
  -H 'Origin: app://obsidian.md' \
  -H 'Access-Control-Request-Method: GET'
```

You want a 200 with a single `Access-Control-Allow-Origin: app://obsidian.md`.

## 3. 413 / "Request Entity Too Large"

CouchDB's default `max_http_request_size` is comfortable, but attachments and large chunks can exceed a reverse proxy's 1 MB nginx default.

```nginx
client_max_body_size 64M;
```

On the CouchDB side:

```bash
curl -X PUT http://admin:password@127.0.0.1:5984/_node/_local/_config/chttpd/max_http_request_size \
  -d '"4294967296"'
```

And in the plugin, under **Sync Settings**, reduce the **chunk size**. A smaller chunk size means more, smaller requests — slower but far more tolerant of proxies and flaky mobile connections. If sync works on desktop and 413s on mobile, chunk size is the lever.

## 4. The conflict / "database locked" loop

The nastier failure: sync appears to run forever, the device count climbs, and files keep reappearing.

This usually means **two devices were set up with different plugin settings** — different chunk size, different end-to-end encryption passphrase, or one with E2EE on and one off. LiveSync stores chunks keyed by those settings; mismatched devices write incompatible data into the same database.

The recovery is deliberate and worth doing properly:

1. Pick one device whose vault is known-good. In the plugin: **Hatch → Rebuild everything** (this rewrites the remote database from that device).
2. On every other device, use **Hatch → Fetch from remote** (not rebuild). This discards local sync state and pulls fresh.
3. Confirm all devices show the *same* settings in **Sync Settings** before letting them run.

Doing step 1 on two devices is how people lose notes. Only one device rebuilds.

Also relevant: **`.obsidian` directory sync.** Syncing plugin settings and workspace state between a desktop and a phone generates constant conflicts, because `workspace.json` differs by design. Exclude it:

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.trash/
```

## What not to do

- **Don't put CouchDB behind Cloudflare's proxy for sync.** The request pattern (many small writes, long polls) is exactly what gets rate-limited, and the 100 MB body cap applies too.
- **Don't delete the CouchDB database to fix conflicts** without first confirming a device has the complete vault. The database *is* the merged state.
- **Don't change the E2EE passphrase on one device.** It invalidates every chunk; treat it as a full rebuild.
- **Don't enable LiveSync and another sync tool (Syncthing, iCloud, Dropbox) on the same vault.** Two systems writing the same files produces conflicts nothing can untangle.

## Prevention

| Habit | Why |
|---|---|
| Use the plugin's **setup URI** to copy settings between devices | Eliminates the mismatched-settings class entirely |
| Keep a plain file-level backup of the vault | CouchDB is not a backup; a bad rebuild is unrecoverable without one |
| Exclude `workspace*.json` from day one | Removes the most common recurring conflict |
| Write down the chunk size and E2EE state | Needed every time you add a device |

## FAQ

**Is CouchDB required, or can I use something else?**
LiveSync supports an object-storage backend (S3-compatible) in recent versions, which sidesteps the CORS problem completely. It's a reasonable choice if CouchDB is the only reason you're running a database.

**Mobile syncs then stops after a while.**
Usually the OS suspending the app mid-chunk. Smaller chunks help; so does opening the app and letting it finish.

**The device count keeps growing.**
Each fresh install registers a new device ID. Clean up stale entries in the plugin's device list; they don't break sync but they do inflate the chunk retention.

**Can I sync only some folders?**
Yes, via the ignore patterns in Sync Settings — but ignore rules differing between devices causes the same mismatch problems as above.
