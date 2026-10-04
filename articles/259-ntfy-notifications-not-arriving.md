---
title: "Self-Hosted ntfy Notifications Not Arriving on Android? Check These Five Things"
slug: ntfy-notifications-not-arriving
meta_description: "Messages publish fine but never reach the phone. Topic names, base URL, WebSocket proxying, access control and how Android delivery actually works without Firebase."
updated: October 2026
cluster: round 12 (tech) — ntfy GitHub issues; the SERP is full of setup guides answering a different question
competition: LOW
---

# Self-Hosted ntfy Notifications Not Arriving on Android? Check These Five Things

Every search result is a "how to self-host ntfy" tutorial. This is the other half: it's installed, publishing returns 200, and the phone stays silent.

## 1. How delivery works on a self-hosted server

This matters, because it explains most of the symptoms.

With your own server (not ntfy.sh), the Android app **cannot use Firebase** unless you build a custom app with your own Firebase credentials. Instead it keeps a **foreground service** with an open connection and listens directly.

Consequences:
- The app shows a **persistent notification** — that's the listener, not a bug. Don't "fix" it by force-stopping the app
- **Android battery optimisation** will kill that service. Exclude ntfy: Settings → Apps → ntfy → Battery → **Unrestricted**
- Some vendor ROMs (Xiaomi, Samsung, Huawei, OnePlus) need extra steps: disable "deep sleep"/"adaptive battery" for the app and lock it in the recents list
- After a **phone reboot** the service must restart — open the app once if your ROM is aggressive

## 2. The topic name

Blunt but true: the most common cause. Topic names are **case-sensitive**, and there's no error for publishing to a topic nobody subscribes to.

```bash
curl -d "test" https://ntfy.example.com/alerts
```
Then confirm the app is subscribed to **`alerts`**, not `Alerts` or `alert`. Check in the app, character by character.

## 3. Base URL and HTTPS

- **`NTFY_BASE_URL` must exactly match the public HTTPS address** clients use. A mismatch and the app and web client refuse to work properly
- The **web client** refuses to show notifications over plain HTTP — that's the browser Notifications API, not ntfy
- In the Android app, the subscription must use the **same host and scheme** as the server's base URL
- Trailing slashes and `http` vs `https` both count

## 4. WebSocket through the reverse proxy

Real-time delivery needs the connection upgraded. Default nginx configs block it:

```nginx
location / {
    proxy_pass http://127.0.0.1:2586;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_connect_timeout 3m;
    proxy_send_timeout 3m;
    proxy_read_timeout 3m;
}
```

Short proxy timeouts are the subtle one: the listener reconnects constantly and you get delayed or missed messages rather than none at all.

## 5. Access control

If you enabled auth, a 403 is easy to miss:

```bash
ntfy access                       # show the ACL
ntfy access myuser alerts rw      # grant on the specific topic
```

Creating a user is not the same as **granting access to that topic**. Check both the publisher's and the subscriber's permissions, and remember `everyone` defaults change with `NTFY_AUTH_DEFAULT_ACCESS`.

## Testing the chain

```bash
# 1. does the server accept?
curl -s -o /dev/null -w "%{http_code}\n" -d "hi" https://ntfy.example.com/alerts
# 2. is it delivered live? (leave running, publish from another shell)
curl -s https://ntfy.example.com/alerts/json
# 3. does the websocket upgrade?
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  https://ntfy.example.com/alerts/ws
```

200 → 1 is fine. Stream shows the message → the server is fine and the problem is the phone. 101 missing → proxy.

## iOS is different

iOS **does** use push via ntfy's infrastructure, which means a self-hosted server must be reachable by ntfy.sh for iOS delivery (the `upstream-base-url` setting), or you poll. If iOS is silent while Android works, read that part of the docs rather than this list.

## Prevention

1. **Unrestricted battery** for the ntfy app, documented for whoever else uses it
2. **Exact base URL**, HTTPS, no mismatch
3. Proxy timeouts of **minutes**, not seconds
4. One **topic naming convention**, lowercase
5. Keep a **second channel** for critical alerts

## FAQ

**Why is there a permanent notification from ntfy?**
That's the foreground listener on a self-hosted setup. Removing it stops delivery.

**Messages work when the app is open but not in the background.**
Battery optimisation is killing the service.

**Do I need Firebase?**
Only if you build a custom app. The default self-hosted path uses the foreground service.

**Why does iOS behave differently?**
iOS delivery goes through ntfy's push infrastructure, so it needs the upstream setting configured.
