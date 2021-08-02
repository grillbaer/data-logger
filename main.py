#! /usr/bin/python3

"""
Data Logger application.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2021, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

# initialize custom logging:
import log

import logging
from datetime import datetime
import time

from kivy.config import Config
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout

from mqttclient import MqttClient

# from signalsourcesconfig import signal_sources_config
from mocksignalsourcesconfig import signal_sources_config

logger = logging.getLogger().getChild(__name__)


class DataLoggerWidget(BoxLayout):
    """
    Main widget of the application.
    """
    status_text = StringProperty()
    time_text = StringProperty()
    date_text = StringProperty()

    SCREENSAVER_DELAY = 600

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clock_update_event = Clock.schedule_interval(self.update_clock, 1.)
        self.ids.measurements_screen.use_signals_config(signal_sources_config)
        self.ids.graphs_screen.use_signals_config(signal_sources_config)

        self._last_user_activity = time.time()
        self._screensaver_active = None
        self._activate_screensaver(False)

    def update_clock(self, *args):
        now = time.time()
        dt = datetime.fromtimestamp(now)
        self.time_text = '{:%H:%M:%S}'.format(dt)
        self.date_text = '{:%d.%m.%Y}'.format(dt)

        if self._last_user_activity is not None and self._last_user_activity < now - DataLoggerWidget.SCREENSAVER_DELAY:
            self._activate_screensaver(True)
            self._last_user_activity = None

    def on_touch_down(self, touch):
        self._last_user_activity = time.time()
        self._activate_screensaver(False)
        return super().on_touch_down(touch)

    def _activate_screensaver(self, activate):
        if self._screensaver_active != activate:
            self._screensaver_active = activate
            try:
                with open('/sys/class/backlight/rpi_backlight/bl_power', 'w') as file:
                    file.write('1' if activate else '0')
            except:
                logger.error('Could not ' + ('activate' if activate else 'deactivate') + ' screensaver')


class DataLoggerApp(App):

    def build(self):
        return DataLoggerWidget()


if __name__ == '__main__':
    logger.error('Starting application')
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '480')
    mqtt_client = MqttClient()
    mqtt_client.use_signals_config(signal_sources_config)
    mqtt_client.start()
    DataLoggerApp().run()
