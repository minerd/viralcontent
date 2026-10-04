---
title: "Grafana Panels Showing 'No Data' After an Upgrade? Datasource UIDs First"
slug: grafana-no-data-after-upgrade
meta_description: "Dashboards that worked now show No Data. Why datasource references by name break, what Mixed datasource panels do, and how to prove the query still works in Explore."
updated: October 2026
cluster: round 10 (tech) — Grafana GitHub issues and community forum threads
competition: LOW
---

# Grafana Panels Showing 'No Data' After an Upgrade? Datasource UIDs First

You upgrade Grafana and dashboards that worked for years return **No Data**. The data is still in the database — Explore proves it — but the panels are empty.

## Step 1: prove where the break is

Before touching dashboards:

1. **Open the panel → Edit → Explore** (or copy the query into Explore). Does it return data there?
   - **Yes in Explore, no in the panel** → the panel's datasource reference or transformation is the problem (most common after upgrades)
   - **No in Explore either** → it's the datasource or the data, not the dashboard
2. Check the panel's **Query inspector → Query** tab: what is actually being sent, and which datasource `uid` is attached?
3. Look at the panel's **time range** and the dashboard's — an upgrade that changes a default can leave you looking at a window with no data

## Step 2: datasource references and UIDs

Grafana identifies datasources by **UID**. Dashboards that reference a datasource **by name**, or by a UID that changed when the datasource was recreated or re-provisioned, break on upgrade.

Signs:
- Panels show No Data but the datasource tests fine
- The datasource dropdown in the panel editor is **empty or shows a UID string** instead of a name
- Only **some** panels broke — the ones with older or hand-edited JSON

Fixes:
- Open the panel, **re-select the datasource** from the dropdown, save
- For many dashboards, edit the JSON and fix the `datasource` blocks, or re-import the dashboard and map datasources during import
- If you provision datasources from YAML, **pin an explicit `uid:`** in the provisioning file so it never changes again. This is the durable fix
- Deleting and recreating the datasource in the UI then re-selecting it in panels has been a reported resolution — but it changes the UID again, so pin it afterwards

## Step 3: Mixed datasource panels

There's a specific, reported Grafana 11 regression: panels using the **Mixed** datasource return No Data while the same queries work in Explore, because the per-query `datasource` field was a **string** rather than an object with `type` and `uid`.

If a panel uses Mixed:
- Open the panel JSON and make each query's datasource an object:
  ```json
  "datasource": { "type": "prometheus", "uid": "abc123" }
  ```
- Or rebuild the panel's queries by re-selecting each datasource in the editor
- Where you don't actually need Mixed, switch the panel to a single datasource

## Step 4: panel-type migrations

Old panel types get migrated automatically, and the migration doesn't always carry every option:

- **Stat / Singlestat → Stat**: field selection can land on a field that has no data. In the panel's **Value options**, check **Fields** (try *All fields* / *Numeric fields*) and the **Calculation**
- **Graph (old) → Time series**: legend/field overrides and some transformations don't survive cleanly
- **Table (old) → Table**: column selection and transformations need checking

The data is arriving; the panel is displaying the wrong field. Query inspector → **Data** tab shows the frames that came back, which tells you immediately whether this is a display problem.

## Step 5: datasource plugin and version compatibility

- **Plugin versions**: an upgraded Grafana with an old datasource plugin is a common No Data cause. Update plugins alongside Grafana
- **Config files replaced**: check your `grafana.ini` / provisioning files weren't overwritten by the package upgrade (`.rpmnew` / `.dpkg-dist` files are the giveaway)
- **InfluxDB / Prometheus query language changes** between major versions — a query valid before may now return nothing silently rather than erroring
- Datasource **auth** that silently expired during the upgrade window

## Rollback and recovery

- Keep the **previous Grafana version's** container tag or package to roll back while investigating
- **Export dashboards to JSON before upgrading** (and keep them in git). Then a broken migration is a re-import, not an evening of clicking
- Grafana keeps **dashboard version history** — Dashboard settings → Versions → compare and restore a pre-upgrade version

## FAQ

**Why does Explore work but the panel doesn't?**
The query is fine; the panel's datasource reference, field selection or transformation is the problem.

**Only one panel type broke across all dashboards.**
That's a panel-type migration issue — check field selection and calculation in that panel type.

**Should I delete and recreate my datasources?**
It works, but it changes the UID. If you do, pin the UID in provisioning afterwards.

**How do I stop this happening at the next upgrade?**
Pin datasource UIDs in provisioning, keep dashboard JSON in version control, upgrade plugins with Grafana, and test one dashboard before rolling out.
