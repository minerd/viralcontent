---
title: "Kimai: Timesheet Export Fails With a Critical Error"
slug: kimai-export-failed
meta_description: "\"A critical error occurred\" on export, even as super-admin. Temp directory permissions, PHP extensions and the export_timesheet permission."
updated: October 2026
cluster: round 14 (tech) — kimai/kimai GitHub issues and docs
competition: LOW
---

# Kimai: Timesheet Export Fails With a Critical Error

The giveaway in most reports: **it fails regardless of role, including as super-admin.** That rules out permissions and points at the filesystem or PHP, because the export writes a temporary file before streaming it.

Run Kimai's own self-check first — it tests exactly these things:

```bash
docker exec kimai bin/console kimai:reload
docker exec kimai bin/console doctor
```

`doctor` reports PHP version, extensions, directory permissions and configuration problems in one go. A red line there is your answer.

## 1. Temp and cache directory permissions

Exports (XLSX, PDF, CSV) are generated into `var/` before download. If the web server user can't write there, you get a generic critical error with the detail only in the log.

```bash
docker exec kimai ls -ld var var/cache var/log var/data
docker exec kimai id
```

```bash
# inside the container, as root
chown -R www-data:www-data var/
chmod -R u+rwX var/
```

For a bare-metal install:

```bash
sudo chown -R www-data:www-data /var/www/kimai/var
sudo setfacl -R -m u:www-data:rwX /var/www/kimai/var
```

The log tells you plainly:

```bash
docker exec kimai tail -n 60 var/log/prod.log
```

Look for `Unable to write` or `failed to open stream: Permission denied`. Hunting the UI without reading this file is the main time sink here.

## 2. PHP extensions and limits

XLSX export needs **zip**; PDF export needs **gd** or **imagick** depending on the renderer:

```bash
docker exec kimai php -m | grep -iE 'zip|gd|imagick|intl|xml|mbstring'
```

A missing `zip` extension fails XLSX specifically while CSV works — a useful diagnostic: **if CSV exports and XLSX doesn't, it's an extension, not permissions.**

Then the limits:

```ini
; php.ini
memory_limit = 512M
max_execution_time = 300
```

A large date range builds the whole sheet in memory. A 30-day export working and a 12-month one failing is `memory_limit`, and the log will say so.

## 3. The permission that actually governs export

Once the technical side works, the role permissions are straightforward:

```
Admin → Permissions → (role) → export_timesheet
```

Two related permissions worth understanding, because their interaction is a documented surprise:

- **`export_timesheet`** — may export
- **`view_other_timesheet`** — may see other users' entries

A user with `create_export`/`export_timesheet` but **without** `view_other_timesheet` has been able to export **all users'** timesheets. If you grant export to non-managers, verify what they actually get by logging in as such a user and exporting. Don't assume the two permissions compose the way you'd expect.

## 4. Export produces an empty or malformed file

- **No data in range.** Check the filter: date range, customer, project, and the "exported" flag. Entries already marked as exported are hidden by default — that filter catches people every month.
- **A template problem.** Kimai's export templates (`templates/export/`) can be customised; a broken custom template fails or produces nonsense. Test with a built-in renderer to isolate it.
- **Locale and decimal separators** in CSV opened by Excel — not an export failure, a CSV import setting in Excel.

## 5. API returning 403

```
GET /api/timesheets → 403 Forbidden
```

Separate from the UI. The API respects the same permissions plus the API user's own:

- The user must have API access enabled and an API token/password set
- `view_other_timesheet` governs whose entries the API returns
- A reported advisory: the API has returned timesheet entries a user shouldn't be authorised to see, and a missing voter check allowed cross-team manipulation. **Both are reasons to keep Kimai current** rather than to work around them.

```bash
curl -s -u 'user:api-token' https://kimai.example.com/api/timesheets | head -c 300
```

## 6. Can't remove a permission

A documented UI issue: unticking a permission for a role doesn't persist. Workarounds:

- Clear the cache after permission changes:

```bash
docker exec kimai bin/console cache:clear --env=prod
docker exec kimai bin/console kimai:reload
```

- Check the role actually saved by logging in as a member of it. The permission screen can show stale state.

## What not to do

- **Don't run Kimai's web server as root** to fix permissions. Fix ownership of `var/`.
- **Don't grant `export_timesheet` broadly** without testing what the user can see.
- **Don't skip `doctor`.** It checks everything in sections 1–2 in one command.
- **Don't stay on an old version.** Two separate authorisation advisories affect exactly this area.

## Prevention

| Habit | Why |
|---|---|
| `bin/console doctor` after every upgrade | Catches extension and permission drift |
| `var/` owned by the web user, verified | The dominant cause of export failures |
| `memory_limit 512M`, `max_execution_time 300` | Large ranges stop failing |
| Keep Kimai current | Authorisation fixes land in releases |

## FAQ

**Which export format is most reliable?**
CSV — no extensions, no templates, no memory spike. Use it to confirm the data is right, then investigate XLSX/PDF separately.

**Can I export on a schedule?**
Via the API plus a cron job on your side; there's no built-in scheduled export.

**Invoices fail the same way.**
Same mechanism: templates rendered into `var/`. The same checks apply.

**Exports are slow.**
Index coverage on large timesheet tables. Keep the database maintained and narrow the date range.
