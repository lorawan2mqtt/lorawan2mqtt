# lorawan2mqtt

**Decode LoRaWAN sensor payloads into clean MQTT / Home Assistant data.**

Like [Zigbee2MQTT](https://www.zigbee2mqtt.io/), but for LoRaWAN sensors — without running a full
network server stack. This project is being built in the open, starting with its
foundation: a **community codec database** that turns raw LoRaWAN payloads into named,
typed values (`temperature = 24.1 °C`), one JSON file per sensor model.

## Status

| Component | Status |
|---|---|
| [Codec database](codecs/) | 🟢 open for contributions |
| Codec validator + CI | 🟢 working (`tools/validate.py`) |
| MQTT bridge (UDP packet forwarder → decoded MQTT + HA Discovery) | 🔜 planned |
| Home Assistant add-on | 🔜 planned |

## The codec format

A codec is a small JSON file describing how to read a sensor's payload:

```json
{
  "vendor": "acme",
  "model": "TH-1",
  "name": "acme-th1",
  "description": "Temperature & humidity sensor",
  "spec": "temp:i16@0/10#°C hum:u8@2#% bat:u16@3/1000#V",
  "tests": [
    { "fport": 2, "payload": "00F1480BB8",
      "expect": { "temp": 24.1, "hum": 72, "bat": 3.0 } }
  ]
}
```

The `spec` grammar is documented in [codecs/README.md](codecs/README.md).
Every codec ships with test vectors; CI replays them on every pull request.

These files are directly importable into the [Awaro gateway](https://github.com/Di-Ny/awaro)
(Decoders tab → *Import a file*), and will be the decoding engine of the upcoming bridge.
Contributing a codec makes your sensor work everywhere at once.

## Contributing

1. Copy [`codecs/example/example-sensor.json`](codecs/example/example-sensor.json) to `codecs/<vendor>/<model>.json`.
2. Fill in the fields and at least one real test vector (a payload captured from the sensor).
3. Check it locally: `python tools/validate.py`
4. Open a pull request.

No build environment needed — a codec is just a JSON file.

## Maintained by Awaro

This project is maintained by the team behind **[Awaro](https://awaro.fr)** — a plug-and-play
LoRaWAN gateway (ESP32-S3 + SX1302, 8 channels) with this decoding engine, a local network
server, MQTT / Home Assistant / Domoticz integrations built in, and no server to run.
If you want lorawan2mqtt without maintaining anything: that's the box.

## License

[MIT](LICENSE) — codecs included. Sensor payload layouts are published by their vendors;
each codec file credits its source.
