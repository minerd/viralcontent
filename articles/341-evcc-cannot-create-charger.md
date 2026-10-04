---
title: "evcc: \"cannot create charger\" and Wallbox Not Detected"
slug: evcc-cannot-create-charger
meta_description: "evcc won't start, or the wallbox never appears. The chargers-versus-charger typo, OCPP timing, serial parameters and the template route."
updated: October 2026
cluster: round 13 (tech) — evcc GitHub issues and discussions
competition: LOW
---

# evcc: "cannot create charger" and Wallbox Not Detected

evcc validates its whole configuration at startup, so one bad charger block stops everything. The error chain tells you where to look, and it reads from the outside in:

```
cannot create loadpoint 'lp1': cannot create charger 'my_charger':
cannot create charger type 'template': missing parameter 'host'
```

Read the **last** line. That's the actual problem; everything above is context.

## 1. The YAML mistakes that cause most of these

**`chargers` vs `charger`.** The top-level list is `chargers:`; the reference inside a loadpoint is `charger:` (singular). Mixing them gives `invalid key: chargers` or a charger that can't be found.

```yaml
chargers:
  - name: my_charger
    type: template
    template: easee
    user: you@example.com
    password: secret

loadpoints:
  - title: Garage
    charger: my_charger      # singular, references the name above
    mode: pv
```

**Indentation.** evcc's config is deeply nested and a two-space slip puts `template:` at the wrong level, producing "missing parameter" errors for parameters you did supply.

Validate before restarting:

```bash
evcc check -c /etc/evcc.yaml
```

And let evcc write the config for you rather than hand-editing from a guide:

```bash
evcc configure
```

That walks through the device list, **tests each device as it goes**, and emits a config known to work. For a first setup it saves most of this article. Use `evcc configure --advanced` for templates not in the basic list.

## 2. OCPP chargers

```
cannot create charger type 'ocpp': cannot send request ..., no client exists
```

OCPP is **inbound**: the wallbox connects to evcc, not the other way round. So:

- evcc must be reachable from the wallbox on its OCPP port (default 8887), and that port must be published if evcc is in Docker.
- The wallbox's OCPP URL must point at evcc: `ws://192.168.1.10:8887/`
- The **station ID** in the wallbox must match the `stationid` in evcc's config, exactly.

```yaml
chargers:
  - name: wallbox
    type: template
    template: ocpp
    stationid: WB-001
    connector: 1
```

The error above means evcc started, the config is fine, and **no wallbox has connected yet**. evcc waits; check the wallbox's own OCPP status page. A startup timeout is normal if the wallbox is asleep — some only connect when a car is plugged in.

**`SetChargingProfile: Rejected`** is a different thing: the wallbox accepted the connection but refuses the current-limit command. Causes:

- The wallbox's own firmware needs updating
- An "Autostart"/"Free charging" mode on the wallbox overrides remote control — turn it off so OCPP is authoritative
- The requested current is below the wallbox's minimum (usually 6 A); evcc's `mincurrent` must be at or above it

## 3. Serial / Modbus chargers

```
cannot create charger type 'ablmh1': serial: ...
```

- **Serial parameters.** Many wallboxes use **8E1** (8 data bits, even parity, 1 stop bit), not the more common 8N1. A mismatch gives timeouts or garbage. evcc's templates set this correctly — a hand-written `modbus` block often doesn't.
- **Device path.** Use `/dev/serial/by-id/...`, never `/dev/ttyUSB0`, which moves.
- **Port in use.** One consumer per serial port. If another tool (a Modbus bridge, a logger) has it open, evcc can't.

```yaml
chargers:
  - name: wallbox
    type: template
    template: ablemh
    device: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A1B2C3-if00-port0
    baudrate: 38400
    comset: "8E1"
    id: 1
```

- **RS485 termination and A/B polarity.** Swapped A/B gives no communication at all, exactly like a wrong address. If the parameters are right and nothing answers, swap them.

## 4. EEBus chargers (Elli, some Audi/VW units)

```
cannot create charger 'template' cannot create charger 'eebus': eebus not configured
```

EEBus needs a certificate and a top-level `eebus:` section, which is separate from the charger:

```bash
evcc eebus-cert
```

That prints the `eebus:` block to paste into your config. Then the charger must be **paired** from the wallbox's side — the wallbox shows a pairing request that you accept in evcc's UI. Until pairing completes, the charger exists and reports nothing.

## 5. It worked, then stopped after an update

- **Template parameters change between evcc versions.** A renamed or newly-required parameter fails validation at startup. Read the release notes for your version; evcc's error names the parameter.
- **Wallbox firmware update changed its Modbus map or OCPP behaviour.** The evcc template may need updating too — check whether a newer evcc version includes a fix for your model.
- **DHCP change.** Static reservations for the wallbox, as for everything else on the network.

## What not to do

- **Don't hand-write a raw `modbus` charger** when a template exists. The template encodes the register map, the serial parameters and the quirks.
- **Don't run `evcc` with a config you haven't run `evcc check` on.** A startup failure takes your whole charging automation down.
- **Don't leave the wallbox's free-charging mode on** while expecting evcc to control current.
- **Don't set `mincurrent` below 6 A.** It's below the standard's minimum and will be rejected.

## Prevention

| Habit | Why |
|---|---|
| `evcc configure` for the initial config, edit from there | It tests each device as it builds |
| `evcc check` before every restart | Catches YAML and parameter errors without downtime |
| `/dev/serial/by-id` paths | Immune to enumeration order |
| Static IP for the wallbox | Removes a recurring failure |

## FAQ

**Does evcc need a wallbox at all?**
It can run with a "manual" charger for monitoring, but control needs a supported device.

**Can I use a plain smart plug?**
For a simple on/off charge at a fixed current, yes — there are templates for switch-based chargers. You lose current modulation.

**The car isn't detected but the charger is.**
Vehicle detection is separate: either via the charger's own identification, an API for your car brand, or by assigning a vehicle manually to the loadpoint.

**PV mode charges at the wrong times.**
That's a meter/grid-data problem, not a charger one. Check that your grid and PV meters report the expected sign for import/export.
