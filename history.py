"""
Signal history in memory and persistence in plain CSV files.
Used as model of the graphs view.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

import csv
from datetime import datetime
import logging
import os
import re
from threading import RLock
import time

from signalsources import SignalSource 
from utils import RepeatTimer

logger = logging.getLogger().getChild(__name__) 


class SignalHistory:
    MAX_SECONDS_DEFAULT = 24 * 3600  # 1 day
    DELTA_SECONDS_DEFAULT = 60  # every minute
    MAX_SECONDS_CSV_FILES = 24 * 3600 * 32  # 32 days

    def __init__(self):
        
        self.max_seconds = SignalHistory.MAX_SECONDS_DEFAULT
        self.delta_seconds = SignalHistory.DELTA_SECONDS_DEFAULT
        self.max_seconds_csv_files = SignalHistory.MAX_SECONDS_CSV_FILES
        self.max_csv_lines = self.max_seconds // self.delta_seconds + 1
        
        self.sources = []
        self._values_by_source_id = {}
        self._timer = None
        self._data_lock = RLock()
        self._csv_file_basename = None
        self._csv_file = None
        self._csv_writer = None
        self._csv_lines = 0

    def __enter__(self):
        self._data_lock.acquire()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._data_lock.release()
        
    def add_source(self, signal_source):
        with self._data_lock:
            if signal_source in self.sources:
                self.sources.remove(signal_source)
            self.sources.append(signal_source)
            self._values_by_source_id[id(signal_source)] = []
    
    def remove_source(self, signal_source):
        with self._data_lock:
            self.sources.remove(signal_source)
            self._values_by_source_id.pop(id(signal_source))
    
    def start(self):
        if self._timer is None:
            logger.info('Starting to record history every ' + 
                        str(self.delta_seconds) + 's for ' + str(self.max_seconds) + 's')
            self._begin_new_csv_file()
            self._timer = RepeatTimer(self.delta_seconds, self.record)
            self._timer.start()
        
    def stop(self):
        if not self._timer is None:
            self._timer.cancel()
            self._timer = None
            self._close_csv_file()
            logger.info('Stopped recording history')

    def get_values(self, signal_source):
        with self._data_lock:
            return self._values_by_source_id[id(signal_source)]

    def record(self):
        row = []
        with self._data_lock:
            now = time.time()
            row.append(round(now, 3))
            self.__clean_old_history(now)
            for source in self.sources:
                value = source.last_value
                if (value is not None 
                      and value.status == SignalSource.STATUS_OK
                      and value.timestamp > now - self.delta_seconds
                      and source.running):
                    self._values_by_source_id[id(source)].append((now, value.value))
                    row.append(float(source.value_format.format(value.value)))
                else:
                    row.append(None)
        
        if self._csv_writer is not None:
            self._csv_writer.writerow(row)
            self._csv_lines += 1
            self._csv_file.flush()
            if self._csv_lines >= self.max_csv_lines:
                self._begin_new_csv_file()

    def __clean_old_history(self, now):
        with self._data_lock:
            for source_id in self._values_by_source_id:
                values = self._values_by_source_id[source_id]
                while len(values) > 1 and (now - values[1][0] > self.max_seconds):
                    values.pop(0)

    def write_to_csv(self, file_basename):
        self._close_csv_file()
        self._csv_file_basename = file_basename

    def _begin_new_csv_file(self):
        self._close_csv_file()
        if self._csv_file_basename is not None:
            self._delete_old_csv_files()
            file_name = self._new_csv_file_name()
            dir_name = os.path.split(file_name)[0]
            if dir_name != '':
                os.makedirs(dir_name, 0o775, True)
            logger.info("Writing new CSV file '" + file_name + "'")
            self._csv_file = open(file_name, 'w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(['Time'] + [source.label for source in self.sources])
            self._csv_lines = 1
    
    def _close_csv_file(self):
        if self._csv_file is not None:
            logger.info("'Closing CSV file '" + self._csv_file.name + "'")
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None
            self._csv_lines = 0
        
    def _new_csv_file_name(self):
        return '{:}-{:%Y-%m-%d-%H%M%S}.csv'.format(self._csv_file_basename, datetime.now())

    def _delete_old_csv_files(self):
        try:
            for file_info in self._list_csv_files():
                if file_info[1] + self.max_seconds < time.time() - self.max_seconds_csv_files:
                    logger.info("Deleting old CSV file '" + file_info[0] + "'")
                    os.remove(file_info[0])
        except:
            logger.exception('Failed to delete old CSV files')

    def _list_csv_files(self):
        """
        Read list of existing CSV files and their begin and modification times as list of tuples
        [(full_file_name, begin_timestamp, last_modified_timestamp), ...].
        """
        dir_name, file_prefix = os.path.split(self._csv_file_basename)
        file_pattern = re.compile('^' + file_prefix + '-(([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]{2})([0-9]{2})([0-9]{2})).csv$')
        
        csv_files = []
        for file in os.listdir(dir_name):
            match = file_pattern.match(file)
            if match is not None:
                full_path = os.path.join(dir_name, file)
                if os.path.isfile(full_path):
                    begin = datetime.strptime(match.group(1), '%Y-%m-%d-%H%M%S').timestamp()
                    modified = os.stat(full_path).st_mtime
                    csv_files.append((full_path, begin, modified))

        return sorted(csv_files, key=lambda x: x[1])

    def load_from_csv_files(self):
        logger.info('Trying to restore history from CSV files...')
        try:
            begin_time = time.time() - self.max_seconds
            for file_info in self._list_csv_files():
                if file_info[2] > begin_time:
                    self._load_rows_from_csv_file(begin_time, file_info[0])
        except:
            logger.exception('Failed to restore history from CSV files')

    def _load_rows_from_csv_file(self, begin_time, csv_file):
        logger.info("Restoring history from CSV file '" + csv_file + "'")
        len_sources = len(self.sources)
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            first_line = True
            for row in csv_reader:
                if first_line:
                    first_line = False
                elif len(row) == 1 + len_sources:
                    row_time = float(row[0])
                    if row_time >= begin_time:
                        for source, value_string in zip(self.sources, row[1:]):
                            if len(value_string) > 0:
                                value = float(value_string)
                                self._values_by_source_id[id(source)].append((row_time, value))
