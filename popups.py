"""
UI popups.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from kivy.properties import StringProperty
from kivy.uix.popup import Popup


class OkCancelPopup(Popup):

    message = StringProperty()
    result = StringProperty()
    
    def __init__(self, ok_callback=None, title='missing title', **kwargs):
        super().__init__(title=title, **kwargs)
        self.ok_callback = ok_callback
        self.open()
        
    def ok_action(self):
        self.dismiss()
        self.result = 'ok'
        if not self.ok_callback is None:
            self.ok_callback()

    def cancel_action(self):
        self.dismiss()
        self.result = 'cancel'
