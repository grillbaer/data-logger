"""
Test configuration for development containing random test signals.
To be used as import in main.py for simulation.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from signalsources import TestSource

signal_sources_config = {
    'groups' : [
        {'label' : 'Wärmepumpe',
         'sources' : [
            TestSource(12.5, 2, label='Quelle ein',       unit='°C', value_format='{:.1f}', color=[0.5, 0.5, 1.0, 1.0], z_order=1),
            TestSource(9.3,  2, label='Quelle aus',       unit='°C', value_format='{:.1f}', color=[0.0, 0.2, 1.0, 1.0], z_order=2),
            TestSource(35, 0.1, label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.0, 0.0, 1.0], z_order=2),
            TestSource(52, 0.2, label='WW Vorlauf',       unit='°C', value_format='{:.1f}', color=[0.9, 0.0, 0.7, 1.0], z_order=0),
            TestSource(28, 0.3, label='Rücklauf',         unit='°C', value_format='{:.1f}', color=[0.5, 0.1, 0.5, 1.0], z_order=1),
            TestSource(57, 0.1, label='Heizgas',          unit='°C', value_format='{:.1f}', color=[0.8, 0.6, 0.3, 1.0], z_order=-1, with_graph=False),
            TestSource(30, 0.1, label='Flüssigkeit',      unit='°C', value_format='{:.1f}', color=[0.1, 0.2, 0.4, 1.0], z_order=-1, with_graph=False),
            TestSource(18, 0.1, label='Sauggas',          unit='°C', value_format='{:.1f}', color=[0.4, 0.3, 0.1, 1.0], z_order=-1, with_graph=False),
        ]},
        {'label' : 'Heizung',
         'sources' : [
            TestSource(33,   1, label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.6, 0.6, 1.0], z_order=2),
            TestSource(25,   1, label='Heizung Rücklauf', unit='°C', value_format='{:.1f}', color=[0.7, 0.6, 1.0, 1.0], z_order=1),
        ]},
        {'label' : 'Lüftung',
         'sources' : [
            TestSource(-2,   3, label='Frischluft',       unit='°C', value_format='{:.1f}', color=[0.2, 0.8, 1.0, 1.0], z_order=-1),
            TestSource(6,    3, label='Fortluft',         unit='°C', value_format='{:.1f}', color=[0.7, 0.3, 0.1, 1.0], z_order=-1),
            TestSource(18,   1, label='Zuluft',           unit='°C', value_format='{:.1f}', color=[0.7, 0.8, 0.9, 1.0], z_order=0),
            TestSource(21.5, 1, label='Abluft',           unit='°C', value_format='{:.1f}', color=[0.9, 0.6, 0.3, 1.0], z_order=0),
            TestSource(-4, 0.1, label='Außentemperatur',  unit='°C', value_format='{:.1f}', color=[0.1, 0.5, 0.2, 1.0], z_order=1),
        ]}
    ],
    
#    'history_max' : 120,
#    'history_delta' : 1,

    'mqtt_broker_host' : 'holger-gb-15x',
    'web_app_port' : 5000
}
