---
title: "NocoDB: Unable to Connect to an External Database"
slug: nocodb-external-database-connection-failed
meta_description: "Connection test passes and the sync fails, or localhost is refused. The env var that allows local databases, host.docker.internal, and the write-permission requirement."
updated: October 2026
cluster: round 14 (tech) — nocodb GitHub issues and community
competition: LOW
---

# NocoDB: Unable to Connect to an External Database

Four causes cover almost all of these, and two are specific to NocoDB rather than to databases in general.

## 1. Local databases are blocked by default

NocoDB refuses `localhost` / `127.0.0.1` / private-range external sources unless you explicitly allow it. The symptom is a connection that fails immediately with no useful detail:

```yaml
environment:
  NC_ALLOW_LOCAL_EXTERNAL_DBS: "true"
```

This is a deliberate guard against SSRF, not a bug. Set it only on an instance you control.

## 2. localhost means the container

With that flag set, `localhost` still resolves to the **NocoDB container**, not your host or your database container.

| Database location | Host to use |
|---|---|
| Another container on the same Docker network | the service name, e.g. `mysql` |
| On the Docker host (Linux) | `172.17.0.1`, or `host.docker.internal` with `extra_hosts` |
| On the Docker host (Mac/Windows) | `host.docker.internal` |
| Another machine | its LAN IP |

```yaml
services:
  nocodb:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Prove reachability before fighting the UI:

```bash
docker exec nocodb sh -c 'nc -zv mysql 3306'
```

Also: MySQL and MariaDB bind to `127.0.0.1` by default on many installs. A database listening only on loopback is unreachable from any container:

```ini
# /etc/mysql/mysql.conf.d/mysqld.cnf
bind-address = 0.0.0.0
```

and the user must be granted from the right host:

```sql
CREATE USER 'nocodb'@'%' IDENTIFIED BY 'secret';
GRANT ALL PRIVILEGES ON mydb.* TO 'nocodb'@'%';
FLUSH PRIVILEGES;
```

`'nocodb'@'localhost'` will not authenticate a connection arriving from the Docker bridge.

## 3. NocoDB needs write access

This surprises people connecting to a reporting replica: **NocoDB requires write permissions** on an external MySQL database. It creates and maintains its own metadata, and a read-only user fails at the point where it tries to write — which is often *after* a successful connection test.

That is the signature of this cause: **test passes, submit or sync fails.**

If you only want read access, either accept that NocoDB isn't the right tool for that database, or give it a schema of its own to write metadata into and read-only grants on the rest, where your version supports it.

## 4. Driver not present for the database type

```
Cannot find module 'mssql'
```

Some database drivers aren't bundled in every image variant. MSSQL in particular has produced module-not-found errors in Docker. Check the image you're running and prefer the full image over a slim variant; if the driver genuinely isn't there, no configuration adds it.

## 5. Meta-sync stuck in loading

Separate symptom, usually PostgreSQL with many tables. Meta-sync enumerates every table, column and relation; on a large schema it can appear hung.

- Watch the log rather than the spinner:

```bash
docker logs nocodb --tail 100 -f | grep -iE 'meta|sync|error'
```

- Restrict the connection to a **single schema** rather than the whole database. In the connection dialog, set the schema explicitly. This is the main lever.
- Views with expensive definitions are enumerated too; a schema full of materialised views is slow to introspect.
- If it never completes, check for a table NocoDB can't model — composite primary keys and exotic column types have each caused stalls.

## 6. The usual suspects

- **SSL required.** Managed Postgres/MySQL (RDS, DigitalOcean, Supabase) usually require TLS. The connection dialog has an SSL section; "require" without a CA is the common working setting.
- **Firewall / security group** not permitting the NocoDB host's IP.
- **Port mapping** published but the database bound elsewhere. `ss -tlnp` on the database host.

## What not to do

- **Don't enable `NC_ALLOW_LOCAL_EXTERNAL_DBS` on a public instance.** It allows users to make the server connect to internal addresses.
- **Don't point NocoDB at your production database without a replica or a backup.** It writes.
- **Don't connect a whole database when you need one schema.** Introspection cost scales with what you expose.
- **Don't assume a passing connection test means it will work.** Write permission is tested later.

## Prevention

| Habit | Why |
|---|---|
| Dedicated database user with grants scoped to one schema | Limits what a bug or a user can reach |
| Service names or LAN IPs, never `localhost` | Removes the dominant connection failure |
| One schema per NocoDB base | Fast meta-sync, comprehensible UI |
| Snapshot the database before first connecting | NocoDB creates metadata tables |

## FAQ

**Does it modify my tables?**
It adds its own metadata tables and can alter yours if you edit structure in the UI. Treat it as a read-write client.

**Can I use NocoDB's internal database for everything instead?**
Yes — bases created inside NocoDB live in its own Postgres/SQLite and have none of these problems.

**Airtable-style formulas on an external table?**
Supported as NocoDB-side fields; they don't become database columns.

**Connection drops after idle.**
Connection pool timeout versus the database's `wait_timeout`. Lower the pool's idle timeout below the server's.
