import time
import logging
import threading

from influxdb import InfluxDBClient

from .utils import log_error

class DataLogger:

    @log_error
    def __init__(self, database=None, interval=1, log=None):
        self.log = log or logging.getLogger(app_name)
        self._is_ready = False

        try:
            self.client = InfluxDBClient(host='localhost', port=8086)
        except Exception as e:
            self.log.error(f"Failed to connect to influxdb: {e}")
            return

        self.thread = None
        self.running = False

        self.db = database
        self.interval = interval
        
        self.status = {}
        self.__read_data__ = None

    @log_error
    def set_read_data(self, func):
        self.__read_data__ = func

    @log_error
    def set_interval(self, interval):
        self.interval = interval

    @log_error
    def get_data(self):
        if self.__read_data__ is None:
            self.log.error("No read data function set")
            return {}
        data = self.__read_data__()
        if data == {}:
            return {}

        new_data = {}
        for key, value in data.items():
            if isinstance(value, bool):
                value = int(value)
            elif isinstance(value, list):
                continue
            elif isinstance(value, dict):
                continue
            new_data[key] = value

        return new_data

    @log_error
    def loop(self):
        start = time.time()
        while self.running:
            data = self.get_data()
            if data != {}:
                if self.db is not None:
                    status, msg = self.db.set('history', data)
                    if not status:
                        self.log.error(f"Failed to set data: {msg}")

            elapsed = time.time() - start
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            start += self.interval

    @log_error
    def start(self):
        if self.running:
            self.log.warning("Already running")
            return
        self.running = True
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()
        self.log.info("Data Logger Start")

    @log_error
    def stop(self):
        self.log.debug("Stopping Data Logger")
        if self.running:
            self.running = False
            self.thread.join()
        self.log.info("Data Logger stopped")
