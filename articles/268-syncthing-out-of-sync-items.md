---
title: "Syncthing 'Out of Sync Items' That Won't Clear? What Actually Causes It"
slug: syncthing-out-of-sync-items
meta_description: "A folder stuck at 99% with phantom out-of-sync items. Mismatched ignore patterns, ignoreDelete, permission errors and when resetting the database is the right move."
updated: October 2026
cluster: round 12 (tech) — Syncthing community forum threads
competition: LOW
---

# Syncthing 'Out of Sync Items' That Won't Clear? What Actually Causes It

A folder sits at 99%, the out-of-sync list names files that look fine (or don't exist), and nothing you do clears it.

## 1. Click the list first

In the web UI, click **"Out of Sync Items"** on the folder. Syncthing usually names the reason next to each file — permission denied, invalid filename, directory not empty. If there's a reason, stop here and fix that; the rest of this article is for the phantom cases.

## 2. Mismatched ignore patterns (the classic)

If `.stignore` differs between devices, files ignored on one side and not the other are **permanently out of sync** by definition: one device knows about a file it will never accept.

- Make `.stignore` **identical** on every device sharing the folder
- Watch out for `#include` files that exist on one device only
- Patterns with different path separators or cases across platforms
- The documented workaround when they *are* identical: **shut down both sides at the same time**, then start them — the state often clears

## 3. ignoreDelete

If you set the advanced **`ignoreDelete`** option on a folder, deletions aren't propagated — and a file deleted remotely but kept locally shows as out of sync forever. That's inherent: with `ignoreDelete` you cannot fully clear the state.

Decide whether you need it. If you turned it on to protect against accidental deletions, **versioning** is the better tool.

## 4. Case and filename conflicts

- **Case-insensitive filesystems** (macOS, Windows, some NAS shares) versus Linux: `File.txt` and `file.txt` can't coexist locally
- **Invalid characters** for the receiving platform (`:`, `?`, `|`, trailing dots/spaces are illegal on Windows)
- Paths over the platform's **length limit**
- These never resolve themselves — rename the offending file on the side where it's legal

## 5. Permissions and ownership

```bash
ls -la /path/to/folder
id syncthing
```

- The Syncthing user must be able to **write** the folder, not just read it
- `Ignore Permissions` on the folder is the pragmatic setting for shares that cross platforms
- On a NAS or with Docker, mismatched PUID/PGID produces files it can't modify, which it then reports as out of sync

## 6. Resetting indexes and the database

When it's genuinely phantom state — files listed that don't exist — this is the documented escalation path:

**Per folder (safer)**
- Stop Syncthing
- Use **"Revert Local Changes"** on a receive-only folder, or **Override Changes** on a send-only folder, as appropriate
- Or delete the **folder marker** and rescan

**Whole database (bigger hammer)**
```bash
# stop syncthing first
rm -rf ~/.local/state/syncthing/index-v0.14.0.db     # path varies by version/OS
# or use the UI: Actions → Advanced, or on Android: Reset Indexes / Reset Database
```

- **Reset Indexes** makes Syncthing re-exchange index data; it does **not** delete your files
- **Reset Database** rehashes everything from scratch — slow on large folders, and it's the Android option people report success with
- On the mobile side, setting folders to **Receive Only** first makes this safer

Back up before the bigger hammer. Nothing here should delete data, but a mistyped `rm -rf` will.

## 7. NFS and double-managed directories

A folder that's **also** shared over NFS/SMB and edited from elsewhere, or synced by a second tool, creates changes Syncthing can't reconcile. One folder, one sync tool.

## Prevention

1. **Identical `.stignore`** everywhere, kept in your notes
2. **Ignore Permissions** on cross-platform folders
3. Avoid filenames that are illegal on any participating platform
4. Use **versioning** instead of `ignoreDelete`
5. Don't let a second tool manage the same directory

## FAQ

**Does Reset Indexes delete my files?**
No. It rebuilds the index and re-exchanges metadata.

**Why does it say 99% forever?**
Usually ignore-pattern mismatch, an illegal filename, or a permission error on one file.

**Can I just ignore it?**
If you know which file and why, often yes — but you lose the signal that something real is wrong.

**Both sides have the same files. Why is it still out of sync?**
Phantom index state. Shut both down together, then try index reset.
