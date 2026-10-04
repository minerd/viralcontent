---
title: "Home Assistant Database Corrupt After an Update? Recover, Don't Panic"
slug: ha-recorder-database-corrupt
meta_description: "Recorder reporting a corrupt or failed-migration database after a core update. What HA does automatically, how to repair MariaDB, and how to keep history when you can."
updated: October 2026
cluster: round 12 (tech) — HA community threads and core GitHub issues
competition: LOW
---

# Home Assistant Database Corrupt After an Update? Recover, Don't Panic

After a core update you find one of these in the log:

- `Index for table 'events' is corrupt; try to repair it`
- `The system will rename the corrupt database file and create a new one`
- `Database migration failed` with a `UNIQUE constraint failed` or a column error

**First, the reassuring part:** the recorder database holds **history and statistics only**. Your automations, dashboards, scripts and integrations live in `.storage` and YAML, and are unaffected. Losing the database costs graphs, not your house.

## Step 1: let it rename and move on (SQLite)

Home Assistant handles SQLite corruption by **renaming the broken file and starting a fresh one**. You keep a working system and lose history up to that point.

The old file is still there as `home-assistant_v2.db.corrupt.<date>` in your config directory. Keep it until you're sure you don't want to try recovery, then delete it — it's often gigabytes.

If HA won't start at all, stop it, move `home-assistant_v2.db` (and `-wal`/`-shm`) aside, and start again.

## Step 2: try to salvage SQLite history (optional)

```bash
sqlite3 home-assistant_v2.db "PRAGMA integrity_check;"
sqlite3 home-assistant_v2.db ".recover" | sqlite3 recovered.db
```

Worth ten minutes if you care about long-term statistics; not worth an evening. Statistics (long-term, hourly) matter more than events — they're what energy dashboards use.

## Step 3: MariaDB/MySQL — repair rather than recreate

```sql
CHECK TABLE events, states, statistics;
REPAIR TABLE events;
OPTIMIZE TABLE states;
```

For failed migrations (the `schema 46->47` class of error):
- Check **free disk space** on the database volume first — migrations need room for a rebuilt table
- Raise **`innodb_buffer_pool_size`** and the lock table size if you got `lock table size` errors
- Give the migration **time**: on a large database it can run for hours, and people kill it halfway, which is what actually breaks things
- Watch progress rather than guessing: `SHOW PROCESSLIST;`

A reported approach for very large databases: move the database to a **faster machine**, let the migration finish there, then move it back.

## Step 4: when the migration simply won't complete

You have two honest options:

1. **Start fresh.** Drop the recorder database, let HA create a new schema, keep your config. You lose history
2. **Roll back HA core**, keeping the pre-update database and waiting for a fixed release. Only possible if you have a backup from before — the database schema is upgraded in place and isn't backward compatible

This is the reason the backup matters more than the repair technique.

## Step 5: stop it happening again

The common root causes are mundane:

- **SD cards.** Recorder writes constantly; SD cards die and corrupt. Move to SSD/NVMe. This is the single biggest fix
- **Unclean shutdowns.** Pulling power from a running HA is how SQLite gets corrupted. Use a UPS, and shut down properly
- **A full disk.** Monitor it
- **An enormous database.** Trim what you record:

```yaml
recorder:
  purge_keep_days: 10
  commit_interval: 30
  exclude:
    domains: [automation, updater]
    entity_globs:
      - sensor.*_uptime
      - sensor.*_linkquality
```

Excluding noisy entities (Zigbee link quality, uptime counters, per-second power sensors) cuts database size dramatically, which makes every future migration faster and less likely to fail.

- **Back up before updating.** HA's own backup includes the database; keep one off-device
- **Consider MariaDB** on a separate machine for large installs, and keep its own backups

## FAQ

**Will I lose my automations?**
No. The recorder database is history only.

**Should I just delete the database?**
It's a legitimate, fast fix if you don't need the history. Stop HA first.

**Why does this keep happening?**
Almost always SD card wear or unclean shutdowns. Fix the storage and the pattern stops.

**How long should a migration take?**
Minutes on a small SQLite database; hours on a multi-gigabyte MariaDB. Don't interrupt it — monitor it.
