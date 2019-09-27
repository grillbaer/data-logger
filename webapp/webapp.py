from functools import partial
import json
import logging
from time import sleep

import cherrypy
from flask import Flask, Response, render_template

logger = logging.getLogger().getChild(__name__) 

    
class WebApp:
    """
        Web server for web UI.
    """
    def __init__(self):
        self.web_app_port = 5000
        self._signal_groups = []
        self._webapp = Flask(__name__, static_url_path='/static')
        self._init_routing()
        pass
    
    def use_signals_config(self, signal_sources_config):
        self.web_app_port = signal_sources_config['web_app_port']
        self._signal_groups = signal_sources_config['groups']
        for group in self._signal_groups:
            for source in group['sources']:
                source.add_callback(partial(self._publish_signal_value, source))
    
    def start(self):
        cherrypy.tree.graft(self._webapp, '/')
        cherrypy.config.update({
            'engine.autoreload_on': True,
            'log.screen': True,
            'server.socket_port': self.web_app_port,
            'server.socket_host': '0.0.0.0'
        })
        cherrypy.engine.start()
    
    def stop(self):
        cherrypy.engine.stop()
    
    def _publish_signal_value(self, source, value):
        pass

    def _signal_dict(self, source, value):
        return {
            'label'     : source.label,
            'unit'      : source.unit,
            'value'     : value.value,
            'status'    : value.status,
            'timestamp' : value.timestamp
        }
        
    def _signal_groups_dict(self):
        result = []
        for group in self._signal_groups:
            result_group = {'label' : group['label'], 'signals' : []}
            result.append(result_group)
            for source in group['sources']:
                result_group['signals'].append(self._signal_dict(source, source.last_value))
        return result
        
    def _init_routing(self):
        
        @self._webapp.route('/')
        def _measurements():
            return render_template('measurements.html', groups=self._signal_groups_dict())
        
        def _measurement_stream_generator():
            for i in range(100):
                sleep(0.5)
                yield 'data: Event %d\n\n' % i
                
        @self._webapp.route('/data/eventstream')
        def _event_stream():
            return Response(_measurement_stream_generator(), mimetype="text/event-stream")
        
        @self._webapp.route('/data/measurements')
        def _data_measurements():
            return json.dumps(self._signal_groups_dict())


if __name__ == '__main__':
    # Flask development server:
    # _webapp.run(threaded=True, debug=True)
    WebApp().start()
