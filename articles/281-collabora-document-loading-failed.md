---
title: "Nextcloud Office 'Document Loading Failed'? It's the Reverse Proxy or the Allowlist"
slug: collabora-document-loading-failed
meta_description: "Collabora failing to open documents in Nextcloud. The WOPI allowlist, aliasgroups, WebSocket headers, proxy_hide_header Upgrade and HAProxy compatibility."
updated: October 2026
cluster: round 12 (tech) — Nextcloud community, richdocuments GitHub and Collabora forum
competition: LOW
---

# Nextcloud Office 'Document Loading Failed'? It's the Reverse Proxy or the Allowlist

The error is generic; the causes are specific. Work these in order.

## 1. Can the two services reach each other?

Collabora and Nextcloud must **both** be able to call each other. Test from inside the containers, not from your laptop:

```bash
# from Collabora, reach Nextcloud
docker exec -it collabora curl -sI https://cloud.example.com/status.php
# from Nextcloud, reach Collabora
docker exec -it nextcloud curl -sI https://office.example.com/hosting/discovery
```

`/hosting/discovery` must return XML. If either call fails — DNS, TLS, firewall, Docker network — nothing else matters. A self-signed certificate on one side will fail here, which is the quiet killer in homelab setups.

## 2. WOPI allowlist and aliasgroups

Two settings cause a large share of these:

**Nextcloud side** — `richdocuments` has a **WOPI allowlist**. Collabora's requests come from its own IP; if that IP isn't allowed, documents don't load:

```bash
occ config:app:set richdocuments wopi_allowlist --value "172.18.0.0/16,192.168.1.0/24"
```

**Collabora side** — the **`aliasgroup`** must include your Nextcloud URL:

```yaml
environment:
  - aliasgroup1=https://cloud.example.com:443
  - extra_params=--o:ssl.enable=false --o:ssl.termination=true
```

Missing or wrong `aliasgroup`/`wopi_allowlist` is explicitly called out as a likely cause in community threads. Get these two right before touching anything else.

## 3. The nginx header that breaks it

A documented, maddening one: **`proxy_hide_header Upgrade;`** in the nginx config prevents Collabora from working. Removing that single line fixed it.

More generally, Collabora needs WebSockets:

```nginx
location ^~ /browser { proxy_pass http://collabora:9980; proxy_set_header Host $http_host; }
location ^~ /hosting/discovery { proxy_pass http://collabora:9980; proxy_set_header Host $http_host; }
location ^~ /hosting/capabilities { proxy_pass http://collabora:9980; proxy_set_header Host $http_host; }
location ~ ^/cool/(.*)/ws$ {
    proxy_pass http://collabora:9980;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host $http_host;
    proxy_read_timeout 36000s;
}
location ^~ /cool/ { proxy_pass http://collabora:9980; proxy_set_header Host $http_host; }
```

`Failed to establish socket connection or socket connection closed unexpectedly` plus "the reverse proxy might be misconfigured" is the exact error this produces.

## 4. HAProxy and other proxies

Reported: Collabora broke for Nextcloud instances behind **HAProxy 2.x** from a particular Collabora version onward. If you're on HAProxy, check its WebSocket handling (`option http-server-close` vs tunnel mode, and timeouts) before suspecting Nextcloud.

Timeouts matter everywhere: a document session is a long-lived connection. Proxy read timeouts measured in seconds will drop editing sessions mid-sentence.

## 5. SSL termination flags

If your proxy terminates TLS and talks HTTP to Collabora, Collabora must be told:

```
--o:ssl.enable=false --o:ssl.termination=true
```

Getting these backwards produces a service that answers `/hosting/discovery` over the wrong scheme and documents that never load. Pair them with `overwriteprotocol=https` on the Nextcloud side.

## 6. Version pairing

- `richdocuments` (Nextcloud Office) must match your **Nextcloud major version**
- Collabora's own version matters: specific releases have fixed and broken things (updating to a newer `collabora/code` tag resolved loading failures in reported cases)
- Pin both, upgrade deliberately, and check the app store's compatibility note before a Nextcloud major upgrade

## Order of operations

1. `curl` both directions between the containers
2. `/hosting/discovery` returns XML?
3. **wopi_allowlist** and **aliasgroup** correct?
4. WebSocket locations and **no `proxy_hide_header Upgrade`**
5. **ssl.termination** flags consistent
6. Version pairing

## FAQ

**Why does it work for me and not for a remote user?**
Different path through the proxy — check the WebSocket location and timeouts on the public route.

**Do I need `aliasgroup`?**
Yes, with your Nextcloud URL, or Collabora rejects the host.

**Built-in CODE server or separate container?**
The built-in app is convenient for small instances; a separate container is more reliable and easier to debug.

**Documents open then freeze.**
Proxy read timeout too short on the WebSocket path.
