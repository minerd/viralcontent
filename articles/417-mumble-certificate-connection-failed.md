---
title: "Mumble Server: Certificate Errors and Refused Connections"
slug: mumble-certificate-connection-failed
meta_description: "murmur won't start with Let's Encrypt certs, or clients get SSL errors. The file-ownership rule, capabilities, and the TLS version problem."
updated: October 2026
cluster: round 14 (tech) — mumble-voip/mumble GitHub issues and forums
competition: LOW
---

# Mumble Server: Certificate Errors and Refused Connections

The server drops privileges early, which is the root of most certificate problems: by the time it reads the certificate it is no longer root, and a root-owned key is unreadable.

## 1. The ownership rule

```bash
sudo ls -l /etc/letsencrypt/live/voice.example.com/
sudo ls -l /etc/letsencrypt/archive/voice.example.com/
```

Let's Encrypt's `live/` entries are symlinks into `archive/`, and **the real files in `archive/` are root-only**. The documented symptom is murmur failing to read the certificate even with apparently correct permissions on `live/`.

The clean approach is to copy the certificate into a location the mumble user owns, with a renewal hook:

```bash
sudo mkdir -p /etc/mumble/certs
sudo chown mumble-server:mumble-server /etc/mumble/certs
sudo chmod 750 /etc/mumble/certs
```

```bash
# /etc/letsencrypt/renewal-hooks/deploy/mumble.sh
#!/bin/bash
D=voice.example.com
install -o mumble-server -g mumble-server -m 640 \
  /etc/letsencrypt/live/$D/fullchain.pem /etc/mumble/certs/fullchain.pem
install -o mumble-server -g mumble-server -m 640 \
  /etc/letsencrypt/live/$D/privkey.pem /etc/mumble/certs/privkey.pem
systemctl restart mumble-server
```

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/mumble.sh
```

```ini
; /etc/mumble/mumble-server.ini
sslCert=/etc/mumble/certs/fullchain.pem
sslKey=/etc/mumble/certs/privkey.pem
```

Without the hook, everything works for 90 days and then breaks at renewal — the classic.

## 2. The capabilities switch

Debian/Ubuntu's packaging offers an alternative that solves the same problem differently:

```bash
# /etc/default/mumble-server
MURMUR_USE_CAPABILITIES=1
```

With this set, the server starts as root, reads the certificate, then drops to its unprivileged user retaining only the capabilities it needs. The documented fix for "murmur can only read the certificate if it is the file owner".

Either approach works. The capabilities route avoids copying files; the copy route avoids running as root at all. Pick one and document it.

## 3. "The root CA certificate is not trusted for this purpose"

Clients disconnecting with this message means the certificate chain is wrong, not the key.

- **Use `fullchain.pem`, not `cert.pem`.** `cert.pem` is the leaf alone; clients need the intermediates. This single mistake produces exactly this error.
- For a commercial CA, concatenate leaf then intermediates (not the root):

```bash
cat your_domain.crt intermediate.crt > fullchain.pem
```

- Order matters: leaf first.

Verify what the server presents:

```bash
openssl s_client -connect voice.example.com:64738 -showcerts </dev/null 2>/dev/null \
  | grep -E 'subject=|issuer='
```

You should see your leaf and at least one intermediate.

## 4. "SecPKCS12Import returned no items" (macOS)

A reported macOS-specific failure importing a self-signed certificate. Practical handling:

- Generate the PKCS#12 with a password; some import paths refuse an empty one:

```bash
openssl pkcs12 -export -out mumble.p12 -inkey privkey.pem -in fullchain.pem -passout pass:changeme
```

- Prefer a real certificate from a public CA. Self-signed certificates on Mumble are a recurring source of client-side friction across platforms, and a Let's Encrypt certificate removes the whole category.

## 5. TLS version mismatch

```
SSL handshake failed / connection closed during handshake
```

Older clients offering **TLS 1.0** are refused by current OpenSSL defaults on newer distributions. The correct resolution is to update the clients; the server-side alternatives (re-enabling TLS 1.0 in `/etc/ssl/openssl.cnf`) weaken security for everyone to accommodate one old client.

```bash
openssl s_client -connect voice.example.com:64738 -tls1_2 </dev/null 2>&1 | head -5
```

## 6. Refusing all connections

Separate from certificates:

```bash
sudo systemctl status mumble-server
sudo tail -n 60 /var/log/mumble-server/mumble-server.log
sudo ss -tlnp | grep 64738
```

- **Port 64738 on both TCP and UDP.** TCP carries control and (as a fallback) voice; UDP carries voice normally. UDP missing gives working connections with poor-quality audio over TCP.
- **`host=` in the ini** bound to an address the machine doesn't have.
- **`users=`** limit reached.
- **A bad `serverpassword`** — clients get a specific rejection, not a handshake failure.
- **Public server registration failing with an SSL error** is a separate, cosmetic problem: registration requires a valid certificate chain and a resolvable hostname, and failing it doesn't stop local connections.

## What not to do

- **Don't point `sslCert` at `cert.pem`.** Use `fullchain.pem`.
- **Don't chmod the Let's Encrypt archive directory world-readable.** That exposes every certificate's key on the host. Copy with a hook instead.
- **Don't re-enable TLS 1.0** to support one old client.
- **Don't skip the renewal hook.** It works for 90 days without one.

## Prevention

| Habit | Why |
|---|---|
| Deploy hook copying certs with correct ownership | Survives every renewal |
| `fullchain.pem` always | Removes the chain-trust error |
| UDP 64738 open as well as TCP | Voice quality depends on it |
| A real certificate rather than self-signed | Eliminates per-platform import problems |

## FAQ

**Does Mumble need a certificate at all?**
It generates a self-signed one if you don't supply one, and clients warn. A real certificate removes the warning and enables public registration.

**Can I share the certificate with my web server?**
Yes — same hostname, same files, copied to a location mumble can read.

**Clients connect but can't hear each other.**
UDP blocked; everything falls back to TCP. Check the client's connection info for the transport in use.

**Where is the configuration?**
`/etc/mumble/mumble-server.ini` on Debian/Ubuntu, `/etc/murmur.ini` on some others. Packaging names differ; the file's contents don't.
