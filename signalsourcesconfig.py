"""
Configuration for a setup with various temperature sensors of type
DS18x20 and TSIC 306.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import pigpio

from signalsources import TsicSource
from signalsources import Ds1820Source

pigpio_pi = pigpio.pi()

signal_sources_config = {
    'groups' : [
        {'label' : 'Wärmepumpe',
         'sources' : [
            TsicSource(pigpio_pi, 19,          label='Quelle ein',       unit='°C', value_format='{:.1f}', color=[0.5, 0.5, 1.0, 1.0], z_order=1),
            Ds1820Source('10-000801dd1e03', 1, label='Quelle aus',       unit='°C', value_format='{:.1f}', color=[0.0, 0.2, 1.0, 1.0], z_order=2),
            TsicSource(pigpio_pi, 26,          label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.0, 0.0, 1.0], z_order=2),
            Ds1820Source('10-000801dd3c70', 1, label='WW Vorlauf',       unit='°C', value_format='{:.1f}', color=[0.9, 0.0, 0.7, 1.0], z_order=0),
            TsicSource(pigpio_pi, 12,          label='Rücklauf',         unit='°C', value_format='{:.1f}', color=[0.5, 0.1, 0.5, 1.0], z_order=1),
            Ds1820Source('28-000008640446', 1, label='Heizgas',          unit='°C', value_format='{:.1f}', color=[0.8, 0.6, 0.3, 1.0], z_order=-1, with_graph=False),
            Ds1820Source('28-0000089a5063', 1, label='Flüssigkeit',      unit='°C', value_format='{:.1f}', color=[0.1, 0.2, 0.4, 1.0], z_order=-1, with_graph=False),
            Ds1820Source('28-0000089b1ca2', 1, label='Sauggas',          unit='°C', value_format='{:.1f}', color=[0.4, 0.3, 0.1, 1.0], z_order=-1, with_graph=False),
        ]},
        {'label' : 'Heizung',
         'sources' : [
            Ds1820Source('10-000801f6dc25', 1, label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.6, 0.6, 1.0], z_order=2),
            Ds1820Source('10-000801dd3975', 2, label='Heizung Rücklauf', unit='°C', value_format='{:.1f}', color=[0.7, 0.6, 1.0, 1.0], z_order=1),
        ]},
        {'label' : 'Lüftung',
         'sources' : [
            Ds1820Source('28-000008656f81', 1, label='Frischluft',       unit='°C', value_format='{:.1f}', color=[0.2, 0.8, 1.0, 1.0], z_order=-1),
            Ds1820Source('10-000801dcfc0f', 1, label='Fortluft',         unit='°C', value_format='{:.1f}', color=[0.7, 0.3, 0.1, 1.0], z_order=-1),
            TsicSource(pigpio_pi, 16,          label='Zuluft',           unit='°C', value_format='{:.1f}', color=[0.7, 0.8, 0.9, 1.0], z_order=0),
            TsicSource(pigpio_pi, 20,          label='Abluft',           unit='°C', value_format='{:.1f}', color=[0.9, 0.6, 0.3, 1.0], z_order=0),
            TsicSource(pigpio_pi, 21,          label='Außentemperatur',  unit='°C', value_format='{:.1f}', color=[0.1, 0.5, 0.2, 1.0], z_order=1),
        ]}
    ],
    
    'mqtt_broker_host' : 'mqttbrokerhost'
}
