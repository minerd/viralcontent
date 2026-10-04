---
title: "Tasmota: Berry Script Works in the Console But Not in autoexec.be"
slug: tasmota-berry-autoexec-not-running
meta_description: "A Berry script runs when pasted and fails at boot. Wi-Fi and MQTT aren't up yet — use rules, keep functions fast, and watch the comment syntax."
updated: October 2026
cluster: round 14 (tech) — arendst/Tasmota discussions
competition: LOW
---

# Tasmota: Berry Script Works in the Console But Not in `autoexec.be`

The reason is timing, and it is not subtle once you see it:

> **`autoexec.be` runs before Tasmota connects to Wi-Fi and MQTT.** Anything depending on the network fails at that moment.

So a script that works when pasted into the console — by which time everything is connected — fails at boot.

## 1. Defer network-dependent code to a rule

Don't do work at the top level of `autoexec.be`. Register handlers instead:

```python
# autoexec.be

def on_boot()
  print("system booted")
end

def on_mqtt()
  tasmota.publish("tele/mydevice/status", "online")
end

tasmota.add_rule("System#Boot", on_boot)
tasmota.add_rule("Mqtt#Connected", on_mqtt)
tasmota.add_rule("Wifi#Connected", /-> print("wifi up"))
```

The documented guidance is exactly this: **using MQTT functions directly in `autoexec.be` cannot work**, and `tasmota.add_rule("Mqtt#Connected", ...)` is the supported pattern.

Useful triggers:

| Rule | Fires when |
|---|---|
| `System#Boot` | Tasmota core initialised — still no network |
| `Wifi#Connected` | Wi-Fi associated and IP assigned |
| `Mqtt#Connected` | Broker connection established |
| `Time#Initialized` | NTP time available |

If your script needs the clock (for scheduling), use `Time#Initialized`, not `System#Boot`.

Checking connection state at boot is unreliable for the same reason:

```python
# unreliable in autoexec.be — Wi-Fi isn't up yet
if tasmota.wifi("up") ... end
```

## 2. Berry must return quickly

> **Berry code must return quickly, preferably within 50 ms. Tasmota is blocked until the Berry function gives up control. Do not use do-while loops to wait.**

A busy-wait loop in `autoexec.be` hangs the device at boot — no web UI, no MQTT, sometimes a watchdog reset. This presents as "the script broke my device" and is the second most common cause here.

Use timers instead of waiting:

```python
def check_later()
  # do a bit of work
  tasmota.set_timer(5000, check_later)
end

tasmota.add_rule("Mqtt#Connected", /-> tasmota.set_timer(2000, check_later))
```

`set_timer` schedules a callback and returns immediately. Chain it for periodic work, or use `tasmota.add_cron` for schedule-driven tasks.

## 3. The comment syntax that eats your code

A real trap: `#-` starts a **block comment** that continues until `-#`. A line intended as a single-line comment but written with `#-` silently comments out everything after it:

```python
#- this looks like a comment -#     ← correct block comment
#- this one never closes            ← everything below is now a comment
def my_function()
  print("never runs")
end
```

Single-line comments use `#` alone:

```python
# this is a line comment
```

Symptom: part of your script simply doesn't exist, with no error. Check for an unclosed `#-` before anything else if functions are mysteriously undefined.

## 4. Globals and compile-time visibility

> **Berry needs to know globals at compile time, and `load` executes at runtime, so globals declared in sub-files may not be visible at compile time.**

If you split code across files:

```python
# autoexec.be
load("helpers.be")       # runs at runtime
my_helper()              # may fail: not known at compile time
```

Declare the global explicitly, or call it indirectly:

```python
var my_helper            # declare before load
load("helpers.be")
tasmota.set_timer(100, /-> my_helper())
```

Wrapping the call in a lambda defers resolution to runtime, which is usually enough.

## 5. Reading the actual error

```
Console → Tasmota console
```

Berry errors print to the console at boot, but the boot log scrolls fast. Two ways to catch it:

```
Status 0
BrRestart
```

`BrRestart` restarts the Berry VM and re-runs `autoexec.be` **with the console open**, so you see the error. This is the single most useful command for debugging `autoexec.be`.

Common messages:

- `unknown identifier` — a global not visible (section 4), or a typo
- `attribute_error` — calling a method on nil, typically an API not available yet (section 1)
- `stack overflow` — recursion, often an unguarded timer chain

## 6. The file isn't being loaded at all

```
Console: ls
```

Berry's `ls` lists the filesystem. `autoexec.be` must be in the root:

- **No filesystem.** Some builds (and some 1 MB flash devices) have no LittleFS partition, so there is nowhere to store `autoexec.be`. `ls` erroring means you need a build with a filesystem.
- **Wrong name.** `autoexec.bat` is the old rule-based autoexec; Berry's is `autoexec.be`. Having both is valid and they do different things.
- **The Berry feature isn't in your build.** `Status 2` shows the build features; tasmota32 includes Berry, some minimal ESP8266 builds do not.

## What not to do

- **Don't put MQTT or HTTP calls at the top level of `autoexec.be`.** Use rules.
- **Don't busy-wait.** It hangs the device.
- **Don't use `#-` for a single-line comment.**
- **Don't debug by reflashing.** `BrRestart` with the console open is faster and shows the error.

## Prevention

| Habit | Why |
|---|---|
| Everything in `autoexec.be` registers handlers, nothing acts | Matches Tasmota's boot order |
| `set_timer` / `add_cron` instead of loops | Keeps the device responsive |
| `BrRestart` after every edit, console open | You see the error immediately |
| Keep a copy of working scripts off-device | The filesystem is small and easy to clobber |

## FAQ

**Berry or the old scripting language?**
Berry is the current one and far more capable. The legacy Scripting console language still exists in some builds, with different syntax entirely.

**Can Berry drive I²C devices?**
Yes, with the I²C bus API, and that's a common reason to use it over rules.

**Does a Berry crash take the device down?**
A VM error is caught and printed; a busy loop or a stack overflow can trigger a watchdog reset.

**How big can the script be?**
Bounded by the filesystem and RAM. Keep it modest on ESP8266; ESP32 has considerably more headroom.
