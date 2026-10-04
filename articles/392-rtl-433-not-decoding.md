---
title: "rtl_433 Not Decoding Your Sensor"
slug: rtl-433-not-decoding
meta_description: "The SDR is recognised and nothing decodes. Frequency offset, sample rate, -G for all decoders, and the pulse analyser that identifies unknown devices."
updated: October 2026
cluster: round 14 (tech) — rtl_433 GitHub and the rtl_433 mailing list
competition: LOW
---

# rtl_433 Not Decoding Your Sensor

"SDR recognised, nothing decoded" has a short list of causes, and two of them are one-flag fixes.

## 1. Enable all decoders

Decoders that don't emit structured data are **disabled by default**. If your device is handled by one of them, you see nothing:

```bash
rtl_433 -G
```

`-G` enables every decoder including the disabled ones. It produces more noise and more false positives, which is why it isn't the default — but as a diagnostic it's the first thing to try. If your sensor appears with `-G`, note its decoder number and enable only that one:

```bash
rtl_433 -R 0 -R 12 -R 40      # only these decoders
```

## 2. Don't tune dead centre

A counter-intuitive but documented point: tuning exactly on the transmitter's frequency is worse than being slightly off. The RTL-SDR has a DC spike at the centre of its passband, which sits right on top of a signal tuned dead centre.

```bash
rtl_433 -f 433.92M                 # default
rtl_433 -f 433.94M                 # offset ~20 kHz
```

The default sample rate is 1 Msps, giving about 1 MHz of bandwidth, so a 10–20 kHz offset keeps the signal inside the passband and away from the spike.

Also correct the crystal error:

```bash
rtl_test -p            # measures ppm, let it run a minute
rtl_433 -p 42 -f 433.92M
```

A cheap dongle can be tens of ppm off, which at 433 MHz is tens of kHz — enough to miss narrow signals entirely.

## 3. Sample rate and signal levels

```bash
rtl_433 -s 1024k -M level -M noise -Y autolevel
```

- **`-s`** — a sample rate that's too low prevents some protocols decoding. 1024k is the default; 250k is enough for many OOK devices and uses far less CPU, but try the default first.
- **`-M level -M noise`** prints RSSI/SNR per detected pulse train. This is the key diagnostic: if you see pulses with poor SNR, you have a reception problem, not a decoding one. If you see nothing at all, the signal isn't arriving.
- **`-Y autolevel`** improves sensitivity on weak signals; **`-Y squelch`** reduces CPU on weak hardware.

Interpreting it:

```
*** signal_start = 12345, signal_end = 23456
Signal level: -0.1 dB  SNR: 24.0 dB
```

SNR above ~10 dB should decode if a decoder exists. Pulses with 3 dB SNR won't, and that's an antenna problem.

## 4. Reception hardware

If `-M level` shows nothing, fix the physical layer before touching flags:

- **Don't plug the dongle directly into the computer.** USB 3 ports and nearby SSDs radiate across 433 MHz. Use a short USB extension and move it away from the case — this is the single biggest improvement available, and it costs nothing.
- **Antenna length.** The stock whip is usually cut for a different band. A quarter-wave for 433 MHz is about 16.5 cm of wire; for 868 MHz, 8.2 cm. A correctly-cut wire beats the supplied antenna substantially.
- **Gain.** Automatic gain is usually fine; if a strong local transmitter is swamping the front end, fix it manually:

```bash
rtl_433 -g 30
```

## 5. The device isn't supported

```bash
rtl_433 -A
```

`-A` is the **pulse analyser**. It captures a transmission, measures the pulse and gap timings, and guesses the modulation — correctly most of the time. Output looks like:

```
Analyzing pulses...
Total count:   50,  width: 25.22 ms
Pulse width distribution:
 [ 0] count:   25,  width:  484 us
 [ 1] count:   25,  width:  980 us
Guessing modulation: Pulse Width Modulation with sync/delimiter
Attempting demodulation... short_width: 484, long_width: 980, ...
```

That output is what a decoder is written from, and it's what to attach to an issue report if your device isn't supported. Note that rtl_433 was built primarily for **weather station sensors and simple remotes** — a device using a proprietary FSK protocol with rolling encryption will never decode, and that's not a bug.

Record a sample for others to work with:

```bash
rtl_433 -f 433.92M -S unknown      # writes .cu8 files of unrecognised signals
```

## 6. Output and integration

Decodes appearing in the terminal but not in Home Assistant is a separate problem:

```bash
rtl_433 -F "mqtt://192.168.1.10:1883,user=mqttuser,pass=mqttpass,retain=1" \
        -F log -M time:iso -M protocol
```

`retain=1` matters: these sensors report every minute or two, and without retain Home Assistant shows them unavailable after a restart.

## What not to do

- **Don't run with `-G` permanently.** False positives from enabled-but-noisy decoders will pollute your data.
- **Don't plug the dongle into a USB 3 port.** You'll blame the software for an interference problem.
- **Don't run two rtl_433 instances on one dongle.** Only one process can own it.
- **Don't guess at a decoder.** Use `-A` and let it tell you.

## Prevention

| Habit | Why |
|---|---|
| USB extension cable, dongle away from the case | The biggest single sensitivity gain |
| Measured `-p` ppm value in your command line | Tens of kHz of error otherwise |
| `-R` with only the decoders you need | Less CPU, fewer false positives |
| `retain=1` on the MQTT output | Correct availability for infrequent sensors |

## FAQ

**868 MHz devices too?**
Yes: `-f 868.3M`. One instance per frequency, or use hopping (`-H`) and accept missed transmissions.

**Can one dongle cover 433 and 868?**
Only by hopping, which misses signals. Two dongles is the reliable answer.

**CPU usage is high.**
Lower the sample rate (`-s 250k`) and restrict decoders with `-R`.

**Values are wrong rather than missing.**
Two decoders matching the same signal. Restrict with `-R` to the correct one.
