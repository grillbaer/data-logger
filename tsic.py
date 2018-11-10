#! /usr/bin/python3

"""
TSIC temperature sensor and ZACWire protocol support for Raspberry PI.
May be used as a command line tool for testing TSIC input.
"""

__all__ = [ 'ZacWireInputChannel', 'Measurement', 'TsicInputChannel', 'Error', 'PigpioNotConnectedError' ]

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from datetime import datetime
from functools import partial
import argparse
import logging

import pigpio
import threading
import time

logger = logging.getLogger().getChild(__name__) 


class Error(Exception):
    """
    Base class of exceptions from this module.
    """

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class PigpioNotConnectedError(Error):
    """
    Raised when pigpio.pi is not connected.
    """

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ZacWireInputChannel(object):
    """
    ZACWire protocol GPIO packet receiving handler. Receive packets
    of bytes consisting of 8 bits plus an even parity bit.
    """
    
    STATUS_OK = 0
    """ Received data is valid. """
    STATUS_PARITY_ERROR = 1
    """ Received data has a parity error. """
    STATUS_BIT_COUNT_ERROR = 2
    """ Received data has a wrong bit count. """
        
    def __init__(self, pigpio_pi, gpio):
        """
        Initialize ZACWire receiving channel on a GPIO.
        pigpio_pi is the pigpio.pi object to use for GPIO access.
        gpio is the GPIO as Broadcom chip number.
        Initializes the GPIO as input without pull-up or pull-down.
                
        Raises PigpioNotConnectedError if pigpio_pi is not connected.
        """
        self.pi = pigpio_pi
        self.gpio = gpio
        self.__pi_callback = None
        if self.pi.connected:
            self.pi.set_mode(self.gpio, pigpio.INPUT)
            self.pi.set_pull_up_down(self.gpio, pigpio.PUD_OFF)
        else:
            raise PigpioNotConnectedError('pigpio.pi is not connected, input for gpio ' + str(gpio) + ' will not work')

    def start(self, callback):
        """
        Start listening for data and pass received packet bytes
        to the a callback callback(status, [bytes]).
        Note that the callback is called by a pigpio thread.
        
        Exceptions from the callback function are logged with standard
        python logging.
        """
        self.stop()
        self.packet_callback = callback
        if self.pi.connected:
            self.__pi_callback = self.pi.callback(
                self.gpio,
                pigpio.EITHER_EDGE,
                lambda gpio, level, tick: self.__gpio_callback(gpio, level, tick))

    def stop(self):
        """
        Stop listening for data.
        """
        if self.__pi_callback is not None:
            self.pi.set_watchdog(self.gpio, 0) 
            self.__pi_callback.cancel()
            self.__pi_callback = None
        self.__reset_packet()
        self.__last_low_tick = None
        self.__last_high_tick = None
        
    def is_started(self):
        """
        Whether listening for data is running.
        """
        return self.__pi_callback is not None
    
    def __enter__(self):
        self.start(None)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
    def __call_packet_callback(self, status, packet_bytes):
        try:
            self.packet_callback(status, packet_bytes)
        except:
            logger.exception('Exception from callback' + str(self.packet_callback) + ' in ' + str(self))
        
    def __reset_packet(self):
        self.__bit_ticks = None
        self.__parity = 0
        self.__bit_count = 0
        self.__received_bytes = None

    def __pass_any_packet_to_callback(self, status):
        if self.__received_bytes is not None:
            # print('====> RECEIVED {0} STATUS {1}'.format(self.__received_bytes, status))
            self.__call_packet_callback(status, self.__received_bytes)
            self.__received_bytes = None
                        
    def __gpio_callback(self, gpio, level, tick):
        if level == pigpio.LOW:
            
            if self.__last_high_tick is not None:
                high_ticks = pigpio.tickDiff(self.__last_high_tick, tick)

                if high_ticks > 1000:
                    # packet start
                    # print('====> PACKET START')
                    self.__pass_any_packet_to_callback(self.STATUS_OK)
                    self.__received_bytes = [0]
                    self.__parity = 0
                    self.__bit_count = 0
                    self.__bit_ticks = None
                
                elif self.__received_bytes is not None and high_ticks > 150:
                    # next byte in packet
                    # print('====> NEXT BYTE START')
                    if self.__bit_count == 9:
                        self.__received_bytes.append(0)
                        self.__bit_ticks = None
                        self.__bit_count = 0
                        self.__parity = 0
                    else:
                        self.__pass_any_packet_to_callback(self.STATUS_BIT_COUNT_ERROR)
                        self.__reset_packet()
                        
            self.__last_low_tick = tick
            
        elif level == pigpio.HIGH:
            
            if self.__last_low_tick is not None:
                low_ticks = pigpio.tickDiff(self.__last_low_tick, tick)
                # print('{0} @ {1} -> {2}: {3}'.format(gpio, tick, level, low_ticks))
            
                if self.__received_bytes is not None:
                    if self.__bit_ticks is None:
                        # calibration T-strobe at begin of byte
                        self.__bit_ticks = low_ticks
                    else:
                        # a 0-bit has a short high interval, 1-bit a long high interval
                        bit = 0 if low_ticks > self.__bit_ticks else 1
                        if self.__bit_count < 8:
                            # data bit received
                            self.__received_bytes[-1] = self.__received_bytes[-1] * 2 + bit
                        self.__bit_count += 1
                        
                        self.__parity += bit
                        if self.__bit_count == 9:
                            self.__check_parity()
                            self.pi.set_watchdog(self.gpio, 1)  # 1 ms
                        elif self.__bit_count > 9:
                            # more bits than expected (8 bits + 1 __parity)
                            self.__pass_any_packet_to_callback(self.STATUS_BIT_COUNT_ERROR)
                            self.__reset_packet()
    
            self.__last_high_tick = tick

        elif level == pigpio.TIMEOUT:
            self.__pass_any_packet_to_callback(self.STATUS_OK)
            self.__reset_packet()
            
    def __check_parity(self):
        if self.__parity % 2 != 0:
            self.__pass_any_packet_to_callback(self.STATUS_PARITY_ERROR)
            self.__reset_packet()

    def __repr__(self, *args, **kwargs):
        return self.__class__.__name__ + ' for GPIO ' + str(self.gpio)


