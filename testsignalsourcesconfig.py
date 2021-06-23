"""
Test configuration for development containing random test signals.
To be used as import in main.py for simulation.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2019, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from signalsources import TestSource, TestDigitalSource, DeltaSource

_quelle_ein    = TestSource(       'temp-from-well',            12.5,  1, label='Quelle ein',        unit='°C', value_format='{:.1f}',    color=[0.5, 0.5, 1.0, 1.0], z_order=1)
_quelle_aus    = TestSource(       'temp-to-well',              10.3,  1, label='Quelle aus',        unit='°C', value_format='{:.1f}',    color=[0.0, 0.2, 1.0, 1.0], z_order=2)
_wp_hz_vor     = TestSource(       'temp-hp-heat-supply',       31.5,  1, label='Heizung Vorlauf',   unit='°C', value_format='{:.1f}',    color=[1.0, 0.0, 0.0, 1.0], z_order=2)
_wp_ww_vor     = TestSource(       'temp-hp-water-supply',      49.6,  1, label='Wasser Vorlauf',    unit='°C', value_format='{:.1f}',    color=[0.2, 0.3, 0.9, 1.0], z_order=0)
_wp_rueck      = TestSource(       'temp-hp-return',            25.1,  1, label='Rücklauf',          unit='°C', value_format='{:.1f}',    color=[0.5, 0.1, 0.7, 1.0], z_order=1)
_wp_mode       = TestDigitalSource('mode-boiler',               60,       label='Modus',             unit='',   text_0='HZ', text_1='WW', color=[0.4, 0.4, 0.4, 1.0], z_order=-1)
_hz_vor        = TestSource(       'temp-heat-supply',          30.1,  1, label='Heizung Vorlauf',   unit='°C', value_format='{:.1f}',    color=[1.0, 0.6, 0.6, 1.0], z_order=2)
_hz_rueck      = TestSource(       'temp-heat-return',          24.5,  1, label='Heizung Rücklauf',  unit='°C', value_format='{:.1f}',    color=[0.7, 0.6, 1.0, 1.0], z_order=1)
_ww_speicher_o = TestSource(       'temp-water-boiler-top',     46.2,  1, label='Wasser oben',       unit='°C', value_format='{:.1f}',    color=[0.8, 0.7, 1.0, 1.0], z_order=-1, corr_offset=+2.5)
_ww_speicher_u = TestSource(       'temp-water-boiler-middle',  38.8,  1, label='Wasser unten',      unit='°C', value_format='{:.1f}',    color=[0.4, 0.3, 0.5, 1.0], z_order=-2)
_ww_zirk       = TestSource(       'temp-water-circ-return',    34.2,  1, label='Zirkulation',       unit='°C', value_format='{:.1f}',    color=[0.1, 0.6, 0.4, 1.0], z_order=-1)
_lu_frisch     = TestSource(       'temp-air-fresh',             5.2,  1, label='Frischluft',        unit='°C', value_format='{:.1f}',    color=[0.2, 0.8, 1.0, 1.0], z_order=-1)
_lu_fort       = TestSource(       'temp-air-exhaust',           8.7,  1, label='Fortluft',          unit='°C', value_format='{:.1f}',    color=[0.7, 0.3, 0.1, 1.0], z_order=-1)
_lu_zu         = TestSource(       'temp-air-supply',           21.2,  1, label='Zuluft',            unit='°C', value_format='{:.1f}',    color=[0.7, 0.8, 0.9, 1.0], z_order=0)
_lu_ab         = TestSource(       'temp-air-return',           21.8,  1, label='Abluft',            unit='°C', value_format='{:.1f}',    color=[0.9, 0.6, 0.3, 1.0], z_order=0)
_lu_aussen     = TestSource(       'temp-outdoor',               5.0,  1, label='Außentemperatur',   unit='°C', value_format='{:.1f}',    color=[0.1, 0.5, 0.2, 1.0], z_order=1)
_ht_leistung   = TestSource(       'power-heat-high-tariff',    2000, 10, label='Leistung HT',       unit='W',  value_format='{:.0f}',    color=[0.9, 0.4, 0.1, 1.0], with_graph=False, small=False)
_nt_leistung   = TestSource(       'power-heat-low-tariff',     2000, 10, label='Leistung NT',       unit='W',  value_format='{:.0f}',    color=[0.2, 0.3, 0.9, 1.0], with_graph=False, small=False)
_ht_reading    = TestSource(       'reading-heat-high-tariff', 12345, 10, label='Stand HT',          unit='kWh',value_format='{:.1f}',    color=[0.9, 0.4, 0.1, 0.5], with_graph=False, small=True)
_nt_reading    = TestSource(       'reading-heat-low-tariff',  12345, 10, label='Stand NT',          unit='kWh',value_format='{:.1f}',    color=[0.2, 0.3, 0.9, 0.5], with_graph=False, small=True)

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
        ]}
    ],
    
    'mqtt_broker_host' : '',
    'mqtt_broker_port' : 1883,
    'mqtt_broker_user' : '',
    'mqtt_broker_password' : '',
    'mqtt_broker_base_topic' : 'data-logger-test',
    'mqtt_use_ssl' : True,
    'mqtt_broker_cacerts' : 'cacerts.pem'
}
