# Codec database

One JSON file per sensor model, under `codecs/<vendor>/<model>.json`.

## File format

| Field | Required | Description |
|---|---|---|
| `vendor` | yes | Vendor slug, lowercase (`dragino`, `milesight`, …) — matches the directory name |
| `model` | yes | Commercial model name (`LHT65N`) |
| `name` | yes | Codec identifier: `[a-z0-9_-]`, **max 23 chars** (gateway limit). Convention: `<vendor>-<model>` |
| `description` | no | One line: what the sensor measures |
| `spec` | yes | The decode table (grammar below), **max 160 chars** (gateway limit) |
| `tests` | yes | At least one real captured payload with expected values |
| `source` | no | URL of the vendor's payload documentation or official decoder |
| `contributors` | no | List of GitHub handles |

## The `spec` grammar

Space- or `;`-separated fields, each:

```
field:type@offset[/div][#unit]
```

- **field** — value name, `[A-Za-z0-9_]`
- **type** — `u8 i8 u16 i16 u24 u32 i32 f32` (big-endian). Append `l` for
  little-endian multi-byte types: `u16l i16l u32l i32l f32l`
- **offset** — first byte position in the payload (0-based)
- **div** — optional decimal divisor applied to the raw value (`/10`, `/100`, `/1000`)
- **unit** — optional display unit; also drives the Home Assistant device class
  (`°C` → temperature, `%` → humidity, `V` → voltage, …)

Example — temperature (2 bytes, signed, tenths), humidity (1 byte), battery (2 bytes, mV):

```
temp:i16@0/10#°C hum:u8@2#% bat:u16@3/1000#V
```

Payload `00F1480BB8` decodes to `temp = 24.1 °C`, `hum = 72 %`, `bat = 3.0 V`.

### Limits (Awaro gateway compatibility)

- `name` ≤ 23 characters, `spec` ≤ 160 characters, ≤ 24 fields per codec.
- The grammar describes **fixed-layout frames**. Sensors whose layout changes with
  FPort or a mode byte (conditional frames, TLV formats) cannot be expressed as a
  table — those are handled by built-in decoders in the gateway firmware
  (Cayenne LPP, Dragino families, Milesight TLV, …) and documented here for
  reference only: see [`dragino/README.md`](dragino/README.md) and
  [`milesight/README.md`](milesight/README.md).

## Test vectors

```json
"tests": [
  { "fport": 2, "payload": "00F1480BB8",
    "expect": { "temp": 24.1, "hum": 72, "bat": 3.0 } }
]
```

- `payload` — hex string, as captured from the sensor (gateway *Recent packets* page,
  TTN / ChirpStack console, …)
- `expect` — decoded values (numbers). Compared with a small tolerance.
- Please capture **real frames** — a test vector fabricated from the datasheet often
  hides an endianness or offset mistake.

## Validating locally

```
python tools/validate.py            # whole database
python tools/validate.py codecs/acme/th-1.json
```

CI runs the same script on every pull request.
