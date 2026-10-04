---
title: "Synology SMB Not Working After a DSM Update? Check the SMB App Permission First"
slug: synology-smb-not-working-after-dsm-update
meta_description: "Windows can't reach your NAS after a DSM upgrade. The per-user SMB application permission, NTLM policy and protocol range explain almost every case."
updated: October 2026
cluster: round 10 (tech) — Synology community and synoforum threads only
competition: LOW
---

# Synology SMB Not Working After a DSM Update? Check the SMB App Permission First

You upgrade DSM, reboot, and Windows can no longer open your shares — wrong username or password, or the network path simply isn't found. Nothing on your PC changed.

Four causes cover nearly all of these, and the first one catches most people.

## 1. The per-user SMB application permission

DSM 7 introduced **application permissions per user**, and **SMB is one of those applications**. After an upgrade, users who worked fine on DSM 6 can find SMB **denied** at the application level — while their folder permissions look perfect, which is why people spend hours in the wrong place.

**Control Panel → User & Group → select the user → Applications**, and make sure **SMB** is **Allow**. Check it for every user and group that needs file access, including the one you log in with from Windows.

This is also the fix when **one** user can connect and another can't with identical folder permissions.

## 2. NTLM policy mismatch

Windows and DSM must agree on an authentication method. After upgrades, people hit `NTLMv1 not permitted` or a bare "wrong credentials" with correct credentials.

On the NAS: **Control Panel → File Services → SMB → Advanced Settings**. Look at the NTLM options there — enabling **NTLMv1** gets old clients working, but it's the weaker option and shouldn't be your resting state.

On Windows, the better fix is at the client: set the LAN Manager authentication level to **"Send NTLMv2 response only. Refuse LM & NTLM"** (Local Security Policy → Local Policies → Security Options, or the equivalent registry value on Home editions).

Prefer fixing the client. Turning NTLMv1 back on is a workaround with a security cost.

## 3. SMB protocol version range

The negotiated protocol can end up outside what your clients support — especially with a mix of Windows, macOS, TVs and older media players.

**Control Panel → File Services → SMB → Advanced Settings:**
- **Maximum SMB protocol: SMB3**
- **Minimum SMB protocol: SMB2**

SMB1 is off by default and should stay off; if a device needs SMB1, replace the device rather than the policy. On the Windows side, confirm **SMB 1.0/CIFS** isn't the only thing the client is trying, and that **SMB signing** requirements aren't conflicting.

## 4. Stale credentials and caches, on both ends

- **Windows:** `Control Panel → Credential Manager → Windows Credentials` — delete saved entries for the NAS (hostname **and** IP), then reconnect. Also run `net use * /delete` in a terminal to drop live sessions
- **NAS:** **File Services → SMB → Advanced Settings** has a **clear Samba cache** action. Disable SMB, wait, clear the cache, wait, re-enable
- Changing the user's **password** in DSM has fixed login failures for people — it regenerates the stored password hash in the format the current DSM expects

## If it's "network path not found" rather than a login failure

That's discovery/transport, not authentication:

- **SMB service is actually running** (File Services → SMB → Enable)
- Connect by **IP address**, not hostname: `\\192.168.1.x\share`. If IP works and hostname doesn't, it's name resolution — enable **WS-Discovery** on the NAS, and check Windows has network discovery on for your current network profile
- **Firewall** on the NAS (Control Panel → Security → Firewall) — an upgrade can re-apply a profile that blocks 445
- Windows network profile set to **Private**, not Public
- The NAS got a **new IP** from DHCP after reboot

## Order of operations

1. Connect by **IP** to separate auth from discovery
2. Check the user's **SMB application permission**
3. Clear **Windows credentials**, reconnect
4. Check **SMB min/max protocol**
5. Fix **NTLM** at the client
6. Clear the **Samba cache**, restart the service
7. Read **File Services logs** in DSM — they name the rejection reason

## FAQ

**Why did an update break SMB when I changed nothing?**
Upgrades re-apply defaults: application permissions, firewall profiles and protocol settings are the usual ones.

**Should I enable NTLMv1?**
Only as a temporary diagnostic. Fix the Windows client's NTLM level instead.

**Shares work on macOS but not Windows. Why?**
macOS and Windows negotiate differently; this is typically the NTLM or protocol-range issue, not permissions.

**Should I re-enable SMB1 for an old device?**
No. SMB1 is unsafe on a LAN with internet access. Replace or isolate the device.
