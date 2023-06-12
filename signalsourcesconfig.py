"""
Configuration for a setup with various temperature sensors of type
DS18x20 and TSIC 306.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import time
from functools import partial
from typing import Any

import pigpio
from serial import Serial

from powermetersmlobis import PowerMeterSmlObisReader
from signalsources import TsicSource, Ds1820Source, DeltaSource, DigitalInSource, MappingSource, SignalSource, \
    SignalValue, PulseSource
from powermeterapatorec3 import PowerMeterApatorEC3Repeating, PowerMeterApatorEC3

try:
    with open("secret-mqtt-password", "r") as f:
        mqtt_password = f.read().strip()
except IOError:
    mqtt_password = ''

pigpio_pi = pigpio.pi()

power_meter_heat = PowerMeterApatorEC3Repeating(PowerMeterApatorEC3("/dev/serial0"), 10, 2*60)
power_meter_household = PowerMeterSmlObisReader(serial_factory=lambda: Serial(port="/dev/ttyUSB0", baudrate=9600))


def power_meter_hh_map_func(identifier: str, pmeter: PowerMeterSmlObisReader, _: Any) -> SignalValue:
    obis_value = pmeter.values_by_id.get(identifier)
    if obis_value is not None:
        return SignalValue(obis_value.numeric_value, SignalSource.STATUS_OK, time.time())
    else:
        return SignalValue(0., SignalSource.STATUS_MISSING, time.time())


_quelle_ein    = Ds1820Source(   'temp-from-well',           '28-0000089b1ca2', 1, label='Quelle ein',        unit='°C', value_format='{:.1f}',    color=[0.5, 0.5, 1.0, 1.0], z_order=1)
_quelle_aus    = Ds1820Source(   'temp-to-well',             '28-000008640446', 1, label='Quelle aus',        unit='°C', value_format='{:.1f}',    color=[0.0, 0.2, 1.0, 1.0], z_order=2)
_wp_hz_vor     = Ds1820Source(   'temp-hp-heat-supply',      '10-000801dd3c70', 1, label='Heizung Vorlauf',   unit='°C', value_format='{:.1f}',    color=[1.0, 0.0, 0.0, 1.0], z_order=1)
_wp_ww_vor     = TsicSource(     'temp-hp-water-supply',     pigpio_pi, 26,        label='Wasser Vorlauf',    unit='°C', value_format='{:.1f}',    color=[0.2, 0.3, 0.9, 1.0], z_order=0)
_wp_rueck      = TsicSource(     'temp-hp-return',           pigpio_pi, 12,        label='Rücklauf',          unit='°C', value_format='{:.1f}',    color=[0.5, 0.1, 0.7, 1.0], z_order=2)
_wp_mode       = DigitalInSource('mode-boiler',              pigpio_pi, 5,      1, label='Modus',             unit='',   text_0='HZ', text_1='WW', color=[0.4, 0.4, 0.4, 1.0], z_order=-1)
_hz_vor        = Ds1820Source(   'temp-heat-supply',         '10-000801f6dc25', 1, label='Heizung Vorlauf',   unit='°C', value_format='{:.1f}',    color=[1.0, 0.6, 0.6, 1.0], z_order=3)
_hz_rueck      = Ds1820Source(   'temp-heat-return',         '10-000801dd3975', 1, label='Heizung Rücklauf',  unit='°C', value_format='{:.1f}',    color=[0.7, 0.6, 1.0, 1.0], z_order=4)
_ww_speicher_o = TsicSource(     'temp-water-boiler-top',    pigpio_pi, 19,        label='Wasser oben',       unit='°C', value_format='{:.1f}',    color=[0.8, 0.7, 1.0, 1.0], z_order=-1, corr_offset=+2.5)
_ww_speicher_u = Ds1820Source(   'temp-water-boiler-middle', '28-0000089967c2', 1, label='Wasser mitte',      unit='°C', value_format='{:.1f}',    color=[0.4, 0.3, 0.5, 1.0], z_order=-2)
_ww_zirk       = Ds1820Source(   'temp-water-circ-return',   '28-0000089a5063', 1, label='Zirkulation',       unit='°C', value_format='{:.1f}',    color=[0.1, 0.6, 0.4, 1.0], z_order=-1)

_wasser_haupt_flow = PulseSource('flow-water-main',          pigpio_pi, 6,         label='Wasser Haupt',       unit='l/h', value_format='{:.1f}',   color=[0.2, 0.2, 0.8, 1.0], with_graph=False, stale_secs=5*60,
                                 trigger_level=pigpio.HIGH, dead_time_secs=4, pulse_min_secs=2,
                                 calc_value_func=lambda counter, delta_secs: 10.0*3600 / delta_secs)   # 1 pulse/ 10 l

_lu_frisch     = Ds1820Source(   'temp-air-fresh',           '28-000008656f81', 1, label='Frischluft',        unit='°C', value_format='{:.1f}',    color=[0.2, 0.8, 1.0, 1.0], z_order=-1)
_lu_fort       = Ds1820Source(   'temp-air-exhaust',         '10-000801dcfc0f', 1, label='Fortluft',          unit='°C', value_format='{:.1f}',    color=[0.7, 0.3, 0.1, 1.0], z_order=-1)
_lu_zu         = TsicSource(     'temp-air-supply',          pigpio_pi, 16,        label='Zuluft',            unit='°C', value_format='{:.1f}',    color=[0.7, 0.8, 0.9, 1.0], z_order=0)
_lu_ab         = TsicSource(     'temp-air-return',          pigpio_pi, 20,        label='Abluft',            unit='°C', value_format='{:.1f}',    color=[0.9, 0.6, 0.3, 1.0], z_order=0)
_lu_aussen     = TsicSource(     'temp-outdoor',             pigpio_pi, 21,        label='Außentemperatur',   unit='°C', value_format='{:.1f}',    color=[0.1, 0.5, 0.2, 1.0], z_order=1)

_ht_leistung   = MappingSource(  'power-heat-high-tariff',   power_meter_heat,     label='Leistung HT',       unit='W',  value_format='{:.0f}',    color=[0.9, 0.4, 0.1, 1.0], with_graph=False, stale_secs=10*60,
                                 mapping_func=lambda pmeter, reading: SignalValue(pmeter.high.power,
                                                                                  SignalSource.STATUS_OK if pmeter.success and pmeter.high.power is not None else SignalSource.STATUS_MISSING,
                                                                                  pmeter.high.power_from_ts))
_nt_leistung   = MappingSource(  'power-heat-low-tariff',    power_meter_heat,     label='Leistung NT',       unit='W',  value_format='{:.0f}',    color=[0.2, 0.3, 0.9, 1.0], with_graph=False, stale_secs=10*60,
                                 mapping_func=lambda pmeter, reading: SignalValue(pmeter.low.power,
                                                                                  SignalSource.STATUS_OK if pmeter.success and pmeter.low.power is not None else SignalSource.STATUS_MISSING,
                                                                                  pmeter.low.power_from_ts))
_ht_reading    = MappingSource(  'reading-heat-high-tariff', power_meter_heat,     label='Stand HT',          unit='kWh',value_format='{:.1f}',    color=[0.9, 0.4, 0.1, 0.5], with_graph=False, stale_secs=30, small=True,
                                 mapping_func=lambda pmeter, reading: SignalValue(reading.consumption_high_sum_kwh,
                                                                                  SignalSource.STATUS_OK if reading.consumption_high_sum_kwh is not None else SignalSource.STATUS_MISSING,
                                                                                  pmeter.reading_ts))
_nt_reading    = MappingSource(  'reading-heat-low-tariff', power_meter_heat,      label='Stand NT',          unit='kWh',value_format='{:.1f}',    color=[0.2, 0.3, 0.9, 0.5], with_graph=False, stale_secs=30, small=True,
                                 mapping_func=lambda pmeter, reading: SignalValue(reading.consumption_low_sum_kwh,
                                                                                  SignalSource.STATUS_OK if reading.consumption_low_sum_kwh is not None else SignalSource.STATUS_MISSING,
                                                                                  pmeter.reading_ts))
_hh_leistung   = MappingSource(  'power-household',         power_meter_household, label='Leistung Haushalt', unit='W',  value_format='{:.0f}',    color=[0.9, 0.8, 0.1, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "active_power"))
_hh_reading    = MappingSource(  'reading-household-import',power_meter_household, label='Stand Bezug',       unit='kWh',value_format='{:.1f}',    color=[0.9, 0.8, 0.1, 0.6], with_graph=False, stale_secs=10, small=True,
                                 mapping_func=partial(power_meter_hh_map_func, "energy_import"))
_hh_reading_exp= MappingSource(  'reading-household-export',power_meter_household, label='Stand Einsp.',      unit='kWh',value_format='{:.1f}',    color=[0.3, 1.0, 0.1, 0.6], with_graph=False, stale_secs=10, small=True,
                                 mapping_func=partial(power_meter_hh_map_func, "energy_export"))
_hh_frequency  = MappingSource(  'frequency-household',     power_meter_household, label=' Frequenz',         unit='Hz', value_format='{:.2f}',    color=[0.7, 0.7, 0.7, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "frequency"))
_hh_leistung_l1= MappingSource(  'power-household-l1',      power_meter_household, label=' Leistung L1 Hh.',  unit='W',  value_format='{:.0f}',    color=[0.6, 0.6, 0.4, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "active_power_l1"))
_hh_leistung_l2= MappingSource(  'power-household-l2',      power_meter_household, label=' Leistung L2 Hh.',  unit='W',  value_format='{:.0f}',    color=[0.6, 0.6, 0.4, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "active_power_l2"))
_hh_leistung_l3= MappingSource(  'power-household-l3',      power_meter_household, label=' Leistung L3 Hh.',  unit='W',  value_format='{:.0f}',    color=[0.6, 0.6, 0.4, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "active_power_l3"))
_hh_voltage_l1 = MappingSource(  'voltage-household-l1',    power_meter_household, label=' Spannung L1 Hh.',  unit='V',  value_format='{:.1f}',    color=[0.2, 0.6, 0.7, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "voltage_l1"))
_hh_voltage_l2 = MappingSource(  'voltage-household-l2',    power_meter_household, label=' Spannung L2 Hh.',  unit='V',  value_format='{:.1f}',    color=[0.2, 0.6, 0.7, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "voltage_l2"))
_hh_voltage_l3 = MappingSource(  'voltage-household-l3',    power_meter_household, label=' Spannung L3 Hh.',  unit='V',  value_format='{:.1f}',    color=[0.2, 0.6, 0.7, 1.0], with_graph=False, stale_secs=10,
                                 mapping_func=partial(power_meter_hh_map_func, "voltage_l3"))

signal_sources_config = {
    'groups' : [
        {'label' : 'Wärmepumpe',
         'sources' : [
            _quelle_ein,
            _quelle_aus,
            DeltaSource('temp-well-delta',     _quelle_ein, _quelle_aus, label='\u0394 Quelle',      unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _wp_hz_vor,
            _wp_mode,
            DeltaSource('temp-hp-heat-delta',  _wp_hz_vor, _wp_rueck,    label='\u0394 Heizung',     unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _wp_ww_vor,
            DeltaSource('temp-hp-water-delta', _wp_ww_vor, _wp_rueck,    label='\u0394 Wasser',      unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _wp_rueck,
        ]},
        {'label' : 'Heizung/Warmwasser',
         'sources' : [
            _hz_vor,
            _hz_rueck,
            DeltaSource('temp-heat-delta',              _hz_vor, _hz_rueck,       label='\u0394 Heizung',     unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            DeltaSource('temp-heat-supply-hp-delta',    _wp_hz_vor, _hz_vor,      label=' \u0394 WP-Hz Vor',  unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            DeltaSource('temp-heat-return-hp-delta',    _wp_rueck, _hz_rueck,     label=' \u0394 WP-Hz Rück', unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _ww_speicher_o,
            _ww_speicher_u,
            _ww_zirk,
            DeltaSource('temp-water-circ-return-delta', _ww_speicher_o, _ww_zirk, label='\u0394 Wasser-Zirk', unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _wasser_haupt_flow,
        ]},
        {'label' : 'Lüftung/Zähler',
         'sources' : [
            _lu_frisch,
            _lu_fort,
            DeltaSource('temp-air-fresh-exhaust-delta', _lu_fort, _lu_frisch,     label='\u0394 Fort-Frisch', unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _lu_zu,
            _lu_ab,
            DeltaSource('temp-air-supply-return-delta', _lu_ab, _lu_zu,           label='\u0394 Ab-Zu',       unit='K',  value_format='{:.1f}', color=[0.0, 0.0, 0.0, 1.0], with_graph = False),
            _lu_aussen,
            _ht_leistung,
            _nt_leistung,
            _ht_reading,
            _nt_reading,
            _hh_leistung,
            _hh_reading,
            _hh_reading_exp,
            _hh_frequency,
            _hh_leistung_l1,
            _hh_leistung_l2,
            _hh_leistung_l3,
            _hh_voltage_l1,
            _hh_voltage_l2,
            _hh_voltage_l3
        ]}
    ],

    'mqtt_broker_host' : 'homeserver.fritz.box',
    'mqtt_broker_port' : 8883,
    'mqtt_broker_user' : 'user',
    'mqtt_broker_password' : mqtt_password,
    'mqtt_broker_base_topic' : 'home/heating/data-logger',
    'mqtt_use_ssl': True,
    'mqtt_broker_ca_certs': 'mqtt_broker_cacert.pem'
}
