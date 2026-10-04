---
title: "Speedtest Tracker: Tests Failing or Stuck on \"Checking\""
slug: speedtest-tracker-failing
meta_description: "Batch failed for unknown reasons, the Ookla CLI errors, or the server list won't load. Timeouts, rate limits and the container-vs-host difference."
updated: October 2026
cluster: round 14 (tech) — alexjustesen/speedtest-tracker GitHub issues
competition: LOW
---

# Speedtest Tracker: Tests Failing or Stuck on "Checking"

Speedtest Tracker wraps the **Ookla Speedtest CLI**. When tests fail, the question is whether the CLI can run successfully *inside the container* — which is often different from on the host.

```bash
docker exec speedtest-tracker /usr/bin/speedtest --accept-license --accept-gdpr
```

That single command separates the app from the CLI. If it fails there, nothing in the app's configuration helps.

## 1. The server list won't load

```
Unable to retrieve Ookla servers, check internet connection and see logs
```

A documented cause: the **Ookla API request timeout is hardcoded at 5 seconds**, which is not enough on many connections. Testing shows 5 s failing and 20 s succeeding.

What you can do:

- Retry — it's intermittent by nature, and a second attempt often works.
- **Pin a server ID** so the list isn't needed for scheduled runs:

```
Settings → Speedtest → Server ID: 12345
```

Find your preferred server once:

```bash
docker exec speedtest-tracker /usr/bin/speedtest --servers
```

Pinning a server also makes your results comparable over time, which is the point of tracking — a rotating server makes the graph meaningless.

- Check your DNS inside the container:

```bash
docker exec speedtest-tracker sh -c 'nslookup www.speedtest.net; nslookup api.speedtest.net'
```

## 2. Hangs partway, or "Checking" forever

Reported repeatedly: the test reaches 39% download and fails, or everything sits in **Status: Checking** and never completes, while the same CLI binary works outside the container.

Causes, in order:

- **Rate limiting.** Roughly **30 calls per hour** through the CLI. A 15-minute schedule plus manual tests plus a failed-retry loop exceeds it, and the symptom is tests that start and stall. Set the schedule to hourly and see whether it clears:

```
Settings → Speedtest → Schedule: 0 * * * *
```

- **A stuck queue worker.** Speedtest Tracker runs Laravel queues; a dead worker leaves jobs in "Checking" forever:

```bash
docker logs speedtest-tracker --tail 100 | grep -iE 'queue|worker|horizon|job'
docker restart speedtest-tracker
```

If restarting clears a backlog each time, the worker is dying — check memory.

- **Container networking.** A CLI that works on the host and not in the container points at the bridge network's MTU or a restrictive egress policy. Try host networking as a test:

```yaml
    network_mode: host
```

If it works there, it's the Docker network, not Ookla.

- **Synology Container Manager** specifically has produced `An unexpected error occurred while running the Ookla CLI` on every run. On Synology, check that the container has outbound access unimpeded and consider host networking.

## 3. Results are obviously wrong

A real and separate issue: download and upload values that don't match reality.

- **The container is the bottleneck.** CPU limits on the container throttle the test. Remove `cpus:` limits or raise them — a gigabit test needs real CPU.
- **A VPN or proxy in the container's path.** You're measuring the tunnel.
- **Wrong server.** A server 2,000 km away measures latency, not your line.
- **Ookla CLI vs. speedtest++**: if the official CLI reports good numbers from a shell and the app reports poor ones, you have a container resource problem, not a measurement one.

Compare directly:

```bash
docker exec speedtest-tracker /usr/bin/speedtest --server-id=12345 --format=json | python3 -m json.tool | grep -A3 download
speedtest --server-id=12345        # on the host
```

## 4. 500 errors when running a test

```bash
docker logs speedtest-tracker --tail 100 | grep -iE 'error|exception'
```

- **Database not writable** or migrations not run. The image runs them at start; a failed migration leaves a broken schema:

```yaml
    environment:
      - DB_CONNECTION=sqlite
      - APP_KEY=base64:...
    volumes:
      - ./data:/config
```

- **`APP_KEY` missing.** Laravel refuses to run without it; generate one:

```bash
docker exec speedtest-tracker php artisan key:generate --show
```

Set it in the environment and restart. An unset or changed `APP_KEY` also invalidates stored encrypted values.

- **Certificate validation.** A reported case: unable to retrieve servers due to a certificate problem, typically a corporate TLS-inspecting proxy. The container needs that CA installed.

## 5. Scheduling

```
Settings → Speedtest → Schedule
```

Use cron syntax. Practical guidance:

- **Hourly is plenty** for tracking an ISP. Every 15 minutes generates four times the data and risks the rate limit.
- A test saturates your line for 20–30 seconds; frequent tests are noticeable to anyone using the connection.
- Avoid `*/5` entirely.

## What not to do

- **Don't test every few minutes.** Rate limits, saturated line, no extra insight.
- **Don't limit the container's CPU** and then trust the numbers.
- **Don't let the server rotate** if you want comparable history.
- **Don't debug in the UI.** Run the CLI in the container; it prints the real error.

## Prevention

| Habit | Why |
|---|---|
| Pinned server ID | Comparable results and no dependence on the server list |
| Hourly schedule | Well inside the rate limit |
| No CPU limits on the container | Accurate measurements |
| `APP_KEY` set explicitly and backed up | Avoids a class of 500s and lost encrypted settings |

## FAQ

**Can it use a different backend?**
Some versions support LibreSpeed, which has no Ookla rate limit and lets you host your own server — a good option for frequent internal testing.

**Does it notify on slow results?**
Yes, with configurable thresholds and several notification channels.

**Results disappeared after an upgrade.**
Check that the data volume is mounted and the migration completed. The data is in the configured database.

**Can I export the data?**
Yes, and for long-term trends exporting to InfluxDB/Prometheus and graphing there is more useful than the built-in charts.
