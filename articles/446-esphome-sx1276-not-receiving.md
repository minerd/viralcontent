---
title: "ESPHome and SX1276: Transmitting But Not Receiving LoRa Packets"
slug: esphome-sx1276-not-receiving
meta_description: "The module sends and never receives. Matching the radio parameters on both ends, the current the module needs, and where ESPHome's support actually stands."
updated: October 2026
cluster: round 14 (tech) — RadioLib discussions, Semtech forum, SparkFun community
competition: LOW
---

# ESPHome and SX1276: Transmitting But Not Receiving LoRa Packets

Set expectations first, because it saves a weekend: **ESPHome has no first-class SX127x/SX126x LoRa component.** Reported attempts with community `esphome-lora-sx126x`-style external components have been patchy, and the mature path for raw LoRa is an Arduino/ESP-IDF sketch using RadioLib, with ESPHome handling the rest of the device.

That said, the receive-failure causes are the same whichever framework you use.

## 1. Every radio parameter must match, exactly

LoRa receivers only hear transmissions with **identical** modulation parameters. A single mismatch gives perfect transmission and total silence at the other end.

| Parameter | Must match |
|---|---|
| Frequency | Yes |
| Spreading factor (SF) | Yes |
| Bandwidth (BW) | Yes |
| Coding rate (CR) | Yes |
| Sync word | Yes |
| Preamble length | Yes |
| Header mode (explicit/implicit) | Yes |
| CRC on/off | Yes |

```cpp
// RadioLib, both ends identical
radio.begin(868.1, 125.0, 9, 7, 0x12, 10, 8);
//          freq   BW    SF CR sync  pwr preamble
```

The two that catch people most:

- **Sync word.** RadioLib defaults differ from the Arduino-LoRa library's default (`0x12` vs `0x34`). Two devices using different libraries won't hear each other until you set it explicitly on both.
- **Implicit header mode.** If one end has a fixed payload length configured and the other doesn't, reception fails silently.

Print the configuration at boot on both devices and compare the lines side by side. That single discipline resolves most of these.

## 2. Current: the reason TX works and RX doesn't

A documented point with real consequences:

> **Some boards cannot supply enough current for the SX1276 in TX mode, which can cause lockups when sending — use an external 3.3 V supply capable of at least 120 mA.**

The failure is asymmetric and confusing: transmission at +20 dBm draws over 100 mA in bursts. A board whose regulator can't deliver it browns out the radio, which then **stops responding entirely** — including for receive. So the symptom is "it sent once and never received again".

What to do:

- Power the module from a supply that can deliver 150 mA+, not from an ESP dev board's 3V3 pin alone.
- Add bulk capacitance close to the module: 10 µF ceramic plus 100 µF electrolytic across 3V3 and GND.
- Reduce TX power while testing (`+10 dBm`) and see whether receive becomes reliable. If it does, the diagnosis is power.

```cpp
radio.setOutputPower(10);   // test at lower power
```

## 3. The antenna

Non-negotiable:

- **Never transmit without an antenna.** It can damage the PA, and a damaged PA transmits weakly and receives poorly afterwards.
- **Correct length for the band.** A quarter-wave at 868 MHz is about 8.2 cm; at 433 MHz about 16.5 cm. A 433 MHz whip on an 868 MHz module is a large loss both ways.
- The **RF switch** on some modules selects between the RFO and PA_BOOST pins. RadioLib's `setOutputPower` with the wrong `useRfo` setting transmits into the wrong pin — which can produce exactly this profile of working-ish TX and no RX.

## 4. SPI and the DIO pins

A module that answers SPI but never reports a received packet usually has a missing interrupt line:

```cpp
SX1276 radio = new Module(/*NSS*/ 5, /*DIO0*/ 26, /*RESET*/ 14, /*DIO1*/ 35);
```

- **DIO0** signals RX done and TX done. Without it, blocking transmit works and interrupt-driven receive never fires.
- **DIO1** is needed for timeouts in some modes.
- **RESET** must be connected; without it the module can come up in an undefined state after a brown-out and never recover.

Confirm SPI itself:

```cpp
int state = radio.begin();
Serial.println(state);   // 0 = success, -2 = chip not found
```

`-2` means SPI is wrong (wiring, NSS pin, or SPI bus). Anything else is configuration.

## 5. Frequency deviation and bit rate (FSK mode)

If you're using the SX1276 in **FSK** rather than LoRa mode, a documented pitfall:

> Issues arise from improper frequency deviation and bit rate configuration — combinations like 48 kbps with 150 kHz deviation and 200 kHz receiver bandwidth may be too narrow.

The rule of thumb: receiver bandwidth should be at least `2 × deviation + bit rate`. Compute it rather than copying values:

```
BW ≥ 2 × 150 kHz + 48 kbps ≈ 350 kHz
```

A 200 kHz bandwidth there simply cannot receive the signal. Most hobby projects are better off in LoRa mode, where the parameter interactions are simpler.

## 6. Integrating with ESPHome sensibly

Given the component situation, the pragmatic architecture:

- **A dedicated microcontroller** runs RadioLib and talks LoRa.
- It exposes readings over **UART or I²C** to an ESPHome device, or publishes **MQTT** itself.

```yaml
uart:
  id: lora_uart
  rx_pin: GPIO16
  tx_pin: GPIO17
  baud_rate: 9600

sensor:
  - platform: template
    name: "Remote Temperature"
    id: remote_temp
    unit_of_measurement: "°C"

text_sensor:
  - platform: custom
    # parse lines from the LoRa bridge
```

Or skip LoRa entirely for most sensor use cases: **ESP-NOW** or plain Wi-Fi with a well-placed access point covers far more ground than people expect, and Meshtastic handles long-range messaging with a maintained stack. Choose raw LoRa when you genuinely need kilometres and low power.

## What not to do

- **Don't transmit without an antenna.** It damages the module.
- **Don't power the module from the ESP's 3V3 pin** at high TX power.
- **Don't change one parameter on one end.** They must match exactly.
- **Don't expect an ESPHome LoRa component to exist.** Check before planning around it.

## Prevention

| Habit | Why |
|---|---|
| Print the full radio configuration at boot on both ends | Mismatches become obvious |
| Dedicated 3V3 supply with bulk capacitance | Removes the TX-brownout class |
| Correct antenna for the band, always attached | Protects the PA and halves your problems |
| RadioLib on a dedicated MCU, bridged to ESPHome | Matches where the mature code actually is |

## FAQ

**SX1276 or SX1262?**
The SX126x family is newer, more efficient and better supported in current RadioLib. Prefer it for new designs.

**Can two SX1276 modules share one ESP32?**
Yes on one SPI bus with separate NSS and DIO0 pins, but timing gets awkward. One radio per MCU is simpler.

**Range is poor.**
Antenna, height and line of sight dominate. A higher spreading factor trades data rate for sensitivity; SF12 at 125 kHz is very slow and very sensitive.

**Legal limits?**
Duty cycle and power limits are region-specific (868 MHz in Europe, 915 MHz in North America). Check your region before raising power or transmit frequency.
