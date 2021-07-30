"""
UI implementation of the service view.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import logging
import os
from subprocess import call

from kivy.uix.boxlayout import BoxLayout

from popups import OkCancelPopup

logger = logging.getLogger().getChild(__name__) 


class ServiceScreen(BoxLayout):

    def reboot_action(self):
        OkCancelPopup(title='Neustart', message='System jetzt neu starten?', ok_callback=self.reboot)

    def reboot(self):
        logger.info('REBOOT triggered')
        self.exec(['sudo', 'reboot', 'now'])
        
    def shutdown_action(self):
        OkCancelPopup(title='Herunterfahren', message='System jetzt herunterfahren?', ok_callback=self.shutdown)

    def shutdown(self):
        logger.info('SHUTDOWN triggered')
        self.exec(['sudo', 'shutdown', 'now'])
        
    def update_action(self):
        OkCancelPopup(title='Aktualisieren', message='Software jetzt aktualisieren und System neu starten?', ok_callback=self.update)
        
    def update(self):
        logger.info('UPDATE triggered')
        if self.exec(['sh', '-c', 'cd ' + os.getcwd() + '; git pull']) == 0:
            self.reboot()
    
    def exec(self, command):
        try:
            exit_code = call(command)
            if exit_code != 0:
                logger.error('Command ' + str(command) + ' exited with code ' + str(exit_code))
            return exit_code
        except IOError as ex:
            logger.error('Command ' + str(command) + ' failed: ' + str(ex))
            return -1
        
