# Dragino — built-in decoders

The lorawan2mqtt codec database has two families:

1. **Table codecs** — JSON files importable into the Awaro gateway, for fixed-layout frames only. The format is described in [`../README.md`](../README.md). Table codecs for other Dragino models live as JSON files next to this README.
2. **Built-in decoders** — shipped inside the Awaro gateway firmware as C code, for devices whose frames need bitmasks, conditionals or per-mode layouts that the table grammar cannot express.

This page documents the **built-in** Dragino decoders, for reference. They are C ports of the official JS decoders ([github.com/dragino/dragino-end-node-decoder](https://github.com/dragino/dragino-end-node-decoder)), pinned at: LHT52 (TTN decoder), LHT65N v1.5.6, S31-LB v1.3, CPL03-LB v1.1.1, T68DL v1.0, TrackerD v1.5.1, SN50_v3-LB (one decoder per work mode; no upstream version pinned).

## Conventions

- Output is **numeric-only**. Text statuses become 0/1 flags: `door`/`state*` → 1 = closed, `exti*` → 1 = triggered, `alarm*` → 1 = active.
- **Not decoded**: datalog retrieval frames (FPort 3 replays), device-ID frames, and payload timestamps — the gateway stamps every reception itself.
- Multi-byte values are read MSB-first (big-endian), as sent by Dragino nodes.

## Common device-status frame (FPort 5)

Every decoder below understands the common Dragino device-status frame on **FPort 5** (same layout for all products) and emits:

| Field | Unit | Meaning |
|---|---|---|
| `modele` | — | Sensor model code (byte 0) |
| `fw` | — | Firmware version, nibble-encoded (0x0130 → 1.30) |
| `bande` | — | Frequency band code (1 = EU868, 2 = US915, …) |
| `sous_bande` | — | Sub-band; omitted when 0xFF (none) |
| `bat` | V | Battery voltage (mV / 1000) |

## LHT52 — temperature/humidity + optional DS18B20 (TTN decoder)

Sensor uplink on **FPort 2** (≥ 11 bytes):

| Field | Unit | Meaning |
|---|---|---|
| `temp` | °C | Internal temperature (signed, ×0.01) |
| `hum` | % | Relative humidity (×0.1) |
| `temp_ds` | °C | DS18B20 probe temperature (×0.01); omitted when raw = 0x7FFF (no probe) |
| `ext` | — | External sensor type code (byte 6) |

## LHT65N — temperature/humidity + external sensor (v1.5.6)

Sensor uplink on **FPort 2** (≥ 11 bytes). Frames whose poll bits (byte 6, bits 7..6) are non-zero are datalog replays and are not decoded.

Ext types **0x09 / 0x0A** (timestamp variants) emit: `temp_ds` (0x09) or `temp_tmp117` (0x0A) in °C, `bat_status` (2-bit battery level 0–3), `temp` (°C), `hum` (%).

All other Ext types emit `bat` (V, 14-bit mV / 1000), plus `temp` (°C) and `hum` (%) except for Ext 0x0E/0x0F/0x10/0x20, plus `no_connect` = 1 when the external-sensor-absent bit (0x80) is set, then per Ext type (low 7 bits):

| Ext | Fields | Unit | Meaning |
|---|---|---|---|
| 0x01 | `temp_ds` | °C | DS18B20 (×0.01); omitted when raw = 0x7FFF |
| 0x02 | `temp_tmp117` | °C | TMP117 (×0.01) |
| 0x04 | `exti_level`, `exti_status` | — | Interrupt input level and trigger status (0/1) |
| 0x05 | `illum` | lx | Illuminance |
| 0x06 | `adc` | V | ADC input (mV / 1000) |
| 0x07 | `count` | — | 16-bit counter |
| 0x08 | `count` | — | 32-bit counter |
| 0x0B | `ext_temp`, `ext_hum` | °C, % | External SHT31 temperature/humidity |

## S31-LB — SHT31 temperature/humidity (v1.3)

Sensor uplink on **FPort 2** (≥ 11 bytes). The mode-31 min/max config frame is skipped. Note: newer S31 firmwares send 12-byte frames with extra mode bits set; the official v1.3 JS rejects those (`bytes.length == 11`), this decoder accepts them since temp/hum stay at the standard offsets.

| Field | Unit | Meaning |
|---|---|---|
| `bat` | V | Battery voltage (mV / 1000) |
| `temp` | °C | Temperature (signed, ×0.1) |
| `hum` | % | Relative humidity (×0.1) |
| `exti` | — | Interrupt flag (0/1) |
| `door` | — | Door contact, 1 = closed |

## CPL03-LB — contact / pulse counter (v1.1.1)

FPorts 3 and 4 (datalog / config echo) are not decoded.

**FPort 7** — interrupt snapshot, 3 inputs (bitmask of byte 0): `exti1`, `state1`, `exti2`, `state2`, `exti3`, `state3` (all 0/1; `exti` = triggered, `state` = contact closed).

**Regular uplink (FPort 2, ≥ 11 bytes)** — layout depends on the mode bit (byte 0, 0x08):

- *CPL03 mode* (bit set), 3 pulse counters: `pulse1`, `pulse2`, `pulse3` (24-bit counts) and `roc1`, `roc2`, `roc3` (ROC alarm flags, 0/1, from byte 10).
- *CPL01 mode* (bit clear), single contact: `alarm` (0/1), `open` (0/1), `pulses` (24-bit count), `duration` (s, 24-bit).

## T68DL — temperature datalogger (v1.0)

Sensor uplink on **FPort 2** (≥ 9 bytes):

| Field | Unit | Meaning |
|---|---|---|
| `bat` | V | Battery voltage (mV / 1000) |
| `temp` | °C | Temperature (signed, ×0.01) |
| `alarm_high` | — | High-threshold alarm (0/1) |
| `alarm_low` | — | Low-threshold alarm (0/1) |

## TrackerD — GPS tracker (v1.5.1)

BLE/WiFi positioning frames (FPorts 6, 8, 10) are not decoded.

**FPort 2 or 3** (≥ 11 bytes): `lat`, `lon` (°, signed, ×1e-6), `bat` (V, 14-bit mV / 1000), `alarm` (0/1), `motion` (0/1). On FPort 2, when the sensor flag (byte 10, bit 3) is clear and the frame has ≥ 15 bytes, also `hum` (%, ×0.1) and `temp` (°C, signed, ×0.1).

**FPort 4** (≥ 8 bytes, position + UTC frame): `lat`, `lon` only.

**FPort 7** (≥ 3 bytes, alarm heartbeat): `bat` (V), `alarm` (0/1).

## SN50_v3-LB — one decoder per work mode

Five built-in decoders, one per supported work mode (1, 3, 4, 6, 8). Sensor uplink on **FPort 2** (≥ 11 bytes).

**Common fields** (all supported modes): `mode` (work-mode code from the status byte), `bat` (V, mV / 1000), `temp1` (°C, ×0.1; omitted when raw = 0x7FFF), `adc1` (V, mV / 1000; not in mode 8), `din` (digital input, 0/1; not in modes 6 and 8), `exti` (0/1) and `door` (1 = closed; not in mode 6).

| Mode | Extra fields | Unit | Meaning |
|---|---|---|---|
| 1 — ultrasonic distance | `distance` | cm | Distance (×0.1); omitted when raw = 0 |
| | `dist_signal` | — | Ultrasonic signal level; omitted when raw = 0xFFFF |
| 3 — 3× DS18B20 | `temp2`, `temp3` | °C | Probe temperatures (×0.1); each omitted when raw = 0x7FFF |
| 4 — weight (HX711) | `weight` | g | 32-bit signed weight (official JS byte order kept) |
| 6 — 3× interrupt inputs | `exti1..3`, `state1..3` | — | Trigger flags and input states (0/1) |
| 8 — 3× DS18B20 + 2 counters | `temp2`, `temp3` | °C | Probe temperatures (×0.1); each omitted when raw = 0x7FFF |
| | `count1`, `count2` | — | 32-bit counters (only in 17-byte frames) |

All SN50v3 decoders also handle the FPort 5 device-status frame described above.
