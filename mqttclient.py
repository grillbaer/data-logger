"""
MQTT client for sending measurements to a MQTT broker.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from signalsources import SignalSource
from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__)


class MqttClient:
    """
    Sends all signal changes to a MQTT broker.
    """

    DELTA_SECONDS_DEFAULT = 10  # seconds

    def __init__(self):
        self.broker_host = 'localhost'
        self.broker_user = ''
        self.broker_port = 1883
        self.broker_password = ''
        self.use_ssl = False
        self.broker_ca_certs = None
        self.broker_base_topic = 'datalogger'
        self.client = mqtt.Client()
        # self.client.enable_logger(logger)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.__started = False
        self.__timer = None
        self.delta_seconds = MqttClient.DELTA_SECONDS_DEFAULT
        self.sources = []

    def use_signals_config(self, signal_sources_config):
        self.broker_host = signal_sources_config['mqtt_broker_host']
        self.broker_port = signal_sources_config['mqtt_broker_port']
        self.broker_user = signal_sources_config['mqtt_broker_user']
        self.broker_password = signal_sources_config['mqtt_broker_password']
        self.use_ssl = signal_sources_config['mqtt_use_ssl']
        self.broker_ca_certs = signal_sources_config['mqtt_broker_ca_certs']
        self.broker_base_topic = signal_sources_config['mqtt_broker_base_topic']
        for group in signal_sources_config['groups']:
            for source in group['sources']:
                self.sources.append(source)

    def start(self):
        if not self.__started:
            if self.broker_host == '':
                logger.info("NOT starting MQTT client because of config with empty broker")
            else:
                logger.info("Starting MQTT client for broker " + self.broker_host)
                if self.broker_user != '':
                    self.client.username_pw_set(self.broker_user, self.broker_password)
                if self.use_ssl:
                    self.client.tls_set(ca_certs=self.broker_ca_certs)
                self.client.connect_async(self.broker_host, self.broker_port)
                self.client.loop_start()
                self.__timer = RepeatTimer(self.delta_seconds, self.publish)
                self.__timer.start()
                self.__started = True

    def stop(self):
        if self.__started:
            logger.info("Stopping MQTT client for broker " + self.broker_host)
            self.__started = False
            self.__timer.cancel()
            self.__timer = None
            self.client.disconnect()
            self.client.loop_stop(True)

    def publish(self):
        for source in self.sources:
            signal_value = source.last_value
            if signal_value is not None:
                topic = self.broker_base_topic + '/' + source.identifier
                json_value = json.dumps({
                    'value': signal_value.value,
                    'status': signal_value.status,
                    'formatted':
                        '---' if signal_value.status != SignalSource.STATUS_OK
                        else source.format(signal_value.value),
                    'timestamp': datetime.fromtimestamp(signal_value.timestamp).astimezone(timezone.utc).
                        strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'unit': source.unit
                })
                self.client.publish(topic, json_value, 0, True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker " + self.broker_host)
        else:
            logger.error("Failed to connect to MQTT broker " + self.broker_host + " rc=" + str(rc))
        # this would be the place to client.subscribe("#")

    def _on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("Disconnected from MQTT broker " + self.broker_host)
        else:
            logger.error("Connection lost to MQTT broker " + self.broker_host + " rc=" + str(rc))

    def _on_message(self, client, userdata, message):
        # this would be the place to receive subscription messages
        pass
