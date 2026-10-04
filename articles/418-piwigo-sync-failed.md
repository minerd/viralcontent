---
title: "Piwigo: Directory Synchronisation Fails"
slug: piwigo-sync-failed
meta_description: "Sync errors on filenames, SQL syntax errors from apostrophes, or wrong-filename warnings. Permissions, the filename regex and metadata sync."
updated: October 2026
cluster: round 14 (tech) — piwigo.org forum and Piwigo GitHub
competition: LOW
---

# Piwigo: Directory Synchronisation Fails

Synchronisation walks your `galleries/` tree and reconciles it with the database. Three classes of failure, all with specific fixes.

## 1. Permissions

The web server user must be able to **traverse and read** every directory being synchronised, and write to the upload and cache directories.

```bash
cd /var/www/piwigo
sudo chown -R www-data:www-data _data galleries upload
sudo find galleries -type d -exec chmod 755 {} \;
sudo find galleries -type f -exec chmod 644 {} \;
```

Verify as the web user, which is the only test that counts:

```bash
sudo -u www-data test -r /var/www/piwigo/galleries/2026/holiday && echo ok || echo NO
sudo -u www-data test -w /var/www/piwigo/_data && echo ok || echo NO
```

A directory missing the execute bit is readable-but-not-traversable, which produces an empty sync for that subtree with no error. That's the sneaky one.

## 2. Filenames

**"Wrong filename"** warnings come from Piwigo's filename validation, which by default rejects characters it considers unsafe — including **spaces**.

The supported way to loosen it is the **LocalFilesEditor** plugin, adding to your local configuration:

```php
// local/config/config.inc.php
$conf['sync_chars_regex'] = '/^[a-zA-Z0-9-_ .]+$/';
```

That adds the space. Widen it further only if you need to, and understand you're changing what Piwigo will accept into URLs and filesystem operations.

**Apostrophes break the SQL.** A documented bug: synchronising files whose names contain `'` produces a MySQL syntax error and aborts. The practical answer is to rename:

```bash
cd /var/www/piwigo/galleries
find . -name "*'*" -print
# rename them (dry run first)
find . -depth -name "*'*" | while read -r f; do
  echo mv -- "$f" "${f//\'/}"
done
```

Drop the `echo` once the output looks right. The same goes for other shell- and SQL-awkward characters: `"`, backticks, `;`, `&`. Unicode is generally fine; ASCII punctuation is the problem.

Rename **before** syncing. Renaming after means Piwigo holds database rows for paths that no longer exist, and you then need a second sync to clean up.

## 3. Metadata not picked up

After upgrading from very old versions, **metadata synchronisation is disabled by default**. EXIF dates, titles and IPTC keywords are then ignored, and photos get the file's modification time instead of the capture date.

```php
// local/config/config.inc.php
$conf['use_exif'] = true;
$conf['use_iptc'] = true;
$conf['use_exif_mapping'] = array(
    'date_creation' => 'DateTimeOriginal',
);
$conf['use_iptc_mapping'] = array(
    'keywords'        => '2#025',
    'name'            => '2#005',
    'comment'         => '2#120',
    'author'          => '2#122',
);
```

Then run a synchronisation with **"synchronise metadata"** selected — a plain file sync doesn't re-read metadata for files already in the database.

## 4. Sync times out on a large library

```ini
; php.ini
max_execution_time = 600
memory_limit = 512M
```

Piwigo's admin sync runs in a web request. For tens of thousands of files, raise the limits and **sync one album subtree at a time** rather than the whole root — the sync page lets you pick a directory. That's less fragile than one enormous run.

Behind a reverse proxy, raise the read timeout too, or you'll get a 504 while the sync continues server-side (and you won't know whether it finished).

## 5. Remote sync tools failing

Reported for desktop and mobile uploaders: **album creation fails because the API response changed** between Piwigo versions and the client's parser doesn't match.

- Update the client first; these get fixed.
- Check the API directly to see whether the server side is healthy:

```bash
curl -s 'https://piwigo.example.com/ws.php?format=json&method=pwg.categories.getList' | head -c 400
```

A valid JSON category list means Piwigo's API is fine and the client is the variable.

- `pwg.images.add` failing for **MP4** uploads is a known case; video support needs the VideoJS plugin and the correct allowed-extensions configuration:

```php
$conf['file_ext'] = array_merge($conf['file_ext'], array('mp4','MP4','webm','ogg'));
$conf['picture_ext'] = array_merge($conf['picture_ext'], array('mp4','MP4'));
```

## 6. Subfolders not synchronised

Piwigo maps directories to albums, and nesting works — but only for directories it can traverse (section 1) and only when you sync from a level **above** them. Syncing a leaf album won't discover new siblings.

```
galleries/
├── 2026/
│   ├── january/
│   └── february/
```

Sync `galleries/2026` to pick up `february`.

## What not to do

- **Don't widen `sync_chars_regex` to allow everything.** You'll push awkward characters into URLs and filesystem paths.
- **Don't rename files after syncing.** Rename first.
- **Don't sync 50,000 files in one web request.** Subtree at a time.
- **Don't edit `include/config_default.inc.php`.** Overrides go in `local/config/config.inc.php` and survive upgrades.

## Prevention

| Habit | Why |
|---|---|
| ASCII-safe filenames, no apostrophes | Removes the SQL and validation failures |
| Overrides in `local/config/config.inc.php` only | Survives every upgrade |
| Metadata sync enabled and mapped | Correct dates and keywords from the start |
| Sync subtree by subtree | Predictable, resumable, no timeouts |

## FAQ

**Does sync delete database entries for missing files?**
Only if you select that option. Leaving it off means orphaned entries accumulate; running it on a partially-mounted share deletes real data. Check your mounts first.

**Can I use a symlink into another disk?**
Piwigo follows symlinks if PHP can, but `open_basedir` often blocks it. A bind mount is more reliable.

**Thumbnails missing after sync.**
They're generated on demand into `_data/i/`; that directory must be writable.

**Upload via the web works, sync doesn't see files copied by SSH.**
Ownership — files copied as root aren't readable by the web user. `chown` them.
