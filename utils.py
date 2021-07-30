"""
Common utilities used in this project.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from threading import Thread
from threading import Event
import time


class RepeatTimer(Thread):
    """
    Repeating timer that calls a callback task() at regular interval seconds.
    """

    def __init__(self, interval, task):
        super().__init__()
        self.interval = interval
        self.task = task
        self.event = Event()
        self.event.set()

    def run(self):
        while self.event.is_set():
            self.task()
            time.sleep(self.interval)

    def cancel(self):
        self.event.clear()
