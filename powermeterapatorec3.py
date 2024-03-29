"""
Communication with APATOR EC3 power meter to get its actual readings.
"""

from __future__ import annotations

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2021, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import time
from typing import NamedTuple, Optional, Callable, List

import serial
from serial import SEVENBITS, PARITY_EVEN, SerialException

from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__)


class PowerMeterReading(NamedTuple):
    success: bool
    consumption_total_sum_kwh: Optional[float]
    consumption_high_sum_kwh: Optional[float]
    consumption_low_sum_kwh: Optional[float]


class PowerMeterApatorEC3:
    """
    Communication object to get readings from an APATOR EC3 electrical power meter.
    Tested only with a 12EC3 two tariff version to get the readings for 1.8.1 and 1.8.2 OBIS values.
    Unfortunately, this meter does not provide any actual effective power values.

    Uses serial communication with the front IR interface.
    Sends a request to the power meter and reads it's response, i.e. a bidirectional
    TX/RX infrared interface must be connected to the serial port.
    Communication needs quite long timeouts and delays because the meter is reaaaaally slow.
    """

    serial_port: str
    _serial: Optional[serial.Serial]

    def __init__(self, serial_port: str):
        """
        Create new communication object for power meter.
        Does not yet open the serial port.

        :param serial_port: serial port to use, e.g. "COM5" on Windows or "/dev/serialUSB0" on Linux
        """
        self.serial_port = serial_port
        self._serial = None

    def open(self) -> None:
        """
        Open the serial port if not open yet. Don't forget to close it when not needed any more.

        :raises: serial.serialutil.SerialException
        """
        if self._serial is None:
            logger.info("Opening serial port " + self.serial_port)
            self._serial = \
                serial.Serial(self.serial_port,
                              baudrate=300, bytesize=SEVENBITS, parity=PARITY_EVEN,
                              timeout=10)

    def close(self) -> None:
        """
        Close the serial port if open.
        """
        if self._serial is not None:
            logger.info("Closing serial port " + self.serial_port)
            self._serial.close()
            self._serial = None

    def read_raw(self) -> str:
        """
        Read the raw response from the power meter.

        :return: raw response string

        :raises: serial.serialutil.SerialException if communication failed
        """
        logger.debug("Sending request on serial port ...")
        request = b'/?!\r\n'
        self._serial.write(request)
        self._serial.flush()
        time.sleep(2)

        ack_output = b'\x06000\r\n'
        self._serial.write(ack_output)
        self._serial.flush()
        time.sleep(2)

        logger.debug("Reading response from serial port ...")
        data = self._serial.read(65536)
        if len(data) > 0:
            logger.debug("Response:\n" + data.decode("ascii"))
        return data.decode("ascii")

    def read(self) -> PowerMeterReading:
        """
        Try to read values from the power meter. Automatically opens the serial interface
        if not yet open. Closes it upon SerialException to force reopening on next attempt.

        :return: reading with values for the case of success, empty reading in case of failure
        """
        try:
            self.open()
            return self._parse_raw(self.read_raw())
        except SerialException:
            self.close()
            return PowerMeterReading(False, None, None, None)

    def _parse_raw(self, raw: str) -> PowerMeterReading:
        high = None
        low = None

        for line in raw.splitlines(keepends=False):
            cleaned = line.strip('\x02\x03\n\r \t')
            if cleaned.startswith("1.8.1*"):
                high = self._parse_line_float(cleaned)
            elif cleaned.startswith("1.8.2*"):
                low = self._parse_line_float(cleaned)

        if high is not None and low is not None:
            total = high + low
        else:
            total = None

        return PowerMeterReading(True, total, high, low)

    def _parse_line_str(self, cleaned_line: str) -> Optional[str]:
        begin = cleaned_line.find("(") + 1
        end = cleaned_line.rfind(")")
        if begin != -1 and end != -1:
            return cleaned_line[begin:end]
        else:
            return None

    def _parse_line_float(self, cleaned_line: str) -> Optional[float]:
        try:
            return float(self._parse_line_str(cleaned_line))
        except ValueError:
            return None


class SingleCounter:
    _prev_reading: Optional[float]
    _prev_was_edge: bool
    power: Optional[float]
    power_from_ts: Optional[float]
    power_to_ts: Optional[float]

    def __init__(self):
        self._prev_reading = None
        self._prev_was_edge = False
        self.power = None
        self.power_from_ts = None
        self.power_to_ts = None

    def update(self, reading_kwh: Optional[float], reading_ts: float, min_averaging_secs: float,
               other_counter: SingleCounter):
        if reading_kwh is not None \
                and self._prev_reading != reading_kwh \
                and (self.power_to_ts is None or (reading_ts - self.power_to_ts) >= min_averaging_secs):
            if self._prev_was_edge and self.power_to_ts is not None:
                self.power = (reading_kwh - self._prev_reading) * 3.6e6 / \
                             (reading_ts - self.power_to_ts)
                self.power_from_ts = self.power_to_ts
                other_counter.power = 0
                other_counter.power_from_ts = self.power_from_ts
                other_counter._prev_was_edge = True

            if self._prev_reading is not None:
                self._prev_was_edge = True
            self._prev_reading = reading_kwh
            self.power_to_ts = reading_ts


class PowerMeterApatorEC3Repeating:
    min_averaging_secs: float
    _power_meter: PowerMeterApatorEC3
    _timer: RepeatTimer

    reading: Optional[PowerMeterReading]
    reading_ts: Optional[float]
    success: bool

    high: SingleCounter
    low: SingleCounter

    callbacks: List[Callable[[Optional[PowerMeterReading]], None]]

    def __init__(self, power_meter: PowerMeterApatorEC3, interval: float, min_averaging_secs: float):
        self.min_averaging_secs = min_averaging_secs
        self._power_meter = power_meter
        self._timer = RepeatTimer(interval, self._acquire)
        self.reading = None
        self.reading_ts = None
        self.success = False
        self.high = SingleCounter()
        self.low = SingleCounter()
        self.callbacks = []

    def add_callback(self, callback: Callable[[Optional[PowerMeterReading]], None]):
        self.callbacks.append(callback)

    def start(self):
        if not self._timer.is_alive():
            self._timer.start()

    def stop(self):
        self._timer.cancel()
        self._power_meter.close()

    def _acquire(self):
        try:
            ts = time.time()
            self.reading = self._power_meter.read()
            self.reading_ts = ts
            self._update_high_power()
            self._update_low_power()
            self.success = True
        except SerialException:
            self.success = False
        self._fire()

    def _update_low_power(self):
        self.low.update(self.reading.consumption_low_sum_kwh, self.reading_ts, self.min_averaging_secs, self.high)

    def _update_high_power(self):
        self.high.update(self.reading.consumption_high_sum_kwh, self.reading_ts, self.min_averaging_secs, self.low)

    def _fire(self):
        for callback in self.callbacks:
            callback(self.reading)


if __name__ == '__main__':
    pm = PowerMeterApatorEC3Repeating(PowerMeterApatorEC3("COM5"), 30, 10)
    pm.callbacks.append(lambda r: print(pm.success, r, pm.reading_ts, pm.low.power, pm.high.power))
    pm.start()
