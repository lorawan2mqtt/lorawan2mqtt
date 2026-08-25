#!/usr/bin/with-contenv bashio
# Launch the lorawan2mqtt USB bridge with the add-on options and the MQTT
# credentials Home Assistant provides through the service discovery.
set -e

SERIAL_PORT=$(bashio::config 'serial_port')
BAUD=$(bashio::config 'baudrate')

MQTT_HOST=$(bashio::services mqtt "host")
MQTT_PORT=$(bashio::services mqtt "port")
MQTT_USER=$(bashio::services mqtt "username")
MQTT_PASS=$(bashio::services mqtt "password")

bashio::log.info "lorawan2mqtt: ${SERIAL_PORT} @ ${BAUD} -> mqtt://${MQTT_HOST}:${MQTT_PORT}"

exec python3 -m lorawan2mqtt.usb_bridge \
    --port "${SERIAL_PORT}" --baud "${BAUD}" \
    --mqtt-host "${MQTT_HOST}" --mqtt-port "${MQTT_PORT}" \
    --mqtt-user "${MQTT_USER}" --mqtt-pass "${MQTT_PASS}"
