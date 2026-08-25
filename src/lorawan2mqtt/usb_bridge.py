"""USB bridge: Awaro gateway serial firehose -> MQTT + Home Assistant discovery.

The gateway streams every LoRaWAN event on its USB serial port as JSON lines
prefixed with "@LNS " (firmware 3.4.0+ includes the decoded fields with unit
and Home Assistant device class). This bridge needs ZERO codec knowledge:
plug the gateway into the Home Assistant server over USB, run the bridge,
and the sensors appear - no cloud, no WiFi, no LoRaWAN server to install.
"The Zigbee dongle of LoRaWAN."

Usage:
    python -m lorawan2mqtt.usb_bridge --port /dev/ttyUSB0 \
        --mqtt-host 127.0.0.1 --mqtt-port 1883 [--mqtt-user u --mqtt-pass p]

MQTT layout (retained):
    lorawan2mqtt/bridge/status                  online|offline (LWT)
    lorawan2mqtt/<deveui>/state                 {"temp": 21.4, ..., "rssi": -87}
    homeassistant/sensor/l2m_<deveui>_<field>/config   HA discovery
"""
import argparse
import json
import logging
import time

import serial  # pyserial
import paho.mqtt.client as mqtt

log = logging.getLogger("lorawan2mqtt.usb")

PREFIX = "@LNS "
DISCOVERY_ROOT = "homeassistant"
BASE = "lorawan2mqtt"

# Fields published as diagnostic entities on every sensor.
DIAG = {"rssi": ("dBm", "signal_strength"), "snr": ("dB", None), "sf": (None, None)}


def _discovery_payload(deveui, name, field, unit, dev_class, diagnostic=False):
    uid = f"l2m_{deveui.lower()}_{field}"
    payload = {
        "name": field.replace("_", " "),
        "unique_id": uid,
        "state_topic": f"{BASE}/{deveui}/state",
        "value_template": "{{ value_json.%s }}" % field,
        "availability_topic": f"{BASE}/bridge/status",
        "device": {
            "identifiers": [f"l2m_{deveui.lower()}"],
            "name": name or deveui,
            "manufacturer": "Awaro (lorawan2mqtt)",
            "model": "LoRaWAN sensor via USB gateway",
        },
    }
    if unit:
        payload["unit_of_measurement"] = unit
        payload["state_class"] = "measurement"
    if dev_class:
        payload["device_class"] = dev_class
    if diagnostic:
        payload["entity_category"] = "diagnostic"
    return uid, payload


class Bridge:
    def __init__(self, args):
        self.args = args
        self.announced = set()          # unique_ids already discovered
        try:    # paho-mqtt >= 2.0
            self.cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,
                                   client_id="lorawan2mqtt-usb",
                                   clean_session=True)
        except AttributeError:   # paho-mqtt 1.x
            self.cli = mqtt.Client(client_id="lorawan2mqtt-usb",
                                   clean_session=True)
        if args.mqtt_user:
            self.cli.username_pw_set(args.mqtt_user, args.mqtt_pass or None)
        self.cli.will_set(f"{BASE}/bridge/status", "offline", retain=True)

    # ---- MQTT ----------------------------------------------------------
    def connect_mqtt(self):
        while True:
            try:
                self.cli.connect(self.args.mqtt_host, self.args.mqtt_port,
                                 keepalive=60)
                self.cli.loop_start()
                self.cli.publish(f"{BASE}/bridge/status", "online", retain=True)
                log.info("MQTT connected to %s:%d",
                         self.args.mqtt_host, self.args.mqtt_port)
                return
            except OSError as e:
                log.warning("MQTT connect failed (%s), retry in 5 s", e)
                time.sleep(5)

    def announce(self, deveui, name, field, unit, dev_class, diagnostic=False):
        uid, payload = _discovery_payload(deveui, name, field, unit, dev_class,
                                          diagnostic)
        if uid in self.announced:
            return
        topic = f"{DISCOVERY_ROOT}/sensor/{uid}/config"
        self.cli.publish(topic, json.dumps(payload), retain=True)
        self.announced.add(uid)
        log.info("discovery: %s (%s%s)", uid, unit or "-",
                 f", {dev_class}" if dev_class else "")

    # ---- events --------------------------------------------------------
    def handle_line(self, line):
        if not line.startswith(PREFIX):
            return
        try:
            ev = json.loads(line[len(PREFIX):])
        except ValueError:
            log.debug("bad JSON skipped: %.80s", line)
            return
        if ev.get("type") != "up":
            log.info("event %s %s", ev.get("type"), ev.get("deveui", ""))
            return

        deveui = ev.get("deveui", "")
        if not deveui:
            return
        name = ev.get("name") or deveui
        state = {}
        for field, fv in (ev.get("fields") or {}).items():
            state[field] = fv.get("v")
            self.announce(deveui, name, field, fv.get("u") or None,
                          fv.get("c") or None)
        for field, (unit, cls) in DIAG.items():
            if field in ev:
                state[field] = ev[field]
                self.announce(deveui, name, field, unit, cls, diagnostic=True)
        state["fport"] = ev.get("fport")
        state["fcnt"] = ev.get("fcnt")
        state["raw"] = ev.get("data")
        self.cli.publish(f"{BASE}/{deveui}/state", json.dumps(state),
                         retain=True)
        log.info("up %s (%s): %d field(s)", name, deveui,
                 len(ev.get("fields") or {}))

    # ---- serial --------------------------------------------------------
    def run(self):
        self.connect_mqtt()
        while True:
            try:
                s = serial.Serial()
                s.port = self.args.port
                s.baudrate = self.args.baud
                s.timeout = 1
                # do not reset the gateway when opening the port
                s.rts = False
                s.dtr = False
                s.open()
                log.info("serial %s open", self.args.port)
                buf = b""
                while True:
                    chunk = s.read(4096)
                    if chunk:
                        buf += chunk
                        while b"\n" in buf:
                            raw, buf = buf.split(b"\n", 1)
                            self.handle_line(
                                raw.decode("utf-8", errors="replace").strip())
                        if len(buf) > 65536:   # runaway line safety
                            buf = b""
            except (serial.SerialException, OSError) as e:
                log.warning("serial error (%s), reopen in 5 s", e)
                time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", required=True, help="serial port of the gateway")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--mqtt-host", default="127.0.0.1")
    ap.add_argument("--mqtt-port", type=int, default=1883)
    ap.add_argument("--mqtt-user", default=None)
    ap.add_argument("--mqtt-pass", default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s")
    Bridge(args).run()


if __name__ == "__main__":
    main()
