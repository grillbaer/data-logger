"""
Definition of the different input signal sources that can be used for 
measurements.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import random
import re
import time
from collections import namedtuple
from typing import Callable, Any

import pigpio
from tsic import TsicInputChannel, PigpioNotConnectedError

from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__)

SignalValue = namedtuple('Value', ['value', 'status', 'timestamp'])


class SignalSource:
    """
    Common signal source for measurement values.
    """
    STATUS_OK = 'ok'
    STATUS_MISSING = 'missing'

    SEND_MIN_DELTA = 0.5

    def __init__(self,
                 identifier,
                 label='Value',
                 unit='',
                 value_format='{:.1f}',
                 color=[0.6, 0.6, 0.6, 1.0],
                 z_order=0,
                 with_graph=True,
                 corr_offset=0.0):
        self.identifier = identifier
        self.label = label
        self.unit = unit
        self.value_format = value_format
        self.color = color
        self.z_order = z_order
        self.with_graph = with_graph
        self.callbacks = []
        self.corr_offset = corr_offset
        self.last_sent = None
        self.last_value = None
        self.running = False

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
            self._send_signal_value(SignalValue(value + self.corr_offset, status, time.time()))

    def _send_signal_value(self, signal_value: SignalValue):
        if self.running:
            self.last_value = signal_value
            if self.last_sent is None or self.last_sent + SignalSource.SEND_MIN_DELTA <= signal_value.timestamp:
                self.last_sent = signal_value.timestamp
                for callback in self.callbacks:
                    try:
                        callback(self.last_value)
                    except:
                        logger.exception('Exception from signal source callback ' + str(self))

    def format(self, value):
        return self.value_format.format(value)

    def __repr__(self):
        return self.__class__.__name__


class TestSource(SignalSource):
    """
    Random test measurement signal source.
    """

    def __init__(self, identifier, value, interval, **kwargs):
        super().__init__(identifier, **kwargs)
        self.value = value
        self.interval = interval
        self._timer = RepeatTimer(interval, self._send_value)

    def _send_value(self):
        self._send(round(random.gauss(self.value, 2), 3), self.STATUS_OK)

    def start(self, *args):
        super().start(*args)
        self._timer.start()

    def stop(self, *args):
        super().stop(*args)
        self._timer.cancel()


class TestDigitalSource(SignalSource):
    """
    Random test digital input signal source.
    """

    def __init__(self, identifier, interval, text_0='off', text_1='on', **kwargs):
        super().__init__(identifier, **kwargs)
        self.text_0 = text_0
        self.text_1 = text_1
        self._timer = RepeatTimer(interval, self._send_value)

    def _send_value(self):
        self._send(random.choice([0, 1]), self.STATUS_OK)

    def start(self, *args):
        super().start(*args)
        self._timer.start()

    def stop(self, *args):
        super().stop(*args)
        self._timer.cancel()

    def format(self, value):
        return self.text_1 if value != 0 else self.text_0


class DeltaSource(SignalSource):
    """
    Signal source that calculates the delta between two other signals.
    """

    def __init__(self, identifier, signal_a, signal_b, **kwargs):
        super().__init__(identifier, **kwargs)
        self.signal_a = signal_a
        self.signal_b = signal_b
        self.signal_a.add_callback(self._a_updated)
        self.signal_b.add_callback(self._b_updated)
        self._value_a = self.STATUS_MISSING
        self._value_b = self.STATUS_MISSING

    def _a_updated(self, value):
        self._value_a = value
        self._send_value()

    def _b_updated(self, value):
        self._value_b = value
        self._send_value()

    def _send_value(self):
        if self._value_a == self.STATUS_MISSING or self._value_b == self.STATUS_MISSING:
            self._send(0, self.STATUS_MISSING)
        else:
            self._send(round(self._value_a.value - self._value_b.value, 3), self.STATUS_OK)

    def start(self, *args):
        super().start(*args)

    def stop(self, *args):
        super().stop(*args)


class MappingSource(SignalSource):
    """
    Signal source that maps its value from some other input.
    The mapping function must map (input_source, input_value) -> SignalValue.
    The input_source must have a method add_callback(callback_func(input_value)) and a start() method.
    """

    def __init__(self, identifier, input_source, mapping_func: Callable[[Any, Any], SignalValue],
                 **kwargs):
        super().__init__(identifier, **kwargs)
        self._input_source = input_source
        self._input_source.add_callback(self._updated)
        self._mapping_func = mapping_func

    def _updated(self, input_value):
        signal_value = self._mapping_func(self._input_source, input_value)
        self._send_signal_value(signal_value)

    def start(self, *args):
        super().start(*args)
        self._input_source.start()

    def stop(self, *args):
        super().stop(*args)


class TsicSource(SignalSource):
    """
    Temperature measurement signal source from TSIC 206/306 connected to GPIO.
    """

    def __init__(self, identifier, pigpio_pi, gpio_bcm, **kwargs):
        super().__init__(identifier, **kwargs)
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
            self.tsic.start(lambda m: self._send(round(m.degree_celsius, 3), self.STATUS_OK))

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

    def __init__(self, identifier, sensor_id, interval, **kwargs):
        super().__init__(identifier, **kwargs)
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
            self._send(round(temp, 3), self.STATUS_OK)

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


class DigitalInSource(SignalSource):
    """
    Digital GPIO input signal source.
    """

    def __init__(self, identifier, pigpio_pi, gpio_bcm, interval, text_0='off', text_1='on', **kwargs):
        super().__init__(identifier, **kwargs)
        self.pi = pigpio_pi
        self.gpio_bcm = gpio_bcm
        self.interval = interval
        self.text_0 = text_0
        self.text_1 = text_1
        if self.pi.connected:
            self.pi.set_mode(self.gpio_bcm, pigpio.INPUT)
            self.pi.set_pull_up_down(self.gpio_bcm, pigpio.PUD_OFF)
        else:
            raise PigpioNotConnectedError(
                'pigpio.pi is not connected, input for gpio ' + str(gpio_bcm) + ' will not work')
        self._timer = RepeatTimer(interval, self._read_and_send_value)

    def start(self, *args):
        super().start(*args)
        self._timer.start()

    def stop(self, *args):
        super().stop(*args)
        self._timer.cancel()

    def _read_and_send_value(self):
        reading = self.read_once()
        if not reading is None:
            self._send(reading, self.STATUS_OK)
        else:
            self._send(0, self.STATUS_MISSING)

    def read_once(self):
        return self.pi.read(self.gpio_bcm) if self.pi.connected else None

    def format(self, value):
        return self.text_1 if value != 0 else self.text_0

    def __repr__(self):
        return super().__repr__() + ' gpio_bcm=' + str(self.gpio_bcm)