class Measurement(object):
    """
    Measurement consisting of the temperature degree_celsius and the timestamp
    seconds_since_epoch.
    """
    
    def __init__(self, degree_celsius, seconds_since_epoch):
        self.degree_celsius = degree_celsius
        self.seconds_since_epoch = seconds_since_epoch

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__

    def __repr__(self, *args, **kwargs):
        if self.degree_celsius is None:
            return 'Undefined'
        else:
            return (self.__class__.__name__ 
                  + ' {:.2f}°C at {}'
                        .format(self.degree_celsius,
                                datetime.fromtimestamp(self.seconds_since_epoch).isoformat(sep=' ')))


Measurement.UNDEF = Measurement(None, None)
""" Undefined measurement """
    

class TsicType(object):
    """
    Definition of a TSic type.
    """
    
    def __init__(self, name, bytes_to_celcius_func):
        self.name = name
        self.__bytes_to_celcius_func = bytes_to_celcius_func
    
    def bytes_to_degree_celcius(self, packet_bytes):
        """
        Decode the received bytes of a data packet to degrees celsius.
        """
        return self.__bytes_to_celcius_func(packet_bytes)
    
    def __repr__(self, *args, **kwargs):
        return self.name


def _tsic_11bit(packet_bytes, ht, lt):
    return ((packet_bytes[0] * 256 + packet_bytes[1]) / 2047. * (ht - lt) + lt)

def _tsic_14bit(packet_bytes, ht, lt):
    return ((packet_bytes[0] * 256 + packet_bytes[1]) / 16383. * (ht - lt) + lt)


TSIC206 = TsicType("TSic 206/306", partial(_tsic_11bit, ht=150, lt=-50))
""" TSic 206 with range from -50°C to 150°C, 11 bit resolution, +-0.5°C accuracy. Equivalent to TSIC306. """

TSIC306 = TSIC206
""" TSic 306 with range from -50°C to 150°C, 11 bit resolution, +-0.3°C accuracy. Equivalent to TSIC206. """

#TSIC316 = TsicType(partial(_tsic_14bit, ht=???, lt=???))
#""" TSic 316 with range from ???°C to ???°C, 14 bit resolution, +-???°C accuracy. """
# ??? data-sheet not available anywhere, but 316 mentioned in the application notes

TSIC506 = TsicType("TSic 506", partial(_tsic_11bit, ht=60, lt=-10))
""" TSic 506 with range from -10°C to 60°C, 11 bit resolution, +-0.1°C accuracy. """

TSIC716 = TsicType("TSic 716", partial(_tsic_14bit, ht=60, lt=-10))
""" TSic 716 with range from -10°C to 60°C, 14 bit resolution, +-0.07°C accuracy. """


