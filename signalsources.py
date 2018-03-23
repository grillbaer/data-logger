"""
Definition of the different input signal sources that can be used for 
measurements.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from collections import namedtuple
import logging
import random
import re
import time

from tsic import TsicInputChannel
from kivy.tests.test_clock import callback
from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__) 

SignalValue = namedtuple('Value', ['value', 'status', 'timestamp'])


class SignalSource:
    """
    Common signal source for measurement values.
    """
    STATUS_OK = ''
    STATUS_MISSING = 'missing'
    
    SEND_MIN_DELTA = 0.5
   
    def __init__(self, label='Value', unit='', value_format='{:.1f}', color=[0.6, 0.6, 0.6, 1.0], z_order=0, with_graph=True):
        self.label = label
        self.unit = unit
        self.value_format = value_format
        self.color = color
        self.z_order = z_order
        self.with_graph = with_graph
        self.callbacks = []
        self.last_sent = None
        self.last_value = None
    
    def add_callback(self, callback):
        """
        Add a callback to receive signal values as
        callback(SignalValue).
        The callback may be called on arbitrary threads and must return quickly.
        """
        self.callbacks.append(callback)

    def remove_callback(self, callback):
        self.callbacks.remove(callback)
        
    def start(self):
        """
        Start sending measurements to the callbacks.
        Implementors must override this function to start measurement and
        call super().start(callback).
        Send signal using _send(value, status).
        """
        logger.debug('Starting ' + str(self))
        self.running = True
    
    def stop(self):
        """
        Stop sending measurements.
        Implementors must override this function to stop measurement and
        call super().start(callback).       
        """
        logger.debug('Stopping ' + str(self))
        self.running = False
    
    def _send(self, value, status):
        if self.running:
            timestamp = time.time()
            self.last_value = SignalValue(value, status, timestamp)
            if self.last_sent is None or self.last_sent + SignalSource.SEND_MIN_DELTA <= timestamp:
                self.last_sent = timestamp
                for callback in self.callbacks:
                    try:
                        callback(self.last_value)
                    except:
                        logger.exception('Exception from signal source callback ' + str(self))

    def __repr__(self):
        return self.__class__.__name__


class TestSource(SignalSource):
    """
    Random test measurement signal source.
    """

    def __init__(self, value, interval, **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.interval = interval
        self._timer = RepeatTimer(interval, self._send_value)
    
    def _send_value(self):
        self._send(random.gauss(self.value, 2), self.STATUS_OK)
        
    def start(self, *args):
        super().start(*args)
        self._timer.start()
    
    def stop(self, *args):
        super().stop(*args)
        self._timer.cancel()

 
class TsicSource(SignalSource):
    """
    Temperature measurement signal source from TSIC 206/306 connected to GPIO.
    """
     
    def __init__(self, pigpio_pi, gpio_bcm, **kwargs):
        super().__init__(**kwargs)
        try:
            self.__gpio = gpio_bcm
            self.tsic = TsicInputChannel(pigpio_pi, gpio_bcm)
        except Exception as e:
            logger.warn('Failed to initialize TSIC input channel: ' + str(e))
            # handle missing GPIO access for windows development
            self.tsic = None
         
    def start(self, *args):
        super().start(*args)
        if not self.tsic is None:
            self.tsic.start(lambda m: self._send(m.degree_celsius, self.STATUS_OK))
     
    def stop(self, *args):
        super().stop(*args)
        if not self.tsic is None:
            self.tsic.stop()

    def __repr__(self):
        return super().__repr__() + ' bcm_gpio=' + str(self.__gpio)

 
class Ds1820Source(SignalSource):
    """
    Temperature measurement signal source from DS18x20 connected to W1 bus GPIO.
    """
     
    def __init__(self, sensor_id, interval, **kwargs):
        super().__init__(**kwargs)
        self.sensor_id = sensor_id
        self._timer = RepeatTimer(interval, self._read_and_send_value)
         
    def start(self, *args):
        super().start(*args)
        self._timer.start()
     
    def stop(self, *args):
        super().stop(*args)
        self._timer.cancel()

    def _read_and_send_value(self):
        temp = self.read_once()
        if not temp is None:
            self._send(temp, self.STATUS_OK)
        
    def read_once(self):
        try:
            with open('/sys/bus/w1/devices/' + self.sensor_id + '/w1_slave', 'r') as file:
                file.readline()
                templine = file.readline()
                match = re.search('.*t=(-?[0-9]+)', templine)
                if not match is None:
                    return float(match.group(1)) / 1000.;
        except OSError:
            logger.warn("Failed to read DS1820 file for " + self.sensor_id)
        return None
    
    def __repr__(self):
        return super().__repr__() + ' id=' + self.sensor_id

