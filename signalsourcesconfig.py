"""
Configuration for a setup with various temperature sensors of type
DS18x20 and TSIC 306.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import pigpio

from signalsources import TsicSource, Ds1820Source, DeltaSource

pigpio_pi = pigpio.pi()

_quelle_ein  = Ds1820Source('28-0000089b1ca2', 1, label='Quelle ein',       unit='°C', value_format='{:.1f}', color=[0.5, 0.5, 1.0, 1.0], z_order=1)
_quelle_aus  = Ds1820Source('28-000008640446', 1, label='Quelle aus',       unit='°C', value_format='{:.1f}', color=[0.0, 0.2, 1.0, 1.0], z_order=2)
_wp_hz_vor   = Ds1820Source('10-000801dd3c70', 1, label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.0, 0.0, 1.0], z_order=2)
_wp_ww_vor   = TsicSource(pigpio_pi, 26,          label='Wasser Vorlauf',   unit='°C', value_format='{:.1f}', color=[0.2, 0.3, 0.9, 1.0], z_order=0)
_wp_rueck    = TsicSource(pigpio_pi, 12,          label='Rücklauf',         unit='°C', value_format='{:.1f}', color=[0.5, 0.1, 0.7, 1.0], z_order=1)
_hz_vor      = Ds1820Source('10-000801f6dc25', 1, label='Heizung Vorlauf',  unit='°C', value_format='{:.1f}', color=[1.0, 0.6, 0.6, 1.0], z_order=2)
_hz_rueck    = Ds1820Source('10-000801dd3975', 1, label='Heizung Rücklauf', unit='°C', value_format='{:.1f}', color=[0.7, 0.6, 1.0, 1.0], z_order=1)
_lu_frisch   = Ds1820Source('28-000008656f81', 1, label='Frischluft',       unit='°C', value_format='{:.1f}', color=[0.2, 0.8, 1.0, 1.0], z_order=-1)
_lu_fort     = Ds1820Source('10-000801dcfc0f', 1, label='Fortluft',         unit='°C', value_format='{:.1f}', color=[0.7, 0.3, 0.1, 1.0], z_order=-1)
_lu_zu       = TsicSource(pigpio_pi, 16,          label='Zuluft',           unit='°C', value_format='{:.1f}', color=[0.7, 0.8, 0.9, 1.0], z_order=0)
_lu_ab       = TsicSource(pigpio_pi, 20,          label='Abluft',           unit='°C', value_format='{:.1f}', color=[0.9, 0.6, 0.3, 1.0], z_order=0)

signal_sources_config = {
    'groups' : [
        {'label' : 'Wärmepumpe',
         'sources' : [
            _quelle_ein,
            _quelle_aus,
            DeltaSource(_quelle_ein, _quelle_aus, label=' Quelle \u0394',   unit='K', value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            _wp_hz_vor,
            DeltaSource(_wp_hz_vor, _wp_rueck,    label=' Heizung \u0394',  unit='K', value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            _wp_ww_vor,
            DeltaSource(_wp_ww_vor, _wp_rueck,    label=' Wasser \u0394',   unit='K', value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            _wp_rueck,
        ]},
        {'label' : 'Heizung/Warmwasser',
         'sources' : [
            _hz_vor,
            _hz_rueck,
            DeltaSource(_hz_vor, _hz_rueck,    label=' Heizung \u0394',     unit='K',  value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            Ds1820Source('28-0000089a5063', 1, label='Zirkulation',         unit='°C', value_format='{:.1f}', color=[0.1, 0.6, 0.4, 1.0], z_order=-1),
        ]},
        {'label' : 'Lüftung',
         'sources' : [
            _lu_frisch,
            _lu_fort,
            DeltaSource(_lu_fort, _lu_frisch,  label=' Fort-Frisch \u0394', unit='K', value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            _lu_zu,
            _lu_ab,
            DeltaSource(_lu_ab, _lu_zu,        label=' Ab-Zu \u0394',       unit='K', value_format='{:.1f}', color=[0.8, 0.8, 0.8, 1.0], with_graph = False, with_history = False),
            TsicSource(pigpio_pi, 21,          label='Außentemperatur',     unit='°C', value_format='{:.1f}', color=[0.1, 0.5, 0.2, 1.0], z_order=1),
        ]}
    ],
    
    'mqtt_broker_host' : ''
}
