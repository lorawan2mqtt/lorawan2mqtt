ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12
FROM $BUILD_FROM

RUN pip3 install --no-cache-dir pyserial paho-mqtt

COPY ../src/lorawan2mqtt /opt/lorawan2mqtt/lorawan2mqtt
COPY run.sh /
RUN chmod a+x /run.sh

ENV PYTHONPATH=/opt/lorawan2mqtt
CMD ["/run.sh"]
