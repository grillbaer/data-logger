"""
Logging set-up.

NOTE: kivy sets the root logger to some strange and buggy behavior,
a patch is necessary: comment out 'logging.root = Logger' in kivy/logger.py
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging.config
import os
import psutil
import subprocess
import utils


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)-8.8s [%(threadName)-12.12s] %(name)-13.13s: %(message)s     [%(filename)s:%(lineno)d]',
            'datefmt': "%Y-%m-%d %H:%M:%S",
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'rotate_file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/datalogger.log',
            'encoding': 'utf8',
            'maxBytes': 1000000,
            'backupCount': 9,
        }
    },
    'loggers': {
        '': {
            'handlers': ['rotate_file'],
            'level': 'DEBUG',
        },
    }
}

logging.config.dictConfig(LOGGING)

logger = logging.getLogger().getChild(__name__)
logger.info('''


--------------------------------------------------------------------
--- DATALOGGER APPLICATION RESTART  --------------------------------
--------------------------------------------------------------------

''')

# ensure that the header has been printed before any other output
for handler in logger.handlers:
    handler.flush()


def _tick_out():
    try:
        cpu_temp = subprocess.check_output(
           'vcgencmd measure_temp', 
           stderr=subprocess.STDOUT, 
           shell=True).decode('latin-1').replace('\n', '').replace("'", "°")
    except:
        cpu_temp = 'temp unknown'
    
    try:
        this_process = psutil.Process(os.getpid())
        mem_usage = 'VM {:.1f}MB, RSS {:.1f}MB'.format(
           this_process.memory_info().vms / 1e6, 
           this_process.memory_info().rss / 1e6)
    except:
        mem_usage = 'mem unknown'
    
    logging.debug('TICK - CPU ' + cpu_temp + ', memory usage ' + mem_usage)

    
# Setup log timer tick to support diagnostics of power supply problems:
utils.RepeatTimer(60, _tick_out).start()
