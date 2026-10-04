---
title: "Home Assistant MariaDB Migration Taking Days? Let It Finish, on Better Hardware"
slug: ha-mariadb-recorder-migration-stuck
meta_description: "A schema migration crawling at 28% for eleven hours. How to tell progress from a hang, the lock-table-size error, and the move-to-a-faster-machine trick."
updated: October 2026
cluster: round 12 (tech) — HA core GitHub issues and community threads
competition: LOW
---

# Home Assistant MariaDB Migration Taking Days? Let It Finish, on Better Hardware

After a core update, the recorder starts a **schema migration** and Home Assistant is effectively unusable — or recording stops while the queue fills. Reports of 11+ hours at 28% are common, and so is killing it, which is the one thing that makes it worse.

## 1. Is it progressing or hung?

This is the only question that matters at first.

```sql
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS\G
```

- A long-running `ALTER TABLE` on `states` or `events` with a changing state → **it's working**. Leave it
- `Waiting for table metadata lock` → something else holds the table. Find it in the process list and stop it
- Nothing running, no CPU, no disk → actually hung

```bash
iostat -x 5        # is the disk busy?
docker stats       # is the DB container doing work?
```

A `BIGINT` column change on a multi-gigabyte `states` table rewrites the whole table. On an SD card or a cheap VM that genuinely takes a day or more.

## 2. Give it what it needs

**Disk space.** An in-place table rebuild needs room for a second copy of the table. Half-full is not enough:

```bash
df -h /var/lib/mysql
```

**Memory and InnoDB settings.** The `lock table size` error that people hit is a configuration limit:

```ini
[mysqld]
innodb_buffer_pool_size = 1G      # as much as you can spare
innodb_log_file_size = 256M
innodb_online_alter_log_max_size = 2G   # the 'lock table size' fix
tmp_table_size = 64M
max_allowed_packet = 64M
```

Restart MariaDB, then let HA retry the migration.

## 3. The move-to-a-faster-machine trick

The most effective reported approach for a large database:

1. Stop Home Assistant
2. **Dump** the database (`mysqldump`) and copy it to a desktop/server with a fast NVMe and real RAM
3. Restore it there, point a temporary Home Assistant at it, and let the **migration finish**
4. Dump it again and restore it back

Hours instead of days. Worth it once, and it tells you something about where your database should live permanently.

## 4. The honest alternative

If migration keeps failing or the estimate is absurd, **start a fresh recorder database**:

- You lose history and long-term statistics
- You lose nothing else — automations, dashboards and integrations are unaffected
- It takes minutes

```sql
DROP DATABASE homeassistant;
CREATE DATABASE homeassistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then restart HA and it builds the current schema directly. For many people this is the right call and they spend a week avoiding it.

## 5. Make the next migration small

The reason migrations hurt is database size, and that's controllable:

```yaml
recorder:
  db_url: mysql://user:pass@core-mariadb/homeassistant?charset=utf8mb4
  purge_keep_days: 10
  commit_interval: 30
  exclude:
    domains: [automation, updater]
    entity_globs:
      - sensor.*_linkquality
      - sensor.*_rssi
      - sensor.*_uptime
      - sensor.*_power_factor
```

Then once, off-hours:

```yaml
service: recorder.purge
data:
  keep_days: 10
  repack: true
```

A 500 MB database migrates in minutes. A 40 GB one is a weekend. Excluding Zigbee link-quality and per-second power sensors is usually the difference.

## 6. Also check

- **Both** HA and MariaDB on supported versions; very old MariaDB has failed newer migrations
- `utf8mb4` charset and collation — mismatches cause migration errors mid-way
- Reported: migration failures with `UNIQUE constraint` / duplicate-key errors, which need the offending rows removed before it can proceed. Check the issue for your schema version jump
- Don't run **two HA instances** against one database

## Prevention

1. **Keep the database small** (purge + excludes) — this is the whole game
2. **Back up before updating**: database dump plus HA backup
3. Put MariaDB on **SSD/NVMe**, not an SD card
4. Update HA when you can **leave it running** for hours
5. Check the release notes for **schema version** changes before clicking update

## FAQ

**Can I interrupt a migration?**
Avoid it. A half-applied schema change is how databases get corrupted.

**How long is too long?**
Judge by activity, not the clock. Busy disk and a running ALTER means wait.

**Will I lose automations if I drop the database?**
No. Recorder holds history and statistics only.

**Is MariaDB better than SQLite for HA?**
For large installs with good storage, yes. On an SD card, neither will be happy.
