---
title: "vmagent Not Scraping Targets"
slug: vmagent-not-scraping-targets
meta_description: "No targets discovered, or some scraped and others not. The config flag it needs, the /targets debug page, and the service-discovery gaps."
updated: October 2026
cluster: round 14 (tech) — VictoriaMetrics GitHub issues
competition: LOW
---

# vmagent Not Scraping Targets

Start with the fact that catches people on day one:

> **By default vmagent scrapes nothing.** It needs a scrape configuration passed with `-promscrape.config`.

```bash
/usr/local/bin/vmagent \
  -promscrape.config=/etc/vmagent/scrape.yml \
  -remoteWrite.url=http://victoriametrics:8428/api/v1/write
```

No flag, no targets, no error — just an agent doing nothing.

## 1. The /targets page is the answer to most questions

```
http://vmagent:8429/targets
```

It lists every discovered target, the last scrape time, the sample count and **the exact error** when a scrape fails. There is also:

```
http://vmagent:8429/service-discovery
```

which shows targets **before** relabelling, with the labels discovery produced. Comparing the two tells you whether a target was never discovered or was dropped by a relabel rule — the single most useful distinction here.

```bash
curl -s http://vmagent:8429/api/v1/targets | python3 -m json.tool | head -40
```

## 2. Targets discovered then dropped by relabelling

```yaml
scrape_configs:
  - job_name: node
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_label_app]
        regex: node-exporter
        action: keep
```

A `keep` whose regex matches nothing drops everything. A `drop` that's too broad does the same. The `/service-discovery` page shows the pre-relabel labels, so you can see whether `__meta_kubernetes_service_label_app` is even present — frequently it isn't, because the label is on the pod rather than the service, or the name differs.

Test incrementally: comment out the relabel rules, confirm targets appear in `/targets`, then add rules back one at a time.

## 3. Service discovery not returning everything

Several reported cases, all with the same shape: some targets discovered, others not, non-deterministically.

- **Consul SD returning a different count on each restart.** Consul's catalog API paginates and watches; a flaky connection gives partial results. Increase the SD refresh interval and check Consul's own health:

```yaml
    consul_sd_configs:
      - server: consul:8500
        services: []
```

- **Kubernetes endpoints discovered for some services only.** Usually RBAC: the service account needs `list`/`watch` on endpoints, services, pods and nodes across namespaces. A partial grant gives partial discovery with no obvious error:

```bash
kubectl auth can-i list endpoints --as=system:serviceaccount:monitoring:vmagent -A
```

- **Restarting the pod "fixes" it.** Reported for Kubernetes SD, which indicates a watch that didn't establish. A restart is a workaround; the fix is usually RBAC or API server reachability.

## 4. vmagent stuck when remote storage is unavailable

A documented behaviour worth planning for: **vmagent can stall scraping when multiple large remote-write destinations are unavailable.** The in-memory queue fills, backpressure applies, and scrapes stop.

```bash
-remoteWrite.maxDiskUsagePerURL=10GB
-remoteWrite.tmpDataPath=/vmagent-data
-remoteWrite.queues=8
```

On-disk queueing is what keeps scraping alive through a storage outage. Without `-remoteWrite.tmpDataPath` on a real volume, vmagent buffers in memory and then stops:

```yaml
    volumes:
      - vmagent-data:/vmagent-data
```

This is the single most important production setting for vmagent and it's absent from most quickstarts.

## 5. Scrape interval not respected under load

Reported at roughly 2,000 targets: vmagent doesn't honour the configured scrape interval, with scrapes delayed or blocking.

Levers:

```bash
-promscrape.maxScrapeSize=16MB
-promscrape.suppressScrapeErrors
-promscrape.streamParse
```

- **`-promscrape.streamParse`** parses responses as a stream rather than buffering, which cuts memory dramatically on large targets. Enable it for big fleets.
- **Split the work.** Multiple vmagent instances with `-promscrape.cluster.membersCount` and `-promscrape.cluster.memberNum` shard targets between them. That's the designed answer to scale, rather than tuning one instance.
- **Check that a few slow targets aren't blocking.** A target taking 30 seconds to respond with a 15-second interval creates a backlog. `/targets` shows scrape duration per target.

## 6. Scraping works, nothing arrives in VictoriaMetrics

Different half of the pipeline:

```bash
curl -s 'http://vmagent:8429/metrics' | grep -E 'vmagent_remotewrite_(requests_total|errors_total|pending_data_bytes)'
```

- `vmagent_remotewrite_errors_total` rising — the destination is rejecting writes. Check its log; common causes are a wrong URL path (`/api/v1/write` is required) and authentication.
- `pending_data_bytes` growing — the queue isn't draining. Network, or the destination is overloaded.
- Both flat at zero with targets being scraped — no `-remoteWrite.url` configured.

vmagent does not store data locally for querying; it forwards. Querying vmagent itself returns only its own self-metrics, which confuses people expecting Prometheus behaviour.

## What not to do

- **Don't run vmagent without `-remoteWrite.tmpDataPath` on a volume.** A storage outage then stops your monitoring.
- **Don't debug relabelling by reading the YAML.** Use `/service-discovery`.
- **Don't scale one vmagent past a few thousand targets.** Shard it.
- **Don't expect to query vmagent.** It's an agent, not a store.

## Prevention

| Habit | Why |
|---|---|
| `-promscrape.config` and `-remoteWrite.url` both explicit, in your unit file | The two things without which nothing happens |
| On-disk remote-write queue on a persistent volume | Survives storage outages without losing data |
| `/targets` checked after every config change | Errors are per-target and only visible there |
| Shard with cluster flags beyond ~1,000 targets | The supported scaling path |

## FAQ

**Can it replace Prometheus entirely?**
vmagent plus VictoriaMetrics, yes, for scraping and storage. Alerting needs vmalert.

**Does it support Prometheus config verbatim?**
Largely, with extras. Some exotic SD options differ; `/targets` will show you.

**How do I reload config without a restart?**
`curl -X POST http://vmagent:8429/-/reload`, or run with `-promscrape.configCheckInterval=30s` for automatic reloads.

**Self-scraping?**
There are `-selfScrape*` flags; enable them so vmagent's own metrics land in your store.
