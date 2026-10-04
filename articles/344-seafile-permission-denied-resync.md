---
title: "Seafile: \"Permission denied on server. Please try to resync\""
slug: seafile-permission-denied-resync
meta_description: "A library stops syncing with a permission error after an ownership change, password reset, or read-only share. What resync actually fixes and what it doesn't."
updated: October 2026
cluster: round 13 (tech) — Seafile forum and GitHub issues
competition: LOW
---

# Seafile: "Permission denied on server. Please try to resync"

This message is almost always about the **sync auth token**, not about file permissions in the usual sense. Four events invalidate it, and the client's advice to resync is correct for three of them.

## 1. What invalidated the token

| Event | Why it breaks | Fix |
|---|---|---|
| Your password was reset | Sync tokens are derived per device from the login | Resync (re-enter credentials) |
| Library ownership transferred | The token referenced the old owner's permission | Resync |
| Sync token removed in the server admin | Explicit revocation | Resync |
| Library shared **read-only** and the client tries to write | Genuine permission refusal | Not a resync problem — section 3 |

The first three are the common ones, and in each case the data is intact on both ends. A resync re-establishes the token and compares content; it does **not** upload everything again from scratch for files that already match.

## 2. Doing the resync safely

```
Right-click the library in the client → Resync
```

Or, for a library that won't recover:

1. **Unsync** the library (this does not delete local files).
2. Note the local folder path.
3. **Sync** the library again, choosing that same existing folder.
4. The client indexes the local files and matches them against the server by content hash.

What actually happens matters here: Seafile compares and uploads only differences. If a local file differs from the server's version, you get a **conflict copy** (`filename (SFConflict user 2026-10-04).ext`) rather than silent loss. That's the behaviour you want, and it's why resync is safe — but it does mean you should search for `SFConflict` afterwards:

```bash
find ~/Seafile -name '*SFConflict*'
```

Resolve those by hand; the client won't merge them for you.

## 3. Read-only shares and SeaDrive

If the library was shared with you as **read-only**, write attempts are refused and no resync helps. Two specific situations create unexpected writes:

- **SeaDrive creating an empty update.** SeaDrive has been observed attempting to upload an empty change on a read-only library, producing continuous permission errors for a library you never touched. Updating the client is the real fix; it's been addressed in later versions.
- **Local applications writing metadata.** Thumbnail caches, `.DS_Store`, Office lock files and editor swap files all count as writes. On a read-only library, these generate errors with no user action at all. Exclude them in the client's ignore settings:

```
# seafile-ignore.txt in the library root
.DS_Store
Thumbs.db
~$*
*.tmp
.~lock.*
```

If you need to write, ask the sharer for read-write permission. The error is correct.

## 4. When resync doesn't fix it

**Library data corruption.** Run the server-side check:

```bash
cd /opt/seafile/seafile-server-latest
./seaf-fsck.sh -r <library-id>
```

Without `-r` it reports; with `-r` it repairs by discarding blocks it can't verify. Take a backup of the server's `seafile-data` first — `seaf-fsck` repair is not reversible.

To find the library id: in the web UI, the library's URL contains it, or use the admin panel's library list.

**GC needed.** After large deletions, run garbage collection with the server stopped:

```bash
./seafile.sh stop
./seaf-gc.sh
./seafile.sh start
```

Running GC with the server up can remove blocks in use.

**Clock skew.** Token validation is time-sensitive. A client or server hours out of sync produces authentication failures that read as permission problems. Check `date` on both.

**Reverse proxy stripping headers.** If the error appeared after a proxy change, confirm the proxy forwards the authorisation header and the original host:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 0;
}
```

`client_max_body_size 0` (unlimited) matters for large file uploads; a 413 partway through a sync can leave the client in a state where it reports permission errors on retry.

## 5. The Windows checkmark lie

A reported and confusing behaviour: after a password change, the Windows client shows a green checkmark — all synced — while no library is actually syncing. The tray state is not a reliable indicator here.

The check that tells the truth: open a library's details and look at the **last sync time**. Hours-old timestamps with a green icon mean the client is not syncing. Re-enter your credentials in the client's account settings.

## What not to do

- **Don't delete the local folder and re-download** to fix a permission error. You turn a token problem into a full re-download, and any local-only changes are lost.
- **Don't run `seaf-fsck -r` without a backup.** It discards what it can't verify.
- **Don't run `seaf-gc` with the server running.** It can delete live blocks.
- **Don't ignore `SFConflict` files.** They're your unmerged changes.

## Prevention

| Habit | Why |
|---|---|
| `seafile-ignore.txt` with OS and editor junk | Stops spurious writes on read-only libraries |
| Keep the client updated | Several of these are fixed client bugs |
| Check last-sync time, not the tray icon | The icon can lie after a credential change |
| Server-side backups of `seafile-data` and the databases | `seaf-fsck` repair and GC are both destructive |

## FAQ

**Does resync re-upload everything?**
No — it compares by content and transfers differences only. Large libraries still take time to index locally.

**Can I move the local folder?**
Unsync, move it, re-sync choosing the new location. Moving it while synced breaks the client's state.

**Seafile or Nextcloud for this use case?**
Seafile's block-level sync is faster for many small files; Nextcloud's app ecosystem is broader. The token-invalidation behaviour here is specific to Seafile's model.

**Error on one library only.**
That points at ownership or share permission for that library, not at your account.
