---
title: "TrueNAS App Stuck on 'Deploying'? Read the Events, Then the Host Path Checks"
slug: truenas-app-stuck-deploying
meta_description: "A TrueNAS app that never leaves Deploying is almost always a failing container, a host path safety check, or a clock/NTP problem. How to read the real error."
updated: October 2026
cluster: round 10 (tech) — TrueNAS community threads and one Medium post
competition: LOW
---

# TrueNAS App Stuck on 'Deploying'? Read the Events, Then the Host Path Checks

TrueNAS shows **Deploying** forever. The UI gives you nothing else, and it's easy to assume the app system is broken. It usually isn't: **"Deploying" is what you see when a container keeps failing to start.**

## Step 1: get the actual error (do this first)

Two places hold it:

**Application Events** — click the app's card, expand **Application Events**. Look for:
- `Back-off restarting failed container` → the container starts and dies; it's an app config problem
- `Startup probe failed` / `Readiness probe failed` → it starts but never becomes healthy
- `FailedMount` → a storage path problem
- `ImagePullBackOff` → it can't fetch the image (DNS, network, rate limit, wrong tag)

**Logs** — the app card's **⋮ menu → Logs**, and make sure you've selected the **app's own container**, not an init or sidecar container. This is where a missing environment variable, a permissions error or a bad config file shows up in plain text.

Everything below is a guess until you've read those two.

## Step 2: host path safety checks

TrueNAS validates the dataset paths you hand an app. The most common trigger: **the same path is used by an SMB/NFS share and by an app**. Validation blocks the app, and it hangs in Deploying.

Two ways out:
- **Correct**: give the app its **own dataset**, not one that's shared out. Create a child dataset for app data and point the app there
- **Workaround**: **Apps → Settings → Advanced Settings → disable "Enable Host Path Safety Checks"**. Several post-upgrade recoveries come down to this, but you're switching off a check that exists for good reason — prefer separate datasets

Related: an app that can't reach an SMB path while the SMB service holds it. Stopping the SMB service, letting the apps deploy, then starting SMB again is a reported sequence that works.

## Step 3: the clock

Container registries and TLS both care about time. A **BIOS clock in local time**, or **no NTP**, produces image pulls that fail with certificate errors and apps that never deploy.

- **System Settings → General → NTP Servers** — make sure they're configured and reachable
- BIOS clock set to **UTC**
- Check the system time actually matches reality

## Step 4: networking

- **Multiple NICs on the same subnet** causes routing confusion for the apps network. Reported fix: remove the second NIC, reboot
- The apps system needs a working **gateway and DNS**. Test from the shell: resolve and reach a registry
- A **static IP without DNS servers** set is a classic
- Check the app's **node port** doesn't collide with another app or a system service

## Step 5: storage

- The **apps pool** must be set and healthy (**Apps → Settings → Choose Pool**)
- Pool **full or nearly full** — deployments fail with little explanation
- A dataset with the wrong **ACL type** for the app (POSIX vs NFSv4) causes permission failures on first write
- **Dataset permissions**: the app runs as a specific UID/GID; make sure it can write

## Step 6: after an upgrade specifically

Major TrueNAS versions have changed the app backend (Kubernetes-era → Docker-era). After a big upgrade:

- Check the **release notes** for app-system changes before anything else
- Apps may need **uninstall, reinstall and reconfigure** — which is why your app configuration and data should live on datasets you control, not inside the app's own state
- Keep a written note of each app's config; the UI's state is not a backup

## When to stop debugging and redeploy

If events show a container failing on its own config and you have the app's **data on a dataset**, the fastest route is often: delete the app, reinstall it, point it at the same dataset, re-enter the config. Minutes, versus an evening of reading Kubernetes-era error strings.

That only works if you knew the data was on a dataset — which is the real lesson.

## FAQ

**Why does the UI just say Deploying with no error?**
Because the failure is inside the container. Application Events and the container log have the message.

**Is disabling host path safety checks safe?**
It removes a guard against apps and shares writing the same data. Use separate datasets instead where you can.

**Apps worked before the upgrade and now none of them deploy.**
Check the release notes for app-system changes, then the clock, then host path checks — in that order.

**Can I recover an app's data if I delete the app?**
Yes, if it lives on a dataset you created. If it was inside app-managed storage, maybe not — move it out now.
