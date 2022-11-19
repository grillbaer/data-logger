"""
Definition of the different input signal sources that can be used for 
measurements.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2021, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import random
import re
import time
from typing import Callable, Any, Optional, NamedTuple, List

import pigpio
from tsic import TsicInputChannel, PigpioNotConnectedError

from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__)


class SignalValue(NamedTuple):
    value: float
    status: str
    timestamp: Optional[float]


class SignalSource:
    """
    Common signal source for measurement values.
    """
    STATUS_OK = 'ok'
    STATUS_MISSING = 'missing'

    SEND_MIN_DELTA = 0.5

    identifier: str

    label: str
    unit: str
    value_format: str

    color: List[float]
    z_order: int
    with_graph: bool
    small: bool

    stale_secs: float
    corr_offset: float

    callbacks: List[Callable[[SignalValue], None]]
    last_sent_timestamp: Optional[float]
    last_value: Optional[SignalValue]
    running: bool

    def __init__(self,
                 identifier: str,
                 label: str = 'Value',
                 unit: str = '',
                 value_format: str = '{:.1f}',
                 color: List[float] = [0.6, 0.6, 0.6, 1.0],
                 z_order: int = 0,
                 with_graph: bool = True,
                 small: bool = False,
                 stale_secs: float = 10,
                 corr_offset: float = 0.0):
        self.identifier = identifier
        self.label = label
        self.unit = unit
        self.value_format = value_format
        self.color = color
        self.z_order = z_order
        self.with_graph = with_graph
        self.small = small
        self.stale_secs = stale_secs
        self.corr_offset = corr_offset
        self.callbacks = []
        self.last_sent_timestamp = None
        self.last_value = None
        self.running = False

    def add_callback(self, callback: Callable[[SignalValue], None]) -> None:
        """
        Add a callback to receive signal values as
        callback(SignalValue).
        The callback may be called on arbitrary threads and must return quickly.
        """
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[SignalValue], None]) -> None:
        self.callbacks.remove(callback)

    def start(self) -> None:
        """
        Start sending measurements to the callbacks.
        Implementors must override this function to start measurement and
        call super().start(callback).
        Send signal values using _send(value, status).
        """
        logger.debug('Starting ' + str(self))
        self.running = True

    def stop(self) -> None:
        """
        Stop sending measurements.
        Implementors must override this function to stop measurement and
        call super().start(callback).       
        """
        logger.debug('Stopping ' + str(self))
        self.running = False

    def _send(self, value: float, status: str = STATUS_OK, timestamp: Optional[float] = None):
        if self.running:
            ts = time.time() if timestamp is None else timestamp
            self._send_signal_value(SignalValue(value + self.corr_offset, status, ts))

    def _send_signal_value(self, signal_value: SignalValue) -> None:
        if self.running:
            self.last_value = signal_value
            if self.last_sent_timestamp is None or self.last_sent_timestamp + SignalSource.SEND_MIN_DELTA <= signal_value.timestamp:
                self.last_sent_timestamp = signal_value.timestamp
                for callback in self.callbacks:
                    try:
                        callback(self.last_value)
                    except:
                        logger.exception('Exception from signal source callback ' + str(self))

    def format(self, value: float) -> str:
        return self.value_format.format(value)

    def __repr__(self) -> str:
        return self.__class__.__name__


class TestSource(SignalSource):
    """
    Random test measurement signal source.
    """

    def __init__(self, identifier: str, value: float, interval: float, **kwargs):
        super().__init__(identifier, **kwargs)
        self.value = value
        self.interval = interval
        self._timer = RepeatTimer(interval, self._send_random_value)

    def _send_random_value(self) -> None:
        self._send(round(random.gauss(self.value, 2), 3), self.STATUS_OK)

    def start(self) -> None:
        super().start()
        self._timer.start()

    def stop(self) -> None:
        super().stop()
        self._timer.cancel()


class TestDigitalSource(SignalSource):
    """
    Random test digital input signal source.
    """

    def __init__(self, identifier: str, interval: float, text_0: str = 'off', text_1: str = 'on', **kwargs):
        super().__init__(identifier, **kwargs)
        self.text_0 = text_0
        self.text_1 = text_1
        self._timer = RepeatTimer(interval, self._send_value)

    def _send_value(self) -> None:
        self._send(random.choice([0, 1]), self.STATUS_OK)

    def start(self) -> None:
        super().start()
        self._timer.start()

    def stop(self) -> None:
        super().stop()
        self._timer.cancel()

    def format(self, value: float) -> str:
        return self.text_1 if value != 0 else self.text_0


class DeltaSource(SignalSource):
    """
    Signal source that calculates the delta between two other signals.
    """

    def __init__(self, identifier: str, signal_a: SignalSource, signal_b: SignalSource, **kwargs):
        super().__init__(identifier, **kwargs)
        self.signal_a = signal_a
        self.signal_b = signal_b
        self.signal_a.add_callback(self._a_updated)
        self.signal_b.add_callback(self._b_updated)
        self._value_a = SignalValue(0, self.STATUS_MISSING, None)
        self._value_b = self._value_a

    def _a_updated(self, value: SignalValue) -> None:
        self._value_a = value
        self._send_value()

    def _b_updated(self, value: SignalValue) -> None:
        self._value_b = value
        self._send_value()

    def _send_value(self) -> None:
        if self._value_a == self.STATUS_MISSING or self._value_b == self.STATUS_MISSING:
            self._send(0, self.STATUS_MISSING)
        else:
            self._send(round(self._value_a.value - self._value_b.value, 3), self.STATUS_OK)


class MappingSource(SignalSource):
    """
    Signal source that maps its value from some other input.
    The mapping function must map (input_source, input_value) -> SignalValue.
    The input_source must have a method add_callback(callback_func(input_value)) and a start() method.
    """

    def __init__(self,
                 identifier: str,
                 input_source: Any,
                 mapping_func: Callable[[Any, Any], SignalValue],
                 **kwargs):
        super().__init__(identifier, **kwargs)
        self._input_source = input_source
        self._input_source.add_callback(self._updated)
        self._mapping_func = mapping_func

    def _updated(self, input_value) -> None:
        signal_value = self._mapping_func(self._input_source, input_value)
        if signal_value.timestamp is None:
            signal_value = SignalValue(signal_value.value, signal_value.status, time.time())
        self._send_signal_value(signal_value)

    def start(self) -> None:
        super().start()
        self._input_source.start()

    def stop(self) -> None:
        super().stop()
        self._input_source.stop()


class TsicSource(SignalSource):
    """
    Temperature measurement signal source from TSIC 206/306 connected to GPIO.
    """

    def __init__(self, identifier: str,
                 pigpio_pi: pigpio,
                 gpio_bcm: int,
                 **kwargs):
        super().__init__(identifier, **kwargs)
        try:
            self.__gpio = gpio_bcm
            self.tsic = TsicInputChannel(pigpio_pi, gpio_bcm)
        except Exception as e:
            logger.warning('Failed to initialize TSIC input channel: ' + str(e))
            # handle missing GPIO access for windows development
            self.tsic = None

    def start(self) -> None:
        super().start()
        if self.tsic is not None:
            self.tsic.start(lambda m: self._send(round(m.degree_celsius, 3), self.STATUS_OK))

    def stop(self) -> None:
        super().stop()
        if self.tsic is not None:
            self.tsic.stop()

    def __repr__(self) -> str:
        return super().__repr__() + ' bcm_gpio=' + str(self.__gpio)


class Ds1820Source(SignalSource):
    """
    Temperature measurement signal source from DS18x20 connected to W1 bus GPIO.
    """

    def __init__(self, identifier: str, sensor_id: str, interval: float, **kwargs):
        super().__init__(identifier, **kwargs)
        self.sensor_id = sensor_id
        self._timer = RepeatTimer(interval, self._read_and_send_value)

    def start(self) -> None:
        super().start()
        self._timer.start()

    def stop(self) -> None:
        super().stop()
        self._timer.cancel()

    def _read_and_send_value(self) -> None:
        temp = self.read_once()
        if temp is not None:
            self._send(round(temp, 3), self.STATUS_OK)

    def read_once(self) -> Optional[float]:
        try:
            with open('/sys/bus/w1/devices/' + self.sensor_id + '/w1_slave', 'r') as file:
                file.readline()
                temp_line = file.readline()
                match = re.search('.*t=(-?[0-9]+)', temp_line)
                if match is not None:
                    return float(match.group(1)) / 1000.
        except OSError:
            logger.warning("Failed to read DS1820 file for " + self.sensor_id)
        return None

    def __repr__(self) -> str:
        return super().__repr__() + ' id=' + self.sensor_id


class DigitalInSource(SignalSource):
    """
    Digital GPIO input signal source.
    """

    pi: pigpio

    def __init__(self,
                 identifier: str,
                 pigpio_pi: pigpio,
                 gpio_bcm: int,
                 interval: float,
                 text_0: str = 'off',
                 text_1: str = 'on',
                 **kwargs):
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

    def start(self) -> None:
        super().start()
        self._timer.start()

    def stop(self) -> None:
        super().stop()
        self._timer.cancel()

    def _read_and_send_value(self) -> None:
        reading = self.read_once()
        if reading is not None:
            self._send(reading, self.STATUS_OK)
        else:
            self._send(0, self.STATUS_MISSING)

    def read_once(self) -> Optional[int]:
        return self.pi.read(self.gpio_bcm) if self.pi.connected else None

    def format(self, value: float) -> str:
        return self.text_1 if value != 0 else self.text_0

    def __repr__(self) -> str:
        return super().__repr__() + ' gpio_bcm=' + str(self.gpio_bcm)


class PigpioTimestamp:
    """
    Timestamp from pi gpio which handles both the pigpio tick accuracy and
    also long durations without tick rollover.
    """
    ticks: int
    epoch_secs: float

    def __init__(self, ticks: int):
        self.ticks = ticks
        self.epoch_secs = time.time()

    def delta_secs_to(self, latter_timestamp: 'PigpioTimestamp') -> float:
        rough_delta_secs = latter_timestamp.epoch_secs - self.epoch_secs
        if rough_delta_secs >= 3600:  # pigpio ticks wrap around in about 71 minutes
            return rough_delta_secs
        else:
            return pigpio.tickDiff(self.ticks, latter_timestamp.ticks) / 1e6


class PulseSource(SignalSource):
    """
    Digital GPIO pulse counting and time delta measuring signal source.
    Useful for calculating rates, throughput or power from pulse sources.

    Output value calculation is performed by a passed lambda function
    calc_value_func(counter: int, delta_secs: float) -> Optional[float].
    """
    pi: pigpio
    gpio_bcm: int
    trigger_level: int
    dead_time_secs: float
    pulse_min_secs: float
    calc_value_func: Callable[[int, float], Optional[float]]

    counter: int
    delta_secs: Optional[float]

    _last_maybe_pulse_timestamp: Optional[PigpioTimestamp]
    _last_timestamp: Optional[PigpioTimestamp]

    def __init__(self,
                 identifier: str,
                 pigpio_pi: pigpio,
                 gpio_bcm: int,
                 trigger_level: int,
                 dead_time_secs: float,
                 pulse_min_secs: float,
                 calc_value_func: Callable[[int, float], Optional[float]],
                 **kwargs):
        super().__init__(identifier, **kwargs)
        self.pi = pigpio_pi
        self.gpio_bcm = gpio_bcm
        self.trigger_level = trigger_level
        self.dead_time_secs = dead_time_secs
        self.pulse_min_secs = pulse_min_secs
        self.calc_value_func = calc_value_func
        self.counter = 0
        self.delta_secs = None
        self._last_timestamp = None
        self._last_maybe_pulse_timestamp = None
        self.__pi_callback = None
        if self.pi.connected:
            self.pi.set_mode(self.gpio_bcm, pigpio.INPUT)
            self.pi.set_pull_up_down(self.gpio_bcm, pigpio.PUD_OFF)
        else:
            raise PigpioNotConnectedError(
                'pigpio.pi is not connected, pulse input for gpio ' + str(gpio_bcm) + ' will not work')

    def start(self) -> None:
        super().start()
        if self.pi.connected:
            self.__pi_callback = self.pi.callback(
                self.gpio_bcm, pigpio.EITHER_EDGE,
                lambda gpio, level, tick: self.__gpio_callback(gpio, level, tick))

    def stop(self) -> None:
        super().stop()
        if self.__pi_callback is not None:
            self.__pi_callback.cancel()
            self.__pi_callback = None

    def __gpio_callback(self, gpio: int, level: int, tick: int) -> None:
        timestamp = PigpioTimestamp(tick)
        # filter bouncing with requiring min pulse time:
        if self.trigger_level == level:
            self._last_maybe_pulse_timestamp = timestamp
            return
        else:
            if self._last_maybe_pulse_timestamp is not None:
                delta_secs = self._last_maybe_pulse_timestamp.delta_secs_to(timestamp)
                if delta_secs < self.pulse_min_secs:
                    return

        self.counter += 1
        if self._last_timestamp is not None:
            delta_secs = self._last_timestamp.delta_secs_to(timestamp)
            if delta_secs <= self.dead_time_secs:
                return

            self.delta_secs = delta_secs
            begin_ts = timestamp.epoch_secs - delta_secs
            value = self.calc_value_func(self.counter, self.delta_secs)
            logger.debug(
                'Pulse from gpio_bcm=' + str(self.gpio_bcm) +
                ' after ' + str(self.delta_secs) +
                ' secs => value=' + str(value))
            self._send(value, self.STATUS_OK if value is not None else self.STATUS_MISSING, timestamp=begin_ts)
        self._last_timestamp = timestamp

    def __repr__(self):
        return super().__repr__() + ' gpio_bcm=' + str(self.gpio_bcm)
