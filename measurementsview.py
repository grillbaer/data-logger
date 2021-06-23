"""
UI implementation of the measurements view.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import time

from kivy.clock import Clock
from kivy.clock import mainthread
from kivy.properties import BooleanProperty
from kivy.properties import StringProperty
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout

from signalsources import SignalSource, SignalValue

logger = logging.getLogger().getChild(__name__) 


class MeasurementsScreen(BoxLayout):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = None
        
    def use_signals_config(self, signal_sources_config):
        for group in signal_sources_config['groups']:
            group_label = group['label']
            group_widget = MeasurementsGroup(group_label)
            self.ids.columns.add_widget(group_widget)
            for source in group['sources']:
                logger.info('Adding signal {:12} > {:18} - {}'.format(group_label, source.label, str(source)))
                group_widget.add_source(source)
                source.start()
        

class MeasurementsGroup(BoxLayout):
    header_text = StringProperty()
    
    def __init__(self, header_text, **kwargs):
        super().__init__(**kwargs)
        self.header_text = header_text

    def add_source(self, source):
        self.ids.measurements_view.add_widget(MeasurementItem(source))


class MeasurementItem(BoxLayout):
    selected = BooleanProperty(False)
    label = StringProperty()
    value = StringProperty()
    unit = StringProperty()
    stale = BooleanProperty(False)
    small = BooleanProperty(False)
    signal_color = ListProperty()

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.label = source.label
        self.unit = source.unit
        self.signal_color = source.color
        self.small = source.small
        self.stale_clock = None
        self.update_value(SignalValue(0, SignalSource.STATUS_MISSING, time.time()))
        self.source.add_callback(self.update_value)

    @mainthread
    def update_value(self, signal_value):
        self.value = '---' if signal_value.status != SignalSource.STATUS_OK else self.source.format(signal_value.value)
        self.stale = signal_value.value is None or signal_value.status != SignalSource.STATUS_OK
        if not self.stale:
            self.start_stale_timer()

    def mark_stale(self, dt):
        self.stale = True
        self.stop_stale_timer()

    def start_stale_timer(self):
        self.stop_stale_timer()
        self.stale_clock = Clock.schedule_once(self.mark_stale, self.source.stale_secs)
        
    def stop_stale_timer(self):
        if not self.stale_clock is None:
            self.stale_clock.cancel()
            self.stale_clock = None
