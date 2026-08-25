# Milesight — generic built-in decoder

Unlike most vendors in this database, Milesight devices cannot be covered by
[table codecs](../README.md). Milesight uplinks are **TLV frames**: a sequence
of blocks, each made of a 1-byte `channel_id`, a 1-byte `channel_type` and a
value (multi-byte values little-endian). Which blocks appear, and in what
order, depends on what the device has to report in that frame — there is no
fixed byte layout to describe in a table. The Awaro gateway therefore ships a
single **generic built-in decoder** named `Milesight`, written in C inside the
firmware, that covers the whole range. This page documents it; there is
nothing to import.

Reference: the decoder dictionary was verified (2026-08-25) against the
official Milesight decoders,
[github.com/Milesight-IoT/SensorDecoders](https://github.com/Milesight-IoT/SensorDecoders)
(branch `main`).

## How the engine works

The decoder walks the payload block by block. Each `(channel_id, channel_type)`
pair is looked up in a single dictionary that maps it to a value size, a
conversion (u8, i16/10, u16/100, u32, bit 0, …) and an output field name/unit.
Known pairs are decoded (values little-endian) and emitted; device-info blocks
(channel `0xFF`: serial, hardware/firmware version, LoRaWAN class, …) are
consumed silently to keep the stream in sync. On the **first unknown pair the
engine stops** — from that point block lengths cannot be known — and returns
the fields already decoded, which is also what the official JS decoders do.
FPort is ignored (Milesight uses FPort 85, but the frames are self-described).

## Covered models

Dictionary verified against the upstream decoders for:

- **Indoor air quality**: AM103 / AM103L, AM308 (AM307 / AM319 family)
- **EM300 family**: EM300-TH, EM300-SLD, EM300-MCS
- **EM310-UDL**, **EM320-TH**
- **EM500 family**: EM500-CO2, EM500-LGT, EM500-PT100, EM500-SMTC,
  EM500-SWL, EM500-UDL, EM500-PP
- **WS series**: WS101 (smart button), WS202 (PIR & light), WS301 (door),
  WS303 (leak), WS523 (smart socket)
- **WT101** (thermostatic radiator valve)

Because the dictionary is keyed on `(channel, type)` pairs rather than on a
model, other Milesight devices that reuse the same pairs decode as well — but
only the list above has been verified.

## Field dictionary

Field names are emitted exactly as listed (the gateway's field names are in
French). One value per block; alarm fields deliberately use names distinct
from the plain measurement so a frame carrying both never produces duplicate
JSON keys.

### Measurements

| Ch   | Type | Field          | Unit   | Conversion | Notes |
|------|------|----------------|--------|------------|-------|
| 0x01 | 0x75 | `bat`          | %      | u8         | battery |
| 0x03 | 0x67 | `temp`         | °C     | i16 / 10   | shared by the whole range |
| 0x04 | 0x67 | `temp_cible`   | °C     | i16 / 10   | WT101 target temperature |
| 0x04 | 0x68 | `hum`          | %      | u8 / 2     | humidity |
| 0x04 | 0xCA | `humidite_sol` | %      | u16 / 100  | EM500-SMTC, sentinel-checked |
| 0x05 | 0x7F | `ec`           | µS/cm  | u16        | EM500-SMTC, sentinel-checked |
| 0x05 | 0x7D | `co2`          | ppm    | u16        | EM500-CO2 |
| 0x07 | 0x7D | `co2`          | ppm    | u16        | AM10x / AM3xx |
| 0x08 | 0x7D | `tvoc`         | —      | u16 / 100  | iAQ index |
| 0x08 | 0xE6 | `tvoc`         | µg/m³  | u16        | |
| 0x06 | 0x73 | `pression`     | hPa    | u16 / 10   | EM500-CO2 |
| 0x09 | 0x73 | `pression`     | hPa    | u16 / 10   | AM3xx |
| 0x0B | 0x7D | `pm_2_5`       | µg/m³  | u16        | |
| 0x0C | 0x7D | `pm10`         | µg/m³  | u16        | |
| 0x06 | 0xCB | `luminosite`   | —      | u8         | AM3xx light level |
| 0x0E | 0x01 | `buzzer`       | —      | u8         | |
| 0x03 | 0x82 | `distance`     | mm     | u16        | EM310 / EM500-UDL |
| 0x03 | 0x94 | `illum`        | lx     | u32        | EM500-LGT |
| 0x03 | 0x77 | `niveau`       | cm     | u16        | EM500-SWL, sentinel-checked |
| 0x03 | 0x7B | `pression`     | kPa    | i16        | EM500-PP |
| 0x05 | 0x92 | `vanne`        | %      | u8         | WT101 valve opening |
| 0x08 | 0xE5 | `calib`        | —      | u8         | WT101 motor calibration |
| 0x03 | 0x74 | `tension`      | V      | u16 / 10   | WS52x |
| 0x04 | 0x80 | `puissance`    | W      | u32        | WS52x |
| 0x05 | 0x81 | `cos_phi`      | —      | u8         | WS52x power factor |
| 0x06 | 0x83 | `energie`      | Wh     | u32        | WS52x |
| 0x07 | 0xC9 | `courant`      | mA     | u16        | WS52x |
| 0x08 | 0x70 | `prise`        | —      | bit 0      | WS52x socket state (0/1) |

WT101 motor stroke (`0x09/0x90`) and motor position (`0x0B/0x90`) are consumed
but not emitted.

### Status blocks (neutral names)

1-byte status blocks all use `channel_type 0x00`, and the same `(channel,
0x00)` pair means different things on different models (PIR on WS202, door on
WS301, leak on WS303, …). A brand-wide engine cannot pick a semantic name, so
these are emitted under **neutral names keyed on the channel** — the user maps
the meaning in Home Assistant / ThingsBoard:

| Ch   | Type | Field    | Meaning depending on model |
|------|------|----------|----------------------------|
| 0x03 | 0x00 | `etat3`  | PIR / door / leak |
| 0x04 | 0x00 | `etat4`  | tilt / daylight / tamper |
| 0x05 | 0x00 | `etat5`  | PIR / leak |
| 0x06 | 0x00 | `etat6`  | door / tamper |
| 0x07 | 0x00 | `etat7`  | window open (WT101) |
| 0x0A | 0x00 | `etat10` | freeze protection (WT101) |

All are 0/1 values.

### Events (channel 0xFF)

| Ch   | Type | Field       | Value |
|------|------|-------------|-------|
| 0xFF | 0x0B | `demarrage` | constant 1 (power-on event) |
| 0xFF | 0xFE | `reset`     | constant 1 |
| 0xFF | 0x2E | `bouton`    | WS101: 1 = short press, 2 = long, 3 = double |

The other channel-`0xFF` blocks (protocol version `0x01`, serial `0x08`/`0x16`,
hardware `0x09` / firmware `0x0A` version, LoRaWAN class `0x0F`, sensor-enable
bitmask `0x18`, measuring equipment `0x1B`, TSL version `0xFF`) are consumed
without emitting anything.

### Alarm frames

| Ch   | Type | Fields | Notes |
|------|------|--------|-------|
| 0x83 | 0xD7 | `temp_alarme` (°C, i16/10) + `code_alarme` (u8) | temperature threshold/mutation alarm |
| 0x83 | 0xE9 | `code_alarme` (u8) | distance alarm; the distance value itself is **dropped** (the upstream JS divides it by 10 while the plain distance is raw mm — the unit cannot be asserted), only the alarm code is kept |

Alarm names are distinct from the plain measurement (`temp` vs `temp_alarme`)
because both can travel in the same frame.

## Sentinel values

Milesight uses `0xFFFF` (read failed) and `0xFFFD` (out of range) as error
sentinels. The engine honours them **only on the pairs EM500-SMTC/SWL own
exclusively** — `0x04/0xCA` (soil moisture), `0x05/0x7F` (EC), `0x03/0x77`
(water depth): the field is skipped and parsing continues. They are **not**
applied to temperature `0x03/0x67`: that pair is shared by the whole range,
where the raw values `0xFFFF`/`0xFFFD` are the perfectly ordinary temperatures
−0.1 °C / −0.3 °C. This is the inherent limit of a brand-wide engine: a
model-specific rule cannot be applied to a pair several models share.

## Not covered

- **VS121** (AI people counter) is not covered.
- **History / datalog frames** (channel `0x20` / `0x21`) and **config echoes**
  (`0xFE`, `0xF8`, `0xF9`) have model-specific, variable layouts: the engine
  stops parsing when it reaches one (matching upstream behaviour on unknown
  blocks). Live fields already decoded from the same frame are kept.