class TsicInputChannel(object):
    """
    Receive temperature measurements from a TSIC sensor 
    connected to a Raspberry PI GPIO channel.
    The default temperature decoding is set to match TSIC 206/306. 
    Choose other tsic_type TSIC206, TSIC306, TSIC506, TSIC716 if necessary.
    """

    def __init__(self, pigpio_pi, gpio, tsic_type = TSIC306):
        """
        Initialize TSIC receiving channel.
        pigpio_pi is the pigpio.pi object to use for GPIO access.
        gpio is the as GPIO Broadcom chip number.
        tsic_type defines the temperature decoding.
        """
        self.tsic_type = tsic_type
        self.__callback = None
        self.__degree_celsius = None
        self.__timestamp = None
        self.__zacwire_channel = ZacWireInputChannel(pigpio_pi, gpio)
        self.__lock = threading.RLock()
        self.__measure_waiting = threading.Condition()

    def start(self, callback=None):
        """
        Start reading temperatures from the TSIC. Optionally pass each
        successfully received measurement to a callback callback(Measurement) 
        if callback is not None.
        
        Note that the callback is called by a pigpio thread.
        
        You can also fetch the last reading from property measurement.
        """
        self.stop()
        self.__callback = callback
        self.__zacwire_channel.start(lambda status, packet_bytes: self.__packet_received(status, packet_bytes))
    
    def stop(self):
        """
        Stop reading temperatures.
        """
        if self.__zacwire_channel is not None:
            self.__zacwire_channel.stop()

    def is_started(self):
        """
        Whether reading temperatures is currently running.
        """
        return self.__zacwire_channel.is_started()
    
    def __enter__(self):
        self.start(None)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
    def measure_once(self, timeout=None):
        """
        Wait up to optional timeout seconds for a measurement and 
        return the first successfully received measurement as
        Measurement or Measurement.UNDEF otherwise.
        Temporarily start and stop measurement if it is not yet running.
        """
        last_timestamp = self.__timestamp
        was_started = self.is_started()
        if not was_started:
            self.start()
            
        with self.__measure_waiting:
            self.__measure_waiting.wait(timeout)
        
        if not was_started:
            self.stop()
            
        measurement = self.measurement
        if last_timestamp != measurement.seconds_since_epoch:
            return measurement
        else:
            return Measurement.UNDEF
    
    @property    
    def measurement(self):
        """
        The last received measurement as Measurement.
        """
        with self.__lock:
            return Measurement(self.__degree_celsius, self.__timestamp)
                        
    def __packet_received(self, status, packet_bytes):
        if status == ZacWireInputChannel.STATUS_OK and len(packet_bytes) == 2:
            
            with self.__lock:
                self.__degree_celsius = self.tsic_type.bytes_to_degree_celcius(packet_bytes)
                self.__timestamp = time.time()
                measurement = self.measurement
            
            # print('====> Temperature {0}°C'.format(self.__degree_celsius))
            if self.__callback is not None:
                self.__callback(measurement)
                
            with self.__measure_waiting:
                self.__measure_waiting.notifyAll()

    def __repr__(self, *args, **kwargs):
        return self.__class__.__name__ + ' for GPIO ' + str(self.__zacwire_channel.gpio)


if __name__ == '__main__':
    
    tsic_types = { '206' : TSIC206,
                   '306' : TSIC306,
                   '506' : TSIC506,
                   '716' : TSIC716 }
    
    parser = argparse.ArgumentParser(description=
        '''Read temperatures from a TSic 206/306/506/716 sensor
           connected to a Raspberry PI GPIO pin.
           Select your TSic type to get correct temperatures.
           The default is TSic 206/306.''')
    parser.add_argument('gpio', type=int, help='GPIO pin as Broadcom number')
    parser.add_argument('--type', dest='type', choices=tsic_types.keys(), default='206', help='type of TSic sensor - 206/306 is default')
    parser.add_argument('--loop', dest='loop', action='store_const', const=True, default=False, help='print each received measurement until break')
    args = parser.parse_args()
    
    tsic_type = tsic_types[args.type]
    
    print("Receiving data from " + str(tsic_type) + "...")
    
    pi = pigpio.pi()
    tsic = TsicInputChannel(pi, args.gpio, tsic_type)
    try:
        if args.loop:
            tsic.start(callback=lambda m: print(m))
            # wait forever:
            threading.Semaphore(0).acquire()
        else:
            print(tsic.measure_once(timeout=1.0))
    except KeyboardInterrupt:
        pass
    finally:
        pi.stop()
