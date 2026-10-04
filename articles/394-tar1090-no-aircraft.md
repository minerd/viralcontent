---
title: "tar1090 Showing No Aircraft"
slug: tar1090-no-aircraft
meta_description: "\"No aircraft.json found\" or an empty map. tar1090 is a viewer, not a decoder — find out whether readsb/dump1090 is actually running."
updated: October 2026
cluster: round 14 (tech) — wiedehopf/tar1090 and FlightAware discussions
competition: LOW
---

# tar1090 Showing No Aircraft

The single most important fact: **tar1090 is a web interface, not a decoder.** It reads `aircraft.json` produced by readsb, dump1090 or dump1090-fa. An empty map means the decoder isn't producing data, isn't producing it where tar1090 looks, or isn't receiving anything.

```bash
systemctl status readsb       # or dump1090-fa
ls -la /run/readsb/aircraft.json
cat /run/readsb/aircraft.json | head -c 300
```

| What you find | Section |
|---|---|
| No such file | 1 |
| File exists, `"aircraft":[]` | 3 |
| File exists with aircraft, map still empty | 2 |

## 1. "No aircraft.json found in /run/readsb"

tar1090 is configured for one decoder's output path, and the paths differ:

| Decoder | JSON path |
|---|---|
| readsb | `/run/readsb` |
| dump1090-fa | `/run/dump1090-fa` |
| dump1090 (mutability) | `/run/dump1090-mutability` |

**If you switched decoders, you must reinstall or reconfigure tar1090** — it does not detect the change. That's the documented remedy and it applies to graphs1090 too:

```bash
sudo bash -c "$(wget -nv -O - https://github.com/wiedehopf/tar1090/raw/master/install.sh)"
```

Or set the source explicitly:

```bash
# /etc/default/tar1090
INTERVAL=1
HISTORY_SIZE=1500
```
and in `/usr/local/share/tar1090/`, the install script writes the source path — re-running the installer with the right decoder present is simpler than editing it.

Also check that the decoder is actually writing JSON. readsb needs the option:

```bash
# /etc/default/readsb
DECODER_OPTIONS="--write-json /run/readsb --write-json-every 1"
```

Without `--write-json`, readsb decodes happily and produces no file.

## 2. JSON has aircraft, map is empty

- **Browser cache.** Hard refresh. tar1090 caches aggressively.
- **Reverse proxy** not serving the JSON path. tar1090 fetches `data/aircraft.json` relative to its own URL; a proxy that only passes the HTML gives a working page with no data. Check the browser's devtools → Network for a failing request.
- **`https` page fetching `http` data** — mixed content blocked by the browser. Serve both over the same scheme.

## 3. Decoder running, zero aircraft

Now it's reception or the receiver.

```bash
journalctl -u readsb -n 50 --no-pager
```

**`usb_claim_interface error -6`** means something else has the dongle. Two decoders cannot share one SDR:

```bash
sudo systemctl stop dump1090-fa
sudo systemctl start readsb
```

That error is also produced by a leftover `rtl_433` or an SDR server. One process per dongle.

**`Beast TCP input: Connection to 127.0.0.1 port 30005 failed: 111 (Connection refused)`** — tar1090 or a feeder is trying to read from a decoder that isn't listening. The decoder must be up first; check its own status rather than the thing complaining.

**Zero messages received** points at hardware:

- **Antenna.** 1090 MHz needs a quarter-wave of about 6.9 cm, or a proper ADS-B antenna. A 433 MHz whip will see almost nothing.
- **Gain.** Too much gain on a strong-signal location is as bad as too little:

```bash
# /etc/default/readsb
RECEIVER_OPTIONS="--device-type rtlsdr --gain 40 --ppm 0"
```

Try a sweep: 20, 30, 40, 49.6. `wiedehopf`'s `graphs1090` shows message rate per gain setting, which is the honest way to tune it.

- **Line of sight.** ADS-B is line-of-sight at 1090 MHz. An antenna indoors on a ground floor may genuinely see nothing.
- **USB 3 interference.** Same rule as every SDR: extension cable, away from the case.

## 4. Aircraft appear and vanish instantly

- `HISTORY_SIZE` or the decoder's `--write-json-every` too large relative to the UI's refresh.
- Only **Mode S** (no position) being received: those aircraft show in the table with no position and no map marker, which looks like nothing is working. The message-rate graph distinguishes them.

## 5. Check end to end

```bash
# message rate
curl -s http://localhost/tar1090/data/stats.json | python3 -m json.tool | head -40
```

A non-zero `messages` with zero `positions` is reception without ADS-B position decodes — usually gain or antenna. Zero `messages` is no reception at all.

## What not to do

- **Don't run two decoders at once.** They fight over the dongle and both fail.
- **Don't switch decoders without reinstalling tar1090.** The path won't follow.
- **Don't max out the gain.** Over-gain produces fewer decodes, not more.
- **Don't debug tar1090 before confirming the JSON file.** It's one `ls` away.

## Prevention

| Habit | Why |
|---|---|
| One decoder, one dongle, documented | Removes the claim-interface class |
| Reinstall tar1090 after any decoder change | Its source path is baked at install time |
| graphs1090 installed alongside | Turns gain tuning into data instead of guessing |
| Antenna outdoors with clear sky view | The physical limit on everything else |

## FAQ

**readsb or dump1090-fa?**
readsb is actively developed and more configurable; dump1090-fa is what FlightAware's feeder expects. readsb can feed FlightAware too.

**Can I feed several aggregators?**
Yes — readsb outputs Beast on 30005 and each feeder connects to it.

**MLAT not working?**
It needs an accurate receiver position and a feeder client; it's separate from local decoding.

**Range seems poor.**
Antenna height and clear line of sight dominate everything else. Gain tuning is worth a few percent; a better location is worth multiples.
