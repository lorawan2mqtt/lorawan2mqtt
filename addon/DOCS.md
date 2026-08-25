# lorawan2mqtt USB bridge

Plug an [Awaro](https://awaro.fr) LoRaWAN gateway into your Home Assistant
server with a USB cable. The gateway decodes the sensor frames itself
(firmware 3.4.0+) and streams them as JSON lines over the serial port; this
add-on republishes them as MQTT discovery entities. Zero cloud, zero WiFi,
zero broker configuration on the gateway — the LoRaWAN equivalent of a
Zigbee USB dongle.

## Setup

1. Plug the gateway into a USB port of the Home Assistant machine.
2. Install the add-on, check `serial_port` (usually `/dev/ttyUSB0`).
3. Make sure the Mosquitto broker add-on is running (MQTT credentials are
   picked up automatically).
4. Start: your sensors appear in Home Assistant within one uplink period,
   with proper units and device classes.

Sensors are decoded **on the gateway** (built-in decoders + your custom decode
tables from the gateway's web page). The bridge itself is codec-agnostic.

Status: early preview — developed against firmware 3.4.0.
