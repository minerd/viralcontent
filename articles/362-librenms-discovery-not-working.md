---
title: "LibreNMS Discovery Not Finding Devices"
slug: librenms-discovery-not-working
meta_description: "Auto-discovery finds nothing while manual adds work. The cron job that isn't installed, discovery_by_ip, and the networks you have to declare."
updated: October 2026
cluster: round 14 (tech) — LibreNMS community forum
competition: LOW
---

# LibreNMS Discovery Not Finding Devices

Three things must all be true, and the usual situation is that only two are.

1. `snmp-scan.py` must actually run
2. The networks to scan must be declared
3. The devices must answer SNMP from the LibreNMS host

Test them in that order.

## 1. Run the scan by hand first

```bash
cd /opt/librenms
sudo -u librenms ./snmp-scan.py 192.168.1.0/24
```

If devices get discovered this way but never automatically, the scan is not scheduled. LibreNMS's default cron does **not** include `snmp-scan.py`:

```bash
# /etc/cron.d/librenms — add this line
0 1 * * *   librenms   /opt/librenms/snmp-scan.py >> /dev/null 2>&1
```

That is the whole answer for a large share of these reports. Discovery of *new* devices is a separate job from discovery of *already-added* devices' interfaces and sensors, and only the latter is scheduled out of the box.

## 2. Declare the networks

```php
// config.php
$config['nets'][] = '192.168.1.0/24';
$config['nets'][] = '10.0.0.0/16';
```

Or, in newer versions, set it in the web UI under **Settings → Discovery → Networks**. With no networks declared, `snmp-scan.py` run without an argument has nothing to scan.

Also relevant:

```php
$config['discovery_by_ip'] = true;
```

By default LibreNMS adds devices by **reverse DNS name**, not by IP. A device with no PTR record is discovered, then discarded because the hostname lookup fails. The symptom is a scan that reports finding hosts and adds none. Either populate reverse DNS (better long term) or set `discovery_by_ip`.

## 3. SNMP must answer from the LibreNMS host

```bash
snmpwalk -v2c -c public 192.168.1.50 sysDescr
snmpwalk -v3 -l authPriv -u monitor -a SHA -A authpass -x AES -X privpass 192.168.1.50 sysDescr
```

If that times out, nothing in LibreNMS will help. The checklist on the device side:

- SNMP service enabled
- The community string (v2c) or user (v3) matches what LibreNMS will use
- **The LibreNMS host's IP is permitted** in the device's SNMP ACL
- The device's firewall allows UDP/161 from LibreNMS

On Windows hosts this is four separate steps — add the SNMP feature, add the community, add LibreNMS to *Accepted hosts*, and allow it through the Windows firewall. Missing any one gives a silent timeout.

A restricted `snmpd.conf` is the other classic: a `view` that exposes only part of the tree makes the device discoverable but nearly dataless. Use the `snmpd.conf` shipped with LibreNMS as your baseline:

```
# /etc/snmp/snmpd.conf (net-snmp on a Linux target)
agentaddress udp:161
rocommunity YOURSTRING 192.168.1.10
extend .1.3.6.1.4.1.8072.1.3.2.4.1.2 distro /usr/bin/distro
```

## 4. ARP/CDP/LLDP-based discovery

Beyond ping sweeps, LibreNMS discovers neighbours from an already-monitored device's tables. For that to work:

- The seed device must be monitored and answering
- `$config['autodiscovery']['xdp'] = true;` and the ARP/OSPF/BGP equivalents must be enabled
- The discovered neighbour must still satisfy section 3

This path finds things a subnet scan misses, which is why adding one core switch properly is often more productive than scanning harder.

## 5. Check the validator before anything else

```bash
cd /opt/librenms && sudo -u librenms ./validate.php
```

It checks permissions, cron, database schema, PHP modules and more. A discovery problem caused by a broken install shows up here immediately, and chasing SNMP while the validator is red wastes an afternoon.

## What not to do

- **Don't scan /16 networks repeatedly.** It's slow and noisy; scan the subnets you actually use.
- **Don't use `public` as a community string** on anything reachable. SNMP v2c is plaintext.
- **Don't add devices by IP if you can fix reverse DNS.** Hostname-based entries survive re-addressing.
- **Don't skip `validate.php`.** It answers questions you'd otherwise spend hours on.

## Prevention

| Habit | Why |
|---|---|
| `snmp-scan.py` in cron from day one | The default install omits it |
| Reverse DNS for monitored hosts | Cleaner device names, no `discovery_by_ip` needed |
| SNMPv3 with auth and priv | The community-string model leaks everything |
| Run `validate.php` after every upgrade | Catches schema and permission drift |

## FAQ

**Discovery finds the device but no ports/sensors.**
That's the per-device discovery job, which is scheduled by default. Run `./discovery.php -h <device> -d` to see why.

**Can it discover without SNMP?**
There's agent-based and API-based polling for some targets, but the discovery model is SNMP-first.

**Devices appear then disappear.**
Check for a duplicate entry under a different name/IP, and for a polling failure marking it down.

**How long should a /24 scan take?**
Minutes. Hours means SNMP timeouts on every unused address — narrow the range.
